"""AWS Lambda handler - imports from the new MCP server."""

# Import the Lambda handler from our MCP server
from remote_mcp_server.mcp_server import lambda_handler

# Re-export for backward compatibility
__all__ = ["lambda_handler"]
