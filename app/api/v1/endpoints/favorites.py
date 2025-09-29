# app/api/v1/endpoints/favorites.py
from fastapi import APIRouter, Depends
from app.api.deps import oauth2_scheme
from app.services.favorites import favorite_service

router = APIRouter(tags=["favorites"])

@router.get("/")
async def list_favorites(token: str = Depends(oauth2_scheme)):
    return await favorite_service.get_favorites(token)

@router.post("/{product_id}")
async def add_favorite(product_id: int, token: str = Depends(oauth2_scheme)):
    return await favorite_service.add_favorite(token, product_id)

@router.delete("/{product_id}")
async def remove_favorite(product_id: int, token: str = Depends(oauth2_scheme)):
    return await favorite_service.remove_favorite(token, product_id)
