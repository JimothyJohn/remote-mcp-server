"""AWS Lambda handler entry point for Remote MCP Server."""

# Import the Lambda handler from our package
from remote_mcp_server.app import lambda_handler

# Re-export for AWS Lambda
__all__ = ["lambda_handler"]