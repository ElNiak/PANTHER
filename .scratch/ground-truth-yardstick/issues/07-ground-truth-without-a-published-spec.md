# 07 — How is ground truth built for a target with no published spec?

Type: grilling (HITL)
Status: resolved (2026-09-21, session 0ea41509)
Claimed: session 0ea41509 (2026-09-21)
Blocked by: [01 — What is a window's ground truth anchored to?](01-what-is-ground-truth-anchored-to.md), [02 — What counts as reachable?](02-what-counts-as-reachable.md)
Parent: [Ground-Truth Yardstick](../map.md)

## Question

The rule must be general (ruling 3). MARK (`gitlab.cylab.be/cylab/mark`, window [1, 69]) has no RFC and
no dataset. aioquic's dataset was built by hand from RFC sections. For a target without a published
spec, where do the facts come from?

- **(A)** Mechanical extraction from source at the anchor commit (enums, constant assignments,
  config defaults), checked by a human.
- **(B)** Hand curation from the repository's own docs.
- **(C)** Declare reachable recall undefined for such targets and report only form metrics and the
  judge.

Also decide who checks a mechanically extracted fact, and whether an extracted fact must also pass
ticket 02's reachability test to be scored.

**Narrowed by 01 (resolved 2026-09-21).** Every fact must cite the spec version the code *declares*
at the anchor (rulings 3 and 4), and a target that declares none gets no dataset. Options (A) and (B)
survive only if something short of a published spec can count as declared. The question that
remains: **can a repository's own protocol document count as its declared spec** (for example a
versioned `PROTOCOL.md` or an API reference the code names)? If yes, what makes such a document
citable (versioned, pinned, named by the code)? If no, MARK gets no ground truth and its evaluation
rests on form metrics and the judge (option C). First check whether MARK's code names any document or
version it implements.

**02 resolved (2026-09-21):** if 07 allows a spec-less target a dataset, its facts use the same
reachability test. A fact is reachable when its own source line at the anchor is an added line in an
in-window cluster diff of the same file (MARK is Java, and the test is language-agnostic).

## Starting evidence

Depends on 01 (what a fact is anchored to) and 02 (what reachable means). MARK's pristine:
`~/ai-rfc-experiments/rebuild-sp7d/pristine/mark-w01-69` (and the original `pristine/mark-w01-69`).

## Resolution

Grilled with the user on 2026-09-21. **A spec counts as declared only when the code itself names it.
MARK names none, so it gets no ground-truth dataset.**

| # | Question | Ruling |
|---|---|---|
| 1 | What counts as a declared spec | **Only what the code itself names:** an ALPN or version constant, or an explicit reference to a versioned document. It is the literal reading of 01's "the spec version the code declares". A repository document the code never names does not count, and neither does anything chosen by hand. |

**Evidence** (MARK pristine `~/ai-rfc-experiments/pristine/mark-w01-69`, read-only):
- **The anchor is the tip.** MARK's window [1, 69] ends at its clone head `b901f36`, the last member
  of c0069 (`timeline/members.jsonl`).
- **The code declares no spec.** `git grep` at `b901f36` over `*.java`, `*.md` and `*.xml` finds no
  ALPN, no protocol-version constant, and no code reference to a document. The only hits are
  `jsonrpc4j` imports, changelog lines, and prose in `CONTRIBUTING.md`.
- **Its own API document exists, but nothing names it.** `API_Doc_classification.md` is 361 lines
  headed "jsonrpc API", listing method names, parameters and response types. It was last touched by
  `ef458d8` (2024-02-28, "[clean]"), and no code refers to it.
- **Its values couldn't be scored anyway.** MARK's main Java (excluding `/test/`) has **0** hex
  constants; all 55 named constants are decimal or string (`CONNECTION_TIMEOUT = 5000` in
  `client/Client.java:25`, `FILE_KEY = "file"` in `server/…/data/FileSource.java:54`). The scorer
  scores hex only, and research 03 showed decimals score noise.

**Consequences:**
- **MARK has no dataset.** Its reachable recall and claim accuracy are **unmeasured**: `None` with
  the reason "no declared spec", never 0. Its evaluation rests on the form metrics (`analyze`) and the
  judge. Ticket 13 carries this into the report.
- **The remaining sub-questions are already answered.** For any target that does declare a spec,
  facts are checked mechanically against pinned text (01, ruling 6) and must pass the source-line
  reachability test (02).
- **No current target needs a scorer for string- or decimal-valued facts.** This is noted here, not
  ruled out of scope: it would come back if a target with a declared spec had non-hex facts.
- **The Main Campaign map must not preregister a recall figure for MARK.**
