# Ivy LSP + MCP Reliability Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 reliability issues in the Ivy LSP + MCP stack that cause startup crashes, error noise, stale state, and path resolution failures.

**Architecture:** All fixes follow existing patterns in each codebase. No new files, no architectural changes. Fixes touch two git submodules: `ivy-lsp` and `panther-ivy-plugin`, both under `panther/plugins/services/testers/panther_ivy/submodules/`.

**Tech Stack:** Bash (plugin scripts), Python (ivy-lsp server)

**Spec:** `docs/superpowers/specs/2026-03-30-ivy-lsp-mcp-reliability-fixes-design.md`

**Base paths:**
- `PLUGIN`: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin`
- `IVY_LSP`: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp`

---

### Task 1: Fix Serena venv race condition (PYTHONPATH)

**Files:**
- Modify: `${PLUGIN}/scripts/start-serena.sh:140-142`

- [ ] **Step 1: Add PYTHONPATH export before exec**

In `start-serena.sh`, insert two lines before the `exec` on line 142. The `PYTHONPATH` ensures `serena` and `ivy_lsp` are importable even when the editable install `.pth` file is temporarily missing during a concurrent `uv sync`.

Find this block (lines 140-142):
```bash
# --- Launch Serena MCP server ---
log "Launching serena-mcp-server with project root: $DETECTED_ROOT"
exec "$SERENA_BIN" --project "$DETECTED_ROOT" --context claude-code 2>>"$LOG_FILE"
```

Replace with:
```bash
# --- Launch Serena MCP server ---
log "Launching serena-mcp-server with project root: $DETECTED_ROOT"
# Ensure serena + ivy-lsp are importable regardless of .pth file state (uv sync race)
export PYTHONPATH="$SERENA_SRC/src:${IVY_LSP_SRC:+$IVY_LSP_SRC:}${PYTHONPATH:-}"
exec "$SERENA_BIN" --project "$DETECTED_ROOT" --context claude-code 2>>"$LOG_FILE"
```

- [ ] **Step 2: Verify the fix**

Start a new Claude Code session (or restart MCP servers). Check the Serena log for crashes:
```bash
grep "ModuleNotFoundError" /tmp/serena-*.log | tail -5
```
Expected: No new `ModuleNotFoundError` entries after the fix.

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add plugins/panther-ivy-plugin/scripts/start-serena.sh
git commit -m "fix: add PYTHONPATH to prevent serena venv race condition

The editable install .pth file is temporarily unavailable during
concurrent uv sync, causing ModuleNotFoundError on startup.
Setting PYTHONPATH explicitly makes the import independent of .pth state."
```

---

### Task 2: Make Z3 a hard dependency in ivy-lsp

**Files:**
- Modify: `${IVY_LSP}/pyproject.toml:25-31`

- [ ] **Step 1: Add z3-solver to core dependencies**

In `pyproject.toml`, add `"z3-solver",` to the `dependencies` list. Find this block (lines 25-31):
```toml
dependencies = [
    "pygls>=2.0",
    "lsprotocol",
    "panther_ms_ivy",
    "pyyaml>=6.0",
    'exceptiongroup>=1.0.0; python_version < "3.11"',
]
```

Replace with:
```toml
dependencies = [
    "pygls>=2.0",
    "lsprotocol",
    "panther_ms_ivy",
    "z3-solver",
    "pyyaml>=6.0",
    'exceptiongroup>=1.0.0; python_version < "3.11"',
]
```

- [ ] **Step 2: Remove redundant z3 from optional deps**

In the same file, update the `full` and `mcp` optional deps to remove the now-redundant `panther_ms_ivy[z3]`. Find (lines 33-35):
```toml
[project.optional-dependencies]
full = ["panther_ms_ivy[z3]"]
mcp = ["mcp>=1.26.0", "anyio>=4.13.0", "panther_ms_ivy[z3]", "docker>=7.0", "pyyaml>=6.0", "uvicorn>=0.30"]
```

Replace with:
```toml
[project.optional-dependencies]
full = []
mcp = ["mcp>=1.26.0", "anyio>=4.13.0", "docker>=7.0", "pyyaml>=6.0", "uvicorn>=0.30"]
```

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add pyproject.toml
git commit -m "fix: make z3-solver a core dependency

Z3 is required for all parser operations. Moving it from optional
to core prevents 636+ silent ModuleNotFoundError warnings per startup
when the server incorrectly detects Z3 availability."
```

---

### Task 3: Fix Z3 detection in _create_parser()

**Files:**
- Modify: `${IVY_LSP}/ivy_lsp/lsp/server_setup.py:334-368`

- [ ] **Step 1: Fix the Z3 import test**

In `server_setup.py`, update `_create_parser()` to test the correct import and fail-fast instead of falling back. Find this block (lines 334-368):
```python
    def _create_parser(self, resolver: "IncludeResolver") -> None:
        """Create the Ivy parser, falling back to lexer-only mode without z3.

        Sets self._parser and self._full_mode.
        """
        try:
            # Eagerly verify z3 is actually available --- IvyParserWrapper
            # defers ivy imports to method bodies, so the import above
            # succeeds even without z3.
            import ivy.ivy_utils  # noqa: F401 --- triggers z3_shim

            from ivy_lsp.core.parsing.parser_session import IvyParserWrapper

            self._parser = IvyParserWrapper(resolve_callback=resolver.resolve)
            self._full_mode = True
            slog.info(
                "Full parser available (z3 found)",
                extra={"event": LogEvent(LogCategory.MILESTONE, "startup")},
            )
        except Exception as e:
            from ivy_lsp.core.parsing.fallback_parser import FallbackOnlyParser

            self._parser = FallbackOnlyParser()
            self._full_mode = False
            slog.info(
                "z3 not available (%s); running in light mode",
                e,
                extra={
                    "event": LogEvent(
                        LogCategory.DIAGNOSTIC,
                        "startup",
                        {"reason": str(e)},
                    )
                },
            )
```

Replace with:
```python
    def _create_parser(self, resolver: "IncludeResolver") -> None:
        """Create the Ivy parser.  Z3 is mandatory.

        Sets self._parser and self._full_mode.
        Raises RuntimeError if Z3 / ivy.ivy_parser is not importable.
        """
        try:
            # Verify the full Z3-dependent import chain is available.
            # ivy.ivy_parser -> ivy_actions -> ivy_module -> ivy_solver -> z3_shim
            import ivy.ivy_parser  # noqa: F401

            from ivy_lsp.core.parsing.parser_session import IvyParserWrapper

            self._parser = IvyParserWrapper(resolve_callback=resolver.resolve)
            self._full_mode = True
            slog.info(
                "Full parser available (z3 found)",
                extra={"event": LogEvent(LogCategory.MILESTONE, "startup")},
            )
        except Exception as e:
            slog.error(
                "Z3 is required but ivy.ivy_parser could not be imported: %s",
                e,
                extra={
                    "event": LogEvent(
                        LogCategory.DIAGNOSTIC,
                        "startup",
                        {"reason": str(e)},
                    )
                },
            )
            raise RuntimeError(
                f"Z3 is required but not available: {e}. "
                "Install via 'pip install z3-solver'."
            ) from e
```

- [ ] **Step 2: Verify detection works**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python3 -c "import ivy.ivy_parser; print('Z3 import chain OK')"
```
Expected: `Z3 import chain OK` (if z3-solver is installed) or `ModuleNotFoundError` with clear message.

- [ ] **Step 3: Commit**

```bash
git add ivy_lsp/lsp/server_setup.py
git commit -m "fix: test correct Z3 import chain in _create_parser

The previous check tested 'import ivy.ivy_utils' which does not
depend on Z3, so the check always passed. Now tests 'import
ivy.ivy_parser' which transitively requires Z3 via ivy_solver.
Z3 is mandatory — raise RuntimeError instead of falling back."
```

---

### Task 4: Guard imports in IvyParserWrapper.parse()

**Files:**
- Modify: `${IVY_LSP}/ivy_lsp/core/parsing/parser_session.py:165-166`

- [ ] **Step 1: Wrap imports in try/except**

In `parser_session.py`, find the bare imports at lines 165-166:
```python
        import ivy.ivy_parser as ip
        import ivy.ivy_utils as iu
```

Replace with:
```python
        try:
            import ivy.ivy_parser as ip
            import ivy.ivy_utils as iu
        except (ImportError, ModuleNotFoundError) as exc:
            raise RuntimeError(
                f"Z3 is required but not available: {exc}. "
                "Install via 'pip install z3-solver'."
            ) from exc
```

- [ ] **Step 2: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/parsing/parser_session.py
git commit -m "fix: guard ivy imports in IvyParserWrapper.parse()

Belt-and-suspenders for Z3 mandatory requirement. If the import
fails through any code path, raise a clear RuntimeError instead
of leaking ModuleNotFoundError into the analysis pipeline."
```

---

### Task 5: Add remap_paths to ScopedRequirementModel

**Files:**
- Modify: `${IVY_LSP}/ivy_lsp/core/analysis/test_scope.py:227` (after existing methods)
- Modify: `${IVY_LSP}/ivy_lsp/lsp/server_setup.py:559-560`

- [ ] **Step 1: Add remap_paths method to ScopedRequirementModel**

In `test_scope.py`, add the `remap_paths` method after `register_test_scope` (after line 236). Insert after the `register_test_scope` method's closing line:

```python
    def remap_paths(self, base_dir: str) -> None:
        """Convert relative paths in _test_scopes to absolute.

        Follows the same rel→abs pattern used by T1 (symbols),
        T2 (includes), and T3 (exports) in _prepopulate_from_offline_index.
        """
        with self._lock:
            remapped: Dict[str, TestScope] = {}
            for path, scope in self._test_scopes.items():
                if not os.path.isabs(path):
                    abs_path = os.path.join(base_dir, path)
                    scope = TestScope(
                        test_file=abs_path,
                        include_closure=frozenset(
                            os.path.join(base_dir, f) if not os.path.isabs(f) else f
                            for f in scope.include_closure
                        ),
                        exported_actions=scope.exported_actions,
                        imported_actions=scope.imported_actions,
                        tester_role=scope.tester_role,
                    )
                    remapped[abs_path] = scope
                else:
                    remapped[path] = scope
            self._test_scopes = remapped
            # Rebuild file_to_tests from remapped scopes
            self._file_to_tests.clear()
            for test_file, scope in self._test_scopes.items():
                for f in scope.include_closure:
                    self._file_to_tests[f].add(test_file)
            self._scope_cache.clear()
```

Also add `import os` at the top of the file if not already present.

- [ ] **Step 2: Check TestScope fields**

Before proceeding, verify the `TestScope` dataclass fields match the constructor call above:
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
grep -A 10 "class TestScope" ivy_lsp/core/analysis/test_scope.py | head -15
```

Adjust the `TestScope(...)` constructor in step 1 if the field names differ.

- [ ] **Step 3: Call remap_paths at pickle load time**

In `server_setup.py`, find lines 559-560:
```python
            if proto_idx.requirement_graph is not None:
                self._indexer._requirement_graph = proto_idx.requirement_graph
```

Replace with:
```python
            if proto_idx.requirement_graph is not None:
                proto_idx.requirement_graph.remap_paths(protocol_dir)
                self._indexer._requirement_graph = proto_idx.requirement_graph
```

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/analysis/test_scope.py ivy_lsp/lsp/server_setup.py
git commit -m "fix: remap requirement graph paths on offline index load

The offline index stores test scope paths as relative, but T3 bulk
analysis expects absolute paths. T1 (symbols), T2 (includes), and
T3 (exports) already remap rel→abs on load. This adds the same
remapping for the requirement graph's _test_scopes, eliminating
30 'Cannot read ... for bulk T3' warnings per startup."
```

---

### Task 6: Fix stale PID file cleanup

**Files:**
- Modify: `${PLUGIN}/scripts/start-ivy-server.sh:141-142`
- Modify: `${IVY_LSP}/ivy_lsp/__main__.py:253` (after signal handler)

- [ ] **Step 1: Export IVY_PID_FILE in start-ivy-server.sh**

In `start-ivy-server.sh`, find lines 141-142:
```bash
echo $$ > "$PID_DIR/${_PID_PREFIX}-$$.pid"
trap 'rm -f "$PID_DIR/${_PID_PREFIX}-$$.pid" 2>/dev/null' EXIT TERM INT
```

Replace with:
```bash
echo $$ > "$PID_DIR/${_PID_PREFIX}-$$.pid"
export IVY_PID_FILE="$PID_DIR/${_PID_PREFIX}-$$.pid"
trap 'rm -f "$IVY_PID_FILE" 2>/dev/null' EXIT TERM INT
```

- [ ] **Step 2: Register atexit handler in __main__.py**

In `__main__.py`, find line 253:
```python
    signal.signal(signal.SIGTERM, _sigterm_handler)
```

Insert after it:
```python

    # Clean up PID file on exit. The bash trap in start-ivy-server.sh is
    # destroyed by exec, so we register cleanup in the Python process.
    _pid_file = os.environ.get("IVY_PID_FILE")
    if _pid_file:
        import atexit

        atexit.register(
            lambda f=_pid_file: os.unlink(f) if os.path.exists(f) else None
        )
```

- [ ] **Step 3: Commit both submodules**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add plugins/panther-ivy-plugin/scripts/start-ivy-server.sh
git commit -m "fix: export IVY_PID_FILE for Python-side cleanup

The bash trap is destroyed by exec. Exporting the PID file path
allows the Python process to register atexit cleanup."

cd ../ivy-lsp
git add ivy_lsp/__main__.py
git commit -m "fix: register atexit handler for PID file cleanup

The bash trap in start-ivy-server.sh is destroyed when exec
replaces the shell with uvx/python. Register atexit cleanup
using the IVY_PID_FILE env var to ensure PID files are removed."
```

---

### Task 7: Fix observability directory location

**Files:**
- Modify: `${PLUGIN}/hooks/scripts/check-mcp-health.py:28`

- [ ] **Step 1: Fix _get_state_path fallback**

In `check-mcp-health.py`, line 28 already uses `IVY_WORKSPACE_ROOT` with `os.getcwd()` fallback. The current code is:
```python
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip() or os.getcwd()
```

This is actually already correct — it prefers `IVY_WORKSPACE_ROOT` and only falls back to `os.getcwd()` when the env var is empty. The issue is that `IVY_WORKSPACE_ROOT` is not set during early hook execution (before `detect-ivy-workspace.sh` SessionStart hook runs).

The fix is to use the same workspace detection as the scripts. Replace line 28:
```python
def _get_state_path() -> str:
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if not ws_root:
        # Walk up from CWD looking for panther_ivy (mirrors workspace-common.sh)
        check = os.getcwd()
        for _ in range(10):
            candidate = os.path.join(check, "panther", "plugins", "services",
                                     "testers", "panther_ivy")
            if os.path.isdir(os.path.join(candidate, "protocol-testing")):
                ws_root = candidate
                break
            parent = os.path.dirname(check)
            if parent == check:
                break
            check = parent
        if not ws_root:
            ws_root = os.getcwd()
    sid = os.environ.get("IVY_SESSION_ID", "unknown")
    state_dir = os.path.join(ws_root, ".observability", "sessions", sid)
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "mcp-health-state.json")
```

- [ ] **Step 2: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add plugins/panther-ivy-plugin/hooks/scripts/check-mcp-health.py
git commit -m "fix: resolve workspace root in _get_state_path

When IVY_WORKSPACE_ROOT is not yet set (early hook execution),
walk up from CWD to find panther_ivy directory, matching the
logic in workspace-common.sh. Prevents orphaned .observability/
directory at project root."
```

---

### Task 8: Fix session ID race condition

**Files:**
- Modify: `${PLUGIN}/scripts/workspace-common.sh:139-141`

- [ ] **Step 1: Add wait-and-retry for session file**

In `workspace-common.sh`, find the end of `resolve_session_id()` (lines 139-141):
```bash
    local session_file="/tmp/ivy-session-${ws_hash}.id"
    [ -s "$session_file" ] && { head -n 1 "$session_file" | tr -d '\r\n'; return 0; }
    echo "unknown"
```

Replace with:
```bash
    local session_file="/tmp/ivy-session-${ws_hash}.id"
    [ -s "$session_file" ] && { head -n 1 "$session_file" | tr -d '\r\n'; return 0; }
    # Wait briefly for SessionStart hook to write the session file
    local retries=0
    while [ $retries -lt 3 ] && [ ! -s "$session_file" ]; do
        sleep 1
        retries=$((retries + 1))
    done
    [ -s "$session_file" ] && { head -n 1 "$session_file" | tr -d '\r\n'; return 0; }
    echo "unknown"
```

- [ ] **Step 2: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add plugins/panther-ivy-plugin/scripts/workspace-common.sh
git commit -m "fix: add retry loop for session ID resolution

MCP servers may start before the SessionStart hook writes the
session ID file. Wait up to 3 seconds for the file to appear
before falling back to 'unknown'."
```

---

### Task 9: Verification

- [ ] **Step 1: Clean up stale state**

```bash
rm -f /tmp/ivy-lsp-pids/*.pid
rm -rf .observability/sessions/unknown/
```

- [ ] **Step 2: Start a new Claude Code session and run /nct-health**

Verify all 9 checks pass. Specifically confirm:
- No `ModuleNotFoundError` in Serena logs
- No `Z3 Python bindings not found` errors
- No `Cannot read ... for bulk T3` warnings
- PID files are created and cleaned up on exit
- `.observability/sessions/` exists under `IVY_WORKSPACE_ROOT`, not project root
- Session ID is not "unknown" on first MCP startup
