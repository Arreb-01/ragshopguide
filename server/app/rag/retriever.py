from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.llm.doubao_client import DoubaoClient


SERVER_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHROMA_PATH = Path(
    os.getenv("CHROMA_PERSIST_DIR", str(SERVER_ROOT / "data" / "chroma"))
)
COLLECTION_NAME = "ecommerce_products"


class ChromaRetriever:
    """Embed the user query, then retrieve matching source-aware chunks."""

    def __init__(
        self,
        persist_dir: str | Path = DEFAULT_CHROMA_PATH,
        collection_name: str = COLLECTION_NAME,
        llm_client: DoubaoClient | None = None,
    ) -> None:
        self.llm_client = llm_client or DoubaoClient()
        self.collection = _get_collection(persist_dir, collection_name)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        query_embedding = self.llm_client.embed(query)[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters,
            include=["documents", "metadatas", "distances"],
        )
        return _flatten_query_result(result)


def retrieve(
    query: str,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return ChromaRetriever().retrieve(query=query, top_k=top_k, filters=filters)


def _get_collection(persist_dir: str | Path, collection_name: str):
    try:
        import chromadb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency 'chromadb'. Install server dependencies with "
            "`pip install -r requirements.txt` from the server directory."
        ) from exc

    chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    return chroma_client.get_or_create_collection(name=collection_name)


def _flatten_query_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    ids = _first_result_list(result.get("ids"))
    documents = _first_result_list(result.get("documents"))
    metadatas = _first_result_list(result.get("metadatas"))
    distances = _first_result_list(result.get("distances"))

    rows: list[dict[str, Any]] = []
    for index, chunk_id in enumerate(ids):
        rows.append(
            {
                "id": chunk_id,
                "text": documents[index] if index < len(documents) else "",
                "metadata": metadatas[index] if index < len(metadatas) else {},
                "distance": distances[index] if index < len(distances) else None,
            }
        )
    return rows


def _first_result_list(value: Any) -> list[Any]:
    if not value:
        return []
    return value[0] if isinstance(value[0], list) else value
