# 07 — Can the rebuilt MARK pristine carry a v2 cluster through its last gate?

Type: task (AFK, $0)
Status: closed (task, 2026-09-21)
Claimed: chart-ai-rfc-main-campaign (session 40f5ddb1), 2026-09-21 12:17 CEST
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

MARK is one of the two targets (user ruling at charting). Its old draft repository **can never
pass the v2 build gate**: the 2026-09-02 MARK draft repo is a copy of i-d-template itself, from
before D45, with no root `Makefile`, so `idnits`' versioned sub-build has no `.targets.mk` rule
(SP7d ruling R90). No MARK revision, not even -37, passes `ai-rfc draft build`. The paid MARK
consolidation round of 2026-09-21 ran for $11.37 and could not tag for this reason. A $0
`draft build` beforehand would have caught it.

SP7d rebuilt a MARK pristine that passed its gate:
`~/ai-rfc-experiments/rebuild-sp7d/pristine/mark-w01-69`, under a separate root, because
`prepare` refuses the old evidence path. Its two forge captures are byte-identical. Whether a
*session's* work on it can clear the **last** gate (build, then `revision tag`, then the strict
citation gate) is unmeasured.

**Do, at $0:** copy the pristine with `copy_workspace` into a scratch directory. Run
`ai-rfc draft build` on the fresh draft. Then walk one cluster's gates by hand with the agent
verbs (claim, checkpoint, `revision record`, `revision tag`) far enough to see the tag either
created or refused. **Output:** MARK ready for a v2 campaign, or the list of what a fresh
bootstrap must change. Never edit the pristine itself.

## Resolution (task, 2026-09-21)

Asset: [`prototypes/07-mark-last-gate/README.md`](../prototypes/07-mark-last-gate/README.md),
with the full command transcript and the three scripts.

**Yes: the rebuilt MARK pristine is ready for a v2 campaign.** On a copy (ai_rfc `c5e4a6c`), the
draft builds with no findings (`.txt` and `.html`). Cluster `c0001-epoch-c84a5f082e40` goes
through checkpoint, revision record, **tag** (strict manifest gate, build at the tag, strict
citation gate: findings `[]`, not rolled back) and `citation-gate --strict` ("gate clean"). Every
step exits 0. R90's pre-D45 failure does not occur: the rebuilt `draft/` has a root `Makefile`.
The pristine's digest was clean before and after, and **the copy was checked to resolve to itself
before any write**.

**The build cannot run inside this Claude Code sandbox.** i-d-template's `trace.sh` calls
`mktemp` in `/var/folders/…/T` and writes `/dev/fd/62`, and the sandbox refuses both ("Operation
not permitted"). Every stage then fails, with **empty stderr in the build report**. That is the
cause of the `campaign init` verification refusal recorded on
[Freeze prompts, pin code, and dry-run](13-freeze-pin-and-dry-run.md). Outside the sandbox,
`toolchain verify` prints `ok`. The three build-running commands ran with the sandbox disabled,
on that evidence, writing only inside the scratch copy.

**Surfaced for the freeze ticket:** whether arms B and C can build inside a campaign session is
unmeasured. They build through their session's Bash, while arm A builds through the MCP server.
The profile has no sandbox key, so their Bash is probably unsandboxed, but no arm-B session has
built a v2 draft yet.

Not tested here: a session's claims and prose, which can raise their own lint and build findings.
