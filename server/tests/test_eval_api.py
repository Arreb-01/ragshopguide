from __future__ import annotations

from fastapi.testclient import TestClient

from app.evaluation.testset import EVAL_CASES
from app.main import app


client = TestClient(app)


def test_eval_testset_contains_25_prd_scenarios() -> None:
    scenario_counts: dict[str, int] = {}
    for case in EVAL_CASES:
        scenario_counts[case["type"]] = scenario_counts.get(case["type"], 0) + 1

    assert len(EVAL_CASES) == 25
    assert scenario_counts == {
        "single_recommendation": 5,
        "conditional_filter": 4,
        "multi_turn": 4,
        "exclusion": 4,
        "comparison": 3,
        "cross_category_scene": 3,
        "anti_hallucination": 2,
    }


def test_eval_run_returns_dry_run_report_without_external_llm_calls() -> None:
    response = client.post("/eval/run", json={"dry_run": True})

    assert response.status_code == 200
    report = response.json()
    assert report["mode"] == "dry_run"
    assert report["total_cases"] == 25
    assert report["metrics"] == {
        "retrieval_recall": None,
        "answer_accuracy": None,
        "hallucination_rate": None,
        "first_token_latency_ms": None,
        "total_latency_ms": None,
    }
    assert len(report["cases"]) == 25
    assert report["cases"][0]["status"] == "not_run"


def test_eval_run_returns_rule_checked_report_without_external_llm_calls() -> None:
    response = client.post("/eval/run", json={"dry_run": False})

    assert response.status_code == 200
    report = response.json()
    assert report["mode"] == "rule_check"
    assert report["total_cases"] == 25
    assert isinstance(report["metrics"]["retrieval_recall"], float)
    assert report["metrics"]["hallucination_rate"] == 0.0
    assert "rule_pass_rate" in report["metrics"]
    assert len(report["cases"]) == 25
    first_case = report["cases"][0]
    assert first_case["status"] in {"checked", "needs_review"}
    assert "query_plan" in first_case
    assert "retrieved_product_ids" in first_case
