# app/services/stripe.py - Updated for frontend + Connect payouts

import stripe
import os
import asyncio
from dotenv import load_dotenv
from typing import Dict, Optional, List

# Load Stripe secret key from environment
load_dotenv()
stripe.api_key = STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

# ---------------------------
#  Create Standard PaymentIntent
# ---------------------------
async def create_stripe_payment_intent(
    billing: dict,
    amount: int,
    currency: str = "usd",
    order_id: Optional[int] = None
):
    """
    Create a Stripe PaymentIntent for frontend card processing
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

        if order_id:
            metadata["wc_order_id"] = str(order_id)

        # Stripe library is synchronous — wrap in a thread for async
        loop = asyncio.get_event_loop()
        payment_intent = await loop.run_in_executor(
            None,
            lambda: stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata=metadata,
                automatic_payment_methods={"enabled": True},
            )
        )

        print(f"✅ PaymentIntent created successfully: {payment_intent.id}")
        return payment_intent

    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {str(e)}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error creating PaymentIntent: {str(e)}")
        raise


# ---------------------------
#  Handle Successful Payment (Webhook or Frontend confirmation)
# ---------------------------
async def handle_successful_payment(payment_intent_id: str, order_id: int):
    """
    Called after a payment is confirmed.
    You can update WooCommerce or trigger payouts here.
    """
    try:
        print(f"✅ Payment successful for PaymentIntent: {payment_intent_id}, Order: {order_id}")
        # Example: wc_api.update_order(order_id, {"status": "processing"})
    except Exception as e:
        print(f"❌ Error handling successful payment: {str(e)}")
        raise

# ---------------------------
#  Create Payout to Connected Account(s)
# ---------------------------
async def create_stripe_connect_payout_intent(
    author_stripe_ids: List[str],
    total_amount: int,
    order_id: Optional[int] = None,
    currency: str = "usd"
):
    """
    Split the total_amount: 90% to authors evenly, 10% remains for platform.
    
    Args:
        author_stripe_ids: List of connected account IDs (acct_...)
        total_amount: Total order amount (in cents)
        order_id: Optional WooCommerce order ID
    """
    if not author_stripe_ids:
        raise ValueError("No connected account IDs provided for payout")

    loop = asyncio.get_event_loop()
    transfers = []

    # 90% goes to authors
    total_author_share = int(total_amount * 0.9)
    platform_fee = total_amount - total_author_share
    author_share_each = total_author_share // len(author_stripe_ids)

    print(f"💰 Total amount: {total_amount} | Author total: {total_author_share} | Platform fee: {platform_fee}")

    for destination in author_stripe_ids:
        try:
            transfer = await loop.run_in_executor(
                None,
                lambda: stripe.Transfer.create(
                    amount=author_share_each,
                    currency=currency,
                    destination=destination,
                    metadata={"wc_order_id": str(order_id) if order_id else "unknown"},
                    description=f"Author payout (90%) for order {order_id or 'N/A'}"
                )
            )
            transfers.append(transfer)
            print(f"💸 Created transfer to {destination} for {author_share_each} cents")
        except stripe.error.StripeError as e:
            print(f"❌ Stripe transfer error for {destination}: {str(e)}")
        except Exception as e:
            print(f"❌ Unexpected error creating transfer to {destination}: {str(e)}")

    print(f"✅ Platform keeps {platform_fee} cents")
    return transfers
