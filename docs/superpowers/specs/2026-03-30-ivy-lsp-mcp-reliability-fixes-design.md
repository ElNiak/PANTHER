# Ivy LSP + MCP Reliability Fixes

**Date**: 2026-03-30
**Scope**: ivy-lsp (submodule) + panther-ivy-plugin (submodule)
**Total changes**: ~40 lines across 8 files

## Context

A health check and log analysis of the Ivy LSP + MCP stack revealed 6 reliability issues during session startup:

1. Serena venv crash from `uv sync` race condition (3 crashes per session start)
2. Z3 not detected correctly, producing 636+ silent errors per startup
3. T3 bulk read failures from relative/absolute path mismatch in offline index
4. Stale PID files from `exec` destroying bash `trap` handlers
5. Observability directory created in wrong location (`os.getcwd()` fallback)
6. Session ID race between MCP server start and SessionStart hook

All fixes follow existing patterns in each codebase. No architectural changes.

## Fix 1: Serena venv race condition

**Root cause**: `start-serena.sh` finds the pre-built `.venv/bin/serena-mcp-server` but the editable install's `.pth` file is temporarily missing during a concurrent `uv sync`. Python can't find `from serena.cli import start_mcp_server`, producing `ModuleNotFoundError`. Claude Code auto-restarts the crashed process with no backoff, amplifying it into a restart storm (3 crashes before self-healing).

**Evidence**: `uv_cache.json` timestamp for `serena_agent` (epoch 1774607609) exactly matches the first crash log at 09:53:02. The `.pth` file mechanism (`_serena_agent.pth` adding `.../panther-serena/src` to `sys.path`) is non-atomic during `uv sync`.

**Fix**: Add explicit `PYTHONPATH` before `exec` in `start-serena.sh`, making the import independent of the `.pth` file:

```bash
# Before exec, ensure serena and ivy-lsp are importable regardless of .pth state
export PYTHONPATH="$SERENA_SRC/src:${IVY_LSP_SRC:+$IVY_LSP_SRC:}${PYTHONPATH:-}"
```

**File**: `panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-serena.sh` (before line 142)

## Fix 2: Z3 mandatory — fix detection and make it a hard dependency

**Root cause**: `_create_parser()` in `server_setup.py` tests `import ivy.ivy_utils` which does NOT depend on Z3. The check passes, `_full_mode=True` is set, then `IvyParserWrapper.parse()` calls `import ivy.ivy_parser` which transitively imports `ivy_solver` → `z3_shim` → `ModuleNotFoundError`. This produces 636 `analysis_tier2 failed` warnings + 60 `Z3 Python bindings not found` errors per startup.

**Design decision**: Z3 is mandatory. No graceful fallback. If Z3 is missing, fail immediately with a clear error.

**Fixes (3 changes)**:

### 2a. Move `z3-solver` to core dependencies

In `ivy-lsp/pyproject.toml`, move `z3-solver` from `[project.optional-dependencies] mcp` to `[project] dependencies`:

```toml
dependencies = [
    "pygls>=2.0",
    "lsprotocol",
    "panther_ms_ivy",
    "z3-solver",
]
```

### 2b. Fix Z3 detection in `_create_parser()`

In `server_setup.py`, change the import test to use the actual import chain that requires Z3:

```python
# Current (broken — ivy_utils does NOT depend on Z3):
import ivy.ivy_utils  # noqa: F401

# Fixed — tests the actual Z3-dependent import chain:
import ivy.ivy_parser  # noqa: F401
```

If this import fails, log a clear error (`"Z3 is required but ivy.ivy_parser could not be imported"`) and raise, preventing the server from starting in a broken state. Do not fall back to `FallbackOnlyParser`.

### 2c. Guard imports in `IvyParserWrapper.parse()`

In `parser_session.py:165-166`, wrap the imports in try/except with an actionable error:

```python
def parse(self, source, filename="<string>", timeout=None):
    try:
        import ivy.ivy_parser as ip
        import ivy.ivy_utils as iu
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            f"Z3 is required but not available: {exc}. "
            "Install via 'pip install z3-solver'."
        ) from exc
```

**Files**: `ivy-lsp/pyproject.toml`, `ivy-lsp/ivy_lsp/lsp/server_setup.py`, `ivy-lsp/ivy_lsp/core/parsing/parser_session.py`

**ARM/Apple Silicon risk**: Z3 has known math errors on ARM (documented in CLAUDE.md). Accepted — no escape hatch.

## Fix 3: T3 path resolution — follow T1/T2 pattern

**Root cause**: The offline index builder (`index_builder.py:169`) stores test scope paths as relative. When the pickle is loaded at `server_setup.py:559`, the requirement graph's `_test_scopes` are injected with relative paths. The bulk T3 orchestrator calls `open(test_file)` which fails because the LSP's working directory isn't the protocol directory.

**Key insight**: T1 (symbols), T2 (includes), and T3 exports all remap `rel_path → os.path.join(protocol_dir, rel_path)` on pickle load (lines 507, 536, 544). The requirement graph at line 559-560 is the **only** component loaded without path remapping.

**Fix**: Add a `remap_paths(base_dir)` method to the requirement graph model and call it at load time, following the same pattern as T1/T2/exports:

```python
# server_setup.py line 559-560
if proto_idx.requirement_graph is not None:
    proto_idx.requirement_graph.remap_paths(protocol_dir)
    self._indexer._requirement_graph = proto_idx.requirement_graph
```

The `remap_paths` method iterates `_test_scopes` and converts relative keys to absolute using `os.path.join(base_dir, key)`.

**Files**: `ivy-lsp/ivy_lsp/lsp/server_setup.py:559`, `ivy-lsp/ivy_lsp/core/analysis/test_scope.py` (add `remap_paths` method to `ScopedRequirementModel`)

## Fix 4: Stale PID file cleanup

**Root cause**: `start-ivy-server.sh` sets a bash `trap` at line 142 for PID cleanup, then `exec` at line 150/159 replaces bash with `uvx`/python. The `exec` destroys the bash process and its trap handler, so PID files are never cleaned up on exit.

**Fix**: Pass PID file path via env var, register `atexit` cleanup in Python:

### 4a. Export PID file path in `start-ivy-server.sh`

```bash
export IVY_PID_FILE="$PID_DIR/${_PID_PREFIX}-$$.pid"
```

### 4b. Register atexit handler in `ivy_lsp/__main__.py`

```python
import atexit, os

pid_file = os.environ.get("IVY_PID_FILE")
if pid_file:
    atexit.register(lambda: os.unlink(pid_file) if os.path.exists(pid_file) else None)
```

The `atexit` handler is registered in the Python process that actually runs (post-`exec`). The existing SIGTERM handler in `__main__.py` calls `sys.exit()` which triggers `atexit`.

**Files**: `panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-ivy-server.sh`, `ivy-lsp/ivy_lsp/__main__.py`

## Fix 5: Observability directory location

**Root cause**: `check-mcp-health.py:_get_state_path()` uses `os.getcwd()` as fallback when `IVY_WORKSPACE_ROOT` is not set. This creates an orphaned `.observability/unknown/` at the project root instead of under the actual workspace root.

**Fix**: Use `IVY_WORKSPACE_ROOT` env var (already set by `detect-ivy-workspace.sh` SessionStart hook):

```python
def _get_state_path():
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", os.getcwd())
    # ... rest uses ws_root
```

**File**: `panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/check-mcp-health.py`

## Fix 6: Session ID race condition

**Root cause**: MCP servers start before the `detect-ivy-workspace.sh` SessionStart hook writes `IVY_SESSION_ID` to the session file. The first MCP instance resolves session as "unknown".

**Fix**: In `workspace-common.sh:resolve_session_id()`, add a short wait-and-retry when the session file doesn't exist yet:

```bash
# After all other resolution attempts fail, wait briefly for SessionStart hook
local retries=0
while [ $retries -lt 3 ] && [ ! -s "$session_file" ]; do
    sleep 1
    retries=$((retries + 1))
done
[ -s "$session_file" ] && { head -n 1 "$session_file" | tr -d '\r\n'; return 0; }
echo "unknown"
```

Worst case: 3-second delay on first startup only. Subsequent restarts within the same session already have the session file populated.

**File**: `panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/workspace-common.sh`

## Files Changed Summary

### ivy-lsp submodule (fixes 2, 3, 4)
- `pyproject.toml` — add `z3-solver` to core dependencies
- `ivy_lsp/lsp/server_setup.py` — fix Z3 detection import + add `remap_paths` call
- `ivy_lsp/core/parsing/parser_session.py` — guard imports with actionable error
- `ivy_lsp/core/analysis/test_scope.py` — add `remap_paths` method to `ScopedRequirementModel`
- `ivy_lsp/__main__.py` — register PID file atexit cleanup

### panther-ivy-plugin submodule (fixes 1, 4, 5, 6)
- `scripts/start-serena.sh` — add PYTHONPATH export
- `scripts/start-ivy-server.sh` — export IVY_PID_FILE env var
- `scripts/workspace-common.sh` — add session ID wait-and-retry
- `hooks/scripts/check-mcp-health.py` — use IVY_WORKSPACE_ROOT

## Testing

- Start a new Claude Code session and verify zero `ModuleNotFoundError` crashes in Serena logs
- Verify zero `Z3 Python bindings not found` errors (Z3 now mandatory and installed)
- Verify zero `Cannot read ... for bulk T3` warnings (paths remapped to absolute)
- Kill the LSP process and verify PID file is cleaned up
- Check `.observability/sessions/` exists only under `IVY_WORKSPACE_ROOT`
- Verify session ID resolves correctly on first MCP startup (not "unknown")
