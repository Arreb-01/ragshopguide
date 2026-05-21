from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi.testclient import TestClient

from app.api.chat import ChatRequest, _stream_chat
from app.main import app


client = TestClient(app)


def _parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in body.strip().split("\n\n"):
        event_name = ""
        data: dict[str, object] = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            if line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        if event_name:
            events.append({"event": event_name, "data": data})
    return events


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_products_endpoint_returns_card_metadata_for_all_products() -> None:
    response = client.get("/products")

    assert response.status_code == 200
    products = response.json()["products"]
    assert len(products) == 100
    first = products[0]
    assert set(first) == {
        "product_id",
        "title",
        "brand",
        "category",
        "sub_category",
        "base_price",
        "image_path",
        "image_url",
        "tags",
    }
    assert first["image_url"].startswith("/static/images/")
    assert first["tags"]


def test_static_image_endpoint_serves_dataset_image() -> None:
    products = client.get("/products").json()["products"]
    image_url = products[0]["image_url"]

    response = client.get(image_url)

    assert response.status_code == 200
    assert response.headers["content-type"] in {"image/jpeg", "image/jpg"}
    assert response.content.startswith(b"\xff\xd8")


def test_chat_empty_query_returns_sse_error_event() -> None:
    response = client.post("/chat", json={"query": "   ", "session_id": "s1"})

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert events == [
        {
            "event": "error",
            "data": {"message": "query must not be empty"},
        }
    ]


def test_stream_chat_supports_injected_retriever_and_llm_client() -> None:
    def fake_retrieve(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        assert query == "推荐油皮洗面奶"
        assert top_k == 5
        assert filters is None
        return [
            {
                "id": "p_beauty_001:basic",
                "text": "适合油皮的洁面",
                "metadata": {
                    "product_id": "p_beauty_001",
                    "source_type": "basic",
                    "title": "控油洁面",
                },
                "distance": 0.1,
            }
        ]

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            assert stream is True
            assert "推荐油皮洗面奶" in messages[-1]["content"]
            return [
                {"choices": [{"delta": {"content": "推荐控油洁面"}}]},
                {"choices": [{"delta": {"content": " [[PRODUCT:p_beauty_001]]"}}]},
            ]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="推荐油皮洗面奶", session_id="s1"),
                retrieve_func=fake_retrieve,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    assert events[0]["event"] == "meta"
    assert events[0]["data"]["session_id"] == "s1"
    assert events[0]["data"]["retrieved_product_ids"] == ["p_beauty_001"]
    assert events[0]["data"]["query_plan"] == {
        "intent": "recommendation",
        "max_price": None,
        "excluded_brands": [],
        "excluded_keywords": [],
        "required_keywords": [],
        "compare_product_ids": [],
        "scene_key": None,
    }
    assert events[0]["data"]["source_counts"] == {"official": 1}
    assert events[0]["data"]["timings_ms"]["retrieval"] >= 0
    token_text = "".join(
        str(event["data"].get("token", ""))
        for event in events
        if event["event"] == "token"
    )
    assert "推荐控油洁面 [[PRODUCT:p_beauty_001]]" in token_text
    assert "[[SOURCE:official|" in token_text
    assert events[-1]["event"] == "done"
    assert events[-1]["data"]["product_ids"] == ["p_beauty_001"]
    assert events[-1]["data"]["retrieved_product_ids"] == ["p_beauty_001"]
    assert events[-1]["data"]["compare_product_groups"] == []
    assert events[-1]["data"]["timings_ms"]["total"] >= 0


def test_stream_chat_exposes_query_plan_and_compare_groups() -> None:
    def fake_retrieve(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "p_digital_001:basic",
                "text": "iPhone 官方基础信息",
                "metadata": {
                    "product_id": "p_digital_001",
                    "source_type": "basic",
                    "title": "Apple iPhone 17 Pro",
                    "brand": "Apple 苹果",
                    "base_price": 8999.0,
                },
            },
            {
                "id": "p_digital_002:review:1",
                "text": "华为用户评价",
                "metadata": {
                    "product_id": "p_digital_002",
                    "source_type": "review",
                    "title": "华为 Pura 90 Pro",
                    "brand": "华为",
                    "base_price": 6999.0,
                },
            },
        ]

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            return [
                {
                    "choices": [
                        {
                            "delta": {
                                "content": (
                                    "[[SOURCE:official|官方基础信息]]"
                                    "[[COMPARE:p_digital_001,p_digital_002]]"
                                )
                            }
                        }
                    ]
                }
            ]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="iPhone 17 Pro 和华为 Pura 90 对比一下"),
                retrieve_func=fake_retrieve,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    assert events[0]["event"] == "meta"
    assert events[0]["data"]["query_plan"]["intent"] == "comparison"
    assert events[0]["data"]["query_plan"]["compare_product_ids"] == [
        "p_digital_001",
        "p_digital_002",
    ]
    assert events[0]["data"]["source_counts"]["official"] >= 1
    assert events[0]["data"]["source_counts"]["review"] >= 1
    assert events[-1]["event"] == "done"
    assert events[-1]["data"]["compare_product_groups"] == [
        ["p_digital_001", "p_digital_002"]
    ]


def test_stream_chat_emits_non_breaking_timing_metrics() -> None:
    def fake_retrieve(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "p_beauty_001:basic",
                "text": "商品信息",
                "metadata": {
                    "product_id": "p_beauty_001",
                    "source_type": "basic",
                },
            }
        ]

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            return [{"choices": [{"delta": {"content": "推荐它"}}]}]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="推荐油皮洗面奶"),
                retrieve_func=fake_retrieve,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    meta_timings = events[0]["data"]["timings_ms"]
    done_timings = events[-1]["data"]["timings_ms"]

    assert meta_timings["retrieval"] >= 0
    assert done_timings["first_token"] >= 0
    assert done_timings["total"] >= done_timings["first_token"]


def test_stream_chat_enriches_explicit_product_context_and_appends_missing_markers() -> None:
    def fake_retrieve(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return []

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            assert "p_digital_001" in messages[-1]["content"]
            return [
                {"choices": [{"delta": {"content": "iPhone 续航可以参考官方和用户评价。"}}]},
            ]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="iPhone 17 Pro 续航好不好"),
                retrieve_func=fake_retrieve,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    token_text = "".join(
        str(event["data"].get("token", ""))
        for event in events
        if event["event"] == "token"
    )
    assert events[0]["data"]["retrieved_product_ids"] == ["p_digital_001"]
    assert "[[PRODUCT:p_digital_001]]" in token_text


def test_stream_chat_uses_local_evidence_for_explicit_product_without_vector_retrieval() -> None:
    def fail_if_called(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        raise AssertionError("explicit product query should not call vector retrieval")

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            prompt = messages[-1]["content"]
            assert "p_digital_001" in prompt
            assert "商家营销描述" in prompt
            assert "官方问答" in prompt
            assert "用户评价" in prompt
            return [{"choices": [{"delta": {"content": "续航适合一天正常使用。"}}]}]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="iPhone 17 Pro 续航好不好"),
                retrieve_func=fail_if_called,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    assert events[0]["data"]["retrieved_product_ids"] == ["p_digital_001"]
    assert events[0]["data"]["source_counts"]["official"] >= 1
    assert events[0]["data"]["source_counts"]["review"] >= 1
    assert events[0]["data"]["source_counts"]["marketing"] >= 1


def test_stream_chat_uses_local_scene_evidence_for_fitness_without_vector_retrieval() -> None:
    def fail_if_called(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        raise AssertionError("fitness demo scene should not call vector retrieval")

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            prompt = messages[-1]["content"]
            assert "速干" in prompt
            assert "跑鞋" in prompt
            assert "功能饮料" in prompt
            assert "p_food_" in prompt
            assert "Nike" not in prompt
            assert "耐克" not in prompt
            return [{"choices": [{"delta": {"content": "按预算给你配一套。"}}]}]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(
                    query="不要 Nike，预算压到 1000",
                    history=[
                        {"role": "user", "content": "健身入门装备怎么配"},
                    ],
                ),
                retrieve_func=fail_if_called,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    product_ids = events[0]["data"]["retrieved_product_ids"]
    assert any(str(product_id).startswith("p_clothes_") for product_id in product_ids)
    assert any(str(product_id).startswith("p_food_") for product_id in product_ids)
    assert "p_clothes_003" not in product_ids


def test_stream_chat_appends_missing_cross_category_product_marker_for_fitness() -> None:
    def fail_if_called(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        raise AssertionError("fitness demo scene should not call vector retrieval")

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            return [
                {
                    "choices": [
                        {
                            "delta": {
                                "content": "先选速干衣和跑鞋。[[PRODUCT:p_clothes_020]]"
                            }
                        }
                    ]
                }
            ]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="健身入门装备怎么配"),
                retrieve_func=fail_if_called,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    token_text = "".join(
        str(event["data"].get("token", ""))
        for event in events
        if event["event"] == "token"
    )
    assert "[[PRODUCT:p_food_" in token_text
    assert any(
        str(product_id).startswith("p_food_")
        for product_id in events[-1]["data"]["product_ids"]
    )


def test_stream_chat_appends_missing_source_markers_from_retrieved_chunks() -> None:
    def fake_retrieve(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "official",
                "text": "官方参数",
                "metadata": {
                    "product_id": "p_digital_001",
                    "source_type": "basic",
                },
            },
            {
                "id": "review",
                "text": "用户评价",
                "metadata": {
                    "product_id": "p_digital_001",
                    "source_type": "review",
                },
            },
            {
                "id": "marketing",
                "text": "商家卖点",
                "metadata": {
                    "product_id": "p_digital_001",
                    "source_type": "marketing",
                },
            },
        ]

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            return [{"choices": [{"delta": {"content": "这款手机整体表现均衡。"}}]}]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="iPhone 17 Pro 续航好不好"),
                retrieve_func=fake_retrieve,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    token_text = "".join(
        str(event["data"].get("token", ""))
        for event in events
        if event["event"] == "token"
    )
    assert "[[SOURCE:official|" in token_text
    assert "[[SOURCE:review|" in token_text
    assert "[[SOURCE:marketing|" in token_text
    assert "[[SOURCE:summary|" in token_text


def test_stream_chat_appends_missing_compare_marker_for_comparison() -> None:
    def fake_retrieve(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return []

    class FakeLlmClient:
        def chat(
            self,
            messages: list[dict[str, str]],
            stream: bool,
        ) -> list[dict[str, Any]]:
            assert "p_digital_001" in messages[-1]["content"]
            assert "p_digital_002" in messages[-1]["content"]
            return [{"choices": [{"delta": {"content": "两款手机各有取向。"}}]}]

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="iPhone 17 Pro 和华为 Pura 90 对比一下"),
                retrieve_func=fake_retrieve,
                llm_client_factory=FakeLlmClient,
            )
        )
    )

    events = _parse_sse_events(body)
    token_text = "".join(
        str(event["data"].get("token", ""))
        for event in events
        if event["event"] == "token"
    )
    assert "[[COMPARE:p_digital_001,p_digital_002]]" in token_text
    assert events[-1]["data"]["compare_product_groups"] == [
        ["p_digital_001", "p_digital_002"]
    ]


def test_stream_chat_returns_error_event_when_dependency_fails() -> None:
    def fake_retrieve(
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        raise RuntimeError("retriever unavailable")

    body = asyncio.run(
        _collect_stream(
            _stream_chat(
                ChatRequest(query="推荐耳机"),
                retrieve_func=fake_retrieve,
            )
        )
    )

    assert _parse_sse_events(body) == [
        {
            "event": "error",
            "data": {"message": "retriever unavailable"},
        }
    ]


async def _collect_stream(stream: Any) -> str:
    return "".join([chunk async for chunk in stream])
