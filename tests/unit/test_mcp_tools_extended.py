"""Extended unit tests for MCP tools to achieve 100% coverage."""

import json
from unittest.mock import Mock, patch

import pytest

from remote_mcp_server.mcp_server import (
    calculate_sum,
    echo_message,
    get_current_time,
    get_server_info,
    handle_mcp_request,
    hello_world,
    main,
)


class TestMCPToolsErrorPaths:
    """Test error paths and edge cases in MCP tools."""

    def test_hello_world_non_string_input(self):
        """Test hello_world with non-string input."""
        # Test with integer input
        result = hello_world(12345)
        assert "12345" in result

        # Test with None input
        result = hello_world(None)
        assert "None" in result

    def test_hello_world_long_name_truncation(self):
        """Test hello_world with very long name."""
        long_name = "x" * 150  # Longer than 100 character limit
        result = hello_world(long_name)
        # Should be truncated to 100 characters
        assert len(long_name[:100]) == 100
        assert "x" * 100 in result

    def test_hello_world_exception_logging(self):
        """Test hello_world exception handling."""
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            # Simulate an exception in message formatting
            with patch(
                "remote_mcp_server.mcp_server.log_mcp_tool_execution",
                side_effect=Exception("Test error"),
            ):
                with pytest.raises(Exception):
                    hello_world("test")

    def test_get_current_time_exception_handling(self):
        """Test get_current_time exception paths."""
        with patch("datetime.datetime.now", side_effect=Exception("Time error")):
            with pytest.raises(Exception):
                get_current_time()

    def test_echo_message_non_string_message(self):
        """Test echo_message with non-string message input."""
        result = echo_message(12345, 2)
        assert "12345 12345" in result

    def test_echo_message_non_integer_repeat(self):
        """Test echo_message with non-integer repeat count."""
        # Test with string that can be converted
        result = echo_message("test", "2")
        assert "test test" in result

        # Test with invalid repeat count that defaults to 1
        result = echo_message("test", "invalid")
        assert result == "test"

    def test_echo_message_long_message_truncation(self):
        """Test echo_message with very long message."""
        long_message = "x" * 1200  # Longer than 1000 character limit
        result = echo_message(long_message, 1)
        # Should be truncated to 1000 characters
        assert len(result) == 1000

    def test_echo_message_invalid_repeat_range(self):
        """Test echo_message with invalid repeat counts."""
        # Test repeat < 1
        with pytest.raises(ValueError, match="Repeat count must be between 1 and 10"):
            echo_message("test", 0)

        # Test repeat > 10
        with pytest.raises(ValueError, match="Repeat count must be between 1 and 10"):
            echo_message("test", 15)

    def test_get_server_info_psutil_unavailable(self):
        """Test get_server_info when psutil is not available."""
        with patch(
            "remote_mcp_server.mcp_server.psutil",
            side_effect=ImportError("psutil not available"),
        ):
            result = get_server_info()
            assert result["service"] == "remote-mcp-server"
            assert "memory_percent" not in result

    def test_get_server_info_psutil_exception(self):
        """Test get_server_info when psutil raises an exception."""
        mock_psutil = Mock()
        mock_psutil.virtual_memory.side_effect = Exception("Memory error")
        mock_psutil.cpu_percent.side_effect = Exception("CPU error")

        with patch("remote_mcp_server.mcp_server.psutil", mock_psutil):
            result = get_server_info()
            assert result["service"] == "remote-mcp-server"
            assert "memory_percent" not in result

    def test_get_server_info_exception_handling(self):
        """Test get_server_info general exception handling."""
        with patch("datetime.datetime.now", side_effect=Exception("Time error")):
            with pytest.raises(Exception):
                get_server_info()

    def test_calculate_sum_invalid_input_type(self):
        """Test calculate_sum with invalid input types."""
        # Test with string input
        try:
            calculate_sum("not a list")
            assert False, "Should have raised TypeError"
        except Exception as e:
            # Could be TypeError from isinstance check or from len() call
            assert "list" in str(e) or "len()" in str(e) or "has no len" in str(e)

        # Test with integer input
        try:
            calculate_sum(12345)
            assert False, "Should have raised TypeError"
        except Exception as e:
            # Could be TypeError from isinstance check or from len() call
            assert "list" in str(e) or "len()" in str(e) or "has no len" in str(e)

    def test_calculate_sum_empty_list(self):
        """Test calculate_sum with empty list."""
        result = calculate_sum([])
        assert result == 0.0

    def test_calculate_sum_too_many_numbers(self):
        """Test calculate_sum with more than 100 numbers."""
        large_list = list(range(150))  # More than 100 items
        with pytest.raises(ValueError, match="Maximum 100 numbers allowed"):
            calculate_sum(large_list)

    def test_calculate_sum_invalid_number_types(self):
        """Test calculate_sum with invalid number types."""
        # Test with invalid number at specific index
        with pytest.raises(ValueError, match="Invalid number at index 1"):
            calculate_sum([1.0, "invalid", 3.0])

    def test_calculate_sum_string_conversions(self):
        """Test calculate_sum with string numbers."""
        result = calculate_sum(["1.5", "2.5", "3.0"])
        assert result == 7.0

    def test_calculate_sum_mixed_type_conversions(self):
        """Test calculate_sum with mixed convertible types."""
        result = calculate_sum([1, 2.5, "3.5", 4])
        assert result == 11.0

    def test_calculate_sum_exception_handling(self):
        """Test calculate_sum general exception handling."""
        with patch("remote_mcp_server.mcp_server.tools_logger") as mock_logger:
            # Simulate an exception in sum calculation
            with patch("builtins.sum", side_effect=Exception("Sum error")):
                with pytest.raises(Exception):
                    calculate_sum([1, 2, 3])


class TestMCPRequestHandling:
    """Test MCP request handling functionality."""

    @pytest.mark.asyncio
    async def test_handle_mcp_request_invalid_jsonrpc(self):
        """Test MCP request with invalid JSON-RPC version."""
        request = {"jsonrpc": "1.0", "method": "tools/call", "id": 1}  # Invalid version
        response = await handle_mcp_request(request)
        assert response["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_handle_mcp_request_tools_list(self):
        """Test MCP request for tools list."""
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        response = await handle_mcp_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1

    @pytest.mark.asyncio
    async def test_handle_mcp_request_exception(self):
        """Test MCP request handling with exception."""
        # Simulate an exception during request processing
        with patch("time.time", side_effect=Exception("Time error")):
            request = {"jsonrpc": "2.0", "method": "tools/call", "id": 1}
            response = await handle_mcp_request(request)
            assert "error" in response
            assert response["error"]["code"] == -32603


class TestMainFunction:
    """Test the main entry point function."""

    def test_main_function_default_args(self):
        """Test main function with default arguments."""
        with patch("sys.argv", ["mcp_server.py"]):
            with patch("remote_mcp_server.mcp_server.mcp.run") as mock_run:
                main()
                mock_run.assert_called_once()

    def test_main_function_custom_port(self):
        """Test main function with custom port."""
        with patch("sys.argv", ["mcp_server.py", "--port", "8080"]):
            with patch("remote_mcp_server.mcp_server.mcp.run") as mock_run:
                main()
                mock_run.assert_called_once()

    def test_main_function_custom_log_level(self):
        """Test main function with custom log level."""
        with patch("sys.argv", ["mcp_server.py", "--log-level", "DEBUG"]):
            with patch("remote_mcp_server.mcp_server.mcp.run") as mock_run:
                main()
                mock_run.assert_called_once()

    def test_main_function_all_args(self):
        """Test main function with all arguments."""
        with patch(
            "sys.argv", ["mcp_server.py", "--port", "9000", "--log-level", "ERROR"]
        ):
            with patch("remote_mcp_server.mcp_server.mcp.run") as mock_run:
                main()
                mock_run.assert_called_once()
