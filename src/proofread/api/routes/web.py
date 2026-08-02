"""Proofread 브라우저 분석 화면의 HTML 진입점을 제공합니다."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

WEB_DIRECTORY = Path(__file__).resolve().parents[2] / "web"


def create_router() -> APIRouter:
    """정적 브라우저 앱의 root HTML 라우터를 생성합니다."""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> HTMLResponse:
        """저장소 분석 입력 화면을 반환합니다."""
        return HTMLResponse((WEB_DIRECTORY / "index.html").read_text(encoding="utf-8"))

    return router
