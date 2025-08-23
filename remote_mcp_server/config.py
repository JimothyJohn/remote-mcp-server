"""Configuration management for Remote MCP Server."""

import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration settings."""

    # Server settings
    port: int = 3000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    # Environment
    environment: str = "development"
    version: str = "1.0.0"
    
    # AWS Lambda settings
    memory_limit: int = 256
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create configuration from environment variables."""
        return cls(
            port=int(os.environ.get("PORT", "3000")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),  # type: ignore
            environment=os.environ.get("ENVIRONMENT", "development"),
            version=os.environ.get("VERSION", "1.0.0"),
            memory_limit=int(os.environ.get("MEMORY_LIMIT", "256")),
            timeout=int(os.environ.get("TIMEOUT", "30")),
        )