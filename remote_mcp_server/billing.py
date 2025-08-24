"""
Subscription billing service with Stripe integration for Remote MCP Server.

This module handles:
- Stripe customer and subscription management
- API key generation and validation
- Usage tracking and billing
- Subscription lifecycle management
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

import stripe
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SubscriptionBillingService:
    """Manages subscription billing with Stripe and AWS API Gateway."""
    
    def __init__(self) -> None:
        """Initialize the billing service with Stripe and AWS clients."""
        # Initialize Stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            raise ValueError("STRIPE_SECRET_KEY environment variable is required")
        
        # Initialize AWS clients
        self.dynamodb = boto3.resource('dynamodb')
        self.api_gateway = boto3.client('apigateway')
        
        # Get table name from environment
        stack_name = os.getenv('AWS_SAM_STACK_NAME', 'remote-mcp-server')
        self.subscription_table_name = f"{stack_name}-subscriptions"
        
        try:
            self.subscription_table = self.dynamodb.Table(self.subscription_table_name)
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB table: {e}")
            raise
    
    def create_customer_and_subscription(
        self, 
        email: str, 
        payment_method_id: str,
        plan_id: str = "price_basic_monthly"
    ) -> Dict[str, Any]:
        """
        Create a Stripe customer, subscription, and AWS API key.
        
        Args:
            email: Customer email address
            payment_method_id: Stripe payment method ID
            plan_id: Stripe price ID for the subscription plan
            
        Returns:
            Dictionary containing customer info, subscription details, and API key
        """
        try:
            # Create Stripe customer
            customer = stripe.Customer.create(
                email=email,
                payment_method=payment_method_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
            
            # Create Stripe subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': plan_id}],
                expand=['latest_invoice.payment_intent']
            )
            
            # Generate AWS API key
            api_key_response = self.api_gateway.create_api_key(
                name=f"customer-{customer.id}",
                description=f"API key for customer {email}",
                enabled=True
            )
            
            api_key_id = api_key_response['id']
            api_key_value = api_key_response['value']
            
            # Get usage plan ID (assuming it exists from SAM template)
            usage_plans = self.api_gateway.get_usage_plans()
            usage_plan_id = None
            for plan in usage_plans['items']:
                if 'remote-mcp-server' in plan['name']:
                    usage_plan_id = plan['id']
                    break
            
            if not usage_plan_id:
                raise Exception("Usage plan not found")
            
            # Associate API key with usage plan
            self.api_gateway.create_usage_plan_key(
                usagePlanId=usage_plan_id,
                keyId=api_key_id,
                keyType='API_KEY'
            )
            
            # Store subscription data in DynamoDB
            subscription_data = {
                'api_key': api_key_value,
                'customer_id': customer.id,
                'subscription_id': subscription.id,
                'email': email,
                'plan_id': plan_id,
                'status': subscription.status,
                'created_at': datetime.utcnow().isoformat(),
                'current_period_start': datetime.fromtimestamp(
                    subscription.current_period_start
                ).isoformat(),
                'current_period_end': datetime.fromtimestamp(
                    subscription.current_period_end
                ).isoformat(),
                'usage_count': 0,
                'last_usage': None
            }
            
            self.subscription_table.put_item(Item=subscription_data)
            
            return {
                'customer_id': customer.id,
                'subscription_id': subscription.id,
                'api_key': api_key_value,
                'status': subscription.status,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret
                if subscription.latest_invoice.payment_intent 
                else None
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise Exception(f"Payment processing failed: {str(e)}")
        except ClientError as e:
            logger.error(f"AWS error: {e}")
            raise Exception(f"AWS service error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise Exception(f"Subscription creation failed: {str(e)}")
    
    def get_subscription_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve subscription information by API key.
        
        Args:
            api_key: AWS API Gateway API key
            
        Returns:
            Subscription data or None if not found
        """
        try:
            response = self.subscription_table.get_item(
                Key={'api_key': api_key}
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(f"DynamoDB error: {e}")
            return None
    
    def validate_api_key_and_subscription(self, api_key: str) -> Dict[str, Any]:
        """
        Validate API key and check subscription status.
        
        Args:
            api_key: AWS API Gateway API key
            
        Returns:
            Validation result with subscription status
        """
        subscription = self.get_subscription_by_api_key(api_key)
        
        if not subscription:
            return {'valid': False, 'reason': 'API key not found'}
        
        # Check Stripe subscription status
        try:
            stripe_subscription = stripe.Subscription.retrieve(
                subscription['subscription_id']
            )
            
            # Update local subscription status
            if stripe_subscription.status != subscription['status']:
                self.subscription_table.update_item(
                    Key={'api_key': api_key},
                    UpdateExpression="SET #status = :status",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': stripe_subscription.status}
                )
            
            # Check if subscription is active
            active_statuses = ['active', 'trialing']
            if stripe_subscription.status not in active_statuses:
                return {
                    'valid': False, 
                    'reason': f'Subscription status: {stripe_subscription.status}'
                }
            
            # Check if subscription is current (not past due)
            now = datetime.utcnow().timestamp()
            if stripe_subscription.current_period_end < now:
                return {
                    'valid': False, 
                    'reason': 'Subscription period ended'
                }
            
            return {
                'valid': True,
                'customer_id': subscription['customer_id'],
                'subscription_id': subscription['subscription_id'],
                'plan_id': subscription['plan_id'],
                'status': stripe_subscription.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe validation error: {e}")
            return {'valid': False, 'reason': 'Subscription validation failed'}
    
    def track_api_usage(self, api_key: str, endpoint: str, tokens_used: int = 1) -> bool:
        """
        Track API usage for billing purposes.
        
        Args:
            api_key: AWS API Gateway API key
            endpoint: API endpoint used
            tokens_used: Number of tokens/requests used
            
        Returns:
            True if tracking successful, False otherwise
        """
        try:
            current_time = datetime.utcnow().isoformat()
            
            # Update usage count and last usage time
            self.subscription_table.update_item(
                Key={'api_key': api_key},
                UpdateExpression="ADD usage_count :tokens SET last_usage = :timestamp",
                ExpressionAttributeValues={
                    ':tokens': tokens_used,
                    ':timestamp': current_time
                }
            )
            
            # Log usage for detailed analytics (optional)
            logger.info(f"API usage tracked: {api_key[:8]}... used {tokens_used} tokens on {endpoint}")
            return True
            
        except ClientError as e:
            logger.error(f"Usage tracking failed: {e}")
            return False
    
    def cancel_subscription(self, api_key: str) -> Dict[str, Any]:
        """
        Cancel a subscription and disable the API key.
        
        Args:
            api_key: AWS API Gateway API key
            
        Returns:
            Cancellation result
        """
        try:
            subscription = self.get_subscription_by_api_key(api_key)
            if not subscription:
                return {'success': False, 'error': 'Subscription not found'}
            
            # Cancel Stripe subscription
            stripe_subscription = stripe.Subscription.cancel(
                subscription['subscription_id']
            )
            
            # Disable API key in AWS
            # Note: We don't delete the key to maintain audit trail
            try:
                # Find the API key ID by value (this is a limitation of AWS API)
                api_keys = self.api_gateway.get_api_keys()
                api_key_id = None
                for key in api_keys['items']:
                    if key['value'] == api_key:
                        api_key_id = key['id']
                        break
                
                if api_key_id:
                    self.api_gateway.update_api_key(
                        apiKey=api_key_id,
                        patchOps=[
                            {
                                'op': 'replace',
                                'path': '/enabled',
                                'value': 'false'
                            }
                        ]
                    )
            except Exception as e:
                logger.warning(f"Failed to disable API key: {e}")
            
            # Update subscription status in DynamoDB
            self.subscription_table.update_item(
                Key={'api_key': api_key},
                UpdateExpression="SET #status = :status, cancelled_at = :timestamp",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': stripe_subscription.status,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
            
            return {
                'success': True,
                'subscription_id': subscription['subscription_id'],
                'cancelled_at': stripe_subscription.canceled_at
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe cancellation error: {e}")
            return {'success': False, 'error': f'Stripe error: {str(e)}'}
        except Exception as e:
            logger.error(f"Cancellation error: {e}")
            return {'success': False, 'error': f'Cancellation failed: {str(e)}'}
    
    def get_usage_statistics(self, customer_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Usage statistics and billing information
        """
        try:
            # Query by customer_id using GSI
            response = self.subscription_table.query(
                IndexName='CustomerIndex',
                KeyConditionExpression='customer_id = :customer_id',
                ExpressionAttributeValues={':customer_id': customer_id}
            )
            
            if not response['Items']:
                return {'error': 'Customer not found'}
            
            subscription = response['Items'][0]
            
            # Get Stripe subscription for current period info
            stripe_subscription = stripe.Subscription.retrieve(
                subscription['subscription_id']
            )
            
            # Calculate billing period
            period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            
            return {
                'customer_id': customer_id,
                'subscription_id': subscription['subscription_id'],
                'plan_id': subscription['plan_id'],
                'status': stripe_subscription.status,
                'usage_count': subscription.get('usage_count', 0),
                'last_usage': subscription.get('last_usage'),
                'billing_period': {
                    'start': period_start.isoformat(),
                    'end': period_end.isoformat(),
                    'days_remaining': (period_end - datetime.utcnow()).days
                },
                'created_at': subscription['created_at']
            }
            
        except Exception as e:
            logger.error(f"Usage statistics error: {e}")
            return {'error': f'Failed to retrieve usage statistics: {str(e)}'}


# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    'basic': {
        'name': 'Basic Plan',
        'description': 'Essential AI infrastructure tools',
        'price_monthly': 'price_basic_monthly',  # Stripe price ID
        'price_yearly': 'price_basic_yearly',    # Stripe price ID
        'features': [
            '10,000 API calls per month',
            'Standard MCP tools',
            'Email support',
            '99.9% uptime SLA'
        ],
        'limits': {
            'monthly_requests': 10000,
            'rate_limit': 100,  # requests per minute
            'burst_limit': 500
        }
    },
    'professional': {
        'name': 'Professional Plan',
        'description': 'Advanced AI orchestration for growing teams',
        'price_monthly': 'price_pro_monthly',
        'price_yearly': 'price_pro_yearly',
        'features': [
            '100,000 API calls per month',
            'Premium MCP tools',
            'Priority support',
            'Custom integrations',
            '99.95% uptime SLA'
        ],
        'limits': {
            'monthly_requests': 100000,
            'rate_limit': 500,
            'burst_limit': 2000
        }
    },
    'enterprise': {
        'name': 'Enterprise Plan',
        'description': 'Custom enterprise AI infrastructure',
        'price_monthly': 'price_enterprise_monthly',
        'price_yearly': 'price_enterprise_yearly',
        'features': [
            'Unlimited API calls',
            'Enterprise MCP tools',
            'Dedicated support',
            'Custom development',
            'SLA guarantees',
            'On-premise deployment'
        ],
        'limits': {
            'monthly_requests': -1,  # Unlimited
            'rate_limit': 2000,
            'burst_limit': 10000
        }
    }
}