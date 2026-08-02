"""Proofread HTTP 애플리케이션의 진입점입니다.

이 모듈은 공개 GitHub 저장소 분석 파이프라인에서 요청 접수와 결과 제공 구간을
담당합니다. GitHub 수집, 규칙 평가, 비동기 작업 실행과 리포트 저장은 인접한
전용 모듈의 책임이며 이 모듈은 HTTP 계약만 제공합니다.
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Proofread의 HTTP 애플리케이션을 생성합니다."""
    app = FastAPI(title="Proofread")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """프로세스가 요청을 처리할 수 있음을 반환합니다."""
        return {"status": "ok"}

    return app
