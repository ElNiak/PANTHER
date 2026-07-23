# Strict Layer Resolution + APT Layer Merge

**Date**: 2026-03-30
**Status**: Design (v2 — simplified)
**Branch**: `release/v0.12.0-package-redesign-and-workspace-features` (ivy-lsp)

## Context

Running `IVY_LSP_LOG_LEVEL=DEBUG python -m ivy_lsp index --force --all` produces:
- 1,701 "Cross-layer collision (expected)" DEBUG messages
- 1,782 "Staging collision (layer-handled)" DEBUG messages
- 888 "Layer staging miss" WARNING messages

The collisions arise because the APT tree mirrors the standard protocol tree with **semantically different** modifications. The LSP must never resolve an APT file's include to the standard protocol variant.

Currently, when the layer system can't find a file via own-layer + `depends_on`, it falls back to **proximity-scoring across all layers**. This is the root cause of cross-protocol leakage — it should not exist.

## Key Insight

Each layer's `include_paths` already defines its physical boundary. A `quic` layer only contains files under `protocol-testing/quic/`. A `bgp` layer only contains `protocol-testing/bgp/`. Plus everyone gets stdlib. The proximity fallback across unrelated layers is a bug, not a feature.

## Design

### Change 1: Merge APT sub-layers

**Before (5 layers):**
```
apt_core:        7 dirs, no depends_on         (87 files)
apt_quic_fork:   quic dirs, depends_on=[apt_core]  (184 files)
apt_minip_fork:  minip dirs, depends_on=[apt_core]  (19 files)
apt_tls_fork:    tls dirs, depends_on=[apt_core]    (1 file)
apt_tests:       test dirs, depends_on=[all above]   (40 files)
```

**After (2 layers):**
```
apt:         all dirs merged (no depends_on)   (291 files)
apt_tests:   test dirs, depends_on=[apt]       (40 files)
```

Zero basename collisions between APT sub-layers. Merging eliminates the circular dependency and all 888 staging miss WARNINGs.

### Change 2: Remove cross-layer proximity fallback

Remove the proximity-scored fallback loop in `_resolve_via_layers()` (lines ~376-414). The resolution chain becomes:

```
1. Same directory as from_file → return
2. Own layer staging directory → return
3. depends_on layers (in declaration order) → return
4. Stdlib fallback → return
5. FAIL (unresolved — surface as diagnostic)
```

No cross-layer proximity guessing. If a file isn't reachable via own-layer + depends_on + stdlib, it's a missing dependency.

Also remove the workspace root fallback in `_resolve_via_flat_staging()` when layers are active — same principle.

### Change 3: Fix protocol file distribution

Each protocol must be self-contained. Current bugs:

| Protocol | File | Bug | Fix |
|---|---|---|---|
| bgp | `bgp/bgp_utils/file.ivy` | Empty stub (2 lines) | Copy from `quic/quic_utils/file.ivy` |
| coap | `random_value.ivy` | Missing entirely | Create coap-adapted version |

### Change 4: Update workspace config

Update `.ivyworkspace` files with merged APT layers. Remove `apt_quic` workspace group (no longer meaningful).

## Files to Modify

### ivy-lsp (submodule)
1. `ivy_lsp/core/indexer/include_resolver.py` — remove proximity fallback loop, remove workspace root fallback when layers active
2. `tests/test_group_scoped_resolution.py` (create) — test strict layer resolution
3. `tests/test_include_resolver_fallback.py` — update workspace root fallback expectations

### panther_ivy (parent)
4. `.ivyworkspace` (root) — merge APT layers, update groups
5. `protocol-testing/apt/.ivyworkspace` — merge APT layers
6. `protocol-testing/bgp/bgp_utils/file.ivy` — replace empty stub
7. `protocol-testing/coap/coap_utils/random_value.ivy` — create

## Verification

1. `IVY_LSP_LOG_LEVEL=DEBUG python -m ivy_lsp index --force --all`:
   - Zero "Layer staging miss" for APT
   - Zero "Intra-layer collision"
   - No new ERRORs
2. Run ivy-lsp test suite: `pytest tests/ -x`
3. Unresolved includes surface as diagnostics (not silent wrong-variant resolution)
