# 02 — Diff the three rendered arm prompts from a fresh `campaign init`

Type: task (AFK)
Status: closed (task, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 11:53 CEST
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

The protocol's constants say the arms' "system prompts and skills [are] identical modulo minimal
invocation syntax; the pair is diffed and the diff published" (`<protocol>` §4). **ARM-B showed
they were not**: arm B's claim slot showed one literal code anchor and no adr anchor, so arm B
never recorded a second evidence class and confirmed 0% of its claims while arms A and C
confirmed about nine in ten. That was fixed as `8358238`, but nobody has looked for the next one.

Known asymmetries at charting, all in `<ai_rfc>/ai_rfc/driver/render.py`'s `SLOT_TABLES`:
- Arm A's claim slot gives a field list, `{evidence_class, locator, commit, line}`, with no
  literal anchor (`render.py:382-387`).
- Arms C and interactive edit `manifest.yaml` by hand and are shown no anchor shape at all
  (`_RAW`, `render.py:138-141`).
- D16: arm A reaches 20 operations as tools, arm B 19 as verbs, since `ai_rfc_status` has no verb
  (`<protocol>` §1, "One measured asymmetry").

Diff arm C too, whatever
[Does the main campaign include arm C](17-does-the-main-campaign-include-arm-c.md) rules. Spec D42
froze its surface at pre-v2, and `campaign init` still renders and freezes a
`consolidation-C.md` that no session is ever launched from (`<protocol>:302-306`).

**Do:** render all three arms from a fresh `campaign init` in a scratch directory (the command
records each rendered file's digest in `campaign.json`). Diff A against B, B against C and A
against C, loop and consolidation prompts both. Write the diffs and **one list of every
difference that is not invocation syntax** (what the session is told, shown or allowed), each with
its `render.py` slot and line. Nothing is ruled here: the rulings are
[Rule each arm asymmetry](04-rule-each-arm-asymmetry.md). $0; no session is launched.

The output lands under `.scratch/arfc-main-campaign/prototypes/02-arm-prompt-diff/` (tracked)
and is linked from the resolution comment.

## Resolution (task, 2026-09-21)

Asset: [`prototypes/02-arm-prompt-diff/README.md`](../prototypes/02-arm-prompt-diff/README.md),
with the frozen prompts, the loop and consolidation pair diffs, each arm's surfaces (arm A's 20
MCP tools as listed, arm B's and arm C's `--help` for every command their slot tables name, and
the allowlists), `campaign.json`, and the three scripts that reproduce all of it.

**How.** Rendered from a `git archive` snapshot of ai_rfc `8358238`, not the live tree, which the
owed-fixes session had mid-edit in modules the tool listing imports. `campaign init` **refused at
toolchain verification** ("the example did not build offline": the venue, kramdown-rfc and v2v3
stages each exited 1). The campaign was frozen by the same code path with verification skipped.
The refusal is recorded for
[Freeze prompts, pin code, and dry-run](13-freeze-pin-and-dry-run.md). All nine prompt digests
check. **`task.md` is byte-identical to the pilot's** (`05e731d3…f84539`).

**What differs, beyond invocation syntax: sixteen entries (D1–D16), and two common to every arm
(S1–S2).** The ones "Rule each arm asymmetry" most needs:
- **D1, the anchor shape**: A gets a field list; B gets both literal anchors (after `8358238`);
  **C's prompt never names `evidence_class` at all**.
- **D2, structure fields in the loop**: A is told kind, title, section and members; **B is told
  only `--json '…'`**, and its `--help` adds nothing.
- **D16, the one "neutral" skill text written for arm A**: `ai-rfc-structures/SKILL.md`, bundled
  into every consolidation prompt, teaches the structure body under `ai_rfc_structure_upsert` and
  `ai_rfc_draft_render`, tool names arm B cannot call.
- **D7, corpus schema**: neither A's `corpus_query` nor B's `corpus query` shows a table or
  column; C has `sqlite3 .schema`. This confirms SP7d's report.
- **D8/D9, arm C's frozen v2 surface (D42)**: no structures, no build, and a tag made by raw
  `git tag` with no rollback.
- **D13/D14**: C's unrestricted `git` (the clone's whole history, and the draft's tags and
  history) and `sqlite3` (it can write the corpus).

**Common to every arm** (not for the asymmetry ruling): window-less cluster access
(`cluster_get` has no window check, and the pristine holds all 342 clusters), and the clone
checked out at the tip. They belong to the Ground-Truth Yardstick map's tip-leak ticket and gate
the freeze.

Nothing is ruled here.
