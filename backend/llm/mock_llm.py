"""Deterministic mock LLM - the offline fallback and test harness.

Kept intentionally (not deleted) as the always-available fallback and test
path: every ensemble slot and the judge fall back here automatically when
their assigned provider has no API key or the live call fails (see
backend/llm/client.py). No network call, no API key, no randomness - given
the same case, always the same output. Each of the three child agents
applies a different severity nudge so their mock opinions genuinely
disagree, exercising the same majority-vote fallback path a real
disagreement would.
"""

from collections import Counter

RATING_ORDER = ["Low", "Medium", "High"]

HIGH_RISK_KEYWORDS = [
    "cross-border",
    "cross border",
    "sanction",
    "cash",
    "money service",
    "msb",
    "correspondent",
    "high-risk jurisdiction",
    "crypto",
    "cryptocurrency",
]

MEDIUM_RISK_KEYWORDS = [
    "vendor",
    "third-party",
    "third party",
    "new geography",
    "new segment",
    "onboarding",
    "pep",
    "non-resident",
]

# Per-slot severity nudge (in RATING_ORDER steps) so the mock ensemble's three
# opinions differ instead of being three identical answers.
_SLOT_NUDGE = {"agent1": 0, "agent2": -1, "agent3": 1}


def score_risk(text: str) -> tuple[str, list[str]]:
    """Deterministic keyword heuristic standing in for a real risk model."""
    lower = text.lower()

    high_hits = [kw for kw in HIGH_RISK_KEYWORDS if kw in lower]
    if high_hits:
        return "High", high_hits

    medium_hits = [kw for kw in MEDIUM_RISK_KEYWORDS if kw in lower]
    if medium_hits:
        return "Medium", medium_hits

    return "Low", []


def recommendation_for(rating: str, hits: list[str]) -> tuple[str, list[str]]:
    if rating == "Low":
        return "approve", []

    if rating == "Medium":
        return "approve_with_conditions", [
            "Confirm existing transaction monitoring scenarios cover the new activity pattern.",
            "Confirm CDD/EDD triggers are updated for any newly in-scope customer or geography.",
        ]

    # High
    if "sanction" in hits:
        return "reject", []

    return "approve_with_conditions", [
        "Update sanctions and EDD screening coverage before launch.",
        "Validate corridor/vendor-specific monitoring thresholds end-to-end prior to go-live.",
        "Escalate to BSA/AML Officer for sign-off before removing conditions.",
    ]


def mock_assessment(description: str, slot: str) -> dict:
    rating, hits = score_risk(description)
    idx = RATING_ORDER.index(rating) + _SLOT_NUDGE.get(slot, 0)
    rating = RATING_ORDER[max(0, min(2, idx))]
    recommendation, conditions = recommendation_for(rating, hits)

    reason = f"keyword signal(s): {', '.join(hits)}" if hits else "no elevated-risk keywords detected"
    # Deterministic self-reported confidence: fewer/no keyword hits reads as
    # a clearer-cut case (higher confidence); more hits means more competing
    # risk signals to weigh (lower confidence).
    confidence = max(55, 95 - 12 * len(hits))
    return {
        "risk_rating": rating,
        "recommendation": recommendation,
        "summary": f"[mock:{slot}] Draft risk rating: {rating} ({reason}).",
        "conditions": conditions,
        "rationale": f"Deterministic mock assessment ({reason}), slot severity nudge {_SLOT_NUDGE.get(slot, 0):+d}.",
        "confidence": confidence,
    }


# Generic, non-banking asks that have no business going through an FCRM
# change-risk workbench. Deliberately narrow (false negatives - letting an
# odd submission through to the real agents - are cheaper than false
# positives that block a legitimate bank change request).
OUT_OF_SCOPE_HINTS = [
    "poem",
    "recipe",
    "joke",
    "weather",
    "song",
    "lyrics",
    "story",
    "homework",
    "translate",
    "workout plan",
    "diet plan",
    "write code",
    "travel itinerary",
]


def mock_scope_check(title: str, change_type: str, description: str) -> dict:
    """Deterministic stand-in for the scope-guard LLM call: does this
    submission plausibly describe a bank product/feature/vendor/geography/
    customer-segment/process change worth an FCRM risk assessment?
    """
    text = f"{title} {change_type} {description}".lower().strip()

    if len(description.strip()) < 5:
        return {
            "in_scope": False,
            "reason": "Submission has no meaningful description to assess.",
        }

    hit = next((h for h in OUT_OF_SCOPE_HINTS if h in text), None)
    if hit:
        return {
            "in_scope": False,
            "reason": (
                f"Submission reads as unrelated to a bank product/process/vendor/geography/"
                f"customer-segment change (matched off-topic signal: '{hit}')."
            ),
        }

    return {
        "in_scope": True,
        "reason": "Submission plausibly describes a business change relevant to this bank's FCRM review.",
    }


def mock_judge(assessments: dict[str, dict]) -> dict:
    """Majority vote across the mock assessments, ties broken toward the
    more conservative (higher-risk) rating.
    """
    counts = Counter(a["risk_rating"] for a in assessments.values())
    top_count = max(counts.values())
    tied = [rating for rating, count in counts.items() if count == top_count]
    chosen_rating = max(tied, key=RATING_ORDER.index)
    chosen_slot = next(slot for slot, a in assessments.items() if a["risk_rating"] == chosen_rating)
    chosen = assessments[chosen_slot]

    return {
        "risk_rating": chosen_rating,
        "recommendation": chosen["recommendation"],
        "summary": chosen["summary"],
        "conditions": chosen["conditions"],
        "chosen_agent": chosen_slot,
        "rationale": (
            f"Majority vote across {len(assessments)} agents ({dict(counts)}); "
            f"selected {chosen_slot}'s {chosen_rating}-risk assessment as the consensus."
        ),
    }
