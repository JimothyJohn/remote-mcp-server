"""AWS Lambda handler for Remote MCP Server."""

import json
import logging
import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from .config import ServerConfig
from .middleware import require_api_key, optional_api_key, with_rate_limiting
from .billing import SubscriptionBillingService

logger = logging.getLogger(__name__)


class LambdaHandler:
    """AWS Lambda handler for HTTP and MCP requests."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self._openapi_spec: Optional[str] = None
        try:
            self.billing_service = SubscriptionBillingService()
        except Exception as e:
            logger.warning(f"Billing service initialization failed: {e}")
            self.billing_service = None
        
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
        
        # Subscription management endpoints
        if path.startswith("/subscription/"):
            return self._handle_subscription_request(event, context)
        
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
        
        # OpenAPI specification endpoint
        elif path in ["/openapi.yaml", "/openapi.yml"] and method == "GET":
            try:
                openapi_spec = self._get_openapi_spec()
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/x-yaml"},
                    "body": openapi_spec,
                }
            except Exception as e:
                logger.error(f"Failed to serve OpenAPI spec: {e}")
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "error": "Internal Server Error",
                        "error_code": "OPENAPI_LOAD_ERROR",
                        "message": "Failed to load OpenAPI specification",
                        "timestamp": datetime.datetime.now().isoformat(),
                    }),
                }
        
        # OpenAPI specification as JSON endpoint
        elif path == "/openapi.json" and method == "GET":
            try:
                openapi_spec_dict = self._get_openapi_spec_json()
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(openapi_spec_dict),
                }
            except Exception as e:
                logger.error(f"Failed to serve OpenAPI spec as JSON: {e}")
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "error": "Internal Server Error",
                        "error_code": "OPENAPI_JSON_ERROR",
                        "message": "Failed to convert OpenAPI specification to JSON",
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
        elif path not in ["/", "/health", "/openapi.yaml", "/openapi.yml", "/openapi.json"] and method == "GET":
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
                        "GET /openapi.yaml": "OpenAPI specification (YAML)",
                        "GET /openapi.json": "OpenAPI specification (JSON)",
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
                    "mcp": "POST / with JSON-RPC payload",
                    "openapi_yaml": "/openapi.yaml",
                    "openapi_json": "/openapi.json"
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
                result: dict[str, Any] = {
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
        
        response_body: dict[str, Any] = {
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
    
    def _get_openapi_spec(self) -> str:
        """Load and return OpenAPI specification as YAML string."""
        if self._openapi_spec is not None:
            return self._openapi_spec
            
        # Look for openapi.yaml in multiple possible locations
        possible_paths = [
            # Current directory (for local development)
            Path.cwd() / "openapi.yaml",
            # Project root
            Path(__file__).parent.parent / "openapi.yaml",
            # Lambda deployment location
            Path("/opt/openapi.yaml"),
            Path("/var/task/openapi.yaml"),
        ]
        
        for openapi_path in possible_paths:
            if openapi_path.exists():
                try:
                    with open(openapi_path, 'r', encoding='utf-8') as f:
                        self._openapi_spec = f.read()
                    logger.info(f"Loaded OpenAPI spec from {openapi_path}")
                    return self._openapi_spec
                except Exception as e:
                    logger.warning(f"Failed to load OpenAPI spec from {openapi_path}: {e}")
                    continue
        
        # If no file found, create a minimal spec dynamically
        logger.warning("OpenAPI specification file not found, generating minimal spec")
        minimal_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "Remote MCP Server API",
                "version": self.config.version,
                "description": "A comprehensive MCP server with AWS Lambda compatibility"
            },
            "servers": [
                {"url": "https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod", "description": "Production"}
            ],
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health Check",
                        "responses": {
                            "200": {"description": "Server is healthy"}
                        }
                    }
                }
            }
        }
        self._openapi_spec = yaml.dump(minimal_spec, default_flow_style=False)
        return self._openapi_spec
    
    def _get_openapi_spec_json(self) -> dict[str, Any]:
        """Load and return OpenAPI specification as JSON dict."""
        yaml_spec = self._get_openapi_spec()
        try:
            return yaml.safe_load(yaml_spec)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse OpenAPI YAML: {e}")
            raise ValueError(f"Invalid OpenAPI YAML format: {e}") from e
    
    def _handle_subscription_request(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Handle subscription management requests."""
        if not self.billing_service:
            return self._error_response(
                "Billing service unavailable",
                503,
                "BILLING_SERVICE_ERROR"
            )
        
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        
        try:
            if path == "/subscription/create" and method == "POST":
                return self._create_subscription(event, context)
            elif path.startswith("/subscription/") and method == "GET":
                # Extract API key from path: /subscription/{api_key}
                api_key = path.split("/")[-1]
                return self._get_subscription_info(api_key, event, context)
            elif path == "/subscription/usage" and method == "POST":
                return self._update_usage(event, context)
            elif path == "/subscription/cancel" and method == "POST":
                return self._cancel_subscription(event, context)
            else:
                return self._error_response(
                    f"Subscription endpoint not found: {method} {path}",
                    404,
                    "ENDPOINT_NOT_FOUND"
                )
        except Exception as e:
            logger.error(f"Subscription request error: {e}")
            return self._error_response(
                f"Subscription operation failed: {str(e)}",
                500,
                "SUBSCRIPTION_ERROR"
            )
    
    def _create_subscription(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Create a new subscription with Stripe and AWS API key."""
        try:
            body_data = self._parse_request_body(event)
            
            # Required fields
            email = body_data.get("email")
            payment_method_id = body_data.get("payment_method_id")
            plan_id = body_data.get("plan_id", "basic")
            
            if not email or not payment_method_id:
                return self._error_response(
                    "Missing required fields: email and payment_method_id",
                    400,
                    "MISSING_FIELDS"
                )
            
            # Create subscription
            result = self.billing_service.create_customer_and_subscription(
                email=email,
                payment_method_id=payment_method_id,
                plan_id=plan_id
            )
            
            return {
                "statusCode": 201,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": True,
                    "message": "Subscription created successfully",
                    "data": result,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            }
            
        except Exception as e:
            logger.error(f"Subscription creation error: {e}")
            return self._error_response(
                f"Failed to create subscription: {str(e)}",
                400,
                "SUBSCRIPTION_CREATION_FAILED"
            )
    
    @optional_api_key()
    def _get_subscription_info(self, api_key: str, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Get subscription information by API key."""
        try:
            subscription = self.billing_service.get_subscription_by_api_key(api_key)
            
            if not subscription:
                return self._error_response(
                    "Subscription not found",
                    404,
                    "SUBSCRIPTION_NOT_FOUND"
                )
            
            # Get usage statistics
            customer_id = subscription.get('customer_id')
            if customer_id:
                usage_stats = self.billing_service.get_usage_statistics(customer_id)
            else:
                usage_stats = {"error": "Customer ID not found"}
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "subscription": {
                        "customer_id": subscription.get('customer_id'),
                        "subscription_id": subscription.get('subscription_id'),
                        "email": subscription.get('email'),
                        "plan_id": subscription.get('plan_id'),
                        "status": subscription.get('status'),
                        "created_at": subscription.get('created_at'),
                        "usage_count": subscription.get('usage_count', 0),
                        "last_usage": subscription.get('last_usage')
                    },
                    "usage_statistics": usage_stats,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            }
            
        except Exception as e:
            logger.error(f"Get subscription info error: {e}")
            return self._error_response(
                f"Failed to retrieve subscription information: {str(e)}",
                500,
                "SUBSCRIPTION_INFO_ERROR"
            )
    
    @require_api_key(track_usage=False)
    def _update_usage(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Update usage statistics for a subscription."""
        try:
            body_data = self._parse_request_body(event)
            api_key = event.get('api_key')
            
            endpoint = body_data.get("endpoint", "unknown")
            tokens_used = body_data.get("tokens_used", 1)
            
            if not api_key:
                return self._error_response(
                    "API key required for usage tracking",
                    401,
                    "API_KEY_REQUIRED"
                )
            
            success = self.billing_service.track_api_usage(api_key, endpoint, tokens_used)
            
            if success:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "success": True,
                        "message": "Usage tracked successfully",
                        "endpoint": endpoint,
                        "tokens_used": tokens_used,
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                }
            else:
                return self._error_response(
                    "Failed to track usage",
                    500,
                    "USAGE_TRACKING_FAILED"
                )
                
        except Exception as e:
            logger.error(f"Usage tracking error: {e}")
            return self._error_response(
                f"Failed to update usage: {str(e)}",
                500,
                "USAGE_UPDATE_ERROR"
            )
    
    @require_api_key(track_usage=False)
    def _cancel_subscription(self, event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Cancel a subscription."""
        try:
            api_key = event.get('api_key')
            
            if not api_key:
                return self._error_response(
                    "API key required for subscription cancellation",
                    401,
                    "API_KEY_REQUIRED"
                )
            
            result = self.billing_service.cancel_subscription(api_key)
            
            if result.get('success'):
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "success": True,
                        "message": "Subscription cancelled successfully",
                        "subscription_id": result.get('subscription_id'),
                        "cancelled_at": result.get('cancelled_at'),
                        "timestamp": datetime.datetime.now().isoformat()
                    })
                }
            else:
                return self._error_response(
                    result.get('error', 'Unknown cancellation error'),
                    400,
                    "SUBSCRIPTION_CANCELLATION_FAILED"
                )
                
        except Exception as e:
            logger.error(f"Subscription cancellation error: {e}")
            return self._error_response(
                f"Failed to cancel subscription: {str(e)}",
                500,
                "CANCELLATION_ERROR"
            )