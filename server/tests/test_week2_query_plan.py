from __future__ import annotations

from app.rag.pipeline import extract_compare_product_ids, extract_source_blocks
from app.rag.pipeline import extract_product_ids
from app.rag.prompts import build_rag_messages
from app.rag.query_plan import (
    QueryPlan,
    apply_query_plan_filters,
    build_query_plan,
    build_retrieval_queries,
    source_counts,
)


def test_query_plan_extracts_price_limits() -> None:
    assert build_query_plan("300 元以下的真无线耳机有哪些").max_price == 300
    assert build_query_plan("预算 500 以内的跑鞋").max_price == 500
    assert build_query_plan("不要 Nike，预算压到 1000").max_price == 1000


def test_query_plan_extracts_exclusion_constraints() -> None:
    plan = build_query_plan("推荐防晒霜，但我不要日系品牌，也不要含酒精的")

    assert plan.intent == "exclusion"
    assert {"安热沙", "资生堂", "珊珂", "芳珂", "SK-II"}.issubset(
        set(plan.excluded_brands)
    )
    assert "酒精" in plan.excluded_keywords


def test_query_plan_accumulates_multi_turn_constraints() -> None:
    plan = build_query_plan(
        "预算 500 以内",
        history=[
            {"role": "user", "content": "推荐跑鞋"},
            {"role": "assistant", "content": "可以，日常跑量多少？"},
            {"role": "user", "content": "每周 20 公里左右，要轻便"},
        ],
    )

    assert plan.intent == "conditional_filter"
    assert plan.max_price == 500
    assert "跑鞋" in plan.required_keywords
    assert "轻便" in plan.required_keywords


def test_query_plan_identifies_comparison_products() -> None:
    plan = build_query_plan("iPhone 17 Pro 和华为 Pura 90 对比一下")

    assert plan.intent == "comparison"
    assert plan.compare_product_ids == ["p_digital_001", "p_digital_002"]


def test_single_product_source_query_is_not_classified_as_comparison() -> None:
    plan = build_query_plan("iPhone 17 Pro 续航好不好")

    assert plan.intent == "source_query"
    assert plan.compare_product_ids == ["p_digital_001"]


def test_explicit_product_query_does_not_inherit_previous_scene_constraints() -> None:
    history = [
        {"role": "user", "content": "健身入门装备怎么配"},
        {"role": "user", "content": "不要 Nike，预算压到 1000"},
    ]

    plan = build_query_plan("iPhone 17 Pro 续航好不好", history=history)

    assert plan.intent == "source_query"
    assert plan.max_price is None
    assert plan.excluded_brands == []
    assert plan.scene_key is None
    assert plan.required_keywords == []
    assert plan.compare_product_ids == ["p_digital_001"]


def test_product_follow_up_can_inherit_previous_product_context() -> None:
    plan = build_query_plan(
        "那续航好不好",
        history=[
            {"role": "user", "content": "iPhone 17 Pro 值不值得买"},
        ],
    )

    assert plan.intent == "source_query"
    assert plan.compare_product_ids == ["p_digital_001"]


def test_explicit_comparison_query_does_not_inherit_previous_scene_constraints() -> None:
    history = [
        {"role": "user", "content": "健身入门装备怎么配"},
        {"role": "user", "content": "不要 Nike，预算压到 1000"},
    ]

    plan = build_query_plan("iPhone 17 Pro 和华为 Pura 90 对比一下", history=history)

    assert plan.intent == "comparison"
    assert plan.max_price is None
    assert plan.excluded_brands == []
    assert plan.scene_key is None
    assert plan.compare_product_ids == ["p_digital_001", "p_digital_002"]


def test_query_plan_identifies_fitness_scene() -> None:
    plan = build_query_plan("我刚办了健身卡，准备开始撸铁，帮我配一套入门装备")

    assert plan.intent == "cross_category_scene"
    assert plan.scene_key == "fitness_entry"
    assert {"速干", "跑鞋", "功能饮料"}.issubset(set(plan.required_keywords))


def test_retrieval_query_uses_accumulated_multi_turn_keywords() -> None:
    plan = build_query_plan(
        "预算 500 以内",
        history=[
            {"role": "user", "content": "推荐跑鞋"},
            {"role": "user", "content": "要轻便"},
        ],
    )

    assert build_retrieval_queries("预算 500 以内", plan) == [
        "预算 500 以内 跑鞋 轻便"
    ]


def test_apply_query_plan_filters_removes_excluded_brand_and_price() -> None:
    chunks = [
        {
            "id": "nike",
            "text": "Nike 跑鞋",
            "metadata": {
                "product_id": "p_clothes_007",
                "brand": "Nike",
                "base_price": 899.0,
                "source_type": "basic",
            },
        },
        {
            "id": "anta",
            "text": "安踏 跑鞋 轻便",
            "metadata": {
                "product_id": "p_clothes_008",
                "brand": "安踏",
                "base_price": 399.0,
                "source_type": "basic",
            },
        },
        {
            "id": "hoka",
            "text": "HOKA 跑鞋",
            "metadata": {
                "product_id": "p_clothes_009",
                "brand": "HOKA",
                "base_price": 1099.0,
                "source_type": "basic",
            },
        },
    ]
    plan = QueryPlan(max_price=500, excluded_brands=["Nike", "耐克"])

    filtered = apply_query_plan_filters(chunks, plan)

    assert [chunk["id"] for chunk in filtered] == ["anta"]


def test_source_counts_groups_official_reviews_and_marketing() -> None:
    counts = source_counts(
        [
            {"metadata": {"source_type": "faq"}},
            {"metadata": {"source_type": "basic"}},
            {"metadata": {"source_type": "review"}},
            {"metadata": {"source_type": "marketing"}},
        ]
    )

    assert counts == {"official": 2, "review": 1, "marketing": 1}


def test_source_and_compare_markers_are_extracted() -> None:
    reply = (
        "[[SOURCE:official|官方标称续航 1 天]]"
        "[[SOURCE:review|用户反馈重度使用需补电]]"
        "[[COMPARE:p_digital_001,p_digital_002]]"
    )

    assert extract_source_blocks(reply) == [
        {"source_type": "official", "text": "官方标称续航 1 天"},
        {"source_type": "review", "text": "用户反馈重度使用需补电"},
    ]
    assert extract_compare_product_ids(reply) == [["p_digital_001", "p_digital_002"]]


def test_product_marker_accepts_comma_separated_ids() -> None:
    reply = "[[PRODUCT:p_clothes_020,p_clothes_002,p_food_005]]"

    assert extract_product_ids(reply) == [
        "p_clothes_020",
        "p_clothes_002",
        "p_food_005",
    ]


def test_prompt_documents_source_marker_protocol() -> None:
    messages = build_rag_messages("iPhone 17 Pro 续航好不好", [])

    system_prompt = messages[0]["content"]
    assert "[[SOURCE:official|内容]]" in system_prompt
    assert "[[SOURCE:review|内容]]" in system_prompt
    assert "[[SOURCE:marketing|内容]]" in system_prompt
    assert "[[SOURCE:summary|内容]]" in system_prompt
