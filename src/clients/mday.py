import json

import httpx

from utils.data_models import Contact
from utils.logger import get_logger
from utils.retry_strategy import api_retry_strategy

logger = get_logger(__name__)

MONDAY_URL = "https://api.monday.com/v2"


class MondayClient:
    def __init__(self, api_key: str, board_id: str):
        logger.info("Initialising Monday object")
        self.board_id = board_id
        self._headers = {"Authorization": api_key, "Content-Type": "application/json"}
        self._session = httpx.AsyncClient()

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

    async def get_existing_contacts(self) -> list[dict]:
        """Return all contacts on the Monday board."""
        query = (
            """
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
            """
            % self.board_id
        )
        logger.info("Getting existing Monday contacts")
        return await self._post(query)

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
