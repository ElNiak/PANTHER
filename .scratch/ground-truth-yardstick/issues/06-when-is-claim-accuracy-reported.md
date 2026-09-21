# 06 — When is claim accuracy reported?

Type: grilling (HITL)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: —
Parent: [Ground-Truth Yardstick](../map.md)

## Question

`claim_accuracy` is matched ÷ attempted. All three w02-11 drafts report **1.0 over 8 attempts**: the
eight frame types, and nothing else was even attempted. The drafts' `HTTP_*` error codes don't count as
attempts, because no dataset symbol pattern matches them. The instrument already reports `None`, never
0.0, when nothing was attempted. Should it also:

- withhold the figure below a minimum number of attempts, or print it with its attempt count
  ("1.0 of 8");
- report attempts per fact kind, so "accurate on frame types only" is visible;
- count a draft that states a fact under an era's spelling (ticket 01, option C) as an attempt?

## Starting evidence

`<t11>/gt-armA/{A1,A2}/ground-truth.json` and `<t11>/gt-pilot/ground-truth.json`: attempted = matched =
the 8 `h3-frame-*` ids, mismatched `[]`. Scorer outcomes: `<pin>/ai_rfc/experiment/ground_truth.py`
(missed / attempted / matched / mismatched).

## Resolution

Grilled with the user on 2026-09-21. **Claim accuracy is always reported with the counts it rests on,
broken down per fact kind. A fact named without a value becomes its own diagnostic outcome.** The
user's rulings:

| # | Question | Ruling |
|---|---|---|
| 1 | Low attempts | **Always report it with its counts.** Everywhere claim accuracy appears (JSON and text), it carries the attempted count and the reachable count, e.g. "1.000 (8 attempted of 26 reachable)". There is no threshold. The existing rule stays: `None`, never 0.0, when nothing was attempted. |
| 2 | Per kind | **Yes.** Matched, attempted, missed and named (ruling 3) are reported for each fact kind (`error_code`, `frame_type`, …), beside the totals. "Accurate on frame types, silent on error codes" is what today's 8/8 hides. |
| 3 | Named without a value | **Counted separately, as a diagnostic.** A fact whose symbol the draft names with no value of the right shape nearby is **named**, not missed. It isn't an attempt, and it changes neither recall nor accuracy. `missed` splits into *named* and *absent*. A1's `HTTP_WRONG_STREAM` (no value) is the case. |

**The third bullet of the question is moot:** ticket 01 anchored facts to the window-end spelling, so
there are no per-era spellings to count.

**Evidence (at `<pin>`):**
- `claim_accuracy` is matched ÷ attempted, or `None` (`ai_rfc/experiment/ground_truth.py:134-148`).
  An entry is attempted when its symbol is named and a value of the right shape lies within
  `NEARBY_CHARS` (`score_draft`, :220+).
- The verb's text already prints "claim accuracy: 8 of 8", but its JSON writes the bare ratio
  (`experiment/cli.py:1135`).
- **Ground truth is in neither `analyze` nor the campaign report:** `metrics.py` and `report.py` never
  reference it. That presentation question graduates to ticket 13.

**Spec items for ticket 09:**
- The JSON and text carry `claim_accuracy` together with the attempted and reachable counts.
- The report adds a per-kind breakdown.
- A `named` outcome is added (the same symbol pattern and window as today, with no qualifying value).
- The name `claim_accuracy` stays; "precision" is reserved for the judge.
