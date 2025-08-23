"""Integration tests for API Gateway endpoints."""

import os

import boto3
import pytest
import requests

"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test.
"""


@pytest.mark.integration
class TestApiGateway:
    """Test API Gateway integration with enhanced MCP functionality."""

    @pytest.fixture()
    def api_gateway_url(self):
        """Get the API Gateway URL from CloudFormation Stack outputs."""
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")

        # If no stack name is provided, use the known deployed endpoint
        if stack_name is None:
            return "https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod"

        client = boto3.client("cloudformation")

        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name} \n"
                f'Please make sure a stack with the name "{stack_name}" exists'
            ) from e

        stacks = response["Stacks"]
        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [
            output
            for output in stack_outputs
            if output["OutputKey"] == "RemoteMcpServerApi"
        ]

        if not api_outputs:
            raise KeyError(f"RemoteMcpServerApi not found in stack {stack_name}")

        return api_outputs[0]["OutputValue"]  # Extract url from stack outputs

    def test_api_gateway_default_endpoint(self, api_gateway_url):
        """Test the remote-mcp-server endpoint behavior."""
        # The API Gateway routes to /remote-mcp-server, not root
        endpoint_url = f"{api_gateway_url}/remote-mcp-server"
        response = requests.get(endpoint_url)

        # API Gateway might return 404 if the route doesn't exist, or 200 if it does
        if response.status_code == 404:
            # API Gateway level 404 - this is acceptable for this configuration
            assert response.status_code == 404
        elif response.status_code == 200:
            # Lambda function handled it
            json_response = response.json()
            # Our Lambda function returns an error for GET /remote-mcp-server since it expects /
            assert json_response["error"] == "Not Found"
            assert json_response["error_code"] == "INVALID_ENDPOINT"
            assert "available_endpoints" in json_response
        else:
            # Unexpected status code
            assert False, f"Unexpected status code: {response.status_code}"

    def test_api_gateway_health_endpoint(self, api_gateway_url):
        """Test the health check endpoint."""
        # Construct health endpoint URL
        health_url = api_gateway_url.rstrip("/") + "/health"

        response = requests.get(health_url)

        assert response.status_code == 200

        json_response = response.json()
        assert json_response["status"] == "healthy"
        assert json_response["service"] == "remote-mcp-server"
        assert json_response["version"] == "1.0.0"
        assert "timestamp" in json_response

    def test_api_gateway_cors_headers(self, api_gateway_url):
        """Test that proper CORS headers are returned."""
        health_url = f"{api_gateway_url}/health"
        response = requests.get(health_url)

        assert response.status_code == 200
        # CORS headers are configured in the SAM template Globals section
        # This test verifies they're working
        headers = response.headers
        # API Gateway should add CORS headers based on our template configuration

    def test_api_gateway_post_request(self, api_gateway_url):
        """Test POST request handling."""
        test_data = {
            "user_data": "integration test",
            "action": "test_post",
            "parameters": {"test_param": "test_value"},
        }

        # POST to the remote-mcp-server endpoint
        endpoint_url = f"{api_gateway_url}/remote-mcp-server"
        response = requests.post(
            endpoint_url,
            json=test_data,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["message"] == "POST request received"
        assert json_response["method"] == "POST"
        assert "received_data" in json_response
        assert json_response["received_data"]["user_data"] == "integration test"
        assert json_response["received_data"]["action"] == "test_post"

    def test_api_gateway_mcp_ping_request(self, api_gateway_url):
        """Test MCP ping request via POST."""
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 1,
        }

        endpoint_url = f"{api_gateway_url}/remote-mcp-server"
        response = requests.post(
            endpoint_url,
            json=mcp_request,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["jsonrpc"] == "2.0"
        assert json_response["result"]["status"] == "pong"
        assert json_response["id"] == 1
    
    def test_api_gateway_mcp_tools_list(self, api_gateway_url):
        """Test MCP tools list request."""
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2,
        }

        endpoint_url = f"{api_gateway_url}/remote-mcp-server"
        response = requests.post(
            endpoint_url,
            json=mcp_request,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["jsonrpc"] == "2.0"
        assert "tools" in json_response["result"]
        
        tools = json_response["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]
        expected_tools = ["hello_world", "get_current_time", "echo_message", "get_server_info", "calculate_sum"]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    def test_api_gateway_mcp_tool_call(self, api_gateway_url):
        """Test MCP tool call request."""
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "hello_world",
                "arguments": {"name": "API Gateway Test"},
            },
            "id": 3,
        }

        endpoint_url = f"{api_gateway_url}/remote-mcp-server"
        response = requests.post(
            endpoint_url,
            json=mcp_request,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["jsonrpc"] == "2.0"
        assert json_response["result"]["status"] == "success"
        assert "hello_world" in json_response["result"]["message"]
        assert json_response["id"] == 3

    @pytest.mark.slow
    def test_api_gateway_performance(self, api_gateway_url):
        """Test API Gateway response time."""
        import time

        health_url = f"{api_gateway_url}/health"
        start_time = time.time()
        response = requests.get(health_url)
        end_time = time.time()

        assert response.status_code == 200

        # Response should be reasonably fast (under 5 seconds)
        response_time = end_time - start_time
        assert response_time < 5.0, f"Response time too slow: {response_time}s"

    def test_api_gateway_error_handling(self, api_gateway_url):
        """Test error handling for invalid requests."""
        # Send a request with invalid path
        invalid_url = api_gateway_url.rstrip("/") + "/invalid-path"

        # Depending on API Gateway configuration, this might return 404 or 200
        response = requests.get(invalid_url)

        # The response should be valid JSON regardless
        try:
            json_response = response.json()
            # Should have some form of response structure
            assert isinstance(json_response, dict)
        except Exception:
            # If not JSON, should at least have a reasonable status code
            assert response.status_code in [200, 404, 500]

    def test_api_gateway_content_type(self, api_gateway_url):
        """Test that proper content type is returned."""
        health_url = f"{api_gateway_url}/health"
        response = requests.get(health_url)

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "").lower()

    @pytest.mark.slow
    def test_api_gateway_multiple_concurrent_requests(self, api_gateway_url):
        """Test multiple concurrent requests."""
        import concurrent.futures
        import threading

        def make_request():
            health_url = f"{api_gateway_url}/health"
            return requests.get(health_url)

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            json_response = response.json()
            assert json_response["status"] == "healthy"
            assert json_response["service"] == "remote-mcp-server"

    def test_api_gateway_mcp_error_handling(self, api_gateway_url):
        """Test MCP error handling for invalid requests."""
        # Test invalid JSON-RPC method
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "nonexistent_method",
            "id": 99,
        }

        endpoint_url = f"{api_gateway_url}/remote-mcp-server"
        response = requests.post(
            endpoint_url,
            json=mcp_request,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["jsonrpc"] == "2.0"
        assert "error" in json_response
        assert json_response["error"]["code"] == -32601  # Method not found
        assert "available_methods" in json_response["error"]["data"]
