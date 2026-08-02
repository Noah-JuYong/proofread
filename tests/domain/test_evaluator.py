"""저장소 신호를 포트폴리오 평가로 변환하는 규칙을 검증합니다."""

from proofread.domain.evaluator import evaluate
from proofread.domain.models import AssessmentCategory, RepositoryProfile


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
