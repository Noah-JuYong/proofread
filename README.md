# Proofread

Evidence-based GitHub portfolio analysis for data engineers. Every recommendation links to a
detected file or README section, rather than relying on a free-form model score.

Proofread evaluates data-flow evidence, reproducibility, quality, operability, and measurable
results. The MVP supports public repositories and the `data_engineer` role only. Scores and
findings are deterministic; an optional LLM adapter may only reword existing findings.

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

## API

```bash
curl -X POST http://127.0.0.1:8000/v1/analyses \
  -H 'content-type: application/json' \
  -d '{"repository_url":"https://github.com/owner/repository","target_role":"data_engineer"}'
```

Poll `GET /v1/analyses/{analysis_id}` for the queued, running, completed, or failed result. The
Compose worker processes jobs through Redis and PostgreSQL.

## Privacy and contributing

Proofread keeps public GitHub metadata only. It does not persist GitHub tokens, LLM keys, or LLM
request bodies, and it does not place repository URLs in metric labels. Before opening a pull
request, run `uv run pytest -v`, `uv run ruff check .`, and `docker compose config`.
