# AI 엔지니어 루브릭 설계

## 목표

Proofread가 공개 GitHub 저장소를 `ai_engineer` 관점에서도 분석해, 실제 파일과
README 섹션을 evidence로 갖는 점수와 개선 과제를 반환한다. 기존 데이터·인프라
루브릭의 결과는 바꾸지 않는다.

## 범위

- `ai_engineer` 역할을 API·worker·웹 역할 선택에 추가한다.
- 다음 다섯 축을 각 0~20점으로 결정론적으로 평가한다.
  1. 데이터·피처
  2. 모델 개발
  3. 평가·책임 있는 AI
  4. 실험·재현성
  5. 서빙·MLOps
- 점수와 finding은 경로·README 섹션·README 텍스트의 탐지 신호만 사용한다.

## 제외 범위

- LLM이 점수 또는 finding을 만들거나 변경하는 기능
- 모델 파일, 데이터셋, 비공개 저장소의 내용 수집
- 새 GitHub API 호출, DB 스키마 마이그레이션, 클라우드 배포

## 설계

`TargetRole.AI_ENGINEER`와 다섯 AI 전용 `AssessmentCategory`를 추가하고,
`evaluate(profile, target_role)`가 `_evaluate_ai` 순수 함수로 분기한다. 공통
`AnalysisReport`, 영속성, 상태 전이, API 응답 구조는 그대로 사용한다.

웹은 기존 select에 AI 엔지니어 option을 추가하고, 응답 category key를 한국어
label로 변환한다. 따라서 새 프론트엔드 상태나 별도 API는 필요 없다.

## 평가 규칙

| 축 | 탐지 신호 | 점수 원칙 |
| --- | --- | --- |
| 데이터·피처 | `data/`, dataset, feature, Feast, DVC | 독립 신호 묶음당 점수, 최대 20점 |
| 모델 개발 | train, model, PyTorch, TensorFlow, scikit-learn, notebook | 학습 코드·모델 프레임워크·notebook 신호를 독립 반영 |
| 평가·책임 있는 AI | evaluate, metrics, benchmark, accuracy, fairness, bias, model card | 평가 자동화와 책임 있는 AI 문서를 독립 반영 |
| 실험·재현성 | MLflow, Weights & Biases, experiment, config, lock file, seed | 실험 추적·설정·재현성 근거를 독립 반영 |
| 서빙·MLOps | FastAPI, BentoML, KServe, Seldon, deployment, monitoring | 추론 서비스·배포·모델 모니터링 신호를 독립 반영 |

데이터·피처 또는 모델 평가 신호가 전혀 없으면 각각 개선 finding을 생성한다. 관련
README 섹션이 탐지된 경우에만 evidence로 쓰며, 없으면 빈 배열을 반환해 임의의
경로를 근거로 제시하지 않는다.

## 호환성과 검증

- 지원하지 않는 역할은 기존처럼 HTTP 422로 거절한다.
- 기존 분석의 `data_engineer`, `infrastructure_engineer` 결과와 저장 형식은 유지한다.
- AI fixture의 다섯 축 점수·evidence·누락 finding, 기존 직무 회귀, API 수락,
  서비스 역할 전달, 웹 role option을 테스트한다.
- 전체 pytest, ruff, Docker Compose config와 Docker worker E2E를 실행한다.
