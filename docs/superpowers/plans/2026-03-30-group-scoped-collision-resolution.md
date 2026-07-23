# Strict Layer Resolution + APT Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate cross-protocol include leakage by removing the proximity fallback, merging APT sub-layers, and fixing incomplete protocol file distributions.

**Architecture:** Each layer resolves includes via own-layer + depends_on + stdlib only. No cross-layer proximity guessing. Merge 5 APT layers into 2 to eliminate circular dependencies. Fix bgp/coap so each protocol is self-contained.

**Tech Stack:** Python 3.10+, ivy-lsp indexer, JSON workspace configs, Ivy language files

**Spec:** `docs/superpowers/specs/2026-03-30-group-scoped-collision-resolution-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `panther_ivy/.ivyworkspace` | Merge APT layers, update groups |
| Modify | `panther_ivy/protocol-testing/apt/.ivyworkspace` | Merge APT layers |
| Modify | `panther_ivy/protocol-testing/bgp/bgp_utils/file.ivy` | Fix empty stub |
| Create | `panther_ivy/protocol-testing/coap/coap_utils/random_value.ivy` | CoAP-adapted random value |
| Modify | `ivy-lsp/ivy_lsp/core/indexer/include_resolver.py` | Remove proximity fallback, remove workspace root fallback when layers active |
| Create | `ivy-lsp/tests/test_strict_layer_resolution.py` | Tests for strict resolution |
| Modify | `ivy-lsp/tests/test_include_resolver_fallback.py` | Update fallback expectations |

All `ivy-lsp/` paths relative to: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
All `panther_ivy/` paths relative to: `panther/plugins/services/testers/panther_ivy/`

---

### Task 1: Fix bgp `file.ivy` empty stub

**Files:**
- Modify: `panther_ivy/protocol-testing/bgp/bgp_utils/file.ivy`
- Reference: `panther_ivy/protocol-testing/quic/quic_utils/file.ivy` (153 lines)

- [ ] **Step 1: Verify the stub is empty**

Run: `wc -l panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_utils/file.ivy`
Expected: `2` (just `#lang ivy1.7` + blank line)

- [ ] **Step 2: Copy the full implementation from quic**

```bash
cp panther/plugins/services/testers/panther_ivy/protocol-testing/quic/quic_utils/file.ivy \
   panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_utils/file.ivy
```

- [ ] **Step 3: Verify the copy**

Run: `wc -l panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_utils/file.ivy`
Expected: `153`

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_utils/file.ivy
git commit -m "fix(bgp): replace empty file.ivy stub with full implementation

The bgp file.ivy was a 2-line empty stub that depended on quic's version
via cross-protocol fallback. Copy quic's binary_input_file module so bgp
is self-contained."
```

---

### Task 2: Create coap `random_value.ivy`

**Files:**
- Create: `panther_ivy/protocol-testing/coap/coap_utils/random_value.ivy`
- Reference: `panther_ivy/protocol-testing/quic/quic_utils/random_value.ivy` (128 lines)

- [ ] **Step 1: Check what types coap_types.ivy exports**

Run: `grep -E '^type |^alias ' panther/plugins/services/testers/panther_ivy/protocol-testing/coap/coap_utils/coap_types.ivy`

The quic version includes `quic_types` and uses `stream_pos`, `stream_id`, `stream_data`, `milliseconds`. The coap version must use coap equivalents.

- [ ] **Step 2: Check what coap behavior files actually call from random_value**

Run: `grep -B2 -A5 'random_value' panther/plugins/services/testers/panther_ivy/protocol-testing/coap/coap_enntities_behavior/*.ivy`

Only implement the functions coap actually uses.

- [ ] **Step 3: Create the coap-adapted random_value.ivy**

Based on Steps 1-2 findings, create `protocol-testing/coap/coap_utils/random_value.ivy` with:
- `include coap_types` (not quic_types)
- Only the functions coap behavior files actually call
- Adapted to use coap type names

If coap uses the same type names as quic (e.g., `stream_pos`), copy from quic and change the include. If types differ, adapt function signatures.

- [ ] **Step 4: Verify the file exists**

Run: `ls -la panther/plugins/services/testers/panther_ivy/protocol-testing/coap/coap_utils/random_value.ivy`

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/coap/coap_utils/random_value.ivy
git commit -m "fix(coap): add random_value.ivy for protocol self-containment

CoAP behavior files include random_value but no such file existed in the
coap tree. Create a coap-adapted version so coap is self-contained."
```

---

### Task 3: Merge APT sub-layers in workspace configs

**Files:**
- Modify: `panther_ivy/.ivyworkspace`
- Modify: `panther_ivy/protocol-testing/apt/.ivyworkspace`

- [ ] **Step 1: Update root `.ivyworkspace`**

In `panther/plugins/services/testers/panther_ivy/.ivyworkspace`:

Replace `workspace_groups`:
```json
"workspace_groups": {
    "quic": ["quic", "quic_tests"],
    "apt": ["apt", "apt_tests"],
    "minip": ["minip"],
    "bgp": ["bgp"],
    "coap": ["coap"],
    "scaffolds": ["scaffolds"]
}
```

Replace the 5 APT layer entries (apt_core, apt_quic_fork, apt_minip_fork, apt_tls_fork, apt_tests) with 2:
```json
{"id": "apt", "include_paths": [
    "protocol-testing/apt/apt_entities",
    "protocol-testing/apt/apt_entities_behavior",
    "protocol-testing/apt/apt_lifecycle",
    "protocol-testing/apt/apt_network",
    "protocol-testing/apt/apt_shims",
    "protocol-testing/apt/apt_stack",
    "protocol-testing/apt/apt_utils",
    "protocol-testing/apt/apt_protocols/quic",
    "protocol-testing/apt/apt_protocols/minip",
    "protocol-testing/apt/apt_protocols/tls"
], "priority": 4},
{"id": "apt_tests", "include_paths": [
    "protocol-testing/apt/apt_tests"
], "priority": 5, "depends_on": ["apt"]}
```

Renumber bgp (6), coap (7), scaffolds (8).

- [ ] **Step 2: Update APT-specific `.ivyworkspace`**

Replace `panther/plugins/services/testers/panther_ivy/protocol-testing/apt/.ivyworkspace` with:
```json
{
  "version": 3,
  "standard_library": "ivy/include/1.7",
  "scope_detection": "auto",
  "protocol_id": "apt",
  "workspace_root_offset": "../..",
  "workspace_layers": [
    {
      "id": "apt",
      "include_paths": [
        "protocol-testing/apt/apt_entities",
        "protocol-testing/apt/apt_entities_behavior",
        "protocol-testing/apt/apt_lifecycle",
        "protocol-testing/apt/apt_network",
        "protocol-testing/apt/apt_shims",
        "protocol-testing/apt/apt_stack",
        "protocol-testing/apt/apt_utils",
        "protocol-testing/apt/apt_protocols/quic",
        "protocol-testing/apt/apt_protocols/minip",
        "protocol-testing/apt/apt_protocols/tls"
      ],
      "priority": 1
    },
    {
      "id": "apt_tests",
      "include_paths": ["protocol-testing/apt/apt_tests"],
      "priority": 2,
      "depends_on": ["apt"]
    }
  ],
  "exclude_paths": [
    "doc", "examples", "test", "notebooks", "patches", "submodules", "ivy",
    "protocol-testing/apt/apt_protocols/dns",
    "protocol-testing/apt/apt_protocols/http",
    "protocol-testing/apt/apt_protocols/smtp"
  ]
}
```

- [ ] **Step 3: Validate JSON**

Run: `python3 -c "import json; json.load(open('panther/plugins/services/testers/panther_ivy/.ivyworkspace')); print('OK')"`
Run: `python3 -c "import json; json.load(open('panther/plugins/services/testers/panther_ivy/protocol-testing/apt/.ivyworkspace')); print('OK')"`
Expected: Both `OK`

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/.ivyworkspace
git add panther/plugins/services/testers/panther_ivy/protocol-testing/apt/.ivyworkspace
git commit -m "refactor(workspace): merge APT sub-layers into single apt layer

Merge apt_core, apt_quic_fork, apt_minip_fork, apt_tls_fork into one
'apt' layer. Zero basename collisions between them. Eliminates the
circular dependency and all staging miss WARNINGs within APT."
```

---

### Task 4: Remove cross-layer proximity fallback

**Files:**
- Modify: `ivy-lsp/ivy_lsp/core/indexer/include_resolver.py` (lines ~376-414)
- Create: `ivy-lsp/tests/test_strict_layer_resolution.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_strict_layer_resolution.py`:

```python
"""Tests for strict layer resolution — no cross-layer proximity fallback."""
import os
import pytest
from ivy_lsp.core.indexer.include_resolver import IncludeResolver
from ivy_lsp.core.workspace.detection import WorkspaceLayer


class TestNoProximityFallback:
    """Cross-layer proximity fallback is disabled."""

    @pytest.fixture
    def two_layer_workspace(self, tmp_path):
        """Two independent layers with a colliding basename."""
        ws = tmp_path / "ws"
        (ws / "proto_a").mkdir(parents=True)
        (ws / "proto_a" / "types.ivy").write_text("#lang ivy1.7\n# proto_a types")
        (ws / "proto_a" / "main.ivy").write_text("#lang ivy1.7\ninclude helper")

        (ws / "proto_b").mkdir(parents=True)
        (ws / "proto_b" / "helper.ivy").write_text("#lang ivy1.7\n# proto_b helper")

        layers = [
            WorkspaceLayer(id="a", include_paths=["proto_a"], priority=1),
            WorkspaceLayer(id="b", include_paths=["proto_b"], priority=2),
        ]
        resolver = IncludeResolver(
            workspace_root=str(ws),
            include_paths=["proto_a", "proto_b"],
            workspace_layers=layers,
        )
        resolver.create_staging_directory()
        resolver.build_layered_staging()
        return resolver, ws

    def test_cross_layer_blocked(self, two_layer_workspace):
        """Layer a cannot resolve 'helper' from layer b without depends_on."""
        resolver, ws = two_layer_workspace
        from_file = str(ws / "proto_a" / "main.ivy")
        result = resolver.resolve("helper", from_file)
        # helper.ivy only exists in layer b — layer a has no depends_on
        assert result is None

    def test_depends_on_still_works(self, tmp_path):
        """Explicit depends_on still resolves cross-layer."""
        ws = tmp_path / "ws"
        (ws / "base").mkdir(parents=True)
        (ws / "base" / "shared.ivy").write_text("#lang ivy1.7\n# shared")
        (ws / "ext").mkdir(parents=True)
        (ws / "ext" / "main.ivy").write_text("#lang ivy1.7\ninclude shared")

        layers = [
            WorkspaceLayer(id="base_layer", include_paths=["base"], priority=1),
            WorkspaceLayer(id="ext_layer", include_paths=["ext"], priority=2,
                           depends_on=["base_layer"]),
        ]
        resolver = IncludeResolver(
            workspace_root=str(ws),
            include_paths=["base", "ext"],
            workspace_layers=layers,
        )
        resolver.create_staging_directory()
        resolver.build_layered_staging()

        from_file = str(ws / "ext" / "main.ivy")
        result = resolver.resolve("shared", from_file)
        assert result is not None
        assert "base" in result

    def test_same_layer_resolves(self, tmp_path):
        """Files within the same layer resolve normally."""
        ws = tmp_path / "ws"
        (ws / "proto").mkdir(parents=True)
        (ws / "proto" / "types.ivy").write_text("#lang ivy1.7\n# types")
        (ws / "proto" / "main.ivy").write_text("#lang ivy1.7\ninclude types")

        layers = [
            WorkspaceLayer(id="proto", include_paths=["proto"], priority=1),
        ]
        resolver = IncludeResolver(
            workspace_root=str(ws),
            include_paths=["proto"],
            workspace_layers=layers,
        )
        resolver.create_staging_directory()
        resolver.build_layered_staging()

        from_file = str(ws / "proto" / "main.ivy")
        result = resolver.resolve("types", from_file)
        assert result is not None
        assert "proto" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_strict_layer_resolution.py::TestNoProximityFallback::test_cross_layer_blocked -v`
Expected: FAIL — proximity fallback finds helper.ivy in layer b

- [ ] **Step 3: Remove the proximity fallback loop**

In `ivy_lsp/core/indexer/include_resolver.py`, find the cross-layer proximity fallback section in `_resolve_via_layers()` (lines ~376-414). This is the block that starts with `cross_candidates = []` and iterates over `_partition_staging`.

Replace the entire block (from `cross_candidates = []` through the `return os.path.realpath(best_cand)`) with:

```python
        # No cross-layer proximity fallback. If a file isn't in own-layer
        # or depends_on, it's unresolved. This prevents cross-protocol
        # leakage (e.g., APT file resolving to standard QUIC variant).
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_strict_layer_resolution.py -v`
Expected: All 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/indexer/include_resolver.py tests/test_strict_layer_resolution.py
git commit -m "feat(resolver): remove cross-layer proximity fallback

Each layer resolves via own-layer + depends_on + stdlib only. No more
proximity-scored guessing across unrelated layers. If a file isn't
reachable through declared dependencies, it's unresolved.

This eliminates cross-protocol leakage where APT files could accidentally
resolve to standard QUIC variants."
```

---

### Task 5: Remove workspace root fallback when layers are active

**Files:**
- Modify: `ivy-lsp/ivy_lsp/core/indexer/include_resolver.py` (lines ~482-486)
- Modify: `ivy-lsp/tests/test_strict_layer_resolution.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_strict_layer_resolution.py`:

```python
class TestNoWorkspaceRootFallback:
    """Workspace root fallback is disabled when layers are active."""

    def test_workspace_root_blocked_with_layers(self, tmp_path):
        """Files at workspace root cannot be reached when layers are active."""
        ws = tmp_path / "ws"
        # File at workspace root that would match
        (ws / "stray.ivy").write_text("#lang ivy1.7\n# stray file at root")
        (ws / "proto").mkdir(parents=True)
        (ws / "proto" / "main.ivy").write_text("#lang ivy1.7\ninclude stray")

        layers = [
            WorkspaceLayer(id="proto", include_paths=["proto"], priority=1),
        ]
        resolver = IncludeResolver(
            workspace_root=str(ws),
            include_paths=["proto"],
            workspace_layers=layers,
        )
        resolver.create_staging_directory()
        resolver.build_layered_staging()

        from_file = str(ws / "proto" / "main.ivy")
        result = resolver.resolve("stray", from_file)
        # stray.ivy is at workspace root, not in any layer — should not resolve
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_strict_layer_resolution.py::TestNoWorkspaceRootFallback -v`
Expected: FAIL — workspace root fallback finds stray.ivy

- [ ] **Step 3: Disable workspace root fallback when layers are active**

In `ivy_lsp/core/indexer/include_resolver.py`, find the workspace root fallback in `_resolve_via_flat_staging()` (lines ~482-486):

```python
        # Workspace root fallback
        candidate = os.path.join(self._workspace_root, fname)
        if os.path.isfile(candidate):
            return os.path.realpath(candidate)
```

Replace with:

```python
        # Workspace root fallback — skip when layers are active (strict mode).
        # With layers, resolution is: own-layer → depends_on → stdlib.
        if not _file_to_layer:
            candidate = os.path.join(self._workspace_root, fname)
            if os.path.isfile(candidate):
                return os.path.realpath(candidate)
```

- [ ] **Step 4: Run all strict resolution tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_strict_layer_resolution.py -v`
Expected: All PASSED

- [ ] **Step 5: Run existing fallback tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_include_resolver_fallback.py -v`
Expected: PASS — these tests don't use layers, so workspace root fallback still works for non-layered workspaces

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/indexer/include_resolver.py tests/test_strict_layer_resolution.py
git commit -m "fix(resolver): disable workspace root fallback when layers are active

When workspace layers are configured, resolution is strictly:
own-layer → depends_on → stdlib. The workspace root fallback is only
used for non-layered workspaces (backward compatibility)."
```

---

### Task 6: Integration verification

**Files:** None (read-only)

- [ ] **Step 1: Run full ivy-lsp test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x --timeout=120 -v`
Expected: All PASS

- [ ] **Step 2: Run index with debug logging**

Run: `cd panther/plugins/services/testers/panther_ivy && IVY_LSP_LOG_LEVEL=DEBUG python -m ivy_lsp index --force --all 2>&1 | tee /tmp/post-fix-index.log`

- [ ] **Step 3: Verify no APT staging misses**

Run: `grep "Layer staging miss" /tmp/post-fix-index.log | grep -c "apt"`
Expected: `0`

- [ ] **Step 4: Verify no intra-layer collisions**

Run: `grep -c "Intra-layer collision" /tmp/post-fix-index.log`
Expected: `0`

- [ ] **Step 5: Check for new unresolved includes**

Run: `grep -c "ERROR" /tmp/post-fix-index.log`

If new unresolved includes appear, they indicate missing `depends_on` declarations — fix them by adding explicit dependencies in `.ivyworkspace`. These are real dependency bugs that the proximity fallback was hiding.

- [ ] **Step 6: Compare collision counts**

Run: `grep -c "Cross-layer collision" /tmp/post-fix-index.log`
Expected: Same or fewer than 1,701 (the merge reduces APT-internal collisions).
