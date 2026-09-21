# 09 — Which model, effort, CLI version and code pin does the main campaign fix?

Type: grilling (HITL)
Status: closed (grilling, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 12:45 CEST
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Protocol §6 item 7: "model id, version, sampling parameters; harness identity and version". The
protocol's constants pin the model and the harness for every arm, and "model churn" is an
external threat mitigated by pinning and naming (§5).

**At charting:**
- The pilot ran **`claude-opus-5`, effort `high`, Claude Code 2.1.251** (`<protocol>` "Pilot-derived
  defaults"). SP7d's Phase 5 arm-A runs used the same model. The GEPA pilot's sessions ran
  `claude-sonnet-5`.
- `claude --version` now reads **2.1.278**. The protocol says: "Re-run the S0 spike whenever the
  CLI moves; the enforcement mechanism is a measured property of the CLI, not a contract". The
  pilot's enforcement evidence is therefore for a CLI no longer installed.
- Code: SP7d pinned its paid runs to a clone (`~/ai-rfc-experiments/code-pins/ai_rfc-3406985`
  plus `code-pins/venv-3406985`, an editable install of the clone with dependencies constrained to
  the worktree venv's freeze), because a peer committing to `<ai_rfc>` moves live code under an
  editable install. Sessions do not inherit `PATH`: `driver/session.py` composes
  `[campaign/bin, dirname(python), /usr/bin, /bin]`, so they use `/usr/bin/git` (SP7d R88).

**Decide:** the model id(s), and whether the model is a factor or a constant; the effort level;
the CLI version and how it is held fixed across a campaign that may span days (auto-update); and
the code-pin method and commit. The S0 re-run on the chosen CLI belongs to
[Freeze prompts, pin code, and dry-run](13-freeze-pin-and-dry-run.md).

## Resolution (grilling, 2026-09-21)

Ruled by the user in two rounds, confirmed as a whole before recording.

**Facts found while grilling:**
- **The CLI version is not pinned today.** `campaign init` freezes `shutil.which("claude")`,
  which is the `~/.local/bin/claude` **symlink** that every auto-update re-points (to
  `versions/2.1.278` since Sep 19), so the "freeze the binary" comment at
  `experiment/config.py:346-355` is defeated.
- Each run records the **campaign's** frozen version, not the binary it ran (`runner.py:293`).
- Nothing disables auto-update, and the installer keeps only the last three versions (2.1.274,
  2.1.276, 2.1.278 are on disk; the pilot's 2.1.251 is gone).
- The shipped GEPA-optimized skill texts were tuned on `claude-sonnet-5` sessions.

**Rulings:**
- **Model: `claude-opus-5`**, one model, not a factor. It is comparable with the pilot, with
  SP7d, and with the noise the statistical plan uses. That the skills were tuned on
  `claude-sonnet-5` is disclosed.
- **Effort: `high`.**
- **Sampling parameters: stated as not exposed.** The model id and effort are recorded;
  temperature and top-p are the service's defaults, not settable through Claude Code.
- **Claude Code version: chosen at the freeze.** Whatever version is current then has its binary
  **copied** into `~/ai-rfc-experiments/code-pins/claude-<version>`, and `--claude` points at
  the copy, never at the symlink. Auto-update is disabled for the campaign. Each run records the
  version it **really** launched, and a mismatch is **refused**. S0 re-runs on the copy.
- **Code: SP7d's clone and venv** (`code-pins/ai_rfc-<sha>`, plus `code-pins/venv-<sha>` with an
  editable install and dependencies constrained to the worktree freeze), with `--python` pointing
  at it. The commit is chosen by the freeze ticket, after the landings.
- **The pin code** (freeze the resolved binary, record the real version per run, refuse a
  mismatch) goes into
  [Land the fault, retry and exclusion rules in the experiment path](18-land-the-fault-retry-and-exclusion-rules.md)
  as its item 7. The freeze ticket's pin steps now spell these rulings out.
