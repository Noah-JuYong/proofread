# 인프라 엔지니어 루브릭 구현 계획

> **에이전트 작업자용:** 이 계획을 작업 단위로 구현할 때는 `superpowers:executing-plans` 하위 스킬을 반드시 사용합니다. 단계는 체크박스(`- [ ]`)로 관리합니다.

**목표:** 공개 GitHub 저장소를 `infrastructure_engineer` 역할로 분석해 역할별 점수와 근거 기반 개선 과제를 반환한다.

**아키텍처:** `TargetRole`이 API 요청부터 worker 평가 호출까지 분석 역할을 보존한다. `evaluate`는 공통 `AnalysisReport` 모델을 반환하되 역할별로 분리된 순수 규칙 함수를 선택한다. 웹은 역할 선택 값을 요청에 보내고 category 이름을 한국어로 표시한다.

**기술 스택:** Python 3.12, FastAPI, Pydantic v2, Dramatiq, HTML, browser JavaScript, pytest.

## 공통 제약

- `data_engineer`의 기존 다섯 축, 점수, finding 동작을 변경하지 않는다.
- 인프라 루브릭은 IaC·클라우드 구성, 컨테이너·배포 자동화, 플랫폼·오케스트레이션, 관측성·신뢰성, 보안·운영 문서를 각각 0~20점으로 계산한다.
- LLM, 새 GitHub API 호출, DB 스키마 마이그레이션, 비공개 저장소 지원을 추가하지 않는다.
- 누락 finding은 실제 관련 README 섹션이 있을 때만 evidence로 사용하고, 없으면 빈 배열을 반환한다.

---

### 작업 1: 역할 모델과 인프라 규칙 평가기

**파일:** 수정 `src/proofread/domain/models.py`, `src/proofread/domain/evaluator.py`; 수정 `tests/domain/test_evaluator.py`.

**인터페이스:** `TargetRole.DATA_ENGINEER = "data_engineer"`, `TargetRole.INFRASTRUCTURE_ENGINEER = "infrastructure_engineer"`; `evaluate(profile: RepositoryProfile, target_role: TargetRole = TargetRole.DATA_ENGINEER) -> AnalysisReport`.

- [ ] **1단계: 실패하는 인프라 평가 테스트를 작성한다.**

  ```python
  def test_evaluate_infrastructure_report_uses_role_specific_evidence() -> None:
      profile = RepositoryProfile(
          repository_url="https://github.com/acme/platform",
          paths={
              "infrastructure/main.tf",
              "Dockerfile",
              ".github/workflows/deploy.yml",
              "charts/api/Chart.yaml",
              "k8s/deployment.yaml",
              "monitoring/prometheus.yml",
              "monitoring/alertmanager.yml",
              ".github/workflows/security-scan.yml",
          },
          readme_sections={"runbook"},
      )

      report = evaluate(profile, TargetRole.INFRASTRUCTURE_ENGINEER)

      assert report.score_for(AssessmentCategory.INFRASTRUCTURE_AS_CODE) == 10
      assert report.score_for(AssessmentCategory.DELIVERY) == 16
      assert report.score_for(AssessmentCategory.PLATFORM) == 16
      assert report.score_for(AssessmentCategory.OBSERVABILITY) == 14
      assert report.score_for(AssessmentCategory.SECURITY_OPERATIONS) == 20
  ```

- [ ] **2단계: 실패를 확인한다.** `uv run pytest tests/domain/test_evaluator.py -v`를 실행해 `TargetRole` 또는 인프라 category 부재로 실패하는지 확인한다.
- [ ] **3단계: 최소 구현을 작성한다.** `TargetRole`과 다섯 인프라 `AssessmentCategory`를 추가한다. `evaluate`가 역할을 분기하도록 하고, `_evaluate_infrastructure`에서 다음 고정 점수 묶음을 더한다.

  ```python
  infrastructure_as_code = ((".tf", "terraform"), 10), (("pulumi", "cloudformation", "cdk"), 10)
  delivery = (("dockerfile",), 8), (("compose.yaml", "docker-compose"), 4), (("deploy", "release"), 8)
  platform = (("k8s/", "kubernetes", "deployment.yaml"), 10), (("chart.yaml", "helm"), 6), (("kustomize", "argocd", "argo-cd"), 4)
  observability = (("prometheus", "grafana", "opentelemetry", "otel"), 8), (("alertmanager", "alert", "pagerduty"), 6), (("slo", "retry", "backoff"), 6)
  security_operations = (("security", "secrets", "sbom", "scan"), 10), (("runbook", "incident", "architecture", "operations"), 10)
  ```

  README 섹션은 마지막 `security_operations` 묶음에만 사용한다. IaC와 관측성 점수가 0이면 각각 `missing_infrastructure_as_code_evidence`, `missing_observability_evidence` finding을 추가하고, 관련 README 섹션이 없으면 evidence는 빈 배열로 둔다.
- [ ] **4단계: 점수와 기존 회귀 테스트를 확인한다.** `uv run pytest tests/domain/test_evaluator.py -v`를 실행해 PASS를 확인한다.
- [ ] **5단계: 커밋한다.** `git add src/proofread/domain/models.py src/proofread/domain/evaluator.py tests/domain/test_evaluator.py && git commit -m "feat: add infrastructure rubric"를 실행한다.

### 작업 2: API·서비스·worker 역할 전달

**파일:** 수정 `src/proofread/api/routes/analyses.py`, `src/proofread/services/analysis.py`, `src/proofread/worker.py`; 수정 `tests/api/test_analyses.py`, `tests/services/test_analysis.py`.

**인터페이스:** `CreateAnalysisRequest.target_role: TargetRole`; `Analysis.target_role: TargetRole`; `Evaluator = Callable[[RepositoryProfile, TargetRole], AnalysisReport]`; `run_analysis`은 저장된 `analysis.target_role`을 evaluator의 두 번째 인자로 전달한다.

- [ ] **1단계: 실패하는 API·서비스 테스트를 작성한다.** API 테스트는 `target_role="infrastructure_engineer"` 요청이 202와 같은 역할을 반환하는지 확인한다. 서비스 테스트는 evaluator가 받은 역할을 목록에 추가해 `TargetRole.INFRASTRUCTURE_ENGINEER`인지 검증한다.

  ```python
  received_roles: list[TargetRole] = []

  def evaluator(profile: RepositoryProfile, role: TargetRole) -> AnalysisReport:
      received_roles.append(role)
      return evaluate(profile, role)

  assert received_roles == [TargetRole.INFRASTRUCTURE_ENGINEER]
  ```

- [ ] **2단계: 실패를 확인한다.** `uv run pytest tests/api/test_analyses.py tests/services/test_analysis.py -v`를 실행해 API validation 또는 evaluator 인자 수 불일치로 실패하는지 확인한다.
- [ ] **3단계: 최소 구현을 작성한다.** API 요청 모델의 `Literal`을 `TargetRole`로 바꾸고, `Analysis`·`create_analysis`·`Evaluator`의 역할 타입을 맞춘다. `run_analysis`은 `evaluator(profile, analysis.target_role)`을 호출하며 worker는 `evaluate`를 그대로 전달한다.
- [ ] **4단계: 역할 전달 테스트를 확인한다.** `uv run pytest tests/api/test_analyses.py tests/services/test_analysis.py -v`를 실행해 PASS를 확인한다.
- [ ] **5단계: 커밋한다.** `git add src/proofread/api/routes/analyses.py src/proofread/services/analysis.py src/proofread/worker.py tests/api/test_analyses.py tests/services/test_analysis.py && git commit -m "feat: route infrastructure analyses"를 실행한다.

### 작업 3: 웹 역할 선택과 공개 문서

**파일:** 수정 `src/proofread/web/index.html`, `src/proofread/web/app.js`, `README.md`, `docs/superpowers/specs/2026-08-02-proofread-design.md`; 수정 `tests/api/test_web.py`.

**인터페이스:** HTML은 `id="target-role"` select에 `data_engineer`, `infrastructure_engineer` option을 제공한다. JavaScript는 `{ repository_url: url, target_role: selectedRole }`을 전송하고, category key를 한국어 label로 변환한다.

- [ ] **1단계: 실패하는 웹 계약 테스트를 작성한다.**

  ```python
  assert 'id="target-role"' in response.text
  assert 'value="infrastructure_engineer"' in response.text
  assert 'target_role: selectedRole' in (WEB_DIRECTORY / "app.js").read_text()
  ```

- [ ] **2단계: 실패를 확인한다.** `uv run pytest tests/api/test_web.py -v`를 실행해 role selector 부재로 실패하는지 확인한다.
- [ ] **3단계: 최소 구현을 작성한다.** 입력 폼에 한국어 role select와 안내 문구를 추가한다. `app.js`에서 선택 값을 POST body에 넣고, 두 역할의 category label map을 사용해 점수 카드를 렌더링한다. README와 제품 설계 문서의 지원 역할을 두 역할로 갱신한다.
- [ ] **4단계: 웹 계약을 확인한다.** `uv run pytest tests/api/test_web.py -v`를 실행해 PASS를 확인한다.
- [ ] **5단계: 전체 검증과 커밋을 실행한다.** `uv run pytest -v && uv run ruff check . && docker compose config --quiet && git diff --check`를 실행한 뒤 `git add src/proofread/web/index.html src/proofread/web/app.js README.md docs/superpowers/specs/2026-08-02-proofread-design.md tests/api/test_web.py && git commit -m "feat: select infrastructure role in web report"를 실행한다.

## 자체 검토

작업 1은 역할별 category와 결정론적 인프라 점수를 제공하고, 작업 2는 선택된 역할을 비동기 worker까지 보존한다. 작업 3은 사용자가 웹에서 새 역할을 요청할 수 있게 하며 공개 문서를 갱신한다. 계획은 AI 루브릭, LLM 점수화, 추가 수집 API, DB 마이그레이션을 포함하지 않는다.
