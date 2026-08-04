"""분석 요청과 결과 조회 HTTP 계약을 검증합니다."""

from uuid import UUID, uuid4

import httpx
import pytest

from proofread.api.app import create_app
from proofread.domain.models import (
    AnalysisReport,
    AssessmentCategory,
    CategoryScore,
    TargetRole,
)
from proofread.services.analysis import (
    Analysis,
    AnalysisStatus,
    InMemoryAnalysisRepository,
)


@pytest.mark.anyio
async def test_create_analysis_returns_queued() -> None:
    """유효한 공개 GitHub URL은 큐에 넣을 분석 ID와 queued 상태를 반환합니다."""
    repository = InMemoryAnalysisRepository()
    enqueued: list[UUID] = []
    transport = httpx.ASGITransport(app=create_app(repository=repository, enqueue=enqueued.append))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/analyses",
            json={
                "repository_url": "https://github.com/acme/pipeline",
                "target_role": "data_engineer",
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert enqueued == [UUID(body["analysis_id"])]


@pytest.mark.anyio
async def test_create_analysis_rejects_unsupported_role() -> None:
    """MVP 범위를 벗어난 직무는 명확한 validation 오류로 거절합니다."""
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/analyses",
            json={"repository_url": "https://github.com/acme/pipeline", "target_role": "backend"},
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_analysis_accepts_infrastructure_role() -> None:
    """인프라 엔지니어 역할은 큐에 넣을 분석 작업에 그대로 저장합니다."""
    repository = InMemoryAnalysisRepository()
    enqueued: list[UUID] = []
    transport = httpx.ASGITransport(app=create_app(repository=repository, enqueue=enqueued.append))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/analyses",
            json={
                "repository_url": "https://github.com/acme/platform",
                "target_role": "infrastructure_engineer",
            },
        )

    assert response.status_code == 202
    assert repository.get(enqueued[0]).target_role is TargetRole.INFRASTRUCTURE_ENGINEER


@pytest.mark.anyio
async def test_create_analysis_accepts_ai_role() -> None:
    """AI 엔지니어 역할은 큐에 넣을 분석 작업에 그대로 저장합니다."""
    repository = InMemoryAnalysisRepository()
    enqueued: list[UUID] = []
    transport = httpx.ASGITransport(app=create_app(repository=repository, enqueue=enqueued.append))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/v1/analyses",
            json={
                "repository_url": "https://github.com/acme/model-service",
                "target_role": "ai_engineer",
            },
        )

    assert response.status_code == 202
    assert repository.get(enqueued[0]).target_role is TargetRole.AI_ENGINEER


@pytest.mark.anyio
async def test_get_analysis_returns_completed_report() -> None:
    """완료된 작업은 저장된 근거 리포트를 그대로 조회할 수 있습니다."""
    repository = InMemoryAnalysisRepository()
    analysis_id = uuid4()
    repository.create(
        Analysis(
            id=analysis_id,
            repository_url="https://github.com/acme/pipeline",
            status=AnalysisStatus.COMPLETED,
            report=AnalysisReport(
                categories={
                    AssessmentCategory.DATA_FLOW: CategoryScore(score=10),
                    AssessmentCategory.REPRODUCIBILITY: CategoryScore(score=10),
                    AssessmentCategory.QUALITY: CategoryScore(score=10),
                    AssessmentCategory.OPERABILITY: CategoryScore(score=10),
                    AssessmentCategory.RESULTS: CategoryScore(score=10),
                }
            ),
        )
    )
    transport = httpx.ASGITransport(app=create_app(repository=repository))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/v1/analyses/{analysis_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["report"]["total_score"] == 50


@pytest.mark.anyio
async def test_get_analysis_returns_not_found() -> None:
    """존재하지 않는 분석 ID는 404로 반환합니다."""
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/v1/analyses/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_analyses_returns_recent_items() -> None:
    """최근 분석 목록은 로컬 저장소의 완료 결과를 반환합니다."""
    repository = InMemoryAnalysisRepository()
    analysis_id = uuid4()
    repository.create(
        Analysis(
            id=analysis_id,
            repository_url="https://github.com/acme/pipeline",
            status=AnalysisStatus.COMPLETED,
            report=AnalysisReport(categories={}),
        )
    )
    transport = httpx.ASGITransport(app=create_app(repository=repository))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/v1/analyses")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(analysis_id)
