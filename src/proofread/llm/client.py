"""Proofread가 외부 LLM 제공자에 요구하는 최소 경계를 정의합니다."""

from typing import Protocol


class LlmClient(Protocol):
    """근거가 제한된 구조화 입력을 짧은 구조화 문안으로 변환합니다."""

    def generate(self, payload: list[dict[str, object]]) -> list[dict[str, str]]:
        """finding 코드와 근거만 받은 구조화 응답을 반환합니다."""
        ...
