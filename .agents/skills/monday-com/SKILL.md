---
name: monday-com
description: >
  Monday.com GraphQL API integration for Python — covers authentication, querying boards,
  reading existing items, creating new contacts, updating column values, and handling the
  Monday.com column value JSON format. Use this skill whenever working with the Monday.com
  API, managing board items, mapping contact fields to Monday columns, or building any
  Monday.com integration in Python.
---

# Monday.com Skill

## Overview

Monday.com uses a **GraphQL API** — not REST. Every operation is a query or mutation sent
as a POST request to a single endpoint. Column values have a specific JSON format that varies
by column type and is the most common source of bugs.

---

## Environment Variables

```bash
MONDAY_API_KEY=         # from Monday profile → Administration → API
MONDAY_BOARD_ID=        # from the board URL: monday.com/boards/123456789
```

Getting the API key: **Profile picture → Administration → API → Copy**

Getting the board ID: Open your board in the browser — the number in the URL is the board ID.

---

## Client

Full async client. Always use as a context manager.

```python
# clients/mday.py
import aiohttp
import json
from utils.logger import get_logger

logger = get_logger(__name__)

MONDAY_API_URL = "https://api.monday.com/v2"
API_VERSION = "2024-01"


class MondayClient:
    def __init__(self, api_key: str, board_id: str):
        self._api_key = api_key
        self._board_id = board_id
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": self._api_key,
                "Content-Type": "application/json",
                "API-Version": API_VERSION,
            }
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def _execute(self, query: str, variables: dict = None) -> dict:
        """Execute a GraphQL query or mutation."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with self._session.post(
            MONDAY_API_URL,
            json=payload,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        # Monday returns 200 even for errors — always check
        if "errors" in data:
            raise ValueError(f"Monday GraphQL error: {data['errors']}")

        return data.get("data", {})
```

---

## Reading Existing Contacts

Fetch all items from the board to build a lookup dict keyed by email address.
Used for deduplication — check before creating.

```python
    async def get_existing_contacts(self) -> dict[str, "Contact"]:
        """
        Returns dict of {email_address: Contact} for all items on the board.
        Fetches all pages — Monday paginates at 500 items by default.
        """
        query = """
        query GetContacts($board_id: ID!, $cursor: String) {
            boards(ids: [$board_id]) {
                items_page(limit: 500, cursor: $cursor) {
                    cursor
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
        contacts = {}
        cursor = None

        while True:
            data = await self._execute(
                query,
                {"board_id": self._board_id, "cursor": cursor}
            )

            page = data["boards"][0]["items_page"]
            items = page.get("items", [])

            for item in items:
                contact = _parse_monday_item(item)
                if contact.email_address:
                    contacts[contact.email_address.lower()] = contact

            cursor = page.get("cursor")
            if not cursor or not items:
                break

        logger.info(f"Fetched {len(contacts)} existing Monday contacts")
        return contacts
```

---

## Creating a New Item

```python
    async def post_new_contact(self, contact: "Contact") -> str:
        """Create a new board item. Returns the new item's Monday ID."""
        mutation = """
        mutation CreateItem($board_id: ID!, $name: String!, $column_values: JSON!) {
            create_item(
                board_id: $board_id,
                item_name: $name,
                column_values: $column_values
            ) {
                id
            }
        }
        """
        column_values = _build_column_values(contact)

        data = await self._execute(mutation, {
            "board_id": self._board_id,
            "name": contact.name or contact.email_address,
            "column_values": json.dumps(column_values),
        })

        item_id = data["create_item"]["id"]
        logger.info(f"Created Monday item {item_id} for {contact.email_address}")
        return item_id
```

---

## Updating an Existing Item

```python
    async def update_contact(self, monday_id: str, fields: dict) -> None:
        """Update specific column values on an existing item."""
        mutation = """
        mutation UpdateItem($board_id: ID!, $item_id: ID!, $column_values: JSON!) {
            change_multiple_column_values(
                board_id: $board_id,
                item_id: $item_id,
                column_values: $column_values
            ) {
                id
            }
        }
        """
        column_values = _build_column_values_from_fields(fields)

        await self._execute(mutation, {
            "board_id": self._board_id,
            "item_id": monday_id,
            "column_values": json.dumps(column_values),
        })

        logger.info(f"Updated Monday item {monday_id} with fields: {list(fields.keys())}")
```

---

## Column Value Format

This is the most error-prone part of Monday's API. Each column type requires a different
JSON structure. Pass as a JSON-encoded string in mutations.

```python
def _build_column_values(contact: "Contact") -> dict:
    """
    Map Contact fields to Monday column value format.
    Column IDs must match your actual board — find them via the API or board settings.
    """
    values = {}

    if contact.email_address:
        # Email column
        values["email"] = {
            "email": contact.email_address,
            "text": contact.email_address
        }

    if contact.phone:
        # Phone column
        values["phone"] = {
            "phone": contact.phone,
            "countryShortName": "GB"    # adjust for your region
        }

    if contact.linkedin:
        # Link/URL column
        values["linkedin"] = {
            "url": contact.linkedin,
            "text": contact.linkedin
        }

    if contact.job_title:
        # Text column — just a plain string
        values["job_title"] = contact.job_title

    if contact.website:
        # Link/URL column
        values["website"] = {
            "url": contact.website,
            "text": contact.website
        }

    if contact.address:
        # Long text column — plain string
        values["address"] = contact.address

    return values


def _build_column_values_from_fields(fields: dict) -> dict:
    """Build column values from a partial fields dict (for updates)."""
    # Create a temporary contact-like object and reuse _build_column_values
    # Or map directly — depends on your field naming
    column_map = {
        "phone":     lambda v: {"phone": v, "countryShortName": "GB"},
        "linkedin":  lambda v: {"url": v, "text": v},
        "job_title": lambda v: v,
        "website":   lambda v: {"url": v, "text": v},
        "address":   lambda v: v,
    }
    return {
        col: column_map[field](value)
        for field, value in fields.items()
        if field in column_map
        for col in [field]  # column ID matches field name in this project
        if value
    }
```

---

## Column Types Reference

| Monday Column Type | JSON Format |
|---|---|
| Email | `{"email": "a@b.com", "text": "a@b.com"}` |
| Phone | `{"phone": "+441234567890", "countryShortName": "GB"}` |
| Link/URL | `{"url": "https://...", "text": "display text"}` |
| Text | `"plain string"` |
| Long Text | `"plain string"` |
| Status | `{"label": "Active"}` or `{"index": 0}` |
| Date | `{"date": "2024-01-15"}` |
| Checkbox | `{"checked": "true"}` |
| Numbers | `"42"` (as string) |
| People | `{"personsAndTeams": [{"id": 123, "kind": "person"}]}` |

---

## Finding Your Column IDs

Column IDs are not the display names — they're slugs like `"email"`, `"phone0"`, `"text7"`.
Find them by querying the board:

```python
query = """
query {
    boards(ids: [YOUR_BOARD_ID]) {
        columns {
            id
            title
            type
        }
    }
}
"""
```

Run this once and map the IDs to your Contact fields. Hard-code the mapping in
`_build_column_values` — it won't change unless you restructure the board.

---

## Parsing Monday Items Back to Contacts

```python
from models.contact import Contact

def _parse_monday_item(item: dict) -> Contact:
    """Parse a Monday board item into a Contact model."""
    col = {cv["id"]: cv for cv in item.get("column_values", [])}

    def get_text(col_id: str) -> str | None:
        return col.get(col_id, {}).get("text") or None

    def get_value(col_id: str, key: str) -> str | None:
        raw = col.get(col_id, {}).get("value")
        if not raw:
            return None
        try:
            return json.loads(raw).get(key)
        except (json.JSONDecodeError, AttributeError):
            return None

    return Contact(
        monday_id=item["id"],
        name=item.get("name"),
        email_address=get_value("email", "email") or get_text("email") or "",
        phone=get_text("phone"),
        linkedin=get_value("linkedin", "url"),
        job_title=get_text("job_title"),
        website=get_value("website", "url"),
        address=get_text("address"),
    )
```

---

## Rate Limits

Monday's free/standard API allows ~5,000 requests/minute. For this project that's not a
concern. If you hit limits, the response is `429` with a `Retry-After` header.

Monday also has a **complexity limit** per query — fetching too many nested fields in one
query can exceed it. If you get a complexity error, reduce `$select` fields or page size.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `errors` in response body | Wrong query syntax or bad column ID | Check column IDs, validate GraphQL |
| `columnValueException` | Wrong JSON format for column type | Check column type vs format table above |
| `ItemsLimitationException` | Board item limit reached | Upgrade Monday plan |
| `AuthenticationException` | Bad or expired API key | Regenerate in Monday profile |
| `ComplexityException` | Query too large | Reduce page size or fields requested |

---

## Important Gotchas

- **Monday returns 200 for errors** — always check `data["errors"]` before using response
- **Column IDs are not display names** — query the board to find real IDs first
- **`column_values` must be JSON-encoded string** — `json.dumps(dict)`, not the dict itself
- **Item name is separate from column values** — pass as `item_name` parameter, not a column
- **Pagination uses cursor not offset** — store and pass the `cursor` from each response
- **`text` field in column_values is read-only** — it's what Monday renders, not what you set
