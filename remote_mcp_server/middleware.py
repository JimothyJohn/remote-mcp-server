"""
API key validation middleware for Remote MCP Server.

This middleware handles:
- API key extraction from headers
- Subscription validation via AWS and Stripe
- Usage tracking and rate limiting
- Authentication and authorization
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from datetime import datetime

from .billing import SubscriptionBillingService

logger = logging.getLogger(__name__)


class APIKeyMiddleware:
    """Middleware for API key validation and subscription management."""
    
    def __init__(self):
        """Initialize the middleware with billing service."""
        try:
            self.billing_service = SubscriptionBillingService()
            logger.info("API key middleware initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize billing service: {e}")
            self.billing_service = None
    
    def extract_api_key(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Extract API key from Lambda event headers.
        
        Args:
            event: AWS Lambda event dictionary
            
        Returns:
            API key string or None if not found
        """
        headers = event.get('headers', {})
        
        # Check for X-API-Key header (primary)
        api_key = headers.get('X-API-Key') or headers.get('x-api-key')
        
        # Check for Authorization header as fallback
        if not api_key:
            auth_header = headers.get('Authorization') or headers.get('authorization')
            if auth_header and auth_header.startswith('Bearer '):
                api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        return api_key
    
    def validate_subscription(self, api_key: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate API key and subscription status.
        
        Args:
            api_key: AWS API Gateway API key
            
        Returns:
            Tuple of (is_valid, validation_details)
        """
        if not self.billing_service:
            logger.error("Billing service not available")
            return False, {'error': 'Service temporarily unavailable'}
        
        try:
            validation = self.billing_service.validate_api_key_and_subscription(api_key)
            
            if validation['valid']:
                logger.info(f"API key validation successful for customer: {validation.get('customer_id', 'unknown')[:8]}...")
                return True, validation
            else:
                logger.warning(f"API key validation failed: {validation.get('reason', 'unknown reason')}")
                return False, validation
                
        except Exception as e:
            logger.error(f"Subscription validation error: {e}")
            return False, {'error': f'Validation failed: {str(e)}'}
    
    def track_usage(self, api_key: str, endpoint: str, tokens_used: int = 1) -> bool:
        """
        Track API usage for billing purposes.
        
        Args:
            api_key: AWS API Gateway API key
            endpoint: API endpoint accessed
            tokens_used: Number of tokens/requests used
            
        Returns:
            True if tracking successful, False otherwise
        """
        if not self.billing_service:
            return False
        
        return self.billing_service.track_api_usage(api_key, endpoint, tokens_used)
    
    def get_rate_limits(self, subscription_plan: str) -> Dict[str, int]:
        """
        Get rate limits based on subscription plan.
        
        Args:
            subscription_plan: Subscription plan identifier
            
        Returns:
            Dictionary with rate limit configurations
        """
        from .billing import SUBSCRIPTION_PLANS
        
        plan_config = SUBSCRIPTION_PLANS.get(subscription_plan, SUBSCRIPTION_PLANS['basic'])
        return plan_config['limits']
    
    def create_error_response(self, status_code: int, error_message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create standardized error response for API key validation failures.
        
        Args:
            status_code: HTTP status code
            error_message: Error message
            details: Additional error details
            
        Returns:
            Lambda response dictionary
        """
        response_body = {
            'error': 'Authentication Failed' if status_code == 401 else 'Authorization Failed',
            'message': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'remote-mcp-server'
        }
        
        if details:
            response_body.update(details)
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps(response_body)
        }


def require_api_key(track_usage: bool = True):
    """
    Decorator to require valid API key for Lambda function endpoints.
    
    Args:
        track_usage: Whether to track API usage for billing
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            # Initialize middleware
            middleware = APIKeyMiddleware()
            
            # Extract API key
            api_key = middleware.extract_api_key(event)
            
            if not api_key:
                logger.warning("Request missing API key")
                return middleware.create_error_response(
                    401, 
                    "API key required. Include X-API-Key header or Authorization: Bearer token.",
                    {'hint': 'Get your API key from the subscription dashboard'}
                )
            
            # Validate subscription
            is_valid, validation_details = middleware.validate_subscription(api_key)
            
            if not is_valid:
                reason = validation_details.get('reason', 'Invalid API key')
                logger.warning(f"API key validation failed: {reason}")
                
                # Determine appropriate status code
                status_code = 403 if 'expired' in reason.lower() or 'ended' in reason.lower() else 401
                
                return middleware.create_error_response(
                    status_code,
                    f"Subscription validation failed: {reason}",
                    {'subscription_status': validation_details.get('status')}
                )
            
            # Track usage if enabled
            if track_usage:
                endpoint = event.get('path', 'unknown')
                success = middleware.track_usage(api_key, endpoint)
                if not success:
                    logger.warning("Failed to track API usage")
            
            # Add subscription details to event for use in handler
            event['subscription'] = validation_details
            event['api_key'] = api_key
            
            # Call the original function
            try:
                return func(event, context)
            except Exception as e:
                logger.error(f"Handler function error: {e}")
                return middleware.create_error_response(
                    500,
                    "Internal server error occurred",
                    {'error_type': type(e).__name__}
                )
        
        return wrapper
    return decorator


def optional_api_key():
    """
    Decorator for endpoints that optionally accept API keys (e.g., health checks).
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            # Initialize middleware
            middleware = APIKeyMiddleware()
            
            # Extract API key (optional)
            api_key = middleware.extract_api_key(event)
            
            if api_key:
                # Validate if present
                is_valid, validation_details = middleware.validate_subscription(api_key)
                
                if is_valid:
                    event['subscription'] = validation_details
                    event['api_key'] = api_key
                    logger.info("Optional API key validated successfully")
                else:
                    logger.info("Optional API key validation failed - proceeding without authentication")
            
            # Call the original function regardless of API key status
            return func(event, context)
        
        return wrapper
    return decorator


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self):
        """Initialize rate limiter with in-memory storage."""
        self.request_counts = {}
        self.last_reset = {}
    
    def is_rate_limited(self, api_key: str, limits: Dict[str, int]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if API key has exceeded rate limits.
        
        Args:
            api_key: AWS API Gateway API key
            limits: Rate limit configuration
            
        Returns:
            Tuple of (is_limited, limit_info)
        """
        current_time = datetime.utcnow()
        
        # Reset counts every minute
        if api_key not in self.last_reset or (current_time - self.last_reset[api_key]).seconds >= 60:
            self.request_counts[api_key] = 0
            self.last_reset[api_key] = current_time
        
        # Check rate limit
        current_count = self.request_counts.get(api_key, 0)
        rate_limit = limits.get('rate_limit', 100)  # requests per minute
        
        if current_count >= rate_limit:
            return True, {
                'limited': True,
                'current_count': current_count,
                'rate_limit': rate_limit,
                'reset_time': (self.last_reset[api_key]).isoformat()
            }
        
        # Increment counter
        self.request_counts[api_key] = current_count + 1
        
        return False, {
            'limited': False,
            'current_count': current_count + 1,
            'rate_limit': rate_limit,
            'remaining': rate_limit - (current_count + 1)
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


def with_rate_limiting():
    """
    Decorator to add rate limiting to API endpoints.
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            # Get subscription details (should be set by require_api_key decorator)
            subscription = event.get('subscription')
            api_key = event.get('api_key')
            
            if not subscription or not api_key:
                # No subscription info, skip rate limiting
                return func(event, context)
            
            # Get rate limits for subscription plan
            middleware = APIKeyMiddleware()
            plan_id = subscription.get('plan_id', 'basic')
            limits = middleware.get_rate_limits(plan_id)
            
            # Check rate limits
            is_limited, limit_info = rate_limiter.is_rate_limited(api_key, limits)
            
            if is_limited:
                logger.warning(f"Rate limit exceeded for API key: {api_key[:8]}...")
                return middleware.create_error_response(
                    429,
                    "Rate limit exceeded. Please reduce request frequency.",
                    {
                        'rate_limit': limit_info,
                        'plan': plan_id
                    }
                )
            
            # Add rate limit info to response headers
            response = func(event, context)
            
            if isinstance(response, dict) and 'headers' in response:
                response['headers'].update({
                    'X-RateLimit-Limit': str(limit_info['rate_limit']),
                    'X-RateLimit-Remaining': str(limit_info['remaining']),
                    'X-RateLimit-Used': str(limit_info['current_count'])
                })
            
            return response
        
        return wrapper
    return decorator