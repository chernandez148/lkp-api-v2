# app/api/v1/endpoints/products.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.services.products import (
    get_products_for_user,
    get_products_for_user_library,
    get_product_by_slug,
    get_all_product_authors,
    get_all_product_genres,
    get_all_featured_products
)
from app.schemas.filters import ProductFilters
from app.utils.cache import get_cached, set_cached
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

CACHE_TTL_PRODUCTS = 120
CACHE_TTL_SINGLE_PRODUCT = 300
CACHE_TTL_GENRES = 300
CACHE_TTL_AUTHORS = 300
CACHE_TTL_FEATURED = 600
CACHE_TTL_LIBRARY = 180

def make_cache_key(prefix: str, user_id: Optional[int] = None, filters: dict = None, slug: str = None):
    key_parts = [prefix]
    if filters:
        key_parts.append(json.dumps(filters, sort_keys=True))
    if slug:
        key_parts.append(slug)
    if user_id:
        key_parts.append(str(user_id))
    return ":".join(key_parts)

@router.get("/")
async def list_products(filters: ProductFilters = Depends(), user_id: Optional[int] = Query(None)):
    cache_key = make_cache_key("products", user_id, filters.dict())
    cached = await get_cached(cache_key)
    if cached:
        return cached
    products = await get_products_for_user(user_id, filters.dict())
    await set_cached(cache_key, products, ttl=CACHE_TTL_PRODUCTS)
    return products

@router.get("/library")
async def list_ebook_products(filters: ProductFilters = Depends(), user_id: Optional[int] = Query(None)):
    cache_key = make_cache_key("library_products", user_id, filters.dict())
    cached = await get_cached(cache_key)
    if cached:
        return cached
    products = await get_products_for_user_library(user_id, filters.dict())
    await set_cached(cache_key, products, ttl=CACHE_TTL_LIBRARY)
    return products

@router.get("/featured")
async def list_featured_products(featured: bool = True):
    cache_key = make_cache_key("featured_products", filters={"featured": featured})
    cached = await get_cached(cache_key)
    if cached:
        return cached
    products = await get_all_featured_products({"featured": featured})
    await set_cached(cache_key, products, ttl=CACHE_TTL_FEATURED)
    return products

@router.get("/genres")
async def list_product_genres():
    cache_key = make_cache_key("genres")
    cached = await get_cached(cache_key)
    if cached:
        return cached
    genres = await get_all_product_genres()
    await set_cached(cache_key, genres, ttl=CACHE_TTL_GENRES)
    return genres

@router.get("/authors")
async def list_product_authors(search: Optional[str] = Query(None)):
    cache_key = make_cache_key("authors", filters={"search": search or "all"})
    cached = await get_cached(cache_key)
    if cached:
        return cached
    authors = await get_all_product_authors()
    if search:
        search_lower = search.lower()
        authors = [a for a in authors if search_lower in a.lower()]
    result = [{"name": a} for a in authors]
    await set_cached(cache_key, result, ttl=CACHE_TTL_AUTHORS)
    return result

@router.get("/{slug}")
async def get_product(slug: str, user_id: Optional[int] = Query(None)):
    cache_key = make_cache_key("product", user_id, slug=slug)
    cached = await get_cached(cache_key)
    if cached:
        return cached
    product = await get_product_by_slug(slug, user_id)
    await set_cached(cache_key, product, ttl=CACHE_TTL_SINGLE_PRODUCT)
    return product
