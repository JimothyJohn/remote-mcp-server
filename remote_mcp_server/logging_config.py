"""Comprehensive logging configuration for Remote MCP Server.

This module provides structured logging capabilities for troubleshooting,
monitoring, and performance analysis across all components.
"""

import functools
import json
import logging
import logging.config
import os
import sys
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

# Type definitions
F = TypeVar("F", bound=Callable[..., Any])

# Global request context for correlation
_request_context: dict[str, Any] = {}


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if _request_context:
            log_entry["request"] = _request_context.copy()

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from the log record
        if self.include_extra_fields:
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                }:
                    try:
                        # Sanitize sensitive data
                        sanitized_value = _sanitize_value(key, value)
                        # Ensure value is JSON serializable
                        json.dumps(sanitized_value)
                        log_entry[key] = sanitized_value
                    except (TypeError, ValueError):
                        log_entry[key] = str(value)

        return json.dumps(log_entry, default=str, separators=(",", ":"))


class PerformanceLogger:
    """Logger for performance metrics and timing information."""

    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)

    def log_timing(self, operation: str, duration: float, **kwargs):
        """Log performance timing information."""
        self.logger.info(
            f"Performance: {operation} completed",
            extra={
                "operation": operation,
                "duration_ms": round(duration * 1000, 2),
                "duration_seconds": round(duration, 3),
                **kwargs,
            },
        )

    def log_memory_usage(self, operation: str, memory_mb: float, **kwargs):
        """Log memory usage information."""
        self.logger.info(
            f"Memory: {operation}",
            extra={"operation": operation, "memory_mb": round(memory_mb, 2), **kwargs},
        )


def setup_logging(
    log_level: str = None,
    enable_structured_logging: bool = True,
    enable_performance_logging: bool = True,
    log_file: str = None,
) -> None:
    """Configure comprehensive logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_structured_logging: Enable JSON structured logging
        enable_performance_logging: Enable performance metrics logging
        log_file: Optional file path for logging output
    """
    # Determine log level
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Validate log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    if enable_structured_logging:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure specific loggers
    logging.getLogger("remote_mcp_server").setLevel(numeric_level)

    if enable_performance_logging:
        logging.getLogger("performance").setLevel(logging.INFO)

    # Reduce noise from third-party libraries
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "structured_logging": enable_structured_logging,
            "performance_logging": enable_performance_logging,
            "log_file": log_file,
            "environment": os.getenv("ENVIRONMENT", "development"),
        },
    )


def set_request_context(
    request_id: str = None, user_id: str = None, session_id: str = None, **kwargs
) -> str:
    """Set request context for correlation across logs.

    Args:
        request_id: Unique request identifier
        user_id: User identifier
        session_id: Session identifier
        **kwargs: Additional context fields

    Returns:
        The request ID (generated if not provided)
    """
    global _request_context

    if request_id is None:
        request_id = str(uuid.uuid4())

    _request_context = {
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if user_id:
        _request_context["user_id"] = user_id
    if session_id:
        _request_context["session_id"] = session_id

    # Add any additional context
    for key, value in kwargs.items():
        _request_context[key] = value

    logger = logging.getLogger(__name__)
    logger.debug("Request context set", extra={"context": _request_context})

    return request_id


def clear_request_context():
    """Clear the current request context."""
    global _request_context
    _request_context.clear()


def get_request_context() -> dict[str, Any]:
    """Get the current request context."""
    return _request_context.copy()


def log_function_entry_exit(
    logger: logging.Logger = None,
    log_args: bool = True,
    log_result: bool = True,
    log_duration: bool = True,
):
    """Decorator to log function entry, exit, and performance.

    Args:
        logger: Logger instance to use (creates one if None)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        log_duration: Whether to log execution duration
    """

    def decorator(func: F) -> F:
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Log function entry
            entry_extra = {
                "function": func.__name__,
                "source_module": func.__module__,
                "action": "entry",
            }

            if log_args:
                # Sanitize arguments (avoid logging sensitive data)
                safe_args = _sanitize_args(args)
                safe_kwargs = _sanitize_kwargs(kwargs)
                entry_extra["function_args"] = safe_args
                entry_extra["function_kwargs"] = safe_kwargs

            logger.debug(f"Entering function {func.__name__}", extra=entry_extra)

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Log successful exit
                duration = time.time() - start_time
                exit_extra = {
                    "function": func.__name__,
                    "source_module": func.__module__,
                    "action": "exit",
                    "status": "success",
                }

                if log_duration:
                    exit_extra["duration_ms"] = round(duration * 1000, 2)

                if log_result and result is not None:
                    exit_extra["result_type"] = type(result).__name__
                    if isinstance(result, (str, int, float, bool, list, dict)):
                        try:
                            # Limit result size in logs
                            result_str = str(result)
                            if len(result_str) <= 200:
                                exit_extra["result"] = result
                            else:
                                exit_extra["result_preview"] = result_str[:200] + "..."
                        except Exception:
                            exit_extra["result_type"] = type(result).__name__

                logger.debug(f"Exiting function {func.__name__}", extra=exit_extra)

                # Log performance if duration is significant
                if log_duration and duration > 0.1:  # Log if > 100ms
                    perf_logger = PerformanceLogger()
                    perf_logger.log_timing(
                        f"{func.__module__}.{func.__name__}",
                        duration,
                        function=func.__name__,
                        module=func.__module__,
                    )

                return result

            except Exception as e:
                # Log exception exit
                duration = time.time() - start_time
                error_extra = {
                    "function": func.__name__,
                    "source_module": func.__module__,
                    "action": "exit",
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

                if log_duration:
                    error_extra["duration_ms"] = round(duration * 1000, 2)

                logger.error(
                    f"Function {func.__name__} failed: {e}",
                    extra=error_extra,
                    exc_info=True,
                )

                raise

        return wrapper

    return decorator


def log_aws_lambda_context(context):
    """Log AWS Lambda context information."""
    logger = logging.getLogger("aws.lambda")

    if hasattr(context, "aws_request_id"):
        context_info = {
            "aws_request_id": context.aws_request_id,
            "function_name": context.function_name,
            "function_version": context.function_version,
            "memory_limit_mb": context.memory_limit_in_mb,
            "remaining_time_ms": context.get_remaining_time_in_millis(),
            "log_group_name": getattr(context, "log_group_name", None),
            "log_stream_name": getattr(context, "log_stream_name", None),
        }

        # Set as request context
        set_request_context(
            request_id=context.aws_request_id,
            lambda_function=context.function_name,
            lambda_version=context.function_version,
            **context_info,
        )

        logger.info("AWS Lambda context", extra=context_info)


def log_mcp_tool_execution(
    tool_name: str,
    arguments: dict[str, Any],
    result: Any = None,
    error: Exception = None,
):
    """Log MCP tool execution with detailed context."""
    logger = logging.getLogger("mcp.tools")

    tool_context = {
        "tool_name": tool_name,
        "arguments": _sanitize_kwargs(arguments),
        "execution_context": "mcp_tool",
    }

    if error:
        logger.error(
            f"MCP tool {tool_name} failed: {error}",
            extra={
                **tool_context,
                "status": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            exc_info=True,
        )
    else:
        result_info = {}
        if result is not None:
            result_info["result_type"] = type(result).__name__
            if isinstance(result, (str, int, float, bool)):
                result_info["result"] = result
            elif isinstance(result, (list, dict)):
                result_str = str(result)
                if len(result_str) <= 100:
                    result_info["result"] = result
                else:
                    result_info["result_size"] = len(result_str)

        logger.info(
            f"MCP tool {tool_name} executed successfully",
            extra={**tool_context, "status": "success", **result_info},
        )


def log_http_request(
    method: str, path: str, headers: dict[str, Any] = None, body: Any = None
):
    """Log incoming HTTP request details."""
    logger = logging.getLogger("http.request")

    request_info = {"method": method, "path": path, "request_type": "http"}

    if headers:
        # Log only non-sensitive headers
        safe_headers = {
            k: v
            for k, v in headers.items()
            if k.lower() not in {"authorization", "cookie", "x-api-key"}
        }
        request_info["headers"] = safe_headers
        request_info["content_type"] = headers.get("content-type")
        request_info["user_agent"] = headers.get("user-agent")

    if body:
        if isinstance(body, str) and len(body) <= 500:
            try:
                # Try to parse as JSON for better logging
                parsed_body = json.loads(body)
                request_info["body"] = parsed_body
            except (json.JSONDecodeError, TypeError):
                request_info["body"] = body
        else:
            request_info["body_size"] = len(str(body))
            request_info["body_type"] = type(body).__name__

    logger.info(f"HTTP {method} {path}", extra=request_info)


def log_http_response(
    status_code: int, response_body: Any = None, duration: float = None
):
    """Log HTTP response details."""
    logger = logging.getLogger("http.response")

    response_info = {
        "status_code": status_code,
        "status_category": f"{status_code // 100}xx",
        "response_type": "http",
    }

    if duration is not None:
        response_info["duration_ms"] = round(duration * 1000, 2)

    if response_body:
        if (
            isinstance(response_body, (str, dict, list))
            and len(str(response_body)) <= 200
        ):
            response_info["response_body"] = response_body
        else:
            response_info["response_size"] = len(str(response_body))
            response_info["response_type"] = type(response_body).__name__

    level = (
        logging.INFO
        if status_code < 400
        else logging.WARNING if status_code < 500 else logging.ERROR
    )

    logger.log(level, f"HTTP response {status_code}", extra=response_info)


def _sanitize_args(args: tuple) -> list:
    """Sanitize function arguments for logging (remove sensitive data)."""
    sanitized = []
    for arg in args:
        if isinstance(arg, (str, int, float, bool, type(None))):
            sanitized.append(arg)
        elif isinstance(arg, (list, tuple)):
            if len(arg) <= 10:  # Limit size
                sanitized.append(list(arg))
            else:
                sanitized.append(f"<{type(arg).__name__}[{len(arg)}]>")
        elif isinstance(arg, dict):
            if len(arg) <= 10:  # Limit size
                sanitized.append(_sanitize_dict(arg))
            else:
                sanitized.append(f"<dict[{len(arg)}]>")
        else:
            sanitized.append(f"<{type(arg).__name__}>")
    return sanitized


def _sanitize_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Sanitize keyword arguments for logging."""
    if not isinstance(kwargs, dict):
        return {"value": str(kwargs), "type": type(kwargs).__name__}

    return _sanitize_dict(kwargs)


def _sanitize_value(key: str, value: Any) -> Any:
    """Sanitize a single key-value pair for logging."""
    sensitive_keys = {
        "password",
        "token",
        "key",
        "secret",
        "authorization",
        "cookie",
        "session",
        "credential",
        "auth",
        "api_key",
    }

    key_lower = str(key).lower()

    # Check if key contains sensitive information
    if any(sensitive in key_lower for sensitive in sensitive_keys):
        return "<REDACTED>"

    # If value is a dict, sanitize it recursively
    if isinstance(value, dict):
        return _sanitize_dict(value)

    return value


def _sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize dictionary data for logging."""
    sanitized = {}
    sensitive_keys = {
        "password",
        "token",
        "key",
        "secret",
        "authorization",
        "cookie",
        "session",
        "credential",
        "auth",
    }

    for key, value in data.items():
        key_lower = str(key).lower()

        # Check if key contains sensitive information
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "<REDACTED>"
        elif isinstance(value, (str, int, float, bool, type(None))):
            sanitized[key] = value
        elif isinstance(value, (list, tuple)):
            if len(value) <= 5:
                sanitized[key] = list(value)
            else:
                sanitized[key] = f"<{type(value).__name__}[{len(value)}]>"
        elif isinstance(value, dict):
            if len(value) <= 5:
                sanitized[key] = _sanitize_dict(value)
            else:
                sanitized[key] = f"<dict[{len(value)}]>"
        else:
            sanitized[key] = f"<{type(value).__name__}>"

    return sanitized


def create_logger(name: str) -> logging.Logger:
    """Create a logger with the given name and proper configuration."""
    return logging.getLogger(name)


# Global performance logger instance
performance_logger = PerformanceLogger()

# Initialize logging on module import
setup_logging()
