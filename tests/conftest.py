"""Pytest configuration and fixtures."""

import json
import os
from unittest.mock import patch

import pytest
from mcp.server import FastMCP

from remote_mcp_server.mcp_server import create_lambda_handler, mcp


@pytest.fixture
def mock_environment():
    """Mock environment variables."""
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "test", "AWS_REGION": "us-east-1", "LOG_LEVEL": "INFO"},
    ):
        yield


@pytest.fixture
def mcp_server():
    """Provide MCP server instance for testing."""
    return mcp


@pytest.fixture
def lambda_handler():
    """Provide Lambda handler for testing."""
    return create_lambda_handler()


@pytest.fixture
def sample_api_gateway_event():
    """Sample API Gateway event for testing."""
    return {
        "httpMethod": "GET",
        "path": "/",
        "headers": {"Accept": "application/json", "Content-Type": "application/json"},
        "queryStringParameters": {},
        "body": None,
        "requestContext": {"requestId": "test-request-id", "stage": "test"},
    }


@pytest.fixture
def sample_health_check_event():
    """Sample health check event for testing."""
    return {
        "httpMethod": "GET",
        "path": "/health",
        "headers": {"Accept": "application/json", "Content-Type": "application/json"},
        "queryStringParameters": {},
        "body": None,
        "requestContext": {"requestId": "test-health-request-id", "stage": "test"},
    }


@pytest.fixture
def sample_mcp_request():
    """Sample MCP request for testing."""
    return {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "hello_world", "arguments": {"name": "Test User"}},
        "id": 1,
    }


@pytest.fixture
def sample_post_event():
    """Sample POST event for testing."""
    return {
        "httpMethod": "POST",
        "path": "/remote-mcp-server",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "user_data": "test data",
                "action": "process",
                "parameters": {"key1": "value1", "key2": "value2"},
            }
        ),
        "isBase64Encoded": False,
        "requestContext": {"requestId": "test-post-request-id", "stage": "test"},
    }


@pytest.fixture
def sample_mcp_post_event():
    """Sample MCP request via POST event."""
    mcp_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "calculate_sum", "arguments": {"numbers": [1, 2, 3, 4, 5]}},
        "id": 42,
    }

    return {
        "httpMethod": "POST",
        "path": "/remote-mcp-server",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(mcp_request),
        "isBase64Encoded": False,
        "requestContext": {"requestId": "test-mcp-post-request-id", "stage": "test"},
    }


class MockLambdaContext:
    """Mock AWS Lambda context for testing."""

    def __init__(self):
        self.function_name = "test-function"
        self.function_version = "$LATEST"
        self.invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        )
        self.memory_limit_in_mb = "128"
        self.log_group_name = "/aws/lambda/test-function"
        self.log_stream_name = "2023/01/01/[$LATEST]test123"
        self.aws_request_id = "test-request-id-123"

    def get_remaining_time_in_millis(self):
        """Get remaining execution time."""
        return 30000


@pytest.fixture
def lambda_context():
    """Provide mock Lambda context."""
    return MockLambdaContext()


@pytest.fixture
def mock_mcp_tools():
    """Mock MCP tools for testing."""
    tools = [
        {
            "name": "hello_world",
            "description": "Say hello to someone",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name to greet",
                        "default": "World",
                    }
                },
            },
        },
        {
            "name": "get_current_time",
            "description": "Get the current timestamp",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]
    return tools
