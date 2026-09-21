# 08 — Which runs are excluded, and how is an infrastructure-faulted session treated?

Type: grilling (HITL)
Status: open
Claimed: —
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
