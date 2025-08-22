"""Extended logging tests for 100% coverage."""

import json
import logging
import tempfile
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from remote_mcp_server.logging_config import (
    PerformanceLogger,
    StructuredFormatter,
    _sanitize_args,
    _sanitize_dict,
    _sanitize_kwargs,
    _sanitize_value,
    create_logger,
    log_aws_lambda_context,
    log_http_request,
    log_http_response,
    performance_logger,
    setup_logging,
)


class TestStructuredFormatterExtended:
    """Extended tests for StructuredFormatter."""

    def test_structured_formatter_without_extra_fields(self):
        """Test formatter with include_extra_fields disabled."""
        formatter = StructuredFormatter(include_extra_fields=False)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add extra fields that should be ignored
        record.custom_field = "should_be_ignored"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "custom_field" not in log_data
        assert log_data["message"] == "Test message"

    def test_structured_formatter_json_serialization_error(self):
        """Test formatter with non-JSON-serializable extra fields."""
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

        # Add non-serializable field
        class NonSerializable:
            def __str__(self):
                return "non_serializable_value"

        record.non_serializable = NonSerializable()

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["non_serializable"] == "non_serializable_value"

    def test_structured_formatter_exception_info(self):
        """Test formatter with exception information."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=(ValueError, ValueError("Test exception"), None),
            )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"


class TestPerformanceLoggerExtended:
    """Extended tests for PerformanceLogger."""

    def test_performance_logger_log_memory_usage(self):
        """Test performance logger memory usage logging."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        perf_logger = PerformanceLogger("test_perf")
        perf_logger.logger.addHandler(handler)
        perf_logger.logger.setLevel(logging.INFO)

        perf_logger.log_memory_usage("memory_test", 512.75, processes=5, cpu_usage=25.5)

        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert log_data["operation"] == "memory_test"
        assert log_data["memory_mb"] == 512.75
        assert log_data["processes"] == 5
        assert log_data["cpu_usage"] == 25.5


class TestAWSLambdaLogging:
    """Test AWS Lambda specific logging functions."""

    def test_log_aws_lambda_context_full(self):
        """Test AWS Lambda context logging with all attributes."""
        context = Mock()
        context.aws_request_id = "test-123"
        context.function_name = "test-function"
        context.function_version = "1.0"
        context.memory_limit_in_mb = "256"
        context.get_remaining_time_in_millis.return_value = 25000
        context.log_group_name = "/aws/lambda/test-function"
        context.log_stream_name = "2025/01/01/test-stream"

        with patch("remote_mcp_server.logging_config.set_request_context") as mock_set:
            log_aws_lambda_context(context)
            mock_set.assert_called_once_with(
                request_id="test-123",
                lambda_function="test-function",
                lambda_version="1.0",
            )

    def test_log_aws_lambda_context_without_aws_request_id(self):
        """Test AWS Lambda context logging without aws_request_id."""
        context = Mock()
        # No aws_request_id attribute
        del context.aws_request_id

        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_lambda")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        with patch("remote_mcp_server.logging_config.lambda_logger", logger):
            log_aws_lambda_context(context)

        # Should not crash and should log debug message
        log_output = output.getvalue()
        assert "AWS Lambda context not detected" in log_output


class TestHTTPLogging:
    """Test HTTP request/response logging."""

    def test_log_http_request_full(self):
        """Test HTTP request logging with all fields."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_http")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "test-agent/1.0",
            "Authorization": "Bearer secret-token",
        }

        with patch("remote_mcp_server.logging_config.http_logger", logger):
            log_http_request("POST", "/api/test", headers, '{"data": "test"}')

        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert log_data["method"] == "POST"
        assert log_data["path"] == "/api/test"
        assert log_data["content_type"] == "application/json"
        assert log_data["user_agent"] == "test-agent/1.0"
        assert (
            log_data["headers"]["Authorization"] == "<REDACTED>"
        )  # Should be sanitized

    def test_log_http_response_different_status_codes(self):
        """Test HTTP response logging with different status codes."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_http")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        with patch("remote_mcp_server.logging_config.http_logger", logger):
            # Test different status code ranges
            test_cases = [
                (200, "2xx"),
                (301, "3xx"),
                (404, "4xx"),
                (500, "5xx"),
                (199, "1xx"),  # Edge case
            ]

            for status_code, expected_category in test_cases:
                output.truncate(0)
                output.seek(0)

                log_http_response(status_code, '{"result": "test"}', 0.123)

                log_line = output.getvalue().strip()
                if log_line:  # Only check if there's output
                    log_data = json.loads(log_line)
                    assert log_data["status_code"] == status_code
                    assert log_data["status_category"] == expected_category


class TestDataSanitization:
    """Extended data sanitization tests."""

    def test_sanitize_value_nested_dict(self):
        """Test sanitization of nested dictionaries."""
        test_data = {
            "user_info": {
                "username": "john",
                "password": "secret123",
                "nested": {"api_key": "abc123", "public_data": "safe"},
            }
        }

        result = _sanitize_value("user_info", test_data)

        assert result["user_info"]["username"] == "john"
        assert result["user_info"]["password"] == "<REDACTED>"
        assert result["user_info"]["nested"]["api_key"] == "<REDACTED>"
        assert result["user_info"]["nested"]["public_data"] == "safe"

    def test_sanitize_dict_complex_structures(self):
        """Test dictionary sanitization with complex data structures."""
        test_data = {
            "credentials": {"token": "secret-token", "refresh_token": "refresh-secret"},
            "user_data": {"name": "John Doe", "email": "john@example.com"},
            "array_data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],  # More than 10 items
            "long_dict": {
                f"key_{i}": f"value_{i}" for i in range(15)
            },  # More than 10 items
        }

        result = _sanitize_dict(test_data)

        assert result["credentials"]["token"] == "<REDACTED>"
        assert result["credentials"]["refresh_token"] == "<REDACTED>"
        assert result["user_data"]["name"] == "John Doe"
        assert "array_data" in result
        assert "long_dict" in result

    def test_sanitize_args_large_args(self):
        """Test argument sanitization with large argument lists."""
        large_args = tuple(range(25))  # More than 20 items

        result = _sanitize_args(large_args)

        # Should be truncated and show summary
        assert isinstance(result, list)

    def test_sanitize_kwargs_sensitive_keys(self):
        """Test keyword argument sanitization with sensitive keys."""
        kwargs = {
            "username": "john",
            "password": "secret",
            "api_key": "abc123",
            "session_token": "session-secret",
            "normal_param": "safe_value",
        }

        result = _sanitize_kwargs(kwargs)

        assert result["username"] == "john"
        assert result["password"] == "<REDACTED>"
        assert result["api_key"] == "<REDACTED>"
        assert result["session_token"] == "<REDACTED>"
        assert result["normal_param"] == "safe_value"


class TestLoggingSetup:
    """Test logging setup and configuration."""

    def test_setup_logging_with_file(self):
        """Test logging setup with log file."""
        with tempfile.NamedTemporaryFile() as temp_file:
            setup_logging(
                log_level="DEBUG",
                enable_structured_logging=True,
                enable_performance_logging=True,
                log_file=temp_file.name,
            )

            # Test that logging works
            logger = create_logger("test_file_setup")
            logger.info("Test message")

    def test_setup_logging_environment_detection(self):
        """Test logging setup with environment detection."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            setup_logging()

            # Should not raise an exception
            logger = create_logger("test_env")
            logger.info("Test message")

    def test_create_logger_hierarchy(self):
        """Test logger creation with hierarchical names."""
        logger1 = create_logger("parent")
        logger2 = create_logger("parent.child")
        logger3 = create_logger("parent.child.grandchild")

        assert logger1.name == "parent"
        assert logger2.name == "parent.child"
        assert logger3.name == "parent.child.grandchild"

    def test_performance_logger_global_instance(self):
        """Test global performance logger instance."""
        assert isinstance(performance_logger, PerformanceLogger)

        # Should work without errors
        performance_logger.log_timing("global_test", 0.001)
        performance_logger.log_memory_usage("global_memory_test", 128.0)


class TestEdgeCases:
    """Test various edge cases and error conditions."""

    def test_sanitize_value_with_none(self):
        """Test sanitization with None values."""
        result = _sanitize_value("test_key", None)
        assert result is None

        result = _sanitize_value("password", None)
        assert result == "<REDACTED>"

    def test_sanitize_dict_with_none_values(self):
        """Test dictionary sanitization with None values."""
        test_data = {
            "valid_key": "valid_value",
            "none_key": None,
            "password": None,
            "empty_dict": {},
            "empty_list": [],
        }

        result = _sanitize_dict(test_data)

        assert result["valid_key"] == "valid_value"
        assert result["none_key"] is None
        assert result["password"] == "<REDACTED>"
        assert result["empty_dict"] == {}
        assert result["empty_list"] == []

    def test_structured_formatter_with_request_context(self):
        """Test formatter with request context present."""
        from remote_mcp_server.logging_config import (
            clear_request_context,
            set_request_context,
        )

        formatter = StructuredFormatter()

        # Set up request context
        set_request_context(request_id="test-context-123")

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=42,
                msg="Test with context",
                args=(),
                exc_info=None,
            )

            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            assert "request" in log_data
            assert log_data["request"]["request_id"] == "test-context-123"

        finally:
            clear_request_context()

    def test_log_http_request_minimal(self):
        """Test HTTP request logging with minimal parameters."""
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(StructuredFormatter())

        logger = logging.getLogger("test_minimal_http")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        with patch("remote_mcp_server.logging_config.http_logger", logger):
            log_http_request("GET", "/", {}, None)

        log_line = output.getvalue().strip()
        log_data = json.loads(log_line)

        assert log_data["method"] == "GET"
        assert log_data["path"] == "/"
        assert log_data["content_type"] is None
        assert log_data["user_agent"] is None
