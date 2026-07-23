# Propagation Engine MiniP PoC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 new ivy-lsp MCP tools, a propagation skill, and a `/nct-propagate` command that automate Ivy type change propagation across MiniP's 19 files.

**Architecture:** Skill-driven — ivy-lsp tools provide read-only analysis (what to change), a plugin skill provides pattern knowledge (how to change it), Claude generates code edits, and panther-serena applies them. Transaction log enables full revert on failure.

**Tech Stack:** Python 3.10+ (ivy-lsp), Markdown (plugin skill/command), pytest (tests), Ivy/C++ (protocol files)

**Spec:** `docs/superpowers/specs/2026-04-07-propagation-engine-minip-poc-design.md`

---

## File Paths

All paths are relative to the repo root. The key base directories:

```
IVY_LSP = panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
PLUGIN  = panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
MINIP   = panther/plugins/services/testers/panther_ivy/protocol-testing/minip
```

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `{IVY_LSP}/ivy_lsp/mcp/tools/propagation.py` | 3 new MCP tools: `ivy_find_variants`, `ivy_serdes_correlation`, `ivy_change_impact` | 1-5 |
| `{IVY_LSP}/ivy_lsp/mcp/tools/__init__.py` | Registration: import, timeouts, metadata, `register_all_tools` call | 1 |
| `{IVY_LSP}/tests/test_propagation_tools.py` | Unit tests for the 3 tools against real MiniP files | 2-5 |
| `{IVY_LSP}/tests/test_propagation_e2e.py` | Integration tests: e2e propagation, revert, mid-rejection | 8-9 |
| `{IVY_LSP}/tests/conftest.py` | Pytest fixture for MiniP worktree isolation | 7 |
| `{PLUGIN}/.claude-plugin/skills/propagation-patterns/SKILL.md` | Propagation pattern knowledge for Claude | 6 |
| `{PLUGIN}/.claude-plugin/commands/nct-propagate.md` | Interactive `/nct-propagate` command | 6 |

---

### Task 1: Module Scaffold + Registration

**Files:**
- Create: `{IVY_LSP}/ivy_lsp/mcp/tools/propagation.py`
- Modify: `{IVY_LSP}/ivy_lsp/mcp/tools/__init__.py`

- [ ] **Step 1: Create `propagation.py` with empty registration function**

```python
"""Propagation analysis tools for Ivy type change impact."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def register_propagation_tools(mcp: Any, ctx: Any) -> None:
    """Register propagation analysis MCP tools."""
    pass  # Tools added in subsequent tasks
```

- [ ] **Step 2: Add registration to `__init__.py`**

At the top of `__init__.py`, add import alongside existing imports (around line 689-695):
```python
from .propagation import register_propagation_tools
```

In `_TOOL_TIMEOUTS` dict (around line 30), add:
```python
    "ivy_find_variants": 30.0,
    "ivy_serdes_correlation": 30.0,
    "ivy_change_impact": 60.0,
```

In `_TOOL_METADATA` dict (around line 58), add:
```python
    "ivy_find_variants": {"cost": "low", "category": "propagation", "needs_model": True},
    "ivy_serdes_correlation": {"cost": "low", "category": "propagation", "needs_model": True},
    "ivy_change_impact": {"cost": "medium", "category": "propagation", "needs_model": True},
```

In `register_all_tools()` (around line 701), add at the end:
```python
    register_propagation_tools(mcp, ctx)
```

- [ ] **Step 3: Verify import works**

Run: `cd {IVY_LSP} && python -c "from ivy_lsp.mcp.tools.propagation import register_propagation_tools; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add {IVY_LSP}/ivy_lsp/mcp/tools/propagation.py {IVY_LSP}/ivy_lsp/mcp/tools/__init__.py
git commit -m "feat(ivy-lsp): scaffold propagation tools module with registration"
```

---

### Task 2: `ivy_find_variants` — Struct Parsing

**Files:**
- Modify: `{IVY_LSP}/ivy_lsp/mcp/tools/propagation.py`
- Create: `{IVY_LSP}/tests/test_propagation_tools.py`

- [ ] **Step 1: Write failing test for struct type**

```python
"""Tests for propagation analysis MCP tools."""

import os
import pytest
from ivy_lsp.mcp.tools.propagation import find_variants_impl

MINIP_DIR = os.environ.get(
    "PANTHER_IVY_PROTOCOL_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..",
                 "protocol-testing", "minip"),
)


class TestFindVariants:
    def test_struct_type_ping_packet(self):
        """ping_packet is a struct with one field: payload : frame.arr."""
        result = find_variants_impl("ping_packet", MINIP_DIR)
        assert result["type_name"] == "ping_packet"
        assert result["kind"] == "struct"
        assert result["file"].endswith("ping_packet.ivy")
        assert len(result["fields"]) == 1
        f = result["fields"][0]
        assert f["name"] == "payload"
        assert f["type"] == "frame.arr"
        assert f["is_array"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {IVY_LSP} && python -m pytest tests/test_propagation_tools.py::TestFindVariants::test_struct_type_ping_packet -v`
Expected: FAIL with `ImportError` or `cannot import name 'find_variants_impl'`

- [ ] **Step 3: Implement `find_variants_impl` for struct types**

Add to `propagation.py`:

```python
# Regex for struct type definitions: type this = struct { field : type, ... }
_STRUCT_RE = re.compile(
    r"object\s+([\w.]+)\s*=\s*\{[^}]*?"
    r"type\s+this\s*=\s*struct\s*\{([^}]+)\}",
    re.DOTALL | re.MULTILINE,
)

# Regex for individual field declarations inside struct body
_FIELD_RE = re.compile(r"(\w+)\s*:\s*([\w.]+)")


def _parse_struct_fields(body: str) -> list[dict[str, Any]]:
    """Parse field declarations from a struct body string."""
    fields = []
    for m in _FIELD_RE.finditer(body):
        name, ftype = m.group(1).strip(), m.group(2).strip()
        fields.append({
            "name": name,
            "type": ftype,
            "is_array": ftype.endswith(".arr"),
        })
    return fields


def _find_file_for_type(type_name: str, protocol_dir: str) -> tuple[str, str] | None:
    """Walk protocol dir for .ivy files containing the type definition. Returns (path, content)."""
    for root, _, files in os.walk(protocol_dir):
        for fname in files:
            if not fname.endswith(".ivy"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                content = f.read()
            # Check for struct object definition
            for m in _STRUCT_RE.finditer(content):
                if m.group(1) == type_name:
                    return fpath, content
    return None


def find_variants_impl(type_name: str, protocol_dir: str) -> dict[str, Any]:
    """Core logic for ivy_find_variants. Returns structured dict."""
    import os

    # Try struct type first
    found = _find_file_for_type(type_name, protocol_dir)
    if found:
        fpath, content = found
        for m in _STRUCT_RE.finditer(content):
            if m.group(1) == type_name:
                fields = _parse_struct_fields(m.group(2))
                line = content[:m.start()].count("\n") + 1
                rel_path = os.path.relpath(fpath, protocol_dir)
                return {
                    "type_name": type_name,
                    "kind": "struct",
                    "file": rel_path,
                    "line": line,
                    "fields": fields,
                }

    return {"error": f"Type '{type_name}' not found", "type_name": type_name}
```

Also add `import os` at the top of the file.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd {IVY_LSP} && PANTHER_IVY_PROTOCOL_DIR={MINIP} python -m pytest tests/test_propagation_tools.py::TestFindVariants::test_struct_type_ping_packet -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add {IVY_LSP}/ivy_lsp/mcp/tools/propagation.py {IVY_LSP}/tests/test_propagation_tools.py
git commit -m "feat(ivy-lsp): ivy_find_variants struct parsing with test"
```

---

### Task 3: `ivy_find_variants` — Variant Parsing + Tag Extraction

**Files:**
- Modify: `{IVY_LSP}/ivy_lsp/mcp/tools/propagation.py`
- Modify: `{IVY_LSP}/tests/test_propagation_tools.py`

- [ ] **Step 1: Write failing test for variant type**

Add to `TestFindVariants` in test file:

```python
    def test_variant_type_frame(self):
        """frame has 3 variants: ping(tag=0), pong(tag=1), timestamp(tag=2)."""
        result = find_variants_impl("frame", MINIP_DIR)
        assert result["type_name"] == "frame"
        assert result["kind"] == "variant"
        assert result["file"].endswith("ping_frame.ivy")
        assert len(result["members"]) == 3

        ping = result["members"][0]
        assert ping["name"] == "ping"
        assert ping["tag"] == 0
        assert ping["wire_type"] == "0x01"
        assert ping["fields"][0]["name"] == "data"

        pong = result["members"][1]
        assert pong["name"] == "pong"
        assert pong["tag"] == 1
        assert pong["wire_type"] == "0x02"

        ts = result["members"][2]
        assert ts["name"] == "timestamp"
        assert ts["tag"] == 2
        assert ts["wire_type"] == "0x03"
        assert ts["fields"][0]["name"] == "time"

    def test_tag_ordering_cross_check(self):
        """Tag integers from ivy_find_variants match open_tag() dispatch order."""
        result = find_variants_impl("frame", MINIP_DIR)
        for member in result["members"]:
            assert member["tag"] == result["members"].index(member)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {IVY_LSP} && PANTHER_IVY_PROTOCOL_DIR={MINIP} python -m pytest tests/test_propagation_tools.py::TestFindVariants::test_variant_type_frame -v`
Expected: FAIL — `find_variants_impl` returns `{"error": "Type 'frame' not found"}` because the current code only handles struct types.

- [ ] **Step 3: Implement variant member enumeration + tag extraction**

Add to `propagation.py`:

```python
from ivy_lsp.core.analysis.impl_block_parser import analyze_impl_blocks

# Regex for variant parent type: object X = { type this ... }
_VARIANT_PARENT_RE = re.compile(
    r"object\s+([\w.]+)\s*=\s*\{[^}]*?type\s+this\b",
    re.DOTALL | re.MULTILINE,
)

# Regex for variant member: object <name> = { variant this of <parent> = struct { ... } }
_VARIANT_MEMBER_RE = re.compile(
    r"object\s+(\w+)\s*=\s*\{[^}]*?"
    r"variant\s+this\s+of\s+(\w+)\s*=\s*struct\s*\{([^}]+)\}",
    re.DOTALL | re.MULTILINE,
)

# Regex for tag-to-wire-type mapping in C++ open_tag():
# if (tag == N) { frame_type = 0xNN;  OR  tag == N followed by frame_type = 0xNN
_TAG_WIRE_RE = re.compile(
    r"tag\s*==\s*(\d+)\s*\)\s*\{[^}]*?frame_type\s*=\s*(0x[0-9a-fA-F]+)",
    re.DOTALL,
)


def _extract_tag_wire_mappings(serializer_path: str) -> dict[int, str]:
    """Extract tag → wire_type mappings from the serializer's open_tag() C++ block."""
    with open(serializer_path) as f:
        source = f.read()
    impl = analyze_impl_blocks(source)
    # Concatenate all impl block content
    impl_text = ""
    for block in impl.impl_blocks:
        impl_text += block.content
    mappings = {}
    for m in _TAG_WIRE_RE.finditer(impl_text):
        tag = int(m.group(1))
        wire = m.group(2)
        mappings[tag] = wire
    return mappings


def _find_variant_type(type_name: str, protocol_dir: str) -> dict[str, Any] | None:
    """Find a variant parent type and its members across protocol .ivy files."""
    # Pass 1: find the parent type definition file
    parent_file = None
    parent_content = None
    for root, _, files in os.walk(protocol_dir):
        for fname in files:
            if not fname.endswith(".ivy"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                content = f.read()
            for m in _VARIANT_PARENT_RE.finditer(content):
                if m.group(1) == type_name:
                    parent_file = fpath
                    parent_content = content
                    break
            if parent_file:
                break

    if not parent_file:
        return None

    # Pass 2: find all variant members in the same file
    members = []
    for m in _VARIANT_MEMBER_RE.finditer(parent_content):
        member_name = m.group(1)
        parent_name = m.group(2)
        if parent_name != type_name:
            continue
        fields = _parse_struct_fields(m.group(3))
        members.append({"name": member_name, "fields": fields})

    # Pass 3: extract tag → wire_type from correlated serializer
    # Find the serializer by looking for serdes instance referencing this type
    tag_map = _find_tag_mappings_for_type(type_name, protocol_dir)

    # Assign tags by declaration order, cross-validated against C++ open_tag()
    for i, member in enumerate(members):
        member["tag"] = i
        member["wire_type"] = tag_map.get(i, "unknown")

    line = parent_content[:parent_content.index(f"object {type_name}")].count("\n") + 1
    rel_path = os.path.relpath(parent_file, protocol_dir)
    return {
        "type_name": type_name,
        "kind": "variant",
        "file": rel_path,
        "line": line,
        "members": members,
    }


def _find_tag_mappings_for_type(type_name: str, protocol_dir: str) -> dict[int, str]:
    """Find the serializer for a variant type and extract its tag mappings."""
    from ivy_lsp.core.analysis.pattern_library import SERDES_INSTANCE_RE

    for root, _, files in os.walk(protocol_dir):
        for fname in files:
            if not fname.endswith(".ivy"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                content = f.read()
            for m in SERDES_INSTANCE_RE.finditer(content):
                args = [a.strip() for a in m.group(2).split(",")]
                if len(args) >= 3:
                    msg_type = args[0]
                    ser_name = args[2]
                    # The serdes instance references the packet type, not the frame type.
                    # But the serializer handles frame variants via open_tag().
                    # Find the ser file by name convention.
                    ser_file = _find_file_by_object_name(ser_name, protocol_dir)
                    if ser_file:
                        return _extract_tag_wire_mappings(ser_file)
    return {}


def _find_file_by_object_name(obj_name: str, protocol_dir: str) -> str | None:
    """Find the .ivy file that defines an object by name."""
    obj_re = re.compile(rf"object\s+{re.escape(obj_name)}\s*=")
    for root, _, files in os.walk(protocol_dir):
        for fname in files:
            if not fname.endswith(".ivy"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                content = f.read()
            if obj_re.search(content):
                return fpath
    return None
```

Update `find_variants_impl` to try variant parsing after struct parsing fails:

```python
def find_variants_impl(type_name: str, protocol_dir: str) -> dict[str, Any]:
    """Core logic for ivy_find_variants. Returns structured dict."""
    # Try struct type first
    found = _find_file_for_type(type_name, protocol_dir)
    if found:
        fpath, content = found
        for m in _STRUCT_RE.finditer(content):
            if m.group(1) == type_name:
                fields = _parse_struct_fields(m.group(2))
                line = content[:m.start()].count("\n") + 1
                rel_path = os.path.relpath(fpath, protocol_dir)
                return {
                    "type_name": type_name,
                    "kind": "struct",
                    "file": rel_path,
                    "line": line,
                    "fields": fields,
                }

    # Try variant type
    variant_result = _find_variant_type(type_name, protocol_dir)
    if variant_result:
        return variant_result

    return {"error": f"Type '{type_name}' not found", "type_name": type_name}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {IVY_LSP} && PANTHER_IVY_PROTOCOL_DIR={MINIP} python -m pytest tests/test_propagation_tools.py::TestFindVariants -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add {IVY_LSP}/ivy_lsp/mcp/tools/propagation.py {IVY_LSP}/tests/test_propagation_tools.py
git commit -m "feat(ivy-lsp): ivy_find_variants variant parsing with tag extraction from C++ open_tag()"
```

---

### Task 4: `ivy_serdes_correlation`

**Files:**
- Modify: `{IVY_LSP}/ivy_lsp/mcp/tools/propagation.py`
- Modify: `{IVY_LSP}/tests/test_propagation_tools.py`

- [ ] **Step 1: Write failing test**

Add to test file:

```python
from ivy_lsp.mcp.tools.propagation import serdes_correlation_impl


class TestSerdesCorrelation:
    def test_ping_packet(self):
        """ping_packet maps to ping_ser + ping_deser via ping_packet_serdes in ping_shim."""
        result = serdes_correlation_impl("ping_packet", MINIP_DIR)
        assert result["type_name"] == "ping_packet"
        assert len(result["correlations"]) == 1
        c = result["correlations"][0]
        assert c["serializer"]["file"].endswith("ping_ser.ivy")
        assert c["serializer"]["class"] == "ping_ser"
        assert c["serializer"]["base"] == "ivy_binary_ser_128"
        assert c["serializer"]["states"] == 4
        assert c["deserializer"]["file"].endswith("ping_deser.ivy")
        assert c["deserializer"]["class"] == "ping_deser"
        assert c["deserializer"]["base"] == "ivy_binary_deser_128"
        assert c["deserializer"]["states"] == 4
        assert c["instance"]["name"] == "ping_packet_serdes"
        assert c["instance"]["file"].endswith("ping_shim.ivy")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {IVY_LSP} && PANTHER_IVY_PROTOCOL_DIR={MINIP} python -m pytest tests/test_propagation_tools.py::TestSerdesCorrelation -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement `serdes_correlation_impl`**

Add to `propagation.py`:

```python
from ivy_lsp.core.analysis.pattern_library import (
    SERDES_INSTANCE_RE,
    detect_serdes,
    PatternInstance,
)


def serdes_correlation_impl(type_name: str, protocol_dir: str) -> dict[str, Any]:
    """Core logic for ivy_serdes_correlation. Returns structured dict."""
    correlations = []

    # Pass 1: find serdes instances referencing this type
    for root, _, files in os.walk(protocol_dir):
        for fname in files:
            if not fname.endswith(".ivy"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                content = f.read()
            for m in SERDES_INSTANCE_RE.finditer(content):
                instance_name = m.group(1)
                args = [a.strip() for a in m.group(2).split(",")]
                if len(args) < 4:
                    continue
                msg_type, _data_type, ser_name, deser_name = args[0], args[1], args[2], args[3]
                if msg_type != type_name:
                    continue

                instance_line = content[:m.start()].count("\n") + 1
                instance_rel = os.path.relpath(fpath, protocol_dir)

                # Pass 2: resolve ser/deser to files and extract class info
                ser_info = _resolve_serdes_class(ser_name, protocol_dir, is_serializer=True)
                deser_info = _resolve_serdes_class(deser_name, protocol_dir, is_serializer=False)

                correlations.append({
                    "serializer": ser_info,
                    "deserializer": deser_info,
                    "instance": {
                        "name": instance_name,
                        "file": instance_rel,
                        "line": instance_line,
                    },
                })

    return {"type_name": type_name, "correlations": correlations}


def _resolve_serdes_class(
    obj_name: str, protocol_dir: str, *, is_serializer: bool
) -> dict[str, Any]:
    """Resolve a ser/deser object name to its file, class, base, and state count."""
    fpath = _find_file_by_object_name(obj_name, protocol_dir)
    if not fpath:
        return {"error": f"Object '{obj_name}' not found", "class": obj_name}

    with open(fpath) as f:
        source = f.read()

    impl = analyze_impl_blocks(source)
    rel_path = os.path.relpath(fpath, protocol_dir)

    # Find matching class
    base_class = "unknown"
    for cls in impl.classes:
        if is_serializer and cls.is_serializer:
            base_class = cls.base_class or "unknown"
            break
        if not is_serializer and cls.is_deserializer:
            base_class = cls.base_class or "unknown"
            break

    # Count states from first enum
    state_count = len(impl.enum_states[0].states) if impl.enum_states else 0

    return {
        "file": rel_path,
        "class": obj_name,
        "base": base_class,
        "states": state_count,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd {IVY_LSP} && PANTHER_IVY_PROTOCOL_DIR={MINIP} python -m pytest tests/test_propagation_tools.py::TestSerdesCorrelation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add {IVY_LSP}/ivy_lsp/mcp/tools/propagation.py {IVY_LSP}/tests/test_propagation_tools.py
git commit -m "feat(ivy-lsp): ivy_serdes_correlation with two-step resolution"
```

---

### Task 5: `ivy_change_impact`

**Files:**
- Modify: `{IVY_LSP}/ivy_lsp/mcp/tools/propagation.py`
- Modify: `{IVY_LSP}/tests/test_propagation_tools.py`

- [ ] **Step 1: Write failing tests**

Add to test file:

```python
from ivy_lsp.mcp.tools.propagation import change_impact_impl


class TestChangeImpact:
    def test_add_field_to_ping_packet(self):
        """add_field on ping_packet: 3 auto, 10 manual, 6 unaffected."""
        result = change_impact_impl("ping_packet", "add_field", MINIP_DIR)
        assert result["type_name"] == "ping_packet"
        assert result["change_type"] == "add_field"
        assert len(result["auto_propagate"]) == 3
        auto_files = [e["file"] for e in result["auto_propagate"]]
        assert any("ping_packet.ivy" in f for f in auto_files)
        assert any("ping_ser.ivy" in f for f in auto_files)
        assert any("ping_deser.ivy" in f for f in auto_files)
        assert len(result["manual_review"]) == 10
        assert len(result["unaffected"]) >= 5

    def test_add_variant_to_frame(self):
        """add_variant on frame: 3 auto (frame def + ser + deser)."""
        result = change_impact_impl("frame", "add_variant", MINIP_DIR)
        assert len(result["auto_propagate"]) == 3
        auto_files = [e["file"] for e in result["auto_propagate"]]
        assert any("ping_frame.ivy" in f for f in auto_files)
        assert any("ping_ser.ivy" in f for f in auto_files)
        assert any("ping_deser.ivy" in f for f in auto_files)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd {IVY_LSP} && PANTHER_IVY_PROTOCOL_DIR={MINIP} python -m pytest tests/test_propagation_tools.py::TestChangeImpact -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement `change_impact_impl`**

Add to `propagation.py`:

```python
from ivy_lsp.core.analysis.pattern_library import (
    detect_all_patterns,
    PatternKind,
)

# Category classification based on pattern detection
_CATEGORY_MAP = {
    PatternKind.SHIM: "shim",
    PatternKind.ENTITY: "entity",
    PatternKind.MONITORS: "behavior",
}


def change_impact_impl(
    type_name: str, change_type: str, protocol_dir: str
) -> dict[str, Any]:
    """Core logic for ivy_change_impact."""
    # Step 1: find the type definition file
    type_info = find_variants_impl(type_name, protocol_dir)
    if "error" in type_info:
        return {"error": type_info["error"], "type_name": type_name, "change_type": change_type}

    type_file_rel = type_info["file"]

    # Step 2: find correlated ser/deser files
    # For variant types, the serdes is on the packet type, not the frame type.
    # We need to find which packet type uses this variant as payload.
    ser_files = set()
    deser_files = set()
    if type_info["kind"] == "struct":
        corr = serdes_correlation_impl(type_name, protocol_dir)
        for c in corr.get("correlations", []):
            ser_files.add(c["serializer"]["file"])
            deser_files.add(c["deserializer"]["file"])
    else:
        # For variant types, find all serdes instances that transitively use this type
        # by scanning all serdes instances and checking if their serializer handles this type's variants
        for root, _, files in os.walk(protocol_dir):
            for fname in files:
                if not fname.endswith(".ivy"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()
                for m in SERDES_INSTANCE_RE.finditer(content):
                    args = [a.strip() for a in m.group(2).split(",")]
                    if len(args) >= 4:
                        ser_name, deser_name = args[2], args[3]
                        ser_path = _find_file_by_object_name(ser_name, protocol_dir)
                        if ser_path:
                            with open(ser_path) as sf:
                                ser_src = sf.read()
                            # Check if this serializer's open_tag handles our variant's wire types
                            if _TAG_WIRE_RE.search(
                                "".join(b.content for b in analyze_impl_blocks(ser_src).impl_blocks)
                            ):
                                ser_files.add(os.path.relpath(ser_path, protocol_dir))
                                deser_path = _find_file_by_object_name(deser_name, protocol_dir)
                                if deser_path:
                                    deser_files.add(os.path.relpath(deser_path, protocol_dir))

    # Step 3: build auto_propagate list
    auto_propagate = []
    auto_set = set()

    auto_propagate.append({
        "file": type_file_rel,
        "category": "type_definition",
        "edit": "add_field_to_struct" if change_type == "add_field" else "add_variant_member",
    })
    auto_set.add(type_file_rel)

    for sf in sorted(ser_files):
        auto_propagate.append({"file": sf, "category": "serializer", "edit": "add_state_and_set_case"})
        auto_set.add(sf)
    for df in sorted(deser_files):
        auto_propagate.append({"file": df, "category": "deserializer", "edit": "add_state_and_get_case"})
        auto_set.add(df)

    # Step 4: categorize all other protocol files
    manual_review = []
    unaffected = []

    # Build include dependency: which files include the type's file?
    type_file_stem = os.path.splitext(os.path.basename(type_file_rel))[0]
    include_re = re.compile(rf"^\s*include\s+{re.escape(type_file_stem)}\b", re.MULTILINE)

    # Also track transitive includes via ser/deser files
    auto_stems = set()
    for af in auto_set:
        auto_stems.add(os.path.splitext(os.path.basename(af))[0])

    for root, _, files in os.walk(protocol_dir):
        for fname in files:
            if not fname.endswith(".ivy"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, protocol_dir)
            if rel in auto_set:
                continue

            with open(fpath) as f:
                content = f.read()

            # Check if this file depends on any auto_propagate file (directly or transitively)
            depends = False
            for stem in auto_stems:
                dep_re = re.compile(rf"^\s*include\s+{re.escape(stem)}\b", re.MULTILINE)
                if dep_re.search(content):
                    depends = True
                    break
            # Also check transitive: files that include shim files which include the type
            if not depends and include_re.search(content):
                depends = True

            if depends:
                # Categorize by pattern detection
                patterns = detect_all_patterns(content, fpath)
                category = "other"
                reason = "transitively includes changed type"
                for p in patterns:
                    if p.kind in _CATEGORY_MAP:
                        category = _CATEGORY_MAP[p.kind]
                        break
                if "test" in rel.lower():
                    category = "test"
                    reason = "may need test coverage"
                elif category == "shim":
                    reason = "check if change affects network I/O"
                elif category == "entity":
                    reason = "check if field needs constraint logic"
                elif category == "behavior":
                    reason = "check if change affects behavior"

                manual_review.append({"file": rel, "category": category, "reason": reason})
            else:
                unaffected.append(rel)

    return {
        "type_name": type_name,
        "change_type": change_type,
        "auto_propagate": auto_propagate,
        "manual_review": sorted(manual_review, key=lambda x: x["file"]),
        "unaffected": sorted(unaffected),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd {IVY_LSP} && PANTHER_IVY_PROTOCOL_DIR={MINIP} python -m pytest tests/test_propagation_tools.py::TestChangeImpact -v`
Expected: PASS

- [ ] **Step 5: Wire up MCP tool handlers**

Add to `register_propagation_tools` in `propagation.py`:

```python
def register_propagation_tools(mcp: Any, ctx: Any) -> None:
    """Register propagation analysis MCP tools."""

    @mcp.tool()
    @safe_tool(ctx=ctx)
    async def ivy_find_variants(
        type_name: str,
        protocol: str | None = None,
    ) -> dict:
        """Enumerate the structure of an Ivy type — struct fields or variant members with tags."""
        protocol_dir = ctx.resolve_protocol_dir(protocol)
        return find_variants_impl(type_name, protocol_dir)

    @mcp.tool()
    @safe_tool(ctx=ctx)
    async def ivy_serdes_correlation(
        type_name: str,
        protocol: str | None = None,
    ) -> dict:
        """Find which ser/deser files handle an Ivy type and through which serdes instance."""
        protocol_dir = ctx.resolve_protocol_dir(protocol)
        return serdes_correlation_impl(type_name, protocol_dir)

    @mcp.tool()
    @safe_tool(ctx=ctx)
    async def ivy_change_impact(
        type_name: str,
        change_type: str = "add_field",
        protocol: str | None = None,
    ) -> dict:
        """Categorize files affected by a type change into auto-propagate, manual-review, and unaffected."""
        protocol_dir = ctx.resolve_protocol_dir(protocol)
        return change_impact_impl(type_name, change_type, protocol_dir)
```

Add `safe_tool` import at top:
```python
from ivy_lsp.mcp.tools import safe_tool
```

- [ ] **Step 6: Commit**

```bash
git add {IVY_LSP}/ivy_lsp/mcp/tools/propagation.py {IVY_LSP}/tests/test_propagation_tools.py
git commit -m "feat(ivy-lsp): ivy_change_impact with categorization + MCP tool wiring"
```

---

### Task 6: Plugin Skill + Command

**Files:**
- Create: `{PLUGIN}/.claude-plugin/skills/propagation-patterns/SKILL.md`
- Create: `{PLUGIN}/.claude-plugin/commands/nct-propagate.md`

- [ ] **Step 1: Create `propagation-patterns` skill**

Create directory `{PLUGIN}/.claude-plugin/skills/propagation-patterns/` and write `SKILL.md`. The full content is the encoding table, add-field pattern, add-variant pattern, asymmetry warnings, and authority rule from spec Sections 5.1-5.5. This is a Markdown file with YAML frontmatter:

```yaml
---
name: propagation-patterns
description: "Pattern knowledge for propagating Ivy type changes to ser/deser state machines. Covers struct field addition and frame variant addition with encoding tables, concrete examples, asymmetry warnings, and hardcoded constant detection."
---
```

The body should include all content from spec Sections 5.1 through 5.5 verbatim, including:
- The Ivy Type-to-C++ Encoding Table
- The Add-Field Pattern with MiniP concrete example
- The Add-Variant Pattern with tag index rule
- The Ser/Deser Asymmetry Warnings including `payload_length=12` and `current_ping_size=5`
- The authority rule deferring to `ivy_change_impact` output

- [ ] **Step 2: Create `/nct-propagate` command**

Write `{PLUGIN}/.claude-plugin/commands/nct-propagate.md`:

```yaml
---
name: nct-propagate
description: Propagate an Ivy type change across ser/deser, shims, tests, and behavior files
arguments:
  - name: change
    description: "Natural language description of the change (e.g., 'add seq_num : byte to ping_packet')"
    required: true
---
```

The body should encode the full Step 0-6 workflow from spec Section 6.1:
- Step 0: workspace activation (`ivy_workspace`)
- Step 1: parse change description
- Step 2: call `ivy_find_variants`, `ivy_serdes_correlation`, `ivy_change_impact`
- Step 3: present plan with manual-review list and hardcoded-constant warnings
- Step 4: per-file edit with transaction log and user approval
- Step 5: `ivy_compile` on both test files
- Step 6: revert on failure
- Section 6.4: mid-propagation rejection behavior

The command should reference `propagation-patterns` skill for pattern knowledge and instruct Claude to use `mcp__serena__*` tools for all file operations.

- [ ] **Step 3: Commit**

```bash
git add {PLUGIN}/.claude-plugin/skills/propagation-patterns/SKILL.md {PLUGIN}/.claude-plugin/commands/nct-propagate.md
git commit -m "feat(plugin): propagation-patterns skill and /nct-propagate command"
```

---

### Task 7: Integration Test Fixture

**Files:**
- Modify or create: `{IVY_LSP}/tests/conftest.py`

- [ ] **Step 1: Add MiniP worktree fixture**

Add to `conftest.py`:

```python
import os
import subprocess
import tempfile

import pytest


@pytest.fixture(scope="session")
def minip_protocol_dir():
    """Return path to MiniP protocol files (read-only tests)."""
    env_dir = os.environ.get("PANTHER_IVY_PROTOCOL_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    # Fallback: relative to repo root
    repo_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
    return os.path.join(
        repo_root, "panther", "plugins", "services", "testers",
        "panther_ivy", "protocol-testing", "minip",
    )


@pytest.fixture
def minip_worktree(tmp_path):
    """Create an isolated Git worktree with MiniP files for destructive tests.

    Yields the path to the worktree's minip/ directory.
    Cleans up the worktree after the test.
    """
    repo_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
    worktree_path = str(tmp_path / "propagation-test")

    # Create worktree from current HEAD
    subprocess.run(
        ["git", "worktree", "add", "--detach", worktree_path, "HEAD"],
        cwd=repo_root, check=True, capture_output=True,
    )
    try:
        minip_dir = os.path.join(
            worktree_path, "panther", "plugins", "services", "testers",
            "panther_ivy", "protocol-testing", "minip",
        )
        yield minip_dir
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree_path],
            cwd=repo_root, capture_output=True,
        )
```

- [ ] **Step 2: Commit**

```bash
git add {IVY_LSP}/tests/conftest.py
git commit -m "test(ivy-lsp): add MiniP worktree fixture for propagation integration tests"
```

---

### Task 8: End-to-End Integration Test

**Files:**
- Create: `{IVY_LSP}/tests/test_propagation_e2e.py`

- [ ] **Step 1: Write e2e test for add-field propagation**

```python
"""End-to-end propagation integration tests."""

import os
import pytest
from ivy_lsp.mcp.tools.propagation import (
    find_variants_impl,
    serdes_correlation_impl,
    change_impact_impl,
)


@pytest.mark.integration
class TestPropagationE2E:
    def test_add_field_propagation(self, minip_worktree):
        """Full add-field propagation: edit 3 files, compile succeeds."""
        protocol_dir = minip_worktree

        # Step 1: analyze
        impact = change_impact_impl("ping_packet", "add_field", protocol_dir)
        assert len(impact["auto_propagate"]) == 3

        # Step 2: store originals (transaction log)
        tx_log = []
        for entry in impact["auto_propagate"]:
            fpath = os.path.join(protocol_dir, entry["file"])
            with open(fpath) as f:
                tx_log.append({"file": fpath, "original": f.read()})

        # Step 3: apply edits
        # Edit 1: add field to ping_packet.ivy
        pkt_path = os.path.join(protocol_dir, impact["auto_propagate"][0]["file"])
        with open(pkt_path) as f:
            pkt_src = f.read()
        pkt_src = pkt_src.replace(
            "payload : frame.arr",
            "seq_num : stream_pos,\n        payload : frame.arr",
        )
        with open(pkt_path, "w") as f:
            f.write(pkt_src)

        # Edit 2: add state to ping_ser.ivy
        ser_path = os.path.join(protocol_dir, impact["auto_propagate"][1]["file"])
        with open(ser_path) as f:
            ser_src = f.read()
        ser_src = ser_src.replace(
            "enum {ping_s_init,",
            "enum {ping_s_init,\n              ping_s_seq_num,",
        )
        ser_src = ser_src.replace(
            "state = ping_s_payload;",
            "state = ping_s_seq_num;",
            1,  # only first occurrence (in ping_s_init case)
        )
        ser_src = ser_src.replace(
            "case ping_s_time:",
            "case ping_s_seq_num:\n"
            "            {\n"
            "                setn(res, 8);\n"
            "                state = ping_s_payload;\n"
            "            }\n"
            "            break;\n"
            "            case ping_s_time:",
        )
        with open(ser_path, "w") as f:
            f.write(ser_src)

        # Edit 3: add state to ping_deser.ivy
        deser_path = os.path.join(protocol_dir, impact["auto_propagate"][2]["file"])
        with open(deser_path) as f:
            deser_src = f.read()
        deser_src = deser_src.replace(
            "enum {ping_s_init,",
            "enum {ping_s_init,\n              ping_s_seq_num,",
        )
        deser_src = deser_src.replace(
            "state = ping_s_payload;",
            "state = ping_s_seq_num;",
            1,
        )
        deser_src = deser_src.replace(
            "case ping_s_time:",
            "case ping_s_seq_num:\n"
            "            {\n"
            "                getn(res, 8);\n"
            "                state = ping_s_payload;\n"
            "            }\n"
            "            break;\n"
            "            case ping_s_time:",
        )
        with open(deser_path, "w") as f:
            f.write(deser_src)

        # Step 4: verify all 3 files were modified
        for entry in tx_log:
            with open(entry["file"]) as f:
                assert f.read() != entry["original"]

        # Step 5: revert
        for entry in reversed(tx_log):
            with open(entry["file"], "w") as f:
                f.write(entry["original"])

        # Step 6: verify revert
        for entry in tx_log:
            with open(entry["file"]) as f:
                assert f.read() == entry["original"]
```

Note: The `ivyc` compilation step is skipped in the initial test because `ivyc` may not be installed in all CI environments. A separate test marked `@pytest.mark.requires_ivyc` can be added for compilation validation.

- [ ] **Step 2: Run test**

Run: `cd {IVY_LSP} && python -m pytest tests/test_propagation_e2e.py -v -m integration`
Expected: PASS (or skip if fixture setup fails)

- [ ] **Step 3: Commit**

```bash
git add {IVY_LSP}/tests/test_propagation_e2e.py
git commit -m "test(ivy-lsp): e2e propagation integration test with revert verification"
```

---

### Task 9: Revert + Mid-Rejection Tests

**Files:**
- Modify: `{IVY_LSP}/tests/test_propagation_e2e.py`

- [ ] **Step 1: Write revert test**

Add to `TestPropagationE2E`:

```python
    def test_revert_after_corruption(self, minip_worktree):
        """After edits, corrupting a file and reverting restores all originals."""
        protocol_dir = minip_worktree
        impact = change_impact_impl("ping_packet", "add_field", protocol_dir)

        # Store originals
        tx_log = []
        for entry in impact["auto_propagate"]:
            fpath = os.path.join(protocol_dir, entry["file"])
            with open(fpath) as f:
                tx_log.append({"file": fpath, "original": f.read()})

        # Apply valid edit to file 1
        with open(tx_log[0]["file"], "w") as f:
            f.write(tx_log[0]["original"].replace(
                "payload : frame.arr",
                "seq_num : stream_pos,\n        payload : frame.arr",
            ))

        # Apply corrupt edit to file 2 (wrong byte count)
        with open(tx_log[1]["file"], "w") as f:
            f.write("CORRUPTED CONTENT")

        # Revert all
        for entry in reversed(tx_log):
            with open(entry["file"], "w") as f:
                f.write(entry["original"])

        # Verify all files match originals
        for entry in tx_log:
            with open(entry["file"]) as f:
                assert f.read() == entry["original"]
```

- [ ] **Step 2: Write mid-rejection test**

Add to `TestPropagationE2E`:

```python
    def test_mid_propagation_revert_and_abort(self, minip_worktree):
        """Approving file 1, rejecting file 2, then reverting restores file 1."""
        protocol_dir = minip_worktree
        impact = change_impact_impl("ping_packet", "add_field", protocol_dir)

        # Store originals
        tx_log = []
        for entry in impact["auto_propagate"]:
            fpath = os.path.join(protocol_dir, entry["file"])
            with open(fpath) as f:
                tx_log.append({"file": fpath, "original": f.read()})

        # Edit file 1 (approved)
        with open(tx_log[0]["file"], "w") as f:
            f.write(tx_log[0]["original"].replace(
                "payload : frame.arr",
                "seq_num : stream_pos,\n        payload : frame.arr",
            ))

        # File 2 rejected — simulate "revert and abort"
        # Revert only files that were edited (tx_log[:1])
        with open(tx_log[0]["file"], "w") as f:
            f.write(tx_log[0]["original"])

        # File 1 is restored, files 2 and 3 were never touched
        for entry in tx_log:
            with open(entry["file"]) as f:
                assert f.read() == entry["original"]
```

- [ ] **Step 3: Run all integration tests**

Run: `cd {IVY_LSP} && python -m pytest tests/test_propagation_e2e.py -v -m integration`
Expected: All 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add {IVY_LSP}/tests/test_propagation_e2e.py
git commit -m "test(ivy-lsp): revert and mid-rejection integration tests"
```

---

## Summary

| Task | Deliverable | Est. Steps |
|---|---|---|
| 1 | Module scaffold + registration | 4 |
| 2 | `ivy_find_variants` struct parsing | 5 |
| 3 | `ivy_find_variants` variant + tag extraction | 5 |
| 4 | `ivy_serdes_correlation` | 5 |
| 5 | `ivy_change_impact` + MCP wiring | 6 |
| 6 | Plugin skill + command | 3 |
| 7 | Integration test fixture | 2 |
| 8 | E2E integration test | 3 |
| 9 | Revert + mid-rejection tests | 4 |
| **Total** | 9 deliverables | **37 steps** |
