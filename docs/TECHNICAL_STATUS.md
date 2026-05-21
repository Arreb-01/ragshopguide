# Technical Status

## Implemented

- FastAPI app with `/health`, `/chat`, `/products`, `/eval/run`, and static dataset image serving.
- Source-aware product chunking: `basic`, `marketing`, `faq`, `review`.
- Chroma-backed retrieval with source metadata.
- RAG prompt assembly with anti-hallucination and source-label rules.
- Lightweight Week 2 `QueryPlan` for price limits, brand/keyword exclusions, comparison detection, multi-turn constraints, and the fitness-entry scene.
- Fast local retrieval paths for the Week 2 demo: fitness-entry bundles, iPhone 17 Pro source queries, and iPhone/Huawei comparison use local evidence instead of external embedding calls.
- SSE stream events: `meta`, `token`, `done`, `error`; `meta` now includes `query_plan`, `source_counts`, and `timings_ms.retrieval`, and `done` includes `compare_product_groups`, `timings_ms.first_token`, and `timings_ms.total`.
- Protocol fallback for real LLM variance: missing `SOURCE`, `PRODUCT`, or `COMPARE` markers are appended from retrieved evidence and query plan data.
- Fitness demo product fallback ensures at least top/shoe/drink cards are available for the Android carousel.
- Android Kotlin MVP with prompt tiles, chat stream rendering, product cards, source-marked answer blocks, structured comparison cards, and runtime backend URL switching.
- Backend automated tests for data loading, prompt construction, marker parsing, API smoke checks, injected chat dependencies, query planning, and evaluation fixtures.
- 2026-05-21 real Doubao demo validation passed the four Week 2 prompts in the demo path.
- 2026-05-22 real Doubao demo validation passed again; retrieval timing for the four demo turns was 53-192ms, with first token timing still dominated by Doubao generation at roughly 8-26s.

## Remaining Work

- Add Room persistence for multi-session history.
- Improve LLM generation latency for live demos; retrieval is now local-fast on the main demo path, but first token can still take 8-26s depending on Doubao response time.
- Replace `/eval/run` rule-check answer placeholders with real LLM answer-quality scoring.
- Add `POST /multimodal/analyze` after the P0 demo path is stable.

## Demo Path

1. Start backend on `0.0.0.0:8000`.
2. Launch Android app from `client-android`.
3. Tap `健身入门装备怎么配`.
4. Ask `不要 Nike，预算压到 1000`.
5. Ask `iPhone 17 Pro 续航好不好`.
6. Ask `iPhone 17 Pro 和华为 Pura 90 对比一下`.
