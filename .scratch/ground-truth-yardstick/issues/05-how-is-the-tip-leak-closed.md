# 05 — How is the tip-source leak closed?

Type: grilling (HITL)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: [04 — What reads the pristine clone's working tree?](04-what-reads-the-clone-working-tree.md)
Parent: [Ground-Truth Yardstick](../map.md)

## Question

A yardstick is valid only if the answers can't be read (ruling 4). The pristine's `clone/` sits at the
tip and arm A's `Read` can open it. Which route closes this, for every target and window?

- **(A)** Check `clone/` out at the window's end commit when a pristine is prepared.
- **(B)** Confine the session's file tools so they can't open `clone/`.
- **(C)** Leave it open and prove unreachability instead: audit every run's transcript for tip-source
  reads and void any run that has one.
- A combination.

Also decide what happens to the drafts already produced (pilot and v2 A1/A2): no run opened tip source,
so do they stand as valid?

## Starting evidence

Ticket 04's research: [research/04-clone-working-tree-consumers.md](../research/04-clone-working-tree-consumers.md).
Key facts, each checked at the site:

- The leak is **not only `clone/`**. `ai_rfc_cluster_get` (`<pin>/ai_rfc/server/core/queries.py:105-120`)
  reads any `clusters/<id>/` with no window check. The pristine holds all 342 clusters' views, and
  `clusters/c0120-*/span.diff` contains `H3_NO_ERROR = 0x100`.
- Arm C's `Bash(git *)` (`driver/arms.py:66`) reaches tip objects whatever the working tree holds.
- Every arm gets plain `Read, Edit, Write, Grep, Glob` (`arms.py:21, 42-68`); the guard matches `Bash`
  only (`enforcement.py:217`).
- Option (A) is possible only as a late checkout inside `workspace prepare`, after `views --verify` and
  before `write_digest`, with `clone_head` re-recorded (`experiment/workspace.py:398, 418, 425`).
  Earlier, it cuts the corpus; on a sealed pristine, every launch and copy refuses. The prompt's
  "Restore the pin" row (`loop.tmpl.md:103`) points back at the tip.
- Option (B) works only as a tool-level deny, which is unmeasured on CLI 2.1.278. An OS-level lock
  breaks the seal, the copy and the MCP gate (`server/core/gates.py:137-146`).
- Neither v2 run read tip-source content. A2's two `Glob "*"` calls listed tip file names, and four of
  its Greps searched `clone/` with no matches. Neither run's 56 corpus queries were audited.

A second map, "ai_rfc Main Campaign, Ready to Launch" (`<wt>/.scratch/arfc-main-campaign/`), won't
freeze its campaign until this fix has landed in the pinned code, or until the user rules the leak
acceptable.

## Resolution

Grilled with the user on 2026-09-21. **Every run workspace carries the repository's whole future.
The run gets a workspace built so that nothing after the window's end is in it, and an audit of each
transcript is the backstop.** The user's rulings:

| # | Question | Ruling |
|---|---|---|
| 1 | What the run must not see | **Anything describing the repository after the window's end commit** (*future material*): the clone's tip files, out-of-window cluster diffs, forge records after the end, corpus rows after the end, and git objects past the end. |
| 2 | Route | **A future-free workspace, plus an audit as backstop.** The run's workspace is built so the future isn't there to reach, whatever tool or arm asks. Every transcript is audited for future content. Feasibility (whether the in-window cluster ids survive truncation) is **unmeasured**, so research ticket 11 comes first. If 11 finds truncation infeasible, the route question reopens as a new grilling ticket. |
| 3 | When a run has "touched" future material | **When future content reached the model** in a tool result: a file's text, a diff, a query row. A bare file name in a listing (A2's `Glob "*"` of the tip tree) doesn't count. |
| 4 | The drafts already produced (pilot v1 A1, v2 A1, v2 A2) | **Valid only after a $0 audit** of their transcripts under rulings 1 and 3. This includes their 56 unaudited corpus queries and the never-examined pilot transcript. The audit is task ticket 12, which blocks 09's re-score. |

**The five routes to future material (each checked at the site):**
1. **`clone/` working tree** at the 2025 tip. Every arm's `Read`/`Grep`/`Glob` can open it
   (`<pin>/ai_rfc/driver/arms.py:21, 42-68`); the guard matches `Bash` only (`enforcement.py:217`).
2. **Out-of-window cluster diffs.** `ai_rfc_cluster_get` has no window check
   (`server/core/queries.py:105-109`), and `Read` can open `clusters/*` directly. The pristine holds
   342 cluster dirs, and `clusters/c0120-*/span.diff` and `c0241-*/span.diff` contain
   `H3_NO_ERROR = 0x100`.
3. **The forge snapshot.** `forge/github.com__aiortc__aioquic/snapshot-2026-08-25T15-16-59Z/` holds
   every PR to 2026-08-25, and its `pulls.jsonl` and `comments.jsonl` mention `H3_NO_ERROR` / `0x100`.
   Any arm's `Read` can open them.
4. **The corpus.** `corpus/commits.jsonl` holds all 1,182 commits to the tip. It is metadata only,
   but 4 subjects name `H3_*` constants (e.g. "Update the vlaue of H3_DATAGRAM to RFC9297").
   `corpus_query` runs any SELECT over the full index (`queries.py:44-60`).
5. **Git objects.** Arm C's `Bash(git *)` (`arms.py:62-66`) reaches every commit up to the tip, and
   would also undo a sparse checkout.

Routes 1, 2 and 5 were independently confirmed by the Main Campaign map's prompt-diff asset
(`.scratch/arfc-main-campaign/prototypes/02-arm-prompt-diff/README.md`: S1, S2 and D13).

**An integrity path, not a leak (a peer's note):** arm C's `Bash(sqlite3 *)` can *write*
`corpus/index.sqlite`, whereas A's and B's corpus queries are SELECT-only. The scorer doesn't read the
corpus, so this is outside this map; it is recorded so that nobody rediscovers it.

**Consequences:**
- **The fix is ai_rfc code**, so it goes into ticket 09's hand-off spec, shaped by 11's findings
  (ruling 6): a future-free `workspace prepare` plus an audit backstop that records read-tool paths
  (`audit.py:199-200` records none today). Research 04's "a-late" checkout placement and its
  empty-sparse-checkout probe are inputs; neither closes routes 2–5 on its own.
- **The Main Campaign map's freeze** waits on this fix landing in the pinned code.
