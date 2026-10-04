"""Intake gatekeeper. Runs before any of the three child agents or the
master agent - decides whether a submission is actually a bank change-risk
question this workbench exists to assess, so the LLM ensemble only ever
runs for that specific business problem.
"""

from backend.config import BANK_PROFILE
from backend.llm.client import complete, extract_json
from backend.llm.mock_llm import mock_scope_check
from backend.models import Case

_SYSTEM_PROMPT = f"""{BANK_PROFILE}

You are the intake gatekeeper for this bank's Financial Crimes Risk Management (FCRM) \
change-review workbench. This workbench exists ONLY to assess financial-crime risk (money \
laundering, sanctions, fraud, terrorist financing, bribery/corruption exposure) for proposed \
changes to the bank's own products, features, vendors, geographies, customer segments, or \
internal processes across consumer banking, commercial banking, payments, and wealth management.

Given a submitted change request, decide whether it is in scope for this workbench.

Respond with ONLY a single JSON object, no prose, no markdown fences:
{{"in_scope": true|false, "reason": "<one sentence>"}}

Mark in_scope=false for anything that is not a plausible bank product/process/vendor/geography/\
customer-segment change - e.g. requests unrelated to banking or financial crime, personal \
requests, or requests to have the assistant do something else entirely."""


def _build_user_prompt(case: Case) -> str:
    return f"Title: {case.title}\nChange type: {case.change_type}\nDescription: {case.description}"


def check_scope(case: Case) -> tuple[bool, str]:
    result = complete(
        slot="scope_guard",
        system=_SYSTEM_PROMPT,
        user=_build_user_prompt(case),
        mock_fn=lambda: str(mock_scope_check(case.title, case.change_type, case.description)),
    )

    if result.mode == "live":
        parsed = extract_json(result.text)
    else:
        parsed = mock_scope_check(case.title, case.change_type, case.description)

    if not parsed or "in_scope" not in parsed:
        parsed = mock_scope_check(case.title, case.change_type, case.description)

    return bool(parsed["in_scope"]), str(parsed.get("reason", "")).strip()
