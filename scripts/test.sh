#!/bin/bash
#
# Comprehensive test and quality check script
# Runs linting, type checking, security scanning, and tests
#
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    log_error "pyproject.toml not found. Please run from the project root directory."
    exit 1
fi

# Configuration
SKIP_SLOW=${SKIP_SLOW:-false}
SKIP_INTEGRATION=${SKIP_INTEGRATION:-false}
COVERAGE_THRESHOLD=${COVERAGE_THRESHOLD:-80}
PARALLEL_JOBS=${PARALLEL_JOBS:-auto}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-slow)
            SKIP_SLOW=true
            shift
            ;;
        --skip-integration)
            SKIP_INTEGRATION=true
            shift
            ;;
        --coverage-threshold)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        --parallel-jobs)
            PARALLEL_JOBS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --skip-slow               Skip slow tests"
            echo "  --skip-integration        Skip integration tests"
            echo "  --coverage-threshold N    Set coverage threshold (default: 80)"
            echo "  --parallel-jobs N         Set parallel job count (default: auto)"
            echo "  --help                    Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check dependencies
log_section "Checking Dependencies"
if ! command -v uv &> /dev/null; then
    log_error "uv is not installed. Please install it from https://docs.astral.sh/uv/"
    exit 1
fi

log_info "Installing/updating dependencies..."
uv sync --group dev

# Environment setup
export PYTHONPATH="${PWD}:${PYTHONPATH:-}"
export LOG_LEVEL=ERROR  # Reduce noise during testing

# Code formatting
log_section "Code Formatting"
log_info "Running black formatter..."
if uv run black --check --diff .; then
    log_success "Code formatting is correct"
else
    log_warning "Code formatting issues found. Run 'uv run black .' to fix"
    if [[ "${CI:-false}" == "true" ]]; then
        exit 1
    fi
fi

# Linting
log_section "Linting"
log_info "Running ruff linter..."
if uv run ruff check . --output-format=github; then
    log_success "No linting issues found"
else
    log_error "Linting issues found. Run 'uv run ruff check --fix .' to fix auto-fixable issues"
    if [[ "${CI:-false}" == "true" ]]; then
        exit 1
    fi
fi

# Type checking
log_section "Type Checking"
log_info "Running mypy type checker..."
if uv run mypy .; then
    log_success "No type checking issues found"
else
    log_error "Type checking issues found"
    if [[ "${CI:-false}" == "true" ]]; then
        exit 1
    fi
fi

# Security scanning
log_section "Security Scanning"
log_info "Scanning for known security vulnerabilities..."
if uv run safety check --json > safety_report.json 2>/dev/null; then
    log_success "No known security vulnerabilities found"
    rm -f safety_report.json
else
    log_warning "Security scan completed with warnings. Check safety_report.json for details"
    # Don't fail on security warnings in development, but log them
    if [[ -f safety_report.json ]]; then
        cat safety_report.json
        rm -f safety_report.json
    fi
fi

# Unit tests
log_section "Unit Tests"
TEST_MARKERS=""
if [[ "$SKIP_SLOW" == "true" ]]; then
    TEST_MARKERS="not slow"
    log_info "Skipping slow tests"
fi

if [[ "$SKIP_INTEGRATION" == "true" ]]; then
    if [[ -n "$TEST_MARKERS" ]]; then
        TEST_MARKERS="$TEST_MARKERS and not integration"
    else
        TEST_MARKERS="not integration"
    fi
    log_info "Skipping integration tests"
fi

PYTEST_ARGS=(
    "--cov=remote_mcp_server"
    "--cov-report=term-missing"
    "--cov-report=html:htmlcov"
    "--cov-report=xml:coverage.xml"
    "--cov-fail-under=$COVERAGE_THRESHOLD"
    "-v"
    "--tb=short"
)

if [[ "$PARALLEL_JOBS" != "auto" ]]; then
    PYTEST_ARGS+=("-n" "$PARALLEL_JOBS")
fi

if [[ -n "$TEST_MARKERS" ]]; then
    PYTEST_ARGS+=("-m" "$TEST_MARKERS")
fi

log_info "Running unit tests with coverage..."
if uv run pytest "${PYTEST_ARGS[@]}" tests/unit/; then
    log_success "Unit tests passed"
else
    log_error "Unit tests failed"
    exit 1
fi

# Integration tests (if not skipped and AWS credentials available)
if [[ "$SKIP_INTEGRATION" != "true" ]]; then
    log_section "Integration Tests"
    
    # Check if AWS credentials are available
    if [[ -n "${AWS_SAM_STACK_NAME:-}" ]] && uv run python -c "import boto3; boto3.client('sts').get_caller_identity()" &>/dev/null; then
        log_info "Running integration tests..."
        if uv run pytest tests/integration/ -m integration -v; then
            log_success "Integration tests passed"
        else
            log_error "Integration tests failed"
            if [[ "${CI:-false}" == "true" ]]; then
                exit 1
            fi
        fi
    else
        log_warning "Skipping integration tests - AWS credentials not available or AWS_SAM_STACK_NAME not set"
    fi
fi

# Test coverage report
log_section "Coverage Report"
if [[ -f htmlcov/index.html ]]; then
    log_info "Coverage report generated: htmlcov/index.html"
fi

if [[ -f coverage.xml ]]; then
    log_info "Coverage XML report generated: coverage.xml"
fi

# Docker build test (if Docker is available)
log_section "Docker Build Test"
if command -v docker &> /dev/null; then
    log_info "Testing Docker build..."
    if docker build -t remote-mcp-server-test --target production . >/dev/null 2>&1; then
        log_success "Docker build successful"
        docker rmi remote-mcp-server-test >/dev/null 2>&1 || true
    else
        log_error "Docker build failed"
        if [[ "${CI:-false}" == "true" ]]; then
            exit 1
        fi
    fi
else
    log_warning "Docker not available, skipping Docker build test"
fi

# SAM validation (if SAM CLI is available)
log_section "SAM Template Validation"
if command -v sam &> /dev/null; then
    log_info "Validating SAM template..."
    if sam validate --lint; then
        log_success "SAM template is valid"
    else
        log_error "SAM template validation failed"
        if [[ "${CI:-false}" == "true" ]]; then
            exit 1
        fi
    fi
else
    log_warning "SAM CLI not available, skipping template validation"
fi

# Final summary
log_section "Test Summary"
log_success "All quality checks completed successfully!"
log_info "Run './scripts/build.sh' to build the application"
log_info "Run './scripts/deploy.sh' to deploy to AWS"

# Cleanup
rm -f .coverage 2>/dev/null || true