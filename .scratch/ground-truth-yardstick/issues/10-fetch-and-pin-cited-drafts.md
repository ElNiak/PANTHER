# 10 — Fetch and pin the draft texts w02-11 cites

Type: task (AFK)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: —
Parent: [Ground-Truth Yardstick](../map.md)

## Question

Ticket 01 ruled that every fact cites the spec version the code declares at the anchor, checked
mechanically against pinned spec text. At w02-11's anchor, `509065a`, aioquic declares **h3-22**:
ALPN `"h3-22"` in `examples/http3_client.py:294` and `examples/http3_server.py:298,433`, and the
default `QuicProtocolVersion.DRAFT_22` at `aioquic/quic/configuration.py:80`. The w02-11 prototype
(ticket 08) can't verify a single citation until those drafts' texts are pinned. Do the work:

1. **Identify the documents.** One is draft-ietf-quic-http-22. The other is the QPACK draft of the
   same generation. Find it from the drafts' own cross-references (http-22's normative reference to
   QPACK names a draft number), not from dates. Also record whether aioquic at `509065a` names a
   QPACK draft anywhere.
2. **Fetch both** as plain text from the IETF archive (datatracker or rfc-editor), once. The network
   is needed; the cost is $0.
3. **Pin them** under `../assets/specs/` with their exact names and a `SHA256SUMS` file. Record the
   source URL and fetch date in `../assets/specs/README.md`.
4. **Prove they're usable.** For each of the 26 w02-11 candidate facts (17 `HTTP_*` error codes and 9
   frame types at `509065a`), locate the section that states the value and record whether it agrees,
   comparing values as integers. This is evidence for 08, not the dataset itself. Leave any decision
   about disagreements to 08, per 01's ruling 5.

## Constraints

Write only under this map. Never write in `<ai_rfc>` or `~/ai-rfc-experiments`. No spend, no API key.
Resolved when the texts are pinned and the 26-fact agreement table is recorded in this ticket's
resolution.

## Resolution

Done on 2026-09-21 ($0; network to `www.ietf.org` only). **All 26 w02-11 candidates agree with
draft-ietf-quic-http-22.** Details are in [assets/specs/README.md](../assets/specs/README.md).

**Pinned under [`assets/specs/`](../assets/specs/)** (verify with `shasum -a 256 -c SHA256SUMS`):

| File | sha256 | Draft date |
|---|---|---|
| `draft-ietf-quic-http-22.txt` | `86081a2e…3f12` | July 09, 2019 |
| `draft-ietf-quic-qpack-10.txt` | `5e122ab8…fc82` | September 12, 2019 |
| `draft-ietf-quic-qpack-09.txt` | `9ec5deb2…0e7a` | July 08, 2019 |

**The QPACK draft, and a discrepancy (not decided here).** http-22's normative reference (l.2659)
names **draft-ietf-quic-qpack-10**, "July 2019". The published qpack-10, though, is dated September 12,
2019, after both http-22 and the window's end (2019-09-04). The QPACK draft that actually existed with
http-22 is qpack-09 (July 08, 2019). Both are pinned. **It doesn't matter for w02-11:** aioquic at
`509065a` uses `pylsqpack` (`setup.py:56`) and names no QPACK draft. None of the 26 candidates is a
QPACK fact, and the only QPACK-defined window values (decimal settings and stream types) are excluded
by ticket 03.

**Agreement table:** [research/10-pin/agreement.md](../research/10-pin/agreement.md), produced by
[research/10-pin/agree.py](../research/10-pin/agree.py) (git-ignored, reproducible). It parses the
`ErrorCode`/`FrameType` enums from `git show 509065a:aioquic/h3/connection.py`, finds each symbol's
value-stating line in the pinned draft by exact pattern, and compares values as integers.

| kind | count | agree | disagree | not found | where in http-22 |
|---|---|---|---|---|---|
| error_code | 17 | 17 | 0 | 0 | §8.1, l.2139 (`HTTP_NO_ERROR (0x00)`) … l.2207 (`HTTP_SETTINGS_ERROR (0x00FF)`) |
| frame_type | 9 | 9 | 0 | 0 | §7.2.1–7.2.9, e.g. l.1554 (`DATA frames (type=0x0)`), l.2048 (`DUPLICATE_PUSH frame (type=0xE)`) |

So 01's ruling 5 (exclude a fact whose code and cited draft disagree) **excludes nothing** for w02-11:
all 26 are cited, verified and reachable (ticket 02).

**Fixed while doing it:** the first run cited draft line numbers 27–38 too high, because Python's
`splitlines()` also splits on the RFC text's form-feed page breaks. The script now splits on `\n`, and
the cited lines were re-checked against `sed -n` output.
