#!/bin/bash
#
# Build script for Remote MCP Server
# Builds application, Docker images, and SAM artifacts
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
BUILD_DOCKER=${BUILD_DOCKER:-true}
BUILD_SAM=${BUILD_SAM:-true}
DOCKER_TAG=${DOCKER_TAG:-remote-mcp-server}
DOCKER_REGISTRY=${DOCKER_REGISTRY:-}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            BUILD_DOCKER=false
            shift
            ;;
        --skip-sam)
            BUILD_SAM=false
            shift
            ;;
        --docker-tag)
            DOCKER_TAG="$2"
            shift 2
            ;;
        --docker-registry)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --skip-docker          Skip Docker build"
            echo "  --skip-sam             Skip SAM build"
            echo "  --docker-tag TAG       Docker image tag (default: remote-mcp-server)"
            echo "  --docker-registry URL  Docker registry URL"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Ensure dependencies are installed
log_section "Installing Dependencies"
if ! command -v uv &> /dev/null; then
    log_error "uv is not installed. Please install it from https://docs.astral.sh/uv/"
    exit 1
fi

log_info "Installing/updating dependencies..."
uv sync

# Run tests first
log_section "Pre-build Validation"
log_info "Running tests before build..."
if ! ./scripts/test.sh --skip-slow; then
    log_error "Tests failed. Aborting build."
    exit 1
fi

# Clean previous builds
log_section "Cleaning Previous Builds"
log_info "Cleaning build artifacts..."
rm -rf .aws-sam/
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/

# Build Python package
log_section "Building Python Package"
log_info "Building Python wheel..."
uv build

if [[ -f "dist/"*.whl ]]; then
    log_success "Python package built successfully"
else
    log_error "Python package build failed"
    exit 1
fi

# Build Docker image
if [[ "$BUILD_DOCKER" == "true" ]]; then
    log_section "Building Docker Images"
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not available, skipping Docker build"
    else
        log_info "Building production Docker image..."
        if docker build -t "${DOCKER_TAG}:latest" --target production .; then
            log_success "Production Docker image built: ${DOCKER_TAG}:latest"
        else
            log_error "Docker build failed"
            exit 1
        fi
        
        log_info "Building development Docker image..."
        if docker build -t "${DOCKER_TAG}:dev" --target development .; then
            log_success "Development Docker image built: ${DOCKER_TAG}:dev"
        else
            log_warning "Development Docker image build failed"
        fi
        
        # Tag with registry if provided
        if [[ -n "$DOCKER_REGISTRY" ]]; then
            log_info "Tagging images for registry ${DOCKER_REGISTRY}..."
            docker tag "${DOCKER_TAG}:latest" "${DOCKER_REGISTRY}/${DOCKER_TAG}:latest"
            docker tag "${DOCKER_TAG}:dev" "${DOCKER_REGISTRY}/${DOCKER_TAG}:dev"
            log_success "Images tagged for registry"
        fi
        
        # Show image sizes
        log_info "Docker image sizes:"
        docker images "${DOCKER_TAG}" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
    fi
fi

# Build SAM application
if [[ "$BUILD_SAM" == "true" ]]; then
    log_section "Building SAM Application"
    
    if ! command -v sam &> /dev/null; then
        log_warning "SAM CLI not available, skipping SAM build"
    else
        log_info "Building SAM application..."
        if sam build --parallel; then
            log_success "SAM application built successfully"
        else
            log_error "SAM build failed"
            exit 1
        fi
        
        log_info "Validating SAM template..."
        if sam validate --lint; then
            log_success "SAM template is valid"
        else
            log_error "SAM template validation failed"
            exit 1
        fi
    fi
fi

# Generate build info
log_section "Build Information"
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

cat > build-info.json << EOF
{
  "build_time": "$BUILD_TIME",
  "git_commit": "$GIT_COMMIT",
  "git_branch": "$GIT_BRANCH",
  "docker_tag": "$DOCKER_TAG",
  "docker_registry": "$DOCKER_REGISTRY"
}
EOF

log_info "Build completed at: $BUILD_TIME"
log_info "Git commit: $GIT_COMMIT"
log_info "Git branch: $GIT_BRANCH"

# Show build artifacts
log_section "Build Artifacts"
if [[ -d "dist" ]]; then
    log_info "Python packages:"
    ls -la dist/
fi

if [[ "$BUILD_DOCKER" == "true" ]] && command -v docker &> /dev/null; then
    log_info "Docker images:"
    docker images "${DOCKER_TAG}" --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"
fi

if [[ "$BUILD_SAM" == "true" ]] && [[ -d ".aws-sam" ]]; then
    log_info "SAM artifacts:"
    find .aws-sam -name "*.zip" -o -name "template.yaml" | head -10
fi

log_success "Build completed successfully!"
log_info "Next steps:"
log_info "  - Test locally: docker run -p 3000:3000 ${DOCKER_TAG}:latest"
log_info "  - Deploy SAM: ./scripts/deploy.sh"
if [[ -n "$DOCKER_REGISTRY" ]]; then
    log_info "  - Push Docker: docker push ${DOCKER_REGISTRY}/${DOCKER_TAG}:latest"
fi