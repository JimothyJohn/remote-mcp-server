#!/usr/bin/env python3
"""Simple test for MCP server tools functionality."""

import sys

# Add the project to the path
sys.path.insert(0, "/home/nick/github/remote-mcp-server")

from remote_mcp_server.mcp_server import (
    calculate_sum,
    echo_message,
    get_current_time,
    get_server_info,
    hello_world,
    mcp,
)


def test_mcp_tools():
    """Test all MCP tools directly."""

    print("🔍 Testing Remote MCP Server Tools...")
    print("=" * 50)

    test_cases = [
        {
            "name": "hello_world",
            "func": hello_world,
            "args": ("Claude Code User",),
            "kwargs": {},
        },
        {
            "name": "get_current_time",
            "func": get_current_time,
            "args": (),
            "kwargs": {},
        },
        {
            "name": "echo_message",
            "func": echo_message,
            "args": ("Testing MCP integration!", 2),
            "kwargs": {},
        },
        {"name": "get_server_info", "func": get_server_info, "args": (), "kwargs": {}},
        {
            "name": "calculate_sum",
            "func": calculate_sum,
            "args": ([10, 20, 30, 15, 25],),
            "kwargs": {},
        },
    ]

    print("🧪 Testing MCP tools:")
    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        try:
            print(f"  {i}. Testing {test_case['name']}...")
            result = test_case["func"](*test_case["args"], **test_case["kwargs"])

            # Format result for display
            result_str = str(result)
            if len(result_str) > 100:
                result_str = result_str[:97] + "..."

            print(f"     ✅ Result: {result_str}")
            success_count += 1

        except Exception as e:
            print(f"     ❌ Exception: {e}")

    print()
    print(f"📊 Results: {success_count}/{len(test_cases)} tools passed")

    # Test MCP server metadata
    try:
        print(
            f"🔧 MCP Server tools count: {len(mcp._tools) if hasattr(mcp, '_tools') else 'Unknown'}"
        )
        print(f"🏷️  MCP Server name: {mcp.name}")
        print(f"📝 MCP Server instructions: {mcp.instructions[:100]}...")

    except Exception as e:
        print(f"⚠️  Could not get MCP server metadata: {e}")

    print()

    if success_count == len(test_cases):
        print("🎉 All MCP tools are working correctly!")
        print("✅ The Remote MCP Server is ready to use with Claude Code.")
        return True
    else:
        print(f"❌ {len(test_cases) - success_count} tools failed.")
        return False


if __name__ == "__main__":
    try:
        success = test_mcp_tools()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
