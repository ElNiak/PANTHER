# Session-Aware Log Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route all ivy-lsp observability logs into date-prefixed per-session directories (e.g., `2026-03-25T1430-abc123/`) instead of `/tmp/` and `sessions/unknown/`.

**Architecture:** SessionStart hook applies date prefix to session ID and writes to a shared session file. MCP server and hook scripts both read from that file, ensuring all logs converge in the same directory. Server logs (stderr, debug trace) are also redirected into the session directory.

**Tech Stack:** Python 3.10+, Bash, pytest, monkeypatch

**Spec:** `docs/superpowers/specs/2026-03-25-session-aware-log-consolidation-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `hooks/scripts/detect-ivy-workspace.sh` | Modify | Apply date prefix to `RESOLVED_SESSION_ID` |
| `ivy_lsp/session_observability.py` | Modify | Add `_read_session_file()`, `_workspace_hash()`, update `get_session_id()`, add `reset_session_cache()` |
| `hooks/scripts/observability/log_event.py` | Modify | Add `_resolve_session_id()` to read from session file |
| `scripts/start-ivy-server.sh` | Modify | Redirect log files into session directory |
| `tests/test_session_observability.py` | Modify | Add tests for file-based resolution, caching, race, session transition |

**Path roots:**
- ivy-lsp Python: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
- Plugin scripts/hooks: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

---

### Task 1: Date-prefix session ID in SessionStart hook

**Files:**
- Modify: `hooks/scripts/detect-ivy-workspace.sh` (lines 27-31 and 55)

- [ ] **Step 1: Add date prefix after session ID resolution**

In `detect-ivy-workspace.sh`, after line 31 (after the `RESOLVED_SESSION_ID` fallback block), add:

```bash
# Apply date prefix for chronologically sortable session directories
if [ -n "$RESOLVED_SESSION_ID" ]; then
    _SESSION_DATE="$(date +%Y-%m-%dT%H%M)"
    RESOLVED_SESSION_ID="${_SESSION_DATE}-${RESOLVED_SESSION_ID}"
fi
```

This goes AFTER line 31 (`RESOLVED_SESSION_ID="${CLAUDE_SESSION_ID:-...}"`) and BEFORE line 34 (`resolve_ivy_lsp_source`). The rest of the script (writing to `CLAUDE_ENV_FILE` at line 55, writing to session file at line 63) already uses `$RESOLVED_SESSION_ID` — no changes needed there.

- [ ] **Step 2: Verify script syntax**

Run: `bash -n panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/detect-ivy-workspace.sh`

Expected: No output (no syntax errors).

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/detect-ivy-workspace.sh
git commit -m "feat(observability): date-prefix session IDs for chronological sorting"
```

---

### Task 2: Add `_workspace_hash()`, `_read_session_file()`, and update `get_session_id()`

**Files:**
- Modify: `ivy_lsp/session_observability.py`
- Modify: `tests/test_session_observability.py`

- [ ] **Step 1: Write the failing tests**

In `tests/test_session_observability.py`, first update the import block and autouse fixture:

```python
# Replace the existing import block with:
import hashlib
import json
import unittest.mock

import pytest

from ivy_lsp.config import reset_config
from ivy_lsp.debug_trace import init_tracer
from ivy_lsp.session_observability import (
    _read_session_file,
    _workspace_hash,
    get_session_id,
    get_session_logger,
    reset_session_cache,
    reset_session_logger,
    resolve_session_log_dir,
)


# Replace the existing autouse fixture with:
@pytest.fixture(autouse=True)
def _reset_observability_state():
    reset_config()
    reset_session_logger()
    reset_session_cache()
    yield
    reset_config()
    reset_session_logger()
    reset_session_cache()
```

Then add these new tests at the end of the file:

```python
# --- Session file resolution tests ---

def test_workspace_hash_matches_shell_convention():
    """Python hash must match: printf '%s' "$path" | shasum -a 256 | cut -c1-12"""
    path = "/Users/test/workspace"
    expected = hashlib.sha256(path.encode()).hexdigest()[:12]
    assert _workspace_hash(path) == expected
    assert len(_workspace_hash(path)) == 12


def test_read_session_file_returns_id(tmp_path):
    ws = str(tmp_path / "workspace")
    ws_hash = hashlib.sha256(ws.encode()).hexdigest()[:12]
    session_file = tmp_path / f"ivy-session-{ws_hash}.id"
    session_file.write_text("2026-03-25T1430-abc123\n")

    result = _read_session_file(ws, session_dir=str(tmp_path))
    assert result == "2026-03-25T1430-abc123"


def test_read_session_file_returns_none_when_missing(tmp_path):
    result = _read_session_file("/nonexistent/path", session_dir=str(tmp_path))
    assert result is None


def test_read_session_file_caches_within_ttl(tmp_path):
    ws = str(tmp_path / "workspace")
    ws_hash = hashlib.sha256(ws.encode()).hexdigest()[:12]
    session_file = tmp_path / f"ivy-session-{ws_hash}.id"
    session_file.write_text("2026-03-25T1430-first\n")

    result1 = _read_session_file(ws, session_dir=str(tmp_path))
    assert result1 == "2026-03-25T1430-first"

    session_file.write_text("2026-03-25T1430-second\n")
    result2 = _read_session_file(ws, session_dir=str(tmp_path))
    assert result2 == "2026-03-25T1430-first"  # cached


def test_read_session_file_expires_after_ttl(tmp_path):
    ws = str(tmp_path / "workspace")
    ws_hash = hashlib.sha256(ws.encode()).hexdigest()[:12]
    session_file = tmp_path / f"ivy-session-{ws_hash}.id"
    session_file.write_text("2026-03-25T1430-old\n")

    _read_session_file(ws, session_dir=str(tmp_path))
    session_file.write_text("2026-03-25T1431-new\n")

    # Backdate cache entry to simulate TTL expiry
    import ivy_lsp.session_observability as obs_mod
    cached = obs_mod._session_cache.get(ws)
    assert cached is not None
    obs_mod._session_cache[ws] = (cached[0] - 10.0, cached[1])

    result = _read_session_file(ws, session_dir=str(tmp_path))
    assert result == "2026-03-25T1431-new"


def test_read_session_file_per_workspace_isolation(tmp_path):
    ws_a = str(tmp_path / "workspace-a")
    ws_b = str(tmp_path / "workspace-b")
    hash_a = hashlib.sha256(ws_a.encode()).hexdigest()[:12]
    hash_b = hashlib.sha256(ws_b.encode()).hexdigest()[:12]
    (tmp_path / f"ivy-session-{hash_a}.id").write_text("session-a\n")
    (tmp_path / f"ivy-session-{hash_b}.id").write_text("session-b\n")

    assert _read_session_file(ws_a, session_dir=str(tmp_path)) == "session-a"
    assert _read_session_file(ws_b, session_dir=str(tmp_path)) == "session-b"


def test_get_session_id_prefers_env_var(monkeypatch):
    monkeypatch.setenv("IVY_SESSION_ID", "from-env")
    assert get_session_id() == "from-env"


def test_get_session_id_falls_back_to_file(tmp_path, monkeypatch):
    monkeypatch.delenv("IVY_SESSION_ID", raising=False)
    ws = str(tmp_path / "workspace")
    monkeypatch.setenv("IVY_WORKSPACE_ROOT", ws)
    ws_hash = hashlib.sha256(ws.encode()).hexdigest()[:12]
    (tmp_path / f"ivy-session-{ws_hash}.id").write_text("2026-03-25T1430-file\n")

    assert get_session_id(session_dir=str(tmp_path)) == "2026-03-25T1430-file"


def test_get_session_id_returns_unknown_when_no_source(tmp_path, monkeypatch):
    monkeypatch.delenv("IVY_SESSION_ID", raising=False)
    monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
    assert get_session_id(session_dir=str(tmp_path)) == "unknown"


def test_get_session_id_race_then_resolve(tmp_path, monkeypatch):
    """File absent → unknown; file written → resolves immediately (no TTL wait)."""
    monkeypatch.delenv("IVY_SESSION_ID", raising=False)
    ws = str(tmp_path / "workspace")
    monkeypatch.setenv("IVY_WORKSPACE_ROOT", ws)

    # Before SessionStart hook
    assert get_session_id(session_dir=str(tmp_path)) == "unknown"

    # SessionStart hook writes file (absent-file case is not cached, so no wait)
    ws_hash = hashlib.sha256(ws.encode()).hexdigest()[:12]
    (tmp_path / f"ivy-session-{ws_hash}.id").write_text("2026-03-25T1430-real\n")

    assert get_session_id(session_dir=str(tmp_path)) == "2026-03-25T1430-real"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_session_observability.py -k "workspace_hash or read_session_file or get_session_id_prefers or get_session_id_falls or get_session_id_returns or get_session_id_race" -v`

Expected: FAIL — `_read_session_file`, `_workspace_hash`, `reset_session_cache` do not exist yet.

- [ ] **Step 3: Implement the changes in `session_observability.py`**

Add these imports at the top (after the existing imports):

```python
import hashlib
import time
```

Add these helpers after the imports, before `get_session_id()`:

```python
# --- Session file cache (keyed by workspace root) ---
_session_cache: dict[str, tuple[float, str]] = {}  # ws_root -> (monotonic_time, session_id)
_SESSION_CACHE_TTL = 5.0  # seconds


def _workspace_hash(workspace_root: str) -> str:
    """12-char SHA-256 hex hash matching the shell convention.

    Shell equivalent: ``printf '%s' "$path" | shasum -a 256 | cut -c1-12``
    """
    return hashlib.sha256(workspace_root.encode()).hexdigest()[:12]


def _read_session_file(
    workspace_root: str,
    *,
    session_dir: str = "/tmp",
) -> str | None:
    """Read session ID from the file written by the SessionStart hook.

    Returns ``None`` if the file is missing, empty, or unreadable.
    Results are cached per workspace root for ``_SESSION_CACHE_TTL`` seconds.
    Thread safety: simple dict assignment is atomic under CPython GIL.
    """
    now = time.monotonic()
    cached = _session_cache.get(workspace_root)
    if cached and (now - cached[0]) < _SESSION_CACHE_TTL:
        return cached[1]

    ws_hash = _workspace_hash(workspace_root)
    path = Path(session_dir) / f"ivy-session-{ws_hash}.id"
    try:
        value = path.read_text().strip()
    except OSError:
        return None
    if value:
        _session_cache[workspace_root] = (now, value)
        return value
    return None


def reset_session_cache() -> None:
    """Clear the session file cache (for tests)."""
    _session_cache.clear()
```

Replace the existing `get_session_id()` (lines 19-22) with:

```python
def get_session_id(*, session_dir: str = "/tmp") -> str:
    """Return the active session identifier, or ``unknown`` when missing.

    Resolution order:
      1. ``IVY_SESSION_ID`` environment variable (explicit override)
      2. ``/tmp/ivy-session-<ws_hash>.id`` file (written by SessionStart hook)
      3. ``"unknown"`` fallback
    """
    from_env = os.environ.get("IVY_SESSION_ID", "").strip()
    if from_env:
        return from_env

    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip() or os.getcwd()
    from_file = _read_session_file(ws_root, session_dir=session_dir)
    if from_file:
        return from_file

    return "unknown"
```

Update `get_session_logger()` to forward `session_dir`:

```python
def get_session_logger(*, session_dir: str = "/tmp") -> SessionEventLogger:
    """Return a session logger keyed by current config/session state."""
    from ivy_lsp.config import get_config

    cfg = get_config()
    session_id = get_session_id(session_dir=session_dir)
    # ... rest unchanged ...
```

Update `reset_session_logger()` to also reset cache (inside the lock):

```python
def reset_session_logger() -> None:
    """Reset singleton logger state (intended for tests)."""
    global _logger, _logger_key
    with _logger_lock:
        _logger = None
        _logger_key = None
        reset_session_cache()
```

- [ ] **Step 4: Run all tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_session_observability.py -v`

Expected: ALL PASS (new tests + existing tests).

- [ ] **Step 5: Verify backward compatibility of new keyword-only params**

Run: `grep -rn "get_session_id\|get_session_logger" panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/ | grep -v "def \|#\|import\|__pycache__"`

Expected: All callers use `()` with no arguments — the new `session_dir` keyword-only param with default `"/tmp"` is backward-compatible.

- [ ] **Step 6: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/session_observability.py panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/test_session_observability.py
git commit -m "feat(observability): lazy file-based session ID resolution with TTL cache"
```

---

### Task 3: Update hook `log_event.py` to read from session file

**Files:**
- Modify: `hooks/scripts/observability/log_event.py`

- [ ] **Step 1: Add `_resolve_session_id()` and `import hashlib`**

In `log_event.py`, add `import hashlib` to the imports, then add this function before `log_event()`:

```python
import hashlib


def _resolve_session_id(raw_session_id: str) -> str:
    """Resolve session ID from session file, falling back to raw payload ID.

    The session file contains the date-prefixed ID written by SessionStart hook.
    Hook scripts are short-lived, so no caching is needed.
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

- [ ] **Step 2: Update `log_event()` to use `_resolve_session_id()`**

Replace line 64 in `log_event()`:

```python
# OLD:
safe_session_id = (session_id or "unknown").strip() or "unknown"

# NEW:
safe_session_id = _resolve_session_id(session_id)
```

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/observability/log_event.py
git commit -m "feat(observability): hook log_event reads date-prefixed session ID from file"
```

---

### Task 4: Redirect server logs into session directory in `start-ivy-server.sh`

**Files:**
- Modify: `scripts/start-ivy-server.sh` (lines 30-43 and after line 96)

- [ ] **Step 1: Remove symlinks from early log setup**

Replace lines 30-43 of `start-ivy-server.sh` (the log setup block including `log()` helper) with:

```bash
# --- Log setup (initial — may be re-routed after session detection) ---
_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-${MODE}-${_IVY_LOG_TS}-$$.log}"

log() { echo "[ivy-${MODE}] $*" >>"$LOG_FILE"; }
```

This removes the symlink creation that was at lines 35-41. The `log()` helper stays.

- [ ] **Step 2: Add session-aware log redirection after session ID resolution**

After line 96 (the `log "Session id unresolved..."` block), add:

```bash
# --- Session-aware log redirection ---
if [ -n "${IVY_SESSION_ID:-}" ] && [ -n "${IVY_WORKSPACE_ROOT:-}" ]; then
    SESSION_LOG_DIR="${IVY_WORKSPACE_ROOT}/.observability/sessions/${IVY_SESSION_ID}"
    mkdir -p "$SESSION_LOG_DIR"

    LOG_FILE="${SESSION_LOG_DIR}/ivy-${MODE}-${_IVY_LOG_TS}-$$.log"
    export IVY_LSP_LOG_FILE="$LOG_FILE"
    export IVY_LSP_DEBUG_LOG_PATH="${SESSION_LOG_DIR}/debug-trace.log"

    log "Log files redirected to session dir: $SESSION_LOG_DIR"
fi

# Mode-specific symlinks (backward compat — always point to current log file)
if [ "$MODE" = "lsp" ]; then
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-lsp-latest.log"
else
    ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-mcp-latest.log"
fi
```

- [ ] **Step 3: Verify script syntax**

Run: `bash -n panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-ivy-server.sh`

Expected: No output (no syntax errors).

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-ivy-server.sh
git commit -m "feat(observability): redirect server logs into per-session directory"
```

---

### Task 5: Final verification

**Files:** None (verification only)

- [ ] **Step 1: Run all session observability tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_session_observability.py -v`

Expected: ALL PASS.

- [ ] **Step 2: Run broader ivy-lsp test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -v --timeout=30 2>&1 | tail -30`

Expected: No new failures.

- [ ] **Step 3: Verify all callers are backward-compatible**

Run: `grep -rn "get_session_id\|get_session_logger" panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/ | grep -v "def \|#\|import\|__pycache__"`

Expected: All callers use `()` with no arguments.

- [ ] **Step 4: Verify shell scripts are syntactically valid**

Run: `bash -n panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/scripts/start-ivy-server.sh && bash -n panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/detect-ivy-workspace.sh`

Expected: No output (no syntax errors).
