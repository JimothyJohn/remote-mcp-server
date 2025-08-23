"""MCP tools for Remote MCP Server."""

import datetime
import logging
from typing import Any

from mcp.server import FastMCP

from .config import ServerConfig

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, config: ServerConfig) -> None:
    """Register all MCP tools with the server."""
    
    @mcp.tool()
    def hello_world(name: str = "World") -> str:
        """Say hello to someone.

        Args:
            name: The name to greet (defaults to "World")

        Returns:
            A greeting message
        """
        # Basic input validation
        if not isinstance(name, str):
            name = str(name)
        
        # Limit length for security
        if len(name) > 100:
            name = name[:100]
            
        message = f"Hello, {name}! Welcome to Remote MCP Server."
        logger.info(f"Generated greeting for {name}")
        
        return message

    @mcp.tool()
    def get_current_time() -> str:
        """Get the current timestamp.

        Returns:
            ISO formatted current timestamp
        """
        timestamp = datetime.datetime.now().isoformat()
        logger.info("Generated current timestamp")
        
        return timestamp

    @mcp.tool()
    def echo_message(message: str, repeat: int = 1) -> str:
        """Echo a message back, optionally repeated.

        Args:
            message: The message to echo
            repeat: Number of times to repeat (default: 1, max: 10)

        Returns:
            The echoed message(s)
        """
        # Input validation
        if not isinstance(message, str):
            message = str(message)
            
        if not isinstance(repeat, int) or repeat < 1 or repeat > 10:
            raise ValueError("Repeat count must be between 1 and 10")
            
        # Limit message length for security
        if len(message) > 1000:
            message = message[:1000]
            
        result = " ".join([message] * repeat)
        logger.info(f"Echoed message {repeat} times")
        
        return result

    @mcp.tool()
    def get_server_info() -> dict[str, Any]:
        """Get server information and status.

        Returns:
            Dictionary containing server status and metadata
        """
        info = {
            "service": "remote-mcp-server",
            "version": config.version,
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "environment": config.environment,
        }
        
        # Add tools count if available
        if hasattr(mcp, "_tools"):
            info["tools_available"] = len(mcp._tools)
            
        logger.info("Generated server info")
        return info

    @mcp.tool()
    def calculate_sum(numbers: list[float]) -> float:
        """Calculate the sum of a list of numbers.

        Args:
            numbers: List of numbers to sum

        Returns:
            The sum of all numbers
        """
        # Input validation
        if not isinstance(numbers, (list, tuple)):
            raise TypeError(f"Expected list or tuple, got {type(numbers).__name__}")
            
        if not numbers:
            return 0.0
            
        if len(numbers) > 100:
            raise ValueError("Maximum 100 numbers allowed")

        # Convert all numbers to float
        try:
            validated_numbers = [float(num) for num in numbers]
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid number in list: {e}") from e

        result = sum(validated_numbers)
        logger.info(f"Calculated sum of {len(validated_numbers)} numbers")
        
        return result