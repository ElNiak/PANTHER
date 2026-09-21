# 13 — Freeze prompts, pin code, and dry-run the campaign at $0

Type: task (AFK)
Status: open
Claimed: —
Blocked by: [Rule each arm asymmetry](04-rule-each-arm-asymmetry.md), [Has the owed-fixes row landed](05-has-the-owed-fixes-row-landed.md), [Close the guard tamper hole](06-close-the-guard-tamper-hole.md), [Which model, CLI and code pin](09-which-model-cli-and-code-pin.md), [Which task list per target](12-which-task-list-per-target.md), [Land the fault, retry and exclusion rules](18-land-the-fault-retry-and-exclusion-rules.md), [Land the arm-parity fixes](19-land-the-arm-parity-fixes.md)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

The protocol requires a "versioned prompt freeze: no mid-experiment edits" (§4), with the prompt
pair's diff published and the parity results attached before any run (§6 items 8 and 11). SP7d
showed why code must be pinned too: a peer committing to `<ai_rfc>` moves live code under an
editable install mid-run. **The validation pilot must measure the frozen artifacts**, or its
variance estimate describes something the main campaign will not run.

**Do:**
1. Pin, as [Which model, CLI and code pin](09-which-model-cli-and-code-pin.md) ruled:
   - **The code**: choose the commit once every landing this ticket waits on is in. Clone it to
     `~/ai-rfc-experiments/code-pins/ai_rfc-<sha>`, and make an editable install in
     `code-pins/venv-<sha>` with dependencies constrained to the worktree venv's freeze. The
     campaign's `--python` points at that venv.
   - **Claude Code**: take **the version current at the freeze**, copy its versioned binary from
     `~/.local/share/claude/versions/<version>` to `code-pins/claude-<version>`, and point
     `--claude` at the copy, **never** the auto-updating `~/.local/bin/claude` symlink. Disable
     auto-update for the campaign's duration. The version-record and mismatch refusal come from
     the landing ticket.
   - **The model**: `claude-opus-5` at effort `high`. There are no other sampling parameters to
     set.
2. From the pinned install, `campaign init` a campaign for each target's task list. The command
   records every rendered prompt file's digest in `campaign.json`. Publish the arm diffs
   (re-rendered after the rulings of ticket 04).
3. Re-run the **S0 enforcement spike** on the **copied** CLI. It launches real sessions, so read
   its cost first and ask the user if it is not $0.
4. Run the parity suite on the pinned code and keep its output (pre-run evidence).
4b. **Freeze the judge** (H4's primary metric): record the digest of its prompt and rubric beside
   `campaign.json`. If no code records it, add that to the landing ticket before freezing. Also
   check what `total_cost_usd` means under the subscription the campaign runs on (H2's cost):
   whether it is a notional price or billed spend.
5. **Dry-run each target's last gate at $0** on a copy of its pristine: `draft build`, and a tag
   created or refused. "Could start" is not "could finish" (SP7d's third blind spot).

**Precondition from the sibling map "Ground-Truth Yardstick".** Its "How is the tip-source leak
closed?" was **resolved with the user on 2026-09-21**. Anything describing the repository after
the window's end commit counts as future material, and it found **five routes**. Three were
measured in [Diff the three rendered arm prompts](02-diff-the-rendered-arm-prompts.md) (S1, S2,
D13); the other two are that map's findings:
- each pristine's `clone/` working tree is checked out at the target's tip, readable by every
  arm's `Read`;
- `cluster_get` has no window check, and the pristine holds all 342 clusters' diffs, readable by
  A's tool, B's verb and C's `Read`;
- arm C's unrestricted `git` reaches the clone's whole history;
- the forge snapshot (`pulls.jsonl`, `comments.jsonl`) mentions post-window material;
- the corpus indexes every commit to the tip (1,182 for aioquic), and `corpus_query` admits any
  SELECT.

**Its ruled fix is a future-free workspace, with a transcript audit as the backstop.**
`workspace prepare` cuts at the last member of the window's top cluster, keeps every merged PR
that landed by then, clones with `--no-local --revision=<end>`, removes `origin`, and asserts the
object set. Its research ticket measured this offline for w02-11: clusters c0001–c0011 stayed
byte-equal, and the clone held only the 3,624 objects reachable from the end. Absolute paths to
repositories outside the workspace stay reachable, hence the audit. The fix is handed to ai_rfc
through that map's scorer and dataset hand-off ticket, and **has not landed**. No run has used
any route so far. **This ticket does not freeze until that fix has landed in the pinned code and
the audit backstop exists**, or the user rules the leak acceptable and disclosed.

**Also found on 2026-09-21: `campaign init` refuses at toolchain verification.**
`~/ai-rfc-experiments/tools/toolchain.json` (sha256 `97e4e644…d79ee`) fails with "the example did
not build offline": the venue, kramdown-rfc and v2v3 stages each exit 1. **Diagnosed the same
day in [Can the rebuilt MARK pristine pass its last gate](07-can-the-mark-pristine-pass-its-last-gate.md):
it is the sandbox, not the toolchain.** i-d-template's `trace.sh` calls `mktemp` in
`/var/folders/…/T` and writes `/dev/fd/62`, and the sandbox refuses both. Outside it, `toolchain
verify` prints `ok`. So run `campaign init` and every build from an unsandboxed shell.

**Add to the dry run: prove arms B and C can build inside a campaign session.** Arm A builds
through the MCP server process; B and C run `draft build` (and the tag's build) through their
session's Bash. The campaign profile has no sandbox key and sessions launch with
`--setting-sources project`, so their Bash is probably unsandboxed. But no arm-B session has built
a v2 draft yet. If it were sandboxed, B's and C's builds would fail where A's pass: an arm
asymmetry no prompt diff or parity twin can see. A $0 run of the arm's `bin/ai-rfc draft build`
under `driver/session.py`'s environment covers `PATH` and the environment only. **Whether Claude
Code sandboxes a session's Bash shows only inside a real session**, and a one-turn probe costs
money, so ask first.

**Output:** the pin (commit, clone path, venv freeze digest), the `campaign.json` digests, the
arm diffs, the S0 verdict, the parity output and the dry-run results, each linked from the
resolution comment.
