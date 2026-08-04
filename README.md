# Proofread

Proofread는 데이터 엔지니어를 위한 근거 기반 GitHub 포트폴리오 분석 도구입니다.
자유 형식의 모델 점수에 의존하지 않고, 탐지한 파일 또는 README 섹션을 모든
개선 제안의 근거로 연결합니다.

이 도구는 역할별 코드·문서·운영 근거를 평가합니다. 공개 저장소에서
`data_engineer`, `infrastructure_engineer`, `ai_engineer` 직무를 지원합니다. 점수와
finding은 결정론적으로 계산하며, 선택적 LLM 어댑터는 기존 finding의 문안만 다듬을 수 있습니다.

## 로컬 개발

```bash
cp .env.example .env
uv sync --group dev
uv run uvicorn proofread.api.app:create_app --factory --reload
```

실행 중인 서비스는 `GET http://localhost:8000/healthz`로 확인합니다.

API, worker, PostgreSQL, Redis를 함께 실행하려면 다음 명령을 사용합니다.

```bash
docker compose up --build
```

## 로컬 Codex AI 피드백

분석 점수와 finding은 항상 규칙 기반으로 계산합니다. 선택적 AI 피드백은 각 사용자의
PC에서만 동작하며, Docker 컨테이너에는 Codex 로그인 정보가 전달되지 않습니다.

Compose 실행 뒤 별도 터미널에서 다음을 실행합니다.

```bash
uv run proofread-codex-companion
```

브라우저에서 `http://localhost:8000`을 열고 분석을 완료한 뒤 `Codex로 로그인`과
`AI 피드백 생성`을 차례로 선택합니다. 사용자는 자신의 PC에 Codex CLI를 설치하고
직접 로그인해야 합니다. OAuth 토큰과 LLM 요청 본문은 Proofread 데이터베이스나 로그에
저장하지 않습니다.

첫 릴리스는 공개 GitHub 저장소만 분석합니다.

## API

```bash
curl -X POST http://localhost:8000/v1/analyses \
  -H 'content-type: application/json' \
  -d '{"repository_url":"https://github.com/owner/repository","target_role":"data_engineer"}'
```

`GET /v1/analyses/{analysis_id}`를 조회하면 `queued`, `running`, `completed`,
`failed` 상태와 결과를 확인할 수 있습니다. Compose worker는 Redis와 PostgreSQL을
통해 작업을 처리합니다.

## 개인정보 보호와 기여

Proofread는 공개 GitHub 메타데이터만 보관합니다. GitHub 토큰, LLM 키, LLM 요청
본문은 저장하지 않으며, 저장소 URL을 메트릭 라벨에도 사용하지 않습니다. Pull Request를
열기 전에는 `uv run pytest -v`, `uv run ruff check .`, `docker compose config`를
실행합니다.
