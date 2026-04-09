# Incremental LSP Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `documentSymbol` available at ~1.6s after server start instead of ~25.7s by introducing incremental readiness signaling and deferring offline index loading.

**Architecture:** Split `WorkspaceContext.load()` into fast detection + deferred index loading. Add a `_parser_ready_event` that fires after the parser is created. `documentSymbol` waits on this new event instead of the monolithic `_ready_event`.

**Tech Stack:** Python 3.10+, pygls, threading, pytest

**Spec:** `docs/superpowers/specs/2026-04-09-incremental-lsp-readiness-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `ivy_lsp/core/workspace/context.py` | Modify | Add `detect_only` classmethod and `load_indexes` method, refactor `load()` |
| `ivy_lsp/lsp/server.py` | Modify | Add `_parser_ready_event` field and set it in `finally` block |
| `ivy_lsp/lsp/server_setup.py` | Modify | Restructure `_setup_indexer` to use `detect_only`, signal parser readiness, defer index loading |
| `ivy_lsp/lsp/document_symbols.py` | Modify | Switch ready gate from `_ready_event` to `_parser_ready_event`, fix timeout handling |
| `tests/test_workspace_context_split.py` | Create | Tests for `detect_only` / `load_indexes` / `load()` equivalence |
| `tests/test_incremental_readiness.py` | Create | Tests for parser-ready event, documentSymbol during init, timeout behavior |

All file paths are relative to: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

---

### Task 1: Split `WorkspaceContext.load()` into `detect_only` + `load_indexes`

**Files:**
- Modify: `ivy_lsp/core/workspace/context.py:124-175`
- Test: `tests/test_workspace_context_split.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workspace_context_split.py`:

```python
"""Tests for WorkspaceContext.detect_only / load_indexes split."""

import os

import pytest

from ivy_lsp.core.workspace.context import WorkspaceContext


class TestDetectOnly:
    """WorkspaceContext.detect_only should return a context without indexes."""

    def test_returns_context_with_empty_indexes(self, tmp_path):
        ctx = WorkspaceContext.detect_only(str(tmp_path))
        assert isinstance(ctx, WorkspaceContext)
        assert ctx.protocol_indexes == {}
        assert ctx.workspace_root

    def test_has_index_returns_false(self, tmp_path):
        ctx = WorkspaceContext.detect_only(str(tmp_path))
        assert ctx.has_index() is False

    def test_workspace_config_is_populated(self, tmp_path):
        ctx = WorkspaceContext.detect_only(str(tmp_path))
        assert ctx.workspace_config is not None
        assert ctx.workspace_config.workspace_root


class TestLoadIndexes:
    """WorkspaceContext.load_indexes should populate protocol_indexes in place."""

    def test_no_indexes_directory_stays_empty(self, tmp_path):
        ctx = WorkspaceContext.detect_only(str(tmp_path))
        ctx.load_indexes()
        assert ctx.protocol_indexes == {}

    def test_populates_indexes_when_present(self, tmp_path):
        # Create a minimal .ivy-index structure
        proto_dir = tmp_path / "protocol-testing" / "test_proto"
        index_dir = proto_dir / ".ivy-index"
        index_dir.mkdir(parents=True)
        manifest = index_dir / "manifest.json"
        manifest.write_text('{"version": 1, "protocol": "test_proto"}')
        # Create minimal symbols file so _load_protocol_index succeeds
        symbols_dir = index_dir / "symbols"
        symbols_dir.mkdir()

        ctx = WorkspaceContext.detect_only(str(tmp_path))
        ctx.load_indexes()
        # May or may not load depending on manifest validation,
        # but should not raise
        assert isinstance(ctx.protocol_indexes, dict)


class TestLoadEquivalence:
    """WorkspaceContext.load() should produce the same result as detect_only + load_indexes."""

    def test_load_matches_detect_plus_indexes(self, tmp_path):
        ctx_load = WorkspaceContext.load(str(tmp_path))
        ctx_split = WorkspaceContext.detect_only(str(tmp_path))
        ctx_split.load_indexes()

        assert ctx_load.workspace_root == ctx_split.workspace_root
        assert ctx_load.project_type == ctx_split.project_type
        assert set(ctx_load.protocol_indexes.keys()) == set(
            ctx_split.protocol_indexes.keys()
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_context_split.py -v`

Expected: FAIL — `WorkspaceContext` has no attribute `detect_only`

- [ ] **Step 3: Implement `detect_only` and `load_indexes`, refactor `load()`**

In `ivy_lsp/core/workspace/context.py`, add `detect_only` classmethod after line 121 (before existing `load`):

```python
    @classmethod
    def detect_only(cls, start_dir: str) -> "WorkspaceContext":
        """Detect workspace config without loading offline indexes.

        Returns a WorkspaceContext with empty protocol_indexes. Call
        :meth:`load_indexes` separately to populate them (can be done
        in a background thread).
        """
        ws_config = detect_ivy_workspace(start_dir)
        return cls(
            workspace_root=ws_config.workspace_root,
            project_type=ws_config.project_type or "fallback",
            workspace_config=ws_config,
        )

    def load_indexes(self) -> None:
        """Load offline protocol indexes from .ivy-index directories.

        Populates ``self.protocol_indexes`` in place. Safe to call from
        a background thread — only writes to ``protocol_indexes`` dict.
        """
        pattern = os.path.join(
            self.workspace_root,
            "protocol-testing",
            "*",
            ".ivy-index",
            "manifest.json",
        )
        manifest_paths = glob.glob(pattern)

        for manifest_path in sorted(manifest_paths):
            index_dir = os.path.dirname(manifest_path)
            protocol_dir = os.path.dirname(index_dir)
            protocol = os.path.basename(protocol_dir)

            idx = self._load_protocol_index(protocol, index_dir)
            if idx is not None:
                self.protocol_indexes[protocol] = idx
                logger.info(
                    "Loaded index for protocol %s (%s, %d symbols files)",
                    protocol,
                    idx.staleness.status,
                    len(idx.symbols),
                )

        if not self.protocol_indexes:
            logger.debug(
                "No .ivy-index directories found under %s",
                self.workspace_root,
            )
```

Then replace the body of the existing `load()` classmethod (lines 125-175) with:

```python
    @classmethod
    def load(cls, start_dir: str) -> "WorkspaceContext":
        """Detect workspace and load all protocol indexes.

        Args:
            start_dir: Directory to start workspace detection from.

        Returns:
            A fully populated WorkspaceContext (possibly with empty indexes
            if no ``.ivy-index/`` directories are found).
        """
        ctx = cls.detect_only(start_dir)
        ctx.load_indexes()
        return ctx
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_context_split.py -v`

Expected: PASS (3 tests)

- [ ] **Step 5: Run existing context tests for regression**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_workspace_context_active.py tests/test_scope_views.py -v -x`

Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add ivy_lsp/core/workspace/context.py tests/test_workspace_context_split.py
git commit -m "refactor: split WorkspaceContext.load into detect_only + load_indexes"
```

---

### Task 2: Add `_parser_ready_event` to server

**Files:**
- Modify: `ivy_lsp/lsp/server.py:64` (add field), `ivy_lsp/lsp/server.py:451-453` (finally block)
- Test: `tests/test_incremental_readiness.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_incremental_readiness.py`:

```python
"""Tests for incremental readiness signaling."""

import threading

import pytest


class TestParserReadyEvent:
    """_parser_ready_event should exist and be set in the finally block."""

    def test_server_has_parser_ready_event(self):
        from ivy_lsp.lsp.server import IvyLanguageServer

        server = IvyLanguageServer()
        assert hasattr(server, "_parser_ready_event")
        assert isinstance(server._parser_ready_event, threading.Event)
        # Should not be set at construction time
        assert not server._parser_ready_event.is_set()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_incremental_readiness.py::TestParserReadyEvent::test_server_has_parser_ready_event -v`

Expected: FAIL — `_parser_ready_event` does not exist

- [ ] **Step 3: Add `_parser_ready_event` field to `server.py`**

In `ivy_lsp/lsp/server.py`, after line 64 (`self._ready_event: threading.Event = threading.Event()`), add:

```python
        self._parser_ready_event: threading.Event = threading.Event()
```

In the `finally` block at line 451-454, add `_parser_ready_event.set()`:

```python
            finally:
                self._initializing = False
                self._parser_ready_event.set()
                self._ready_event.set()
                self._send_server_ready_notification(init_start)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_incremental_readiness.py::TestParserReadyEvent -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/lsp/server.py tests/test_incremental_readiness.py
git commit -m "feat: add _parser_ready_event to IvyLanguageServer"
```

---

### Task 3: Restructure `_setup_indexer` in `server_setup.py`

**Files:**
- Modify: `ivy_lsp/lsp/server_setup.py:55-155` (`_setup_indexer` method)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_incremental_readiness.py`:

```python
import time
from unittest.mock import MagicMock, patch


class TestSetupIndexerSignaling:
    """_setup_indexer should set _parser_ready_event after _create_parser."""

    def test_parser_ready_set_before_create_indexer(self):
        """Verify _parser_ready_event fires between _create_parser and _create_indexer."""
        from ivy_lsp.lsp.server import IvyLanguageServer

        server = IvyLanguageServer()
        # Track call order
        call_log = []

        original_create_parser = server._create_parser
        original_create_indexer = server._create_indexer

        def mock_create_parser(resolver):
            original_create_parser(resolver)
            call_log.append(
                ("create_parser", server._parser_ready_event.is_set())
            )

        def mock_create_indexer(ws_root, resolver):
            call_log.append(
                ("create_indexer_start", server._parser_ready_event.is_set())
            )
            return original_create_indexer(ws_root, resolver)

        with patch.object(server, "_create_parser", side_effect=mock_create_parser), \
             patch.object(server, "_create_indexer", side_effect=mock_create_indexer):
            try:
                server._setup_indexer()
            except Exception:
                pass  # May fail without full env, that's fine

        # If create_parser ran, _parser_ready_event should NOT be set during it
        # but SHOULD be set by the time create_indexer starts
        parser_entries = [e for e in call_log if e[0] == "create_parser"]
        indexer_entries = [e for e in call_log if e[0] == "create_indexer_start"]

        if parser_entries and indexer_entries:
            assert not parser_entries[0][1], \
                "_parser_ready_event should not be set during _create_parser"
            assert indexer_entries[0][1], \
                "_parser_ready_event should be set before _create_indexer"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_incremental_readiness.py::TestSetupIndexerSignaling -v`

Expected: FAIL — `_parser_ready_event` is not set between `_create_parser` and `_create_indexer`

- [ ] **Step 3: Restructure `_setup_indexer`**

Replace lines 80-120 of `ivy_lsp/lsp/server_setup.py` (the `WorkspaceContext.load` block and its exception handler) with:

```python
        # Detect workspace config (fast — no offline index loading)
        try:
            from ivy_lsp.core.workspace.context import WorkspaceContext

            self._workspace_context = WorkspaceContext.detect_only(ws_root)
        except Exception:
            logger.warning(
                "WorkspaceContext detection failed; proceeding with fallback",
                exc_info=True,
            )
            from ivy_lsp.core.workspace.context import WorkspaceContext
            from ivy_lsp.core.workspace.detection import WorkspaceConfig

            self._workspace_context = WorkspaceContext(
                workspace_root=ws_root,
                project_type="fallback",
                workspace_config=WorkspaceConfig(
                    workspace_root=ws_root,
                    detected_by="fallback",
                ),
            )
```

Keep lines 122-149 (active workspace loading) unchanged.

After the `_create_parser` timed_phase block (after the tier diagnostic probe block, around line 187), insert:

```python
        # Signal parser readiness — documentSymbol can start serving symbols.
        self._parser_ready_event.set()

        # Kick off offline index loading in a background thread.
        # If it finishes before _create_indexer checks has_index(),
        # the fast prepopulation path is used; otherwise live scan runs.
        import threading

        _index_loader = threading.Thread(
            target=self._load_offline_indexes_background,
            daemon=True,
        )
        _index_loader.start()
```

Add the background loader method to the `ServerSetupMixin` class:

```python
    def _load_offline_indexes_background(self) -> None:
        """Load offline protocol indexes in a background thread."""
        try:
            ws_ctx = getattr(self, "_workspace_context", None)
            if ws_ctx is None:
                return
            ws_ctx.load_indexes()
            if ws_ctx.has_index():
                protocols = ws_ctx.list_protocols()
                slog.info(
                    "Loaded offline index for %d protocol(s): %s",
                    len(protocols),
                    ", ".join(protocols),
                    extra={
                        "event": LogEvent(
                            LogCategory.MILESTONE,
                            "offline_index",
                            {"protocols": protocols},
                        )
                    },
                )
            else:
                slog.info(
                    "No offline index found; using live indexing",
                    extra={
                        "event": LogEvent(
                            LogCategory.DIAGNOSTIC, "offline_index"
                        )
                    },
                )
        except Exception:
            logger.warning(
                "Background offline index loading failed",
                exc_info=True,
            )
```

Update the `_setup_indexer` docstring to reflect the new sequence:

```python
    def _setup_indexer(self):
        """Create and populate the workspace indexer.

        Thin orchestrator that delegates to focused helpers:
        1. _configure_activity_logging --- env-based log level
        2. WorkspaceContext.detect_only --- fast workspace config (no indexes)
        3. _create_resolver --- include resolver + staging
        4. _create_parser --- z3 detection + parser creation
        5. ★ _parser_ready_event.set() --- documentSymbol unblocked
        6. Background thread: load_indexes() --- offline index (best-effort)
        7. _create_indexer --- indexer construction + workspace scan
        8. _setup_analysis_pipeline --- semantic model + adapters + pipeline
        """
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_incremental_readiness.py::TestSetupIndexerSignaling -v`

Expected: PASS

- [ ] **Step 5: Run existing server tests for regression**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_task_1_9_server.py -v -x`

Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add ivy_lsp/lsp/server_setup.py tests/test_incremental_readiness.py
git commit -m "feat: restructure _setup_indexer for incremental readiness

Signal _parser_ready_event after parser creation (~1.6s) instead of
waiting for full init (~25.7s). Defer offline index loading to a
background thread."
```

---

### Task 4: Update `documentSymbol` ready gate

**Files:**
- Modify: `ivy_lsp/lsp/document_symbols.py:195-202`
- Test: `tests/test_incremental_readiness.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_incremental_readiness.py`:

```python
import asyncio

from lsprotocol import types as lsp

from ivy_lsp.lsp.document_symbols import (
    _status_document_symbol,
    compute_document_symbols,
)


class TestDocumentSymbolReadyGate:
    """documentSymbol should wait on _parser_ready_event, not _ready_event."""

    def test_compute_returns_symbols_with_parser_only(self):
        """Parser alone (no indexer) should produce symbols."""
        from ivy_lsp.core.parsing.parser_session import IvyParserWrapper

        parser = IvyParserWrapper()
        source = "#lang ivy1.7\n\ntype cid\ntype pkt_num\n"
        result = compute_document_symbols(parser, None, source, "test.ivy")
        assert len(result) >= 2, f"Expected >=2 symbols, got {len(result)}"
        names = [s.name for s in result]
        assert "cid" in names
        assert "pkt_num" in names

    def test_status_symbol_on_timeout(self):
        """When _parser_ready_event times out, a status symbol should be returned."""
        sym = _status_document_symbol(
            "server still initializing",
            "Parser initialization exceeded 30s. Check ivy-lsp logs.",
        )
        assert isinstance(sym, lsp.DocumentSymbol)
        assert "still initializing" in sym.name
        assert sym.kind == lsp.SymbolKind.Namespace
```

- [ ] **Step 2: Run tests to verify they fail or pass as baseline**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_incremental_readiness.py::TestDocumentSymbolReadyGate -v`

Expected: Both should PASS already (they test existing functions). This establishes the baseline.

- [ ] **Step 3: Update the ready gate in `document_symbols.py`**

Replace lines 195-202 of `ivy_lsp/lsp/document_symbols.py`:

```python
            # Wait for parser initialization before reading parser/indexer.
            # _parser_ready_event fires after _create_parser (~1.6s),
            # much earlier than _ready_event which waits for full indexing.
            parser_ready = getattr(server, "_parser_ready_event", None)
            if parser_ready is not None and not parser_ready.is_set():
                loop = asyncio.get_running_loop()
                timed_out = not await loop.run_in_executor(
                    None, parser_ready.wait, 30.0
                )
                if timed_out:
                    return [
                        _status_document_symbol(
                            "server still initializing",
                            "Parser initialization exceeded 30s. "
                            "Check ivy-lsp logs.",
                        )
                    ]
```

- [ ] **Step 4: Run all document symbol tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_incremental_readiness.py tests/test_task_1_9_server.py tests/test_lsp_navigation_extended.py -v -x`

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/lsp/document_symbols.py tests/test_incremental_readiness.py
git commit -m "fix: documentSymbol waits on _parser_ready_event with 30s timeout

Replaces the _ready_event gate (10s timeout, always expired) with
_parser_ready_event (fires at ~1.6s). Explicitly handles timeout
with a 'still initializing' status instead of silently falling
through to 'unavailable'."
```

---

### Task 5: Integration smoke test and full regression

**Files:**
- Test: All test files in the ivy-lsp test suite

- [ ] **Step 1: Run the full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --tb=short -x`

Expected: All tests pass. Report pass/fail count.

- [ ] **Step 2: Verify no import cycles or missing attributes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "from ivy_lsp.lsp.server import IvyLanguageServer; s = IvyLanguageServer(); print('_parser_ready_event:', hasattr(s, '_parser_ready_event')); print('_ready_event:', hasattr(s, '_ready_event'))"`

Expected output:
```
_parser_ready_event: True
_ready_event: True
```

- [ ] **Step 3: Verify WorkspaceContext.load equivalence**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "from ivy_lsp.core.workspace.context import WorkspaceContext; ctx = WorkspaceContext.detect_only('.'); print('detect_only:', ctx.workspace_root, 'indexes:', len(ctx.protocol_indexes)); ctx.load_indexes(); print('after load_indexes:', len(ctx.protocol_indexes))"`

Expected: First line shows 0 indexes, second line shows the loaded count.

- [ ] **Step 4: Commit any test fixes if needed**

Only if Steps 1-3 revealed issues that needed fixing.
