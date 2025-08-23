"""Integration tests for MCP server functionality."""

import json
import pytest

from remote_mcp_server.server import create_mcp_server
from remote_mcp_server.config import ServerConfig
from remote_mcp_server.aws_lambda import LambdaHandler


@pytest.mark.integration
class TestMCPIntegration:
    """Integration tests for MCP server."""

    def test_mcp_server_creation_and_lambda_integration(self):
        """Test MCP server creation integrates properly with Lambda handler."""
        config = ServerConfig(environment="test")
        
        # Create MCP server
        mcp_server = create_mcp_server(config)
        assert mcp_server is not None
        assert mcp_server.name == "remote-mcp-server"
        
        # Create Lambda handler
        lambda_handler = LambdaHandler(config)
        assert lambda_handler is not None

    def test_full_mcp_request_flow(self):
        """Test complete MCP request flow through Lambda handler."""
        config = ServerConfig(environment="test")
        handler = LambdaHandler(config)
        
        # Test tools/list request
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            })
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        response_data = json.loads(response["body"])
        
        assert response_data["jsonrpc"] == "2.0"
        assert "result" in response_data
        assert "tools" in response_data["result"]
        
        # Verify expected tools are listed
        tools = response_data["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]
        
        expected_tools = [
            "hello_world",
            "get_current_time", 
            "echo_message",
            "get_server_info",
            "calculate_sum"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not found in {tool_names}"

    def test_mcp_error_handling_integration(self):
        """Test MCP error handling integration."""
        config = ServerConfig(environment="test")
        handler = LambdaHandler(config)
        
        # Test invalid method
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": json.dumps({
                "jsonrpc": "2.0",
                "method": "nonexistent_method",
                "id": 1
            })
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        response_data = json.loads(response["body"])
        
        assert response_data["jsonrpc"] == "2.0"
        assert "error" in response_data
        assert response_data["error"]["code"] == -32601  # Method not found
        assert "available_methods" in response_data["error"]["data"]

    def test_configuration_integration(self):
        """Test configuration integration across components."""
        custom_config = ServerConfig(
            port=8080,
            log_level="DEBUG",
            environment="integration-test",
            version="test-version"
        )
        
        # Create components with custom config
        mcp_server = create_mcp_server(custom_config)
        lambda_handler = LambdaHandler(custom_config)
        
        # Test that configuration is properly used
        assert lambda_handler.config.environment == "integration-test"
        assert lambda_handler.config.version == "test-version"
        assert lambda_handler.config.port == 8080
        
        # Test health check reflects configuration
        event = {
            "httpMethod": "GET",
            "path": "/health",
            "body": None
        }
        context = {}
        
        response = lambda_handler(event, context)
        response_data = json.loads(response["body"])
        
        assert response_data["version"] == "test-version"