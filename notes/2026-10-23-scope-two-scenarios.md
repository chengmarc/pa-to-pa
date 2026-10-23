# Scope decision: start with D1 + D2 only

Date: 2026-10-23

## Decision

Run the two distributive scenarios first:

- D1 second-hand item (prices from Zhu et al. or Xia et al.)
- D2 single-issue salary (BATNA = another offer)

Reason: on a single price axis, surplus and exploitation are unambiguous and
can be scored by code.

## Consequences for the design

- Main grid: 4 strategies × 2 tiers × 2 scenarios × 2 persuadee models × 45
  principals = 1,440 runs.
- Strategy × tier cells shrink from ~540 to ~180 runs. Strategy and tier both
  vary within principal, so the paired design helps, but adding 2–3 seeds per
  cell is cheap and recovers margin for the interaction.
- H3 (loss-aversion moderation) is still limited by 45 principals, not by run
  count.
- Fisher & Ury relies on interests and options for mutual gain, which a
  single-issue price negotiation barely allows. The Voss vs F&U comparison
  (RQ-B) is tilted toward Voss here and must be scoped to distributive
  settings.
- The fallback minimum version in the plan (D1, I1, G1) no longer applies.

## Open questions

- Which side does the secretary agent represent in each scenario (buyer or
  seller in D1; candidate or employer in D2)?
- Do we add D2 → I2 (salary + equity/bonus/start date) later as the one
  integrative extension?

## Decision: no-deals stand

A game that reaches the message limit without a deal is recorded as a no-deal. We don't force a deal. A no-deal has
no price and no advance; deal rate is reported as its own outcome, and mean advance is computed over deals only.
Both prompts state the payoff honestly (no deal is worse than any price within your limit) but nothing compels
agreement.
