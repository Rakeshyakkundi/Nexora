from datetime import datetime
from typing import Literal

from pydantic import BaseModel

CaseStatus = Literal["submitted", "running", "complete"]
DecisionStatus = Literal["pending", "approved", "rejected"]
AgentStatus = Literal["queued", "processing", "done", "skipped"]
RiskRating = Literal["Low", "Medium", "High"]
Recommendation = Literal["approve", "approve_with_conditions", "reject"]


class KnowledgeSource(BaseModel):
    source: str
    section: str


class Assessment(BaseModel):
    risk_rating: RiskRating
    recommendation: Recommendation
    summary: str
    conditions: list[str] = []
    rationale: str = ""
    confidence: int | None = None


class JudgeVerdict(BaseModel):
    risk_rating: RiskRating
    recommendation: Recommendation
    summary: str
    conditions: list[str] = []
    chosen_agent: str
    rationale: str = ""


class LLMResult(BaseModel):
    text: str
    provider: str
    model: str
    mode: Literal["live", "mock"]


class AgentResult(BaseModel):
    agent: str
    role: str
    status: AgentStatus
    output: str
    sources: list[KnowledgeSource] = []
    provider: str = "mock"
    model: str = ""
    mode: Literal["live", "mock"] = "mock"
    assessment: Assessment | None = None
    duration_ms: int | None = None


class CaseResult(BaseModel):
    risk_rating: RiskRating | None = None
    summary: str
    recommendation: Recommendation
    conditions: list[str] = []
    chosen_agent: str | None = None
    judge_rationale: str | None = None
    votes: dict[str, int] = {}
    confidence: int | None = None
    judge_mode: Literal["live", "mock"] = "mock"
    out_of_scope: bool = False
    scope_reason: str | None = None


class Case(BaseModel):
    id: str
    title: str
    change_type: str
    description: str
    filenames: list[str]
    status: CaseStatus
    decision: DecisionStatus = "pending"
    created_at: datetime
    created_by: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    agent_results: dict[str, AgentResult] = {}
    result: CaseResult | None = None


class CaseCreateResponse(BaseModel):
    case_id: str
    status: CaseStatus
    title: str
    change_type: str
    description: str
    filenames: list[str]
    created_at: datetime
    created_by: str | None = None


class RunResponse(BaseModel):
    case_id: str
    status: CaseStatus
    agents: list[AgentResult]


class CaseDetailResponse(BaseModel):
    case_id: str
    title: str
    change_type: str
    description: str
    filenames: list[str]
    status: CaseStatus
    result: CaseResult | None
    decision: DecisionStatus
    created_at: datetime
    created_by: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]


class DecisionResponse(BaseModel):
    case_id: str
    decision: DecisionStatus
    decided_by: str | None = None
    decided_at: datetime | None = None


class CaseSummary(BaseModel):
    case_id: str
    title: str
    change_type: str
    status: CaseStatus
    risk_rating: RiskRating | None
    decision: DecisionStatus
    created_at: datetime
    created_by: str | None = None
    decided_by: str | None = None


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str


class AuthResponse(BaseModel):
    token: str
    username: str
    email: str


class MeResponse(BaseModel):
    username: str
    email: str
