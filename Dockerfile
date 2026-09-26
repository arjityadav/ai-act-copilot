# syntax=docker/dockerfile:1.7
# Multi-stage build: dependencies are installed in a builder stage; the runtime image
# contains only the virtualenv and the app, runs as a non-root user, and has a health check.

FROM python:3.12-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.8.*
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project --extra cloud --extra mlops --extra ui
COPY app ./app
COPY prompts ./prompts
COPY migrations ./migrations
COPY data/obligations.yaml ./data/obligations.yaml

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH" APP_ENV=prod
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
