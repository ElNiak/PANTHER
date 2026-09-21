# 03 — Audit the parity suite: which operations carry a cross-arm behavioural assertion?

Type: task (AFK)
Status: closed (task, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 12:07 CEST
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Parity is "the arm-design backbone": both frontends drive one shared core, and "any capability
delta discovered is a protocol stop-ship" (`<protocol>` §1). The parity suite is the evidence,
attached to the preregistration and re-run after the campaign.

**The pilot found the suite weaker than it looks** (`<pilot>` "Threats observed"): its
completeness check was a markdown name-grep, and only **5 of 16** rows in `docs/parity.md` carried
a cross-arm behavioural assertion. Both of the pilot's parity passes (7 tests each) were
therefore weak evidence.

At charting, `<ai_rfc>/tests/server/test_parity.py` holds **25** test functions against **20**
MCP tools and **19** `ai-rfc` verbs, and `<ai_rfc>/docs/parity.md` has 26 table lines, header
included. The protocol says "twenty twins, one per MCP tool". Whether each twin compares what
the two arms wrote or read, or only that both ran, is unmeasured.

**Also check, unverified at charting:** the SP7d session reported that `corpus_query` hides its
schema from the agent (its arm-A session guessed `commit_sha`, `parents`, `c.committed_at`). Arm C
queries with `sqlite3` directly and can read `.schema`. If that holds, it is a capability delta
between arms.

**Do:** for each tool/verb pair, record whether a test drives both over byte-identical workspaces
and **asserts equal effects**, and cite the assertion's line. List every operation with no such
assertion, and every capability one arm has that another lacks. $0. Nothing is ruled here: the
rulings are [Rule each arm asymmetry](04-rule-each-arm-asymmetry.md).

## Resolution (task, 2026-09-21)

Asset: [`prototypes/03-parity-audit/README.md`](../prototypes/03-parity-audit/README.md), with
`pytest-output.txt`, the three probes and their output.

**The suite is far stronger than the pilot found, and its gaps are inputs, not operations.** At
ai_rfc `571355c`, run from a clean snapshot, `test_parity.py` gives **25 passed, 0 failed**. All
20 MCP tools have a twin that drives arm A's tool and arm B's verb over twin workspaces and
compares files or payloads. **13 are full, 6 partial, and 1 none by design** (`ai_rfc_status`
has no verb, D16). The pilot counted 5 of 16.

**The six partial twins** each cover one input shape, not the ones sessions also use:
- corpus query: no schema read, no refusal;
- **claim upsert: no `--anchor` at all**;
- record status: no explicit ids, and no non-vacuity guard;
- **revision tag: the success path only, not the refusal on build findings or the tag deletion
  on citation findings**, which sessions hit;
- draft lint: no guard, and the exit code is not compared;
- structure upsert: kind `record` only, no `enum` or `state-machine`.

**The probes** (inputs no twin covers; outcomes recorded, nothing asserted):
- **Both A and B can read the corpus schema** through `SELECT … FROM sqlite_master`. So the
  prompt diff's D7 is about exposure, not capability.
- Both refuse `DELETE`.
- **A code-plus-adr anchor upsert leaves byte-equal manifests.** The ARM-B fix's path keeps
  parity today, but no twin would notice it breaking.

**Limits of the construct:**
- **No transport is tested**: the tool functions are called directly, not through MCP, and
  `cli.main` is called in-process, not through the campaign's shim.
- **Arm C has no twin at all.**
- Two refusals are pinned per arm, never across arms.

Nothing is ruled here, and no test was added.
