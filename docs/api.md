# API Documentation

This document provides comprehensive documentation for the Remote MCP Server REST API and MCP Protocol interfaces.

## Overview

Remote MCP Server provides dual interfaces:
- **REST API**: HTTP endpoints for traditional web integration
- **MCP Protocol**: Model Context Protocol for AI assistant integration

## Base URLs

### Production (AWS Lambda)
- **Base URL**: `https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/`
- **Region**: us-east-1
- **Environment**: Production

### Local Development
- **Base URL**: `http://localhost:3000/`
- **Environment**: Development

## REST API Endpoints

### Health Check

Monitor server health and availability.

#### `GET /health`

**Description**: Returns server health status and metadata.

**Request**:
```http
GET /health HTTP/1.1
Host: rexlaqrt59.execute-api.us-east-1.amazonaws.com
Accept: application/json
```

**Response**:
```json
{
  "status": "healthy",
  "service": "remote-mcp-server", 
  "version": "1.0.0",
  "timestamp": "2025-08-22T02:24:52.062825"
}
```

**Response Headers**:
```
Content-Type: application/json
Access-Control-Allow-Origin: *
```

**Status Codes**:
- `200 OK`: Server is healthy
- `500 Internal Server Error`: Server health check failed

---

### Main Endpoint

Primary endpoint for server information and requests.

#### `GET /remote-mcp-server`

**Description**: Returns server information and request metadata.

**Request**:
```http
GET /remote-mcp-server HTTP/1.1
Host: rexlaqrt59.execute-api.us-east-1.amazonaws.com
Accept: application/json
```

**Response**:
```json
{
  "message": "remote-mcp-server",
  "version": "1.0.0", 
  "timestamp": "2025-08-22T02:25:00.428904",
  "method": "GET",
  "path": "/remote-mcp-server"
}
```

**Status Codes**:
- `200 OK`: Request successful
- `500 Internal Server Error`: Server error

---

### POST Data Handler

Multi-purpose POST endpoint supporting various data formats.

#### `POST /remote-mcp-server`

**Description**: Handles POST requests with JSON data, Base64 encoded data, or MCP protocol requests.

##### Regular JSON Data

**Request**:
```http
POST /remote-mcp-server HTTP/1.1
Host: rexlaqrt59.execute-api.us-east-1.amazonaws.com  
Content-Type: application/json

{
  "message": "Hello from API!",
  "data": [1, 2, 3],
  "user_id": 123
}
```

**Response**:
```json
{
  "message": "POST request received",
  "service": "remote-mcp-server",
  "version": "1.0.0",
  "timestamp": "2025-08-22T02:25:08.947510",
  "received_data": {
    "message": "Hello from API!",
    "data": [1, 2, 3], 
    "user_id": 123
  },
  "path": "/remote-mcp-server",
  "method": "POST"
}
```

##### Base64 Encoded Data

**Request**:
```http
POST /remote-mcp-server HTTP/1.1
Content-Type: application/json
Content-Encoding: base64

eyJtZXNzYWdlIjogIkVuY29kZWQgZGF0YSIsICJkYXRhIjogWzEsIDIsIDNdfQ==
```

**Response**:
```json
{
  "message": "POST request received",
  "service": "remote-mcp-server", 
  "version": "1.0.0",
  "timestamp": "2025-08-22T02:25:15.123456",
  "received_data": {
    "message": "Encoded data",
    "data": [1, 2, 3]
  },
  "path": "/remote-mcp-server",
  "method": "POST"
}
```

##### MCP Protocol Request

**Request**:
```http
POST /remote-mcp-server HTTP/1.1
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "hello_world",
    "arguments": {"name": "API User"}
  },
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "success", 
    "message": "MCP request processed successfully"
  }
}
```

**Status Codes**:
- `200 OK`: Request processed successfully
- `400 Bad Request`: Invalid JSON or malformed request
- `500 Internal Server Error`: Processing error

---

## MCP Protocol Interface

The MCP (Model Context Protocol) interface provides direct integration with AI assistants using the JSON-RPC 2.0 protocol over stdio.

### Protocol Overview

- **Transport**: Standard input/output (stdio)
- **Format**: JSON-RPC 2.0
- **Encoding**: UTF-8

### Starting MCP Server

```bash
# Start MCP server in stdio mode
uv run python -m remote_mcp_server.mcp_server

# Start with custom log level  
uv run python -m remote_mcp_server.mcp_server --log-level DEBUG
```

### Available Tools

#### 1. hello_world

Greet someone with a personalized message.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "hello_world",
    "arguments": {
      "name": "Alice"
    }
  },
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0", 
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Hello, Alice! Welcome to Remote MCP Server."
      }
    ]
  },
  "id": 1
}
```

**Parameters**:
- `name` (string, optional): Name to greet (defaults to "World")

---

#### 2. get_current_time

Get the current timestamp in ISO format.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call", 
  "params": {
    "name": "get_current_time",
    "arguments": {}
  },
  "id": 2
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text", 
        "text": "2025-08-22T02:24:52.062825"
      }
    ]
  },
  "id": 2
}
```

**Parameters**: None

---

#### 3. echo_message

Echo a message with optional repetition.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "echo_message", 
    "arguments": {
      "message": "Hello World",
      "repeat": 3
    }
  },
  "id": 3
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Hello World Hello World Hello World"
      }
    ]
  }, 
  "id": 3
}
```

**Parameters**:
- `message` (string, required): Message to echo
- `repeat` (integer, optional): Number of repetitions (1-10, defaults to 1)

**Validation**:
- `repeat` must be between 1 and 10
- Raises `ValueError` if validation fails

---

#### 4. get_server_info

Get comprehensive server information and metadata.

**Request**:
```json
{
  "jsonrpc": "2.0", 
  "method": "tools/call",
  "params": {
    "name": "get_server_info",
    "arguments": {}
  },
  "id": 4
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"service\": \"remote-mcp-server\", \"version\": \"1.0.0\", \"status\": \"healthy\", \"timestamp\": \"2025-08-22T02:24:52.062825\", \"environment\": \"production\", \"tools_available\": 5}"
      }
    ]
  },
  "id": 4
}
```

**Response Fields**:
- `service`: Service name
- `version`: Current version
- `status`: Health status
- `timestamp`: Current ISO timestamp
- `environment`: Runtime environment
- `tools_available`: Number of registered tools

**Parameters**: None

---

#### 5. calculate_sum

Calculate the sum of a list of numbers.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "calculate_sum",
    "arguments": {
      "numbers": [1.5, 2.0, 3.5, 4.0]
    }
  },
  "id": 5
}
```

**Response**:
```json
{
  "jsonrpc": "2.0", 
  "result": {
    "content": [
      {
        "type": "text",
        "text": "11.0"
      }
    ]
  },
  "id": 5
}
```

**Parameters**:
- `numbers` (array of numbers, required): List of numbers to sum

**Validation**:
- Maximum 100 numbers allowed
- Empty array returns 0.0
- Raises `ValueError` if more than 100 numbers provided

---

### Tool Discovery

List all available tools and their schemas.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": 6
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "hello_world",
        "description": "Say hello to someone.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "The name to greet (defaults to \"World\")"
            }
          }
        }
      },
      // ... other tools
    ]
  },
  "id": 6
}
```

## Error Handling

### HTTP Errors

#### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Invalid JSON format in request body",
  "timestamp": "2025-08-22T02:24:52.062825"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Internal server error", 
  "message": "An unexpected error occurred",
  "timestamp": "2025-08-22T02:24:52.062825"
}
```

### MCP Protocol Errors

#### Method Not Found
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {
      "method": "unknown_method"
    }
  },
  "id": 1
}
```

#### Invalid Parameters
```json
{
  "jsonrpc": "2.0", 
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "error": "Repeat count must be between 1 and 10"
    }
  },
  "id": 1
}
```

#### Internal Error
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "error": "Detailed error information"
    }
  },
  "id": 1
}
```

## Rate Limiting

### AWS API Gateway Limits
- **Request Rate**: 10,000 requests per second
- **Burst Limit**: 5,000 requests  
- **Throttling**: 429 Too Many Requests

### Lambda Limits  
- **Concurrent Executions**: 1000 (default)
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Payload Size**: 6 MB

## Authentication

### Current Status
- **Authentication**: None (open access)
- **Authorization**: None required
- **CORS**: Enabled for all origins

### Future Enhancements
- API Key authentication
- OAuth 2.0 integration  
- Role-based access control

## CORS Configuration

```json
{
  "AllowOrigin": "*",
  "AllowMethods": "GET,POST,OPTIONS", 
  "AllowHeaders": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "MaxAge": 86400
}
```

## Monitoring and Observability

### Health Check Monitoring
```bash
# Monitor endpoint availability
curl -f https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/health

# Check response time
curl -w "@curl-format.txt" -s -o /dev/null https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/health
```

### Logging
- **CloudWatch Logs**: `/aws/lambda/remote-mcp-server-RemoteMcpServerFunction-*`
- **Log Level**: INFO (configurable)
- **Request Tracing**: Each request has unique trace ID

### Metrics
- **Invocation Count**: Lambda function invocations
- **Duration**: Request processing time
- **Error Rate**: Failed request percentage  
- **Throttles**: Rate limit violations

## Client Integration Examples

### Python Client
```python
import requests

# Health check
response = requests.get("https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/health")
print(response.json())

# POST request with data
data = {"message": "Hello from Python!", "user_id": 123}
response = requests.post(
    "https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/remote-mcp-server",
    json=data
)
print(response.json())

# MCP protocol request
mcp_request = {
    "jsonrpc": "2.0",
    "method": "tools/call", 
    "params": {
        "name": "hello_world",
        "arguments": {"name": "Python Client"}
    },
    "id": 1
}
response = requests.post(
    "https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/remote-mcp-server",
    json=mcp_request
)
print(response.json())
```

### JavaScript/Node.js Client
```javascript
// Health check
const healthResponse = await fetch('https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/health');
const healthData = await healthResponse.json();
console.log(healthData);

// MCP protocol request
const mcpRequest = {
  jsonrpc: "2.0",
  method: "tools/call",
  params: {
    name: "calculate_sum", 
    arguments: { numbers: [1, 2, 3, 4, 5] }
  },
  id: 1
};

const mcpResponse = await fetch('https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/remote-mcp-server', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(mcpRequest)
});

const mcpData = await mcpResponse.json(); 
console.log(mcpData);
```

### curl Examples
```bash
# Health check
curl https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/health

# POST JSON data
curl -X POST https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/remote-mcp-server \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from curl!", "data": [1,2,3]}'

# MCP protocol tool call
curl -X POST https://rexlaqrt59.execute-api.us-east-1.amazonaws.com/Prod/remote-mcp-server \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "echo_message",
      "arguments": {"message": "Hello MCP!", "repeat": 2}
    },
    "id": 1
  }'
```

## Development and Testing

### Local API Server
```bash
# Start local server
uv run python -m remote_mcp_server.mcp_server --port 8000

# Test local endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/remote-mcp-server \
  -H "Content-Type: application/json" \
  -d '{"test": "local development"}'
```

### SAM Local Testing
```bash
# Start local API Gateway
sam local start-api

# Test with local endpoints
curl http://127.0.0.1:3000/health
curl http://127.0.0.1:3000/remote-mcp-server
```

---

## API Versioning

### Current Version: 1.0.0

- **Stability**: Stable
- **Compatibility**: Backwards compatible
- **Support**: Full support and maintenance

### Future Versions
- **v1.1**: Additional MCP tools and features
- **v2.0**: Breaking changes and major enhancements

### Version Headers
```http
X-API-Version: 1.0.0
X-Server-Version: 1.0.0
```

---

For more information, see:
- [Development Guide](development.md)
- [Deployment Guide](deployment.md) 
- [Architecture Overview](architecture.md)