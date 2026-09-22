# Map: Ground-Truth Yardstick

Label: `wayfinder:map`
Charted: 2026-09-21 (plan `~/.claude/plans/next-sp7d-you-are-a-magical-locket.md`, approved)
Tracker: local markdown — tickets are `issues/NN-<slug>.md`; the frontier is every ticket whose
`Status:` is exactly `open`, whose every `Blocked by` ticket is closed, and whose `Claimed:` is `—`,
lowest number first. Compute it from those three lines, never by grepping for one closed-spelling.
**This map lives in the iut-ai-rfc worktree**, not lsp-to-claude where the other eleven maps live.

`<wt>` = this worktree (`…/PANTHER/master/.claude/worktrees/iut-ai-rfc`)
`<ai_rfc>` = `<wt>/panther/plugins/services/testers/ai_rfc` (on `main`; **another session is landing
the owed-fixes row there — never edit it from this map**)
`<pin>` = `~/ai-rfc-experiments/code-pins/ai_rfc-3406985` (ai_rfc at `3406985`, clean; **read code here**)
`<pristine>` = `~/ai-rfc-experiments/pristine/aioquic-w02-11` (the workspace every w02-11 run copies)
`<t11>` = `<ai_rfc>/.superpowers/sdd/2026-09-15-arfc-sp7d/t11` (SP7d Phase 5 evidence, git-ignored)

## Destination

A **valid yardstick** for how many facts a reconstructed draft recovers: a ruled, general definition
of a window's ground truth and of **reachable recall**; the aioquic w02-11 dataset built to it (a map
asset); the pilot and v2 A1/A2 drafts re-scored against it at $0; and a scorer-change spec handed off
to ai_rfc.

Reached when ticket 09 records the re-scored numbers and the spec. Not reached by editing ai_rfc code
or by any paid run.

## Notes

**Why this map exists.** SP7d Phase 5 scored three aioquic w02-11 drafts (pilot v1 A1, v2 A1, v2 A2)
against `<pin>/ai_rfc/experiment/groundtruth/aioquic-w02-11.yaml`: every one scored recall 8/35, the
same eight HTTP/3 frame types. That is the window's **ceiling**, not a finding about the drafts:

- the dataset is anchored at `commit: 6d36838d…` (yaml:59) = `<pristine>/pristine.json` `clone_head`,
  aioquic's **2025 tip**, and was built from the final RFCs (9114, 9204, …);
- w02-11 ends at `509065a` (2019-09-04), the last of c0011's five members. c0011's `view.json`
  `anchor_sha` `d290ebe` is its FIRST member, which charting mis-named as the end (corrected by
  ticket 04). At `509065a`, `aioquic/h3/connection.py` has `HTTP_NO_ERROR = 0x00` …
  `HTTP_SETTINGS_ERROR = 0xFF` (draft-22) and decimal settings (`QPACK_MAX_TABLE_CAPACITY = 1`);
- the 27 missed facts' `H3_*` names and RFC values first appear in clusters c0013–c0241 (mapped via
  `<pristine>/timeline/members.jsonl`), all outside [2, 11];
- the scorer (`<pin>/ai_rfc/experiment/ground_truth.py`) scores hex values only
  (`_value_shape`, l.439-441) and builds its symbol pattern from the dataset symbol (l.410-415), so
  `HTTP_WRONG_STREAM (0x0A)` in a draft is not even an attempt; `claim_accuracy 1.0` rests on 8 claims;
- `pre_seeded` (332 cluster ids) loads no claims or prose (`experiment/workspace.py:173-208`);
- the pristine `clone/` working tree is checked out at the tip, and arm A's `Read` could open it — no
  run did (the only clone path in A1's transcript is `clone/.readthedocs.yaml`).

The ledger's R93 records this; the SP7d "v2 recovers no more facts" reading is withdrawn.

### Settled at charting (user rulings, 2026-09-21) — do not re-litigate

| # | Decision | Ruling |
|---|---|---|
| 1 | Destination | A valid yardstick: definition + w02-11 dataset + $0 re-score of the pilot and v2 drafts |
| 2 | Recall | **Reachable recall is primary**; all-facts recall is secondary, always printed with its ceiling |
| 3 | Scope | A **general rule**; aioquic w02-11 is the first instance (MARK has no dataset) |
| 4 | Tip-source leak | **In scope** |
| 5 | Tickets | The nine charted below |
| 6 | Execution | **$0 build inside the map, ticket 09 only** (dataset as a map asset; re-score by script). Changes to ai_rfc's scorer are **written as a spec and handed off**, never made here |
| 7 | SP7d held commits | The Phase 5 write-up and the `JUDGE_DRAFT_TIMEOUT_S` comment stay held until 09's numbers exist |

**Standing rules.** Never re-run `audit` or `analyze` against pilot data. `ai-rfc experiment
ground-truth` writes only to a named `--out`; point it inside this map's `research/` or
`prototypes/`. Nothing here spends. Read ai_rfc code at `<pin>`, not `<ai_rfc>`.

**Skills.** Grilling tickets: `mattpocock-skills:grilling` + `mattpocock-skills:domain-modeling`.
Prototype: `mattpocock-skills:prototype`. Research: `research`.

**Glossary (provisional).** It moves into `<ai_rfc>/CONTEXT.md` once the owed-fixes row lands; use
these words in tickets.
- *window*: the ordinal range of clusters a run works.
- *anchor commit*: the commit at which a dataset's facts are true. For a window, this is the last
  member commit of its last cluster (ticket 01).
- *declared spec version*: the spec version the code itself names at the anchor commit, through an
  ALPN or version constant, or an explicit reference to a versioned document (ticket 07). A document
  the code never names doesn't count.
- *citation*: a fact's pointer to the section of its declared spec version that states its value,
  verified against pinned spec text.
- *future material*: anything describing the repository after the window's end commit (ticket 05).
- *future-free workspace*: a run workspace built so that it holds no future material.
- *touched*: a run touched future material when a tool result delivered future content (not merely a
  file name) to the model.
- *attempted*: the draft names a fact's symbol with a value of the right shape nearby (ticket 06).
- *named*: the draft names a fact's symbol with no such value nearby. It is a diagnostic, and is
  neither attempted nor absent.
- *shown material*: the lines that in-window cluster diffs add or change, which are the lines the
  agent may anchor a claim to (ticket 02).
- *reachable fact*: a fact whose own source line at the anchor commit appears among the shown
  material for the same file. This is decided once per window (ticket 02).
- *reachable recall*: facts recovered ÷ reachable facts.
- *all-facts recall*: facts recovered ÷ scored facts.
- *ceiling*: reachable facts ÷ scored facts, the most all-facts recall can reach.

## Decisions so far

<!-- one line per closed ticket: [title](issues/NN-slug.md): gist -->

- [01 — What is a window's ground truth anchored to?](issues/01-what-is-ground-truth-anchored-to.md):
  **the code at the window's end**, meaning the last member commit of its last cluster (`509065a` for
  w02-11). Every fact must cite the spec version the code declares there (h3-22 for w02-11), and the
  citation is verified mechanically against pinned spec text. A fact whose code and spec disagree is
  excluded with its reason. The RFC-final set is kept, renamed to its anchor (`6d36838`). This amends
  spec D44 and SP7d U3, and the D-row is owed through 09.
- [02 — What counts as reachable?](issues/02-what-counts-as-reachable.md): **a fact is reachable when
  its own source line at the anchor appears as an added line in an in-window cluster's diff of the
  same file.** It is decided once per window. Context lines, removed lines and PR text don't count.
  w02-11: 26 of 26 reachable via c0005, so its ceiling is 1.0.
- [03 — How often would scoring a bare decimal near a symbol be wrong?](issues/03-how-often-is-a-bare-decimal-wrong.md):
  **always, here.** No genuine decimal statement of any setting or stream type exists in the window's
  diffs (13/13 and 77/77 unrelated) or in the drafts (122 of 450 equal only by coincidence, such as
  `ai_rfc:h3.1` or `HTTP/3`). Admitting decimals scores noise, and narrowing the window doesn't help.
  **Side finding:** `_tokens_near` slices before `findall`, so a hex token that straddles the slice
  end is cut (`0x10A` becomes `0x1`) and can be counted a match. That fix belongs in 09's spec.
- [04 — What reads the pristine clone's working tree?](issues/04-what-reads-the-clone-working-tree.md):
  **no production code reads `clone/` file content.** Consumers read git objects, and some require
  HEAD = corpus tip. The exceptions are the `pristine.sha256` seal (it covers every `clone/` file),
  the anchor tests (they read an older tree, `~/arfc-experiments/…`), and every arm's unconfined
  `Read`/`Grep`/`Glob`. A late checkout in `workspace prepare` (after `views --verify`, before the
  seal) is possible. **The leak is wider than `clone/`:** `cluster_get` serves out-of-window cluster
  diffs with no window check (c0120's diff holds `H3_NO_ERROR = 0x100`), and arm C's `git` reaches
  tip objects. Neither v2 run read any tip-source content.
- [05 — How is the tip-source leak closed?](issues/05-how-is-the-tip-leak-closed.md): **anything
  after the window's end is future material**, reachable by five routes: `clone/`, out-of-window
  clusters, forge, corpus and git. The run gets a **future-free workspace**, with a transcript audit as
  the backstop. "Touched" means future content reached the model; a bare file name doesn't count. The
  old drafts stand only after an audit (task 12). Feasibility is research 11, and the fix goes into
  09's hand-off spec.
- [11 — Can a future-free workspace keep the window's cluster ids?](issues/11-can-a-future-free-workspace-keep-cluster-ids.md):
  **yes, with conditions.** A real offline prepare cut at `509065a` reproduced c0001–c0011 byte for
  byte. It produced no clusters after the end, and its clone holds only the 3,624 objects reachable
  from the end. Ordinals are first-parent spine positions from the root (`timeline/build.py:50-63`).
  The conditions:
  - cut at the window top cluster's last member, asserted against a full-timeline pass;
  - keep every merged PR that landed by the end;
  - clone with `--no-local --revision=<end>` and remove `origin`;
  - assert the object set.

  This belongs in `workspace prepare`, not `copy_workspace`. Repositories outside the workspace are
  still reachable by absolute path, so the audit stays.
- [06 — When is claim accuracy reported?](issues/06-when-is-claim-accuracy-reported.md): **always
  with its attempted and reachable counts**, and no threshold; broken down per fact kind. A symbol
  named without a value is a separate diagnostic (*named* is not *missed*), which moves neither recall
  nor accuracy. How `analyze` and the report present all this graduated to ticket 13.
- [07 — How is ground truth built for a target with no published spec?](issues/07-ground-truth-without-a-published-spec.md):
  **a spec counts as declared only when the code names it** (an ALPN or version constant, or an
  explicit reference to a versioned document). MARK names none: its own `API_Doc_classification.md`
  is named by no code, and its constants are all decimal or string. So MARK has **no dataset**, its
  recall is unmeasured (`None`, never 0), and it is evaluated by form metrics and the judge.
- [10 — Fetch and pin the draft texts w02-11 cites](issues/10-fetch-and-pin-cited-drafts.md):
  **pinned** in [assets/specs/](assets/specs/README.md) with sha256: draft-ietf-quic-http-22, plus
  qpack-10 (the draft http-22 cross-references, published after the window's end) and qpack-09 (the
  draft that existed at the time). Which QPACK draft to cite is left undecided; it doesn't matter for
  w02-11, which has no QPACK facts. **All 26 candidates agree** with http-22 (17 in §8.1, 9 in
  §7.2.x), so 01's ruling 5 excludes nothing. Ticket 08 is now unblocked.
- [08 — What does a w02-11 dataset built to the rule look like?](issues/08-what-does-a-window-dataset-look-like.md):
  **the prototype shape stands** ([prototype](prototypes/08-window-dataset/README.md)): 26 cited,
  reachable hex facts plus 8 decimal entries kept for disambiguation. 09 quotes the cited spec line as
  each statement, and **pilot A2 joins**. Provisional scores are pilot v1 A1/A2 **11, 11**, v2 A1/A2
  **9, 10** of 26 (ceiling 1.0, accuracy 1.000). The old dataset reproduces SP7d's 8/35, and the
  truncation fix changes nothing.
- [12 — Audit the pilot and v2 transcripts for future material](issues/12-audit-old-transcripts-for-future-material.md):
  **all four drafts touched future material, through `corpus_query` only**: 1, 2, 2 and 6 results
  carried commit metadata from after the end. **None contains a scored fact's name or value.** No
  run read changed clone files, out-of-window clusters, the forge or git. **User ruling:** the four
  drafts are re-scored in 09, labelled as touched, and 05's rule stands for future runs. The corpus is
  the route that actually leaked, so 09's future-free prepare must truncate it too.
- [13 — How do `analyze` and the campaign report present ground truth?](issues/13-how-analyze-presents-ground-truth.md):
  **`analyze` scores every run's final draft by default** (the one at `latest_tag`) whenever a dataset
  exists for the campaign's target and exact window. The report gets a "Ground truth" section: per
  run and per kind, and per arm as mean / min with pooled accuracy. A missing dataset shows "—" with
  its status, never 0. **Touched runs are flagged and left out of arm rows.** Per-revision scoring is
  out of scope.
- [09 — Build the w02-11 dataset, re-score the pilot and v2 drafts, and write the scorer-change spec](issues/09-build-dataset-rescore-and-spec.md):
  **done.** The [dataset](assets/09/aioquic-w02-11-at-509065a.yaml) has 26 cited, reachable, agreeing
  facts, with statements quoted from the spec. [Re-scored](assets/09/rescore.md) on the valid
  yardstick: pilot v1 **11, 11** vs v2 **9, 10** of 26, all labelled touched. The
  [hand-off spec](../../docs/superpowers/specs/2026-09-21-arfc-ground-truth-yardstick-design.md) is in
  PANTHER, uncommitted.

## Not yet specified

<!-- empty: the last item (judge reachability) was ruled out of scope on 2026-09-21 -->

## Out of scope

- **Changing the agent so it records reachable enums.** A1 read the 2019 `ErrorCode` enum in c0005
  and never registered a structure. That is a real behaviour gap, but this map measures; it does not
  tune the agent.
- **Moving the experiment to a later window** where the RFC-final facts exist (the `H3_*` codes only
  from c0120). The user chose to fix the yardstick, not to move the target.
- **Per-revision scoring** (score each revision against the code at its own cluster). Ruled out by
  [13](issues/13-how-analyze-presents-ground-truth.md): the destination is a yardstick for a run's
  final draft, and scoring every revision needs a dataset anchored at each cluster's end, which is a
  new effort.
- **Making the blinded judge window-aware.** Ruled out by the user on 2026-09-21, while planning 09.
  The judge grades `completeness` (`JUDGE_DIMENSIONS`) without knowing the window, and telling it the
  window would weaken its blinding. Instead, the hand-off spec (§6.4) requires the report to state
  that judge completeness is not comparable across windows of different sizes. The Main Campaign map
  may take this up.

## Status

**Destination reached on 2026-09-21. Every ticket is resolved, and nothing is left in Not yet
specified.** The hand-off is
[`docs/superpowers/specs/2026-09-21-arfc-ground-truth-yardstick-design.md`](../../docs/superpowers/specs/2026-09-21-arfc-ground-truth-yardstick-design.md).
Implementing it is ai_rfc work for a future row, not part of this map. The map and the spec were
committed in PANTHER `6b2e70f14`.

**After the map (2026-09-22).** The user settled research 11's open questions in a prevention
grilling, and the spec's §7, §11 and §8 (a second D-row) record the rulings. Two plans implement
the spec:
- `docs/superpowers/plans/2026-09-21-arfc-ground-truth-measurement.md` (PANTHER `e6e7918b1`).
  Its Task 5 was amended so that only clusters after the window's top count as future.
- `docs/superpowers/plans/2026-09-22-arfc-future-free-workspace.md`, which runs after it.

Both wait for the owed-fixes row. One finding went to the Main Campaign map rather than into
either plan: that map scores aioquic at the c0011 tag inside w02-31, and c0020 renumbers 17 of the
w02-11 dataset's 26 scored facts.
