#!/bin/bash
#
# Deployment script for Remote MCP Server
# Deploys to AWS using SAM with validation and health checks
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
if [[ ! -f "template.yaml" ]]; then
    log_error "template.yaml not found. Please run from the project root directory."
    exit 1
fi

# Configuration
STACK_NAME=${STACK_NAME:-remote-mcp-server}
ENVIRONMENT=${ENVIRONMENT:-staging}
AWS_REGION=${AWS_REGION:-us-east-1}
GUIDED=${GUIDED:-false}
CAPABILITIES=${CAPABILITIES:-CAPABILITY_IAM}
CONFIRM_CHANGESET=${CONFIRM_CHANGESET:-true}
SKIP_TESTS=${SKIP_TESTS:-false}
HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-300}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --guided)
            GUIDED=true
            shift
            ;;
        --no-confirm)
            CONFIRM_CHANGESET=false
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --stack-name NAME      CloudFormation stack name (default: remote-mcp-server)"
            echo "  --environment ENV      Environment (default: staging)"
            echo "  --region REGION        AWS region (default: us-east-1)"
            echo "  --guided               Use SAM guided deployment"
            echo "  --no-confirm           Skip changeset confirmation"
            echo "  --skip-tests           Skip pre-deployment tests"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate prerequisites
log_section "Validating Prerequisites"

if ! command -v sam &> /dev/null; then
    log_error "SAM CLI is not installed. Please install it from https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it and configure credentials."
    exit 1
fi

# Check AWS credentials
log_info "Checking AWS credentials..."
if ! aws sts get-caller-identity --region "$AWS_REGION" >/dev/null 2>&1; then
    log_error "AWS credentials not configured or invalid"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_info "Deploying to AWS Account: $AWS_ACCOUNT_ID in region: $AWS_REGION"

# Pre-deployment tests
if [[ "$SKIP_TESTS" != "true" ]]; then
    log_section "Pre-deployment Testing"
    log_info "Running tests before deployment..."
    if ! ./scripts/test.sh --skip-integration; then
        log_error "Pre-deployment tests failed. Use --skip-tests to override."
        exit 1
    fi
    log_success "Pre-deployment tests passed"
fi

# Build application
log_section "Building Application"
if [[ ! -d ".aws-sam" ]] || [[ "template.yaml" -nt ".aws-sam/build/template.yaml" ]]; then
    log_info "Building SAM application..."
    if ! sam build --parallel; then
        log_error "SAM build failed"
        exit 1
    fi
    log_success "SAM build completed"
else
    log_info "SAM application already built and up-to-date"
fi

# Deploy application
log_section "Deploying Application"

DEPLOY_ARGS=(
    --stack-name "$STACK_NAME"
    --region "$AWS_REGION"
    --capabilities "$CAPABILITIES"
    --parameter-overrides "Environment=$ENVIRONMENT"
    --tags "Environment=$ENVIRONMENT Project=remote-mcp-server"
)

if [[ "$GUIDED" == "true" ]]; then
    DEPLOY_ARGS+=(--guided)
else
    DEPLOY_ARGS+=(--no-confirm-changeset)
    if [[ "$CONFIRM_CHANGESET" == "true" ]]; then
        DEPLOY_ARGS+=(--confirm-changeset)
    fi
fi

log_info "Deploying stack: $STACK_NAME"
log_info "Environment: $ENVIRONMENT"
log_info "Region: $AWS_REGION"

if sam deploy "${DEPLOY_ARGS[@]}"; then
    log_success "Deployment completed successfully"
else
    log_error "Deployment failed"
    exit 1
fi

# Get stack outputs
log_section "Deployment Information"
log_info "Retrieving stack outputs..."

STACK_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs' \
    --output json)

if [[ "$STACK_OUTPUTS" != "null" ]]; then
    echo "$STACK_OUTPUTS" | jq -r '.[] | "\(.OutputKey): \(.OutputValue)"'
    
    # Extract API Gateway URL for health check
    API_URL=$(echo "$STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="RemoteMcpServerApi") | .OutputValue' 2>/dev/null || echo "")
else
    log_warning "No stack outputs found"
fi

# Health check
if [[ -n "$API_URL" ]]; then
    log_section "Health Check"
    log_info "Testing deployed endpoint..."
    
    HEALTH_URL="${API_URL%/}/health"
    log_info "Health check URL: $HEALTH_URL"
    
    # Wait for API Gateway to be ready
    log_info "Waiting for API Gateway to be ready..."
    sleep 30
    
    HEALTH_CHECK_START=$(date +%s)
    while true; do
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - HEALTH_CHECK_START))
        
        if [[ $ELAPSED -gt $HEALTH_CHECK_TIMEOUT ]]; then
            log_error "Health check timeout after ${HEALTH_CHECK_TIMEOUT}s"
            break
        fi
        
        if curl -f -s "$HEALTH_URL" >/dev/null 2>&1; then
            log_success "Health check passed"
            
            # Test the main endpoint
            log_info "Testing main endpoint..."
            if RESPONSE=$(curl -s "$API_URL" 2>/dev/null); then
                if echo "$RESPONSE" | jq -e '.message' >/dev/null 2>&1; then
                    log_success "Main endpoint responding correctly"
                    echo "Response: $(echo "$RESPONSE" | jq -c .)"
                else
                    log_warning "Main endpoint responding but format unexpected"
                fi
            else
                log_warning "Main endpoint not responding"
            fi
            
            # Test POST endpoint
            log_info "Testing POST endpoint..."
            if POST_RESPONSE=$(curl -s -X POST "$API_URL" \
                -H "Content-Type: application/json" \
                -d '{"test": "deployment validation"}' 2>/dev/null); then
                if echo "$POST_RESPONSE" | jq -e '.message' >/dev/null 2>&1; then
                    log_success "POST endpoint responding correctly"
                else
                    log_warning "POST endpoint responding but format unexpected"
                fi
            else
                log_warning "POST endpoint not responding"
            fi
            
            break
        else
            log_info "Waiting for endpoint to be ready... (${ELAPSED}s elapsed)"
            sleep 10
        fi
    done
else
    log_warning "API Gateway URL not found in stack outputs, skipping health check"
fi

# Integration tests (if available)
if [[ "$SKIP_TESTS" != "true" ]] && [[ -n "$API_URL" ]]; then
    log_section "Post-deployment Integration Tests"
    log_info "Running integration tests against deployed stack..."
    
    export AWS_SAM_STACK_NAME="$STACK_NAME"
    
    if uv run pytest tests/integration/ -m integration -v --tb=short; then
        log_success "Integration tests passed"
    else
        log_error "Integration tests failed"
        log_warning "Deployment completed but post-deployment tests failed"
        exit 1
    fi
fi

# Deployment summary
log_section "Deployment Summary"
log_success "Deployment completed successfully!"

if [[ -n "$API_URL" ]]; then
    log_info "API Endpoint: $API_URL"
    log_info "Health Check: ${API_URL%/}/health"
fi

log_info "Stack Name: $STACK_NAME"
log_info "Environment: $ENVIRONMENT"
log_info "Region: $AWS_REGION"
log_info "Account: $AWS_ACCOUNT_ID"

# Save deployment info
DEPLOY_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > deploy-info.json << EOF
{
  "deployment_time": "$DEPLOY_TIME",
  "stack_name": "$STACK_NAME",
  "environment": "$ENVIRONMENT",
  "region": "$AWS_REGION",
  "account_id": "$AWS_ACCOUNT_ID",
  "api_url": "$API_URL"
}
EOF

log_info "Deployment info saved to deploy-info.json"

# Next steps
log_info "Next steps:"
log_info "  - Test the API: curl $API_URL"
if [[ -n "$API_URL" ]]; then
    log_info "  - Test POST: curl -X POST $API_URL -H 'Content-Type: application/json' -d '{\"test\":\"data\"}'"
fi
log_info "  - Monitor logs: sam logs -n $STACK_NAME --tail"
log_info "  - Update stack: sam deploy (with same parameters)"
log_info "  - Delete stack: sam delete --stack-name $STACK_NAME"