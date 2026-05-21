from __future__ import annotations

import argparse
import sys
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app.rag.pipeline import chat


SAMPLE_QUERIES = [
    "推荐一款适合油皮的洗面奶",
    "200 元以下的耳机",
    "iPhone 续航好不好",
    "用户对小米手机评价怎么样",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test non-streaming RAG chat.")
    parser.add_argument("query", nargs="?", help="Query to test. Runs samples if omitted.")
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    queries = [args.query] if args.query else SAMPLE_QUERIES
    for query in queries:
        print("=" * 80)
        print(f"Query: {query}")
        result = chat(query, top_k=args.top_k)
        print(f"Product IDs: {result['product_ids']}")
        print(result["reply"])


if __name__ == "__main__":
    main()
