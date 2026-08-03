# 인프라 엔지니어 루브릭 설계

## 목표

Proofread가 공개 GitHub 저장소를 `infrastructure_engineer` 관점에서도 분석해,
확인 가능한 파일·README 근거와 개선 과제를 제공한다. 데이터 엔지니어 루브릭의
점수·finding 결과는 변경하지 않는다.

## 범위

- `POST /v1/analyses`의 `target_role`에 `infrastructure_engineer`를 추가한다.
- 웹 화면에서 데이터 엔지니어와 인프라 엔지니어 중 하나를 선택하게 한다.
- 다음 다섯 축을 각 0~20점으로 결정론적으로 평가한다.
  1. IaC·클라우드 구성
  2. 컨테이너·배포 자동화
  3. 플랫폼·오케스트레이션
  4. 관측성·신뢰성
  5. 보안·운영 문서
- 각 점수와 finding에는 탐지한 실제 경로 또는 README 섹션만 evidence로 넣는다.

## 제외 범위

- `ai_engineer` 루브릭과 비공개 저장소 수집
- LLM을 이용한 점수·finding 계산
- 새 GitHub API 호출 또는 저장소 스키마 마이그레이션

## 설계 선택

역할별 평가 함수를 분리하고, `target_role`로 적합한 함수를 선택한다. 하나의
데이터 엔지니어 규칙 집합에 인프라 키워드를 추가하는 방식은 `data_flow`처럼
직무와 맞지 않는 축을 노출한다. 역할별 리포트 모델을 완전히 분리하는 방식은
저장·HTTP·웹 계약을 중복시킨다.

공통 `AnalysisReport`와 `CategoryScore`는 유지하되, `AssessmentCategory`에 인프라
전용 축을 추가한다. 데이터 엔지니어 리포트에는 기존 다섯 축만, 인프라 리포트에는
새 다섯 축만 담는다. 웹은 이미 응답의 category 항목을 순회하므로, 표시 이름만
사람이 읽을 수 있게 변환하면 두 역할을 같은 화면으로 제공할 수 있다.

## 평가 규칙

| 축 | 탐지 신호 | 점수 원칙 |
| --- | --- | --- |
| IaC·클라우드 구성 | `*.tf`, Pulumi, CloudFormation, Terraform 구성 | 서로 다른 근거 묶음당 점수, 최대 20점 |
| 컨테이너·배포 자동화 | Dockerfile, Compose, GitHub Actions, 배포 workflow | 컨테이너와 자동 배포 신호를 독립 반영 |
| 플랫폼·오케스트레이션 | Kubernetes manifest, Helm chart, Kustomize, Argo CD | 플랫폼 관련 근거 묶음당 점수, 최대 20점 |
| 관측성·신뢰성 | Prometheus, Grafana, OpenTelemetry, Alertmanager, SLO, retry | 관측성·알림·복구 신호를 독립 반영 |
| 보안·운영 문서 | security, runbook, incident, architecture, secrets 관련 README 섹션·경로 | 보안 신호와 운영 문서 신호를 독립 반영 |

한 축에 탐지 근거가 없으면 해당 축 점수는 0점이다. 인프라 저장소에 IaC 또는
관측성 근거가 전혀 없으면 해당 축의 개선 finding을 만들며, evidence는 임의의
경로가 아니라 해당하는 README 섹션 또는 탐지 실패와 직접 관계 있는 최소 경로만
사용한다.

## 데이터 흐름

기존 GitHub collector가 만든 `RepositoryProfile(paths, readme_sections, readme_text,
languages)`을 그대로 사용한다. worker는 분석 요청에 저장된 `target_role`을
`evaluate(profile, target_role=...)`에 전달한다. 결과 `AnalysisReport`는 기존
repository와 API 응답에 저장되고, 브라우저는 선택한 역할을 요청 본문에 포함해
동적 category 카드를 표시한다.

## 오류 처리와 호환성

- 지원하지 않는 역할은 기존과 동일하게 HTTP 422로 거절한다.
- 저장된 기존 `data_engineer` 분석은 기존 category와 점수를 그대로 조회한다.
- 새 역할의 분석 작업 실패 처리와 GitHub rate-limit 재시도는 기존 상태 전이를
  그대로 사용한다.
- `narrator`는 기존 finding만 입력으로 사용하므로 역할 확장으로 권한이나 LLM
  범위가 넓어지지 않는다.

## 검증

- 인프라 fixture에 대해 다섯 축 점수·evidence·누락 finding을 단위 테스트한다.
- 데이터 엔지니어 fixture의 기존 기대값이 유지되는지 회귀 테스트한다.
- API가 인프라 역할을 202로 수락하고 임의 역할을 422로 거절하는지 검증한다.
- 웹 문서와 JavaScript가 역할 선택 컨트롤과 요청 본문을 제공하는지 검증한다.
- 전체 pytest, ruff, Docker Compose config를 실행한다.
