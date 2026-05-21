from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "dataset" / "ecommerce_agent_dataset"


def load_products(dataset_root: str | Path | None = None) -> list[dict[str, Any]]:
    """Load all product JSON files from the competition dataset."""

    root = Path(dataset_root) if dataset_root else DEFAULT_DATASET_ROOT
    if not root.exists():
        raise FileNotFoundError(f"Dataset root not found: {root}")

    products: list[dict[str, Any]] = []
    for json_path in sorted(root.glob("*/data/*.json")):
        with json_path.open("r", encoding="utf-8") as file:
            product = json.load(file)
        product["_json_path"] = str(json_path)
        products.append(product)
    return products


def load_chunks(dataset_root: str | Path | None = None) -> list[dict[str, Any]]:
    """Split products into source-aware RAG chunks."""

    chunks: list[dict[str, Any]] = []
    for product in load_products(dataset_root):
        chunks.extend(_product_to_chunks(product))
    return chunks


def summarize_chunks(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Return simple stats used by indexing scripts and smoke checks."""

    source_counts = Counter(chunk["metadata"]["source_type"] for chunk in chunks)
    product_ids = {chunk["metadata"]["product_id"] for chunk in chunks}
    return {
        "product_count": len(product_ids),
        "chunk_count": len(chunks),
        "source_counts": dict(sorted(source_counts.items())),
    }


def _product_to_chunks(product: dict[str, Any]) -> list[dict[str, Any]]:
    product_id = str(product["product_id"])
    base_metadata = _base_metadata(product)
    knowledge = product.get("rag_knowledge", {})

    chunks = [
        {
            "id": f"{product_id}:basic",
            "text": _build_basic_text(product),
            "metadata": {**base_metadata, "source_type": "basic"},
        },
        {
            "id": f"{product_id}:marketing",
            "text": _build_marketing_text(product),
            "metadata": {**base_metadata, "source_type": "marketing"},
        },
    ]

    for index, faq in enumerate(knowledge.get("official_faq", []), start=1):
        chunks.append(
            {
                "id": f"{product_id}:faq:{index}",
                "text": _build_faq_text(product, faq),
                "metadata": {**base_metadata, "source_type": "faq"},
            }
        )

    for index, review in enumerate(knowledge.get("user_reviews", []), start=1):
        chunks.append(
            {
                "id": f"{product_id}:review:{index}",
                "text": _build_review_text(product, review),
                "metadata": {
                    **base_metadata,
                    "source_type": "review",
                    "rating": int(review.get("rating", 0)),
                },
            }
        )

    return chunks


def _base_metadata(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_id": str(product["product_id"]),
        "category": str(product.get("category", "")),
        "sub_category": str(product.get("sub_category", "")),
        "brand": str(product.get("brand", "")),
        "base_price": float(product.get("base_price", 0.0)),
        "title": str(product.get("title", "")),
        "image_path": str(product.get("image_path", "")),
    }


def _build_basic_text(product: dict[str, Any]) -> str:
    sku_lines = []
    for sku in product.get("skus", []):
        properties = "，".join(
            f"{key}:{value}" for key, value in sku.get("properties", {}).items()
        )
        sku_lines.append(
            f"- {sku.get('sku_id', '')}: {properties}，价格 {sku.get('price', '')} 元"
        )

    sku_text = "\n".join(sku_lines)
    return (
        f"商品基础信息\n"
        f"商品ID：{product.get('product_id', '')}\n"
        f"标题：{product.get('title', '')}\n"
        f"品牌：{product.get('brand', '')}\n"
        f"品类：{product.get('category', '')} / {product.get('sub_category', '')}\n"
        f"基础价：{product.get('base_price', '')} 元\n"
        f"SKU：\n{sku_text}"
    )


def _build_marketing_text(product: dict[str, Any]) -> str:
    description = product.get("rag_knowledge", {}).get("marketing_description", "")
    return (
        f"商家营销描述\n"
        f"商品：{product.get('title', '')}\n"
        f"品牌：{product.get('brand', '')}\n"
        f"内容：{description}"
    )


def _build_faq_text(product: dict[str, Any], faq: dict[str, Any]) -> str:
    return (
        f"官方问答\n"
        f"商品：{product.get('title', '')}\n"
        f"问题：{faq.get('question', '')}\n"
        f"回答：{faq.get('answer', '')}"
    )


def _build_review_text(product: dict[str, Any], review: dict[str, Any]) -> str:
    return (
        f"用户评价\n"
        f"商品：{product.get('title', '')}\n"
        f"用户：{review.get('nickname', '')}\n"
        f"评分：{review.get('rating', '')}/5\n"
        f"内容：{review.get('content', '')}"
    )
