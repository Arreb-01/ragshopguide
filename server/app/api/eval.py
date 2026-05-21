from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.evaluation.runner import run_rule_evaluation
from app.evaluation.testset import EVAL_CASES


router = APIRouter(prefix="/eval", tags=["evaluation"])


class EvalRunRequest(BaseModel):
    dry_run: bool = True


@router.post("/run")
def eval_run_endpoint(request: EvalRunRequest) -> dict[str, Any]:
    """Return the fixed PRD evaluation set and metric shape for demo tracking."""

    if not request.dry_run:
        return run_rule_evaluation()

    mode = "dry_run"
    return {
        "mode": mode,
        "total_cases": len(EVAL_CASES),
        "metrics": {
            "retrieval_recall": None,
            "answer_accuracy": None,
            "hallucination_rate": None,
            "first_token_latency_ms": None,
            "total_latency_ms": None,
        },
        "cases": [
            {
                "id": case["id"],
                "type": case["type"],
                "query": case.get("query") or " / ".join(case.get("turns", [])),
                "status": "not_run",
            }
            for case in EVAL_CASES
        ],
    }
