"""규칙 기반 finding을 근거 범위 안의 사용자용 문안으로 변환합니다.

이 모듈은 이미 계산된 finding의 코드·우선순위·근거만 LLM 경계로 보냅니다. 점수 계산,
finding 생성, 제공자별 인증과 HTTP 통신은 각각 evaluator와 외부 LLM adapter의 책임입니다.
"""

from pydantic import BaseModel, ValidationError

from proofread.domain.models import AnalysisReport
from proofread.llm.client import LlmClient


class NarrativeResponse(BaseModel):
    """외부 LLM이 반환해야 하는 검증 가능한 서술 한 건입니다."""

    finding_code: str
    message: str


def narrate(report: AnalysisReport, *, client: LlmClient | None) -> list[str]:
    """유효한 finding만 참조하는 LLM 서술을 반환하고 모든 실패를 안전히 폴백합니다."""
    if client is None or not report.findings:
        return []
    payload = [
        {
            "finding_code": finding.code,
            "priority": finding.priority.value,
            "evidence": finding.evidence,
        }
        for finding in report.findings
    ]
    try:
        responses = client.generate(payload)
    except Exception:
        return []
    allowed_codes = {finding.code for finding in report.findings}
    messages: list[str] = []
    for response in responses:
        try:
            parsed = NarrativeResponse.model_validate(response)
        except ValidationError:
            continue
        if parsed.finding_code in allowed_codes and parsed.message.strip():
            messages.append(parsed.message.strip())
    return messages
