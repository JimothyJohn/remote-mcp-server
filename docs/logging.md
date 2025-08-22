# Logging Documentation

This document provides comprehensive information about the logging system implemented in Remote MCP Server for troubleshooting, monitoring, and performance analysis.

## Overview

The Remote MCP Server implements a comprehensive structured logging system designed for:

- **Troubleshooting**: Detailed error context and stack traces
- **Performance Monitoring**: Request/response timing and resource usage
- **Security Auditing**: Request tracing and user activity
- **Operational Insights**: System health and usage patterns

## Logging Architecture

### Components

1. **Logging Configuration Module** (`remote_mcp_server.logging_config`)
   - Structured JSON logging formatter
   - Request correlation and tracing
   - Performance metrics collection
   - Security-aware data sanitization

2. **Logger Categories**
   - `remote_mcp_server.mcp_server`: Main application logger
   - `mcp.server`: MCP protocol operations
   - `mcp.tools`: Individual tool execution
   - `aws.lambda`: AWS Lambda-specific events
   - `http.request`: Incoming HTTP requests
   - `http.response`: HTTP response details
   - `performance`: Timing and resource metrics

3. **Log Levels**
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General operational information
   - `WARNING`: Potentially problematic situations
   - `ERROR`: Error conditions that don't halt execution
   - `CRITICAL`: Serious errors that may cause termination

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Global log level |
| `STRUCTURED_LOGGING` | `true` | Enable JSON structured logs |
| `PERFORMANCE_LOGGING` | `true` | Enable performance metrics |
| `LOG_FILE` | None | Optional log file path |

### Programmatic Configuration

```python
from remote_mcp_server.logging_config import setup_logging

# Basic setup
setup_logging(log_level="DEBUG")

# Advanced setup
setup_logging(
    log_level="INFO",
    enable_structured_logging=True,
    enable_performance_logging=True,
    log_file="/var/log/mcp-server.log"
)
```

## Log Structure

### JSON Log Format

All logs are output as structured JSON when structured logging is enabled:

```json
{
  "timestamp": "2025-08-22T02:30:45.123Z",
  "level": "INFO",
  "logger": "mcp.tools",
  "message": "MCP tool hello_world executed successfully",
  "module": "mcp_server",
  "function": "hello_world",
  "line": 95,
  "request": {
    "request_id": "abc-123-def-456",
    "timestamp": "2025-08-22T02:30:45.000Z",
    "lambda_function": "remote-mcp-server-Function",
    "lambda_version": "$LATEST"
  },
  "tool_name": "hello_world",
  "input_name": "User",
  "message_length": 42,
  "action": "tool_success"
}
```

### Key Fields

- **timestamp**: ISO 8601 UTC timestamp
- **level**: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **logger**: Logger category
- **message**: Human-readable message
- **module**: Source code module
- **function**: Source code function
- **line**: Source code line number
- **request**: Request correlation context
- **action**: Standardized action type for filtering
- **Custom Fields**: Context-specific additional data

## Logging Categories

### 1. MCP Tool Execution

Logs all MCP tool operations with comprehensive context.

#### Tool Start
```json
{
  "timestamp": "2025-08-22T02:30:45.123Z",
  "level": "INFO",
  "logger": "mcp.tools",
  "message": "Executing hello_world tool",
  "tool_name": "hello_world",
  "input_name": "Alice",
  "action": "tool_start"
}
```

#### Tool Success
```json
{
  "timestamp": "2025-08-22T02:30:45.145Z",
  "level": "INFO",
  "logger": "mcp.tools",
  "message": "Hello world message generated",
  "tool_name": "hello_world",
  "message": "Hello, Alice! Welcome to Remote MCP Server.",
  "message_length": 42,
  "action": "tool_success"
}
```

#### Tool Error
```json
{
  "timestamp": "2025-08-22T02:30:45.145Z",
  "level": "ERROR",
  "logger": "mcp.tools",
  "message": "Hello world tool failed: Invalid input",
  "tool_name": "hello_world",
  "input_name": "InvalidName",
  "error_type": "ValueError",
  "action": "tool_error",
  "exception": {
    "type": "ValueError",
    "message": "Invalid input",
    "traceback": "Traceback (most recent call last)..."
  }
}
```

### 2. HTTP Request/Response Logging

#### Request Logging
```json
{
  "timestamp": "2025-08-22T02:30:45.000Z",
  "level": "INFO",
  "logger": "http.request",
  "message": "HTTP POST /remote-mcp-server",
  "method": "POST",
  "path": "/remote-mcp-server",
  "request_type": "http",
  "content_type": "application/json",
  "user_agent": "Mozilla/5.0 (compatible; API Client)",
  "body": {"jsonrpc": "2.0", "method": "tools/call"},
  "headers": {
    "content-type": "application/json",
    "host": "api.example.com"
  }
}
```

#### Response Logging
```json
{
  "timestamp": "2025-08-22T02:30:45.150Z",
  "level": "INFO",
  "logger": "http.response",
  "message": "HTTP response 200",
  "status_code": 200,
  "status_category": "2xx",
  "response_type": "http",
  "duration_ms": 150.5,
  "response_size": 256
}
```

### 3. AWS Lambda Events

#### Cold Start Detection
```json
{
  "timestamp": "2025-08-22T02:30:45.000Z",
  "level": "INFO",
  "logger": "aws.lambda",
  "message": "Lambda function invoked",
  "cold_start": true,
  "context_type": "LambdaContext",
  "event_type": "api_gateway",
  "action": "lambda_start"
}
```

#### Lambda Context
```json
{
  "timestamp": "2025-08-22T02:30:45.005Z",
  "level": "INFO",
  "logger": "aws.lambda",
  "message": "AWS Lambda context",
  "aws_request_id": "abc-123-def-456",
  "function_name": "remote-mcp-server-Function",
  "function_version": "$LATEST",
  "memory_limit_mb": 256,
  "remaining_time_ms": 29800
}
```

### 4. Performance Metrics

#### Timing Information
```json
{
  "timestamp": "2025-08-22T02:30:45.200Z",
  "level": "INFO",
  "logger": "performance",
  "message": "Performance: hello_world completed",
  "operation": "hello_world",
  "duration_ms": 22.5,
  "duration_seconds": 0.023,
  "tool_name": "hello_world",
  "module": "mcp_server"
}
```

#### Memory Usage (when available)
```json
{
  "timestamp": "2025-08-22T02:30:45.200Z",
  "level": "INFO",
  "logger": "performance",
  "message": "Memory: get_server_info",
  "operation": "get_server_info",
  "memory_mb": 45.2,
  "memory_percent": 18.1,
  "cpu_percent": 5.3
}
```

### 5. MCP Protocol Events

#### Protocol Request
```json
{
  "timestamp": "2025-08-22T02:30:45.010Z",
  "level": "INFO",
  "logger": "mcp.server",
  "message": "Processing MCP request",
  "request_id": "1",
  "method": "tools/call",
  "jsonrpc": "2.0",
  "has_params": true,
  "action": "mcp_request_start"
}
```

#### Tool Call Request
```json
{
  "timestamp": "2025-08-22T02:30:45.015Z",
  "level": "INFO",
  "logger": "mcp.server",
  "message": "Tool call request",
  "request_id": "1",
  "tool_name": "hello_world",
  "has_arguments": true,
  "action": "tool_call_request"
}
```

## Request Correlation

### Request Context

Each request is assigned a unique identifier that flows through all related log entries:

```python
from remote_mcp_server.logging_config import set_request_context

# Set request context
request_id = set_request_context(
    request_id="custom-id-123",
    user_id="user-456",
    session_id="session-789"
)

# All subsequent logs will include this context
logger.info("Processing user request")
```

### Context Fields

- **request_id**: Unique request identifier
- **user_id**: User identifier (if available)
- **session_id**: Session identifier (if available)
- **lambda_function**: AWS Lambda function name
- **lambda_version**: AWS Lambda version

## Security and Privacy

### Data Sanitization

The logging system automatically sanitizes sensitive data:

#### Sensitive Field Detection
```python
# These fields are automatically redacted
sensitive_keys = {
    'password', 'token', 'key', 'secret', 'authorization',
    'cookie', 'session', 'credential', 'auth'
}
```

#### Sanitized Output
```json
{
  "user_credentials": "<REDACTED>",
  "api_key": "<REDACTED>",
  "username": "john_doe",
  "data": {"message": "Hello World"}
}
```

### Size Limits

- **Log Messages**: Truncated at 1000 characters
- **Function Arguments**: Limited to first 200 characters
- **Array/Object Display**: Maximum 10 items shown
- **Response Bodies**: Limited to 200 characters in logs

## Decorators and Utilities

### Function Entry/Exit Logging

```python
from remote_mcp_server.logging_config import log_function_entry_exit

@log_function_entry_exit(
    logger=my_logger,
    log_args=True,
    log_result=True,
    log_duration=True
)
def my_function(arg1, arg2):
    # Function implementation
    return result
```

### Performance Logging

```python
from remote_mcp_server.logging_config import performance_logger

# Log timing
performance_logger.log_timing("database_query", 0.125, query_type="SELECT")

# Log memory usage
performance_logger.log_memory_usage("data_processing", 128.5, records_processed=1000)
```

### MCP Tool Execution Logging

```python
from remote_mcp_server.logging_config import log_mcp_tool_execution

# Success case
log_mcp_tool_execution("my_tool", {"param": "value"}, result="success")

# Error case
try:
    # Tool execution
    pass
except Exception as e:
    log_mcp_tool_execution("my_tool", {"param": "value"}, error=e)
```

## Troubleshooting Guide

### Common Log Analysis Patterns

#### Find All Errors for a Request
```bash
# Using jq to filter logs
cat logs.jsonl | jq 'select(.request.request_id == "abc-123" and .level == "ERROR")'
```

#### Performance Analysis
```bash
# Find slow operations (> 1 second)
cat logs.jsonl | jq 'select(.logger == "performance" and .duration_ms > 1000)'
```

#### Tool Usage Statistics
```bash
# Count tool executions by tool name
cat logs.jsonl | jq -r 'select(.action == "tool_success") | .tool_name' | sort | uniq -c
```

#### Error Rate Analysis
```bash
# Count errors by type
cat logs.jsonl | jq -r 'select(.level == "ERROR") | .error_type' | sort | uniq -c
```

### AWS CloudWatch Integration

#### Log Groups
- **Function Logs**: `/aws/lambda/remote-mcp-server-Function-*`
- **API Gateway**: `/aws/apigateway/remote-mcp-server`

#### CloudWatch Insights Queries

##### Find High Latency Requests
```sql
fields @timestamp, @message
| filter @message like /performance/
| filter duration_ms > 1000
| sort @timestamp desc
| limit 20
```

##### Error Analysis
```sql
fields @timestamp, @message, error_type, tool_name
| filter level = "ERROR"
| stats count() by error_type, tool_name
| sort count desc
```

##### Cold Start Analysis
```sql
fields @timestamp, @message
| filter @message like /cold_start/
| filter cold_start = true
| stats count() by bin(5m)
```

### Local Development Debugging

#### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
uv run python -m remote_mcp_server.mcp_server
```

#### File-based Logging
```bash
export LOG_FILE=/tmp/mcp-server.log
uv run python -m remote_mcp_server.mcp_server

# Monitor logs
tail -f /tmp/mcp-server.log | jq .
```

#### Filter Specific Components
```bash
# Only tool execution logs
cat logs.jsonl | jq 'select(.logger == "mcp.tools")'

# Only performance logs
cat logs.jsonl | jq 'select(.logger == "performance")'

# Only errors and warnings
cat logs.jsonl | jq 'select(.level == "ERROR" or .level == "WARNING")'
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Error Rate**
   - Total errors per minute
   - Error rate by tool/endpoint
   - Critical errors requiring immediate attention

2. **Performance Metrics**
   - Average response time
   - 95th percentile latency
   - Cold start frequency and duration

3. **Usage Patterns**
   - Requests per minute
   - Most used tools
   - Geographic distribution

4. **Resource Utilization**
   - Memory usage patterns
   - CPU utilization
   - Lambda concurrent executions

### Alerting Examples

#### High Error Rate Alert
```sql
fields @timestamp
| filter level = "ERROR"
| stats count() as error_count by bin(1m)
| filter error_count > 10
```

#### Performance Degradation Alert
```sql
fields @timestamp, duration_ms
| filter logger = "performance" 
| stats avg(duration_ms) as avg_duration by bin(5m)
| filter avg_duration > 1000
```

## Log Retention and Management

### AWS Lambda
- **Default Retention**: Never expire
- **Recommended**: 30-90 days for cost optimization
- **Configuration**: CloudFormation template or AWS Console

### Log Rotation (Local Development)
```bash
# Using logrotate (Linux)
/var/log/mcp-server.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

## Best Practices

### For Developers

1. **Use Appropriate Log Levels**
   - DEBUG: Detailed diagnostic information
   - INFO: Normal operation progress
   - WARNING: Unexpected but recoverable issues
   - ERROR: Serious problems requiring attention

2. **Include Context**
   - Always include relevant identifiers
   - Add timing information for performance analysis
   - Include error context and recovery information

3. **Security Considerations**
   - Never log passwords, tokens, or secrets
   - Sanitize user input before logging
   - Consider data privacy requirements

### For Operations

1. **Monitor Key Metrics**
   - Set up alerts for error rates and performance
   - Track resource utilization trends
   - Monitor cold start frequency

2. **Log Analysis**
   - Use structured queries for analysis
   - Create dashboards for operational visibility
   - Implement automated anomaly detection

3. **Capacity Planning**
   - Monitor log volume growth
   - Plan for log storage costs
   - Optimize retention policies

---

## Configuration Examples

### Development Environment
```python
setup_logging(
    log_level="DEBUG",
    enable_structured_logging=True,
    enable_performance_logging=True,
    log_file="development.log"
)
```

### Production Environment
```python
setup_logging(
    log_level="INFO",
    enable_structured_logging=True,
    enable_performance_logging=True
    # No log file - use CloudWatch
)
```

### High-Performance Environment
```python
setup_logging(
    log_level="WARNING",
    enable_structured_logging=True,
    enable_performance_logging=False  # Reduce overhead
)
```

For more information, see:
- [API Documentation](api.md)
- [Deployment Guide](deployment.md)
- [Architecture Overview](architecture.md)