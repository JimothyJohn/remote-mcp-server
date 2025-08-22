"""Targeted tests to achieve 100% code coverage."""

import json
import logging
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from remote_mcp_server.logging_config import (
    StructuredFormatter,
    _sanitize_dict,
    log_aws_lambda_context,
    log_http_request,
    log_http_response,
)
from remote_mcp_server.mcp_server import (
    calculate_sum,
    create_lambda_handler,
    echo_message,
    get_current_time,
    get_server_info,
    handle_mcp_request,
    hello_world,
    main,
)
from tests.conftest import MockLambdaContext


class TestSpecificMissingLines:
    """Tests targeting specific missing lines in coverage."""

    def test_hello_world_non_string_warning_log(self):
        """Target lines 77-78 in hello_world: non-string conversion warning."""
        # This should trigger the warning log on lines 78-81
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            result = hello_world(12345)
            assert "12345" in result

            # Verify the warning was logged
            mock_logger.warning.assert_called()

    def test_hello_world_long_name_warning_log(self):
        """Target lines 85-86 in hello_world: name truncation warning."""
        long_name = "x" * 150
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            result = hello_world(long_name)

            # Should have logged truncation warning
            mock_logger.warning.assert_called()

    def test_hello_world_exception_paths(self):
        """Target lines 106-118 in hello_world: exception handling."""
        # Simulate an exception in the logging function
        with patch(
            "remote_mcp_server.mcp_server.log_mcp_tool_execution",
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(Exception):
                hello_world("test")

    def test_get_current_time_exception_paths(self):
        """Target lines 155-166 in get_current_time: exception handling."""
        # Force an exception during timestamp generation
        with patch("datetime.datetime.now", side_effect=Exception("Time error")):
            with pytest.raises(Exception):
                get_current_time()

    def test_echo_message_non_string_conversion(self):
        """Target lines 194-195 in echo_message: non-string message conversion."""
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            result = echo_message(12345, 1)
            assert "12345" in result
            mock_logger.warning.assert_called()

    def test_echo_message_invalid_repeat_conversion(self):
        """Target lines 201-209 in echo_message: invalid repeat handling."""
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            # Test non-integer that can be converted
            result = echo_message("test", "2")
            assert "test test" in result
            mock_logger.warning.assert_called()

    def test_echo_message_long_message_truncation(self):
        """Target lines 230-231 in echo_message: message truncation."""
        long_message = "x" * 1200
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            result = echo_message(long_message)
            assert len(result) == 1000  # Should be truncated
            mock_logger.warning.assert_called()

    def test_get_server_info_psutil_import_error(self):
        """Target lines 297-298 in get_server_info: psutil ImportError."""
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            with patch(
                "remote_mcp_server.mcp_server.psutil",
                side_effect=ImportError("No psutil"),
            ):
                result = get_server_info()
                assert result["service"] == "remote-mcp-server"
                # Should have logged debug message about psutil not available
                mock_logger.debug.assert_called()

    def test_get_server_info_psutil_exception(self):
        """Target lines 305-306 in get_server_info: psutil exception."""
        mock_psutil = Mock()
        mock_psutil.virtual_memory.side_effect = Exception("Memory error")

        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            with patch("remote_mcp_server.mcp_server.psutil", mock_psutil):
                result = get_server_info()
                # Should have logged warning about system info failure
                mock_logger.warning.assert_called()

    def test_get_server_info_general_exception(self):
        """Target lines 339-350 in get_server_info: general exception handling."""
        with patch("datetime.datetime.now", side_effect=Exception("Time error")):
            with pytest.raises(Exception):
                get_server_info()

    def test_calculate_sum_invalid_type_error(self):
        """Target lines 377-388 in calculate_sum: TypeError for invalid types."""
        with pytest.raises(Exception):  # Could be TypeError or AttributeError
            calculate_sum("not a list")  # This triggers len() error

    def test_calculate_sum_invalid_number_error(self):
        """Target lines 420-441 in calculate_sum: invalid number handling."""
        with pytest.raises(ValueError, match="Invalid number at index"):
            calculate_sum([1, 2, "invalid_number", 4])

    def test_calculate_sum_large_data_truncation(self):
        """Target line 444 in calculate_sum: conversion warning truncation."""
        # Create a scenario that generates many conversion warnings
        mixed_data = [str(i) for i in range(15)]  # More than 5 conversions
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            result = calculate_sum(mixed_data)
            # Should log conversion warnings with truncation
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_mcp_request_invalid_jsonrpc_warning(self):
        """Target line 550 in handle_mcp_request: invalid JSON-RPC warning."""
        request = {"jsonrpc": "1.0", "method": "tools/call", "id": 1}  # Invalid version
        with patch("remote_mcp_server.mcp_server.mcp_logger") as mock_logger:
            response = await handle_mcp_request(request)
            # Should have logged warning about invalid JSON-RPC version
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_mcp_request_exception_handling(self):
        """Target lines 581-597 in handle_mcp_request: exception handling."""
        with patch("time.time", side_effect=Exception("Time error")):
            request = {"jsonrpc": "2.0", "method": "tools/call", "id": 1}
            response = await handle_mcp_request(request)
            assert "error" in response
            assert response["error"]["code"] == -32603

    def test_lambda_handler_no_aws_request_id(self):
        """Target line 634 in lambda_handler: no aws_request_id."""
        handler = create_lambda_handler()

        # Mock context without aws_request_id attribute
        context = Mock()
        context.function_name = "test"
        # Remove aws_request_id if it exists
        if hasattr(context, "aws_request_id"):
            delattr(context, "aws_request_id")

        event = {"httpMethod": "GET", "path": "/", "headers": {}}

        with patch("remote_mcp_server.mcp_server.set_request_context") as mock_set:
            response = handler(event, context)
            assert response["statusCode"] == 200
            mock_set.assert_called()

    def test_lambda_event_processing_edge_cases(self):
        """Target lines 806-808 and other edge cases."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        # Test unusual path combinations not covered
        event = {
            "httpMethod": "PATCH",
            "path": "/custom-path",
            "headers": {},
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

    def test_main_function_with_args(self):
        """Target lines 861-888 in main function."""
        # Test main with various argument combinations
        test_cases = [
            ["--port", "8080"],
            ["--log-level", "DEBUG"],
            ["--port", "9000", "--log-level", "ERROR"],
            ["--help"],  # This should trigger SystemExit
        ]

        for args in test_cases[:-1]:  # Skip help case for now
            with patch("sys.argv", ["mcp_server.py"] + args):
                with patch("remote_mcp_server.mcp_server.mcp.run") as mock_run:
                    with patch("logging.getLogger") as mock_logger:
                        main()
                        mock_run.assert_called_once()

    def test_main_function_help(self):
        """Test main function help argument."""
        with patch("sys.argv", ["mcp_server.py", "--help"]):
            with pytest.raises(SystemExit):
                main()


class TestLoggingSpecificLines:
    """Target specific missing lines in logging_config.py."""

    def test_structured_formatter_json_error_fallback(self):
        """Target lines 73-74: JSON serialization error fallback."""
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

        # Add a field that can't be JSON serialized
        class Unserializable:
            def __init__(self):
                self.circular = self

        record.problematic_field = Unserializable()

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Should have converted to string as fallback
        assert isinstance(log_data.get("problematic_field"), str)

    def test_request_context_missing_timestamp(self):
        """Target line 134: missing timestamp in context."""
        from remote_mcp_server.logging_config import (
            _request_context,
            clear_request_context,
            set_request_context,
        )

        clear_request_context()
        # Manually set context without timestamp to trigger edge case
        _request_context.update({"request_id": "test-123"})

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "request" in log_data
        clear_request_context()

    def test_lambda_context_missing_optional_fields(self):
        """Target lines 305-306, 312-313: missing optional Lambda context fields."""
        context = Mock()
        context.aws_request_id = "test-123"
        context.function_name = "test-function"
        context.function_version = "1.0"
        context.memory_limit_in_mb = "128"
        context.get_remaining_time_in_millis.return_value = 30000
        # Deliberately omit log_group_name and log_stream_name

        with patch("remote_mcp_server.logging_config.lambda_logger") as mock_logger:
            log_aws_lambda_context(context)
            mock_logger.info.assert_called()

    def test_http_request_body_parsing_error(self):
        """Target lines 448-449: HTTP request body JSON parsing error."""
        with patch("remote_mcp_server.logging_config.http_logger") as mock_logger:
            with patch(
                "json.loads", side_effect=json.JSONDecodeError("Invalid JSON", "", 0)
            ):
                log_http_request("POST", "/test", {}, '{"invalid": json}')
                mock_logger.info.assert_called()

    def test_sanitize_dict_type_conversion_error(self):
        """Target lines 557-559: dictionary sanitization with type conversion error."""
        test_data = {
            "normal_field": "value",
            "complex_object": {"nested": {"deep": "value"}},
            "long_string": "x" * 250,  # Triggers truncation
        }

        result = _sanitize_dict(test_data)
        assert "normal_field" in result

    def test_http_response_logging_edge_cases(self):
        """Test HTTP response logging edge cases."""
        # Test with different response body types
        test_cases = [(200, None, 0.1), (404, "", 0.2), (500, {}, 0.3), (301, [], 0.4)]

        with patch("remote_mcp_server.logging_config.http_logger") as mock_logger:
            for status, body, duration in test_cases:
                log_http_response(status, body, duration)
                mock_logger.info.assert_called()


class TestErrorConditionCoverage:
    """Test specific error conditions and edge cases."""

    def test_lambda_handler_context_without_attrs(self):
        """Test Lambda handler with minimal context."""
        handler = create_lambda_handler()

        # Create minimal context
        context = Mock(spec=[])  # Empty spec means no attributes

        event = {"httpMethod": "GET", "path": "/", "headers": {}}

        response = handler(event, context)
        assert response["statusCode"] == 200
