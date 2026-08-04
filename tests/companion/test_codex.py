"""로컬 Codex CLI 어댑터의 안전한 실행 경계를 검증합니다."""

from dataclasses import dataclass

import pytest

from proofread.companion.codex import CodexCli, CodexGenerationError


@dataclass
class CommandResult:
    """가짜 Codex 명령의 종료 결과입니다."""

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class FakeRunner:
    """명령 인자와 표준 입력을 기록하는 테스트용 실행기입니다."""

    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.arguments: list[str] = []
        self.input_text: str | None = None

    def run(self, arguments: list[str], *, input_text: str | None = None) -> CommandResult:
        self.arguments = arguments
        self.input_text = input_text
        return self.result


def test_generate_runs_codex_in_read_only_temporary_directory() -> None:
    """서술 생성은 임시 폴더의 read-only Codex 실행만 사용합니다."""
    runner = FakeRunner(
        CommandResult(
            stdout='[{"finding_code":"missing_tests","message":"테스트를 추가하세요."}]'
        )
    )

    result = CodexCli(runner=runner).generate(
        [{"finding_code": "missing_tests", "priority": "high", "evidence": ["tests/"]}]
    )

    assert result == [{"finding_code": "missing_tests", "message": "테스트를 추가하세요."}]
    assert runner.arguments[:4] == ["codex", "exec", "--sandbox", "read-only"]
    assert "--skip-git-repo-check" in runner.arguments
    assert "--ephemeral" in runner.arguments
    assert "-C" in runner.arguments
    assert runner.input_text is not None
    assert "missing_tests" in runner.input_text
    assert "repository_url" not in runner.input_text


def test_generate_rejects_non_list_json() -> None:
    """Codex가 JSON 배열이 아닌 응답을 내면 서술 생성만 실패합니다."""
    runner = FakeRunner(CommandResult(stdout="not json"))

    with pytest.raises(CodexGenerationError):
        CodexCli(runner=runner).generate([])

