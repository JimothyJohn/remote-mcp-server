#!/usr/bin/env python3
"""Simple test client for the Remote MCP Server."""

import asyncio
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_mcp_server():
    """Test the Remote MCP Server functionality."""

    # Configure server parameters
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "remote_mcp_server.mcp_server"],
        cwd="/home/nick/github/remote-mcp-server",
        env={"LOG_LEVEL": "INFO"},
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the server
                await session.initialize()

                print("🚀 Remote MCP Server initialized successfully!")
                print(f"📋 Server info: {session.server_info}")
                print()

                # List available tools
                tools_response = await session.list_tools()
                print("🔧 Available tools:")
                for tool in tools_response.tools:
                    print(f"  • {tool.name}: {tool.description}")
                print()

                # Test each tool
                test_cases = [
                    {"name": "hello_world", "arguments": {"name": "Claude Code User"}},
                    {"name": "get_current_time", "arguments": {}},
                    {
                        "name": "echo_message",
                        "arguments": {
                            "message": "Testing MCP integration!",
                            "repeat": 2,
                        },
                    },
                    {"name": "get_server_info", "arguments": {}},
                    {
                        "name": "calculate_sum",
                        "arguments": {"numbers": [10, 20, 30, 15, 25]},
                    },
                ]

                print("🧪 Testing MCP tools:")
                for i, test_case in enumerate(test_cases, 1):
                    try:
                        print(f"  {i}. Testing {test_case['name']}...")
                        result = await session.call_tool(
                            test_case["name"], test_case["arguments"]
                        )

                        if result.is_error:
                            print(f"     ❌ Error: {result.content}")
                        else:
                            print(
                                f"     ✅ Result: {result.content[:100]}{'...' if len(str(result.content)) > 100 else ''}"
                            )

                    except Exception as e:
                        print(f"     ❌ Exception: {e}")

                print()
                print("🎉 MCP Server testing completed!")

    except Exception as e:
        print(f"❌ Failed to connect to MCP server: {e}")
        return False

    return True


if __name__ == "__main__":
    print("🔍 Testing Remote MCP Server...")
    print("=" * 50)

    try:
        success = asyncio.run(test_mcp_server())
        if success:
            print("✅ Remote MCP Server is working correctly!")
            print("🔗 You can now use it with Claude Code.")
        else:
            print("❌ Remote MCP Server test failed.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
