import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from backend.agents.assessor import run_assessment
from backend.agents.scope_guard import check_scope
from backend.config import BANK_PROFILE
from backend.llm.client import complete, extract_json
from backend.llm.mock_llm import mock_judge
from backend.models import AgentResult, Case, CaseResult, JudgeVerdict
from backend.rag.retriever import query_knowledge_base

ASSESSOR_SLOTS = ["agent1", "agent2", "agent3"]

_JUDGE_SYSTEM_PROMPT = (
    BANK_PROFILE
    + "\n\n"
    + """You are the senior FCRM reviewer. You are given three independent risk \
assessments of the same proposed change, each produced by a different analyst/model. Compare \
them and decide the single best final assessment.

Respond with ONLY a single JSON object, no prose, no markdown fences, matching exactly this \
schema:
{
  "risk_rating": "Low" | "Medium" | "High",
  "recommendation": "approve" | "approve_with_conditions" | "reject",
  "summary": "<2-3 sentence final summary for the reviewer>",
  "conditions": ["<condition>", ...],
  "chosen_agent": "<the agent id whose reasoning you found most reliable, e.g. agent1>",
  "rationale": "<why you picked this outcome over the others>"
}
"conditions" must be [] when recommendation is "approve\""""
)


def _format_verdict(verdict: JudgeVerdict) -> str:
    """Human-readable rendering of the judge's structured verdict - shown to
    end users in the Agent tab instead of the raw JSON the model returns.
    """
    lines = [verdict.summary, "", f"Rationale: {verdict.rationale}"]
    if verdict.chosen_agent:
        lines.append(f"Most reliable child agent: {verdict.chosen_agent}")
    if verdict.conditions:
        lines.append("")
        lines.append("Conditions:")
        lines.extend(f"- {c}" for c in verdict.conditions)
    return "\n".join(lines)


def _build_judge_prompt(case: Case, agent_results: list[AgentResult]) -> str:
    blocks = []
    for result in agent_results:
        assessment = result.assessment
        blocks.append(
            f"{result.agent} [{result.provider}/{result.model}]: "
            f"risk_rating={assessment.risk_rating}, recommendation={assessment.recommendation}, "
            f"summary={assessment.summary}, rationale={assessment.rationale}"
        )
    return (
        f"Change title: {case.title}\n"
        f"Change type: {case.change_type}\n"
        f"Description: {case.description}\n\n"
        f"Independent assessments:\n" + "\n".join(blocks)
    )


def _out_of_scope_results(reason: str) -> tuple[list[AgentResult], CaseResult]:
    """Short-circuit: none of the 3 child agents or the judge are called -
    the scope guardrail keeps this pipeline running for this bank's FCRM
    change-risk problem only, not as a general-purpose LLM endpoint.
    """
    skip_output = f"Skipped: submission is out of scope for this FCRM workbench. {reason}"

    skipped_agents = [
        AgentResult(agent=slot, role="Independent assessment", status="skipped", output=skip_output)
        for slot in ASSESSOR_SLOTS
    ]
    master = AgentResult(agent="master_agent", role="Judge", status="skipped", output=skip_output)

    result = CaseResult(
        risk_rating=None,
        summary=reason,
        recommendation="reject",
        conditions=[],
        out_of_scope=True,
        scope_reason=reason,
    )

    return [*skipped_agents, master], result


def run_pipeline(case: Case) -> tuple[list[AgentResult], CaseResult]:
    in_scope, scope_reason = check_scope(case)
    if not in_scope:
        return _out_of_scope_results(scope_reason)

    query_text = f"{case.title} {case.description} {' '.join(case.filenames)}"
    sources = query_knowledge_base(query_text)

    with ThreadPoolExecutor(max_workers=len(ASSESSOR_SLOTS)) as pool:
        agent_results = list(pool.map(lambda slot: run_assessment(case, sources, slot), ASSESSOR_SLOTS))

    assessments_by_slot = {r.agent: r.assessment.model_dump() for r in agent_results}

    judge_started_at = time.perf_counter()
    judge_result = complete(
        slot="master_agent",
        system=_JUDGE_SYSTEM_PROMPT,
        user=_build_judge_prompt(case, agent_results),
        mock_fn=lambda: str(mock_judge(assessments_by_slot)),
    )
    judge_duration_ms = round((time.perf_counter() - judge_started_at) * 1000)

    verdict = None
    if judge_result.mode == "live":
        parsed = extract_json(judge_result.text)
        if parsed:
            try:
                verdict = JudgeVerdict.model_validate(parsed)
            except ValueError:
                verdict = None

    judge_mode = judge_result.mode if verdict is not None else "mock"
    if verdict is None:
        verdict = JudgeVerdict.model_validate(mock_judge(assessments_by_slot))
        judge_provider, judge_model = "mock", "mock"
    else:
        judge_provider, judge_model = judge_result.provider, judge_result.model

    if verdict.recommendation == "approve":
        verdict.conditions = []

    judge_output = _format_verdict(verdict)

    votes = dict(Counter(r.assessment.risk_rating for r in agent_results))
    confidence = round(100 * max(votes.values()) / len(agent_results))

    master = AgentResult(
        agent="master_agent",
        role="Judge",
        status="done",
        output=judge_output,
        provider=judge_provider,
        model=judge_model,
        mode=judge_mode,
        duration_ms=judge_duration_ms,
    )

    result = CaseResult(
        risk_rating=verdict.risk_rating,
        summary=verdict.summary,
        recommendation=verdict.recommendation,
        conditions=verdict.conditions,
        chosen_agent=verdict.chosen_agent,
        judge_rationale=verdict.rationale,
        votes=votes,
        confidence=confidence,
        judge_mode=judge_mode,
    )

    return [*agent_results, master], result
