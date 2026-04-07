import httpx
import json

from utils.data_models import Contact

URL = "https://api.monday.com/v2"

class MondayClient:
    def __init__(self, api_key: str, board_id: str):
        self.board_id = board_id
        self._headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        self._session = httpx.AsyncClient()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._session.aclose()

    async def _post(self, query:str, vars:dict= None) -> dict:
        data = {"query": query, "variables": vars or {}}
        response = await self._session.post(URL, json=data, headers=self._headers)
        response.raise_for_status()
        return response.json()

    async def get_existing_contacts(self):
        """Return set of all contacts already on the board."""
        query = """
        {
            boards(ids: %s) {
                name
                items_page {
                items {
                    id
                    name
                    column_values {
                    id
                    text
                    value
                    }
                }
                }
            }
            }
            """ % self.board_id
        return await self._post(query)
    
    async def post_new_contacts(self, contact: Contact):
        query = """
        mutation ($name: String!, $values: JSON!) {
            create_item(
                board_id: %s,
                item_name: $name,
                column_values: $values
            ) {
                id
            }
        }
        """ % self.board_id

        vars = {
                "name": contact.name,
                "values": json.dumps({
                    "email": {"email": contact.email, "text": contact.email},
                    "phone": contact.phone,
                })
                }

        return await self._post(query, vars=vars)