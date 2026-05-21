from __future__ import annotations

from typing import Any


EVAL_CASES: list[dict[str, Any]] = [
    {
        "id": "single_001",
        "type": "single_recommendation",
        "query": "推荐一款适合油皮的洗面奶",
    },
    {
        "id": "single_002",
        "type": "single_recommendation",
        "query": "敏感肌适合用什么面霜",
    },
    {
        "id": "single_003",
        "type": "single_recommendation",
        "query": "推荐一款通勤用的轻薄笔记本",
    },
    {
        "id": "single_004",
        "type": "single_recommendation",
        "query": "有什么适合夏天用的防晒霜",
    },
    {
        "id": "single_005",
        "type": "single_recommendation",
        "query": "想买一双日常慢跑鞋",
    },
    {
        "id": "filter_001",
        "type": "conditional_filter",
        "query": "300 元以下的真无线耳机有哪些",
    },
    {
        "id": "filter_002",
        "type": "conditional_filter",
        "query": "500 元以内的跑鞋推荐",
    },
    {
        "id": "filter_003",
        "type": "conditional_filter",
        "query": "200 元以下适合办公室喝的咖啡",
    },
    {
        "id": "filter_004",
        "type": "conditional_filter",
        "query": "1000 元以内的入门健身装备",
    },
    {
        "id": "multi_001",
        "type": "multi_turn",
        "turns": ["推荐跑鞋", "每周 20 公里左右，要轻便", "预算 500 以内"],
    },
    {
        "id": "multi_002",
        "type": "multi_turn",
        "turns": ["想买手机", "主要拍照和续航", "不要太贵"],
    },
    {
        "id": "multi_003",
        "type": "multi_turn",
        "turns": ["推荐洁面", "我是油皮", "最好 200 元以内"],
    },
    {
        "id": "multi_004",
        "type": "multi_turn",
        "turns": ["我要买耳机", "运动时用", "预算 300"],
    },
    {
        "id": "exclude_001",
        "type": "exclusion",
        "query": "推荐防晒霜，但我不要日系品牌，也不要含酒精的",
    },
    {
        "id": "exclude_002",
        "type": "exclusion",
        "query": "推荐手机，不要苹果",
    },
    {
        "id": "exclude_003",
        "type": "exclusion",
        "query": "推荐跑鞋，不要 Nike",
    },
    {
        "id": "exclude_004",
        "type": "exclusion",
        "query": "给我推荐饮料，但不要含糖太高的",
    },
    {
        "id": "compare_001",
        "type": "comparison",
        "query": "iPhone 17 Pro 和华为 Pura 90 对比一下",
    },
    {
        "id": "compare_002",
        "type": "comparison",
        "query": "这两款真无线耳机帮我对比一下",
    },
    {
        "id": "compare_003",
        "type": "comparison",
        "query": "两双入门跑鞋哪个更适合新手",
    },
    {
        "id": "scene_001",
        "type": "cross_category_scene",
        "query": "我刚办了健身卡，准备开始撸铁，帮我配一套入门装备",
    },
    {
        "id": "scene_002",
        "type": "cross_category_scene",
        "query": "下周去三亚度假，帮我列一套防晒和出行清单",
    },
    {
        "id": "scene_003",
        "type": "cross_category_scene",
        "query": "我想开始晨跑，鞋服和补给怎么配",
    },
    {
        "id": "hallucination_001",
        "type": "anti_hallucination",
        "query": "你们有没有特斯拉手机",
    },
    {
        "id": "hallucination_002",
        "type": "anti_hallucination",
        "query": "帮我推荐一台 199 元的 MacBook",
    },
]
