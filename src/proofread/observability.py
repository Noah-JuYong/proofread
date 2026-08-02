"""Proofread 분석 서비스의 비밀 없는 기본 계측을 구성합니다.

이 모듈은 API와 워커가 사용할 서비스 식별자와 집계 메트릭만 제공합니다. URL, 토큰,
README 원문과 LLM 요청 본문 같은 사용자 입력은 계측 속성으로 기록하지 않습니다.
"""

from fastapi import FastAPI
from opentelemetry import metrics


class Observability:
    """안전한 집계 분석 메트릭을 기록합니다."""

    def __init__(self) -> None:
        meter = metrics.get_meter("proofread")
        self._created = meter.create_counter("proofread.analyses.created")

    def record_created(self) -> None:
        """새 분석 요청 한 건을 URL 라벨 없이 기록합니다."""
        self._created.add(1)


def configure_observability(app: FastAPI) -> None:
    """앱에 안정적인 서비스 이름과 안전한 집계 계측기를 등록합니다."""
    app.state.service_name = "proofread"
    app.state.observability = Observability()
