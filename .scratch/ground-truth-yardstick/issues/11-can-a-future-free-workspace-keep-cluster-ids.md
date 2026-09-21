# 11 — Can a future-free workspace keep the window's cluster ids?

Type: research (AFK)
Status: resolved (2026-09-21, research subagent)
Claimed: research subagent (2026-09-21)
Blocked by: —
Parent: [Ground-Truth Yardstick](../map.md)

## Question

Ticket 05 ruled that a run gets a **future-free workspace**: nothing describing the repository after
the window's end commit (`509065a` for w02-11) is in it. That covers five routes: the `clone/` tip
files, out-of-window `clusters/`, forge records after the end, corpus rows after the end, and git
objects past the end. Before the fix can be specified (ticket 09), establish whether it can be built
**without changing the in-window cluster ids**. Everything is keyed on those ids: checkpoints,
`revisions.yaml`, the dataset's reachability test (ticket 02) and the pre-seeding. Establish too what
it breaks. Answer with evidence:

1. **Cluster ids.** How are cluster ids and ordinals computed (`<pin>/ai_rfc/timeline/`, the forge
   `pulls.jsonl`)? Does a history and forge truncated at the window's end reproduce the ids of
   c0002–c0011 exactly? Could the last in-window cluster (c0011, an epoch) be cut differently when
   history ends at its last member? What about c0001, whose members precede the window?
2. **HEAD guards and the seal.** Research 04 found consumers that require the clone's HEAD to equal
   the corpus tip (`pipeline/state.py:102-107`, `git_log.py:102,173`, `timeline/cli.py:141-147`), and
   a `pristine.sha256` seal that covers every `clone/` file. Does a history *consistently* truncated
   at the end (clone, corpus and timeline all ending there) satisfy them?
3. **Out-of-window markers.** Do the sweep, the ledger (`ledger.py:91` counts pre-seeded as done),
   `cluster_next` or the gates need the views of out-of-window clusters (the 331 pre-seeded
   c0001/c0012–c0342 dirs), or only markers?
4. **Placement.** Where would truncation sit: in `workspace prepare` (a future-free pristine per
   window) or in `copy_workspace` (a future-free run copy of a full pristine)? Which is simpler, and
   which keeps the seal meaningful?
5. **Git objects.** How are objects past the end dropped from the run's clone, so that arm C's
   `Bash(git *)` can't reach them (a fresh clone to the end commit, `--single-branch`, a gc)? What
   does each cost?

**Best evidence:** prepare w02-11 from history and a forge snapshot truncated at `509065a`, writing
only under `/private/tmp/claude-501/` and never into `~/ai-rfc-experiments`. Then diff the in-window
cluster ids and members against `<pristine>/timeline/clusters.jsonl` and `members.jsonl`. If a real
prepare can't be run offline and read-only against the evidence, say so and reason from the code, with
file:line.

## Constraints

$0, no API key. Write only under `/private/tmp/claude-501/` and this map's `research/`. Never write in
`<ai_rfc>` (another session is committing there) or `~/ai-rfc-experiments`. Read code at `<pin>`.
Findings go to `../research/11-future-free-workspace.md`. If truncation turns out infeasible, say so
plainly: ticket 05's route then reopens.

## Resolution

**Feasible, with conditions.** A real, offline run of the pinned `workspace prepare` over a clone and
forge snapshot both cut at `509065a` reproduced c0001–c0011 exactly. The `clusters.jsonl` and
`members.jsonl` rows, all 11 span diffs and all 5 PR evidence files are byte-equal to the pristine's,
and only the `source` digests in `view.json` differ. No cluster after the end was produced, and the
run's clone holds exactly the 3,624 objects reachable from the end, so `6d36838` is gone. The ids
survive in general because an ordinal is a position on the first-parent spine counted from the root.
The conditions are these:
- The cut must be the **last member of the window's top cluster**, which only a full timeline names.
  So prepare needs a cheap resolution pass (0.2 s) and an assert that rows 1..H match; a mid-epoch cut
  keeps the id but changes the cluster.
- The forge must keep every merged pull whose landing commit is an ancestor of the end. Without #24 and
  #25, c0008 and c0010 vanish.
- The clone must be made with `--no-local --revision=<end>` (a plain local clone keeps every object)
  and must have its `origin` removed (`git fetch origin main` restores the tip).
- Repositories outside the workspace that still hold the future remain reachable by absolute path, so
  the transcript audit stays necessary.

Placement belongs in `workspace prepare`, not `copy_workspace`: every HEAD guard, `views --verify` and
the seal then hold by construction. Details, the git-route costs and the reproduction commands:
[research/11-future-free-workspace.md](../research/11-future-free-workspace.md).
