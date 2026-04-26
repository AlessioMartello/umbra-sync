import os
import pytest
from unittest.mock import patch

# Import main to access _validate_env
import sys
from pathlib import Path

# Add src to path to import main
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import _validate_env


class TestValidateEnv:
    """Test environment variable validation at startup."""

    def test_validate_env_succeeds_with_all_required_vars(self):
        """Test that validation passes when all required env vars are set."""
        with patch.dict(
            os.environ,
            {
                "AZURE_CLIENT_ID": "test-client-id",
                "REFRESH_TOKEN": "test-token",
                "MONDAY_API_KEY": "test-api-key",
                "MONDAY_BOARD_ID": "12345",
            },
            clear=False,
        ):
            # Should not raise any exception
            _validate_env()

    def test_validate_env_raises_on_missing_azure_client_id(self):
        """Test that EnvironmentError is raised when AZURE_CLIENT_ID is missing."""
        with patch.dict(
            os.environ,
            {
                "REFRESH_TOKEN": "test-token",
                "MONDAY_API_KEY": "test-api-key",
                "MONDAY_BOARD_ID": "12345",
            },
            clear=True,
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                _validate_env()
            assert "AZURE_CLIENT_ID" in str(exc_info.value)
            assert "Missing required environment variables" in str(exc_info.value)

    def test_validate_env_raises_on_missing_refresh_token(self):
        """Test that EnvironmentError is raised when REFRESH_TOKEN is missing."""
        with patch.dict(
            os.environ,
            {
                "AZURE_CLIENT_ID": "test-client-id",
                "MONDAY_API_KEY": "test-api-key",
                "MONDAY_BOARD_ID": "12345",
            },
            clear=True,
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                _validate_env()
            assert "REFRESH_TOKEN" in str(exc_info.value)

    def test_validate_env_raises_on_missing_monday_api_key(self):
        """Test that EnvironmentError is raised when MONDAY_API_KEY is missing."""
        with patch.dict(
            os.environ,
            {
                "AZURE_CLIENT_ID": "test-client-id",
                "REFRESH_TOKEN": "test-token",
                "MONDAY_BOARD_ID": "12345",
            },
            clear=True,
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                _validate_env()
            assert "MONDAY_API_KEY" in str(exc_info.value)

    def test_validate_env_raises_on_missing_monday_board_id(self):
        """Test that EnvironmentError is raised when MONDAY_BOARD_ID is missing."""
        with patch.dict(
            os.environ,
            {
                "AZURE_CLIENT_ID": "test-client-id",
                "REFRESH_TOKEN": "test-token",
                "MONDAY_API_KEY": "test-api-key",
            },
            clear=True,
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                _validate_env()
            assert "MONDAY_BOARD_ID" in str(exc_info.value)

    def test_validate_env_raises_on_multiple_missing_vars(self):
        """Test that EnvironmentError lists all missing variables."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError) as exc_info:
                _validate_env()
            error_msg = str(exc_info.value)
            assert "AZURE_CLIENT_ID" in error_msg
            assert "REFRESH_TOKEN" in error_msg
            assert "MONDAY_API_KEY" in error_msg
            assert "MONDAY_BOARD_ID" in error_msg

    def test_validate_env_error_message_mentions_env_file(self):
        """Test that error message guides user to check .env file."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError) as exc_info:
                _validate_env()
            assert ".env" in str(exc_info.value)
