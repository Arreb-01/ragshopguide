from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.eval import router as eval_router
from app.api.products import router as products_router
from app.data.loader import DEFAULT_DATASET_ROOT


app = FastAPI(title="RAG 多模态电商智能导购 API")
app.include_router(chat_router)
app.include_router(products_router)
app.include_router(eval_router)
app.mount(
    "/static/images",
    StaticFiles(directory=str(DEFAULT_DATASET_ROOT)),
    name="product-images",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
