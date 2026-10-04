# Sanctions Screening

## Regulatory Basis
The Bank must comply with sanctions programs administered by OFAC (U.S. Treasury), UN sanctions lists, EU consolidated lists, and other applicable regimes wherever the Bank operates. Screening applies to customers, counterparties, beneficial owners, and transaction parties.

## Screening Points
Sanctions screening must occur at multiple points in the customer and transaction lifecycle:
- **Onboarding** — screening new customers and beneficial owners against sanctions lists before an account is opened.
- **Ongoing monitoring** — rescanning the existing customer base as sanctions lists are updated.
- **Transaction screening** — real-time or near-real-time screening of payment instructions, particularly for cross-border and correspondent banking transactions, to catch sanctioned parties named anywhere in the payment chain.

## Common Gaps Introduced by New Products or Corridors
- **New payment corridors or rails** (e.g. instant cross-border transfers) may not automatically inherit the screening logic applied to existing rails, especially if message formats differ (e.g. free-text remittance fields that evade name-matching).
- **New intermediary or correspondent relationships** can introduce nested exposure — the Bank may not have visibility into the ultimate parties of a transaction routed through a third party.
- **Vendor and fintech partnerships** that originate or route transactions on the Bank's behalf must be contractually and technically required to perform equivalent screening, or the Bank must screen on their behalf.

## Risk Assessment Expectations
A change introducing a new corridor, new payment rail, or new third-party origination flow should document:
1. Which entity performs sanctions screening at each step of the flow.
2. Whether screening covers all parties in the transaction (originator, beneficiary, intermediaries), not just the Bank's direct customer.
3. Match/hit handling procedures (holds, manual review, regulatory reporting) for the new flow.
4. Whether name-matching logic accounts for non-Latin scripts, transliteration, or free-text fields specific to the new corridor.
