# 04 — Rule each arm asymmetry: equalize, fix or disclose?

Type: grilling (HITL)
Status: open
Claimed: —
Blocked by: [Diff the three rendered arm prompts](02-diff-the-rendered-arm-prompts.md), [Audit the parity suite](03-audit-the-parity-suite.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

With the prompt diff and the parity audit in hand, rule each asymmetry they list. The three
available rulings:

- **Equalize.** Change the prompt so every arm is told and shown the same thing, modulo syntax.
  This is what `8358238` did for arm B's anchor.
- **Fix.** Close a capability gap in the code, or add the missing cross-arm assertion to the
  parity suite.
- **Disclose.** Keep the asymmetry and record it in `docs/parity.md` and the paper, as D16 was
  (arm A's 20 operations against arm B's 19).

The protocol's rule is the bar: a genuine capability delta is a stop-ship, so it can only be
fixed. Prompt differences beyond syntax must be equalized or disclosed. The pilot said "no prompt
or template change is indicated", but ARM-B showed that was wrong, so every ruling here needs the
evidence from tickets 02 and 03, not the pilot's verdict.

Execution is carried: an **equalize** or **fix** ruling may land in this ticket, committed by
explicit path in `<ai_rfc>` after checking the owed-fixes row's file list. It does not touch the
row's files (see the map's Notes). The rulings also fix the enforcement configuration per arm
(§6 item 6) where an asymmetry concerns what the guard admits.
