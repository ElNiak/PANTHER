# 08 — Which runs are excluded, and how is an infrastructure-faulted session treated?

Type: grilling (HITL)
Status: closed (grilling, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 12:36 CEST
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Protocol §6 item 5 asks for the exclusion rule. The protocol has one for integrity-violated runs,
excluded "by a pre-registered rule, never silently" (§2). The pilot added that a run is excluded
only after **the guard's verdict and the audit's verdict agree** on the offending call: its one
apparent violation was an instrument defect.

**Nothing covers infrastructure faults**, and the GEPA pilot showed what that costs. **D31**
(`.superpowers/sdd/GEPA-PILOT/progress.md:801`): during a network outage a session "ran, reached
the API, and was refused". It returned an audit record, so the evaluator's `_harness_fault` did
not fire, and it **scored 0.0** instead of aborting. "A harness fault that scores zero rather than
aborting silently rewrites the search's comparisons." In a campaign, the same fault would record a
run as a failed run of its arm.

**Decide:**
- What counts as an infrastructure fault: network failure, API refusal or rate limit, a CLI
  crash, a quota stop, or a timeout that is not the model's.
- For each: retry (how many times, and whether a retry keeps its place in the run order),
  exclude, or count as a failure. Whether excluded runs are replaced.
- How a fault is detected from the transcript, so the rule is mechanical, as the integrity audit
  is.
- How an instrument defect is told apart from a run defect. **R91/R92** have the
  record-before-tag shape: an entry claiming a revision whose tag was refused. See
  [Has the owed-fixes row landed](05-has-the-owed-fixes-row-landed.md) for whether that is fixed.

The pilot had no timeouts, budget hits or interrupted runs (`<pilot>` "What broke"), so the rule
has no precedent in this experiment's own data.

## Resolution (grilling, 2026-09-21)

Ruled by the user in three rounds, confirmed as a whole before recording.

**What the code does today** (ai_rfc `c5e4a6c`, mapped by an Explore agent). The experiment path
has **no split between infrastructure faults and model failures**: `driver/stop.py`'s `classify`
is used only by the production sweep. No run is ever retried (`campaign_runs.py:133-140`).
Per-cluster mode spends one of a cluster's 2 attempts on any failure, and two failures halt the run
(`per_cluster.py:51`, `:658-678`). An interrupt or crash in `launch()` writes no `status.json` and
blocks the campaign's resume (`campaign_runs.py:141-145`). Integrity violations are reported,
never excluded (`metrics.py:498`), and the guard-against-audit agreement check exists only as a
test. `api_errors` is computed and never read (`audit.py:403-404`).

**Rulings:**
- **Session mode: `per-cluster`.**
- **Infrastructure fault** (a session) is any of:
  - no result event;
  - `is_error` within the session's first turn;
  - an API `error` event or a rate-limit rejection in its transcript;
  - a crash or interrupt outside the model;
  - a timeout preceded by an API error or a rate-limit event.
- **Model failure** (counted, never excluded): a budget hit, a timeout with no API stall before it,
  exhausted attempts, poor output.
- **Fault retry**: the same cluster's session re-runs up to **3** times, **outside** the cluster's
  2 model attempts and inside the run, so the run keeps its place in the order. Interrupts and
  crashes resume at their cluster.
- **Infrastructure-incomplete run**: one cluster has used all 3 fault retries. The run is
  excluded.
- **Integrity exclusion**: only when the audit's out-of-arm call **and** the guard's verdict on
  that same call agree, through a per-run check that has to be built. When they disagree, the run
  is kept and an instrument defect is reported.
- **Excluded run**: kept in the report with its reason, left out of the arm's metrics.
- **Replacement run**: same arm and target, **appended at the end of the run order**, at most **one
  per cell**. A second exclusion in the same cell **stops the campaign for review**.
- **Faulted spend**: reported as its own line per cell, outside the arm's cost metrics.
- **Code**: a new task ticket,
  [Land the fault, retry and exclusion rules in the experiment path](18-land-the-fault-retry-and-exclusion-rules.md),
  which waits on the owed-fixes checkpoint. The freeze and the validation pilot wait on it.
- **The optimizer's D31 gap** (`_harness_fault` in `optimize/evaluator.py`) is **out of scope**
  for this map. It is recorded on the map.
