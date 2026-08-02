"""공개 GitHub 저장소를 평가용 profile로 정규화합니다.

이 모듈은 GitHub API에서 README, 파일 트리, 언어 통계를 수집해 ``RepositoryProfile``을
만듭니다. 점수화와 finding 생성은 domain evaluator, HTTP 요청·작업 저장은 인접 모듈의
책임입니다.
"""

import re
from urllib.parse import urlparse

from proofread.domain.models import RepositoryProfile
from proofread.github.client import GitHubClient
from proofread.github.errors import InvalidRepositoryUrl, RepositoryNotFound


def collect_public_repository(
    repository_url: str, *, client: GitHubClient | None = None
) -> RepositoryProfile:
    """공개 GitHub 저장소의 비밀 없는 신호를 수집해 정규화합니다."""
    owner, repository = _parse_repository_url(repository_url)
    api_path = f"/repos/{owner}/{repository}"
    if client is not None:
        return _collect(client, api_path, repository_url)
    with GitHubClient() as managed_client:
        return _collect(managed_client, api_path, repository_url)


def _collect(client: GitHubClient, api_path: str, repository_url: str) -> RepositoryProfile:
    repository_data = _as_mapping(client.get_json(api_path))
    default_branch = repository_data.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise RepositoryNotFound("The public repository has no default branch.")
    tree_data = _as_mapping(
        client.get_json(f"{api_path}/git/trees/{default_branch}", params={"recursive": "1"})
    )
    readme_text = client.get_text(f"{api_path}/readme")
    languages_data = _as_mapping(client.get_json(f"{api_path}/languages"))
    return RepositoryProfile(
        repository_url=repository_url,
        paths=_tree_paths(tree_data),
        readme_sections=_readme_sections(readme_text),
        readme_text=readme_text,
        languages={name: size for name, size in languages_data.items() if isinstance(size, int)},
    )


def _parse_repository_url(repository_url: str) -> tuple[str, str]:
    parsed = urlparse(repository_url)
    path_parts = tuple(part for part in parsed.path.split("/") if part)
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "github.com"
        or len(path_parts) != 2
        or parsed.query
        or parsed.fragment
    ):
        raise InvalidRepositoryUrl(
            "A public https://github.com/{owner}/{repository} URL is required."
        )
    return path_parts[0], path_parts[1].removesuffix(".git")


def _as_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RepositoryNotFound("GitHub returned an invalid public repository response.")
    return value


def _tree_paths(tree_data: dict[str, object]) -> set[str]:
    tree = tree_data.get("tree")
    if not isinstance(tree, list):
        return set()
    return {
        item["path"]
        for item in tree
        if isinstance(item, dict)
        and item.get("type") == "blob"
        and isinstance(item.get("path"), str)
    }


def _readme_sections(readme_text: str) -> set[str]:
    return {
        match.group(1).strip().lower()
        for line in readme_text.splitlines()
        if (match := re.match(r"^#{1,6}\s+(.+?)\s*$", line))
    }
