# 03 — How often would scoring a bare decimal near a symbol be wrong?

Type: research (AFK)
Status: resolved (2026-09-21, research subagent)
Claimed: research subagent (2026-09-21)
Blocked by: —
Parent: [Ground-Truth Yardstick](../map.md)

## Question

The scorer scores only hex values. `_value_shape` (`<pin>/ai_rfc/experiment/ground_truth.py:439-441`)
excludes a fact whose value is a bare decimal, on the reasoning that "prose does not distinguish it
from any other number that falls near the symbol". In the w02-11 window the settings are written in
decimal (`QPACK_MAX_TABLE_CAPACITY = 1`, `QPACK_BLOCKED_STREAMS = 7`), and so are the four stream types.
A window-anchored dataset (ticket 01) would therefore lose them unless decimals can be scored.

**Measure it.** Use the scorer's own normalisation (l.383), symbol pattern (l.410-415), window
(`NEARBY_CHARS = 120`, l.33, both sides, l.562-563) and integer comparison (l.326), with decimal
tokens admitted. Run it over:

- the window's shown material: `<pristine>/clusters/c0002-*` … `c0011-*/span.diff`;
- the three drafts: `<t11>/armA-drafts/A1-10.md`, `A2-10.md`, and the pilot draft if a copy can be
  found read-only.

For every (symbol, decimal token within 120 chars) pair, record whether the token equals the symbol's
window-end value or is unrelated (a line number, a count, another constant). Report the false-match
rate per fact kind (setting, stream type, error code), with counts and examples.

## Constraints

Read-only. Never write in `<ai_rfc>` or `~/ai-rfc-experiments`. Import the scorer from `<pin>` (e.g.
`~/ai-rfc-experiments/code-pins/venv-3406985/bin/python`); do not copy its logic by hand where it can
be called. Findings go to `../research/03-bare-decimal-false-match.md`.

## Resolution

At W = 120, every decimal near a setting in the window is unrelated (13/13 pairs; the drafts name no
setting). Stream types show the same in the window (77/77). In the drafts 328 of 450 pairs are
unrelated, and the other 122 are equal only by coincidence (claim-tag digits such as `ai_rfc:h3.1`, or
`HTTP/3`); error codes have 0 equal pairs out of 40. Neither corpus holds a single genuine decimal
statement of any setting or stream type, so a decimal-admitting scorer would score only noise: 4
spurious matches and 4 spurious mismatches out of 8 draft entries. Narrowing to 40 or 60 characters or
adding a `.` guard does not change that. Findings:
[research/03-bare-decimal-false-match.md](../research/03-bare-decimal-false-match.md)

**Note (2026-09-21, session 0ea41509):** the research took its window-end values from `d290ebea`, which
charting mis-named as the window's end. The real end is `509065a` (ticket 01). The result is
unaffected: the whole enum block (`class ErrorCode` through `class StreamType`, 47 lines) is
byte-identical at both commits (checked with `diff`).
