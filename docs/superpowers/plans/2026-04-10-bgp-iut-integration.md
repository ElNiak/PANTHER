# BGP IUT Integration & ivy_compile Native Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `ivy_compile` MCP tool for native compilation, then create PANTHER BGP integration so `panther run` can test BGP Ivy models against FRRouting.

**Architecture:** Two independent pieces. Piece 1 fixes three bugs in the ivy-lsp MCP server (broken guard, missing Z3 paths, missing file staging). Piece 2 creates PANTHER plugin infrastructure for BGP (protocol registration, FRRouting IUT plugin, Ivy tester BGP support) plus an experiment config. An MCP wrapper tool (`ivy_iut_test`) sits on top.

**Tech Stack:** Python 3.10+, Pydantic, Jinja2, Docker, asyncio subprocess, MCP (FastMCP)

**Spec:** `docs/superpowers/specs/2026-04-10-bgp-iut-integration-design.md`

---

## File Map

### Piece 1: ivy_compile native fix (ivy-lsp codebase)

All paths relative to `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

| File | Action | Responsibility |
|------|--------|---------------|
| `ivy_lsp/core/environment.py` | Create | Z3 detection (`detect_z3_dir()`) |
| `ivy_lsp/core/verification.py` | Modify | Inject Z3DIR env, add workspace staging |
| `ivy_lsp/mcp/tools/verification.py` | Modify | Fix guard check at line 250 |
| `tests/core/test_environment.py` | Create | Tests for Z3 detection |
| `tests/core/test_compile_staging.py` | Create | Tests for staging + Z3DIR injection |

### Piece 2: PANTHER BGP integration (PANTHER codebase)

All paths relative to project root.

| File | Action | Responsibility |
|------|--------|---------------|
| `panther/plugins/protocols/client_server/bgp/__init__.py` | Create | Package marker |
| `panther/plugins/protocols/client_server/bgp/bgp.py` | Create | BGP protocol registration |
| `panther/plugins/services/iut/bgp/__init__.py` | Create | Package marker |
| `panther/plugins/services/iut/bgp/frr_bgp/__init__.py` | Create | Package marker |
| `panther/plugins/services/iut/bgp/frr_bgp/frr_bgp.py` | Create | FRRouting service manager |
| `panther/plugins/services/iut/bgp/frr_bgp/config_schema.py` | Create | Pydantic config model |
| `panther/plugins/services/iut/bgp/frr_bgp/Dockerfile` | Create | FRR Docker image |
| `panther/plugins/services/iut/bgp/frr_bgp/version_configs/rfc4271.yaml` | Create | FRR runtime parameters |
| `panther/plugins/services/iut/bgp/frr_bgp/templates/server_command.jinja` | Create | bgpd startup command |
| `panther/plugins/services/iut/bgp/frr_bgp/templates/bgpd.conf.jinja` | Create | FRR config template |
| `panther/plugins/services/testers/panther_ivy/panther_ivy.py` | Modify | Add "bgp" to supported_protocols |
| `panther/plugins/services/testers/panther_ivy/ivy_network_resolution_mixin.py` | Modify | Add hex IP format specifier |
| `panther/plugins/services/testers/panther_ivy/version_configs/bgp/rfc4271.yaml` | Create | Ivy BGP test parameters |
| `panther/plugins/services/testers/panther_ivy/templates/bgp/client_command.jinja` | Create | Ivy client param template |
| `panther/plugins/services/testers/panther_ivy/templates/bgp/server_command.jinja` | Create | Ivy server param template |
| `experiment-config/protocols/bgp/experiment_config_bgp.yaml` | Create | BGP experiment config |

### Piece 2, Layer B: MCP wrapper (ivy-lsp codebase)

| File | Action | Responsibility |
|------|--------|---------------|
| `ivy_lsp/mcp/tools/iut_testing.py` | Create | `ivy_iut_test` MCP tool |
| `ivy_lsp/mcp/tools/__init__.py` | Modify | Register new tool group |

---

## Phase A: Fix ivy_compile Native Execution

### Task 1: Create Z3 detection utility

**Files:**
- Create: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/core/environment.py`
- Create: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/core/test_environment.py`

- [ ] **Step 1: Write the test file**

```python
# tests/core/test_environment.py
"""Tests for Z3 detection utility."""

import os
from unittest.mock import patch

import pytest

from ivy_lsp.core.environment import detect_z3_dir


class TestDetectZ3Dir:
    """Tests for detect_z3_dir()."""

    def setup_method(self):
        # Clear the lru_cache between tests
        detect_z3_dir.cache_clear()

    def test_returns_z3dir_env_var_when_set(self, tmp_path):
        z3_dir = str(tmp_path / "z3")
        os.makedirs(z3_dir, exist_ok=True)
        with patch.dict(os.environ, {"Z3DIR": z3_dir}):
            assert detect_z3_dir() == z3_dir

    def test_returns_none_when_nothing_found(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("shutil.which", return_value=None):
                with patch("os.path.isfile", return_value=False):
                    with patch("subprocess.run", side_effect=FileNotFoundError):
                        assert detect_z3_dir() is None

    def test_returns_brew_prefix_on_macos(self, tmp_path):
        brew_z3 = str(tmp_path / "homebrew-z3")
        os.makedirs(brew_z3, exist_ok=True)
        with patch.dict(os.environ, {}, clear=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = brew_z3
                with patch("sys.platform", "darwin"):
                    assert detect_z3_dir() == brew_z3

    def test_returns_usr_local_when_header_exists(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                with patch("os.path.isfile") as mock_isfile:
                    mock_isfile.side_effect = lambda p: p == "/usr/local/include/z3++.h"
                    assert detect_z3_dir() == "/usr/local"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/core/test_environment.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.core.environment'`

- [ ] **Step 3: Write the implementation**

```python
# ivy_lsp/core/environment.py
"""Environment detection utilities for native Ivy compilation."""

from __future__ import annotations

import functools
import os
import subprocess
import sys
from typing import Optional


@functools.lru_cache(maxsize=1)
def detect_z3_dir() -> Optional[str]:
    """Detect the Z3 installation directory for native compilation.

    Checks in order:
    1. Z3DIR environment variable
    2. Homebrew prefix on macOS (brew --prefix z3)
    3. /usr/local/include/z3++.h
    4. /usr/include/z3++.h

    Returns:
        Path to the Z3 installation root, or None if not found.
    """
    # 1. Explicit environment variable
    z3dir = os.environ.get("Z3DIR")
    if z3dir and os.path.isdir(z3dir):
        return z3dir

    # 2. Homebrew on macOS
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["brew", "--prefix", "z3"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                brew_path = result.stdout.strip()
                if brew_path and os.path.isdir(brew_path):
                    return brew_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # 3. Standard system paths
    for prefix in ("/usr/local", "/usr"):
        if os.path.isfile(os.path.join(prefix, "include", "z3++.h")):
            return prefix

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/core/test_environment.py -v`

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/environment.py tests/core/test_environment.py
git commit -m "feat: add Z3 detection utility for native ivy_compile"
```

---

### Task 2: Fix guard check in ivy_compile MCP tool

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/verification.py:250`

- [ ] **Step 1: Fix the guard check**

In `ivy_lsp/mcp/tools/verification.py`, replace line 250:

OLD (exact):
```python
        if not shutil.which("ivyc") and not ctx.docker_image:
```

NEW:
```python
        if not shutil.which("ivyc") and ctx.executor is None:
```

This changes the check from the nonexistent `ctx.docker_image` attribute to `ctx.executor`, which is `None` when no Docker executor is configured and non-`None` when `--docker-image` or `IVY_DOCKER_IMAGE` was provided.

- [ ] **Step 2: Verify no other references to ctx.docker_image exist**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && grep -r "ctx.docker_image" ivy_lsp/`

Expected: No matches (the one we just fixed was the only reference)

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/verification.py
git commit -m "fix: replace broken ctx.docker_image guard with ctx.executor check"
```

---

### Task 3: Add Z3DIR injection and workspace staging to run_ivy_compile

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/core/verification.py:135-189`
- Create: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/core/test_compile_staging.py`

- [ ] **Step 1: Write tests for Z3DIR injection and staging**

```python
# tests/core/test_compile_staging.py
"""Tests for Z3DIR injection and workspace file staging in run_ivy_compile."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from ivy_lsp.core.verification import _find_workspace_root, _stage_workspace_files


class TestFindWorkspaceRoot:
    """Tests for workspace root discovery."""

    def test_finds_ivyworkspace_in_parent(self, tmp_path):
        ws_root = tmp_path / "protocol-testing" / "bgp"
        ws_root.mkdir(parents=True)
        (ws_root / ".ivyworkspace").write_text("version: 3")
        test_file = ws_root / "bgp_tests" / "speaker_tests" / "test.ivy"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("#lang ivy1.7")
        assert _find_workspace_root(str(test_file)) == str(ws_root)

    def test_returns_none_when_no_workspace(self, tmp_path):
        test_file = tmp_path / "test.ivy"
        test_file.write_text("#lang ivy1.7")
        assert _find_workspace_root(str(test_file)) is None


class TestStageWorkspaceFiles:
    """Tests for staging .ivy files into the include directory."""

    def test_copies_ivy_files_from_workspace(self, tmp_path):
        ws_root = tmp_path / "bgp"
        (ws_root / "bgp_stack").mkdir(parents=True)
        (ws_root / "bgp_stack" / "bgp_fsm.ivy").write_text("#lang ivy1.7\n# fsm")
        (ws_root / "bgp_utils").mkdir(parents=True)
        (ws_root / "bgp_utils" / "bgp_type.ivy").write_text("#lang ivy1.7\n# type")

        include_dir = tmp_path / "include" / "1.7"
        include_dir.mkdir(parents=True)

        staged = _stage_workspace_files(str(ws_root), str(include_dir))
        assert (include_dir / "bgp_fsm.ivy").exists()
        assert (include_dir / "bgp_type.ivy").exists()
        assert len(staged) == 2

    def test_cleanup_removes_staged_files(self, tmp_path):
        ws_root = tmp_path / "bgp"
        (ws_root / "stack").mkdir(parents=True)
        (ws_root / "stack" / "a.ivy").write_text("#lang ivy1.7")

        include_dir = tmp_path / "include" / "1.7"
        include_dir.mkdir(parents=True)
        (include_dir / "existing.ivy").write_text("# keep me")

        staged = _stage_workspace_files(str(ws_root), str(include_dir))
        # Clean up
        for f in staged:
            os.remove(f)
        assert not (include_dir / "a.ivy").exists()
        assert (include_dir / "existing.ivy").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/core/test_compile_staging.py -v`

Expected: FAIL with `ImportError: cannot import name '_find_workspace_root' from 'ivy_lsp.core.verification'`

- [ ] **Step 3: Implement staging helpers and modify run_ivy_compile**

Add the following at the top of `ivy_lsp/core/verification.py`, after the existing imports (around line 20):

```python
import glob
import shutil
from ivy_lsp.core.environment import detect_z3_dir
```

Add these helper functions before `run_ivy_compile` (insert before line 135):

```python
def _find_workspace_root(filepath: str) -> str | None:
    """Walk up from filepath looking for .ivyworkspace marker."""
    current = os.path.dirname(os.path.abspath(filepath))
    for _ in range(10):  # max 10 levels up
        if os.path.isfile(os.path.join(current, ".ivyworkspace")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def _get_ivy_include_dir() -> str | None:
    """Find the Ivy include/1.7 directory from the installed package."""
    try:
        import ivy as _ivy
        return os.path.join(os.path.dirname(_ivy.__file__), "include", "1.7")
    except ImportError:
        return None


def _stage_workspace_files(workspace_root: str, include_dir: str) -> list[str]:
    """Copy all .ivy files from workspace subdirectories into include_dir.

    Returns list of absolute paths of staged files (for cleanup).
    """
    staged: list[str] = []
    for ivy_file in glob.glob(os.path.join(workspace_root, "**", "*.ivy"), recursive=True):
        # Skip test files (they should be compiled, not included)
        if "_tests" in ivy_file or "_test" in os.path.basename(ivy_file):
            continue
        dest = os.path.join(include_dir, os.path.basename(ivy_file))
        shutil.copy2(ivy_file, dest)
        staged.append(dest)
    return staged
```

Then modify `run_ivy_compile` (the function starting at line 135) to inject Z3DIR and do staging. Replace lines 153-161 (the section from `resolved = ...` through `result = await run_ivy_subprocess(...)`) with:

OLD:
```python
        resolved = resolve_staging_path(filepath, staging_dir, resolver=resolver)
        cwd = os.path.dirname(resolved)
        os.makedirs(os.path.join(cwd, "build"), exist_ok=True)
        cmd = ["ivyc", f"target={target}"]
        if isolate:
            cmd.append(f"isolate={isolate}")
        cmd.append(os.path.basename(resolved))

        result = await run_ivy_subprocess(cmd, timeout=timeout, cwd=cwd)
```

NEW:
```python
        resolved = resolve_staging_path(filepath, staging_dir, resolver=resolver)
        cwd = os.path.dirname(resolved)
        os.makedirs(os.path.join(cwd, "build"), exist_ok=True)

        # Stage workspace files into Ivy's include dir for target=test
        staged_files: list[str] = []
        if target == "test":
            ws_root = _find_workspace_root(filepath)
            include_dir = _get_ivy_include_dir()
            if ws_root and include_dir and os.path.isdir(include_dir):
                staged_files = _stage_workspace_files(ws_root, include_dir)

        # Build Z3DIR-aware environment
        env = None
        z3_dir = detect_z3_dir()
        if z3_dir:
            env = {**os.environ, "Z3DIR": z3_dir}

        cmd = ["ivyc", f"target={target}"]
        if isolate:
            cmd.append(f"isolate={isolate}")
        cmd.append(os.path.basename(resolved))

        try:
            result = await run_ivy_subprocess(cmd, timeout=timeout, cwd=cwd, env=env)
        finally:
            # Clean up staged files
            for f in staged_files:
                try:
                    os.remove(f)
                except OSError:
                    pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/core/test_compile_staging.py tests/core/test_environment.py -v`

Expected: All tests PASS

- [ ] **Step 5: Manual validation — compile BGP test via MCP**

Restart the MCP server and run:
```bash
# This should now work without manually setting Z3DIR
ivy_compile(relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy", target="test")
```

Verify: the call returns `"success": true` and a binary is produced.

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/verification.py tests/core/test_compile_staging.py
git commit -m "feat: inject Z3DIR and stage workspace files for native ivy_compile"
```

---

## Phase B: PANTHER BGP Integration

### Task 4: BGP protocol registration

**Files:**
- Create: `panther/plugins/protocols/client_server/bgp/__init__.py`
- Create: `panther/plugins/protocols/client_server/bgp/bgp.py`

- [ ] **Step 1: Create the package directory**

```bash
mkdir -p panther/plugins/protocols/client_server/bgp
```

- [ ] **Step 2: Create the __init__.py**

```python
# panther/plugins/protocols/client_server/bgp/__init__.py
```

(Empty file — package marker only.)

- [ ] **Step 3: Create the protocol registration**

```python
# panther/plugins/protocols/client_server/bgp/bgp.py
"""
BGP Protocol Plugin

Registers BGP-4 (RFC 4271) as a client-server protocol in PANTHER.
BGP uses TCP port 179 for session establishment between autonomous systems.
"""

from panther.plugins.core.plugin_decorators import register_protocol
from panther.plugins.protocols.protocol_interface import IProtocolManager


@register_protocol(
    name="bgp",
    type="client_server",
    versions=["rfc4271"],
    default_version="rfc4271",
    description="BGP-4 path-vector routing protocol (RFC 4271)",
    author="IETF IDR Working Group",
    license="IETF",
    homepage="https://datatracker.ietf.org/doc/html/rfc4271",
    capabilities=[
        "route-advertisement",
        "as-path",
        "communities",
        "fsm",
        "keepalive",
        "notification",
    ],
    tags=["routing", "tcp", "inter-domain"],
    config_schema={
        "hold_time": {
            "type": "integer",
            "default": 180,
            "description": "Hold timer in seconds (0 = no keepalives)",
        },
        "bgp_version": {
            "type": "integer",
            "default": 4,
            "description": "BGP protocol version",
        },
    },
    default_config={
        "hold_time": 180,
        "bgp_version": 4,
    },
)
class BGPProtocol(IProtocolManager):
    """BGP-4 Protocol Manager."""

    def __init__(self):
        self._metadata = self.get_protocol_metadata()

    def validate_config(self):
        pass

    def load_config(self) -> dict:
        return self._metadata.get("default_config", {})

    def get_version_parameters(self, version: str) -> dict:
        if version == "rfc4271":
            return {
                "port": 179,
                "hold_time": 180,
                "keepalive_interval": 60,
                "bgp_version": 4,
            }
        return {}

    @classmethod
    def get_default_server_port(cls) -> int:
        return 179

    @classmethod
    def get_default_client_port(cls) -> int:
        return 0


import logging  # noqa: E402

logging.getLogger(__name__)
```

- [ ] **Step 4: Verify plugin discovery**

```bash
python -c "from panther.plugins.protocols.client_server.bgp.bgp import BGPProtocol; print('BGP protocol loaded')"
```

Expected: `BGP protocol loaded`

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/protocols/client_server/bgp/
git commit -m "feat: register BGP-4 as a PANTHER client-server protocol"
```

---

### Task 5: FRRouting IUT plugin

**Files:**
- Create: `panther/plugins/services/iut/bgp/__init__.py`
- Create: `panther/plugins/services/iut/bgp/frr_bgp/__init__.py`
- Create: `panther/plugins/services/iut/bgp/frr_bgp/config_schema.py`
- Create: `panther/plugins/services/iut/bgp/frr_bgp/frr_bgp.py`
- Create: `panther/plugins/services/iut/bgp/frr_bgp/Dockerfile`
- Create: `panther/plugins/services/iut/bgp/frr_bgp/version_configs/rfc4271.yaml`
- Create: `panther/plugins/services/iut/bgp/frr_bgp/templates/server_command.jinja`
- Create: `panther/plugins/services/iut/bgp/frr_bgp/templates/bgpd.conf.jinja`

- [ ] **Step 1: Create directories**

```bash
mkdir -p panther/plugins/services/iut/bgp/frr_bgp/{version_configs,templates}
```

- [ ] **Step 2: Create package markers**

```python
# panther/plugins/services/iut/bgp/__init__.py
```

```python
# panther/plugins/services/iut/bgp/frr_bgp/__init__.py
```

- [ ] **Step 3: Create config schema**

```python
# panther/plugins/services/iut/bgp/frr_bgp/config_schema.py
"""FRRouting BGP plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class FrrBgpVersion(VersionBase):
    """Version information for FRRouting BGP implementation."""

    server: Optional[dict] = Field(default_factory=dict)
    client: Optional[dict] = Field(default_factory=dict)


class FrrBgpConfig(ServiceConfig):
    """FRRouting BGP implementation configuration.

    Uses the official FRRouting Docker image to run bgpd.

    Example YAML::

        services:
          bgp_router:
            implementation:
              name: frr_bgp
              type: iut
            protocol:
              name: bgp
              role: server
    """

    VERSION_CLASS: ClassVar[Optional[type]] = FrrBgpVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="frr_bgp", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="bgp", role="server"),
        description="Protocol configuration",
    )
    version: FrrBgpVersion = Field(
        default_factory=lambda: FrrBgpConfig.load_version(),
        description="Version configuration",
    )
```

- [ ] **Step 4: Create the service manager**

```python
# panther/plugins/services/iut/bgp/frr_bgp/frr_bgp.py
"""FRRouting BGP service manager for PANTHER."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from panther.config.core.models import ProtocolConfig
from panther.core.command_processor.builders import ServiceCommandBuilder
from panther.core.docker_builder.plugin_mixin.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.utils.string_representation_mixin import StringRepresentationMixin
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.iut.implementation_interface import (
    IImplementationManager,
)
from panther.plugins.services.iut.iut_event_mixin import IUTManagerEventMixin
from panther.plugins.services.iut.iut_service_manager_mixin import (
    IUTServiceManagerMixin,
)

from panther.plugins.services.iut.bgp.frr_bgp.config_schema import FrrBgpConfig

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


@register_plugin(
    plugin_type=PluginType.IUT,
    name="frr_bgp",
    version="1.0.0",
    description="FRRouting BGP-4 implementation",
    author="PANTHER Team",
    dependencies=["docker"],
    supported_protocols=["bgp"],
    capabilities=["rfc4271", "route-advertisement", "communities"],
    external_dependencies=["docker"],
)
class FrrBgpServiceManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    IUTManagerEventMixin,
    ErrorHandlerMixin,
    IImplementationManager,
    StringRepresentationMixin,
):
    """Service manager for FRRouting BGP implementation."""

    def __init__(
        self,
        service_config_to_test: FrrBgpConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
        **kwargs,
    ):
        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            **kwargs,
        )
        self.standard_iut_initialization(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
            plugin_dir=Path(__file__).parent,
        )

    def generate_pre_compile_commands(self) -> List[str]:
        return []

    def generate_compile_commands(self) -> List[str]:
        return []

    def generate_runtime_commands(self) -> List[str]:
        return []

    def generate_run_command(self) -> str:
        builder = ServiceCommandBuilder(self.service_config)
        return builder.build_from_jinja_template(
            template_dir=str(Path(__file__).parent / "templates"),
            template_name="server_command.jinja",
            context=self._build_template_context(),
        )

    def generate_post_run_commands(self) -> List[str]:
        return ["cp /tmp/frr/*.log /app/logs/ 2>/dev/null || true"]

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        return [
            ("test", "*.log"),
            ("test", "*.err.log"),
        ]

    def _build_template_context(self) -> dict:
        vc = self.version_config or {}
        server = vc.get("server", {})
        return {
            "as_number": server.get("as_number", 2),
            "router_id": server.get("router_id", "10.0.0.3"),
            "neighbor_ip": server.get("neighbor_ip", "10.0.0.1"),
            "neighbor_as": server.get("neighbor_as", 1),
            "hold_time": server.get("hold_time", 180),
            "keepalive_time": server.get("keepalive_time", 60),
            "listen_port": server.get("listen_port", 179),
        }

    def _do_prepare(self, plugin_manager: "PluginManager") -> None:
        self.prepare_docker_image(plugin_manager)
```

- [ ] **Step 5: Create Dockerfile**

```dockerfile
# panther/plugins/services/iut/bgp/frr_bgp/Dockerfile
ARG BASE_IMAGE=frrouting/frr:10.2.1
FROM ${BASE_IMAGE}

# FRR ships with all daemons; we only need bgpd + zebra
RUN sed -i 's/bgpd=no/bgpd=yes/' /etc/frr/daemons && \
    sed -i 's/zebra=no/zebra=yes/' /etc/frr/daemons

WORKDIR /etc/frr

ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
```

- [ ] **Step 6: Create version config**

```yaml
# panther/plugins/services/iut/bgp/frr_bgp/version_configs/rfc4271.yaml
version: "rfc4271"
commit: "10.2.1"
server:
  as_number: 2
  router_id: "@{self_service:ip:decimal}"
  neighbor_ip: "@{client_service:ip:decimal}"
  neighbor_as: 1
  hold_time: 180
  keepalive_time: 60
  listen_port: 179
  binary:
    dir: "/usr/lib/frr"
    name: "bgpd"
  logging:
    log_path: "/tmp/frr/bgpd.log"
    err_path: "/tmp/frr/bgpd.err.log"
```

- [ ] **Step 7: Create server command template**

```jinja
{# panther/plugins/services/iut/bgp/frr_bgp/templates/server_command.jinja #}
mkdir -p /tmp/frr && /usr/lib/frr/zebra -d -f /etc/frr/zebra.conf --log file:/tmp/frr/zebra.log && sleep 1 && /usr/lib/frr/bgpd -n -f /etc/frr/bgpd.conf --log file:/tmp/frr/bgpd.log -p {{ listen_port }}
```

- [ ] **Step 8: Create bgpd.conf template**

```jinja
{# panther/plugins/services/iut/bgp/frr_bgp/templates/bgpd.conf.jinja #}
frr version 10.2.1
frr defaults traditional
!
router bgp {{ as_number }}
 bgp router-id {{ router_id }}
 neighbor {{ neighbor_ip }} remote-as {{ neighbor_as }}
 neighbor {{ neighbor_ip }} timers {{ hold_time }} {{ keepalive_time }}
 !
 address-family ipv4 unicast
  neighbor {{ neighbor_ip }} activate
 exit-address-family
!
```

- [ ] **Step 9: Verify plugin loads**

```bash
python -c "from panther.plugins.services.iut.bgp.frr_bgp.frr_bgp import FrrBgpServiceManager; print('FRR BGP plugin loaded')"
```

Expected: `FRR BGP plugin loaded`

- [ ] **Step 10: Commit**

```bash
git add panther/plugins/services/iut/bgp/
git commit -m "feat: add FRRouting BGP IUT plugin for PANTHER"
```

---

### Task 6: Ivy tester BGP support and hex IP format

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/panther_ivy.py:59`
- Modify: `panther/plugins/services/testers/panther_ivy/ivy_network_resolution_mixin.py`
- Create: `panther/plugins/services/testers/panther_ivy/version_configs/bgp/rfc4271.yaml`
- Create: `panther/plugins/services/testers/panther_ivy/templates/bgp/client_command.jinja`
- Create: `panther/plugins/services/testers/panther_ivy/templates/bgp/server_command.jinja`

- [ ] **Step 1: Add "bgp" to supported_protocols**

In `panther/plugins/services/testers/panther_ivy/panther_ivy.py`, line 59:

OLD:
```python
    supported_protocols=["quic"],
```

NEW:
```python
    supported_protocols=["quic", "bgp"],
```

- [ ] **Step 2: Create template directories and files**

```bash
mkdir -p panther/plugins/services/testers/panther_ivy/templates/bgp
mkdir -p panther/plugins/services/testers/panther_ivy/version_configs/bgp
```

- [ ] **Step 3: Create BGP version config for Ivy tester**

```yaml
# panther/plugins/services/testers/panther_ivy/version_configs/bgp/rfc4271.yaml
version: "rfc4271"
env:
  PROTOCOL_TESTED: "bgp"
parameters:
  speaker_addr:
    value: "@{client_service:ip:hex}"
    description: "Ivy speaker IP address (hex format for Ivy model)"
  speaker_id:
    value: "@{client_service:ip:hex}"
    description: "Ivy speaker BGP identifier (hex)"
  speaker_as:
    value: "1"
    description: "Ivy speaker AS number"
  speaker_impl_addr:
    value: "@{server_service:ip:hex}"
    description: "IUT speaker IP address (hex)"
  speaker_impl_id:
    value: "@{server_service:ip:hex}"
    description: "IUT speaker BGP identifier (hex)"
  speaker_impl_as:
    value: "2"
    description: "IUT speaker AS number"
server:
  binary:
    dir: "PANTHER_IVY_INSTALL_DIR/protocol-testing/"
    name: ""
  speaker_addr: "@{server_service:ip:hex}"
  speaker_id: "@{server_service:ip:hex}"
  speaker_as: "1"
  speaker_impl_addr: "@{client_service:ip:hex}"
  speaker_impl_id: "@{client_service:ip:hex}"
  speaker_impl_as: "2"
client:
  binary:
    dir: "PANTHER_IVY_INSTALL_DIR/protocol-testing/"
    name: ""
  speaker_addr: "@{client_service:ip:hex}"
  speaker_id: "@{client_service:ip:hex}"
  speaker_as: "1"
  speaker_impl_addr: "@{server_service:ip:hex}"
  speaker_impl_id: "@{server_service:ip:hex}"
  speaker_impl_as: "2"
```

- [ ] **Step 4: Create client command template**

```jinja
{# panther/plugins/services/testers/panther_ivy/templates/bgp/client_command.jinja #}
speaker_addr={{ speaker_addr }} speaker_id={{ speaker_id }} speaker_as={{ speaker_as }} speaker_impl_addr={{ speaker_impl_addr }} speaker_impl_id={{ speaker_impl_id }} speaker_impl_as={{ speaker_impl_as }}
```

- [ ] **Step 5: Create server command template**

```jinja
{# panther/plugins/services/testers/panther_ivy/templates/bgp/server_command.jinja #}
speaker_addr={{ speaker_addr }} speaker_id={{ speaker_id }} speaker_as={{ speaker_as }} speaker_impl_addr={{ speaker_impl_addr }} speaker_impl_id={{ speaker_impl_id }} speaker_impl_as={{ speaker_impl_as }}
```

- [ ] **Step 6: Add hex IP format to IvyNetworkResolutionMixin**

In `panther/plugins/services/testers/panther_ivy/ivy_network_resolution_mixin.py`, the `_resolve_placeholders_in_string` method (line 198) resolves role aliases to service names but does not convert IP format. The actual IP resolution happens later in the PANTHER network layer. We need to ensure the network layer supports `hex` as a format specifier.

Find the method or code that resolves `@{service_name:ip:decimal}` to an actual IP value. Search for where `decimal` is handled and add a `hex` branch that converts the IP to `0x` prefixed hex (e.g., `10.0.0.1` → `0x0a000001`).

If the final resolution happens in PANTHER core (not in the ivy plugin), add a post-resolution hook in the mixin. Add this method to the class:

```python
def _post_resolve_ip_format(self, resolved_value: str, format_type: str) -> str:
    """Convert resolved IP to the requested format.

    The network layer resolves to decimal by default. For hex format,
    convert dotted-decimal to 0x-prefixed hex (e.g., 10.0.0.1 -> 0x0a000001).
    """
    if format_type != "hex":
        return resolved_value
    try:
        import ipaddress
        addr = ipaddress.ip_address(resolved_value)
        return f"0x{int(addr):08x}"
    except (ValueError, TypeError):
        return resolved_value
```

The exact integration point depends on where in the PANTHER pipeline IP values are substituted. This may need to be wired into the command generation step in `ivy_command_mixin.py` where placeholders are resolved to final values. Verify the exact integration during implementation.

- [ ] **Step 7: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/panther_ivy.py
git add panther/plugins/services/testers/panther_ivy/ivy_network_resolution_mixin.py
git add panther/plugins/services/testers/panther_ivy/version_configs/bgp/
git add panther/plugins/services/testers/panther_ivy/templates/bgp/
git commit -m "feat: add BGP support to Ivy tester plugin with hex IP format"
```

---

### Task 7: BGP experiment config

**Files:**
- Create: `experiment-config/protocols/bgp/experiment_config_bgp.yaml`

- [ ] **Step 1: Create directory**

```bash
mkdir -p experiment-config/protocols/bgp
```

- [ ] **Step 2: Create experiment config**

```yaml
# experiment-config/protocols/bgp/experiment_config_bgp.yaml
logging:
  level: INFO
paths:
  output_dir: "outputs"
  plugin_dir: "panther/plugins"
docker:
  force_build_docker_image: false
  use_buildx: true
tests:
  - name: "BGP Session Establishment (Join)"
    network_environment:
      type: docker_compose
    iterations: 1
    services:
      frr_router:
        name: frr_router
        timeout: 60
        implementation:
          name: frr_bgp
          type: iut
        protocol:
          name: bgp
          version: rfc4271
          role: server
        ports:
          - "179:179"
      ivy_tester:
        name: ivy_tester
        timeout: 120
        implementation:
          name: panther_ivy
          type: testers
          test: bgp_speaker_test_join
        protocol:
          name: bgp
          version: rfc4271
          role: client
          target: frr_router
```

- [ ] **Step 3: Validate config parsing**

```bash
panther config validate --config experiment-config/protocols/bgp/experiment_config_bgp.yaml
```

Expected: Config validates successfully (or specific errors to fix).

- [ ] **Step 4: Commit**

```bash
git add experiment-config/protocols/bgp/
git commit -m "feat: add BGP experiment config for FRRouting + Ivy testing"
```

---

### Task 8: MCP ivy_iut_test tool

**Files:**
- Create: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/iut_testing.py`
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/__init__.py:730-752`

- [ ] **Step 1: Create the iut_testing tool module**

```python
# ivy_lsp/mcp/tools/iut_testing.py
"""MCP tool for running Ivy tests against IUTs via PANTHER."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import time
import uuid
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_TEMPLATE = {
    "logging": {"level": "INFO"},
    "paths": {"output_dir": "outputs", "plugin_dir": "panther/plugins"},
    "docker": {"force_build_docker_image": False, "use_buildx": True},
}


def register_iut_testing_tools(mcp: Any, ctx: Any) -> None:
    """Register IUT testing tools on the MCP server."""

    @mcp.tool()
    async def ivy_iut_test(
        protocol: str,
        test_name: str,
        iut_name: str,
        version: str = "",
        timeout: int = 120,
        extra_params: dict | None = None,
    ) -> dict[str, Any]:
        """Run an Ivy test against an IUT via PANTHER's experiment pipeline.

        Generates a temporary experiment config and invokes `panther run`.

        Args:
            protocol: Protocol name (e.g., "bgp", "quic").
            test_name: Ivy test file name without .ivy extension.
            iut_name: Registered IUT plugin name (e.g., "frr_bgp").
            version: Protocol version (default: protocol's default version).
            timeout: Total timeout in seconds (default: 120).
            extra_params: Override version_config values.
        """
        if not shutil.which("panther"):
            return {
                "success": False,
                "error": "panther CLI not found on PATH. Install PANTHER first.",
            }

        version = version or ""
        config = _build_experiment_config(
            protocol=protocol,
            test_name=test_name,
            iut_name=iut_name,
            version=version,
            timeout=timeout,
        )

        run_id = str(uuid.uuid4())[:8]
        tmp_dir = os.path.join(tempfile.gettempdir(), f"ivy-iut-{run_id}")
        os.makedirs(tmp_dir, exist_ok=True)
        config_path = os.path.join(tmp_dir, "config.yaml")

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                "panther", "run", "--config", config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=ctx.root,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            duration = time.monotonic() - t0
            stdout = stdout_bytes.decode(errors="replace")
            stderr = stderr_bytes.decode(errors="replace")

            if proc.returncode == 0:
                verdict = "pass"
            else:
                verdict = "fail"

        except asyncio.TimeoutError:
            duration = time.monotonic() - t0
            proc.kill()
            stdout = ""
            stderr = "Timeout exceeded"
            verdict = "timeout"
        except Exception as exc:
            duration = time.monotonic() - t0
            stdout = ""
            stderr = str(exc)
            verdict = "error"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        return {
            "verdict": verdict,
            "test_name": test_name,
            "iut_name": iut_name,
            "protocol": protocol,
            "test_stdout": stdout[-5000:],
            "test_stderr": stderr[-2000:],
            "duration_seconds": round(duration, 2),
            "error": stderr if verdict in ("error", "timeout") else None,
        }


def _build_experiment_config(
    protocol: str,
    test_name: str,
    iut_name: str,
    version: str,
    timeout: int,
) -> dict:
    """Build a PANTHER experiment config dict."""
    config = dict(_CONFIG_TEMPLATE)
    config["tests"] = [
        {
            "name": f"IUT Test: {test_name} vs {iut_name}",
            "network_environment": {"type": "docker_compose"},
            "iterations": 1,
            "services": {
                "iut": {
                    "name": "iut",
                    "timeout": timeout,
                    "implementation": {
                        "name": iut_name,
                        "type": "iut",
                    },
                    "protocol": {
                        "name": protocol,
                        **({"version": version} if version else {}),
                        "role": "server",
                    },
                },
                "ivy_tester": {
                    "name": "ivy_tester",
                    "timeout": timeout,
                    "implementation": {
                        "name": "panther_ivy",
                        "type": "testers",
                        "test": test_name,
                    },
                    "protocol": {
                        "name": protocol,
                        **({"version": version} if version else {}),
                        "role": "client",
                        "target": "iut",
                    },
                },
            },
        }
    ]
    return config
```

- [ ] **Step 2: Register the tool in __init__.py**

In `ivy_lsp/mcp/tools/__init__.py`, add the import at line 737 (after the existing imports):

```python
from ivy_lsp.mcp.tools.iut_testing import register_iut_testing_tools
```

Add the registration call inside `register_all_tools()` at line 752 (after `register_propagation_tools`):

```python
    register_iut_testing_tools(mcp, ctx)
```

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/iut_testing.py ivy_lsp/mcp/tools/__init__.py
git commit -m "feat: add ivy_iut_test MCP tool wrapping panther run"
```

---

### Task 9: End-to-end validation

- [ ] **Step 1: Run panther config validate**

```bash
panther config validate --config experiment-config/protocols/bgp/experiment_config_bgp.yaml
```

Fix any config validation errors before proceeding.

- [ ] **Step 2: Run panther plugins list**

```bash
panther plugins list
```

Verify `frr_bgp` appears in the IUT plugins list and `bgp` appears in protocols.

- [ ] **Step 3: Attempt a full experiment run**

```bash
panther run --config experiment-config/protocols/bgp/experiment_config_bgp.yaml
```

This will likely fail on the first attempt (Docker image needs building, network placeholders need debugging). Document any failures and iterate.

- [ ] **Step 4: Final commit with any fixes**

```bash
git add -A
git commit -m "fix: resolve integration issues from end-to-end BGP test run"
```
