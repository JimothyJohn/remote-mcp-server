"""AWS Lambda handler for Remote MCP Server."""

import json
import logging
import datetime
from typing import Any

from .config import ServerConfig

logger = logging.getLogger(__name__)


class LambdaHandler:
    """AWS Lambda handler for HTTP and MCP requests."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        
    def __call__(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Handle AWS Lambda events."""
        try:
            logger.info(f"Lambda invoked: {event.get('httpMethod', 'UNKNOWN')} {event.get('path', '/')}")
            
            # Handle different event types
            if "httpMethod" in event:
                return self._handle_http_request(event, context)
            elif "method" in event:
                return self._handle_mcp_request(event, context)
            else:
                return self._default_response()
                
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            return self._error_response(
                error_message=f"Lambda handler encountered an unexpected error: {str(e)}",
                status_code=500,
                error_code="LAMBDA_HANDLER_ERROR"
            )
            
    def _handle_http_request(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Handle HTTP requests from API Gateway."""
        method = event.get("httpMethod", "GET")
        path = event.get("path", "/")
        
        # Health check endpoint
        if path == "/health" and method == "GET":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "status": "healthy",
                    "service": "remote-mcp-server",
                    "version": self.config.version,
                    "timestamp": datetime.datetime.now().isoformat(),
                }),
            }
        
        # Handle POST requests with JSON data
        elif method == "POST":
            try:
                body_data = self._parse_request_body(event)
                
                # Validate request has body
                if not body_data:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({
                            "error": "Bad Request",
                            "error_code": "MISSING_BODY",
                            "message": "POST request requires a JSON body",
                            "details": "Send a JSON payload in the request body. For MCP requests, include 'jsonrpc', 'method', and 'id' fields.",
                            "timestamp": datetime.datetime.now().isoformat(),
                        }),
                    }
                
                # Check if this is an MCP request
                if self._is_mcp_request(body_data):
                    response = self._process_mcp_request(body_data)
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(response),
                    }
                
                # Regular POST data response
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "message": "POST request received",
                        "service": "remote-mcp-server",
                        "version": self.config.version,
                        "timestamp": datetime.datetime.now().isoformat(),
                        "received_data": body_data,
                        "path": path,
                        "method": method,
                    }),
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in request body: {e}")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "error": "Bad Request",
                        "error_code": "INVALID_JSON",
                        "message": "Request body contains invalid JSON",
                        "details": f"JSON parsing failed at line {e.lineno}, column {e.colno}: {e.msg}",
                        "suggestion": "Validate your JSON syntax. Common issues: trailing commas, unquoted keys, invalid escape sequences.",
                        "timestamp": datetime.datetime.now().isoformat(),
                    }),
                }
            except ValueError as e:
                logger.error(f"Value error processing request: {e}")
                return {
                    "statusCode": 422,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "error": "Unprocessable Entity", 
                        "error_code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "details": str(e),
                        "timestamp": datetime.datetime.now().isoformat(),
                    }),
                }
            except Exception as e:
                logger.error(f"Unexpected error processing POST request: {e}")
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "error": "Internal Server Error",
                        "error_code": "PROCESSING_ERROR",
                        "message": "Failed to process POST request",
                        "details": "An unexpected error occurred while processing your request. Please try again.",
                        "timestamp": datetime.datetime.now().isoformat(),
                    }),
                }
        
        # Handle unsupported methods
        elif method not in ["GET", "POST", "OPTIONS"]:
            return {
                "statusCode": 405,
                "headers": {
                    "Content-Type": "application/json",
                    "Allow": "GET, POST, OPTIONS"
                },
                "body": json.dumps({
                    "error": "Method Not Allowed",
                    "error_code": "UNSUPPORTED_METHOD",
                    "message": f"HTTP method '{method}' is not supported",
                    "allowed_methods": ["GET", "POST", "OPTIONS"],
                    "details": "Use GET for health checks and server info, POST for MCP requests and data submission.",
                    "timestamp": datetime.datetime.now().isoformat(),
                }),
            }
        
        # Handle unsupported paths
        elif path not in ["/", "/health"] and method == "GET":
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": "Not Found",
                    "error_code": "INVALID_ENDPOINT",
                    "message": f"Endpoint '{path}' not found",
                    "available_endpoints": {
                        "GET /": "Server information",
                        "GET /health": "Health check",
                        "POST /": "MCP requests and data submission"
                    },
                    "timestamp": datetime.datetime.now().isoformat(),
                }),
            }
        
        # Default GET response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "remote-mcp-server",
                "version": self.config.version,
                "timestamp": datetime.datetime.now().isoformat(),
                "method": method,
                "path": path,
                "endpoints": {
                    "health": "/health",
                    "mcp": "POST / with JSON-RPC payload"
                },
            }),
        }
    
    def _handle_mcp_request(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Handle direct MCP requests."""
        response = self._process_mcp_request(event)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response),
        }
    
    def _parse_request_body(self, event: dict[str, Any]) -> dict[str, Any]:
        """Parse request body from Lambda event."""
        body = event.get("body", "")
        if not body:
            return {}
        
        # Handle base64 encoded body
        if event.get("isBase64Encoded"):
            try:
                import base64
                body = base64.b64decode(body).decode("utf-8")
            except Exception as e:
                raise ValueError(f"Failed to decode base64 body: {e}")
        
        # Validate body size (prevent excessive memory usage)
        if len(body) > 1024 * 1024:  # 1MB limit
            raise ValueError("Request body too large. Maximum size is 1MB.")
        
        # Parse JSON
        try:
            parsed_data = json.loads(body)
            
            # Basic validation for common issues
            if isinstance(parsed_data, str):
                raise ValueError("Request body should be a JSON object, not a string.")
            
            return parsed_data
        except json.JSONDecodeError as e:
            # Re-raise with more context for better error handling upstream
            raise json.JSONDecodeError(
                f"Invalid JSON format: {e.msg}",
                body,
                e.pos
            )
    
    def _is_mcp_request(self, data: dict[str, Any]) -> bool:
        """Check if request data is an MCP request."""
        return "jsonrpc" in data and "method" in data
    
    def _process_mcp_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process MCP request and return response."""
        request_id = data.get("id")
        method = data.get("method")
        params = data.get("params", {})
        
        # Validate required MCP fields
        if "jsonrpc" not in data or data["jsonrpc"] != "2.0":
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": {
                        "details": "Missing or invalid 'jsonrpc' field. Must be '2.0'.",
                        "received": data.get("jsonrpc"),
                        "expected": "2.0"
                    }
                },
                "id": request_id,
            }
        
        if not method:
            return {
                "jsonrpc": "2.0", 
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": {
                        "details": "Missing 'method' field in MCP request.",
                        "required_fields": ["jsonrpc", "method", "id"],
                        "received_fields": list(data.keys())
                    }
                },
                "id": request_id,
            }
        
        if request_id is None:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600, 
                    "message": "Invalid Request",
                    "data": {
                        "details": "Missing 'id' field in MCP request.",
                        "note": "The 'id' field is required for request/response correlation."
                    }
                },
                "id": None,
            }
        
        try:
            # Validate method exists (basic validation for template)
            if method not in ["tools/list", "tools/call", "ping"]:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": "Method not found",
                        "data": {
                            "method": method,
                            "available_methods": ["tools/list", "tools/call", "ping"],
                            "details": f"Method '{method}' is not implemented in this MCP server."
                        }
                    },
                    "id": request_id,
                }
            
            # Basic MCP response - in a real implementation this would 
            # integrate with the MCP server to execute tools
            if method == "ping":
                result = {"status": "pong", "timestamp": datetime.datetime.now().isoformat()}
            elif method == "tools/list":
                result = {
                    "tools": [
                        {"name": "hello_world", "description": "Greet someone"},
                        {"name": "get_current_time", "description": "Get current timestamp"},
                        {"name": "echo_message", "description": "Echo a message"},
                        {"name": "get_server_info", "description": "Get server information"},
                        {"name": "calculate_sum", "description": "Calculate sum of numbers"}
                    ]
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                if not tool_name:
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32602,
                            "message": "Invalid params",
                            "data": {
                                "details": "Missing 'name' parameter for tool call.",
                                "required_params": ["name"],
                                "received_params": list(params.keys())
                            }
                        },
                        "id": request_id,
                    }
                result = {
                    "status": "success", 
                    "message": f"Tool '{tool_name}' would be executed with params: {params.get('arguments', {})}"
                }
            else:
                result = {"status": "success", "message": "MCP request processed successfully"}
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id,
            }
            
        except ValueError as e:
            logger.error(f"Value error in MCP request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Invalid params",
                    "data": {
                        "details": str(e),
                        "method": method,
                        "params": params
                    }
                },
                "id": request_id,
            }
        except Exception as e:
            logger.error(f"Unexpected error processing MCP request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {
                        "details": f"An unexpected error occurred: {str(e)}",
                        "method": method,
                        "suggestion": "Please check your request format and try again."
                    }
                },
                "id": request_id,
            }
    
    def _default_response(self) -> dict[str, Any]:
        """Return default response for unknown event types."""
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "remote-mcp-server",
                "version": self.config.version,
            }),
        }
    
    def _error_response(self, error_message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR") -> dict[str, Any]:
        """Return detailed error response."""
        error_types = {
            400: "Bad Request",
            401: "Unauthorized", 
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        
        error_title = error_types.get(status_code, "Error")
        
        response_body = {
            "error": error_title,
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.datetime.now().isoformat(),
            "service": "remote-mcp-server",
            "version": self.config.version
        }
        
        # Add helpful suggestions based on error type
        if status_code == 400:
            response_body["suggestions"] = [
                "Check request format and content type",
                "Ensure JSON is properly formatted",
                "Verify all required fields are present"
            ]
        elif status_code == 404:
            response_body["suggestions"] = [
                "Check the URL path",
                "Use GET /health for health checks",
                "Use POST / for MCP requests"
            ]
        elif status_code == 405:
            response_body["allowed_methods"] = ["GET", "POST", "OPTIONS"]
        elif status_code >= 500:
            response_body["suggestions"] = [
                "Try your request again in a few moments",
                "Check server status at /health endpoint",
                "Contact support if the issue persists"
            ]
        
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "X-Error-Code": error_code
            },
            "body": json.dumps(response_body),
        }