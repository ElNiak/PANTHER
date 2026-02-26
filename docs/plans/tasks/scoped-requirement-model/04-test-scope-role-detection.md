# Task 4: TestScope Data Structure and Role Detection

**Status:** pending
**Depends on:** Task 1

**Files:**
- Modify: `ivy_lsp/analysis/test_scope.py` (add TestScope, detect_test_role)
- Create: `tests/test_test_scope.py`

**Key concept -- Ivy Role Inversion:**
- Testing a server means Ivy acts as client (tester_role = "client")
- Testing a client means Ivy acts as server (tester_role = "server")
- Detected from behavior file names in include closure

---

## Step 1: Write the failing test

```python
# tests/test_test_scope.py
"""Tests for TestScope computation and role detection."""
import pytest
from ivy_lsp.analysis.test_scope import TestScope, detect_test_role


class TestDetectTestRole:
    def test_server_behavior_means_client_tester(self):
        closure = frozenset({
            "/test/quic_server_test.ivy",
            "/test/ivy_quic_server_behavior.ivy",
            "/test/quic_types.ivy",
        })
        assert detect_test_role(closure) == "client"

    def test_client_behavior_means_server_tester(self):
        closure = frozenset({
            "/test/quic_client_test.ivy",
            "/test/ivy_quic_client_behavior.ivy",
        })
        assert detect_test_role(closure) == "server"

    def test_mim_behavior(self):
        closure = frozenset({
            "/test/quic_mim_test.ivy",
            "/test/ivy_quic_mim_behavior.ivy",
        })
        assert detect_test_role(closure) == "mim"

    def test_unknown_when_no_behavior_file(self):
        closure = frozenset({"/test/quic_types.ivy", "/test/quic_frame.ivy"})
        assert detect_test_role(closure) == "unknown"

    def test_empty_closure(self):
        assert detect_test_role(frozenset()) == "unknown"


class TestTestScopeCreation:
    def test_create_scope(self):
        scope = TestScope(
            test_file="/test/quic_server_test.ivy",
            include_closure=frozenset({"/test/quic_server_test.ivy", "/test/types.ivy"}),
            exported_actions=frozenset({"quic.send", "quic.recv"}),
            imported_actions=frozenset({"tls.handshake"}),
            tester_role="client",
        )
        assert scope.test_file == "/test/quic_server_test.ivy"
        assert len(scope.include_closure) == 2
        assert "quic.send" in scope.exported_actions
        assert scope.tester_role == "client"

    def test_action_in_scope(self):
        scope = TestScope(
            test_file="/test/test.ivy",
            include_closure=frozenset({"/test/test.ivy"}),
            exported_actions=frozenset({"quic.send"}),
            imported_actions=frozenset(),
            tester_role="client",
        )
        assert scope.is_action_exported("quic.send") is True
        assert scope.is_action_exported("quic.recv") is False

    def test_file_in_scope(self):
        scope = TestScope(
            test_file="/test/test.ivy",
            include_closure=frozenset({"/test/test.ivy", "/test/types.ivy"}),
            exported_actions=frozenset(),
            imported_actions=frozenset(),
            tester_role="client",
        )
        assert scope.is_file_in_scope("/test/types.ivy") is True
        assert scope.is_file_in_scope("/other/file.ivy") is False
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_test_scope.py -v
```

Expected: FAIL with `ImportError: cannot import name 'TestScope'`

## Step 3: Write minimal implementation

Add to `ivy_lsp/analysis/test_scope.py`:

```python
import os
from typing import FrozenSet


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


def detect_test_role(include_closure: FrozenSet[str]) -> str:
    """Derive tester role from included behavior files.

    Uses Ivy role inversion: testing a server means tester is client.
    """
    for f in include_closure:
        basename = os.path.basename(f).replace(".ivy", "")
        if "server_behavior" in basename:
            return "client"
        if "client_behavior" in basename:
            return "server"
        if "mim" in basename:
            return "mim"
    return "unknown"
```

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_test_scope.py -v
```

Expected: PASS (8 tests)

## Step 5: Commit

```bash
git add ivy_lsp/analysis/test_scope.py tests/test_test_scope.py
git commit -m "feat(test-scope): add TestScope dataclass and role detection"
```
