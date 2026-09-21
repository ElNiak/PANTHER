# 18 — Land the fault, retry and exclusion rules in the experiment path

Type: task (AFK)
Status: open
Claimed: —
Blocked by: [Has the owed-fixes row landed](05-has-the-owed-fixes-row-landed.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Graduated on 2026-09-21 from
[Which runs are excluded, and how is an infrastructure-faulted session treated?](08-which-runs-are-excluded.md),
whose resolution holds the user's rulings. **This ticket makes the experiment path obey them.**
Nothing here is re-decided; if the code shows a ruling cannot be implemented as stated, stop and
reopen that ticket.

Execution is carried (map Notes). The work is ai_rfc code, landed RED-test first, committed by
explicit path in `<ai_rfc>`, $0. It waits on the owed-fixes checkpoint because it touches that
row's files: `experiment/{runner,audit,per_cluster}.py`, and probably `campaign_runs.py` and
`metrics.py`. Find that row's session with `ListAgents` before touching anything it owns.

**What has to exist**, with today's location (ai_rfc `c5e4a6c`):
1. **A fault classifier on the experiment path.** Reuse `driver/stop.py`'s `classify`
   (`:342-362`; `errored` means no result event, or `is_error` within the first turn). Add the
   API `error` events that `audit.py:403-404` already counts but nothing reads, and rate-limit
   rejections (read today only by `optimize/claude_cli.py:93-109`). A timeout counts as a fault
   only when an API error or rate-limit event precedes the kill. Record the verdict per session in
   `sessions.jsonl` and per run on `RunStatus` (`runner.py:55-67`), which has no fault field.
2. **Fault retries outside the attempts.** `per_cluster.py` spends one of
   `ATTEMPTS_PER_CLUSTER = 2` (`:51`) on any failure. Faulted sessions get up to 3 retries that do
   not use an attempt. After 3 on one cluster, the run is `infrastructure-incomplete`.
3. **Interrupts and crashes resume at their cluster.** Today an exception or interrupt inside
   `launch()` writes no `status.json`, and the next `run` refuses the campaign
   (`campaign_runs.py:141-145`). `5b45d09`'s interrupt handling covers only the root CLI and the
   driver, not `python -m ai_rfc.experiment`.
4. **A per-run guard-against-audit agreement check** on each out-of-arm call. Today it exists only
   as `tests/driver/test_enforcement_corpus.py:125`. Exclude only on agreement; report a
   disagreement as an instrument defect.
5. **Exclusion and replacement.** Excluded runs (infrastructure-incomplete, or agreed integrity
   violations) stay in the report with their reason and leave the arm's metrics. `metrics.py`
   today drops only runs with no `status.json` (`:534`) or a broken surface (`:443-444`). One
   replacement per cell is **appended to the run order**. A second exclusion in a cell **stops the
   campaign** for review.
6. **Faulted spend on its own line per cell**, outside the arm's cost metrics.
7. **The Claude Code pin**, added on 2026-09-21 by
   [Which model, effort, CLI version and code pin …](09-which-model-cli-and-code-pin.md):
   - `campaign init` freezes the **resolved** binary. Today `shutil.which` returns the
     `~/.local/bin/claude` symlink, which every auto-update re-points (`experiment/config.py:346-355`).
   - Each run records the version it **really launched** (its `--version` at launch). Today
     `runner.py:293` copies the campaign's frozen value.
   - A run whose binary reports a version other than the campaign's is **refused**.
8. **The run order**, added on 2026-09-21 by
   [How is run order randomized and balanced across time?](11-how-is-run-order-randomized.md):
   - `run_order` (`experiment/config.py:230-246`) keeps its blocks and adds **position balance
     across repeats**: a seeded Latin-square rotation, exact when k is a multiple of the arm
     count. The campaign has two arms, A and B, since arm C was dropped on 2026-09-21; the
     rotation still takes the arm list as given.
   - **A cross-campaign schedule**: one command runs the two frozen campaigns (aioquic and MARK)
     block by block in a seeded alternation, **sequentially**, and records the realised order
     with timestamps.
   - Replacements (item 5) are still appended at the end.

**Done when**: each ruling has a RED-then-GREEN test; the full ai_rfc suite passes (report
collected, passed, failed and skipped separately); and a $0 rehearsal with the fake claude
(`experiment/cli.py`'s `_fake_claude`) shows a fault retried outside the attempts, and an excluded
run replaced at the end of the order.
