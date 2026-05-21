from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app.data.loader import load_chunks, summarize_chunks
from app.llm.doubao_client import DoubaoClient


COLLECTION_NAME = "ecommerce_products"
DEFAULT_CHROMA_PATH = Path(
    os.getenv("CHROMA_PERSIST_DIR", str(SERVER_ROOT / "data" / "chroma"))
)


def build_index(
    batch_size: int = 16,
    persist_dir: str | Path = DEFAULT_CHROMA_PATH,
    collection_name: str = COLLECTION_NAME,
    sleep_seconds: float = 0.0,
    reset_collection: bool = False,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    chunks = load_chunks()
    stats = summarize_chunks(chunks)
    client = DoubaoClient()
    chroma_client, collection = _get_client_and_collection(
        persist_dir, collection_name, reset_collection=reset_collection
    )

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        batch_ids = [chunk["id"] for chunk in batch]
        existing_ids = set(collection.get(ids=batch_ids, include=[])["ids"])
        missing_batch = [
            chunk for chunk in batch if chunk["id"] not in existing_ids
        ]
        if not missing_batch:
            print(
                f"Skipped {min(start + batch_size, len(chunks))}/{len(chunks)} chunks",
                flush=True,
            )
            continue

        texts = [chunk["text"] for chunk in missing_batch]
        embeddings = client.embed(texts)
        collection.upsert(
            ids=[chunk["id"] for chunk in missing_batch],
            documents=texts,
            metadatas=[chunk["metadata"] for chunk in missing_batch],
            embeddings=embeddings,
        )
        print(
            f"Indexed {min(start + batch_size, len(chunks))}/{len(chunks)} chunks",
            flush=True,
        )
        if sleep_seconds > 0 and start + batch_size < len(chunks):
            time.sleep(sleep_seconds)

    stats["collection_count"] = collection.count()
    stats["reload_count"] = verify_index_reload(persist_dir, collection_name)
    stats["persist_dir"] = str(Path(persist_dir).resolve())
    stats["collection_name"] = collection_name
    return stats


def _get_client_and_collection(
    persist_dir: str | Path,
    collection_name: str,
    reset_collection: bool = False,
):
    try:
        import chromadb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency 'chromadb'. Install server dependencies with "
            "`pip install -r requirements.txt` from the server directory."
        ) from exc

    chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    if reset_collection:
        try:
            chroma_client.delete_collection(name=collection_name)
            print(f"Deleted existing Chroma collection: {collection_name}")
        except Exception:
            print(f"No existing Chroma collection to delete: {collection_name}")
    collection = chroma_client.get_or_create_collection(name=collection_name)
    return chroma_client, collection


def verify_index_reload(
    persist_dir: str | Path,
    collection_name: str,
) -> int:
    """Open the persisted Chroma collection from disk and verify it can count."""

    import chromadb

    verify_client = chromadb.PersistentClient(path=str(persist_dir))
    verify_collection = verify_client.get_collection(name=collection_name)
    return verify_collection.count()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Chroma index for ecommerce RAG chunks."
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--persist-dir", default=str(DEFAULT_CHROMA_PATH))
    parser.add_argument("--collection-name", default=COLLECTION_NAME)
    parser.add_argument(
        "--reset-collection",
        action="store_true",
        help="Delete the existing Chroma collection before rebuilding it.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional pause between embedding batches to reduce rate-limit risk.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    stats = build_index(
        batch_size=args.batch_size,
        persist_dir=args.persist_dir,
        collection_name=args.collection_name,
        sleep_seconds=args.sleep_seconds,
        reset_collection=args.reset_collection,
    )

    print("Index build summary")
    print(f"Products: {stats['product_count']}")
    print(f"Chunks: {stats['chunk_count']}")
    for source_type, count in stats["source_counts"].items():
        print(f"- {source_type}: {count}")
    print(f"Chroma collection: {stats['collection_name']}")
    print(f"Chroma count: {stats['collection_count']}")
    print(f"Reload verification count: {stats['reload_count']}")
    print(f"Persist dir: {stats['persist_dir']}")


if __name__ == "__main__":
    main()
