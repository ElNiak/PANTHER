# Task 7: NCT Classification

**Status:** pending
**Depends on:** Task 4

**Files:**
- Modify: `ivy_lsp/analysis/test_scope.py`
- Create: `tests/test_nct_classification.py`

**Key concept -- NCT classification rules:**
- `require` in `before` = ASSUMPTION (precondition the tester must satisfy)
- `require`/`ensure`/`assert` in `after` = GUARANTEE (postcondition the IUT must satisfy)
- `_generating` flag in formula text = TESTER_ONLY (tester-internal constraint)
- `assume` in `before` = ASSUMPTION
- `ensure`/`assert` as direct = GUARANTEE

**Action direction:**
- `export` = GENERATED (tester controls this action)
- `import` = RECEIVED (tester observes this action)
- Neither = INTERNAL (helper action)

---

## Step 1: Write the failing test

```python
# tests/test_nct_classification.py
"""Tests for NCT assume/guarantee classification."""
import pytest
from ivy_lsp.analysis.requirement_graph import RequirementNode
from ivy_lsp.analysis.test_scope import (
    NctClassification, ActionClassification,
    classify_requirement, classify_action_direction, TestScope,
)


def _req(kind="require", mixin_kind="before", formula="x > 0"):
    return RequirementNode(
        id="/test:1", kind=kind, formula_text=formula, line=1, col=0,
        file="/test", monitor_action="act", mixin_kind=mixin_kind,
    )


class TestNctClassification:
    def test_require_before_is_assumption(self):
        assert classify_requirement(_req("require", "before")) == NctClassification.ASSUMPTION

    def test_require_after_is_guarantee(self):
        assert classify_requirement(_req("require", "after")) == NctClassification.GUARANTEE

    def test_ensure_after_is_guarantee(self):
        assert classify_requirement(_req("ensure", "after")) == NctClassification.GUARANTEE

    def test_assert_after_is_guarantee(self):
        assert classify_requirement(_req("assert", "after")) == NctClassification.GUARANTEE

    def test_assume_before_is_assumption(self):
        assert classify_requirement(_req("assume", "before")) == NctClassification.ASSUMPTION

    def test_generating_flag_is_tester_only(self):
        req = _req("require", "before", formula="connected & _generating")
        assert classify_requirement(req) == NctClassification.TESTER_ONLY

    def test_require_direct_is_assumption(self):
        assert classify_requirement(_req("require", "direct")) == NctClassification.ASSUMPTION

    def test_ensure_direct_is_guarantee(self):
        assert classify_requirement(_req("ensure", "direct")) == NctClassification.GUARANTEE


class TestActionClassification:
    def test_exported_is_generated(self):
        scope = TestScope(
            test_file="/test.ivy", include_closure=frozenset(),
            exported_actions=frozenset({"quic.send"}),
            imported_actions=frozenset(), tester_role="client",
        )
        assert classify_action_direction("quic.send", scope) == ActionClassification.GENERATED

    def test_imported_is_received(self):
        scope = TestScope(
            test_file="/test.ivy", include_closure=frozenset(),
            exported_actions=frozenset(),
            imported_actions=frozenset({"tls.handshake"}), tester_role="client",
        )
        assert classify_action_direction("tls.handshake", scope) == ActionClassification.RECEIVED

    def test_neither_is_internal(self):
        scope = TestScope(
            test_file="/test.ivy", include_closure=frozenset(),
            exported_actions=frozenset({"quic.send"}),
            imported_actions=frozenset(), tester_role="client",
        )
        assert classify_action_direction("helper.compute", scope) == ActionClassification.INTERNAL
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_nct_classification.py -v
```

Expected: FAIL with `ImportError: cannot import name 'NctClassification'`

## Step 3: Write minimal implementation

Add to `ivy_lsp/analysis/test_scope.py`:

```python
from enum import Enum


class NctClassification(Enum):
    ASSUMPTION = "assumption"
    GUARANTEE = "guarantee"
    TESTER_ONLY = "tester_only"


class ActionClassification(Enum):
    GENERATED = "generated"
    RECEIVED = "received"
    INTERNAL = "internal"


def classify_requirement(req: "RequirementNode") -> NctClassification:
    """Classify a requirement as assumption, guarantee, or tester-only.

    Rules:
    - _generating in formula -> TESTER_ONLY
    - mixin_kind == "after" -> GUARANTEE
    - kind in (ensure, assert) -> GUARANTEE
    - Everything else -> ASSUMPTION
    """
    if "_generating" in req.formula_text:
        return NctClassification.TESTER_ONLY
    if req.mixin_kind == "after":
        return NctClassification.GUARANTEE
    if req.kind in ("ensure", "assert"):
        return NctClassification.GUARANTEE
    return NctClassification.ASSUMPTION


def classify_action_direction(
    action_name: str, scope: TestScope
) -> ActionClassification:
    """Classify an action as generated, received, or internal."""
    if action_name in scope.exported_actions:
        return ActionClassification.GENERATED
    if action_name in scope.imported_actions:
        return ActionClassification.RECEIVED
    return ActionClassification.INTERNAL
```

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_nct_classification.py -v
```

Expected: PASS (11 tests)

## Step 5: Commit

```bash
git add ivy_lsp/analysis/test_scope.py tests/test_nct_classification.py
git commit -m "feat(nct): add NCT classification and action direction"
```
