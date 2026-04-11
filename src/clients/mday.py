import json

import httpx

from utils.data_models import Contact
from utils.logger import get_logger
from utils.retry_strategy import api_retry_strategy

logger = get_logger(__name__)

MONDAY_URL = "https://api.monday.com/v2"


class MondayClient:
    COLUMN_IDS = ["email", "phone", "linkedin"]

    def __init__(self, api_key: str, board_id: str):
        logger.info("Initialising Monday object")
        self.board_id = board_id
        self._headers = {"Authorization": api_key, "Content-Type": "application/json"}
        self._session = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._session.aclose()

    @api_retry_strategy
    async def _post(self, query: str, mday_vars: dict = None) -> dict:
        """Post to Monday API"""
        data = {"query": query, "variables": mday_vars or {}}
        response = await self._session.post(
            MONDAY_URL, json=data, headers=self._headers
        )
        response.raise_for_status()
        return response.json()

    async def get_existing_contacts(self) -> dict[str, dict]:
        """Fetch existing contacts from Monday and return as email-keyed dict."""
        items = await self._fetch_all_items()
        return self._build_contact_lookup(items)

    async def _fetch_all_items(self) -> list[dict]:
        """Return all contacts on the Monday board."""
        query = """
            query ($boardId: ID!, $cursor: String) {
                boards(ids: [$boardId]) {
                    items_page(limit: 500, cursor: $cursor) {
                        cursor
                        items {
                            id
                            name
                            column_values(ids: ["email", "phone", "linkedin"]) {
                                id
                                text
                            }
                        }
                    }
                }
            }
            """

        logger.info("Getting existing Monday contacts")

        all_items = []
        cursor = None

        while True:
            result = await self._post(
                query, {"boardId": self.board_id, "cursor": cursor}
            )
            page = result["data"]["boards"][0]["items_page"]
            all_items.extend(page["items"])
            cursor = page.get("cursor")
            logger.info(f"Retrieved {len(all_items)} Monday.com contacts so far")
            if not cursor:
                break

        logger.info(f"Fetched {len(all_items)} items from Monday board")
        return all_items

    @staticmethod
    def _build_contact_lookup(items: list[dict]) -> dict[str, dict]:
        """Build email-keyed lookup dict from raw Monday items."""
        contacts = {}
        for item in items:
            cols = {col["id"]: col["text"] for col in item["column_values"]}
            email = cols.get("email")
            if email:
                contacts[email] = {
                    "id": item["id"],
                    "name": item["name"],
                    "phone": cols.get("phone"),
                    "linkedin_url": cols.get("linkedin"),
                }
        return contacts

    async def post_new_contact(self, contact: Contact):
        """Make POST request to Monday of new contact"""
        query = (
            """
        mutation ($name: String!, $values: JSON!) {
            create_item(
                board_id: %s,
                item_name: $name,
                column_values: $values
            ) {
                id
            }
        }
        """
            % self.board_id
        )

        mday_vars = {
            "name": contact.name,
            "values": json.dumps(
                {
                    "email": {
                        "email": contact.email_address,
                        "text": contact.email_address,
                    },
                    "phone": contact.phone,
                    "linkedin": contact.linkedin_url,
                }
            ),
        }
        logger.info(f"Posting {contact.email_address} to Monday.com")
        return await self._post(query, mday_vars=mday_vars)
