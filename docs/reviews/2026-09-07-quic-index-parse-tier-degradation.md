# QUIC index rebuild "parsing errors" — diagnosis

**Date:** 2026-09-07
**Question:** are the `.ivy` sources wrong, or is the indexing/parsing code wrong?
**Answer: the tooling. The `.ivy` sources are fine.**

Paths are relative to `panther/plugins/services/testers/panther_ivy/`;
ivy-lsp paths are under its `submodules/ivy-lsp/`.

**Status:** all four index defects fixed, each with tests — D4 `5aa2600`,
D3 `ba04158`, D1+D2 `f7c3e5e`. The cause of the transient itself, an unscoped
staging GC, is confirmed and fixed in `48227c7`. What remains is purely
operational: five protocol indexes still need rebuilding.

## The observable symptom

`protocol-testing/quic/.ivy-index/manifest.json` records 199 files, of which
**39 carry `"parse_tier": "lexer"` and `"completeness": "partial"`** instead of
`"ast"` / `"complete"`. Tier 1 is the real Ivy AST parser; Tier 2 is a
lexer-only fallback (`core/parsing/tiered_extractor.py:222-315`). A `lexer`
entry means the AST parse raised and the builder silently degraded.

For those 39 entries no error text is stored anywhere — that was defect D3,
now fixed, so future degradations record their reason. The existing 39 cannot
be explained retroactively.

## The `.ivy` files are not at fault

1. `quic_attacks_stack/replayed_packet.ivy` is **13 bytes**, containing exactly
   `#lang ivy1.7` — no declarations, no includes. It cannot have a syntax
   error, yet it is recorded `lexer` / `partial`. Likewise
   `quic_stack/quic_packet_stateless_reset.ivy` (237 bytes: a lang line and
   four comment lines).
2. Running the builder's own `_extract_one_file()` over all 39 in isolation:
   **0/39 degraded**.
3. Repeated with the builder's *exact* resolver construction — the
   per-protocol `protocol-testing/quic/.ivyworkspace` marker (2 layers), as
   `IndexBuilder._create_protocol_resolver()` uses, rather than the 8-layer
   workspace config: **0/40 degraded**.
4. A real `IndexBuilder(force=True, workers=1)` run with the tier logger
   captured: **104 consecutive files, every one `tier=1 (parser) succeeded`,
   zero failures** — including several the stored manifest marks degraded.

## The degradation is transient, then made permanent

One forced sequential rebuild did reproduce it (40 degraded: the same 39 plus
`quic_tests/server_tests/quic_server_test_stream_limit_error.ivy`), but three
later runs of the same code over the same files produced none. So the Tier-1
failure is **environmental and intermittent**, not a property of any file.

What makes it permanent is D1: once a file is recorded `lexer`, the SHA-keyed
cache copies that verdict forward on every subsequent rebuild. A transient
failure becomes a permanent index defect.

### Cause of the transient: an unscoped staging GC (CONFIRMED, FIXED `48227c7`)

Reported independently by a concurrent session, then **confirmed live**.
`_cleanup_stale_dirs` (`core/staging/flat.py`), called at the top of every
`prepare()`, `rmtree`d any `ivy-lsp-stage-*` directory older than an hour
judged purely by the directory's own mtime — no ownership, PID, or liveness
check. `mcp/startup.py:179` creates the server's staging directory once at
startup and never rewrites it, so after an hour a live server's directory is
indistinguishable from a leaked one.

**Observed directly:** `ivy_status` reported
`staging_dir: …/ivy-lsp-stage-7gqe1o2q` while that path did not exist on disk.
The running server's staging had already been deleted underneath it.

That accounts for every observation here: staging disappears, includes stop
resolving, the Tier-1 parse raises, and `TieredExtractor` falls back to the
lexer tier — intermittently, depending on whether a GC pass has run. It also
explains why isolated probes never reproduced it: each builds its own fresh
staging via `create_staging_directory()`.

**Fix:** `prepare()` writes an owner marker naming the creating PID; the GC
skips any stale directory whose owner is still running, and its own. Two
details are load-bearing. `PermissionError` from `os.kill(pid, 0)` means the
process is **alive** and owned by another user — reading it as dead restores
the bug on a multi-user machine. And a live PID is honoured only up to
`_MAX_LIFETIME_SECS`, because PIDs are recycled and a dead owner's number can
reappear on an unrelated process and pin a directory forever. Unmarked
directories keep the old mtime-only behaviour, so legacy dirs are still
collected.

Still not explained: `replayed_packet.ivy` has no includes at all, so losing
staging should not affect it. Either it degrades for a different reason, or
Tier 1 touches staging even for an include-free file. With D3 in place the
next occurrence records its own reason, which will settle it.

### The flat-staging basename collision is LATENT, not live (measured)

Flagged alongside the GC: three protocols define `file.ivy` (bgp, quic and
apt/quic) and the flat staging directory holds exactly one — APT's copy won
the build inspected. A resolution falling back to flat would silently compile
BGP against APT's file rather than failing.

Measured across the whole workspace rather than reasoned about. Resolution is
a chain — same-dir → layered → flat → stdlib — so flat is only reached when
the layered path misses:

- **2634 include sites, 0 unresolved, 26 cross-protocol.**
- All 26 are `apt → quic` (`quic_time` ×21, `random_value` ×5), which is **by
  design**: the `apt` layer declares `depends_on: ["quic"]`.
- Every single `include file` site resolves inside its own protocol —
  bgp→bgp, quic→quic, apt→apt — *despite* flat holding APT's copy.

So the layered path wins in every real case and the flat winner is never
consulted. The hazard is real but latent: it would bite only if a file lost
its layer mapping. Worth fixing on its own terms (a flat collision should
fail loudly rather than pick a winner), not as part of a GC change.

## Defects

### D1 — degraded parse tiers were cached forever (FIXED, `f7c3e5e`)
`lsp/index_cache.py`. A cache hit was keyed on the file's own SHA-256,
presence in five maps, and the manifest format version — ignoring
`parse_tier`, `builder_version`, and the file's **include closure**. The
cached entry, `parse_tier: lexer` included, was copied forward verbatim, so
fixing the parser un-degraded nothing.

**Fix:** `classify_files()` takes `retry_degraded` and treats a cached
non-`ast` tier as a miss. `build_protocol()` passes it only when this build
could actually do better — Tier 1 available and not `fast` mode — so a build
that cannot improve on the cached verdict does not pay to retry. A healthy
`ast` entry stays a cache hit, bounding the cost by the number of degraded
files.

### D2 — the MCP `ivy_index` tool could not repair it (FIXED, `f7c3e5e`)
`mcp/tools/analysis.py` built `IndexBuilder(ctx.root, ws_config, fast=fast)`
and the tool declared no `force`, so through MCP there was no way to re-parse
a cached entry short of editing the file. The CLI had `--force`; the tool
exposed nothing.

**Fix:** `ivy_index` gains `force`, wired through to `IndexBuilder`. Note the
test asserts the *declared schema* rather than passing the argument: the MCP
layer silently drops unknown kwargs, so a call with `force=True` succeeded
before the fix and proved nothing.

### D3 — the parse errors were computed, then discarded (FIXED, `ba04158`)
`lsp/index_builder.py` assembled a `tier1_failures` summary and returned it in
the result dict; `write_index_artifacts` never persisted it. The manifest
stored the tier, never the reason. Worse, the accumulator sat inside the
*extraction-results* loop, so it covered only cache **misses** — after one
rebuild a cached-degraded file contributed nothing. This is why the original
39 failures cannot now be explained: the evidence was discarded at write time.

**Fix:** `_extract_one_file()` writes a truncated `parse_error` into the
manifest entry whenever Tier 1 raised, so the reason is stored on disk and
replayed with the cached entry; and `build_protocol()` now derives its
`tier1_failures` summary from `manifest_files` rather than from the current
run's extractions, so a file that degraded on an earlier build and came back
as a cache hit is still reported. `ivy_index` already returns the build
summary, so the reason reaches MCP callers with no tool change.
`parse_error` is optional, so `INDEX_FORMAT_VERSION` is deliberately **not**
bumped — bumping it would invalidate every cached entry.

Note this does not retro-explain the existing 39: their reasons were already
lost. It ensures the next occurrence is explainable.

### D4 — `write_model_to_index` destroyed healthy indexes (FIXED, `5aa2600`)
`mcp/model_builder.py`. Three compounding defects:

1. **Wrong search root.** `McpServerState.find_ivy_files(search_root)`
   (`mcp/server.py:250-283`) joins **workspace-relative** `include_paths`
   (e.g. `protocol-testing/quic/quic_stack`) onto `search_root`, so it expects
   the workspace root. It was called with a *protocol directory*, producing
   `…/protocol-testing/quic/protocol-testing/quic/quic_stack` — never a real
   path. Every `isdir` check failed and the result was empty for **every**
   protocol. (`server.py:276-281` logs `"include_paths %s yielded no .ivy files
   under %s"` on each pass.)
2. **Wrong path contract.** `find_ivy_files` returns paths *relative to the
   search root* (`infra/utils/ivy_output.py:500-519`), but the caller passed
   them straight to `os.stat()`, which resolves relative paths against the CWD.
3. **Unconditional write.** `manifest.json` was written every time, despite a
   docstring promising it only bootstraps directories "if they don't exist
   yet". A `version: 1` stub with an empty `files` map replaced richer
   `version: 2` IndexBuilder manifests — destroying the index *and* downgrading
   the format version, which invalidates every cached entry.

Observed on disk before the fix:

| protocol | `.ivy` files on disk | files in manifest |
|---|---|---|
| apt | 360 | **0** |
| coap | 37 | **0** |
| minip | 19 | **0** |
| new_prot | 10 | **0** |
| bgp | 49 | 49 |
| quic | 199 | 199 |

`bgp` and `quic` looked healthy only because a real `IndexBuilder` run later
overwrote their stubs. During the investigation the running MCP server
clobbered QUIC's healthy 199-file manifest **twice** (15:17 and 15:43); both
times it was restored from a backup.

Why the tests missed it: `tests/test_mcp_index_bootstrap.py`'s mock
`find_ivy_files` did a plain `os.walk` returning absolute paths, modelling
neither the relative-path contract nor the `include_paths` joining.

**Fix:** call the finder once with the workspace root and bucket results per
protocol; resolve returned paths against that root (which also accepts absolute
paths unchanged); and write `manifest.json` only when it is absent and the file
map is non-empty. The model pickle is still written either way. Five tests
added under `TestWriteModelToIndexDoesNotClobber`, using a finder that mirrors
the real contract.

## Impact of the remaining defects

`_extract_one_file` passes `ast=result.ast` into `extract_requirements`, and
`result.ast` is `None` on a lexer-tier result (`index_builder.py:216-233`);
exports fall back to `extract_exports_imports_light`. So symbols, exports and
requirements for ~20% of the QUIC model come from the degraded path.
`core/analysis/requirement_graph.py:192-198` notes that `"ast"` and `"lexer"`
nodes can describe the same file — a plausible root of the open
"requirement extraction is nondeterministic" bug.

## Recommended next steps

All code defects are fixed, including the staging GC. What remains is
operational, and it needs a server restart first so the running process picks
up `48227c7` — otherwise it keeps deleting staging directories.

1. **Restart the MCP server**, so the GC fix is loaded.
2. **Rebuild the five stubbed protocols.** See the recovery note below — a
   restart stops further damage but repairs nothing already on disk.
3. **Rebuild quic with `force`** and read the tier distribution. With D1 the
   39 degraded entries are now re-parsed rather than replayed; with D3, any
   that still fail record why. This is the experiment that closes the case —
   in particular whether an include-free file such as `replayed_packet.ivy`
   can degrade at all once staging is stable.

Optional, on its own terms: make a flat-staging basename collision fail
loudly rather than silently pick a winner. Measured as latent today (see
above), so it is a hardening change, not a repair.

## Recovery is NOT automatic after the restart

The D4 fix deliberately never overwrites an existing `manifest.json`. So a
restarted server, seeing the five empty `version: 1` stubs already present
(apt, bgp, coap, minip, new_prot), will leave them exactly as they are. **The
restart stops further destruction; it repairs nothing.** Only quic is intact,
and only because it was restored from a backup.

Recovery is one `IndexBuilder` run per stubbed protocol — `classify_files`
rejects `version: 1`, so each does a full re-extract — or deleting the stub
first and letting the bootstrap or a build recreate it.

`ivy_index` now takes `force` (D2), but two traps on that path remain,
already recorded in project memory: `ivy_index(protocol=<one>)` narrows the
semantic model and reports 0% coverage, while `ivy_index(protocol="all")`
times out at 300 s. For a bulk repair prefer the CLI —
`ivy-lsp index <protocol_dir> --force --workers N` — which has no tool
timeout.

## Notes for whoever picks this up

- A full QUIC index build takes roughly 10 minutes and exceeds a 10-minute
  tool timeout. Redirect output to a file rather than piping it, or the results
  are lost when the process is killed.
- `.ivy-index/` is gitignored derived data. Back up `manifest.json` before
  experimenting; a run killed part-way can leave it as an empty stub.
- The tier-selection reason is logged at DEBUG by
  `ivy_lsp.core.parsing.tiered_extractor`; raising just that one logger
  captures it without flooding the log.

## Test baseline

ivy-lsp suite with the worktree `.venv`: **6 failed, 3485 passed, 35 skipped**.
The same 6 reproduce at pristine `HEAD` with the changes reverted, so they are
pre-existing: `test_requirement_extraction_determinism.py` (2) and
`test_validation_correctness.py` (4).

**Do not trust a red full-suite run on its own.** Under `-n auto` against
destroyed or stubbed indexes, the 4 `test_validation_correctness` failures
turn into 6-11 *errors* — an environment artifact of the missing indexes, not
a regression. Re-run those two files serially before concluding anything:

    pytest tests/test_validation_correctness.py \
           tests/test_requirement_extraction_determinism.py

---

# Follow-up, 2026-09-08: what D3 revealed

`apt` and `coap` were rebuilt after D3 landed, so for the first time their
degraded entries carry reasons. They are **three different causes**, not one —
the single-cause assumption that drove the original investigation was wrong.

## apt — configuration drift, 36 files (FIXED, panther_ivy `bb1b9afc`)

Every reason is `module quic_time.ivy not found` (×31) or
`module random_value.ivy not found` (×5). Both modules exist only under
`protocol-testing/quic/quic_utils/`.

`IndexBuilder._create_protocol_resolver()` prefers a protocol's own
`.ivyworkspace` over the workspace-level one. The two `apt` layer definitions
have **identical `include_paths`**, but the workspace-level marker declares
`depends_on: ["quic"]` and the per-protocol marker declared no dependency at
all. So apt's own index build could not reach quic's modules, and a fifth of
the apt model was indexed without an AST.

**Fix:** add a `quic` layer mirroring the workspace-level definition and make
`apt` depend on it. quic's paths and apt's do not overlap, so this does not
hit the `_file_to_layer` reassignment hazard that bites when a shared
directory is listed under two layers. Verified against the builder's own
resolver: **36 of 41 now reach tier `ast`**.

The deeper question is left open: should the builder prefer a per-protocol
marker at all, when the workspace-level marker holds the authoritative
cross-protocol dependency graph? Fixing the data was the smaller change; the
drift can recur.

## coap — genuine `.ivy` defects, but NOT one-line fixes (NOT fixed)

Unlike quic, here the sources really are wrong. Two defects, both deeper than
they first appear — an attempted fix was made and **reverted**.

**`coap_message_method.ivy`** has two `around handle { }` blocks (lines
120-124 and 135-139) whose only content is a commented-out `# ...`. Ivy's
`...` marks where the wrapped action's body splices in, so the blocks are
empty and the closing brace is a syntax error, cascading to nine files.
Uncommenting it does **not** fix it: the error simply moves to
`line 122: unexpected token '...'`. A lone `...` is not a valid `around`
body — every working example (`bgp_error_code.ivy:85`, `quic_frame.ivy:718`)
has real statements around it. Making these blocks valid means deciding what
the CoAP request and response handlers should actually do, which is a
modelling decision, not a syntax patch.

**`coap_state_management.ivy`** is written in pseudo-Ivy throughout, so
line 29 is not the only problem: `import coap_message` (a file, not an
action), `map[ip.endpoint, coap_interaction]` (bracketed generics), `if
endpoint in interactions` (an `in` operator), and
`interactions[endpoint].state := ...` (map subscripting) are all non-Ivy.
Fixing line 29 alone would move the error to line 38. The file needs a
representation decision — most likely a `function` or a `map` module
instance — not an edit.

## Ten files are 0 bytes

Five under apt and five under coap are empty placeholders. `TieredExtractor`
returns `tier_used=0` for empty source, recorded as `parse_tier: "unknown"`
with no `parse_error`. They are not failures, but they do inflate the
degraded count — worth distinguishing in any future report.

## The reason string now names its file (ivy-lsp `09bb524`)

D3 persisted the reason but `format_ivy_error` rendered only
`line 124: syntax error`, dropping the `.filename` the error object carries.
Nine coap files therefore showed byte-identical messages while the defect was
in one shared include, and locating it took five probes. Case 2 now renders
`<basename>:<line>: …`, matching the `quic_shim.ivy:47` style the tuple cases
already used. Errors without a location keep the old wording.

## CLOSED — verified end to end, 2026-09-08

The server was restarted and the indexes rebuilt. **The staging GC fix is
confirmed live**: the new staging directory exists and carries an
`.ivy-lsp-owner` marker (`pid 36306`), so `48227c7` is the code running and
the collector can no longer reclaim it.

Rebuilds were incremental, not forced — D1 makes a degraded entry a cache
miss, so only the damaged files were re-parsed:

| protocol | before | after | outcome |
|---|---|---|---|
| **quic** | `ast 160, lexer 39` | **`ast 199`** | **all 39 recovered**, 317 s |
| **apt** | `ast 289, lexer 36, unknown 5` | **`ast 325, unknown 5`** | all 36 recovered, 483 s |
| coap | `ast 22, lexer 10, unknown 5` | unchanged | real source defects, as predicted |

**The original question is answered.** QUIC's 39 files were never wrong. They
parse at full AST tier once the staging garbage collector stops deleting the
running server's staging directory. The `.ivy` sources were fine throughout;
every one of the five defects was in the tooling.

coap is unchanged by design — its 10 failures are genuine `.ivy` syntax
defects and are documented above. They now report
`coap_message_method.ivy:124` and `coap_state_management.ivy:29` instead of
nine indistinguishable "line 124" messages, which is the D3 + `09bb524` pair
working in production. The 10 remaining `unknown` entries across apt and coap
are 0-byte placeholder files, not failures.

## The 600 s model timeout — diagnosed and fixed (`45138a4`)

Not the stub indexes, as this document twice guessed. **A healthy index was
reporting itself stale**, so the semantic model never loaded from it and every
attempt fell back to a full 644-file rebuild that died on the 600 s timeout.
That is why `ivy_coverage` and `ivy_diagnostics(mode=full)` were unavailable.

Two independent causes, either sufficient alone, because `build_mcp_model()`
accepts the offline merge only when **nothing** was skipped:

1. **SHA-validated cache, mtime-judged staleness.** `classify_files()` accepts
   a cache hit when the **SHA** matches and copied the entry verbatim, keeping
   its old `mtime`; `_check_staleness()` judges by **mtime**. A file whose
   timestamp moved without a content change — a checkout, a rebase — therefore
   read as "modified" forever. Measured: **bgp 9/49 files drifted, apt
   108/330**, both by ~18 hours, both `stale_major` minutes after a successful
   rebuild. The SHA already proves the content is unchanged, so the entry is
   now refreshed with the file's current mtime (on a copy, not the loaded
   index).
2. **An empty manifest was unconditionally `stale_major`.** Correct when the
   index was destroyed, wrong when the protocol genuinely has no `.ivy` files.
   `patterns` has none, so it could never be fresh and poisoned the gate by
   itself. The two cases are now distinguished by looking for a source file.

Measured effect: **before, 4 protocols used and 3 skipped → fall back. After,
7 used and 0 skipped → Strategy 1 succeeds.**

Not yet observed live: the running server holds the pre-`45138a4` code, so
confirming the model actually loads needs one more `/mcp` reconnect.

## Still open

- **coap's two modelling defects** — deliberately left, see above.
- Nothing is pushed and no gitlink is bumped.
