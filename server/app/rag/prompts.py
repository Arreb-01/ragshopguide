from __future__ import annotations

from typing import Any


SOURCE_LABELS = {
    "basic": "商品基础信息",
    "marketing": "商家话术",
    "faq": "官方问答",
    "review": "用户评价",
}

MAX_CONTEXT_CHUNKS = 12
MAX_CONTEXT_TEXT_CHARS = 260
MAX_HISTORY_ITEMS = 6
MAX_HISTORY_CONTENT_CHARS = 500


SYSTEM_PROMPT = """你是一个基于 RAG 的电商智能导购助手。

你只能基于【检索上下文】里的商品回答，严禁编造库外商品、价格、优惠、库存或规格。
如果上下文不足以回答问题，要明确说明缺少信息，并给出基于现有上下文的谨慎建议。

引用商品信息时必须标明来源：
- 商家话术：适合解释卖点，但不能当作真实用户体验。
- 官方问答：适合解释参数、用法、规格、续航等官方信息。
- 用户评价：适合解释真实体验、缺点、口碑和是否值买。

回复格式：
1. 先用自然语言解释推荐理由或回答问题。
2. 涉及来源时必须使用来源标记，不要只写普通段落：
   - 官方/参数/FAQ 信息用 [[SOURCE:official|内容]]
   - 用户评价/真实体验用 [[SOURCE:review|内容]]
   - 商家卖点/营销描述用 [[SOURCE:marketing|内容]]
   - 综合建议用 [[SOURCE:summary|内容]]
3. 如推荐了商品，必须在回复末尾列出商品标记，格式为 [[PRODUCT:商品ID]]。
4. 如对比 2-3 款商品，必须在对比段落后列出标记，格式为 [[COMPARE:商品ID1,商品ID2]]。
5. 只允许输出检索上下文中出现过的商品 ID。
"""


def build_rag_messages(
    query: str,
    retrieved_chunks: list[dict[str, Any]],
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Build chat messages from retrieved chunks.

    这里把 prompt 单独集中，便于后续答辩解释和 Week 2 调整三源引用策略。
    """

    context = build_retrieval_context(retrieved_chunks)
    user_prompt = (
        "【用户问题】\n"
        f"{query}\n\n"
        "【检索上下文】\n"
        f"{context}\n\n"
        "请基于以上上下文回答。"
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(_normalize_history(history))
    messages.append({"role": "user", "content": user_prompt})
    return messages


def build_retrieval_context(retrieved_chunks: list[dict[str, Any]]) -> str:
    if not retrieved_chunks:
        return "未检索到相关商品。"

    lines: list[str] = []
    for index, chunk in enumerate(retrieved_chunks[:MAX_CONTEXT_CHUNKS], start=1):
        metadata = chunk.get("metadata", {})
        source_type = metadata.get("source_type", "")
        source_label = SOURCE_LABELS.get(source_type, source_type or "未知来源")
        distance = chunk.get("distance")
        distance_text = "" if distance is None else f"；距离={distance:.4f}"
        lines.append(
            "\n".join(
                [
                    f"[{index}] 来源={source_label}{distance_text}",
                    f"商品ID={metadata.get('product_id', '')}",
                    f"标题={metadata.get('title', '')}",
                    f"品牌={metadata.get('brand', '')}",
                    f"品类={metadata.get('category', '')}/{metadata.get('sub_category', '')}",
                    f"基础价={metadata.get('base_price', '')}",
                    f"内容={_truncate_text(str(chunk.get('text', '')), MAX_CONTEXT_TEXT_CHARS)}",
                ]
            )
        )
    return "\n\n".join(lines)


def _normalize_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep only OpenAI-compatible role/content pairs from client history."""

    normalized: list[dict[str, str]] = []
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            normalized.append(
                {
                    "role": role,
                    "content": _truncate_text(
                        str(content),
                        MAX_HISTORY_CONTENT_CHARS,
                    ),
                }
            )
    return normalized[-MAX_HISTORY_ITEMS:]


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."
