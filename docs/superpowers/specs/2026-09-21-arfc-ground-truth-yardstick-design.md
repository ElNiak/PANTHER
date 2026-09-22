# ai_rfc ground-truth yardstick — design

Status: **hand-off spec, not implemented.** Written 2026-09-21 by ticket 09 of the wayfinder map
"Ground-Truth Yardstick" (`.scratch/ground-truth-yardstick/map.md` in the `iut-ai-rfc` worktree).
Every requirement below is a user ruling recorded on one of that map's tickets, which are linked by
name. Code is cited **by function name at ai_rfc `main` `2c768b5`**, because another session (the
owed-fixes row) is changing these files. Line numbers are given only where they help find a function
at that commit.

**Amended 2026-09-22.** §7, §8, §9, §10 and §11 carry the prevention rulings made with the user
that day, which settle research 11's open questions. The two plans that implement this spec are
`docs/superpowers/plans/2026-09-21-arfc-ground-truth-measurement.md` (§3–§6, §7.3, §8–§10) and
`docs/superpowers/plans/2026-09-22-arfc-future-free-workspace.md` (§7.1, §7.2, §7.4 and the
prevention half of §7.3).

`<map>` = `.scratch/ground-truth-yardstick/` in the `iut-ai-rfc` worktree.
`<ai_rfc>` = `panther/plugins/services/testers/ai_rfc/`.

## 1. Why

SP7d scored three aioquic w02-11 drafts (pilot v1 A1, v2 A1, v2 A2) against
`ai_rfc/experiment/groundtruth/aioquic-w02-11.yaml` and got **8/35 on every draft**. The result looked
like "v2 recovers no more facts than v1". It was a **ceiling**:

- **The dataset describes the wrong code.** It is anchored at `commit: 6d36838…` (aioquic's 2025
  tip) and built from the final RFCs, but the window ends in 2019 at `509065a`, where the code states
  `HTTP_*` draft-22 error codes and decimal settings.
- **No draft could reach the missed facts.** The 27 missed facts first exist in clusters c0013–c0241,
  all outside the window.
- **The scorer couldn't recognise what the drafts did say.** It scores hex values only, and its
  `H3_*` patterns can't match `HTTP_*` names.

Measured on the valid yardstick this spec defines (§12), **the v1 pilot drafts recover slightly more
facts than the v2 drafts** (11, 11 vs 9, 10 of 26).

Three further defects were found on the way:
- **The scorer can count a truncated number as a match** (§4.6).
- **Runs can see the future:** every run workspace exposes the repository's future through five
  routes, and one route, `corpus_query`, leaked in all four runs audited (§7).
- **The judge's `completeness` is not comparable across windows** (§6.4).

## 2. Rulings index

| Ticket | Ruling (gist) |
|---|---|
| [01 — What is a window's ground truth anchored to?](../../../.scratch/ground-truth-yardstick/issues/01-what-is-ground-truth-anchored-to.md) | The code at the window's end (the last member of its last cluster). Every fact cites the spec version the code declares, verified mechanically against pinned text. A disagreeing fact is excluded with its reason. The RFC-final set is kept, renamed to its anchor. |
| [02 — What counts as reachable?](../../../.scratch/ground-truth-yardstick/issues/02-what-counts-as-reachable.md) | A fact is reachable when its own source line at the anchor is an added line in an in-window cluster diff of the same file. Decided per window. |
| [03 — How often would scoring a bare decimal be wrong?](../../../.scratch/ground-truth-yardstick/issues/03-how-often-is-a-bare-decimal-wrong.md) | Always, on w02-11. Decimals stay unscored. The scorer's edge-truncation bug was found here (§4.6). |
| [04 — What reads the pristine clone's working tree?](../../../.scratch/ground-truth-yardstick/issues/04-what-reads-the-clone-working-tree.md) | No production code reads `clone/` file content. The leak is wider than `clone/`. |
| [05 — How is the tip-source leak closed?](../../../.scratch/ground-truth-yardstick/issues/05-how-is-the-tip-leak-closed.md) | Anything after the window's end is future material. Runs get a future-free workspace plus an audit backstop. "Touched" means future content reached the model. |
| [06 — When is claim accuracy reported?](../../../.scratch/ground-truth-yardstick/issues/06-when-is-claim-accuracy-reported.md) | Always with its attempted and reachable counts, and per kind. *Named* is a diagnostic. |
| [07 — How is ground truth built for a target with no published spec?](../../../.scratch/ground-truth-yardstick/issues/07-ground-truth-without-a-published-spec.md) | A spec is declared only when the code names it. MARK names none, so it has no dataset. |
| [08 — What does a w02-11 dataset built to the rule look like?](../../../.scratch/ground-truth-yardstick/issues/08-what-does-a-window-dataset-look-like.md) | The prototype shape stands. Statements quote the cited spec paragraph. Pilot A2 joins the comparison. |
| [10 — Fetch and pin the draft texts w02-11 cites](../../../.scratch/ground-truth-yardstick/issues/10-fetch-and-pin-cited-drafts.md) | http-22, qpack-10 and qpack-09 are pinned with sha256. 26 of 26 facts agree. |
| [11 — Can a future-free workspace keep the window's cluster ids?](../../../.scratch/ground-truth-yardstick/issues/11-can-a-future-free-workspace-keep-cluster-ids.md) | Yes: a truncated prepare reproduced c0001–c0011 byte-equal. Conditions in §7.1. |
| [12 — Audit the pilot and v2 transcripts for future material](../../../.scratch/ground-truth-yardstick/issues/12-audit-old-transcripts-for-future-material.md) | All four drafts touched future material through `corpus_query` only, with no scored fact in it. They are scored, labelled. |
| [13 — How do `analyze` and the campaign report present ground truth?](../../../.scratch/ground-truth-yardstick/issues/13-how-analyze-presents-ground-truth.md) | Scored by default; a report section; touched runs left out of arm rows; per-revision scoring is out of scope. |
| Prevention grilling, 2026-09-22 (with the user; no ticket, the map was complete) | Prepare derives the end and builds the pristine there, asserting the window's rows byte-equal; every clone is made at its pin with no remote; forge rule R1 with `derived_from`/`truncated_at`; git honesty asserted everywhere with a recorded digest; a path guard for every file tool and every Bash path; `cluster_get` refuses only clusters after the window's top. §7, §11. |

## 3. Dataset format and selection

### 3.1 Format

The reference instance is `<map>/assets/09/aioquic-w02-11-at-509065a.yaml`, built by
`<map>/assets/09/build_dataset.py`. The format extends today's; existing keys keep their meaning.

**Top level:**
- `repository`
- `target`: the campaign target name, e.g. `aioquic`
- `window`: `[a, b]`
- `commit`: the **anchor**, the last member commit of cluster *b* (01)
- `declared_spec`: `version`, plus `evidence` as `file:line` strings showing where the code declares
  it (07)
- `specs`: the pinned spec file name → sha256
- `entries`

**Per entry:**
- `id`, `symbol`, `value` (spelled as the code spells it), `kind`
- `source {path, line}`: at the anchor
- `statement`: the cited spec paragraph, quoted and whitespace-collapsed (08, ruling 2)
- `citation {doc, section, line}`, and `citation_agrees`
- `reachable {cluster, diff_line}`, or `null` (02)
- `unscored_reason`: only on entries the scorer cannot score

Decimal-valued entries **stay in the dataset**, unscored. The scorer uses every entry's symbol to tell
a symbol from part of a longer one (`_inside_a_longer_symbol`), and dropping them would bring back the
"`SETTINGS` inside `HTTP_SETTINGS_ERROR`" misreads.

### 3.2 Selection (13)

`load_dataset` loses its hard-coded default (`DATASET = "aioquic-w02-11.yaml"`). A dataset is
selected by the `target` and `window` it declares: an **exact window match**. If nothing matches, the
status is `no dataset for this window` (§6.2).

### 3.3 The existing dataset (01, ruling 7)

- **Rename** it to its anchor: aioquic HTTP/3 at `6d36838`, e.g. `aioquic-h3-at-6d36838.yaml`, with
  `window` set to the window whose end is `6d36838`.
- **Never select it for w02-11 again.** SP7d's scores against it stay on record, labelled
  ceiling-bound.

### 3.4 Datasets for new targets (01, 07)

A target gets a dataset only if its code **names** a spec at the anchor: an ALPN or version constant,
or an explicit reference to a versioned document. A repository document the code never names doesn't
count. MARK names none (checked at `b901f36`), so it has no dataset.

## 4. Scoring

### 4.1 Citation verification (01, rulings 5–6)

For every scored entry, a test checks that `value` appears in the pinned spec text at `citation.line`,
**compared as integers**. A fact whose code and cited spec disagree is kept out of the scored set, with
its reason in `unscored_reason`. On w02-11 all 26 agree (10).

### 4.2 Anchor verification by object, not working tree (04, open question 7)

`resolve_anchors(entries, clone)` reads files from a working tree. Today the anchor tests read
`~/arfc-experiments/…`, a tree nobody prepares any more, and they skip silently if it moves. The
change: resolve `git show <dataset.commit>:<source.path>` and check that line `source.line` states
the value. This works in any clone that holds the anchor object.

### 4.3 Reachability (02)

For each scored entry, it is reachable if its source line's content, whitespace-stripped, equals an
**added** line (`+`, excluding the `+++` header) in the `span.diff` of some cluster whose ordinal is
in `[a, b]`, under that diff's header for the same path. Defaults:
- follow renames made inside the window, using the path the diff names;
- out-of-window clusters are never shown material.

It is **decided per window**, stored in the dataset (`reachable`), and computed when the dataset is
built. On w02-11 all 26 are reachable via c0005.

### 4.4 Figures (01, 02, 06)

| Figure | Definition |
|---|---|
| reachable recall | matched reachable facts ÷ reachable facts. **Primary.** |
| all-facts recall | matched ÷ scored. Secondary; always printed with the ceiling. |
| ceiling | reachable ÷ scored |
| claim accuracy | matched ÷ attempted. **Always printed with "N attempted of R reachable"**; no threshold; `None` when nothing was attempted. |
| per kind | matched / mismatched / named / absent for each `kind` |

Outcomes per scored fact:
- `matched`, `mismatched`;
- **`named`**: the symbol appears, not inside a longer dataset symbol, with no value of the right
  shape nearby. It is a diagnostic: not an attempt, and it moves neither recall nor accuracy;
- `absent`.

Today's `missed` splits into `named` and `absent`. The name `claim_accuracy` stays, because
"precision" is the judge's word.

### 4.5 Unscored values (03)

Only hex values are scored, as today (`_value_shape`). Admitting decimals scored pure noise on w02-11:
- 13/13 setting pairs and 77/77 stream-type pairs near a symbol in the window's diffs were
  unrelated;
- 122 of 450 draft pairs were equal only by coincidence (`ai_rfc:h3.1`, `HTTP/3`).

### 4.6 Fix: whole tokens in `_tokens_near` (03)

`_tokens_near` runs `token.findall(body[start : match.end() + NEARBY_CHARS])`. A token that straddles
the slice's end is cut: `0x10A` 117 characters after the symbol is read as `0x1`, and `score_draft`
can report a false **match**. Fix: find the tokens in the whole body, and keep those whose span meets
the window. Measured on the four drafts, against both the old and the new dataset, the fix changes
**no outcome**, so no existing result depended on the bug.

## 5. The `ground-truth` verb (`_ground_truth_run`, `_write_ground_truth` in `experiment/cli.py`)

- **JSON** gains:
  - `reachable_recall`, `all_facts_recall`, `ceiling`;
  - `claim_accuracy` plus its counts, `attempted` and `reachable`;
  - `per_kind`;
  - `named`, and `absent` (split from `missed`);
  - the dataset's `commit`, `window` and `declared_spec`.
- **Text** leads with reachable recall, then all-facts recall with the ceiling, then claim accuracy
  with its counts, then the per-kind lines, then named.
- The verb keeps working on any single draft, and takes a dataset by name or by target and window.

## 6. `analyze` and the campaign report (13)

### 6.1 Scoring by default

`analyze_run` (`experiment/metrics.py`) adds a `ground_truth` record beside `quality`. It scores the
draft at `draft.gate.latest_tag`, the one `final_build` uses, whenever §3.2 finds a dataset. It is $0
and calls no model, so there is no flag.

### 6.2 Status vocabulary

The status follows the build-status pattern, a status column beside an error column:
- `scored`;
- `no declared spec` (MARK);
- `no dataset for this window`;
- `draft unreadable` (e.g. a recorded tag the draft repository doesn't hold, as MARK's `-38`).

A missing figure renders as "—" with its status. **It is never 0.**

### 6.3 Report section (`render_report`, `experiment/report.py`)

A **"Ground truth"** section, using the shared escaper at its new home, `ai_rfc/markdown.py`
(`9c61fab`):
- **per run:** status, reachable recall "11/26 (0.423)", ceiling "26/26", claim accuracy
  "1.000 (11 attempted of 26 reachable)", named, and the **future-material verdict** (§7.3);
- **per kind:** one table;
- **per arm:** reachable recall as mean / min (the "completed" pattern), with claim accuracy from
  pooled counts. **Touched runs are left out, and the row says how many** (13, ruling 3).

### 6.4 Judge caveat (map scoping ruling, 2026-09-21)

The report states, beside the judge's figures, that the blinded judge's `completeness`
(`JUDGE_DIMENSIONS`, `experiment/cli.py`) is graded **without knowledge of the window**. It is
therefore **not comparable across windows of different sizes**. Making the judge window-aware would
weaken its blinding, so it is out of scope here.

## 7. Future-free workspaces and the audit backstop (05, 11, 12)

**Future material** is anything describing the repository after the window's end commit. A run
workspace carries it by five routes:
1. `clone/` at the tip (any arm's `Read`/`Grep`/`Glob`);
2. `clusters/` after the window's top: `cluster_get` has no window check
   (`server/core/queries.py` `cluster_get`), and `Read` can open them directly;
3. the forge snapshot (`forge/…/pulls.jsonl`, `comments.jsonl`);
4. the corpus (`corpus/`, and `corpus_query` over all 1,182 commits);
5. git objects (arm C's `Bash(git *)`).

**Measured in ticket 12: route 4 leaked in all four audited runs** (1, 2, 2 and 6 results), from
open-ended queries such as `authored_at > '2019-09-02'` or `ORDER BY rowid DESC`.

**Settled with the user on 2026-09-22** (§11). A cluster *before* the window is the run's past and
its context. Only what follows the window's end is future material, so every rule below that names
clusters names those after the window's top.

### 7.1 Future-free `workspace prepare` (11; rulings of 2026-09-22)

The cut belongs in `workspace prepare` (`experiment/workspace.py` `prepare`), **not** in
`copy_workspace`: there, the HEAD guards and the seal (`write_digest`) hold by construction. A real
offline prepare at `509065a` measured it, reproducing c0001–c0011 byte-equal.

- **Prepare derives the end; the operator never names it.**
  - A resolution pass runs `acquire`, history and timeline over the operator's pin, in scratch
    space.
  - The end is the last member of the window's top cluster H, read as cluster H+1's
    `spine_prev_sha`. All 341 aioquic boundaries satisfy this.
  - When H is the timeline's last cluster, or the config declares no window, the end is the pin
    itself and nothing is cut.
  - The cut is **always on**; no flag keeps the full history.
- **The pristine is built at the end.** `initialise` receives the config with `source.pin` replaced
  by the end. The sealed `recon.yaml` therefore names the real `source.repo` and pins the end.
  `pristine.json` gains a `cut` block recording:
  - the operator's pin and its resolution;
  - the end;
  - the top cluster;
  - what the forge cut kept and dropped.
- **Prepare asserts that the cut kept the window.** Pass 2's `clusters.jsonl` must equal pass 1's
  rows 1..H, and its `members.jsonl` pass 1's rows for those clusters, byte for byte. A mid-epoch cut
  keeps an id while it shrinks the cluster; this assert is the guard against that.
- **The corpus holds only commits up to the end.** It is built from the clone at the end, and
  prepare asserts that `corpus/commits.jsonl` equals the resolution pass's `git rev-list <end>`. This
  is the route that leaked.
- **Every clone holds only its pin's history.** `acquire` (`lifecycle/workspace.py`) runs
  `git clone --no-local --revision=<pin>`, then `git remote remove origin`, for every workspace,
  production `ai-rfc init` included.
  - A pin is a branch, a tag or a full commit id. An abbreviated id is refused; git 2.55 reports
    "Remote revision … not found".
  - git ≥ 2.49 is required, and nothing falls back to another route.
  - `--depth` is never used, because the substrate refuses shallow clones.
- **Forge rule R1:**
  - Keep a pull if and only if it merged and its landing commit is an ancestor of the end. The
    landing commit is `squash_commit_sha`, else `merge_commit_sha`, exactly as `_match_pulls` reads
    it.
  - Keep a review or comment only if its pull is kept and its own timestamp is at or before the
    end's committer time. An undated one is dropped.
  - The derived snapshot keeps `fetched_at` and sets `clone_head` to the end. It records
    `derived_from` (the source snapshot's directory name and `meta.json` sha256) and `truncated_at`
    (the end), and `adopt_snapshot` carries both.
  - **Disclosed, because it can't be detected:** a kept pull's title or body edited after the end.
- **Git honesty is asserted everywhere.** Prepare, `copy_workspace`, `reseal` and the post-run audit
  all assert three things about the clone:
  - it has no remote;
  - it has no `objects/info/alternates`;
  - it stores exactly the objects reachable from HEAD.

  `pristine.json` records the object set (`clone_objects`: count and digest), and `copy_workspace`
  compares it. The seal (`write_digest`) never covers `.git`, so this is the only check there.
- **Older pristines are refused.** Every pristine prepared before this lands has an `origin` remote,
  and aioquic's also store objects past their end, so `copy_workspace` refuses them. They remain
  read-only evidence. The Main Campaign re-prepares MARK w01-69, which needs no cut because it ends
  at the clone head; that map's session was told on 2026-09-22. The interview fixture that the
  optimize route copies is rebuilt the same way whenever it is next needed.
- **The audit stays (§7.3).** Repositories outside the workspace are still reachable by absolute
  path. §7.4 closes that for the tools the harness controls.

### 7.2 Clusters after the window

With a future-free prepare, no cluster after the window's top is left to serve. `cluster_get`
still **refuses an ordinal above the window's top**, as defence in depth; the window is read by
`ledger.window_of`. A cluster **before** the window, such as c0001 (pre-seeded), stays readable,
because it is the run's past and its context. The owed-fixes commit `e16bff2` guards path joins, and
this is a separate window check. (Amended 2026-09-22 from "refuse an ordinal outside the run's
window".)

### 7.3 Audit backstop

`audit_events` (`experiment/audit.py`) records **no path for read tools** today. The backstop must:
- record each `Read`/`Grep`/`Glob` path;
- classify every tool result by route, using ticket 12's method
  (`<map>/research/12-audit/audit.py`): future shas against `git rev-list <end>`, dates after the end,
  cluster ids above the window's top (amended 2026-09-22 from "out-of-window"), and clone files that
  differ from the end;
- check the run's clone for git honesty (§7.1). A clone that stores an object HEAD doesn't reach,
  or that has gained a remote or alternates, makes the run **touched** through route 5, with the
  problems as its evidence;
- emit a per-run verdict, **clean** or **touched**, with the evidence.

"Touched" means future **content** reached the model; a bare file name in a listing doesn't count
(05, ruling 3). `analyze` shows the verdict (§6.3), and arm rows leave touched runs out.

### 7.4 The path guard (rulings of 2026-09-22)

The `PreToolUse` guard (`driver/guard.py`, mounted by `driver/enforcement.py` `render_settings`)
confines Bash to an arm's command prefixes, and today that is all it does. It gains the run's
workspace as an argument, and it refuses:
- `Read`, `Grep`, `Glob`, `Edit` and `Write`, for **every arm**, when the path they name resolves
  outside the run's workspace, following symlinks. The path is `file_path`, `path`, or a `pattern` or
  `glob` that is absolute or climbs with `..`.
- A Bash command any of whose path arguments resolves outside the workspace. This covers arm C's
  `git`, `sqlite3` and raw-substrate commands, and arm B's `ai-rfc --config <another workspace>`,
  which reaches the same kind of full pristine.
- An arm C `git` subcommand that reaches another repository, whatever its arguments: `archive`,
  `bundle`, `clone`, `config`, `fetch`, `ls-remote`, `pull`, `push`, `remote`, `submodule`,
  `worktree`.

The audit reads calls with the same predicate. An executed out-of-workspace call is an integrity
violation, and a blocked one is a bypass attempt, as blocked Bash is today.

A preflight check measures whether the installed CLI honours an exit-2 block on these tools before
any campaign runs. It makes two live calls, which spend, so the plan stops for approval. Arm
enforcement changes, so the Main Campaign's parity work covers it; that map's session was told on
2026-09-22.

## 8. D-row (draft text, to be numbered when it enters the draft-quality spec)

> **D-(next) amends D44 and SP7d U3 — a window's ground truth is the code at the window's end.** A
> window's dataset is anchored at the last member commit of the window's last cluster, not at the
> pinned checkout's tip. Every scored fact cites the spec version the code declares at that anchor
> (ALPN or a version constant, or an explicit reference to a versioned document), and is checked
> mechanically against pinned spec text, comparing values as integers. A fact whose code and cited
> spec disagree is excluded, with its reason recorded. A target whose code declares no spec has no
> dataset: its recall is unmeasured, never zero. Recall is reported first as **reachable recall**
> (facts whose source line an in-window diff adds), with all-facts recall and the ceiling beside it.
> The existing `aioquic-w02-11.yaml` described the 2025 tip, so it is renamed to its anchor, and the
> SP7d ground-truth results against it are ceiling-bound (8/35 was the most any w02-11 draft could
> score).

> **D-(next+1) — a windowed pristine holds nothing after its window's end** (added 2026-09-22).
> `workspace prepare` derives the end commit from a full-history pass: the last member of the
> window's top cluster. It builds the pristine at that commit and asserts that the window's
> clusters are byte-equal to that pass. Every clone is made with `--no-local --revision=<pin>` and
> keeps no remote. Its forge snapshot keeps only pulls that landed by the end, and only discussion
> dated by then. The pristine record seals the clone's object set, and every copy is checked against
> it. `cluster_get` refuses a cluster after the window's top. Every file tool and every Bash path is
> confined to the run's workspace.

## 9. Tests that pin it

- **Dataset integrity:**
  - every scored entry's `source` resolves at `commit` through `git show`, and states `value`;
  - every `citation` line in the pinned spec states `value`, as an integer;
  - the `specs` sha256 matches the pinned file.
- **Selection:**
  - an exact target+window match returns the dataset;
  - no match gives status `no dataset for this window`;
  - a target with no declared spec gives `no declared spec`.
- **Reachability:** a fixture diff where the fact's line is only in a removed line → not reachable;
  added → reachable.
- **Outcomes:** `named` (symbol, no value), `absent`, and `matched`/`mismatched` on fixtures; a
  symbol inside a longer dataset symbol is not `named`.
- **Truncation regression:** `0x10A` placed so that it straddles the window end must not match
  `0x1`.
- **Figures:**
  - claim accuracy prints its counts;
  - `None` when nothing is attempted;
  - per-kind counts sum to the totals.
- **analyze/report:**
  - status and error columns;
  - "—" never 0;
  - a touched run is excluded from the arm row and counted.
- **Prepare:**
  - the rows-1..H assert, including that a cut which changes a kept cluster is refused;
  - the corpus holds no commit after the end;
  - the object-set assert and the recorded digest;
  - no `origin` remote;
  - the sealed pin is the end, and `pristine.json` names the cut;
  - a window that ends at the last cluster is not cut;
  - the forge cut keeps and drops rows by R1;
  - in-window ids byte-equal to a full prepare.

  The fixture is a small synthetic repository with an epoch, a merge PR and a forge-squash PR. The
  aioquic reproduction is an acceptance step and never a test fixture, because the evidence
  pristines are read-only.
- **Copies:** `copy_workspace` and `reseal` refuse a clone with a remote, with alternates, with an
  object HEAD doesn't reach, or with an object set that differs from the record, and they refuse a
  pristine that records none.
- **Guard:**
  - each file tool is refused outside the workspace, and a symlink out of it is followed;
  - a Bash path argument outside the workspace is refused;
  - arm C's repository-reaching git subcommands are refused;
  - the audit's in-arm verdict matches the guard's.
- **`cluster_get`:** an ordinal above the window's top is refused; one before the window is served.
- **Audit:** ticket 12's four transcripts (or fixtures cut from them) classify as it found. A clone
  that gained an object makes the run touched through route 5.

## 10. Documents to amend once this lands

- SP7d's recall reading. `<ai_rfc>/docs/experiments/2026-09-18-sp7d-instrument.md` is **not**
  amended: it is a recording, and it holds no ground-truth section. The 8/35 reading was only ever
  in the git-ignored SP7d ledger. The correction is published by the new dated
  `<ai_rfc>/docs/experiments/2026-09-21-sp7d-phase5.md` below. (Amended 2026-09-22.)
- `docs/superpowers/plans/2026-09-15-arfc-sp7d-deviations.md` (PANTHER): a deviation recording R93.
- The held SP7d Phase 5 write-up, `<ai_rfc>/docs/experiments/2026-09-21-sp7d-phase5.md`, which uses
  §12's figures and labels. It is drafted in the SP7d ledger and committed once the owed-fixes row
  lands.
- `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md`: both D-rows in §8.
- `<ai_rfc>/ai_rfc/experiment/README.md`: its enforcement section, which describes a guard that
  covers Bash only.
- The Main Campaign map's freeze ticket: its step 1b re-prepares MARK, and its parity work covers the
  path guard. Both were handed to that map's session on 2026-09-22.

## 11. Open questions (from research 11), resolved with the user on 2026-09-22

1. **Where the cut lives:** in `prepare`, which derives the end itself (§7.1). `acquire` clones every
   workspace at its pin with `--no-local --revision` and drops `origin`, so the pass at the end needs
   no scratch source and `acquire` no new parameter.
2. **Snapshot identity:** the derived snapshot's `meta.json` gains `derived_from` and
   `truncated_at`, carried by `adopt_snapshot`, and `pristine.json` records the cut as well.
3. **Forge edge rules:** R1. A pull merged after the end is dropped, and so is a never-merged pull.
   Discussion dated after the end, or undated, is dropped. Title and body edits after the end are
   disclosed as undetectable.
4. **Narrowing:** the path guard (§7.4), for every arm and every file tool, with arm C's
   repository-reaching git subcommands refused. Whether the CLI honours the block is a preflight
   check, which spends.
5. **Seal extension:** both. The honesty checks are asserted in prepare, `copy_workspace`, `reseal`
   and the audit, and the digest is recorded in `pristine.json`.
6. **Comparability:** a disclosure, not a decision. Old runs used full pristines (332 pre-seeded).
   Their in-window ids and diffs are identical, but any comparison of pre-seeded counts or digests
   says that the two kinds of pristine differ.
7. **Declared references:** the sealed `references.yaml` and `refcache/` are a bibliography, not
   material about the repository. They stay with ticket 01.

**Handed off, not resolved here (2026-09-22):**
- The Main Campaign scores aioquic at the c0011 revision tag inside a w02-31 window.
- c0020 renumbers every HTTP error code into draft-23's 0x100 range, which covers 17 of the w02-11
  dataset's 26 scored facts. c0021 adds the ALPN `h3-23` beside `h3-22`.
- Both clusters are inside w02-31, so the cut keeps them, and a run at c0011 can read them through
  `clone/` and `cluster_get`.
- The measurement plan scores final drafts only, and this map ruled per-revision scoring out of
  scope.
- The question therefore went to the Main Campaign map's session, which rules its secondary metric.

## 12. Results on w02-11 (ticket 09, $0)

From `<map>/assets/09/rescore.md`. **Every run is labelled "touched: future commit metadata through
`corpus_query`, no scored fact (ticket 12)".** Per 13, ruling 3, the arm rows therefore have no
figure.

| run | final draft | reachable recall | ceiling | claim accuracy | error codes m/mm/n/a | frame types m |
|---|---|---|---|---|---|---|
| pilot v1 A1 | tag -10 | 11/26 (0.423) | 26/26 | 1.000 (11 attempted of 26 reachable) | 2/0/0/15 | 9/9 |
| pilot v1 A2 | tag -11 | 11/26 (0.423) | 26/26 | 1.000 (11 of 26) | 2/0/0/15 | 9/9 |
| v2 A1 | tag -10 | 9/26 (0.346) | 26/26 | 1.000 (9 of 26) | 0/0/2/15 | 9/9 |
| v2 A2 | tag -10 | 10/26 (0.385) | 26/26 | 1.000 (10 of 26) | 1/0/1/15 | 9/9 |

The error-code column counts matched / mismatched / named / absent.

- **Frame types:** every draft states all nine.
- **Error codes:** both pilots state `HTTP_WRONG_STREAM (0x0A)` and `HTTP_UNEXPECTED_FRAME (0x13)`
  with values. v2 A1 names both without values; v2 A2 states one and names the other. 15 of 17 error
  codes appear in no draft.
- **Caution:** this is one window, two runs per side, and a gap of 1–2 facts.
- **Checks:** the old dataset reproduces SP7d's 8/35 with the same ids, and the §4.6 fix changes no
  outcome.
