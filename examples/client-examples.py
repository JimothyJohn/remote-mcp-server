#!/usr/bin/env python3
"""Example client implementations for Remote MCP Server.

This module demonstrates different ways to interact with the Remote MCP Server:
- Direct HTTP API calls
- MCP protocol requests
- Error handling
- Authentication (future)
"""

import asyncio
import json
import subprocess
from typing import Any

import httpx
import requests


class RemoteMcpClient:
    """HTTP client for Remote MCP Server API."""

    def __init__(
        self,
        base_url: str = "https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod",
    ):
        self.base_url = base_url.rstrip("/")

    def health_check(self) -> dict[str, Any]:
        """Check server health status."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def get_server_info(self) -> dict[str, Any]:
        """Get basic server information."""
        response = requests.get(f"{self.base_url}/remote-mcp-server")
        response.raise_for_status()
        return response.json()

    def post_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Send arbitrary JSON data to the server."""
        response = requests.post(
            f"{self.base_url}/remote-mcp-server",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def call_mcp_tool(
        self, tool_name: str, arguments: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Call an MCP tool via HTTP POST."""
        if arguments is None:
            arguments = {}

        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }

        response = requests.post(
            f"{self.base_url}/remote-mcp-server",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


class AsyncRemoteMcpClient:
    """Async HTTP client for Remote MCP Server API."""

    def __init__(
        self,
        base_url: str = "https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod",
    ):
        self.base_url = base_url.rstrip("/")

    async def health_check(self) -> dict[str, Any]:
        """Check server health status asynchronously."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def call_mcp_tool(
        self, tool_name: str, arguments: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Call an MCP tool asynchronously."""
        if arguments is None:
            arguments = {}

        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/remote-mcp-server",
                json=mcp_request,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()


class DirectMcpClient:
    """Direct MCP client using stdio protocol."""

    def __init__(self, command: list[str] = None):
        if command is None:
            command = ["uv", "run", "python", "-m", "remote_mcp_server.mcp_server"]
        self.command = command
        self.process: subprocess.Popen | None = None

    def start(self):
        """Start the MCP server process."""
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None

    def send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a request to the MCP server."""
        if not self.process:
            raise RuntimeError("MCP server not started")

        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")

        return json.loads(response_line.strip())

    def call_tool(
        self, tool_name: str, arguments: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Call an MCP tool directly."""
        if arguments is None:
            arguments = {}

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }

        return self.send_request(request)

    def list_tools(self) -> dict[str, Any]:
        """List available tools."""
        request = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2}

        return self.send_request(request)


def example_http_client():
    """Example using HTTP client."""
    print("=== HTTP Client Example ===")

    client = RemoteMcpClient()

    # Health check
    health = client.health_check()
    print(f"Health: {health}")

    # Server info
    info = client.get_server_info()
    print(f"Server Info: {info}")

    # Post arbitrary data
    data = {"message": "Hello from Python client!", "user_id": 12345}
    response = client.post_data(data)
    print(f"POST Response: {response}")

    # Call MCP tools via HTTP
    hello_response = client.call_mcp_tool("hello_world", {"name": "HTTP Client"})
    print(f"Hello World: {hello_response}")

    time_response = client.call_mcp_tool("get_current_time")
    print(f"Current Time: {time_response}")

    sum_response = client.call_mcp_tool("calculate_sum", {"numbers": [1, 2, 3, 4, 5]})
    print(f"Sum: {sum_response}")


async def example_async_client():
    """Example using async HTTP client."""
    print("\\n=== Async HTTP Client Example ===")

    client = AsyncRemoteMcpClient()

    # Health check
    health = await client.health_check()
    print(f"Health: {health}")

    # Call tools concurrently
    tasks = [
        client.call_mcp_tool("hello_world", {"name": "Async Client"}),
        client.call_mcp_tool("get_current_time"),
        client.call_mcp_tool("echo_message", {"message": "Async", "repeat": 3}),
    ]

    results = await asyncio.gather(*tasks)
    for i, result in enumerate(results):
        print(f"Async Result {i+1}: {result}")


def example_direct_mcp_client():
    """Example using direct MCP protocol client."""
    print("\\n=== Direct MCP Client Example ===")

    client = DirectMcpClient()

    try:
        client.start()

        # List available tools
        tools = client.list_tools()
        print(f"Available Tools: {tools}")

        # Call tools
        hello_response = client.call_tool("hello_world", {"name": "Direct MCP Client"})
        print(f"Hello Response: {hello_response}")

        echo_response = client.call_tool(
            "echo_message", {"message": "MCP Protocol", "repeat": 2}
        )
        print(f"Echo Response: {echo_response}")

    finally:
        client.stop()


def example_error_handling():
    """Example demonstrating error handling."""
    print("\\n=== Error Handling Example ===")

    client = RemoteMcpClient()

    # Test invalid tool call
    try:
        response = client.call_mcp_tool("nonexistent_tool")
        print(f"Unexpected success: {response}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error (expected): {e}")
    except Exception as e:
        print(f"Other Error: {e}")

    # Test invalid parameters
    try:
        response = client.call_mcp_tool(
            "echo_message", {"repeat": 100}
        )  # Too many repeats
        print(f"Response with invalid params: {response}")
    except Exception as e:
        print(f"Parameter Error: {e}")


def example_batch_operations():
    """Example performing multiple operations efficiently."""
    print("\\n=== Batch Operations Example ===")

    client = RemoteMcpClient()

    # Simulate multiple user requests
    requests_to_process = [
        ("hello_world", {"name": "User1"}),
        ("hello_world", {"name": "User2"}),
        ("get_current_time", {}),
        ("calculate_sum", {"numbers": [10, 20, 30]}),
        ("echo_message", {"message": "Batch", "repeat": 2}),
    ]

    results = []
    for tool_name, args in requests_to_process:
        try:
            result = client.call_mcp_tool(tool_name, args)
            results.append({"success": True, "tool": tool_name, "result": result})
        except Exception as e:
            results.append({"success": False, "tool": tool_name, "error": str(e)})

    print(f"Batch Results: {json.dumps(results, indent=2)}")


def main():
    """Run all examples."""
    print("Remote MCP Server Client Examples")
    print("=" * 50)

    # Check if server is accessible
    try:
        client = RemoteMcpClient()
        health = client.health_check()
        print(f"Server Status: {health['status']}")
    except Exception as e:
        print(f"Warning: Server not accessible - {e}")
        print("Some examples may fail\\n")

    # Run examples
    example_http_client()

    # Async example
    asyncio.run(example_async_client())

    # Direct MCP client (requires local server)
    try:
        example_direct_mcp_client()
    except Exception as e:
        print(f"Direct MCP client failed (expected if not running locally): {e}")

    example_error_handling()
    example_batch_operations()

    print("\\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    main()
