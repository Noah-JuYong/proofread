"""localhost Codex 동반 프로세스의 HTTP 계약을 검증합니다."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from proofread.companion.app import create_companion_app
from proofread.domain.models import (
    AnalysisReport,
    AssessmentCategory,
    CategoryScore,
    Finding,
    Priority,
)


@dataclass(frozen=True)
class FakeStatus:
    available: bool
    authenticated: bool


class FakeCodex:
    def __init__(self, *, available: bool = True, authenticated: bool = True) -> None:
        self._status = FakeStatus(available, authenticated)
        self.login_started = False

    def status(self) -> FakeStatus:
        return self._status

    def start_login(self) -> None:
        self.login_started = True

    def generate(self, payload: list[dict[str, object]]) -> list[dict[str, str]]:
        return [{"finding_code": payload[0]["finding_code"], "message": "테스트를 추가하세요."}]


@pytest.mark.anyio
async def test_status_reports_authenticated_local_codex() -> None:
    """허용된 localhost 화면은 CLI 설치·로그인 상태를 받습니다."""
    app = create_companion_app(codex=FakeCodex())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/v1/codex/status", headers={"Origin": "http://localhost:8000"}
        )

    assert response.json() == {"available": True, "authenticated": True}
    assert response.headers["access-control-allow-origin"] == "http://localhost:8000"


@pytest.mark.anyio
async def test_login_starts_for_installed_codex() -> None:
    """로그인 버튼은 로컬 Codex CLI 로그인만 시작합니다."""
    codex = FakeCodex()
    app = create_companion_app(codex=codex)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/codex/login")

    assert response.status_code == 202
    assert codex.login_started is True


@pytest.mark.anyio
async def test_narratives_return_only_existing_finding_messages() -> None:
    """동반 API도 narrator의 finding 코드 검증을 유지합니다."""
    app = create_companion_app(codex=FakeCodex())
    transport = httpx.ASGITransport(app=app)
    report = AnalysisReport(
        categories={AssessmentCategory.DATA_FLOW: CategoryScore(score=0)},
        findings=[
            Finding(
                code="missing_tests",
                category=AssessmentCategory.DATA_FLOW,
                priority=Priority.HIGH,
                message="테스트 근거가 부족합니다.",
                recommendation="테스트를 추가하세요.",
            )
        ]
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/v1/codex/narratives", json=report.model_dump(mode="json"))

    assert response.status_code == 200
    assert response.json() == {"narratives": ["테스트를 추가하세요."]}


def test_project_declares_local_companion_command() -> None:
    """패키지는 localhost 동반 프로세스 실행 명령을 제공합니다."""
    project = tomllib.loads(Path("pyproject.toml").read_text())

    assert project["project"]["scripts"]["proofread-codex-companion"] == (
        "proofread.companion.cli:main"
    )
