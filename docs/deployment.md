# Deployment Guide

This guide covers deploying Remote MCP Server to various environments including AWS Lambda, Docker containers, and local development setups.

## AWS Lambda Deployment

### Prerequisites

1. **AWS CLI**: Configured with appropriate credentials
2. **SAM CLI**: Version 1.40+ recommended
3. **Python 3.11+**: For local development and testing
4. **UV**: Modern Python package manager

### Quick Deployment

```bash
# Clone repository
git clone https://github.com/yourusername/remote-mcp-server.git
cd remote-mcp-server

# Install dependencies
uv sync

# Build SAM application
sam build

# Deploy with guided setup
sam deploy --guided
```

### Configuration Parameters

During `sam deploy --guided`, you'll be prompted for:

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| Stack name | CloudFormation stack name | `remote-mcp-server` | `my-mcp-server` |
| AWS Region | Deployment region | Current region | `us-east-1` |
| Confirm changes | Review changes before deploy | `Y` | `Y` |
| Allow IAM role creation | Create Lambda execution role | `Y` | `Y` |
| Disable rollback | Keep stack on failure | `N` | `N` |

### Manual Parameter Configuration

Create `samconfig.toml` with custom parameters:

```toml
version = 0.1

[default.global.parameters]
stack_name = "remote-mcp-server-prod"

[default.deploy.parameters]
capabilities = "CAPABILITY_IAM"
confirm_changeset = true
resolve_s3 = true
parameter_overrides = [
    "Environment=production",
    "LogLevel=INFO",
    "MemorySize=256",
    "Timeout=30"
]

[default.build.parameters]
cached = true
parallel = true
```

### Environment-Specific Deployments

#### Development Environment
```bash
sam deploy \
  --stack-name remote-mcp-server-dev \
  --parameter-overrides \
    Environment=development \
    LogLevel=DEBUG \
    MemorySize=128
```

#### Staging Environment
```bash
sam deploy \
  --stack-name remote-mcp-server-staging \
  --parameter-overrides \
    Environment=staging \
    LogLevel=INFO \
    MemorySize=256
```

#### Production Environment
```bash
sam deploy \
  --stack-name remote-mcp-server-prod \
  --parameter-overrides \
    Environment=production \
    LogLevel=WARNING \
    MemorySize=512 \
    Timeout=60
```

### Post-Deployment Verification

```bash
# Get API Gateway URL
aws cloudformation describe-stacks \
  --stack-name remote-mcp-server \
  --query 'Stacks[0].Outputs[?OutputKey==`RemoteMcpServerApi`].OutputValue' \
  --output text

# Test health endpoint
curl https://your-api-url/Prod/health

# Test MCP endpoint
curl -X POST https://your-api-url/Prod/remote-mcp-server \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"hello_world","arguments":{"name":"Production"}},"id":1}'
```

### Infrastructure Components

The deployment creates:

1. **Lambda Function**
   - Runtime: Python 3.11
   - Memory: 256 MB (configurable)
   - Timeout: 30 seconds (configurable)
   - Environment variables for configuration

2. **API Gateway**
   - REST API with CORS enabled
   - Three endpoints: `/health`, `/remote-mcp-server` (GET/POST)
   - Request/response validation
   - Throttling and rate limiting

3. **IAM Role**
   - Least privilege execution role
   - CloudWatch Logs permissions
   - Basic Lambda execution permissions

4. **CloudWatch Resources**
   - Log group for Lambda function
   - Application Insights (optional)
   - Custom metrics and alarms

## Docker Deployment

### Building Images

#### Development Image
```bash
# Build with all development tools
docker build -t remote-mcp-server:dev .

# Or build development target specifically  
docker build -t remote-mcp-server:dev --target development .
```

#### Production Image
```bash
# Build optimized production image
docker build -t remote-mcp-server:prod --target production .

# Build with custom tag
docker build -t my-registry.com/remote-mcp-server:1.0.0 --target production .
```

### Running Containers

#### Local Development
```bash
# Run development container with hot reload
docker run -p 3000:3000 -v $(pwd):/app remote-mcp-server:dev

# Run with custom environment
docker run -p 3000:3000 \
  -e LOG_LEVEL=DEBUG \
  -e ENVIRONMENT=development \
  remote-mcp-server:dev
```

#### Production Container
```bash
# Run production container
docker run -p 8080:8080 remote-mcp-server:prod

# Run with restart policy
docker run -d \
  --name mcp-server \
  --restart unless-stopped \
  -p 8080:8080 \
  remote-mcp-server:prod
```

### Docker Compose

#### Development Setup
```bash
# Start all development services
docker-compose up -d

# Start specific service
docker-compose up dev

# View logs
docker-compose logs -f dev

# Run tests
docker-compose run --rm test

# Run linting
docker-compose run --rm lint
```

#### Production-like Testing
```bash
# Start production simulation
docker-compose up prod

# Test the production container
curl http://localhost:8080/health
```

### Environment Variables

| Variable | Description | Default | Docker |
|----------|-------------|---------|---------|
| `PORT` | Server port | `3000` | `8080` |
| `LOG_LEVEL` | Logging level | `INFO` | `INFO` |
| `ENVIRONMENT` | Environment name | `development` | `production` |

## Local Development Deployment

### Direct Python Execution

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode)
uv run python -m remote_mcp_server.mcp_server

# Run with custom parameters
uv run python -m remote_mcp_server.mcp_server --port 8000 --log-level DEBUG
```

### Local API Server

```bash
# Start HTTP server for testing
uv run python -c "
from remote_mcp_server.mcp_server import create_lambda_handler
import uvicorn
handler = create_lambda_handler()
# Run with uvicorn for development
uvicorn main:app --port 3000 --reload
"
```

### SAM Local Testing

```bash
# Start local API Gateway
sam local start-api --port 3000

# Test local endpoints
curl http://127.0.0.1:3000/health
curl http://127.0.0.1:3000/remote-mcp-server

# Invoke function directly
sam local invoke RemoteMcpServerFunction --event event.json

# Generate sample events
sam local generate-event apigateway aws-proxy > event.json
```

## Production Deployment Best Practices

### Security

1. **IAM Roles**
   ```yaml
   # Use least privilege principles
   Policies:
     - Version: '2012-10-17'
       Statement:
         - Effect: Allow
           Action:
             - logs:CreateLogGroup
             - logs:CreateLogStream  
             - logs:PutLogEvents
           Resource: !Sub 'arn:aws:logs:${AWS::Region}:${AWS::AccountId}:*'
   ```

2. **API Gateway Security**
   ```yaml
   # Enable throttling
   ThrottleSettings:
     BurstLimit: 200
     RateLimit: 100
   
   # Add request validation
   RequestValidatorId: !Ref RequestValidator
   ```

3. **Environment Variables**
   ```bash
   # Never hardcode secrets
   export DATABASE_URL=$(aws ssm get-parameter --name /mcp/database-url --with-decryption --query 'Parameter.Value' --output text)
   ```

### Monitoring

1. **CloudWatch Alarms**
   ```yaml
   ErrorRateAlarm:
     Type: AWS::CloudWatch::Alarm
     Properties:
       AlarmName: !Sub '${AWS::StackName}-ErrorRate'
       MetricName: Errors
       Namespace: AWS/Lambda
       Statistic: Sum
       Period: 60
       EvaluationPeriods: 2
       Threshold: 5
   ```

2. **Custom Metrics**
   ```python
   import boto3
   
   cloudwatch = boto3.client('cloudwatch')
   cloudwatch.put_metric_data(
       Namespace='MCP/Server',
       MetricData=[{
           'MetricName': 'ToolCalls',
           'Value': 1,
           'Unit': 'Count'
       }]
   )
   ```

3. **Application Insights**
   - Automatically enabled in SAM template
   - Provides application-level monitoring
   - Correlates logs, metrics, and traces

### Performance Optimization

1. **Lambda Configuration**
   ```yaml
   # Optimize memory for your workload
   MemorySize: 512  # Balance cost vs performance
   Timeout: 30      # Set appropriate timeout
   
   # Enable provisioned concurrency for consistent performance
   ProvisionedConcurrency: 5
   ```

2. **API Gateway Caching**
   ```yaml
   # Enable response caching for GET requests
   CacheClusterEnabled: true
   CacheClusterSize: 0.5
   CachingEnabled: true
   CacheTtlInSeconds: 300
   ```

3. **Connection Reuse**
   ```python
   # Reuse connections outside handler
   import boto3
   
   # Initialize outside handler function
   dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table('mcp-data')
   
   def lambda_handler(event, context):
       # Use existing connections
       pass
   ```

## Multi-Region Deployment

### Primary Region (us-east-1)
```bash
# Deploy to primary region
sam deploy \
  --stack-name remote-mcp-server-primary \
  --region us-east-1 \
  --parameter-overrides Environment=production
```

### Secondary Region (us-west-2)
```bash
# Deploy to secondary region
sam deploy \
  --stack-name remote-mcp-server-secondary \
  --region us-west-2 \
  --parameter-overrides Environment=production
```

### Global DNS with Route 53
```yaml
# Health check for primary region
PrimaryHealthCheck:
  Type: AWS::Route53::HealthCheck
  Properties:
    Type: HTTPS
    ResourcePath: /Prod/health
    FullyQualifiedDomainName: !Sub '${ApiGateway}.execute-api.us-east-1.amazonaws.com'

# Failover routing
PrimaryRecord:
  Type: AWS::Route53::RecordSet
  Properties:
    SetIdentifier: primary
    Failover: PRIMARY
    HealthCheckId: !Ref PrimaryHealthCheck
```

## CI/CD Integration

### GitHub Actions Deployment

```yaml
name: Deploy to AWS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/setup-sam@v2
      - uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Build and Deploy
        run: |
          sam build
          sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
```

### Blue/Green Deployment

```yaml
# SAM template with deployment preferences
DeploymentPreference:
  Type: Canary10Percent30Minutes
  Alarms:
    - !Ref ErrorRateAlarm
    - !Ref LatencyAlarm
  Hooks:
    PreTraffic: !Ref PreTrafficHook
    PostTraffic: !Ref PostTrafficHook
```

## Troubleshooting

### Common Issues

1. **Cold Start Latency**
   ```bash
   # Solution: Increase memory or enable provisioned concurrency
   sam deploy --parameter-overrides MemorySize=1024
   ```

2. **Timeout Errors**
   ```bash
   # Solution: Increase timeout value
   sam deploy --parameter-overrides Timeout=60
   ```

3. **Permission Errors**
   ```bash
   # Check IAM role permissions
   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/remote-mcp-server
   ```

4. **API Gateway 502 Errors**
   ```bash
   # Check Lambda function logs
   sam logs --stack-name remote-mcp-server --tail
   ```

### Monitoring Commands

```bash
# View CloudFormation events
aws cloudformation describe-stack-events --stack-name remote-mcp-server

# Monitor Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=remote-mcp-server-Function \
  --start-time 2025-08-22T00:00:00Z \
  --end-time 2025-08-22T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum

# View recent logs
sam logs --stack-name remote-mcp-server --start-time 2025-08-22T00:00:00
```

## Cost Optimization

### Lambda Pricing
- **Requests**: $0.20 per 1M requests
- **Duration**: $0.0000166667 per GB-second
- **Free Tier**: 1M requests and 400,000 GB-seconds per month

### API Gateway Pricing
- **REST API**: $3.50 per million API calls
- **Data Transfer**: $0.09 per GB
- **Caching**: Additional cost for response caching

### Optimization Strategies
1. **Right-size memory allocation** based on actual usage
2. **Enable response caching** for repeated requests
3. **Use provisioned concurrency** only when necessary
4. **Monitor and optimize cold starts**

---

## Production Checklist

- [ ] **Security**: IAM roles follow least privilege
- [ ] **Monitoring**: CloudWatch alarms configured
- [ ] **Logging**: Structured logging enabled
- [ ] **Performance**: Memory and timeout optimized
- [ ] **Backup**: Infrastructure as Code in version control
- [ ] **Testing**: Integration tests pass
- [ ] **Documentation**: Deployment runbooks updated
- [ ] **Alerting**: Error notifications configured

For additional help, see:
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)