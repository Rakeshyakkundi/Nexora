# Cross-Border Payments Risk

## Why Cross-Border Payments Are Higher Risk
Cross-border transfers are consistently among the highest financial-crime-risk activities a bank offers, because they can move funds across jurisdictions with differing regulatory regimes, involve intermediary banks the Bank does not directly control, and are frequently used in trade-based money laundering and layering schemes.

## Key Risk Factors
- **Corridor risk** — some country pairs carry materially higher risk than others based on corruption indices, sanctions exposure, and known typologies (e.g. certain corridors are associated with trade-based laundering or informal value transfer).
- **Speed vs. control tradeoff** — instant or near-instant cross-border rails compress the window available for pre-transaction screening and manual review, which can force a choice between speed and control rigor.
- **Message transparency** — some payment message formats truncate or omit originator/beneficiary information as they pass through intermediary banks, weakening downstream screening ("black-box" routing).
- **Currency and settlement risk** — multi-currency transactions can obscure the true economic purpose of a transfer.

## Controls Typically Required
- Full originator and beneficiary information must travel with the payment message end-to-end (Travel Rule-equivalent expectations).
- Sanctions and PEP screening must occur before funds are released, not only after settlement.
- Corridor-specific risk ratings should feed into transaction monitoring scenario thresholds — higher-risk corridors typically warrant lower alerting thresholds.
- New corridors should not go live until screening coverage and monitoring scenarios have been validated end-to-end.

## Assessment Guidance
Any new product or feature enabling a new cross-border corridor, or increasing the speed of existing cross-border transfers, should be treated as at least Medium risk by default, escalating to High if the corridor involves a jurisdiction with elevated sanctions or corruption risk, or if screening cannot occur before funds are released.
