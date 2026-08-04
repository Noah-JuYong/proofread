"""Proofread의 저장소 증거와 평가 결과 계약을 정의합니다.

이 모듈은 GitHub 수집 결과를 정규화한 뒤 규칙 평가기로 전달하는 구간을 담당합니다.
HTTP 요청 처리, GitHub 통신, 작업 저장과 LLM 문안 생성은 인접 모듈의 책임입니다.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, computed_field


class TargetRole(StrEnum):
    """Proofread가 지원하는 포트폴리오 대상 직무입니다."""

    DATA_ENGINEER = "data_engineer"
    INFRASTRUCTURE_ENGINEER = "infrastructure_engineer"
    AI_ENGINEER = "ai_engineer"


class AssessmentCategory(StrEnum):
    """직무별 포트폴리오 리포트가 사용하는 평가 축입니다."""

    DATA_FLOW = "data_flow"
    REPRODUCIBILITY = "reproducibility"
    QUALITY = "quality"
    OPERABILITY = "operability"
    RESULTS = "results"
    INFRASTRUCTURE_AS_CODE = "infrastructure_as_code"
    DELIVERY = "delivery"
    PLATFORM = "platform"
    OBSERVABILITY = "observability"
    SECURITY_OPERATIONS = "security_operations"
    DATA_FEATURES = "data_features"
    MODEL_DEVELOPMENT = "model_development"
    MODEL_EVALUATION = "model_evaluation"
    EXPERIMENT_REPRODUCIBILITY = "experiment_reproducibility"
    SERVING_MLOPS = "serving_mlops"


class Priority(StrEnum):
    """개선 과제의 사용자 우선순위입니다."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RepositoryProfile(BaseModel):
    """공개 저장소에서 수집해 평가에 쓰는 비밀 없는 신호입니다."""

    repository_url: str
    paths: set[str] = Field(default_factory=set)
    readme_sections: set[str] = Field(default_factory=set)
    readme_text: str = ""
    languages: dict[str, int] = Field(default_factory=dict)


class CategoryScore(BaseModel):
    """하나의 평가 축 점수와 확인된 신호입니다."""

    score: int = Field(ge=0, le=20)
    evidence: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    """사용자가 검증할 수 있는 개선 과제입니다."""

    code: str
    category: AssessmentCategory
    priority: Priority
    message: str
    recommendation: str
    evidence: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    """규칙 평가가 만든 전체 점수와 근거 기반 개선 과제입니다."""

    categories: dict[AssessmentCategory, CategoryScore]
    findings: list[Finding] = Field(default_factory=list)
    narratives: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def total_score(self) -> int:
        """다섯 평가 축의 합계 점수를 반환합니다."""
        return sum(score.score for score in self.categories.values())

    def score_for(self, category: AssessmentCategory) -> int:
        """요청한 평가 축의 점수를 반환합니다."""
        return self.categories[category].score
