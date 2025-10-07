# app/webhook/stripe.py
from fastapi import APIRouter, Request, HTTPException
from app.services.stripe import create_stripe_connect_payout_intent
from app.utils.wc_api import wc_api
import stripe
import os

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")  # Set in .env

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

            # Fetch the order from WooCommerce
            order = await wc_api.get_order(order_id)

            # Extract author Stripe IDs from line items meta_data
            author_stripe_ids = [
                meta.get("value")
                for item in order.get("line_items", [])
                for meta in item.get("meta_data", [])
                if meta.get("key") == "author_stripe_id"
            ]

            amount_in_cents = payment_intent["amount_received"]

            if author_stripe_ids:
                await create_stripe_connect_payout_intent(
                    author_stripe_ids=author_stripe_ids,
                    total_amount=amount_in_cents,
                    order_id=order_id
                )
                print(f"✅ Payout triggered for order {order_id}")
            else:
                print(f"No author Stripe IDs found for order {order_id}")

        return {"status": "success"}

    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as e:
        print(f"❌ Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook failed: {str(e)}")
