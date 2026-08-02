"""저장소 증거를 데이터 엔지니어 포트폴리오 리포트로 평가합니다.

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
)


def evaluate(profile: RepositoryProfile) -> AnalysisReport:
    """확인 가능한 profile 신호만 사용해 데이터 엔지니어 포트폴리오를 평가합니다."""
    categories = {
        AssessmentCategory.DATA_FLOW: _data_flow_score(profile),
        AssessmentCategory.REPRODUCIBILITY: _reproducibility_score(profile),
        AssessmentCategory.QUALITY: _quality_score(profile),
        AssessmentCategory.OPERABILITY: _operability_score(profile),
        AssessmentCategory.RESULTS: _results_score(profile),
    }
    findings = _findings(profile, categories)
    return AnalysisReport(categories=categories, findings=findings)


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
