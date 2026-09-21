# Arm prompt and surface diff, ai_rfc `8358238` (2026-09-21)

The asset of the ticket
[Diff the three rendered arm prompts](../../issues/02-diff-the-rendered-arm-prompts.md). It lists
what the three arms are **told** (prompt text), **shown** (tool descriptions and `--help`) and
**allowed** (allowlists), beyond invocation syntax. **It rules nothing**; the rulings belong to
[Rule each arm asymmetry](../../issues/04-rule-each-arm-asymmetry.md), and the arm C question to
[Does the main campaign include arm C](../../issues/17-does-the-main-campaign-include-arm-c.md).

## Provenance

- **Code:** ai_rfc `8358238` (the ARM-B fix), exported with `git archive` into the session
  scratchpad, outside any repository. The live tree was not used: the owed-fixes session had
  uncommitted edits in `server/core/*`, `server/paths.py` and `draft/gate.py`, which listing
  arm A's tools imports. `PYTHONPATH=<snapshot>` was checked to import `ai_rfc`,
  `ai_rfc.driver.render` and `ai_rfc.server.server` from the snapshot.
- **`campaign init` refused** at toolchain verification: "the example did not build offline
  (first): draft-todo-yourname-protocol: stage venue failed (exit 1); … stage kramdown-rfc failed
  (exit 1); … stage v2v3 failed (exit 1)" (toolchain `~/ai-rfc-experiments/tools/toolchain.json`,
  sha256 `97e4e644…d79ee`). The cause was not diagnosed; it matters to
  [Freeze prompts, pin code, and dry-run](../../issues/13-freeze-pin-and-dry-run.md). The campaign
  was frozen with `scripts/init_no_verify.py` instead. It parses the same argv with the snapshot's
  own experiment parser and calls `init_campaign(..., verify_toolchain=False)`, so everything but
  verification is the CLI's path:
  `campaign init --root <scratch> --id armdiff-8358238 --baseline
  ~/ai-rfc-experiments/pristine/aioquic-w02-11 --arms A,B,C --toolchain <above> --skip-parity
  --python <worktree .venv python>`.
- **The record** (`campaign.json`) reads target aioquic, window [2, 11], `claude-opus-5` at effort
  `high`, Claude Code **2.1.278**, session mode `single`, run order `B1 A1 C1 A2 C2 B2`. Those are
  the CLI's defaults, not decisions. `parity: null` because `--skip-parity` was passed; the parity
  audit is its own ticket. `git.ai_rfc: unknown` because the snapshot is deliberately not a
  repository (inside the worktree, `git describe` would have described PANTHER instead).
- **Checks** (`scripts/verify_prototype.py`): all nine prompt files match their `prompt_sha256`;
  `arm-B.md` carries both the code and the adr literal anchor, so the render is at or after
  `8358238`. `task.md`'s digest `05e731d3…f84539` equals the one the 2026-08-31 pilot froze: **the
  task prompt has not changed since the pilot.**
- **Surfaces** (`scripts/surfaces.py`, `COLUMNS=100`): `surfaces/arm-A-mcp-tools.json` holds the
  20 tools as the server lists them; `surfaces/arm-{B,C}-help.txt` holds the `--help` of every
  command the arm's slot table names; `surfaces/allowlists.json` holds each arm's tools, allowed
  tools and guard prefixes.

## Files

- `prompts/`: `arm-{A,B,C}.md` (loop), `consolidation-{A,B,C}.md`, `task.md` and the two task
  templates, as frozen.
- `diffs/loop-*.patch`: written by `campaign init` itself.
- `diffs/consolidation-*.patch`: written by `render.unified_diff`; `campaign init` writes none.
- **The diffs are for reading, not applying.** The single space on each blank context line was
  stripped (30 lines across the six files) because PANTHER's pre-commit `trailing-whitespace` hook
  would otherwise rewrite them. Its `end-of-file-fixer` also trimmed the extra blank line at the
  end of the three loop diffs and of `surfaces/arm-{B,C}-help.txt`. `campaign.json` records no digest for a diff. The prompts carry no
  trailing whitespace, so they are byte-exact and their digests check.

## Identical across arms (the baseline)

- **Everything outside the slot substitutions**: the loop and consolidation templates' own text,
  the `guidance` slot, and the bundled skill texts (`render.arm_prompt`, `render.py:640-681`).
  Every hunk in `diffs/` falls on a slot. The bundled texts are byte-identical across arms, but
  one of them is written for arm A (D16).
- **The task prompt** (`task.md`), and the shared sentence every arm reads in step 3: "A commit
  message stating a decision is an `adr` anchor".
- **Pure invocation syntax**: a tool call against a verb against a raw command for the same
  operation, "returns" against "prints", and the pagination flags against `sed -n`.

## Differences between arms (arm-differential)

Line numbers are in the snapshot's `ai_rfc/driver/render.py` unless another file is named. "C"
means `_RAW` plus the C table.

| # | What differs | Kind | Arms | Source |
|---|---|---|---|---|
| D1 | **Anchor shape in the claim step.** A gets a field list, `{evidence_class, locator, commit, line}`, with no literal and no class named. B gets two literal anchors, code and adr. C hand-edits `manifest.yaml`, and **no anchor field name appears anywhere in `arm-C.md`** (0 occurrences of `evidence_class`). C can learn the schema only from the workspace's existing manifest or from checker errors. | told | A, B, C | A `:382-387`; B `:306-313`; C `:138-141` |
| D2 | **Structure body fields, in the loop.** A is told "with the kind, title, section and members". B is told only `--json '…'`, and its `--help` says just "The structure body as JSON". A's MCP schema is also silent (`fields: object`). So in a cluster round, **A's knowledge comes from the prompt alone, and B has none** (0 occurrences of "members" in `arm-B.md`). Consolidation rounds differ: see D16. C: not available (D8). | told, shown | A, B | A `:362-365`; B `:285`; `surfaces/arm-B-help.txt` |
| D3 | **Optional claim fields.** A: "optional `intent`/`req_class`". B: `[--field intent=…]` in the prompt, though its `--field` help lists `req_class, intent, question-id, testable`. C hand-edits. | told, shown | A, B | A `:382-387`; B `:306-313` |
| D4 | **"The tag rebuilds the draft" is said twice to A.** A's build slot adds "`ai_rfc_revision_tag` runs it again and refuses on findings"; B's does not. Both tag slots say the tag builds. | told (minor) | A, B | A `:403-409`; B `:326-331` |
| D5 | **Prose editing.** A's preamble says to "edit prose with the Edit/Write tools". B's preamble does not. C's says "edit YAML by hand where no command exists". All three arms have `Edit`/`Write` (`driver/arms.py:21`). | told (minor) | A, B, C | A `:346-350`; B `:270-273`; C `:253-257` |
| D6 | **Where the draft stands, in a consolidation round.** A: `ai_rfc_status()`. B is told that no verb reports this round's changes and that it has no `git` to list tags (D16: `ai-rfc status` is the operator's ledger and needs a `recon.yaml`). C: `git … tag --list`. Consolidation prompts only; the loop does not use this slot. | told, allowed | A, B, C | A `:358-361`; B `:279-284`; C `:128-131` |
| D7 | **Corpus schema visibility.** Neither A's `ai_rfc_corpus_query` ("Run one SELECT over the corpus index (at most 200 rows)", `sql: string`) nor B's `corpus query` help names a table or column. C runs `sqlite3` directly and can read `.schema`. This confirms SP7d's report that its arm-A session guessed `commit_sha`, `parents` and `c.committed_at`. Whether A or B can reach `sqlite_master` through a SELECT was **not tested here**; that belongs to the parity audit. | shown | A, B against C | `surfaces/arm-A-mcp-tools.json`; `surfaces/arm-B-help.txt`; C `:137` |
| D8 | **The v2 surface is absent from C (spec D42).** Structure upsert, draft render, draft lint, draft build and the consolidation checkpoint and record are all "not available in arm C — skip this step". C's drafts cannot carry structures, and the protocol's "every tag compiles" guarantee does not hold for C. | told, allowed | C | C `:242-251` |
| D9 | **How a tag is made.** A and B: the tag verb runs the strict manifest gate, builds, tags, runs the strict citation gate and **deletes the tag on findings**. C: raw `git tag -a` "only after the strict manifest gate exited 0", with no build and no rollback. A C tag can exist that neither compiles nor passes the citation gate. | allowed | A, B against C | A `:410-…`; B `:332-337`; C `:170-173` |
| D10 | **Which cluster is next.** A and B: `cluster_next` computes the in-window, not-done cluster in code. C reads `timeline/clusters.jsonl` and applies the rule itself, so for C the window is enforced only by the prompt. | allowed | A, B against C | C `:127` (`_CLUSTER_NEXT_RAW`) |
| D11 | **Recording statuses.** A and B: a verb writes exactly the supported status. C hand-sets `status` in `manifest.yaml` from `out/report.json`. The guard does not inspect YAML content; the strict gate catches overstatement. | allowed | A, B against C | C `:147-150` |
| D12 | **Recording revisions and questions.** C appends `revisions.yaml` by hand, copying `checkpoint_manifest_sha256` from the checkpoint, and appends `questions.yaml` by hand; A and B use verbs. | allowed | A, B against C | C `:161-165`, `:181-184` |
| D13 | **Unrestricted `git`.** C's `Bash(git *)` covers any repository in reach: the clone's whole history, including objects past the window (the yardstick session's finding), and the draft repository's tags and history (C can delete a tag or rewrite history). A and B have no `git`. | allowed | C | `driver/arms.py:62-66` |
| D14 | **Unrestricted `sqlite3`.** C's `Bash(sqlite3 *)` can write the corpus index (UPDATE, DELETE); A's and B's corpus query is SELECT-only. Whether any audit or gate would notice a modified corpus is **unverified**. | allowed | C | `driver/arms.py:62-66` |
| D16 | **A "neutral" skill text speaks arm A's vocabulary.** `CONSOLIDATION_TEXTS` bundles `skills/ai-rfc-structures/SKILL.md` into every arm's consolidation prompt, and its "How" section says "`ai_rfc_structure_upsert` with the id, the kind, the title, the section …, and its members under the key its kind takes … (The tool's second parameter is named `fields`, but it carries the whole body …)" and "`ai_rfc_draft_render` returns one block per declared structure". B's consolidation prompt therefore carries the full body schema, but under MCP tool names B cannot call, next to its own slot's `ai-rfc structure upsert <id> --json '…'`. C's carries it too, but no C consolidation is ever launched (D8). It is the only bundled text that names an arm's tools: the loop's five texts and the other consolidation texts name none. | told | B, C (A reads it natively) | `render.py:46-52`; `plugins/ai-rfc/skills/ai-rfc-structures/SKILL.md`, "How" step 1–2; `prompts/consolidation-B.md:233-244` |
| D15 | **Tool count (D16, already disclosed in `<protocol>` §1).** A has 20 tools; B's slot table names 18 verbs. `ai_rfc_status` has no verb, and `ai_rfc_question_export` and `ai_rfc_answer_record` are named by no arm's prompt. | allowed | A, B | `surfaces/arm-A-mcp-tools.json`; `surfaces/arm-B-help.txt` |

## Common to every arm (substrate-common, not for the asymmetry ruling)

| # | What | Why common | Owner |
|---|---|---|---|
| S1 | **Window-less cluster access.** `cluster_get` has no window check (`server/core/queries.py:105-109` in the snapshot), and the pristine holds all 342 cluster directories. Out-of-window diffs include the RFC-final `H3_*` values (the yardstick session's finding). | A's tool and B's verb share one core; C can `Read` `clusters/`. | Ground-Truth Yardstick, "How is the tip-source leak closed?"; a precondition of "Freeze prompts, pin code, and dry-run" |
| S2 | **The clone's working tree sits at the tip.** | Every arm has `Read`. | Same owner |

**What this means for the channel.** Arm A's MCP descriptions are one line each, and its upsert
schemas type `fields` as a bare object. Arm A therefore learns every shape from its prompt, arm B
from its prompt and its `--help`, and arm C from neither (it learns from the workspace files). D1
and D2 are asymmetries of exactly the kind ARM-B found, in which channel carries the shape.
