# 22 — Has the Yardstick map delivered the w02-31 dataset and score_run?

Type: task (HITL checkpoint)
Status: open
Claimed: —
Blocked by: — (ON THE FRONTIER)
Parent: [ai_rfc Main Campaign, Ready to Launch](../map.md)

## Question

Graduated on 2026-09-22 from
[How is aioquic's secondary recall measured, now that the c0011-tag score is exposed and unimplemented?](21-how-is-aioquic-secondary-recall-measured.md).
The user ruled that aioquic's secondary recall scores each run's final draft against a **new
w02-31 dataset anchored at c0031's end** (`48092046ff28`). The **Ground-Truth Yardstick map**
(`.scratch/ground-truth-yardstick/`) builds it by its own definitions. **The freeze waits for
it, and for `score_run` landed in ai_rfc.** Like the owed-fixes checkpoint, this ticket turns
another effort's delivery into something the frontier can compute. This map builds nothing here.

**Closes when all three hold:**
1. **The dataset exists** in the form the Yardstick map hands off. It must record:
   - `window: [2, 31]`, and `commit` equal to c0031's end as that map's `prepare` derives it;
   - its `declared_spec`, with evidence. This map proposed **draft-23**: QUIC versions
     `[DRAFT_23, DRAFT_22]` since c0019, ALPN `["h3-23", "h3-22"]` since c0021 and c0028, and
     error codes at draft-23 values since c0020. The tie-break is that map's to rule; record
     whatever it rules.
   - its sha256, which the preregistration names.
2. **`score_run(target, window, workspace)`** (plan
   `docs/superpowers/plans/2026-09-21-arfc-ground-truth-measurement.md:1393`, PANTHER
   `e6e7918b1`) **is landed in ai_rfc**, and it scores w02-31 against that dataset.
3. **A $0 check scores one existing final draft** with the landed `score_run` against the new
   dataset, and the record carries recall and claim accuracy. The draft is a v2 aioquic run's
   draft, even a w02-11 one; a partial window scores low by design, and this only proves the
   path works.

**Record on closing:** the dataset's path and sha256, its declared spec, the ai_rfc commit that
carries `score_run`, and the check's output. If the Yardstick map declines, or rules the w02-31
dataset out of its scope, **the user rules** whether this map builds it by that map's
definitions or drops the secondary metric.

**The request is NOT yet delivered.** On 2026-09-22 (~14:50) the message to
`build-w02-11-dataset-handoff` failed with "No agent named … is reachable": that session had
ended, and no Yardstick session was listed by `ListAgents`. **Hand the request below to that
map's next session**, or to its map, as the user chooses. **This map does not edit the Yardstick
map's files on its own.**

> Please build an aioquic w02-31 ground-truth dataset anchored at c0031's end (anchor
> `48092046ff28`), by your map's definitions. The user ruled on 2026-09-22 (the main-campaign
> map's recall ticket) that aioquic's secondary recall scores each run's **final** draft with
> `score_run` against it. The c0011-tag reading is dropped, so no revision-tag scoring is needed
> and your out-of-scope ruling stands. The proposed declared spec is draft-23, but the tie-break
> is yours:
> - c0019: QUIC defaults become `[DRAFT_23, DRAFT_22]`;
> - c0021: the ALPN becomes `["h3-23", "h3-22"]`, and c0028 adds
>   `H3_ALPN = ["h3-23", "h3-22"]`;
> - c0020: all 17 HTTP/3 error codes move to draft-23 values;
> - frame-type and stream-type values are unchanged through c0031.
>
> The main campaign's freeze waits on two things:
> 1. the dataset (path, sha256 and `declared_spec`);
> 2. `score_run` landed in ai_rfc (plan `e6e7918b1:1393`).
