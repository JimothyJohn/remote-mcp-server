"""Legacy handler test - updated for new MCP integration."""

import json

import pytest

from remote_mcp_server.mcp_server import lambda_handler


@pytest.fixture()
def apigw_event():
    """Generate API Gateway Event for backward compatibility testing."""
    return {
        "body": '{ "test": "body"}',
        "resource": "/{proxy+}",
        "requestContext": {
            "resourceId": "123456",
            "apiId": "1234567890",
            "resourcePath": "/{proxy+}",
            "httpMethod": "POST",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "accountId": "123456789012",
            "identity": {
                "apiKey": "",
                "userArn": "",
                "cognitoAuthenticationType": "",
                "caller": "",
                "userAgent": "Custom User Agent String",
                "user": "",
                "cognitoIdentityPoolId": "",
                "cognitoIdentityId": "",
                "cognitoAuthenticationProvider": "",
                "sourceIp": "127.0.0.1",
                "accountId": "",
            },
            "stage": "prod",
        },
        "queryStringParameters": {"foo": "bar"},
        "headers": {
            "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Mobile-Viewer": "false",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
            "CloudFront-Viewer-Country": "US",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-Port": "443",
            "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
            "X-Forwarded-Proto": "https",
            "X-Amz-Cf-Id": "aaaaaaaaaae3VYQb9jd-nvCd-de396Uhbp027Y2JvkCPNLmGJHqlaA==",
            "CloudFront-Is-Tablet-Viewer": "false",
            "Cache-Control": "max-age=0",
            "User-Agent": "Custom User Agent String",
            "CloudFront-Forwarded-Proto": "https",
            "Accept-Encoding": "gzip, deflate, sdch",
        },
        "pathParameters": {"proxy": "/examplepath"},
        "httpMethod": "POST",
        "stageVariables": {"baz": "qux"},
        "path": "/examplepath",
    }


class MockContext:
    """Mock Lambda context."""

    def __init__(self):
        self.function_name = "test-function"
        self.function_version = "$LATEST"
        self.invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        )
        self.memory_limit_in_mb = "128"
        self.log_group_name = "/aws/lambda/test-function"
        self.log_stream_name = "2023/01/01/[$LATEST]test123"
        self.aws_request_id = "test-id"

    def get_remaining_time_in_millis(self):
        """Get remaining execution time."""
        return 30000


def test_lambda_handler_backward_compatibility(apigw_event):
    """Test that the Lambda handler maintains backward compatibility."""
    context = MockContext()

    ret = lambda_handler(apigw_event, context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "message" in ret["body"]
    # POST requests now return different message - this is expected behavior
    if apigw_event["httpMethod"] == "POST":
        assert data["message"] == "POST request received"
    else:
        assert data["message"] == "remote-mcp-server"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


def test_lambda_handler_new_functionality(apigw_event):
    """Test new MCP-enhanced functionality."""
    # Modify event to test health endpoint
    apigw_event["httpMethod"] = "GET"
    apigw_event["path"] = "/health"

    context = MockContext()
    ret = lambda_handler(apigw_event, context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert data["status"] == "healthy"
    assert data["service"] == "remote-mcp-server"
    assert data["version"] == "1.0.0"
