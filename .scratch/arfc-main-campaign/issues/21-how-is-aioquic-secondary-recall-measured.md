# 21 — How is aioquic's secondary recall measured, now that the c0011-tag score is exposed and unimplemented?

Type: grilling (HITL)
Status: closed (grilling, 2026-09-22)
Claimed: watch-push-resume-flow (session 40f5ddb1), 2026-09-22 14:33 CEST
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

[Which task list does each target use, with its provenance-class coverage?](12-which-task-list-per-target.md)
ruled that aioquic runs **w02-31**, and that **secondary reachable recall** is scored on each
run's draft **at its c0011 revision tag**, against the Ground-Truth Yardstick map's w02-11 dataset
(anchored `509065a`). On 2026-09-22 that map's session (`build-w02-11-dataset-handoff`) sent a
finding that the user ruled belongs to this map. **The window ruling stands; the secondary-recall
line does not.** Checked at the source on 2026-09-22:

- **The window reaches past the dataset's spec.**
  - `c0020-epoch-34e9ba073e96/span.diff` (in `~/ai-rfc-experiments/pristine/aioquic-w02-11/clusters/`)
    moves every HTTP/3 error code into draft-23's 0x100 range. `HTTP_NO_ERROR` goes from 0x00 to
    0x100, and `HTTP_SETTINGS_ERROR` from 0xFF to 0x109. `HTTP_UNEXPECTED_FRAME` is renamed
    `HTTP_FRAME_UNEXPECTED`, `HTTP_INCOMPLETE_REQUEST` is renamed `HTTP_REQUEST_INCOMPLETE`, and
    `HTTP_WRONG_STREAM` is removed.
  - `c0021-pr-b8c652bb6051/span.diff` changes the ALPN to `["h3-23", "h3-22"]` (and
    `["hq-23", "hq-22"]`).
- **17 of the dataset's 26 scored facts are those error codes.**
  `.scratch/ground-truth-yardstick/assets/09/aioquic-w02-11-at-509065a.yaml` has 34 entries:
  17 `error_code`, 9 `frame_type`, 4 `setting`, 4 `stream_type`. The 8 settings and stream types
  carry an `unscored_reason`.
- **A run at its c0011 tag can read the draft-23 values.** The future-free cut at c0031's end
  keeps c0020 and c0021, by design: the yardstick rule treats as future only what comes after the
  window's end. They reach the run through `clone/` (checked out at c0031's end) and through
  `cluster_get` on c0012–c0031. A drafted 0x100 then scores as a mismatch.
- **Nothing scores at a revision tag.** The measurement plan (PANTHER `e6e7918b1`,
  `docs/superpowers/plans/2026-09-21-arfc-ground-truth-measurement.md:1393`) defines
  `score_run(target, window, workspace)`, which scores only a run's final draft. The yardstick map
  ruled per-revision scoring out of its scope.
- **A w02-31 dataset would need a tie-break.** At c0031's end the code declares two ALPNs, so
  the yardstick rule "the dataset follows the spec the code declares" needs a tie-break there.

**The options named so far** (for the grilling, not ruled):
- Score each run's **final draft** against a **w02-31 dataset anchored at c0031's end**. This
  follows the yardstick rule and the planned `score_run` without a tag branch. It needs the
  yardstick map to build that dataset and to rule the ALPN tie-break.
- Keep the **c0011 tag, labelled exposed**. This needs revision-tag scoring, which reopens the
  yardstick map's out-of-scope ruling.
- Run **w02-11 as its own task list** for the recall measure: extra runs, extra cost.
- **Drop** the secondary recall metric. MARK already has none, so the campaign would then carry no
  ground-truth measure at all.

**Also for the grilling:** any measure taken before a window's end can read the window's later
clusters (`clone/` at the end, and `cluster_get` without a per-cluster window). Both arms have
the same access, so the A-against-B contrast is not biased by it. But the preregistration should
say it, for any per-revision reading.

**Blocks** [Freeze prompts, pin code, and dry-run](13-freeze-pin-and-dry-run.md). Any scorer
change must be in the pinned code, and any new dataset must exist before the freeze.

## Resolution (grilling, 2026-09-22)

**Facts gathered at the source** (cluster diffs in
`~/ai-rfc-experiments/pristine/aioquic-w02-11/clusters/`, read as files; the worktree guard
refuses git aimed at the external clone):
- **Only the error codes and the preferred versions move inside w02-31.**
  - Error codes: c0020 moves all 17 HTTP/3 codes to draft-23 values.
  - QUIC versions: c0019 makes the defaults `[DRAFT_23, DRAFT_22]`.
  - ALPN: c0021 changes it to `["h3-23", "h3-22"]`, and c0028 adds the constant
    `H3_ALPN = ["h3-23", "h3-22"]`.
  - Unchanged through c0031: the frame-type and stream-type values. c0013 adds the QPACK error
    codes (0x200–0x202), and c0018 removes one QUIC transport error.
- **So at c0031's end** (`48092046ff28`, the anchor of `c0031-pr-48092046ff28`) the code
  prefers draft-23 on every count: QUIC version, ALPN, and error-code values.

**Rulings (user, 2026-09-22):**
1. **Secondary recall (aioquic only) is each run's final draft**, scored by `score_run` against
   a **new w02-31 dataset anchored at c0031's end** (`48092046ff28`). No revision-tag scoring is
   needed. The c0011-tag reading is dropped. The final draft follows the whole window, so no
   within-window lookahead applies to it.
2. **The Ground-Truth Yardstick map builds that dataset**, by its own definitions. This map
   proposes **draft-23** as the declared spec, since the code puts it first on every count, but
   the tie-break is that map's to rule. The ruled message to its session
   (`build-w02-11-dataset-handoff`) could not be delivered, because the session had ended. The
   request text is kept in the checkpoint ticket below, for that map's next session.
3. **The freeze waits for the dataset and for `score_run` landed in ai_rfc**, so both are in
   the pin and the $0 dry run scores a draft end to end. The tracking checkpoint is
   [Has the Yardstick map delivered the w02-31 dataset and score_run?](22-has-the-yardstick-delivered-the-w02-31-dataset.md).

The window rulings of
[Which task list does each target use](12-which-task-list-per-target.md) stand. The
preregistration names the dataset's digest.
