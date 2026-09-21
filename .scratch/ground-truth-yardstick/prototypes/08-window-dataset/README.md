# PROTOTYPE: aioquic w02-11 dataset built to the map's rules (ticket 08). Throwaway.

**Assumption.** The prototype skill offers an HTML logic demo or UI variants, and ticket 08's question
("what does the dataset look like, and what does it score?") is neither. So the artifact is the
dataset file plus a one-command re-scorer that prints the full per-fact state.

**Provisional:** these scores stand only once ticket 12's audit clears the three drafts of future
material.

## Run (pinned interpreter, $0, reads only)

```
PY=~/ai-rfc-experiments/code-pins/venv-3406985/bin/python
$PY build_dataset.py      # -> aioquic-w02-11-at-509065a.PROTOTYPE.yaml
$PY rescore.py            # -> prints everything below (kept in rescore.out.md)
```

## The dataset: `aioquic-w02-11-at-509065a.PROTOTYPE.yaml`

It has 34 entries in the current YAML shape. Anchor `509065a`, window [2, 11], declared spec h3-22 with
its evidence, and the pinned spec's sha256.
- **26 scored hex facts:** 17 `HTTP_*` error codes and 9 frame types. Each has `source {path, line}`
  at the anchor, a `citation {doc, section, line}` into the pinned draft-ietf-quic-http-22 with
  `citation_agrees: true`, and `reachable {cluster, diff_line}` (all 26 via c0005).
- **8 decimal entries** (4 settings, 4 stream types). The scorer excludes them itself, but they stay
  as entries because the scorer uses every entry's symbol to tell a symbol from part of a longer one
  (`SETTINGS` inside `HTTP_SETTINGS_ERROR`). Today's dataset works the same way.

Example entry:

```yaml
- id: h3-22-frame-goaway
  statement: In aioquic at 509065a (h3-22), GOAWAY is the HTTP/3 frame type with value 0x7.
  symbol: GOAWAY
  value: '0x7'
  kind: frame_type
  source: {path: aioquic/h3/connection.py, line: 53}
  citation: {doc: draft-ietf-quic-http-22, section: 7.2.7, line: 1970}
  citation_agrees: true
  reachable: {cluster: c0005-epoch-79f631193bdf, diff_line: 202}
```

## Results (provisional)

| Draft | Reachable recall | All-facts recall | Ceiling | Claim accuracy | Error codes (m/n/a) | Frame types (m) |
|---|---|---|---|---|---|---|
| pilot v1 A1 (tag -10) | **11/26 = 0.423** | 0.423 | 26/26 | 1.000 (11 attempted of 26 reachable) | 2 / 0 / 15 | 9 / 9 |
| pilot v1 A2 (tag -11) | **11/26 = 0.423** | 0.423 | 26/26 | 1.000 (11 attempted of 26 reachable) | 2 / 0 / 15 | 9 / 9 |
| v2 A1 | 9/26 = 0.346 | 0.346 | 26/26 | 1.000 (9 attempted of 26 reachable) | 0 / 2 / 15 | 9 / 9 |
| v2 A2 | 10/26 = 0.385 | 0.385 | 26/26 | 1.000 (10 attempted of 26 reachable) | 1 / 1 / 15 | 9 / 9 |

In the error-code column, m/n/a is matched / named without a value / absent.

- **Every draft states all 9 frame types**, including `DUPLICATE_PUSH = 0xE`.
- **The difference is in the error codes.** The pilot states two with values: "HTTP_WRONG_STREAM,
  whose value is 0x0A" (pilot draft l.166) and "HTTP_UNEXPECTED_FRAME, whose value is 0x13" (l.187).
  v2 A1 names both with no value (A1-10.md l.721-736). v2 A2 states one with a value and names the
  other.
- **15 of 17 error codes are absent from every draft.**
- **Pilot A2 was added at the user's request.** Its final revision is tag `-11`: A2 numbers its
  revisions one higher, and its `-11` is the c0011 revision, as A1's `-10` is. It also states both
  error codes with values.
- **On the valid yardstick, both v1 pilot runs recover slightly more facts (11, 11) than either v2 run
  (9, 10).** This is one window, n = 2 against 2, and differences of 1–2 facts.

## Checks

- **Reproduction:** the OLD dataset (tip `6d36838`) scored against the pilot draft gives **8/35 with
  the same 8 ids as SP7d's `t11/gt-pilot`**. So the pilot text used here is the one SP7d scored.
- **Truncation (research 03's edge-cut bug):** a whole-token `_tokens_near` changes **no outcome** on
  either dataset for any of the three drafts. No existing match depends on the bug. The fix still
  belongs in 09's spec.

## Sources (read-only)

- The pilot v1 A1 draft is read with `git show draft-elniak-aioquic-reconstructed-10:…` from
  `~/arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831/runs/A1/workspace/draft`.
- The v2 drafts are `<t11>/armA-drafts/A{1,2}-10.md`.
- The code is `git show 509065a:aioquic/h3/connection.py` in `<pristine>/clone`.
- The spec is `../../assets/specs/draft-ietf-quic-http-22.txt`, located with ticket 10's `agree.py`.
