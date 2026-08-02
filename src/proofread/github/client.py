"""GitHub REST API의 인증·오류 경계를 제공합니다.

이 모듈은 공개 저장소 메타데이터를 요청하고 안전한 도메인 오류로 변환합니다.
수집 결과를 평가 profile로 정규화하는 일은 collector 모듈의 책임입니다.
"""

import os
from collections.abc import Mapping

import httpx

from proofread.github.errors import GitHubUnavailable, RateLimited, RepositoryNotFound


class GitHubClient:
    """공개 GitHub REST API에 인증 헤더를 선택적으로 붙여 요청합니다."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "proofread"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url="https://api.github.com", headers=headers, timeout=10.0
        )

    def __enter__(self) -> "GitHubClient":
        """컨텍스트 관리자에서 사용할 클라이언트를 반환합니다."""
        return self

    def __exit__(self, *_: object) -> None:
        """이 인스턴스가 만든 HTTP 클라이언트만 닫습니다."""
        if self._owns_client:
            self._client.close()

    def get_json(self, path: str, *, params: Mapping[str, str] | None = None) -> object:
        """JSON 응답을 가져오고 GitHub 실패를 도메인 오류로 변환합니다."""
        response = self._client.get(path, params=params)
        self._raise_for_error(response)
        return response.json()

    def get_text(self, path: str) -> str:
        """텍스트 응답을 가져오고 GitHub 실패를 도메인 오류로 변환합니다."""
        response = self._client.get(path, headers={"Accept": "application/vnd.github.raw+json"})
        self._raise_for_error(response)
        return response.text

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code == 404:
            raise RepositoryNotFound("The public repository was not found.")
        if response.status_code == 429 or (
            response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise RateLimited("GitHub API rate limit reached.")
        if response.status_code >= 500:
            raise GitHubUnavailable("GitHub API is temporarily unavailable.")
        raise GitHubUnavailable("GitHub API request failed.")
