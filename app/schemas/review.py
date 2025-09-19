# app/schemas/review.py
from pydantic import BaseModel, EmailStr, conint, constr

# Pydantic models for request/response validation
class ReviewCreate(BaseModel):
    product_id: int
    review: constr(min_length=10)
    reviewer: constr(min_length=2)
    reviewer_email: EmailStr
    rating: conint(ge=1, le=5)

class ReviewResponse(BaseModel):
    id: int
    product_id: int
    status: str
    reviewer: str
    reviewer_email: str
    review: str
    rating: int
    date_created: str