import time

from backend.config import BANK_PROFILE
from backend.llm.client import complete, extract_json
from backend.llm.mock_llm import mock_assessment
from backend.models import Assessment, AgentResult, Case, KnowledgeSource

# Each child agent now runs on the same provider/model (Groq) - what makes
# them independent isn't a different provider anymore, it's a different
# specialist lens/scenario per the user's request: "all three should have
# their own prompt." Each still returns the same JSON schema so the judge
# can compare them uniformly.
SLOT_SPECIALISTS = {
    "agent1": {
        "role": "Sanctions & AML Typology Specialist",
        "framing": (
            "You are this bank's Sanctions & Anti-Money-Laundering (AML) Typology Specialist "
            "within the FCRM function. Your lens is money laundering, terrorist financing, and "
            "sanctions exposure specifically: layering/structuring risk, sanctioned-party or "
            "PEP exposure, and gaps in sanctions/AML screening coverage introduced by the "
            "proposed change."
        ),
    },
    "agent2": {
        "role": "Regulatory & Customer Due Diligence Specialist",
        "framing": (
            "You are this bank's Regulatory & Customer Due Diligence (CDD) Specialist within the "
            "FCRM function. Your lens is regulatory compliance and customer risk: KYC/CDD/EDD "
            "adequacy, customer risk segmentation, licensing/registration requirements, and "
            "SAR-filing readiness for the proposed change."
        ),
    },
    "agent3": {
        "role": "Third-Party & Geographic Risk Specialist",
        "framing": (
            "You are this bank's Third-Party, Vendor & Geographic Risk Specialist within the "
            "FCRM function. Your lens is operational and external exposure: third-party/vendor "
            "due diligence gaps, new-geography or cross-border corridor risk, and operational "
            "control gaps the proposed change introduces."
        ),
    },
}

_DEFAULT_FRAMING = (
    "You are one of this bank's Financial Crimes Risk Management (FCRM) analysts. Given a "
    "proposed business change and relevant internal policy excerpts, produce an independent "
    "risk assessment."
)

_RESPONSE_SCHEMA = """
Given a proposed business change and relevant internal policy excerpts, produce an independent \
risk assessment through your lens.

Respond with ONLY a single JSON object, no prose, no markdown fences, matching exactly this \
schema:
{
  "risk_rating": "Low" | "Medium" | "High",
  "recommendation": "approve" | "approve_with_conditions" | "reject",
  "summary": "<2-3 sentence summary of the assessment>",
  "conditions": ["<condition>", ...],
  "rationale": "<why you reached this rating>",
  "confidence": <integer 0-100, how confident you are in this rating given the information available>
}
"conditions" must be [] when recommendation is "approve\""""


def _system_prompt_for(slot: str) -> str:
    framing = SLOT_SPECIALISTS.get(slot, {}).get("framing", _DEFAULT_FRAMING)
    return BANK_PROFILE + "\n\n" + framing + "\n" + _RESPONSE_SCHEMA


def _role_for(slot: str) -> str:
    return SLOT_SPECIALISTS.get(slot, {}).get("role", "Independent assessment")


def _format_assessment(assessment: Assessment) -> str:
    """Human-readable rendering of a structured Assessment - the raw JSON
    the model returns is parsed into `assessment` for the app to use, but
    end users see this readable text instead in the Agent tab.
    """
    lines = [assessment.summary, "", f"Rationale: {assessment.rationale}"]
    if assessment.conditions:
        lines.append("")
        lines.append("Conditions:")
        lines.extend(f"- {c}" for c in assessment.conditions)
    return "\n".join(lines)


def _build_user_prompt(case: Case, sources: list[dict]) -> str:
    if sources:
        policy_block = "\n".join(f"- [{s['source']} / {s['section']}]: {s['text']}" for s in sources)
    else:
        policy_block = "(no closely matching internal policy article found)"

    filenames = ", ".join(case.filenames) if case.filenames else "none"
    return (
        f"Change title: {case.title}\n"
        f"Change type: {case.change_type}\n"
        f"Description: {case.description}\n"
        f"Supporting documents: {filenames}\n\n"
        f"Relevant internal FCRM policy excerpts:\n{policy_block}"
    )


def run_assessment(case: Case, sources: list[dict], slot: str) -> AgentResult:
    user_prompt = _build_user_prompt(case, sources)

    started_at = time.perf_counter()
    result = complete(
        slot=slot,
        system=_system_prompt_for(slot),
        user=user_prompt,
        mock_fn=lambda: str(mock_assessment(case.description, slot)),
    )
    duration_ms = round((time.perf_counter() - started_at) * 1000)

    parsed = extract_json(result.text) if result.mode == "live" else mock_assessment(case.description, slot)

    try:
        assessment = Assessment.model_validate(parsed) if parsed else None
    except ValueError:
        assessment = None

    if assessment is None:
        fallback = mock_assessment(case.description, slot)
        assessment = Assessment.model_validate(fallback)
        provider, model, mode = "mock", "mock", "mock"
    else:
        provider, model, mode = result.provider, result.model, result.mode

    output_text = _format_assessment(assessment)

    knowledge_sources = [KnowledgeSource(source=s["source"], section=s["section"]) for s in sources]

    return AgentResult(
        agent=slot,
        role=_role_for(slot),
        status="done",
        output=output_text,
        sources=knowledge_sources,
        provider=provider,
        model=model,
        mode=mode,
        assessment=assessment,
        duration_ms=duration_ms,
    )
