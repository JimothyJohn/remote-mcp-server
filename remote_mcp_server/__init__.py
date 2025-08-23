"""Remote MCP Server package."""

from .config import ServerConfig
from .server import create_lambda_handler, create_mcp_server, main

__version__ = "1.0.0"
__author__ = "Nick Armenta"
__description__ = "A Model Context Protocol server with AWS Lambda compatibility"

__all__ = [
    "ServerConfig",
    "create_lambda_handler", 
    "create_mcp_server",
    "main",
]
