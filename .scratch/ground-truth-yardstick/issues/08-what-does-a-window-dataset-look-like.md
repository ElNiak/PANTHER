# 08 — What does a w02-11 dataset built to the rule look like?

Type: prototype (HITL)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: [01 — What is a window's ground truth anchored to?](01-what-is-ground-truth-anchored-to.md), [02 — What counts as reachable?](02-what-counts-as-reachable.md), [03 — How often would scoring a bare decimal be wrong?](03-how-often-is-a-bare-decimal-wrong.md), [10 — Fetch and pin the draft texts w02-11 cites](10-fetch-and-pin-cited-drafts.md)
Parent: [Ground-Truth Yardstick](../map.md)

## Question

Given 01's anchor, 02's reachability test and 03's verdict on decimals, what does the aioquic w02-11
dataset actually look like, and how do the three existing drafts score against it?

Build a rough version under `../prototypes/08-window-dataset/` (throwaway; nothing enters `<ai_rfc>`):

- the dataset file in the current YAML shape, re-anchored at `509065a` per 01, with for each fact its
  window-end name and value, its `file:line` there, a **citation** to the section of the draft the
  code declares (h3-22, pinned by ticket 10), and a reachability flag. Compute the flag with 02's
  test: the fact's source line appears as an added line in an in-window cluster diff of the same file.
  For w02-11 all 26 candidates pass, via c0005. Facts whose code and cited draft disagree go in an
  excluded list with the reason (01, ruling 5);
- a throwaway scoring script that reuses `<pin>`'s scorer where it can;
- a table for the pilot, v2 A1 and v2 A2 showing reachable recall, all-facts recall, the ceiling and
  claim accuracy with its attempt count (per 06, if resolved).

Call `Skill("mattpocock-skills:prototype")`. React to it with the user before 09 builds it for real.

## Resolution

Prototyped and reacted to with the user on 2026-09-21. **The shape stands. 09 builds it with
statements quoted from the cited spec line, and pilot A2 joins the comparison.** The prototype is at
[prototypes/08-window-dataset/](../prototypes/08-window-dataset/README.md). Run
`build_dataset.py`, then `rescore.py`, under the pinned interpreter; the output is kept in
`rescore.out.md`.

**What was built.** Neither of the prototype skill's branches (HTML logic demo, UI variants) fits
this question, so the artifact is the dataset file plus a one-command re-scorer that prints the full
per-fact state. The dataset (`aioquic-w02-11-at-509065a.PROTOTYPE.yaml`) has 34 entries in the current
YAML shape: anchor `509065a`, window [2, 11], declared spec h3-22 with its evidence, and the pinned
spec's sha256.
- **26 scored hex facts** (17 `HTTP_*` error codes, 9 frame types). Each carries `source {path,
  line}`, `citation {doc, section, line}` with `citation_agrees: true`, and `reachable {cluster,
  diff_line}` (all via c0005).
- **8 decimal entries**, which the scorer excludes itself. They are kept because the scorer uses every
  entry's symbol to tell a symbol apart from part of a longer one, as today's dataset does.

**The user's reactions:**

| # | Question | Ruling |
|---|---|---|
| 1 | Is this the shape 09 builds? | **Yes, as prototyped:** ids `h3-22-<kind>-<name>`, source, citation (+ `citation_agrees`), reachable, and the decimal entries kept for disambiguation. |
| 2 | What goes in `statement` (not scored)? | **The cited spec line, quoted**: the draft's own sentence at the citation. It is mechanical and checkable against the pinned text. The template is dropped. |
| 3 | Add pilot A2? | **Yes.** The comparison is two v1 runs against two v2 runs. Ticket 12's audit covers four drafts, and 09 re-scores four. |

**Provisional results** (they stand only once ticket 12's audit clears the drafts):

| Draft | Reachable recall (= all-facts; ceiling 26/26) | Claim accuracy | Error codes: matched / named / absent | Frame types |
|---|---|---|---|---|
| pilot v1 A1 (tag -10) | 11/26 = 0.423 | 1.000 (11 attempted of 26 reachable) | 2 / 0 / 15 | 9/9 |
| pilot v1 A2 (tag -11) | 11/26 = 0.423 | 1.000 (11 of 26) | 2 / 0 / 15 | 9/9 |
| v2 A1 | 9/26 = 0.346 | 1.000 (9 of 26) | 0 / 2 / 15 | 9/9 |
| v2 A2 | 10/26 = 0.385 | 1.000 (10 of 26) | 1 / 1 / 15 | 9/9 |

- **Every draft states all 9 frame types.**
- **Both pilots state the two error codes with values**: "HTTP_WRONG_STREAM, whose value is 0x0A"
  and "HTTP_UNEXPECTED_FRAME, whose value is 0x13" (pilot A1 draft l.166 and l.187). v2 A1 names both
  with no value; v2 A2 states one and names the other.
- **15 of 17 error codes are absent everywhere.**
- **On the valid yardstick, v1 recovers slightly more facts than v2 (11, 11 vs 9, 10).** It is one
  window, and the differences are 1–2 facts.
- **Pilot A2's final revision is tag `-11`**, its revision for c0011. A2 numbers its revisions one
  higher than A1 (per each run's `revisions.yaml`).

**Checks:**
- **Reproduction:** the old dataset against pilot A1 gives 8/35 with SP7d's exact 8 ids.
- **Truncation:** the edge-cut fix changes no outcome on either dataset for any draft, so no existing
  match depends on the bug (09's check). The fix still goes into 09's spec.
