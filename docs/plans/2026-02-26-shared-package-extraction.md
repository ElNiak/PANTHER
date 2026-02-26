# Shared Package Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract shared types into two pip-installable packages (`panther-ivy-types`, `panther-types`) and add a `panther.api` facade module, reducing cross-project coupling and enabling panther_web development.

**Architecture:** Two shared packages with different dependency profiles (zero-dep for ivy types, pydantic+omegaconf for framework types) live as subdirectories in `packages/`. Original locations become re-export shims for backward compatibility. A `panther.api` module wraps existing managers for web consumption.

**Tech Stack:** Python 3.10+, dataclasses (Phase 1), Pydantic v2 + OmegaConf (Phase 2), existing PANTHER managers (Phase 3)

**Design Document:** `/Users/elniak/.claude/plans/valiant-mixing-hammock.md`

---

## Phase 1: Extract `panther-ivy-types` (near-zero risk)

### Task 1: Create package scaffold

**Files:**
- Create: `packages/panther-ivy-types/pyproject.toml`
- Create: `packages/panther-ivy-types/panther_ivy_types/__init__.py`

**Step 1: Create directory structure**

Run: `mkdir -p packages/panther-ivy-types/panther_ivy_types`

**Step 2: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "panther-ivy-types"
version = "0.1.0"
description = "Shared data types for the PANTHER Ivy formal verification toolchain"
license = "MIT"
requires-python = ">=3.10"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "mypy>=1.0"]

[tool.setuptools.packages.find]
include = ["panther_ivy_types*"]
```

**Step 3: Write `__init__.py` with public API**

```python
"""Shared data types for the PANTHER Ivy formal verification toolchain.

This package contains pure dataclasses with zero external dependencies,
importable by any project in the PANTHER ecosystem (ivy-lsp, panther_ivy,
panther-serena, panther_web) without pulling in heavy framework deps.
"""

from panther_ivy_types.api import (
    CommandResult,
    CompileResult,
    DiagnosticItem,
    ExecutionResult,
    TestInfo,
    TestRunResult,
)
from panther_ivy_types.analysis import (
    ActionNode,
    PropertyNode,
    RequirementNode,
    StateVarNode,
)
from panther_ivy_types.scope import ExportImportInfo, TestScope

__all__ = [
    "CommandResult",
    "CompileResult",
    "DiagnosticItem",
    "ExecutionResult",
    "TestInfo",
    "TestRunResult",
    "RequirementNode",
    "StateVarNode",
    "ActionNode",
    "PropertyNode",
    "ExportImportInfo",
    "TestScope",
]
```

**Step 4: Commit**

```bash
git add packages/panther-ivy-types/
git commit -m "feat: scaffold panther-ivy-types package"
```

---

### Task 2: Extract API types module

**Files:**
- Create: `packages/panther-ivy-types/panther_ivy_types/api.py`
- Create: `packages/panther-ivy-types/tests/__init__.py`
- Create: `packages/panther-ivy-types/tests/test_api.py`
- Source: `panther/plugins/services/testers/panther_ivy/api/types.py`

**Step 1: Write the failing test**

```python
"""Tests for panther_ivy_types.api module."""

from dataclasses import asdict

import pytest


def test_command_result_fields():
    from panther_ivy_types.api import CommandResult

    r = CommandResult(commands=["echo hello"], environment={"FOO": "bar"}, working_dir="/tmp")
    assert r.commands == ["echo hello"]
    assert r.environment == {"FOO": "bar"}
    assert r.working_dir == "/tmp"


def test_command_result_to_dict():
    from panther_ivy_types.api import CommandResult

    r = CommandResult(commands=["ls"], environment={}, working_dir="/home")
    d = r.to_dict()
    assert d == {"commands": ["ls"], "environment": {}, "working_dir": "/home"}


def test_compile_result_nesting():
    from panther_ivy_types.api import CommandResult, CompileResult

    setup = CommandResult(commands=["apt update"], environment={}, working_dir="/")
    compile_cmd = CommandResult(commands=["ivyc test.ivy"], environment={"PATH": "/bin"}, working_dir="/opt")
    result = CompileResult(setup_commands=setup, compile_commands=compile_cmd)
    d = result.to_dict()
    assert d["setup_commands"]["commands"] == ["apt update"]
    assert d["compile_commands"]["commands"] == ["ivyc test.ivy"]


def test_test_run_result_nesting():
    from panther_ivy_types.api import CommandResult, CompileResult, TestRunResult

    setup = CommandResult(commands=[], environment={}, working_dir="/")
    compile_cmd = CommandResult(commands=["ivyc"], environment={}, working_dir="/")
    compile_result = CompileResult(setup_commands=setup, compile_commands=compile_cmd)
    run = CommandResult(commands=["./test"], environment={}, working_dir="/opt")
    result = TestRunResult(compile=compile_result, run_commands=run)
    d = result.to_dict()
    assert d["run_commands"]["commands"] == ["./test"]


def test_diagnostic_item_fields():
    from panther_ivy_types.api import DiagnosticItem

    d = DiagnosticItem(file="test.ivy", line=10, column=5, severity="error", message="type mismatch")
    assert d.file == "test.ivy"
    assert d.severity == "error"
    assert d.to_dict()["line"] == 10


def test_test_info_fields():
    from panther_ivy_types.api import TestInfo

    t = TestInfo(name="quic_server_test_stream", protocol="quic", version="rfc9000", role="server", ivy_file="/opt/quic_tests/server_tests/test.ivy")
    assert t.protocol == "quic"
    assert t.role == "server"


def test_execution_result_fields():
    from panther_ivy_types.api import ExecutionResult

    r = ExecutionResult(exit_code=0, stdout="PASS", stderr="", target="docker")
    assert r.exit_code == 0
    assert r.target == "docker"
```

**Step 2: Run test to verify it fails**

Run: `cd packages/panther-ivy-types && python -m pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'panther_ivy_types.api'`

**Step 3: Write the api.py module**

Copy from `panther/plugins/services/testers/panther_ivy/api/types.py` (verbatim, 79 lines):

```python
"""API data types for the Ivy formal verification toolchain.

These are pure dataclasses with zero external dependencies. Originally
defined in panther_ivy/api/types.py, now canonical home is here.
"""

from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class CommandResult:
    """Shell commands with their environment and working directory."""

    commands: List[str]
    environment: Dict[str, str]
    working_dir: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CompileResult:
    """Result of generating compilation commands."""

    setup_commands: CommandResult
    compile_commands: CommandResult

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestRunResult:
    """Result of generating full test execution commands."""

    compile: CompileResult
    run_commands: CommandResult

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiagnosticItem:
    """A single diagnostic (error/warning) from compilation."""

    file: str
    line: int
    column: int
    severity: str  # "error" | "warning" | "info"
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestInfo:
    """Metadata about an available Ivy test specification."""

    name: str
    protocol: str
    version: str
    role: str  # "server" | "client"
    ivy_file: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExecutionResult:
    """Result of executing commands in Docker or on host."""

    exit_code: int
    stdout: str
    stderr: str
    target: str  # "docker" | "host"

    def to_dict(self) -> dict:
        return asdict(self)
```

**Step 4: Run test to verify it passes**

Run: `cd packages/panther-ivy-types && python -m pytest tests/test_api.py -v`
Expected: 7 PASSED

**Step 5: Commit**

```bash
git add packages/panther-ivy-types/panther_ivy_types/api.py packages/panther-ivy-types/tests/
git commit -m "feat(panther-ivy-types): add API types module with tests"
```

---

### Task 3: Extract analysis types module

**Files:**
- Create: `packages/panther-ivy-types/panther_ivy_types/analysis.py`
- Create: `packages/panther-ivy-types/tests/test_analysis.py`
- Source: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/requirement_graph.py` (dataclass nodes only, lines 27-77)

**Step 1: Write the failing test**

```python
"""Tests for panther_ivy_types.analysis module."""

import pytest


def test_requirement_node_fields():
    from panther_ivy_types.analysis import RequirementNode

    r = RequirementNode(
        id="test.ivy:10",
        kind="require",
        formula_text="sent_pkt(C,L)",
        line=10,
        col=0,
        file="/opt/test.ivy",
        monitor_action="frame.ack.handle",
        mixin_kind="before",
    )
    assert r.id == "test.ivy:10"
    assert r.kind == "require"
    assert r.bracket_tags == []
    assert r.ast_node is None


def test_requirement_node_with_bracket_tags():
    from panther_ivy_types.analysis import RequirementNode

    r = RequirementNode(
        id="test.ivy:20",
        kind="ensure",
        formula_text="ack_eliciting(C)",
        line=20,
        col=4,
        file="/opt/test.ivy",
        monitor_action="quic.send",
        mixin_kind="after",
        bracket_tags=["rfc9000:4.1", "rfc9000:8.1"],
    )
    assert r.bracket_tags == ["rfc9000:4.1", "rfc9000:8.1"]


def test_state_var_node_fields():
    from panther_ivy_types.analysis import StateVarNode

    s = StateVarNode(
        id="frame.ack.sent_pkt",
        name="sent_pkt",
        qualified_name="frame.ack.sent_pkt",
        file="/opt/quic_stack/frame.ivy",
        line=42,
    )
    assert s.is_relation is False
    assert s.params is None


def test_state_var_node_relation():
    from panther_ivy_types.analysis import StateVarNode

    s = StateVarNode(
        id="conn.sent_pkt",
        name="sent_pkt",
        qualified_name="conn.sent_pkt",
        file="/opt/conn.ivy",
        line=15,
        is_relation=True,
        params="(C:cid, L:quic_packet_type)",
    )
    assert s.is_relation is True
    assert s.params == "(C:cid, L:quic_packet_type)"


def test_action_node_fields():
    from panther_ivy_types.analysis import ActionNode

    a = ActionNode(
        id="quic.send",
        name="send",
        qualified_name="quic.send",
        file="/opt/quic.ivy",
        line=100,
    )
    assert a.qualified_name == "quic.send"


def test_property_node_fields():
    from panther_ivy_types.analysis import PropertyNode

    p = PropertyNode(
        id="/opt/inv.ivy:5",
        kind="invariant",
        name="conn_invariant",
        formula_text="forall C. connected(C) -> valid(C)",
        file="/opt/inv.ivy",
        line=5,
    )
    assert p.kind == "invariant"
```

**Step 2: Run test to verify it fails**

Run: `cd packages/panther-ivy-types && python -m pytest tests/test_analysis.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the analysis.py module**

```python
"""Analysis data types for the Ivy requirement graph.

These are pure dataclasses representing graph nodes. The graph logic
(RequirementGraph, ScopedRequirementModel) stays in ivy-lsp.
Originally defined in ivy_lsp/analysis/requirement_graph.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class RequirementNode:
    """A require/ensure/assume/assert statement extracted from a monitor body."""

    id: str  # "filepath:line" unique key
    kind: str  # "require" | "ensure" | "assume" | "assert"
    formula_text: str
    line: int  # 0-based
    col: int  # 0-based
    file: str  # absolute filepath
    monitor_action: str  # action being monitored (mixee)
    mixin_kind: str  # "before" | "after" | "implement" | "direct"
    bracket_tags: List[str] = field(default_factory=list)
    ast_node: Any = None  # reference to original AST node


@dataclass
class StateVarNode:
    """A state variable (relation, function, individual) in the workspace."""

    id: str  # qualified name
    name: str  # e.g. "sent_pkt"
    qualified_name: str  # e.g. "frame.ack.sent_pkt"
    file: str
    line: int
    is_relation: bool = False
    params: Optional[str] = None  # e.g. "(C:cid, L:quic_packet_type)"


@dataclass
class ActionNode:
    """An action declaration in the workspace."""

    id: str  # qualified name
    name: str
    qualified_name: str
    file: str
    line: int


@dataclass
class PropertyNode:
    """An invariant, property, axiom, or conjecture declaration."""

    id: str  # "filepath:line"
    kind: str  # "invariant" | "property" | "axiom" | "conjecture"
    name: str
    formula_text: str
    file: str
    line: int
```

**Step 4: Run test to verify it passes**

Run: `cd packages/panther-ivy-types && python -m pytest tests/test_analysis.py -v`
Expected: 6 PASSED

**Step 5: Commit**

```bash
git add packages/panther-ivy-types/panther_ivy_types/analysis.py packages/panther-ivy-types/tests/test_analysis.py
git commit -m "feat(panther-ivy-types): add analysis node types with tests"
```

---

### Task 4: Extract scope types module

**Files:**
- Create: `packages/panther-ivy-types/panther_ivy_types/scope.py`
- Create: `packages/panther-ivy-types/tests/test_scope.py`
- Source: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/test_scope.py` (ExportImportInfo and TestScope only, lines 17-47)

**Step 1: Write the failing test**

```python
"""Tests for panther_ivy_types.scope module."""

import pytest


def test_export_import_info_defaults():
    from panther_ivy_types.scope import ExportImportInfo

    info = ExportImportInfo(file="/opt/test.ivy")
    assert info.exports == []
    assert info.imports == []
    assert info.export_lines == {}
    assert info.import_lines == {}
    assert info.has_exports is False


def test_export_import_info_with_data():
    from panther_ivy_types.scope import ExportImportInfo

    info = ExportImportInfo(
        file="/opt/quic_stack/frame.ivy",
        exports=["frame.ack.handle", "frame.ack.send"],
        imports=["quic.send"],
        export_lines={"frame.ack.handle": 10, "frame.ack.send": 20},
        import_lines={"quic.send": 5},
    )
    assert info.has_exports is True
    assert len(info.exports) == 2


def test_test_scope_frozen():
    from panther_ivy_types.scope import TestScope

    scope = TestScope(
        test_file="/opt/quic_tests/server_tests/test_stream.ivy",
        include_closure=frozenset(["/opt/quic_stack/frame.ivy", "/opt/quic_stack/conn.ivy"]),
        exported_actions=frozenset(["frame.ack.handle"]),
        imported_actions=frozenset(["quic.send"]),
        tester_role="client",
    )
    assert scope.tester_role == "client"
    # frozen dataclass - should be hashable
    hash(scope)


def test_test_scope_is_action_exported():
    from panther_ivy_types.scope import TestScope

    scope = TestScope(
        test_file="test.ivy",
        include_closure=frozenset(),
        exported_actions=frozenset(["frame.ack.handle", "quic.send"]),
        imported_actions=frozenset(),
        tester_role="server",
    )
    assert scope.is_action_exported("frame.ack.handle") is True
    assert scope.is_action_exported("unknown.action") is False


def test_test_scope_is_file_in_scope():
    from panther_ivy_types.scope import TestScope

    scope = TestScope(
        test_file="test.ivy",
        include_closure=frozenset(["/opt/a.ivy", "/opt/b.ivy"]),
        exported_actions=frozenset(),
        imported_actions=frozenset(),
        tester_role="unknown",
    )
    assert scope.is_file_in_scope("/opt/a.ivy") is True
    assert scope.is_file_in_scope("/opt/c.ivy") is False
```

**Step 2: Run test to verify it fails**

Run: `cd packages/panther-ivy-types && python -m pytest tests/test_scope.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the scope.py module**

```python
"""Scope data types for per-test requirement scoping.

These are pure dataclasses for export/import tracking and test scope
computation. The ScopedRequirementModel logic stays in ivy-lsp.
Originally defined in ivy_lsp/analysis/test_scope.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List


@dataclass
class ExportImportInfo:
    """Export/import declarations extracted from a single Ivy file."""

    file: str
    exports: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    export_lines: Dict[str, int] = field(default_factory=dict)
    import_lines: Dict[str, int] = field(default_factory=dict)

    @property
    def has_exports(self) -> bool:
        return len(self.exports) > 0


@dataclass(frozen=True)
class TestScope:
    """Scope of a single Ivy test file."""

    test_file: str
    include_closure: FrozenSet[str]
    exported_actions: FrozenSet[str]
    imported_actions: FrozenSet[str]
    tester_role: str  # "client" | "server" | "mim" | "unknown"

    def is_action_exported(self, action_name: str) -> bool:
        return action_name in self.exported_actions

    def is_file_in_scope(self, filepath: str) -> bool:
        return filepath in self.include_closure
```

**Step 4: Run test to verify it passes**

Run: `cd packages/panther-ivy-types && python -m pytest tests/test_scope.py -v`
Expected: 5 PASSED

**Step 5: Commit**

```bash
git add packages/panther-ivy-types/panther_ivy_types/scope.py packages/panther-ivy-types/tests/test_scope.py
git commit -m "feat(panther-ivy-types): add scope types with tests"
```

---

### Task 5: Install package and run full test suite

**Files:**
- No new files

**Step 1: Install panther-ivy-types in editable mode**

Run: `cd packages/panther-ivy-types && pip install -e ".[dev]"`
Expected: `Successfully installed panther-ivy-types-0.1.0`

**Step 2: Run all panther-ivy-types tests**

Run: `cd packages/panther-ivy-types && python -m pytest tests/ -v`
Expected: 18 PASSED (7 api + 6 analysis + 5 scope)

**Step 3: Verify imports work from anywhere**

Run: `python -c "from panther_ivy_types import DiagnosticItem, RequirementNode, TestScope; print('OK:', DiagnosticItem.__module__, RequirementNode.__module__, TestScope.__module__)"`
Expected: `OK: panther_ivy_types.api panther_ivy_types.analysis panther_ivy_types.scope`

**Step 4: Run existing panther unit tests (no regression)**

Run: `pytest tests/ -n auto -m unit --timeout=60 -q`
Expected: All existing tests still pass (panther-ivy-types is additive, no changes to existing code yet)

**Step 5: Commit (no code changes, just verification)**

No commit needed - this was a verification step.

---

### Task 6: Wire re-export shim in panther_ivy/api/types.py

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/api/types.py`
- Create: `packages/panther-ivy-types/tests/test_backward_compat.py`

**Step 1: Write the backward compatibility test**

```python
"""Tests that the old import paths still work via re-export shims."""

import pytest


def test_old_import_path_command_result():
    """Verify panther_ivy.api.types still exports CommandResult."""
    from panther_ivy.api.types import CommandResult

    r = CommandResult(commands=["echo"], environment={}, working_dir="/")
    assert r.commands == ["echo"]


def test_old_import_path_diagnostic_item():
    from panther_ivy.api.types import DiagnosticItem

    d = DiagnosticItem(file="x.ivy", line=1, column=0, severity="error", message="bad")
    assert d.severity == "error"


def test_same_class_identity():
    """Verify old and new import paths resolve to the same class."""
    from panther_ivy.api.types import CommandResult as OldCommandResult
    from panther_ivy_types.api import CommandResult as NewCommandResult

    assert OldCommandResult is NewCommandResult
```

**Step 2: Run test to verify current state (should pass since old types.py still exists)**

Run: `python -m pytest packages/panther-ivy-types/tests/test_backward_compat.py -v`
Expected: PASS (old module still exists with original definitions)

**Step 3: Replace panther_ivy/api/types.py with re-export shim**

Replace the entire content of `panther/plugins/services/testers/panther_ivy/api/types.py` with:

```python
"""Data types for the panther_ivy public API.

Re-exported from panther_ivy_types for backward compatibility.
Canonical definitions are now in the panther-ivy-types package.
"""

from panther_ivy_types.api import (  # noqa: F401
    CommandResult,
    CompileResult,
    DiagnosticItem,
    ExecutionResult,
    TestInfo,
    TestRunResult,
)
```

**Step 4: Run backward compatibility test**

Run: `python -m pytest packages/panther-ivy-types/tests/test_backward_compat.py -v`
Expected: 3 PASSED (including `test_same_class_identity`)

**Step 5: Run panther_ivy API tests (no regression)**

Run: `python -m pytest panther/plugins/services/testers/panther_ivy/tests/test_api/ -v`
Expected: All existing panther_ivy API tests still pass

**Step 6: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/api/types.py packages/panther-ivy-types/tests/test_backward_compat.py
git commit -m "refactor: wire panther_ivy/api/types.py as re-export shim for panther-ivy-types"
```

---

### Task 7: Wire re-export shims in ivy-lsp analysis modules

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/requirement_graph.py`
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/test_scope.py`

**Note:** These are submodule files. Changes here need to be committed in the ivy-lsp submodule first, then the submodule pointer updated in panther_ivy, then in panther. However, since panther-ivy-types is now pip-installable, ivy-lsp can add it as a dependency and import from it. This task documents what the ivy-lsp changes look like, but the actual commit goes in the ivy-lsp repo.

**Step 1: Update requirement_graph.py to import from panther_ivy_types**

In `ivy_lsp/analysis/requirement_graph.py`, replace lines 27-77 (the 4 dataclass definitions) with imports:

```python
# Replace local dataclass definitions with imports from shared package
from panther_ivy_types.analysis import (
    ActionNode,
    PropertyNode,
    RequirementNode,
    StateVarNode,
)
```

Keep everything else (RequirementGraph class, EdgeType enum, all methods) unchanged.

**Step 2: Update test_scope.py to import from panther_ivy_types**

In `ivy_lsp/analysis/test_scope.py`, replace lines 17-47 (ExportImportInfo and TestScope dataclasses) with imports:

```python
from panther_ivy_types.scope import ExportImportInfo, TestScope
```

Keep `detect_test_role()` function and `ScopedRequirementModel` class unchanged. `ScopedRequirementModel` still imports `RequirementGraph` and `RequirementNode` - update its import to:

```python
from panther_ivy_types.analysis import RequirementNode
from ivy_lsp.analysis.requirement_graph import RequirementGraph
```

**Step 3: Run ivy-lsp tests to verify no regression**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest -v` (if test suite exists)

**Step 4: Commit in ivy-lsp submodule**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/analysis/requirement_graph.py ivy_lsp/analysis/test_scope.py
git commit -m "refactor: import shared types from panther-ivy-types package"
```

**Step 5: Update submodule pointer in panther_ivy**

```bash
cd panther/plugins/services/testers/panther_ivy
git add submodules/ivy-lsp
git commit -m "chore: update ivy-lsp submodule - use panther-ivy-types for shared types"
```

**Step 6: Update submodule pointer in panther**

```bash
cd .  # back to panther root
git add panther/plugins/services/testers/panther_ivy
git commit -m "chore: update panther_ivy submodule - shared types via panther-ivy-types"
```

---

## Phase 2: Extract `panther-types` (medium complexity)

> **Note:** Phase 2 is more complex due to Pydantic validators that import from `panther.config.core.validators` and `panther.config.core.components.universal_validators`. These validator functions must either be extracted alongside the models or inlined. A detailed exploration of all validator dependencies should be done before starting Phase 2.

### Task 8: Create panther-types package scaffold

**Files:**
- Create: `packages/panther-types/pyproject.toml`
- Create: `packages/panther-types/panther_types/__init__.py`
- Create: `packages/panther-types/panther_types/config/__init__.py`
- Create: `packages/panther-types/panther_types/events/__init__.py`
- Create: `packages/panther-types/panther_types/exceptions/__init__.py`
- Create: `packages/panther-types/panther_types/plugin/__init__.py`
- Create: `packages/panther-types/panther_types/observer/__init__.py`

**Step 1: Create directory structure**

Run: `mkdir -p packages/panther-types/panther_types/{config,events,exceptions,plugin,observer} packages/panther-types/tests`

**Step 2: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "panther-types"
version = "0.1.0"
description = "Shared configuration, event, and plugin types for the PANTHER framework"
license = "MIT"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "omegaconf>=2.3",
    "PyYAML>=6.0",
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Typing :: Typed",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "mypy>=1.0"]

[tool.setuptools.packages.find]
include = ["panther_types*"]
```

**Step 3: Create empty `__init__.py` files**

Create `__init__.py` with empty content for each subdirectory.

**Step 4: Commit**

```bash
git add packages/panther-types/
git commit -m "feat: scaffold panther-types package"
```

---

### Task 9: Extract exception hierarchy

**Files:**
- Create: `packages/panther-types/panther_types/exceptions/base.py`
- Create: `packages/panther-types/tests/test_exceptions.py`
- Source: `panther/core/exceptions/` (read all files to identify full hierarchy)

**Step 1: Read source exceptions to understand full hierarchy**

Check: `panther/core/exceptions/__init__.py`, `panther/core/exceptions/base.py`, and any submodules

**Step 2: Write failing test for exception hierarchy**

**Step 3: Extract exception classes (these have no external deps beyond stdlib)**

**Step 4: Run tests, commit**

---

### Task 10: Extract plugin enums and structures

**Files:**
- Create: `packages/panther-types/panther_types/plugin/types.py`
- Create: `packages/panther-types/tests/test_plugin_types.py`
- Source: `panther/plugins/core/structures/` (PluginType, PluginManifest, PluginMetadata)

**Step 1: Read source to identify exact classes and their deps**

**Step 2-5: Write test, extract, verify, commit**

---

### Task 11: Extract config base classes

**Files:**
- Create: `packages/panther-types/panther_types/config/base.py`
- Create: `packages/panther-types/tests/test_config_base.py`
- Source: `panther/config/core/base.py` (BaseConfig, 244 lines)
- Source: `panther/config/core/models/base_model.py` (BaseUnifiedModel)

**Key challenge:** BaseConfig imports `yaml`, `omegaconf`, `pydantic` - all declared as panther-types dependencies, so this is fine. BaseUnifiedModel imports from `.base` (relative) which becomes `panther_types.config.base`.

**Step 1-5: Write test, extract, verify, commit**

---

### Task 12: Extract service config enums

**Files:**
- Create: `packages/panther-types/panther_types/config/service.py` (enums only first)
- Create: `packages/panther-types/tests/test_service_enums.py`
- Source: `panther/config/core/models/service.py` (ImplementationType, ProtocolRole, VersionBase)

**Note:** Extract enums first (zero complex deps), then ProtocolConfig and ServiceConfig later (have validators with panther internal imports).

**Step 1-5: Write test, extract enums, verify, commit**

---

### Task 13: Extract plugin config models

**Files:**
- Create: `packages/panther-types/panther_types/config/plugin.py`
- Create: `packages/panther-types/tests/test_plugin_config.py`
- Source: `panther/config/core/models/plugin.py` (BasePluginConfig, ServicePluginConfig, etc.)

**Key challenge:** `ServicePluginConfig.validate_type` references `ImplementationType` which is now in `panther_types.config.service`. The validator logic is simple (string-to-enum conversion) and can be inlined.

**Step 1-5: Write test, extract, verify, commit**

---

### Task 14: Wire re-export shims in panther core

**Files:**
- Modify: `panther/config/core/base.py` -> re-export from panther_types
- Modify: `panther/config/core/models/plugin.py` -> re-export from panther_types
- Modify: `panther/config/core/models/service.py` -> re-export enums from panther_types (keep full models in panther for now due to validator deps)
- Modify: `panther/core/exceptions/` -> re-export from panther_types

**Step 1: Replace each source file with re-export shim (same pattern as Task 6)**

**Step 2: Run full test suite: `pytest tests/ -n auto -m unit`**

**Step 3: Commit**

---

### Task 15: Update panther_ivy imports

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/config_schema.py` (lines 7-8)
- Modify: `panther/plugins/services/testers/panther_ivy/panther_ivy.py` (lines 14-15)

**Step 1: Update imports**

```python
# config_schema.py
from panther_types.config.plugin import ServicePluginConfig
from panther_types.config.service import ImplementationType, VersionBase
```

**Step 2: Run panther_ivy tests, commit**

---

## Phase 3: Build `panther.api` module (outline)

> **Note:** Phase 3 depends on Phase 2 completion. Detailed task breakdown should be done when Phase 2 is stable. The outline below captures the key deliverables.

### Task 16: Create panther.api scaffold

**Files:**
- Create: `panther/api/__init__.py`
- Create: `panther/api/config.py`
- Create: `panther/api/plugins.py`
- Create: `panther/api/experiments.py`
- Create: `panther/api/events.py`
- Create: `panther/api/docker.py`
- Create: `panther/api/schemas.py`

### Task 17: Implement config API

Wrap `ConfigurationManager` with functions: `load_config()`, `validate_config()`, `save_config()`, `get_config_schema()`, `merge_configs()`.

Reference: `panther/config/core/manager.py` (ConfigurationManager class)

### Task 18: Implement plugins API

Wrap `PluginManager` with functions: `list_plugins()`, `get_plugin_info()`, `get_plugin_config_schema()`, `list_protocols()`, `list_environments()`.

Reference: `panther/plugins/plugin_manager.py` (PluginManager class), `panther/webapp/web_app.py` (existing Flask endpoints as prior art)

### Task 19: Implement experiments API

Wrap `ExperimentManager` with functions: `create_experiment()`, `launch_experiment()`, `get_status()`, `stop_experiment()`, `list_experiments()`, `get_results()`.

Reference: `panther/core/experiment_manager.py` (ExperimentManager class)

### Task 20: Implement events API

Wrap `EventManager` with functions: `subscribe()`, `unsubscribe()`, `event_stream()`.

Reference: `panther/core/observer/management/event_manager.py` (EventManager class)

### Task 21: Implement schemas API

JSON Schema generation from Pydantic models for frontend form building.

### Task 22: Integration tests for panther.api

End-to-end test: load config -> create experiment -> subscribe to events -> launch -> collect results.

---

## Verification Checklist

After each phase, verify:

- [ ] **Phase 1**: `pip install -e packages/panther-ivy-types/` works, all 18+ new tests pass, existing panther unit tests unchanged, re-export shims verified with `test_same_class_identity`
- [ ] **Phase 2**: `pip install -e packages/panther-types/` works, panther_ivy imports from panther_types, full test suite passes (767+ tests), backward compat shims verified
- [ ] **Phase 3**: `from panther.api import config, plugins, experiments, events` works, each facade function delegates correctly, integration test with minimal experiment config passes
