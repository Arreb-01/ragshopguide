from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app.rag.retriever import retrieve


def build_filters(args: argparse.Namespace) -> dict[str, Any] | None:
    conditions: list[dict[str, Any]] = []
    if args.category:
        conditions.append({"category": args.category})
    if args.source_type:
        conditions.append({"source_type": args.source_type})
    if args.max_price is not None:
        conditions.append({"base_price": {"$lte": args.max_price}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def print_results(results: list[dict[str, Any]]) -> None:
    if not results:
        print("No results found.")
        return

    for rank, row in enumerate(results, start=1):
        metadata = row.get("metadata", {})
        distance = row.get("distance")
        distance_text = "n/a" if distance is None else f"{distance:.4f}"
        text = " ".join(str(row.get("text", "")).split())
        snippet = text[:180] + ("..." if len(text) > 180 else "")
        print(f"[{rank}] distance={distance_text}")
        print(
            "    "
            f"product_id={metadata.get('product_id', '')} "
            f"source_type={metadata.get('source_type', '')} "
            f"brand={metadata.get('brand', '')}"
        )
        print(f"    title={metadata.get('title', '')}")
        print(f"    text={snippet}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test ecommerce Chroma retrieval.")
    parser.add_argument("query", help="User query to retrieve relevant chunks for.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--category")
    parser.add_argument(
        "--source-type",
        choices=["basic", "marketing", "faq", "review"],
    )
    parser.add_argument("--max-price", type=float)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    filters = build_filters(args)
    results = retrieve(args.query, top_k=args.top_k, filters=filters)
    print_results(results)


if __name__ == "__main__":
    main()
