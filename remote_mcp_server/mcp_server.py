"""MCP Server implementation for Remote MCP Server."""

import argparse
import asyncio
import datetime
import json
import logging
import os
import sys
import time
from typing import Any

from mcp.server import FastMCP
from pydantic import BaseModel, Field

from remote_mcp_server import __version__
from remote_mcp_server.logging_config import (
    clear_request_context,
    create_logger,
    log_aws_lambda_context,
    log_function_entry_exit,
    log_http_request,
    log_http_response,
    log_mcp_tool_execution,
    performance_logger,
    set_request_context,
    setup_logging,
)

# Configure comprehensive logging
setup_logging()
logger = create_logger(__name__)
mcp_logger = create_logger("mcp.server")
lambda_logger = create_logger("aws.lambda")
tools_logger = create_logger("mcp.tools")

# Create MCP server instance
mcp = FastMCP(
    "remote-mcp-server",
    instructions="A simple MCP server demonstrating basic operations and AWS Lambda compatibility.",
)


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str = Field(description="Service status")
    timestamp: str = Field(description="Current timestamp")
    version: str = Field(description="Service version")


@mcp.tool()
@log_function_entry_exit(logger=tools_logger, log_args=True, log_result=True)
def hello_world(name: str = "World") -> str:
    """Say hello to someone.

    Args:
        name: The name to greet (defaults to "World")

    Returns:
        A greeting message
    """
    try:
        tools_logger.info(
            "Executing hello_world tool",
            extra={
                "tool_name": "hello_world",
                "input_name": name,
                "action": "tool_start",
            },
        )

        # Input validation and sanitization
        if not isinstance(name, str):
            name = str(name)
            tools_logger.warning(
                "Non-string name provided, converted to string",
                extra={"original_type": type(name).__name__, "converted_name": name},
            )

        # Limit name length for security
        if len(name) > 100:
            name = name[:100]
            tools_logger.warning(
                "Name truncated to 100 characters for security",
                extra={"truncated_name": name},
            )

        message = f"Hello, {name}! Welcome to Remote MCP Server."

        tools_logger.info(
            "Hello world message generated",
            extra={
                "tool_name": "hello_world",
                "tool_result": message,
                "message_length": len(message),
                "action": "tool_success",
            },
        )

        log_mcp_tool_execution("hello_world", {"name": name}, result=message)
        return message

    except Exception as e:
        tools_logger.error(
            f"Hello world tool failed: {e}",
            extra={
                "tool_name": "hello_world",
                "input_name": name,
                "error_type": type(e).__name__,
                "action": "tool_error",
            },
            exc_info=True,
        )
        log_mcp_tool_execution("hello_world", {"name": name}, error=e)
        raise


@mcp.tool()
@log_function_entry_exit(logger=tools_logger, log_result=True)
def get_current_time() -> str:
    """Get the current timestamp.

    Returns:
        ISO formatted current timestamp
    """
    try:
        start_time = time.time()
        tools_logger.info(
            "Executing get_current_time tool",
            extra={"tool_name": "get_current_time", "action": "tool_start"},
        )

        timestamp = datetime.datetime.now().isoformat()
        generation_time = time.time() - start_time

        tools_logger.info(
            "Timestamp generated",
            extra={
                "tool_name": "get_current_time",
                "timestamp": timestamp,
                "generation_time_ms": round(generation_time * 1000, 3),
                "timezone": "local",
                "action": "tool_success",
            },
        )

        log_mcp_tool_execution("get_current_time", {}, result=timestamp)
        performance_logger.log_timing("get_current_time", generation_time)

        return timestamp

    except Exception as e:
        tools_logger.error(
            f"Get current time tool failed: {e}",
            extra={
                "tool_name": "get_current_time",
                "error_type": type(e).__name__,
                "action": "tool_error",
            },
            exc_info=True,
        )
        log_mcp_tool_execution("get_current_time", {}, error=e)
        raise


@mcp.tool()
@log_function_entry_exit(logger=tools_logger, log_args=True, log_result=True)
def echo_message(message: str, repeat: int = 1) -> str:
    """Echo a message back, optionally repeated.

    Args:
        message: The message to echo
        repeat: Number of times to repeat (default: 1, max: 10)

    Returns:
        The echoed message(s)
    """
    try:
        tools_logger.info(
            "Executing echo_message tool",
            extra={
                "tool_name": "echo_message",
                "message_length": len(message) if message else 0,
                "repeat_count": repeat,
                "action": "tool_start",
            },
        )

        # Input validation
        if not isinstance(message, str):
            message = str(message)
            tools_logger.warning(
                "Non-string message provided, converted to string",
                extra={"original_type": type(message).__name__},
            )

        if not isinstance(repeat, int):
            try:
                repeat = int(repeat)
                tools_logger.warning(
                    "Non-integer repeat count provided, converted to int",
                    extra={"original_value": repeat, "converted_value": int(repeat)},
                )
            except (ValueError, TypeError):
                repeat = 1
                tools_logger.warning(
                    "Invalid repeat count, defaulting to 1",
                    extra={"original_value": repeat},
                )

        if repeat < 1 or repeat > 10:
            tools_logger.error(
                "Invalid repeat count",
                extra={
                    "tool_name": "echo_message",
                    "repeat_count": repeat,
                    "valid_range": "1-10",
                    "action": "validation_error",
                },
            )
            error = ValueError("Repeat count must be between 1 and 10")
            log_mcp_tool_execution(
                "echo_message", {"message": message, "repeat": repeat}, error=error
            )
            raise error

        # Security: limit message length
        if len(message) > 1000:
            message = message[:1000]
            tools_logger.warning(
                "Message truncated to 1000 characters for security",
                extra={"truncated_length": 1000},
            )

        start_time = time.time()
        result = " ".join([message] * repeat)
        processing_time = time.time() - start_time

        tools_logger.info(
            "Echo message processed",
            extra={
                "tool_name": "echo_message",
                "original_message": (
                    message[:50] + "..." if len(message) > 50 else message
                ),
                "repeat_count": repeat,
                "result_length": len(result),
                "processing_time_ms": round(processing_time * 1000, 3),
                "action": "tool_success",
            },
        )

        log_mcp_tool_execution(
            "echo_message", {"message": message, "repeat": repeat}, result=result
        )
        performance_logger.log_timing(
            "echo_message",
            processing_time,
            repeat_count=repeat,
            message_length=len(message),
        )

        return result

    except Exception as e:
        tools_logger.error(
            f"Echo message tool failed: {e}",
            extra={
                "tool_name": "echo_message",
                "message_length": len(message) if message else 0,
                "repeat_count": repeat,
                "error_type": type(e).__name__,
                "action": "tool_error",
            },
            exc_info=True,
        )
        log_mcp_tool_execution(
            "echo_message", {"message": message, "repeat": repeat}, error=e
        )
        raise


@mcp.tool()
@log_function_entry_exit(logger=tools_logger, log_result=True)
def get_server_info() -> dict[str, Any]:
    """Get server information and status.

    Returns:
        Dictionary containing server status and metadata
    """
    try:
        start_time = time.time()
        tools_logger.info(
            "Executing get_server_info tool",
            extra={"tool_name": "get_server_info", "action": "tool_start"},
        )

        # Gather system information
        environment = os.environ.get("ENVIRONMENT", "development")
        tools_count = len(mcp._tools) if hasattr(mcp, "_tools") else 0
        current_time = datetime.datetime.now().isoformat()

        # System resource information (if available)
        system_info = {}
        try:
            import psutil

            memory = psutil.virtual_memory()
            system_info.update(
                {
                    "memory_percent": round(memory.percent, 1),
                    "memory_available_mb": round(memory.available / 1024 / 1024, 1),
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                }
            )
        except ImportError:
            tools_logger.debug("psutil not available, skipping system metrics")
        except Exception as e:
            tools_logger.warning(f"Failed to gather system info: {e}")

        info = {
            "service": "remote-mcp-server",
            "version": __version__,
            "status": "healthy",
            "timestamp": current_time,
            "environment": environment,
            "tools_available": tools_count,
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            **system_info,
        }

        processing_time = time.time() - start_time

        tools_logger.info(
            "Server info collected",
            extra={
                "tool_name": "get_server_info",
                "environment": environment,
                "tools_count": tools_count,
                "processing_time_ms": round(processing_time * 1000, 3),
                "system_metrics_included": bool(system_info),
                "action": "tool_success",
            },
        )

        log_mcp_tool_execution("get_server_info", {}, result=info)
        performance_logger.log_timing("get_server_info", processing_time)

        return info

    except Exception as e:
        tools_logger.error(
            f"Get server info tool failed: {e}",
            extra={
                "tool_name": "get_server_info",
                "error_type": type(e).__name__,
                "action": "tool_error",
            },
            exc_info=True,
        )
        log_mcp_tool_execution("get_server_info", {}, error=e)
        raise


@mcp.tool()
@log_function_entry_exit(logger=tools_logger, log_args=True, log_result=True)
def calculate_sum(numbers: list[float]) -> float:
    """Calculate the sum of a list of numbers.

    Args:
        numbers: List of numbers to sum

    Returns:
        The sum of all numbers
    """
    try:
        start_time = time.time()
        tools_logger.info(
            "Executing calculate_sum tool",
            extra={
                "tool_name": "calculate_sum",
                "input_count": len(numbers) if numbers else 0,
                "action": "tool_start",
            },
        )

        # Input validation
        if not isinstance(numbers, (list, tuple)):
            tools_logger.error(
                "Invalid input type for numbers",
                extra={
                    "tool_name": "calculate_sum",
                    "input_type": type(numbers).__name__,
                    "expected_type": "list or tuple",
                    "action": "validation_error",
                },
            )
            error = TypeError(f"Expected list or tuple, got {type(numbers).__name__}")
            log_mcp_tool_execution("calculate_sum", {"numbers": numbers}, error=error)
            raise error

        if not numbers:
            tools_logger.info(
                "Empty list provided, returning 0.0",
                extra={"tool_name": "calculate_sum", "action": "empty_input"},
            )
            log_mcp_tool_execution("calculate_sum", {"numbers": numbers}, result=0.0)
            return 0.0

        if len(numbers) > 100:
            tools_logger.error(
                "Too many numbers provided",
                extra={
                    "tool_name": "calculate_sum",
                    "input_count": len(numbers),
                    "max_allowed": 100,
                    "action": "validation_error",
                },
            )
            error = ValueError("Maximum 100 numbers allowed")
            log_mcp_tool_execution("calculate_sum", {"numbers": numbers}, error=error)
            raise error

        # Validate and convert numbers
        validated_numbers = []
        conversion_warnings = []

        for i, num in enumerate(numbers):
            try:
                if isinstance(num, (int, float)):
                    validated_numbers.append(float(num))
                elif isinstance(num, str):
                    converted = float(num)
                    validated_numbers.append(converted)
                    conversion_warnings.append(f"index {i}: '{num}' -> {converted}")
                else:
                    converted = float(num)
                    validated_numbers.append(converted)
                    conversion_warnings.append(
                        f"index {i}: {type(num).__name__} -> {converted}"
                    )
            except (ValueError, TypeError) as e:
                tools_logger.error(
                    f"Invalid number at index {i}",
                    extra={
                        "tool_name": "calculate_sum",
                        "invalid_index": i,
                        "invalid_value": str(num),
                        "error": str(e),
                        "action": "validation_error",
                    },
                )
                error = ValueError(f"Invalid number at index {i}: {num}")
                log_mcp_tool_execution(
                    "calculate_sum", {"numbers": numbers}, error=error
                )
                raise error

        if conversion_warnings:
            tools_logger.warning(
                "Some values were converted to numbers",
                extra={
                    "tool_name": "calculate_sum",
                    "conversions": conversion_warnings[:5],  # Limit to first 5
                    "total_conversions": len(conversion_warnings),
                },
            )

        # Perform calculation
        result = sum(validated_numbers)
        processing_time = time.time() - start_time

        # Statistical information
        stats = {
            "count": len(validated_numbers),
            "sum": result,
            "average": result / len(validated_numbers),
            "min": min(validated_numbers),
            "max": max(validated_numbers),
        }

        tools_logger.info(
            "Sum calculation completed",
            extra={
                "tool_name": "calculate_sum",
                "input_count": len(validated_numbers),
                "result": result,
                "processing_time_ms": round(processing_time * 1000, 3),
                "statistics": stats,
                "conversions_performed": len(conversion_warnings),
                "action": "tool_success",
            },
        )

        log_mcp_tool_execution("calculate_sum", {"numbers": numbers}, result=result)
        performance_logger.log_timing(
            "calculate_sum", processing_time, number_count=len(validated_numbers)
        )

        return result

    except Exception as e:
        tools_logger.error(
            f"Calculate sum tool failed: {e}",
            extra={
                "tool_name": "calculate_sum",
                "input_count": len(numbers) if numbers else 0,
                "error_type": type(e).__name__,
                "action": "tool_error",
            },
            exc_info=True,
        )
        log_mcp_tool_execution("calculate_sum", {"numbers": numbers}, error=e)
        raise


@log_function_entry_exit(logger=mcp_logger, log_args=True, log_result=True)
async def handle_mcp_request(request_data: dict[str, Any]) -> dict[str, Any]:
    """Handle MCP request (for Lambda integration).

    Args:
        request_data: MCP request data

    Returns:
        MCP response data
    """
    request_id = request_data.get("id", "unknown")
    method = request_data.get("method", "unknown")

    try:
        start_time = time.time()
        mcp_logger.info(
            "Processing MCP request",
            extra={
                "request_id": request_id,
                "method": method,
                "jsonrpc": request_data.get("jsonrpc"),
                "has_params": "params" in request_data,
                "action": "mcp_request_start",
            },
        )

        # Validate JSON-RPC structure
        if request_data.get("jsonrpc") != "2.0":
            mcp_logger.warning(
                "Invalid or missing JSON-RPC version",
                extra={
                    "request_id": request_id,
                    "jsonrpc_version": request_data.get("jsonrpc"),
                    "expected": "2.0",
                },
            )

        # Log method-specific information
        if method == "tools/call":
            params = request_data.get("params", {})
            tool_name = params.get("name", "unknown")
            mcp_logger.info(
                "Tool call request",
                extra={
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "has_arguments": "arguments" in params,
                    "action": "tool_call_request",
                },
            )
        elif method == "tools/list":
            mcp_logger.info(
                "Tools list request",
                extra={"request_id": request_id, "action": "tools_list_request"},
            )

        # This would be implemented based on the MCP protocol
        # For now, return a simple response
        response = {
            "jsonrpc": "2.0",
            "result": {
                "status": "success",
                "message": "MCP request processed successfully",
            },
            "id": request_id,
        }

        processing_time = time.time() - start_time

        mcp_logger.info(
            "MCP request processed successfully",
            extra={
                "request_id": request_id,
                "method": method,
                "processing_time_ms": round(processing_time * 1000, 3),
                "action": "mcp_request_success",
            },
        )

        performance_logger.log_timing(f"mcp_request_{method}", processing_time)
        return response

    except Exception as e:
        processing_time = time.time() - start_time if "start_time" in locals() else 0

        mcp_logger.error(
            f"Error handling MCP request: {e}",
            extra={
                "request_id": request_id,
                "method": method,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "processing_time_ms": round(processing_time * 1000, 3),
                "action": "mcp_request_error",
            },
            exc_info=True,
        )

        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}",
                "data": {"error_type": type(e).__name__, "request_id": request_id},
            },
            "id": request_id,
        }


def create_lambda_handler():
    """Create Lambda handler function."""

    @log_function_entry_exit(logger=lambda_logger, log_duration=True)
    def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
        """AWS Lambda handler for HTTP requests.

        Args:
            event: Lambda event data
            context: Lambda context

        Returns:
            HTTP response
        """
        start_time = time.time()
        request_id = None

        try:
            # Set up request context and logging
            if hasattr(context, "aws_request_id"):
                request_id = context.aws_request_id
                log_aws_lambda_context(context)
            else:
                request_id = set_request_context()

            lambda_logger.info(
                "Lambda function invoked",
                extra={
                    "event_keys": list(event.keys()),
                    "context_type": type(context).__name__,
                    "cold_start": not hasattr(lambda_handler, "_warm"),
                    "action": "lambda_start",
                },
            )

            # Mark as warm for subsequent requests
            lambda_handler._warm = True

            # Log event details (sanitized)
            event_info = {
                "event_type": "unknown",
                "source": event.get("source"),
                "event_size": len(json.dumps(event, default=str)),
            }

            if "httpMethod" in event:
                event_info["event_type"] = "api_gateway"
                event_info["method"] = event.get("httpMethod")
                event_info["path"] = event.get("path")
                event_info["source_ip"] = (
                    event.get("requestContext", {}).get("identity", {}).get("sourceIp")
                )

                # Log HTTP request details
                log_http_request(
                    method=event.get("httpMethod", "UNKNOWN"),
                    path=event.get("path", "/"),
                    headers=event.get("headers", {}),
                    body=event.get("body"),
                )
            elif "Records" in event:
                event_info["event_type"] = "eventbridge_sqs_sns"
                event_info["record_count"] = len(event["Records"])
            elif "method" in event:
                event_info["event_type"] = "direct_mcp"
                event_info["method"] = event.get("method")

            lambda_logger.info("Event analysis", extra=event_info)

            # Process the request
            response = _process_lambda_event(event, context, start_time)

            processing_time = time.time() - start_time

            # Log response details
            status_code = response.get("statusCode", 200)
            log_http_response(
                status_code=status_code,
                response_body=response.get("body"),
                duration=processing_time,
            )

            lambda_logger.info(
                "Lambda processing completed",
                extra={
                    "status_code": status_code,
                    "processing_time_ms": round(processing_time * 1000, 3),
                    "response_size": len(json.dumps(response, default=str)),
                    "action": "lambda_success",
                },
            )

            performance_logger.log_timing(
                "lambda_request", processing_time, status_code=status_code
            )

            return response

        except Exception as e:
            processing_time = time.time() - start_time

            lambda_logger.error(
                f"Lambda handler error: {e}",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "processing_time_ms": round(processing_time * 1000, 3),
                    "action": "lambda_error",
                },
                exc_info=True,
            )

            error_response = {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "error": "Internal server error",
                        "message": str(e),
                        "request_id": request_id,
                        "timestamp": datetime.datetime.now().isoformat(),
                    }
                ),
            }

            log_http_response(500, error_response.get("body"), processing_time)
            return error_response

        finally:
            clear_request_context()

    def _process_lambda_event(
        event: dict[str, Any], context: Any, start_time: float
    ) -> dict[str, Any]:
        """Process different types of Lambda events."""

        # Handle different event types
        if "httpMethod" in event:
            # API Gateway event
            path = event.get("path", "/")
            method = event.get("httpMethod", "GET")

            if path == "/health" and method == "GET":
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "status": "healthy",
                            "service": "remote-mcp-server",
                            "version": __version__,
                            "timestamp": datetime.datetime.now().isoformat(),
                        }
                    ),
                }

            # Handle POST requests with data
            elif method == "POST":
                try:
                    # Parse request body
                    body_data = {}
                    if event.get("body"):
                        if event.get("isBase64Encoded"):
                            import base64

                            body = base64.b64decode(event["body"]).decode("utf-8")
                        else:
                            body = event["body"]

                        # Try to parse as JSON
                        try:
                            body_data = json.loads(body)
                        except json.JSONDecodeError:
                            body_data = {"raw_body": body}

                    # Process the POST request
                    response_data = {
                        "message": "POST request received",
                        "service": "remote-mcp-server",
                        "version": __version__,
                        "timestamp": datetime.datetime.now().isoformat(),
                        "received_data": body_data,
                        "path": path,
                        "method": method,
                    }

                    # If this looks like an MCP request, handle it appropriately
                    if "jsonrpc" in body_data and "method" in body_data:
                        logger.info("Received MCP request via POST")
                        mcp_response = asyncio.run(handle_mcp_request(body_data))
                        return {
                            "statusCode": 200,
                            "headers": {"Content-Type": "application/json"},
                            "body": json.dumps(mcp_response),
                        }

                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(response_data),
                    }

                except Exception as e:
                    logger.error(f"Error processing POST request: {e}")
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(
                            {
                                "error": "Bad Request",
                                "message": f"Error processing POST data: {str(e)}",
                                "timestamp": datetime.datetime.now().isoformat(),
                            }
                        ),
                    }

            # Default GET response (keeping original functionality)
            else:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "message": "remote-mcp-server",
                            "version": __version__,
                            "timestamp": datetime.datetime.now().isoformat(),
                            "method": method,
                            "path": path,
                        }
                    ),
                }

        # Handle MCP requests
        elif "method" in event:
            # This looks like an MCP request
            response = asyncio.run(handle_mcp_request(event))
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(response),
            }

        # Default fallback
        else:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"message": "remote-mcp-server", "version": __version__}
                ),
            }

    return lambda_handler


def main():
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

    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    logger.info(f"Starting Remote MCP Server v{__version__}")
    logger.info(f"Server will run on port {args.port}")

    # Run the MCP server
    mcp.run()


# Create lambda handler instance
lambda_handler = create_lambda_handler()

if __name__ == "__main__":
    main()
