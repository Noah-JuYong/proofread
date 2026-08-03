"""분석 작업의 상태 전이와 안전한 실패 처리를 검증합니다."""

import pytest

from proofread.domain.evaluator import evaluate
from proofread.domain.models import AnalysisReport, RepositoryProfile, TargetRole
from proofread.github.errors import RateLimited, RepositoryNotFound
from proofread.services.analysis import (
    AnalysisStatus,
    InMemoryAnalysisRepository,
    create_analysis,
    run_analysis,
)


def test_run_analysis_persists_completed_report() -> None:
    """수집과 평가가 성공하면 작업이 완료 상태와 리포트를 보관합니다."""
    repository = InMemoryAnalysisRepository()
    analysis_id = create_analysis("https://github.com/acme/pipeline", repository=repository)

    run_analysis(
        analysis_id,
        repository=repository,
        collector=lambda _: RepositoryProfile(
            repository_url="https://github.com/acme/pipeline", paths={"tests/test_pipeline.py"}
        ),
        evaluator=evaluate,
    )

    analysis = repository.get(analysis_id)
    assert analysis.status is AnalysisStatus.COMPLETED
    assert analysis.report is not None


def test_run_analysis_persists_safe_permanent_failure() -> None:
    """없는 공개 저장소는 안전한 오류 코드만 남기고 실패로 끝납니다."""
    repository = InMemoryAnalysisRepository()
    analysis_id = create_analysis("https://github.com/acme/missing", repository=repository)

    run_analysis(
        analysis_id,
        repository=repository,
        collector=lambda _: (_ for _ in ()).throw(RepositoryNotFound("not found")),
        evaluator=evaluate,
    )

    analysis = repository.get(analysis_id)
    assert analysis.status is AnalysisStatus.FAILED
    assert analysis.error_code == "repository_not_found"


def test_run_analysis_reraises_retryable_rate_limit() -> None:
    """rate limit은 영구 실패로 저장하지 않고 워커 재시도를 위해 다시 발생시킵니다."""
    repository = InMemoryAnalysisRepository()
    analysis_id = create_analysis("https://github.com/acme/pipeline", repository=repository)

    with pytest.raises(RateLimited):
        run_analysis(
            analysis_id,
            repository=repository,
            collector=lambda _: (_ for _ in ()).throw(RateLimited("limited")),
            evaluator=evaluate,
        )

    assert repository.get(analysis_id).status is AnalysisStatus.QUEUED


def test_run_analysis_passes_stored_target_role_to_evaluator() -> None:
    """worker 실행은 분석 요청에 저장된 인프라 역할로 평가기를 호출합니다."""
    repository = InMemoryAnalysisRepository()
    analysis_id = create_analysis(
        "https://github.com/acme/platform",
        repository=repository,
        target_role=TargetRole.INFRASTRUCTURE_ENGINEER,
    )
    received_roles: list[TargetRole] = []

    def evaluator(profile: RepositoryProfile, role: TargetRole) -> AnalysisReport:
        received_roles.append(role)
        return evaluate(profile, role)

    run_analysis(
        analysis_id,
        repository=repository,
        collector=lambda _: RepositoryProfile(repository_url="https://github.com/acme/platform"),
        evaluator=evaluator,
    )

    assert received_roles == [TargetRole.INFRASTRUCTURE_ENGINEER]
