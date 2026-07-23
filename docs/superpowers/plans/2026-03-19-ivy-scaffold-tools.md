# Object-Centric Scaffold MCP Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 5 new MCP tools (`ivy_add_object`, `ivy_add_field`, `ivy_add_action`, `ivy_add_monitor`, `ivy_apply_changes`) that provide high-level, object-centric scaffold operations with a two-step preview-then-apply workflow.

**Architecture:** Tools stage changes in an in-memory `StagingSession` and return JSON previews. A separate `ivy_apply_changes` tool atomically writes staged files to disk. Symbol lookup uses the SemanticModel (coarse: file + line) then regex scanning (precise: insertion point within file). Ser/deser updates target C++ state machines inside `<<< impl >>>` blocks.

**Tech Stack:** Python 3.10+, FastMCP, pygls, asyncio, threading, dataclasses, regex

**Base path alias** used throughout:
```
$IVY_LSP = panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
```

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `$IVY_LSP/ivy_lsp/features/scaffold.py` | Data structures, session management, SourceLocator, code generators, orchestrators |
| Create | `$IVY_LSP/ivy_lsp/tools/scaffold.py` | MCP tool registrations (5 tools) |
| Create | `$IVY_LSP/tests/test_tools_scaffold.py` | Unit + integration tests |
| Modify | `$IVY_LSP/ivy_lsp/tools/__init__.py` | Wire scaffold tools, add timeouts + metadata |
| Modify | `$IVY_LSP/ivy_lsp/mcp_server.py` | Update MCP instructions string |

**Reference files (read-only):**
- `$IVY_LSP/ivy_lsp/semantic/model.py` — `get_nodes_by_type()`, `get_node()`
- `$IVY_LSP/ivy_lsp/semantic/nodes.py` — `SymbolNode`, `TypeNode`, `MonitorNode`
- `$IVY_LSP/ivy_lsp/analysis/impl_block_parser.py` — `extract_impl_blocks()`, `parse_enum_states()`, `CPP_ENUM_RE`
- `$IVY_LSP/ivy_lsp/analysis/pattern_library.py` — `OBJECT_RE`, `VARIANT_RE`, `TYPE_STRUCT_RE`, `MONITOR_RE`
- `$IVY_LSP/ivy_lsp/features/patterns.py` — `handle_pattern_scaffold()`, `_load_and_substitute()`
- `$IVY_LSP/ivy_lsp/tools/__init__.py` — `safe_tool`, `error_response()`, `_TOOL_TIMEOUTS`, `_TOOL_METADATA`
- `$IVY_LSP/tests/test_tools_quality.py` — test fixture pattern: `_get_mcp_app()`, `_create_protocol_workspace()`

---

### Task 1: Data Structures and Session Management

**Files:**
- Create: `$IVY_LSP/ivy_lsp/features/scaffold.py`
- Test: `$IVY_LSP/tests/test_tools_scaffold.py`

- [ ] **Step 1: Write failing tests for data structures and session lifecycle**

```python
# tests/test_tools_scaffold.py
"""Tests for object-centric scaffold MCP tools."""
from __future__ import annotations

import time
import pytest

from ivy_lsp.features.scaffold import (
    FileEdit,
    StagingSession,
    TextEdit,
    apply_session,
    create_session,
    get_session,
    _sessions,
    _SESSION_TTL,
)


class TestTextEdit:
    def test_basic_construction(self):
        edit = TextEdit(line=10, col=0, end_line=10, end_col=0, new_text="    foo : bar,\n")
        assert edit.line == 10
        assert edit.new_text == "    foo : bar,\n"


class TestFileEdit:
    def test_create_kind(self):
        fe = FileEdit(file_path="/tmp/test.ivy", kind="create", new_content="object foo = {}")
        assert fe.kind == "create"
        assert fe.new_content == "object foo = {}"
        assert fe.edits == []

    def test_modify_kind(self):
        edit = TextEdit(line=5, col=0, end_line=5, end_col=0, new_text="new line\n")
        fe = FileEdit(file_path="/tmp/test.ivy", kind="modify", edits=[edit])
        assert fe.kind == "modify"
        assert len(fe.edits) == 1


class TestSessionManagement:
    def setup_method(self):
        _sessions.clear()

    def test_create_session(self):
        session = create_session("minip", "ivy_add_object")
        assert session.protocol == "minip"
        assert session.tool_name == "ivy_add_object"
        assert len(session.session_id) > 0
        assert session.session_id in _sessions

    def test_get_session(self):
        session = create_session("minip", "ivy_add_object")
        retrieved = get_session(session.session_id)
        assert retrieved is session

    def test_get_session_not_found(self):
        assert get_session("nonexistent") is None

    def test_session_ttl_expiry(self, monkeypatch):
        session = create_session("minip", "ivy_add_object")
        # Simulate time passing beyond TTL
        monkeypatch.setattr(session, "created_at", time.monotonic() - _SESSION_TTL - 1)
        assert get_session(session.session_id) is None

    def test_apply_session_creates_file(self, tmp_path):
        session = create_session("minip", "ivy_add_object")
        target = str(tmp_path / "test.ivy")
        session.file_edits.append(
            FileEdit(file_path=target, kind="create", new_content="#lang ivy1.7\n\nobject foo = {}\n")
        )
        result = apply_session(session.session_id)
        assert result["success"] is True
        assert (tmp_path / "test.ivy").read_text() == "#lang ivy1.7\n\nobject foo = {}\n"
        # Session consumed after apply
        assert get_session(session.session_id) is None

    def test_apply_session_modifies_file(self, tmp_path):
        # Create a file to modify
        target = tmp_path / "existing.ivy"
        target.write_text("line0\nline1\nline2\nline3\n")
        session = create_session("minip", "ivy_add_field")
        edit = TextEdit(line=2, col=0, end_line=2, end_col=0, new_text="inserted\n")
        session.file_edits.append(
            FileEdit(file_path=str(target), kind="modify", edits=[edit])
        )
        result = apply_session(session.session_id)
        assert result["success"] is True
        lines = target.read_text().splitlines()
        assert "inserted" in lines

    def test_apply_expired_session(self, monkeypatch):
        session = create_session("minip", "ivy_add_object")
        monkeypatch.setattr(session, "created_at", time.monotonic() - _SESSION_TTL - 1)
        result = apply_session(session.session_id)
        assert result["success"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestTextEdit -v 2>&1 | head -20`
Expected: FAIL — `ModuleNotFoundError: No module named 'ivy_lsp.features.scaffold'`

- [ ] **Step 3: Implement data structures and session management**

```python
# ivy_lsp/features/scaffold.py
"""Object-centric scaffold operations for Ivy specifications.

Provides data structures, session management, source location,
code generation, and orchestration for the ivy_add_* MCP tools.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TextEdit:
    """A single text insertion/replacement within a file.

    For pure insertions, set end_line=line, end_col=col (zero-width range).
    """

    line: int  # 0-based
    col: int  # 0-based
    end_line: int
    end_col: int
    new_text: str


@dataclass
class FileEdit:
    """A staged edit to a single file."""

    file_path: str  # Absolute path
    kind: Literal["create", "modify"]
    new_content: Optional[str] = None  # For "create"
    edits: List[TextEdit] = field(default_factory=list)  # For "modify"


@dataclass
class StagingSession:
    """A set of staged file changes awaiting apply."""

    session_id: str
    created_at: float  # time.monotonic()
    protocol: str
    tool_name: str
    file_edits: List[FileEdit] = field(default_factory=list)
    preview: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

_sessions: Dict[str, StagingSession] = {}
_sessions_lock = threading.Lock()
_SESSION_TTL: float = 300.0  # 5 minutes


def _cleanup_expired() -> None:
    """Remove expired sessions. Caller must hold _sessions_lock."""
    now = time.monotonic()
    expired = [
        sid for sid, s in _sessions.items() if now - s.created_at > _SESSION_TTL
    ]
    for sid in expired:
        del _sessions[sid]


def create_session(protocol: str, tool_name: str) -> StagingSession:
    """Create and register a new staging session."""
    session = StagingSession(
        session_id=uuid.uuid4().hex[:12],
        created_at=time.monotonic(),
        protocol=protocol,
        tool_name=tool_name,
    )
    with _sessions_lock:
        _cleanup_expired()
        _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> Optional[StagingSession]:
    """Retrieve a session by ID, or None if expired/missing."""
    with _sessions_lock:
        _cleanup_expired()
        return _sessions.get(session_id)


def apply_session(session_id: str) -> Dict[str, Any]:
    """Apply staged changes to disk and consume the session.

    Returns dict with success, files_written, and suggested_next_tools.
    """
    with _sessions_lock:
        _cleanup_expired()
        session = _sessions.pop(session_id, None)

    if session is None:
        return {"success": False, "message": f"Session '{session_id}' not found or expired"}

    files_written: List[Dict[str, str]] = []
    try:
        for fe in session.file_edits:
            if fe.kind == "create":
                os.makedirs(os.path.dirname(fe.file_path), exist_ok=True)
                with open(fe.file_path, "w") as f:
                    f.write(fe.new_content or "")
                files_written.append({"path": fe.file_path, "kind": "created"})

            elif fe.kind == "modify":
                with open(fe.file_path) as f:
                    lines = f.readlines()

                # Apply edits in reverse line order to preserve positions
                for edit in sorted(fe.edits, key=lambda e: (e.line, e.col), reverse=True):
                    if edit.line == edit.end_line and edit.col == edit.end_col:
                        # Pure insertion
                        lines.insert(edit.line, edit.new_text)
                    else:
                        # Replacement (line-level granularity)
                        lines[edit.line : edit.end_line] = [edit.new_text]

                with open(fe.file_path, "w") as f:
                    f.writelines(lines)
                files_written.append({"path": fe.file_path, "kind": "modified"})

    except OSError as exc:
        return {"success": False, "message": f"File write error: {exc}"}

    return {
        "success": True,
        "files_written": files_written,
        "suggested_next_tools": ["ivy_verify"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py -k "TestTextEdit or TestFileEdit or TestSessionManagement" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/features/scaffold.py tests/test_tools_scaffold.py
git commit -m "feat(scaffold): add data structures and session management for preview-apply workflow"
```

---

### Task 2: SourceLocator

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/features/scaffold.py`
- Modify: `$IVY_LSP/tests/test_tools_scaffold.py`

**Reference:** Real Ivy files for test fixtures:
- `protocol-testing/apt/apt_protocols/minip/minip_stack/ping_frame.ivy` — object/variant structure
- `protocol-testing/apt/apt_protocols/minip/minip_utils/ping_ser.ivy` — C++ impl blocks

- [ ] **Step 1: Write failing tests for SourceLocator**

```python
# Add to tests/test_tools_scaffold.py

from ivy_lsp.features.scaffold import SourceLocator

# Minimal Ivy source fixtures
FRAME_SOURCE = """\
#lang ivy1.7

include order

object ping_frame = {
    type this

    object ping = {
        variant this of ping_frame = struct {
            data : stream_data
        }
    }

    object pong = {
        variant this of ping_frame = struct {
            data : stream_data
        }
    }

    action handle(f:this, dst:ip.endpoint)

    instance idx : unbounded_sequence
    instance arr : array(idx, this)
}
"""

SER_SOURCE = """\
#lang ivy1.7

object ping_ser = {}
<<< impl
class ping_ser : public ivy_binary_ser_128 {
    enum {
        ping_s_init,
        ping_s_frame,
        ping_s_payload
    } state;
    int frame_type;
    virtual void set(int128_t res) {
        switch (state) {
            case ping_s_frame:
                setn(res, 1);
                break;
            default:
                throw deser_err();
        }
    }
    virtual void open_tag(int tag, const std::string &) {
        if (state == ping_s_payload || state == ping_s_init) {
            int sz = 1;
            if (tag == 0) {
                frame_type = 0x01;
                state = ping_s_frame;
            }
            else {
                throw deser_err();
            }
            setn(frame_type, sz);
            return;
        }
        throw deser_err();
    }
};
>>>
"""

INCLUDE_SOURCE = """\
#lang ivy1.7

include order
include collections
include ping_frame

object test_spec = {}
"""


class TestSourceLocator:
    def test_find_object_body_end(self):
        loc = SourceLocator(FRAME_SOURCE, "ping_frame.ivy")
        end_line = loc.find_object_body_end("ping_frame")
        assert end_line is not None
        lines = FRAME_SOURCE.splitlines()
        assert lines[end_line].strip() == "}"

    def test_find_object_body_end_not_found(self):
        loc = SourceLocator(FRAME_SOURCE, "ping_frame.ivy")
        assert loc.find_object_body_end("nonexistent") is None

    def test_find_struct_body_end(self):
        loc = SourceLocator(FRAME_SOURCE, "ping_frame.ivy")
        end_line = loc.find_struct_body_end("ping")
        assert end_line is not None
        lines = FRAME_SOURCE.splitlines()
        # Should point to closing brace of struct
        assert "}" in lines[end_line]

    def test_find_last_include(self):
        loc = SourceLocator(INCLUDE_SOURCE, "test.ivy")
        line = loc.find_last_include()
        assert line is not None
        lines = INCLUDE_SOURCE.splitlines()
        assert "include ping_frame" in lines[line]

    def test_find_impl_block(self):
        loc = SourceLocator(SER_SOURCE, "ping_ser.ivy")
        block = loc.find_impl_block()
        assert block is not None
        assert block.start_offset > 0
        assert "ping_ser" in block.content

    def test_find_enum_states(self):
        loc = SourceLocator(SER_SOURCE, "ping_ser.ivy")
        states = loc.find_enum_states()
        assert "ping_s_init" in states
        assert "ping_s_frame" in states
        assert "ping_s_payload" in states

    def test_count_variant_tags(self):
        loc = SourceLocator(FRAME_SOURCE, "ping_frame.ivy")
        count = loc.count_variants("ping_frame")
        assert count == 2  # ping, pong

    def test_find_switch_case_insertion_point(self):
        loc = SourceLocator(SER_SOURCE, "ping_ser.ivy")
        line = loc.find_switch_case_insertion_point("set")
        assert line is not None
        lines = SER_SOURCE.splitlines()
        # Should be before "default:"
        assert "default" in lines[line] or "default" in lines[line + 1]

    def test_find_open_tag_insertion_point(self):
        loc = SourceLocator(SER_SOURCE, "ping_ser.ivy")
        line = loc.find_open_tag_insertion_point()
        assert line is not None
        lines = SER_SOURCE.splitlines()
        # Should be before the else/throw block
        assert "else" in lines[line] or "throw" in lines[line + 1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestSourceLocator::test_find_object_body_end -v 2>&1 | head -20`
Expected: FAIL — `ImportError: cannot import name 'SourceLocator'`

- [ ] **Step 3: Implement SourceLocator**

Add to `ivy_lsp/features/scaffold.py`:

```python
import re
from ivy_lsp.analysis.impl_block_parser import (
    ImplBlock,
    extract_impl_blocks,
    parse_enum_states,
    IMPL_BLOCK_RE,
)

# Regex patterns reused from pattern_library
_OBJECT_RE = re.compile(r"^\s*object\s+(\w+)\s*=\s*\{", re.MULTILINE)
_VARIANT_RE = re.compile(
    r"^\s*variant\s+this\s+of\s+(\w+)\s*=\s*struct\s*\{", re.MULTILINE
)
_INCLUDE_RE = re.compile(r"^\s*include\s+(\S+)", re.MULTILINE)
_STRUCT_RE = re.compile(
    r"^\s*(?:variant\s+this\s+of\s+\w+|type\s+this)\s*=\s*struct\s*\{", re.MULTILINE
)


class SourceLocator:
    """Find insertion points in Ivy source files.

    Uses brace-depth counting with impl-block skipping for accurate
    positioning in files that mix Ivy and embedded C++.
    """

    def __init__(self, source: str, filepath: str) -> None:
        self._source = source
        self._filepath = filepath
        self._lines = source.splitlines(keepends=True)

        # Pre-compute impl block ranges (line-based) to skip during
        # Ivy brace counting
        self._impl_ranges: List[tuple[int, int]] = []
        for m in IMPL_BLOCK_RE.finditer(source):
            start_line = source[:m.start()].count("\n")
            end_line = source[:m.end()].count("\n")
            self._impl_ranges.append((start_line, end_line))

    def _in_impl_block(self, line_num: int) -> bool:
        """Check if a line is inside a <<< impl >>> block."""
        return any(s <= line_num <= e for s, e in self._impl_ranges)

    def find_object_body_end(self, object_name: str) -> Optional[int]:
        """Find the closing brace line of 'object {name} = { ... }'.

        Returns 0-based line number, or None if not found.
        Finds the FIRST (declaration) block for the object.
        """
        pattern = re.compile(
            rf"^\s*object\s+{re.escape(object_name)}\s*=\s*\{{", re.MULTILINE
        )
        m = pattern.search(self._source)
        if not m:
            return None

        start_line = self._source[:m.end()].count("\n")
        depth = 1
        for i in range(start_line + 1, len(self._lines)):
            if self._in_impl_block(i):
                continue
            for ch in self._lines[i]:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return i
        return None

    def find_struct_body_end(self, nested_object_name: str) -> Optional[int]:
        """Find closing brace of struct inside a nested object.

        Looks for 'object {name} = {' then finds the struct inside it.
        """
        obj_pattern = re.compile(
            rf"^\s*object\s+{re.escape(nested_object_name)}\s*=\s*\{{", re.MULTILINE
        )
        m = obj_pattern.search(self._source)
        if not m:
            return None

        # Search for struct within this object
        obj_start = m.end()
        struct_m = _STRUCT_RE.search(self._source, obj_start)
        if not struct_m:
            return None

        start_line = self._source[:struct_m.end()].count("\n")
        depth = 1
        for i in range(start_line + 1, len(self._lines)):
            if self._in_impl_block(i):
                continue
            for ch in self._lines[i]:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return i
        return None

    def find_last_include(self) -> Optional[int]:
        """Find the line of the last 'include ...' directive."""
        last = None
        for m in _INCLUDE_RE.finditer(self._source):
            last = self._source[:m.start()].count("\n")
        return last

    def find_impl_block(self) -> Optional[ImplBlock]:
        """Find the first <<< impl >>> block."""
        blocks = extract_impl_blocks(self._source)
        return blocks[0] if blocks else None

    def find_enum_states(self) -> List[str]:
        """Find enum state names in the first impl block."""
        block = self.find_impl_block()
        if not block:
            return []
        enums = parse_enum_states(block.content)
        if not enums:
            return []
        return enums[0].states

    def count_variants(self, parent_object: str) -> int:
        """Count existing variant declarations for a parent object."""
        pattern = re.compile(
            rf"variant\s+this\s+of\s+{re.escape(parent_object)}\s*=", re.MULTILINE
        )
        return len(pattern.findall(self._source))

    def find_switch_case_insertion_point(self, method: str) -> Optional[int]:
        """Find line before 'default:' in switch/case within an impl block.

        Returns 0-based line number in the full source.
        """
        block = self.find_impl_block()
        if not block:
            return None

        # Find the method, then find its switch/case default
        block_start_line = block.line
        in_method = False
        for i, line_text in enumerate(self._lines):
            if i < block_start_line:
                continue
            if i > block_start_line + block.content.count("\n") + 2:
                break
            stripped = line_text.strip()
            if method in stripped and "void" in stripped:
                in_method = True
            if in_method and stripped.startswith("default"):
                return i
        return None

    def find_open_tag_insertion_point(self) -> Optional[int]:
        """Find insertion line before the else/throw in open_tag().

        Returns 0-based line number for inserting a new 'else if (tag == N)' branch.
        """
        block = self.find_impl_block()
        if not block:
            return None

        block_start_line = block.line
        in_open_tag = False
        last_tag_block_end = None

        for i, line_text in enumerate(self._lines):
            if i < block_start_line:
                continue
            if i > block_start_line + block.content.count("\n") + 2:
                break
            stripped = line_text.strip()
            if "open_tag" in stripped and "void" in stripped:
                in_open_tag = True
            if in_open_tag:
                # Track the last 'else if (tag ==' or 'if (tag ==' closing brace
                if stripped.startswith("else if (tag ==") or (
                    stripped.startswith("if (tag ==") and "state ==" not in stripped
                ):
                    last_tag_block_end = None
                if last_tag_block_end is None and stripped == "}":
                    last_tag_block_end = i
                # The final else { throw ... } is our target
                if stripped.startswith("else") and "tag" not in stripped:
                    return i
        return last_tag_block_end
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestSourceLocator -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/features/scaffold.py tests/test_tools_scaffold.py
git commit -m "feat(scaffold): add SourceLocator for AST-aware insertion point finding"
```

---

### Task 3: Code Generators — Object, Variant, Ser/Deser

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/features/scaffold.py`
- Modify: `$IVY_LSP/tests/test_tools_scaffold.py`

- [ ] **Step 1: Write failing tests for code generators**

```python
# Add to tests/test_tools_scaffold.py

from ivy_lsp.features.scaffold import (
    generate_object_declaration,
    generate_variant_entry,
    generate_ser_state_additions,
    generate_deser_state_additions,
    TYPE_TO_BYTES,
)


class TestGenerateObjectDeclaration:
    def test_basic_object(self):
        code = generate_object_declaration("minip", "keepalive", [("interval", "milliseconds"), ("timeout", "pkt_num")])
        assert "object keepalive" in code
        assert "type this = struct" in code or "variant this" in code
        assert "interval : milliseconds" in code
        assert "timeout : pkt_num" in code

    def test_empty_fields(self):
        code = generate_object_declaration("minip", "empty", [])
        assert "object empty" in code


class TestGenerateVariantEntry:
    def test_variant_with_fields(self):
        code = generate_variant_entry("minip", "ping_frame", "keepalive", [("interval", "milliseconds")])
        assert "object keepalive" in code
        assert "variant this of ping_frame" in code
        assert "interval : milliseconds" in code


class TestGenerateSerStateAdditions:
    def test_basic_field(self):
        result = generate_ser_state_additions(
            protocol="minip",
            field_name="interval",
            field_type="milliseconds",
            byte_width=8,
            tag_index=3,
            wire_code=0x04,
        )
        assert "enum_state" in result
        assert "minip_s_interval" in result["enum_state"]
        assert "set_case" in result
        assert "setn(res, 8)" in result["set_case"]
        assert "open_tag_branch" in result
        assert "tag == 3" in result["open_tag_branch"]
        assert "0x04" in result["open_tag_branch"] or "0x4" in result["open_tag_branch"]

    def test_type_to_bytes_lookup(self):
        assert TYPE_TO_BYTES["milliseconds"] == 8
        assert TYPE_TO_BYTES["bool"] == 1
        assert TYPE_TO_BYTES["version"] == 4


class TestGenerateDeserStateAdditions:
    def test_basic_field(self):
        result = generate_deser_state_additions(
            protocol="minip",
            field_name="interval",
            field_type="milliseconds",
            byte_width=8,
            tag_index=3,
            wire_code=0x04,
        )
        assert "enum_state" in result
        assert "minip_s_interval" in result["enum_state"]
        assert "get_case" in result
        assert "getn(res, 8)" in result["get_case"]
        assert "open_tag_branch" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestGenerateObjectDeclaration -v 2>&1 | head -20`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement code generators**

Add to `ivy_lsp/features/scaffold.py`:

```python
# ---------------------------------------------------------------------------
# Type-to-byte-width registry for ser/deser generation
# ---------------------------------------------------------------------------

TYPE_TO_BYTES: Dict[str, int] = {
    "bool": 1,
    "bit": 1,
    "stream_kind": 1,
    "type_bits": 1,
    "cid_length": 1,
    "port": 1,
    "error_code": 2,
    "version": 4,
    "reset_token": 4,
    "pkt_num": 8,
    "cid": 8,
    "microseconds": 8,
    "milliseconds": 8,
    "seconds": 8,
}

_DEFAULT_BYTE_WIDTH: int = 4


def _get_byte_width(field_type: str) -> tuple[int, bool]:
    """Return (byte_width, is_known) for a field type."""
    width = TYPE_TO_BYTES.get(field_type)
    if width is not None:
        return width, True
    return _DEFAULT_BYTE_WIDTH, False


# ---------------------------------------------------------------------------
# Code generators — pure functions returning Ivy/C++ source strings
# ---------------------------------------------------------------------------


def generate_object_declaration(
    protocol: str,
    name: str,
    fields: List[tuple[str, str]],
) -> str:
    """Generate an Ivy object declaration with a struct type.

    Returns a standalone object block like:
        object keepalive = {
            type this = struct {
                interval : milliseconds,
                timeout : pkt_num
            }
        }
    """
    if not fields:
        return f"object {name} = {{\n    type this = struct {{\n    }}\n}}\n"

    field_lines = []
    for i, (fname, ftype) in enumerate(fields):
        comma = "," if i < len(fields) - 1 else ""
        field_lines.append(f"        {fname} : {ftype}{comma}")

    fields_block = "\n".join(field_lines)
    return (
        f"object {name} = {{\n"
        f"    type this = struct {{\n"
        f"{fields_block}\n"
        f"    }}\n"
        f"}}\n"
    )


def generate_variant_entry(
    protocol: str,
    parent: str,
    name: str,
    fields: List[tuple[str, str]],
) -> str:
    """Generate a variant object nested inside a parent frame.

    Returns:
        object keepalive = {
            variant this of ping_frame = struct {
                interval : milliseconds
            }
        }
    """
    if not fields:
        return (
            f"object {name} = {{\n"
            f"    variant this of {parent} = struct {{\n"
            f"    }}\n"
            f"}}\n"
        )

    field_lines = []
    for i, (fname, ftype) in enumerate(fields):
        comma = "," if i < len(fields) - 1 else ""
        field_lines.append(f"        {fname} : {ftype}{comma}")

    fields_block = "\n".join(field_lines)
    return (
        f"object {name} = {{\n"
        f"    variant this of {parent} = struct {{\n"
        f"{fields_block}\n"
        f"    }}\n"
        f"}}\n"
    )


def generate_ser_state_additions(
    protocol: str,
    field_name: str,
    field_type: str,
    byte_width: int,
    tag_index: int,
    wire_code: int,
) -> Dict[str, str]:
    """Generate C++ snippets for serializer updates.

    Returns dict with keys:
        - enum_state: new enum entry (e.g., "ping_s_interval,")
        - set_case: new switch case in set() method
        - open_tag_branch: new else-if in open_tag()
    """
    state_name = f"{protocol}_s_{field_name}"
    return {
        "enum_state": f"        {state_name},",
        "set_case": (
            f"            case {state_name}:\n"
            f"                setn(res, {byte_width});\n"
            f"                break;"
        ),
        "open_tag_branch": (
            f"            else if (tag == {tag_index}) {{\n"
            f"                frame_type = 0x{wire_code:02x};\n"
            f"                state = {state_name};\n"
            f"            }}"
        ),
    }


def generate_deser_state_additions(
    protocol: str,
    field_name: str,
    field_type: str,
    byte_width: int,
    tag_index: int,
    wire_code: int,
) -> Dict[str, str]:
    """Generate C++ snippets for deserializer updates.

    Mirror of generate_ser_state_additions with getn instead of setn.
    """
    state_name = f"{protocol}_s_{field_name}"
    return {
        "enum_state": f"        {state_name},",
        "get_case": (
            f"            case {state_name}:\n"
            f"                getn(res, {byte_width});\n"
            f"                break;"
        ),
        "open_tag_branch": (
            f"            else if (tag == {tag_index}) {{\n"
            f"                frame_type = 0x{wire_code:02x};\n"
            f"                state = {state_name};\n"
            f"            }}"
        ),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py -k "Generate" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/features/scaffold.py tests/test_tools_scaffold.py
git commit -m "feat(scaffold): add code generators for objects, variants, and ser/deser"
```

---

### Task 4: Code Generators — Action and Monitor

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/features/scaffold.py`
- Modify: `$IVY_LSP/tests/test_tools_scaffold.py`

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_tools_scaffold.py

from ivy_lsp.features.scaffold import (
    generate_action_declaration,
    generate_monitor_block,
)


class TestGenerateActionDeclaration:
    def test_basic_action(self):
        code = generate_action_declaration(
            "minip", "ping_frame", "handle_keepalive",
            [("f", "ping_frame.keepalive"), ("dst", "ip.endpoint")]
        )
        assert "action handle_keepalive" in code
        assert "f:ping_frame.keepalive" in code
        assert "dst:ip.endpoint" in code

    def test_no_params(self):
        code = generate_action_declaration("minip", "ping_frame", "reset", [])
        assert "action reset" in code


class TestGenerateMonitorBlock:
    def test_before_monitor(self):
        code = generate_monitor_block("minip", "ping_frame.handle", "before", "_generating")
        assert "before" in code
        assert "ping_frame.handle" in code
        assert "_generating" in code

    def test_after_monitor(self):
        code = generate_monitor_block("minip", "ping_frame.handle", "after", "_generating")
        assert "after" in code

    def test_around_monitor(self):
        code = generate_monitor_block("minip", "ping_frame.handle", "around", "_generating")
        assert "around" in code
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestGenerateActionDeclaration -v 2>&1 | head -20`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement action and monitor generators**

Add to `ivy_lsp/features/scaffold.py`:

```python
def generate_action_declaration(
    protocol: str,
    object_name: str,
    action_name: str,
    params: List[tuple[str, str]],
) -> str:
    """Generate an Ivy action declaration.

    Returns:
        action handle_keepalive(f:ping_frame.keepalive, dst:ip.endpoint)
    """
    if params:
        param_str = ", ".join(f"{pname}:{ptype}" for pname, ptype in params)
        return f"    action {action_name}({param_str})\n"
    return f"    action {action_name}\n"


def generate_monitor_block(
    protocol: str,
    action_name: str,
    kind: str,
    guard: str,
) -> str:
    """Generate a before/after/around monitor block.

    Returns:
        before ping_frame.handle {
            if _generating {
                # AUTO-GENERATED monitor
            }
        }
    """
    return (
        f"{kind} {action_name} {{\n"
        f"    if {guard} {{\n"
        f"        # AUTO-GENERATED monitor — add constraints here\n"
        f"    }}\n"
        f"}}\n"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py -k "Action or Monitor" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/features/scaffold.py tests/test_tools_scaffold.py
git commit -m "feat(scaffold): add action and monitor code generators"
```

---

### Task 5: plan_add_object Orchestrator

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/features/scaffold.py`
- Modify: `$IVY_LSP/tests/test_tools_scaffold.py`

- [ ] **Step 1: Write failing tests for plan_add_object**

```python
# Add to tests/test_tools_scaffold.py
import os

from ivy_lsp.features.scaffold import plan_add_object


def _create_minip_workspace(tmp_path):
    """Create a minimal minip protocol workspace for testing."""
    proto_dir = tmp_path / "protocol-testing" / "minip" / "minip_stack"
    proto_dir.mkdir(parents=True)
    utils_dir = tmp_path / "protocol-testing" / "minip" / "minip_utils"
    utils_dir.mkdir(parents=True)

    # Frame file with existing variants
    (proto_dir / "ping_frame.ivy").write_text(FRAME_SOURCE)
    # Serializer
    (utils_dir / "ping_ser.ivy").write_text(SER_SOURCE)

    return str(tmp_path / "protocol-testing")


class TestPlanAddObject:
    def test_creates_object_file(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_object(
            root=root,
            model=None,  # No model needed for file creation
            protocol="minip",
            name="keepalive",
            fields=[("interval", "milliseconds"), ("timeout", "pkt_num")],
            with_serdes=False,
            with_variant=False,
        )
        assert session is not None
        assert len(session.file_edits) >= 1
        create_edits = [fe for fe in session.file_edits if fe.kind == "create"]
        assert len(create_edits) >= 1
        assert "keepalive" in create_edits[0].new_content

    def test_with_variant_adds_modify_edit(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_object(
            root=root,
            model=None,
            protocol="minip",
            name="keepalive",
            fields=[("interval", "milliseconds")],
            with_serdes=False,
            with_variant=True,
        )
        modify_edits = [fe for fe in session.file_edits if fe.kind == "modify"]
        # Should modify frame file to add variant
        assert any("ping_frame" in fe.file_path for fe in modify_edits)

    def test_with_serdes_generates_state_updates(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_object(
            root=root,
            model=None,
            protocol="minip",
            name="keepalive",
            fields=[("interval", "milliseconds")],
            with_serdes=True,
            with_variant=True,
        )
        # Should have edits for ser file
        ser_edits = [fe for fe in session.file_edits if "ser" in fe.file_path]
        assert len(ser_edits) >= 1

    def test_preview_populated(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_object(
            root=root,
            model=None,
            protocol="minip",
            name="keepalive",
            fields=[("interval", "milliseconds")],
            with_serdes=False,
            with_variant=False,
        )
        assert session.preview.get("success") is True
        assert "changes" in session.preview
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestPlanAddObject::test_creates_object_file -v 2>&1 | head -20`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement plan_add_object**

Add to `ivy_lsp/features/scaffold.py`:

```python
import glob as glob_module


def _find_protocol_files(root: str, protocol: str) -> Dict[str, str]:
    """Find key protocol files by scanning the workspace.

    Returns dict with keys: "frame", "ser", "deser", "stack_dir", "utils_dir"
    """
    result: Dict[str, str] = {}
    # Search for frame file (contains 'type this' + variants)
    for path in glob_module.glob(os.path.join(root, "**", f"*frame*.ivy"), recursive=True):
        if protocol in path.lower() or protocol in os.path.basename(os.path.dirname(path)).lower():
            result["frame"] = path
            break

    # Search for ser/deser files
    for path in glob_module.glob(os.path.join(root, "**", f"*ser*.ivy"), recursive=True):
        basename = os.path.basename(path)
        if "deser" in basename:
            result["deser"] = path
        elif "ser" in basename:
            result["ser"] = path

    # Determine directories
    if "frame" in result:
        result["stack_dir"] = os.path.dirname(result["frame"])
    if "ser" in result:
        result["utils_dir"] = os.path.dirname(result["ser"])

    return result


def _build_preview(
    session: StagingSession,
    summary: str,
    warnings: Optional[List[str]] = None,
) -> None:
    """Populate session.preview with a JSON-serializable summary."""
    changes = []
    for fe in session.file_edits:
        change: Dict[str, Any] = {
            "file": fe.file_path,
            "kind": fe.kind,
        }
        if fe.kind == "create":
            preview_lines = (fe.new_content or "").splitlines()[:20]
            change["preview_lines"] = [f"+ {l}" for l in preview_lines]
            change["description"] = f"Create {os.path.basename(fe.file_path)}"
        else:
            change["edits_count"] = len(fe.edits)
            change["preview_lines"] = [
                f"+ {e.new_text.rstrip()}" for e in fe.edits[:10]
            ]
            change["description"] = f"Modify {os.path.basename(fe.file_path)}"
        changes.append(change)

    session.preview = {
        "success": True,
        "session_id": session.session_id,
        "tool": session.tool_name,
        "protocol": session.protocol,
        "summary": summary,
        "changes": changes,
        "warnings": warnings or [],
        "apply_command": f"ivy_apply_changes(session_id='{session.session_id}')",
    }


def plan_add_object(
    root: str,
    model: Any,
    protocol: str,
    name: str,
    fields: List[tuple[str, str]],
    with_serdes: bool,
    with_variant: bool,
) -> StagingSession:
    """Plan all file changes for adding a new Ivy object.

    Orchestrates:
    1. Create object declaration file (or variant entry if with_variant)
    2. Optionally modify ser/deser files (if with_serdes)
    3. Optionally modify frame file (if with_variant)
    4. Update include chain if new files created
    """
    session = create_session(protocol, "ivy_add_object")
    warnings: List[str] = []

    proto_files = _find_protocol_files(root, protocol)
    stack_dir = proto_files.get("stack_dir", os.path.join(root, protocol, f"{protocol}_stack"))

    # 1. Generate object declaration
    if with_variant and "frame" in proto_files:
        # Add as variant entry inside existing frame file
        frame_path = proto_files["frame"]
        source = open(frame_path).read()
        loc = SourceLocator(source, frame_path)

        # Find parent frame object name
        frame_basename = os.path.splitext(os.path.basename(frame_path))[0]
        parent_name = frame_basename  # e.g., "ping_frame"

        # Find insertion point (before closing brace of frame object)
        end_line = loc.find_object_body_end(parent_name)
        if end_line is not None:
            # Indent variant at object nesting level (4 spaces)
            raw = generate_variant_entry(protocol, parent_name, name, fields)
            variant_code = "\n    # AUTO-GENERATED\n" + "".join(
                f"    {line}\n" if line.strip() else "\n"
                for line in raw.splitlines()
            )
            session.file_edits.append(FileEdit(
                file_path=frame_path,
                kind="modify",
                edits=[TextEdit(
                    line=end_line, col=0, end_line=end_line, end_col=0,
                    new_text=variant_code,
                )],
            ))
        else:
            warnings.append(f"Could not find frame object body end in {frame_path}")
    else:
        # Create standalone object file
        object_code = f"#lang ivy1.7\n\n{generate_object_declaration(protocol, name, fields)}"
        target_path = os.path.join(stack_dir, f"{protocol}_{name}.ivy")
        session.file_edits.append(FileEdit(
            file_path=target_path,
            kind="create",
            new_content=object_code,
        ))

    # 2. Optionally update ser/deser
    if with_serdes and fields:
        tag_index = 0
        if with_variant and "frame" in proto_files:
            frame_source = open(proto_files["frame"]).read()
            frame_loc = SourceLocator(frame_source, proto_files["frame"])
            frame_basename = os.path.splitext(os.path.basename(proto_files["frame"]))[0]
            tag_index = frame_loc.count_variants(frame_basename)

        wire_code = tag_index + 1  # Simple 1-based wire code

        for ser_key in ("ser", "deser"):
            if ser_key not in proto_files:
                warnings.append(f"No {ser_key} file found — skipping {ser_key} updates")
                continue

            ser_path = proto_files[ser_key]
            ser_source = open(ser_path).read()
            ser_loc = SourceLocator(ser_source, ser_path)

            edits: List[TextEdit] = []

            # For each field, generate state additions
            for fname, ftype in fields:
                byte_width, known = _get_byte_width(ftype)
                if not known:
                    warnings.append(f"Unknown type '{ftype}' for field '{fname}' — using {byte_width} bytes")

                if ser_key == "ser":
                    additions = generate_ser_state_additions(
                        protocol, fname, ftype, byte_width, tag_index, wire_code,
                    )
                else:
                    additions = generate_deser_state_additions(
                        protocol, fname, ftype, byte_width, tag_index, wire_code,
                    )

                # Add enum state
                existing_states = ser_loc.find_enum_states()
                if existing_states:
                    # Find the last enum state line and insert after it
                    last_state = existing_states[-1]
                    for line_idx, line_text in enumerate(ser_source.splitlines()):
                        if last_state in line_text:
                            edits.append(TextEdit(
                                line=line_idx + 1, col=0,
                                end_line=line_idx + 1, end_col=0,
                                new_text=additions["enum_state"] + "\n",
                            ))
                            break

                # Add set/get case
                case_key = "set_case" if ser_key == "ser" else "get_case"
                case_line = ser_loc.find_switch_case_insertion_point(
                    "set" if ser_key == "ser" else "get"
                )
                if case_line is not None:
                    edits.append(TextEdit(
                        line=case_line, col=0,
                        end_line=case_line, end_col=0,
                        new_text=additions[case_key] + "\n",
                    ))

            # Add open_tag branch (once per variant, not per field)
            tag_line = ser_loc.find_open_tag_insertion_point()
            if tag_line is not None and fields:
                first_field = fields[0]
                byte_width, _ = _get_byte_width(first_field[1])
                if ser_key == "ser":
                    branch = generate_ser_state_additions(
                        protocol, first_field[0], first_field[1], byte_width, tag_index, wire_code,
                    )["open_tag_branch"]
                else:
                    branch = generate_deser_state_additions(
                        protocol, first_field[0], first_field[1], byte_width, tag_index, wire_code,
                    )["open_tag_branch"]
                edits.append(TextEdit(
                    line=tag_line, col=0,
                    end_line=tag_line, end_col=0,
                    new_text=branch + "\n",
                ))

            if edits:
                session.file_edits.append(FileEdit(
                    file_path=ser_path,
                    kind="modify",
                    edits=edits,
                ))

    # 3. Build preview
    summary_parts = [f"Add object '{name}' with {len(fields)} field(s)"]
    if with_variant:
        summary_parts.append("variant entry")
    if with_serdes:
        summary_parts.append("ser/deser updates")
    _build_preview(session, ", ".join(summary_parts), warnings)

    return session
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestPlanAddObject -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/features/scaffold.py tests/test_tools_scaffold.py
git commit -m "feat(scaffold): add plan_add_object orchestrator"
```

---

### Task 6: plan_add_field Orchestrator

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/features/scaffold.py`
- Modify: `$IVY_LSP/tests/test_tools_scaffold.py`

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_tools_scaffold.py

from ivy_lsp.features.scaffold import plan_add_field


class TestPlanAddField:
    def test_inserts_field_into_struct(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_field(
            root=root,
            model=None,
            protocol="minip",
            object_name="ping",
            field_name="sequence_num",
            field_type="pkt_num",
        )
        assert session is not None
        modify_edits = [fe for fe in session.file_edits if fe.kind == "modify"]
        assert len(modify_edits) >= 1
        # Should have edit containing the field
        all_new_text = " ".join(e.new_text for fe in modify_edits for e in fe.edits)
        assert "sequence_num" in all_new_text

    def test_error_when_object_not_found(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_field(
            root=root,
            model=None,
            protocol="minip",
            object_name="nonexistent",
            field_name="foo",
            field_type="bar",
        )
        assert session.preview.get("success") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestPlanAddField -v 2>&1 | head -20`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement plan_add_field**

Add to `ivy_lsp/features/scaffold.py`:

```python
def _find_object_in_workspace(root: str, protocol: str, object_name: str) -> Optional[tuple[str, str]]:
    """Find an object by name in the protocol workspace.

    Returns (file_path, source) or None.
    """
    pattern = os.path.join(root, "**", "*.ivy")
    obj_re = re.compile(rf"^\s*object\s+{re.escape(object_name)}\s*=\s*\{{", re.MULTILINE)
    for path in sorted(glob_module.glob(pattern, recursive=True)):
        try:
            source = open(path).read()
        except OSError:
            continue
        if obj_re.search(source):
            return path, source
    return None


def plan_add_field(
    root: str,
    model: Any,
    protocol: str,
    object_name: str,
    field_name: str,
    field_type: str,
) -> StagingSession:
    """Plan adding a field to an existing object's struct."""
    session = create_session(protocol, "ivy_add_field")
    warnings: List[str] = []

    # Find the object
    found = _find_object_in_workspace(root, protocol, object_name)
    if found is None:
        session.preview = {
            "success": False,
            "message": f"Object '{object_name}' not found in protocol '{protocol}'",
        }
        return session

    file_path, source = found
    loc = SourceLocator(source, file_path)

    # Find struct body end for insertion
    struct_end = loc.find_struct_body_end(object_name)
    if struct_end is None:
        session.preview = {
            "success": False,
            "message": f"Could not find struct body in object '{object_name}'",
        }
        return session

    # Insert field before closing brace.
    # Ivy 1.7 tolerates trailing commas in struct fields.
    field_line = f"        {field_name} : {field_type}\n"
    session.file_edits.append(FileEdit(
        file_path=file_path,
        kind="modify",
        edits=[TextEdit(
            line=struct_end, col=0, end_line=struct_end, end_col=0,
            new_text=field_line,
        )],
    ))

    # Update ser/deser if they exist
    proto_files = _find_protocol_files(root, protocol)
    byte_width, known = _get_byte_width(field_type)
    if not known:
        warnings.append(f"Unknown type '{field_type}' — using {byte_width} bytes for ser/deser")

    for ser_key in ("ser", "deser"):
        if ser_key not in proto_files:
            continue
        ser_path = proto_files[ser_key]
        ser_source = open(ser_path).read()
        ser_loc = SourceLocator(ser_source, ser_path)

        edits: List[TextEdit] = []

        # Add enum state
        existing_states = ser_loc.find_enum_states()
        if existing_states:
            state_name = f"{protocol}_s_{field_name}"
            last_state = existing_states[-1]
            for line_idx, line_text in enumerate(ser_source.splitlines()):
                if last_state in line_text:
                    edits.append(TextEdit(
                        line=line_idx + 1, col=0,
                        end_line=line_idx + 1, end_col=0,
                        new_text=f"        {state_name},\n",
                    ))
                    break

            # Add set/get case
            method = "set" if ser_key == "ser" else "get"
            case_line = ser_loc.find_switch_case_insertion_point(method)
            if case_line is not None:
                fn_name = "setn" if ser_key == "ser" else "getn"
                case_text = (
                    f"            case {state_name}:\n"
                    f"                {fn_name}(res, {byte_width});\n"
                    f"                break;\n"
                )
                edits.append(TextEdit(
                    line=case_line, col=0,
                    end_line=case_line, end_col=0,
                    new_text=case_text,
                ))

        if edits:
            session.file_edits.append(FileEdit(
                file_path=ser_path,
                kind="modify",
                edits=edits,
            ))

    _build_preview(
        session,
        f"Add field '{field_name}: {field_type}' to object '{object_name}'",
        warnings,
    )
    return session
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestPlanAddField -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/features/scaffold.py tests/test_tools_scaffold.py
git commit -m "feat(scaffold): add plan_add_field orchestrator"
```

---

### Task 7: plan_add_action and plan_add_monitor Orchestrators

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/features/scaffold.py`
- Modify: `$IVY_LSP/tests/test_tools_scaffold.py`

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_tools_scaffold.py

from ivy_lsp.features.scaffold import plan_add_action, plan_add_monitor


class TestPlanAddAction:
    def test_adds_action_to_object(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_action(
            root=root,
            model=None,
            protocol="minip",
            object_name="ping_frame",
            action_name="handle_keepalive",
            params=[("f", "ping_frame.keepalive"), ("dst", "ip.endpoint")],
            with_monitor=False,
        )
        assert session is not None
        assert session.preview.get("success") is True
        all_text = " ".join(e.new_text for fe in session.file_edits for e in fe.edits)
        assert "handle_keepalive" in all_text

    def test_with_monitor_creates_extra_edit(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_action(
            root=root,
            model=None,
            protocol="minip",
            object_name="ping_frame",
            action_name="handle_keepalive",
            params=[("f", "ping_frame.keepalive")],
            with_monitor=True,
        )
        all_text = " ".join(
            e.new_text for fe in session.file_edits for e in fe.edits
            if fe.kind == "modify"
        )
        assert "before" in all_text or "after" in all_text


class TestPlanAddMonitor:
    def test_adds_monitor(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        session = plan_add_monitor(
            root=root,
            model=None,
            protocol="minip",
            action_name="ping_frame.handle",
            kind="before",
            guard="_generating",
        )
        assert session is not None
        assert session.preview.get("success") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestPlanAddAction -v 2>&1 | head -20`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement plan_add_action and plan_add_monitor**

Add to `ivy_lsp/features/scaffold.py`:

```python
def plan_add_action(
    root: str,
    model: Any,
    protocol: str,
    object_name: str,
    action_name: str,
    params: List[tuple[str, str]],
    with_monitor: bool,
) -> StagingSession:
    """Plan adding an action to an object, optionally with monitors."""
    session = create_session(protocol, "ivy_add_action")
    warnings: List[str] = []

    found = _find_object_in_workspace(root, protocol, object_name)
    if found is None:
        session.preview = {
            "success": False,
            "message": f"Object '{object_name}' not found in protocol '{protocol}'",
        }
        return session

    file_path, source = found
    loc = SourceLocator(source, file_path)

    # Insert action before object closing brace
    end_line = loc.find_object_body_end(object_name)
    if end_line is None:
        session.preview = {
            "success": False,
            "message": f"Could not find object body end for '{object_name}'",
        }
        return session

    action_code = generate_action_declaration(protocol, object_name, action_name, params)
    session.file_edits.append(FileEdit(
        file_path=file_path,
        kind="modify",
        edits=[TextEdit(
            line=end_line, col=0, end_line=end_line, end_col=0,
            new_text="\n" + action_code,
        )],
    ))

    # Optionally add monitor
    if with_monitor:
        qualified_name = f"{object_name}.{action_name}"
        monitor_code = generate_monitor_block(protocol, qualified_name, "before", "_generating")
        # Append monitor after the object (as standalone block)
        lines = source.splitlines()
        append_line = len(lines)
        session.file_edits.append(FileEdit(
            file_path=file_path,
            kind="modify",
            edits=[TextEdit(
                line=append_line, col=0, end_line=append_line, end_col=0,
                new_text="\n" + monitor_code,
            )],
        ))

    summary_parts = [f"Add action '{action_name}' to '{object_name}'"]
    if with_monitor:
        summary_parts.append("with before monitor")
    _build_preview(session, ", ".join(summary_parts), warnings)
    return session


def plan_add_monitor(
    root: str,
    model: Any,
    protocol: str,
    action_name: str,
    kind: str,
    guard: str,
) -> StagingSession:
    """Plan adding a monitor block for an existing action."""
    session = create_session(protocol, "ivy_add_monitor")
    warnings: List[str] = []

    # Find any file containing the action
    action_re = re.compile(rf"action\s+{re.escape(action_name.split('.')[-1])}\b")
    target_file = None
    target_source = None

    pattern = os.path.join(root, "**", "*.ivy")
    for path in sorted(glob_module.glob(pattern, recursive=True)):
        try:
            source = open(path).read()
        except OSError:
            continue
        if action_re.search(source):
            target_file = path
            target_source = source
            break

    if target_file is None:
        session.preview = {
            "success": False,
            "message": f"Action '{action_name}' not found in protocol '{protocol}'",
        }
        return session

    # Append monitor at end of file
    lines = target_source.splitlines()
    monitor_code = generate_monitor_block(protocol, action_name, kind, guard)
    session.file_edits.append(FileEdit(
        file_path=target_file,
        kind="modify",
        edits=[TextEdit(
            line=len(lines), col=0, end_line=len(lines), end_col=0,
            new_text="\n" + monitor_code,
        )],
    ))

    _build_preview(
        session,
        f"Add {kind} monitor for '{action_name}'",
        warnings,
    )
    return session
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py -k "PlanAddAction or PlanAddMonitor" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/features/scaffold.py tests/test_tools_scaffold.py
git commit -m "feat(scaffold): add plan_add_action and plan_add_monitor orchestrators"
```

---

### Task 8: MCP Tool Registration

**Files:**
- Create: `$IVY_LSP/ivy_lsp/tools/scaffold.py`
- Modify: `$IVY_LSP/tests/test_tools_scaffold.py`

- [ ] **Step 1: Write failing integration tests**

```python
# Add to tests/test_tools_scaffold.py
import json

from ivy_lsp.mcp_server import start_mcp


def _get_mcp_app(workspace_root: str):
    """Create an MCP app instance for testing."""
    return start_mcp(workspace_root, _return_app=True)


def _extract_text(result) -> str:
    """Extract text from MCP tool result (matches test_tools_quality.py pattern)."""
    if isinstance(result, dict):
        if "result" in result:
            return result["result"]
        return json.dumps(result)
    if isinstance(result, tuple):
        content_blocks = result[0]
        if len(result) > 1 and isinstance(result[1], dict) and "result" in result[1]:
            return result[1]["result"]
        result = content_blocks
    texts = []
    for block in result:
        if hasattr(block, "text"):
            texts.append(block.text)
        elif isinstance(block, dict) and "text" in block:
            texts.append(block["text"])
    return "\n".join(texts)


class TestScaffoldToolRegistration:
    @pytest.mark.asyncio
    async def test_ivy_add_object_registered(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        mcp = _get_mcp_app(root)
        result = await mcp.call_tool(
            "ivy_add_object",
            {
                "protocol": "minip",
                "name": "keepalive",
                "fields": ["interval:milliseconds", "timeout:pkt_num"],
            },
        )
        data = json.loads(_extract_text(result))
        assert data["success"] is True
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_ivy_apply_changes_registered(self, tmp_path):
        root = _create_minip_workspace(tmp_path)
        mcp = _get_mcp_app(root)
        # First create a session
        result = await mcp.call_tool(
            "ivy_add_object",
            {
                "protocol": "minip",
                "name": "test_obj",
                "fields": ["x:bool"],
                "with_serdes": False,
                "with_variant": False,
            },
        )
        data = json.loads(_extract_text(result))
        session_id = data["session_id"]

        # Then apply
        result2 = await mcp.call_tool(
            "ivy_apply_changes",
            {"session_id": session_id},
        )
        data2 = json.loads(_extract_text(result2))
        assert data2["success"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestScaffoldToolRegistration -v 2>&1 | head -20`
Expected: FAIL — tool not registered

- [ ] **Step 3: Implement tools/scaffold.py**

```python
# ivy_lsp/tools/scaffold.py
"""Object-centric scaffold MCP tools.

Registers ivy_add_object, ivy_add_field, ivy_add_action,
ivy_add_monitor, and ivy_apply_changes tools.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ivy_lsp.features.scaffold import (
    apply_session,
    plan_add_action,
    plan_add_field,
    plan_add_monitor,
    plan_add_object,
)
from ivy_lsp.tools import safe_tool

logger = logging.getLogger(__name__)


def _parse_fields(fields: list[str]) -> list[tuple[str, str]]:
    """Parse field strings like 'name:type' into (name, type) tuples."""
    result = []
    for f in fields:
        if ":" in f:
            name, ftype = f.split(":", 1)
            result.append((name.strip(), ftype.strip()))
        else:
            result.append((f.strip(), "bool"))
    return result


def _parse_params(params: list[str]) -> list[tuple[str, str]]:
    """Parse param strings like 'name:type' into (name, type) tuples."""
    return _parse_fields(params)


def register_scaffold_tools(mcp: Any, ctx: Any) -> None:
    """Register object-centric scaffold MCP tools."""

    @mcp.tool()
    @safe_tool
    async def ivy_add_object(
        protocol: str,
        name: str,
        fields: list[str] | None = None,
        with_serdes: bool = True,
        with_variant: bool = True,
    ) -> str:
        """Add a new Ivy object with optional ser/deser and variant entry.

        Returns a preview of changes. Call ivy_apply_changes(session_id)
        to write them to disk.

        Args:
            protocol: Protocol name (e.g., "minip", "quic")
            name: Object name (e.g., "keepalive")
            fields: List of "field_name:field_type" strings
            with_serdes: Generate serializer/deserializer updates
            with_variant: Add as variant in parent frame object
        """
        parsed_fields = _parse_fields(fields or [])
        session = plan_add_object(
            root=ctx.root,
            model=await ctx.get_model() if hasattr(ctx, "get_model") else None,
            protocol=protocol,
            name=name,
            fields=parsed_fields,
            with_serdes=with_serdes,
            with_variant=with_variant,
        )
        return json.dumps(session.preview, indent=2)

    @mcp.tool()
    @safe_tool
    async def ivy_add_field(
        protocol: str,
        object_name: str,
        field_name: str,
        field_type: str,
    ) -> str:
        """Add a field to an existing object's struct, updating ser/deser.

        Returns a preview of changes. Call ivy_apply_changes(session_id)
        to write them to disk.

        Args:
            protocol: Protocol name
            object_name: Name of existing object (e.g., "ping")
            field_name: New field name (e.g., "sequence_num")
            field_type: Field type (e.g., "pkt_num")
        """
        session = plan_add_field(
            root=ctx.root,
            model=await ctx.get_model() if hasattr(ctx, "get_model") else None,
            protocol=protocol,
            object_name=object_name,
            field_name=field_name,
            field_type=field_type,
        )
        return json.dumps(session.preview, indent=2)

    @mcp.tool()
    @safe_tool
    async def ivy_add_action(
        protocol: str,
        object_name: str,
        action_name: str,
        params: list[str] | None = None,
        with_monitor: bool = True,
    ) -> str:
        """Add an action to an object, optionally with a before monitor.

        Returns a preview of changes. Call ivy_apply_changes(session_id)
        to write them to disk.

        Args:
            protocol: Protocol name
            object_name: Name of existing object
            action_name: New action name
            params: List of "param_name:param_type" strings
            with_monitor: Also generate a before monitor block
        """
        parsed_params = _parse_params(params or [])
        session = plan_add_action(
            root=ctx.root,
            model=await ctx.get_model() if hasattr(ctx, "get_model") else None,
            protocol=protocol,
            object_name=object_name,
            action_name=action_name,
            params=parsed_params,
            with_monitor=with_monitor,
        )
        return json.dumps(session.preview, indent=2)

    @mcp.tool()
    @safe_tool
    async def ivy_add_monitor(
        protocol: str,
        action_name: str,
        kind: str = "before",
        guard: str = "_generating",
    ) -> str:
        """Add a monitor block for an existing action.

        Returns a preview of changes. Call ivy_apply_changes(session_id)
        to write them to disk.

        Args:
            protocol: Protocol name
            action_name: Fully qualified action name (e.g., "ping_frame.handle")
            kind: Monitor kind — "before", "after", or "around"
            guard: Guard variable for the monitor body
        """
        session = plan_add_monitor(
            root=ctx.root,
            model=await ctx.get_model() if hasattr(ctx, "get_model") else None,
            protocol=protocol,
            action_name=action_name,
            kind=kind,
            guard=guard,
        )
        return json.dumps(session.preview, indent=2)

    @mcp.tool()
    @safe_tool
    async def ivy_apply_changes(
        session_id: str,
    ) -> str:
        """Apply staged changes from a preview session to disk.

        Writes all staged files atomically. After applying, run ivy_verify
        to check the result.

        Args:
            session_id: Session ID returned by ivy_add_* tools
        """
        result = apply_session(session_id)
        return json.dumps(result, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py::TestScaffoldToolRegistration -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/tools/scaffold.py tests/test_tools_scaffold.py
git commit -m "feat(scaffold): add MCP tool registrations for ivy_add_* and ivy_apply_changes"
```

---

### Task 9: Wire Tools into Registration Hub

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/tools/__init__.py`
- Modify: `$IVY_LSP/ivy_lsp/mcp_server.py`

- [ ] **Step 1: Read current files**

Read `$IVY_LSP/ivy_lsp/tools/__init__.py` to find exact import section and `register_all_tools()` function. Read `$IVY_LSP/ivy_lsp/mcp_server.py` to find `_MCP_INSTRUCTIONS`.

- [ ] **Step 2: Add import and registration call to tools/__init__.py**

In the imports section (after existing tool imports):
```python
from ivy_lsp.tools.scaffold import register_scaffold_tools
```

In `register_all_tools()` (after `register_quality_tools(mcp, ctx)`):
```python
    register_scaffold_tools(mcp, ctx)
```

In `_TOOL_TIMEOUTS` dict:
```python
    "ivy_add_object": 30.0,
    "ivy_add_field": 30.0,
    "ivy_add_action": 30.0,
    "ivy_add_monitor": 30.0,
    "ivy_apply_changes": 10.0,
```

In `_TOOL_METADATA` dict:
```python
    "ivy_add_object": {"cost": "low", "category": "scaffold", "needs_model": False},
    "ivy_add_field": {"cost": "low", "category": "scaffold", "needs_model": True},
    "ivy_add_action": {"cost": "low", "category": "scaffold", "needs_model": True},
    "ivy_add_monitor": {"cost": "low", "category": "scaffold", "needs_model": False},
    "ivy_apply_changes": {"cost": "low", "category": "scaffold", "needs_model": False},
```

- [ ] **Step 3: Update MCP instructions in mcp_server.py**

Find `_MCP_INSTRUCTIONS` and add a section:

```
## Object-Centric Scaffold Tools (preview → apply workflow)

- **ivy_add_object**: Add a new Ivy object with optional ser/deser and variant entry. Returns preview.
- **ivy_add_field**: Add a field to an existing struct, updating ser/deser state machines. Returns preview.
- **ivy_add_action**: Add an action to an object with optional monitor. Returns preview.
- **ivy_add_monitor**: Add a before/after/around monitor for an action. Returns preview.
- **ivy_apply_changes**: Apply staged preview changes to disk. Call after reviewing any ivy_add_* preview.

Workflow: call ivy_add_* → review preview → call ivy_apply_changes(session_id) → call ivy_verify.
```

- [ ] **Step 4: Run full test suite**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/tools/__init__.py ivy_lsp/mcp_server.py
git commit -m "feat(scaffold): wire scaffold tools into registration hub and MCP instructions"
```

---

### Task 10: End-to-End Verification

**Files:** No new files — verification only

- [ ] **Step 1: Run the full existing test suite to check for regressions**

Run: `cd $IVY_LSP && python -m pytest tests/ -v --timeout=60 2>&1 | tail -30`
Expected: No new failures (pre-existing failures may exist)

- [ ] **Step 2: Verify import chain works**

Run: `cd $IVY_LSP && python -c "from ivy_lsp.tools.scaffold import register_scaffold_tools; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run scaffold tests in isolation**

Run: `cd $IVY_LSP && python -m pytest tests/test_tools_scaffold.py -v --tb=short`
Expected: All PASS

- [ ] **Step 4: Commit all test results**

No commit needed if tests pass. If any test adjustments required, commit:
```bash
git add -u
git commit -m "fix(scaffold): adjust tests after integration verification"
```
