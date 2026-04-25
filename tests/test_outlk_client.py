import datetime

import pytest
import respx
import httpx
from unittest.mock import Mock, patch

from clients.outlk import OutlookClient, AUTHORITY, NUM_EMAILS_TO_RETRIEVE_PER_REQUEST


class TestOutlookClientInitialization:
    """Test OutlookClient initialization and token management."""

    def test_client_initialization_with_valid_credentials(self):
        """Test successful client initialization with mock MSAL."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "valid_token_123"
            }
            mock_msal.return_value = mock_app_instance

            client = OutlookClient(
                client_id="test_client_id", refresh_token="test_refresh"
            )

            assert client._token_response["access_token"] == "valid_token_123"
            mock_msal.assert_called_once_with("test_client_id", authority=AUTHORITY)
            mock_app_instance.acquire_token_by_refresh_token.assert_called_once()

    def test_client_initialization_with_failed_refresh(self):
        """Test client initialization when token refresh fails."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "error": "invalid_grant",
                "error_description": "Token has expired",
            }
            mock_msal.return_value = mock_app_instance

            client = OutlookClient(
                client_id="test_client_id", refresh_token="expired_token"
            )

            assert "error" in client._token_response
            assert client._token_response["error"] == "invalid_grant"

    async def test_async_context_manager(self):
        """Test OutlookClient async context manager protocol."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                assert isinstance(client, OutlookClient)
                assert isinstance(client._session, httpx.AsyncClient)

            # Session should be closed after context exit
            assert client._session.is_closed


class TestOutlookClientTokenManagement:
    """Test token retrieval and header generation."""

    def test_get_token_returns_valid_token(self):
        """Test _get_token returns access token when present."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "valid_token_xyz"
            }
            mock_msal.return_value = mock_app_instance

            client = OutlookClient(client_id="test", refresh_token="test")
            token = client._get_token()

            assert token == "valid_token_xyz"

    def test_get_token_logs_error_when_refresh_fails(self, caplog):
        """Test _get_token logs error when access_token not in response."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "error": "invalid_grant",
                "error_description": "Refresh token has expired",
            }
            mock_msal.return_value = mock_app_instance

            client = OutlookClient(client_id="test", refresh_token="test")

            with caplog.at_level("INFO"):
                result = client._get_token()

            assert result is None
            assert "Refresh failed" in caplog.text

    def test_headers_includes_bearer_token(self):
        """Test _headers returns properly formatted Authorization header."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "bearer_token_abc"
            }
            mock_msal.return_value = mock_app_instance

            client = OutlookClient(client_id="test", refresh_token="test")
            headers = client._headers()

            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer bearer_token_abc"


class TestOutlookClientHttpMethods:
    """Test HTTP request methods."""

    @respx.mock
    async def test_get_makes_authorized_request(self):
        """Test _get sends proper authorization headers."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "test_token"
            }
            mock_msal.return_value = mock_app_instance

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                respx.get("https://api.test.com/endpoint").mock(
                    return_value=httpx.Response(200, json={"data": "test"})
                )

                result = await client._get("https://api.test.com/endpoint")

                assert result == {"data": "test"}
                request = respx.calls.last.request
                assert request.headers["Authorization"] == "Bearer test_token"

    @respx.mock
    async def test_get_with_query_parameters(self):
        """Test _get includes query parameters."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                respx.get("https://api.test.com/endpoint?$top=50&$filter=test").mock(
                    return_value=httpx.Response(200, json={"data": []})
                )

                params = {"$top": 50, "$filter": "test"}
                result = await client._get(
                    "https://api.test.com/endpoint", params=params
                )

                assert result == {"data": []}

    @respx.mock
    async def test_get_handles_http_errors(self):
        """Test _get raises on HTTP errors."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                respx.get("https://api.test.com/error").mock(
                    return_value=httpx.Response(401, json={"error": "Unauthorized"})
                )

                with pytest.raises(httpx.HTTPStatusError):
                    await client._get("https://api.test.com/error")


class TestOutlookClientPagination:
    """Test pagination logic for multi-page responses."""

    async def test_paginate_with_no_next_link(self):
        """Test _paginate returns emails unchanged when no nextLink."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                initial_emails = [{"id": "1", "subject": "Test"}]
                result = await client._paginate(initial_emails.copy(), next_link=None)

                assert result == initial_emails

    @respx.mock
    async def test_paginate_with_multiple_pages(self):
        """Test _paginate fetches all pages using nextLink."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            page_2_data = {
                "value": [{"id": "2", "subject": "Page 2"}],
                "@odata.nextLink": "https://api/page3",
            }
            page_3_data = {
                "value": [{"id": "3", "subject": "Page 3"}],
            }

            respx.get("https://api/page2").mock(
                return_value=httpx.Response(200, json=page_2_data)
            )
            respx.get("https://api/page3").mock(
                return_value=httpx.Response(200, json=page_3_data)
            )

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                initial_emails = [{"id": "1", "subject": "Page 1"}]
                result = await client._paginate(
                    initial_emails, next_link="https://api/page2"
                )

                assert len(result) == 3
                assert result[0]["id"] == "1"
                assert result[1]["id"] == "2"
                assert result[2]["id"] == "3"

    @respx.mock
    async def test_paginate_handles_empty_value_responses(self):
        """Test _paginate handles responses with missing 'value' key."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            respx.get("https://api/page").mock(
                return_value=httpx.Response(200, json={})
            )

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                initial_emails = [{"id": "1"}]
                result = await client._paginate(
                    initial_emails, next_link="https://api/page"
                )

                assert len(result) == 1  # Only initial email, nothing added


class TestOutlookClientInboxRetrieval:
    """Test inbox and sent items retrieval."""

    @respx.mock
    async def test_get_inbox_items_without_since_filter(self):
        """Test get_inbox_items retrieves inbox without date filter."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            inbox_response = {
                "value": [
                    {"id": "email1", "subject": "Test 1"},
                    {"id": "email2", "subject": "Test 2"},
                ]
            }

            respx.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
            ).mock(return_value=httpx.Response(200, json=inbox_response))

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                result = await client.get_inbox_items()

                assert len(result) == 2
                assert result[0]["id"] == "email1"

                # Verify request params
                request = respx.calls.last.request
                assert "$top" in request.url.params
                assert request.url.params["$top"] == str(
                    NUM_EMAILS_TO_RETRIEVE_PER_REQUEST
                )

    @respx.mock
    async def test_get_inbox_items_with_since_filter(self):
        """Test get_inbox_items applies date filter when since provided."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            inbox_response = {"value": [{"id": "email1", "subject": "Recent"}]}

            respx.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
            ).mock(return_value=httpx.Response(200, json=inbox_response))

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                since = datetime.datetime(
                    2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
                )
                result = await client.get_inbox_items(since=since)

                assert len(result) == 1

                # Verify filter parameter was included
                request = respx.calls.last.request
                assert "$filter" in request.url.params
                assert "2024-01-01T00:00:00Z" in request.url.params["$filter"]

    @respx.mock
    async def test_get_inbox_items_with_pagination(self):
        """Test get_inbox_items handles pagination."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            page_1_response = {
                "value": [{"id": "email1"}],
                "@odata.nextLink": "https://api/page2",
            }
            page_2_response = {"value": [{"id": "email2"}]}

            respx.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
            ).mock(return_value=httpx.Response(200, json=page_1_response))
            respx.get("https://api/page2").mock(
                return_value=httpx.Response(200, json=page_2_response)
            )

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                result = await client.get_inbox_items()

                assert len(result) == 2
                assert result[0]["id"] == "email1"
                assert result[1]["id"] == "email2"

    @respx.mock
    async def test_get_sent_items(self):
        """Test get_sent_items retrieves sent folder."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            sent_response = {
                "value": [
                    {"id": "sent1", "toRecipients": []},
                    {"id": "sent2", "toRecipients": []},
                ]
            }

            respx.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/sentItems/messages"
            ).mock(return_value=httpx.Response(200, json=sent_response))

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                result = await client.get_sent_items()

                assert len(result) == 2
                assert result[0]["id"] == "sent1"

    @respx.mock
    async def test_get_sent_items_with_pagination(self):
        """Test get_sent_items handles pagination."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            page_1 = {
                "value": [{"id": "sent1"}],
                "@odata.nextLink": "https://api/sent/page2",
            }
            page_2 = {"value": [{"id": "sent2"}]}

            respx.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/sentItems/messages"
            ).mock(return_value=httpx.Response(200, json=page_1))
            respx.get("https://api/sent/page2").mock(
                return_value=httpx.Response(200, json=page_2)
            )

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                result = await client.get_sent_items()

                assert len(result) == 2


class TestOutlookClientErrorHandling:
    """Test error handling and edge cases."""

    @respx.mock
    async def test_get_inbox_items_handles_empty_response(self):
        """Test get_inbox_items with empty inbox."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            respx.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
            ).mock(return_value=httpx.Response(200, json={"value": []}))

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                result = await client.get_inbox_items()

                assert result == []

    @respx.mock
    async def test_http_timeout_is_retried(self):
        """Test that HTTP timeouts trigger retry logic."""
        with patch("clients.outlk.msal.PublicClientApplication") as mock_msal:
            mock_app_instance = Mock()
            mock_app_instance.acquire_token_by_refresh_token.return_value = {
                "access_token": "token"
            }
            mock_msal.return_value = mock_app_instance

            # First call times out, second succeeds
            respx.get("https://api.test.com/endpoint").mock(
                side_effect=[
                    httpx.TimeoutException("Request timed out"),
                    httpx.Response(200, json={"data": "success"}),
                ]
            )

            async with OutlookClient(client_id="test", refresh_token="test") as client:
                result = await client._get("https://api.test.com/endpoint")
                assert result == {"data": "success"}
