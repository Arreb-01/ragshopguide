from __future__ import annotations

import re
from typing import Any, Callable

from app.llm.doubao_client import DoubaoClient
from app.rag.prompts import build_rag_messages
from app.rag.retriever import retrieve as default_retrieve


PRODUCT_MARK_RE = re.compile(r"\[\[PRODUCT:([A-Za-z0-9_,\s-]+)\]\]")
COMPARE_MARK_RE = re.compile(r"\[\[COMPARE:([A-Za-z0-9_,\s-]+)\]\]")
SOURCE_MARK_RE = re.compile(
    r"\[\[SOURCE:(official|review|marketing|summary)\|(.*?)\]\]",
    re.DOTALL,
)


def chat(
    query: str,
    history: list[dict[str, str]] | None = None,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
    retriever: Callable[..., list[dict[str, Any]]] | None = None,
    llm_client: DoubaoClient | None = None,
) -> dict[str, Any]:
    """Run the non-streaming RAG pipeline.

    流程保持简单：用户问题 -> 向量检索 -> 构造带来源的 prompt -> 豆包生成。
    `retriever` 和 `llm_client` 可注入，方便不依赖真实 API 的本地验证。
    """

    if not query.strip():
        raise ValueError("query must not be empty")

    retrieve_func = retriever or default_retrieve
    retrieved_chunks = retrieve_func(query, top_k=top_k, filters=filters)
    messages = build_rag_messages(query, retrieved_chunks, history)
    client = llm_client or DoubaoClient()
    reply = client.chat(messages)
    product_ids = extract_product_ids(reply)
    return {
        "reply": reply,
        "product_ids": product_ids,
    }


def extract_product_ids(reply: str) -> list[str]:
    """Extract product markers like [[PRODUCT:p_digital_001]] in output order."""

    product_ids: list[str] = []
    seen: set[str] = set()
    for marker_body in PRODUCT_MARK_RE.findall(reply):
        for product_id in _split_marker_product_ids(marker_body):
            if product_id not in seen:
                seen.add(product_id)
                product_ids.append(product_id)
    return product_ids


def extract_compare_product_ids(reply: str) -> list[list[str]]:
    """Extract compare markers like [[COMPARE:p_001,p_002]] in output order."""

    groups: list[list[str]] = []
    for marker_body in COMPARE_MARK_RE.findall(reply):
        product_ids = _split_marker_product_ids(marker_body)
        if product_ids:
            groups.append(product_ids)
    return groups


def _split_marker_product_ids(marker_body: str) -> list[str]:
    return [
        item.strip()
        for item in marker_body.split(",")
        if item.strip()
    ]


def extract_source_blocks(reply: str) -> list[dict[str, str]]:
    """Extract source blocks like [[SOURCE:review|real user feedback]]."""

    return [
        {"source_type": source_type, "text": text.strip()}
        for source_type, text in SOURCE_MARK_RE.findall(reply)
        if text.strip()
    ]


def unique_retrieved_product_ids(chunks: list[dict[str, Any]]) -> list[str]:
    product_ids: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        product_id = str(chunk.get("metadata", {}).get("product_id", ""))
        if product_id and product_id not in seen:
            seen.add(product_id)
            product_ids.append(product_id)
    return product_ids
