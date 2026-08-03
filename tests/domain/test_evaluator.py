"""저장소 신호를 포트폴리오 평가로 변환하는 규칙을 검증합니다."""

from proofread.domain.evaluator import evaluate
from proofread.domain.models import AssessmentCategory, RepositoryProfile, TargetRole


def test_evaluate_reports_undocumented_test_signal() -> None:
    """테스트와 CI가 문서에 드러나지 않으면 근거가 있는 개선 과제를 만듭니다."""
    profile = RepositoryProfile(
        repository_url="https://github.com/acme/pipeline",
        paths={"tests/test_pipeline.py", ".github/workflows/ci.yml"},
        readme_sections={"overview", "installation"},
    )

    report = evaluate(profile)

    assert report.score_for(AssessmentCategory.QUALITY) == 13
    assert report.findings[0].evidence == [".github/workflows/ci.yml", "tests/test_pipeline.py"]
    assert report.findings[0].priority == "high"


def test_evaluate_does_not_report_documented_test_signal() -> None:
    """README가 테스트를 설명하면 문서화 누락 finding을 만들지 않습니다."""
    profile = RepositoryProfile(
        repository_url="https://github.com/acme/pipeline",
        paths={"tests/test_pipeline.py", ".github/workflows/ci.yml"},
        readme_sections={"overview", "testing"},
    )

    report = evaluate(profile)

    assert report.score_for(AssessmentCategory.QUALITY) == 13
    assert all(finding.code != "undocumented_test_signal" for finding in report.findings)


def test_evaluate_empty_profile_returns_zero_scores_without_evidence() -> None:
    """확인할 근거가 없는 저장소에는 점수나 근거 없는 조언을 만들지 않습니다."""
    report = evaluate(RepositoryProfile(repository_url="https://github.com/acme/empty"))

    assert all(score.score == 0 for score in report.categories.values())
    assert report.findings == []


def test_evaluate_infrastructure_report_uses_role_specific_evidence() -> None:
    """인프라 역할은 플랫폼 운영 신호를 다섯 축으로 분리해 점수화합니다."""
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
    assert report.categories[AssessmentCategory.DELIVERY].evidence == [
        ".github/workflows/deploy.yml",
        "Dockerfile",
    ]


def test_evaluate_infrastructure_reports_missing_iac_without_false_evidence() -> None:
    """탐지하지 못한 IaC에는 임의 경로를 evidence로 붙이지 않습니다."""
    profile = RepositoryProfile(
        repository_url="https://github.com/acme/service",
        paths={"Dockerfile"},
        readme_sections={"overview"},
    )

    report = evaluate(profile, TargetRole.INFRASTRUCTURE_ENGINEER)

    finding = next(
        finding
        for finding in report.findings
        if finding.code == "missing_infrastructure_as_code_evidence"
    )
    assert finding.evidence == []
