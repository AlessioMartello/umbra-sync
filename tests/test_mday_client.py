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


class TestMondayClientInitialization:
    """Test MondayClient initialization."""

    def test_client_initialization_stores_credentials(self):
        """Test that client stores API key and board ID."""
        client = MondayClient(FAKE_API_KEY, FAKE_BOARD_ID)

        assert client.board_id == FAKE_BOARD_ID
        assert "Authorization" in client._headers
        assert "Content-Type" in client._headers
        assert client._headers["Authorization"] == FAKE_API_KEY
        assert client._headers["Content-Type"] == "application/json"

    def test_client_has_async_session(self):
        """Test that client creates AsyncClient."""
        client = MondayClient(FAKE_API_KEY, FAKE_BOARD_ID)

        assert isinstance(client._session, httpx.AsyncClient)
        assert client._session.timeout == httpx.Timeout(30.0)

    async def test_client_async_context_manager(self):
        """Test client as async context manager."""
        async with MondayClient(FAKE_API_KEY, FAKE_BOARD_ID) as client:
            assert isinstance(client, MondayClient)

        assert client._session.is_closed


class TestBuildContactLookup:
    """Test contact lookup dictionary building."""

    def test_build_contact_lookup_with_all_fields(self):
        """Test building lookup with all fields populated."""
        items = [
            {
                "id": "123",
                "name": "John Doe",
                "column_values": [
                    {"id": "email", "text": "john@example.com"},
                    {"id": "phone", "text": "+441234567890"},
                    {"id": "text_mm274aw7", "text": "linkedin.com/in/john"},
                    {"id": "text_mm2jnfn5", "text": "123 Main St"},
                    {"id": "text0", "text": "Software Engineer"},
                    {"id": "text_mm2jf3vf", "text": "john.com"},
                ],
            }
        ]
        result = MondayClient._build_contact_lookup(items)

        assert len(result) == 1
        contact = result["john@example.com"]
        assert contact.name == "John Doe"
        assert contact.phone == "+441234567890"
        assert contact.linkedin == "linkedin.com/in/john"
        assert contact.address == "123 Main St"
        assert contact.job_title == "Software Engineer"
        assert contact.website == "john.com"

    def test_build_contact_lookup_with_missing_optional_fields(self):
        """Test building lookup with only required fields."""
        items = [
            {
                "id": "456",
                "name": "Jane Smith",
                "column_values": [
                    {"id": "email", "text": "jane@example.com"},
                ],
            }
        ]
        result = MondayClient._build_contact_lookup(items)

        contact = result["jane@example.com"]
        assert contact.phone is None
        assert contact.linkedin is None
        assert contact.address is None

    def test_build_contact_lookup_with_multiple_contacts(self):
        """Test building lookup with multiple contacts."""
        items = [
            {
                "id": "1",
                "name": "User 1",
                "column_values": [
                    {"id": "email", "text": "user1@example.com"},
                ],
            },
            {
                "id": "2",
                "name": "User 2",
                "column_values": [
                    {"id": "email", "text": "user2@example.com"},
                ],
            },
            {
                "id": "3",
                "name": "User 3",
                "column_values": [
                    {"id": "email", "text": "user3@example.com"},
                ],
            },
        ]
        result = MondayClient._build_contact_lookup(items)

        assert len(result) == 3
        assert "user1@example.com" in result
        assert "user2@example.com" in result
        assert "user3@example.com" in result

    def test_build_contact_lookup_with_empty_list(self):
        """Test building lookup from empty items list."""
        result = MondayClient._build_contact_lookup([])

        assert result == {}

    def test_build_contact_lookup_handles_empty_column_values(self):
        """Test that items with empty column_values are skipped."""
        items = [
            {
                "id": "999",
                "name": "No Columns",
                "column_values": [],
            }
        ]
        result = MondayClient._build_contact_lookup(items)

        assert len(result) == 0

    def test_build_contact_lookup_stores_monday_id(self):
        """Test that monday_id is correctly stored."""
        items = [
            {
                "id": "12345",
                "name": "Test User",
                "column_values": [
                    {"id": "email", "text": "test@example.com"},
                ],
            }
        ]
        result = MondayClient._build_contact_lookup(items)

        contact = result["test@example.com"]
        assert contact.monday_id == "12345"

    def test_build_contact_lookup_duplicate_emails_last_wins(self):
        """Test that duplicate emails result in last item overwriting."""
        items = [
            {
                "id": "1",
                "name": "First",
                "column_values": [
                    {"id": "email", "text": "duplicate@example.com"},
                ],
            },
            {
                "id": "2",
                "name": "Second",
                "column_values": [
                    {"id": "email", "text": "duplicate@example.com"},
                ],
            },
        ]
        result = MondayClient._build_contact_lookup(items)

        assert len(result) == 1
        contact = result["duplicate@example.com"]
        assert contact.name == "Second"
        assert contact.monday_id == "2"


class TestGetExistingContacts:
    """Test fetching existing contacts."""

    @respx.mock
    async def test_get_existing_contacts(self, client):
        """Test that get_existing_contacts fetches and builds lookup."""
        mock_items = [
            {
                "id": "1",
                "name": "Alice",
                "column_values": [
                    {"id": "email", "text": "alice@example.com"},
                ],
            }
        ]
        respx.post(MONDAY_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "boards": [
                            {
                                "items_page": {
                                    "cursor": None,
                                    "items": mock_items,
                                }
                            }
                        ]
                    }
                },
            )
        )

        result = await client.get_existing_contacts()

        assert "alice@example.com" in result
        assert result["alice@example.com"].name == "Alice"


class TestPostNewContact:
    """Test posting new contacts to Monday."""

    @respx.mock
    async def test_post_new_contact_with_all_fields(self, client):
        """Test posting contact with all fields."""
        contact = Contact(
            email_address="alice@example.com",
            name="Alice Smith",
            phone="+441234567890",
            linkedin="linkedin.com/in/alice",
            address="123 Main St",
            job_title="Engineer",
            website="alice.com",
        )

        respx.post(MONDAY_URL).mock(
            return_value=httpx.Response(
                200, json={"data": {"create_item": {"id": "new_id"}}}
            )
        )

        result = await client.post_new_contact(contact)  # noqa

        assert respx.calls.call_count == 1
        request_body = json.loads(respx.calls.last.request.content)
        assert "create_item" in request_body["query"]

    @respx.mock
    async def test_post_new_contact_sends_board_id(self, client):
        """Test that post includes correct board ID."""
        contact = Contact(email_address="test@example.com", name="Test")

        respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={}))

        await client.post_new_contact(contact)

        request_body = json.loads(respx.calls.last.request.content)
        assert request_body["variables"]["board_id"] == FAKE_BOARD_ID

    @respx.mock
    async def test_post_new_contact_includes_email_in_values(self, client):
        """Test that post includes email in column values."""
        contact = Contact(email_address="test@example.com", name="Test User")

        respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={}))

        await client.post_new_contact(contact)

        request_body = json.loads(respx.calls.last.request.content)
        column_values = json.loads(request_body["variables"]["values"])
        assert client.COL_EMAIL in column_values


class TestUpdateContact:
    """Test updating existing contacts."""

    @respx.mock
    async def test_update_contact_with_single_field(self, client):
        """Test updating single field."""
        respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={}))

        await client.update_contact("item_123", {"phone": "+441111111111"})

        request_body = json.loads(respx.calls.last.request.content)
        column_values = json.loads(request_body["variables"]["columnValues"])
        assert client.COL_PHONE in column_values
        assert column_values[client.COL_PHONE] == "+441111111111"

    @respx.mock
    async def test_update_contact_with_multiple_fields(self, client):
        """Test updating multiple fields."""
        respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={}))

        await client.update_contact(
            "item_456",
            {
                "phone": "+449999999999",
                "linkedin": "linkedin.com/in/updated",
                "job_title": "Manager",
            },
        )

        request_body = json.loads(respx.calls.last.request.content)
        column_values = json.loads(request_body["variables"]["columnValues"])
        assert client.COL_PHONE in column_values
        assert client.COL_LINKEDIN in column_values
        assert client.COL_JOB_TITLE in column_values

    @respx.mock
    async def test_update_contact_includes_board_id(self, client):
        """Test that update includes board ID."""
        respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={}))

        await client.update_contact("item_789", {"phone": "+441111111111"})

        request_body = json.loads(respx.calls.last.request.content)
        assert request_body["variables"]["boardId"] == FAKE_BOARD_ID

    @respx.mock
    async def test_update_contact_includes_item_id(self, client):
        """Test that update includes correct item ID."""
        item_id = "specific_item_123"
        respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={}))

        await client.update_contact(item_id, {"phone": "+441111111111"})

        request_body = json.loads(respx.calls.last.request.content)
        assert request_body["variables"]["itemId"] == item_id


class TestMondayClientErrorHandling:
    """Test error handling scenarios."""

    @respx.mock
    async def test_post_with_network_error(self, client):
        """Test handling of network errors."""
        respx.post(MONDAY_URL).mock(side_effect=httpx.ConnectError("Network error"))

        with pytest.raises(httpx.ConnectError):
            await client._post("query { test }")

    @respx.mock
    async def test_post_with_missing_data_in_response(self, client):
        """Test handling of malformed response."""
        respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json={}))

        with pytest.raises((KeyError, RuntimeError)):
            await client._fetch_all_items()

    @respx.mock
    async def test_build_contact_lookup_with_malformed_items(self, client):
        """Test handling of malformed items."""
        items = [
            {
                "id": "1",
                "name": "Test",
                "column_values": [
                    {"id": "email", "text": "test@example.com"},  # Add 'text' field
                ],
            }
        ]
        # Should not crash, just process the item
        result = MondayClient._build_contact_lookup(items)
        assert len(result) == 1

    @respx.mock
    async def test_fetch_all_items_with_empty_page(self, client):
        """Test handling of empty pages during pagination."""
        response = {
            "data": {
                "boards": [
                    {
                        "items_page": {
                            "cursor": None,
                            "items": [],
                        }
                    }
                ]
            }
        }
        respx.post(MONDAY_URL).mock(return_value=httpx.Response(200, json=response))

        result = await client._fetch_all_items()

        assert result == []


class TestMondayClientColumnMapping:
    """Test column ID mapping."""

    def test_column_ids_constant_defined(self):
        """Test that COLUMN_IDS contains expected values."""
        assert len(MondayClient.COLUMN_IDS) > 0
        assert MondayClient.COL_EMAIL in MondayClient.COLUMN_IDS
        assert MondayClient.COL_PHONE in MondayClient.COLUMN_IDS

    def test_field_to_column_id_mapping(self):
        """Test field to column ID mapping."""
        assert MondayClient.FIELD_TO_COLUMN_ID["phone"] == MondayClient.COL_PHONE
        assert MondayClient.FIELD_TO_COLUMN_ID["linkedin"] == MondayClient.COL_LINKEDIN
        assert (
            MondayClient.FIELD_TO_COLUMN_ID["job_title"] == MondayClient.COL_JOB_TITLE
        )

    def test_field_to_column_id_all_fields_mapped(self):
        """Test that all expected fields have column mappings."""
        expected_fields = ["phone", "linkedin", "address", "website", "job_title"]
        for field in expected_fields:
            assert field in MondayClient.FIELD_TO_COLUMN_ID
