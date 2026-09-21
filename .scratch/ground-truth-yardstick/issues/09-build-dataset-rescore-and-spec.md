# 09 — Build the w02-11 dataset, re-score the pilot and v2 drafts, and write the scorer-change spec

Type: task (AFK)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: [08 — What does a w02-11 dataset built to the rule look like?](08-what-does-a-window-dataset-look-like.md), [11 — Can a future-free workspace keep the window's cluster ids?](11-can-a-future-free-workspace-keep-cluster-ids.md), [12 — Audit the pilot and v2 transcripts for future material](12-audit-old-transcripts-for-future-material.md), [13 — How do `analyze` and the campaign report present ground truth?](13-how-analyze-presents-ground-truth.md)
Parent: [Ground-Truth Yardstick](../map.md)

## Question

This is the map's one execution ticket (ruling 6, $0). Do three things:

1. **Build the dataset.** Produce the w02-11 dataset as settled by 08, as a map asset under
   `../assets/`, with every fact's anchor, its reachability flag and the evidence for it. **Start from
   08's prototype** (`../prototypes/08-window-dataset/build_dataset.py`), keeping its shape: ids
   `h3-22-<kind>-<name>`, source, citation with `citation_agrees`, reachable, and the decimal entries
   kept for disambiguation. **Make each `statement` the cited spec line quoted from the pinned text**,
   not the prototype's template (08, ruling 2).
2. **Re-score.** Score the four drafts (pilot v1 A1 tag -10, pilot v1 A2 tag -11, v2 A1, v2 A2; 08,
   ruling 3) with a script reusing `<pin>`'s scorer. 08's `rescore.py` is the starting point; its
   provisional numbers are 11, 11, 9 and 10 of 26. **Ticket 12 found all four touched, through
   `corpus_query` returning future commit metadata with no scored fact in it. By user ruling they are
   still scored, and every figure is labelled "touched: future commit metadata through
   `corpus_query`, no scored fact (ticket 12)".**
   Record reachable recall, all-facts recall, the ceiling and claim accuracy with its attempts, in this
   ticket's resolution.
3. **Write the spec.** Specify the scorer change for ai_rfc: what `ground_truth.py` and the
   `ground-truth` verb must compute and print, how the dataset format carries the anchor and
   reachability, the tests that pin it, and which published SP7d documents to amend. Hand it off; do
   not edit `<ai_rfc>`. **The spec must include the edge-truncation fix** found by ticket 03:
   `_tokens_near` (`<pin>/ai_rfc/experiment/ground_truth.py`, the `token.findall(body[start :
   match.end() + NEARBY_CHARS])` line) cuts a hex token that straddles the slice end (`0x10A` becomes
   `0x1`), and `score_draft` can then report a false **match**. Check whether any of the eight
   existing frame-type matches depends on it. **The spec must also carry 01's amendments.** Write a
   D-row amending spec D44 and SP7d U3: the anchor is the window's end, and each fact cites the spec
   version the code declares, checked mechanically against pinned text. It also carries the rename of
   today's `aioquic-w02-11.yaml` to its anchor (aioquic HTTP/3 at `6d36838`), and the rule that a
   disagreeing fact is excluded with its reason. **It also specifies 02's reachability computation**:
   a fact is reachable if its source line at the anchor is an added line in an in-window cluster's
   `span.diff` for that file, decided per window. It carries 02's three defaults, which are
   whitespace-stripped comparison, following in-window renames, and never counting out-of-window
   clusters. **It also specifies 05's leak fix, shaped by 11's findings.** Each run gets a
   future-free workspace: none of the five routes (`clone/`, out-of-window clusters, forge, corpus,
   git) reaches past the window's end. The spec also adds an audit backstop that records read-tool
   paths and flags any tool result carrying future content. The Main Campaign map's freeze waits on
   this landing. **Research 11 settled the shape:** the fix goes in `workspace prepare`. Specify its
   five conditions exactly as
   [research/11-future-free-workspace.md](../research/11-future-free-workspace.md) states them:
   - cut at the last member of the window's top cluster, asserted against a full-timeline pass;
   - **the corpus (`corpus/commits.jsonl`, `files.jsonl`, `index.sqlite`) holds only commits up to
     the end.** This is the route ticket 12 found actually leaking, through `corpus_query`. Research
     11's truncated prepare builds the corpus from the truncated clone; the spec must assert it;
   - keep every merged PR whose landing commit is an ancestor of the end, and rewrite
     `meta.clone_head`;
   - clone with `--no-local --revision=<end>` and remove `origin`;
   - assert that the stored objects are exactly those reachable from HEAD (the seal never covers
     `.git`);
   - keep the audit, because repositories outside the workspace stay reachable by absolute path.

   Include that file's "Open questions for the spec". **It also carries 06's reporting rules:**
   - `claim_accuracy` always with its attempted and reachable counts, in JSON and text; no threshold;
     still `None` when nothing was attempted;
   - a per-kind breakdown (matched, attempted, missed, named);
   - a *named* diagnostic outcome, meaning the symbol appears with no qualifying value nearby. It is
     not an attempt, and it doesn't touch recall or accuracy.

   **It also carries 13's decisions:**
   - `analyze` scores each run's final draft (at `latest_tag`) by default, whenever a dataset exists
     for the campaign's target and exact window. The result sits beside `quality` in `analyze_run`.
     There is no flag, and the verb stays for scoring a single draft.
   - **Dataset selection** is by the target and window the dataset declares, replacing the
     hard-coded `DATASET`.
   - **The report gets a "Ground truth" section:**
     - per run: status and error, reachable recall, ceiling, claim accuracy with its counts, named
       count, and the future-material verdict;
     - a per-kind table;
     - per arm: reachable recall as mean / min, with claim accuracy from pooled counts.
   - **Statuses:** `scored` | `no declared spec` | `no dataset for this window` | `draft unreadable`.
     A missing figure shows "—" with its status, never 0.
   - **Touched runs** (flagged by 05's audit backstop) are scored and flagged, left out of the arm
     aggregate, and the number left out is stated.

   **Published SP7d documents to amend** (moved here from the map's fog when 13 resolved):
   - `<ai_rfc>/docs/experiments/2026-09-18-sp7d-instrument.md`;
   - the SP7d deviation log, `docs/superpowers/plans/2026-09-15-arfc-sp7d-deviations.md` in PANTHER;
   - the held SP7d Phase 5 write-up.

   **Note on the owed-fixes row:** that session moved the Markdown escaper from
   `ai_rfc/experiment/markdown.py` to `ai_rfc/markdown.py`. The report section must use it at its
   new path, and the spec cites current `main`, not `<pin>`, wherever that row has changed a file.

When done, tell the SP7d session: its held Phase 5 write-up and judge-timeout comment are waiting on
these numbers.

## Resolution

Done on 2026-09-21 ($0, session 0ea41509). **The dataset is built, the four drafts are re-scored, and
the hand-off spec is written.**

1. **Dataset:** [assets/09/aioquic-w02-11-at-509065a.yaml](../assets/09/aioquic-w02-11-at-509065a.yaml),
   built by [assets/09/build_dataset.py](../assets/09/build_dataset.py) (tracked and self-contained;
   ticket 10's spec reader is inlined).
   - **Contents:** 34 entries. The 26 hex facts are all cited against the pinned draft-ietf-quic-http-22,
     agree with it, and are reachable (via c0005); the 8 decimal entries are kept for disambiguation.
   - **Header:** `target: aioquic`, `window: [2, 11]`, anchor `509065a`, `declared_spec` h3-22 with
     its evidence, and the spec's sha256.
   - **Statements:** each statement quotes the cited spec paragraph. All 26 pass the build's checks:
     the value is present, there is no page-break artifact, and the paragraph ends with a full stop.
2. **Re-score:** [assets/09/rescore.md](../assets/09/rescore.md), produced by
   [assets/09/rescore.py](../assets/09/rescore.py) in ticket 13's report format. **Every run is
   labelled "touched: future commit metadata through `corpus_query`, no scored fact (ticket 12)"**, so
   the arm rows show "— (2 of 2 touched, left out)".

   | Run | Reachable recall | Claim accuracy | Error codes (matched / mismatched / named / absent) | Frame types |
   |---|---|---|---|---|
   | pilot v1 A1 (tag -10) | 11/26 (0.423) | 1.000 (11 attempted of 26 reachable) | 2/0/0/15 | 9/9 |
   | pilot v1 A2 (tag -11) | 11/26 (0.423) | 1.000 (11 of 26) | 2/0/0/15 | 9/9 |
   | v2 A1 | 9/26 (0.346) | 1.000 (9 of 26) | 0/0/2/15 | 9/9 |
   | v2 A2 | 10/26 (0.385) | 1.000 (10 of 26) | 1/0/1/15 | 9/9 |

   - The ceiling is 26/26 for every run.
   - These are identical to 08's prototype, as expected: statements don't affect scoring.
   - **Checks:** the old dataset reproduces SP7d's 8/35 with the same ids, and the whole-token
     `_tokens_near` changes no outcome.
3. **Hand-off spec:**
   [`docs/superpowers/specs/2026-09-21-arfc-ground-truth-yardstick-design.md`](../../../docs/superpowers/specs/2026-09-21-arfc-ground-truth-yardstick-design.md)
   (PANTHER, uncommitted). It cites code by function name at ai_rfc `main` `2c768b5`. Its sections:
   - the rulings index, linking tickets 01–13;
   - the dataset format and selection by target and window, including renaming the old dataset;
   - citation verification, and anchor verification through `git show` rather than a working tree;
   - scoring: reachability, the figures, `named`, and the §4.6 truncation fix;
   - the verb's JSON and text;
   - `analyze` and the report: statuses, the "Ground truth" section, and the judge-completeness
     caveat;
   - future-free prepare with its six conditions (the corpus included), a `cluster_get` window check,
     and the audit backstop;
   - draft D-row text amending D44 and U3;
   - the tests that pin each rule, the documents to amend, research 11's seven open questions, and
     these results.

**For the SP7d session** (this same session): the held Phase 5 write-up and the
`JUDGE_DRAFT_TIMEOUT_S` comment now have their numbers. Committing them waits on the user.
