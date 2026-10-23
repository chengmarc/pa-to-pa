# persuader-strategies

One file per persuader strategy, named by its id in `src/labels.json`. The file goes under "How to negotiate" in the
persuader's prompt.

- `s0_none.md` (None) — baseline: one line, no tactics
- `s1_generic.md` (Generic) — a skilled negotiator without either book's tactics, length-matched to the two below
- `sx_fisher_ury.md` (Fisher-Ury) — Fisher & Ury, *Getting to Yes*: interests, options, objective criteria
- `sy_voss.md` (Voss) — Voss, *Never Split the Difference*: labels, mirrors, calibrated questions, Ackerman bargaining

`s1_generic`, `sx_fisher_ury` and `sy_voss` are kept within a few words of each other (~210), so a difference between
them isn't a difference in prompt length. **The current files are drafts**, to be replaced by the final versions.
