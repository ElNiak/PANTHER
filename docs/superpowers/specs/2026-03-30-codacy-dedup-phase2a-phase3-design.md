# Codacy Deduplication: Phase 2A Navigation Factory + Phase 3 Utilities

**Date:** 2026-03-30
**Branch:** `release/v0.12.0-package-redesign-and-workspace-features` (ivy-lsp submodule)
**Context:** Continuation of Codacy clone reduction for PR6. Phases 1 and 2B-2E completed in prior commits (`ecf808c`, `2a909f4`). This spec covers the remaining deferred items.

---

## Phase 2A: Navigation Handler Abstraction

### Problem

The 4 navigation handler files (`definition.py`, `hover.py`, `implementation.py`, `call_hierarchy.py`) share ~20-30 lines of identical boilerplate in their `register()` functions:

1. URI extraction from params
2. Optional `_last_active_uri` tracking
3. Document fetch from workspace
4. Indexer null-check guard
5. Source line splitting
6. URI-to-path conversion
7. `asyncio.get_running_loop()` + `run_in_executor()` dispatch
8. Exception catch + logger.warning + return None

This produces ~16 Codacy clones across 6 handlers (call_hierarchy has 3).

### Design

**New file:** `ivy_lsp/lsp/navigation/_handler.py`

```python
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable

from ivy_lsp.infra.utils import uri_to_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NavigationContext:
    """Shared context prepared for all navigation handlers."""
    uri: str
    doc: Any
    lines: list[str]
    filepath: str
    model: Any       # server.semantic_model (may be None)
    indexer: Any      # server.indexer (guaranteed non-None at this point)
    server: Any       # full server reference for edge cases


async def run_navigation_handler(
    params,
    server,
    compute_fn: Callable[[NavigationContext], Any],
    *,
    trace_method: str | None = None,
    track_active_uri: bool = False,
):
    """Common async wrapper: setup -> executor dispatch -> error handling.

    Returns None if indexer is unavailable or compute_fn raises.
    """
    uri = params.text_document.uri
    if track_active_uri:
        server._last_active_uri = uri
    doc = server.workspace.get_text_document(uri)
    if server.indexer is None:
        return None
    lines = doc.source.split("\n") if doc.source else []
    filepath = uri_to_path(uri)
    ctx = NavigationContext(
        uri=uri,
        doc=doc,
        lines=lines,
        filepath=filepath,
        model=server.semantic_model,
        indexer=server.indexer,
        server=server,
    )
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, compute_fn, ctx)
    except Exception:
        logger.warning(
            "Error in %s for %s",
            trace_method or "navigation",
            filepath,
            exc_info=True,
        )
        return None
```

### Handler modifications

Each handler keeps its `@server.feature()` decoration and any handler-specific logic (tracer calls). The setup+dispatch+exception block is replaced with a call to `run_navigation_handler()`.

| File | Compute function(s) | Flags |
|------|---------------------|-------|
| `definition.py` | `_compute_definition(ctx)` | `track_active_uri=True`, tracer after |
| `hover.py` | `_compute_hover(ctx)` | `track_active_uri=True`, tracer after |
| `implementation.py` | `_compute_implementation(ctx)` | — |
| `call_hierarchy.py` | `_compute_prepare(ctx)`, `_compute_incoming(ctx)`, `_compute_outgoing(ctx)` | — |

Tracer integration stays in `definition.py` and `hover.py` (only 2/4 files use it — not worth abstracting).

---

## Phase 3A: `get_last_component` Utility

### Problem

29 occurrences of `name.rsplit(".", 1)[-1] if "." in name else name` scattered across ~15 files.

### Design

**New file:** `ivy_lsp/infra/utils/name_utils.py`

```python
def get_last_component(qualified_name: str) -> str:
    """Extract leaf from dotted name: 'a.b.c' -> 'c', 'c' -> 'c'."""
    return qualified_name.rsplit(".", 1)[-1] if "." in qualified_name else qualified_name
```

All 29 call sites updated to `get_last_component(var)`. Sites that chain `.lower()` become `get_last_component(var).lower()`. Sites used inline in f-strings or keyword args use the function call directly.

### Files affected

- `ivy_lsp/lsp/document_highlight.py`
- `ivy_lsp/lsp/workspace_symbols.py`
- `ivy_lsp/lsp/navigation/definition.py`
- `ivy_lsp/lsp/navigation/hover.py`
- `ivy_lsp/lsp/navigation/implementation.py`
- `ivy_lsp/lsp/navigation/call_hierarchy.py`
- `ivy_lsp/lsp/navigation/references.py`
- `ivy_lsp/lsp/rename.py`
- `ivy_lsp/lsp/ui/selection_range.py`
- `ivy_lsp/core/adapters/ast_enrichment_adapter.py`
- `ivy_lsp/core/analysis/requirement_graph.py`
- `ivy_lsp/core/compilation/graph_enrichment.py`
- `ivy_lsp/core/parsing/ast_to_symbols.py`
- `ivy_lsp/core/semantic/model_builder.py`
- `ivy_lsp/mcp/server.py`

---

## Phase 3B: Node Type Filter Helpers

### Problem

7+ occurrences of `[n for n in nodes if isinstance(n, SymbolNode)]` and `next((n for n in nodes if isinstance(n, node_type)), None)` patterns in navigation and completion code.

### Design

**New file:** `ivy_lsp/core/semantic/node_filters.py`

```python
from __future__ import annotations
from typing import Iterable, TypeVar

T = TypeVar("T")


def nodes_of_type(nodes: Iterable, node_type: type[T]) -> list[T]:
    """Filter nodes by type."""
    return [n for n in nodes if isinstance(n, node_type)]


def first_node_of_type(nodes: Iterable, node_type: type[T]) -> T | None:
    """First node of type, or None."""
    return next((n for n in nodes if isinstance(n, node_type)), None)
```

### Files affected

- `ivy_lsp/lsp/completion.py`
- `ivy_lsp/lsp/navigation/hover.py`
- `ivy_lsp/lsp/navigation/call_hierarchy.py`

---

## Phase 3C: Task Cancel/Register Helpers

### Problem

5 clones of cancel-old-task + register-new-task + done-callback pattern in `publisher.py`.

### Design

**In `ivy_lsp/lsp/diagnostics/publisher.py`** (module-level functions, not a new file):

```python
def _cancel_task(tasks: dict[str, asyncio.Task], key: str) -> None:
    """Cancel and remove an existing task if it's still running."""
    old = tasks.pop(key, None)
    if old and not old.done():
        old.cancel()


def _register_task(
    tasks: dict[str, asyncio.Task], key: str, coro
) -> asyncio.Task:
    """Cancel any existing task for key, create new one with auto-cleanup."""
    _cancel_task(tasks, key)
    task = asyncio.get_running_loop().create_task(coro)
    task.add_done_callback(
        lambda t, k=key: tasks.pop(k, None) if tasks.get(k) is t else None
    )
    tasks[key] = task
    return task
```

### Usage transformation

Before:
```python
old_task = _debounce_tasks.pop(uri, None)
if old_task and not old_task.done():
    old_task.cancel()
# ... define coro ...
loop = asyncio.get_running_loop()
task = loop.create_task(_debounced())
task.add_done_callback(lambda t, u=uri: (_debounce_tasks.pop(u, None) if _debounce_tasks.get(u) is t else None))
_debounce_tasks[uri] = task
```

After:
```python
# ... define coro ...
_register_task(_debounce_tasks, uri, _debounced())
```

Cancel-only sites (did_close):
```python
_cancel_task(_debounce_tasks, uri)
_cancel_task(_deep_tasks, uri)
```

---

## Verification

1. `pytest tests/ -x -q` — all 2784+ tests pass
2. No new pyright type errors
3. No behavioral changes — pure refactoring
4. Pre-commit hooks pass (black, isort, ruff)

## Estimated Impact

| Item | Codacy clones eliminated | Net lines saved |
|------|--------------------------|-----------------|
| Phase 2A: nav handler factory | ~16 | ~120 |
| Phase 3A: get_last_component | ~12 | ~29 consolidated |
| Phase 3B: node_filters | ~7 | ~20 |
| Phase 3C: task helpers | ~5 | ~25 |
| **Total** | **~40** | **~194** |
