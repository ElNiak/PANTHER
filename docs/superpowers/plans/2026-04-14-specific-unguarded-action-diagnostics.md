# Specific Unguarded-Action Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic "Action modifies state" diagnostic with one that names the specific action and state variables being written without guards.

**Architecture:** Add an action-centric diagnostic to `coverage_hints.py` that maps WRITES edges to actions via line-range bucketing, then suppress the structural `unguarded-action` lint when graph-based hints are available.

**Tech Stack:** Python 3.10+, lsprotocol, pytest

**Base path:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

---

### Task 1: Register `ivy.action.unguardedWrite` in the codes registry

**Files:**
- Modify: `ivy_lsp/core/diagnostics/codes.py:237` (after `ivy.action.unexportedMonitor`)

- [ ] **Step 1: Add the new diagnostic descriptor**

Insert after line 237 (after the closing `)` of `ivy.action.unexportedMonitor`):

```python
_reg(
    DiagnosticDescriptor(
        code="ivy.action.unguardedWrite",
        title="Unguarded state writes in action '{action}'",
        explanation=(
            "Action writes state variables not guarded by any requirement. "
            "Add require/ensure clauses to constrain writes."
        ),
        default_severity=lsp.DiagnosticSeverity.Hint,
        source="ivy-semantic",
        has_quick_fix=True,
    )
)
```

- [ ] **Step 2: Verify import works**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "from ivy_lsp.core.diagnostics.codes import DIAGNOSTIC_REGISTRY; print('ivy.action.unguardedWrite' in DIAGNOSTIC_REGISTRY)"`

Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add ivy_lsp/core/diagnostics/codes.py
git commit -m "feat(diag): register ivy.action.unguardedWrite diagnostic code"
```

---

### Task 2: Write failing tests for the new coverage hint diagnostic

**Files:**
- Create: `tests/test_coverage_hints.py`

- [ ] **Step 1: Create the test file with three test cases**

```python
"""Tests for coverage_hints.compute_coverage_hints — action-centric unguarded writes."""

from ivy_lsp.core.analysis.requirement_graph import (
    ActionNode,
    EdgeType,
    RequirementGraph,
    RequirementNode,
    StateVarNode,
)
from ivy_lsp.core.coverage_hints import compute_coverage_hints

FILEPATH = "/fake/test.ivy"


def _make_graph_with_unguarded_action():
    """Graph: action 'send' at line 10 writes 'sent_pkt' (unguarded)."""
    g = RequirementGraph()
    g.add_action(ActionNode(
        id="send", name="send", qualified_name="send",
        file=FILEPATH, line=10,
    ))
    g.add_state_var(StateVarNode(
        id="sent_pkt", name="sent_pkt", qualified_name="sent_pkt",
        file=FILEPATH, line=5, is_relation=True,
    ))
    # Write edge: line 12 inside action send's body
    g.add_edge(f"{FILEPATH}:12:write:sent_pkt", EdgeType.WRITES, "sent_pkt")
    return g


def _make_graph_with_guarded_action():
    """Graph: action 'send' writes 'sent_pkt', but a requirement reads it."""
    g = _make_graph_with_unguarded_action()
    req = RequirementNode(
        id=f"{FILEPATH}:15:require",
        kind="require",
        formula_text="sent_pkt(S)",
        file=FILEPATH,
        line=15,
        monitor_action="send",
    )
    g.add_requirement(req)
    g.add_edge(req.id, EdgeType.CONSTRAINS, "send")
    g.add_edge(req.id, EdgeType.READS, "sent_pkt")
    return g


def test_unguarded_action_names_variables():
    """Action with unguarded write produces diagnostic naming the variable."""
    g = _make_graph_with_unguarded_action()
    hints = compute_coverage_hints(g, FILEPATH)
    action_hints = [h for h in hints if h["code"] == "ivy.action.unguardedWrite"]
    assert len(action_hints) == 1
    h = action_hints[0]
    assert h["line"] == 10
    assert "'send'" in h["message"]
    assert "'sent_pkt'" in h["message"]
    assert h["severity"] == "hint"


def test_guarded_action_no_diagnostic():
    """Action whose written vars are all guarded produces no diagnostic."""
    g = _make_graph_with_guarded_action()
    hints = compute_coverage_hints(g, FILEPATH)
    action_hints = [h for h in hints if h["code"] == "ivy.action.unguardedWrite"]
    assert len(action_hints) == 0


def test_multiple_actions_line_bucketing():
    """Writes are attributed to the correct action via line ranges."""
    g = RequirementGraph()
    # action alpha at line 5, action beta at line 20
    g.add_action(ActionNode(
        id="alpha", name="alpha", qualified_name="alpha",
        file=FILEPATH, line=5,
    ))
    g.add_action(ActionNode(
        id="beta", name="beta", qualified_name="beta",
        file=FILEPATH, line=20,
    ))
    g.add_state_var(StateVarNode(
        id="var_a", name="var_a", qualified_name="var_a",
        file=FILEPATH, line=2, is_relation=True,
    ))
    g.add_state_var(StateVarNode(
        id="var_b", name="var_b", qualified_name="var_b",
        file=FILEPATH, line=3, is_relation=True,
    ))
    # var_a written at line 10 (inside alpha), var_b at line 25 (inside beta)
    g.add_edge(f"{FILEPATH}:10:write:var_a", EdgeType.WRITES, "var_a")
    g.add_edge(f"{FILEPATH}:25:write:var_b", EdgeType.WRITES, "var_b")

    hints = compute_coverage_hints(g, FILEPATH)
    action_hints = [h for h in hints if h["code"] == "ivy.action.unguardedWrite"]
    assert len(action_hints) == 2

    alpha_hint = [h for h in action_hints if "'alpha'" in h["message"]]
    beta_hint = [h for h in action_hints if "'beta'" in h["message"]]
    assert len(alpha_hint) == 1
    assert "'var_a'" in alpha_hint[0]["message"]
    assert len(beta_hint) == 1
    assert "'var_b'" in beta_hint[0]["message"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_coverage_hints.py -v`

Expected: All 3 tests FAIL (no `ivy.action.unguardedWrite` hints produced yet).

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_coverage_hints.py
git commit -m "test: add failing tests for action-centric unguarded write diagnostic"
```

---

### Task 3: Implement the action-centric unguarded write diagnostic

**Files:**
- Modify: `ivy_lsp/core/coverage_hints.py:103` (after the existing unguarded-write section)

- [ ] **Step 1: Add the action-centric diagnostic section**

First, add `defaultdict` to the module-level imports (line 10-11):

```python
import logging
from collections import defaultdict
from typing import Any, Dict, List
```

Then insert after line 102 (after the closing of section 2's for-loop) and before section 3 (`# 3. Per-requirement checks`):

```python
    # -----------------------------------------------------------------
    # 2b. Action-centric unguarded writes (names specific vars per action)
    # -----------------------------------------------------------------

    # Build action line ranges per file for write attribution.
    # Sort actions by line within each file, then assign each write
    # to the action whose range [action.line, next_action.line) contains it.
    actions_by_file: Dict[str, List[Any]] = defaultdict(list)
    for action_node in graph.actions.values():
        actions_by_file[action_node.file].append(action_node)
    for file_actions in actions_by_file.values():
        file_actions.sort(key=lambda a: a.line)

    # Collect all WRITES edges grouped by file, with their line numbers.
    # Edge source format: "filepath:line:write:var_name"
    writes_by_file: Dict[str, List[tuple]] = defaultdict(list)
    for src, etype, dst in graph.edges:
        if etype != EdgeType.WRITES:
            continue
        marker = ":write:"
        marker_idx = src.find(marker)
        if marker_idx < 0:
            continue
        prefix = src[:marker_idx]
        last_colon = prefix.rfind(":")
        if last_colon <= 0:
            continue
        write_file = prefix[:last_colon]
        try:
            write_line = int(prefix[last_colon + 1 :])
        except ValueError:
            continue
        writes_by_file[write_file].append((write_line, dst))

    # For each action in the target file, bucket writes and check guardedness.
    if filepath in actions_by_file:
        file_actions = actions_by_file[filepath]
        file_writes = sorted(writes_by_file.get(filepath, []), key=lambda w: w[0])

        for i, action_node in enumerate(file_actions):
            range_start = action_node.line
            range_end = file_actions[i + 1].line if i + 1 < len(file_actions) else float("inf")

            unguarded_vars = []
            for write_line, var_id in file_writes:
                if write_line < range_start:
                    continue
                if write_line >= range_end:
                    break
                if var_id not in guarded_vars:
                    unguarded_vars.append(var_id)

            if unguarded_vars:
                var_names = [
                    graph.state_vars[v].name
                    for v in unguarded_vars
                    if v in graph.state_vars
                ]
                if var_names:
                    var_list = ", ".join(f"'{v}'" for v in var_names)
                    hints.append(
                        {
                            "line": action_node.line,
                            "message": (
                                f"Action '{action_node.name}' writes {var_list} "
                                f"without a 'require' precondition"
                            ),
                            "severity": "hint",
                            "code": "ivy.action.unguardedWrite",
                            "template": f"require {var_names[0]}(...) ",
                        }
                    )
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_coverage_hints.py -v`

Expected: All 3 tests PASS.

- [ ] **Step 3: Run the full existing test suite to check for regressions**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --timeout=30 2>&1 | tail -20`

Expected: No new failures.

- [ ] **Step 4: Commit**

```bash
git add ivy_lsp/core/coverage_hints.py
git commit -m "feat(diag): add action-centric unguarded write diagnostic with variable names"
```

---

### Task 4: Suppress structural `unguarded-action` when graph is available

**Files:**
- Modify: `ivy_lsp/lsp/diagnostics/compute.py:540-571` (coverage hints section)

- [ ] **Step 1: Add deduplication filter after coverage hints run**

In `compute_diagnostics()`, after the coverage hints loop (after line 571), add:

```python
            # Suppress generic structural 'unguarded-action' when graph-based
            # coverage hints provide specific variable-naming diagnostics.
            diags = [
                d for d in diags
                if not (hasattr(d, "code") and d.code == "unguarded-action")
            ]
```

This goes inside the `if graph is not None:` block (indented to match, at the same level as the `for hint in ...` loop).

- [ ] **Step 2: Write a test for deduplication behavior**

Add to `tests/test_coverage_hints.py`:

```python
from unittest.mock import MagicMock

from ivy_lsp.lsp.diagnostics.compute import compute_diagnostics


def test_structural_unguarded_action_suppressed_with_graph():
    """When graph is available, structural 'unguarded-action' is filtered out."""
    source = "#lang ivy1.7\naction send(S:cid) = {\n    sent(S) := true;\n}\n"
    # Mock indexer with a graph present
    indexer = MagicMock()
    indexer.requirement_graph = RequirementGraph()
    indexer.resolver = MagicMock()
    indexer.resolver.resolve = MagicMock(return_value=None)
    indexer.resolver._partition_staging = {}

    diags = compute_diagnostics(
        parser=None,
        source=source,
        filepath="/fake/test.ivy",
        indexer=indexer,
    )
    codes = [d.code for d in diags if d.code is not None]
    assert "unguarded-action" not in codes


def test_structural_unguarded_action_present_without_graph():
    """Without graph, structural 'unguarded-action' fires as fallback."""
    source = "#lang ivy1.7\naction send(S:cid) = {\n    sent(S) := true;\n}\n"

    diags = compute_diagnostics(
        parser=None,
        source=source,
        filepath="/fake/test.ivy",
        indexer=None,
    )
    codes = [d.code for d in diags if d.code is not None]
    assert "unguarded-action" in codes
```

- [ ] **Step 3: Run all tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_coverage_hints.py -v`

Expected: All 5 tests PASS.

- [ ] **Step 4: Run the full suite for regressions**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --timeout=30 2>&1 | tail -20`

Expected: No new failures.

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/lsp/diagnostics/compute.py tests/test_coverage_hints.py
git commit -m "feat(diag): suppress generic unguarded-action when graph provides specific hints"
```

---

### Task 5: Final verification and cleanup

**Files:**
- All modified files from Tasks 1-4

- [ ] **Step 1: Run the full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --timeout=30`

Expected: All tests pass, no regressions.

- [ ] **Step 2: Run black and isort**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m black ivy_lsp/core/coverage_hints.py ivy_lsp/core/diagnostics/codes.py ivy_lsp/lsp/diagnostics/compute.py tests/test_coverage_hints.py && python -m isort ivy_lsp/core/coverage_hints.py ivy_lsp/core/diagnostics/codes.py ivy_lsp/lsp/diagnostics/compute.py tests/test_coverage_hints.py`

Expected: Files formatted, no errors.

- [ ] **Step 3: Commit any formatting changes**

```bash
git add -u
git commit -m "style: format new diagnostic code with black/isort"
```
