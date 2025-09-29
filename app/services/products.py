# app/services/products.py
import httpx
from typing import List, Dict, Optional, Set
from app.utils.wc_api import wc_api
from app.services.permissions import has_purchased, is_admin
from app.utils.cache import get_cached, set_cached
import asyncio
import re
import logging  # ← Add this
from app.services.favorites import favorite_service
from app.core.config import settings

logger = logging.getLogger(__name__)  # ← Add this

CATEGORY_CACHE_TTL = 3600  # 1 hour

split_pattern = re.compile(r'\s*[,&]\s*')

# -----------------------------
# Product Authors
# -----------------------------
async def get_all_product_authors() -> List[str]:
    raw_products = await wc_api.get_products(params={'per_page': 100})
    authors: Set[str] = set()
    
    for product in raw_products:
        author_value = next((meta.get('value') for meta in product.get('meta_data', []) if meta.get('key') == 'author'), None)
        if author_value:
            for name in split_pattern.split(author_value):
                if name.strip():
                    authors.add(name.strip().title())
    return sorted(authors)

# -----------------------------
# Product Genres
# -----------------------------
async def get_all_product_genres() -> List[str]:
    genres = await wc_api.get_tags()
    return genres

# -----------------------------
# Category enrichment with caching
# -----------------------------
async def enrich_product_categories(product: Dict) -> Dict:
    if "categories" not in product:
        return product

    async def fetch_category(cat):
        cache_key = f"category:{cat['id']}"
        cached = await get_cached(cache_key)
        if cached:
            return cached
        category = await wc_api.get_category(cat["id"])
        if category:
            enriched = {"id": category["id"], "name": category["name"], "image": category.get("image", {}).get("src")}
            await set_cached(cache_key, enriched, ttl=CATEGORY_CACHE_TTL)
            return enriched
        return None

    enriched_categories = await asyncio.gather(*(fetch_category(cat) for cat in product["categories"]))
    product["categories"] = [c for c in enriched_categories if c]
    return product

# -----------------------------
# Permission caching helper
# -----------------------------
async def sanitize_products_bulk(products: List[Dict], user_id: Optional[int]) -> List[Dict]:
    logger.info(f"Sanitizing {len(products)} products for user_id: {user_id}")
    
    if not user_id:
        logger.info("No user_id, removing ebook URLs for all products")
        for product in products:
            product["meta_data"] = [meta for meta in product.get("meta_data", []) if meta.get("key") != "_ebook_stream_url"]
        return products

    # Cache user permissions for 5 minutes
    admin_cache_key = f"user_is_admin:{user_id}"

    is_user_admin = await get_cached(admin_cache_key)
    if is_user_admin is None:
        is_user_admin = await is_admin(user_id)
        logger.info(f"User {user_id} admin status: {is_user_admin}")
        await set_cached(admin_cache_key, is_user_admin, ttl=300)
    else:
        logger.info(f"User {user_id} admin status (cached): {is_user_admin}")

    # Bulk process permissions
    async def process_product(product):
        product_id = product["id"]
        allowed = is_user_admin
        
        if not allowed:
            product_purchase_key = f"user_purchase:{user_id}:{product_id}"
            purchased = await get_cached(product_purchase_key)
            if purchased is None:
                purchased = await has_purchased(user_id, product_id)
                logger.info(f"User {user_id} purchase check for product {product_id}: {purchased}")
                await set_cached(product_purchase_key, purchased, ttl=300)
            else:
                logger.info(f"User {user_id} purchase status for product {product_id} (cached): {purchased}")
            allowed = purchased

        if not allowed:
            # Count ebook URLs before removal
            ebook_count = len([meta for meta in product.get("meta_data", []) if meta.get("key") == "_ebook_stream_url"])
            product["meta_data"] = [meta for meta in product.get("meta_data", []) if meta.get("key") != "_ebook_stream_url"]
            if ebook_count > 0:
                logger.info(f"Removed {ebook_count} ebook URLs from product {product_id} for user {user_id}")
        else:
            logger.info(f"User {user_id} has access to product {product_id}")
            
        return product

    return await asyncio.gather(*(process_product(p) for p in products))

# -----------------------------
# Get products for user (library or general)
# -----------------------------
async def get_products_for_user(user_id: Optional[int], filters: Dict) -> List[Dict]:
    raw_products = await wc_api.get_products(params=filters)
    # Enrich categories in parallel
    enriched_products = await asyncio.gather(*(enrich_product_categories(p) for p in raw_products))
    # Apply permission filtering
    return await sanitize_products_bulk(enriched_products, user_id)

async def get_products_for_user_library(user_id: Optional[int], filters: Dict) -> List[Dict]:
    products = await get_products_for_user(user_id, filters)
    # Only keep products with ebook stream URL
    return [p for p in products if any(meta.get("key") == "_ebook_stream_url" for meta in p.get("meta_data", []))]

# -----------------------------
# Single product
# -----------------------------
async def get_product_by_slug(slug: str, user_id: Optional[int], token: Optional[str] = None) -> Dict:
    product = await wc_api.get_product(slug)
    enriched = await enrich_product_categories(product)
    sanitized_list = await sanitize_products_bulk([enriched], user_id)
    product_data = sanitized_list[0]

    # If token is provided, check favorites
    if token:
        favorites_result = await favorite_service.get_favorites(token)
        if favorites_result.get("success") and isinstance(favorites_result.get("data"), list):
            product_data["favorite"] = product_data.get("id") in favorites_result["data"]
        else:
            product_data["favorite"] = False

    return product_data

# -----------------------------
# Featured products
# -----------------------------
async def get_all_featured_products(filters: Dict) -> List[Dict]:
    return await wc_api.get_products(params=filters)


# -----------------------------
# Favorite products
# -----------------------------
async def get_favorite_products_for_user(token: str):
    result = await favorite_service.get_favorites(token)
    if not result["success"]:
        return []

    product_ids = result["data"]  # e.g., [226, 305, 412]
    if not product_ids:
        return []

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.WP_URL}/wp-json/wc/v3/products",
            params={"include": ",".join(map(str, product_ids))},
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        return resp.json()
