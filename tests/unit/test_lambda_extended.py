"""Extended Lambda handler tests for 100% coverage."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from remote_mcp_server.mcp_server import create_lambda_handler
from tests.conftest import MockLambdaContext


class TestLambdaHandlerExtended:
    """Extended tests for Lambda handler edge cases."""

    def test_lambda_handler_without_aws_request_id(self):
        """Test Lambda handler when context doesn't have aws_request_id."""
        handler = create_lambda_handler()

        # Create context without aws_request_id
        context = Mock()
        context.function_name = "test-function"
        # No aws_request_id attribute

        event = {
            "httpMethod": "GET",
            "path": "/health",
            "headers": {},
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

    def test_lambda_handler_cold_start_detection(self):
        """Test Lambda handler cold start detection."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {"httpMethod": "GET", "path": "/", "headers": {}, "requestContext": {}}

        # First call should be cold start
        response1 = handler(event, context)
        assert response1["statusCode"] == 200

        # Second call should be warm
        response2 = handler(event, context)
        assert response2["statusCode"] == 200

    def test_lambda_handler_records_event(self):
        """Test Lambda handler with Records event (SQS/SNS)."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {
            "Records": [
                {"eventSource": "aws:sqs", "body": "test message"},
                {"eventSource": "aws:sns", "Message": "test notification"},
            ]
        }

        response = handler(event, context)
        assert response["statusCode"] == 200
        assert "remote-mcp-server" in response["body"]

    def test_lambda_handler_direct_mcp_event(self):
        """Test Lambda handler with direct MCP method call."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "hello_world", "arguments": {"name": "Test"}},
            "id": 1,
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["jsonrpc"] == "2.0"

    def test_lambda_handler_unknown_event_type(self):
        """Test Lambda handler with unknown event type."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {"unknown_field": "unknown_value", "custom_data": {"key": "value"}}

        response = handler(event, context)
        assert response["statusCode"] == 200
        assert "remote-mcp-server" in response["body"]

    def test_lambda_handler_base64_encoded_body(self):
        """Test Lambda handler with base64 encoded POST body."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        import base64

        test_data = {"test": "base64 data"}
        encoded_body = base64.b64encode(json.dumps(test_data).encode()).decode()

        event = {
            "httpMethod": "POST",
            "path": "/remote-mcp-server",
            "headers": {"Content-Type": "application/json"},
            "body": encoded_body,
            "isBase64Encoded": True,
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

    def test_lambda_handler_malformed_json_body(self):
        """Test Lambda handler with malformed JSON in POST body."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {
            "httpMethod": "POST",
            "path": "/remote-mcp-server",
            "headers": {"Content-Type": "application/json"},
            "body": "invalid json {{{",
            "isBase64Encoded": False,
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert "raw_body" in body["received_data"]

    def test_lambda_handler_empty_post_body(self):
        """Test Lambda handler with empty POST body."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {
            "httpMethod": "POST",
            "path": "/remote-mcp-server",
            "headers": {"Content-Type": "application/json"},
            "body": None,
            "isBase64Encoded": False,
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

    def test_lambda_handler_mcp_request_via_post(self):
        """Test Lambda handler with MCP request sent via POST."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "hello_world", "arguments": {"name": "PostTest"}},
            "id": 42,
        }

        event = {
            "httpMethod": "POST",
            "path": "/remote-mcp-server",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(mcp_request),
            "isBase64Encoded": False,
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["jsonrpc"] == "2.0"
        assert body["id"] == 42

    def test_lambda_handler_post_processing_exception(self):
        """Test Lambda handler POST processing with exception."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {
            "httpMethod": "POST",
            "path": "/remote-mcp-server",
            "headers": {"Content-Type": "application/json"},
            "body": "{}",
            "isBase64Encoded": False,
            "requestContext": {},
        }

        # Simulate exception in JSON processing
        with patch("json.loads", side_effect=Exception("JSON error")):
            response = handler(event, context)
            assert response["statusCode"] == 400
            assert "Bad Request" in response["body"]

    def test_lambda_handler_exception_without_start_time(self):
        """Test Lambda handler exception before start_time is set."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {"httpMethod": "GET", "path": "/", "headers": {}}

        # Simulate exception very early in processing
        with patch(
            "remote_mcp_server.mcp_server.log_aws_lambda_context",
            side_effect=Exception("Early error"),
        ):
            response = handler(event, context)
            assert response["statusCode"] == 500

    def test_lambda_handler_context_cleanup(self):
        """Test that request context is cleaned up in finally block."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {"httpMethod": "GET", "path": "/", "headers": {}}

        with patch("remote_mcp_server.mcp_server.clear_request_context") as mock_clear:
            handler(event, context)
            mock_clear.assert_called_once()

    def test_lambda_event_processing_edge_cases(self):
        """Test edge cases in Lambda event processing."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        # Test with unusual path and method combinations
        event = {
            "httpMethod": "PUT",
            "path": "/unusual-path",
            "headers": {"Custom-Header": "test"},
            "requestContext": {},
        }

        response = handler(event, context)
        assert response["statusCode"] == 200

    def test_lambda_handler_response_logging(self):
        """Test Lambda handler response logging details."""
        handler = create_lambda_handler()
        context = MockLambdaContext()

        event = {
            "httpMethod": "GET",
            "path": "/health",
            "headers": {},
            "requestContext": {},
        }

        with patch("remote_mcp_server.mcp_server.log_http_response") as mock_log:
            response = handler(event, context)
            assert response["statusCode"] == 200
            mock_log.assert_called()
