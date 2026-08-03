"""로컬 Docker Compose 실행 명령의 회귀를 방지합니다."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_commands_skip_dependency_sync() -> None:
    """컨테이너는 빌드된 의존성을 재동기화하지 않고 시작합니다."""
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text()
    compose = (PROJECT_ROOT / "compose.yaml").read_text()

    assert 'CMD ["uv", "run", "--no-sync", "uvicorn"' in dockerfile
    assert 'command: ["uv", "run", "--no-sync", "dramatiq", "proofread.worker"]' in compose
