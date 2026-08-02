# Proofread

Evidence-based GitHub portfolio analysis for data engineers.

## Local development

```bash
cp .env.example .env
uv sync --group dev
uv run uvicorn proofread.api.app:create_app --factory --reload
```

Verify the running service with `GET http://127.0.0.1:8000/healthz`.

Start the local infrastructure with:

```bash
docker compose up --build
```

The first release will analyse public GitHub repositories only.
