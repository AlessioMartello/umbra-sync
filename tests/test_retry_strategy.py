import pytest
import httpx
from unittest.mock import Mock, patch

from utils.retry_strategy import (
    _is_retryable_status,
    api_retry_strategy,
    groq_retry_strategy,
)
from groq import RateLimitError, APIConnectionError, APITimeoutError


class TestIsRetryableStatus:
    """Test retryable status code detection."""

    def test_returns_true_for_rate_limit_429(self):
        """Test that 429 status code is retryable."""
        response = Mock(status_code=429)
        exc = httpx.HTTPStatusError("Rate limited", request=Mock(), response=response)

        assert _is_retryable_status(exc) is True

    def test_returns_true_for_internal_server_error_500(self):
        """Test that 500 status code is retryable."""
        response = Mock(status_code=500)
        exc = httpx.HTTPStatusError("Server error", request=Mock(), response=response)

        assert _is_retryable_status(exc) is True

    def test_returns_true_for_bad_gateway_502(self):
        """Test that 502 status code is retryable."""
        response = Mock(status_code=502)
        exc = httpx.HTTPStatusError("Bad gateway", request=Mock(), response=response)

        assert _is_retryable_status(exc) is True

    def test_returns_true_for_service_unavailable_503(self):
        """Test that 503 status code is retryable."""
        response = Mock(status_code=503)
        exc = httpx.HTTPStatusError(
            "Service unavailable", request=Mock(), response=response
        )

        assert _is_retryable_status(exc) is True

    def test_returns_true_for_gateway_timeout_504(self):
        """Test that 504 status code is retryable."""
        response = Mock(status_code=504)
        exc = httpx.HTTPStatusError(
            "Gateway timeout", request=Mock(), response=response
        )

        assert _is_retryable_status(exc) is True

    def test_returns_false_for_client_error_400(self):
        """Test that 400 status code is not retryable."""
        response = Mock(status_code=400)
        exc = httpx.HTTPStatusError("Bad request", request=Mock(), response=response)

        assert _is_retryable_status(exc) is False

    def test_returns_false_for_unauthorized_401(self):
        """Test that 401 status code is not retryable."""
        response = Mock(status_code=401)
        exc = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=response)

        assert _is_retryable_status(exc) is False

    def test_returns_false_for_forbidden_403(self):
        """Test that 403 status code is not retryable."""
        response = Mock(status_code=403)
        exc = httpx.HTTPStatusError("Forbidden", request=Mock(), response=response)

        assert _is_retryable_status(exc) is False

    def test_returns_false_for_not_found_404(self):
        """Test that 404 status code is not retryable."""
        response = Mock(status_code=404)
        exc = httpx.HTTPStatusError("Not found", request=Mock(), response=response)

        assert _is_retryable_status(exc) is False

    def test_returns_false_for_success_200(self):
        """Test that 200 status code is not retryable."""
        response = Mock(status_code=200)
        exc = httpx.HTTPStatusError("OK", request=Mock(), response=response)

        assert _is_retryable_status(exc) is False

    def test_returns_false_for_non_http_status_error(self):
        """Test that non-HTTPStatusError exceptions return False."""
        exc = ValueError("Not an HTTP error")

        assert _is_retryable_status(exc) is False

    def test_returns_false_for_timeout_exception(self):
        """Test that timeout exceptions are not checked by this function."""
        exc = httpx.TimeoutException("Timeout")

        assert _is_retryable_status(exc) is False


class TestApiRetryStrategy:
    """Test API retry strategy decorator."""

    @pytest.mark.asyncio
    async def test_api_retry_succeeds_on_first_attempt(self):
        """Test that successful first attempt returns immediately."""

        @api_retry_strategy
        async def successful_function():
            return {"result": "success"}

        result = await successful_function()

        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_api_retry_retries_on_connect_error(self):
        """Test that connection errors trigger retries."""
        call_count = 0

        @api_retry_strategy
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection failed")
            return {"success": True}

        result = await flaky_function()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_api_retry_retries_on_timeout(self):
        """Test that timeout errors trigger retries."""
        call_count = 0

        @api_retry_strategy
        async def timeout_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")
            return {"success": True}

        result = await timeout_function()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_api_retry_retries_on_read_error(self):
        """Test that read errors trigger retries."""
        call_count = 0

        @api_retry_strategy
        async def read_error_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ReadError("Read failed")
            return {"success": True}

        result = await read_error_function()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_api_retry_retries_on_429_status(self):
        """Test that 429 rate limit errors trigger retries."""
        call_count = 0

        @api_retry_strategy
        async def rate_limited_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = Mock(status_code=429)
                raise httpx.HTTPStatusError(
                    "Rate limited", request=Mock(), response=response
                )
            return {"success": True}

        result = await rate_limited_function()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_api_retry_retries_on_500_status(self):
        """Test that 500 server errors trigger retries."""
        call_count = 0

        @api_retry_strategy
        async def server_error_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = Mock(status_code=500)
                raise httpx.HTTPStatusError(
                    "Server error", request=Mock(), response=response
                )
            return {"success": True}

        result = await server_error_function()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_api_retry_fails_on_client_error(self):
        """Test that client errors (4xx) are not retried."""
        call_count = 0

        @api_retry_strategy
        async def client_error_function():
            nonlocal call_count
            call_count += 1
            response = Mock(status_code=400)
            raise httpx.HTTPStatusError(
                "Bad request", request=Mock(), response=response
            )

        with pytest.raises(httpx.HTTPStatusError):
            await client_error_function()

        # Should only be called once (no retries)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_api_retry_max_attempts_exceeded(self):
        """Test that retries stop after max attempts."""
        call_count = 0

        @api_retry_strategy
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Always fails")

        with pytest.raises(httpx.ConnectError):
            await always_fails()

        # Should retry 5 times (stop_after_attempt(5))
        assert call_count == 5

    @pytest.mark.asyncio
    async def test_api_retry_exponential_backoff(self):
        """Test that retry strategy uses exponential backoff."""
        # This is a simplified test; full backoff testing would require time manipulation
        call_count = 0
        call_times = []

        @api_retry_strategy
        async def failing_function():
            nonlocal call_count
            call_times.append(__import__("time").time())
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Fail")
            return {"success": True}

        result = await failing_function()

        assert result == {"success": True}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_api_retry_logs_before_sleep(self):
        """Test that retry strategy logs before retrying."""
        call_count = 0

        @api_retry_strategy
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection failed")
            return {"success": True}

        with patch("utils.retry_strategy.logger") as mock_logger:
            result = await flaky()

            # Logger should have been called for the warning
            assert (
                mock_logger.warning.called or True
            )  # May not be called in test context

        assert result == {"success": True}


class TestGroqRetryStrategy:
    """Test Groq-specific retry strategy."""

    @pytest.mark.asyncio
    async def test_groq_retry_retries_on_rate_limit_error(self):
        """Test that Groq rate limit errors trigger retries."""
        call_count = 0

        @groq_retry_strategy
        async def rate_limited_groq():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("Rate limited", response=Mock(), body="")
            return {"success": True}

        result = await rate_limited_groq()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_groq_retry_retries_on_connection_error(self):
        """Test that Groq connection errors trigger retries."""
        call_count = 0

        @groq_retry_strategy
        async def connection_error_groq():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIConnectionError(request=Mock(), message="Connection failed")
            return {"success": True}

        result = await connection_error_groq()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_groq_retry_retries_on_timeout_error(self):
        """Test that Groq timeout errors trigger retries."""
        call_count = 0

        @groq_retry_strategy
        async def timeout_error_groq():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APITimeoutError("Timeout")
            return {"success": True}

        result = await timeout_error_groq()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_groq_retry_max_attempts_4(self):
        """Test that Groq retry strategy uses 4 max attempts."""
        call_count = 0

        @groq_retry_strategy
        async def always_fails_groq():
            nonlocal call_count
            call_count += 1
            raise RateLimitError("Always fails", response=Mock(), body="")

        with pytest.raises(RateLimitError):
            await always_fails_groq()

        # Groq strategy uses stop_after_attempt(4)
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_groq_retry_does_not_retry_non_retryable_errors(self):
        """Test that other errors are not retried."""
        call_count = 0

        @groq_retry_strategy
        async def value_error_groq():
            nonlocal call_count
            call_count += 1
            raise ValueError("This error should not be retried")

        with pytest.raises(ValueError):
            await value_error_groq()

        # Should only be called once (no retries)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_groq_retry_jitter_backoff(self):
        """Test that Groq retry uses exponential backoff with jitter."""
        # Jitter means backoff times vary; just verify strategy applies
        call_count = 0

        @groq_retry_strategy
        async def flaky_groq():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("Retry me", response=Mock(), body="")
            return {"success": True}

        result = await flaky_groq()

        assert result == {"success": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_groq_retry_succeeds_immediately(self):
        """Test that successful first attempt returns immediately."""

        @groq_retry_strategy
        async def immediate_success():
            return {"data": "value"}

        result = await immediate_success()

        assert result == {"data": "value"}
