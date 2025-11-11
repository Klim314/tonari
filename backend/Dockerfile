FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

ARG INSTALL_DEV=false
ARG EDITABLE_INSTALL=false

# System deps (optional: build dependencies if needed)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv once so we can use it for dependency management.
RUN pip install --no-cache-dir --upgrade pip uv

# Copy project and install
COPY . /app
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        target=".[dev]"; \
    else \
        target="."; \
    fi && \
    if [ "$EDITABLE_INSTALL" = "true" ]; then \
        uv pip install --system -e "$target"; \
    else \
        uv pip install --system "$target"; \
    fi

EXPOSE 8087

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8087"]

