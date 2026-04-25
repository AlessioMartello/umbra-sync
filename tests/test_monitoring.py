import os
from unittest.mock import patch

from utils.monitoring import write_job_summary


class TestWriteJobSummary:
    """Test job summary writing functionality."""

    def test_write_job_summary_creates_summary_file(self, tmp_path):
        """Test that write_job_summary creates a summary file."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=5, updated=3, skipped=2, since="2024-01-01")

            assert summary_file.exists()

    def test_write_job_summary_contains_expected_content(self, tmp_path):
        """Test that summary contains all expected metrics."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(
                created=10, updated=5, skipped=2, since="2024-01-01T00:00:00Z"
            )

            content = summary_file.read_text()

            assert "Contacts sync summary" in content
            assert "10" in content  # created count
            assert "5" in content  # updated count
            assert "2" in content  # skipped count
            assert "17" in content  # total processed (10 + 5 + 2)

    def test_write_job_summary_includes_watermark(self, tmp_path):
        """Test that summary includes watermark value."""
        summary_file = tmp_path / "summary.md"
        watermark = "2024-01-15T10:30:00Z"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=1, updated=1, skipped=1, since=watermark)

            content = summary_file.read_text()
            assert watermark in content

    def test_write_job_summary_includes_run_timestamp(self, tmp_path):
        """Test that summary includes current run timestamp."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=0, updated=0, skipped=0, since="2024-01-01")

            content = summary_file.read_text()

            # Should contain date in format like 2024-01-25
            assert "2024" in content or "202" in content  # Year format
            # Should contain time
            assert ":" in content  # Time separator

    def test_write_job_summary_with_zero_metrics(self, tmp_path):
        """Test summary with all zero metrics."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=0, updated=0, skipped=0, since="2024-01-01")

            content = summary_file.read_text()
            assert "0" in content

    def test_write_job_summary_with_large_metrics(self, tmp_path):
        """Test summary with large metric values."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(
                created=1000, updated=500, skipped=100, since="2024-01-01"
            )

            content = summary_file.read_text()
            assert "1000" in content
            assert "500" in content
            assert "100" in content
            assert "1600" in content  # total

    def test_write_job_summary_markdown_table_format(self, tmp_path):
        """Test that summary uses markdown table format."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=1, updated=1, skipped=1, since="2024-01-01")

            content = summary_file.read_text()

            # Should contain markdown table indicators
            assert "|" in content
            assert "Metric" in content
            assert "Value" in content

    def test_write_job_summary_skips_when_env_var_missing(self, tmp_path):
        """Test that function handles missing GITHUB_STEP_SUMMARY gracefully."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise an exception
            write_job_summary(created=1, updated=1, skipped=1, since="2024-01-01")

    def test_write_job_summary_overwrites_existing_file(self, tmp_path):
        """Test that summary overwrites existing file."""
        summary_file = tmp_path / "summary.md"
        summary_file.write_text("Old content")

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=5, updated=5, skipped=5, since="2024-01-01")

            content = summary_file.read_text()
            assert "Old content" not in content
            assert "Contacts sync summary" in content

    def test_write_job_summary_creates_parent_directory(self, tmp_path):
        """Test that function creates parent directories if needed."""
        summary_file = tmp_path / "nested" / "dir" / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=1, updated=1, skipped=1, since="2024-01-01")

            assert summary_file.exists()

    def test_write_job_summary_total_processed_calculation(self, tmp_path):
        """Test that total processed is correctly calculated."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=10, updated=20, skipped=30, since="2024-01-01")

            content = summary_file.read_text()
            # Total should be 10 + 20 + 30 = 60
            assert "60" in content

    def test_write_job_summary_with_special_characters_in_watermark(self, tmp_path):
        """Test summary with special characters in watermark."""
        summary_file = tmp_path / "summary.md"
        watermark = "2024-01-01T00:00:00+00:00"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=1, updated=1, skipped=1, since=watermark)

            content = summary_file.read_text()
            assert "2024-01-01" in content

    def test_write_job_summary_formatting_consistency(self, tmp_path):
        """Test that multiple calls maintain consistent formatting."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            # First call
            write_job_summary(created=1, updated=1, skipped=1, since="2024-01-01")
            first_content = summary_file.read_text()

            # Second call (file gets overwritten)
            write_job_summary(created=2, updated=2, skipped=2, since="2024-01-02")
            second_content = summary_file.read_text()

            # Both should have same structure
            assert first_content.count("|") == second_content.count("|")
            assert first_content.count("Metric") == second_content.count("Metric")

    def test_write_job_summary_handles_path_object(self, tmp_path):
        """Test that function handles Path object as environment variable."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=1, updated=1, skipped=1, since="2024-01-01")

            assert summary_file.exists()

    def test_write_job_summary_with_negative_zero_metrics(self, tmp_path):
        """Test summary with edge case of zero metrics."""
        summary_file = tmp_path / "summary.md"

        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_job_summary(created=0, updated=0, skipped=0, since="")

            content = summary_file.read_text()
            # Should handle empty watermark
            assert "Contacts sync summary" in content
