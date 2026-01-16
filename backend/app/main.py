import json
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.db import init_db

app = FastAPI(title="tonari-backend", version="0.0.1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """
    Custom validation error handler that returns structured error information.
    Transforms Pydantic validation errors into a more user-friendly format.
    """
    errors = []
    for error in exc.errors():
        # Build the field name from the location tuple
        field_parts = []
        for part in error["loc"]:
            # Skip 'body' part, that's just the request body marker
            if part != "body":
                field_parts.append(str(part))

        field_name = ".".join(field_parts) if field_parts else "unknown"

        errors.append(
            {
                "field": field_name,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": errors})


class TranslationLogFormatter(logging.Formatter):
    """Custom formatter that includes extra fields for translation logging."""

    def format(self, record):
        # Get base formatted message
        base_msg = super().format(record)
        # Extract extra fields (anything not in the standard record attributes)
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "getMessage",
            "asctime",
        }
        extra_fields = {k: v for k, v in record.__dict__.items() if k not in standard_attrs}
        if extra_fields:
            extra_str = json.dumps(extra_fields)
            return f"{base_msg} | {extra_str}"
        return base_msg


@app.on_event("startup")
def on_startup() -> None:
    # Configure logging to show application logs with extra fields
    logging.basicConfig(level=logging.INFO)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(
            TranslationLogFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


from app.routers.chapter_translations import router as chapter_translations_router  # noqa: E402
from app.routers.ingest import router as ingest_router  # noqa: E402
from app.routers.models import router as models_router  # noqa: E402
from app.routers.prompts import router as prompts_router  # noqa: E402
from app.routers.works import router as works_router  # noqa: E402
from app.routers.lab import router as lab_router  # noqa: E402

app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(
    chapter_translations_router, prefix="/chapter-translations", tags=["chapter-translations"]
)
app.include_router(models_router, prefix="/models", tags=["models"])
app.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
app.include_router(works_router, prefix="/works", tags=["works"])
app.include_router(lab_router, prefix="/lab", tags=["lab"])
