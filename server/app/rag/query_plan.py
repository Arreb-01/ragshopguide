from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


PRICE_PATTERNS = [
    re.compile(r"(?:预算|价格|价位)?\s*(\d+(?:\.\d+)?)\s*元?\s*(?:以下|以内|内|之内)"),
    re.compile(r"预算\s*(?:压到|控制在)?\s*(\d+(?:\.\d+)?)"),
]

BRAND_ALIASES = {
    "nike": ["Nike", "耐克"],
    "耐克": ["Nike", "耐克"],
    "苹果": ["Apple 苹果", "苹果"],
    "apple": ["Apple 苹果", "苹果"],
}

JAPANESE_BEAUTY_BRANDS = ["安热沙", "资生堂", "珊珂", "芳珂", "SK-II"]

PRODUCT_MENTIONS = {
    "iphone 17 pro": "p_digital_001",
    "iPhone 17 Pro": "p_digital_001",
    "华为 pura 90": "p_digital_002",
    "Pura 90": "p_digital_002",
    "pura 90": "p_digital_002",
}


@dataclass
class QueryPlan:
    intent: str = "recommendation"
    max_price: float | None = None
    excluded_brands: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)
    required_keywords: list[str] = field(default_factory=list)
    compare_product_ids: list[str] = field(default_factory=list)
    scene_key: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "max_price": self.max_price,
            "excluded_brands": self.excluded_brands,
            "excluded_keywords": self.excluded_keywords,
            "required_keywords": self.required_keywords,
            "compare_product_ids": self.compare_product_ids,
            "scene_key": self.scene_key,
        }


def build_query_plan(
    query: str,
    history: list[dict[str, str]] | None = None,
) -> QueryPlan:
    conversation_text = query if _should_reset_history(query) else _conversation_text(query, history)
    plan = QueryPlan()
    plan.max_price = _extract_max_price(conversation_text)
    plan.excluded_brands = _extract_excluded_brands(conversation_text)
    plan.excluded_keywords = _extract_excluded_keywords(conversation_text)
    plan.required_keywords = _extract_required_keywords(conversation_text)
    plan.compare_product_ids = _extract_compare_product_ids(conversation_text)
    plan.scene_key = _extract_scene_key(conversation_text)

    has_comparison_words = any(
        word in conversation_text for word in ["对比", "比一下", "哪个更"]
    )
    if len(plan.compare_product_ids) >= 2 or has_comparison_words:
        plan.intent = "comparison"
    elif plan.scene_key:
        plan.intent = "cross_category_scene"
    elif plan.excluded_brands or plan.excluded_keywords:
        plan.intent = "exclusion"
    elif plan.max_price is not None:
        plan.intent = "conditional_filter"
    elif any(word in conversation_text for word in ["续航", "用户评价", "真实反馈", "好不好"]):
        plan.intent = "source_query"
    return plan


def build_retrieval_queries(query: str, plan: QueryPlan) -> list[str]:
    if plan.scene_key == "fitness_entry":
        return [
            "健身 入门 速干 训练 上衣",
            "健身 入门 跑鞋 训练鞋 轻便",
            "健身 入门 功能饮料 能量 补给",
            query,
        ]
    if plan.intent == "comparison" and len(plan.compare_product_ids) >= 2:
        return [query, " ".join(plan.compare_product_ids)]
    if plan.required_keywords:
        return [" ".join([query, *plan.required_keywords])]
    return [query]


def apply_query_plan_filters(
    chunks: list[dict[str, Any]],
    plan: QueryPlan,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        text = f"{chunk.get('text', '')} {metadata.get('title', '')} {metadata.get('brand', '')}"

        if plan.max_price is not None:
            try:
                if float(metadata.get("base_price", 0)) > plan.max_price:
                    continue
            except (TypeError, ValueError):
                continue

        brand = str(metadata.get("brand", ""))
        if any(_contains_case_insensitive(brand, excluded) for excluded in plan.excluded_brands):
            continue
        if any(_contains_case_insensitive(text, keyword) for keyword in plan.excluded_keywords):
            continue

        filtered.append(chunk)
    return filtered


def source_counts(chunks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in chunks:
        source_type = str(chunk.get("metadata", {}).get("source_type", ""))
        public_type = _public_source_type(source_type)
        if not public_type:
            continue
        counts[public_type] = counts.get(public_type, 0) + 1
    return counts


def _conversation_text(
    query: str,
    history: list[dict[str, str]] | None,
) -> str:
    parts: list[str] = []
    for item in history or []:
        if item.get("role") == "user" and item.get("content"):
            parts.append(str(item["content"]))
    parts.append(query)
    return "\n".join(parts)


def _should_reset_history(query: str) -> bool:
    return bool(_extract_compare_product_ids(query))


def _extract_max_price(text: str) -> float | None:
    values: list[float] = []
    for pattern in PRICE_PATTERNS:
        values.extend(float(match) for match in pattern.findall(text))
    if not values:
        return None
    value = values[-1]
    return int(value) if value.is_integer() else value


def _extract_excluded_brands(text: str) -> list[str]:
    excluded: list[str] = []
    lowered = text.lower()
    if "不要日系品牌" in text or "排除日系品牌" in text:
        excluded.extend(JAPANESE_BEAUTY_BRANDS)

    for alias, brands in BRAND_ALIASES.items():
        if f"不要 {alias}".lower() in lowered or f"不要{alias}".lower() in lowered:
            excluded.extend(brands)
        if f"排除 {alias}".lower() in lowered or f"排除{alias}".lower() in lowered:
            excluded.extend(brands)

    return _dedupe(excluded)


def _extract_excluded_keywords(text: str) -> list[str]:
    keywords: list[str] = []
    if "不要含酒精" in text or "不含酒精" in text or "含酒精" in text:
        keywords.append("酒精")
    if "不要含糖太高" in text or "不要高糖" in text or "含糖太高" in text:
        keywords.extend(["高糖", "含糖"])
    return _dedupe(keywords)


def _extract_required_keywords(text: str) -> list[str]:
    keywords: list[str] = []
    if "跑鞋" in text:
        keywords.append("跑鞋")
    if "轻便" in text or "轻量" in text:
        keywords.append("轻便")
    if any(word in text for word in ["健身", "撸铁", "健身卡"]):
        keywords.extend(["速干", "跑鞋", "功能饮料"])
    return _dedupe(keywords)


def _extract_compare_product_ids(text: str) -> list[str]:
    product_ids: list[str] = []
    lowered = text.lower()
    for mention, product_id in PRODUCT_MENTIONS.items():
        if mention.lower() in lowered or mention in text:
            product_ids.append(product_id)
    return _dedupe(product_ids)


def _extract_scene_key(text: str) -> str | None:
    if any(word in text for word in ["健身卡", "撸铁", "健身入门", "入门装备"]):
        return "fitness_entry"
    return None


def _public_source_type(source_type: str) -> str:
    if source_type in {"basic", "faq"}:
        return "official"
    if source_type == "review":
        return "review"
    if source_type == "marketing":
        return "marketing"
    return ""


def _contains_case_insensitive(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
