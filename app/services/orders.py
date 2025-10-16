# app/services/orders.py - Simplified for frontend Stripe integration
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse
from app.schemas.token import TokenData
from app.services.stripe import create_stripe_payment_intent
from app.utils.wc_api import wc_api
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

async def create_user_order(order_data: OrderCreate, current_user: TokenData) -> OrderResponse:
    line_items_payload = []
    for item in order_data.line_items:
        line_item_dict = item.dict()
        # Add author Stripe ID to meta_data for webhook
        line_item_dict["meta_data"] = line_item_dict.get("meta_data", [])
        if item.authorStripeID:
            line_item_dict["meta_data"].append({
                "key": "author_stripe_id",
                "value": item.authorStripeID
            })
        line_items_payload.append(line_item_dict)

    payload = {
        "payment_method": "stripe",
        "payment_method_title": order_data.payment_method_title,
        "set_paid": False,
        "billing": order_data.billing.dict(),
        "line_items": line_items_payload,
        "customer_id": int(current_user["id"])
    }

    try:
        # Create WooCommerce order
        created_order = await wc_api.create_order(payload)

        order_id = created_order["id"]
        billing = created_order.get("billing", {})
        total_amount = float(created_order["total"])
        amount_in_cents = int(total_amount * 100)

        if amount_in_cents <= 0:
            raise HTTPException(status_code=400, detail="Order total must be greater than zero")

        # Create Stripe PaymentIntent
        payment_intent = await create_stripe_payment_intent(
            billing=billing,
            amount=amount_in_cents,
            order_id=order_id
        )
        
        return OrderResponse(
            id=created_order["id"],
            payment_url=None,
            status=created_order["status"],
            total=created_order["total"],
            payment_method=created_order["payment_method"],
            payment_method_title=created_order["payment_method_title"],
            stripe_payment_intent_client_secret=payment_intent.client_secret
        )

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

async def list_user_orders(current_user: TokenData, page, per_page):
    """List user orders"""
    try:
        user_orders = await wc_api.list_orders(customer_id=current_user["id"], page=page, per_page=per_page)
        return user_orders
    except Exception as e:
        print(f"Error listing orders: {str(e)}")
        logger.error(f"Error listing orders: {str(e)}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list orders: {str(e)}"
        )   