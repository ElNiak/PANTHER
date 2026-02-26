# Task 5: ScopedRequirementModel -- Core

**Status:** pending
**Depends on:** Task 1, Task 4

**Files:**
- Modify: `ivy_lsp/analysis/test_scope.py` (add ScopedRequirementModel)
- Create: `tests/test_scoped_requirement_model.py`

**Key design decision:** Subclass `RequirementGraph` so all existing call sites work unchanged. New scoped methods are layered on top.

**Scoping rule:** Requirement R is in scope for test T iff:
- `R.file in T.include_closure` AND
- `R.monitor_action in T.exported_actions`

---

## Step 1: Write the failing test

```python
# tests/test_scoped_requirement_model.py
"""Tests for ScopedRequirementModel scoped queries."""
import pytest
from ivy_lsp.analysis.requirement_graph import (
    ActionNode, EdgeType, RequirementGraph, RequirementNode, StateVarNode,
)
from ivy_lsp.analysis.test_scope import (
    ExportImportInfo, ScopedRequirementModel, TestScope,
)


def _make_req(file, line, kind="require", formula="true", action="", mixin_kind="before"):
    return RequirementNode(
        id=f"{file}:{line}", kind=kind, formula_text=formula,
        line=line, col=0, file=file, monitor_action=action, mixin_kind=mixin_kind,
    )


@pytest.fixture
def scoped_model():
    """Model with two test scopes sharing some files.

    Test A (client test): exports quic.send, includes file_a + shared
    Test B (server test): exports quic.recv, includes file_b + shared
    Shared file has requirements on both quic.send and quic.recv.
    """
    model = ScopedRequirementModel()

    req_a1 = _make_req("/test/file_a.ivy", 10, "require", "x > 0", "quic.send")
    model.add_requirement(req_a1)
    model.add_edge(req_a1.id, EdgeType.CONSTRAINS, "quic.send")

    req_b1 = _make_req("/test/file_b.ivy", 10, "require", "y > 0", "quic.recv")
    model.add_requirement(req_b1)
    model.add_edge(req_b1.id, EdgeType.CONSTRAINS, "quic.recv")

    req_s1 = _make_req("/test/shared.ivy", 5, "require", "connected", "quic.send")
    req_s2 = _make_req("/test/shared.ivy", 10, "ensure", "acked", "quic.recv")
    model.add_requirement(req_s1)
    model.add_requirement(req_s2)
    model.add_edge(req_s1.id, EdgeType.CONSTRAINS, "quic.send")
    model.add_edge(req_s2.id, EdgeType.CONSTRAINS, "quic.recv")

    scope_a = TestScope(
        test_file="/test/test_a.ivy",
        include_closure=frozenset({"/test/test_a.ivy", "/test/file_a.ivy", "/test/shared.ivy"}),
        exported_actions=frozenset({"quic.send"}),
        imported_actions=frozenset(),
        tester_role="client",
    )
    scope_b = TestScope(
        test_file="/test/test_b.ivy",
        include_closure=frozenset({"/test/test_b.ivy", "/test/file_b.ivy", "/test/shared.ivy"}),
        exported_actions=frozenset({"quic.recv"}),
        imported_actions=frozenset(),
        tester_role="server",
    )
    model.register_test_scope(scope_a)
    model.register_test_scope(scope_b)
    return model


class TestBackwardCompatibility:
    def test_is_subclass(self):
        assert issubclass(ScopedRequirementModel, RequirementGraph)

    def test_unscoped_get_requirements_for_action(self, scoped_model):
        reqs = scoped_model.get_requirements_for_action("quic.send")
        assert len(reqs) == 2

    def test_unscoped_counts(self, scoped_model):
        counts = scoped_model.get_requirement_counts_for_action("quic.send")
        assert counts["require"] == 2


class TestScopedQueries:
    def test_scoped_requirements_test_a(self, scoped_model):
        reqs = scoped_model.get_scoped_requirements("/test/test_a.ivy")
        assert len(reqs) == 2
        ids = {r.id for r in reqs}
        assert "/test/file_a.ivy:10" in ids
        assert "/test/shared.ivy:5" in ids

    def test_scoped_requirements_test_b(self, scoped_model):
        reqs = scoped_model.get_scoped_requirements("/test/test_b.ivy")
        assert len(reqs) == 2
        ids = {r.id for r in reqs}
        assert "/test/file_b.ivy:10" in ids
        assert "/test/shared.ivy:10" in ids

    def test_scoped_counts(self, scoped_model):
        counts = scoped_model.get_scoped_counts("/test/test_a.ivy", "quic.send")
        assert counts == {"require": 2}

    def test_scoped_counts_excludes_other_test(self, scoped_model):
        counts = scoped_model.get_scoped_counts("/test/test_a.ivy", "quic.recv")
        assert counts == {}

    def test_get_tests_for_file(self, scoped_model):
        tests = scoped_model.get_tests_for_file("/test/shared.ivy")
        assert tests == {"/test/test_a.ivy", "/test/test_b.ivy"}

    def test_get_tests_for_exclusive_file(self, scoped_model):
        tests = scoped_model.get_tests_for_file("/test/file_a.ivy")
        assert tests == {"/test/test_a.ivy"}

    def test_get_tests_for_unknown_file(self, scoped_model):
        tests = scoped_model.get_tests_for_file("/unknown.ivy")
        assert tests == set()


class TestActiveTestSelector:
    def test_no_active_test_by_default(self, scoped_model):
        assert scoped_model.get_active_scope() is None

    def test_set_active_test(self, scoped_model):
        scoped_model.set_active_test("/test/test_a.ivy")
        scope = scoped_model.get_active_scope()
        assert scope is not None
        assert scope.test_file == "/test/test_a.ivy"

    def test_clear_active_test(self, scoped_model):
        scoped_model.set_active_test("/test/test_a.ivy")
        scoped_model.set_active_test(None)
        assert scoped_model.get_active_scope() is None

    def test_set_unknown_test_is_noop(self, scoped_model):
        scoped_model.set_active_test("/nonexistent.ivy")
        assert scoped_model.get_active_scope() is None


class TestCacheInvalidation:
    def test_invalidate_file_clears_scope_cache(self, scoped_model):
        scoped_model.get_scoped_requirements("/test/test_a.ivy")
        assert "/test/test_a.ivy" in scoped_model._scope_cache
        scoped_model.invalidate_file("/test/shared.ivy")
        assert "/test/test_a.ivy" not in scoped_model._scope_cache

    def test_invalidate_unrelated_file_preserves_cache(self, scoped_model):
        scoped_model.get_scoped_requirements("/test/test_a.ivy")
        scoped_model.invalidate_file("/test/file_b.ivy")
        assert "/test/test_a.ivy" in scoped_model._scope_cache
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_scoped_requirement_model.py -v
```

Expected: FAIL with `ImportError: cannot import name 'ScopedRequirementModel'`

## Step 3: Write minimal implementation

Add to `ivy_lsp/analysis/test_scope.py`:

```python
import logging
from collections import defaultdict
from typing import Any, Optional, Set
from ivy_lsp.analysis.requirement_graph import (
    EdgeType, RequirementGraph, RequirementNode,
)

logger = logging.getLogger(__name__)


class ScopedRequirementModel(RequirementGraph):
    """RequirementGraph with per-test scoping layer.

    Inherits all RequirementGraph methods (unscoped) and adds
    scoped query methods that filter by test scope.
    """

    def __init__(self) -> None:
        super().__init__()
        self._test_scopes: Dict[str, TestScope] = {}
        self._file_to_tests: Dict[str, Set[str]] = defaultdict(set)
        self._active_test: Optional[str] = None
        self._scope_cache: Dict[str, list] = {}
        self._compilation_results: Dict[str, Any] = {}

    def register_test_scope(self, scope: TestScope) -> None:
        self._test_scopes[scope.test_file] = scope
        for f in scope.include_closure:
            self._file_to_tests[f].add(scope.test_file)
        self._scope_cache.pop(scope.test_file, None)

    def set_active_test(self, test_file: Optional[str]) -> None:
        if test_file is None or test_file in self._test_scopes:
            self._active_test = test_file

    def get_active_scope(self) -> Optional[TestScope]:
        if self._active_test is None:
            return None
        return self._test_scopes.get(self._active_test)

    def get_tests_for_file(self, filepath: str) -> Set[str]:
        return set(self._file_to_tests.get(filepath, set()))

    def get_scoped_requirements(self, test_file: str) -> List[RequirementNode]:
        if test_file in self._scope_cache:
            return self._scope_cache[test_file]
        scope = self._test_scopes.get(test_file)
        if scope is None:
            return []
        result = [
            r for r in self.requirements.values()
            if r.file in scope.include_closure
            and r.monitor_action in scope.exported_actions
        ]
        self._scope_cache[test_file] = result
        return result

    def get_scoped_counts(self, test_file: str, action_name: str) -> Dict[str, int]:
        scope = self._test_scopes.get(test_file)
        if scope is None or action_name not in scope.exported_actions:
            return {}
        counts: Dict[str, int] = defaultdict(int)
        for req in self.get_scoped_requirements(test_file):
            if req.monitor_action == action_name:
                counts[req.kind] += 1
        return dict(counts)

    def invalidate_file(self, filepath: str) -> None:
        for test_file in self._file_to_tests.get(filepath, set()):
            self._scope_cache.pop(test_file, None)
```

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_scoped_requirement_model.py -v
```

Expected: PASS (16 tests)

## Step 5: Commit

```bash
git add ivy_lsp/analysis/test_scope.py tests/test_scoped_requirement_model.py
git commit -m "feat(scoped-model): add ScopedRequirementModel with per-test queries"
```
