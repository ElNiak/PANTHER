# 01 — What is a window's ground truth anchored to?

Type: grilling (HITL)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: —
Parent: [Ground-Truth Yardstick](../map.md)

## Question

When a draft reconstructs window [a, b] of a repository's history, what makes a fact **true** for it?

- **(A) The code at the window's end.** The anchor commit is the last commit of cluster b. Facts are
  named and valued as that code spells them: for w02-11, `HTTP_WRONG_STREAM = 0x0A`, not
  `H3_FRAME_UNEXPECTED = 0x105`.
- **(B) The final published spec.** This is today's dataset: anchored at the clone's tip `6d36838`
  and built from RFC 9114/9204. A 2019 window can't reach it (ceiling 8/35).
- **(C) A concept with per-era spellings.** One fact ("the wrong-stream error") carries each era's name
  and value, and the window selects the spelling it could have seen.

Also decide what happens to the existing RFC-final dataset `<pin>/ai_rfc/experiment/groundtruth/aioquic-w02-11.yaml`:
keep it as a secondary set (and under what name, since "w02-11" in its name claims a window it
doesn't describe), retire it, or re-anchor it.

## Starting evidence

- `groundtruth/aioquic-w02-11.yaml:59` `commit: 6d36838d…` = `<pristine>/pristine.json` `clone_head`.
  The comment block above it says each value was checked against the cited RFC section.
- `git -C <pristine>/clone show 509065a:aioquic/h3/connection.py` (the window's end, 2019-09-04, the
  last of c0011's five members; `d290ebe`, c0011's `anchor_sha`, is its first):
  `class ErrorCode` has `HTTP_NO_ERROR = 0x00` … `HTTP_SETTINGS_ERROR = 0xFF`; `class Setting` has
  `QPACK_MAX_TABLE_CAPACITY = 1`, `SETTINGS_MAX_HEADER_LIST_SIZE = 6`, `QPACK_BLOCKED_STREAMS = 7`,
  `SETTINGS_NUM_PLACEHOLDERS = 9`.
- Some dataset facts have no in-window predecessor at all (`H3_FRAME_ERROR`, `H3_MESSAGE_ERROR`,
  `DUMMY`, `ENABLE_CONNECT_PROTOCOL`).
- Ruling 3 (map Notes): the answer must work as a general rule for any target and window.

## Resolution

Grilled with the user on 2026-09-21 in two rounds. **(A) wins: a fact is true as the code at the
window's end states it.** The user's rulings:

| # | Question | Ruling |
|---|---|---|
| 1 | Anchor | **The code at the window's end.** A fact is true as that code names and values it (`HTTP_WRONG_STREAM = 0x0A`, `GOAWAY = 0x7`). |
| 2 | Which commit | **The last member commit of the window's last cluster**, computed from `timeline/members.jsonl`. For w02-11 that is `509065a` (2019-09-04), not c0011's `anchor_sha` `d290ebe` (its first member). |
| 3 | Citation | **Required on every fact.** A target whose code declares no spec gets no dataset. (The user chose this over "code is the authority, citation optional", aware of that consequence.) |
| 4 | Which spec version | **The one the code declares at the anchor**, through ALPN or version constants. For w02-11 that is draft-ietf-quic-http-22 plus the QPACK draft of the same generation. |
| 5 | Code and cited spec disagree | **The fact is excluded, with the reason recorded**, as today's 6 exclusions are. The agent reads code, so scoring it against a spec value it never saw would punish being faithful. |
| 6 | Verification | **Mechanical, with the spec text pinned.** The source resolves to a `file:line` holding the value at the anchor commit, and the value appears in the cited section, compared as integers. The cited draft texts are fetched once and pinned beside the dataset ($0, network). |
| 7 | Today's RFC-final dataset | **Kept, renamed to its anchor** (aioquic HTTP/3 at `6d36838`), and never used to score w02-11 again. The SP7d scores against it stay on record, labelled ceiling-bound. |

**Evidence gathered during grilling, checked at the site:**
- **Spec D44** (`docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md:52`) says the w02-11
  set has "values from the pinned code, RFC sections recorded".
- **SP7d plan U3** (`docs/superpowers/plans/2026-09-15-arfc-sp7d.md:98-101`) pins each fact "to a
  `file:line` in the pinned aioquic checkout… and an RFC section".
- **Nobody noticed the pinned checkout was the tip:** it was `6d36838`, the 2025 tip, not the window's end.
- **The loop prompt** (`<pin>/ai_rfc/driver/prompts/loop.tmpl.md:28-29`) has the agent state "only what
  the cluster's own diff shows".
- **The code at `509065a`** (`git show 509065a:aioquic/h3/connection.py`) has:
  - 17 `HTTP_*` error codes, in hex;
  - 9 frame types, in hex, including `DUPLICATE_PUSH = 0xE`;
  - 4 settings and 4 stream types, in decimal. Ticket 03 showed decimals can't be scored from prose.
- **It declares h3-22:** ALPN `"h3-22"` in `examples/http3_client.py:294` and
  `examples/http3_server.py:298,433`, and the default `QuicProtocolVersion.DRAFT_22` at
  `aioquic/quic/configuration.py:80`.

**Consequences:**
- **Rulings 1, 2, 3 and 6 amend D44 and U3,** so a spec D-row is owed. Ticket 09's hand-off spec
  carries it.
- **Rulings 3 and 4 narrow ticket 07:** a target whose code declares no spec has no dataset.
- **The w02-11 candidates are 26 hex facts** (17 error codes + 9 frame types). Ticket 02's reachability
  test and ruling 5's agreement filter apply after that.
- **Pinning the cited drafts is new work.** It is ticket 10, which ticket 08 now waits on.
- **Per-revision scoring** (each tag against the code at its own cluster) was not decided. It is in the
  map's Not yet specified.
