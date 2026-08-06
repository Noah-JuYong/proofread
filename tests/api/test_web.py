"""브라우저 분석 화면의 공개 진입점 계약을 검증합니다."""

import httpx
import pytest

from proofread.api.app import create_app
from proofread.api.routes.web import WEB_DIRECTORY


@pytest.mark.anyio
async def test_root_returns_analysis_form_and_script() -> None:
    """루트 화면은 저장소 URL 입력 폼과 분석 JavaScript를 제공합니다."""
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert 'id="analysis-form"' in response.text
    assert 'id="target-role"' in response.text
    assert 'value="infrastructure_engineer"' in response.text
    assert 'value="ai_engineer"' in response.text
    assert 'id="codex-feedback"' in response.text
    assert 'id="retry-analysis"' in response.text
    assert 'id="retry-codex"' in response.text
    assert 'id="download-error"' in response.text
    assert 'src="/static/app.js"' in response.text
    assert 'target_role: document.querySelector("#target-role").value' in (
        WEB_DIRECTORY / "app.js"
    ).read_text()
    assert 'model_development: "모델 개발"' in (WEB_DIRECTORY / "app.js").read_text()
    assert "http://127.0.0.1:8751/v1/codex/status" in (WEB_DIRECTORY / "app.js").read_text()
    assert "AI 피드백 생성" in (WEB_DIRECTORY / "app.js").read_text()
    assert "retryLastAnalysis" in (WEB_DIRECTORY / "app.js").read_text()
    assert "showDownloadError" in (WEB_DIRECTORY / "app.js").read_text()
    app_script = (WEB_DIRECTORY / "app.js").read_text()
    assert "async function runCodexAction" in app_script
    assert app_script.count("runCodexAction(async () =>") == 2
