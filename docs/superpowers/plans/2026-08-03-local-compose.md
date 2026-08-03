# 로컬 Compose 구현 계획

> **에이전트 작업자용:** 이 계획을 작업 단위로 구현할 때는 `superpowers:executing-plans` 하위 스킬을 반드시 사용합니다. 단계는 체크박스(`- [ ]`)로 관리합니다.

**목표:** `docker compose up --build`로 API와 worker가 이미 빌드된 의존성만 사용해 기동되고, 공개 저장소 분석까지 로컬에서 검증할 수 있게 한다.

**아키텍처:** Docker 이미지 빌드 단계는 이미 production 의존성을 동기화한다. API와 worker의 런타임 명령에 `uv run --no-sync`를 추가해 개발 의존성 설치를 막는다. 설정 파일을 읽는 작은 회귀 테스트와 README 실행 절차로 이 계약을 보존한다.

**기술 스택:** Docker, Docker Compose, uv, FastAPI, Dramatiq, pytest.

## 공통 제약

- 새 외부 서비스·클라우드 계정·의존성을 추가하지 않는다.
- Compose는 `.env.example`의 `postgres`, `redis` 서비스 주소를 그대로 사용한다.
- API 계약과 분석 루브릭을 변경하지 않는다.
- 검증용 컨테이너는 종료하되 PostgreSQL 볼륨은 삭제하지 않는다.

---

### 작업 1: 런타임 의존성 재동기화 방지

**파일:** 생성 `tests/test_local_compose.py`; 수정 `Dockerfile`, `compose.yaml`.

**인터페이스:** API 명령은 `uv run --no-sync uvicorn proofread.api.app:create_app --factory --host 0.0.0.0 --port 8000`을 사용한다. worker 명령은 `uv run --no-sync dramatiq proofread.worker`를 사용한다.

- [ ] `tests/test_local_compose.py`에 다음 테스트를 작성한다.

  ```python
  from pathlib import Path

  PROJECT_ROOT = Path(__file__).resolve().parents[1]


  def test_runtime_commands_skip_dependency_sync() -> None:
      dockerfile = (PROJECT_ROOT / "Dockerfile").read_text()
      compose = (PROJECT_ROOT / "compose.yaml").read_text()

      assert 'CMD ["uv", "run", "--no-sync", "uvicorn"' in dockerfile
      assert 'command: ["uv", "run", "--no-sync", "dramatiq", "proofread.worker"]' in compose
  ```

- [ ] `uv run pytest tests/test_local_compose.py -v`를 실행해 테스트 파일 부재로 실패하는지 확인한다.
- [ ] Dockerfile의 `CMD`와 Compose worker `command`에 `--no-sync`를 추가한다.
- [ ] README가 `.env` 복사, `docker compose up --build`, `http://localhost:8000/healthz`를 함께 안내하는지 확인한다. 현재 세 항목이 있어 README는 변경하지 않는다.
- [ ] 집중 테스트, 전체 `uv run pytest -v`, `uv run ruff check .`, `docker compose config`를 실행한다.
- [ ] `fix: streamline local compose startup`으로 커밋한다.

### 작업 2: 실제 로컬 분석 흐름 검증

**파일:** 없음. 이 작업은 Task 1 결과의 수동 통합 검증이다.

**인터페이스:** `GET http://localhost:8000/healthz`는 `{"status":"ok"}`을 반환한다. `POST /v1/analyses`는 공개 저장소 URL에 대해 `analysis_id`와 `queued` 상태를 반환한다.

- [ ] `.env`가 없다면 `.env.example`을 복사해 생성한다. 이 파일은 Git에 추가하지 않는다.
- [ ] `docker compose up --build -d`를 실행한다.
- [ ] `curl --fail http://localhost:8000/healthz`로 API 준비 상태를 확인한다.
- [ ] 공개 저장소 URL과 `data_engineer`를 담아 `POST /v1/analyses`를 호출하고 `analysis_id`를 기록한다.
- [ ] `GET /v1/analyses/{analysis_id}`를 상태가 `completed` 또는 `failed`가 될 때까지 조회한다. `failed`면 GitHub API 오류 코드를 기록해 원인을 구분한다.
- [ ] worker 로그에 `localhost:6379` 연결 거부가 없는지 확인한다.
- [ ] `docker compose down`으로 검증용 컨테이너를 중지하고 `docker compose ps`가 비어 있는지 확인한다.

## 자체 검토

작업 1은 느린 시작의 원인인 런타임 의존성 동기화를 회귀 테스트로 막고, 작업 2는 API·Redis·PostgreSQL·worker를 포함한 실제 흐름을 검증한다. 클라우드 배포, LLM 연결, 평가 로직 변경은 범위에 포함하지 않는다.
