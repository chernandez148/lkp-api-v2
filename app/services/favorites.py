import httpx
from app.core.config import settings

class FavoriteService:
    def __init__(self):
        self.base_url = f"{settings.WP_URL}/wp-json/custom/v1/favorites"

    async def _handle_response(self, resp: httpx.Response, action: str):
        try:
            resp.raise_for_status()
            return {
                "success": True,
                "message": f"{action} successful",
                "data": resp.json(),
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"{action} failed: {str(e)}",
                "data": None,
            }

    async def get_favorites(self, token: str):
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.base_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            return await self._handle_response(resp, "Get favorites")

    async def add_favorite(self, token: str, product_id: int):
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/add",
                headers={"Authorization": f"Bearer {token}"},
                json={"product_id": product_id}
            )
            return await self._handle_response(resp, "Add favorite")

    async def remove_favorite(self, token: str, product_id: int):
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/remove",
                headers={"Authorization": f"Bearer {token}"},
                json={"product_id": product_id}
            )
            return await self._handle_response(resp, "Remove favorite")

favorite_service = FavoriteService()
