# Proofread MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 공개 GitHub 저장소를 데이터 엔지니어 포트폴리오 관점에서 근거 기반으로 평가하는 비동기 API를 구축한다.

**Architecture:** FastAPI는 요청과 조회만 처리한다. Dramatiq 워커가 GitHub 공개 메타데이터를 수집하고 `RepositoryProfile`로 정규화한다. 순수 함수 평가기는 `AnalysisReport`를 만들며 PostgreSQL에 작업·스냅샷·리포트를 저장한다.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL, Redis, Dramatiq, httpx, pytest, respx, Docker Compose, OpenTelemetry.

## Global Constraints

- 공개 저장소와 `data_engineer` 루브릭만 지원한다.
- 점수와 finding은 규칙 기반 신호에서만 생성한다.
- LLM은 evidence 기반 문안만 만들며 점수와 finding을 변경하지 않는다.
- 키와 민감한 요청 본문을 저장·로그 기록하지 않는다.

---

### Task 1: 서비스 골격

**Files:** Create `pyproject.toml`, `src/proofread/api/app.py`, `tests/api/test_health.py`, `Dockerfile`, `compose.yaml`, `.env.example`, `README.md`.

**Interfaces:** `create_app() -> FastAPI`; `GET /healthz` returns `{"status": "ok"}`.

- [ ] Write `test_healthz_returns_ok` with `TestClient(create_app()).get("/healthz")`; assert HTTP 200 and `{"status":"ok"}`.
- [ ] Run `uv run pytest tests/api/test_health.py::test_healthz_returns_ok -v`; expect import failure.
- [ ] Implement `create_app` and the health route; configure dependencies and PostgreSQL/Redis services in Compose.
- [ ] Run the same test; expect PASS.
- [ ] Commit `chore: bootstrap Proofread service`.

### Task 2: 도메인 모델과 규칙 평가기

**Files:** Create `src/proofread/domain/models.py`, `src/proofread/domain/evaluator.py`, `tests/domain/test_evaluator.py`.

**Interfaces:** `evaluate(profile: RepositoryProfile) -> AnalysisReport`; models `RepositoryProfile`, `Finding`, `AnalysisReport`.

- [ ] Write a test profile with `tests/test_pipeline.py` and `.github/workflows/ci.yml`, but no README test section; assert a high-priority finding contains both paths as evidence.
- [ ] Run `uv run pytest tests/domain/test_evaluator.py -v`; expect missing-module failure.
- [ ] Implement five 0–20 scores and evidence-bound findings for pipeline, reproducibility, quality, operability, and results signals.
- [ ] Add empty-profile and documented-test boundary tests.
- [ ] Run the evaluator tests; expect PASS.
- [ ] Commit `feat: add evidence-based repository evaluator`.

### Task 3: GitHub 공개 메타데이터 수집

**Files:** Create `src/proofread/github/client.py`, `src/proofread/github/collector.py`, `tests/github/fixtures/repository.json`, `tests/github/fixtures/tree.json`, `tests/github/test_collector.py`.

**Interfaces:** `collect_public_repository(repository_url: str) -> RepositoryProfile`; typed `RepositoryNotFound` and retryable `RateLimited` errors.

- [ ] Write a respx test for repository metadata and recursive tree responses; assert `tests/test_pipeline.py` is in `profile.paths`.
- [ ] Run `uv run pytest tests/github/test_collector.py -v`; expect missing-module failure.
- [ ] Validate only `https://github.com/{owner}/{repository}`, fetch metadata and default-branch tree with httpx, and map HTTP errors to typed errors without token contents.
- [ ] Add invalid URL, 404, and 403/rate-limit tests.
- [ ] Run collector tests; expect PASS.
- [ ] Commit `feat: collect public GitHub repository evidence`.

### Task 4: 분석 작업과 워커

**Files:** Create `src/proofread/persistence/database.py`, `src/proofread/persistence/models.py`, `src/proofread/services/analysis.py`, `src/proofread/worker.py`, `tests/services/test_analysis.py`.

**Interfaces:** `create_analysis(repository_url: str) -> UUID`; `run_analysis(analysis_id: UUID) -> None`; status `queued -> running -> completed | failed`.

- [ ] Write a fake repository/collector lifecycle test and assert a completed report is persisted.
- [ ] Run `uv run pytest tests/services/test_analysis.py -v`; expect missing-module failure.
- [ ] Add SQLAlchemy analysis rows with URL, status, snapshot JSON, report JSON, error code, and timestamps; enqueue `run_analysis` through Dramatiq.
- [ ] Add tests for permanent failure and retryable rate-limit failure.
- [ ] Run service tests; expect PASS.
- [ ] Commit `feat: add asynchronous analysis lifecycle`.

### Task 5: HTTP 분석 API

**Files:** Create `src/proofread/api/routes/analyses.py`, `tests/api/test_analyses.py`; modify `src/proofread/api/app.py`.

**Interfaces:** `POST /v1/analyses`; `GET /v1/analyses/{analysis_id}`.

- [ ] Write a POST test with a public URL and `data_engineer`; assert 202 and `queued` status.
- [ ] Run `uv run pytest tests/api/test_analyses.py -v`; expect route-not-found failure.
- [ ] Implement Pydantic request/response models, dependency-injected analysis service, 422 validation, 404 lookup, and completed report response.
- [ ] Add invalid URL, unsupported role, unknown ID, and evidence-array tests.
- [ ] Run API tests; expect PASS.
- [ ] Commit `feat: expose analysis API`.

### Task 6: LLM 문안 보강과 출시 준비

**Files:** Create `src/proofread/llm/narrator.py`, `src/proofread/observability.py`, `tests/llm/test_narrator.py`, `.github/workflows/ci.yml`; modify `src/proofread/services/analysis.py`, `README.md`, `compose.yaml`.

**Interfaces:** `narrate(report: AnalysisReport) -> list[str]`; `configure_observability(app: FastAPI) -> None`.

- [ ] Write a fake-LLM test asserting its input consists only of existing finding IDs and evidence, then assert invalid LLM responses are dropped.
- [ ] Run `uv run pytest tests/llm/test_narrator.py -v`; expect missing-module failure.
- [ ] Implement Pydantic-validated narration and empty-narrative fallback for absent key or client error; record only aggregate metrics without URL labels.
- [ ] Document setup, privacy scope, architecture, contribution flow, and a Docker Compose smoke test; add CI for `uv run pytest` and `uv run ruff check .`.
- [ ] Run `uv run pytest && uv run ruff check . && docker compose config`; expect success.
- [ ] Commit `docs: prepare public MVP release`.

## Plan Self-Review

Tasks 2–3 cover evidence-based scoring and GitHub collection; Task 4 covers durable asynchronous work; Task 5 covers both API contracts; Task 6 covers optional LLM, observability, CI, and public documentation. `RepositoryProfile` flows from collector to evaluator, while `AnalysisReport` flows from evaluator through persistence to API and narrator.
