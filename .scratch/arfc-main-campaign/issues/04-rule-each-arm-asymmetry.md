# 04 — Rule each arm asymmetry: equalize, fix or disclose?

Type: grilling (HITL)
Status: open
Claimed: —
Blocked by: [Diff the three rendered arm prompts](02-diff-the-rendered-arm-prompts.md), [Audit the parity suite](03-audit-the-parity-suite.md), [Does the main campaign include arm C](17-does-the-main-campaign-include-arm-c.md)
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

**Inputs, both closed on 2026-09-21:**
- [`prototypes/02-arm-prompt-diff/README.md`](../prototypes/02-arm-prompt-diff/README.md):
  sixteen arm differences, D1–D16, each marked told, shown or allowed, plus S1–S2, which are
  common to every arm and belong to the tip-leak work, not here.
- [`prototypes/03-parity-audit/README.md`](../prototypes/03-parity-audit/README.md): the 20
  twins (13 full, 6 partial, 1 none by design), three probes, the construct limits L1–L3 and the
  capability differences K1–K4.

The rulings split by kind: D-rows are prompt or allowlist rulings (equalize or disclose); partial
twins and L1–L3 are test rulings (fix or accept); K-rows are capability rulings (a genuine delta
can only be fixed). Many D-rows touching arm C depend on
[Does the main campaign include arm C](17-does-the-main-campaign-include-arm-c.md): if C is
dropped, D8–D14 need no ruling. **Wired as a blocker on 2026-09-21**, when the parity audit
closed, so the frontier cannot offer this ticket before the arm C decision.

**Arm C was dropped on 2026-09-21** ([its ticket](17-does-the-main-campaign-include-arm-c.md)).
Rows D8–D14 and K2 need no ruling, and D1's and D16's arm-C halves fall away. The rows left to
rule are the A-against-B ones:
- D1: A's anchor field list against B's literal anchors;
- D2: structure fields told to A only in the loop;
- D3: optional claim fields;
- D4 and D5: minor told differences;
- D6: status, which B lacks in consolidation;
- D7: corpus schema exposure, capability equal per the parity probes;
- D15 (D16 in the protocol): 20 tools against 19 verbs;
- D16 (the prompt diff's): the structures skill in A's vocabulary, now inside B's consolidation
  prompt;
- the six partial twins and L1–L3 of the parity audit;
- K1: status.
