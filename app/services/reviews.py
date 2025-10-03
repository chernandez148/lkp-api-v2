# app/services/reviews.py
from typing import List, Dict
from fastapi import HTTPException
from app.schemas.review import ReviewCreate, ReviewResponse
from app.utils.wc_api import wc_api

async def get_product_reviews(product_id: int, page: int = 1) -> List[Dict]:
    """Get all reviews for a product with pagination"""
    reviews = await wc_api.get_reviews(product_id, page=page)  # Handle page in the API request
    return [
        {
            "id": r["id"],
            "product_id": r["product_id"],
            "status": r["status"],
            "reviewer": r["reviewer"],
            "reviewer_email": r["reviewer_email"],
            "review": r["review"],
            "rating": r["rating"],
            "date_created": r["date_created"]
        }
        for r in reviews
    ]


async def create_product_review(review_data: ReviewCreate) -> ReviewResponse:
    """Create a new product review"""
    payload = {
        "product_id": review_data.product_id,
        "review": review_data.review,
        "reviewer": review_data.reviewer,
        "reviewer_email": review_data.reviewer_email,
        "rating": review_data.rating,
        "status": "approved"
    }
    
    created_review = await wc_api.create_review(payload)
    return ReviewResponse(**created_review)