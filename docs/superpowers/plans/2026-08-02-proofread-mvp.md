# Proofread MVP 구현 계획

> **에이전트 작업자용:** 이 계획을 작업 단위로 구현할 때는 `superpowers:subagent-driven-development`(권장) 또는 `superpowers:executing-plans` 하위 스킬을 반드시 사용합니다. 단계는 체크박스(`- [ ]`)로 관리합니다.

**목표:** 공개 GitHub 저장소를 데이터 엔지니어 포트폴리오 관점에서 근거 기반으로 평가하는 비동기 API를 구축한다.

**아키텍처:** FastAPI는 요청과 조회만 처리한다. Dramatiq worker가 GitHub 공개 메타데이터를 수집하고 `RepositoryProfile`로 정규화한다. 순수 함수 평가기는 `AnalysisReport`를 만들며 PostgreSQL에 작업·스냅샷·리포트를 저장한다.

**기술 스택:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL, Redis, Dramatiq, httpx, pytest, respx, Docker Compose, OpenTelemetry.

## 공통 제약

- 공개 저장소와 `data_engineer` 루브릭만 지원한다.
- 점수와 finding은 규칙 기반 신호에서만 생성한다.
- LLM은 evidence 기반 문안만 만들며 점수와 finding을 변경하지 않는다.
- 키와 민감한 요청 본문을 저장·로그 기록하지 않는다.

---

### 작업 1: 서비스 골격

**파일:** 생성 `pyproject.toml`, `src/proofread/api/app.py`, `tests/api/test_health.py`, `Dockerfile`, `compose.yaml`, `.env.example`, `README.md`.

**인터페이스:** `create_app() -> FastAPI`; `GET /healthz`는 `{"status": "ok"}`를 반환한다.

- [ ] `TestClient(create_app()).get("/healthz")`로 `test_healthz_returns_ok`를 작성하고, HTTP 200과 `{"status":"ok"}`을 검증한다.
- [ ] `uv run pytest tests/api/test_health.py::test_healthz_returns_ok -v`를 실행해 import 실패를 확인한다.
- [ ] `create_app`과 health route를 구현하고 Compose에 의존성과 PostgreSQL/Redis 서비스를 구성한다.
- [ ] 같은 테스트를 실행해 PASS를 확인한다.
- [ ] `chore: bootstrap Proofread service`로 커밋한다.

### 작업 2: 도메인 모델과 규칙 평가기

**파일:** 생성 `src/proofread/domain/models.py`, `src/proofread/domain/evaluator.py`, `tests/domain/test_evaluator.py`.

**인터페이스:** `evaluate(profile: RepositoryProfile) -> AnalysisReport`; 모델 `RepositoryProfile`, `Finding`, `AnalysisReport`.

- [ ] `tests/test_pipeline.py`와 `.github/workflows/ci.yml`는 있지만 README 테스트 섹션은 없는 프로필을 작성하고, 높은 우선순위 finding이 두 경로를 evidence로 포함하는지 검증한다.
- [ ] `uv run pytest tests/domain/test_evaluator.py -v`를 실행해 모듈 없음 실패를 확인한다.
- [ ] pipeline, reproducibility, quality, operability, results 신호에 대한 0~20점 다섯 개와 근거 연결 finding을 구현한다.
- [ ] 빈 프로필과 문서화된 테스트 경계 테스트를 추가한다.
- [ ] 평가기 테스트를 실행해 PASS를 확인한다.
- [ ] `feat: add evidence-based repository evaluator`로 커밋한다.

### 작업 3: GitHub 공개 메타데이터 수집

**파일:** 생성 `src/proofread/github/client.py`, `src/proofread/github/collector.py`, `tests/github/fixtures/repository.json`, `tests/github/fixtures/tree.json`, `tests/github/test_collector.py`.

**인터페이스:** `collect_public_repository(repository_url: str) -> RepositoryProfile`; 타입이 지정된 `RepositoryNotFound`, 재시도 가능한 `RateLimited` 오류.

- [ ] 저장소 메타데이터와 재귀 트리 응답을 위한 respx 테스트를 작성하고, `tests/test_pipeline.py`가 `profile.paths`에 포함되는지 검증한다.
- [ ] `uv run pytest tests/github/test_collector.py -v`를 실행해 모듈 없음 실패를 확인한다.
- [ ] `https://github.com/{owner}/{repository}`만 검증하고 httpx로 메타데이터와 기본 브랜치 트리를 가져오며, 토큰 내용 없이 HTTP 오류를 타입 오류로 변환한다.
- [ ] 유효하지 않은 URL, 404, 403/rate-limit 테스트를 추가한다.
- [ ] 수집기 테스트를 실행해 PASS를 확인한다.
- [ ] `feat: collect public GitHub repository evidence`로 커밋한다.

### 작업 4: 분석 작업과 worker

**파일:** 생성 `src/proofread/persistence/database.py`, `src/proofread/persistence/models.py`, `src/proofread/services/analysis.py`, `src/proofread/worker.py`, `tests/services/test_analysis.py`.

**인터페이스:** `create_analysis(repository_url: str) -> UUID`; `run_analysis(analysis_id: UUID) -> None`; 상태 `queued -> running -> completed | failed`.

- [ ] 가짜 repository/collector 수명 주기 테스트를 작성하고 완료된 리포트가 저장되는지 검증한다.
- [ ] `uv run pytest tests/services/test_analysis.py -v`를 실행해 모듈 없음 실패를 확인한다.
- [ ] URL, 상태, snapshot JSON, report JSON, error code, timestamp를 갖는 SQLAlchemy 분석 행을 추가하고 Dramatiq로 `run_analysis`를 enqueue한다.
- [ ] 영구 실패와 재시도 가능한 rate-limit 실패 테스트를 추가한다.
- [ ] 서비스 테스트를 실행해 PASS를 확인한다.
- [ ] `feat: add asynchronous analysis lifecycle`로 커밋한다.

### 작업 5: HTTP 분석 API

**파일:** 생성 `src/proofread/api/routes/analyses.py`, `tests/api/test_analyses.py`; 수정 `src/proofread/api/app.py`.

**인터페이스:** `POST /v1/analyses`; `GET /v1/analyses/{analysis_id}`.

- [ ] 공개 URL과 `data_engineer`가 담긴 POST 테스트를 작성하고 202와 `queued` 상태를 검증한다.
- [ ] `uv run pytest tests/api/test_analyses.py -v`를 실행해 route 없음 실패를 확인한다.
- [ ] Pydantic 요청/응답 모델, 의존성 주입 분석 서비스, 422 검증, 404 조회, 완료 리포트 응답을 구현한다.
- [ ] 유효하지 않은 URL, 지원하지 않는 직무, 알 수 없는 ID, evidence 배열 테스트를 추가한다.
- [ ] API 테스트를 실행해 PASS를 확인한다.
- [ ] `feat: expose analysis API`로 커밋한다.

### 작업 6: LLM 문안 보강과 출시 준비

**파일:** 생성 `src/proofread/llm/narrator.py`, `src/proofread/observability.py`, `tests/llm/test_narrator.py`, `.github/workflows/ci.yml`; 수정 `src/proofread/services/analysis.py`, `README.md`, `compose.yaml`.

**인터페이스:** `narrate(report: AnalysisReport) -> list[str]`; `configure_observability(app: FastAPI) -> None`.

- [ ] 가짜 LLM 테스트를 작성해 입력이 기존 finding ID와 evidence만으로 구성되는지 확인하고, 유효하지 않은 LLM 응답은 제거되는지 검증한다.
- [ ] `uv run pytest tests/llm/test_narrator.py -v`를 실행해 모듈 없음 실패를 확인한다.
- [ ] Pydantic 검증 문안 생성과 키 없음·클라이언트 오류 시 빈 narrative fallback을 구현하며, URL 라벨 없는 집계 메트릭만 기록한다.
- [ ] 설정, 개인정보 보호 범위, 아키텍처, 기여 흐름, Docker Compose smoke test를 문서화하고 `uv run pytest`, `uv run ruff check .` CI를 추가한다.
- [ ] `uv run pytest && uv run ruff check . && docker compose config`를 실행해 성공을 확인한다.
- [ ] `docs: prepare public MVP release`로 커밋한다.

## 계획 자체 검토

작업 2~3은 근거 기반 점수화와 GitHub 수집을, 작업 4는 영속적인 비동기 작업을, 작업 5는 두 API 계약을, 작업 6은 선택적 LLM·관측성·CI·공개 문서를 다룬다. `RepositoryProfile`은 수집기에서 평가기로 흐르고, `AnalysisReport`는 평가기에서 저장소를 거쳐 API와 narrator로 흐른다.
