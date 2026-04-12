# app/webhook/stripe.py
from fastapi import APIRouter, Request, HTTPException
from app.services.stripe import create_stripe_connect_payout_intent, handle_successful_payment
from app.utils.wc_api import wc_api
import stripe
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        # Verify the webhook signature
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        
        # Only process successful payments
        if event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            
            # Extract metadata we saved during PaymentIntent creation
            order_id = payment_intent["metadata"].get("wc_order_id")
            user_id = payment_intent["metadata"].get("user_id")

            if not order_id or not user_id:
                logger.warning(f"⚠️ Webhook received but missing metadata. Order: {order_id}, User: {user_id}")
                return {"status": "metadata_missing"}

            logger.info(f"🚀 Processing successful payment for Order {order_id}, User {user_id}")

            # 1. Update WooCommerce status to 'completed'
            # This triggers the generation of digital download permissions in WC
            try:
                await wc_api.update_order(order_id, status="completed")
                logger.info(f"✅ WooCommerce Order {order_id} marked as completed")
            except Exception as e:
                logger.error(f"❌ Failed to update WC order {order_id}: {str(e)}")

            # 2. Clear Redis Cache (Library list + Product permissions)
            # This ensures the user sees the new product immediately on refetch
            try:
                await handle_successful_payment(
                    payment_intent_id=payment_intent['id'], 
                    order_id=int(order_id), 
                    user_id=int(user_id)
                )
            except Exception as e:
                logger.error(f"❌ Cache invalidation failed for user {user_id}: {str(e)}")

            # 3. Handle Connect Payouts to Authors
            try:
                # Fetch the order details to see exactly what was paid for
                order = await wc_api.get_order(order_id)
                author_revenue = {}
                
                for item in order.get("line_items", []):
                    # Find author Stripe ID for this product from meta_data
                    author_stripe_id = None
                    for meta in item.get("meta_data", []):
                        if meta.get("key") == "author_stripe_id":
                            author_stripe_id = meta.get("value")
                            break
                    
                    if author_stripe_id:
                        # Calculate author's 90% share (item total is after discounts)
                        product_total = float(item.get("total", 0))
                        author_share_cents = int(product_total * 0.9 * 100)
                        
                        author_revenue[author_stripe_id] = author_revenue.get(author_stripe_id, 0) + author_share_cents
                
                # Trigger the Stripe Transfers
                for stripe_id, cents in author_revenue.items():
                    if cents > 0:
                        await create_stripe_connect_payout_intent(
                            author_stripe_ids=[stripe_id],
                            total_amount=cents,
                            order_id=int(order_id)
                        )
                        logger.info(f"💸 Paid ${cents/100:.2f} to author {stripe_id}")

            except Exception as e:
                logger.error(f"❌ Payout processing failed for order {order_id}: {str(e)}")

            logger.info(f"🎯 Finished processing Webhook for Order {order_id}")

        return {"status": "success"}

    except stripe.error.SignatureVerificationError:
        logger.error("❌ Invalid Stripe signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"❌ Webhook failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")