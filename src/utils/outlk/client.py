import httpx
import msal
import datetime

AUTHORITY = "https://login.microsoftonline.com/consumers"

class OutlookClient:
    def __init__(self, client_id: str, refresh_token: str):
        # self.mailbox = mailbox
        self._session = httpx.AsyncClient()
        self._token: str | None = None
        # self._token_expiry: datetime | None = None
        app = msal.PublicClientApplication(client_id, authority=AUTHORITY)
        self._token_response = app.acquire_token_by_refresh_token(
            refresh_token,
            scopes=["https://graph.microsoft.com/Mail.Read"]
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._session.aclose()
    
    def _get_token(self) -> str:
        """Authorise to the client"""
        if "access_token" in self._token_response:
            print("Access Token acquired!")
            return self._token_response["access_token"]
        else:
            print(f"Refresh failed: {self._token_response.get('error_description')}")

    def _headers(self) -> dict:
        """Return API call headers"""
        return {"Authorization": f"Bearer {self._get_token()}"}

    async def _get(self, url: str, params: dict = None) -> dict:
        """Make GET request"""       
        response = await self._session.get(url, headers=self._headers(), params=params)
        response.raise_for_status()
        return response.json()

    async def get_inbox_items(self):
        """Retrun Inbox emails"""
        params = {
        "$orderby": "receivedDateTime desc",
        "$select": "subject,from,receivedDateTime,body,inferenceClassification", 
        "$top": 100
        } 
        return await self._get("https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages", params=params)

    def get_sent_items(self):
        ...