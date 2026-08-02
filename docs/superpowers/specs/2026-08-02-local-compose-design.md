# 로컬 Compose 설계

## 목표

개발자가 비용이나 별도 클라우드 계정 없이 `docker compose up --build` 한 번으로 Proofread의 API, worker, PostgreSQL, Redis를 실행하고 공개 저장소 분석 흐름을 검증하게 한다.

## 범위

- 컨테이너 런타임 명령은 이미지에 이미 설치된 잠금된 의존성만 사용한다.
- API와 worker는 `.env.example`의 Compose 서비스 주소를 `.env`로 복사해 사용한다.
- 로컬 접속 문서는 `http://localhost:8000`과 `/healthz`를 기준으로 안내한다.
- 공개 GitHub 저장소 하나를 제출해 `queued`에서 최종 상태까지 전이하는 수동 E2E 절차를 문서화하고 검증한다.

## 제외 범위

- 클라우드 배포, 결제 계정 생성, 외부 관리형 DB 또는 Redis 연결
- GitHub 비공개 저장소 분석이나 사용자 GitHub 토큰 자동 설정
- LLM 제공자 연동

## 아키텍처

Dockerfile의 API 명령과 Compose의 worker 명령은 `uv run --no-sync`를 사용한다. 이미지 빌드 단계의 `uv sync --frozen --no-dev`가 런타임 환경을 완성하므로, 시작 시점에 개발 도구를 추가 설치하지 않는다.

Compose는 `.env`가 있는 경우에만 해당 파일의 `DATABASE_URL`, `REDIS_URL`을 API와 worker에 전달한다. 기본값은 `.env.example`에 정의된 `postgres`, `redis` 서비스 호스트를 사용하며, 실제 키나 토큰은 새로 요구하지 않는다.

## 실패 처리

- `.env`가 없으면 README의 복사 명령으로 복구한다. API만 단독 실행할 때는 기존 in-memory 모드가 유지되지만, Compose worker E2E는 지원하지 않는다.
- `localhost:8000` 포트가 사용 중이면 사용자에게 포트 충돌을 해소하거나 Compose 포트 매핑을 바꾸도록 안내한다. 다른 로컬 프로세스를 종료하지 않는다.
- GitHub API 제한 또는 네트워크 오류로 분석이 실패하면 실패 상태와 오류 코드를 확인하고, 코드 변경 없이 나중에 재시도한다.

## 검증

- 설정 회귀 테스트로 API와 worker 런타임 명령이 `--no-sync`를 유지하는지 확인한다.
- `docker compose config`로 Compose 구성을 확인한다.
- `docker compose up --build -d` 후 `http://localhost:8000/healthz`가 `{"status":"ok"}`을 반환하는지 확인한다.
- 공개 저장소 분석을 요청하고, 결과 조회가 `completed` 또는 외부 실패 원인을 설명하는 `failed` 상태로 끝나는지 확인한다.
