# Active Workspace System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two-tier active workspace system that prevents cross-protocol collisions and constrains Claude edits to the active protocol.

**Architecture:** Layer-based coarse gate (immediate) + TestScope-based fine lens (after indexing). Per-protocol `.ivyworkspace` markers for auto-scoping. State persisted in `.ivy-workspace-state.json`. Edit isolation via PreToolUse hooks. MCP tool `ivy_workspace` for runtime management.

**Tech Stack:** Python 3.10+, ivy-lsp (LSP/MCP server), panther-ivy-plugin (Claude Code plugin, bash/python hooks, markdown skills)

**Spec:** `docs/superpowers/specs/2026-03-24-active-workspace-system-design.md`

**Base paths:**
- ivy-lsp: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
- panther-ivy-plugin: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

**Review-validated patterns:**
- MCP tools: `@mcp.tool()` + `@safe_tool` + `async def` (see `tools/verification.py`)
- Thread safety: `threading.Lock()` with `with` context manager (see `session_overlay.py`)
- Hook block output: `{"decision": "block", "reason": "..."}` — NO `hookSpecificOutput` wrapper on blocks
- Hook warn output: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "..."}}` — separate from block format
- `build_layered_staging()`: safe to add `layers=None` param — direct iteration, no indirection

**Implementation errata (from plan review):**
- `_find_source_files_by_layer()` also iterates `self._workspace_layers` — must accept `layers` param too
- `set_active_workspace()` must clear `_partition_staging`, `_file_to_partition`, `_file_to_layer` dicts before rebuild
- `set_active_workspace()` must guard: if `_file_to_layer` is empty (pre-indexing), log warning and return (Invariant 3)
- `resolve()` lock must wrap full body, not just "dispatch section" — `_staging_dir` can be swapped mid-flight
- `from_test_file()` needs `workspace_layers: List[WorkspaceLayer]` param for `depends_on` resolution (RF-12)
- Task 7 must implement RF-5 tiebreak logic (explicit beats marker)
- `workspace_groups` must be added to `ToolContext` (not just `active_workspace`)
- Task 12 migration script should verify output matches Task 3 hand-written markers
- panther_ivy root: `panther/plugins/services/testers/panther_ivy/`

---

## Task 1: Investigate CoAP Dependency (Phase 1 prerequisite)

**Files:**
- Read: `panther_ivy/protocol-testing/coap/` (all .ivy files)
- Read: `panther_ivy/.ivyworkspace`

- [ ] **Step 1: List all .ivy files in CoAP**
Run: `find panther_ivy/protocol-testing/coap/ -name "*.ivy" -type f`

- [ ] **Step 2: Check if any CoAP file includes QUIC-specific files**
Run: `grep -r "^include" panther_ivy/protocol-testing/coap/ --include="*.ivy" | grep -v "^#"`
Expected: Check for includes like `quic_frame`, `quic_types`, etc.

- [ ] **Step 3: Decide CoAP dependency status**
If CoAP includes QUIC files → create `coap_quic` group in workspace_groups.
If CoAP does NOT include QUIC files → remove `depends_on: ["quic"]`.
Document finding in a comment in `.ivyworkspace`.

- [ ] **Step 4: Commit investigation result**
```bash
git add panther_ivy/.ivyworkspace
git commit -m "docs: document CoAP dependency investigation result"
```

---

## Task 2: WorkspaceConfig Schema Extension (Phase 1)

**Files:**
- Modify: `ivy-lsp/ivy_lsp/workspace_detection.py:23-52` (WorkspaceConfig + WorkspaceLayer dataclasses)
- Modify: `ivy-lsp/ivy_lsp/workspace_detection.py:69-112` (_apply_marker function)
- Test: `ivy-lsp/tests/test_workspace_detection.py` (new tests)

- [ ] **Step 1: Write failing tests for new WorkspaceConfig fields**

```python
# tests/test_workspace_detection.py — append these tests

def test_workspace_config_has_workspace_groups():
    config = WorkspaceConfig(workspace_root="/tmp")
    assert config.workspace_groups == {}
    assert config.protocol_id is None
    assert config.workspace_root_offset is None

def test_apply_marker_parses_workspace_groups(tmp_path):
    marker = tmp_path / ".ivyworkspace"
    marker.write_text(json.dumps({
        "version": 3,
        "workspace_groups": {"quic": ["quic", "quic_tests"]},
        "workspace_layers": [
            {"id": "quic", "include_paths": ["quic_stack"], "priority": 1}
        ]
    }))
    config = _apply_marker(str(marker), json.loads(marker.read_text()))
    assert config.workspace_groups == {"quic": ["quic", "quic_tests"]}

def test_apply_marker_parses_protocol_id(tmp_path):
    marker = tmp_path / ".ivyworkspace"
    marker.write_text(json.dumps({
        "version": 3,
        "protocol_id": "quic",
        "workspace_root_offset": "../..",
        "workspace_layers": [
            {"id": "quic", "include_paths": ["protocol-testing/quic/quic_stack"], "priority": 1}
        ]
    }))
    config = _apply_marker(str(marker), json.loads(marker.read_text()))
    assert config.protocol_id == "quic"
    assert config.workspace_root_offset == "../.."

def test_workspace_root_offset_resolves_correctly(tmp_path):
    """When workspace_root_offset is set, workspace_root points to the resolved path."""
    proto_dir = tmp_path / "protocol-testing" / "quic"
    proto_dir.mkdir(parents=True)
    marker = proto_dir / ".ivyworkspace"
    marker.write_text(json.dumps({
        "version": 3,
        "protocol_id": "quic",
        "workspace_root_offset": "../..",
        "workspace_layers": [
            {"id": "quic", "include_paths": ["protocol-testing/quic/quic_stack"], "priority": 1}
        ]
    }))
    config = _apply_marker(str(marker), json.loads(marker.read_text()))
    assert os.path.normpath(config.workspace_root) == os.path.normpath(str(tmp_path))
```

- [ ] **Step 2: Run tests to verify they fail**
Run: `cd ivy-lsp && python -m pytest tests/test_workspace_detection.py -v -k "workspace_groups or protocol_id or workspace_root_offset" --no-header`
Expected: FAIL — `WorkspaceConfig` has no `workspace_groups` field

- [ ] **Step 3: Add new fields to WorkspaceConfig**

In `workspace_detection.py`, add after line 52:
```python
    workspace_groups: dict[str, list[str]] = field(default_factory=dict)
    protocol_id: Optional[str] = None
    workspace_root_offset: Optional[str] = None
```

- [ ] **Step 4: Update `_apply_marker()` to parse new fields**

Replace `_apply_marker` return statement (lines 103-112):
```python
    # Parse workspace_root_offset: resolve workspace_root relative to marker dir
    workspace_root = marker_dir
    offset = data.get("workspace_root_offset")
    if offset:
        workspace_root = os.path.normpath(os.path.join(marker_dir, offset))

    # Parse workspace_groups
    workspace_groups = data.get("workspace_groups", {})

    # Parse protocol_id
    protocol_id = data.get("protocol_id")

    return WorkspaceConfig(
        workspace_root=workspace_root,
        include_paths=flat_include_paths or data.get("include_paths", []),
        exclude_paths=data.get("exclude_paths", []),
        detected_by="marker",
        project_type=data.get("project_type"),
        scope_detection=data.get("scope_detection", "auto"),
        standard_library=data.get("standard_library"),
        workspace_layers=layers,
        workspace_groups=workspace_groups,
        protocol_id=protocol_id,
        workspace_root_offset=offset,
    )
```

- [ ] **Step 5: Run tests to verify they pass**
Run: `cd ivy-lsp && python -m pytest tests/test_workspace_detection.py -v -k "workspace_groups or protocol_id or workspace_root_offset" --no-header`
Expected: PASS

- [ ] **Step 6: Run full test suite to check backward compatibility**
Run: `cd ivy-lsp && python -m pytest tests/ -x --no-header -q`
Expected: All existing tests still pass

- [ ] **Step 7: Commit**
```bash
git add ivy_lsp/workspace_detection.py tests/test_workspace_detection.py
git commit -m "feat: extend WorkspaceConfig with workspace_groups, protocol_id, workspace_root_offset"
```

---

## Task 3: Root `.ivyworkspace` Cleanup + Per-Protocol Markers (Phase 1)

**Files:**
- Modify: `panther_ivy/.ivyworkspace`
- Create: `panther_ivy/protocol-testing/quic/.ivyworkspace`
- Create: `panther_ivy/protocol-testing/apt/.ivyworkspace`
- Create: `panther_ivy/protocol-testing/minip/.ivyworkspace`
- Create: `panther_ivy/protocol-testing/bgp/.ivyworkspace`
- Create: `panther_ivy/protocol-testing/coap/.ivyworkspace`
- Modify: `panther_ivy/.gitignore`

- [ ] **Step 1: Update root `.ivyworkspace` — add workspace_groups, remove false depends_on**

Edit `panther_ivy/.ivyworkspace`:
- Add `"workspace_groups"` field after `"scope_detection"` (see spec §2 for full JSON)
- Remove `"depends_on": ["quic", "minip"]` from `apt_core` layer (line 31)
- Handle CoAP based on Task 1 investigation result
- Add `"scaffolds"` to workspace_groups

- [ ] **Step 2: Create per-protocol `.ivyworkspace` markers**

Create `protocol-testing/quic/.ivyworkspace` (see spec §1 for full JSON content).
Create `protocol-testing/apt/.ivyworkspace` (see spec §1 for full JSON content — autonomous, intra-APT deps only).
Create minimal markers for `minip/`, `bgp/`, `coap/` with their respective layers.

- [ ] **Step 3: Add `.ivy-workspace-state.json` to `.gitignore`**

Append to `panther_ivy/.gitignore`:
```
.ivy-workspace-state.json
```

- [ ] **Step 4: Verify marker walk-up works**
Run: `cd ivy-lsp && python -c "from ivy_lsp.workspace_detection import detect_ivy_workspace; c = detect_ivy_workspace('$(pwd)/../protocol-testing/quic/quic_stack/'); print(c.protocol_id, c.workspace_root)"`
Expected: `quic /path/to/panther_ivy`

- [ ] **Step 5: Commit**
```bash
git add panther_ivy/.ivyworkspace panther_ivy/.gitignore panther_ivy/protocol-testing/*/.ivyworkspace
git commit -m "feat: add workspace_groups, per-protocol markers, remove false depends_on"
```

---

## Task 4: ActiveWorkspace State Class (Phase 2)

**Files:**
- Create: `ivy-lsp/ivy_lsp/active_workspace.py`
- Test: `ivy-lsp/tests/test_active_workspace.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_active_workspace.py
import json
import os
import pytest
from ivy_lsp.active_workspace import ActiveWorkspace

def test_cleared_workspace_allows_everything():
    ws = ActiveWorkspace.cleared()
    assert not ws.is_set()
    allowed, reason = ws.is_file_allowed("/any/file.ivy", {})
    assert allowed

def test_set_workspace_blocks_out_of_scope():
    ws = ActiveWorkspace(
        active_group="quic",
        active_layers={"quic", "quic_tests"},
        active_tests=[],
        granularity="protocol",
        set_by="explicit",
    )
    file_to_layer = {"/path/quic_types.ivy": "quic", "/path/apt_time.ivy": "apt_core"}
    allowed, _ = ws.is_file_allowed("/path/quic_types.ivy", file_to_layer)
    assert allowed
    allowed, reason = ws.is_file_allowed("/path/apt_time.ivy", file_to_layer)
    assert not allowed
    assert "apt_core" in reason

def test_stdlib_always_allowed():
    ws = ActiveWorkspace(
        active_group="quic",
        active_layers={"quic"},
        active_tests=[],
        granularity="protocol",
        set_by="explicit",
    )
    allowed, _ = ws.is_file_allowed("/ivy/include/1.7/order.ivy", {})
    assert allowed

def test_save_and_load(tmp_path):
    ws = ActiveWorkspace(
        active_group="quic",
        active_layers={"quic", "quic_tests"},
        active_tests=[],
        granularity="protocol",
        set_by="explicit",
    )
    state_file = str(tmp_path / ".ivy-workspace-state.json")
    ws.save(state_file)
    loaded = ActiveWorkspace.load(state_file)
    assert loaded.active_group == "quic"
    assert loaded.active_layers == {"quic", "quic_tests"}

def test_load_missing_file_returns_cleared(tmp_path):
    loaded = ActiveWorkspace.load(str(tmp_path / "nonexistent.json"))
    assert not loaded.is_set()

def test_from_test_file():
    file_to_layer = {"/path/quic_client_test.ivy": "quic_tests"}
    workspace_groups = {"quic": ["quic", "quic_tests"], "apt": ["apt_core"]}
    ws = ActiveWorkspace.from_test_file(
        "/path/quic_client_test.ivy", file_to_layer, workspace_groups
    )
    assert ws.active_group == "quic"
    assert ws.active_layers == {"quic", "quic_tests"}
    assert ws.granularity == "test"

def test_from_test_file_unknown_layer_falls_back():
    file_to_layer = {"/path/unknown_test.ivy": "scaffolds"}
    workspace_groups = {"quic": ["quic", "quic_tests"]}
    ws = ActiveWorkspace.from_test_file(
        "/path/unknown_test.ivy", file_to_layer, workspace_groups
    )
    # Fallback: just the layer itself
    assert "scaffolds" in ws.active_layers
```

- [ ] **Step 2: Run tests — expect failure**
Run: `cd ivy-lsp && python -m pytest tests/test_active_workspace.py -v --no-header`
Expected: FAIL — module `ivy_lsp.active_workspace` does not exist

- [ ] **Step 3: Implement ActiveWorkspace**

Create `ivy_lsp/active_workspace.py`:
```python
"""Active workspace state — which protocol layers are currently in scope."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_STDLIB_MARKER = os.sep + os.path.join("ivy", "include")


@dataclass
class ActiveWorkspace:
    active_group: Optional[str]
    active_layers: Set[str]
    active_tests: List[str]
    granularity: str  # "protocol" | "role_pair" | "test" | "none"
    set_by: str  # "explicit" | "auto" | "marker" | "cleared"

    def is_set(self) -> bool:
        return self.granularity != "none" and bool(self.active_layers)

    def is_file_allowed(
        self,
        filepath: str,
        file_to_layer: Dict[str, str],
        scope_views: Optional[Dict] = None,
    ) -> Tuple[bool, str]:
        if not self.is_set():
            return True, ""
        norm = os.path.normpath(os.path.abspath(filepath))
        if _STDLIB_MARKER in norm:
            return True, "stdlib"
        layer = file_to_layer.get(norm)
        if layer is None:
            return True, "unlayered"
        if layer in self.active_layers:
            return True, f"in layer {layer}"
        return False, (
            f"layer '{layer}' is not in active workspace '{self.active_group}' "
            f"(active layers: {sorted(self.active_layers)})"
        )

    def save(self, state_file_path: str) -> None:
        data = {
            "version": 1,
            "active_group": self.active_group,
            "active_layers": sorted(self.active_layers),
            "active_tests": self.active_tests,
            "granularity": self.granularity,
            "set_by": self.set_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(state_file_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            logger.warning("Failed to save workspace state: %s", exc)

    @classmethod
    def load(cls, state_file_path: str) -> "ActiveWorkspace":
        try:
            with open(state_file_path) as f:
                data = json.load(f)
            return cls(
                active_group=data.get("active_group"),
                active_layers=set(data.get("active_layers", [])),
                active_tests=data.get("active_tests", []),
                granularity=data.get("granularity", "none"),
                set_by=data.get("set_by", "unknown"),
            )
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to load workspace state from %s: %s", state_file_path, exc)
            return cls.cleared()

    @classmethod
    def cleared(cls) -> "ActiveWorkspace":
        return cls(
            active_group=None,
            active_layers=set(),
            active_tests=[],
            granularity="none",
            set_by="cleared",
        )

    @classmethod
    def from_test_file(
        cls,
        test_file: str,
        file_to_layer: Dict[str, str],
        workspace_groups: Dict[str, List[str]],
    ) -> "ActiveWorkspace":
        norm = os.path.normpath(test_file)
        layer = file_to_layer.get(norm)
        if not layer:
            logger.warning("Test file %s not found in any layer", test_file)
            return cls.cleared()
        # Find workspace group containing this layer
        for group_name, group_layers in workspace_groups.items():
            if layer in group_layers:
                return cls(
                    active_group=group_name,
                    active_layers=set(group_layers),
                    active_tests=[test_file],
                    granularity="test",
                    set_by="explicit",
                )
        # Fallback: just the layer itself + its depends_on
        logger.warning("Layer '%s' not in any workspace_groups; using single-layer scope", layer)
        return cls(
            active_group=None,
            active_layers={layer},
            active_tests=[test_file],
            granularity="test",
            set_by="explicit",
        )
```

- [ ] **Step 4: Run tests — expect pass**
Run: `cd ivy-lsp && python -m pytest tests/test_active_workspace.py -v --no-header`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add ivy_lsp/active_workspace.py tests/test_active_workspace.py
git commit -m "feat: add ActiveWorkspace state class with save/load/from_test_file"
```

---

## Task 5: Include Resolver — Thread-Safe Staging Rebuild (Phase 2)

**Files:**
- Modify: `ivy-lsp/ivy_lsp/indexer/include_resolver.py:136-159` (__init__), line 438 (create_staging_directory), line 894 (build_layered_staging)
- Test: `ivy-lsp/tests/test_active_workspace_resolver.py` (new)

- [ ] **Step 1: Write failing tests for set_active_workspace**

```python
# tests/test_active_workspace_resolver.py
import os
import pytest
from ivy_lsp.indexer.include_resolver import IncludeResolver
from ivy_lsp.workspace_detection import WorkspaceLayer

def test_set_active_workspace_filters_layers(tmp_path):
    """After set_active_workspace, resolve only finds files from active layers."""
    # Create protocol dirs
    quic_dir = tmp_path / "protocol-testing" / "quic" / "quic_stack"
    apt_dir = tmp_path / "protocol-testing" / "apt" / "apt_stack"
    quic_dir.mkdir(parents=True)
    apt_dir.mkdir(parents=True)
    (quic_dir / "quic_frame.ivy").write_text("#lang ivy1.7\n")
    (apt_dir / "quic_frame.ivy").write_text("#lang ivy1.7\n# APT version\n")

    layers = [
        WorkspaceLayer(id="quic", include_paths=["protocol-testing/quic/quic_stack"], priority=1),
        WorkspaceLayer(id="apt_core", include_paths=["protocol-testing/apt/apt_stack"], priority=2),
    ]
    resolver = IncludeResolver(
        workspace_root=str(tmp_path),
        workspace_layers=layers,
    )
    resolver.build_layered_staging()
    resolver.create_staging_directory()

    # Before active workspace: both layers searchable
    result_all = resolver.resolve("quic_frame", str(quic_dir / "dummy.ivy"))
    assert result_all is not None

    # Set active workspace to quic only
    resolver.set_active_workspace({"quic"})
    result = resolver.resolve("quic_frame", str(quic_dir / "dummy.ivy"))
    assert result is not None
    assert "quic" in result and "apt" not in result

    # Set active workspace to apt only
    resolver.set_active_workspace({"apt_core"})
    result = resolver.resolve("quic_frame", str(apt_dir / "dummy.ivy"))
    assert result is not None
    assert "apt" in result

def test_set_active_workspace_clears_restores_all(tmp_path):
    """Passing empty set restores all layers."""
    quic_dir = tmp_path / "protocol-testing" / "quic" / "quic_stack"
    quic_dir.mkdir(parents=True)
    (quic_dir / "quic_types.ivy").write_text("#lang ivy1.7\n")
    layers = [
        WorkspaceLayer(id="quic", include_paths=["protocol-testing/quic/quic_stack"], priority=1),
    ]
    resolver = IncludeResolver(workspace_root=str(tmp_path), workspace_layers=layers)
    resolver.build_layered_staging()
    resolver.create_staging_directory()
    resolver.set_active_workspace({"quic"})
    resolver.set_active_workspace(set())  # clear
    result = resolver.resolve("quic_types", str(quic_dir / "dummy.ivy"))
    assert result is not None

def test_resolver_has_staging_lock():
    """IncludeResolver must have a _staging_lock for thread safety."""
    resolver = IncludeResolver(workspace_root="/tmp")
    assert hasattr(resolver, '_staging_lock')
```

- [ ] **Step 2: Run tests — expect failure**
Run: `cd ivy-lsp && python -m pytest tests/test_active_workspace_resolver.py -v --no-header`
Expected: FAIL — `set_active_workspace` not found

- [ ] **Step 3: Implement set_active_workspace in include_resolver.py**

Add to `__init__` (after line 159):
```python
        import threading
        self._staging_lock = threading.Lock()
        self._active_layers: set[str] = set()
```

Add new method (after `build_layered_staging`):
```python
    def set_active_workspace(self, active_layers: set[str]) -> None:
        """Rebuild staging with only the specified layers active.

        Thread-safe: acquires _staging_lock during the rebuild to prevent
        concurrent resolve() calls from reading partially-rebuilt staging.
        """
        with self._staging_lock:
            self._active_layers = set(active_layers)
            if active_layers:
                filtered = [l for l in self._workspace_layers if l.id in active_layers]
            else:
                filtered = list(self._workspace_layers)
            # Clean and rebuild both layered and flat staging
            self.cleanup_staging()
            if filtered:
                self._workspace_layers_active = filtered
                self.build_layered_staging(layers=filtered)
                self.create_staging_directory()
            logger.info(
                "Active workspace set: %d layers active (%s)",
                len(filtered),
                ", ".join(l.id for l in filtered),
            )
```

Modify `build_layered_staging` signature (line 894):
```python
    def build_layered_staging(self, layers=None) -> None:
```
And at the start of the method, add:
```python
        if layers is None:
            layers = self._workspace_layers
```
Then replace all references to `self._workspace_layers` within the method body with `layers`.

Wrap the dispatch section of `resolve()` with `self._staging_lock` (the section that reads `self._partition_staging` and `self._file_to_layer`).

- [ ] **Step 4: Run tests — expect pass**
Run: `cd ivy-lsp && python -m pytest tests/test_active_workspace_resolver.py -v --no-header`
Expected: PASS

- [ ] **Step 5: Run full test suite**
Run: `cd ivy-lsp && python -m pytest tests/ -x --no-header -q`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**
```bash
git add ivy_lsp/indexer/include_resolver.py tests/test_active_workspace_resolver.py
git commit -m "feat: add set_active_workspace() with thread-safe staging rebuild"
```

---

## Task 6: ivy_workspace MCP Tool (Phase 2)

**Files:**
- Create: `ivy-lsp/ivy_lsp/tools/workspace.py`
- Modify: `ivy-lsp/ivy_lsp/tools/__init__.py:489-496` (register_all_tools)
- Modify: `ivy-lsp/ivy_lsp/mcp_server.py:77-127` (ToolContext — add active_workspace field)
- Test: `ivy-lsp/tests/test_tool_workspace.py`

- [ ] **Step 1: Write failing tests for the MCP tool**

Test: `set` action writes state file and returns status.
Test: `get` action reads current state.
Test: `list` action returns available workspace groups.
Test: `clear` action resets state.
Test: unknown target returns error with available groups list.

- [ ] **Step 2: Run tests — expect failure**

- [ ] **Step 3: Add `active_workspace` field to ToolContext**

In `mcp_server.py`, add after line 102:
```python
    # Active workspace state (populated on startup or by ivy_workspace tool)
    active_workspace: Any = None  # Optional[ActiveWorkspace]
```

- [ ] **Step 4: Implement `tools/workspace.py`**

Create `ivy_lsp/tools/workspace.py` with:
- `register_workspace_tools(mcp, ctx)` function
- `ivy_workspace` tool handler with actions: set, get, list, clear
- `set` reads `workspace_groups` from ctx, creates ActiveWorkspace, saves state file, calls `ctx.include_resolver.set_active_workspace()` (in-process mode)
- `list` shows current workspace + available groups
- State file path: `os.path.join(ctx.root, ".ivy-workspace-state.json")`

- [ ] **Step 5: Register in `tools/__init__.py`**

Add `register_workspace_tools` call in `register_all_tools`.

- [ ] **Step 6: Run tests — expect pass**

- [ ] **Step 7: Commit**
```bash
git add ivy_lsp/tools/workspace.py ivy_lsp/tools/__init__.py ivy_lsp/mcp_server.py tests/test_tool_workspace.py
git commit -m "feat: add ivy_workspace MCP tool for workspace management"
```

---

## Task 7: WorkspaceContext Integration (Phase 2)

**Files:**
- Modify: `ivy-lsp/ivy_lsp/workspace_context.py:108` (add ActiveWorkspace integration)
- Modify: `ivy-lsp/ivy_lsp/server_setup.py` (init workspace state from state file or marker)

- [ ] **Step 1: Add ActiveWorkspace to WorkspaceContext**

In `workspace_context.py`, add to `__init__`:
```python
        from ivy_lsp.active_workspace import ActiveWorkspace
        self.active_workspace: ActiveWorkspace = ActiveWorkspace.cleared()
```

Add method to load state:
```python
    def load_active_workspace(self, state_file_path: str) -> None:
        from ivy_lsp.active_workspace import ActiveWorkspace
        self.active_workspace = ActiveWorkspace.load(state_file_path)
```

- [ ] **Step 2: Init workspace state in server_setup.py**

After workspace detection, check for `.ivy-workspace-state.json` and load it.

- [ ] **Step 3: Run full test suite**
Run: `cd ivy-lsp && python -m pytest tests/ -x --no-header -q`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add ivy_lsp/workspace_context.py ivy_lsp/server_setup.py
git commit -m "feat: integrate ActiveWorkspace into WorkspaceContext and server startup"
```

---

## Task 8: Edit Isolation Hook (Phase 3)

**Files:**
- Create: `panther-ivy-plugin/hooks/scripts/check-workspace-scope.py`
- Modify: `panther-ivy-plugin/hooks/hooks.json`
- Test: Manual test via `/set-workspace` + edit attempt

- [ ] **Step 1: Create `check-workspace-scope.py`**

Python script that:
1. Reads `.ivy-workspace-state.json` from `$IVY_WORKSPACE_ROOT`
2. Gets tool input from stdin (JSON with `tool_input.file_path`)
3. Decision logic per spec §7 + RF-4 block message template
4. Progressive narrowing: read/write `$TMPDIR/ivy-inferred-protocol-${IVY_SESSION_ID}.json`
5. Outputs JSON: `{"decision": "block"|"allow", "reason": "...", "hookSpecificOutput": {...}}`

- [ ] **Step 2: Register in hooks.json**

Add new PreToolUse entry for `Write|Edit` matcher (before the observability hook):
```json
{
  "matcher": "Write|Edit",
  "hooks": [{
    "type": "command",
    "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check-workspace-scope.py",
    "timeout": 5
  }]
}
```

- [ ] **Step 3: Test manually**
Run `/set-workspace quic`, then try to edit an APT file.
Expected: Hook blocks with RF-4 message template.

- [ ] **Step 4: Commit**
```bash
git add hooks/scripts/check-workspace-scope.py hooks/hooks.json
git commit -m "feat: add PreToolUse hook for workspace edit isolation"
```

---

## Task 9: Slash Commands (Phase 3)

**Files:**
- Create: `panther-ivy-plugin/skills/set-workspace/SKILL.md`
- Create: `panther-ivy-plugin/skills/clear-workspace/SKILL.md`
- Modify: `panther-ivy-plugin/hooks/scripts/detect-ivy-workspace.sh` (state restore)

- [ ] **Step 1: Create `/set-workspace` skill**

SKILL.md that:
- With args: calls `ivy_workspace(action="set", target=<arg>)`
- Without args: calls `ivy_workspace(action="list")` to show current + available
- With invalid target: shows available groups (per RF-8)
- Always shows current workspace as first line

- [ ] **Step 2: Create `/clear-workspace` skill**

SKILL.md that calls `ivy_workspace(action="clear")` and reports confirmation.

- [ ] **Step 3: Update `detect-ivy-workspace.sh` for state restore**

After existing workspace detection, add:
```bash
# Restore active workspace from previous session
STATE_FILE="${IVY_WORKSPACE_ROOT}/.ivy-workspace-state.json"
if [ -f "$STATE_FILE" ]; then
    ACTIVE_GROUP=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('active_group',''))" 2>/dev/null)
    SET_BY=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('set_by',''))" 2>/dev/null)
    if [ -n "$ACTIVE_GROUP" ] && [ "$SET_BY" = "explicit" ]; then
        echo "IVY_ACTIVE_WORKSPACE=$ACTIVE_GROUP" >> "$CLAUDE_ENV_FILE"
        # Include in additionalContext
    fi
fi
```

- [ ] **Step 4: Commit**
```bash
git add skills/set-workspace/ skills/clear-workspace/ hooks/scripts/detect-ivy-workspace.sh
git commit -m "feat: add /set-workspace and /clear-workspace commands with session restore"
```

---

## Task 10: Workspace Symbol Filtering (Phase 4)

**Files:**
- Modify: `ivy-lsp/ivy_lsp/features/workspace_symbols.py`
- Test: Add to existing workspace symbol tests

- [ ] **Step 1: Add active workspace filtering to `compute_workspace_symbols()`**

Add `active_workspace` parameter. When set, filter symbols to active layers + stdlib (per RF-11):
```python
if active_workspace and active_workspace.is_set() and hasattr(indexer, 'resolver'):
    file_to_layer = indexer.resolver._file_to_layer
    stdlib_path = os.sep + os.path.join("ivy", "include")
    flat = [f for f in flat
            if file_to_layer.get(os.path.normpath(os.path.abspath(f.file_path))) in active_workspace.active_layers
            or (f.file_path and stdlib_path in f.file_path)]
```

- [ ] **Step 2: Thread active_workspace through from LSP handler**

- [ ] **Step 3: Test and commit**
```bash
git commit -m "feat: filter workspace symbols to active workspace layers"
```

---

## Task 11: Collision Diagnostics (Phase 4)

**Files:**
- Modify: `ivy-lsp/ivy_lsp/tools/analysis.py`
- Test: `ivy-lsp/tests/test_collision_diagnostics.py`

- [ ] **Step 1: Add `mode="collisions"` to `ivy_diagnostics`**

New code path that:
- Reads `resolver._collision_map`
- Classifies each collision: intra-layer (ERROR), cross-layer in active scope (WARNING), cross-boundary (INFO)
- Returns structured JSON with collisions per severity

- [ ] **Step 2: Test and commit**
```bash
git commit -m "feat: add collision diagnostics mode to ivy_diagnostics"
```

---

## Task 12: Migration Script (Phase 1 — can run after Phase 2)

**Files:**
- Create: `ivy-lsp/scripts/generate_protocol_markers.py`

- [ ] **Step 1: Create idempotent script**

Python script that:
- Reads root `.ivyworkspace`
- For each workspace_group, generates a per-protocol `.ivyworkspace` marker
- Computes `workspace_root_offset` from protocol dir to root
- Writes marker files (overwrites if exists)

- [ ] **Step 2: Test by running and verifying output**
Run: `cd panther_ivy && python ../ivy-lsp/scripts/generate_protocol_markers.py`
Expected: Marker files created/updated with correct content

- [ ] **Step 3: Commit**
```bash
git commit -m "feat: add generate_protocol_markers.py migration script"
```

---

## Task 13: PANTHER Heuristic Cleanup (Phase 4)

**Files:**
- Modify: `ivy-lsp/ivy_lsp/workspace_detection.py:208-286`

- [ ] **Step 1: Replace hardcoded protocol names with dynamic discovery**

Instead of hardcoding `quic`, `minip`, `apt`, scan `protocol-testing/` for `.ivyworkspace` markers.

- [ ] **Step 2: Run existing detection tests**
Run: `cd ivy-lsp && python -m pytest tests/test_workspace_detection.py -v --no-header`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git commit -m "refactor: replace hardcoded PANTHER heuristic with dynamic marker discovery"
```

---

## Task 14: Plugin CLAUDE.md + Ecosystem Updates (Phase 5)

**Files:**
- Modify: `panther-ivy-plugin/CLAUDE.md`
- Modify: All 16 skill SKILL.md files
- Modify: All 5 agent .md files
- Modify: All 10 command .md files
- Modify: Hook scripts (detect-ivy-workspace, post-write-ivy-lint, wait-for-indexing, 7 observability hooks)

This task is best executed as a **batch with a subagent** using a template pattern:

- [ ] **Step 1: Add "Workspace Awareness" section to CLAUDE.md**

Add after the "Available Agents" section:
```markdown
## Workspace Awareness

The plugin supports active workspace scoping to prevent cross-protocol collisions.

### Commands
- `/set-workspace <protocol>` — activate workspace (e.g., `/set-workspace quic`)
- `/clear-workspace` — remove workspace restrictions
- `/set-workspace` (no args) — show current workspace and available groups

### Behavior
- **Edit isolation**: When a workspace is active, writes to `.ivy` files outside the active protocol are blocked.
- **Auto-restore**: Previous session's workspace is restored on session start.
- **Auto-detection**: Opening a file auto-scopes to its protocol via per-protocol `.ivyworkspace` markers.
- **Progressive narrowing**: Without explicit workspace, the system suggests scoping after cross-protocol edits.

### Scoping
All MCP tool `relative_path` and `test_file` parameters are workspace-relative.
Use `test_file` for NCT-aligned coverage scoping.
```

- [ ] **Step 2: Update skills (batch)**

For each of the 16 skills, add a note about workspace awareness. Template:
```
**Workspace**: Set active workspace with `/set-workspace <protocol>` before starting. All file paths and MCP tool calls are scoped to the active workspace.
```

Key skills needing specific updates:
- `nct-methodology`: Add "Step 0: Set workspace" before EXPLORE phase
- `ivy-toolkit`: Update coverage scoping table with workspace column
- `ivy-workflow-orchestrator`: Add workspace stability checkpoint
- `ivy-lsp-walkthrough`: Add workspace bootstrapping step

- [ ] **Step 3: Update agents (batch)**

For each of the 5 agents, add workspace context awareness:
- `navigator.md`: Check workspace at dispatch, suggest if not set
- `spec-analyst.md`: Anchor Glob/LSP calls to workspace root
- `model-reviewer.md`: Scope file discovery to workspace
- `methodology-guide.md`: Add `ivy_workspace` to tool table
- `traceability-agent.md`: Workspace-relative manifest paths

- [ ] **Step 4: Update commands (batch)**

For each of the 10 commands, add workspace reporting:
- `nct-health.md`: Report active workspace in health output
- `nct-validate.md`: Add workspace pre-flight check
- `nct-scaffold.md`: Confirm workspace before file creation
- Others: Add workspace context to output header

- [ ] **Step 5: Update hook scripts**

- `post-write-ivy-lint.sh`: Skip lint for files outside active workspace
- `wait-for-indexing.sh`: Report workspace size (file count)
- `obs_*.py` (7 files): Add `workspace_root` tag to all events

- [ ] **Step 6: Commit**
```bash
git add -A
git commit -m "docs: add workspace awareness to all plugin skills, agents, commands, and hooks"
```

---

## Task 15: Final Verification

- [ ] **Step 1: Run ivy-lsp full test suite**
Run: `cd ivy-lsp && python -m pytest tests/ -v --no-header`
Expected: All tests pass

- [ ] **Step 2: Manual smoke test**
```
/set-workspace quic
# Edit quic_connection.ivy → succeeds
# Edit apt_connection.ivy → blocked with RF-4 message
/set-workspace apt_quic
# Edit apt_connection.ivy → succeeds (apt_core in scope)
/clear-workspace
# All edits allowed
ivy_diagnostics(mode="collisions")
# Shows collision report
```

- [ ] **Step 3: Verify per-protocol marker auto-scoping**
Open a file in `protocol-testing/quic/` → expect auto-scope notification

- [ ] **Step 4: Final commit + push**
```bash
git log --oneline -10  # Review commit history
```
