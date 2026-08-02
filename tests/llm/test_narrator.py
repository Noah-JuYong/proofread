"""LLM 서술이 규칙 리포트의 근거 경계를 지키는지 검증합니다."""

from proofread.domain.evaluator import evaluate
from proofread.domain.models import RepositoryProfile
from proofread.llm.narrator import narrate


class FakeLlmClient:
    """LLM 입력과 구조화 응답을 테스트에서 고정합니다."""

    def __init__(self, response: list[dict[str, str]]) -> None:
        self.response = response
        self.payload: list[dict[str, object]] | None = None

    def generate(self, payload: list[dict[str, object]]) -> list[dict[str, str]]:
        self.payload = payload
        return self.response


def test_narrate_accepts_only_existing_finding_codes() -> None:
    """LLM은 finding 코드·우선순위·근거만 받고 존재하는 finding만 서술합니다."""
    report = evaluate(
        RepositoryProfile(
            repository_url="https://github.com/acme/pipeline",
            paths={
                ".github/workflows/ci.yml",
                "pipelines/ingest_events.py",
                "tests/test_pipeline.py",
            },
        )
    )
    client = FakeLlmClient(
        [
            {
                "finding_code": "undocumented_test_signal",
                "message": "README에 검증 방법을 추가하세요.",
            }
        ]
    )

    narratives = narrate(report, client=client)

    assert narratives == ["README에 검증 방법을 추가하세요."]
    assert client.payload == [
        {
            "finding_code": "undocumented_test_signal",
            "priority": "high",
            "evidence": [".github/workflows/ci.yml", "tests/test_pipeline.py"],
        }
    ]


def test_narrate_drops_invalid_responses_and_falls_back_on_error() -> None:
    """잘못된 응답과 LLM 호출 실패는 규칙 리포트를 깨지 않고 빈 서술로 끝납니다."""
    report = evaluate(RepositoryProfile(repository_url="https://github.com/acme/empty"))
    client = FakeLlmClient([{"finding_code": "invented", "message": "근거 없는 주장"}])

    assert narrate(report, client=client) == []
    assert narrate(report, client=None) == []
