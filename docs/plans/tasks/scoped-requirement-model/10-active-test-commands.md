# Task 10: Active Test Selector + Compile Commands

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add three LSP custom commands (`ivy/setActiveTest`, `ivy/listTests`, `ivy/compileTest`) that let clients control which test scope is active and compile specific test files.

**Architecture:** New handlers registered inside the existing `register()` function in `commands.py`, following the exact `@server.feature()` pattern used by `ivy/verify`, `ivy/compile`, `ivy/showModel`, and `ivy/capabilities`. The handlers access `ScopedRequirementModel` via `server._indexer._requirement_graph`. Sync handlers for state queries (`setActiveTest`, `listTests`); async handler for subprocess (`compileTest`).

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio, lsprotocol, unittest.mock. No new dependencies.

**Status:** pending
**Depends on:** Task 5 (ScopedRequirementModel), Task 6 (WorkspaceIndexer integration)

**Files:**
- Modify: `ivy_lsp/features/commands.py` (add 3 handlers inside `register()` at line 259)
- Create: `tests/test_active_test_commands.py`

**Base path for all files:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

**Test runner:** `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/<file> -v`

---

## Design Decisions

### Command contract

| Command | Params (namedtuple attrs) | Returns | Sync/Async |
|---------|---------------------------|---------|------------|
| `ivy/setActiveTest` | `testFile: str \| None` | `{success, activeTest, error?}` | sync |
| `ivy/listTests` | (none) | `{tests: [{testFile, testerRole, exportCount, importCount, includeCount}]}` | sync |
| `ivy/compileTest` | `testFile: str`, `workDoneToken?: str\|int` | `{success, message, output, duration}` | async |

### Why these are separate from existing commands

- `ivy/compile` compiles the **currently open** file (`textDocument.uri`). `ivy/compileTest` compiles a **specific test file** from the test list -- the user may be editing a shared protocol file but want to compile a test that includes it.
- `ivy/setActiveTest` controls scoped diagnostics/lenses (Tasks 8, 9). No existing command does this.
- `ivy/listTests` exposes test scope metadata the client needs for UI (test picker, status bar).

### Diagnostic refresh

`ivy/setActiveTest` does NOT automatically refresh diagnostics. The client (VS Code extension) is responsible for triggering a diagnostic refresh after receiving the success response. This follows the separation-of-concerns pattern used by other LSP servers.

### Param access pattern

Pygls 2.0.1 converts JSON params to namedtuples via `_dict_to_object()`. All param fields MUST be accessed via `getattr(params, "field", default)`, NOT `params.get("field")` or `params["field"]`. This is the pattern used by all existing handlers (see `commands.py:184`, `commands.py:188`, `commands.py:232`).

### Graceful fallback

All three commands handle the case where `server._indexer._requirement_graph` is NOT a `ScopedRequirementModel` (e.g., workspace not fully indexed yet). They return sensible defaults instead of crashing.

---

## Step 1: Write the failing tests

Create `tests/test_active_test_commands.py`:

```python
# tests/test_active_test_commands.py
"""Tests for ivy/setActiveTest, ivy/listTests, ivy/compileTest commands."""

import asyncio
import sys
from collections import namedtuple
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

IVY_ROOT = Path(__file__).resolve().parent.parent
if str(IVY_ROOT) not in sys.path:
    sys.path.insert(0, str(IVY_ROOT))

from ivy_lsp.analysis.requirement_graph import RequirementGraph
from ivy_lsp.analysis.test_scope import ScopedRequirementModel, TestScope
from ivy_lsp.features.commands import register


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_commands.py -- small, self-contained)
# ---------------------------------------------------------------------------


def _make_registered_handlers():
    """Register handlers on a mock server and return (server, handlers dict)."""
    server = MagicMock()
    registered = {}

    def fake_feature(method):
        def decorator(fn):
            registered[method] = fn
            return fn
        return decorator

    server.feature = fake_feature
    register(server)
    return server, registered


def _make_namedtuple_params(fields: dict):
    """Build a nested namedtuple mimicking pygls _dict_to_object() output."""
    def _convert(obj):
        if isinstance(obj, dict):
            converted = {k: _convert(v) for k, v in obj.items()}
            NT = namedtuple("Object", list(converted.keys()), rename=True)
            return NT(**converted)
        return obj
    return _convert(fields)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scoped_server():
    """Server with ScopedRequirementModel containing two test scopes."""
    server, registered = _make_registered_handlers()

    model = ScopedRequirementModel()
    scope_client = TestScope(
        test_file="/workspace/quic_client_test.ivy",
        include_closure=frozenset({
            "/workspace/quic_client_test.ivy",
            "/workspace/quic_stack.ivy",
            "/workspace/quic_types.ivy",
        }),
        exported_actions=frozenset({"quic.send_packet", "quic.send_frame"}),
        imported_actions=frozenset({"tls.handshake"}),
        tester_role="client",
    )
    scope_server = TestScope(
        test_file="/workspace/quic_server_test.ivy",
        include_closure=frozenset({
            "/workspace/quic_server_test.ivy",
            "/workspace/quic_stack.ivy",
        }),
        exported_actions=frozenset({"quic.recv_packet"}),
        imported_actions=frozenset(),
        tester_role="server",
    )
    model.register_test_scope(scope_client)
    model.register_test_scope(scope_server)

    server._indexer._requirement_graph = model
    return server, registered, model


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestNewCommandsRegistered:
    def test_set_active_test_registered(self):
        _server, registered = _make_registered_handlers()
        assert "ivy/setActiveTest" in registered

    def test_list_tests_registered(self):
        _server, registered = _make_registered_handlers()
        assert "ivy/listTests" in registered

    def test_compile_test_registered(self):
        _server, registered = _make_registered_handlers()
        assert "ivy/compileTest" in registered

    def test_existing_commands_still_registered(self):
        _server, registered = _make_registered_handlers()
        assert "ivy/verify" in registered
        assert "ivy/compile" in registered
        assert "ivy/showModel" in registered
        assert "ivy/capabilities" in registered


# ---------------------------------------------------------------------------
# ivy/setActiveTest
# ---------------------------------------------------------------------------


class TestSetActiveTestHandler:
    def test_set_known_test(self, scoped_server):
        server, registered, model = scoped_server
        params = _make_namedtuple_params({
            "testFile": "/workspace/quic_client_test.ivy",
        })
        result = registered["ivy/setActiveTest"](params)
        assert result["success"] is True
        assert result["activeTest"] == "/workspace/quic_client_test.ivy"
        assert model.get_active_scope() is not None
        assert model.get_active_scope().tester_role == "client"

    def test_clear_active_test(self, scoped_server):
        server, registered, model = scoped_server
        # First set one
        model.set_active_test("/workspace/quic_client_test.ivy")
        # Then clear
        params = _make_namedtuple_params({"testFile": None})
        result = registered["ivy/setActiveTest"](params)
        assert result["success"] is True
        assert result["activeTest"] is None
        assert model.get_active_scope() is None

    def test_set_unknown_test_returns_error(self, scoped_server):
        server, registered, model = scoped_server
        params = _make_namedtuple_params({
            "testFile": "/workspace/nonexistent.ivy",
        })
        result = registered["ivy/setActiveTest"](params)
        assert result["success"] is False
        assert "error" in result

    def test_no_scoped_model_returns_error(self):
        server, registered = _make_registered_handlers()
        # Plain RequirementGraph, not ScopedRequirementModel
        server._indexer._requirement_graph = RequirementGraph()
        params = _make_namedtuple_params({
            "testFile": "/workspace/test.ivy",
        })
        result = registered["ivy/setActiveTest"](params)
        assert result["success"] is False
        assert "error" in result

    def test_switch_between_tests(self, scoped_server):
        server, registered, model = scoped_server
        params_a = _make_namedtuple_params({
            "testFile": "/workspace/quic_client_test.ivy",
        })
        params_b = _make_namedtuple_params({
            "testFile": "/workspace/quic_server_test.ivy",
        })
        registered["ivy/setActiveTest"](params_a)
        assert model.get_active_scope().tester_role == "client"
        registered["ivy/setActiveTest"](params_b)
        assert model.get_active_scope().tester_role == "server"


# ---------------------------------------------------------------------------
# ivy/listTests
# ---------------------------------------------------------------------------


class TestListTestsHandler:
    def test_list_with_scopes(self, scoped_server):
        server, registered, model = scoped_server
        result = registered["ivy/listTests"](None)
        assert "tests" in result
        tests = result["tests"]
        assert len(tests) == 2
        # Sorted by testFile for determinism
        files = [t["testFile"] for t in tests]
        assert files == sorted(files)

    def test_list_entry_fields(self, scoped_server):
        server, registered, model = scoped_server
        result = registered["ivy/listTests"](None)
        entry = next(
            t for t in result["tests"]
            if t["testFile"] == "/workspace/quic_client_test.ivy"
        )
        assert entry["testerRole"] == "client"
        assert entry["exportCount"] == 2
        assert entry["importCount"] == 1
        assert entry["includeCount"] == 3

    def test_list_empty_scopes(self):
        server, registered = _make_registered_handlers()
        server._indexer._requirement_graph = ScopedRequirementModel()
        result = registered["ivy/listTests"](None)
        assert result["tests"] == []

    def test_list_no_scoped_model(self):
        server, registered = _make_registered_handlers()
        server._indexer._requirement_graph = RequirementGraph()
        result = registered["ivy/listTests"](None)
        assert result["tests"] == []

    def test_list_includes_active_marker(self, scoped_server):
        server, registered, model = scoped_server
        model.set_active_test("/workspace/quic_client_test.ivy")
        result = registered["ivy/listTests"](None)
        assert result["activeTest"] == "/workspace/quic_client_test.ivy"

    def test_list_no_active_test(self, scoped_server):
        server, registered, model = scoped_server
        result = registered["ivy/listTests"](None)
        assert result["activeTest"] is None


# ---------------------------------------------------------------------------
# ivy/compileTest
# ---------------------------------------------------------------------------


class TestCompileTestHandler:
    @pytest.mark.asyncio
    async def test_compile_success(self, scoped_server):
        server, registered, model = scoped_server
        server._indexer._resolver.get_staged_path.return_value = (
            "/tmp/staging/quic_client_test.ivy"
        )

        params = _make_namedtuple_params({
            "testFile": "/workspace/quic_client_test.ivy",
            "workDoneToken": None,
        })

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"ok\n", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            result = await registered["ivy/compileTest"](params)

        assert result["success"] is True
        assert result["message"] == "OK"

    @pytest.mark.asyncio
    async def test_compile_uses_staging(self, scoped_server):
        server, registered, model = scoped_server
        server._indexer._resolver.get_staged_path.return_value = (
            "/tmp/staging/quic_client_test.ivy"
        )

        params = _make_namedtuple_params({
            "testFile": "/workspace/quic_client_test.ivy",
            "workDoneToken": None,
        })

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"ok\n", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await registered["ivy/compileTest"](params)

        call_args = mock_exec.call_args[0]
        assert "/tmp/staging/quic_client_test.ivy" in call_args
        assert "/workspace/quic_client_test.ivy" not in call_args

    @pytest.mark.asyncio
    async def test_compile_cmd_has_target_test(self, scoped_server):
        server, registered, model = scoped_server
        server._indexer._resolver.get_staged_path.return_value = None

        params = _make_namedtuple_params({
            "testFile": "/workspace/quic_client_test.ivy",
            "workDoneToken": None,
        })

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"ok\n", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await registered["ivy/compileTest"](params)

        call_args = mock_exec.call_args[0]
        assert "ivyc" in call_args
        assert "target=test" in call_args

    @pytest.mark.asyncio
    async def test_compile_stores_result(self, scoped_server):
        server, registered, model = scoped_server
        server._indexer._resolver.get_staged_path.return_value = None

        params = _make_namedtuple_params({
            "testFile": "/workspace/quic_client_test.ivy",
            "workDoneToken": None,
        })

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"ok\n", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await registered["ivy/compileTest"](params)

        assert "/workspace/quic_client_test.ivy" in model._compilation_results
        assert model._compilation_results["/workspace/quic_client_test.ivy"]["success"]

    @pytest.mark.asyncio
    async def test_compile_no_test_file(self, scoped_server):
        server, registered, model = scoped_server
        params = _make_namedtuple_params({
            "testFile": None,
            "workDoneToken": None,
        })
        result = await registered["ivy/compileTest"](params)
        assert result["success"] is False
        assert "testFile" in result["message"].lower() or "test" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_compile_failure_exit_code(self, scoped_server):
        server, registered, model = scoped_server
        server._indexer._resolver.get_staged_path.return_value = None

        params = _make_namedtuple_params({
            "testFile": "/workspace/quic_client_test.ivy",
            "workDoneToken": None,
        })

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (
                b"", b"error: compilation failed\n"
            )
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            result = await registered["ivy/compileTest"](params)

        assert result["success"] is False
        assert "Exit code 1" in result["message"]

    @pytest.mark.asyncio
    async def test_compile_without_scoped_model_still_works(self):
        """Compile should work even with plain RequirementGraph."""
        server, registered = _make_registered_handlers()
        server._indexer._requirement_graph = RequirementGraph()
        server._indexer._resolver.get_staged_path.return_value = None

        params = _make_namedtuple_params({
            "testFile": "/workspace/test.ivy",
            "workDoneToken": None,
        })

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"ok\n", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            result = await registered["ivy/compileTest"](params)

        assert result["success"] is True
```

## Step 2: Run tests to verify they fail

Run: `python -m pytest tests/test_active_test_commands.py -v`

Expected: FAIL -- handlers `ivy/setActiveTest`, `ivy/listTests`, `ivy/compileTest` are not registered yet, so `registered["ivy/setActiveTest"]` raises `KeyError`.

## Step 3: Implement the three command handlers

Modify `ivy_lsp/features/commands.py`.

**3a. Add import** at line 12 (after `from lsprotocol import types as lsp`):

```python
from ivy_lsp.analysis.test_scope import ScopedRequirementModel
```

**3b. Add three handlers** inside `register()`, after the `ivy_capabilities` handler (after line 259):

```python
    @server.feature("ivy/setActiveTest")
    def ivy_set_active_test(params) -> Dict[str, Any]:
        """Set the active test scope for diagnostics and code lenses.

        The client is responsible for triggering a diagnostic refresh
        after a successful response.
        """
        test_file = getattr(params, "testFile", None)

        try:
            graph = server._indexer._requirement_graph
        except AttributeError:
            return {"success": False, "error": "Indexer not available"}

        if not isinstance(graph, ScopedRequirementModel):
            return {"success": False, "error": "Scoped model not available"}

        graph.set_active_test(test_file)
        active = graph.get_active_scope()

        if test_file is not None and active is None:
            return {
                "success": False,
                "error": f"Unknown test: {test_file}",
                "activeTest": None,
            }

        return {
            "success": True,
            "activeTest": active.test_file if active else None,
        }

    @server.feature("ivy/listTests")
    def ivy_list_tests(params: Any = None) -> Dict[str, Any]:
        """List all discovered test scopes with metadata."""
        try:
            graph = server._indexer._requirement_graph
        except AttributeError:
            return {"tests": [], "activeTest": None}

        if not isinstance(graph, ScopedRequirementModel):
            return {"tests": [], "activeTest": None}

        tests = []
        for test_file in sorted(graph._test_scopes):
            scope = graph._test_scopes[test_file]
            tests.append({
                "testFile": scope.test_file,
                "testerRole": scope.tester_role,
                "exportCount": len(scope.exported_actions),
                "importCount": len(scope.imported_actions),
                "includeCount": len(scope.include_closure),
            })

        active = graph.get_active_scope()
        return {
            "tests": tests,
            "activeTest": active.test_file if active else None,
        }

    @server.feature("ivy/compileTest")
    async def ivy_compile_test(params) -> Dict[str, Any]:
        """Compile a specific test file with ivyc target=test."""
        test_file = getattr(params, "testFile", None)
        if not test_file:
            return {
                "success": False,
                "message": "No testFile specified",
                "output": [],
                "duration": 0.0,
            }

        token = getattr(params, "workDoneToken", None)
        staged = _resolve_via_staging(server, test_file)
        cmd = ["ivyc", "target=test", staged]
        result = await _run_tool(cmd, DEFAULT_COMPILE_TIMEOUT, server, token)

        # Store compilation result in scoped model if available
        try:
            graph = server._indexer._requirement_graph
            if isinstance(graph, ScopedRequirementModel):
                graph._compilation_results[test_file] = result
        except AttributeError:
            pass

        return result
```

## Step 4: Run new tests to verify they pass

Run: `python -m pytest tests/test_active_test_commands.py -v`

Expected: PASS (21 tests)

## Step 5: Run existing command tests for regression

Run: `python -m pytest tests/test_commands.py -v`

Expected: PASS (all existing tests unchanged)

## Step 6: Commit

```bash
git add ivy_lsp/features/commands.py tests/test_active_test_commands.py
git commit -m "feat(commands): add ivy/setActiveTest, ivy/listTests, ivy/compileTest"
```

---

## Corrections from original plan

This rewrite fixes the following issues in the original draft:

| Issue | Original | Fixed |
|-------|----------|-------|
| Wrong decorator | `@server.command("ivy/...")` | `@server.feature("ivy/...")` (matches existing pattern at line 180, 227, 239, 252) |
| Wrong param access | `params.get("testFile")` | `getattr(params, "testFile", None)` (pygls namedtuple compat) |
| Wrong indexer access | `indexer._requirement_graph` | `server._indexer._requirement_graph` (closures capture `server`, not `indexer`) |
| Missing timeout arg | `_run_tool(cmd, staging_dir, server, ...)` | `_run_tool(cmd, DEFAULT_COMPILE_TIMEOUT, server, token)` (timeout is 2nd positional arg) |
| Wrong staging call | `_resolve_via_staging(test_file, indexer)` | `_resolve_via_staging(server, test_file)` (server is 1st arg) |
| Weak test coverage | Only model-level tests (duplicate of Task 5) | Full handler tests: registration, namedtuple params, mock subprocess, error paths, fallback behavior |
| No error handling | Always returns `success: True` | Reports errors for unknown tests, missing model, missing indexer |
| No `os` import needed | Used `os.path.basename()` | Pass full staged path directly (consistent with `ivy/compile` at line 235) |
| Non-deterministic listTests | Dict iteration order | Sorted by `test_file` for determinism |
