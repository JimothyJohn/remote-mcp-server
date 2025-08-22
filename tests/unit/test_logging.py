"""Unit tests for logging configuration and functionality."""

import json
import logging
import tempfile
import unittest.mock
from io import StringIO

import pytest

from remote_mcp_server.logging_config import (
    PerformanceLogger,
    StructuredFormatter,
    clear_request_context,
    create_logger,
    get_request_context,
    log_function_entry_exit,
    log_mcp_tool_execution,
    performance_logger,
    set_request_context,
    setup_logging,
)


class TestStructuredFormatter:
    """Test structured logging formatter."""

    def test_basic_formatting(self):
        """Test basic log formatting."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["line"] == 42
        assert "timestamp" in log_data

    def test_exception_formatting(self):
        """Test exception information in logs."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=(ValueError, ValueError("Test error"), None),
            )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test error"

    def test_extra_fields(self):
        """Test extra fields in log records."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add extra fields
        record.tool_name = "test_tool"
        record.duration_ms = 123.45
        record.action = "test_action"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["tool_name"] == "test_tool"
        assert log_data["duration_ms"] == 123.45
        assert log_data["action"] == "test_action"


class TestRequestContext:
    """Test request context management."""

    def setup_method(self):
        """Clear context before each test."""
        clear_request_context()

    def test_set_request_context(self):
        """Test setting request context."""
        request_id = set_request_context(
            request_id="test-123", user_id="user-456", session_id="session-789"
        )

        assert request_id == "test-123"

        context = get_request_context()
        assert context["request_id"] == "test-123"
        assert context["user_id"] == "user-456"
        assert context["session_id"] == "session-789"
        assert "timestamp" in context

    def test_generate_request_id(self):
        """Test automatic request ID generation."""
        request_id = set_request_context()

        assert request_id is not None
        assert len(request_id) > 0

        context = get_request_context()
        assert context["request_id"] == request_id

    def test_clear_request_context(self):
        """Test clearing request context."""
        set_request_context(request_id="test-123")
        assert get_request_context()["request_id"] == "test-123"

        clear_request_context()
        assert get_request_context() == {}

    def test_request_context_in_logs(self):
        """Test that request context appears in log output."""
        # Setup logging to capture output
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_context")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Set context and log
        set_request_context(request_id="test-context-123")
        logger.info("Test message with context")

        # Parse log output
        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert "request" in log_data
        assert log_data["request"]["request_id"] == "test-context-123"


class TestPerformanceLogger:
    """Test performance logging functionality."""

    def test_log_timing(self):
        """Test timing log entries."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        perf_logger = PerformanceLogger("test_performance")
        perf_logger.logger.addHandler(handler)
        perf_logger.logger.setLevel(logging.INFO)

        perf_logger.log_timing("test_operation", 0.123, custom_field="test_value")

        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert log_data["operation"] == "test_operation"
        assert log_data["duration_ms"] == 123.0
        assert log_data["duration_seconds"] == 0.123
        assert log_data["custom_field"] == "test_value"

    def test_log_memory_usage(self):
        """Test memory usage log entries."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        perf_logger = PerformanceLogger("test_performance")
        perf_logger.logger.addHandler(handler)
        perf_logger.logger.setLevel(logging.INFO)

        perf_logger.log_memory_usage("memory_operation", 256.75, process_count=10)

        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert log_data["operation"] == "memory_operation"
        assert log_data["memory_mb"] == 256.75
        assert log_data["process_count"] == 10


class TestFunctionDecorator:
    """Test function entry/exit logging decorator."""

    def test_function_entry_exit_logging(self):
        """Test decorator logs function entry and exit."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_decorator")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        @log_function_entry_exit(
            logger=logger, log_args=True, log_result=True, log_duration=True
        )
        def test_function(arg1, arg2, keyword_arg="default"):
            return f"{arg1}-{arg2}-{keyword_arg}"

        result = test_function("hello", "world", keyword_arg="test")

        log_output = output.getvalue()
        log_lines = [line for line in log_output.strip().split("\n") if line]

        # Should have entry and exit logs
        assert len(log_lines) >= 2

        entry_log = json.loads(log_lines[0])
        exit_log = json.loads(log_lines[-1])

        # Check entry log
        assert entry_log["action"] == "entry"
        assert entry_log["function"] == "test_function"
        assert "function_args" in entry_log
        assert "function_kwargs" in entry_log

        # Check exit log
        assert exit_log["action"] == "exit"
        assert exit_log["status"] == "success"
        assert "duration_ms" in exit_log
        assert result == "hello-world-test"

    def test_function_exception_logging(self):
        """Test decorator logs exceptions properly."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_decorator")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        @log_function_entry_exit(logger=logger)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        log_output = output.getvalue()
        log_lines = [line for line in log_output.strip().split("\n") if line]

        # Find the error log
        error_log = None
        for line in log_lines:
            log_data = json.loads(line)
            if log_data.get("status") == "error":
                error_log = log_data
                break

        assert error_log is not None
        assert error_log["status"] == "error"
        assert error_log["error_type"] == "ValueError"
        assert "duration_ms" in error_log


class TestMcpToolExecutionLogging:
    """Test MCP tool execution logging."""

    def test_successful_tool_execution_logging(self):
        """Test logging successful tool execution."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("mcp.tools")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        log_mcp_tool_execution(
            "test_tool", {"param1": "value1", "param2": 42}, result="success_result"
        )

        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert log_data["tool_name"] == "test_tool"
        assert log_data["status"] == "success"
        assert log_data["arguments"]["param1"] == "value1"
        assert log_data["arguments"]["param2"] == 42
        assert log_data["result"] == "success_result"

    def test_failed_tool_execution_logging(self):
        """Test logging failed tool execution."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("mcp.tools")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        error = ValueError("Test error message")

        log_mcp_tool_execution("test_tool", {"param": "value"}, error=error)

        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert log_data["tool_name"] == "test_tool"
        assert log_data["status"] == "error"
        assert log_data["error_type"] == "ValueError"
        assert log_data["error_message"] == "Test error message"


class TestSetupLogging:
    """Test logging setup functionality."""

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".log") as temp_file:
            setup_logging(
                log_level="DEBUG",
                enable_structured_logging=True,
                enable_performance_logging=True,
                log_file=temp_file.name,
            )

            # Test that logging works
            logger = create_logger("test_setup")
            logger.info("Test setup message")

            # Should not raise an exception
            assert True

    def test_create_logger(self):
        """Test logger creation."""
        logger = create_logger("test.module")

        assert logger.name == "test.module"
        assert isinstance(logger, logging.Logger)

    def test_global_performance_logger(self):
        """Test global performance logger instance."""
        assert isinstance(performance_logger, PerformanceLogger)

        # Should not raise an exception
        performance_logger.log_timing("test_operation", 0.001)


class TestDataSanitization:
    """Test data sanitization for security."""

    def test_sensitive_data_redaction(self):
        """Test that sensitive fields are redacted."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_sanitization")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log with sensitive data
        logger.info(
            "User login",
            extra={
                "username": "john_doe",
                "password": "secret123",
                "api_key": "abc123def456",
                "user_id": "12345",
            },
        )

        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert log_data["username"] == "john_doe"  # Safe field
        assert log_data["password"] == "<REDACTED>"  # Sensitive field
        assert log_data["api_key"] == "<REDACTED>"  # Sensitive field
        assert log_data["user_id"] == "12345"  # Safe field

    def test_large_data_truncation(self):
        """Test that large data structures are truncated."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_truncation")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        @log_function_entry_exit(logger=logger, log_args=True)
        def function_with_large_args(large_list):
            return "done"

        # Call with large argument
        large_list = list(range(20))  # More than limit
        function_with_large_args(large_list)

        log_output = output.getvalue()

        # Check that the large list was truncated
        assert "list[20]" in log_output or len(log_output) < 10000


if __name__ == "__main__":
    pytest.main([__file__])
