"""GitHub 수집과 규칙 평가를 지속 가능한 분석 작업으로 실행합니다.

이 모듈은 작업 상태 전이와 수집·평가 호출 순서를 담당합니다. HTTP 라우팅, GitHub
통신 세부 구현, SQL 연결 설정, 큐 브로커 구성은 각각 인접 계층의 책임입니다.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel

from proofread.domain.models import AnalysisReport, RepositoryProfile, TargetRole
from proofread.github.errors import GitHubCollectionError


class AnalysisStatus(StrEnum):
    """분석 작업이 API에 노출하는 상태입니다."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Analysis(BaseModel):
    """저장소 분석 요청과 안전한 결과를 표현합니다."""

    id: UUID
    repository_url: str
    target_role: TargetRole = TargetRole.DATA_ENGINEER
    status: AnalysisStatus
    snapshot: RepositoryProfile | None = None
    report: AnalysisReport | None = None
    error_code: str | None = None


class AnalysisRepository(Protocol):
    """분석 작업을 저장하고 다시 조회하는 경계입니다."""

    def create(self, analysis: Analysis) -> None: ...

    def get(self, analysis_id: UUID) -> Analysis: ...

    def save(self, analysis: Analysis) -> None: ...

    def list_recent(self, limit: int = 20) -> list[Analysis]: ...


class InMemoryAnalysisRepository:
    """HTTP 통합 테스트와 로컬 단위 테스트용 비영속 저장소입니다."""

    def __init__(self) -> None:
        self._analyses: dict[UUID, Analysis] = {}

    def create(self, analysis: Analysis) -> None:
        self._analyses[analysis.id] = analysis

    def get(self, analysis_id: UUID) -> Analysis:
        return self._analyses[analysis_id]

    def save(self, analysis: Analysis) -> None:
        self._analyses[analysis.id] = analysis

    def list_recent(self, limit: int = 20) -> list[Analysis]:
        """테스트용 저장 순서 기준의 최근 분석을 반환합니다."""
        return list(self._analyses.values())[-limit:][::-1]


Collector = Callable[[str], RepositoryProfile]
Evaluator = Callable[[RepositoryProfile, TargetRole], AnalysisReport]
Narrator = Callable[[AnalysisReport], list[str]]


def create_analysis(
    repository_url: str,
    *,
    repository: AnalysisRepository,
    target_role: TargetRole = TargetRole.DATA_ENGINEER,
) -> UUID:
    """큐에 넣기 전 새 분석을 queued 상태로 저장합니다."""
    analysis = Analysis(
        id=uuid4(),
        repository_url=repository_url,
        target_role=target_role,
        status=AnalysisStatus.QUEUED,
    )
    repository.create(analysis)
    return analysis.id


def run_analysis(
    analysis_id: UUID,
    *,
    repository: AnalysisRepository,
    collector: Collector,
    evaluator: Evaluator,
    narrator: Narrator | None = None,
) -> None:
    """분석을 실행하고 완료 리포트 또는 안전한 실패 상태를 저장합니다."""
    analysis = repository.get(analysis_id)
    analysis.status = AnalysisStatus.RUNNING
    analysis.error_code = None
    repository.save(analysis)
    try:
        profile = collector(analysis.repository_url)
        report = evaluator(profile, analysis.target_role)
    except GitHubCollectionError as error:
        if error.retryable:
            analysis.status = AnalysisStatus.QUEUED
            repository.save(analysis)
            raise
        analysis.status = AnalysisStatus.FAILED
        analysis.error_code = error.code
        repository.save(analysis)
        return
    analysis.status = AnalysisStatus.COMPLETED
    analysis.snapshot = profile
    if narrator is not None:
        try:
            report.narratives = narrator(report)
        except Exception:
            report.narratives = []
    analysis.report = report
    repository.save(analysis)
