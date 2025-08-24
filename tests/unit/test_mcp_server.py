"""Unit tests for MCP server functionality."""

import datetime
import pytest
from mcp.server import FastMCP

from remote_mcp_server.config import ServerConfig
from remote_mcp_server.server import create_lambda_handler, create_mcp_server
from remote_mcp_server.aws_lambda import LambdaHandler


class TestMCPServer:
    """Test MCP server creation and configuration."""
    
    def test_create_mcp_server(self):
        """Test MCP server creation."""
        config = ServerConfig()
        server = create_mcp_server(config)
        
        assert isinstance(server, FastMCP)
        assert server.name == "remote-mcp-server"
        assert "A simple MCP server" in server.instructions
    
    def test_create_lambda_handler(self):
        """Test Lambda handler creation."""
        config = ServerConfig()
        handler = create_lambda_handler(config)
        
        assert handler is not None
        assert hasattr(handler, '__call__')
        assert isinstance(handler, LambdaHandler)


class TestServerConfig:
    """Test server configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ServerConfig()
        
        assert config.port == 3000
        assert config.log_level == "INFO"
        assert config.environment == "dev"
        assert config.version == "1.0.0"
        assert config.memory_limit == 256
        assert config.timeout == 30

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ServerConfig(
            port=8080,
            log_level="DEBUG",
            environment="prod"
        )
        
        assert config.port == 8080
        assert config.log_level == "DEBUG"
        assert config.environment == "prod"

    def test_config_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("ENVIRONMENT", "staging")
        
        config = ServerConfig.from_env()
        
        assert config.port == 9000
        assert config.log_level == "WARNING" 
        assert config.environment == "staging"


class TestLambdaHandler:
    """Test Lambda handler functionality."""
    
    @pytest.fixture
    def handler(self):
        """Create a Lambda handler for testing."""
        config = ServerConfig()
        return LambdaHandler(config)
    
    def test_health_check(self, handler):
        """Test health check endpoint."""
        event = {
            "httpMethod": "GET",
            "path": "/health",
            "body": None
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        assert "application/json" in response["headers"]["Content-Type"]
        
        import json
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
        assert body["service"] == "remote-mcp-server"
        assert body["version"] == "1.0.0"
    
    def test_default_get_response(self, handler):
        """Test default GET response."""
        event = {
            "httpMethod": "GET",
            "path": "/",
            "body": None
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        assert "application/json" in response["headers"]["Content-Type"]
        
        import json
        body = json.loads(response["body"])
        assert body["message"] == "remote-mcp-server"
        assert body["version"] == "1.0.0"
        assert "endpoints" in body
    
    def test_unsupported_method(self, handler):
        """Test unsupported HTTP method."""
        event = {
            "httpMethod": "DELETE",
            "path": "/",
            "body": None
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 405
        assert "Allow" in response["headers"]
        
        import json
        body = json.loads(response["body"])
        assert body["error"] == "Method Not Allowed"
        assert body["error_code"] == "UNSUPPORTED_METHOD"
    
    def test_invalid_endpoint(self, handler):
        """Test invalid endpoint."""
        event = {
            "httpMethod": "GET",
            "path": "/invalid",
            "body": None
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 404
        
        import json
        body = json.loads(response["body"])
        assert body["error"] == "Not Found"
        assert body["error_code"] == "INVALID_ENDPOINT"
    
    def test_post_without_body(self, handler):
        """Test POST request without body."""
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": None
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 400
        
        import json
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert body["error_code"] == "MISSING_BODY"
    
    def test_post_with_invalid_json(self, handler):
        """Test POST request with invalid JSON."""
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": '{"invalid": json,}'
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 400
        
        import json
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert body["error_code"] == "INVALID_JSON"
    
    def test_mcp_request_invalid_jsonrpc(self, handler):
        """Test MCP request with invalid JSON-RPC version."""
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": '{"jsonrpc": "1.0", "method": "ping", "id": 1}'
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        
        import json
        response_data = json.loads(response["body"])
        
        assert response_data["jsonrpc"] == "2.0"
        assert "error" in response_data
        assert response_data["error"]["code"] == -32600
    
    def test_post_request_missing_method(self, handler):
        """Test POST request that's missing method field (not treated as MCP)."""
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": '{"jsonrpc": "2.0", "id": 1}'
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        
        import json
        body = json.loads(response["body"])
        
        # This is not an MCP request (missing "method"), so it should be a regular POST response
        assert body["message"] == "POST request received"
        assert body["service"] == "remote-mcp-server"
    
    def test_mcp_request_ping(self, handler):
        """Test MCP ping request."""
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": '{"jsonrpc": "2.0", "method": "ping", "id": 1}'
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        
        import json
        response_data = json.loads(response["body"])
        
        assert response_data["jsonrpc"] == "2.0"
        assert "result" in response_data
        assert response_data["result"]["status"] == "pong"
        assert response_data["id"] == 1
    
    def test_mcp_request_tools_list(self, handler):
        """Test MCP tools/list request."""
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        
        import json
        response_data = json.loads(response["body"])
        
        assert response_data["jsonrpc"] == "2.0"
        assert "result" in response_data
        assert "tools" in response_data["result"]
        
        tools = response_data["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]
        expected_tools = ["hello_world", "get_current_time", "echo_message", "get_server_info", "calculate_sum"]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names
    
    def test_mcp_request_invalid_method(self, handler):
        """Test MCP request with invalid method."""
        event = {
            "httpMethod": "POST",
            "path": "/",
            "body": '{"jsonrpc": "2.0", "method": "invalid_method", "id": 1}'
        }
        context = {}
        
        response = handler(event, context)
        
        assert response["statusCode"] == 200
        
        import json
        response_data = json.loads(response["body"])
        
        assert response_data["jsonrpc"] == "2.0"
        assert "error" in response_data
        assert response_data["error"]["code"] == -32601