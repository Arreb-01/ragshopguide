from __future__ import annotations

from app.data.loader import load_chunks, load_products, summarize_chunks
from app.rag.pipeline import extract_compare_product_ids, extract_product_ids
from app.rag.prompts import build_rag_messages, build_retrieval_context


def test_dataset_loads_expected_products_and_source_chunks() -> None:
    products = load_products()
    chunks = load_chunks()
    summary = summarize_chunks(chunks)

    assert len(products) == 100
    assert summary == {
        "product_count": 100,
        "chunk_count": 1092,
        "source_counts": {
            "basic": 100,
            "faq": 439,
            "marketing": 100,
            "review": 453,
        },
    }


def test_extract_product_ids_preserves_order_and_removes_duplicates() -> None:
    reply = (
        "推荐先看 [[PRODUCT:p_digital_001]]，再看 "
        "[[PRODUCT:p_digital_002]]。重复的 [[PRODUCT:p_digital_001]] 不应再出现。"
    )

    assert extract_product_ids(reply) == ["p_digital_001", "p_digital_002"]


def test_extract_product_ids_returns_empty_list_when_no_markers() -> None:
    assert extract_product_ids("没有商品标记的回复") == []


def test_extract_compare_product_ids_returns_marker_groups() -> None:
    reply = (
        "对比 [[COMPARE:p_digital_001,p_digital_002]]，"
        "再看 [[COMPARE:p_beauty_001, p_beauty_002, p_beauty_003]]"
    )

    assert extract_compare_product_ids(reply) == [
        ["p_digital_001", "p_digital_002"],
        ["p_beauty_001", "p_beauty_002", "p_beauty_003"],
    ]


def test_build_retrieval_context_marks_source_and_product_fields() -> None:
    context = build_retrieval_context(
        [
            {
                "id": "p_digital_001:review:1",
                "text": "用户评价内容",
                "distance": 0.12,
                "metadata": {
                    "product_id": "p_digital_001",
                    "source_type": "review",
                    "title": "Apple iPhone 17 Pro",
                    "brand": "Apple 苹果",
                    "category": "数码电子",
                    "sub_category": "智能手机",
                    "base_price": 8999.0,
                },
            }
        ]
    )

    assert "来源=用户评价" in context
    assert "商品ID=p_digital_001" in context
    assert "Apple iPhone 17 Pro" in context
    assert "距离=0.1200" in context


def test_build_retrieval_context_caps_chunk_count_and_text_length() -> None:
    chunks = [
        {
            "id": f"p_demo_{index:03d}:basic",
            "text": "x" * 420,
            "metadata": {
                "product_id": f"p_demo_{index:03d}",
                "source_type": "basic",
                "title": f"测试商品 {index}",
                "brand": "Demo",
                "category": "测试",
                "sub_category": "测试",
                "base_price": 99.0,
            },
        }
        for index in range(14)
    ]

    context = build_retrieval_context(chunks)

    assert "商品ID=p_demo_011" in context
    assert "商品ID=p_demo_012" not in context
    assert ("x" * 260) in context
    assert ("x" * 261) not in context


def test_build_rag_messages_compacts_history_for_generation_prompt() -> None:
    history = [
        {"role": "user", "content": f"turn-{index}-" + "x" * 700}
        for index in range(8)
    ]

    messages = build_rag_messages("推荐耳机", [], history=history)
    history_messages = messages[1:-1]

    assert len(history_messages) == 6
    assert history_messages[0]["content"].startswith("turn-2-")
    assert len(history_messages[0]["content"]) <= 503
    assert history_messages[0]["content"].endswith("...")


def test_system_prompt_documents_product_and_compare_markers() -> None:
    messages = build_rag_messages("这两款手机对比一下", [])

    assert "[[PRODUCT:商品ID]]" in messages[0]["content"]
    assert "[[COMPARE:商品ID1,商品ID2]]" in messages[0]["content"]


def test_build_rag_messages_normalizes_history_and_handles_empty_context() -> None:
    messages = build_rag_messages(
        "推荐耳机",
        [],
        history=[
            {"role": "system", "content": "should be removed"},
            {"role": "user", "content": "预算 300"},
            {"role": "assistant", "content": "可以"},
            {"role": "assistant", "content": ""},
        ],
    )

    assert messages[0]["role"] == "system"
    assert messages[1:] == [
        {"role": "user", "content": "预算 300"},
        {"role": "assistant", "content": "可以"},
        {
            "role": "user",
            "content": "【用户问题】\n推荐耳机\n\n【检索上下文】\n未检索到相关商品。\n\n请基于以上上下文回答。",
        },
    ]
