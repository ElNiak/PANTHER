# Pinned spec texts for the aioquic w02-11 dataset

Pinned by ticket 10 ("Fetch and pin the draft texts w02-11 cites"), 2026-09-21, session 0ea41509.
Verify with `shasum -a 256 -c SHA256SUMS`.

| File | Source URL | Fetched (UTC) | Bytes | Draft date |
|---|---|---|---|---|
| `draft-ietf-quic-http-22.txt` | https://www.ietf.org/archive/id/draft-ietf-quic-http-22.txt | 2026-09-21T11:06:56Z | 143,905 | July 09, 2019 |
| `draft-ietf-quic-qpack-10.txt` | https://www.ietf.org/archive/id/draft-ietf-quic-qpack-10.txt | 2026-09-21T11:07:08Z | 84,755 | September 12, 2019 |
| `draft-ietf-quic-qpack-09.txt` | https://www.ietf.org/archive/id/draft-ietf-quic-qpack-09.txt | 2026-09-21T11:07:38Z | 83,532 | July 08, 2019 |

## Why these files

Ticket 01 ruled that every fact cites the spec version the code **declares** at the anchor. At w02-11's
anchor, `509065a` (2019-09-04), aioquic declares **h3-22**: ALPN `"h3-22"` in
`examples/http3_client.py:294` and `examples/http3_server.py:298,433`, and the default
`QuicProtocolVersion.DRAFT_22` at `aioquic/quic/configuration.py:80`. That is
`draft-ietf-quic-http-22`.

## How the QPACK draft was identified, and a discrepancy

http-22's normative reference (line 2659) names it explicitly:

```
   [QPACK]    Krasic, C., Bishop, M., and A. Frindell, Ed., "QPACK:
              Header Compression for HTTP over QUIC", draft-ietf-quic-
              qpack-10 (work in progress), July 2019.
```

So the cross-referenced QPACK draft is **qpack-10**. But the published qpack-10 is dated **September 12,
2019**, which is after both http-22 (July 09, 2019) and the window's end (2019-09-04). The QPACK draft
that actually existed alongside http-22 is **qpack-09**, dated July 08, 2019. http-22 cited the next
QPACK version before it was published, as the QUIC working group's synchronized drafts often did.
**Both are pinned. Which one w02-11 cites is not decided here.**

**It doesn't affect w02-11's scoring.** aioquic at `509065a` does QPACK through `pylsqpack`
(`setup.py:56`) and names no QPACK draft. None of the 26 candidate facts is a QPACK fact. The only
QPACK-defined values in the window are the decimal settings and stream types, which are excluded
(ticket 03).

## Agreement with the code

See `../../research/10-pin/agreement.md`, produced by `../../research/10-pin/agree.py` (git-ignored):
**26 of 26 candidates agree** with draft-ietf-quic-http-22 (17 error codes in §8.1, 9 frame types in
§7.2.1–7.2.9).
