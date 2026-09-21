# 04 — What reads the pristine clone's working tree, and what breaks if it moves to the window's end?

Type: research (AFK)
Status: resolved (2026-09-21, research subagent)
Claimed: research subagent (2026-09-21)
Blocked by: —
Parent: [Ground-Truth Yardstick](../map.md)

## Question

`<pristine>/clone/` is checked out at the repository tip (`6d36838`, 2025). Its
`src/aioquic/h3/connection.py` already holds every answer the dataset scores. Every run workspace
copies it. Before ticket 05 decides how to close that route, list **every consumer of a pristine or
run workspace's `clone/` working tree** (as opposed to its git objects) and say what each needs.

Cover at least:

- corpus build;
- forge adoption (`--forge-snapshot`);
- `workspace prepare`, `copy_workspace` and `verify_digest` (does `pristine.sha256` cover `clone/` files?);
- `ai_rfc_cluster_get` and every other MCP tool that reads it;
- the dataset's anchor tests (they run against a clone at exactly `6d36838`, so is it this clone?);
- the file tools arms A, B and C can reach (`driver/arms.py`, `driver/guard.py`: the guard confines
  Bash only, so can `Read`/`Grep`/`Glob` open `clone/`?);
- anything in `per_cluster.py` or the prompts that points the agent at `clone/`.

For each, say what breaks if `clone/` were (a) checked out at the window's end commit or (b) made
unreadable to the session. Also report whether any run so far read a tip source file (A1's transcript
shows only `clone/.readthedocs.yaml`).

## Constraints

Read-only. Cite `file:line` in `<pin>`. Never write in `<ai_rfc>` or `~/ai-rfc-experiments`. Findings
go to `../research/04-clone-working-tree-consumers.md`.

## Resolution

No production code reads the content of a `clone/` working-tree file; every consumer reads git
objects, some also require HEAD to equal the corpus tip, and the exceptions are the
`pristine.sha256` seal, the unused `resolve_anchors` helper and its tests (which read a different
tree, `~/arfc-experiments/…`), and every arm's unconfined `Read`/`Grep`/`Glob`. So (a) works only as
a late checkout inside `workspace prepare` (after `views --verify`, before the seal, with
`clone_head` re-recorded), and (b) only as a tool-level deny, which is unmeasured on CLI 2.1.278.
Neither closes the leak alone: out-of-window `clusters/c0120-*`/`c0241-*/span.diff` carry the same
answers, `ai_rfc_cluster_get` has no window check, and arm C's `git` reaches tip objects. The
window's end commit is `509065a` (c0011's last member), not `d290ebe`. Findings: [research/04-clone-working-tree-consumers.md](../research/04-clone-working-tree-consumers.md)
