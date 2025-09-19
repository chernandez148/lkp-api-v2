# app/services/stripe.py - Updated for frontend integration
import stripe
import os
from typing import Dict, Optional

stripe.api_key = STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

async def create_stripe_payment_intent(
    billing: dict, 
    amount: int, 
    currency: str = "usd",
    order_id: Optional[int] = None
):
    """
    Create a Stripe PaymentIntent for frontend processing
    
    Args:
        billing: Dictionary containing billing information
        amount: Amount in cents (e.g., 1000 for $10.00)
        currency: Currency code (default: "usd")
        order_id: WooCommerce order ID for tracking
    """
    print(f"Creating PaymentIntent: amount={amount}, order_id={order_id}")
    
    try:
        metadata = {
            "customer_name": f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip(),
            "customer_email": billing.get("email", ""),
            "customer_phone": billing.get("phone", ""),
            "billing_city": billing.get("city", ""),
            "billing_state": billing.get("state", ""),
            "billing_country": billing.get("country", ""),
        }
        
        # Add order ID to metadata if provided
        if order_id:
            metadata["wc_order_id"] = str(order_id)
        
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            metadata=metadata,
            # Enable automatic payment methods
            automatic_payment_methods={
                'enabled': True,
            },
        )
        
        print(f"PaymentIntent created successfully: {payment_intent.id}")
        return payment_intent
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error creating PaymentIntent: {str(e)}")
        raise

async def handle_successful_payment(payment_intent_id: str, order_id: int):
    """
    Handle successful payment - update WooCommerce order status
    This would be called after successful payment confirmation
    """
    try:
        # You might want to update the WooCommerce order status here
        # For example, mark it as "processing" or "completed"
        print(f"Payment successful for PaymentIntent: {payment_intent_id}, Order: {order_id}")
        
        # Example: Update WooCommerce order
        # wc_api.update_order(order_id, {"status": "processing"})
        
    except Exception as e:
        print(f"Error handling successful payment: {str(e)}")
        raise