"""Main MCP Server implementation."""

import argparse
import logging
from typing import Any

from mcp.server import FastMCP

from .aws_lambda import LambdaHandler
from .config import ServerConfig
from .tools import register_tools


def setup_logging(log_level: str) -> None:
    """Setup basic logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def create_mcp_server(config: ServerConfig) -> FastMCP:
    """Create and configure MCP server."""
    mcp = FastMCP(
        "remote-mcp-server",
        instructions="A simple MCP server demonstrating basic operations and AWS Lambda compatibility.",
    )
    
    # Register all tools
    register_tools(mcp, config)
    
    return mcp


def create_lambda_handler(config: ServerConfig | None = None) -> Any:
    """Create AWS Lambda handler."""
    if config is None:
        config = ServerConfig.from_env()
        
    handler = LambdaHandler(config)
    return handler


def main() -> None:
    """Main entry point for MCP server."""
    parser = argparse.ArgumentParser(
        description="Remote MCP Server - A simple MCP server with AWS Lambda compatibility"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to run the server on (default: 3000)",
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = ServerConfig(
        port=args.port,
        log_level=args.log_level,  # type: ignore
    )
    
    # Setup logging
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting Remote MCP Server v{config.version}")
    logger.info(f"Server will run on port {config.port}")
    
    # Create and run MCP server
    mcp = create_mcp_server(config)
    mcp.run()


# Create default lambda handler for AWS
lambda_handler = create_lambda_handler()

if __name__ == "__main__":
    main()