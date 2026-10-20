# syntax=docker/dockerfile:1

# 1. Build the React app into static files.
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY frontend/ ./
RUN npm run build

# 2. Python image with the backend; it also serves the built frontend.
FROM python:3.14-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first, so code changes don't reinstall them.
COPY backend/pyproject.toml backend/uv.lock* backend/README.md ./
RUN if [ -f uv.lock ]; then uv sync --locked --no-dev --no-install-project; \
    else uv sync --no-dev --no-install-project; fi
COPY backend/ ./
RUN if [ -f uv.lock ]; then uv sync --locked --no-dev; else uv sync --no-dev; fi

COPY --from=frontend /src/dist /app/static
ENV PATH="/app/.venv/bin:${PATH}" \
    STATIC_DIR=/app/static

RUN useradd --system --uid 10001 shortly
USER shortly
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
CMD ["uvicorn", "shortly.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
