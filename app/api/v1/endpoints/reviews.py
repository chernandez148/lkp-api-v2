# app/api/v1/endpoints/products.py
from fastapi import APIRouter
from app.services.reviews import get_product_reviews

router = APIRouter()

@router.get("/")
async def get_reviews(product: int, page: int = 1):
    print(f"Product ID (product): {product}, Page: {page}")
    return await get_product_reviews(product, page)
