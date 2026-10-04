# Customer Risk Segmentation

## Purpose
Customer risk segmentation assigns each customer a risk tier (e.g. Low, Medium, High) based on a combination of factors, driving differentiated due diligence depth, review frequency, and transaction monitoring sensitivity.

## Segmentation Factors
- **Customer type** — individual retail customers are generally lower risk than corporate entities, trusts, or money services businesses.
- **Geography** — customers domiciled in, or with significant activity tied to, higher-risk jurisdictions receive elevated risk tiers.
- **Product usage** — customers using cash-intensive services, cross-border transfers, or correspondent-style services typically carry higher risk than customers using only basic deposit products.
- **Behavioral history** — prior SAR filings, sanctions hits (even if cleared), or unusual account activity elevate risk tier regardless of other factors.

## Segment-Specific Requirements
- **High-risk segment** customers require EDD at onboarding, more frequent periodic reviews (e.g. annually rather than every three years), and lower transaction monitoring alert thresholds.
- **Medium-risk segment** customers receive standard CDD with moderate review frequency.
- **Low-risk segment** customers receive baseline KYC/CDD with standard review cycles.

## Relevance to New Customer Segments
When a proposed change opens the product to a new customer segment (e.g. minors, non-resident aliens, small businesses, gig-economy workers, or MSBs), the assessment must determine:
1. Which risk tier the new segment should default to, and why.
2. Whether onboarding data collection is sufficient to place new customers into the correct tier from day one.
3. Whether the new segment introduces behavioral patterns (e.g. high transaction velocity for gig workers) that could trigger false-positive alert volume, and whether monitoring scenarios need tuning before launch.
4. Whether segment-specific regulatory requirements apply (e.g. additional protections for minors, enhanced scrutiny for MSBs as a customer type rather than merely a transaction counterparty).
