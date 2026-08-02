"""서비스 관측성의 공개 식별자 설정을 검증합니다."""

from fastapi import FastAPI

from proofread.observability import configure_observability


def test_configure_observability_registers_service_name() -> None:
    """메트릭 리소스는 안정적인 proofread 서비스 이름을 사용합니다."""
    app = FastAPI()

    configure_observability(app)

    assert app.state.service_name == "proofread"
