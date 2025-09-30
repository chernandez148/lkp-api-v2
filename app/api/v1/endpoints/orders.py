# app/api/v1/endpoints/orders.py
from fastapi import APIRouter, Depends
from typing import Optional
from app.services.orders import create_user_order, list_user_orders
from app.schemas.order import OrderCreate, OrderResponse, PaginatedOrderResponse
from app.api.deps import get_current_user
from app.schemas.token import TokenData  # or your user schema

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: TokenData = Depends(get_current_user),
):
    return await create_user_order(order_data, current_user)

@router.get("/", response_model=PaginatedOrderResponse)
async def list_orders(
    current_user: TokenData = Depends(get_current_user),
    page: Optional[int] = 1,
    per_page: Optional[int] = 10,
):
    return await list_user_orders(current_user, page, per_page)
