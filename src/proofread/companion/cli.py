"""Proofread의 localhost Codex 동반 프로세스를 실행합니다.

이 모듈은 브라우저에서 직접 로그인한 사용자의 로컬 Codex CLI에만 연결합니다. Docker
서비스를 실행하거나 OAuth 자격 증명을 읽어 저장하는 책임은 맡지 않습니다.
"""

import uvicorn

from proofread.companion.app import create_companion_app


def main() -> None:
    """localhost 전용 동반 API를 시작합니다."""
    uvicorn.run(create_companion_app(), host="127.0.0.1", port=8751)

