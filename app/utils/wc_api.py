# app/utils/wc_api.py
import httpx
from typing import Optional, Dict, List, Any
from fastapi import HTTPException
from app.core.config import settings

class WooCommerceAPI:
    def __init__(self):
        self.base_url = settings.WC_API_URL.rstrip('/')
        self.auth = (settings.WC_CONSUMER_KEY, settings.WC_CONSUMER_SECRET)
        self.timeout = 30.0
    
    async def _request(self, method: str, endpoint: str, return_headers: bool = False, **kwargs) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    url,
                    auth=self.auth,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                if return_headers:
                    return response.json(), response.headers
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"WooCommerce API error: {e.response.text}"
                )
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"WooCommerce connection error: {str(e)}"
                )
    
    async def get_products(self, params: Optional[Dict] = None) -> List[Dict]:
        return await self._request("GET", "products", params=params)
    
    async def get_product(self, slug: str) -> Dict:
        products = await self._request("GET", "products", params={"slug": slug})
        if not products:
            raise HTTPException(status_code=404, detail=f"Product with slug '{slug}' not found")
        return products[0]  # Return the first product from the list

    async def list_orders(self, customer_id: int, page: int, per_page: int) -> Dict:
        params = {"customer": customer_id, "page": page, "per_page": per_page}
        data, headers = await self._request("GET", "orders", params=params, return_headers=True)

        # Extract pagination info from headers
        total = int(headers.get("X-WP-Total", 0))
        total_pages = int(headers.get("X-WP-TotalPages", 0))

        return {
            "data": data,
            "total": total,
            "total_pages": total_pages,
            "current_page": page,
            "per_page": per_page
        }

    async def create_order(self, order_data: Dict) -> Dict:
        return await self._request("POST", "orders", json=order_data)

    async def get_order(self, order_id: int) -> Dict:
        """Fetch a single order by ID"""
        orders = await self._request("GET", f"orders/{order_id}")
        return orders
        
    async def update_order(self, order_id: int, status: str = "completed") -> Dict:
        params = {"status": status}
        return await self._request("POST", f"orders/{order_id}", params={"status": status})

    async def get_orders(self, customer_id: int, status: str = "completed") -> List[Dict]:
        params = {"customer": customer_id, "status": status}
        return await self._request("GET", "orders", params=params)
    
    async def get_category(self, category_id: int) -> Optional[Dict]:
        try:
            return await self._request("GET", f"products/categories/{category_id}")
        except HTTPException as e:
            if e.status_code == 404:
                return None
            raise

    async def get_tags(self) -> Optional[Dict]:
        try:
            return await self._request("GET", f"products/tags")
        except HTTPException as e:
            if e.status_code == 404:
                return None
            raise
    
    async def create_review(self, review_data: Dict) -> Dict:
        return await self._request("POST", "products/reviews", json=review_data)
    
    async def get_reviews(self, product_id: int, page:int, params: Optional[Dict] = None) -> List[Dict]:
        """Get reviews for a specific product"""
        if not params:
            params = {}
        params["product"] = product_id
        params["page"] = page 
        return await self._request("GET", "products/reviews", params=params)

# Singleton instance
wc_api = WooCommerceAPI()