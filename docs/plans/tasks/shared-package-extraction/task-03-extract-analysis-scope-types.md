# Task 03: Extract Analysis and Scope Types to panther-ivy-types

## Goal
Extract `RequirementNode`, `StateVarNode`, `ActionNode`, `PropertyNode` from ivy-lsp's `requirement_graph.py` and `ExportImportInfo`, `TestScope` from `test_scope.py` into panther-ivy-types.

## Prerequisites
- Task 01 completed (package scaffolded)

## Source Files

### requirement_graph.py (348 lines total)
`panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/requirement_graph.py`

Extract:
- `RequirementNode` (lines 27-40) - dataclass
- `StateVarNode` (lines 43-53) - dataclass
- `ActionNode` (lines 56-64) - dataclass
- `PropertyNode` (lines 67-76) - dataclass

Leave in ivy-lsp:
- `EdgeType` (lines 84-91) - only used within ivy-lsp
- `RequirementGraph` (lines 98-348) - complex logic, stays in ivy-lsp

### test_scope.py (174 lines total)
`panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/test_scope.py`

Extract only:
- `ExportImportInfo` (lines 18-31) - dataclass
- `TestScope` (lines 33-48) - frozen dataclass

Leave in ivy-lsp:
- `detect_test_role()` (lines 50-63) - function with logic
- `NctClassification` (lines 66-72) - only used within ivy-lsp
- `ActionClassification` (lines 74-80) - only used within ivy-lsp
- `classify_requirement()` (lines 82-97) - function with logic
- `classify_action_direction()` (lines 100-108) - function with logic
- `ScopedRequirementModel` (lines 114-174) - complex class extending RequirementGraph

## Steps

### Step 1: Write panther_ivy_types/analysis.py

Read the source RequirementNode and StateVarNode from requirement_graph.py and copy their exact field definitions:

```python
# packages/panther-ivy-types/panther_ivy_types/analysis.py
"""Analysis data types for Ivy requirement graphs.

These dataclasses represent nodes in the requirement dependency graph
used for formal verification of protocol implementations.
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
    is_relation: bool = False  # True if relation (bool sort + args)
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

### Step 2: Write panther_ivy_types/scope.py

Read the source ExportImportInfo and TestScope from test_scope.py and copy their exact field definitions:

```python
# packages/panther-ivy-types/panther_ivy_types/scope.py
"""Scope data types for Ivy test scope analysis.

These dataclasses represent the scope boundaries of Ivy test files,
tracking which actions are exported/imported and the overall test scope.
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

### Step 3: Write tests

```python
# packages/panther-ivy-types/tests/test_analysis_types.py
"""Tests for analysis types."""
from panther_ivy_types.analysis import ActionNode, PropertyNode, RequirementNode, StateVarNode


class TestRequirementNode:
    def test_create(self):
        node = RequirementNode(
            id="test.ivy:10", kind="require", formula_text="x > 0",
            line=10, col=5, file="test.ivy",
            monitor_action="frame.ack.handle", mixin_kind="before",
        )
        assert node.kind == "require"
        assert node.bracket_tags == []
        assert node.ast_node is None

    def test_with_bracket_tags(self):
        node = RequirementNode(
            id="test.ivy:20", kind="ensure", formula_text="connected(c)",
            line=20, col=1, file="quic.ivy",
            monitor_action="handle_packet", mixin_kind="after",
            bracket_tags=["rfc9000:4.1", "rfc9000:8.1"],
        )
        assert node.mixin_kind == "after"
        assert len(node.bracket_tags) == 2


class TestStateVarNode:
    def test_create_simple(self):
        node = StateVarNode(
            id="quic.conn_seen", name="conn_seen",
            qualified_name="quic.conn_seen",
            file="quic.ivy", line=5,
        )
        assert node.is_relation is False
        assert node.params is None

    def test_create_relation(self):
        node = StateVarNode(
            id="conn.sent_pkt", name="sent_pkt",
            qualified_name="conn.sent_pkt",
            file="conn.ivy", line=10,
            is_relation=True,
            params="(C:cid, L:quic_packet_type)",
        )
        assert node.is_relation is True
        assert node.params == "(C:cid, L:quic_packet_type)"


class TestActionNode:
    def test_create(self):
        node = ActionNode(
            id="quic.send", name="send",
            qualified_name="quic.send",
            file="quic.ivy", line=100,
        )
        assert node.qualified_name == "quic.send"


class TestPropertyNode:
    def test_create(self):
        node = PropertyNode(
            id="/opt/inv.ivy:5", kind="invariant",
            name="conn_invariant",
            formula_text="forall C. connected(C) -> valid(C)",
            file="/opt/inv.ivy", line=5,
        )
        assert node.kind == "invariant"
```

```python
# packages/panther-ivy-types/tests/test_scope_types.py
"""Tests for scope types."""
from panther_ivy_types.scope import ExportImportInfo, TestScope


class TestExportImportInfo:
    def test_create_empty(self):
        info = ExportImportInfo(file="test.ivy")
        assert info.exports == []
        assert info.imports == []
        assert info.export_lines == {}
        assert info.import_lines == {}
        assert info.has_exports is False

    def test_create_with_data(self):
        info = ExportImportInfo(
            file="quic_server_test_stream.ivy",
            exports=["handle_packet", "send_frame"],
            imports=["tls_handshake"],
            export_lines={"handle_packet": 10, "send_frame": 20},
            import_lines={"tls_handshake": 5},
        )
        assert len(info.exports) == 2
        assert info.has_exports is True
        assert info.export_lines["handle_packet"] == 10


class TestTestScope:
    def test_frozen(self):
        scope = TestScope(
            test_file="test.ivy",
            include_closure=frozenset(),
            exported_actions=frozenset(),
            imported_actions=frozenset(),
            tester_role="unknown",
        )
        try:
            scope.test_file = "other.ivy"
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_create_full(self):
        scope = TestScope(
            test_file="quic_server_test_stream.ivy",
            include_closure=frozenset(["quic_stack.ivy", "tls_stack.ivy"]),
            exported_actions=frozenset(["handle_packet"]),
            imported_actions=frozenset(["tls_init"]),
            tester_role="client",
        )
        assert scope.tester_role == "client"
        assert "quic_stack.ivy" in scope.include_closure

    def test_is_action_exported(self):
        scope = TestScope(
            test_file="test.ivy",
            include_closure=frozenset(),
            exported_actions=frozenset(["frame.ack.handle", "quic.send"]),
            imported_actions=frozenset(),
            tester_role="server",
        )
        assert scope.is_action_exported("frame.ack.handle") is True
        assert scope.is_action_exported("unknown.action") is False

    def test_is_file_in_scope(self):
        scope = TestScope(
            test_file="test.ivy",
            include_closure=frozenset(["/opt/a.ivy", "/opt/b.ivy"]),
            exported_actions=frozenset(),
            imported_actions=frozenset(),
            tester_role="unknown",
        )
        assert scope.is_file_in_scope("/opt/a.ivy") is True
        assert scope.is_file_in_scope("/opt/c.ivy") is False

    def test_hashable(self):
        """TestScope is frozen, so it should be usable as a dict key."""
        scope1 = TestScope(
            test_file="a.ivy", include_closure=frozenset(),
            exported_actions=frozenset(), imported_actions=frozenset(),
            tester_role="unknown",
        )
        scope2 = TestScope(
            test_file="b.ivy", include_closure=frozenset(),
            exported_actions=frozenset(), imported_actions=frozenset(),
            tester_role="unknown",
        )
        d = {scope1: "first", scope2: "second"}
        assert d[scope1] == "first"
```

## Verification
```bash
cd packages/panther-ivy-types
pytest tests/test_analysis_types.py tests/test_scope_types.py -v
```

All tests should pass. Also verify the __init__.py re-exports work:
```bash
python -c "from panther_ivy_types import RequirementNode, StateVarNode, ExportImportInfo, TestScope; print('OK')"
```

## Important Notes
- Read the ACTUAL source files before copying. The field definitions above are based on the exploration but the source may have been updated.
- `RequirementNode` and `StateVarNode` fields must exactly match what `RequirementGraph` (in ivy-lsp) uses, since it will import these types.
- `TestScope` must remain `frozen=True` as it's used as dict keys in the codebase.

## Commit Message
```
feat(panther-ivy-types): add analysis and scope types

Extract RequirementNode, StateVarNode, ActionNode, PropertyNode from
requirement_graph.py and ExportImportInfo, TestScope from test_scope.py
into panther-ivy-types package.
```

## Files Modified
- `packages/panther-ivy-types/panther_ivy_types/analysis.py` (populated)
- `packages/panther-ivy-types/panther_ivy_types/scope.py` (populated)
- `packages/panther-ivy-types/tests/test_analysis_types.py` (new)
- `packages/panther-ivy-types/tests/test_scope_types.py` (new)
