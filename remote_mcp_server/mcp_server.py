"""Legacy MCP Server entry point for backward compatibility."""

# Re-export the main functionality from the new modular structure
from .config import ServerConfig
from .server import create_lambda_handler, create_mcp_server, main, lambda_handler

# Backward compatibility: Create default MCP server instance
_config = ServerConfig()
mcp = create_mcp_server(_config)

# Re-export for backward compatibility
__all__ = [
    "mcp",
    "main",
    "create_mcp_server", 
    "create_lambda_handler",
    "lambda_handler",
    "ServerConfig",
]