# app/api/v1/routers.py
from fastapi import APIRouter, Depends
from app.api.v1.endpoints import auth, products, reviews, users, orders, favorites
from app.api.deps import get_current_user

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(users.router, prefix="/users", tags=["users"], dependencies=[Depends(get_current_user)])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"], dependencies=[Depends(get_current_user)])
api_router.include_router(favorites.router, prefix="/favorites", tags=["favorites"], dependencies=[Depends(get_current_user)])
