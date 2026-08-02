"""Redis 큐에서 Proofread 분석 작업을 실행합니다.

이 모듈은 Dramatiq actor를 제공하며, HTTP API는 작업 생성만 담당합니다. GitHub 수집과
규칙 평가는 각각 collector와 evaluator 모듈의 책임입니다.
"""

import os
from uuid import UUID

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from proofread.domain.evaluator import evaluate
from proofread.github.collector import collect_public_repository
from proofread.persistence.database import create_session_factory
from proofread.persistence.repository import SqlAlchemyAnalysisRepository
from proofread.services.analysis import run_analysis

dramatiq.set_broker(RedisBroker(url=os.getenv("REDIS_URL", "redis://localhost:6379/0")))


@dramatiq.actor(max_retries=3, min_backoff=1000)
def run_analysis_task(analysis_id: str) -> None:
    """저장된 분석 ID 하나를 큐 워커에서 실행합니다."""
    repository = SqlAlchemyAnalysisRepository(create_session_factory())
    run_analysis(
        UUID(analysis_id),
        repository=repository,
        collector=collect_public_repository,
        evaluator=evaluate,
    )
