"""GitHub 수집 과정에서 호출자에게 노출할 안전한 오류를 정의합니다."""


class GitHubCollectionError(RuntimeError):
    """인증 정보 없이 수집 실패 원인을 전달하는 기반 오류입니다."""

    code = "github_collection_error"
    retryable = False


class InvalidRepositoryUrl(GitHubCollectionError):
    """분석 대상이 공개 GitHub 저장소 URL 형식이 아닐 때 발생합니다."""

    code = "invalid_repository_url"


class RepositoryNotFound(GitHubCollectionError):
    """GitHub가 공개 저장소를 찾지 못했을 때 발생합니다."""

    code = "repository_not_found"


class RateLimited(GitHubCollectionError):
    """GitHub 호출 한도 초과로 작업 재시도가 필요할 때 발생합니다."""

    code = "github_rate_limited"
    retryable = True


class GitHubUnavailable(GitHubCollectionError):
    """일시적 GitHub 오류가 발생해 작업 재시도가 필요할 때 발생합니다."""

    code = "github_unavailable"
    retryable = True
