from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse
from app.schemas.token import TokenData
from app.services.stripe import create_stripe_payment_intent
from app.utils.wc_api import wc_api
from app.utils.cache import invalidate_cache
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

async def create_user_order(order_data: OrderCreate, current_user: TokenData) -> OrderResponse:
    user_id = int(current_user["id"])
    line_items_payload = []
    
    for item in order_data.line_items:
        line_item_dict = item.dict() if hasattr(item, 'dict') else item
        line_item_dict["meta_data"] = line_item_dict.get("meta_data", [])
        author_stripe_id = getattr(item, 'authorStripeID', None) or line_item_dict.get('authorStripeID')
        
        if author_stripe_id:
            line_item_dict["meta_data"].append({
                "key": "author_stripe_id",
                "value": author_stripe_id
            })
        line_items_payload.append(line_item_dict)

    payload = {
        "payment_method": "stripe",
        "payment_method_title": order_data.payment_method_title,
        "set_paid": False,
        "billing": order_data.billing.dict() if hasattr(order_data.billing, 'dict') else order_data.billing,
        "line_items": line_items_payload,
        "customer_id": user_id
    }

    if getattr(order_data, "coupon_lines", None):
        payload["coupon_lines"] = [{"code": coupon.code} for coupon in order_data.coupon_lines]

    try:
        # Create WooCommerce order
        created_order = await wc_api.create_order(payload)
        order_id = created_order["id"]
        billing = created_order.get("billing", {})
        total_amount = float(created_order["total"])
        amount_in_cents = int(total_amount * 100)

        # CASE 1: 100% FREE ORDERS
        if amount_in_cents == 0:
            # Mark order as complete in WC
            await wc_api.update_order(order_id, status="completed")
            
            # Clear the library list
            await invalidate_cache(f"library_products:*:{user_id}")

            # Clear the individual purchase permissions (gatekeeper)
            await invalidate_cache(f"user_purchase:{user_id}:*")

            # Clear the cached product detail page for this user
            await invalidate_cache(f"product_detail:*:{user_id}")
            
            logger.info(f"✅ Full cache clear for user {user_id} (Free Order)")
            return OrderResponse(
                id=order_id,
                payment_url=None,
                status="completed", 
                total=created_order["total"],
                payment_method=created_order["payment_method"],
                payment_method_title=created_order["payment_method_title"],
                stripe_payment_intent_client_secret=None
            )
            
        elif amount_in_cents < 50:
            raise HTTPException(
                status_code=400, 
                detail="Order total after discounts is less than the $0.50 minimum charge."
            )

        # CASE 2: PAID ORDERS
        # We pass user_id so it can be saved in Stripe metadata for the Webhook to use
        payment_intent = await create_stripe_payment_intent(
            billing=billing,
            amount=amount_in_cents,
            order_id=order_id,
            user_id=user_id
        )

        return OrderResponse(
            id=order_id,
            payment_url=None,
            status=created_order["status"],
            total=created_order["total"],
            payment_method=created_order["payment_method"],
            payment_method_title=created_order["payment_method_title"],
            stripe_payment_intent_client_secret=payment_intent.client_secret
        )

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

async def list_user_orders(current_user: TokenData, page, per_page):
    try:
        return await wc_api.list_orders(customer_id=current_user["id"], page=page, per_page=per_page)
    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list orders: {str(e)}")