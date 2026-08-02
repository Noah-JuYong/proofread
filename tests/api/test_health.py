"""Proofread API의 공개 health endpoint 계약을 검증합니다."""

import httpx
import pytest

from proofread.api.app import create_app


@pytest.mark.anyio
async def test_healthz_returns_ok() -> None:
    """서비스 상태 endpoint는 호출자에게 정상 상태를 반환한다."""
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
