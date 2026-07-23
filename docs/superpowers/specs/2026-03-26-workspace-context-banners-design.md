# Workspace/Scope Context Banners for Ivy MCP Tools

**Date**: 2026-03-26
**Status**: Approved
**Scope**: ivy-lsp MCP server (`panther_ivy/submodules/ivy-lsp/`)

## Problem

19 MCP tools return results without showing which workspace is active, which layers are in scope, or which endpoint mirror (client/server) the results apply to. This creates three concrete issues:

1. **Ambiguous outputs**: Coverage stats, verification results, and diagnostics don't indicate whether they apply to the whole model or a specific endpoint mirror's include closure.
2. **False-positive collisions**: `ivy_include_graph` and `ivy_capabilities` report 189 collisions from ALL 11 layers, even when the active workspace ("quic") only has 2 layers. The collisions are between `protocol-testing/quic/` and `protocol-testing/apt/apt_protocols/quic/` — duplicate basenames that the resolver correctly ignores but diagnostics over-report.
3. **Role confusion**: When `tester_role: "client"` is shown, it's unclear whether the client is being tested or Ivy is acting as the client (it's the latter — Ivy=client tests the server IUT).

### Root Cause

The workspace system has a two-phase architecture with a filtering gap:

- **Phase 1 (startup)**: `create_staging_directory()` stages ALL files from ALL 11 layers (636 files). `BasenameCache` is built from this full set. Collision map records all 189 cross-layer collisions.
- **Phase 2 (per-query)**: `set_active_workspace("quic")` sets `_active_layers = {"quic", "quic_tests"}`. The `resolve()` method correctly filters by active layers. But `find_all_ivy_files()`, `BasenameCache`, collision map, and all tool formatters do NOT filter.

Additionally, tool handlers put `scope` and `scope_role` fields into result dicts, but no formatter renders them.

## Design

### Approach: Centralized injection in `safe_tool` + banner formatter

Single injection point in the `safe_tool` decorator. Context metadata is built once per tool call and injected into the result dict before formatting. A centralized banner function renders the context at the top of every tool output.

### Phase 1: Workspace Banner + File Filtering

#### 1.1 `build_context_metadata()` helper in `context.py`

New method on `ToolContext`:

```python
def build_context_metadata(self) -> dict:
    ctx = {}
    ws = self.active_workspace
    if ws is None or not getattr(ws, 'active_group', None):
        return ctx
    ctx["workspace"] = ws.active_group
    ctx["layers"] = sorted(ws.active_layers)
    ctx["set_by"] = ws.set_by
    if self.include_resolver and hasattr(self.include_resolver, '_file_to_layer'):
        ftl = self.include_resolver._file_to_layer
        active = self.include_resolver._active_layers
        ctx["files_in_scope"] = sum(1 for l in ftl.values() if l in active) if active else len(ftl)
        ctx["files_total"] = len(ftl)
        # Filtered collision count
        cmap = getattr(self.include_resolver, '_collision_map', {})
        if cmap and active:
            in_scope = sum(
                1 for variants in cmap.values()
                if sum(1 for v in variants if ftl.get(v) in active) > 1
            )
            ctx["collisions_in_scope"] = in_scope
            ctx["collisions_total"] = len(cmap)
    return ctx
```

Returns empty dict when workspace is not set. Gracefully handles None/missing attributes.

#### 1.2 `_context` injection in `safe_tool` decorator (`tools/__init__.py`)

After the handler returns its result dict, before calling `_format_result`:

```python
result = await _cancel_safe_wait_for(fn(*args, **kwargs), timeout=timeout)
# Inject workspace context metadata
if isinstance(result, dict) and hasattr(fn, '_tool_context'):
    result["_context"] = fn._tool_context.build_context_metadata()
result = _format_result(tool_name, result)
```

The `_tool_context` reference is wired when the decorator wraps the handler — each handler already receives `ctx` as its first argument.

#### 1.3 `_format_context_banner()` in `formatters/primitives.py`

```python
def _format_context_banner(data: dict) -> str:
    ctx = data.get("_context")
    if not ctx or os.environ.get("IVY_LSP_NO_CONTEXT_BANNER"):
        return ""
    parts = []
    ws = ctx.get("workspace")
    if ws:
        layers = ", ".join(ctx.get("layers", []))
        parts.append(f"**Workspace**: {ws} ({layers})")
    in_scope = ctx.get("files_in_scope")
    total = ctx.get("files_total")
    if in_scope is not None and total is not None:
        parts.append(f"**Files**: {in_scope}/{total}")
    col_scope = ctx.get("collisions_in_scope")
    col_total = ctx.get("collisions_total")
    if col_total and col_total > 0:
        parts.append(f"**Collisions**: {col_scope or 0}/{col_total}")
    if not parts:
        return ""
    return "> " + " | ".join(parts) + "\n"
```

~50-70 tokens per banner. Always-on by default. Opt-out via `IVY_LSP_NO_CONTEXT_BANNER=1`.

#### 1.4 Banner rendering in `format_tool_result()` (`formatters/__init__.py`)

Prepend banner before tool-specific markdown:

```python
def format_tool_result(tool_name: str, data: dict) -> str:
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

Note: `_format_generic` already strips `_` prefixed keys (line 75), so `_context` won't appear in fallback JSON output.

#### 1.5 `find_all_ivy_files(filter_active=True)` in `include_resolver.py`

Add optional parameter to filter by active layers:

```python
def find_all_ivy_files(self, root=None, filter_active=False):
    if self._file_to_layer and root is None:
        files = self._file_to_layer.keys()
        if filter_active and self._active_layers:
            # Snapshot active_layers to avoid TOCTOU
            active = set(self._active_layers)
            files = [f for f in files if self._file_to_layer[f] in active]
        return sorted(files)
    if self._staging_dir and root is None:
        return sorted(self._staged_files.values())
    return self._find_source_files(root)
```

#### 1.6 `BasenameCache.invalidate()` in `basename_cache.py`

```python
def invalidate(self) -> None:
    """Clear the cache to force rebuild on next access."""
    with self._lock:
        self._cache = None
```

#### 1.7 Cache invalidation on workspace switch (`workspace.py`)

In `_handle_set()`, after calling `set_active_workspace()`:

```python
ctx.include_resolver.set_active_workspace(ws.active_layers)
# Invalidate basename cache so it rebuilds with new layer scope
if hasattr(ctx, '_basename_cache_invalidate'):
    ctx._basename_cache_invalidate()
```

Wire the invalidation callback in `context.py`:

```python
_basename_cache_obj = BasenameCache(_find_files, ws_root)
ctx._basename_cache_invalidate = _basename_cache_obj.invalidate
```

#### 1.8 Update `_find_files` callback in `context.py`

Pass `filter_active=True` when workspace is active:

```python
def _find_files(search_root: str) -> list[str]:
    if resolver is not None:
        has_active = bool(getattr(resolver, '_active_layers', None))
        return resolver.find_all_ivy_files(filter_active=has_active)
    return _find_ivy_raw(search_root, _exclude)
```

### Phase 2: Mirror/Endpoint Context

#### 2.1 Extend `build_context_metadata()` with scope parameter

```python
def build_context_metadata(self, scope=None) -> dict:
    ctx = { ... }  # Phase 1 workspace context
    # Mirror context from TestScope
    if scope and hasattr(scope, 'tester_role'):
        role = scope.tester_role
        opposite = {"client": "server", "server": "client", "mim": "network"}.get(role, "unknown")
        ctx["mirror"] = os.path.basename(scope.test_file).replace(".ivy", "")
        ctx["ivy_role"] = role
        ctx["tests_role"] = opposite
        ctx["closure_size"] = len(scope.include_closure)
        ctx["exported_actions"] = len(scope.exported_actions)
        ctx["imported_actions"] = len(scope.imported_actions)
    return ctx
```

#### 2.2 Extend banner rendering

```python
# In _format_context_banner:
mirror = ctx.get("mirror")
if mirror:
    ivy_role = ctx.get("ivy_role", "unknown")
    tests_role = ctx.get("tests_role", "unknown")
    closure = ctx.get("closure_size", "?")
    parts.append(f"**Mirror**: {mirror} (Ivy={ivy_role}, tests {tests_role}, {closure} files)")
```

#### 2.3 Pass scope through `safe_tool`

The decorator needs to extract `scope`/`test_file` from handler kwargs and resolve the TestScope before building context. This requires checking if the handler's result dict contains `scope`/`scope_role` fields (already populated by handlers that support it).

Alternative: build mirror context AFTER handler returns, reading `scope` and `scope_role` from the result dict:

```python
if isinstance(result, dict):
    _ctx_meta = fn._tool_context.build_context_metadata()
    # Enrich with mirror info if handler provided it
    if result.get("scope_role"):
        _ctx_meta["ivy_role"] = result["scope_role"]
        _ctx_meta["tests_role"] = {"client": "server", "server": "client"}.get(result["scope_role"], "?")
    if result.get("scope"):
        _ctx_meta["mirror"] = result["scope"]
    result["_context"] = _ctx_meta
```

This avoids re-resolving the scope — reuses what the handler already computed.

### Example Outputs

**Before (no context):**
```
## RFC Coverage Statistics
[....................] 0.0%
0/97 requirements covered
```

**After Phase 1 (workspace context):**
```
> **Workspace**: quic (quic, quic_tests) | **Files**: 200/636 | **Collisions**: 0/189

## RFC Coverage Statistics
[....................] 0.0%
0/97 requirements covered
```

**After Phase 2 (with mirror):**
```
> **Workspace**: quic (quic, quic_tests) | **Files**: 200/636 | **Collisions**: 0/189 | **Mirror**: quic_server_test (Ivy=client, tests server, 42 files)

## RFC Coverage Statistics
[....................] 0.0%
0/97 requirements covered
```

**Scope without workspace:**
```
> **Workspace**: (not set) | **Mirror**: quic_server_test (Ivy=client, tests server, 42 files)

## Verification: PASS
```

## Files Modified

### Phase 1 (~95 lines changed)

| File | Change | Lines |
|------|--------|-------|
| `ivy_lsp/mcp/context.py` | Add `build_context_metadata()`, wire `_basename_cache_invalidate`, update `_find_files` | ~35 |
| `ivy_lsp/mcp/tools/__init__.py` | Inject `_context` in `safe_tool` after handler returns | ~15 |
| `ivy_lsp/mcp/tools/formatters/primitives.py` | Add `_format_context_banner()` | ~20 |
| `ivy_lsp/mcp/tools/formatters/__init__.py` | Prepend banner in `format_tool_result()` | ~5 |
| `ivy_lsp/core/indexer/include_resolver.py` | Add `filter_active` param to `find_all_ivy_files()` | ~10 |
| `ivy_lsp/infra/utils/basename_cache.py` | Add `invalidate()` method | ~5 |
| `ivy_lsp/mcp/tools/workspace.py` | Call `invalidate()` on workspace change | ~5 |

### Phase 2 (~40 lines changed)

| File | Change | Lines |
|------|--------|-------|
| `ivy_lsp/mcp/context.py` | Extend `build_context_metadata()` with scope | ~15 |
| `ivy_lsp/mcp/tools/__init__.py` | Extract mirror info from result dict | ~10 |
| `ivy_lsp/mcp/tools/formatters/primitives.py` | Render mirror section in banner | ~15 |

## Non-Goals

- Changing tool handler signatures (all injection happens in decorator)
- Adding scope/test_file params to tools that don't have them
- Rebuilding staging directory on workspace change (too expensive; query-time filtering is sufficient)
- Modifying the LSP server (only MCP tools are affected)

## Testing

- Verify banner appears on all 19 tools when workspace is active
- Verify banner is absent when workspace is not set and no scope is provided
- Verify `find_all_ivy_files(filter_active=True)` returns only files from active layers
- Verify `BasenameCache` invalidates on workspace switch
- Verify `ivy_include_graph` shows 0 ambiguous candidates when workspace is "quic"
- Verify `IVY_LSP_NO_CONTEXT_BANNER=1` suppresses the banner
- Verify role inversion label: "Ivy=client, tests server"
