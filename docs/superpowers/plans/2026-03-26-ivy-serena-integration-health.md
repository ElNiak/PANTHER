# Ivy-LSP Serena Integration + /nct-serena-health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the IvyLanguageServer integration in panther-serena to follow the official language support guide, and create a `/nct-serena-health` plugin command to validate the full Serena integration chain.

**Architecture:** Two repos modified: panther-serena (DependencyProvider refactor, test repo restructure, LSP tests, docs) and panther-ivy-plugin (new slash command). The IvyLanguageServer refactor follows the `LanguageServerDependencyProviderSinglePath` pattern used by PyrightServer. The health command follows the existing `/nct-health` verify-as-you-go pattern.

**Tech Stack:** Python 3.11+, SolidLSP framework, pytest, Click (PANTHER CLI), Claude Code plugin commands (Markdown + YAML frontmatter)

---

## File Structure

### panther-serena (modify) — base: `panther/plugins/services/testers/panther_ivy/submodules/panther-serena/`

| File | Responsibility |
|------|---------------|
| `src/solidlsp/language_servers/ivy_language_server.py` | Refactor to DependencyProvider pattern |
| `test/resources/repos/ivy/test_repo/sample.ivy` | Move from `ivy/` + keep content |
| `test/resources/repos/ivy/test_repo/helper.ivy` | Move from `ivy/` + enrich for reference testing |
| `test/conftest.py` | Add ivy_lsp PATH check to disabled languages |
| `test/solidlsp/ivy/test_ivy_basic.py` | New: basic LSP tests (symbols, definition, references) |
| `README.md` | Add Ivy to supported languages list |
| `docs/01-about/020_programming-languages.md` | Add Ivy entry |
| `CHANGELOG.md` | Add Ivy changelog entry |

### panther-ivy-plugin (create) — base: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

| File | Responsibility |
|------|---------------|
| `commands/nct-serena-health.md` | New: 11-check health command for Serena integration chain |

### Reference files (read-only)

| File | Why |
|------|-----|
| `panther-serena/src/solidlsp/language_servers/pyright_server.py` | DependencyProvider pattern to follow |
| `panther-serena/src/solidlsp/ls.py:266-340,547-551` | Base classes: `LanguageServerDependencyProvider`, `SinglePath`, `_create_process_launch_info` |
| `panther-serena/test/solidlsp/php/test_php_basic.py` | Test suite pattern to replicate |
| `panther-serena/test/conftest.py:216-251` | Disabled languages pattern (ccls, clangd, php) |
| `panther-ivy-plugin/commands/nct-health.md` | Health command pattern to follow |

---

## Task 1: Restructure Test Repository

**Files:**
- Move: `test/resources/repos/ivy/sample.ivy` -> `test/resources/repos/ivy/test_repo/sample.ivy`
- Move: `test/resources/repos/ivy/helper.ivy` -> `test/resources/repos/ivy/test_repo/helper.ivy`
- Modify: `test/resources/repos/ivy/test_repo/helper.ivy` (enrich content)

Working directory: `panther/plugins/services/testers/panther_ivy/submodules/panther-serena/`

- [ ] **Step 1: Create test_repo directory and move files**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/
mkdir -p test/resources/repos/ivy/test_repo
mv test/resources/repos/ivy/sample.ivy test/resources/repos/ivy/test_repo/sample.ivy
mv test/resources/repos/ivy/helper.ivy test/resources/repos/ivy/test_repo/helper.ivy
```

- [ ] **Step 2: Verify sample.ivy content is intact**

Run: `cat test/resources/repos/ivy/test_repo/sample.ivy`
Expected: Original content with `#lang ivy1.7`, `include helper`, `object protocol`

- [ ] **Step 3: Enrich helper.ivy for cross-file testing**

Replace `test/resources/repos/ivy/test_repo/helper.ivy` with:

```ivy
#lang ivy1.7

object helper = {
    type id
    action get_id : id
    relation active(X: id)

    after init {
        active(X) := false
    }

    action activate(x: id) = {
        active(x) := true
    }
}
```

This adds `relation active` and `action activate` for within-file reference testing.

- [ ] **Step 4: Verify old directory has no leftover .ivy files**

Run: `ls test/resources/repos/ivy/`
Expected: Only `test_repo/` directory, no `.ivy` files at top level

- [ ] **Step 5: Commit**

```bash
git add test/resources/repos/ivy/
git commit -m "refactor: move ivy test repo to test_repo/ subdirectory

Serena's conftest.py:get_repo_path() expects test files at
test/resources/repos/<language>/test_repo/. Also enriches
helper.ivy with relation and action for reference testing."
```

---

## Task 2: Refactor IvyLanguageServer to DependencyProvider Pattern

**Files:**
- Modify: `src/solidlsp/language_servers/ivy_language_server.py`
- Reference: `src/solidlsp/language_servers/pyright_server.py`

- [ ] **Step 1: Read reference implementation**

Read `src/solidlsp/language_servers/pyright_server.py` lines 1-55 to understand the DependencyProvider pattern:
- `super().__init__(config, repository_root_path, None, "python", solidlsp_settings)` — `None` for process_launch_info
- `_create_dependency_provider()` returns inner class instance
- Inner `DependencyProvider(LanguageServerDependencyProviderSinglePath)` with `_get_or_install_core_dependency()` and `_create_launch_command()`

- [ ] **Step 2: Refactor ivy_language_server.py**

Replace the full file content of `src/solidlsp/language_servers/ivy_language_server.py` with:

```python
"""Ivy language server integration for the SolidLSP framework."""

import logging
import os
import pathlib
import shutil
import threading

from solidlsp.ls import LanguageServerDependencyProvider, LanguageServerDependencyProviderSinglePath, SolidLanguageServer
from solidlsp.ls_config import LanguageServerConfig
from solidlsp.lsp_protocol_handler.lsp_types import InitializeParams
from solidlsp.settings import SolidLSPSettings

log = logging.getLogger(__name__)


class IvyLanguageServer(SolidLanguageServer):
    """
    Provides Ivy specific instantiation of the LanguageServer class using ivy_lsp.
    Ivy is a formal verification language used for protocol modeling and verification.
    """

    def __init__(
        self,
        config: LanguageServerConfig,
        repository_root_path: str,
        solidlsp_settings: SolidLSPSettings,
    ):
        """
        Creates an IvyLanguageServer instance. This class is not meant to be
        instantiated directly. Use LanguageServer.create() instead.
        """
        self._diagnostics_store: dict[str, list[dict[str, object]]] = {}
        self._diagnostics_lock = threading.Lock()

        super().__init__(
            config,
            repository_root_path,
            None,
            "ivy",
            solidlsp_settings,
        )

    def _create_dependency_provider(self) -> LanguageServerDependencyProvider:
        return self.DependencyProvider(self._custom_settings, self._ls_resources_dir)

    class DependencyProvider(LanguageServerDependencyProviderSinglePath):
        """Discovers ivy_lsp on PATH and constructs the launch command."""

        def _get_or_install_core_dependency(self) -> str:
            """
            Locate the ivy_lsp executable on the system PATH.

            Unlike most other language servers in Serena, ivy_lsp is not
            auto-downloaded. It must be installed separately (typically via
            pip install from the ivy-lsp package).

            :return: path to the ivy_lsp executable
            :raises FileNotFoundError: if ivy_lsp is not found on PATH
            """
            ivy_lsp_path = shutil.which("ivy_lsp")
            if ivy_lsp_path is None:
                raise FileNotFoundError(
                    "ivy_lsp is not installed or is not in PATH.\n"
                    "Install it via: pip install ivy-lsp\n"
                    "Or from the panther_ivy package: pip install -e '.[lsp]'\n"
                    "After installation, make sure 'ivy_lsp' is available on your PATH."
                )
            log.info(f"Found ivy_lsp at: {ivy_lsp_path}")
            return ivy_lsp_path

        def _create_launch_command(self, core_path: str) -> list[str]:
            return [core_path]

        def create_launch_command_env(self) -> dict[str, str]:
            env: dict[str, str] = {}
            include_paths = os.environ.get("IVY_LSP_INCLUDE_PATHS", "")
            exclude_paths = os.environ.get("IVY_LSP_EXCLUDE_PATHS", "submodules,test")
            if include_paths:
                env["IVY_LSP_INCLUDE_PATHS"] = include_paths
            if exclude_paths:
                env["IVY_LSP_EXCLUDE_PATHS"] = exclude_paths
            return env

    def send_custom_request(self, method: str, params: dict | None = None) -> dict:
        """Send a custom LSP request (e.g., ivy/verify) to the ivy-lsp server.

        :param method: the custom method name, e.g. "ivy/verify", "ivy/serverStatus"
        :param params: optional parameters dict for the request
        :return: the server's response payload as a dict
        :raises SolidLSPException: if the request returns an error
        :raises RuntimeError: if the server is not started
        """
        if not self.server_started:
            raise RuntimeError("Ivy language server is not started. Cannot send custom request.")
        result = self.server.send_request(method, params)
        if isinstance(result, dict):
            return result
        # send_request may return other PayloadLike types; coerce to dict
        if isinstance(result, list):
            return {"results": result}
        if isinstance(result, bool):
            return {"success": result}
        return {}

    def get_stored_diagnostics(self, uri: str) -> list[dict[str, object]]:
        """Return stored diagnostics for the given URI, or empty list (defensive copy)."""
        with self._diagnostics_lock:
            return list(self._diagnostics_store.get(uri, []))

    def get_all_stored_diagnostics(self) -> dict[str, list[dict[str, object]]]:
        """Return all stored diagnostics keyed by URI (defensive copy)."""
        with self._diagnostics_lock:
            return {uri: list(diags) for uri, diags in self._diagnostics_store.items()}

    @staticmethod
    def _get_initialize_params(repository_absolute_path: str) -> InitializeParams:
        """
        Returns the initialize params for the Ivy Language Server.
        """
        root_uri = pathlib.Path(repository_absolute_path).as_uri()
        initialize_params = {
            "locale": "en",
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "didSave": True,
                        "dynamicRegistration": True,
                    },
                    "completion": {
                        "dynamicRegistration": True,
                        "completionItem": {"snippetSupport": True},
                    },
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "documentSymbol": {
                        "dynamicRegistration": True,
                        "hierarchicalDocumentSymbolSupport": True,
                        "symbolKind": {"valueSet": list(range(1, 27))},
                    },
                    "hover": {
                        "dynamicRegistration": True,
                        "contentFormat": ["markdown", "plaintext"],
                    },
                },
                "workspace": {
                    "workspaceFolders": True,
                    "didChangeConfiguration": {"dynamicRegistration": True},
                    "symbol": {"dynamicRegistration": True},
                },
            },
            "processId": os.getpid(),
            "rootPath": repository_absolute_path,
            "rootUri": root_uri,
            "workspaceFolders": [
                {
                    "uri": root_uri,
                    "name": os.path.basename(repository_absolute_path),
                }
            ],
        }
        return initialize_params

    def _start_server(self) -> None:
        """
        Starts the Ivy Language Server and waits for it to be ready.
        """

        def register_capability_handler(params):
            log.debug("ivy_lsp requested client/registerCapability: %s", params)
            return

        def window_log_message(msg):
            log.info(f"LSP: window/logMessage: {msg}")

        def do_nothing(params):
            return

        def store_diagnostics(params):
            """Capture publishDiagnostics notifications for later querying."""
            if not isinstance(params, dict):
                log.warning(
                    "Received non-dict publishDiagnostics params (type=%s), ignoring.",
                    type(params).__name__,
                )
                return
            uri = params.get("uri", "")
            if not uri:
                log.warning("Received publishDiagnostics with empty URI, ignoring.")
                return
            diags = params.get("diagnostics", [])
            with self._diagnostics_lock:
                self._diagnostics_store[uri] = diags
            log.debug(f"Stored {len(diags)} diagnostics for {uri}")

        self.server.on_request("client/registerCapability", register_capability_handler)
        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_notification("$/progress", do_nothing)
        self.server.on_notification("textDocument/publishDiagnostics", store_diagnostics)

        log.info("Starting ivy_lsp server process")
        self.server.start()
        initialize_params = self._get_initialize_params(self.repository_root_path)

        log.info("Sending initialize request from LSP client to ivy_lsp server and awaiting response")
        init_response = self.server.send.initialize(initialize_params)
        log.debug(f"Received initialize response from ivy_lsp server: {init_response}")

        capabilities = init_response.get("capabilities", {})
        if "textDocumentSync" not in capabilities:
            raise RuntimeError(
                "ivy_lsp did not report textDocumentSync capability. " "Check that ivy_lsp is correctly installed and up to date."
            )

        for cap_name in [
            "completionProvider",
            "definitionProvider",
            "referencesProvider",
            "documentSymbolProvider",
            "workspaceSymbolProvider",
            "hoverProvider",
        ]:
            if cap_name in capabilities:
                log.info(f"ivy_lsp supports {cap_name}")
            else:
                log.warning(f"ivy_lsp does not report {cap_name}")

        self.server.notify.initialized({})
        log.info("Ivy language server initialization complete")
```

Key changes from original:
- `super().__init__()` passes `None` instead of `ProcessLaunchInfo`
- New `_create_dependency_provider()` method
- New inner `DependencyProvider` class with `_get_or_install_core_dependency`, `_create_launch_command`, `create_launch_command_env`
- Removed `_find_ivy_lsp()` static method (logic moved to `_get_or_install_core_dependency`)
- Removed `ProcessLaunchInfo` import
- Added `LanguageServerDependencyProvider`, `LanguageServerDependencyProviderSinglePath` imports

- [ ] **Step 3: Verify the refactored class can be imported**

Run:
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/
python -c "
from solidlsp.language_servers.ivy_language_server import IvyLanguageServer
assert hasattr(IvyLanguageServer, '_create_dependency_provider'), 'Missing _create_dependency_provider'
assert hasattr(IvyLanguageServer, 'DependencyProvider'), 'Missing DependencyProvider inner class'
print('DependencyProvider pattern: OK')
"
```
Expected: `DependencyProvider pattern: OK`

- [ ] **Step 4: Run type-check**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/ && uv run poe type-check`
Expected: No new type errors in `ivy_language_server.py`

- [ ] **Step 5: Commit**

```bash
git add src/solidlsp/language_servers/ivy_language_server.py
git commit -m "refactor: migrate IvyLanguageServer to DependencyProvider pattern

Follow the adding_new_language_support_guide.md:
- Pass None for process_launch_info, implement _create_dependency_provider()
- Inner DependencyProvider(SinglePath) handles binary discovery + env vars
- Enables ls_path custom setting for user overrides
- Env vars (IVY_LSP_INCLUDE_PATHS, IVY_LSP_EXCLUDE_PATHS) move to
  create_launch_command_env(), matching Kotlin/Pyright pattern"
```

---

## Task 3: Add Conftest Disable + Basic LSP Tests

**Files:**
- Modify: `test/conftest.py:249` (add ivy_lsp check)
- Create: `test/solidlsp/ivy/test_ivy_basic.py`
- Reference: `test/solidlsp/php/test_php_basic.py`

- [ ] **Step 1: Add ivy_lsp PATH check to conftest.py**

In `test/conftest.py`, add before `return result` (after the AL block at line 249):

```python
    # Disable Ivy tests if ivy_lsp is not available
    ivy_tests_enabled = _sh.which("ivy_lsp") is not None
    if not ivy_tests_enabled:
        result.append(Language.IVY)
```

This follows the exact pattern of ccls (line 233), clangd (line 238), php_phpactor (line 243).

- [ ] **Step 2: Create test_ivy_basic.py**

Create `test/solidlsp/ivy/test_ivy_basic.py`:

```python
from pathlib import Path

import pytest

from solidlsp import SolidLanguageServer
from solidlsp.ls_config import Language
from test.conftest import language_tests_enabled


@pytest.mark.skipif(not language_tests_enabled(Language.IVY), reason="ivy_lsp not available")
@pytest.mark.ivy
class TestIvyLanguageServer:
    @pytest.mark.parametrize("language_server", [Language.IVY], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.IVY], indirect=True)
    def test_ls_is_running(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test that the Ivy language server starts and stops successfully."""
        assert language_server.is_running()
        assert Path(language_server.language_server.repository_root_path).resolve() == repo_path.resolve()

    @pytest.mark.parametrize("language_server", [Language.IVY], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.IVY], indirect=True)
    def test_find_symbols(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test that document symbols are returned for an Ivy file."""
        symbols = language_server.request_document_symbols(str(repo_path / "sample.ivy"))
        assert symbols, f"Expected non-empty symbols list but got {symbols=}"
        symbol_names = [s.get("name", "") for s in symbols]
        assert "protocol" in symbol_names, f"Expected 'protocol' symbol in {symbol_names}"

    @pytest.mark.parametrize("language_server", [Language.IVY], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.IVY], indirect=True)
    def test_find_definition_across_files(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test cross-file go-to-definition via include statement."""
        # Line 2 (0-indexed): "include helper" — resolve "helper" to helper.ivy
        definition_location_list = language_server.request_definition(
            str(repo_path / "sample.ivy"), 2, 8
        )
        assert definition_location_list, f"Expected definition locations but got {definition_location_list=}"
        assert any(
            d["uri"].endswith("helper.ivy") for d in definition_location_list
        ), f"Expected a definition in helper.ivy, got {definition_location_list}"

    @pytest.mark.parametrize("language_server", [Language.IVY], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.IVY], indirect=True)
    def test_find_references_within_file(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test that references are found for a type used multiple times."""
        # Line 5 (0-indexed): "type packet" — "packet" is used in send(p: packet), receive(p: packet)
        refs = language_server.request_references(str(repo_path / "sample.ivy"), 5, 9)
        assert len(refs) >= 2, f"Expected >=2 references for 'packet', got {len(refs)}: {refs}"
```

**Note**: Line/character positions (line 2 char 8 for "helper", line 5 char 9 for "packet") are estimates based on 0-indexed counting of the test repo content. They must be verified empirically by running the tests once. If the Ivy LSP uses different offsets, adjust accordingly.

- [ ] **Step 3: Run ivy tests (if ivy_lsp is on PATH)**

Run:
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/
uv run poe test -m ivy -v
```
Expected: If ivy_lsp is on PATH, tests run. If line/character positions are wrong, adjust them based on actual LSP output. If ivy_lsp is not on PATH, tests are skipped.

- [ ] **Step 4: Run the existing ivy unit tests to verify no regression**

Run:
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/
uv run poe test -k "test_ivy_tools_unit" -v
```
Expected: All existing `test_ivy_tools_unit.py` tests PASS.

- [ ] **Step 5: Commit**

```bash
git add test/conftest.py test/solidlsp/ivy/test_ivy_basic.py
git commit -m "test: add basic LSP tests for Ivy language server

- Add ivy_lsp PATH check to _determine_disabled_languages() in conftest
- Create test_ivy_basic.py with: ls_is_running, find_symbols,
  find_definition_across_files, find_references_within_file
- Tests skip gracefully when ivy_lsp is not installed"
```

---

## Task 4: Update Documentation

**Files:**
- Modify: `README.md:85`
- Modify: `docs/01-about/020_programming-languages.md` (between Haskell and Java)
- Modify: `CHANGELOG.md:1-5`

- [ ] **Step 1: Add Ivy to README.md supported languages list**

On line 85 of `README.md`, the alphabetical language list reads:
```
...Haskell, Java, Javascript,...
```

Insert `Ivy,` between `Haskell,` and `Java,`:
```
...Haskell, Ivy, Java, Javascript,...
```

- [ ] **Step 2: Add Ivy entry to docs/01-about/020_programming-languages.md**

Insert between the Haskell entry (line 56) and the Java entry (line 57):

```markdown
* **Ivy**
  (formal verification language for protocol modeling; requires installation of `ivy-lsp`: `pip install ivy-lsp`)
```

- [ ] **Step 3: Add Ivy to CHANGELOG.md**

Under the `# latest` section, add a new bullet under `* General:`:

```markdown
    * Add support for Ivy formal verification language via ivy_lsp
```

- [ ] **Step 4: Verify documentation updates**

Run:
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/
grep -n "Ivy" README.md
grep -n "Ivy" docs/01-about/020_programming-languages.md
grep -n -i "ivy" CHANGELOG.md
```
Expected: Ivy appears in all three files.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/01-about/020_programming-languages.md CHANGELOG.md
git commit -m "docs: add Ivy to supported languages

- README.md: add to alphabetical language list
- 020_programming-languages.md: add entry with install instructions
- CHANGELOG.md: add changelog entry under latest"
```

---

## Task 5: Create /nct-serena-health Command

**Files:**
- Create: `commands/nct-serena-health.md` (in panther-ivy-plugin)
- Reference: `commands/nct-health.md` (existing health command pattern)

Working directory: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

- [ ] **Step 1: Read existing /nct-health command for pattern**

Read `commands/nct-health.md` to understand the structure: YAML frontmatter, execution model (sequential verify-as-you-go), layer organization, result format, interaction protocol.

- [ ] **Step 2: Create nct-serena-health.md**

Create `commands/nct-serena-health.md`:

```markdown
---
name: nct-serena-health
description: Validate the Serena integration chain (serena-mcp-server -> SolidLSP -> IvyLanguageServer -> ivy_lsp)
arguments: []
---
<!-- MODE: FAST — Diagnostic health check, no orchestrator required -->

Validate the full Serena integration layer end-to-end, from package installation through SolidLSP framework to IvyLanguageServer and the ivy_lsp binary.

## Instructions

Run the following 11 checks organized in 3 layers. Execution is **strictly sequential with interleaved verification** (verify-as-you-go).

### Execution Model

**Every step follows this 3-phase cycle:**
1. **Call** — invoke one tool (Bash or Serena MCP)
2. **Verify** — immediately verify the result using classical tools (Read, Grep, Glob, Bash). Do NOT proceed until verification is complete.
3. **Record** — log PASS/WARN/FAIL with verification evidence, then proceed to the next step.

**Do NOT batch multiple tool calls in a single message.** Each step must complete before starting the next.

**Gate rule**: If ALL of Steps 1-4 FAIL → abort with "Serena stack is not installed." Individual Layer 1 failures do NOT gate — continue collecting diagnostics.

---

## Layer 1: Prerequisites — "Is the Serena stack installed?"

### Step 1: serena-mcp-server binary

Run via Bash:
```
which serena-mcp-server
```

Classification:
- **PASS**: Binary found. Report the path.
- **FAIL**: "serena-mcp-server not found on PATH."

### Step 2: Serena package import

Run via Bash:
```
python3 -c "import serena; print(f'serena {serena.__version__}')" 2>&1
```

Classification:
- **PASS**: Import succeeds. Report the version.
- **FAIL**: "Serena package not importable." Report the error.

### Step 3: SolidLSP framework + Language.IVY

Run via Bash:
```
python3 -c "from solidlsp.ls_config import Language; print(f'Language.IVY = {Language.IVY}')" 2>&1
```

Classification:
- **PASS**: Prints `Language.IVY = ivy`. The Ivy enum is registered.
- **FAIL**: "SolidLSP not importable or Language.IVY not in enum."

### Step 4: IvyLanguageServer class loadable

Run via Bash:
```
python3 -c "from solidlsp.language_servers.ivy_language_server import IvyLanguageServer; print('IvyLanguageServer: OK')" 2>&1
```

Classification:
- **PASS**: Import succeeds.
- **FAIL**: "IvyLanguageServer not importable." Report the error.

### Step 5: DependencyProvider pattern

Run via Bash:
```
python3 -c "
from solidlsp.language_servers.ivy_language_server import IvyLanguageServer
has_provider = hasattr(IvyLanguageServer, '_create_dependency_provider')
has_inner = hasattr(IvyLanguageServer, 'DependencyProvider')
print(f'_create_dependency_provider: {has_provider}')
print(f'DependencyProvider inner class: {has_inner}')
if has_provider and has_inner:
    print('RESULT: DependencyProvider pattern OK')
else:
    print('RESULT: DependencyProvider pattern MISSING')
" 2>&1
```

Classification:
- **PASS**: Both `_create_dependency_provider` method and `DependencyProvider` inner class exist.
- **WARN**: One or both are missing. "IvyLanguageServer does not follow the DependencyProvider pattern. See adding_new_language_support_guide.md."

### Step 6: ivy_lsp binary

Run via Bash:
```
which ivy_lsp && ivy_lsp --version 2>&1 || echo "ivy_lsp not found"
```

Classification:
- **PASS**: Binary found. Report path and version.
- **FAIL**: "ivy_lsp not found on PATH. Install via: pip install ivy-lsp"

---

## Layer 2: Configuration — "Is it correctly configured?"

### Step 7: Serena project config

Use `Glob` to find `.serena/project.yml` at the workspace root (the panther_ivy directory). Then use `Read` to inspect it.

Check:
1. File exists and is valid YAML
2. Note what languages are listed (informational — ivy is NOT required here since project.yml configures the Serena project itself, not Ivy workspaces)

Classification:
- **PASS**: project.yml exists and is valid. Report configured languages.
- **WARN**: ivy not in languages list. "This is expected — project.yml configures Serena's own codebase, not the Ivy workspace."
- **FAIL**: "project.yml not found or unparseable."

---

## Layer 3: Integration — "Does the full chain work?"

### Step 8: Serena MCP server alive

Call `mcp__plugin_panther-ivy-plugin_serena__get_current_config` with no arguments.

Classification:
- **PASS**: Returns config JSON with project information. Report project name and active tools count.
- **FAIL**: "Serena MCP server not responding." Report the error.

### Step 9: Serena tool registry

From the config result in Step 8, inspect the active tools list. Look for tools containing "ivy" in their names (e.g., `ivy_diagnostics`, `ivy_goto_definition`, `ivy_server_status`, `ivy_test_scope`).

**Classical verify**: Run via Bash:
```
python3 -c "
from serena.tools.ivy_tools import IvyDiagnosticsTool, IvyGotoDefinitionTool, IvyServerStatusTool, IvyTestScopeTool
print('Ivy tools importable: 4 classes')
" 2>&1
```

Classification:
- **PASS**: Ivy tools found in registry AND importable. Report tool names.
- **WARN**: Tools importable but not in active registry. "Ivy tools are defined but may be disabled (ToolMarkerOptional). Add them to included_optional_tools in project.yml to enable."
- **FAIL**: "Ivy tools not importable." Report the error.

### Step 10: LSP handshake through Serena

Call `mcp__plugin_panther-ivy-plugin_serena__get_symbols_overview` with:
- `relative_path`: path to an `.ivy` file in the workspace (use `Glob` to find one first, e.g. `**/sample.ivy` or `**/quic_types.ivy`)

**Classical verify**: Compare the returned symbols with what you'd expect from the file content (use `Read` to check the file).

Classification:
- **PASS**: Returns symbols. Report symbol count and file.
- **WARN**: Empty symbols returned. "Language server may not have indexed the file yet. Try restarting."
- **FAIL**: "Serena could not retrieve symbols via LSP." Report the error.

### Step 11: Cross-validate with /nct-health

Check if `/nct-health` was run earlier in this session (look for its result table in the conversation).

If found:
- Compare LSP process status (nct-health Step 1) with Serena's view (this command Step 10)
- Compare ivy_lsp binary path from nct-health with Step 6 here

Classification:
- **PASS**: Results are consistent, or /nct-health was not run.
- **WARN**: Inconsistency detected. Detail the mismatch.

---

## Result Presentation

Present the final results in this format:

```
## Serena Integration Health Check

### Layer 1: Prerequisites
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 1 | serena-mcp-server binary  | PASS   | /path/to/serena-mcp-server           |
| 2 | Serena package import     | PASS   | serena 1.2.3                         |
| 3 | SolidLSP + Language.IVY   | PASS   | Language.IVY = ivy                   |
| 4 | IvyLanguageServer class   | PASS   | Import OK                            |
| 5 | DependencyProvider pattern| PASS   | Both attrs present                   |
| 6 | ivy_lsp binary            | PASS   | /path/to/ivy_lsp (v0.11.1)          |

### Layer 2: Configuration
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 7 | Serena project config     | PASS   | languages: python, typescript        |

### Layer 3: Integration
| # | Check                     | Status | Details                              |
|---|---------------------------|--------|--------------------------------------|
| 8 | Serena MCP server alive   | PASS   | project: serena, 24 tools active     |
| 9 | Serena tool registry      | PASS   | 4 ivy tools importable               |
|10 | LSP handshake via Serena  | PASS   | 5 symbols in sample.ivy              |
|11 | Cross-validate /nct-health| PASS   | /nct-health not run (skipped)        |

**Overall: 11/11 PASS**
```

### Interactive Follow-up

After presenting the result table, engage the user. Reference the `interaction-patterns` skill for checkpoint format details.

**If any checks FAIL → Gate**:
- Ask: "Serena health check found {N} failure(s). Which would you like to investigate first?"
- List the failed checks as numbered options.
- Wait for user selection before showing suggested actions.

**If all checks PASS → Inform-and-Continue**:
- State: "Serena integration is healthy. All 11 checks pass. Run `/nct-health` for full LSP + MCP validation?"

**If WARNings present (but no FAILs) → Collaborative**:
- State: "Serena health check passed with {N} warning(s): {list}. Any concern?"

### Suggested Actions

If any checks fail, add a `### Suggested Actions` section:

- If Step 1 fails: "Install Serena: `pip install -e <path-to-panther-serena>` or `uv pip install -e <path>`"
- If Step 2 fails: "Serena package not installed. Run: `pip install -e panther/plugins/services/testers/panther_ivy/submodules/panther-serena/`"
- If Step 3 fails: "SolidLSP not installed or Language.IVY not registered. Reinstall Serena or check ls_config.py."
- If Step 4 fails: "IvyLanguageServer import error. Check for syntax errors or missing dependencies in ivy_language_server.py."
- If Step 5 warns: "IvyLanguageServer does not use the DependencyProvider pattern. See .serena/memories/adding_new_language_support_guide.md."
- If Step 6 fails: "Install ivy-lsp: `pip install ivy-lsp` or `pip install -e <path-to-ivy-lsp>`"
- If Step 7 fails: "Create or fix .serena/project.yml at the workspace root."
- If Step 8 fails: "Serena MCP server not running. Check start-serena.sh and the plugin's .mcp.json configuration."
- If Step 9 warns: "Add ivy tools to included_optional_tools in .serena/project.yml. Or ensure ivy is in the languages list for the target project."
- If Step 10 fails: "Serena cannot retrieve symbols. The IvyLanguageServer may not be starting. Check /tmp/serena-*.log for errors."
- If Step 11 warns: "Inconsistency between /nct-health and /nct-serena-health. Run both again to confirm."

See the `tooling-reference` skill for Serena and LSP architecture details.
```

- [ ] **Step 3: Verify command file has valid frontmatter**

Run:
```bash
head -5 commands/nct-serena-health.md
```
Expected: YAML frontmatter with `name: nct-serena-health`

- [ ] **Step 4: Commit**

```bash
git add commands/nct-serena-health.md
git commit -m "feat: add /nct-serena-health command

11-check health command validating the full Serena integration chain:
- Layer 1: Prerequisites (binary, imports, DependencyProvider pattern)
- Layer 2: Configuration (project.yml)
- Layer 3: Integration (MCP server, tool registry, LSP handshake)
Follows /nct-health verify-as-you-go pattern."
```

---

## Task 6: Final Verification

- [ ] **Step 1: Run format + type-check in panther-serena**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/
uv run poe format && uv run poe type-check
```
Expected: No formatting changes needed, no new type errors.

- [ ] **Step 2: Run all ivy tests**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/
uv run poe test -m ivy -v
```
Expected: All tests PASS (or skip if ivy_lsp not on PATH).

- [ ] **Step 3: Verify DependencyProvider end-to-end**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena/
python -c "
from solidlsp.language_servers.ivy_language_server import IvyLanguageServer
from solidlsp.ls import LanguageServerDependencyProviderSinglePath
# Verify inheritance
assert issubclass(IvyLanguageServer.DependencyProvider, LanguageServerDependencyProviderSinglePath)
# Verify env var method exists
assert hasattr(IvyLanguageServer.DependencyProvider, 'create_launch_command_env')
print('Full DependencyProvider verification: OK')
"
```
Expected: `Full DependencyProvider verification: OK`

- [ ] **Step 4: Test /nct-serena-health command manually**

In a Claude Code session with the panther-ivy-plugin active, run `/nct-serena-health` and verify the 11-check table is produced.
