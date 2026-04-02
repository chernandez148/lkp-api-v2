# app/webhook/stripe.py
from fastapi import APIRouter, Request, HTTPException
from app.services.stripe import create_stripe_connect_payout_intent
from app.utils.wc_api import wc_api
import stripe
import os

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

        if event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            order_id = payment_intent["metadata"].get("wc_order_id")

            if not order_id:
                raise HTTPException(status_code=400, detail="Order ID missing in PaymentIntent metadata")

            # ✅ UPDATE WOOCOMMERCE ORDER STATUS FIRST
            try:
                await wc_api.update_order(order_id)
                print(f"✅ Order {order_id} updated to 'completed'")
            except Exception as e:
                print(f"❌ Failed to update order status: {str(e)}")

            # Fetch the updated order from WooCommerce
            order = await wc_api.get_order(order_id)

            # ✅ GROUP PRODUCT REVENUE BY AUTHOR
            author_revenue = {}
            
            for item in order.get("line_items", []):
                # Find author Stripe ID for this product
                author_stripe_id = None
                for meta in item.get("meta_data", []):
                    if meta.get("key") == "author_stripe_id":
                        author_stripe_id = meta.get("value")
                        break
                
                if author_stripe_id:
                    # Calculate author's share for this product (90% of product total)
                    product_total = float(item.get("total", 0))
                    author_share = int(product_total * 0.9 * 100)  # Convert to cents
                    
                    if author_stripe_id not in author_revenue:
                        author_revenue[author_stripe_id] = 0
                    author_revenue[author_stripe_id] += author_share
            
            # ✅ CREATE PAYOUTS FOR EACH AUTHOR WITH THEIR ACTUAL REVENUE
            for author_stripe_id, amount_in_cents in author_revenue.items():
                if amount_in_cents > 0:
                    try:
                        # Create individual transfer for each author
                        await create_stripe_connect_payout_intent(
                            author_stripe_ids=[author_stripe_id],  # Single author
                            total_amount=amount_in_cents,  # Their specific revenue
                            order_id=order_id
                        )
                        print(f"💸 Paid {amount_in_cents/100:.2f} to author {author_stripe_id}")
                    except Exception as e:
                        print(f"❌ Failed to pay author {author_stripe_id}: {str(e)}")

            print(f"✅ All payouts completed for order {order_id}")

        return {"status": "success"}

    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as e:
        print(f"❌ Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook failed: {str(e)}")
