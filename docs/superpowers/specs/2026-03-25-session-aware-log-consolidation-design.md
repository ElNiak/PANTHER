# Session-Aware Log Consolidation

**Date**: 2026-03-25
**Status**: Draft
**Branch**: `refactor/ivy-lsp-cleanup` (worktree: `lsp-to-claude`)

## Problem

All ivy-lsp/MCP observability logs land in `.observability/sessions/unknown/` instead of being tagged with the Claude Code session ID. Additionally, server logs (stderr, Python rotating logs, debug traces) scatter across `/tmp/` with no session association. Session directories use opaque IDs that are hard to browse chronologically.

### Root Cause

1. **Missing env var bridge**: The MCP server reads `IVY_SESSION_ID` from its process environment, but Claude Code does not expose a session ID env var to MCP child processes. The SessionStart hook writes `IVY_SESSION_ID` to `CLAUDE_ENV_FILE`, but that only affects future Bash commands — not already-running MCP servers.

2. **Startup race**: The SessionStart hook writes the session ID to `/tmp/ivy-session-<hash>.id`, and `start-ivy-server.sh` tries to read it. But the MCP server may start before or concurrently with the SessionStart hook, so the file doesn't exist yet.

3. **One-shot resolution**: `get_session_id()` reads `os.environ` once. For a long-running MCP server process, the env var never changes, so even if the hook eventually writes the file, the server never picks it up.

4. **Hook/MCP directory mismatch**: Hook scripts receive the raw Claude Code session ID from hook payloads, while the MCP server resolves its own session ID independently. Without a shared session file, they could write to different directories.

## Design

### 0. Date-prefixed session IDs

Session directory names use the format `YYYY-MM-DDTHHMM-<claude_session_id>` (e.g., `2026-03-25T1430-abc123`). This makes sessions chronologically sortable and human-browsable.

The date prefix is applied **once** at session start in `detect-ivy-workspace.sh` and written to the session file. All consumers (MCP server, hook scripts, startup script) read the same prefixed ID from the session file — guaranteeing all logs land in the same directory.

### 1. SessionStart hook writes date-prefixed session ID

**File**: `hooks/scripts/detect-ivy-workspace.sh`

After resolving the raw Claude Code session ID (line 27-31), apply the date prefix:

```bash
if [ -n "$RESOLVED_SESSION_ID" ]; then
    _SESSION_DATE="$(date +%Y-%m-%dT%H%M)"
    RESOLVED_SESSION_ID="${_SESSION_DATE}-${RESOLVED_SESSION_ID}"
fi
```

This prefixed ID is then written to both `CLAUDE_ENV_FILE` (line 55) and the session file (line 63), which already happens — no change to those write paths.

### 2. Lazy file-based session ID resolution in MCP server

**File**: `ivy_lsp/session_observability.py` — `get_session_id()`

Change the resolution chain to:

```
1. os.environ["IVY_SESSION_ID"]          (explicit override, existing)
2. Read /tmp/ivy-session-<ws_hash>.id    (written by SessionStart hook, NEW)
3. "unknown"                              (fallback, existing)
```

The workspace hash **must use 12 hex characters** of SHA-256, matching the shell convention in `detect-ivy-workspace.sh` (line 62) and `start-ivy-server.sh` (line 84):

```python
# Python — must match: printf '%s' "$path" | shasum -a 256 | cut -c1-12
hashlib.sha256(workspace_root.encode()).hexdigest()[:12]
```

Note: `debug_trace.py` uses `[:8]` for its own hash — that is a different convention for a different purpose and must NOT be changed.

**Why this works**: By the time the first MCP tool call executes, the SessionStart hook has already run and written the file. The existing `_LoggerKey` comparison in `get_session_logger()` detects the session_id change and auto-creates a new `SessionEventLogger` pointing at the correct session directory. Note: `get_config()` in `config.py` has its own `IVY_SESSION_ID` env-var-based rebuild trigger — this trigger becomes dead code under the file-based scheme, which is harmless since `_LoggerKey` handles all session transitions independently.

**Caching**: Cache the file read per workspace root with a simple TTL approach:

```python
_session_cache: dict[str, tuple[float, str]] = {}  # ws_root -> (monotonic_time, session_id)
_SESSION_CACHE_TTL = 5.0  # seconds

def _read_session_file(ws_root: str, *, session_dir: str = "/tmp") -> str | None:
    now = time.monotonic()
    cached = _session_cache.get(ws_root)
    if cached and (now - cached[0]) < _SESSION_CACHE_TTL:
        return cached[1]
    ws_hash = hashlib.sha256(ws_root.encode()).hexdigest()[:12]
    path = Path(session_dir) / f"ivy-session-{ws_hash}.id"
    try:
        value = path.read_text().strip()
    except OSError:
        return None
    if value:
        _session_cache[ws_root] = (now, value)
        return value
    return None
```

No mtime tracking — pure TTL. On `OSError` (file deleted, permissions), return `None` and fall through to `"unknown"`. Thread safety: simple dict assignment is atomic under CPython GIL.

### 3. Hook observability scripts read from session file

**File**: `hooks/scripts/observability/log_event.py`

Currently, hook scripts pass the raw `session_id` from the hook payload to `log_event()`. This raw ID won't match the date-prefixed directory.

Add a `_resolve_session_id()` function to `log_event.py` that reads from the session file first, falling back to the raw payload ID:

```python
def _resolve_session_id(raw_session_id: str) -> str:
    """Resolve session ID from session file, falling back to raw payload ID.

    The session file contains the date-prefixed ID written by the SessionStart hook.
    """
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if ws_root:
        ws_hash = hashlib.sha256(ws_root.encode()).hexdigest()[:12]
        session_file = Path("/tmp") / f"ivy-session-{ws_hash}.id"
        try:
            value = session_file.read_text().strip()
            if value:
                return value
        except OSError:
            pass
    return (raw_session_id or "unknown").strip() or "unknown"
```

Update `log_event()` to call `_resolve_session_id(session_id)` instead of the inline normalization at line 64.

No caching needed here — hook scripts are short-lived processes (one invocation per hook event), so file I/O is negligible.

### 4. Redirect server logs into session directory

**File**: `start-ivy-server.sh`

After session ID resolution (lines 76-96), if a session ID was resolved:

```bash
SESSION_LOG_DIR="${IVY_WORKSPACE_ROOT}/.observability/sessions/${IVY_SESSION_ID}"
mkdir -p "$SESSION_LOG_DIR"
LOG_FILE="${SESSION_LOG_DIR}/ivy-${MODE}-${_IVY_LOG_TS}-$$.log"
export IVY_LSP_LOG_FILE="$LOG_FILE"
export IVY_LSP_DEBUG_LOG_PATH="${SESSION_LOG_DIR}/debug-trace.log"
```

Keep `/tmp/` symlinks for backward compat:

```bash
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"    # or ivy-mcp-latest.log
```

**When session ID is NOT resolved** (fallback): Use existing `/tmp/` paths unchanged. No regression.

### 5. Resulting per-session directory structure

```
.observability/sessions/2026-03-25T1430-abc123/
├── events.jsonl                # Structured MCP/LSP/hook events (JSONL)
├── debug-trace.log             # Debug trace (parser tiers, MCP I/O, LSP responses)
├── ivy-mcp-<ts>-<pid>.log     # MCP server stderr + Python rotating log
└── ivy-lsp-<ts>-<pid>.log     # LSP server stderr + Python rotating log (if applicable)
```

## Edge Cases

### Race condition at startup

The MCP server starts before the SessionStart hook writes the session file. On the first `get_session_id()` call (at startup), the file doesn't exist, so session resolves to `"unknown"`. The first few Python logger setup lines go to `unknown/`. On the first MCP tool call (which always happens after SessionStart), `get_session_id()` re-reads the file, finds the real session ID, and `_LoggerKey` triggers logger recreation. From that point on, all events go to the correct session directory.

**Acceptable**: Only a handful of startup log lines land in `unknown/`. The `events.jsonl` entries that matter (tool calls) all get the correct session ID.

**Note on absent-file caching**: When the file is absent, `_read_session_file` returns `None` without caching. This means the next call will immediately re-check the file — no 5-second wait required. The TTL cache only applies to successfully resolved session IDs.

**Debug trace in the race case**: When the session file doesn't exist at startup, `start-ivy-server.sh` does not set `IVY_LSP_DEBUG_LOG_PATH`, so `debug_trace.py` falls back to `resolve_session_log_dir(get_session_id())` — which also resolves to `"unknown"` at that point. The debug trace log lands in `unknown/debug-trace.log`. Unlike `events.jsonl`, the debug trace FileHandler is set once at init and does not auto-rotate on session change. This is acceptable: the debug trace is a continuous process-level log (like the bash stderr log), not a per-session artifact.

### Session change mid-process

If a new Claude Code session starts while the MCP server is still running, the SessionStart hook overwrites `/tmp/ivy-session-<hash>.id` with a new date-prefixed ID. On the next MCP tool call, `get_session_id()` picks up the new ID (after TTL expiry), `_LoggerKey` rebuilds the logger, and events route to a new session directory.

The bash-level log file stays in the original session directory — acceptable since it's a long-running process log.

### No workspace root

If `IVY_WORKSPACE_ROOT` is not set, `get_session_id()` falls back to `os.getcwd()` for hash computation. Hook `log_event.py` falls back to the raw payload ID. If neither works, falls back to `"unknown"`.

### Backward compatibility

- `/tmp/ivy-lsp-latest.log` and `/tmp/ivy-mcp-latest.log` symlinks still point to the active log file (now inside the session directory). CLAUDE.md debug instructions remain valid.
- Hook observability scripts now use the session file when available, falling back to raw payload IDs — no breaking change.

## Files Modified

| File | Change |
|------|--------|
| `hooks/scripts/detect-ivy-workspace.sh` | Apply date prefix to `RESOLVED_SESSION_ID` before writing |
| `ivy_lsp/session_observability.py` | `get_session_id()`: add file-based fallback with per-workspace cached read |
| `hooks/scripts/observability/log_event.py` | Add `_resolve_session_id()` to read from session file |
| `scripts/start-ivy-server.sh` | Redirect `LOG_FILE`, `IVY_LSP_LOG_FILE`, `IVY_LSP_DEBUG_LOG_PATH` into session dir |

## Files NOT Modified

- `.mcp.json` — no env var changes needed
- `debug_trace.py` — already falls back to session dir via `resolve_session_log_dir()`; explicit `IVY_LSP_DEBUG_LOG_PATH` override from startup script handles the non-race case. In the race case, debug trace lands in `unknown/` for the process lifetime (see edge case section)
- Individual hook scripts (`obs_post_tool_use.py`, etc.) — they pass raw session_id to `log_event()`, which now resolves internally

## Testing

1. **Unit test**: Mock `/tmp/ivy-session-<hash>.id` file, verify `get_session_id()` reads date-prefixed ID when env var is empty
2. **Unit test**: Verify per-workspace cache — two different workspace roots return different session IDs
3. **Unit test**: Verify cache TTL and expiry
4. **Unit test**: Verify `get_session_id()` falls back to `"unknown"` when both env var and file are absent
5. **Unit test**: Verify startup race — `get_session_id()` returns `"unknown"` when file absent (no caching), then returns correct ID immediately after file is written
6. **Unit test**: Verify `log_event.py` `_resolve_session_id()` reads from session file
7. **Integration test**: Verify `events.jsonl` has correct date-prefixed session ID and lives in correct directory
8. **Integration test**: Race scenario — initial events in `unknown/`, subsequent events in correct session directory
9. **Manual test**: Start Claude Code session, run MCP tool, verify `.observability/sessions/YYYY-MM-DDTHHMM-<id>/` contains all log files
