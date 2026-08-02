"""GitHub 공개 메타데이터 수집 계약을 HTTP fixture로 검증합니다."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from proofread.github.collector import collect_public_repository
from proofread.github.errors import InvalidRepositoryUrl, RateLimited, RepositoryNotFound

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text())


def test_collect_public_repository_builds_profile() -> None:
    """수집기는 저장소 메타데이터를 평가기가 쓰는 profile로 정규화합니다."""
    base = "https://api.github.com/repos/acme/pipeline"
    with respx.mock(assert_all_called=True) as mock:
        mock.get(base).mock(return_value=httpx.Response(200, json=_fixture("repository.json")))
        mock.get(f"{base}/git/trees/main", params={"recursive": "1"}).mock(
            return_value=httpx.Response(200, json=_fixture("tree.json"))
        )
        mock.get(f"{base}/readme").mock(
            return_value=httpx.Response(200, text="# Pipeline\n\n## Testing\n\nRun pytest.")
        )
        mock.get(f"{base}/languages").mock(return_value=httpx.Response(200, json={"Python": 1280}))

        profile = collect_public_repository("https://github.com/acme/pipeline")

    assert profile.paths == {
        ".github/workflows/ci.yml",
        "README.md",
        "pipelines/ingest_events.py",
        "tests/test_pipeline.py",
    }
    assert profile.readme_sections == {"pipeline", "testing"}
    assert profile.languages == {"Python": 1280}


def test_collect_public_repository_rejects_non_github_url() -> None:
    """공개 GitHub 저장소 형식이 아닌 URL은 HTTP 호출 전에 거절합니다."""
    with pytest.raises(InvalidRepositoryUrl):
        collect_public_repository("https://example.com/acme/pipeline")


@respx.mock
def test_collect_public_repository_raises_not_found() -> None:
    """404 저장소는 재시도하지 않는 명시적 오류로 변환합니다."""
    respx.get("https://api.github.com/repos/acme/missing").mock(return_value=httpx.Response(404))

    with pytest.raises(RepositoryNotFound):
        collect_public_repository("https://github.com/acme/missing")


@respx.mock
def test_collect_public_repository_marks_rate_limit_retryable() -> None:
    """GitHub rate limit은 인증 정보 없이 재시도 가능한 오류로 변환합니다."""
    respx.get("https://api.github.com/repos/acme/pipeline").mock(
        return_value=httpx.Response(403, headers={"x-ratelimit-remaining": "0"})
    )

    with pytest.raises(RateLimited) as raised:
        collect_public_repository("https://github.com/acme/pipeline")

    assert raised.value.retryable is True
    assert "token" not in str(raised.value).lower()
