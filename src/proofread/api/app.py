"""Proofread HTTP 애플리케이션의 진입점입니다.

이 모듈은 공개 GitHub 저장소 분석 파이프라인에서 요청 접수와 결과 제공 구간을
담당합니다. GitHub 수집, 규칙 평가, 비동기 작업 실행과 리포트 저장은 인접한
전용 모듈의 책임이며 이 모듈은 HTTP 계약만 제공합니다.
"""

import os
from collections.abc import Callable
from uuid import UUID

from fastapi import FastAPI

from proofread.api.routes.analyses import create_router
from proofread.persistence.database import create_session_factory
from proofread.persistence.repository import SqlAlchemyAnalysisRepository
from proofread.services.analysis import AnalysisRepository, InMemoryAnalysisRepository


def create_app(
    *,
    repository: AnalysisRepository | None = None,
    enqueue: Callable[[UUID], None] | None = None,
) -> FastAPI:
    """Proofread의 HTTP 애플리케이션을 생성합니다."""
    app = FastAPI(title="Proofread")

    configured_repository = repository or _default_repository()
    configured_enqueue = enqueue or _default_enqueue
    app.include_router(create_router(repository=configured_repository, enqueue=configured_enqueue))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """프로세스가 요청을 처리할 수 있음을 반환합니다."""
        return {"status": "ok"}

    return app


def _default_repository() -> AnalysisRepository:
    """배포 환경은 PostgreSQL, 로컬 단독 실행은 in-memory 저장소를 사용합니다."""
    if os.getenv("DATABASE_URL"):
        return SqlAlchemyAnalysisRepository(create_session_factory())
    return InMemoryAnalysisRepository()


def _default_enqueue(analysis_id: UUID) -> None:
    """배포 환경에서 Dramatiq 작업을 enqueue하고 로컬 단독 실행에서는 보류합니다."""
    if not os.getenv("DATABASE_URL"):
        return
    from proofread.worker import run_analysis_task

    run_analysis_task.send(str(analysis_id))
