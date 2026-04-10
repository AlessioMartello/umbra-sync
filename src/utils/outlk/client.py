import datetime
import logging

import httpx
import msal
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    retry_if_exception_type,
)

from utils.logger import get_logger

logger = get_logger(__name__)


AUTHORITY = "https://login.microsoftonline.com/consumers"
NUM_EMAILS_TO_RETRIEVE_PER_REQUEST = 50


class OutlookClient:
    def __init__(self, client_id: str, refresh_token: str):
        logger.info("Initialising Outlook object")
        # self.mailbox = mailbox
        self._session = httpx.AsyncClient()
        self._token: str | None = None
        app = msal.PublicClientApplication(client_id, authority=AUTHORITY)
        self._token_response = app.acquire_token_by_refresh_token(
            refresh_token, scopes=["https://graph.microsoft.com/Mail.Read"]
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._session.aclose()

    def _get_token(self) -> str:
        """Authorise to the client"""
        if "access_token" in self._token_response:
            return self._token_response["access_token"]
        else:
            logger.info(
                f"Refresh failed: {self._token_response.get('error_description')}"
            )

    def _headers(self) -> dict:
        """Return API call headers"""
        return {"Authorization": f"Bearer {self._get_token()}"}

    @retry(
        retry=retry_if_exception_type(
            (
                httpx.HTTPStatusError,  # 429, 500, 502, 503 etc
                httpx.ConnectError,  # DNS failure, connection refused
                httpx.TimeoutException,  # request timed out
                httpx.ReadError,  # connection reset mid-response
            )
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _get(self, url: str, params: dict = None) -> dict:
        """Make GET request to Outlook API"""
        response = await self._session.get(url, headers=self._headers(), params=params)
        response.raise_for_status()
        return response.json()

    async def _paginate(self, all_emails: list, next_link: str = None) -> list:
        """Paginate using Outlook nextlink in response"""
        while next_link:
            data = await self._get(next_link)  # No params needed for nextLink
            all_emails.extend(data.get("value", []))
            next_link = data.get("@odata.nextLink")
        return all_emails

    async def get_inbox_items(self, since: datetime = None) -> list:
        """Return Inbox emails"""
        all_inbox_emails = []
        params = {
            "$select": "subject,from,receivedDateTime,body,inferenceClassification",
            "$top": NUM_EMAILS_TO_RETRIEVE_PER_REQUEST,
        }

        if since:
            params["$filter"] = (
                f"receivedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            )

        logger.info("Fetching Outlook Inbox items")
        data = await self._get(
            "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages",
            params=params,
        )
        all_inbox_emails.extend(data.get("value", []))

        next_link = data.get("@odata.nextLink")
        items = await self._paginate(all_inbox_emails, next_link)
        logger.info(f"Returned {len(items)} inbox items")
        return items

    async def get_sent_items(self) -> list:
        """Returns Sent emais"""
        all_sent_emails = []
        params = {"$select": "toRecipients", "$top": NUM_EMAILS_TO_RETRIEVE_PER_REQUEST}

        logger.info("Fetching Outlook Sent items")
        data = await self._get(
            "https://graph.microsoft.com/v1.0/me/mailFolders/sentItems/messages",
            params=params,
        )
        all_sent_emails.extend(data.get("value", []))

        next_link = data.get("@odata.nextLink")
        items = await self._paginate(all_sent_emails, next_link)
        logger.info(f"Returned {len(items)} sent items")
        return items
