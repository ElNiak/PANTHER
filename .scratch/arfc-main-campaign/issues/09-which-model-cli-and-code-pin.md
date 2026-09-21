# 09 — Which model, effort, CLI version and code pin does the main campaign fix?

Type: grilling (HITL)
Status: open
Claimed: —
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
