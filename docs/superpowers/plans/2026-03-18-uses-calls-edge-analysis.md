# USES/CALLS Edge Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CALLS, USES, MONITORS, and CONTAINS edges to the ivy-lsp semantic model, enabling symbol-to-symbol cross-reference analysis for impact analysis and call hierarchy features.

**Architecture:** Extend `ExtractionResult` with a `SymbolReference` list populated by each extraction tier (AST-based for Tier 1, regex for Tier 2/3). Wire references into `SemanticModel` edges in `model_builder`. Refactor `call_hierarchy.py` to query semantic edges instead of brute-force regex scanning.

**Tech Stack:** Python 3.10+, lsprotocol, ivy (optional for Tier 1), pytest

**Root:** All relative paths below are under `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

**Test command:** `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q`

---

### Task 1: Add SymbolReference dataclass and CALLS/USES edge types

**Files:**
- Modify: `ivy_lsp/parsing/symbols.py` (add `SymbolReference` after `IvySymbol` at ~line 58)
- Modify: `ivy_lsp/semantic/edges.py` (add `CALLS`, `USES` to enum at ~line 36)
- Test: `tests/test_reference_extraction.py` (NEW)

- [ ] **Step 1: Write failing test for SymbolReference**

Create `tests/test_reference_extraction.py`:

```python
"""Tests for SymbolReference extraction from Ivy source."""
from __future__ import annotations

import pytest

from ivy_lsp.parsing.symbols import SymbolReference


class TestSymbolReference:
    """SymbolReference dataclass basics."""

    @pytest.mark.unit
    def test_create_call_reference(self):
        ref = SymbolReference(
            source_name="process",
            target_name="connect",
            kind="call",
            line=7,
            col=4,
            file_path="/tmp/proto.ivy",
        )
        assert ref.source_name == "process"
        assert ref.target_name == "connect"
        assert ref.kind == "call"

    @pytest.mark.unit
    def test_create_instance_reference(self):
        ref = SymbolReference(
            source_name="client",
            target_name="endpoint.client_endpoint",
            kind="instance",
            line=3,
        )
        assert ref.kind == "instance"

    @pytest.mark.unit
    def test_create_monitor_reference(self):
        ref = SymbolReference(
            source_name="before connect",
            target_name="connect",
            kind="monitor",
            line=10,
        )
        assert ref.kind == "monitor"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reference_extraction.py::TestSymbolReference -v`
Expected: `ImportError: cannot import name 'SymbolReference' from 'ivy_lsp.parsing.symbols'`

- [ ] **Step 3: Implement SymbolReference in symbols.py**

Add after line 58 (after `IvySymbol.from_dict`) in `ivy_lsp/parsing/symbols.py`:

```python
# In the existing import on line 12, add Literal:
# from typing import Dict, List, Literal, Optional, Set, Tuple

@dataclass
class SymbolReference:
    """A reference from one symbol's scope to another symbol.

    Attributes:
        source_name: Qualified name of the containing symbol.
        target_name: Name of the referenced symbol (may be unqualified).
        kind: The type of reference.
        line: 0-based line number where the reference occurs.
        col: 0-based column of the reference token.
        file_path: File where the reference is found.
    """

    source_name: str
    target_name: str
    kind: Literal["call", "instance", "monitor"]
    line: int
    col: int = 0
    file_path: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reference_extraction.py::TestSymbolReference -v`
Expected: 3 passed

- [ ] **Step 5: Write failing test for new edge types**

Add to `tests/test_reference_extraction.py`:

```python
from ivy_lsp.semantic.edges import SemanticEdgeType


class TestEdgeTypes:
    @pytest.mark.unit
    def test_calls_edge_type_exists(self):
        assert SemanticEdgeType.CALLS.value == "calls"

    @pytest.mark.unit
    def test_uses_edge_type_exists(self):
        assert SemanticEdgeType.USES.value == "uses"

    @pytest.mark.unit
    def test_monitors_edge_type_exists(self):
        """MONITORS already exists but verify it's there."""
        assert SemanticEdgeType.MONITORS.value == "monitors"

    @pytest.mark.unit
    def test_contains_edge_type_exists(self):
        """CONTAINS already exists but verify it's there."""
        assert SemanticEdgeType.CONTAINS.value == "contains"
```

- [ ] **Step 6: Run test to verify CALLS/USES fail**

Run: `python -m pytest tests/test_reference_extraction.py::TestEdgeTypes -v`
Expected: FAIL for `test_calls_edge_type_exists` and `test_uses_edge_type_exists`

- [ ] **Step 7: Add CALLS and USES to SemanticEdgeType**

In `ivy_lsp/semantic/edges.py`, add after line 36 (`COVERS = "covers"`):

```python
    CALLS = "calls"  # action A invokes action B
    USES = "uses"  # instance X instantiates module Y
```

- [ ] **Step 8: Run all tests to verify pass + no regressions**

Run: `python -m pytest tests/test_reference_extraction.py -v && python -m pytest tests/ -x -q`
Expected: All pass (2191+ tests)

- [ ] **Step 9: Commit**

```bash
git add ivy_lsp/parsing/symbols.py ivy_lsp/semantic/edges.py tests/test_reference_extraction.py
git commit -m "feat: add SymbolReference dataclass and CALLS/USES edge types"
```

---

### Task 2: Extend ExtractionResult with references and add Tier 3 regex extraction

**Files:**
- Modify: `ivy_lsp/parsing/tiered_extractor.py` (extend ExtractionResult, add regex ref extraction to `_try_regex`)
- Test: `tests/test_reference_extraction.py` (add Tier 3 tests)

- [ ] **Step 1: Write failing tests for Tier 3 reference extraction**

Add to `tests/test_reference_extraction.py`:

```python
from ivy_lsp.parsing.tiered_extractor import TieredExtractor


SAMPLE_IVY = """\
#lang ivy1.7

type cid

action connect(src:cid, dst:cid)

action process(c:cid) = {
    call connect(c, c);
}

instance client : endpoint.quic_ep(addr, port)

before connect {
    require src ~= dst;
}
"""


class TestTier3ReferenceExtraction:
    """Tier 3 (regex) should extract SymbolReferences."""

    @pytest.mark.unit
    def test_extraction_result_has_references_field(self):
        ext = TieredExtractor()
        result = ext.extract(SAMPLE_IVY, "/tmp/test.ivy")
        assert hasattr(result, "references")
        assert isinstance(result.references, list)

    @pytest.mark.unit
    def test_extracts_call_reference(self):
        ext = TieredExtractor()
        result = ext.extract(SAMPLE_IVY, "/tmp/test.ivy")
        calls = [r for r in result.references if r.kind == "call"]
        assert len(calls) >= 1
        assert any(r.target_name == "connect" for r in calls)

    @pytest.mark.unit
    def test_extracts_instance_reference(self):
        ext = TieredExtractor()
        result = ext.extract(SAMPLE_IVY, "/tmp/test.ivy")
        instances = [r for r in result.references if r.kind == "instance"]
        assert len(instances) >= 1
        assert any(r.source_name == "client" for r in instances)
        assert any(r.target_name == "endpoint.quic_ep" for r in instances)

    @pytest.mark.unit
    def test_extracts_monitor_reference(self):
        ext = TieredExtractor()
        result = ext.extract(SAMPLE_IVY, "/tmp/test.ivy")
        monitors = [r for r in result.references if r.kind == "monitor"]
        assert len(monitors) >= 1
        assert any(r.target_name == "connect" for r in monitors)

    @pytest.mark.unit
    def test_call_reference_has_source_name(self):
        ext = TieredExtractor()
        result = ext.extract(SAMPLE_IVY, "/tmp/test.ivy")
        calls = [r for r in result.references if r.kind == "call"]
        # The call to connect is inside action process
        assert any(r.source_name == "process" for r in calls)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_reference_extraction.py::TestTier3ReferenceExtraction -v`
Expected: FAIL (no `references` attribute or empty list)

- [ ] **Step 3: Add `references` field to ExtractionResult**

In `ivy_lsp/parsing/tiered_extractor.py`:

Add import at top:
```python
from ivy_lsp.parsing.symbols import IvySymbol, SymbolReference
```

Add field to `ExtractionResult` (after `includes` field):
```python
    references: List[SymbolReference] = field(default_factory=list)
```

- [ ] **Step 4: Add regex patterns and extraction helpers**

Add module-level regexes after existing pattern definitions (~line 89):

```python
# Reference extraction patterns (Tier 3 / Tier 2 fallback)
_CALL_STMT_RE = re.compile(r"call\s+([\w.]+)\s*\(", re.MULTILINE)
_INSTANCE_RE = re.compile(r"^\s*instance\s+([\w.]+)\s*:\s*([\w.]+)", re.MULTILINE)
_MONITOR_RE = re.compile(r"^\s*(before|after|around)\s+([\w.]+)", re.MULTILINE)
```

Add helper function before `TieredExtractor` class:

```python
def _find_enclosing_action(
    line_no: int,
    symbols: List[IvySymbol],
) -> Optional[str]:
    """Find the action symbol whose range encloses *line_no*.

    Returns the action name or None if no enclosing action is found.
    """
    best_name: Optional[str] = None
    best_line = -1
    for sym in symbols:
        if sym.kind != SymbolKind.Function:
            continue
        sym_line = sym.range[0]
        if sym_line <= line_no and sym_line > best_line:
            best_name = sym.name
            best_line = sym_line
    return best_name


def _extract_references_regex(
    source: str,
    filepath: str,
    symbols: List[IvySymbol],
) -> List[SymbolReference]:
    """Extract SymbolReferences using regex patterns (Tier 2/3 fallback)."""
    refs: List[SymbolReference] = []
    lines = source.split("\n")

    # CALLS: explicit "call foo(...)" statements
    for m in _CALL_STMT_RE.finditer(source):
        target = m.group(1)
        line_no = source[: m.start()].count("\n")
        col = m.start() - source.rfind("\n", 0, m.start()) - 1
        enclosing = _find_enclosing_action(line_no, symbols)
        if enclosing and enclosing != target.split(".")[-1]:
            refs.append(
                SymbolReference(
                    source_name=enclosing,
                    target_name=target,
                    kind="call",
                    line=line_no,
                    col=col,
                    file_path=filepath,
                )
            )

    # INSTANCES: "instance X : module.name(...)"
    for m in _INSTANCE_RE.finditer(source):
        instance_name = m.group(1)
        module_name = m.group(2)
        line_no = source[: m.start()].count("\n")
        refs.append(
            SymbolReference(
                source_name=instance_name,
                target_name=module_name,
                kind="instance",
                line=line_no,
                file_path=filepath,
            )
        )

    # MONITORS: "before/after/around action_name"
    for m in _MONITOR_RE.finditer(source):
        monitor_kind = m.group(1)
        target_action = m.group(2)
        line_no = source[: m.start()].count("\n")
        refs.append(
            SymbolReference(
                source_name=f"{monitor_kind} {target_action}",
                target_name=target_action,
                kind="monitor",
                line=line_no,
                file_path=filepath,
            )
        )

    return refs
```

- [ ] **Step 5: Update `_try_regex()` to return references**

Change `_try_regex()` return type and body (the last 2 lines):

```python
    def _try_regex(
        self, source: str, filepath: str
    ) -> Tuple[List[IvySymbol], List[str], List[SymbolReference]]:
        """Tier 3: Regex-based extraction (always succeeds)."""
        # ... existing symbol extraction code stays the same ...

        # Includes
        includes = INCLUDE_PATTERN.findall(source)

        # References (new)
        references = _extract_references_regex(source, filepath, symbols)

        return symbols, includes, references
```

- [ ] **Step 6: Update `_try_lexer()` to return references**

Change return type and add reference extraction at end of `_try_lexer()`:

```python
    def _try_lexer(
        self, source: str, filepath: str
    ) -> Tuple[List[IvySymbol], List[str], List[SymbolReference]]:
        # ... existing code ...

        # Extract references using regex fallback (lexer doesn't provide body analysis)
        references = _extract_references_regex(source, filepath, declaration_symbols)

        return declaration_symbols, includes, references
```

- [ ] **Step 7: Update `_try_parser()` to return references**

Change return type (references will be added in Task 3; for now return empty):

```python
    def _try_parser(
        self, source: str, filepath: str
    ) -> Tuple[List[IvySymbol], List[str], List[SymbolReference]]:
        # ... existing code ...
        return symbols, includes, []  # AST references added in Task 3
```

- [ ] **Step 8: Update `extract()` to unpack the third element**

In the `extract()` method, update all three tier success paths to unpack `references`.
The unpack lines are at approximately: line 147 (Tier 1), line 190 (Tier 2), and line 231 (Tier 3) of `tiered_extractor.py`.
Change `symbols, includes = self._try_*()` to `symbols, includes, references = self._try_*()` and add `references=references` to the `ExtractionResult` constructor:

```python
        # Tier 1 success path:
        symbols, includes, references = self._try_parser(source, filepath)
        # ...
        return ExtractionResult(
            symbols=symbols, includes=includes, references=references,
            tier_used=1, timing_ms=elapsed, errors=errors,
        )

        # Tier 2 success path:
        symbols, includes, references = self._try_lexer(source, filepath)
        # ...
        return ExtractionResult(
            symbols=symbols, includes=includes, references=references,
            tier_used=2, timing_ms=elapsed, errors=errors,
        )

        # Tier 3 success path:
        symbols, includes, references = self._try_regex(source, filepath)
        # ...
        return ExtractionResult(
            symbols=symbols, includes=includes, references=references,
            tier_used=3, timing_ms=elapsed, errors=errors,
        )
```

- [ ] **Step 9: Run tests to verify pass + no regressions**

Run: `python -m pytest tests/test_reference_extraction.py -v && python -m pytest tests/ -x -q`
Expected: All pass

- [ ] **Step 10: Commit**

```bash
git add ivy_lsp/parsing/tiered_extractor.py tests/test_reference_extraction.py
git commit -m "feat: extend ExtractionResult with references, add Tier 3 regex extraction"
```

---

### Task 3: Add Tier 1 AST reference extraction

**Files:**
- Modify: `ivy_lsp/parsing/ast_to_symbols.py` (add `extract_references_from_ast()`)
- Modify: `ivy_lsp/parsing/tiered_extractor.py` (wire into `_try_parser()`)
- Test: `tests/test_reference_extraction.py` (add AST extraction tests)

- [ ] **Step 1: Write failing test for AST reference extraction**

Add to `tests/test_reference_extraction.py`:

```python
class TestTier1ASTReferenceExtraction:
    """Tier 1 (AST) should extract SymbolReferences from parsed AST."""

    @pytest.mark.unit
    def test_extract_references_from_ast_importable(self):
        from ivy_lsp.parsing.ast_to_symbols import extract_references_from_ast
        assert callable(extract_references_from_ast)

    @pytest.mark.unit
    def test_ast_extracts_call_references(self):
        """If Ivy parser is available, AST extraction should find calls."""
        try:
            from ivy_lsp.parsing.parser_session import IvyParserWrapper
        except ImportError:
            pytest.skip("Ivy parser not available")

        from ivy_lsp.parsing.ast_to_symbols import extract_references_from_ast

        source = (
            "#lang ivy1.7\n"
            "type cid\n"
            "action connect(src:cid, dst:cid)\n"
            "action process(c:cid) = {\n"
            "    call connect(c, c);\n"
            "}\n"
        )
        wrapper = IvyParserWrapper()
        result = wrapper.parse(source, filename="/tmp/test.ivy", timeout=5.0)
        if not result.success or result.ast is None:
            pytest.skip("Parse failed")

        refs = extract_references_from_ast(result.ast, "/tmp/test.ivy", source)
        calls = [r for r in refs if r.kind == "call"]
        assert len(calls) >= 1
        assert any(r.target_name == "connect" for r in calls)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reference_extraction.py::TestTier1ASTReferenceExtraction -v`
Expected: `ImportError: cannot import name 'extract_references_from_ast'`

- [ ] **Step 3: Implement `extract_references_from_ast()`**

Add to `ivy_lsp/parsing/ast_to_symbols.py` after the `ast_to_symbols()` function:

```python
def extract_references_from_ast(
    ivy_obj: Any, filename: str, source: str
) -> List["SymbolReference"]:
    """Extract cross-references (calls, instances, monitors) from a parsed Ivy AST.

    Walks the same declaration list as ``ast_to_symbols()`` but extracts
    references rather than symbol definitions.
    """
    from ivy_lsp.parsing.symbols import SymbolReference

    if ivy_obj is None or not hasattr(ivy_obj, "decls"):
        return []

    refs: List[SymbolReference] = []
    abs_filename = os.path.abspath(filename) if filename else filename

    for decl in ivy_obj.decls:
        try:
            if is_from_included_file(decl, abs_filename):
                continue
            refs.extend(_extract_refs_from_decl(decl, filename))
        except Exception:
            logger.debug(
                "Failed to extract references from %s in %s",
                type(decl).__name__,
                filename,
                exc_info=True,
            )

    return refs


def _extract_refs_from_decl(decl: Any, filename: str) -> List["SymbolReference"]:
    """Extract references from a single AST declaration."""
    import ivy.ivy_ast as ia

    from ivy_lsp.parsing.symbols import SymbolReference

    refs: List[SymbolReference] = []

    # CALLS: walk action bodies for CallAction nodes
    if isinstance(decl, ia.ActionDecl):
        defs = decl.defines()
        if not defs:
            return refs
        action_name = defs[0][0]
        try:
            action_def = decl.args[0]  # ActionDef
            body = getattr(action_def, "body", None)
            if body is not None:
                refs.extend(
                    _extract_calls_from_body(body, action_name, filename)
                )
        except (IndexError, AttributeError):
            pass

    # USES: instance declarations
    elif isinstance(decl, ia.InstantiateDecl):
        defs = decl.defines()
        if defs:
            instance_name = defs[0][0]
            module_name = _extract_instantiate_target(decl)
            if module_name:
                lineno = getattr(decl, "lineno", None)
                line = (getattr(lineno, "line", 0) or 0) - 1
                refs.append(
                    SymbolReference(
                        source_name=instance_name,
                        target_name=module_name,
                        kind="instance",
                        line=max(0, line),
                        file_path=filename,
                    )
                )

    # MONITORS: mixin declarations (before/after/around)
    elif isinstance(decl, ia.MixinDecl):
        mixer_name, mixee_name, kind = _extract_mixin_info(decl)
        if mixer_name and mixee_name:
            lineno = getattr(decl, "lineno", None)
            line = (getattr(lineno, "line", 0) or 0) - 1
            refs.append(
                SymbolReference(
                    source_name=f"{kind} {mixee_name}" if kind else mixer_name,
                    target_name=mixee_name,
                    kind="monitor",
                    line=max(0, line),
                    file_path=filename,
                )
            )

    return refs


def _extract_calls_from_body(
    body: Any, action_name: str, filename: str
) -> List["SymbolReference"]:
    """Recursively walk an action body AST to find call references."""
    from ivy_lsp.parsing.symbols import SymbolReference

    refs: List[SymbolReference] = []

    try:
        import ivy.ivy_actions as iact
    except ImportError:
        return refs

    if isinstance(body, iact.CallAction):
        if body.args:
            callee_atom = body.args[0]
            callee = getattr(callee_atom, "relname", None)
            if callee and callee != action_name:
                lineno = getattr(body, "lineno", None)
                line = (getattr(lineno, "line", 0) or 0) - 1
                refs.append(
                    SymbolReference(
                        source_name=action_name,
                        target_name=callee,
                        kind="call",
                        line=max(0, line),
                        file_path=filename,
                    )
                )

    # Recurse into compound actions
    for arg in getattr(body, "args", ()):
        if arg is not None:
            refs.extend(_extract_calls_from_body(arg, action_name, filename))

    return refs


def _extract_instantiate_target(decl: Any) -> Optional[str]:
    """Extract the module name from an InstantiateDecl."""
    try:
        app = decl.args[0]  # The application expression
        func = getattr(app, "func", None) or (app.args[0] if app.args else None)
        name = getattr(func, "relname", None) or getattr(func, "rep", None)
        return str(name) if name else None
    except (IndexError, AttributeError):
        return None


def _extract_mixin_info(decl: Any) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract (mixer_name, mixee_name, kind) from a MixinDecl.

    Returns (None, None, None) on failure.
    """
    try:
        mixer_atom = decl.args[0] if decl.args else None
        mixer_name = _atom_name(mixer_atom) if mixer_atom else None
        mixee = getattr(decl, "mixee", None)
        mixee_name = _atom_name(mixee) if mixee else None
        kind = getattr(decl, "kind", None)
        if kind is None:
            # Heuristic: check mixer name for before/after prefix
            if mixer_name:
                for prefix in ("before_", "after_", "around_"):
                    if mixer_name.startswith(prefix):
                        kind = prefix.rstrip("_")
                        break
        return mixer_name, mixee_name, kind
    except (IndexError, AttributeError):
        return None, None, None
```

- [ ] **Step 4: Wire into `_try_parser()` in tiered_extractor.py**

Update `_try_parser()` to call `extract_references_from_ast()`:

```python
    def _try_parser(
        self, source: str, filepath: str
    ) -> Tuple[List[IvySymbol], List[str], List[SymbolReference]]:
        from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols, extract_references_from_ast
        from ivy_lsp.parsing.parser_session import IvyParserWrapper

        wrapper = IvyParserWrapper(resolve_callback=self._resolve_callback)
        result = wrapper.parse(source, filename=filepath, timeout=self._parser_timeout)

        if not result.success or result.ast is None:
            error_msgs = [str(e) for e in result.errors[:3]]
            raise RuntimeError(
                f"Parse failed with {len(result.errors)} error(s): "
                + "; ".join(error_msgs)
            )

        symbols = ast_to_symbols(result.ast, filepath, source)
        includes = _extract_includes_from_ast(result.ast)
        references = extract_references_from_ast(result.ast, filepath, source)

        return symbols, includes, references
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_reference_extraction.py -v && python -m pytest tests/ -x -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add ivy_lsp/parsing/ast_to_symbols.py ivy_lsp/parsing/tiered_extractor.py tests/test_reference_extraction.py
git commit -m "feat: add Tier 1 AST reference extraction for CALLS, USES, MONITORS"
```

---

### Task 4: Wire CALLS, USES, MONITORS, CONTAINS edges in model_builder

**Files:**
- Modify: `ivy_lsp/semantic/model_builder.py` (add edge wiring sections)
- Test: `tests/test_semantic_model.py` (add edge wiring tests)

- [ ] **Step 1: Write failing tests for edge wiring**

Add to `tests/test_semantic_model.py` (or create if needed):

```python
"""Tests for CALLS/USES/MONITORS/CONTAINS edge wiring in model_builder."""
import pytest

from ivy_lsp.parsing.symbols import SymbolReference
from ivy_lsp.semantic.edges import SemanticEdgeType
from ivy_lsp.semantic.model import SemanticModel
from ivy_lsp.semantic.nodes import SymbolNode


def _make_model_with_symbols():
    """Build a minimal SemanticModel with action symbols for edge testing."""
    model = SemanticModel()
    model.add_node(
        SymbolNode(
            id="/tmp/test.ivy:5:connect",
            name="connect",
            qualified_name="connect",
            kind="action",
            file="/tmp/test.ivy",
            line=5,
        )
    )
    model.add_node(
        SymbolNode(
            id="/tmp/test.ivy:8:process",
            name="process",
            qualified_name="process",
            kind="action",
            file="/tmp/test.ivy",
            line=8,
        )
    )
    model.add_node(
        SymbolNode(
            id="/tmp/test.ivy:12:endpoint",
            name="endpoint",
            qualified_name="endpoint",
            kind="module",
            file="/tmp/test.ivy",
            line=12,
        )
    )
    model.add_node(
        SymbolNode(
            id="/tmp/test.ivy:14:client",
            name="client",
            qualified_name="client",
            kind="instance",
            file="/tmp/test.ivy",
            line=14,
        )
    )
    # Nested symbol for CONTAINS test
    model.add_node(
        SymbolNode(
            id="/tmp/test.ivy:16:endpoint.send",
            name="send",
            qualified_name="endpoint.send",
            kind="action",
            file="/tmp/test.ivy",
            line=16,
        )
    )
    return model


class TestEdgeWiring:
    @pytest.mark.unit
    def test_calls_edges_wired(self):
        from ivy_lsp.semantic.model_builder import _wire_semantic_edges

        model = _make_model_with_symbols()
        refs = [
            SymbolReference(
                source_name="process",
                target_name="connect",
                kind="call",
                line=9,
                file_path="/tmp/test.ivy",
            )
        ]
        _wire_semantic_edges(model, {}, {}, {"/tmp/test.ivy": refs})
        outgoing = model.get_outgoing(
            "/tmp/test.ivy:8:process", SemanticEdgeType.CALLS
        )
        assert len(outgoing) == 1
        assert outgoing[0][1] == "/tmp/test.ivy:5:connect"

    @pytest.mark.unit
    def test_uses_edges_wired(self):
        from ivy_lsp.semantic.model_builder import _wire_semantic_edges

        model = _make_model_with_symbols()
        refs = [
            SymbolReference(
                source_name="client",
                target_name="endpoint",
                kind="instance",
                line=14,
                file_path="/tmp/test.ivy",
            )
        ]
        _wire_semantic_edges(model, {}, {}, {"/tmp/test.ivy": refs})
        outgoing = model.get_outgoing(
            "/tmp/test.ivy:14:client", SemanticEdgeType.USES
        )
        assert len(outgoing) == 1
        assert outgoing[0][1] == "/tmp/test.ivy:12:endpoint"

    @pytest.mark.unit
    def test_contains_edges_wired_from_qualified_names(self):
        from ivy_lsp.semantic.model_builder import _wire_semantic_edges

        model = _make_model_with_symbols()
        _wire_semantic_edges(model, {}, {}, {})
        outgoing = model.get_outgoing(
            "/tmp/test.ivy:12:endpoint", SemanticEdgeType.CONTAINS
        )
        assert len(outgoing) == 1
        assert outgoing[0][1] == "/tmp/test.ivy:16:endpoint.send"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_semantic_model.py::TestEdgeWiring -v`
Expected: `TypeError: _wire_semantic_edges() takes 3 positional arguments but 4 were given` (or similar)

- [ ] **Step 3: Update `_wire_semantic_edges()` signature and add edge wiring**

In `ivy_lsp/semantic/model_builder.py`, update `_wire_semantic_edges`:

1. Add `file_references` parameter
2. Build symbol name→id index
3. Add sections 4-7 for CALLS, USES, MONITORS, CONTAINS

```python
def _wire_semantic_edges(
    model: Any,
    basename_to_path: dict[str, str],
    file_includes: dict[str, list[str]],
    file_references: dict[str, list] | None = None,
) -> None:
    """Wire COVERS, HAS_PARAM, RETURNS_TYPE, INCLUDES, CALLS, USES, MONITORS, CONTAINS edges."""
    from ivy_lsp.semantic.edges import SemanticEdgeType
    from ivy_lsp.semantic.nodes import (
        RfcAnnotation,
        RfcRequirement,
        SymbolNode,
        TypeNode,
    )
    from ivy_lsp.semantic.rfc_annotations import normalize_tag_to_manifest_ids

    # ... existing sections 1-3 (COVERS, HAS_PARAM/RETURNS_TYPE, INCLUDES) unchanged ...

    # -- Build symbol name index for cross-reference resolution --
    symbol_by_name: dict[str, str] = {}
    symbol_by_qname: dict[str, str] = {}
    for sn in model.get_nodes_by_type(SymbolNode):
        symbol_by_name.setdefault(sn.name, sn.id)
        symbol_by_qname[sn.qualified_name] = sn.id

    def _resolve(name: str) -> str | None:
        return symbol_by_qname.get(name) or symbol_by_name.get(name)

    # 4. CALLS / USES / MONITORS from extracted references
    if file_references:
        for refs in file_references.values():
            for ref in refs:
                src_id = _resolve(ref.source_name)
                tgt_id = _resolve(ref.target_name)
                if not src_id or not tgt_id:
                    continue
                if ref.kind == "call":
                    model.add_edge(src_id, SemanticEdgeType.CALLS, tgt_id)
                elif ref.kind == "instance":
                    model.add_edge(src_id, SemanticEdgeType.USES, tgt_id)
                elif ref.kind == "monitor":
                    model.add_edge(src_id, SemanticEdgeType.MONITORS, tgt_id)

    # 5. CONTAINS from qualified name hierarchy
    for sn in model.get_nodes_by_type(SymbolNode):
        if "." in sn.qualified_name:
            parent_qname = sn.qualified_name.rsplit(".", 1)[0]
            parent_id = symbol_by_qname.get(parent_qname)
            if parent_id:
                model.add_edge(parent_id, SemanticEdgeType.CONTAINS, sn.id)
    for tn in model.get_nodes_by_type(TypeNode):
        if "." in tn.qualified_name:
            parent_qname = tn.qualified_name.rsplit(".", 1)[0]
            parent_id = symbol_by_qname.get(parent_qname)
            if parent_id:
                model.add_edge(parent_id, SemanticEdgeType.CONTAINS, tn.id)
```

- [ ] **Step 4: Update `build_semantic_model()` to cache and pass references**

Add `file_references` dict alongside `file_includes`, cache `result.references`, pass to `_wire_semantic_edges`:

```python
    file_references: dict[str, list] = {}
    # ... in the scan loop, after file_includes[abs_path] = result.includes:
    file_references[abs_path] = result.references

    # ... at the end:
    _wire_semantic_edges(model, basename_to_path, file_includes, file_references)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_semantic_model.py::TestEdgeWiring -v && python -m pytest tests/ -x -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add ivy_lsp/semantic/model_builder.py tests/test_semantic_model.py
git commit -m "feat: wire CALLS, USES, MONITORS, CONTAINS edges in model_builder"
```

---

### Task 5: Wire Tier 3 compiled edges in graph_enrichment

**Files:**
- Modify: `ivy_lsp/compilation/graph_enrichment.py`
- Test: `tests/test_graph_enrichment.py` (update)

- [ ] **Step 1: Write failing test for MONITORS edges from ir.mixins**

Add to `tests/test_graph_enrichment.py`:

```python
@pytest.mark.unit
def test_monitors_edges_from_mixins():
    from ivy_lsp.compilation.graph_enrichment import enrich_semantic_model
    from ivy_lsp.compilation.ir import ActionIR, CompiledModuleIR, MixinIR
    from ivy_lsp.semantic.edges import SemanticEdgeType
    from ivy_lsp.semantic.model import SemanticModel

    model = SemanticModel()
    ir = CompiledModuleIR(
        actions={
            "connect": ActionIR(name="connect"),
            "ext:before_connect": ActionIR(name="ext:before_connect"),
        },
        mixins={
            "connect": (
                MixinIR(mixer="ext:before_connect", mixee="connect", kind="before"),
            ),
        },
        success=True,
        source_file="/tmp/test.ivy",
    )
    enrich_semantic_model(model, ir, "/tmp/test.ivy")

    mixer_id = "compiled:/tmp/test.ivy:ext:before_connect"
    outgoing = model.get_outgoing(mixer_id, SemanticEdgeType.MONITORS)
    assert len(outgoing) >= 1


@pytest.mark.unit
def test_contains_edges_from_hierarchy():
    from ivy_lsp.compilation.graph_enrichment import enrich_semantic_model
    from ivy_lsp.compilation.ir import ActionIR, CompiledModuleIR
    from ivy_lsp.semantic.edges import SemanticEdgeType
    from ivy_lsp.semantic.model import SemanticModel

    model = SemanticModel()
    ir = CompiledModuleIR(
        actions={
            "packet": ActionIR(name="packet"),
            "packet.encode": ActionIR(name="packet.encode"),
        },
        hierarchy={"packet": frozenset({"packet.encode"})},
        success=True,
        source_file="/tmp/test.ivy",
    )
    enrich_semantic_model(model, ir, "/tmp/test.ivy")

    parent_id = "compiled:/tmp/test.ivy:packet"
    outgoing = model.get_outgoing(parent_id, SemanticEdgeType.CONTAINS)
    assert len(outgoing) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_graph_enrichment.py::test_monitors_edges_from_mixins tests/test_graph_enrichment.py::test_contains_edges_from_hierarchy -v`
Expected: FAIL (no MONITORS/CONTAINS edges)

- [ ] **Step 3: Add MONITORS and CONTAINS edge wiring to `enrich_semantic_model()`**

In `ivy_lsp/compilation/graph_enrichment.py`, add after the Actions section (before `model.update_file`):

```python
    # --- Mixins -> MONITORS edges ---
    for action_name, mixin_tuple in ir.mixins.items():
        for mixin in mixin_tuple:
            mixer_id = f"compiled:{filepath}:{mixin.mixer}"
            mixee_id = f"compiled:{filepath}:{mixin.mixee}"
            edges.append((mixer_id, SemanticEdgeType.MONITORS, mixee_id))

    # --- Hierarchy -> CONTAINS edges ---
    # Note: parent_name may be a module/object only in ir.symbols, not ir.actions.
    # Build a set of all known node IDs to guard against orphan edges.
    known_ids = {f"compiled:{filepath}:{n}" for n in (*ir.actions, *ir.symbols, *ir.sorts)}
    for parent_name, children in ir.hierarchy.items():
        parent_id = f"compiled:{filepath}:{parent_name}"
        if parent_id not in known_ids:
            continue
        for child_name in children:
            child_id = f"compiled:{filepath}:{child_name}"
            if child_id in known_ids:
                edges.append((parent_id, SemanticEdgeType.CONTAINS, child_id))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_graph_enrichment.py -v && python -m pytest tests/ -x -q`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/compilation/graph_enrichment.py tests/test_graph_enrichment.py
git commit -m "feat: wire MONITORS and CONTAINS edges from compiled IR in graph_enrichment"
```

---

### Task 6: Update traceability tool — remove "not yet implemented" message

**Files:**
- Modify: `ivy_lsp/tools/traceability.py` (lines 455-462 and 522-526)
- Modify: `tests/test_tools_traceability.py` (update assertion)

- [ ] **Step 1: Update the test assertion first**

In `tests/test_tools_traceability.py`, change `TestImpactAnalysisNote.test_impact_analysis_has_fx5_note_code`:

```python
class TestImpactAnalysisNote:
    def test_impact_analysis_has_fx5_note_code(self):
        """The impact analysis should report when no edges found."""
        from ivy_lsp.tools import traceability

        source = Path(traceability.__file__).read_text()
        # Updated: no longer says "not yet implemented"
        assert "No cross-reference edges found for this symbol" in source
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tools_traceability.py::TestImpactAnalysisNote -v`
Expected: FAIL (old message still present)

- [ ] **Step 3: Update traceability.py**

In `ivy_lsp/tools/traceability.py`:

1. Update the docstring (lines 455-462) — remove the `.. note::` block:

```python
    async def _ivy_impact_analysis(symbol_name: str) -> str:
        """Analyze incoming and outgoing edges for a symbol.

        Returns edges from the semantic model graph including COVERS,
        HAS_PARAM, RETURNS_TYPE, INCLUDES, CALLS, USES, MONITORS,
        and CONTAINS edges.
        """
```

2. Update the fallback note (lines 522-526):

```python
            else:
                result["note"] = (
                    "No cross-reference edges found for this symbol."
                )
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_tools_traceability.py -v && python -m pytest tests/ -x -q`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/tools/traceability.py tests/test_tools_traceability.py
git commit -m "fix: replace 'USES/CALLS not implemented' note with accurate message"
```

---

### Task 7: Refactor call_hierarchy.py to use semantic edges

**Files:**
- Modify: `ivy_lsp/features/call_hierarchy.py`
- Modify: `tests/test_call_hierarchy.py` (add model-based tests)

- [ ] **Step 1: Write failing tests for model-based call hierarchy**

Add to `tests/test_call_hierarchy.py`:

```python
from ivy_lsp.semantic.edges import SemanticEdgeType
from ivy_lsp.semantic.model import SemanticModel
from ivy_lsp.semantic.nodes import SymbolNode


def _make_model_for_call_hierarchy(tmp_path):
    """Build a SemanticModel with CALLS edges matching SAMPLE_SOURCE."""
    filepath = str(tmp_path / "proto.ivy")
    model = SemanticModel()
    model.add_node(
        SymbolNode(
            id=f"{filepath}:5:connect",
            name="connect",
            qualified_name="connect",
            kind="action",
            file=filepath,
            line=5,
        )
    )
    model.add_node(
        SymbolNode(
            id=f"{filepath}:7:process",
            name="process",
            qualified_name="process",
            kind="action",
            file=filepath,
            line=7,
        )
    )
    # process CALLS connect
    model.add_edge(
        f"{filepath}:7:process",
        SemanticEdgeType.CALLS,
        f"{filepath}:5:connect",
    )
    return model


class TestIncomingCallsWithModel:
    @pytest.mark.unit
    def test_model_based_incoming_calls(self, tmp_path):
        ws = _make_workspace(tmp_path, {"proto.ivy": SAMPLE_SOURCE})
        indexer = _index(ws)
        filepath = str(tmp_path / "proto.ivy")
        model = _make_model_for_call_hierarchy(tmp_path)
        result = get_incoming_calls(indexer, "connect", filepath, model=model)
        assert len(result) >= 1
        caller_names = [call.from_.name for call in result]
        assert "process" in caller_names

    @pytest.mark.unit
    def test_fallback_when_model_is_none(self, tmp_path):
        ws = _make_workspace(tmp_path, {"proto.ivy": SAMPLE_SOURCE})
        indexer = _index(ws)
        filepath = str(tmp_path / "proto.ivy")
        result = get_incoming_calls(indexer, "connect", filepath, model=None)
        # Should still work via regex fallback
        assert len(result) >= 1


class TestOutgoingCallsWithModel:
    @pytest.mark.unit
    def test_model_based_outgoing_calls(self, tmp_path):
        ws = _make_workspace(tmp_path, {"proto.ivy": SAMPLE_SOURCE})
        indexer = _index(ws)
        filepath = str(tmp_path / "proto.ivy")
        model = _make_model_for_call_hierarchy(tmp_path)
        result = get_outgoing_calls(indexer, "process", filepath, model=model)
        assert len(result) >= 1
        callee_names = [call.to.name for call in result]
        assert "connect" in callee_names

    @pytest.mark.unit
    def test_fallback_when_model_is_none(self, tmp_path):
        ws = _make_workspace(tmp_path, {"proto.ivy": SAMPLE_SOURCE})
        indexer = _index(ws)
        filepath = str(tmp_path / "proto.ivy")
        result = get_outgoing_calls(indexer, "process", filepath, model=None)
        assert len(result) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_call_hierarchy.py::TestIncomingCallsWithModel tests/test_call_hierarchy.py::TestOutgoingCallsWithModel -v`
Expected: `TypeError: get_incoming_calls() got an unexpected keyword argument 'model'`

- [ ] **Step 3: Add model parameter and helpers to call_hierarchy.py**

Add helpers after existing helpers section:

```python
def _find_symbol_node_id(model, name: str, filepath: str) -> Optional[str]:
    """Find a SymbolNode matching *name* and *filepath* in the model."""
    from ivy_lsp.semantic.nodes import SymbolNode

    last = name.rsplit(".", 1)[-1] if "." in name else name
    for sn in model.get_nodes_by_type(SymbolNode):
        if sn.name == last and sn.file == filepath:
            return sn.id
    # Fallback: match by name only (cross-file)
    for sn in model.get_nodes_by_type(SymbolNode):
        if sn.name == last:
            return sn.id
    return None


def _node_to_call_hierarchy_item(model, node_id: str) -> Optional[lsp.CallHierarchyItem]:
    """Convert a semantic model node_id to a CallHierarchyItem."""
    node = model.get_node(node_id)
    if node is None:
        return None
    name = getattr(node, "name", "unknown")
    filepath = getattr(node, "file", "")
    line = max(0, getattr(node, "line", 1) - 1)  # 1-based to 0-based
    uri = Path(filepath).as_uri() if filepath else ""
    r = make_range(line, 0, line, len(name))
    return lsp.CallHierarchyItem(
        name=name,
        kind=lsp.SymbolKind.Function,
        uri=uri,
        range=r,
        selection_range=r,
        detail=getattr(node, "kind", ""),
    )
```

- [ ] **Step 4: Refactor `get_incoming_calls()` with model-first, regex-fallback**

```python
def get_incoming_calls(
    indexer,
    item_name: str,
    item_filepath: str,
    model=None,
) -> List[lsp.CallHierarchyIncomingCall]:
    """Find all actions/monitors that reference *item_name*."""
    # Model path: use semantic CALLS/MONITORS edges
    if model is not None:
        from ivy_lsp.semantic.edges import SemanticEdgeType

        node_id = _find_symbol_node_id(model, item_name, item_filepath)
        if node_id and model.get_node(node_id) is not None:
            results = []
            # Get CALLS + MONITORS incoming edges
            for edge_type in (SemanticEdgeType.CALLS, SemanticEdgeType.MONITORS):
                for _, src_id in model.get_incoming(node_id, edge_type):
                    item = _node_to_call_hierarchy_item(model, src_id)
                    if item is None:
                        continue
                    # Targeted regex for from_ranges (just the caller's body)
                    from_ranges = _targeted_from_ranges(
                        item.name, item_name, item_filepath, indexer
                    )
                    results.append(
                        lsp.CallHierarchyIncomingCall(
                            from_=item,
                            from_ranges=from_ranges or [item.range],
                        )
                    )
            if results:
                return results

    # Fallback: regex scanning (existing implementation)
    return _get_incoming_calls_regex(indexer, item_name, item_filepath)
```

Rename the existing `get_incoming_calls` body to `_get_incoming_calls_regex`.

- [ ] **Step 5: Add `_targeted_from_ranges()` helper**

```python
def _targeted_from_ranges(
    caller_name: str,
    target_name: str,
    target_filepath: str,
    indexer,
) -> List[lsp.Range]:
    """Find exact ranges where *target_name* appears in *caller_name*'s body."""
    last_component = target_name.rsplit(".", 1)[-1] if "." in target_name else target_name
    pattern = re.compile(r"\b" + re.escape(last_component) + r"\b")

    # Find caller's file and body
    results = indexer.lookup_symbol(caller_name) if indexer else []
    if not results:
        return []

    sl = results[0]
    fpath = sl.filepath
    if not fpath:
        return []

    try:
        source = Path(fpath).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    file_lines = source.split("\n")
    file_symbols = indexer.get_symbols(fpath)
    decl_line = sl.range[0]

    # Find end of caller's scope
    sorted_lines = sorted(set(s.range[0] for s in file_symbols))
    idx = sorted_lines.index(decl_line) if decl_line in sorted_lines else -1
    if idx >= 0 and idx + 1 < len(sorted_lines):
        end_line = sorted_lines[idx + 1]
    else:
        end_line = len(file_lines)

    ranges = []
    for line_idx in range(decl_line + 1, min(end_line, len(file_lines))):
        for match in pattern.finditer(file_lines[line_idx]):
            ranges.append(make_range(line_idx, match.start(), line_idx, match.end()))
    return ranges
```

- [ ] **Step 6: Refactor `get_outgoing_calls()` similarly**

```python
def get_outgoing_calls(
    indexer,
    item_name: str,
    item_filepath: str,
    model=None,
) -> List[lsp.CallHierarchyOutgoingCall]:
    """Find all actions referenced in the body of *item_name*."""
    if model is not None:
        from ivy_lsp.semantic.edges import SemanticEdgeType

        node_id = _find_symbol_node_id(model, item_name, item_filepath)
        if node_id and model.get_node(node_id) is not None:
            results = []
            for _, tgt_id in model.get_outgoing(node_id, SemanticEdgeType.CALLS):
                item = _node_to_call_hierarchy_item(model, tgt_id)
                if item is None:
                    continue
                from_ranges = _targeted_from_ranges(
                    item_name, item.name, item_filepath, indexer
                )
                results.append(
                    lsp.CallHierarchyOutgoingCall(
                        to=item,
                        from_ranges=from_ranges or [item.range],
                    )
                )
            if results:
                return results

    return _get_outgoing_calls_regex(indexer, item_name, item_filepath)
```

Rename the existing `get_outgoing_calls` body to `_get_outgoing_calls_regex`.

- [ ] **Step 7: Update `register()` handlers to pass model**

In the `incoming_calls` handler:
```python
return await loop.run_in_executor(
    None, get_incoming_calls, server.indexer, name, filepath,
    getattr(server, "semantic_model", None),
)
```

In the `outgoing_calls` handler:
```python
return await loop.run_in_executor(
    None, get_outgoing_calls, server.indexer, name, filepath,
    getattr(server, "semantic_model", None),
)
```

- [ ] **Step 8: Run tests**

Run: `python -m pytest tests/test_call_hierarchy.py -v && python -m pytest tests/ -x -q`
Expected: All pass (old tests use `model=None` fallback, new tests use model path)

- [ ] **Step 9: Commit**

```bash
git add ivy_lsp/features/call_hierarchy.py tests/test_call_hierarchy.py
git commit -m "refactor: call_hierarchy uses semantic CALLS edges with regex fallback"
```

---

### Task 8: Integration verification

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -x -q`
Expected: 2191+ tests pass, 0 failures

- [ ] **Step 2: Verify edge counts via MCP tools**

Use `ivy_model_summary` on the QUIC workspace and check for non-zero CALLS/USES/MONITORS/CONTAINS edge counts.

- [ ] **Step 3: Verify impact analysis works**

Use `ivy_query mode=impact symbol=quic_packet_event` — should return CALLS edges instead of the old "not yet implemented" note.

- [ ] **Step 4: Run nct-validate**

Run `/nct-validate` to ensure the QUIC workspace still passes all checks.

- [ ] **Step 5: Final commit if any fixups needed**

```bash
git add -u
git commit -m "fix: address integration test issues for USES/CALLS edge analysis"
```
