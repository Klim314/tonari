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

# Copy project and install
COPY . /app
RUN pip install --no-cache-dir --upgrade pip && \
    if [ "$INSTALL_DEV" = "true" ]; then \
        target=".[dev]"; \
    else \
        target="."; \
    fi && \
    if [ "$EDITABLE_INSTALL" = "true" ]; then \
        pip install --no-cache-dir -e "$target"; \
    else \
        pip install --no-cache-dir "$target"; \
    fi

EXPOSE 8087

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8087"]

