from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib import error, request


class DoubaoConfigError(RuntimeError):
    """Raised when the Doubao client is missing required environment config."""


def _load_dotenv_if_available() -> None:
    """Load server/.env when python-dotenv is installed."""

    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return

    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path)


_load_dotenv_if_available()


class DoubaoClient:
    """Small wrapper for Doubao models exposed through Volcengine Ark.

    Ark exposes an OpenAI-compatible API surface, so the official OpenAI SDK can
    call Doubao chat and embedding endpoints by overriding the base_url.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        chat_model: str | None = None,
        embedding_model: str | None = None,
        embedding_api: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("ARK_API_KEY")
        if not self.api_key or self.api_key == "your_api_key_here":
            raise DoubaoConfigError(
                "Missing ARK_API_KEY. Copy server/.env.example to server/.env "
                "and set your Volcengine Ark API key."
            )

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise DoubaoConfigError(
                "Missing dependency 'openai'. Install server dependencies with "
                "`pip install -r server/requirements.txt`."
            ) from exc

        self.base_url = base_url or os.getenv(
            "ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/"
        )
        self.chat_model = chat_model or os.getenv(
            "ARK_CHAT_MODEL", "ep-20260521111129-t5sf5"
        )
        self.embedding_model = embedding_model or os.getenv(
            "ARK_EMBEDDING_MODEL", "doubao-embedding-vision-251215"
        )
        self.embedding_api = (
            embedding_api
            or os.getenv("ARK_EMBEDDING_API")
            or (
                "multimodal"
                if "embedding-vision" in self.embedding_model
                else "standard"
            )
        ).lower()
        self.timeout = timeout if timeout is not None else float(
            os.getenv("ARK_TIMEOUT_SECONDS", "30")
        )
        self.max_retries = max_retries if max_retries is not None else int(
            os.getenv("ARK_MAX_RETRIES", "3")
        )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        stream: bool = False,
        **kwargs: Any,
    ) -> str | Iterable[Any]:
        """Call the configured Doubao chat model.

        Non-streaming calls return the assistant text. Streaming calls return the
        SDK stream object so the API layer can forward token deltas as SSE later.
        """

        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=temperature,
            stream=stream,
            **kwargs,
        )

        if stream:
            return response

        content = response.choices[0].message.content
        return content or ""

    def embed(self, texts: str | list[str]) -> list[list[float]]:
        """Create embeddings for one string or a batch of strings."""

        input_texts = [texts] if isinstance(texts, str) else texts
        if not input_texts:
            return []

        if self.embedding_api == "multimodal":
            return [self._embed_multimodal_text(text) for text in input_texts]

        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=input_texts,
        )
        return [item.embedding for item in response.data]

    def _embed_multimodal_text(self, text: str) -> list[float]:
        """Call Ark's multimodal embedding endpoint with text-only input.

        Doubao vision embedding uses `/embeddings/multimodal` and returns one
        embedding for the provided multimodal input. For Chroma documents we call
        it once per text chunk so each chunk gets its own vector.
        """

        url = f"{self.base_url.rstrip('/')}/embeddings/multimodal"
        payload = {
            "model": self.embedding_model,
            "input": [{"type": "text", "text": text}],
        }
        req = request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        data = self._post_json_with_retry(req)

        embedding = data.get("data", {}).get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError(f"Unexpected Ark embedding response shape: {data}")
        return [float(value) for value in embedding]

    def _post_json_with_retry(self, req: request.Request) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504}:
                    body = exc.read().decode("utf-8", errors="replace")
                    raise RuntimeError(
                        "Ark multimodal embedding request failed: "
                        f"HTTP {exc.code} {body}"
                    ) from exc
                last_error = exc
            except error.URLError as exc:
                last_error = exc

            if attempt < self.max_retries:
                time.sleep(min(2**attempt, 8))

        raise RuntimeError(
            f"Ark multimodal embedding request failed after retries: {last_error}"
        )
