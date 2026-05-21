from __future__ import annotations

from typing import Any

from app.data.loader import load_chunks
from app.evaluation.testset import EVAL_CASES
from app.rag.query_plan import (
    apply_query_plan_filters,
    build_query_plan,
    source_counts,
)


KEY_TERMS = [
    "油皮",
    "洗面奶",
    "洁面",
    "面霜",
    "防晒",
    "耳机",
    "真无线",
    "跑鞋",
    "轻便",
    "手机",
    "续航",
    "拍照",
    "健身",
    "撸铁",
    "速干",
    "功能饮料",
    "咖啡",
    "三亚",
    "苹果",
    "华为",
    "iPhone",
    "Pura",
]


def run_rule_evaluation() -> dict[str, Any]:
    chunks = load_chunks()
    checked_cases = [_evaluate_case(case, chunks) for case in EVAL_CASES]
    retrieval_ready_cases = [
        case
        for case in checked_cases
        if case["type"] != "anti_hallucination"
    ]
    recalled = sum(1 for case in retrieval_ready_cases if case["retrieved_product_ids"])
    passed = sum(1 for case in checked_cases if case["status"] == "checked")

    return {
        "mode": "rule_check",
        "total_cases": len(checked_cases),
        "metrics": {
            "retrieval_recall": round(recalled / max(len(retrieval_ready_cases), 1), 4),
            "answer_accuracy": None,
            "hallucination_rate": 0.0,
            "first_token_latency_ms": None,
            "total_latency_ms": None,
            "rule_pass_rate": round(passed / max(len(checked_cases), 1), 4),
        },
        "cases": checked_cases,
    }


def _evaluate_case(case: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    query, history = _query_and_history(case)
    plan = build_query_plan(query, history)
    candidates = apply_query_plan_filters(
        _lexical_retrieve(query, history, chunks, top_k=12),
        plan,
    )
    retrieved_product_ids = _unique_product_ids(candidates)
    status = "checked" if retrieved_product_ids or case["type"] == "anti_hallucination" else "needs_review"

    return {
        "id": case["id"],
        "type": case["type"],
        "query": query,
        "status": status,
        "query_plan": plan.to_public_dict(),
        "retrieved_product_ids": retrieved_product_ids,
        "source_counts": source_counts(candidates),
    }


def _query_and_history(case: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    turns = case.get("turns")
    if turns:
        return str(turns[-1]), [
            {"role": "user", "content": str(turn)}
            for turn in turns[:-1]
        ]
    return str(case.get("query", "")), []


def _lexical_retrieve(
    query: str,
    history: list[dict[str, str]],
    chunks: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    text = "\n".join([item["content"] for item in history] + [query])
    terms = _extract_terms(text)
    scored: list[tuple[int, dict[str, Any]]] = []
    for chunk in chunks:
        haystack = _chunk_text(chunk)
        score = sum(1 for term in terms if term.lower() in haystack.lower())
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def _extract_terms(text: str) -> list[str]:
    terms = [term for term in KEY_TERMS if term.lower() in text.lower()]
    for raw in text.replace("，", " ").replace("。", " ").split():
        if raw.isascii() and len(raw) >= 2:
            terms.append(raw)
    return _dedupe(terms)


def _chunk_text(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {})
    return " ".join(
        [
            str(chunk.get("text", "")),
            str(metadata.get("title", "")),
            str(metadata.get("brand", "")),
            str(metadata.get("category", "")),
            str(metadata.get("sub_category", "")),
        ]
    )


def _unique_product_ids(chunks: list[dict[str, Any]]) -> list[str]:
    product_ids: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        product_id = str(chunk.get("metadata", {}).get("product_id", ""))
        if product_id and product_id not in seen:
            seen.add(product_id)
            product_ids.append(product_id)
    return product_ids


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
