# Task 9: Scoped Diagnostics

**Status:** pending
**Depends on:** Task 5, Task 6

**Files:**
- Modify: `ivy_lsp/features/diagnostics.py:135-257` (`compute_requirement_diagnostics`)
- Create: `tests/test_scoped_diagnostics.py`

**Key change:** When an active test scope exists, the "unmonitored action" diagnostic should only flag actions that are actually exported in the active test. Non-exported actions are not relevant for the current test scope.

---

## Step 1: Write the failing test

```python
# tests/test_scoped_diagnostics.py
"""Tests for scoped requirement diagnostics."""
import pytest
from unittest.mock import MagicMock
from ivy_lsp.features.diagnostics import compute_requirement_diagnostics
from ivy_lsp.analysis.test_scope import ScopedRequirementModel, TestScope
from ivy_lsp.analysis.requirement_graph import EdgeType, RequirementNode


class TestScopedUnmonitoredAction:
    def test_non_exported_action_not_flagged(self):
        model = ScopedRequirementModel()
        req = RequirementNode(
            id="/f.ivy:5", kind="require", formula_text="x > 0",
            line=5, col=0, file="/f.ivy",
            monitor_action="quic.recv", mixin_kind="before",
        )
        model.add_requirement(req)
        model.add_edge(req.id, EdgeType.CONSTRAINS, "quic.recv")
        scope = TestScope(
            test_file="/test.ivy",
            include_closure=frozenset({"/test.ivy", "/f.ivy"}),
            exported_actions=frozenset({"quic.send"}),
            imported_actions=frozenset(), tester_role="client",
        )
        model.register_test_scope(scope)
        model.set_active_test("/test.ivy")

        indexer = MagicMock()
        indexer._requirement_graph = model
        indexer._include_graph = MagicMock()

        source = "action quic.recv(x:t)\n"
        diags = compute_requirement_diagnostics(source, "/f.ivy", indexer)
        hints = [d for d in diags if "no before/after" in d.message]
        assert len(hints) == 0
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_scoped_diagnostics.py -v
```

Expected: FAIL (old code flags all unmonitored actions regardless of scope)

## Step 3: Update `compute_requirement_diagnostics`

In `ivy_lsp/features/diagnostics.py`, in the unmonitored action detection section (around line 208-228):

```python
# Add scope check before flagging unmonitored actions:
from ivy_lsp.analysis.test_scope import ScopedRequirementModel

graph = indexer._requirement_graph
active_scope = None
if isinstance(graph, ScopedRequirementModel):
    active_scope = graph.get_active_scope()

# In the unmonitored action loop:
for action_name in actions_in_file:
    # If we have an active scope and this action is not exported, skip it
    if active_scope is not None and action_name not in active_scope.exported_actions:
        continue
    # ... existing unmonitored action detection logic ...
```

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_scoped_diagnostics.py -v
python -m pytest tests/test_requirement_diagnostics.py -v  # existing tests still pass
```

Expected: PASS

## Step 5: Commit

```bash
git add ivy_lsp/features/diagnostics.py tests/test_scoped_diagnostics.py
git commit -m "feat(diagnostics): scope-aware unmonitored action detection"
```
