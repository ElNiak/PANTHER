# Task 8: Scoped Code Lenses

**Status:** pending
**Depends on:** Task 5, Task 6

**Files:**
- Modify: `ivy_lsp/features/code_lens.py:76-126` (`_monitor_lenses`)
- Create: `tests/test_scoped_code_lens.py`

**Key change:** When an active test scope exists, `_monitor_lenses` should use `get_scoped_counts()` instead of `get_requirement_counts_for_action()` to display per-test-scoped requirement counts.

---

## Step 1: Write the failing test

```python
# tests/test_scoped_code_lens.py
"""Tests for scoped code lenses."""
import pytest
from unittest.mock import MagicMock
from ivy_lsp.features.code_lens import compute_code_lenses
from ivy_lsp.analysis.test_scope import ScopedRequirementModel, TestScope
from ivy_lsp.analysis.requirement_graph import EdgeType, RequirementNode


class TestScopedMonitorLenses:
    def test_scoped_lens_only_counts_exported_action(self):
        model = ScopedRequirementModel()
        req_a = RequirementNode(
            id="/test/b.ivy:10", kind="require", formula_text="x > 0",
            line=10, col=0, file="/test/b.ivy",
            monitor_action="quic.send", mixin_kind="before",
        )
        req_b = RequirementNode(
            id="/test/b.ivy:20", kind="ensure", formula_text="y > 0",
            line=20, col=0, file="/test/b.ivy",
            monitor_action="quic.recv", mixin_kind="after",
        )
        model.add_requirement(req_a)
        model.add_requirement(req_b)
        model.add_edge(req_a.id, EdgeType.CONSTRAINS, "quic.send")
        model.add_edge(req_b.id, EdgeType.CONSTRAINS, "quic.recv")

        scope = TestScope(
            test_file="/test/test_a.ivy",
            include_closure=frozenset({"/test/test_a.ivy", "/test/b.ivy"}),
            exported_actions=frozenset({"quic.send"}),
            imported_actions=frozenset(), tester_role="client",
        )
        model.register_test_scope(scope)
        model.set_active_test("/test/test_a.ivy")

        indexer = MagicMock()
        indexer._requirement_graph = model
        indexer._include_graph = MagicMock()

        source = "before quic.send {\n    require x > 0;\n}\n"
        lenses = compute_code_lenses(indexer, "/test/b.ivy", source)
        titles = [l.command.title for l in lenses if l.command]
        assert any("1 require" in t for t in titles)
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_scoped_code_lens.py -v
```

Expected: FAIL (old code uses unscoped counts, may show wrong numbers or both actions)

## Step 3: Modify `_monitor_lenses`

In `ivy_lsp/features/code_lens.py`, modify `_monitor_lenses` (around line 76-126):

The key change is in the section where requirement counts are fetched. Add a check for active scope:

```python
# Inside _monitor_lenses, where counts are computed:
from ivy_lsp.analysis.test_scope import ScopedRequirementModel

graph = indexer._requirement_graph
active_scope = None
if isinstance(graph, ScopedRequirementModel):
    active_scope = graph.get_active_scope()

# When building the lens title:
if active_scope is not None:
    counts = graph.get_scoped_counts(active_scope.test_file, action_name)
else:
    counts = graph.get_requirement_counts_for_action(action_name)
```

This preserves backward compatibility: when no active test is set, the old behavior remains.

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_scoped_code_lens.py -v
python -m pytest tests/test_code_lens.py -v  # existing tests still pass
```

Expected: PASS

## Step 5: Commit

```bash
git add ivy_lsp/features/code_lens.py tests/test_scoped_code_lens.py
git commit -m "feat(code-lens): use scoped queries when active test is set"
```
