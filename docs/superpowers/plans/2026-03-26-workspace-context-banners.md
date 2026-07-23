# Workspace Context Banners Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add workspace/scope/mirror context banners to all 19 Ivy MCP tool outputs and fix false-positive collision reporting by filtering `find_all_ivy_files()` by active layers.

**Architecture:** Single injection point in the `safe_tool` decorator captures `ctx` (ToolContext) and injects a `_context` metadata dict into every tool result before formatting. A centralized `_format_context_banner()` renders the banner. `BasenameCache` gains invalidation support and `find_all_ivy_files()` gains active-layer filtering.

**Tech Stack:** Python 3.10+, ivy-lsp MCP server, asyncio

**Base path:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
(All file paths below are relative to this base unless stated otherwise.)

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `ivy_lsp/mcp/tools/formatters/primitives.py` | Shared markdown helpers | Add `_format_context_banner()` |
| `ivy_lsp/mcp/tools/formatters/__init__.py` | Format dispatch | Prepend banner in `format_tool_result()` |
| `ivy_lsp/mcp/context.py` | ToolContext dataclass | Add `build_context_metadata()`, wire cache invalidation |
| `ivy_lsp/mcp/tools/__init__.py` | `safe_tool` decorator | Convert to factory `safe_tool(ctx)`, inject `_context` |
| `ivy_lsp/infra/utils/basename_cache.py` | Basename->paths cache | Add `invalidate()` method |
| `ivy_lsp/core/indexer/include_resolver.py` | Include resolution | Add `filter_active` param to `find_all_ivy_files()` |
| `ivy_lsp/mcp/tools/workspace.py` | Workspace management | Call `invalidate()` on workspace switch |
| `ivy_lsp/mcp/tools/verification.py` | Verification tools | Update `@safe_tool` → `@safe_tool(ctx)` |
| `ivy_lsp/mcp/tools/traceability.py` | Traceability tools | Update `@safe_tool` → `@safe_tool(ctx)` |
| `ivy_lsp/mcp/tools/analysis.py` | Analysis tools | Update `@safe_tool` → `@safe_tool(ctx)` |
| `ivy_lsp/mcp/tools/visualization.py` | Visualization tools | Update `@safe_tool` → `@safe_tool(ctx)` |
| `ivy_lsp/mcp/tools/patterns.py` | Pattern tools | Update `@safe_tool` → `@safe_tool(ctx)` |
| `ivy_lsp/mcp/tools/quality.py` | Quality tools | Update `@safe_tool` → `@safe_tool(ctx)` |
| `ivy_lsp/mcp/tools/workspace.py` | Workspace tools | Update `@safe_tool` → `@safe_tool(ctx)` |

---

## Task 1: Add `_format_context_banner()` to primitives

**Files:**
- Modify: `ivy_lsp/mcp/tools/formatters/primitives.py:1-70`
- Test: Manual — verified in Task 6

- [ ] **Step 1: Add the banner function at the end of primitives.py**

```python
# Append to ivy_lsp/mcp/tools/formatters/primitives.py

import os


def _format_context_banner(data: dict) -> str:
    """Render a one-line workspace/scope context banner as a blockquote.

    Reads ``_context`` from the result dict (injected by safe_tool).
    Returns empty string when no context is available or when
    ``IVY_LSP_NO_CONTEXT_BANNER=1`` is set.
    """
    ctx = data.get("_context")
    if not ctx or os.environ.get("IVY_LSP_NO_CONTEXT_BANNER"):
        return ""
    parts: list[str] = []
    ws = ctx.get("workspace")
    if ws:
        layers = ", ".join(ctx.get("layers", []))
        parts.append(f"**Workspace**: {ws} ({layers})")
    elif ctx.get("mirror"):
        # Scope set without workspace
        parts.append("**Workspace**: (not set)")
    in_scope = ctx.get("files_in_scope")
    total = ctx.get("files_total")
    if in_scope is not None and total is not None:
        parts.append(f"**Files**: {in_scope}/{total}")
    col_scope = ctx.get("collisions_in_scope")
    col_total = ctx.get("collisions_total")
    if col_total and col_total > 0:
        parts.append(f"**Collisions**: {col_scope or 0}/{col_total}")
    # Phase 2: mirror context
    mirror = ctx.get("mirror")
    if mirror:
        ivy_role = ctx.get("ivy_role", "unknown")
        tests_role = ctx.get("tests_role", "unknown")
        closure = ctx.get("closure_size", "?")
        parts.append(
            f"**Mirror**: {mirror} (Ivy={ivy_role}, tests {tests_role}, {closure} files)"
        )
    if not parts:
        return ""
    return "> " + " | ".join(parts) + "\n"
```

- [ ] **Step 2: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/formatters/primitives.py
git commit -m "feat: add _format_context_banner() to formatter primitives"
```

---

## Task 2: Prepend banner in `format_tool_result()`

**Files:**
- Modify: `ivy_lsp/mcp/tools/formatters/__init__.py:1-119`

- [ ] **Step 1: Add import and modify `format_tool_result`**

In `ivy_lsp/mcp/tools/formatters/__init__.py`, add the import at line 16 (with the other primitives imports):

```python
from ivy_lsp.mcp.tools.formatters.primitives import _code_block, _format_context_banner
```

Then replace `format_tool_result` (lines 104-116) with:

```python
def format_tool_result(tool_name: str, data: dict) -> str:
    """Dispatch to a per-tool formatter, falling back to generic."""
    if not isinstance(data, dict):
        return _code_block(str(data))
    formatter = _FORMATTERS.get(tool_name, _format_generic)
    banner = _format_context_banner(data)
    try:
        body = formatter(data)
    except Exception:
        try:
            body = _format_generic(data)
        except Exception:
            body = _code_block(str(data))
    return (banner + "\n" + body) if banner else body
```

- [ ] **Step 2: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/formatters/__init__.py
git commit -m "feat: prepend context banner in format_tool_result()"
```

---

## Task 3: Add `build_context_metadata()` to ToolContext

**Files:**
- Modify: `ivy_lsp/mcp/context.py:60-200`

- [ ] **Step 1: Add `build_context_metadata` method to ToolContext dataclass**

Add this method after line 110 (after the `stdlib_modules` field) in the `ToolContext` class body:

```python
    def build_context_metadata(self) -> dict:
        """Build workspace/scope context metadata for tool result injection.

        Returns empty dict when workspace is not set.
        """
        import os

        ctx: dict = {}
        ws = self.active_workspace
        if ws is None or not getattr(ws, "active_group", None):
            return ctx
        ctx["workspace"] = ws.active_group
        ctx["layers"] = sorted(ws.active_layers)
        ctx["set_by"] = getattr(ws, "set_by", "unknown")
        resolver = self.include_resolver
        if resolver is not None and hasattr(resolver, "_file_to_layer"):
            ftl = resolver._file_to_layer
            active = getattr(resolver, "_active_layers", set())
            if active:
                ctx["files_in_scope"] = sum(
                    1 for layer in ftl.values() if layer in active
                )
            else:
                ctx["files_in_scope"] = len(ftl)
            ctx["files_total"] = len(ftl)
            # Filtered collision count
            cmap = getattr(resolver, "_collision_map", {})
            if cmap and active:
                in_scope_collisions = sum(
                    1
                    for variants in cmap.values()
                    if sum(1 for v in variants if ftl.get(v) in active) > 1
                )
                ctx["collisions_in_scope"] = in_scope_collisions
                ctx["collisions_total"] = len(cmap)
        return ctx
```

- [ ] **Step 2: Wire `_basename_cache_invalidate` callback in `from_lsp_server`**

In the `from_lsp_server` classmethod (around line 146 after `_basename_cache_obj` creation), add:

```python
        _basename_cache_obj = BasenameCache(_find_files, ws_root)
        _get_basename_cache = _basename_cache_obj.get

        # Wire cache invalidation callback for workspace switching
        ctx._basename_cache_invalidate = _basename_cache_obj.invalidate
```

And add the field to the ToolContext dataclass (after line 78, near `include_resolver`):

```python
    _basename_cache_invalidate: Callable[[], None] = field(default=lambda: None)
```

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/context.py
git commit -m "feat: add build_context_metadata() and cache invalidation wiring"
```

---

## Task 4: Convert `safe_tool` to factory that captures `ctx`

**Files:**
- Modify: `ivy_lsp/mcp/tools/__init__.py:311-581`

This is the critical task. `safe_tool` currently has no access to `ctx`. We convert it to a factory `safe_tool(ctx=None)` that stores `ctx` and injects `_context` into results.

- [ ] **Step 1: Modify `safe_tool` to accept optional `ctx` parameter**

Replace the `safe_tool` function definition (line 311) with a factory:

```python
def safe_tool(fn=None, *, ctx=None):
    """Decorator that adds timeout, concurrency, metrics, and crash safety.

    Can be used as ``@safe_tool`` (no ctx) or ``@safe_tool(ctx=ctx)``
    to enable workspace context injection into results.
    """

    def _decorator(fn):
        @functools.wraps(fn)
        async def _wrapper(*args, **kwargs):
            tool_name = fn.__name__
            timeout = _get_effective_timeout(tool_name)

            # --- Sidecar delegation (unchanged) ---
```

Keep the entire body of the existing `_wrapper` unchanged, EXCEPT insert context injection after line 441 (after `sem.release()`) and before line 443 (`result = _format_result(...)`):

```python
            finally:
                sem.release()

            # Inject workspace context metadata into dict results
            if ctx is not None and isinstance(result, dict):
                _ctx_meta = ctx.build_context_metadata()
                # Enrich with mirror info if handler provided scope
                scope_role = result.get("scope_role")
                if scope_role:
                    _ctx_meta["ivy_role"] = scope_role
                    _ctx_meta["tests_role"] = {
                        "client": "server",
                        "server": "client",
                        "mim": "network",
                    }.get(scope_role, "unknown")
                scope_name = result.get("scope")
                if scope_name:
                    _ctx_meta["mirror"] = scope_name
                if _ctx_meta:
                    result["_context"] = _ctx_meta

            result = _format_result(tool_name, result)
```

At the end of `safe_tool`, after the `_injected_names` dict and `patched_globals` (keep those unchanged), return the wrapper. Then handle the bare `@safe_tool` vs `@safe_tool(ctx=ctx)` pattern:

```python
        # ... existing _injected_names, patched_globals, wrapper construction ...
        return wrapper

    if fn is not None:
        # Called as @safe_tool (no arguments) — backward compatible
        return _decorator(fn)
    # Called as @safe_tool(ctx=ctx)
    return _decorator
```

- [ ] **Step 2: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/__init__.py
git commit -m "feat: convert safe_tool to factory with ctx injection"
```

---

## Task 5: Update all tool registrations to pass `ctx`

**Files:**
- Modify: `ivy_lsp/mcp/tools/verification.py` (5 tools)
- Modify: `ivy_lsp/mcp/tools/traceability.py`
- Modify: `ivy_lsp/mcp/tools/analysis.py`
- Modify: `ivy_lsp/mcp/tools/visualization.py`
- Modify: `ivy_lsp/mcp/tools/patterns.py`
- Modify: `ivy_lsp/mcp/tools/quality.py`
- Modify: `ivy_lsp/mcp/tools/workspace.py`

All tools currently use `@safe_tool` (bare). Change each to `@safe_tool(ctx=ctx)`.

- [ ] **Step 1: Update verification.py**

In `ivy_lsp/mcp/tools/verification.py`, replace every occurrence of `@safe_tool` with `@safe_tool(ctx=ctx)`. There are 5 occurrences at lines 135, 324, 490, 569, 968:

```python
    @mcp.tool()
    @safe_tool(ctx=ctx)
    async def ivy_verify(...):
```

Repeat for `ivy_compile`, `ivy_model_info`, `ivy_diagnostics`, `ivy_verification_dashboard`.

- [ ] **Step 2: Update traceability.py**

Replace `@safe_tool` with `@safe_tool(ctx=ctx)` for all tools. Check how many:

```bash
grep -n "@safe_tool" ivy_lsp/mcp/tools/traceability.py
```

Update each occurrence.

- [ ] **Step 3: Update analysis.py**

Same pattern — replace `@safe_tool` with `@safe_tool(ctx=ctx)`.

- [ ] **Step 4: Update visualization.py**

Same pattern.

- [ ] **Step 5: Update patterns.py**

Same pattern.

- [ ] **Step 6: Update quality.py**

Same pattern.

- [ ] **Step 7: Update workspace.py**

Same pattern. Additionally, add cache invalidation after `set_active_workspace` call (line ~114):

```python
        if (
            ctx.include_resolver is not None
            and hasattr(ctx.include_resolver, "set_active_workspace")
        ):
            ctx.include_resolver.set_active_workspace(ws.active_layers)

        # Invalidate basename cache so it rebuilds with new layer scope
        if hasattr(ctx, "_basename_cache_invalidate"):
            ctx._basename_cache_invalidate()
```

- [ ] **Step 8: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/verification.py ivy_lsp/mcp/tools/traceability.py \
        ivy_lsp/mcp/tools/analysis.py ivy_lsp/mcp/tools/visualization.py \
        ivy_lsp/mcp/tools/patterns.py ivy_lsp/mcp/tools/quality.py \
        ivy_lsp/mcp/tools/workspace.py
git commit -m "feat: wire ctx into all safe_tool decorators + cache invalidation"
```

---

## Task 6: Add `BasenameCache.invalidate()` and `filter_active` to `find_all_ivy_files`

**Files:**
- Modify: `ivy_lsp/infra/utils/basename_cache.py:1-39`
- Modify: `ivy_lsp/core/indexer/include_resolver.py:574-594`
- Modify: `ivy_lsp/mcp/context.py` (`_find_files` callback)

- [ ] **Step 1: Add `invalidate()` to BasenameCache**

Append after line 38 in `basename_cache.py`:

```python
    def invalidate(self) -> None:
        """Clear the cache so it rebuilds on the next ``get()`` call.

        Called when the active workspace changes, so the basename cache
        reflects only files in active layers.
        """
        with self._lock:
            self._cache = None
```

- [ ] **Step 2: Add `filter_active` parameter to `find_all_ivy_files`**

In `include_resolver.py`, replace `find_all_ivy_files` (lines 574-594) with:

```python
    def find_all_ivy_files(
        self, root: Optional[str] = None, filter_active: bool = False
    ) -> List[str]:
        """Return all .ivy file paths in the workspace, sorted.

        When a staging directory is active and *root* is ``None``, returns
        the original (dereferenced) source paths from the staging map
        instead of re-walking the filesystem.

        Args:
            root: Directory to search. Defaults to workspace_root.
            filter_active: When True, return only files belonging to
                currently active layers. Snapshot ``_active_layers``
                at call time to avoid TOCTOU races.

        Returns:
            Sorted list of absolute paths to .ivy files.
        """
        if self._file_to_layer and root is None:
            if filter_active and self._active_layers:
                active = set(self._active_layers)  # snapshot
                return sorted(
                    path
                    for path, layer in self._file_to_layer.items()
                    if layer in active
                )
            return sorted(self._file_to_layer.keys())
        if self._staging_dir and root is None:
            return sorted(self._staged_files.values())
        return self._find_source_files(root)
```

- [ ] **Step 3: Update `_find_files` callback in context.py**

In `context.py`, in `from_lsp_server` classmethod, replace the `_find_files` closure (around line 140-143):

```python
        def _find_files(search_root: str) -> list[str]:
            if resolver is not None:
                has_active_ws = bool(getattr(resolver, "_active_layers", None))
                return resolver.find_all_ivy_files(filter_active=has_active_ws)
            return _find_ivy_raw(search_root, _exclude)
```

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/infra/utils/basename_cache.py \
        ivy_lsp/core/indexer/include_resolver.py \
        ivy_lsp/mcp/context.py
git commit -m "feat: add BasenameCache.invalidate() and filter_active to find_all_ivy_files"
```

---

## Task 7: Integration Verification

**Files:** None (testing only)

- [ ] **Step 1: Verify banner appears on a tool call**

Start the MCP server (or use the existing Claude Code session) and call:

```
ivy_workspace(action="get")
```

Expected: Output should now include a context banner line:
```
> **Workspace**: quic (quic, quic_tests) | **Files**: ~200/636 | **Collisions**: 0/189
```

- [ ] **Step 2: Verify coverage shows banner**

Call:
```
ivy_coverage(mode="stats")
```

Expected: Banner appears above the coverage table.

- [ ] **Step 3: Verify include_graph no longer shows false ambiguity**

Call:
```
ivy_include_graph(relative_path="protocol-testing/quic/quic_stack/quic_connection.ivy")
```

Expected: With workspace "quic" active, includes should show 0 "ambiguous" annotations (APT candidates filtered out of basename cache).

- [ ] **Step 4: Verify opt-out works**

Set env var and call a tool:
```bash
IVY_LSP_NO_CONTEXT_BANNER=1
```

Call any tool — banner should not appear.

- [ ] **Step 5: Verify workspace switch invalidates cache**

Call:
```
ivy_workspace(action="set", target="apt")
```
then:
```
ivy_workspace(action="set", target="quic")
```

Verify that `files_in_scope` changes between calls (APT has different file count than QUIC).

- [ ] **Step 6: Verify scope/mirror info (Phase 2)**

Call:
```
ivy_verify(relative_path="protocol-testing/quic/quic_stack/quic_types.ivy", scope="quic_server_test")
```

Expected: Banner includes mirror info:
```
> **Workspace**: quic (...) | **Mirror**: quic_server_test (Ivy=client, tests server, 42 files)
```

- [ ] **Step 7: Commit any fixes from testing**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add -A
git commit -m "fix: integration test adjustments for context banners"
```

---

## Summary

| Task | What | Effort |
|------|------|--------|
| 1 | `_format_context_banner()` in primitives | 5 min |
| 2 | Prepend banner in `format_tool_result()` | 5 min |
| 3 | `build_context_metadata()` + cache wiring | 15 min |
| 4 | Convert `safe_tool` to factory with ctx | 20 min |
| 5 | Update all 19 tool decorators + cache invalidation | 15 min |
| 6 | `BasenameCache.invalidate()` + `filter_active` + callback | 15 min |
| 7 | Integration verification | 15 min |
| **Total** | | **~90 min** |
