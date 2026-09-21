# 02 — What counts as reachable?

Type: grilling (HITL)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: [01 — What is a window's ground truth anchored to?](01-what-is-ground-truth-anchored-to.md)
Parent: [Ground-Truth Yardstick](../map.md)

## Question

Reachable recall (ruling 2) needs a **reachable fact** defined precisely enough to compute it
mechanically for any target and window. Two parts:

1. **Which material counts as shown?** Candidates, per window cluster, under
   `<pristine>/clusters/<id>/`:
   - `span.diff`: `ai_rfc_cluster_get` returns a 20,000-byte slice by default, and the agent can page
     for more;
   - `view.json`;
   - `evidence/pr.json`.

   Excluded or open:
   - pre-seeded clusters (they load nothing, `experiment/workspace.py:173-208`);
   - the corpus (metadata only);
   - `refcache/` (bibliography stubs);
   - the `clone/` working tree (ticket 05).

   Does "shown" mean *available to page* or *actually read* in a given run?
2. **What mechanical test marks a fact reachable?** For example, its symbol and its value both appear
   in the shown material; or a definition line (`NAME = VALUE`) appears in an in-window diff's added
   lines; or the symbol alone appears (for instance c0005's diff references `Setting.QPACK_BLOCKED_STREAMS`
   but never its value, which is defined in pre-seeded c0001).

## Starting evidence

- `server/core/queries.py:82-117` (`cluster_get`, at `<pin>`). A1 read c0005 up to byte 89,000, and
  the 2019 `ErrorCode` enum sits around bytes 6,000–7,400 of that diff.
- The frame types (the eight facts every draft matched) are defined in c0005's diff (lines 202-203:
  `GOAWAY = 0x7`, `MAX_PUSH_ID = 0xD`).
- The answer depends on 01: the fact's spelling decides what to search for.
- **01 resolved (2026-09-21):** facts are spelled and valued as the code states them at the window's
  end, `509065a` for w02-11. The candidates are 26 hex facts: 17 `HTTP_*` error codes
  (`HTTP_NO_ERROR = 0x00` … `HTTP_SETTINGS_ERROR = 0xFF`) and 9 frame types (`DATA = 0x0` …
  `DUPLICATE_PUSH = 0xE`). The 4 decimal settings and 4 decimal stream types can't be scored
  (ticket 03). Reachability filters these 26. 01's ruling 5 separately excludes any fact that disagrees
  with its cited draft. One trap: a value can change inside the window (c0005's diff removes
  `GOAWAY = 6` and adds `GOAWAY = 0x7`), so decide whether a removed line counts as showing a fact.

## Resolution

Grilled with the user on 2026-09-21. **A fact is reachable when its own source line at the anchor
appears as an added line in an in-window cluster's diff of the same file, decided once per window.**
The user's rulings:

| # | Question | Ruling |
|---|---|---|
| 1 | Which lines are shown | **Added (or changed) lines of in-window cluster diffs only.** These are exactly the lines the loop prompt lets the agent anchor a claim to ("`line` is a line the diff added or changed", `<pin>/ai_rfc/driver/prompts/loop.tmpl.md`). Context lines, removed lines, PR text (`evidence/pr.json`) and `view.json` don't count. |
| 2 | The test | **The fact's own source line.** The dataset records each fact's `file:line` at the anchor commit. The fact is reachable if that line's content appears as an added line in some in-window cluster's `span.diff` for the same file. It is language-agnostic and mechanical. |
| 3 | Per window or per run | **Per window.** Everything `cluster_get` can serve for an in-window cluster counts, whether or not a run paged to it, so every draft of a window shares one denominator. |

**Defaults for 09's spec (not rulings; the user can overrule):**
- Lines are compared with leading and trailing whitespace stripped.
- "The same file" follows renames made inside the window, using the path the diff names.
- Out-of-window clusters are never shown material, even though `cluster_get` serves them (that is
  the leak, ticket 05).

**Evidence (measured read-only in `<pristine>/clusters/`, c0002–c0011):**
- **Error codes:** all 17 `HTTP_*` definitions at the window's end are added lines in
  `c0005-epoch-79f631193bdf/span.diff`. No other in-window cluster has a definition line for any of them.
- **Frame types:** all 9 are added in c0005, in hex, at L196-204 (`+    DATA = 0x0` …
  `+    DUPLICATE_PUSH = 0xE`). The same diff removes the decimal ones at L187-195, three of which had
  other values: `GOAWAY = 6`, `MAX_PUSH_ID = 7`, `DUPLICATE_PUSH = 8`.
- **Offsets:** all 26 definitions sit at bytes 6,081–7,013 of c0005's 131,966-byte diff, inside the
  first 20,000-byte page `cluster_get` serves by default (`<pin>/ai_rfc/server/core/queries.py:82-120`).
  So "per window" and "per run" give the same answer for w02-11.

**Consequences:**
- **w02-11:** all 26 candidates are reachable via c0005, so before 01's ruling 5 agreement filter,
  **reachable = 26 of 26 and the ceiling is 1.0**. Reachable recall and all-facts recall coincide for
  this window.
- **Earlier values:** a draft that states a value from before c0005 (such as `GOAWAY = 6`) is scored
  as mismatched, because the truth is the window's end.
- **Tickets 07 and 08:** 07 is unblocked (01 and 02 are resolved). 08 still waits on 10.
