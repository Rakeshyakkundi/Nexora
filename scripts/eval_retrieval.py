"""Retrieval quality eval for backend/rag/retriever.py.

Runs a small hand-labeled set of (query, expected_source, expected_section)
cases against the live Chroma collection and scores precision/recall-style
metrics, so a change to the embedder, chunker, or knowledge base that
silently degrades retrieval gets caught instead of discovered in production.

Usage:
    python3 scripts/eval_retrieval.py

Exits non-zero if hit-rate falls below the thresholds in main().
"""

import sys

from backend.rag.ingest import ensure_knowledge_base_ingested
from backend.rag.retriever import query_knowledge_base

# One labeled query per knowledge-base section (32 sections -> 32 cases),
# phrased the way a product owner's change description would actually read,
# not as a copy of the section heading - this is what makes it a retrieval
# eval and not just an embedding-similarity-to-itself check.
LABELED_QUERIES = [
    ("What is the purpose of our AML program and why does it exist?", "01_aml_program_overview.md", "Purpose"),
    ("What are the four pillars of an AML compliance program?", "01_aml_program_overview.md", "Four Pillars"),
    ("Launching a new instant payment product, what AML risks should we consider?", "01_aml_program_overview.md", "New Product and Change Risk Considerations"),
    ("Who do we escalate to when a change introduces an AML control gap?", "01_aml_program_overview.md", "Escalation"),
    ("What is required for basic customer identity verification at account opening?", "02_kyc_cdd_edd.md", "KYC Baseline"),
    ("What risk factors go into a customer due diligence risk profile?", "02_kyc_cdd_edd.md", "Customer Due Diligence (CDD)"),
    ("Which customers require enhanced due diligence and senior approval?", "02_kyc_cdd_edd.md", "Enhanced Due Diligence (EDD)"),
    ("We are onboarding a new customer segment, do we need to update our due diligence questionnaire?", "02_kyc_cdd_edd.md", "Relevance to New Product / Change Assessments"),
    ("Which sanctions lists must the bank screen against?", "03_sanctions_screening.md", "Regulatory Basis"),
    ("At what points in the customer lifecycle does sanctions screening need to happen?", "03_sanctions_screening.md", "Screening Points"),
    ("Launching a new cross-border payment corridor, what sanctions screening gaps are common?", "03_sanctions_screening.md", "Common Gaps Introduced by New Products or Corridors"),
    ("What should a risk assessment document about sanctions screening coverage for a new corridor?", "03_sanctions_screening.md", "Risk Assessment Expectations"),
    ("When is a financial crime risk assessment mandatory before launch?", "04_new_product_risk_assessment_framework.md", "When This Framework Applies"),
    ("What sections does a complete risk assessment document need to cover?", "04_new_product_risk_assessment_framework.md", "Assessment Structure"),
    ("What signals indicate a change should be rated High risk versus Low risk?", "04_new_product_risk_assessment_framework.md", "Risk Rating Heuristics"),
    ("What are the possible committee decisions on a risk assessment?", "04_new_product_risk_assessment_framework.md", "Committee Decision Outcomes"),
    ("Which vendors or third parties fall under third-party risk requirements?", "05_third_party_vendor_risk.md", "Scope"),
    ("What due diligence do we need to do before onboarding a new vendor?", "05_third_party_vendor_risk.md", "Due Diligence Expectations"),
    ("How often should we re-assess an existing vendor relationship?", "05_third_party_vendor_risk.md", "Ongoing Monitoring"),
    ("A new vendor will be doing transaction origination for us, what should the assessment document?", "05_third_party_vendor_risk.md", "Relevance to Change Assessments"),
    ("Why are cross-border transfers considered higher risk than domestic payments?", "06_cross_border_payments_risk.md", "Why Cross-Border Payments Are Higher Risk"),
    ("What corridor-specific risk factors matter for cross-border payments?", "06_cross_border_payments_risk.md", "Key Risk Factors"),
    ("What controls are typically required for cross-border payment corridors?", "06_cross_border_payments_risk.md", "Controls Typically Required"),
    ("How should we rate the risk of a new instant cross-border transfer feature?", "06_cross_border_payments_risk.md", "Assessment Guidance"),
    ("When are we required to file a Suspicious Activity Report?", "07_sar_filing.md", "Purpose"),
    ("What are common red flags that indicate suspicious account activity?", "07_sar_filing.md", "Suspicious Activity Indicators"),
    ("What is the process for deciding whether to file a SAR?", "07_sar_filing.md", "SAR Process Requirements"),
    ("Could a new product change create activity patterns our SAR monitoring would miss?", "07_sar_filing.md", "Relevance to New Product / Change Assessments"),
    ("What is the purpose of assigning customers a risk tier?", "08_customer_risk_segmentation.md", "Purpose"),
    ("What factors determine whether a customer is Low, Medium, or High risk?", "08_customer_risk_segmentation.md", "Segmentation Factors"),
    ("What extra requirements apply to high-risk tier customers?", "08_customer_risk_segmentation.md", "Segment-Specific Requirements"),
    ("We're opening the product to gig-economy workers, how should we segment that new customer type?", "08_customer_risk_segmentation.md", "Relevance to New Customer Segments"),
]


def evaluate(k: int = 3) -> dict:
    hits_at_1 = 0
    hits_at_k_source = 0
    hits_at_k_exact = 0
    rows = []

    for query, expected_source, expected_section in LABELED_QUERIES:
        matches = query_knowledge_base(query, k=k)
        sources = [m["source"] for m in matches]
        pairs = [(m["source"], m["section"]) for m in matches]

        hit_1 = bool(sources) and sources[0] == expected_source
        hit_k_source = expected_source in sources
        hit_k_exact = (expected_source, expected_section) in pairs

        hits_at_1 += hit_1
        hits_at_k_source += hit_k_source
        hits_at_k_exact += hit_k_exact

        rows.append(
            {
                "query": query,
                "expected": f"{expected_source} / {expected_section}",
                "hit_at_1": hit_1,
                "hit_at_k_source": hit_k_source,
                "hit_at_k_exact": hit_k_exact,
                "top_match": f"{sources[0]} / {matches[0]['section']}" if matches else None,
            }
        )

    n = len(LABELED_QUERIES)
    return {
        "k": k,
        "n": n,
        "hit_rate_at_1": hits_at_1 / n,
        "hit_rate_at_k_source": hits_at_k_source / n,
        "hit_rate_at_k_exact_section": hits_at_k_exact / n,
        "rows": rows,
    }


def main() -> None:
    ensure_knowledge_base_ingested()

    k = 3
    result = evaluate(k=k)

    for row in result["rows"]:
        status = "OK" if row["hit_at_k_source"] else "FAIL"
        print(f"[{status}] \"{row['query']}\"")
        print(f"       expected: {row['expected']} | top match: {row['top_match']}")

    print()
    print(f"n={result['n']}  k={k}")
    print(f"hit_rate@1 (exact source):        {result['hit_rate_at_1']:.0%}")
    print(f"hit_rate@{k} (source in top-{k}):      {result['hit_rate_at_k_source']:.0%}")
    print(f"hit_rate@{k} (exact source+section): {result['hit_rate_at_k_exact_section']:.0%}")

    # Thresholds are deliberately lenient (this is a 32-query hand-labeled
    # set over a small corpus, not a statistically rigorous benchmark) - the
    # point is to catch a regression (e.g. an embedder swap or chunking bug
    # that tanks retrieval), not to chase a perfect score.
    threshold = 0.80
    if result["hit_rate_at_k_source"] < threshold:
        print(f"\nFAIL: hit_rate@{k} ({result['hit_rate_at_k_source']:.0%}) is below the {threshold:.0%} threshold.")
        sys.exit(1)

    print("\nRetrieval quality eval passed.")


if __name__ == "__main__":
    main()
