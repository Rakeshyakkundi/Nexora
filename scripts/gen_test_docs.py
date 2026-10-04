"""Generates sample "change request memo" PDFs for manually testing the
Risk Assessment Workbench's Upload flow across different risk scenarios.
Run once: python3 scripts/gen_test_docs.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

OUT_DIR = Path(__file__).resolve().parent.parent / "test-data"
OUT_DIR.mkdir(exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle("MemoTitle", parent=styles["Title"], fontSize=18, spaceAfter=4)
label_style = ParagraphStyle("Label", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10)
body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10.5, leading=15)
section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12, spaceBefore=14, spaceAfter=6)


def build_memo(filename: str, title: str, change_type: str, submitted_by: str, date: str, description: str):
    path = OUT_DIR / filename
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
    )

    story = [
        Paragraph("Change Request Memo", title_style),
        Paragraph("Risk Assessment Workbench &mdash; Product Owner Submission", styles["Italic"]),
        Spacer(1, 16),
    ]

    field_table = Table(
        [
            ["Title:", title],
            ["Change Type:", change_type],
            ["Submitted By:", submitted_by],
            ["Date:", date],
        ],
        colWidths=[1.4 * inch, 4.6 * inch],
    )
    field_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(field_table)

    story.append(Paragraph("Description", section_style))
    story.append(Paragraph(description, body_style))

    doc.build(story)
    return path


memos = [
    dict(
        filename="01_high_risk_cross_border.pdf",
        title="Launch Instant Cross-Border Remittance Corridor to West Africa",
        change_type="New Product",
        submitted_by="J. Alvarez, Consumer Payments Product",
        date="2026-09-26",
        description=(
            "We propose launching an instant cross-border remittance product enabling customers to "
            "send funds with cash pickup at partner agent locations in a new West African corridor. "
            "The product will route transactions through several money service business (MSB) "
            "partners operating in a higher-risk jurisdiction to enable same-minute settlement. "
            "Initial volume is projected at $8M/month within the first two quarters. This memo "
            "requests an FCRM risk assessment prior to pilot launch."
        ),
    ),
    dict(
        filename="02_medium_risk_vendor_onboarding.pdf",
        title="Onboard New Payments Processing Vendor",
        change_type="Vendor Onboarding",
        submitted_by="R. Chen, Commercial Payments",
        date="2026-09-26",
        description=(
            "We propose onboarding a new third-party vendor to handle merchant payment processing "
            "on behalf of the bank's commercial banking line. This vendor relationship will expand "
            "our current merchant acquiring program into a new customer segment of small and "
            "micro-businesses that previously did not qualify under our existing underwriting "
            "criteria. The vendor will have access to transaction data and initial onboarding "
            "workflows. This memo requests an FCRM risk assessment prior to contract execution."
        ),
    ),
    dict(
        filename="03_low_risk_new_savings_tier.pdf",
        title="Add New High-Yield Savings Interest Tier",
        change_type="Feature Change",
        submitted_by="M. Patel, Consumer Banking",
        date="2026-09-26",
        description=(
            "We propose adding a new interest rate tier for existing retail savings account holders "
            "who maintain an average balance above $50,000. This change only affects the interest "
            "calculation applied to current customers' existing accounts; it does not introduce any "
            "new account types, new customer segments, new payment rails, or new geographies. No "
            "changes to onboarding, KYC, or transaction processing are required. This memo requests "
            "sign-off confirming no further FCRM review is needed."
        ),
    ),
    dict(
        filename="04_out_of_scope_unrelated.pdf",
        title="Team Offsite Recipe Suggestions",
        change_type="Process Change",
        submitted_by="T. Nguyen, Office Operations",
        date="2026-09-26",
        description=(
            "Our team is planning a picnic-style offsite next month and we'd like some recipe and "
            "menu suggestions for the event, ideally a mix of vegetarian and non-vegetarian options "
            "that are easy to prepare in bulk and transport outdoors. We'd also appreciate a few "
            "dessert ideas and a simple drink menu. This request is unrelated to any banking product, "
            "process, vendor, or customer change."
        ),
    ),
]

if __name__ == "__main__":
    for memo in memos:
        path = build_memo(**memo)
        print(f"Created {path}")
