# Proofread 설계

## 목표

Proofread는 공개 GitHub 저장소를 데이터·인프라 엔지니어 취업 포트폴리오 관점에서 분석하고, 확인 가능한 코드·문서 근거와 개선 과제를 제공하는 오픈소스 서비스다. 지원 직무는 `data_engineer`, `infrastructure_engineer`다.

## 사용자 흐름

사용자가 공개 저장소 URL을 제출하면 API가 분석 작업을 생성한다. 워커는 README, 파일 트리, GitHub Actions, 언어 통계, 최근 커밋을 수집해 스냅샷으로 보관한다. 정규화된 `RepositoryProfile`은 순수 규칙 평가기에 전달되고, 결과 `AnalysisReport`가 조회 API에 저장된다.

```text
브라우저 또는 CLI -> FastAPI -> PostgreSQL + Redis 큐 -> worker
worker -> GitHub REST API -> snapshot -> 규칙 평가기 -> report
                                        -> 선택적 LLM 문안 생성
```

## 평가 기준

각 항목은 0점부터 20점까지 규칙으로 계산한다.

1. 데이터 흐름: 수집·변환·저장·소비 단계의 구현 또는 문서화
2. 재현성: 설치·실행·환경 변수·의존성 고정·컨테이너 구성
3. 품질: 테스트·린트·타입 검사·CI
4. 운영성: 로그·재시도·오류 처리·데이터 검증
5. 결과: 데이터 규모·처리량·비용·품질 지표·실험 결과

예를 들어 테스트 파일과 CI가 있는데 README에 검증 방법이 없으면, 평가기는 해당 경로를 evidence로 붙인 높은 우선순위의 finding을 만든다. 점수와 finding은 오직 규칙 기반 신호로만 생성한다.

인프라 엔지니어 루브릭은 IaC·클라우드 구성, 컨테이너·배포 자동화, 플랫폼·오케스트레이션, 관측성·신뢰성, 보안·운영 문서를 각각 0점부터 20점까지 평가한다.

## LLM 경계

LLM은 점수와 finding을 만들거나 변경하지 않는다. 이미 생성된 finding의 ID, 점수, 우선순위, evidence만 입력으로 받고, README 개선 문안과 사람이 읽기 쉬운 설명만 JSON 스키마에 맞춰 반환한다. 키가 없거나 호출이 실패하면 빈 narrative와 규칙 기반 리포트를 반환한다.

## API 계약

`POST /v1/analyses`:

```json
{"repository_url":"https://github.com/owner/repository","target_role":"data_engineer"}
```

응답은 `202 Accepted`와 `{"analysis_id":"uuid","status":"queued"}`다. `GET /v1/analyses/{analysis_id}`는 `queued`, `running`, `completed`, `failed` 상태와 완료된 리포트를 반환한다. 유효하지 않은 URL 또는 지원하지 않는 직무는 422, 없는 분석 ID는 404다.

## 안전과 운영

- 공개 저장소와 공개 메타데이터만 수집한다.
- GitHub 토큰·LLM 키·LLM 요청 본문을 영구 저장하거나 로그에 기록하지 않는다.
- 404는 안전한 실패 코드로, rate limit은 지수 백오프 대상의 재시도 가능한 오류로 분류한다.
- GitHub HTTP 호출은 fixture/respx로 격리해 테스트한다.
- 분석 수·성공/실패 수·기간·큐 대기 시간·LLM 성공률을 URL 라벨 없이 측정한다.

## 기술 선택

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL, Redis, Dramatiq, httpx, pytest, respx, Docker Compose, GitHub Actions, OpenTelemetry를 사용한다.

## 출시 기준

공개 저장소 하나에서 각 finding의 파일 경로 또는 README 근거를 보여 주고, LLM이 없어도 리포트를 조회할 수 있어야 한다.
