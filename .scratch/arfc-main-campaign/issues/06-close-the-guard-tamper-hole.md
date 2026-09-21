# 06 — Close the guard-implementation tamper hole

Type: task (AFK)
Status: open
Claimed: —
Blocked by: [Has the owed-fixes row landed](05-has-the-owed-fixes-row-landed.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Arm enforcement is a `PreToolUse` hook, `guard.py`, because `--allowedTools` does not confine a
built-in tool. The pilot found its tamper evidence incomplete and said it "needs a real fix
before the main run" (`<pilot>` "Threats observed"): the settings the hook is mounted from are
digested, but **the hook's implementation is not**. `Edit`/`Write` are not path-confined, so a
session could reach `guard.py` by absolute path.

**Measured still open at charting (2026-09-21):**
- `<ai_rfc>/ai_rfc/driver/session.py:47` names `GUARD_FILE = "guard.json"`; `:51` mounts the
  live `ai_rfc/driver/guard.py`.
- `<ai_rfc>/ai_rfc/experiment/runner.py:218-220` digests only `run_dir / GUARD_FILE` (the
  settings) before spawn.
- `<ai_rfc>/ai_rfc/experiment/audit.py:426-430` re-hashes only that same `guard.json`.
- The pilot's run closed the hole retroactively with hand-recorded digests.

**Decide and land:** how the implementation's integrity is evidenced (e.g. copy `guard.py` into
the run directory and mount the copy, so the existing digest-and-rehash covers it; or digest the
live file at spawn and re-hash it in the audit), plus a RED test that a modified implementation is
reported by the audit. $0.

Blocked on the owed-fixes row because it owns `runner.py` and `audit.py`.
