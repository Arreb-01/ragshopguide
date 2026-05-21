from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any, Callable

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.data.loader import load_chunks
from app.llm.doubao_client import DoubaoClient
from app.rag.pipeline import (
    extract_compare_product_ids,
    extract_product_ids,
    extract_source_blocks,
    unique_retrieved_product_ids,
)
from app.rag.prompts import build_rag_messages
from app.rag.query_plan import (
    QueryPlan,
    apply_query_plan_filters,
    build_query_plan,
    build_retrieval_queries,
    source_counts,
)
from app.rag.retriever import retrieve


router = APIRouter(prefix="", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)


RetrieveFunc = Callable[..., list[dict[str, Any]]]
LlmClientFactory = Callable[[], DoubaoClient]


@router.post("/chat")
async def chat_endpoint(request: ChatRequest) -> StreamingResponse:
    """Stream a RAG answer as SSE for SwiftUI incremental rendering."""

    return StreamingResponse(
        _stream_chat(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_chat(
    request: ChatRequest,
    retrieve_func: RetrieveFunc = retrieve,
    llm_client_factory: LlmClientFactory = DoubaoClient,
) -> AsyncIterator[str]:
    if not request.query.strip():
        yield _sse("error", {"message": "query must not be empty"})
        return

    full_reply: list[str] = []
    retrieved_chunks: list[dict[str, Any]] = []
    start_time = time.perf_counter()

    try:
        # 检索先于生成，保证 prompt 中的商品范围可解释、可回溯。
        query_plan = build_query_plan(request.query, request.history)
        retrieved_chunks = _retrieve_with_query_plan(
            request.query,
            query_plan,
            retrieve_func,
        )
        retrieval_ms = _elapsed_ms(start_time)
        yield _sse(
            "meta",
            {
                "session_id": request.session_id,
                "retrieved_product_ids": unique_retrieved_product_ids(
                    retrieved_chunks
                ),
                "query_plan": query_plan.to_public_dict(),
                "source_counts": source_counts(retrieved_chunks),
                "timings_ms": {"retrieval": retrieval_ms},
            },
        )

        messages = build_rag_messages(request.query, retrieved_chunks, request.history)
        stream = llm_client_factory().chat(messages, stream=True)

        first_token_ms: int | None = None
        for chunk in stream:
            token = _extract_delta_content(chunk)
            if not token:
                continue
            if first_token_ms is None:
                first_token_ms = _elapsed_ms(start_time)
            full_reply.append(token)
            yield _sse("token", {"token": token})

        reply = "".join(full_reply)
        fallback_markers = _missing_protocol_markers(reply, retrieved_chunks, query_plan)
        if fallback_markers:
            full_reply.append(fallback_markers)
            reply = "".join(full_reply)
            yield _sse("token", {"token": fallback_markers})

        yield _sse(
            "done",
            {
                "product_ids": extract_product_ids(reply),
                "retrieved_product_ids": unique_retrieved_product_ids(
                    retrieved_chunks
                ),
                "compare_product_groups": extract_compare_product_ids(reply),
                "timings_ms": {
                    "first_token": first_token_ms,
                    "total": _elapsed_ms(start_time),
                },
            },
        )
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


def _sse(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _elapsed_ms(start_time: float) -> int:
    return max(0, int((time.perf_counter() - start_time) * 1000))


def _retrieve_with_query_plan(
    query: str,
    query_plan: QueryPlan,
    retrieve_func: RetrieveFunc,
) -> list[dict[str, Any]]:
    scene_evidence = _scene_chunks_for_query_plan(query_plan)
    if scene_evidence:
        return apply_query_plan_filters(_dedupe_chunks(scene_evidence), query_plan)

    product_evidence = _supporting_chunks_for_product_ids(query_plan.compare_product_ids)
    if query_plan.compare_product_ids and query_plan.intent in {
        "source_query",
        "comparison",
    }:
        return apply_query_plan_filters(_dedupe_chunks(product_evidence), query_plan)

    chunks: list[dict[str, Any]] = []
    for retrieval_query in build_retrieval_queries(query, query_plan):
        chunks.extend(retrieve_func(retrieval_query, top_k=5))

    chunks.extend(product_evidence)
    deduped = _dedupe_chunks(chunks)
    return apply_query_plan_filters(deduped, query_plan)


def _dedupe_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in chunks:
        chunk_id = str(chunk.get("id", ""))
        fallback_id = f"{chunk.get('metadata', {}).get('product_id', '')}:{chunk.get('text', '')}"
        key = chunk_id or fallback_id
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def _scene_chunks_for_query_plan(query_plan: QueryPlan) -> list[dict[str, Any]]:
    if query_plan.scene_key != "fitness_entry":
        return []

    candidate_chunks = apply_query_plan_filters(load_chunks(), query_plan)
    product_ids: list[str] = []
    for terms, limit in [
        (["速干", "短袖", "训练", "T恤"], 2),
        (["跑鞋", "训练鞋", "轻便", "缓震", "跑步鞋"], 2),
        (["功能饮料", "能量", "补给", "牛磺酸", "咖啡因"], 2),
    ]:
        product_ids.extend(
            _rank_product_ids_by_terms(candidate_chunks, terms, limit=limit)
        )
    return _supporting_chunks_for_product_ids(_dedupe_values(product_ids))


def _rank_product_ids_by_terms(
    chunks: list[dict[str, Any]],
    terms: list[str],
    limit: int,
) -> list[str]:
    scores: dict[str, int] = {}
    prices: dict[str, float] = {}
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        product_id = str(metadata.get("product_id", ""))
        if not product_id:
            continue
        haystack = _chunk_search_text(chunk)
        score = sum(1 for term in terms if term.lower() in haystack.lower())
        if score <= 0:
            continue
        scores[product_id] = scores.get(product_id, 0) + score
        try:
            prices[product_id] = float(metadata.get("base_price", 0.0))
        except (TypeError, ValueError):
            prices[product_id] = 0.0

    ranked = sorted(
        scores,
        key=lambda product_id: (-scores[product_id], prices.get(product_id, 0.0)),
    )
    return ranked[:limit]


def _chunk_search_text(chunk: dict[str, Any]) -> str:
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


def _supporting_chunks_for_product_ids(product_ids: list[str]) -> list[dict[str, Any]]:
    if not product_ids:
        return []

    by_product: dict[str, list[dict[str, Any]]] = {
        product_id: [] for product_id in product_ids
    }
    for chunk in load_chunks():
        product_id = str(chunk.get("metadata", {}).get("product_id", ""))
        if product_id in by_product:
            by_product[product_id].append(chunk)

    supporting: list[dict[str, Any]] = []
    for product_id in product_ids:
        supporting.extend(_select_source_diverse_chunks(by_product.get(product_id, [])))
    return supporting


def _select_source_diverse_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for source_type in ["basic", "faq", "review", "marketing"]:
        match = next(
            (
                chunk
                for chunk in chunks
                if chunk.get("id") not in selected_ids
                and chunk.get("metadata", {}).get("source_type") == source_type
            ),
            None,
        )
        if match:
            selected.append(match)
            selected_ids.add(str(match.get("id", "")))

    if len(selected) >= 4:
        return selected[:4]

    for chunk in sorted(
        chunks,
        key=lambda item: _source_priority(
            str(item.get("metadata", {}).get("source_type", ""))
        ),
    ):
        chunk_id = str(chunk.get("id", ""))
        if chunk_id in selected_ids:
            continue
        selected.append(chunk)
        selected_ids.add(chunk_id)
        if len(selected) >= 4:
            break
    return selected


def _dedupe_values(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _source_priority(source_type: str) -> int:
    return {
        "basic": 0,
        "faq": 1,
        "review": 2,
        "marketing": 3,
    }.get(source_type, 99)


def _missing_protocol_markers(
    reply: str,
    retrieved_chunks: list[dict[str, Any]],
    query_plan: QueryPlan,
) -> str:
    markers = _missing_source_markers(reply, retrieved_chunks)
    existing_product_ids = extract_product_ids(reply)
    compare_groups = extract_compare_product_ids(reply)
    if (
        query_plan.intent == "comparison"
        and not compare_groups
        and len(query_plan.compare_product_ids) >= 2
    ):
        markers.append("[[COMPARE:" + ",".join(query_plan.compare_product_ids[:3]) + "]]")
    elif existing_product_ids:
        markers.extend(
            f"[[PRODUCT:{product_id}]]"
            for product_id in _missing_fitness_scene_product_ids(
                existing_product_ids,
                retrieved_chunks,
                query_plan,
            )
        )
    else:
        candidate_ids = query_plan.compare_product_ids or unique_retrieved_product_ids(
            retrieved_chunks
        )
        markers.extend(f"[[PRODUCT:{product_id}]]" for product_id in candidate_ids[:6])

    if not markers:
        return ""
    return "\n" + "".join(markers)


def _missing_fitness_scene_product_ids(
    existing_product_ids: list[str],
    retrieved_chunks: list[dict[str, Any]],
    query_plan: QueryPlan,
) -> list[str]:
    if query_plan.scene_key != "fitness_entry":
        return []

    existing_buckets = {
        _fitness_bucket(chunk)
        for chunk in retrieved_chunks
        if chunk.get("metadata", {}).get("product_id") in existing_product_ids
    }
    missing_ids: list[str] = []
    for required_bucket in ["top", "shoe", "drink"]:
        if required_bucket in existing_buckets:
            continue
        product_id = _first_retrieved_product_id_for_bucket(
            retrieved_chunks,
            required_bucket,
            existing_product_ids + missing_ids,
        )
        if product_id:
            missing_ids.append(product_id)
    return missing_ids


def _first_retrieved_product_id_for_bucket(
    retrieved_chunks: list[dict[str, Any]],
    bucket: str,
    excluded_product_ids: list[str],
) -> str | None:
    excluded = set(excluded_product_ids)
    for chunk in retrieved_chunks:
        product_id = str(chunk.get("metadata", {}).get("product_id", ""))
        if product_id in excluded:
            continue
        if _fitness_bucket(chunk) == bucket:
            return product_id
    return None


def _fitness_bucket(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {})
    text = _chunk_search_text(chunk)
    product_id = str(metadata.get("product_id", ""))
    if product_id.startswith("p_food_") or "功能饮料" in text:
        return "drink"
    if any(word in text for word in ["跑鞋", "跑步鞋", "训练鞋"]):
        return "shoe"
    if any(word in text for word in ["速干", "短袖", "T恤", "上衣"]):
        return "top"
    return ""


def _missing_source_markers(
    reply: str,
    retrieved_chunks: list[dict[str, Any]],
) -> list[str]:
    existing_types = {
        block["source_type"]
        for block in extract_source_blocks(reply)
        if block.get("source_type")
    }
    counts = source_counts(retrieved_chunks)
    markers: list[str] = []

    source_messages = {
        "official": "官方信息已用于核对商品标题、品牌、价格和基础参数。",
        "review": "用户评价已用于补充真实使用反馈与体验风险。",
        "marketing": "商家话术已用于识别核心卖点，并和其他来源交叉核对。",
    }
    for source_type in ["official", "review", "marketing"]:
        if source_type in existing_types or counts.get(source_type, 0) <= 0:
            continue
        markers.append(f"[[SOURCE:{source_type}|{source_messages[source_type]}]]")

    if markers and "summary" not in existing_types:
        markers.append("[[SOURCE:summary|综合以上来源给出建议，不引入库外商品或价格。]]")
    return markers


def _extract_delta_content(chunk: Any) -> str:
    """Support OpenAI SDK stream chunks and dict-like test doubles."""

    if isinstance(chunk, dict):
        choices = chunk.get("choices") or []
        if not choices:
            return ""
        delta = choices[0].get("delta") or {}
        return delta.get("content") or ""

    choices = getattr(chunk, "choices", None) or []
    if not choices:
        return ""
    delta = getattr(choices[0], "delta", None)
    return getattr(delta, "content", None) or ""
