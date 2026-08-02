"""브라우저 분석 화면의 공개 진입점 계약을 검증합니다."""

import httpx
import pytest

from proofread.api.app import create_app


@pytest.mark.anyio
async def test_root_returns_analysis_form_and_script() -> None:
    """루트 화면은 저장소 URL 입력 폼과 분석 JavaScript를 제공합니다."""
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert 'id="analysis-form"' in response.text
    assert 'src="/static/app.js"' in response.text
