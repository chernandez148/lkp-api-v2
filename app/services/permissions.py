#app/services/permissions.py
from typing import Optional
import httpx
import requests
import os
from requests.auth import HTTPBasicAuth

from app.core.config import settings
from app.utils.wc_api import wc_api
import logging  # ← Add this

logger = logging.getLogger(__name__)  # ← Add this

WC_API_BASE = settings.WC_API_URL
WC_CONSUMER_KEY = settings.WC_CONSUMER_KEY
WC_CONSUMER_SECRET = settings.WC_CONSUMER_SECRET

auth = HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET)

async def has_purchased(user_id: int, product_id: int) -> bool:
    """Check if a user has purchased a product."""
    try:
        logger.info(f"Checking purchase: user_id={user_id}, product_id={product_id}")
        response = await wc_api.get_orders(customer_id=user_id, status="completed")
        logger.info(f"Found {len(response)} completed orders for user {user_id}")
        
        for order in response:
            for item in order.get("line_items", []):
                logger.info(f"Order item: product_id={item.get('product_id')}, searching for={product_id}")
                if item["product_id"] == product_id:
                    logger.info(f"✅ User {user_id} HAS purchased product {product_id}")
                    return True
        
        logger.info(f"❌ User {user_id} has NOT purchased product {product_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking purchase status for user {user_id}, product {product_id}: {e}")
        return False

# --- Permission Check Helpers ---
async def is_admin(user_id: int) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{WC_API_BASE}/customers/{user_id}",
                auth=auth,
            )
        print("Admin status response:", response.status_code, response.text)

        if response.status_code == 200:
            data = response.json()
            print("User roles field:", data.get("role"), data.get("roles"))
            
            roles = data.get("role") or data.get("roles") or []
            if isinstance(roles, list):
                return "administrator" in [role.lower() for role in roles]
            elif isinstance(roles, str):
                return "administrator" == roles.lower()
    except httpx.RequestError as e:
        print(f"Error checking admin status: {e}")
    return False
