from __future__ import annotations

from functools import lru_cache
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter

from app.data.loader import load_products


router = APIRouter(prefix="", tags=["products"])


@router.get("/products")
def products_endpoint() -> dict[str, list[dict[str, Any]]]:
    """Return lightweight product metadata for client-side card rendering."""

    return {"products": get_product_cards()}


@lru_cache(maxsize=1)
def get_product_cards() -> list[dict[str, Any]]:
    return [_to_product_card(product) for product in load_products()]


def _to_product_card(product: dict[str, Any]) -> dict[str, Any]:
    image_path = str(product.get("image_path", "")).replace("\\", "/")
    category = str(product.get("category", ""))
    sub_category = str(product.get("sub_category", ""))
    brand = str(product.get("brand", ""))

    return {
        "product_id": str(product.get("product_id", "")),
        "title": str(product.get("title", "")),
        "brand": brand,
        "category": category,
        "sub_category": sub_category,
        "base_price": float(product.get("base_price", 0.0)),
        "image_path": image_path,
        "image_url": f"/static/images/{quote(image_path, safe='/')}",
        "tags": [tag for tag in [category, sub_category, brand] if tag],
    }
