# Codacy Dedup Phase 2A + Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate ~40 Codacy clones by extracting a navigation handler factory, a `get_last_component` utility, node-type filter helpers, and async task management helpers.

**Architecture:** New shared modules (`_handler.py`, `name_utils.py`, `node_filters.py`) plus inline helpers in `publisher.py`. All navigation handlers delegate setup+dispatch to `run_navigation_handler()`. All `rsplit(".", 1)[-1]` patterns call `get_last_component()`. All `isinstance(n, SymbolNode)` filter patterns call `nodes_of_type()`/`first_node_of_type()`.

**Tech Stack:** Python 3.10+, pygls (LSP server), lsprotocol, pytest

**Working directory:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp`

---

### Task 1: Create navigation handler shared module

**Files:**
- Create: `ivy_lsp/lsp/navigation/_handler.py`

- [ ] **Step 1: Create `_handler.py`**

```python
"""Shared navigation handler infrastructure."""

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
    position: Any  # lsp.Position
    model: Any  # server.semantic_model (may be None)
    indexer: Any  # server.indexer (guaranteed non-None)
    server: Any  # full server reference for edge cases


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
        position=params.position,
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

- [ ] **Step 2: Verify import works**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "from ivy_lsp.lsp.navigation._handler import NavigationContext, run_navigation_handler; print('OK')"`

Expected: `OK`

---

### Task 2: Refactor definition.py to use run_navigation_handler

**Files:**
- Modify: `ivy_lsp/lsp/navigation/definition.py:166-221` (register function)

- [ ] **Step 1: Replace register() body**

Replace the entire `register()` function (lines 166-221) with:

```python
def register(server) -> None:
    """Register the ``textDocument/definition`` feature handler."""

    from ivy_lsp.lsp.navigation._handler import run_navigation_handler

    @server.feature(lsp.TEXT_DOCUMENT_DEFINITION)
    async def definition(
        params: lsp.DefinitionParams,
    ) -> Optional[Union[lsp.Location, List[lsp.Location]]]:
        """Handle textDocument/definition requests."""
        result = await run_navigation_handler(
            params,
            server,
            lambda ctx: goto_definition(
                ctx.indexer,
                ctx.filepath,
                ctx.position,
                ctx.lines,
                semantic_model=ctx.model,
            ),
            track_active_uri=True,
            trace_method="textDocument/definition",
        )
        try:
            from ivy_lsp.infra.observability import get_tracer

            tracer = get_tracer()
            if tracer is not None:
                lines = server.workspace.get_text_document(
                    params.text_document.uri
                ).source.split("\n")
                word = (
                    word_at_position(lines, params.position) if lines else None
                )
                loc_count = (
                    len(result)
                    if isinstance(result, list)
                    else (1 if result is not None else 0)
                )
                tracer.trace_lsp_request(
                    method="textDocument/definition",
                    filepath=uri_to_path(params.text_document.uri),
                    position=f"{params.position.line}:{params.position.character}",
                    word=word,
                    result_summary=(
                        f"{loc_count} location(s)" if result else None
                    ),
                )
        except Exception:
            pass
        return result
```

Remove unused `asyncio` import from the file's top-level imports (it's no longer needed in `register()`).

- [ ] **Step 2: Run definition tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_definition.py -x -q 2>&1 | tail -5`

Expected: All tests pass.

---

### Task 3: Refactor hover.py to use run_navigation_handler

**Files:**
- Modify: `ivy_lsp/lsp/navigation/hover.py:359-405` (register function)

- [ ] **Step 1: Replace register() body**

Replace the `register()` function (lines 359-405) with:

```python
def register(server) -> None:
    """Register the textDocument/hover feature handler."""

    from ivy_lsp.lsp.navigation._handler import run_navigation_handler

    @server.feature(lsp.TEXT_DOCUMENT_HOVER)
    async def hover(params: lsp.HoverParams) -> Optional[lsp.Hover]:
        result = await run_navigation_handler(
            params,
            server,
            lambda ctx: get_hover_info(
                ctx.indexer,
                ctx.filepath,
                ctx.position,
                ctx.lines,
                ctx.model,
            ),
            track_active_uri=True,
            trace_method="textDocument/hover",
        )
        try:
            from ivy_lsp.infra.observability import get_tracer

            tracer = get_tracer()
            if tracer is not None:
                lines = server.workspace.get_text_document(
                    params.text_document.uri
                ).source.split("\n")
                word = (
                    word_at_position(lines, params.position) if lines else None
                )
                content_len = 0
                if result and result.contents:
                    content_len = len(getattr(result.contents, "value", ""))
                tracer.trace_lsp_request(
                    method="textDocument/hover",
                    filepath=uri_to_path(params.text_document.uri),
                    position=f"{params.position.line}:{params.position.character}",
                    word=word,
                    result_summary=(
                        f"Hover content, {content_len} chars" if result else None
                    ),
                )
        except Exception:
            pass
        return result
```

Remove unused `asyncio` import.

- [ ] **Step 2: Run hover tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_hover.py -x -q 2>&1 | tail -5`

Expected: All tests pass.

---

### Task 4: Refactor implementation.py to use run_navigation_handler

**Files:**
- Modify: `ivy_lsp/lsp/navigation/implementation.py:144-171` (register function)

- [ ] **Step 1: Replace register() body**

Replace the `register()` function (lines 144-171) with:

```python
def register(server) -> None:
    """Register the ``textDocument/implementation`` feature handler."""

    from ivy_lsp.lsp.navigation._handler import run_navigation_handler

    @server.feature(lsp.TEXT_DOCUMENT_IMPLEMENTATION)
    async def implementation(
        params: lsp.ImplementationParams,
    ) -> Optional[Union[lsp.Location, List[lsp.Location]]]:
        """Handle textDocument/implementation requests."""
        return await run_navigation_handler(
            params,
            server,
            lambda ctx: goto_implementation(
                ctx.indexer,
                ctx.filepath,
                ctx.position,
                ctx.lines,
            ),
            track_active_uri=True,
            trace_method="textDocument/implementation",
        )
```

Remove unused `asyncio` import from the file's top-level imports.

- [ ] **Step 2: Run implementation tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_implementation.py tests/test_goto_implementation.py -x -q 2>&1 | tail -5`

Expected: All tests pass (some files may not exist — that's OK).

---

### Task 5: Refactor call_hierarchy.py prepare handler

**Files:**
- Modify: `ivy_lsp/lsp/navigation/call_hierarchy.py:464-490` (only the `prepare` handler inside `register()`)

Note: Only the `prepare` handler follows the standard URI-based pattern. The `incoming_calls` and `outgoing_calls` handlers use `params.item` (not `params.text_document`), so they stay as-is.

- [ ] **Step 1: Replace the prepare handler within register()**

Replace lines 467-490 (the `prepare` nested function) with:

```python
    from ivy_lsp.lsp.navigation._handler import run_navigation_handler

    @server.feature(lsp.TEXT_DOCUMENT_PREPARE_CALL_HIERARCHY)
    async def prepare(
        params: lsp.CallHierarchyPrepareParams,
    ) -> Optional[List[lsp.CallHierarchyItem]]:
        """Handle textDocument/prepareCallHierarchy requests."""
        return await run_navigation_handler(
            params,
            server,
            lambda ctx: prepare_call_hierarchy(
                ctx.indexer,
                ctx.filepath,
                ctx.position,
                ctx.lines,
            ),
            trace_method="textDocument/prepareCallHierarchy",
        )
```

Keep the `incoming_calls` and `outgoing_calls` handlers unchanged.

- [ ] **Step 2: Run call hierarchy tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_call_hierarchy.py -x -q 2>&1 | tail -5`

Expected: All tests pass.

- [ ] **Step 3: Run all navigation tests together**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_definition.py tests/test_hover.py tests/test_call_hierarchy.py -x -q 2>&1 | tail -5`

Expected: All tests pass.

- [ ] **Step 4: Commit Phase 2A**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/lsp/navigation/_handler.py ivy_lsp/lsp/navigation/definition.py ivy_lsp/lsp/navigation/hover.py ivy_lsp/lsp/navigation/implementation.py ivy_lsp/lsp/navigation/call_hierarchy.py
git commit -m "refactor: extract run_navigation_handler to deduplicate nav boilerplate"
```

---

### Task 6: Create get_last_component utility

**Files:**
- Create: `ivy_lsp/infra/utils/name_utils.py`
- Create: `tests/test_name_utils.py`

- [ ] **Step 1: Write test**

```python
"""Tests for ivy_lsp.infra.utils.name_utils."""

from ivy_lsp.infra.utils.name_utils import get_last_component


class TestGetLastComponent:
    def test_dotted_name(self):
        assert get_last_component("a.b.c") == "c"

    def test_single_name(self):
        assert get_last_component("foo") == "foo"

    def test_one_dot(self):
        assert get_last_component("frame.ack") == "ack"

    def test_empty_string(self):
        assert get_last_component("") == ""

    def test_trailing_dot(self):
        assert get_last_component("a.") == ""

    def test_only_dot(self):
        assert get_last_component(".") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_name_utils.py -x -q 2>&1 | tail -5`

Expected: FAIL — `ModuleNotFoundError: No module named 'ivy_lsp.infra.utils.name_utils'`

- [ ] **Step 3: Create name_utils.py**

```python
"""Name utilities for Ivy qualified names."""

from __future__ import annotations


def get_last_component(qualified_name: str) -> str:
    """Extract the leaf from a dotted name: ``'a.b.c'`` -> ``'c'``, ``'c'`` -> ``'c'``."""
    return qualified_name.rsplit(".", 1)[-1] if "." in qualified_name else qualified_name
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_name_utils.py -x -q 2>&1 | tail -5`

Expected: 6 passed

---

### Task 7: Update all get_last_component call sites

**Files to modify** (29 call sites across 15 files):

Each file needs `from ivy_lsp.infra.utils.name_utils import get_last_component` added to its imports, then each `X.rsplit(".", 1)[-1] if "." in X else X` or bare `X.rsplit(".", 1)[-1]` replaced with `get_last_component(X)`.

- [ ] **Step 1: Update navigation files (already touched in Phase 2A)**

**`ivy_lsp/lsp/navigation/definition.py:155`**
```python
# Before:
            last = word.rsplit(".", 1)[-1]
# After:
            last = get_last_component(word)
```

**`ivy_lsp/lsp/navigation/hover.py:163`** and **`hover.py:219`**
```python
# Before:
        last = symbol_name.rsplit(".", 1)[-1]
        # ...
        last = word.rsplit(".", 1)[-1]
# After:
        last = get_last_component(symbol_name)
        # ...
        last = get_last_component(word)
```

**`ivy_lsp/lsp/navigation/implementation.py:75-77`**
```python
# Before:
    last_component = (
        action_name.rsplit(".", 1)[-1] if "." in action_name else action_name
    )
# After:
    last_component = get_last_component(action_name)
```

**`ivy_lsp/lsp/navigation/call_hierarchy.py:98`**, **`258`**, **`391`**
```python
# Before:
    last = name.rsplit(".", 1)[-1] if "." in name else name
    # ...
    last_component = item_name.rsplit(".", 1)[-1] if "." in item_name else item_name
    # ...
    last_component = item_name.rsplit(".", 1)[-1] if "." in item_name else item_name
# After:
    last = get_last_component(name)
    # ...
    last_component = get_last_component(item_name)
    # ...
    last_component = get_last_component(item_name)
```

**`ivy_lsp/lsp/navigation/references.py:69`**
```python
# Before:
    name = word.rsplit(".", 1)[-1] if "." in word else word
# After:
    name = get_last_component(word)
```

- [ ] **Step 2: Update LSP feature files**

**`ivy_lsp/lsp/document_highlight.py:32`**
```python
# Before:
    name = word.rsplit(".", 1)[-1] if "." in word else word
# After:
    name = get_last_component(word)
```

**`ivy_lsp/lsp/workspace_symbols.py:68`** and **`139`**
```python
# Before:
        leaf = fs.qualified_name.rsplit(".", 1)[-1].lower()
# After:
        leaf = get_last_component(fs.qualified_name).lower()
```

**`ivy_lsp/lsp/rename.py:49`**
```python
# Before:
    name = word.rsplit(".", 1)[-1] if "." in word else word
# After:
    name = get_last_component(word)
```

**`ivy_lsp/lsp/ui/selection_range.py:62`**
```python
# Before:
    name = word.rsplit(".", 1)[-1] if "." in word else word
# After:
    name = get_last_component(word)
```

- [ ] **Step 3: Update core files**

**`ivy_lsp/core/adapters/ast_enrichment_adapter.py:109`** and **`171`**
```python
# Before:
        short_name = name.rsplit(".", 1)[-1] if "." in name else name
# After:
        short_name = get_last_component(name)
```

**`ivy_lsp/core/compilation/graph_enrichment.py:49`**, **`72`**, **`94`**, **`157`**
```python
# Before:
            name=sort_name.rsplit(".", 1)[-1],
            # ...
            name=sym_name.rsplit(".", 1)[-1],
            # ...
            name=action_name.rsplit(".", 1)[-1],
            # ...
            name=action_name.rsplit(".", 1)[-1],
# After:
            name=get_last_component(sort_name),
            # ...
            name=get_last_component(sym_name),
            # ...
            name=get_last_component(action_name),
            # ...
            name=get_last_component(action_name),
```

**`ivy_lsp/core/analysis/requirement_graph.py:494`**, **`506`**, **`529`**
```python
# Before:
                name=sym.name.rsplit(".", 1)[-1],
                # ...
                name=req.monitor_action.rsplit(".", 1)[-1],
                # ...
                name=var_name.rsplit(".", 1)[-1],
# After:
                name=get_last_component(sym.name),
                # ...
                name=get_last_component(req.monitor_action),
                # ...
                name=get_last_component(var_name),
```

**`ivy_lsp/core/parsing/ast_to_symbols.py:348`**, **`627`**, **`636`**, **`654`**
```python
# Before:
        leaf_name = name.rsplit(".", 1)[-1] if "." in name else name
        # ...
        leaf_name = name.rsplit(".", 1)[-1] if "." in name else name
        # ...
        synthetic=re.fullmatch(r"def\d+", name.rsplit(".", 1)[-1]) is not None,
        # ...
        leaf_name = name.rsplit(".", 1)[-1] if "." in name else name
# After:
        leaf_name = get_last_component(name)
        # ...
        leaf_name = get_last_component(name)
        # ...
        synthetic=re.fullmatch(r"def\d+", get_last_component(name)) is not None,
        # ...
        leaf_name = get_last_component(name)
```

**`ivy_lsp/core/semantic/model_builder.py:226`**
```python
# Before:
            last = name.rsplit(".", 1)[-1] if "." in name else name
# After:
            last = get_last_component(name)
```

- [ ] **Step 4: Update MCP server**

**`ivy_lsp/mcp/server.py:673`** and **`686`**
```python
# Before:
                    name=req.monitor_action.rsplit(".", 1)[-1],
                    # ...
                    name=var_name.rsplit(".", 1)[-1],
# After:
                    name=get_last_component(req.monitor_action),
                    # ...
                    name=get_last_component(var_name),
```

- [ ] **Step 5: Run broad test suite to verify no regressions**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=120 2>&1 | tail -10`

Expected: All tests pass (2784+).

- [ ] **Step 6: Commit Phase 3A**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/infra/utils/name_utils.py tests/test_name_utils.py
git add ivy_lsp/lsp/navigation/definition.py ivy_lsp/lsp/navigation/hover.py ivy_lsp/lsp/navigation/implementation.py ivy_lsp/lsp/navigation/call_hierarchy.py ivy_lsp/lsp/navigation/references.py
git add ivy_lsp/lsp/document_highlight.py ivy_lsp/lsp/workspace_symbols.py ivy_lsp/lsp/rename.py ivy_lsp/lsp/ui/selection_range.py
git add ivy_lsp/core/adapters/ast_enrichment_adapter.py ivy_lsp/core/compilation/graph_enrichment.py ivy_lsp/core/analysis/requirement_graph.py ivy_lsp/core/parsing/ast_to_symbols.py ivy_lsp/core/semantic/model_builder.py
git add ivy_lsp/mcp/server.py
git commit -m "refactor: extract get_last_component utility (29 call sites)"
```

---

### Task 8: Create node_filters helpers and update call sites

**Files:**
- Create: `ivy_lsp/core/semantic/node_filters.py`
- Create: `tests/test_node_filters.py`
- Modify: `ivy_lsp/lsp/completion.py:553`
- Modify: `ivy_lsp/lsp/navigation/hover.py:158-161, 215-216, 221`
- Modify: `ivy_lsp/lsp/navigation/call_hierarchy.py:99`

- [ ] **Step 1: Write test**

```python
"""Tests for ivy_lsp.core.semantic.node_filters."""

from ivy_lsp.core.semantic.node_filters import first_node_of_type, nodes_of_type


class _A:
    pass


class _B:
    pass


class TestNodesOfType:
    def test_filters_by_type(self):
        items = [_A(), _B(), _A()]
        result = nodes_of_type(items, _A)
        assert len(result) == 2
        assert all(isinstance(r, _A) for r in result)

    def test_empty_input(self):
        assert nodes_of_type([], _A) == []

    def test_no_matches(self):
        assert nodes_of_type([_B(), _B()], _A) == []


class TestFirstNodeOfType:
    def test_returns_first(self):
        a1, a2 = _A(), _A()
        result = first_node_of_type([_B(), a1, a2], _A)
        assert result is a1

    def test_returns_none_when_no_match(self):
        assert first_node_of_type([_B()], _A) is None

    def test_empty_input(self):
        assert first_node_of_type([], _A) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_node_filters.py -x -q 2>&1 | tail -5`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create node_filters.py**

```python
"""Type-based node filtering helpers for SemanticModel queries."""

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

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_node_filters.py -x -q 2>&1 | tail -5`

Expected: 6 passed

- [ ] **Step 5: Update call sites**

**`ivy_lsp/lsp/completion.py:553`** — add import and replace:
```python
# Add to imports at top of function or module:
from ivy_lsp.core.semantic.node_filters import first_node_of_type

# Before (line 553):
            sn = next((n for n in candidates if isinstance(n, SymbolNode)), None)
# After:
            sn = first_node_of_type(candidates, SymbolNode)
```

**`ivy_lsp/lsp/navigation/hover.py`** — add import and replace 4 sites:
```python
# Add to module-level imports:
from ivy_lsp.core.semantic.node_filters import first_node_of_type, nodes_of_type

# Line 158-161 (inside _enrich_with_semantic_model):
# Before:
    sn = next(
        (n for n in matches if isinstance(n, SymbolNode)),
        None,
    )
# After:
    sn = first_node_of_type(matches, SymbolNode)

# Lines 215-216 (inside _hover_from_semantic_model):
# Before:
    matches = [n for n in all_matches if isinstance(n, SymbolNode)]
    type_matches = [n for n in all_matches if isinstance(n, TypeNode)]
# After:
    matches = nodes_of_type(all_matches, SymbolNode)
    type_matches = nodes_of_type(all_matches, TypeNode)

# Line 221:
# Before:
        by_last = [n for n in all_by_last if isinstance(n, SymbolNode)]
# After:
        by_last = nodes_of_type(all_by_last, SymbolNode)
```

Note: Lines 165-172 and 225-229 have additional predicates (`n.qualified_name == symbol_name`, `n.qualified_name.endswith(word)`) — leave these as-is since the helper doesn't support predicates.

**`ivy_lsp/lsp/navigation/call_hierarchy.py:99`** — add import and replace:
```python
# Add to module-level imports:
from ivy_lsp.core.semantic.node_filters import nodes_of_type

# Line 99 (inside _find_symbol_node_id):
# Before:
    candidates = [n for n in model.get_nodes_by_name(last) if isinstance(n, SymbolNode)]
# After:
    candidates = nodes_of_type(model.get_nodes_by_name(last), SymbolNode)
```

- [ ] **Step 6: Run affected tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_hover.py tests/test_call_hierarchy.py tests/test_completion.py -x -q 2>&1 | tail -5`

Expected: All pass.

- [ ] **Step 7: Commit Phase 3B**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/semantic/node_filters.py tests/test_node_filters.py
git add ivy_lsp/lsp/completion.py ivy_lsp/lsp/navigation/hover.py ivy_lsp/lsp/navigation/call_hierarchy.py
git commit -m "refactor: extract node_filters helpers (6 call sites)"
```

---

### Task 9: Add task helpers to publisher.py and refactor

**Files:**
- Modify: `ivy_lsp/lsp/diagnostics/publisher.py`

- [ ] **Step 1: Add helper functions at module level (after line 30)**

Insert after the `DEBOUNCE_DELAY` line:

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

- [ ] **Step 2: Replace debounce task management (lines 261-305)**

Replace lines 261-305 (cancel old + create_task + callback + store):

```python
# Before (lines 261-305):
        old_task = _debounce_tasks.pop(uri, None)
        if old_task and not old_task.done():
            old_task.cancel()

        async def _debounced():
            ...  # (unchanged inner function)

        loop = asyncio.get_running_loop()
        task = loop.create_task(_debounced())
        task.add_done_callback(
            lambda t, u=uri: (
                _debounce_tasks.pop(u, None) if _debounce_tasks.get(u) is t else None
            )
        )
        _debounce_tasks[uri] = task

# After:
        async def _debounced():
            ...  # (unchanged inner function)

        _register_task(_debounce_tasks, uri, _debounced())
```

- [ ] **Step 3: Replace deep task management (lines 386-397)**

Replace lines 386-397:

```python
# Before:
        old_deep = _deep_tasks.pop(uri, None)
        if old_deep and not old_deep.done():
            old_deep.cancel()
        loop = asyncio.get_running_loop()
        deep_task = loop.create_task(_deep())
        deep_task.add_done_callback(
            lambda t, u=uri: (
                _deep_tasks.pop(u, None) if _deep_tasks.get(u) is t else None
            )
        )
        _deep_tasks[uri] = deep_task

# After:
        _register_task(_deep_tasks, uri, _deep())
```

- [ ] **Step 4: Replace did_close cancellations (lines 403-409)**

Replace lines 403-409:

```python
# Before:
        old_task = _debounce_tasks.pop(uri, None)
        if old_task and not old_task.done():
            old_task.cancel()
        old_deep = _deep_tasks.pop(uri, None)
        if old_deep and not old_deep.done():
            old_deep.cancel()

# After:
        _cancel_task(_debounce_tasks, uri)
        _cancel_task(_deep_tasks, uri)
```

- [ ] **Step 5: Run diagnostics tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_diagnostics*.py tests/test_publisher*.py -x -q 2>&1 | tail -10`

Expected: All pass.

- [ ] **Step 6: Commit Phase 3C**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/lsp/diagnostics/publisher.py
git commit -m "refactor: extract task cancel/register helpers in publisher.py"
```

---

### Task 10: Final verification and formatting

- [ ] **Step 1: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=120 2>&1 | tail -10`

Expected: All 2784+ tests pass.

- [ ] **Step 2: Run formatters**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m black ivy_lsp/ tests/test_name_utils.py tests/test_node_filters.py && python -m isort ivy_lsp/ tests/test_name_utils.py tests/test_node_filters.py`

Expected: Files reformatted (or already formatted).

- [ ] **Step 3: Stage and amend if formatting changed files**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git status
# If formatting changed files, stage and create a new commit:
git add -u
git commit -m "style: apply black/isort formatting"
```

- [ ] **Step 4: Verify clean state**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && git log --oneline -6`

Expected: 3-4 new commits for Phase 2A, 3A, 3B, 3C (plus optional formatting commit).
