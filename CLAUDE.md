# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Model Context Protocol (MCP) server** with **AWS Lambda compatibility**. It demonstrates how to build AI-compatible tools that can run both as standalone MCP servers for AI assistants and as AWS serverless functions. The project uses Python 3.11+ and follows modern development practices with comprehensive testing, CI/CD, and Docker support.

## Architecture

### Core Components
- **MCP Server**: `remote_mcp_server/mcp_server.py` - Main MCP server with tool definitions
- **Lambda Handler**: `remote-mcp-server/app.py` - AWS Lambda wrapper (backward compatibility)
- **Entry Points**: Both MCP server and Lambda function entry points
- **Infrastructure**: Defined in `template.yaml` using AWS SAM format
- **Configuration**: SAM deployment settings in `samconfig.toml`, project config in `pyproject.toml`

### Dual Compatibility Design
The application can run as:
1. **MCP Server**: Direct integration with AI assistants via MCP protocol
2. **AWS Lambda**: Serverless HTTP API with health checks and backward compatibility
3. **Docker Container**: Containerized deployment for any environment

## Development Commands

### Dependencies and Environment
```bash
# Install all dependencies with dev tools
uv sync --group dev

# Install for production only
uv sync

# Run MCP server locally
uv run remote-mcp-server

# Run with custom settings
uv run remote-mcp-server --port 8000 --log-level DEBUG
```

### Testing (Comprehensive Suite)
```bash
# Run complete test suite with linting
./scripts/test.sh

# Run unit tests only
uv run pytest tests/unit/ -v

# Run integration tests (requires deployed stack)
AWS_SAM_STACK_NAME=remote-mcp-server uv run pytest tests/integration/ -m integration

# Run with coverage reporting
uv run pytest --cov=remote_mcp_server --cov-report=html

# Run specific test types
uv run pytest -m "not slow"  # Skip slow tests
uv run pytest -m unit        # Unit tests only
uv run pytest -m integration # Integration tests only
```

### Code Quality and Linting
```bash
# Run all quality checks
./scripts/test.sh

# Individual tools
uv run ruff check .           # Linting
uv run black .                # Code formatting  
uv run mypy .                 # Type checking
uv run pytest --cov          # Test coverage

# Fix formatting issues
uv run ruff check --fix .
uv run black .
```

### AWS SAM Operations
```bash
# Build the application
sam build

# Validate template
sam validate --lint

# Deploy to AWS
sam deploy --guided

# Local development
sam local start-api           # Start API Gateway locally
sam local start-lambda        # Start Lambda locally
sam local invoke             # Invoke function locally

# Deploy with parameters
sam deploy --parameter-overrides Environment=staging
```

### Docker Operations
```bash
# Build Docker image
docker build -t remote-mcp-server .

# Run container
docker run -p 3000:3000 remote-mcp-server

# Run with environment variables
docker run -e LOG_LEVEL=DEBUG -p 3000:3000 remote-mcp-server

# Docker Compose
docker-compose up -d          # Start services
docker-compose logs -f        # View logs
docker-compose down           # Stop services
```

## Key Files Structure

### Core Application
- `remote_mcp_server/mcp_server.py` - Main MCP server implementation with tools
- `remote_mcp_server/__init__.py` - Package initialization and version info
- `remote-mcp-server/app.py` - Lambda handler wrapper for backward compatibility
- `main.py` - Local development entry point (legacy)

### Configuration
- `pyproject.toml` - Project dependencies, build config, tool settings
- `template.yaml` - SAM template defining AWS resources  
- `samconfig.toml` - SAM CLI configuration and deployment parameters
- `Dockerfile` - Container build configuration
- `docker-compose.yml` - Local development environment

### Testing
- `tests/conftest.py` - Pytest configuration and shared fixtures
- `tests/unit/test_mcp_server.py` - Unit tests for MCP tools and functionality
- `tests/unit/test_handler.py` - Unit tests for Lambda handler (backward compatibility)
- `tests/integration/test_mcp_integration.py` - Integration tests for MCP protocol
- `tests/integration/test_api_gateway.py` - API Gateway integration tests

### CI/CD and Scripts
- `.github/workflows/ci-cd.yml` - GitHub Actions CI/CD pipeline
- `scripts/test.sh` - Comprehensive test and quality check script
- `scripts/build.sh` - Build application and Docker image
- `scripts/deploy.sh` - Deploy with validation
- `scripts/local-dev.sh` - Local development environment setup

### Documentation
- `README.md` - Comprehensive project documentation
- `MCP.md` - MCP architecture analysis and transformation guide
- `CLAUDE.md` - This file (development guidance)

## MCP Tools Available

The server provides these tools for AI assistants:

1. **`hello_world(name: str = "World")`** - Greet someone with a custom message
2. **`get_current_time()`** - Get current ISO timestamp
3. **`echo_message(message: str, repeat: int = 1)`** - Echo message with optional repetition
4. **`get_server_info()`** - Get server status and metadata
5. **`calculate_sum(numbers: list[float])`** - Calculate sum of numbers (max 100)

## Testing Strategy

### Test Types
- **Unit Tests**: Individual function testing with mocking
- **Integration Tests**: MCP protocol and AWS service integration
- **End-to-End Tests**: Full deployment testing
- **Performance Tests**: Load and response time testing

### Test Markers
- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests requiring services
- `@pytest.mark.slow` - Tests taking >1 second
- Use `-m "not slow"` to skip time-consuming tests during development

### Coverage Requirements
- Minimum 80% code coverage
- All new features must have tests
- Critical paths require both unit and integration tests

## Development Workflow

### Local Development
1. Install dependencies: `uv sync --group dev`
2. Install pre-commit hooks: `pre-commit install`
3. Run tests: `./scripts/test.sh`
4. Start MCP server: `uv run remote-mcp-server`
5. Test with MCP client or curl commands

### Deployment Workflow
1. Run full test suite: `./scripts/test.sh`
2. Build application: `sam build`
3. Deploy: `sam deploy`
4. Run integration tests: `AWS_SAM_STACK_NAME=stack-name uv run pytest tests/integration/`
5. Validate deployment: Check health endpoint

### CI/CD Pipeline
The GitHub Actions workflow runs:
1. Code quality checks (ruff, black, mypy)
2. Security scanning
3. Unit test suite with coverage
4. Build Docker image and SAM artifacts
5. Deploy to staging environment
6. Run integration tests
7. Deploy to production (on main branch)

## Environment Variables

### Development
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT` - Environment name (development, staging, production)
- `PORT` - Server port for MCP server (default: 3000)

### Testing  
- `AWS_SAM_STACK_NAME` - Stack name for integration tests
- `AWS_REGION` - AWS region for testing (default: us-east-1)

### Deployment
- `AWS_PROFILE` - AWS profile for deployment
- `STACK_NAME` - CloudFormation stack name

## Common Development Tasks

### Adding New MCP Tools
1. Add tool function with `@mcp.tool()` decorator in `mcp_server.py`
2. Add unit tests in `tests/unit/test_mcp_server.py`
3. Add integration tests in `tests/integration/test_mcp_integration.py`
4. Update documentation in README.md

### Debugging
- Use `--log-level DEBUG` for verbose logging
- Check CloudWatch logs for Lambda issues
- Use `sam local` for local Lambda testing
- Test MCP protocol with curl or MCP client

### Performance Optimization  
- Monitor Lambda cold starts
- Check test performance with `-m slow`
- Use Docker for consistent local testing
- Monitor API Gateway response times

## Security Considerations

- Input validation on all MCP tools
- Error handling prevents information disclosure
- AWS IAM least privilege principles
- Container security scanning in CI/CD
- Dependency vulnerability scanning with safety

## Troubleshooting

### Common Issues
- **Import errors**: Ensure `uv sync` has been run
- **Test failures**: Check AWS credentials for integration tests
- **Deployment fails**: Verify SAM CLI version and AWS permissions
- **MCP connection**: Check port and firewall settings

### Debug Commands
```bash
# Check MCP server status
curl http://localhost:3000/health

# Validate SAM template
sam validate --lint

# Check dependencies
uv tree

# Run specific test with output
uv run pytest tests/unit/test_mcp_server.py::TestMCPTools::test_hello_world_default -v
```