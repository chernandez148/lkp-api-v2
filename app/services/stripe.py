import stripe
import os
import asyncio
from dotenv import load_dotenv
from typing import Dict, Optional, List

from app.utils.cache import invalidate_cache

# Load Stripe secret key from environment
load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ---------------------------
#  Create Standard PaymentIntent
# ---------------------------
async def create_stripe_payment_intent(
    billing: dict,
    amount: int,
    user_id: int,  # Added user_id parameter
    currency: str = "usd",
    order_id: Optional[int] = None
):
    """
    Create a Stripe PaymentIntent for frontend card processing.
    Includes user_id and order_id in metadata for webhook processing.
    """

    print(f"Creating PaymentIntent: amount={amount}, order_id={order_id}, user_id={user_id}")

    try:
        # Metadata is crucial for the Webhook to know which user/order to update
        metadata = {
            "user_id": str(user_id),
            "customer_name": f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip(),
            "customer_email": billing.get("email", ""),
            "customer_phone": billing.get("phone", ""),
            "billing_city": billing.get("city", ""),
            "billing_state": billing.get("state", ""),
            "billing_country": billing.get("country", ""),
        }

        if order_id:
            metadata["wc_order_id"] = str(order_id)

        # Stripe library is synchronous — wrap in a thread for async compatibility
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
#  Handle Successful Payment
# ---------------------------
async def handle_successful_payment(payment_intent_id: str, order_id: int, user_id: int):
    """
    Invalidates all relevant caches for the user so the new purchase 
    appears immediately in their library.
    """
    try:
        print(f"✅ Payment successful for PaymentIntent: {payment_intent_id}, Order: {order_id}")
        
        # 1. Clear the main library list cache (The carousel/list)
        await invalidate_cache(f"library_products:*:{user_id}")
        
        # 2. Clear individual purchase permission caches (The 'gatekeeper')
        # This prevents the 'False' purchase flags from hiding ebook URLs
        await invalidate_cache(f"user_purchase:{user_id}:*")
        
        print(f"🧹 Cache invalidated successfully for user {user_id}")
        
    except Exception as e:
        print(f"❌ Error handling successful payment cache invalidation: {str(e)}")
        # We don't necessarily want to crash the webhook if just cache clearing fails, 
        # but we log it heavily.
        raise


# ---------------------------
#  Create Payout to Connected Account(s)
# ---------------------------
async def create_stripe_connect_payout_intent(
    author_stripe_ids: List[str],
    total_amount: int,  # Amount in cents
    order_id: Optional[int] = None,
    currency: str = "usd"
):
    """
    Create transfer to a connected author account (90% payout).
    """
    if not author_stripe_ids:
        raise ValueError("No connected account IDs provided for payout")

    loop = asyncio.get_event_loop()
    transfers = []

    # Calculate 90% payout (Platform keeps 10%)
    # Note: author_revenue logic is handled in the webhook calling this
    author_payout = total_amount 

    for destination in author_stripe_ids:
        try:
            transfer = await loop.run_in_executor(
                None,
                lambda: stripe.Transfer.create(
                    amount=author_payout,
                    currency=currency,
                    destination=destination,
                    metadata={"wc_order_id": str(order_id) if order_id else "unknown"},
                    description=f"Author payout for order {order_id or 'N/A'}"
                )
            )
            transfers.append(transfer)
            print(f"💸 Created transfer to {destination} for {author_payout} cents")
        except stripe.error.StripeError as e:
            print(f"❌ Stripe transfer error for {destination}: {str(e)}")
        except Exception as e:
            print(f"❌ Unexpected error creating transfer to {destination}: {str(e)}")

    return transfers