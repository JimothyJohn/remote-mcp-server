# Model Context Protocol (MCP) Server Overview

This document summarizes the functionality of the Amazon SNS/SQS MCP Server and provides guidance for transforming the current `remote-mcp-server` into a similar MCP-based service.

## What is MCP?

Model Context Protocol (MCP) is a standard for connecting AI models to external tools and data sources. It allows AI assistants to interact with various services through a standardized interface.

## Amazon SNS/SQS MCP Server Architecture

The example MCP server demonstrates how to create a bridge between AI models and AWS services:

### Core Components

1. **Server Module** (`server.py`)
   - Uses FastMCP framework to create the server
   - Handles CLI arguments (e.g., `--allow-resource-creation`)
   - Registers tools from different service modules
   - Main entry point that runs the MCP server

2. **Service Modules** (`sns.py`, `sqs.py`)
   - Register AWS service-specific tools
   - Define which AWS operations to expose as MCP tools
   - Configure operation overrides and validators
   - Handle resource tagging for security

3. **Tool Generator** (`generator.py`)
   - Dynamically generates MCP tools from AWS boto3 client operations
   - Creates Python functions that can be called by AI models
   - Handles parameter validation and documentation

4. **Security & Common Utilities** (`common.py`)
   - Implements resource tagging (`mcp_server_version` tag)
   - Validates that only MCP-created resources can be modified
   - Provides common validation functions

### Key Features

- **Dynamic Tool Generation**: Automatically creates tools from AWS service APIs
- **Security Controls**: Tags resources to prevent unauthorized modifications
- **Configurable Access**: Can disable resource creation/deletion via CLI flags
- **Multiple Service Support**: Extensible architecture for multiple AWS services
- **Error Handling**: Comprehensive validation and error reporting

## Available Tools (Examples)

**SNS Tools:**
- `create_topic` - Create SNS topics
- `list_topics` - List existing topics
- `subscribe` - Create subscriptions
- `publish` - Send messages
- `delete_topic` - Remove topics

**SQS Tools:**
- `create_queue` - Create SQS queues
- `list_queues` - List existing queues
- `send_message` - Send messages to queue
- `receive_message` - Retrieve messages
- `delete_queue` - Remove queues

## Transforming remote-mcp-server to MCP

To convert the current simple "hello world" Lambda function into an MCP server:

### 1. Dependencies
Add to `pyproject.toml`:
```toml
dependencies = [
    "mcp[cli]>=1.11.0",
    "pydantic>=2.0.0",
    # Add service-specific dependencies (boto3 for AWS, requests for APIs, etc.)
]
```

### 2. Server Structure
Create a new `mcp_server.py`:

```python
from mcp.server.fastmcp import FastMCP

# Create MCP server instance
mcp = FastMCP(
    'remote-mcp-server',
    instructions="A simple MCP server for basic operations.",
    version="1.0.0"
)

@mcp.tool()
def hello_world(name: str = "World"):
    """Say hello to someone."""
    return f"Hello, {name}!"

@mcp.tool() 
def get_time():
    """Get current timestamp."""
    import datetime
    return datetime.datetime.now().isoformat()

def main():
    mcp.run()

if __name__ == '__main__':
    main()
```

### 3. Entry Point Configuration
Update `pyproject.toml`:
```toml
[project.scripts]
"remote-mcp-server" = "remote_mcp_server.mcp_server:main"
```

### 4. AWS Lambda Integration (Optional)
To maintain Lambda compatibility, create a wrapper:

```python
# lambda_handler.py
import json
from mcp_server import mcp

def lambda_handler(event, context):
    # Extract MCP request from Lambda event
    mcp_request = json.loads(event.get('body', '{}'))
    
    # Process MCP request
    result = mcp.handle_request(mcp_request)
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
```

### 5. Template Updates
Update `template.yaml`:
- Change handler to point to Lambda wrapper
- Add environment variables for MCP configuration
- Update runtime to support MCP dependencies

### 6. Development Workflow

**Local Development:**
```bash
# Run MCP server locally
uv run remote-mcp-server

# Or with FastMCP's development mode
uv run python -m remote_mcp_server.mcp_server
```

**Client Integration:**
```json
{
  "mcpServers": {
    "remote-mcp-server": {
      "command": "uvx",
      "args": ["remote-mcp-server@latest"],
      "env": {}
    }
  }
}
```

## Key Implementation Principles

1. **Keep It Simple**: Start with basic tools and expand gradually
2. **Security First**: Validate inputs and implement proper access controls
3. **Error Handling**: Provide clear error messages and handle edge cases
4. **Documentation**: Use clear tool descriptions for AI model understanding
5. **Testability**: Create unit tests for tool functions
6. **Configuration**: Allow behavior modification via CLI arguments

## Benefits of MCP Transformation

- **AI Integration**: Direct interaction with AI assistants
- **Standardized Interface**: Consistent API across different tools
- **Extensibility**: Easy to add new tools and capabilities
- **Security**: Built-in validation and access control patterns
- **Scalability**: Can handle multiple concurrent AI interactions

This transformation would evolve the simple "hello world" function into a proper MCP server that can be integrated with AI assistants while maintaining the simplicity of the original implementation.