# MCP Server Stability & Startup Performance

**Date**: 2026-03-27
**Branch**: `production` (worktree: `lsp-to-claude`)
**Scope**: ivy-lsp MCP server, panther-ivy-plugin scripts, Serena integration

## Problem Statement

Three issues degrade the ivy-tools MCP + Serena integration reliability:

1. **Cold start (233s)**: First MCP tool call blocks for ~233 seconds due to forced package reinstall, sequential parsing, and no persistent index cache.
2. **MCP server crash**: The MCP server dies mid-session from an anyio cancel scope race in sidecar client cleanup, killing all MCP tools for the rest of the session.
3. **Serena connection failure**: Serena MCP server fails on every session start (`MCP error -32000: Connection closed`) because `pip install -e` fails in the Claude Code sandbox.

## Fix 1: Cold Start (233s to ~5s)

### Root Cause

Three compounding factors on the critical path of `_build_model()` in `server.py`:

1. `.mcp.json` sets `IVY_LSP_FORCE_REINSTALL=1`, which passes `--reinstall` to `uvx` on every MCP server start. This forces a full package rebuild from the local `submodules/ivy-lsp` source (~15-30s overhead).
2. `_build_model()` always takes the Strategy 2 path (full `build_semantic_model()` rebuild) because no `.ivy-index/` directories exist. Strategy 1 (load from persisted index) is already implemented but never fires.
3. `_write_model_to_index()` (called after Strategy 2 succeeds) silently does nothing because it requires pre-existing `.ivy-index/` directories with `index_dir` values in `WorkspaceContext.protocol_indexes` — a bootstrapping deadlock.

### Fix 1A: Remove `FORCE_REINSTALL` (config, immediate)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/.mcp.json`

Remove the `IVY_LSP_FORCE_REINSTALL` line from the `ivy-tools` env block. With this removed, `uvx` reuses its cached installation from `~/.local/share/uv/tools/` unless the source specification string changes.

**Trade-off**: If a developer modifies the local `ivy-lsp` source, the stale cached version runs silently. Developers must manually set `IVY_LSP_FORCE_REINSTALL=1` in their shell or re-run `uvx --reinstall` when they change ivy-lsp code. This is documented in the plugin's CLAUDE.md already.

**Do NOT change `IVY_LSP_PARSE_WORKERS`**. The review found this controls background deep indexing (Phase 2), not the `_build_model()` path. Changing it from 1 to >1 skips T2/T3 semantic analysis tiers, causing a quality regression in `ivy_diagnostics(mode="full")`, `ivy_coverage`, `ivy_quality`, and `ivy_visualize`.

### Fix 1B: Bootstrap persistent index (code, production fix)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/server.py`

Modify `_write_model_to_index()` to create `.ivy-index/` directories and write `manifest.json` files even when no prior index exists. The actual bootstrapping deadlock is at `server.py:313` — the `if not os.path.isdir(index_dir): continue` check skips every protocol because no `.ivy-index/` directories exist on first run. (Note: the guard at line 307-308 exits when `workspace_context is None`, which is a separate condition.) The fix:

1. After Strategy 2 completes in `_build_model()`, detect the protocol directories by walking `root/protocol-testing/*/` (since `McpServerState._include_paths` contains `["protocol-testing"]`, not per-protocol subdirs).
2. For each protocol directory, call `os.makedirs(<proto_dir>/.ivy-index/, exist_ok=True)`.
3. Write `manifest.json` with the required schema: `version`, `protocol`, `created_at`, `builder_version`, and a `files` dict mapping each `.ivy` filepath to `{mtime, size, sha256, completeness, parse_tier}`. This matches the schema expected by `WorkspaceContext._check_staleness()` and `_load_protocol_index()`.
4. Write `semantic_model.pickle.gz` and `requirement_graph.pickle.gz` via `write_locked_pickle()` (which requires `index_dir` to exist first).
5. On the next startup, `WorkspaceContext.load()` finds these manifests, `_check_staleness()` validates mtimes, and `_build_model()` takes Strategy 1 (milliseconds instead of minutes).

**Important**: The persistent index only benefits the *next* startup, not the current session. After `_write_model_to_index()` creates the index, the current session's `state.workspace_context.protocol_indexes` remains empty (it was loaded before the directories existed). This is fine because the model is already built in memory.

**Version fingerprinting**: Write `ivy_lsp_version` (from `pyproject.toml` version + git commit hash if available) into `manifest.json`. On load, compare against the running version — any mismatch triggers `stale_major` (full rebuild). This prevents subtle schema drift between ivy-lsp versions from producing silently incorrect results. The existing `_load_pickle` exception handler at `context.py:486-500` only catches gross deserialization failures, not subtle field changes.

**Pickle security**: Create `.ivy-index/.gitignore` containing `*` in each index directory to prevent accidental commits of pickle files to git. Pickle files are arbitrary code execution vectors — they must never be committed to shared repositories.

**Staleness handling**: Already implemented in `context.py:327-368`. Files whose mtime changed since the manifest was written cause `stale_minor` (re-parse changed files only) or `stale_major` (full rebuild).

**Estimated change**: ~70-100 lines in `server.py` (bootstrap logic in `_write_model_to_index()`, manifest generation helper, version fingerprinting, and minor adjustments to `_build_model()`).

### Fix 1C: "Indexing in progress" UX messages (code, UX improvement)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/__init__.py` (and individual tool modules)

Tools with `needs_model: True` in `_TOOL_METADATA` (`ivy_diagnostics` full mode, `ivy_coverage`, `ivy_visualize`, `ivy_model_summary`, `ivy_quality`, `ivy_scope`) currently call `ctx.get_model()` which blocks, or `ctx.get_model_or_none()` which returns `None` during prewarm.

When the model is `None`, return a structured response:

```json
{
  "success": false,
  "message": "Model is still building (~30s remaining). Use ivy_diagnostics(mode='structural') for immediate results, or retry this tool in 30 seconds.",
  "retry_after_seconds": 30
}
```

This replaces cryptic error responses with actionable guidance. Tools that work without the model (`ivy_verify`, `ivy_compile`, `ivy_diagnostics` structural mode) are unaffected.

**Estimated change**: ~20-30 lines across `tools/__init__.py` (add a helper) and minor edits to tool handlers that call `get_model()`.

## Fix 2: MCP Server Crash (Cancel Scope)

### Root Cause

The crash is in **sidecar client cleanup**, not in tool execution. The sequence:

1. MCP server delegates tool calls to a `streamable_http` sidecar LSP via `safe_tool`.
2. On session teardown (Claude sends DELETE), `_cleanup_sidecar()` at `tools/__init__.py:198-205` calls `disconnect_sidecar(client)` via `asyncio.wait_for()`.
3. The sidecar's `streamablehttp_client` async generator was entered in a different task (the SSE listener) than the cleanup task. This violates anyio's cancel scope invariant.
4. The resulting `RuntimeError` propagates as a `BaseExceptionGroup` through three nested `anyio.TaskGroup`s, crashing `mcp.run()`.
5. The restart loop in `__main__.py:311-355` retries 3 times, but each retry inherits the stale sidecar client reference and re-triggers the same crash.

**MCP SDK status**: `mcp>=1.26.0` is the latest release. The upstream bug (issues #521, #577) is open with no fix released.

### Fix 2A: Shield sidecar cleanup (code, root cause fix)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/__init__.py`

Wrap the `_cleanup_sidecar()` coroutine body with `anyio.CancelScope(shield=True)`. This prevents the cancel scope from leaking into the server's task group when the sidecar async generator is closed from a different task context.

```python
import anyio  # Must be added to imports — not currently imported in this file

async def _cleanup_sidecar(client):
    try:
        async with anyio.CancelScope(shield=True):
            await asyncio.wait_for(disconnect_sidecar(client), timeout=3.0)
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("Sidecar cleanup failed (non-fatal): %s", exc)
```

**Required import**: `anyio` is NOT currently imported in `tools/__init__.py` (only referenced in comments). Add `import anyio` to the file's imports. `anyio>=4.13.0` is already an explicit dependency in `pyproject.toml` line 34 via the `[mcp]` extra, so no new package installation is needed.

**Estimated change**: ~10 lines in `tools/__init__.py` (including the import).

### Fix 2B: Graceful exit on transport crash (code, defense-in-depth)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/server.py`

Add a narrow `try/except` around `mcp.run(transport="stdio")` in `start_mcp()`:

```python
# BaseExceptionGroup compat (same pattern as __main__.py:17-20)
try:
    BaseExceptionGroup
except NameError:
    from exceptiongroup import BaseExceptionGroup

try:
    mcp.run(transport="stdio")
except BaseExceptionGroup as eg:
    # Filter: only exit cleanly if ALL sub-exceptions are cancel-scope related.
    # If mixed with non-cancel-scope errors, re-raise to avoid masking real crashes.
    cancel_scope_errors = [
        e for e in eg.exceptions
        if isinstance(e, (RuntimeError, BaseExceptionGroup))
        and "cancel scope" in str(e).lower()
    ]
    non_cancel_errors = [e for e in eg.exceptions if e not in cancel_scope_errors]
    if cancel_scope_errors and not non_cancel_errors:
        logger.warning("[MCP] Cancel scope crash caught at transport level, exiting cleanly: %s", eg)
        sys.exit(0)  # Clean exit → Claude Code auto-restarts
    raise
except RuntimeError as exc:
    if "cancel scope" in str(exc).lower():
        logger.warning("[MCP] Cancel scope RuntimeError, exiting cleanly: %s", exc)
        sys.exit(0)
    raise
```

This uses **sub-exception filtering** (matching the pattern in `__main__.py`) to ensure non-cancel-scope crashes always propagate. A naive string match on the entire ExceptionGroup could swallow unrelated errors.

Exit code 0 signals Claude Code to auto-restart the MCP server rather than showing a fatal error.

**Python 3.10 compatibility**: `BaseExceptionGroup` is Python 3.11+. The project already has a compat import at `__main__.py:17-20` (`try: BaseExceptionGroup except NameError: from exceptiongroup import BaseExceptionGroup`). The same import must be added to `server.py`.

**Estimated change**: ~15 lines in `server.py`.

### Fix 2C: Reset sidecar state in restart loop (code, restart reliability)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/__main__.py`

At the top of each retry iteration in the restart loop (lines 311-355), reset the stale sidecar state:

```python
from ivy_lsp.mcp.client import set_sidecar_client, set_sidecar_port
set_sidecar_client(None)
set_sidecar_port(None)
```

This ensures each restart attempt starts with a fresh sidecar discovery rather than inheriting the reference that caused the previous crash.

**Estimated change**: ~5 lines in `__main__.py`.

## Fix 3: Serena Connection Failure

### Root Cause

1. `start-serena.sh` tries `pip install -e "$SERENA_SRC"` to install Serena.
2. This fails in Claude Code's sandbox (filesystem write restrictions to site-packages).
3. The `|| true` fallback swallows the error silently.
4. `exec serena-mcp-server` fails (not on PATH), script exits non-zero.
5. Claude Code reports `MCP error -32000: Connection closed`.

A pre-built `.venv` already exists at `$SERENA_SRC/.venv/` with `serena-mcp-server` installed, but `start-serena.sh` never uses it.

### Fix 3A: Make Serena opt-in (script, immediate fix)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-serena.sh`

Add at the top of the script (after `set -euo pipefail`, before workspace detection):

```bash
# Serena is optional — disabled by default.
# Set PANTHER_IVY_ENABLE_SERENA=1 in your environment to enable.
if [ "${PANTHER_IVY_ENABLE_SERENA:-0}" = "0" ]; then
    echo "[serena] Disabled (PANTHER_IVY_ENABLE_SERENA != 1). Set to 1 to enable." >&2
    exit 0
fi
```

`exit 0` from an MCP server script signals Claude Code that the server is not running (no retry loop, no error). The stderr message gives visibility when debugging. This eliminates the startup error for all users immediately.

**Required `.mcp.json` change**: Add `"PANTHER_IVY_ENABLE_SERENA": ""` to the Serena server's `env` block in `.mcp.json`. Empty string means "inherit from parent environment." Without this, the env var never reaches the script regardless of what the user sets in their shell, because Claude Code only passes explicitly listed env vars to MCP server subprocesses.

**Estimated change**: ~5 lines in `start-serena.sh` + 1 line in `.mcp.json`.

### Fix 3B: Use pre-built `.venv` (script, correct fix)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-serena.sh`

Replace the current `pip install` + `exec serena-mcp-server` block (lines 102-125) with a resolution chain:

1. Check `$SERENA_SRC/.venv/bin/serena-mcp-server` — use directly if exists and is executable.
2. Check `command -v serena-mcp-server` — use if already on PATH.
3. Try `uv sync --project "$SERENA_SRC"` to populate the `.venv` (sandbox-safe since uv writes to its own cache).
4. Re-check `$SERENA_SRC/.venv/bin/serena-mcp-server` after sync.
5. If nothing works, output a clear error to stderr and `exit 1`.

The `.venv` approach avoids all sandbox restrictions because we're executing a pre-existing binary, not installing anything.

**ivy_lsp PATH requirement**: Serena's `IvyLanguageServer` calls `shutil.which("ivy_lsp")`. The `ivy_lsp` binary must be on PATH. The `.venv` has `ivy_lsp` installed (confirmed), but `.venv/bin/` is NOT automatically on PATH when executing `$SERENA_SRC/.venv/bin/serena-mcp-server` directly. The fix must prepend the `.venv/bin` to PATH before exec:

```bash
export PATH="$SERENA_SRC/.venv/bin:$PATH"
exec "$SERENA_BIN" --project "$DETECTED_ROOT" --context claude-code 2>>"$LOG_FILE"
```

This ensures `shutil.which("ivy_lsp")` finds the `.venv`'s copy.

**Estimated change**: ~25 lines replacing lines 102-125 in `start-serena.sh`.

### Fix 3C: Clear error messages (script, diagnostic improvement)

**File**: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-serena.sh`

Replace the current `ivy_lsp` check at lines 64-68 (which logs but continues) with a hard failure:

```bash
if ! command -v ivy_lsp &>/dev/null && [ ! -x "${SERENA_VENV:-}/bin/ivy_lsp" ]; then
    echo "ERROR: ivy_lsp not found. Serena requires ivy_lsp on PATH." >&2
    echo "Fix: cd $SERENA_SRC && uv sync" >&2
    exit 1
fi
```

Claude Code captures stderr from failed MCP servers and displays it in the connection error panel, giving the user actionable instructions.

**Estimated change**: ~8 lines in `start-serena.sh`.

## Files Changed

| File | Fix | Lines | Description |
|---|---|---|---|
| `plugins/.mcp.json` | 1A, 3A | -1, +1 | Remove `IVY_LSP_FORCE_REINSTALL`; add `PANTHER_IVY_ENABLE_SERENA` to serena env |
| `ivy_lsp/mcp/server.py` | 1B, 2B | +100 | Index bootstrapping + manifest generation + version fingerprint + transport crash handler |
| `ivy_lsp/mcp/tools/__init__.py` | 1C, 2A | +35 | `import anyio` + "indexing in progress" helper + shield sidecar cleanup |
| `ivy_lsp/__main__.py` | 2C | +5 | Reset sidecar state in restart loop |
| `scripts/start-serena.sh` | 3A, 3B, 3C | +35, -25 | Opt-in gate + .venv resolution + PATH export + error messages |
| `.gitignore` (ivy-lsp) | 1B | +1 | Add `.ivy-index/` |
| `.gitignore` (panther_ivy) | 1B | +1 | Add `.ivy-index/` |
| Plugin CLAUDE.md | 3A | +3 | Document `PANTHER_IVY_ENABLE_SERENA` env var |

**Total**: ~180 lines changed across 7-8 files (2 submodule repos: ivy-lsp, panther-ivy-plugin).

## Implementation Order

### Phase 1: Quick Stabilization (config + scripts, no Python changes)
1. Fix 1A — Remove `FORCE_REINSTALL` from `.mcp.json`
2. Fix 3A — Add opt-in gate to `start-serena.sh`
3. Fix 3B — Use `.venv` resolution in `start-serena.sh`
4. Fix 3C — Add error messages to `start-serena.sh`

### Phase 2: MCP Crash Fix (ivy-lsp Python changes)
5. Fix 2A — Shield sidecar cleanup in `tools/__init__.py`
6. Fix 2C — Reset sidecar state in `__main__.py`
7. Fix 2B — Transport crash handler in `server.py`

### Phase 3: Persistent Index (ivy-lsp Python changes)
8. Fix 1B — Bootstrap `_write_model_to_index()` in `server.py`
9. Fix 1C — "Indexing in progress" UX in tool handlers

## Testing Strategy

### Manual Integration Tests

- **Fix 1A**: Start a new Claude Code session, verify MCP server starts without `--reinstall` flag in logs. Check `ivy_capabilities` responds in <10s.
- **Fix 1B**: Delete `.ivy-index/` directories, restart MCP server, verify `.ivy-index/manifest.json` is created after first tool call. Restart again, verify Strategy 1 path taken (log line `[MIL:mcp] Loading from .ivy-index`).
- **Fix 1C**: Call `ivy_coverage` immediately after server restart (before prewarm completes), verify "model building" message instead of error.
- **Fix 2A-C**: Simulate sidecar crash by killing the sidecar HTTP process mid-session. Verify MCP server recovers (logs show restart, tools remain available).
- **Fix 3A-C**: Start session with `PANTHER_IVY_ENABLE_SERENA=0` (default), verify no Serena error. Set `=1`, verify Serena connects via `.venv`. Remove `.venv`, verify clear error message on stderr.

### Automated Unit Tests

Existing test infrastructure in `ivy-lsp/tests/` is mature with well-established patterns for mocking `WorkspaceContext`, sidecar clients, and tool handlers. Each fix should have regression tests.

**Fix 1B** (in new `tests/test_mcp_index_bootstrap.py`, following `test_workspace_context.py` patterns):
- `test_write_model_to_index_empty_protocol_indexes`: Mock `McpContext` with empty `workspace_context.protocol_indexes`, call `_write_model_to_index(model)`, verify `.ivy-index/` created with valid `manifest.json` + pickle files.
- `test_write_model_to_index_creates_directories`: Verify `os.makedirs` called for missing `.ivy-index/` dirs.
- `test_build_model_roundtrip_cold_to_warm`: First `_build_model()` takes Strategy 2, triggers `_write_model_to_index`. Reload `WorkspaceContext`, verify Strategy 1 path taken on second call.
- `test_manifest_version_fingerprint`: Write index with version X, load with version Y, verify `stale_major` triggered.

**Fix 1C** (in `tests/test_mcp_scoped_tools.py`):
- Parametrized test over all tools with `needs_model: True`, verifying that when `ctx.get_model_or_none()` returns None, the tool returns `{"success": false, "retry_after_seconds": 30}`.

**Fix 2A** (in `tests/test_safe_tool_delegation.py`):
- `test_cleanup_sidecar_catches_runtime_error`: Mock `disconnect_sidecar` to raise `RuntimeError("cancel scope in wrong task")`. Verify no propagation.
- `test_cleanup_sidecar_catches_cancelled_error`: Mock to raise `asyncio.CancelledError`. Verify no propagation.
- `test_cleanup_sidecar_timeout`: Mock to hang. Verify returns within 3-second timeout.

**Fix 2B** (in `tests/test_mcp_server.py` or new file):
- Mock `mcp.run()` to raise `BaseExceptionGroup("...", [RuntimeError("cancel scope")])`, verify `sys.exit(0)`.
- Mock with non-cancel-scope error, verify re-raise.
- Mock with mixed ExceptionGroup (one cancel-scope + one ValueError), verify re-raise (not swallowed).

**Fix 2C** (in `tests/test_sidecar_client.py`):
- Verify `set_sidecar_client(None)` and `set_sidecar_port(None)` are called between restart attempts.

**Fix 3A** (in `panther-ivy-plugin/tests/test_workspace_detection.py`, using existing subprocess pattern):
- `test_serena_disabled_by_default`: Run `start-serena.sh` with `PANTHER_IVY_ENABLE_SERENA=0`, verify exit code 0.
- `test_serena_enabled_without_source`: Run with `=1` in directory with no panther-serena, verify exit code 1 and stderr error message.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Stale uvx cache after ivy-lsp source change | Document `IVY_LSP_FORCE_REINSTALL=1` for dev use. Already in plugin CLAUDE.md. |
| Pickle version mismatch after ivy-lsp upgrade | Version fingerprint in `manifest.json` triggers full rebuild on mismatch. Existing exception handling at `context.py:486-500` catches gross deserialization failures as backup. |
| Pickle security (arbitrary code execution via crafted `.pickle.gz`) | `.ivy-index/.gitignore` containing `*` prevents accidental commits. `.ivy-index/` added to repo `.gitignore`. Future: restricted unpickler with module allowlist. |
| `anyio.CancelScope(shield=True)` masking connection leaks | Narrow scope: only shields the disconnect call, with 3s timeout and WARNING-level logging. |
| Fix 2B ExceptionGroup catch swallowing non-cancel-scope errors | Sub-exception filtering: only exits cleanly if ALL sub-exceptions are cancel-scope related. Mixed groups re-raise. |
| `.venv` hardcoded paths break on different machine | Fallback chain: `.venv` → PATH → `uv sync` → error message. |
| `exit 0` for disabled Serena not reaching script (env var not propagated) | `PANTHER_IVY_ENABLE_SERENA` added to `.mcp.json` env block with empty string (inherit from parent). Stderr message on disabled exit for visibility. |
