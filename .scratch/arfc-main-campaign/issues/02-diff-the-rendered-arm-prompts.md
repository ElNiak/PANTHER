# 02 — Diff the three rendered arm prompts from a fresh `campaign init`

Type: task (AFK)
Status: open
Claimed: —
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
