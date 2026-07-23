# Ivy LSP Workspace Root & Indexing Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Ivy LSP workspace detection and indexing integration across panther-serena and ivy-lsp so that workspace roots are correctly detected, env vars are forwarded, and Serena repo-tests pass.

**Architecture:** Changes span two submodules: panther-serena (MCP/LSP bridge) and ivy-lsp (language server). We add a `.ivyworkspace` marker to the test repo so ivy-lsp uses the correct root, modify the `DependencyProvider` to pass `IVY_LSP_WORKSPACE` from `repository_root_path`, and canonicalize paths in ivy-lsp's workspace detection to fix symlink/worktree issues.

**Tech Stack:** Python 3.11, LSP (pygls), ivy-lsp, panther-serena (SolidLSP framework)

**Base paths (relative to worktree root):**
- `SERENA` = `panther/plugins/services/testers/panther_ivy/submodules/panther-serena`
- `IVY_LSP` = `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `${SERENA}/test/resources/repos/ivy/test_repo/.ivyworkspace` | v3 workspace marker for test repo |
| Modify | `${SERENA}/src/solidlsp/language_servers/ivy_language_server.py` | Pass `IVY_LSP_WORKSPACE` + forward workspace env vars |
| Modify | `${IVY_LSP}/ivy_lsp/core/workspace/detection.py` | `os.path.realpath()` canonicalization in worktree + entry point |
| Modify | `${IVY_LSP}/tests/test_workspace_detection.py` | Add symlink canonicalization test |

---

### Task 1: Add `.ivyworkspace` marker to Ivy test repo

**Context:** The test repo at `test/resources/repos/ivy/test_repo/` has no `.ivyworkspace` marker. Without it, ivy-lsp falls through all detection strategies to "fallback" and may use a parent directory as workspace root. If detection walks up to the panther-serena root, the `test/` path component matches the hardcoded `"test"` in `_EXCLUDED_DIR_BASENAMES` (line 35 of `include_resolver.py`), excluding the test repo files from indexing. Adding a v3 marker with explicit `include_paths` ensures ivy-lsp uses `test_repo/` itself as workspace root. Since `os.walk` then starts from `test_repo/` directly, the `"test"` basename exclusion only applies to *child* directories named `test` (there are none), so all `.ivy` files are discovered.

**Note:** `_find_source_files_by_layer()` still applies `_EXCLUDED_DIR_BASENAMES` — the fix works because the workspace root IS the test_repo, not because layers bypass the exclusion.

**Files:**
- Create: `${SERENA}/test/resources/repos/ivy/test_repo/.ivyworkspace`

- [ ] **Step 1: Create the `.ivyworkspace` v3 marker file**

```json
{
  "version": 3,
  "project_type": "standalone",
  "scope_detection": "auto",
  "workspace_layers": [
    {
      "id": "main",
      "include_paths": ["."],
      "priority": 1
    }
  ]
}
```

- [ ] **Step 2: Verify the marker is valid by checking ivy-lsp's schema**

Run from worktree root:
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -c "
from ivy_lsp.core.workspace.detection import _read_marker
import os, json
marker_path = '../panther-serena/test/resources/repos/ivy/test_repo/.ivyworkspace'
data = _read_marker(os.path.abspath(marker_path))
print('Marker parsed OK:', json.dumps(data, indent=2) if data else 'FAILED')
"
```
Expected: Marker parsed OK with version 3 and workspace_layers.

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena
git add test/resources/repos/ivy/test_repo/.ivyworkspace
git commit -m "fix: add .ivyworkspace v3 marker to Ivy test repo

Ensures ivy-lsp uses the test_repo directory as workspace root
instead of walking up to a parent where the 'test/' path component
would match _EXCLUDED_DIR_BASENAMES and exclude the test files."
```

---

### Task 2: Pass `IVY_LSP_WORKSPACE` and forward workspace env vars from Serena

**Context:** `IvyLanguageServer.DependencyProvider.create_launch_command_env()` (line 106-118 of `ivy_language_server.py`) only forwards `IVY_LSP_INCLUDE_PATHS` and `IVY_LSP_EXCLUDE_PATHS`. It never sets `IVY_LSP_WORKSPACE`, so ivy-lsp must guess the workspace root from the `rootUri` in LSP init params. The `DependencyProvider` inner class also has no access to `repository_root_path`.

The base class `LanguageServerDependencyProvider.__init__` (ls.py:272) takes `(self, custom_settings, ls_resources_dir)`.

**Note:** Line numbers reference the **pre-modification** source. Steps within this task must be applied sequentially — earlier steps shift line numbers for later steps.

**Files:**
- Modify: `${SERENA}/src/solidlsp/language_servers/ivy_language_server.py`

- [ ] **Step 1: Add `ivy_workspace` parameter to `DependencyProvider.__init__`**

In the `DependencyProvider` inner class, add an `__init__` that accepts and stores `ivy_workspace`:

```python
class DependencyProvider(LanguageServerDependencyProviderSinglePath):
    """Discovers ivy_lsp on PATH and constructs the launch command."""

    def __init__(
        self,
        custom_settings: "SolidLSPSettings.CustomLSSettings",
        ls_resources_dir: str,
        ivy_workspace: str | None = None,
    ):
        super().__init__(custom_settings, ls_resources_dir)
        self._ivy_workspace = ivy_workspace
```

This replaces the current class that has no `__init__` (inherits from parent).

- [ ] **Step 2: Update `_create_dependency_provider` to pass `repository_root_path`**

Change line 75-76 from:
```python
def _create_dependency_provider(self) -> LanguageServerDependencyProvider:
    return self.DependencyProvider(self._custom_settings, self._ls_resources_dir)
```

To:
```python
def _create_dependency_provider(self) -> LanguageServerDependencyProvider:
    return self.DependencyProvider(
        self._custom_settings,
        self._ls_resources_dir,
        ivy_workspace=self.repository_root_path,
    )
```

- [ ] **Step 3: Update `create_launch_command_env` to set and forward workspace vars**

Replace the current `create_launch_command_env` method (lines 106-118) with:

```python
def create_launch_command_env(self) -> dict[str, str]:
    """Provide environment variables for the ivy_lsp process.

    Sets ``IVY_LSP_WORKSPACE`` to the repository root path so ivy-lsp
    uses it as the workspace root. Also forwards include/exclude paths
    and any explicit workspace env var overrides from the current
    environment.
    """
    include_paths = os.environ.get("IVY_LSP_INCLUDE_PATHS", "")
    exclude_paths = os.environ.get("IVY_LSP_EXCLUDE_PATHS", "submodules,test")
    env: dict[str, str] = {
        "IVY_LSP_INCLUDE_PATHS": include_paths,
        "IVY_LSP_EXCLUDE_PATHS": exclude_paths,
    }
    # Set workspace to repository root path (programmatic default)
    if self._ivy_workspace:
        env["IVY_LSP_WORKSPACE"] = self._ivy_workspace
    # Caller's environment variables take precedence over programmatic defaults
    for var in ("IVY_LSP_WORKSPACE", "IVY_WORKSPACE_ROOT", "IVY_LSP_WORKSPACE_HINT"):
        val = os.environ.get(var)
        if val:
            env[var] = val
    return env
```

- [ ] **Step 4: Run format and type-check**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena
uv run poe format
uv run poe type-check
```
Expected: No formatting changes needed (or auto-fixed). Type-check passes.

- [ ] **Step 5: Run Ivy tests**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena
uv run poe test -m ivy
```
Expected: All Ivy tests pass (test_ls_is_running, test_find_document_symbols, test_find_workspace_symbols, test_find_definition_across_files, test_find_references_within_file). Some may skip if `ivy.ivy_parser` is not installed.

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena
git add src/solidlsp/language_servers/ivy_language_server.py
git commit -m "fix: pass IVY_LSP_WORKSPACE from repository_root_path to ivy-lsp

DependencyProvider now receives repository_root_path and sets
IVY_LSP_WORKSPACE env var when spawning ivy-lsp. Also forwards
IVY_WORKSPACE_ROOT and IVY_LSP_WORKSPACE_HINT if set in the
environment. Explicit env vars take precedence over the default."
```

---

### Task 3: Canonicalize paths in ivy-lsp workspace detection

**Context:** `_resolve_git_worktree()` (detection.py:177-224) uses `os.path.abspath()` and `os.path.normpath()` but never `os.path.realpath()`. When the start directory or resolved main tree root contains symlinks, the resulting workspace root differs from the canonical path used by the MCP bridge for port file hash computation, causing bridge activation failures.

Similarly, `detect_ivy_workspace()` (detection.py:321-448) uses `os.path.abspath()` at its entry points (lines 350 and 378) without resolving symlinks.

**Files:**
- Modify: `${IVY_LSP}/ivy_lsp/core/workspace/detection.py`

- [ ] **Step 1: Canonicalize `current` in `_resolve_git_worktree`**

Line 187, change:
```python
current = os.path.abspath(start_dir)
```
to:
```python
current = os.path.realpath(os.path.abspath(start_dir))
```

- [ ] **Step 2: Canonicalize `main_root` in `_resolve_git_worktree`**

After line 207 (`main_root = os.path.dirname(commondir)`), add canonicalization:
```python
main_root = os.path.dirname(commondir)
main_root = os.path.realpath(main_root)
```

- [ ] **Step 3: Canonicalize explicit workspace in `detect_ivy_workspace`**

Line 350, change:
```python
ws = os.path.abspath(ws)
```
to:
```python
ws = os.path.realpath(os.path.abspath(ws))
```

- [ ] **Step 4: Canonicalize start_dir in `detect_ivy_workspace`**

Line 378, change:
```python
abs_start = os.path.abspath(start_dir)
```
to:
```python
abs_start = os.path.realpath(os.path.abspath(start_dir))
```

- [ ] **Step 5: Add symlink canonicalization test**

Add to `${IVY_LSP}/tests/test_workspace_detection.py`:

```python
def test_detect_ivy_workspace_resolves_symlinks(tmp_path):
    """Verify detect_ivy_workspace returns canonical path when given a symlink."""
    real_dir = tmp_path / "real_workspace"
    real_dir.mkdir()
    (real_dir / ".ivyworkspace").write_text(json.dumps({
        "version": 3,
        "workspace_layers": [{"id": "main", "include_paths": ["."], "priority": 1}],
    }))
    link = tmp_path / "symlink_workspace"
    link.symlink_to(real_dir)

    config = detect_ivy_workspace(str(link))
    assert config.workspace_root == str(real_dir.resolve()), (
        f"Expected canonical path {real_dir.resolve()}, got {config.workspace_root}"
    )
```

- [ ] **Step 6: Run ivy-lsp workspace detection tests**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_workspace_detection.py -v
```
Expected: All tests pass, including the new symlink test. The `os.path.realpath()` is a superset of `os.path.abspath()` for non-symlink paths, so no behavior change for existing tests.

- [ ] **Step 7: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/workspace/detection.py
git commit -m "fix: canonicalize paths in workspace detection with os.path.realpath

Resolves symlinks in _resolve_git_worktree() return values and
detect_ivy_workspace() entry points. Prevents MCP bridge port
file hash mismatches when workspace paths contain symlinks."
```

---

### Task 4: End-to-end verification

- [ ] **Step 1: Run full Serena test suite (non-ivy markers too)**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena
uv run poe test -m "python or go"
```
Expected: Existing tests still pass (no regressions from DependencyProvider changes).

- [ ] **Step 2: Run ivy-lsp full test suite**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/ -v --timeout=60
```
Expected: All tests pass, including workspace detection tests.

- [ ] **Step 3: Verify env var passthrough manually**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena
python -c "
from solidlsp.language_servers.ivy_language_server import IvyLanguageServer
# Verify DependencyProvider accepts ivy_workspace
dp = IvyLanguageServer.DependencyProvider({}, '/tmp', ivy_workspace='/test/root')
env = dp.create_launch_command_env()
assert 'IVY_LSP_WORKSPACE' in env, f'Missing IVY_LSP_WORKSPACE in {env}'
assert env['IVY_LSP_WORKSPACE'] == '/test/root', f'Wrong value: {env[\"IVY_LSP_WORKSPACE\"]}'
print('OK: IVY_LSP_WORKSPACE correctly set to', env['IVY_LSP_WORKSPACE'])
"
```
Expected: `OK: IVY_LSP_WORKSPACE correctly set to /test/root`

---

### Task 5: Update submodule pointers in parent repo

- [ ] **Step 1: Update panther-serena submodule pointer**

```bash
cd .  # worktree root
git add panther/plugins/services/testers/panther_ivy/submodules/panther-serena
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git commit -m "chore: update panther-serena and ivy-lsp submodules

panther-serena: .ivyworkspace marker + IVY_LSP_WORKSPACE passthrough
ivy-lsp: path canonicalization in workspace detection"
```

---

## Deferred (separate PR/task)

These are documented but NOT part of this plan:

- **Per-language workspace roots** in `LanguageServerFactory` (`ls_manager.py`) — cleaner architecture but Task 2 already solves the immediate problem via env var
- **Workspace re-detection** (`ivy/redetect-workspace` command) — for multi-protocol switching without server restart
- **File watcher** (`workspace/didChangeWatchedFiles`) — for external file change detection
- **Remove `"test"` from `_EXCLUDED_DIR_BASENAMES`** — still relevant because `_find_source_files_by_layer()` still applies it; any `.ivy` files in a subdirectory named `test/` within a layer's include path would be excluded
