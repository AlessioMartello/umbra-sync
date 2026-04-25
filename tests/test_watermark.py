import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from utils.watermark import get_watermark, update_watermark, DEBUG_LOOKBACK_DAYS


class TestGetWatermark:
    """Test watermark reading functionality."""

    def test_get_watermark_reads_valid_json(self, tmp_path):
        """Test reading valid watermark file."""
        # Create temp watermark file
        watermark_file = tmp_path / "last_run.json"
        test_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        watermark_file.write_text(json.dumps({"last_run": test_time.isoformat()}))

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            result = get_watermark(debug=False)

            assert result == test_time

    def test_get_watermark_returns_default_when_file_missing(self):
        """Test that missing watermark file returns 365 days ago."""
        with patch("utils.watermark.WATERMARK_PATH") as mock_path:
            mock_path.exists.return_value = False

            result = get_watermark(debug=False)

            # Should be approximately 365 days ago
            expected_time = datetime.now(timezone.utc) - timedelta(days=365)
            time_diff = abs((result - expected_time).total_seconds())
            assert time_diff < 60  # Within 60 seconds

    def test_get_watermark_handles_corrupted_json(self, tmp_path, caplog):
        """Test handling of corrupted JSON in watermark file."""
        watermark_file = tmp_path / "last_run.json"
        watermark_file.write_text("{ invalid json }")

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            result = get_watermark(debug=False)

            # Should return default time and log warning
            expected_time = datetime.now(timezone.utc) - timedelta(days=365)
            time_diff = abs((result - expected_time).total_seconds())
            assert time_diff < 60
            assert "Watermark file corrupt or invalid" in caplog.text

    def test_get_watermark_handles_missing_last_run_key(self, tmp_path, caplog):
        """Test handling when 'last_run' key is missing."""
        watermark_file = tmp_path / "last_run.json"
        watermark_file.write_text(json.dumps({"some_other_key": "value"}))

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            result = get_watermark(debug=False)

            # Should return default and log warning
            expected_time = datetime.now(timezone.utc) - timedelta(days=365)
            time_diff = abs((result - expected_time).total_seconds())
            assert time_diff < 60
            assert "Watermark file corrupt or invalid" in caplog.text

    def test_get_watermark_handles_invalid_datetime_format(self, tmp_path, caplog):
        """Test handling of invalid datetime format."""
        watermark_file = tmp_path / "last_run.json"
        watermark_file.write_text(json.dumps({"last_run": "not_a_datetime"}))

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            result = get_watermark(debug=False)

            # Should return default and log warning
            expected_time = datetime.now(timezone.utc) - timedelta(days=365)
            time_diff = abs((result - expected_time).total_seconds())
            assert time_diff < 60

    def test_get_watermark_debug_mode_returns_lookback_days(self):
        """Test that debug mode returns correct lookback period."""
        result = get_watermark(debug=True)

        expected_time = datetime.now(timezone.utc) - timedelta(days=DEBUG_LOOKBACK_DAYS)
        time_diff = abs((result - expected_time).total_seconds())
        # Allow 5 second tolerance for execution time
        assert time_diff < 5

    def test_get_watermark_debug_mode_ignores_file(self, tmp_path):
        """Test that debug mode ignores existing watermark file."""
        watermark_file = tmp_path / "last_run.json"
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        watermark_file.write_text(json.dumps({"last_run": old_time.isoformat()}))

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            result = get_watermark(debug=True)

            # Should not return the old time from file
            assert result != old_time
            # Should be recent time
            expected_time = datetime.now(timezone.utc) - timedelta(
                days=DEBUG_LOOKBACK_DAYS
            )
            time_diff = abs((result - expected_time).total_seconds())
            assert time_diff < 5

    def test_get_watermark_logs_info_on_success(self, tmp_path, caplog):
        """Test that successful read logs info message."""
        watermark_file = tmp_path / "last_run.json"
        test_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        watermark_file.write_text(json.dumps({"last_run": test_time.isoformat()}))

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            with caplog.at_level("INFO"):
                get_watermark(debug=False)

            assert "Latest watermark is:" in caplog.text

    def test_get_watermark_logs_debug_info(self, caplog):
        """Test that debug mode logs appropriately."""
        with caplog.at_level("INFO"):
            get_watermark(debug=True)

            assert "Debug mode" in caplog.text


class TestUpdateWatermark:
    """Test watermark writing functionality."""

    def test_update_watermark_creates_file(self, tmp_path):
        """Test that update_watermark creates the watermark file."""
        watermark_file = tmp_path / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            update_watermark(debug=False)

            assert watermark_file.exists()

    def test_update_watermark_writes_valid_json(self, tmp_path):
        """Test that update_watermark writes valid JSON."""
        watermark_file = tmp_path / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            update_watermark(debug=False)

            content = json.loads(watermark_file.read_text())
            assert "last_run" in content
            # Verify it's valid ISO format datetime
            datetime.fromisoformat(content["last_run"])

    def test_update_watermark_creates_parent_directory(self, tmp_path):
        """Test that update_watermark creates parent directories."""
        nested_dir = tmp_path / "nested" / "dirs" / "path"
        watermark_file = nested_dir / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            update_watermark(debug=False)

            assert watermark_file.exists()
            assert watermark_file.parent.exists()

    def test_update_watermark_overwrites_existing(self, tmp_path):
        """Test that update_watermark overwrites existing file."""
        watermark_file = tmp_path / "last_run.json"
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        watermark_file.write_text(json.dumps({"last_run": old_time.isoformat()}))

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            update_watermark(debug=False)

            content = json.loads(watermark_file.read_text())
            new_time = datetime.fromisoformat(content["last_run"])

            # New time should be very recent (within last minute)
            time_diff = (datetime.now(timezone.utc) - new_time).total_seconds()
            assert time_diff < 60

    def test_update_watermark_uses_utc_timezone(self, tmp_path):
        """Test that watermark uses UTC timezone."""
        watermark_file = tmp_path / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            update_watermark(debug=False)

            content = json.loads(watermark_file.read_text())
            timestamp_str = content["last_run"]

            # UTC timestamps contain +00:00 (ISO format with UTC offset)
            assert "+00:00" in timestamp_str or timestamp_str.endswith("Z")

    def test_update_watermark_debug_mode_ignores_write(self, tmp_path):
        """Test that debug mode doesn't write watermark."""
        watermark_file = tmp_path / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            update_watermark(debug=True)

            assert not watermark_file.exists()

    def test_update_watermark_logs_success(self, tmp_path, caplog):
        """Test that successful update logs info."""
        watermark_file = tmp_path / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            with caplog.at_level("INFO"):
                update_watermark(debug=False)

            assert "Successfully updated watermark" in caplog.text

    def test_update_watermark_logs_debug_info(self, caplog):
        """Test that debug mode logs appropriately."""
        with caplog.at_level("INFO"):
            update_watermark(debug=True)

            assert "Debug mode" in caplog.text

    def test_update_watermark_handles_os_error(self, tmp_path):
        """Test that OS errors during write are handled."""
        # Create read-only directory
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)

        watermark_file = read_only_dir / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            # Should raise OSError when trying to write to read-only dir
            with pytest.raises(OSError):
                update_watermark(debug=False)

        # Cleanup
        read_only_dir.chmod(0o755)

    def test_update_watermark_timestamp_precision(self, tmp_path):
        """Test that timestamp includes microsecond precision."""
        watermark_file = tmp_path / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            update_watermark(debug=False)

            content = json.loads(watermark_file.read_text())
            timestamp_str = content["last_run"]

            # ISO format with microseconds includes T and multiple digits
            assert "T" in timestamp_str
            assert "." in timestamp_str  # microseconds


class TestWatermarkRoundTrip:
    """Test full round-trip of writing and reading watermark."""

    def test_write_then_read_watermark(self, tmp_path):
        """Test that written watermark can be read back."""
        watermark_file = tmp_path / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            # Write watermark
            update_watermark(debug=False)

            # Read it back
            result = get_watermark(debug=False)

            # Should be very recent (within 1 second)
            time_diff = (datetime.now(timezone.utc) - result).total_seconds()
            assert time_diff < 1

    def test_multiple_write_cycles(self, tmp_path):
        """Test multiple write/read cycles maintain correctness."""
        watermark_file = tmp_path / "last_run.json"

        with patch("utils.watermark.WATERMARK_PATH", watermark_file):
            for i in range(5):
                update_watermark(debug=False)
                result = get_watermark(debug=False)

                # Each should be recent
                time_diff = (datetime.now(timezone.utc) - result).total_seconds()
                assert time_diff < 2  # Allow small time for iterations
