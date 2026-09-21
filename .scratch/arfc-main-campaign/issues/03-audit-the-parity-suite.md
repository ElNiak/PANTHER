# 03 — Audit the parity suite: which operations carry a cross-arm behavioural assertion?

Type: task (AFK)
Status: open
Claimed: —
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
