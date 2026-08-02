"""브라우저 분석 화면의 공개 진입점 계약을 검증합니다."""

from fastapi.testclient import TestClient

from proofread.api.app import create_app


def test_root_returns_analysis_form_and_script() -> None:
    """루트 화면은 저장소 URL 입력 폼과 분석 JavaScript를 제공합니다."""
    response = TestClient(create_app()).get("/")

    assert response.status_code == 200
    assert 'id="analysis-form"' in response.text
    assert 'src="/static/app.js"' in response.text
