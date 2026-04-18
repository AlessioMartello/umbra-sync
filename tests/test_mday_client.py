import json

import pytest
import respx
import httpx

from clients.mday import MondayClient, MONDAY_URL
from utils.data_models import Contact

FAKE_API_KEY = "test_key"
FAKE_BOARD_ID = "12345"


@pytest.fixture
def client():
    return MondayClient(FAKE_API_KEY, FAKE_BOARD_ID)


def test_build_contact_lookup_returns_email_keyed_dict():
    items = [
        {
            "id": "111",
            "name": "Alice Smith",
            "column_values": [
                {"id": "email", "text": "alice@example.com"},
                {"id": "phone", "text": "07700900000"},
                {"id": "text_mm274aw7", "text": "linkedin.com/in/alice"},
            ],
        }
    ]
    result = MondayClient._build_contact_lookup(items)
    assert len(result) == 1

    assert "alice@example.com" in result
    contact = result["alice@example.com"]
    assert contact.name == "Alice Smith"
    assert contact.phone == "07700900000"
    assert contact.linkedin == "linkedin.com/in/alice"
    assert contact.monday_id == "111"


def test_build_contact_lookup_skips_items_without_email():
    items = [
        {
            "id": "111",
            "name": "No Email",
            "column_values": [
                {"id": "phone", "text": "07700900000"},
            ],
        }
    ]
    result = MondayClient._build_contact_lookup(items)
    assert len(result) == 0


@respx.mock
async def test_post_new_contact(client):
    contact = Contact(
        email_address="alice@example.com",
        name="Alice Smith",
        phone="07700900000",
        linkedin="linkedin.com/in/alice",
    )

    respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={"foo": "bar"}))

    await client.post_new_contact(contact)
    assert respx.calls.call_count == 1


@respx.mock
async def test_update_contact(client):

    respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={"foo": "bar"}))

    await client.update_contact("12345", {"linkedin": "linkedin.com/in/alice"})

    # Check the request body contained the translated column ID
    request_body = respx.calls.last.request.content
    body = json.loads(request_body)
    column_values = json.loads(body["variables"]["columnValues"])

    assert client.COL_LINKEDIN in column_values  # translated
    assert "linkedin" not in column_values  # original not present

    assert respx.calls.call_count == 1


@respx.mock
async def test_fetch_all_items_returns_raw_items(client):
    page_1 = {
        "data": {
            "boards": [
                {
                    "items_page": {
                        "cursor": "abc123",
                        "items": [{"id": "1", "name": "Alice", "column_values": []}],
                    }
                }
            ]
        }
    }
    page_2 = {
        "data": {
            "boards": [
                {
                    "items_page": {
                        "cursor": None,
                        "items": [{"id": "2", "name": "Bob", "column_values": []}],
                    }
                }
            ]
        }
    }

    respx.post("https://api.monday.com/v2").mock(
        side_effect=[
            httpx.Response(200, json=page_1),
            httpx.Response(200, json=page_2),
        ]
    )

    result = await client._fetch_all_items()

    assert len(result) == 2
    assert result[0]["id"] == "1"
    assert result[1]["id"] == "2"
    assert respx.calls.call_count == 2


@respx.mock
async def test_post_failure(client):
    respx.post(MONDAY_URL).mock(
        return_value=httpx.Response(200, json={"errors": "failed"})
    )

    with pytest.raises(RuntimeError):
        await client._post("query { test }")
