#!/bin/bash
#
# Local development environment setup script
# Starts local MCP server, SAM local, or Docker containers
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
MODE=${MODE:-mcp}
PORT=${PORT:-3000}
LOG_LEVEL=${LOG_LEVEL:-DEBUG}
ENVIRONMENT=${ENVIRONMENT:-development}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Modes:"
            echo "  mcp         Start MCP server (default)"
            echo "  sam         Start SAM local API"
            echo "  lambda      Start SAM local Lambda"
            echo "  docker      Start Docker container"
            echo "  docker-dev  Start Docker development container"
            echo "  test        Run in test mode with file watching"
            echo ""
            echo "Options:"
            echo "  --mode MODE        Development mode (see above)"
            echo "  --port PORT        Port to use (default: 3000)"
            echo "  --log-level LEVEL  Log level (default: DEBUG)"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set environment variables
export LOG_LEVEL="$LOG_LEVEL"
export ENVIRONMENT="$ENVIRONMENT"
export PORT="$PORT"

# Ensure dependencies are installed
log_section "Setting up Development Environment"
if ! command -v uv &> /dev/null; then
    log_error "uv is not installed. Please install it from https://docs.astral.sh/uv/"
    exit 1
fi

log_info "Installing/updating development dependencies..."
uv sync --group dev

# Create necessary directories
mkdir -p logs
mkdir -p .vscode

# Function to handle cleanup
cleanup() {
    log_info "Shutting down development environment..."
    
    # Kill background processes
    if [[ -f ".dev-pids" ]]; then
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done < .dev-pids
        rm -f .dev-pids
    fi
    
    # Docker cleanup if needed
    if [[ "$MODE" == "docker"* ]]; then
        docker-compose down 2>/dev/null || true
    fi
    
    log_info "Cleanup completed"
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Mode-specific startup
case "$MODE" in
    "mcp")
        log_section "Starting MCP Server"
        log_info "Mode: MCP Server"
        log_info "Port: $PORT"
        log_info "Log Level: $LOG_LEVEL"
        log_info "Environment: $ENVIRONMENT"
        
        log_info "Starting MCP server..."
        log_info "Press Ctrl+C to stop"
        
        exec uv run remote-mcp-server --port "$PORT" --log-level "$LOG_LEVEL"
        ;;
        
    "sam")
        log_section "Starting SAM Local API"
        if ! command -v sam &> /dev/null; then
            log_error "SAM CLI not found. Please install AWS SAM CLI."
            exit 1
        fi
        
        log_info "Building SAM application..."
        sam build
        
        log_info "Starting SAM local API on port $PORT..."
        log_info "API will be available at: http://localhost:$PORT"
        log_info "Press Ctrl+C to stop"
        
        exec sam local start-api --port "$PORT" --env-vars env.json
        ;;
        
    "lambda")
        log_section "Starting SAM Local Lambda"
        if ! command -v sam &> /dev/null; then
            log_error "SAM CLI not found. Please install AWS SAM CLI."
            exit 1
        fi
        
        log_info "Building SAM application..."
        sam build
        
        log_info "Starting SAM local Lambda..."
        log_info "Use 'sam local invoke' to test functions"
        log_info "Press Ctrl+C to stop"
        
        exec sam local start-lambda
        ;;
        
    "docker")
        log_section "Starting Docker Container"
        if ! command -v docker &> /dev/null; then
            log_error "Docker not found. Please install Docker."
            exit 1
        fi
        
        log_info "Building Docker image..."
        docker build -t remote-mcp-server:dev --target development .
        
        log_info "Starting Docker container on port $PORT..."
        log_info "Server will be available at: http://localhost:$PORT"
        log_info "Press Ctrl+C to stop"
        
        exec docker run -it --rm \
            -p "$PORT:3000" \
            -e LOG_LEVEL="$LOG_LEVEL" \
            -e ENVIRONMENT="$ENVIRONMENT" \
            -v "$(pwd)/remote_mcp_server:/app/remote_mcp_server" \
            remote-mcp-server:dev
        ;;
        
    "docker-dev")
        log_section "Starting Docker Development Environment"
        if ! command -v docker-compose &> /dev/null; then
            log_error "Docker Compose not found. Please install Docker Compose."
            exit 1
        fi
        
        log_info "Starting Docker Compose development environment..."
        log_info "MCP Server will be available at: http://localhost:3000"
        log_info "Press Ctrl+C to stop all services"
        
        exec docker-compose up
        ;;
        
    "test")
        log_section "Starting Test Mode"
        log_info "Running in test mode with file watching..."
        
        # Start MCP server in background
        log_info "Starting MCP server in background..."
        uv run remote-mcp-server --port "$PORT" --log-level INFO > logs/mcp-server.log 2>&1 &
        MCP_PID=$!
        echo "$MCP_PID" > .dev-pids
        
        # Wait a moment for server to start
        sleep 2
        
        # Check if server started successfully
        if ! kill -0 "$MCP_PID" 2>/dev/null; then
            log_error "Failed to start MCP server"
            exit 1
        fi
        
        log_success "MCP server started (PID: $MCP_PID)"
        log_info "Server logs: tail -f logs/mcp-server.log"
        log_info "Health check: curl http://localhost:$PORT/health"
        
        # Start file watcher for tests
        log_info "Starting file watcher for automatic testing..."
        
        if command -v watchmedo &> /dev/null; then
            watchmedo auto-restart --directory=./ --pattern="*.py" --recursive \
                -- uv run pytest tests/unit/ -v
        else
            log_warning "watchdog not available, running tests once"
            uv run pytest tests/unit/ -v
            
            log_info "Install watchdog for file watching: uv add watchdog"
            log_info "Server running at http://localhost:$PORT"
            log_info "Press Ctrl+C to stop"
            
            # Keep script running
            while kill -0 "$MCP_PID" 2>/dev/null; do
                sleep 5
            done
        fi
        ;;
        
    *)
        log_error "Unknown mode: $MODE"
        log_error "Available modes: mcp, sam, lambda, docker, docker-dev, test"
        exit 1
        ;;
esac