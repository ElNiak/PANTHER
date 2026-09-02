# `pipeline/` — chaining the deterministic stages

The six substrate commands each do one stage and take every path explicitly.
That is right for them: a stage should not assume a layout it did not create.
But it left nobody holding the sequence, so running a reconstruction meant
typing five commands with matching paths in an order documented only in prose.

This package holds the sequence and nothing else.

## What it does not do

It does not call a model, and it does not reach the network except through the
`forge` stage it delegates to. Two of the ten stages produce content — mining
claims and writing prose — and this package **stops** at them. Reaching such a
boundary is success, not failure: the deterministic half is finished and the
next move belongs to somebody else, so the command exits 0 and says whose turn
it is.

Stage 0 is a **pin check, not a clone**. Cloning reaches the network, which the
package reserves to `forge`, so obtaining the repository stays a human step.

## The stages

| # | Stage | Performer | Reads → writes |
|---|---|---|---|
| 0 | `pin` | manual | — → `clone/` |
| 1 | `history` | deterministic | `clone/` → `corpus/` |
| 2 | `forge` | deterministic | repository URL → `forge/<host>/snapshot-<ts>/` |
| 3 | `timeline` | deterministic | `corpus/` → `timeline/` |
| 4 | `views` | deterministic | `timeline/` → `clusters/` |
| 5 | `mining` | **agent** | `clusters/` → `manifest.yaml` |
| 6 | `check` | deterministic | `manifest.yaml` → `out/report.*` |
| 7 | `prose` | **agent** | evidence → `draft/`, `revisions.yaml` |
| 8 | `checkpoint` | deterministic | `manifest.yaml` → `checkpoints/<id>/` |
| 9 | `gate` | deterministic | `draft/` → `out/gate-report.json` |

`forge` is the only optional stage. Its enrichment matters — on a squash-heavy
repository a git-only timeline sees far fewer pull requests — but a
reconstruction without it is narrower, not broken. Both `state` and the runner
step over it when no `--forge-url` is given, and they are written to agree:
skipping in one and requiring it in the other is the disagreement the runner's
explicit branch exists to prevent.

## State is derived, never recorded

Nothing tracks what has been run. The substrate already writes the digest of
each stage's inputs into that stage's output — `timeline.json` carries the
corpus digests, a `view.json` carries the timeline's, a `checkpoint.json`
carries the manifest's — so "is this still current?" is a question the
artifacts already answer.

A run ledger would answer it faster and would begin lying the moment somebody
ran a sub-CLI by hand, which the authoring loop actively tells them to do.
`status --json` emits a record for a driver to read; nothing reads it back as
authority.

Six states: `done`, `partial` (produced for some of its units but not all —
what exists is correct and stays, so the stage is resumed rather than re-run),
`stale` (produced, but an input moved), `pending`, `blocked` (something
upstream is not ready), and `re-derivable`.

`check` and `gate` are `re-derivable`: both are pure and take
milliseconds, and their output carries no digest of its input. Adding one to
make their doneness derivable would cost more than simply re-deriving the
answer, so the runner performs them rather than probing them.

An uncommitted change in the clone is **reported and does not block**. Nothing
downstream reads the working tree — `history` extracts from `git log`, `views`
reads git objects, and anchors resolve through `git show <commit>:<path>` — so
blocking on it would hide a corpus and timeline that are perfectly current.

## Commands

```bash
python -m …ai_rfc.pipeline status WORKSPACE [--json]
python -m …ai_rfc.pipeline run WORKSPACE [--from STAGE] [--until STAGE] \
    [--forge-url URL] [--host github|gitlab] [--cluster ID] [--strict] [--json]
```

Exit codes follow the package's table: 0 on success *including* a clean stop at
an agent boundary, 1 when the workspace cannot be read, 2 from `argparse`, and
otherwise a stage's own code — so a strict gate's 3 reaches the caller
unchanged.

## The interface a driver calls

`state.next_stage(workspace)` returns the first outstanding stage, its state,
why, and whether a model has to perform it. That is the whole contract an
external driver needs: it can advance the deterministic stages by calling `run`
and fill in the agent stages itself, without knowing the stage table.

## How stages are invoked

Through each sub-package's `cli.main(argv)`, in process — the same way the
tests already drive them. `pipeline` therefore imports only `…cli.main` and
never a core module: data still hands over on disk, exactly as it does when the
commands are typed by hand, so chaining them changes how they are invoked and
not what they share.

An `argparse` failure inside a sub-CLI raises `SystemExit(2)` rather than
returning, and that is deliberately not caught. Every argv is built here, so a
usage error means this package built one wrong — a defect that should surface
loudly rather than be dressed up as a stage failure that looks like the
workspace's fault.
