from pydantic import BaseModel, Field
from typing import Optional, List

class ProductFilters(BaseModel):
    """
    Filters for product listings with WooCommerce API compatible parameters
    """
    category: Optional[str] = Field(
        None,
        description="Filter by category slug",
        example="ebooks"
    )
    search: Optional[str] = Field(
        None,
        description="Search query",
        example="science fiction"
    )
    orderby: Optional[str] = Field(
        "date",
        description="Sort collection by attribute",
        example="price"
    )
    order: Optional[str] = Field(
        "desc",
        description="Order sort attribute ascending or descending",
        example="asc"
    )
    per_page: Optional[int] = Field(
        10,
        description="Maximum number of items to be returned in result set",
        ge=1,
        le=100
    )
    page: Optional[int] = Field(
        1,
        description="Current page of the collection",
        ge=1
    )
    status: Optional[str] = Field(
        "publish",
        description="Limit result set to products assigned a specific status",
        example="publish"
    )
    include: Optional[List[int]] = Field(
        None,
        description="Limit result set to specific IDs"
    )
    exclude: Optional[List[int]] = Field(
        None,
        description="Ensure result set excludes specific IDs"
    )
    slug: Optional[str] = Field(
        None,
        description="Limit result set to products with a specific slug",
        example="premium-ebook"
    )

    def dict(self, **kwargs):
        # Remove None values to clean up the query params
        data = super().dict(**kwargs)
        return {k: v for k, v in data.items() if v is not None}