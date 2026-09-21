# 13 — How do `analyze` and the campaign report present ground truth?

Type: grilling (HITL)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: —
Parent: [Ground-Truth Yardstick](../map.md)

## Question

Today only the `ground-truth` verb computes ground truth. `analyze` and the campaign report never
reference it (`<pin>/ai_rfc/experiment/metrics.py` and `report.py` have no mention). Tickets 01, 02
and 06 have now fixed what a score is:

- reachable recall first, all-facts recall with its ceiling second;
- claim accuracy always with its attempted and reachable counts;
- a per-kind breakdown;
- *named* as a diagnostic.

Decide how it reaches a campaign's results:

- Should `analyze` score each run's final draft whenever the campaign's target and window have a
  dataset, or does ground truth stay a separate verb run by hand?
- What does the report show per run and per arm, and how do the ceiling and counts appear so that a
  vacuous figure can't be read as a result?
- What appears for a target or window with no dataset? **07 resolved (2026-09-21):** MARK declares no
  spec, so it has no dataset. Wherever ground truth appears it shows `None` with the reason "no
  declared spec", never 0, following the project's rule that an absence is unmeasured. Decide only
  how that reads in the report.
- Does the fog item on per-revision scoring (each tag against the code at its own cluster) join here,
  or stay out?

This graduated from the map's Not yet specified when 06 resolved.

## Resolution

Grilled with the user on 2026-09-21. **`analyze` scores every run's final draft by default, whenever
a dataset exists for the campaign's target and window. The report gets its own "Ground truth"
section. Touched runs are shown but left out of arm figures. Per-revision scoring is out of scope.**

| # | Question | Ruling |
|---|---|---|
| 1 | Does `analyze` score it? | **Yes, by default.** It scores each run's final draft (the one at `latest_tag`, the same draft `--build` uses) whenever a dataset exists for the campaign's **target and exact window**. It is $0 and calls no model, so there's no flag. The `ground-truth` verb stays for scoring any single draft by hand. |
| 2 | Report layout | A **"Ground truth" section**. Per run: status; reachable recall "11/26 (0.423)"; ceiling "26/26"; claim accuracy "1.000 (11 attempted of 26 reachable)"; the named count; the future-material verdict. A **per-kind table** below it. **Per arm:** reachable recall as mean / min (the "completed" pattern), with claim accuracy from pooled counts. A run with no dataset shows "—" plus its status, never 0. |
| 3 | Touched runs | **Scored, flagged, and left out of arm rows.** The run's own row keeps its scores, with the flag and the audit's evidence. The arm aggregate leaves it out and states how many runs it dropped. The four historical drafts (all touched, ticket 12) are reported per run under 12's label. |
| 4 | Per-revision scoring (fog) | **Out of scope.** The destination is a yardstick for a run's final draft. Scoring every revision needs a dataset anchored at each cluster's end, which is a new effort. |

**Defaults for 09's spec (not rulings; the user can overrule):**
- **Status vocabulary**, on the build-status pattern (a status column beside an error column):
  `scored` | `no declared spec` (MARK, ticket 07) | `no dataset for this window` | `draft unreadable`
  (for example a recorded tag the draft repository doesn't hold, as MARK's `-38`).
- **Dataset selection** is by the target and window a dataset declares. It replaces today's hard-coded
  `DATASET`.
- **The touched flag** comes from 05's audit backstop in `audit.py`, which records read-tool paths
  and flags future content.

**Evidence (at `<pin>`, ai_rfc `3406985`):**
- `metrics.analyze_run` stores each run's quality under a `quality` key (`experiment/metrics.py:350`);
  ground truth would sit beside it. `analyze_campaign` records the campaign's `target` and `window`
  (`metrics.py:549-550`).
- `report.render_report` renders quality in its own section (`experiment/report.py:108-185`, header
  at :271). Each instrument there pairs a status column with an error column, so a null says why it is
  null.
- The final draft is the one at `draft.gate.latest_tag` (`draft/gate.py:142`), the highest-numbered
  recorded revision, which is the draft `final_build` builds (`experiment/quality.py:608`).
- Today there is one dataset, hard-coded (`experiment/ground_truth.py:18`,
  `DATASET = "aioquic-w02-11.yaml"`), with no lookup by target or window.
