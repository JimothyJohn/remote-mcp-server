"""AWS Lambda handler - imports from the new MCP server."""

# Import the Lambda handler from our server module
from remote_mcp_server.server import lambda_handler

# Re-export for backward compatibility
__all__ = ["lambda_handler"]
