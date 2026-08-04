"""분석 작업 생성과 조회 HTTP 계약을 제공합니다.

이 모듈은 요청 유효성 검사와 상태 직렬화만 담당합니다. GitHub 수집과 평가 실행은
워크커가, 작업 영속성은 주입된 repository가 담당합니다.
"""

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from proofread.domain.models import TargetRole
from proofread.services.analysis import (
    Analysis,
    AnalysisRepository,
    AnalysisStatus,
    create_analysis,
)


class CreateAnalysisRequest(BaseModel):
    """분석 시작 요청의 공개 저장소와 지원 직무입니다."""

    repository_url: str = Field(pattern=r"^https://github\.com/[^/]+/[^/]+$")
    target_role: TargetRole


class CreateAnalysisResponse(BaseModel):
    """큐에 저장된 분석 작업의 초기 상태입니다."""

    analysis_id: UUID
    status: AnalysisStatus


def create_router(
    *,
    repository: AnalysisRepository,
    enqueue: Callable[[UUID], None],
    on_created: Callable[[], None],
) -> APIRouter:
    """특정 저장소와 큐 동작에 연결된 분석 라우터를 생성합니다."""
    router = APIRouter(prefix="/v1/analyses", tags=["analyses"])

    @router.post("", response_model=CreateAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
    def create(request: CreateAnalysisRequest) -> CreateAnalysisResponse:
        """유효한 공개 저장소 분석을 queued 상태로 저장하고 큐에 넣습니다."""
        analysis_id = create_analysis(
            request.repository_url,
            repository=repository,
            target_role=request.target_role,
        )
        enqueue(analysis_id)
        on_created()
        return CreateAnalysisResponse(analysis_id=analysis_id, status=AnalysisStatus.QUEUED)

    @router.get("/{analysis_id}", response_model=Analysis)
    def get(analysis_id: UUID) -> Analysis:
        """저장된 분석 상태와 완료된 리포트를 반환합니다."""
        try:
            return repository.get(analysis_id)
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found."
            ) from error

    @router.get("", response_model=list[Analysis])
    def list_recent() -> list[Analysis]:
        """최근 분석 이력을 최신 순서로 반환합니다."""
        return repository.list_recent()

    return router
