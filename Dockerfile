FROM ghcr.io/astral-sh/uv:0.7.3 AS uv
FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "proofread.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
