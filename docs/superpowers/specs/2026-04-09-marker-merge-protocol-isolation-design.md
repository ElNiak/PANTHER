# Marker-Merge Protocol Isolation

**Date:** 2026-04-09
**Status:** Draft
**Scope:** `ivy_lsp/core/workspace/detection.py`, `ivy_lsp/core/indexer/include_resolver.py`

## Problem

When the ivy-lsp opens at the `panther_ivy/` root, `_build_panther_workspace()` generates coarse heuristic layers with `include_paths=["protocol-testing/{protocol}"]` per discovered protocol. Because `os.walk` recurses into subdirectories, the `apt` layer walks into `apt/apt_protocols/quic/`, which contains modified copies of files also in `protocol-testing/quic/`. This produces 189 basename collisions (78 with genuinely different content) in the flat staging pass.

The per-protocol `.ivyworkspace` markers already define fine-grained, non-overlapping layer scopes, but the heuristic ignores them. The marker-based detection paths (`_walk_up_for_marker`, `_walk_down_for_marker`) stop at the first marker found, returning a single-protocol config instead of a merged multi-protocol one.

## Goal

Index all protocols simultaneously with full isolation. Each protocol's includes resolve only within its own layer scope. Zero cross-protocol collisions. The flat staging collision count should reflect only genuine intra-layer problems (ideally zero).

## Design

### 1. Replace heuristic layer generation with marker merging

**File:** `detection.py` — `_build_panther_workspace()`

Currently, this function calls `_discover_protocols()` to find protocol directories with `.ivyworkspace` markers, then creates one coarse layer per protocol. The fix: after discovering protocols, read each protocol's `.ivyworkspace` marker via `_read_marker` / `_apply_marker`, and merge their `workspace_layers` into a single `WorkspaceConfig`.

Merging rules:

- **workspace_root**: All markers use `workspace_root_offset: "../.."` pointing to `panther_ivy/`. Verify they resolve to the same root; warn and skip any that don't.
- **workspace_layers**: Concatenate all layers from all markers. Layer IDs are already protocol-scoped (`quic`, `quic_tests`, `apt`, `apt_tests`, `bgp`, `coap`, `minip`) so no conflicts.
- **include_paths**: Union of all layers' include_paths (flattened), same as today but derived from markers instead of coarse protocol dirs.
- **exclude_paths**: Intersection-like merge. Use the superset of all exclude_paths across markers (union). All current markers share the same base excludes (`doc`, `examples`, `test`, `notebooks`, `patches`, `submodules`, `ivy`); some add protocol-specific excludes (apt excludes `dns`, `http`, `smtp` subdirs).
- **standard_library**: All markers declare `"ivy/include/1.7"`. Use the first non-null value; warn if they disagree.
- **depends_on**: Preserved as-is from each marker's layer definitions. Cross-protocol dependencies (e.g., `apt_tests` depends on `apt`) remain valid because all layers are in the merged config.
- **protocol_id**: Not applicable at the merged level. Set to `None`. Individual protocol IDs are encoded in layer IDs.
- **workspace_groups**: Union of all markers' `workspace_groups` (currently empty for all markers).
- **detected_by**: Set to `"heuristic+marker"` to reflect that the PANTHER heuristic discovered the project but layer definitions came from markers. Tests that assert `detected_by == "heuristic"` must be updated: `test_workspace_detection.py:153,280` and `test_index_cli.py:62,79`.
- **Fallback for v1/v2 markers or parse failures**: If a marker fails to parse (wrong version, malformed JSON), log a warning and **skip that protocol entirely** (do not generate a coarse fallback layer). A coarse `protocol-testing/{protocol}` layer would reintroduce the recursive walk that causes cross-protocol collisions, defeating the purpose of this change. The skipped protocol's files will not be indexed until its marker is upgraded to v3.

### 2. Fix `_walk_down_for_marker` short-circuiting (detection step 4)

`_walk_down_for_marker` returns the first marker it finds. When the LSP starts at a directory above `panther_ivy/` (e.g., the PANTHER repo root), step 4 could find one protocol's marker and return a single-protocol config, bypassing the heuristic.

Fix: In the PANTHER project context, `_walk_down_for_marker` should not match per-protocol markers inside `protocol-testing/`. The cleanest approach is to do nothing here; the heuristic (step 5) already runs after step 4 fails, and per-protocol markers have `workspace_root_offset` pointing outside their own directory, which means they resolve to `panther_ivy/` — a valid workspace root. The risk is that step 4 finds `apt/.ivyworkspace` first and returns a config for apt only.

Two options:
- **Option A (simpler):** Add a guard in `_walk_down_for_marker`: skip markers whose resolved `workspace_root` differs from the walk's `start_dir`. A marker that points elsewhere via `workspace_root_offset` is a sub-workspace marker embedded in a larger project; the walk should not adopt it as the top-level config. This guard is scoped to `_walk_down_for_marker` only — `_walk_up_for_marker` is unaffected, preserving the legitimate case where someone opens the LSP directly at `protocol-testing/quic/` and the walk-up finds `quic/.ivyworkspace`.
- **Option B:** No change to `_walk_down_for_marker`. Instead, ensure the improved `_build_panther_workspace` is always reached by giving the PANTHER heuristic higher priority (move step 5 before step 4). This is riskier as it changes detection order for non-PANTHER projects.

**Recommendation:** Option A.

### 3. Flat staging collision reporting (cosmetic)

After this fix, `create_staging_directory()` still runs first and computes a flat collision map. With correct per-marker layers, `build_layered_staging()` then creates isolated per-layer directories where each layer has its own copy of colliding basenames.

The `staging_health()` method currently reports the flat collision count, which will still show cross-layer collisions even though they're handled.

**Important context:** `_resolve_via_flat_staging` already returns `None` when layers are active (`include_resolver.py:481-482`), so the flat collisions cause zero functional harm — resolution never consults the flat staging directory when `_file_to_layer` is populated. This means the collision count is purely a misleading observability metric, not a correctness issue. Two options:

- **Option A (minimal):** Add a `cross_layer_collisions` vs `intra_layer_collisions` breakdown in `staging_health()`. The top-level `collisions` field becomes the intra-layer count (the only ones that matter).
- **Option B:** Skip flat staging entirely when layers are configured; `build_layered_staging` already creates self-contained per-layer dirs. This removes the misleading metric at the source.

**Recommendation:** Option A for this change. Option B is a separate follow-up since it changes the resolution fallback chain.

## Scope

### Files to modify

| File | Change |
|------|--------|
| `detection.py` | Rewrite `_build_panther_workspace` to read+merge markers; add guard to `_walk_down_for_marker` |
| `include_resolver.py` | Add intra/cross-layer collision breakdown in `staging_health()` |

### Files to add

None.

### Consumers verified as transparent (no changes needed)

`server_setup.py`, `mcp/server.py`, `index_builder.py`, `analysis.py`, `context.py`, and `__main__.py` all consume `WorkspaceConfig` opaquely via `detect_ivy_workspace()`. They pass include_paths and workspace_layers to the resolver without inspecting layer structure. No code changes needed in these files.

### Test changes

| File | Change |
|------|--------|
| `test_workspace_detection.py` | Update `_panther_heuristic` tests: assert merged layers match markers, not coarse heuristic layers. Update `detected_by` assertions from `"heuristic"` to `"heuristic+marker"` (lines 153, 280). Add test for multi-protocol marker merge. Add test for `_walk_down_for_marker` skip-sub-workspace guard. |
| `test_index_cli.py` | Update `detected_by` / `project_type` assertions (lines 62, 79) to expect `"heuristic+marker"`. |
| `test_staging_health_integration.py` | Assert `intra_layer_collisions == 0` for PANTHER workspace. |

## Edge Cases

1. **Protocol without a v3 marker**: `_build_panther_workspace` currently requires a `.ivyworkspace` marker to discover a protocol. If a new protocol dir has a v1/v2 marker (or none), it's excluded from discovery. The protocol is skipped entirely with a warning — no coarse fallback layer is generated, because a recursive `protocol-testing/{protocol}` walk would reintroduce cross-protocol collisions.
2. **Conflicting workspace_root_offset**: If a marker resolves to a different root, warn and skip it.
3. **Layer ID collision across markers**: Unlikely given naming convention (`quic`, `apt`, `bgp`, etc.), but validate and error if it occurs.
4. **Empty markers** (`{"version": 3}` with no layers): `_apply_marker` returns a config with empty layers. When merging, these contribute nothing and are harmless. The existing test at line 684 uses this pattern.

## Non-Goals

- Per-protocol `IncludeResolver` instances (Approach B). The merged config with correct layers achieves isolation within a single resolver.
- Eliminating the flat staging pass (Approach C). The flat staging remains as a fallback for non-layered workspaces and for the stdlib resolution path.
- Changing how `set_active_workspace` works. It remains a filter-only operation on the merged layer set.
