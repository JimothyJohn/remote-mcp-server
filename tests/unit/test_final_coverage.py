"""Final targeted tests to reach 100% coverage."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from remote_mcp_server.mcp_server import (
    calculate_sum,
    create_lambda_handler,
    echo_message,
    get_current_time,
    get_server_info,
    handle_mcp_request,
    hello_world,
)
from tests.conftest import MockLambdaContext


class TestFinalCoverageTargets:
    """Direct tests for remaining uncovered lines."""

    def test_hello_world_type_conversion_and_truncation(self):
        """Cover lines 77-78 and 85-86 in hello_world."""
        # Test non-string conversion (lines 77-78)
        result1 = hello_world(123)
        assert "123" in result1

        # Test name truncation (lines 85-86)
        long_name = "x" * 150
        result2 = hello_world(long_name)
        assert len(result2) > 0  # Should succeed after truncation

    def test_hello_world_exception_in_logging(self):
        """Cover lines 106-118 in hello_world exception handling."""
        # Force an exception in the log_mcp_tool_execution call
        original_func = None
        try:
            import remote_mcp_server.mcp_server as mcp_mod

            original_func = mcp_mod.log_mcp_tool_execution
            mcp_mod.log_mcp_tool_execution = Mock(
                side_effect=Exception("Logging error")
            )

            with pytest.raises(Exception):
                hello_world("test")

        finally:
            if original_func:
                import remote_mcp_server.mcp_server as mcp_mod

                mcp_mod.log_mcp_tool_execution = original_func

    def test_get_current_time_datetime_exception(self):
        """Cover lines 155-166 in get_current_time exception handling."""
        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.side_effect = RuntimeError("Clock error")

            with pytest.raises(RuntimeError):
                get_current_time()

    def test_echo_message_conversion_paths(self):
        """Cover lines 194-195 in echo_message."""
        # Non-string message conversion
        result = echo_message(42, 1)
        assert "42" in result

    def test_echo_message_invalid_repeat_handling(self):
        """Cover lines 201-209 in echo_message invalid repeat handling."""
        # Test string that can be converted to int
        result1 = echo_message("test", "3")
        assert result1 == "test test test"

        # Test invalid conversion that defaults to 1
        result2 = echo_message("hello", "invalid")
        assert result2 == "hello"

    def test_echo_message_truncation(self):
        """Cover lines 230-231 in echo_message message truncation."""
        very_long_message = "x" * 1100  # Over 1000 char limit
        result = echo_message(very_long_message, 1)
        assert len(result) == 1000  # Should be truncated

    def test_get_server_info_psutil_scenarios(self):
        """Cover lines 297-298 and 305-306 in get_server_info."""
        # Test ImportError scenario (lines 297-298)
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'psutil'")
        ):
            result1 = get_server_info()
            assert "memory_percent" not in result1

        # Test psutil exception scenario (lines 305-306)
        mock_psutil = Mock()
        mock_psutil.virtual_memory.side_effect = Exception("Memory access error")

        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            with patch("remote_mcp_server.mcp_server.psutil", mock_psutil):
                result2 = get_server_info()
                assert "memory_percent" not in result2

    def test_get_server_info_general_exception(self):
        """Cover lines 339-350 in get_server_info general exception."""
        with patch("os.environ.get", side_effect=Exception("Environment error")):
            with pytest.raises(Exception):
                get_server_info()

    def test_calculate_sum_invalid_number_conversion(self):
        """Cover lines 425-427 in calculate_sum."""
        # Test with invalid number that can't be converted
        with pytest.raises(ValueError, match="Invalid number at index"):
            calculate_sum([1, 2, object(), 4])  # object() can't be converted to float

    @pytest.mark.asyncio
    async def test_mcp_request_exception_in_processing(self):
        """Cover lines 581-597 in handle_mcp_request exception handling."""
        # Force exception in request processing by patching time.time
        with patch(
            "remote_mcp_server.mcp_server.time.time",
            side_effect=Exception("Time error"),
        ):
            request = {"jsonrpc": "2.0", "method": "test", "id": 1}

            response = await handle_mcp_request(request)

            assert "error" in response
            assert response["error"]["code"] == -32603

    def test_lambda_handler_edge_cases(self):
        """Cover lines 806-808 and other Lambda edge cases."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        # Test with weird event structure
        event = {
            "httpMethod": "PATCH",
            "path": "/weird-path",
            "headers": {},
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

    def test_lambda_handler_no_aws_context(self):
        """Cover line 634 in lambda_handler when context has no aws_request_id."""
        handler = create_lambda_handler()

        # Create context without aws_request_id
        context = Mock(spec=["function_name"])
        context.function_name = "test-function"

        event = {
            "httpMethod": "GET",
            "path": "/test",
            "headers": {},
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200


class TestLoggingRemainingLines:
    """Target the remaining logging_config.py lines."""

    def test_request_context_edge_case(self):
        """Cover line 134 in logging_config - request context without timestamp."""
        import logging

        from remote_mcp_server.logging_config import (
            StructuredFormatter,
            _request_context,
        )

        # Manually manipulate request context to missing timestamp case
        original_context = _request_context.copy()
        try:
            _request_context.clear()
            _request_context.update({"request_id": "test-no-timestamp"})

            formatter = StructuredFormatter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="test",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            log_data = json.loads(result)
            assert "request" in log_data

        finally:
            _request_context.clear()
            _request_context.update(original_context)

    def test_performance_logger_missing_branch(self):
        """Cover line 257 in logging_config - performance logger creation."""
        import logging

        from remote_mcp_server.logging_config import log_function_entry_exit

        # Create a function with the decorator but without explicit logger
        @log_function_entry_exit()
        def test_func():
            return "test"

        result = test_func()
        assert result == "test"

    def test_lambda_context_optional_attrs(self):
        """Cover lines 305-306, 312-313 in log_aws_lambda_context."""
        from remote_mcp_server.logging_config import log_aws_lambda_context

        # Create context with missing optional attributes
        context = Mock()
        context.aws_request_id = "test-123"
        context.function_name = "test-func"
        context.function_version = "1.0"
        context.memory_limit_in_mb = "128"
        context.get_remaining_time_in_millis.return_value = 30000
        # Missing log_group_name and log_stream_name - should use getattr defaults

        # Should not raise exception
        log_aws_lambda_context(context)

    def test_structured_formatter_json_fallback(self):
        """Cover lines 73-74 - JSON serialization fallback."""
        import logging

        from remote_mcp_server.logging_config import StructuredFormatter

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        # Add non-serializable object
        class NonSerializable:
            pass

        record.bad_field = NonSerializable()

        # Should fall back to string conversion
        result = formatter.format(record)
        assert "bad_field" in result

    def test_sanitize_dict_edge_cases(self):
        """Cover line 559 in _sanitize_dict."""
        from remote_mcp_server.logging_config import _sanitize_dict

        # Test with complex nested structure that triggers edge cases
        test_data = {
            "normal": "value",
            "password": "secret",
            "nested": {"deep": {"deeper": "value", "token": "secret-token"}},
            "large_list": list(range(20)),  # Triggers truncation
        }

        result = _sanitize_dict(test_data)
        assert result["password"] == "<REDACTED>"
        assert "nested" in result

    def test_http_request_json_parse_error(self):
        """Cover lines 448-449 in log_http_request."""
        from remote_mcp_server.logging_config import log_http_request

        # Test with invalid JSON body that triggers parse error
        log_http_request("POST", "/test", {}, '{"invalid": json content}')
        # Should not raise exception, just log without parsed body
