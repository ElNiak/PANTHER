# 11 — How is run order randomized and balanced across time?

Type: grilling (HITL)
Status: closed (grilling, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 12:54 CEST
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

**Already ruled there (2026-09-21), so it is an input here, not an open question:** fault retries
happen inside a run, so the run keeps its place. A replacement for an excluded run is **appended
at the end of the order**, at most one per cell, and a second exclusion in a cell stops the
campaign. What is left for this ticket is whether the appended replacements need their own
balancing, since they all land at the end, in one late time block.

## Resolution (grilling, 2026-09-21)

Ruled by the user in two rounds, confirmed as a whole before recording.

**Facts** (ai_rfc `c5e4a6c`). The order is already blocked: `run_order`
(`experiment/config.py:230-246`) emits one block per repeat, every arm once, shuffled with
`random.Random(seed + block)`. It does not balance each arm's position within the blocks (the
pilot's `B1 A1 C1 A2 C2 B2` put B first, then last). Runs launch strictly in sequence
(`campaign_runs.py:127`). Each target is its own campaign, so nothing orders the two targets in
time.

**Rulings:**
- **Scheme: blocks plus balanced positions.** Each block holds one run per arm, as today, and a
  seeded Latin-square rotation makes each arm take each position equally often across repeats:
  exactly when k is a multiple of the arm count, as close as possible otherwise. It holds for two
  arms or three.
- **Targets: aioquic and MARK blocks alternate in time**, the starting target chosen by the seed.
- **Concurrency: sequential**, one run at a time.
- **Replacements**: accepted at the end of the order. Each is reported with its time and
  position.
- **Enforcement: a cross-campaign schedule in code.** One command runs the two frozen campaigns
  block by block in the seeded alternation, and records the realised order with timestamps.
- **Preregistered**: the seed, the planned order of both campaigns, and the commitment to report
  the realised order with timestamps.
- **Code**: the balanced-position `run_order` and the cross-campaign schedule join
  [Land the fault, retry and exclusion rules in the experiment path](18-land-the-fault-retry-and-exclusion-rules.md)
  as its item 8.
