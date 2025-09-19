from pydantic import BaseModel, EmailStr
from typing import List, Optional

class LineItem(BaseModel):
    product_id: int
    quantity: int
    name: Optional[str] = None  # Optional: Name of the product
    total: Optional[float] = None  # Optional: Price per unit of the product
    sku: Optional[str] = None  # Optional: SKU (Stock Keeping Unit) for the product

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
    status: str
    total: str
    payment_method: str
    payment_method_title: str
    stripe_payment_intent_client_secret: str  # Make sure this exists
    payment_url: Optional[str] = None

class OrderListResponse(BaseModel):
    line_items: List[LineItem]
    total: str
    date_created: str

class Config:
    extra = "ignore"  # Ignore fields WC sends that we don't define