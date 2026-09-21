# 13 — Freeze prompts, pin code, and dry-run the campaign at $0

Type: task (AFK)
Status: open
Claimed: —
Blocked by: [Rule each arm asymmetry](04-rule-each-arm-asymmetry.md), [Has the owed-fixes row landed](05-has-the-owed-fixes-row-landed.md), [Close the guard tamper hole](06-close-the-guard-tamper-hole.md), [Which model, CLI and code pin](09-which-model-cli-and-code-pin.md), [Which task list per target](12-which-task-list-per-target.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

The protocol requires a "versioned prompt freeze: no mid-experiment edits" (§4), with the prompt
pair's diff published and the parity results attached before any run (§6 items 8 and 11). SP7d
showed why code must be pinned too: a peer committing to `<ai_rfc>` moves live code under an
editable install mid-run. **The validation pilot must measure the frozen artifacts**, or its
variance estimate describes something the main campaign will not run.

**Do:**
1. Pin the code at the commit and by the method
   [Which model, CLI and code pin](09-which-model-cli-and-code-pin.md) ruled, in a clone under
   `~/ai-rfc-experiments/code-pins/`.
2. From the pinned install, `campaign init` a campaign for each target's task list. The command
   records every rendered prompt file's digest in `campaign.json`. Publish the arm diffs
   (re-rendered after the rulings of ticket 04).
3. Re-run the **S0 enforcement spike** on the pinned CLI. It launches real sessions, so read its
   cost first and ask the user if it is not $0.
4. Run the parity suite on the pinned code and keep its output (pre-run evidence).
5. **Dry-run each target's last gate at $0** on a copy of its pristine: `draft build`, and a tag
   created or refused. "Could start" is not "could finish" (SP7d's third blind spot).

**Precondition from the sibling map "Ground-Truth Yardstick".** The tip-source leak has three
paths, measured in
[Diff the three rendered arm prompts](02-diff-the-rendered-arm-prompts.md) (entries S1, S2 and
D13):
- each pristine's `clone/` working tree is checked out at the target's tip, readable by every
  arm's `Read`;
- `cluster_get` has no window check, and the pristine holds all 342 clusters' diffs, readable by
  A's tool, B's verb and C's `Read`;
- arm C's unrestricted `git` reaches the clone's whole history.

No run has used any of them so far. That map's "How is the tip-source leak closed?" rules the fix
and hands it to ai_rfc as a spec. **This ticket does not freeze until the fix has landed in the
pinned code and covers all three paths**, or the user rules the leak acceptable and disclosed.

**Also found on 2026-09-21: `campaign init` refuses at toolchain verification.**
`~/ai-rfc-experiments/tools/toolchain.json` (sha256 `97e4e644…d79ee`) fails with "the example did
not build offline": the venue, kramdown-rfc and v2v3 stages each exit 1. The cause was not
diagnosed; it may be the sandbox, or a stale refcache after SP7d's rebuild. A frozen campaign
needs a toolchain that verifies, so diagnose it here, before step 2.

**Output:** the pin (commit, clone path, venv freeze digest), the `campaign.json` digests, the
arm diffs, the S0 verdict, the parity output and the dry-run results, each linked from the
resolution comment.
