"""localhost 전용 Codex 동반 프로세스 HTTP 계약을 제공합니다.

이 모듈은 브라우저와 로컬 Codex CLI 사이의 인증·서술 요청만 담당합니다. GitHub 수집,
규칙 기반 점수 계산, 분석 작업 저장과 OAuth 토큰 보관은 각각 기존 분석 서비스와 Codex
CLI의 책임입니다.
"""

from typing import Protocol

from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from proofread.companion.codex import (
    CodexAuthenticationError,
    CodexCli,
    CodexGenerationError,
    CodexStatus,
    CodexUnavailableError,
)
from proofread.domain.models import AnalysisReport
from proofread.llm.narrator import narrate

ALLOWED_ORIGINS = ("http://localhost:8000", "http://127.0.0.1:8000")


class CodexClient(Protocol):
    """동반 API가 필요한 Codex 상태·로그인·서술 기능입니다."""

    def status(self) -> CodexStatus:
        """설치와 로그인 상태를 반환합니다."""

    def start_login(self) -> None:
        """사용자 로그인 흐름을 시작합니다."""

    def generate(self, payload: list[dict[str, object]]) -> list[dict[str, str]]:
        """제한된 finding 입력으로 서술을 생성합니다."""


class CodexStatusResponse(BaseModel):
    """브라우저가 표시할 로컬 Codex 가능 상태입니다."""

    available: bool
    authenticated: bool


class NarrativesResponse(BaseModel):
    """기존 finding에 연결된 LLM 서술 목록입니다."""

    narratives: list[str]


def create_companion_app(*, codex: CodexClient | None = None) -> FastAPI:
    """localhost 브라우저만 접속할 수 있는 Codex 동반 API를 만듭니다."""
    app = FastAPI(title="Proofread Codex Companion")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type"],
    )
    client = codex or CodexCli()
    router = APIRouter(prefix="/v1/codex")

    @router.get("/status", response_model=CodexStatusResponse)
    def get_status() -> CodexStatusResponse:
        """설치·로그인 상태만 반환하고 인증 세부 정보는 노출하지 않습니다."""
        current_status = client.status()
        return CodexStatusResponse(
            available=current_status.available,
            authenticated=current_status.authenticated,
        )

    @router.post("/login", status_code=status.HTTP_202_ACCEPTED)
    def start_login() -> None:
        """사용자 브라우저에서 Codex 로그인 흐름을 시작합니다."""
        try:
            client.start_login()
        except CodexUnavailableError as error:
            raise HTTPException(status_code=503, detail="codex_unavailable") from error
        except CodexAuthenticationError as error:
            raise HTTPException(status_code=409, detail="codex_login_failed") from error

    @router.post("/narratives", response_model=NarrativesResponse)
    def create_narratives(report: AnalysisReport) -> NarrativesResponse:
        """리포트 finding을 검증된 선택적 LLM 서술로 변환합니다."""
        current_status = client.status()
        if not current_status.available:
            raise HTTPException(status_code=503, detail="codex_unavailable")
        if not current_status.authenticated:
            raise HTTPException(status_code=401, detail="codex_unauthenticated")
        try:
            return NarrativesResponse(narratives=narrate(report, client=client))
        except CodexGenerationError as error:
            raise HTTPException(status_code=502, detail="codex_generation_failed") from error

    app.include_router(router)
    return app

