"""Test the utils module."""

import logging
from typing import Generator
import io
import pytest

from repo_to_text.utils.utils import setup_logging

@pytest.fixture(autouse=True)
def reset_logger() -> Generator[None, None, None]:
    """Reset root logger before each test."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)  # Default level
    yield
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)  # Reset after test

def test_setup_logging_debug() -> None:
    """Test setup_logging with debug mode."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Clear existing handlers
    root_logger.setLevel(logging.WARNING)  # Reset to default

    setup_logging(debug=True)
    assert len(root_logger.handlers) > 0
    assert root_logger.level == logging.DEBUG

def test_setup_logging_info() -> None:
    """Test setup_logging with info mode."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Clear existing handlers
    root_logger.setLevel(logging.WARNING)  # Reset to default

    setup_logging(debug=False)
    assert len(root_logger.handlers) > 0
    assert root_logger.level == logging.INFO

def test_setup_logging_formatter() -> None:
    """Test logging formatter setup."""
    setup_logging(debug=True)
    logger = logging.getLogger()
    handlers = logger.handlers

    # Check if there's at least one handler
    assert len(handlers) > 0

    # Check formatter
    formatter = handlers[0].formatter
    assert formatter is not None

    # Test format string
    test_record = logging.LogRecord(
        name='test',
        level=logging.DEBUG,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None
    )
    formatted = formatter.format(test_record)
    assert 'Test message' in formatted
    assert test_record.levelname in formatted

def test_setup_logging_multiple_calls() -> None:
    """Test that multiple calls to setup_logging don't create duplicate handlers."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    setup_logging(debug=True)
    initial_handler_count = len(root_logger.handlers)

    # Call setup_logging again
    setup_logging(debug=True)
    assert len(root_logger.handlers) == \
        initial_handler_count, "Should not create duplicate handlers"

def test_setup_logging_level_change() -> None:
    """Test changing log levels between setup_logging calls."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Start with debug
    setup_logging(debug=True)
    assert root_logger.level == logging.DEBUG

    # Clear handlers before next setup
    root_logger.handlers.clear()

    # Switch to info
    setup_logging(debug=False)
    assert root_logger.level == logging.INFO

def test_setup_logging_message_format() -> None:
    """Test the actual format of logged messages."""
    setup_logging(debug=True)
    logger = logging.getLogger()

    # Create a temporary handler to capture output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    # Use formatter that includes pathname
    handler.setFormatter(
        logging.Formatter('%(levelname)s %(name)s:%(pathname)s:%(lineno)d %(message)s')
    )
    logger.addHandler(handler)

    # Ensure debug level is set
    logger.setLevel(logging.DEBUG)
    handler.setLevel(logging.DEBUG)

    # Log a test message
    test_message = "Test log message"
    logger.debug(test_message)
    log_output = log_capture.getvalue()

    # Verify format components
    assert test_message in log_output
    assert "DEBUG" in log_output
    assert "test_utils.py" in log_output

def test_setup_logging_error_messages() -> None:
    """Test logging of error messages."""
    setup_logging(debug=False)
    logger = logging.getLogger()

    # Create a temporary handler to capture output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logger.handlers[0].formatter)
    logger.addHandler(handler)

    # Log an error message
    error_message = "Test error message"
    logger.error(error_message)
    log_output = log_capture.getvalue()

    # Error messages should always be logged regardless of debug setting
    assert error_message in log_output
    assert "ERROR" in log_output

if __name__ == "__main__":
    pytest.main([__file__])
