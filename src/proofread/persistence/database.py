"""Proofread PostgreSQL 연결과 스키마 초기화를 제공합니다.

이 모듈은 분석 작업의 영속성 경계만 담당합니다. 작업 상태 전이와 GitHub 수집은
서비스·수집 모듈이 담당합니다.
"""

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from proofread.persistence.models import Base


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """환경 변수 또는 인자로 지정된 데이터베이스용 세션 팩토리를 만듭니다."""
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for persistent analysis storage.")
    engine: Engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
