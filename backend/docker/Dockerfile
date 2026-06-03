# ─── Production Dockerfile ───────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY key_vault/ ./key_vault/

# Non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
