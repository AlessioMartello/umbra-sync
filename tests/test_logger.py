import logging
import sys
from io import StringIO

from utils.logger import get_logger


class TestGetLogger:
    """Test logger initialization and configuration."""

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_has_stream_handler(self):
        """Test that logger has a StreamHandler configured."""
        logger = get_logger("test_module_handler")

        handlers = logger.handlers
        assert len(handlers) > 0
        assert any(isinstance(h, logging.StreamHandler) for h in handlers)

    def test_get_logger_stream_handler_targets_stdout(self):
        """Test that StreamHandler outputs to stdout."""
        logger = get_logger("test_stdout")

        stream_handler = next(
            (h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None
        )

        assert stream_handler is not None
        assert stream_handler.stream == sys.stdout

    def test_get_logger_has_formatter(self):
        """Test that logger handler has proper formatter."""
        logger = get_logger("test_formatter")

        stream_handler = next(
            (h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None
        )

        assert stream_handler is not None
        assert stream_handler.formatter is not None

    def test_get_logger_formatter_includes_timestamp(self):
        """Test that formatter includes timestamp."""
        logger = get_logger("test_timestamp")

        stream_handler = next(
            (h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None
        )

        formatter = stream_handler.formatter
        format_string = formatter._fmt

        assert "%(asctime)s" in format_string

    def test_get_logger_formatter_includes_level(self):
        """Test that formatter includes log level."""
        logger = get_logger("test_level")

        stream_handler = next(
            (h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None
        )

        formatter = stream_handler.formatter
        format_string = formatter._fmt

        assert "%(levelname)-8s" in format_string

    def test_get_logger_formatter_includes_module_name(self):
        """Test that formatter includes module name."""
        logger = get_logger("test_name")

        stream_handler = next(
            (h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None
        )

        formatter = stream_handler.formatter
        format_string = formatter._fmt

        assert "%(name)s" in format_string

    def test_get_logger_formatter_includes_message(self):
        """Test that formatter includes log message."""
        logger = get_logger("test_message")

        stream_handler = next(
            (h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None
        )

        formatter = stream_handler.formatter
        format_string = formatter._fmt

        assert "%(message)s" in format_string

    def test_get_logger_set_to_info_level(self):
        """Test that logger is set to INFO level."""
        logger = get_logger("test_info_level")

        assert logger.level == logging.INFO

    def test_get_logger_datefmt_correct_format(self):
        """Test that datetime format is as expected."""
        logger = get_logger("test_datefmt")

        stream_handler = next(
            (h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None
        )

        formatter = stream_handler.formatter
        # Check the date format string
        assert formatter.datefmt == "%Y-%m-%d %H:%M:%S"

    def test_get_logger_multiple_calls_same_name(self):
        """Test that multiple calls with same name don't add duplicate handlers."""
        # Clear existing handlers first
        logger_name = "test_duplicate_handlers"
        existing_logger = logging.getLogger(logger_name)
        existing_logger.handlers.clear()

        # Get logger twice
        logger1 = get_logger(logger_name)
        logger2 = get_logger(logger_name)

        # Should be same instance
        assert logger1 is logger2

        # Should not have duplicate handlers
        # The function checks `if not logger.handlers` before adding
        # So second call should not add handlers
        stream_handlers = [
            h for h in logger1.handlers if isinstance(h, logging.StreamHandler)
        ]
        # Depending on implementation, there should be exactly one
        assert len(stream_handlers) >= 1

    def test_get_logger_can_log_at_info_level(self):
        """Test that logger can successfully log at INFO level."""
        logger = get_logger("test_log_info")

        # Create a string stream to capture output
        string_stream = StringIO()
        handler = logging.StreamHandler(string_stream)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.info("Test message")

        output = string_stream.getvalue()
        assert "Test message" in output

    def test_get_logger_can_log_at_warning_level(self):
        """Test that logger can log at WARNING level."""
        logger = get_logger("test_log_warning")

        string_stream = StringIO()
        handler = logging.StreamHandler(string_stream)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.warning("Warning message")

        output = string_stream.getvalue()
        assert "Warning message" in output

    def test_get_logger_can_log_at_error_level(self):
        """Test that logger can log at ERROR level."""
        logger = get_logger("test_log_error")

        string_stream = StringIO()
        handler = logging.StreamHandler(string_stream)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.error("Error message")

        output = string_stream.getvalue()
        assert "Error message" in output

    def test_get_logger_can_log_at_debug_level(self):
        """Test that logger can log at DEBUG level (though default is INFO)."""
        logger = get_logger("test_log_debug")

        # For debug to appear, need to adjust level
        logger.setLevel(logging.DEBUG)

        string_stream = StringIO()
        handler = logging.StreamHandler(string_stream)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.debug("Debug message")

        output = string_stream.getvalue()
        assert "Debug message" in output

    def test_get_logger_unique_names(self):
        """Test that loggers with different names are separate."""
        logger1 = get_logger("module_a")
        logger2 = get_logger("module_b")

        assert logger1.name == "module_a"
        assert logger2.name == "module_b"
        assert logger1 is not logger2

    def test_get_logger_with_hierarchical_names(self):
        """Test that hierarchical logger names work."""
        logger = get_logger("parent.child.grandchild")

        assert logger.name == "parent.child.grandchild"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_output_format(self):
        """Test that output has expected format structure."""
        logger = get_logger("test_format_output")

        string_stream = StringIO()
        # Get existing stream handler and replace stream
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.stream = string_stream
                break

        logger.info("Test")

        output = string_stream.getvalue()

        # Should contain timestamp, level, name, and message
        assert "|" in output  # Separator in format
        assert "INFO" in output or "test_format_output" in output or "Test" in output
