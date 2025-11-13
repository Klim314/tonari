from fastapi import FastAPI

from app.db import init_db

app = FastAPI(title="tonari-backend", version="0.0.1")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


from app.routers.chapter_translations import router as chapter_translations_router  # noqa: E402
from app.routers.ingest import router as ingest_router  # noqa: E402
from app.routers.prompts import router as prompts_router  # noqa: E402
from app.routers.works import router as works_router  # noqa: E402

app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(
    chapter_translations_router, prefix="/chapter-translations", tags=["chapter-translations"]
)
app.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
app.include_router(works_router, prefix="/works", tags=["works"])
