# 11 — How is run order randomized and balanced across time?

Type: grilling (HITL)
Status: open
Claimed: —
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

The protocol says "run order is randomized and interleaved across arms to neutralize
time-varying API conditions" (`<protocol>` §4), and logs API conditions per run.

**The pilot showed that randomizing alone does not balance** (`<pilot>` "Threats observed"): its
order `B1 A1 C1 A2 C2 B2` came from a preregistered seed, but each arm's repeats sat at different
points of one 2.5-hour sequential window. Any drift was therefore not balanced at n = 2, and
"time-of-day and rate-limit effects cannot be separated from arm effects".

A main campaign is 3 arms × 2 targets × k runs, at up to ~2 hours each (7200 s timeout; the
pilot's slowest used 22%). Sequentially, that is days. Whether runs may execute in parallel under
one account's rate limits and quota is unmeasured, and so is whether parallel runs interfere
through shared caches or quotas.

**Decide:** the randomization scheme (e.g. blocked, with each block holding one run per arm, so
every arm sees every time period); sequential or parallel execution, with the concurrency limit;
how the seed and the realized order are recorded; and what happens to the order when a run is
retried under
[Which runs are excluded](08-which-runs-are-excluded.md).
