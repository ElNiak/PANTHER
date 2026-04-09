# Marker-Merge Protocol Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix ivy-lsp workspace detection so that all protocols are indexed simultaneously with full isolation — each protocol's includes resolve only within its own layer scope, eliminating 189 cross-protocol basename collisions.

**Architecture:** Replace the coarse PANTHER heuristic in `_build_panther_workspace()` with a marker-merge strategy that reads each per-protocol `.ivyworkspace` marker and concatenates their fine-grained layer definitions. Add a guard in `_walk_down_for_marker` to prevent sub-workspace markers from short-circuiting detection. Add intra/cross-layer collision breakdown in `staging_health()`.

**Tech Stack:** Python 3.10+, pytest, ivy-lsp workspace detection infrastructure

**Spec:** `docs/superpowers/specs/2026-04-09-marker-merge-protocol-isolation-design.md`

---

All paths below are relative to:
```
panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/
```

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `ivy_lsp/core/workspace/detection.py` | Modify | Rewrite `_build_panther_workspace`, add guard to `_walk_down_for_marker` |
| `ivy_lsp/core/indexer/include_resolver.py` | Modify | Add intra/cross collision breakdown in `staging_health()` |
| `tests/test_workspace_detection.py` | Modify | Update existing tests, add marker-merge + guard tests |
| `tests/test_staging_health_integration.py` | Modify | Add collision breakdown assertion |

---

### Task 1: Add `_walk_down_for_marker` guard test (TDD)

**Files:**
- Modify: `tests/test_workspace_detection.py`

- [ ] **Step 1: Write the failing test**

Add a test to `TestWalkDownForMarker` that creates a sub-workspace marker with `workspace_root_offset` pointing to an ancestor, and asserts the walk-down skips it.

```python
def test_skips_sub_workspace_marker(self, tmp_path):
    """Walk-down skips markers whose resolved root differs from start_dir."""
    # Create an isolated parent so we don't walk into sibling test dirs
    parent = tmp_path / "walk_root"
    project = parent / "project"
    sub = project / "protocol-testing" / "quic"
    sub.mkdir(parents=True)
    marker = {
        "version": 3,
        "workspace_root_offset": "../..",
        "workspace_layers": [
            {"id": "quic", "include_paths": ["protocol-testing/quic"]}
        ],
    }
    (sub / ".ivyworkspace").write_text(json.dumps(marker))
    # Walk-down from parent should skip this marker because its
    # resolved root (project/) != start_dir (parent/)
    parent.mkdir(parents=True, exist_ok=True)
    config = _walk_down_for_marker(str(parent))
    assert config is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_detection.py::TestWalkDownForMarker::test_skips_sub_workspace_marker -xvs`

Expected: FAIL — current `_walk_down_for_marker` returns the config instead of skipping it.

- [ ] **Step 3: Implement the guard in `_walk_down_for_marker`**

In `ivy_lsp/core/workspace/detection.py`, modify `_walk_down_for_marker` (lines 154-174). After `_apply_marker` returns a config, check if the resolved `workspace_root` differs from the walk's `start_dir`:

```python
def _walk_down_for_marker(
    start_dir: str, max_depth: int = 6
) -> Optional[WorkspaceConfig]:
    """Walk down up to *max_depth* levels looking for ``.ivyworkspace``."""
    start = os.path.abspath(start_dir)
    for dirpath, dirnames, filenames in os.walk(start):
        rel = os.path.relpath(dirpath, start)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > max_depth:
            dirnames.clear()
            continue
        # Skip hidden dirs and common noise
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if _IVYWORKSPACE_FILENAME in filenames:
            candidate = os.path.join(dirpath, _IVYWORKSPACE_FILENAME)
            data = _read_marker(candidate)
            if data is not None:
                config = _apply_marker(candidate, data)
                if config is not None:
                    # Guard: skip sub-workspace markers whose resolved root
                    # differs from start_dir.  A marker with workspace_root_offset
                    # pointing elsewhere is embedded in a larger project and should
                    # not be adopted as the top-level config.
                    resolved = os.path.realpath(config.workspace_root)
                    if resolved != os.path.realpath(start):
                        logger.debug(
                            "Skipping sub-workspace marker at %s "
                            "(resolved root %s != start %s)",
                            candidate,
                            resolved,
                            start,
                        )
                        continue
                    return config
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_detection.py::TestWalkDownForMarker -xvs`

Expected: All `TestWalkDownForMarker` tests PASS (existing tests unbroken, new test passes).

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/workspace/detection.py tests/test_workspace_detection.py
git commit -m "fix: skip sub-workspace markers in _walk_down_for_marker

Markers whose resolved workspace_root differs from the walk's start_dir
are sub-workspace markers embedded in a larger project. Skipping them
prevents detection step 4 from short-circuiting to a single-protocol
config in PANTHER projects."
```

---

### Task 2: Add marker-merge tests for `_build_panther_workspace` (TDD)

**Files:**
- Modify: `tests/test_workspace_detection.py`

- [ ] **Step 1: Write the failing test for marker merging**

Add a new test class that creates a multi-protocol PANTHER workspace with real v3 markers and asserts the heuristic produces merged layers.

```python
class TestPantherHeuristicMarkerMerge:
    def _make_panther_workspace(self, tmp_path):
        """Helper: create a PANTHER workspace with quic and minip markers."""
        panther_ivy = (
            tmp_path / "panther" / "plugins" / "services" / "testers" / "panther_ivy"
        )
        pt = panther_ivy / "protocol-testing"
        # Create quic marker with fine-grained layers
        quic_dir = pt / "quic"
        (quic_dir / "quic_stack").mkdir(parents=True)
        (quic_dir / "quic_utils").mkdir(parents=True)
        (quic_dir / "quic_tests").mkdir(parents=True)
        (quic_dir / "quic_stack" / "quic_connection.ivy").write_text("# quic conn")
        (quic_dir / "quic_utils" / "byte_stream.ivy").write_text("# quic byte_stream")
        quic_marker = {
            "version": 3,
            "standard_library": "ivy/include/1.7",
            "protocol_id": "quic",
            "workspace_root_offset": "../..",
            "workspace_layers": [
                {
                    "id": "quic",
                    "include_paths": [
                        "protocol-testing/quic/quic_stack",
                        "protocol-testing/quic/quic_utils",
                    ],
                    "priority": 1,
                },
                {
                    "id": "quic_tests",
                    "include_paths": ["protocol-testing/quic/quic_tests"],
                    "priority": 2,
                    "depends_on": ["quic"],
                },
            ],
            "exclude_paths": ["doc", "test", "submodules"],
        }
        (quic_dir / ".ivyworkspace").write_text(json.dumps(quic_marker))

        # Create minip marker with single layer
        minip_dir = pt / "minip"
        minip_dir.mkdir(parents=True)
        (minip_dir / "ping_types.ivy").write_text("# minip types")
        minip_marker = {
            "version": 3,
            "standard_library": "ivy/include/1.7",
            "protocol_id": "minip",
            "workspace_root_offset": "../..",
            "workspace_layers": [
                {
                    "id": "minip",
                    "include_paths": ["protocol-testing/minip"],
                    "priority": 3,
                },
            ],
            "exclude_paths": ["doc", "test", "submodules"],
        }
        (minip_dir / ".ivyworkspace").write_text(json.dumps(minip_marker))

        return panther_ivy, pt

    def test_merges_layers_from_all_markers(self, tmp_path):
        """Heuristic merges layers from per-protocol markers, not coarse dirs."""
        panther_ivy, _pt = self._make_panther_workspace(tmp_path)
        config = _panther_heuristic(str(tmp_path))

        assert config is not None
        assert config.detected_by == "heuristic+marker"
        assert config.project_type == "panther"

        layer_ids = {l.id for l in config.workspace_layers}
        assert layer_ids == {"quic", "quic_tests", "minip"}

        # Verify quic layer has fine-grained paths, not coarse "protocol-testing/quic"
        quic_layer = next(l for l in config.workspace_layers if l.id == "quic")
        assert "protocol-testing/quic/quic_stack" in quic_layer.include_paths
        assert "protocol-testing/quic/quic_utils" in quic_layer.include_paths
        assert "protocol-testing/quic" not in quic_layer.include_paths

        # Verify depends_on preserved
        quic_tests = next(l for l in config.workspace_layers if l.id == "quic_tests")
        assert quic_tests.depends_on == ["quic"]

    def test_standard_library_from_first_marker(self, tmp_path):
        """Merged config uses first non-null standard_library value."""
        _panther_ivy, _pt = self._make_panther_workspace(tmp_path)
        config = _panther_heuristic(str(tmp_path))
        assert config is not None
        assert config.standard_library == "ivy/include/1.7"

    def test_exclude_paths_union(self, tmp_path):
        """Merged config unions exclude_paths from all markers."""
        _panther_ivy, _pt = self._make_panther_workspace(tmp_path)
        config = _panther_heuristic(str(tmp_path))
        assert config is not None
        assert "doc" in config.exclude_paths
        assert "test" in config.exclude_paths
        assert "submodules" in config.exclude_paths

    def test_include_paths_from_layers(self, tmp_path):
        """Merged include_paths is the flattened union of all layers' include_paths."""
        _panther_ivy, _pt = self._make_panther_workspace(tmp_path)
        config = _panther_heuristic(str(tmp_path))
        assert config is not None
        assert "protocol-testing/quic/quic_stack" in config.include_paths
        assert "protocol-testing/quic/quic_utils" in config.include_paths
        assert "protocol-testing/quic/quic_tests" in config.include_paths
        assert "protocol-testing/minip" in config.include_paths

    def test_skips_non_v3_marker(self, tmp_path):
        """Protocols with non-v3 markers are skipped entirely."""
        panther_ivy, pt = self._make_panther_workspace(tmp_path)
        # Add a v1 marker for bgp
        bgp_dir = pt / "bgp"
        bgp_dir.mkdir(parents=True)
        (bgp_dir / ".ivyworkspace").write_text('{"version": 1}')

        config = _panther_heuristic(str(tmp_path))
        assert config is not None
        layer_ids = {l.id for l in config.workspace_layers}
        assert "bgp" not in layer_ids

    def test_skips_conflicting_workspace_root(self, tmp_path):
        """Protocols whose marker resolves to a different root are skipped."""
        panther_ivy, pt = self._make_panther_workspace(tmp_path)
        # Add a marker that resolves to a different root
        bad_dir = pt / "bad"
        bad_dir.mkdir(parents=True)
        bad_marker = {
            "version": 3,
            "workspace_root_offset": "../../..",  # resolves above panther_ivy
            "workspace_layers": [
                {"id": "bad", "include_paths": ["something"]},
            ],
        }
        (bad_dir / ".ivyworkspace").write_text(json.dumps(bad_marker))

        config = _panther_heuristic(str(tmp_path))
        assert config is not None
        layer_ids = {l.id for l in config.workspace_layers}
        assert "bad" not in layer_ids

    def test_layer_id_collision_raises(self, tmp_path):
        """Duplicate layer IDs across markers are detected and the protocol is skipped."""
        panther_ivy, pt = self._make_panther_workspace(tmp_path)
        # Add a protocol with a layer ID that conflicts with quic's
        dup_dir = pt / "dup"
        dup_dir.mkdir(parents=True)
        dup_marker = {
            "version": 3,
            "workspace_root_offset": "../..",
            "workspace_layers": [
                {"id": "quic", "include_paths": ["protocol-testing/dup"]},
            ],
        }
        (dup_dir / ".ivyworkspace").write_text(json.dumps(dup_marker))

        config = _panther_heuristic(str(tmp_path))
        assert config is not None
        # dup protocol should be skipped due to layer ID collision
        layer_ids = [l.id for l in config.workspace_layers]
        assert layer_ids.count("quic") == 1

    def test_empty_v3_marker_harmless(self, tmp_path):
        """Protocol with empty v3 marker contributes no layers."""
        panther_ivy, pt = self._make_panther_workspace(tmp_path)
        empty_dir = pt / "empty"
        empty_dir.mkdir(parents=True)
        (empty_dir / ".ivyworkspace").write_text(
            json.dumps({"version": 3, "workspace_root_offset": "../.."})
        )

        config = _panther_heuristic(str(tmp_path))
        assert config is not None
        layer_ids = {l.id for l in config.workspace_layers}
        # Only quic, quic_tests, minip — nothing from empty
        assert layer_ids == {"quic", "quic_tests", "minip"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_detection.py::TestPantherHeuristicMarkerMerge -xvs`

Expected: FAIL — `_build_panther_workspace` still generates coarse layers and returns `detected_by="heuristic"`.

- [ ] **Step 3: Commit failing tests**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add tests/test_workspace_detection.py
git commit -m "test: add marker-merge tests for _build_panther_workspace

Tests verify: layer merging from per-protocol markers, standard_library
selection, exclude_paths union, non-v3 marker skip, conflicting root
skip, layer ID collision detection, and empty marker handling.
All tests expected to fail until _build_panther_workspace is rewritten."
```

---

### Task 3: Rewrite `_build_panther_workspace` to merge markers

**Files:**
- Modify: `ivy_lsp/core/workspace/detection.py:248-293`

- [ ] **Step 1: Rewrite `_build_panther_workspace`**

Replace the current implementation (lines 248-293) with marker-merge logic:

```python
def _build_panther_workspace(
    panther_ivy_root: str,
) -> Optional[WorkspaceConfig]:
    """Build a WorkspaceConfig for a PANTHER panther_ivy root directory.

    Reads per-protocol ``.ivyworkspace`` markers and merges their
    fine-grained layer definitions into a single config. Protocols whose
    markers fail to parse, resolve to a different root, or have layer ID
    collisions are skipped with a warning.
    """
    protocol_testing_dir = os.path.join(panther_ivy_root, "protocol-testing")
    discovered = _discover_protocols(protocol_testing_dir)

    if not discovered:
        logger.debug(
            "No per-protocol .ivyworkspace markers found under %s; "
            "no workspace detected",
            protocol_testing_dir,
        )
        return None

    panther_ivy_real = os.path.realpath(panther_ivy_root)
    merged_layers: list[WorkspaceLayer] = []
    merged_include_paths: list[str] = []
    merged_exclude_paths: set[str] = set()
    merged_groups: dict[str, list[str]] = {}
    standard_library: Optional[str] = None
    seen_layer_ids: set[str] = set()
    any_marker_merged = False

    for protocol in discovered:
        marker_path = os.path.join(
            protocol_testing_dir, protocol, _IVYWORKSPACE_FILENAME
        )
        data = _read_marker(marker_path)
        if data is None:
            logger.warning(
                "Skipping protocol %s: failed to read .ivyworkspace", protocol
            )
            continue

        config = _apply_marker(marker_path, data)
        if config is None:
            logger.warning(
                "Skipping protocol %s: unsupported marker version", protocol
            )
            continue

        # Verify resolved root matches panther_ivy_root
        resolved_root = os.path.realpath(config.workspace_root)
        if resolved_root != panther_ivy_real:
            logger.warning(
                "Skipping protocol %s: resolved root %s != expected %s",
                protocol,
                resolved_root,
                panther_ivy_real,
            )
            continue

        # Check for layer ID collisions
        new_ids = {l.id for l in config.workspace_layers}
        collisions = new_ids & seen_layer_ids
        if collisions:
            logger.warning(
                "Skipping protocol %s: layer ID collision with already-merged "
                "layers: %s",
                protocol,
                sorted(collisions),
            )
            continue

        # Merge this protocol's layers
        seen_layer_ids.update(new_ids)
        merged_layers.extend(config.workspace_layers)
        merged_include_paths.extend(config.include_paths)
        merged_exclude_paths.update(config.exclude_paths)
        merged_groups.update(config.workspace_groups)

        if standard_library is None and config.standard_library:
            standard_library = config.standard_library
        elif (
            config.standard_library
            and standard_library
            and config.standard_library != standard_library
        ):
            logger.warning(
                "Protocol %s declares standard_library=%s, "
                "but %s was already selected; keeping first",
                protocol,
                config.standard_library,
                standard_library,
            )

        any_marker_merged = True

    if not any_marker_merged:
        logger.debug(
            "No valid v3 markers found under %s; no workspace detected",
            protocol_testing_dir,
        )
        return None

    return WorkspaceConfig(
        workspace_root=panther_ivy_root,
        workspace_layers=merged_layers,
        include_paths=merged_include_paths,
        exclude_paths=sorted(merged_exclude_paths),
        detected_by="heuristic+marker",
        project_type="panther",
        standard_library=standard_library,
        workspace_groups=merged_groups,
    )
```

- [ ] **Step 2: Run the marker-merge tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_detection.py::TestPantherHeuristicMarkerMerge -xvs`

Expected: All PASS.

- [ ] **Step 3: Update existing tests that use bare `{"version": 3}` markers**

The rewrite validates that each marker's resolved `workspace_root` matches `panther_ivy_root`. Existing tests use bare `{"version": 3}` markers (no `workspace_root_offset`), which resolve `workspace_root = marker_dir` (the protocol subdirectory). This won't match `panther_ivy_root`, causing the protocol to be skipped and `_build_panther_workspace` to return `None`.

Fix these tests by adding `workspace_root_offset` to their markers:

**Line 149** (`TestPantherHeuristic.test_panther_structure_detected`): change:
```python
(pt / "quic" / ".ivyworkspace").write_text('{"version": 3}')
```
to:
```python
(pt / "quic" / ".ivyworkspace").write_text(
    json.dumps({"version": 3, "workspace_root_offset": "../.."})
)
```

**Line 153**: change `assert config.detected_by == "heuristic"` to:
```python
assert config.detected_by == "heuristic+marker"
```

**Line 163** (`TestPantherHeuristic.test_inside_panther_ivy`): change:
```python
(pt / "quic" / ".ivyworkspace").write_text('{"version": 3}')
```
to:
```python
(pt / "quic" / ".ivyworkspace").write_text(
    json.dumps({"version": 3, "workspace_root_offset": "../.."})
)
```

**Line 278** (`TestDetectIvyWorkspace.test_panther_heuristic_detected`): change:
```python
(pt / "quic" / ".ivyworkspace").write_text('{"version": 3}')
```
to:
```python
(pt / "quic" / ".ivyworkspace").write_text(
    json.dumps({"version": 3, "workspace_root_offset": "../.."})
)
```

**Line 280**: change `assert config.detected_by == "heuristic"` to:
```python
assert config.detected_by == "heuristic+marker"
```

**Line 684** (`TestPantherHeuristicDynamicDiscovery.test_heuristic_uses_discovered_protocols`): change both markers:
```python
(pt / "quic" / ".ivyworkspace").write_text(
    json.dumps({"version": 3, "workspace_root_offset": "../.."})
)
(pt / "bgp" / ".ivyworkspace").write_text(
    json.dumps({"version": 3, "workspace_root_offset": "../.."})
)
```

**Line 692-693**: The assertion `any("protocol-testing/quic" in p for p in config.include_paths)` will still pass because empty markers (no `workspace_layers`) contribute no include_paths. But the marker still counts as `any_marker_merged = True`. The test should verify that empty markers produce no include_paths. Update to:
```python
# Empty markers (no workspace_layers) contribute no include_paths
assert config.include_paths == []
```

**Line 337** (`TestWorktreeDetection.test_worktree_with_panther_heuristic`): change:
```python
(pt / "quic" / ".ivyworkspace").write_text('{"version": 3}')
```
to:
```python
(pt / "quic" / ".ivyworkspace").write_text(
    json.dumps({"version": 3, "workspace_root_offset": "../.."})
)
```

**Line 366** (`TestHintWithHeuristic.test_hint_with_panther_structure_and_markers`): change:
```python
(pt / "quic" / ".ivyworkspace").write_text('{"version": 3}')
```
to:
```python
(pt / "quic" / ".ivyworkspace").write_text(
    json.dumps({"version": 3, "workspace_root_offset": "../.."})
)
```

- [ ] **Step 4: Run the full test_workspace_detection suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_detection.py -xvs`

Expected: All PASS.

- [ ] **Step 5: Also verify test_index_cli.py is unaffected**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_index_cli.py -xvs`

Expected: All PASS. (These tests mock `WorkspaceContext.detect`, not `_panther_heuristic`.)

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/workspace/detection.py tests/test_workspace_detection.py
git commit -m "fix: merge per-protocol markers in _build_panther_workspace

Read each protocol's .ivyworkspace marker and concatenate their
fine-grained layer definitions instead of generating coarse heuristic
layers. Skip protocols with parse failures, conflicting roots, or
layer ID collisions. Eliminates 189 cross-protocol basename collisions."
```

---

### Task 4: Add intra/cross-layer collision breakdown in `staging_health()`

**Files:**
- Modify: `ivy_lsp/core/indexer/include_resolver.py:1215-1237`
- Modify: `tests/test_staging_health_integration.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_staging_health_integration.py`:

```python
def test_staging_health_collision_breakdown():
    """staging_health returns intra/cross-layer collision counts."""
    from ivy_lsp.core.indexer.include_resolver import IncludeResolver

    resolver = IncludeResolver("/tmp/fake")
    # Simulate staged state with collisions
    resolver._staged_files = {"a.ivy": "/tmp/a.ivy", "b.ivy": "/tmp/b.ivy"}
    resolver._collision_map = {
        "a.ivy": ["/tmp/layer1/a.ivy", "/tmp/layer2/a.ivy"],  # cross-layer
        "b.ivy": ["/tmp/layer1/b.ivy", "/tmp/layer1/b2.ivy"],  # intra-layer
    }
    resolver._file_to_layer = {
        "/tmp/layer1/a.ivy": "quic",
        "/tmp/layer2/a.ivy": "apt",
        "/tmp/layer1/b.ivy": "quic",
        "/tmp/layer1/b2.ivy": "quic",
    }
    resolver._partition_staging = {"quic": "/tmp/s/layer_quic", "apt": "/tmp/s/layer_apt"}
    resolver._file_to_partition = dict(resolver._file_to_layer)
    resolver._staging_dir = "/tmp/fake_staging"

    health = resolver.staging_health()
    assert health["collisions"] == 2  # total (backward compat)
    assert health["intra_layer_collisions"] == 1  # b.ivy only
    assert health["cross_layer_collisions"] == 1  # a.ivy only
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_staging_health_integration.py::test_staging_health_collision_breakdown -xvs`

Expected: FAIL — `KeyError: 'intra_layer_collisions'`

- [ ] **Step 3: Implement collision breakdown in `staging_health()`**

In `ivy_lsp/core/indexer/include_resolver.py`, replace the `staging_health` method (lines 1215-1237):

```python
def staging_health(self) -> Dict[str, Any]:
    """Return a summary of staging directory health.

    Returns:
        Dict with keys: total_staged, collisions, intra_layer_collisions,
        cross_layer_collisions, collision_basenames, symlink_failures,
        layers_active, layer_count, files_mapped_to_layers.
    """
    # Classify collisions as intra-layer vs cross-layer
    intra = 0
    cross = 0
    for basename, paths in self._collision_map.items():
        if self._file_to_layer:
            layers_involved = {
                self._file_to_layer.get(os.path.realpath(p), "unknown")
                for p in paths
            }
            if len(layers_involved) <= 1:
                intra += 1
            else:
                cross += 1
        else:
            intra += 1  # No layers → all collisions are "intra"

    result: Dict[str, Any] = {
        "total_staged": len(self._staged_files),
        "collisions": len(self._collision_map),
        "intra_layer_collisions": intra,
        "cross_layer_collisions": cross,
        "collision_basenames": sorted(self._collision_map.keys())[:20],
        "layers_active": bool(self._partition_staging),
        "layer_count": len(self._partition_staging),
        "files_mapped_to_layers": len(self._file_to_partition),
    }
    # Check for broken symlinks in staging dir
    symlink_failures = 0
    if self._staging_dir and os.path.isdir(self._staging_dir):
        for entry in os.scandir(self._staging_dir):
            if entry.is_symlink() and not os.path.exists(entry.path):
                symlink_failures += 1
    result["symlink_failures"] = symlink_failures
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_staging_health_integration.py -xvs`

Expected: All PASS.

- [ ] **Step 5: Run the full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x --timeout=30`

Expected: All tests PASS (or pre-existing failures only, no new failures).

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/indexer/include_resolver.py tests/test_staging_health_integration.py
git commit -m "feat: add intra/cross-layer collision breakdown in staging_health

Classify each collision by whether all variant paths belong to the same
layer (intra) or span multiple layers (cross). Cross-layer collisions
are expected and handled by layered staging; intra-layer collisions
indicate a genuine problem."
```

---

### Task 5: Integration verification

**Files:** None (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x --timeout=30 -q`

Expected: All tests PASS (or pre-existing failures only).

- [ ] **Step 2: Verify against the real PANTHER workspace**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "
from ivy_lsp.core.workspace.detection import _panther_heuristic
config = _panther_heuristic('$(pwd)/../..')
print('detected_by:', config.detected_by)
print('layers:', [l.id for l in config.workspace_layers])
print('include_paths count:', len(config.include_paths))
print('standard_library:', config.standard_library)
# Verify no coarse protocol-testing/{protocol} paths
for ip in config.include_paths:
    parts = ip.split('/')
    if len(parts) == 2 and parts[0] == 'protocol-testing':
        print(f'WARNING: coarse include path found: {ip}')
"`

Expected: `detected_by: heuristic+marker`, 7 layer IDs (`quic`, `quic_tests`, `apt`, `apt_tests`, `bgp`, `coap`, `minip`), no coarse include paths, `standard_library: ivy/include/1.7`.

- [ ] **Step 3: Verify staging collision count**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "
from ivy_lsp.core.workspace.detection import _panther_heuristic
from ivy_lsp.core.indexer.include_resolver import IncludeResolver
config = _panther_heuristic('$(pwd)/../..')
resolver = IncludeResolver(
    config.workspace_root,
    ivy_include_path=config.workspace_root + '/' + config.standard_library if config.standard_library else None,
    exclude_paths=config.exclude_paths,
    include_paths=config.include_paths,
    workspace_layers=config.workspace_layers,
)
resolver.create_staging_directory()
resolver.build_layered_staging()
health = resolver.staging_health()
print('total_staged:', health['total_staged'])
print('collisions (total):', health['collisions'])
print('intra_layer_collisions:', health['intra_layer_collisions'])
print('cross_layer_collisions:', health['cross_layer_collisions'])
resolver.cleanup_staging()
"`

Expected: `intra_layer_collisions: 0` (or very low). `cross_layer_collisions` may still be non-zero (expected when `apt` and `quic` share basenames with different content), but these are handled by layered staging and don't cause wrong resolution.
