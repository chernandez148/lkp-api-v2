from pydantic import BaseModel, EmailStr
from typing import List, Optional

class LineItem(BaseModel):
    product_id: int
    quantity: int
    name: Optional[str] = None  # Optional: Name of the product
    total: Optional[str] = None  # Optional: Price per unit of the product
    authorStripeID: Optional[str] = None

class BillingInfo(BaseModel):
    first_name: str
    last_name: str
    address_1: str
    city: str
    state: str
    postcode: str
    country: str
    email: EmailStr
    phone: str

class OrderCreate(BaseModel):
    payment_method: str
    payment_method_title: str
    set_paid: bool
    billing: BillingInfo
    line_items: List[LineItem]

class OrderResponse(BaseModel):
    id: int
    status: str
    total: str
    payment_method: str
    payment_method_title: str
    stripe_payment_intent_client_secret: str
    payment_url: Optional[str] = None

class OrderListItem(BaseModel):
    id: int
    name: str
    quantity: int
    total: str
    product_id: Optional[int] = None
    sku: Optional[str] = None

class OrderListResponse(BaseModel):
    id: int
    status: str
    line_items: List[OrderListItem]
    total: str
    date_created: str

    class Config:
        extra = "ignore"

class PaginatedOrderResponse(BaseModel):
    data: List[OrderListResponse]
    total: int
    total_pages: int
    current_page: int
    per_page: int