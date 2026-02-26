# Task 12: Integration Regression Tests

**Status:** pending
**Depends on:** Task 5, Task 6, Task 8, Task 9

**Files:**
- Create: `tests/test_scoped_integration.py`

**Purpose:** Verify the original triple-counting bug is fixed end-to-end.

**Three sources of triple-counting this eliminates:**
1. Include-chain duplication: same requirement counted via multiple include paths
2. Cross-test pollution: requirement counted in tests that don't export the action
3. Semantic duplication: same requirement listed under workspace-wide and per-file views

---

## Step 1: Write the tests

```python
# tests/test_scoped_integration.py
"""Integration tests verifying the triple-counting bug is fixed."""
import pytest
from ivy_lsp.analysis.requirement_graph import EdgeType, RequirementNode
from ivy_lsp.analysis.test_scope import (
    ExportImportInfo, ScopedRequirementModel, TestScope, detect_test_role,
)


def _make_req(file, line, kind="require", formula="true", action="", mixin_kind="before"):
    return RequirementNode(
        id=f"{file}:{line}", kind=kind, formula_text=formula,
        line=line, col=0, file=file, monitor_action=action, mixin_kind=mixin_kind,
    )


class TestTripleCountingEliminated:
    """Reproduce the triple-counting scenario and verify it's fixed."""

    @pytest.fixture
    def quic_model(self):
        """Simulate a real QUIC workspace with shared includes.

        Structure:
        - quic_server_test.ivy (test file, exports quic.send, quic.recv)
          - includes quic_connection.ivy (shared, has requirements on quic.send)
          - includes quic_types.ivy (shared, no requirements)
        - quic_client_test.ivy (test file, exports tls.client_hello)
          - includes quic_connection.ivy (shared)
          - includes quic_types.ivy (shared)
        """
        model = ScopedRequirementModel()

        # Requirements in shared file quic_connection.ivy
        req1 = _make_req("/ws/quic_connection.ivy", 50, "require", "connected", "quic.send")
        req2 = _make_req("/ws/quic_connection.ivy", 60, "ensure", "sent", "quic.send")
        req3 = _make_req("/ws/quic_connection.ivy", 70, "require", "tls_ready", "tls.client_hello")
        model.add_requirement(req1)
        model.add_requirement(req2)
        model.add_requirement(req3)
        model.add_edge(req1.id, EdgeType.CONSTRAINS, "quic.send")
        model.add_edge(req2.id, EdgeType.CONSTRAINS, "quic.send")
        model.add_edge(req3.id, EdgeType.CONSTRAINS, "tls.client_hello")

        # Requirements in server test file
        req4 = _make_req("/ws/quic_server_test.ivy", 10, "require", "x > 0", "quic.send")
        model.add_requirement(req4)
        model.add_edge(req4.id, EdgeType.CONSTRAINS, "quic.send")

        # Register test scopes
        server_scope = TestScope(
            test_file="/ws/quic_server_test.ivy",
            include_closure=frozenset({
                "/ws/quic_server_test.ivy",
                "/ws/quic_connection.ivy",
                "/ws/quic_types.ivy",
            }),
            exported_actions=frozenset({"quic.send", "quic.recv"}),
            imported_actions=frozenset(),
            tester_role="client",
        )
        client_scope = TestScope(
            test_file="/ws/quic_client_test.ivy",
            include_closure=frozenset({
                "/ws/quic_client_test.ivy",
                "/ws/quic_connection.ivy",
                "/ws/quic_types.ivy",
            }),
            exported_actions=frozenset({"tls.client_hello"}),
            imported_actions=frozenset(),
            tester_role="server",
        )
        model.register_test_scope(server_scope)
        model.register_test_scope(client_scope)
        return model

    def test_same_req_counted_once_per_test(self, quic_model):
        """Each requirement appears exactly once in its test scope."""
        reqs = quic_model.get_scoped_requirements("/ws/quic_server_test.ivy")
        ids = [r.id for r in reqs]
        # No duplicates
        assert len(ids) == len(set(ids))
        # Exactly 3: req1 + req2 (shared, on quic.send) + req4 (test file, on quic.send)
        assert len(reqs) == 3

    def test_cross_test_pollution_eliminated(self, quic_model):
        """Requirements for quic.send don't appear in client test scope."""
        reqs = quic_model.get_scoped_requirements("/ws/quic_client_test.ivy")
        for r in reqs:
            assert r.monitor_action != "quic.send", \
                f"quic.send requirement {r.id} leaked into client test scope"
        # Only the tls.client_hello requirement from shared file
        assert len(reqs) == 1
        assert reqs[0].monitor_action == "tls.client_hello"

    def test_include_chain_dedup(self, quic_model):
        """Shared file requirements counted exactly once per test scope."""
        server_reqs = quic_model.get_scoped_requirements("/ws/quic_server_test.ivy")
        shared_reqs = [r for r in server_reqs if r.file == "/ws/quic_connection.ivy"]
        # req1 and req2 are in shared file on quic.send (exported by server test)
        assert len(shared_reqs) == 2

    def test_unscoped_still_returns_all(self, quic_model):
        """Unscoped queries still return workspace-wide results."""
        all_reqs = quic_model.get_requirements_for_action("quic.send")
        assert len(all_reqs) == 3  # req1 + req2 + req4

    def test_scoped_counts_match(self, quic_model):
        """Scoped counts are consistent with scoped requirements."""
        counts = quic_model.get_scoped_counts("/ws/quic_server_test.ivy", "quic.send")
        assert counts == {"require": 2, "ensure": 1}

    def test_file_to_test_mapping(self, quic_model):
        """Shared files map to all tests that include them."""
        tests = quic_model.get_tests_for_file("/ws/quic_connection.ivy")
        assert tests == {"/ws/quic_server_test.ivy", "/ws/quic_client_test.ivy"}

    def test_exclusive_file_maps_to_one_test(self, quic_model):
        """Test-specific files map to only their test."""
        tests = quic_model.get_tests_for_file("/ws/quic_server_test.ivy")
        assert tests == {"/ws/quic_server_test.ivy"}
```

## Step 2: Run tests

```bash
python -m pytest tests/test_scoped_integration.py -v
```

Expected: PASS (all 7 tests)

## Step 3: Verify all existing tests still pass

```bash
python -m pytest tests/test_requirement_graph.py -v
python -m pytest tests/test_light_mode_extractor.py -v
python -m pytest tests/test_code_lens.py -v
python -m pytest tests/test_requirement_diagnostics.py -v
```

Expected: ALL PASS

## Step 4: Run full test suite

```bash
python -m pytest tests/ -v --tb=short
```

Expected: ALL PASS

## Step 5: Commit

```bash
git add tests/test_scoped_integration.py
git commit -m "test: integration tests verifying triple-counting fix"
```
