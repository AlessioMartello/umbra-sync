import json

import httpx

from utils.data_models import Contact
from utils.logger import get_logger
from utils.retry_strategy import api_retry_strategy

logger = get_logger(__name__)

MONDAY_URL = "https://api.monday.com/v2"


class MondayClient:
    COL_EMAIL = "email"
    COL_PHONE = "phone"
    COL_ADDRESS = "text_mm2jnfn5"
    COL_WEBSITE = "text_mm2jf3vf"
    COL_JOB_TITLE = "text0"
    COL_LINKEDIN = "text_mm274aw7"

    COLUMN_IDS = [
        COL_EMAIL,
        COL_PHONE,
        COL_ADDRESS,
        COL_WEBSITE,
        COL_JOB_TITLE,
        COL_LINKEDIN,
    ]

    FIELD_TO_COLUMN_ID = {
        "phone": COL_PHONE,
        "linkedin": COL_LINKEDIN,
        "address": COL_ADDRESS,
        "website": COL_WEBSITE,
        "job_title": COL_JOB_TITLE,
    }

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
        result = response.json()
        if "errors" in result:
            raise RuntimeError(f"Monday API error: {result['errors']}")
        return result

    async def get_existing_contacts(self) -> dict[str, Contact]:
        """Fetch existing contacts from Monday and return as email-keyed dict."""
        items = await self._fetch_all_items()
        return self._build_contact_lookup(items)

    async def _fetch_all_items(self) -> list[dict]:
        """Return all contacts on the Monday board."""
        query = """
            query ($boardId: ID!, $cursor: String, $columnIds: [String!]!) {
                boards(ids: [$boardId]) {
                    items_page(limit: 500, cursor: $cursor) {
                        cursor
                        items {
                            id
                            name
                            column_values(ids: $columnIds) {
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
                query,
                {
                    "boardId": self.board_id,
                    "cursor": cursor,
                    "columnIds": MondayClient.COLUMN_IDS,
                },
            )
            page = result["data"]["boards"][0]["items_page"]
            all_items.extend(page["items"])
            cursor = page.get("cursor")
            logger.info(f"Retrieved {len(all_items)} Monday.com contacts so far")
            if not cursor:
                break

        logger.info(f"Fetched {len(all_items)} items from Monday board")
        return all_items

    @classmethod
    def _build_contact_lookup(cls, items: list[dict]) -> dict[str, Contact]:
        """Build email-keyed lookup dict from raw Monday items."""
        contacts = {}
        for item in items:
            cols = {col["id"]: col["text"] for col in item["column_values"]}
            email = cols.get("email")
            if email:
                contacts[email] = Contact(
                    email_address=email,
                    name=item["name"],
                    phone=cols.get(cls.COL_PHONE),
                    linkedin=cols.get(cls.COL_LINKEDIN),
                    monday_id=item["id"],
                    address=cols.get(cls.COL_ADDRESS),
                    website=cols.get(cls.COL_WEBSITE),
                    job_title=cols.get(cls.COL_JOB_TITLE),
                )
        return contacts

    async def post_new_contact(self, contact: Contact):
        """Make POST request to Monday of new contact"""
        query = """
        mutation ($board_id: ID!, $name: String!, $values: JSON!) {
            create_item(
                board_id: $board_id,
                item_name: $name,
                column_values: $values
            ) {
                id
            }
        }
        """

        mday_vars = {
            "board_id": self.board_id,
            "name": contact.name,
            "values": json.dumps(
                {
                    self.COL_EMAIL: {
                        "email": contact.email_address,
                        "text": contact.email_address,
                    },
                    self.COL_PHONE: contact.phone,
                    self.COL_LINKEDIN: contact.linkedin,
                    self.COL_ADDRESS: contact.address,
                    self.COL_WEBSITE: contact.website,
                    self.COL_JOB_TITLE: contact.job_title,
                }
            ),
        }
        logger.debug(f"Posting {contact.email_address} to Monday.com")
        return await self._post(query, mday_vars=mday_vars)

    async def update_contact(self, monday_id: str, fields: dict) -> None:
        """Update existing Monday contact, matching on ID"""
        translated_monday_fields = {
            self.FIELD_TO_COLUMN_ID[field]: value for field, value in fields.items()
        }
        query = """
        mutation ($boardId: ID!, $itemId: ID!, $columnValues: JSON!) {
            change_multiple_column_values(
                board_id: $boardId,
                item_id: $itemId,
                column_values: $columnValues
            ) { id }
        }
        """
        res = await self._post(
            query,
            {
                "boardId": self.board_id,
                "itemId": monday_id,
                "columnValues": json.dumps(translated_monday_fields),
            },
        )

        logger.debug(f"update response {res}")
