# 12 — Audit the pilot and v2 transcripts for future material

Type: task (AFK)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: —
Parent: [Ground-Truth Yardstick](../map.md)

## Question

Ticket 05, ruling 4: the drafts already produced stand only if their runs never **touched future
material**, meaning no tool result delivered content describing the repository after the window's end
(`509065a`, 2019-09-04). A bare file name in a listing doesn't count. Do the audit ($0) for:

- **v2 A1 and A2:** `~/ai-rfc-experiments/campaigns/aioquic-w02-11-v2-armA-sp7d-pinned/runs/A{1,2}/events.jsonl`;
- **pilot v1 A1 and A2:** their transcripts sit read-only under
  `~/arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831/runs/A{1,2}/`. Never re-run `audit` or
  `analyze` on them; read the files. Pilot A2 was added by ticket 08's ruling 3, so four drafts are
  audited in all.

For every tool result in each transcript, check all five routes (ticket 05's Resolution):

- **`Read`/`Grep`/`Glob` content** from `clone/` (tip source), out-of-window `clusters/`, or `forge/`;
- **`cluster_get`** for any cluster outside [2, 11];
- **every `corpus_query`** result row: does it include commits after `509065a`, or file changes from
  them? (56 queries across A1/A2 were never audited.)
- **any `git`** output reaching past the end (arm A has no Bash, but check anyway).

Record a per-draft verdict (clean or touched), with each touching call quoted with its line in the
transcript. Write the scan code to `../research/12-audit/` so it can be reproduced. It is kept there
because that directory is git-ignored; this ticket's resolution cites it.

## Constraints

Read-only on every transcript and evidence tree. Write only under this map. Resolved when all three
verdicts are recorded. A touched draft is excluded from 09's re-score, and why is recorded.

## Resolution

Done on 2026-09-21 ($0, read-only). **All four drafts touched future material, through one route
only: `corpus_query` returned commit metadata from after the window's end.** None of that content
contains a scored fact's name or value. **User ruling:** these four drafts are still re-scored in
09, with every figure labelled as touched. Ticket 05's rule stands unchanged for all future runs.

Code: [research/12-audit/audit.py](../research/12-audit/audit.py). Report:
[research/12-audit/report.md](../research/12-audit/report.md). Every tool call is classified exactly
once, and the counts sum to each run's total. The past set is `git rev-list 509065a` in each run's
own clone. Every clone is at `6d36838` and contains the end: 588 commits up to the end, 594 after it.

| Draft | Tool calls | Future content | Where it came from |
|---|---|---|---|
| pilot v1 A1 | 193 | 1 | `corpus_query` l.796 |
| pilot v1 A2 | 198 | 2 | `corpus_query` l.48, l.931 |
| v2 A1 | 405 | 2 | `corpus_query` l.339, l.431 |
| v2 A2 | 387 | 6 | `corpus_query` l.15, 635, 974, 985, 1190, 1203 |

**What was touched:**
- **Only commit metadata.** Each future result holds commit shas, dates, subjects and file paths of
  commits after `509065a`. For example, pilot A1 l.796 returned `22a6929` (2019-09-04T21:46:47+02:00,
  "[package] raise pylsqpack requirement to 0.2.3"), which is not an ancestor of the end. v2 A2
  l.974 returned `89aaa0f` from 2025-10-08.
- **Most came from open-ended queries.** Date-range or path queries such as `authored_at > '2019-09-02'`
  or `ORDER BY rowid DESC` run over the whole 1,182-commit corpus and don't stop at the window.
- **No scored fact appears in any of them.** No `HTTP_*`/`H3_*` error name, frame-type name or hex
  value occurs in any future result. The only hits, v2 A1 l.431 and v2 A2 l.635, name `PUSH_PROMISE`
  in the subject of `8d579b2` ("[http3] raise an exception if server receives a PUSH_PROMISE",
  2019-08-31). That commit is **before** the end, and the row sits among later rows in the same
  result. `PUSH_PROMISE`'s value is set by c0005's diff, not by that subject line.

**The other routes were not used:**
- **Code and diffs:** no Read or Grep of changed `clone/` files, no out-of-window `clusters/` file,
  and no `cluster_get` outside [2, 11] in any run.
- **Forge and git:** no forge content, and no Bash (so no git) in any run.

**Kept separate and not counted as touched:**
- **`status` calls:** these report the timeline's `tip_sha` `6d36838` and its counts (2 per pilot
  run, 11 per v2 run). That is metadata naming the tip, with no content.
- **Schema lookups and failed queries:** schema lookups (`sqlite_master`) and failed queries (wrong
  column names) are classified as `no-history`.
- **Empty result:** v2 A1 l.118 returned nothing (`{"result":[]}`).
- **Names only:** Glob listings (ruling 3).

**The ruling.** The user was offered: re-score with a label, exclude all four (nothing re-scorable at
$0), or narrow "touched" to fact-bearing content. They chose **re-score with a label**. 09 re-scores
all four drafts, and every figure carries "touched: future commit metadata through `corpus_query`, no
scored fact (ticket 12)". Ticket 05's definition is unchanged, and future-free workspaces (05, 11) are
what prevent this in new runs. **The corpus route is the one that actually leaked**, so the prepare
fix must truncate `corpus/` as well as `clone/`.
