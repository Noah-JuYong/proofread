"""저장소 증거를 직무별 포트폴리오 리포트로 평가합니다.

이 모듈은 수집 완료된 ``RepositoryProfile``을 결정적 규칙으로 점수와 finding으로
변환합니다. GitHub API 호출, HTTP 응답, 작업 저장, LLM 문안 생성은 담당하지 않습니다.
"""

from collections.abc import Iterable

from proofread.domain.models import (
    AnalysisReport,
    AssessmentCategory,
    CategoryScore,
    Finding,
    Priority,
    RepositoryProfile,
    TargetRole,
)


def evaluate(
    profile: RepositoryProfile, target_role: TargetRole = TargetRole.DATA_ENGINEER
) -> AnalysisReport:
    """확인 가능한 profile 신호만 사용해 요청한 직무 포트폴리오를 평가합니다."""
    if target_role is TargetRole.INFRASTRUCTURE_ENGINEER:
        return _evaluate_infrastructure(profile)
    if target_role is TargetRole.AI_ENGINEER:
        return _evaluate_ai(profile)
    return _evaluate_data_engineer(profile)


def _evaluate_data_engineer(profile: RepositoryProfile) -> AnalysisReport:
    """기존 데이터 엔지니어 루브릭으로 리포트를 생성합니다."""
    categories = {
        AssessmentCategory.DATA_FLOW: _data_flow_score(profile),
        AssessmentCategory.REPRODUCIBILITY: _reproducibility_score(profile),
        AssessmentCategory.QUALITY: _quality_score(profile),
        AssessmentCategory.OPERABILITY: _operability_score(profile),
        AssessmentCategory.RESULTS: _results_score(profile),
    }
    findings = _findings(profile, categories)
    return AnalysisReport(categories=categories, findings=findings)


def _evaluate_infrastructure(profile: RepositoryProfile) -> AnalysisReport:
    """인프라·플랫폼 운영 근거를 직무 전용 다섯 축으로 평가합니다."""
    categories = {
        AssessmentCategory.INFRASTRUCTURE_AS_CODE: _path_group_score(
            profile,
            ((".tf", "terraform"), 10),
            (("pulumi", "cloudformation", "cdk"), 10),
        ),
        AssessmentCategory.DELIVERY: _path_group_score(
            profile,
            (("dockerfile",), 8),
            (("compose.yaml", "docker-compose"), 4),
            ((".github/workflows/deploy", ".github/workflows/release"), 8),
        ),
        AssessmentCategory.PLATFORM: _path_group_score(
            profile,
            (("k8s/", "kubernetes", "deployment.yaml"), 10),
            (("chart.yaml", "helm"), 6),
            (("kustomize", "argocd", "argo-cd"), 4),
        ),
        AssessmentCategory.OBSERVABILITY: _path_group_score(
            profile,
            (("prometheus", "grafana", "opentelemetry", "otel"), 8),
            (("alertmanager", "alert", "pagerduty"), 6),
            (("slo", "retry", "backoff"), 6),
        ),
        AssessmentCategory.SECURITY_OPERATIONS: _security_operations_score(profile),
    }
    return AnalysisReport(
        categories=categories,
        findings=_infrastructure_findings(profile, categories),
    )


def _evaluate_ai(profile: RepositoryProfile) -> AnalysisReport:
    """AI 모델 수명 주기 근거를 직무 전용 다섯 축으로 평가합니다."""
    evaluation_evidence = _path_group_score(
        profile,
        (("evaluate", "metrics", "benchmark", "fairness", "bias"), 10),
    )
    model_card_evidence = _readme_evidence(profile, ("model card", "evaluation", "metrics"))
    categories = {
        AssessmentCategory.DATA_FEATURES: _path_group_score(
            profile,
            (("data/", "dataset"), 10),
            (("feature", "feast", "dvc"), 10),
        ),
        AssessmentCategory.MODEL_DEVELOPMENT: _path_group_score(
            profile,
            (("train", "model"), 10),
            (("notebook", ".ipynb"), 5),
            (("pytorch", "tensorflow", "scikit", "sklearn"), 5),
        ),
        AssessmentCategory.MODEL_EVALUATION: CategoryScore(
            score=min(20, evaluation_evidence.score + (10 if model_card_evidence else 0)),
            evidence=_unique_sorted([*evaluation_evidence.evidence, *model_card_evidence]),
        ),
        AssessmentCategory.EXPERIMENT_REPRODUCIBILITY: _path_group_score(
            profile,
            (("mlflow", "mlruns", "wandb", "weights"), 10),
            (("dvc", "config", "lock", "seed"), 10),
        ),
        AssessmentCategory.SERVING_MLOPS: _path_group_score(
            profile,
            (("inference", "predict", "fastapi", "bentoml", "kserve", "seldon"), 10),
            (("monitoring", "model_metrics", "drift", "deployment"), 6),
        ),
    }
    return AnalysisReport(categories=categories, findings=_ai_findings(profile, categories))


def _data_flow_score(profile: RepositoryProfile) -> CategoryScore:
    evidence = _matching_paths(
        profile, ("airflow", "dbt", "etl", "elt", "ingest", "pipeline", "spark", "kafka")
    )
    return CategoryScore(score=min(20, len(evidence) * 5), evidence=evidence)


def _reproducibility_score(profile: RepositoryProfile) -> CategoryScore:
    evidence: list[str] = []
    score = 0
    for terms, points in (
        (("uv.lock", "poetry.lock", "requirements.txt", "pdm.lock"), 5),
        (("dockerfile", "compose.yaml", "docker-compose.yml"), 5),
        ((".env.example",), 4),
    ):
        match = _matching_paths(profile, terms)
        if match:
            evidence.extend(match)
            score += points
    if _readme_contains(profile, ("install", "setup", "run", "quickstart")):
        evidence.extend(_readme_evidence(profile, ("install", "setup", "run", "quickstart")))
        score += 6
    return CategoryScore(score=min(20, score), evidence=_unique_sorted(evidence))


def _quality_score(profile: RepositoryProfile) -> CategoryScore:
    evidence: list[str] = []
    score = 0
    tests = _matching_paths(profile, ("tests/", "test_"))
    if tests:
        evidence.extend(tests)
        score += 7
    workflows = _matching_paths(profile, (".github/workflows/",))
    if workflows:
        evidence.extend(workflows)
        score += 6
    tooling = _matching_paths(
        profile, ("pyproject.toml", "ruff.toml", ".flake8", "mypy.ini", "tox.ini")
    )
    if tooling:
        evidence.extend(tooling)
        score += 4
    typing = _matching_paths(profile, ("py.typed",))
    if typing:
        evidence.extend(typing)
        score += 3
    return CategoryScore(score=min(20, score), evidence=_unique_sorted(evidence))


def _operability_score(profile: RepositoryProfile) -> CategoryScore:
    evidence = _matching_paths(
        profile, ("log", "retry", "backoff", "validate", "quality", "monitor", "metric")
    )
    return CategoryScore(score=min(20, len(evidence) * 4), evidence=evidence)


def _results_score(profile: RepositoryProfile) -> CategoryScore:
    evidence = _readme_evidence(
        profile, ("%", "latency", "throughput", "records", "rows", "cost", "accuracy")
    )
    return CategoryScore(score=min(20, len(evidence) * 4), evidence=evidence)


def _path_group_score(
    profile: RepositoryProfile, *groups: tuple[tuple[str, ...], int]
) -> CategoryScore:
    """서로 다른 인프라 신호 묶음의 점수와 실제 경로를 합산합니다."""
    evidence: list[str] = []
    score = 0
    for terms, points in groups:
        matched = _matching_paths(profile, terms)
        if matched:
            evidence.extend(matched)
            score += points
    return CategoryScore(score=min(20, score), evidence=_unique_sorted(evidence))


def _security_operations_score(profile: RepositoryProfile) -> CategoryScore:
    """보안 자동화와 운영 문서 신호를 독립적으로 평가합니다."""
    security_evidence = _matching_paths(profile, ("security", "secrets", "sbom", "scan"))
    documentation_evidence = _readme_evidence(
        profile, ("runbook", "incident", "architecture", "operations")
    )
    score = (10 if security_evidence else 0) + (10 if documentation_evidence else 0)
    return CategoryScore(
        score=score,
        evidence=_unique_sorted([*security_evidence, *documentation_evidence]),
    )


def _findings(
    profile: RepositoryProfile, categories: dict[AssessmentCategory, CategoryScore]
) -> list[Finding]:
    findings: list[Finding] = []
    quality = categories[AssessmentCategory.QUALITY]
    tests = _matching_paths(profile, ("tests/", "test_"))
    workflows = _matching_paths(profile, (".github/workflows/",))
    if tests and workflows and not _readme_contains(profile, ("test", "testing", "verify")):
        findings.append(
            Finding(
                code="undocumented_test_signal",
                category=AssessmentCategory.QUALITY,
                priority=Priority.HIGH,
                message="테스트와 CI 신호가 README에 드러나지 않습니다.",
                recommendation="README에 테스트 실행 명령과 CI 검증 범위를 추가하세요.",
                evidence=_unique_sorted([*workflows, *tests]),
            )
        )
    if profile.paths and categories[AssessmentCategory.DATA_FLOW].score == 0:
        findings.append(
            Finding(
                code="missing_data_flow_evidence",
                category=AssessmentCategory.DATA_FLOW,
                priority=Priority.MEDIUM,
                message="저장소에서 데이터 흐름을 확인할 수 있는 신호가 없습니다.",
                recommendation="수집, 변환, 저장, 소비 단계와 각 책임을 문서화하세요.",
                evidence=_unique_sorted(list(profile.paths)[:1]),
            )
        )
    if quality.score == 0 and profile.paths:
        findings.append(
            Finding(
                code="missing_quality_evidence",
                category=AssessmentCategory.QUALITY,
                priority=Priority.MEDIUM,
                message="테스트 또는 CI 품질 신호를 확인할 수 없습니다.",
                recommendation="최소한의 자동화 테스트와 CI 워크플로우를 추가하세요.",
                evidence=_unique_sorted(list(profile.paths)[:1]),
            )
        )
    return findings


def _infrastructure_findings(
    profile: RepositoryProfile, categories: dict[AssessmentCategory, CategoryScore]
) -> list[Finding]:
    """인프라 루브릭에서 누락된 핵심 운영 근거를 안전하게 안내합니다."""
    findings: list[Finding] = []
    if categories[AssessmentCategory.INFRASTRUCTURE_AS_CODE].score == 0:
        findings.append(
            Finding(
                code="missing_infrastructure_as_code_evidence",
                category=AssessmentCategory.INFRASTRUCTURE_AS_CODE,
                priority=Priority.MEDIUM,
                message="IaC 또는 클라우드 구성 근거를 확인할 수 없습니다.",
                recommendation=(
                    "Terraform, Pulumi 또는 클라우드 구성 파일과 적용 범위를 문서화하세요."
                ),
                evidence=_readme_evidence(
                    profile, ("iac", "infrastructure", "terraform", "cloud")
                ),
            )
        )
    if categories[AssessmentCategory.OBSERVABILITY].score == 0:
        findings.append(
            Finding(
                code="missing_observability_evidence",
                category=AssessmentCategory.OBSERVABILITY,
                priority=Priority.MEDIUM,
                message="관측성·알림 또는 복구 근거를 확인할 수 없습니다.",
                recommendation="메트릭, 대시보드, 알림, 재시도 정책과 운영 절차를 문서화하세요.",
                evidence=_readme_evidence(
                    profile, ("observability", "monitoring", "alert", "runbook")
                ),
            )
        )
    return findings


def _ai_findings(
    profile: RepositoryProfile, categories: dict[AssessmentCategory, CategoryScore]
) -> list[Finding]:
    """AI 루브릭에서 누락된 데이터와 평가 근거를 안전하게 안내합니다."""
    findings: list[Finding] = []
    if categories[AssessmentCategory.DATA_FEATURES].score == 0:
        findings.append(
            Finding(
                code="missing_data_evidence",
                category=AssessmentCategory.DATA_FEATURES,
                priority=Priority.MEDIUM,
                message="데이터셋 또는 피처 관리 근거를 확인할 수 없습니다.",
                recommendation="데이터셋, 피처 정의, 버전 관리와 검증 절차를 문서화하세요.",
                evidence=_readme_evidence(profile, ("data", "dataset", "feature")),
            )
        )
    if categories[AssessmentCategory.MODEL_EVALUATION].score == 0:
        findings.append(
            Finding(
                code="missing_model_evaluation_evidence",
                category=AssessmentCategory.MODEL_EVALUATION,
                priority=Priority.MEDIUM,
                message="모델 평가 또는 책임 있는 AI 근거를 확인할 수 없습니다.",
                recommendation="평가 지표, benchmark, model card와 한계를 문서화하세요.",
                evidence=_readme_evidence(profile, ("evaluation", "metrics", "model card")),
            )
        )
    return findings


def _matching_paths(profile: RepositoryProfile, terms: Iterable[str]) -> list[str]:
    """경로 문자열에서 용어를 포함하는 실제 파일만 정렬해 반환합니다."""
    lowered_terms = tuple(term.lower() for term in terms)
    return sorted(
        path for path in profile.paths if any(term in path.lower() for term in lowered_terms)
    )


def _readme_contains(profile: RepositoryProfile, terms: Iterable[str]) -> bool:
    haystack = " ".join([*profile.readme_sections, profile.readme_text]).lower()
    return any(term.lower() in haystack for term in terms)


def _readme_evidence(profile: RepositoryProfile, terms: Iterable[str]) -> list[str]:
    return [
        f"README:{section}"
        for section in sorted(profile.readme_sections)
        if any(term.lower() in section.lower() for term in terms)
    ]


def _unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted(set(values))
