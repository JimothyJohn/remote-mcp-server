# Contributing to Remote MCP Server

Thank you for your interest in contributing to Remote MCP Server! This document provides guidelines and instructions for contributing to the project.

## 🌟 Code of Conduct

This project is committed to providing a welcoming and inclusive environment for all contributors. We expect all participants to adhere to our code of conduct:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Be constructive in discussions and code reviews
- Focus on what's best for the community and project
- Show empathy towards other community members

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+**: Required for development
- **UV**: Modern Python package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker**: For containerized development and testing
- **Git**: For version control
- **AWS SAM CLI**: For testing Lambda deployments (optional)

### Development Setup

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/yourusername/remote-mcp-server.git
   cd remote-mcp-server
   
   # Add upstream remote
   git remote add upstream https://github.com/original-owner/remote-mcp-server.git
   ```

2. **Install Dependencies**
   ```bash
   # Install all dependencies including development tools
   uv sync --group dev
   
   # Install pre-commit hooks
   uv run pre-commit install
   ```

3. **Verify Setup**
   ```bash
   # Run tests to ensure everything works
   ./scripts/test.sh
   
   # Start the MCP server
   uv run python -m remote_mcp_server.mcp_server --help
   ```

### Development Environment

We provide several ways to work on the project:

#### Local Development
```bash
# Start MCP server in development mode
uv run python -m remote_mcp_server.mcp_server --log-level DEBUG

# Run tests with coverage
uv run pytest --cov=remote_mcp_server --cov-report=html

# Start development server with hot reload
./scripts/local-dev.sh
```

#### Docker Development
```bash
# Build and run development container
docker-compose up dev

# Run tests in container
docker-compose run --rm test

# Run linting in container
docker-compose run --rm lint
```

## 🔧 Development Workflow

### Branch Naming

Use descriptive branch names with prefixes:

- `feature/add-new-tool` - New features
- `fix/handle-error-case` - Bug fixes  
- `docs/update-readme` - Documentation updates
- `refactor/simplify-handler` - Code refactoring
- `test/improve-coverage` - Test improvements

### Making Changes

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Write clear, focused commits
   - Include tests for new functionality
   - Update documentation as needed
   - Follow the existing code style

3. **Test Your Changes**
   ```bash
   # Run full test suite
   ./scripts/test.sh
   
   # Run specific test categories
   uv run pytest tests/unit/
   uv run pytest tests/integration/
   
   # Check code quality
   uv run ruff check .
   uv run black --check .
   uv run mypy remote_mcp_server/
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add new MCP tool for data processing"
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes

**Examples:**
```bash
feat(tools): add data validation tool
fix(lambda): handle empty request body
docs(readme): update deployment instructions
test(integration): add API Gateway tests
```

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_mcp_server.py  # Core MCP server tests
│   └── test_handler.py     # Lambda handler tests
├── integration/            # Integration tests
│   ├── test_mcp_integration.py   # End-to-end MCP tests
│   └── test_api_gateway.py       # API Gateway tests
└── conftest.py            # Shared test fixtures
```

### Writing Tests

1. **Unit Tests**
   - Test individual functions and classes
   - Mock external dependencies
   - Aim for high coverage of core logic

2. **Integration Tests**
   - Test complete workflows
   - Test API endpoints end-to-end
   - Test MCP protocol interactions

3. **Test Examples**
   ```python
   import pytest
   from remote_mcp_server.mcp_server import hello_world
   
   def test_hello_world_default():
       """Test hello_world with default name."""
       result = hello_world()
       assert "Hello, World!" in result
   
   def test_hello_world_custom_name():
       """Test hello_world with custom name."""
       result = hello_world("Alice")
       assert "Hello, Alice!" in result
   
   @pytest.mark.asyncio
   async def test_mcp_server_tools():
       """Test MCP server tool registration."""
       from remote_mcp_server.mcp_server import mcp
       tools = await mcp.list_tools()
       assert len(tools) > 0
   ```

### Running Tests

```bash
# All tests with coverage
./scripts/test.sh

# Specific test files
uv run pytest tests/unit/test_mcp_server.py -v

# Tests with specific markers
uv run pytest -m "not slow" -v

# Integration tests (requires AWS setup)
export AWS_SAM_STACK_NAME=remote-mcp-server
uv run pytest tests/integration/ -v
```

## 📝 Documentation Guidelines

### Documentation Types

1. **Code Documentation**
   - Clear docstrings for all functions and classes
   - Type hints for all parameters and return values
   - Examples in docstrings when helpful

2. **README Updates**
   - Update features list for new capabilities
   - Add usage examples for new tools
   - Update installation instructions if needed

3. **API Documentation**
   - Document new endpoints in `docs/api.md`
   - Include request/response examples
   - Note any breaking changes

### Documentation Style

```python
def calculate_sum(numbers: list[float]) -> float:
    """Calculate the sum of a list of numbers.
    
    This tool sums all numbers in the provided list with validation
    to ensure reasonable input sizes and proper error handling.
    
    Args:
        numbers: List of numbers to sum (max 100 items)
        
    Returns:
        The sum of all numbers as a float
        
    Raises:
        ValueError: If the list is empty or contains more than 100 items
        
    Examples:
        >>> calculate_sum([1, 2, 3])
        6.0
        >>> calculate_sum([1.5, 2.5])
        4.0
    """
```

## 🔍 Code Quality Standards

### Code Style

We use automated tools to maintain consistent code quality:

- **Ruff**: Fast Python linter for code quality
- **Black**: Uncompromising code formatter  
- **MyPy**: Static type checking
- **Pre-commit**: Automated checks before commits

### Quality Checks

All code must pass these checks:

```bash
# Linting
uv run ruff check .

# Formatting  
uv run black --check .

# Type checking
uv run mypy remote_mcp_server/

# Security scanning
uv run safety check
```

### Performance Guidelines

- Keep Lambda cold starts under 1 second
- Minimize memory usage in containerized deployments
- Use efficient data structures and algorithms
- Add performance tests for critical paths

### Security Guidelines

- Validate all inputs using Pydantic models
- Never log sensitive information
- Use environment variables for configuration
- Follow AWS security best practices
- Scan dependencies for vulnerabilities

## 🐛 Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Environment Information**
   - Python version
   - Operating system
   - UV version
   - Docker version (if applicable)

2. **Reproduction Steps**
   - Clear steps to reproduce the issue
   - Expected vs actual behavior
   - Error messages or logs

3. **Additional Context**
   - Configuration files (sanitized)
   - Screenshots if relevant
   - Related issues or PRs

### Feature Requests

For new features, please provide:

1. **Use Case Description**
   - What problem does this solve?
   - Who would benefit from this feature?

2. **Proposed Solution**
   - High-level implementation approach
   - Alternative solutions considered

3. **Acceptance Criteria**
   - How do we know when it's complete?
   - What tests should be added?

## 🚀 Pull Request Process

### Before Submitting

1. **Check Requirements**
   - [ ] All tests pass
   - [ ] Code follows style guidelines
   - [ ] Documentation is updated
   - [ ] No merge conflicts
   - [ ] Commit messages follow convention

2. **Self Review**
   - [ ] Code is clear and well-commented
   - [ ] Edge cases are handled
   - [ ] Error handling is appropriate
   - [ ] Performance impact is considered

### Pull Request Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix
- [ ] New feature  
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (please describe)

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated  
- [ ] Manual testing completed
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Automated Checks**
   - CI pipeline must pass
   - All quality checks must pass
   - No security vulnerabilities

2. **Code Review**
   - At least one maintainer review required
   - Address all feedback before merging
   - Maintain respectful discussion

3. **Merging**
   - Use squash merge for feature branches
   - Update changelog for significant changes
   - Tag releases according to semantic versioning

## 📊 Project Maintenance

### Release Process

1. **Version Bumping**
   - Follow semantic versioning
   - Update version in `pyproject.toml`
   - Update `CHANGELOG.md`

2. **Testing**
   - Full test suite passes
   - Manual deployment testing
   - Performance regression testing

3. **Documentation**
   - Update API documentation
   - Update deployment guides
   - Review and update README

### Continuous Integration

Our CI/CD pipeline includes:

- **Code Quality**: Linting, formatting, type checking
- **Testing**: Unit and integration tests with coverage
- **Security**: Dependency vulnerability scanning
- **Building**: Docker images and SAM artifacts
- **Deployment**: Automated staging deployment

### Monitoring and Observability

Production deployments include:

- **Health Checks**: Automated endpoint monitoring
- **Logging**: Structured logging with request tracing  
- **Metrics**: Performance and error rate monitoring
- **Alerting**: Automated alerts for issues

## 🙏 Recognition

Contributors will be recognized in:

- **README**: Contributors section
- **Releases**: Release notes acknowledgments
- **GitHub**: Contributor graphs and statistics

Thank you for contributing to Remote MCP Server! Your contributions help make AI integration more accessible and robust for everyone.

---

## 📞 Getting Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/remote-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/remote-mcp-server/discussions)
- **Documentation**: [Project Documentation](docs/)
- **Examples**: [Example Configurations](examples/)

**Happy coding! 🎉**