"""SQLAlchemy 행과 서비스 분석 모델을 상호 변환합니다."""

from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from proofread.domain.models import AnalysisReport, RepositoryProfile
from proofread.persistence.models import AnalysisRecord
from proofread.services.analysis import Analysis, AnalysisRepository, AnalysisStatus


class SqlAlchemyAnalysisRepository(AnalysisRepository):
    """분석 작업을 PostgreSQL JSON 스냅샷과 함께 저장합니다."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def create(self, analysis: Analysis) -> None:
        with self._sessions.begin() as session:
            session.add(_to_record(analysis))

    def get(self, analysis_id: UUID) -> Analysis:
        with self._sessions() as session:
            record = session.get(AnalysisRecord, str(analysis_id))
            if record is None:
                raise KeyError(analysis_id)
            return _to_analysis(record)

    def save(self, analysis: Analysis) -> None:
        with self._sessions.begin() as session:
            record = session.get(AnalysisRecord, str(analysis.id))
            if record is None:
                raise KeyError(analysis.id)
            record.status = analysis.status.value
            record.snapshot = (
                analysis.snapshot.model_dump(mode="json") if analysis.snapshot else None
            )
            record.report = analysis.report.model_dump(mode="json") if analysis.report else None
            record.error_code = analysis.error_code


def _to_record(analysis: Analysis) -> AnalysisRecord:
    return AnalysisRecord(
        id=str(analysis.id),
        repository_url=analysis.repository_url,
        target_role=analysis.target_role,
        status=analysis.status.value,
        snapshot=analysis.snapshot.model_dump(mode="json") if analysis.snapshot else None,
        report=analysis.report.model_dump(mode="json") if analysis.report else None,
        error_code=analysis.error_code,
    )


def _to_analysis(record: AnalysisRecord) -> Analysis:
    return Analysis(
        id=UUID(record.id),
        repository_url=record.repository_url,
        target_role=record.target_role,
        status=AnalysisStatus(record.status),
        snapshot=RepositoryProfile.model_validate(record.snapshot) if record.snapshot else None,
        report=AnalysisReport.model_validate(record.report) if record.report else None,
        error_code=record.error_code,
    )
