# ivy_iut_test Tool Completion & Workflow Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the `ivy_iut_test` MCP tool (extra_params, output parsing, validation, config_path), add unit tests, integrate into the verify workflow as Phase 5, and create the `/nct-iut-test` shortcut command.

**Architecture:** The MCP tool generates or loads an experiment config, runs `panther run` as an async subprocess, then parses the PANTHER output directory for structured results. The verify workflow gains an optional Phase 5 (IUT Testing) after formal verification. A shortcut command provides direct access.

**Tech Stack:** Python 3.10+, asyncio subprocess, PyYAML, JSON, MCP (FastMCP), pytest with unittest.mock

**Spec:** `docs/superpowers/specs/2026-04-11-ivy-iut-test-tool-completion-design.md`

---

## File Map

All paths relative to project root (`/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/lsp-to-claude/`).

### ivy-lsp (MCP tool codebase)

| File | Action | Responsibility |
|------|--------|---------------|
| `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/iut_testing.py` | Rewrite | Core tool: config gen, validation, subprocess, output parsing |
| `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/__init__.py` | Modify | Add timeout + metadata entries |
| `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/test_iut_testing.py` | Create | Unit tests |

### panther-ivy-plugin (skills, commands, docs)

| File | Action | Responsibility |
|------|--------|---------------|
| `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/verify/SKILL.md` | Modify | Add Phase 5 (IUT Testing), renumber 5→6, 6→7 |
| `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-iut-test.md` | Create | Shortcut command |
| `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/CLAUDE.md` | Modify | Add tool + command to reference tables |

---

## Task 1: Rewrite iut_testing.py — helper functions

**Files:**
- Rewrite: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/iut_testing.py`

This task writes the module-level helper functions. The MCP tool registration (which depends on these helpers) comes in Task 3.

- [ ] **Step 1: Write the validation and config helpers**

Replace the entire contents of `iut_testing.py` with:

```python
"""MCP tool for running Ivy tests against IUTs via PANTHER."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_TEMPLATE = {
    "logging": {"level": "INFO"},
    "docker": {"force_build_docker_image": False, "use_buildx": True},
}

_KNOWN_PROTOCOLS = {"quic", "bgp", "coap", "minip"}


def _validate_inputs(
    protocol: str, test_name: str, iut_name: str, root: str
) -> str | None:
    """Return an error message if inputs are invalid, None if valid."""
    if not protocol or not protocol.strip():
        return "protocol is required"
    if not test_name or not test_name.strip():
        return "test_name is required"
    if not iut_name or not iut_name.strip():
        return "iut_name is required"

    protocol = protocol.strip().lower()

    protocol_dir = os.path.join(
        root, "panther", "plugins", "protocols", "client_server", protocol
    )
    if not os.path.isdir(protocol_dir):
        hint = (
            f" Known protocols: {', '.join(sorted(_KNOWN_PROTOCOLS))}"
            if _KNOWN_PROTOCOLS
            else ""
        )
        return f"Protocol '{protocol}' not found at {protocol_dir}.{hint}"

    iut_dir = os.path.join(
        root, "panther", "plugins", "services", "iut", protocol, iut_name
    )
    if not os.path.isdir(iut_dir):
        return f"IUT plugin '{iut_name}' not found at {iut_dir}"

    return None


def _build_experiment_config(
    protocol: str,
    test_name: str,
    iut_name: str,
    version: str,
    timeout: int,
    run_id: str,
    extra_params: dict | None = None,
) -> dict:
    """Build a PANTHER experiment config dict with deterministic output dir."""
    config = dict(_CONFIG_TEMPLATE)
    config["paths"] = {
        "output_dir": f"outputs/ivy-iut-{run_id}",
        "plugin_dir": "panther/plugins",
    }

    iut_impl: dict[str, Any] = {"name": iut_name, "type": "iut"}
    tester_impl: dict[str, Any] = {
        "name": "panther_ivy",
        "type": "testers",
        "test": test_name,
    }

    if extra_params:
        iut_impl["version_config"] = extra_params
        tester_impl["version_config"] = extra_params

    iut_protocol: dict[str, Any] = {"name": protocol, "role": "server"}
    tester_protocol: dict[str, Any] = {
        "name": protocol,
        "role": "client",
        "target": "iut",
    }
    if version:
        iut_protocol["version"] = version
        tester_protocol["version"] = version

    config["tests"] = [
        {
            "name": f"IUT Test: {test_name} vs {iut_name}",
            "network_environment": {"type": "docker_compose"},
            "iterations": 1,
            "services": {
                "iut": {
                    "name": "iut",
                    "timeout": timeout,
                    "implementation": iut_impl,
                    "protocol": iut_protocol,
                },
                "ivy_tester": {
                    "name": "ivy_tester",
                    "timeout": timeout,
                    "implementation": tester_impl,
                    "protocol": tester_protocol,
                },
            },
        }
    ]
    return config


def _prepare_user_config(
    config_path: str, test_name: str, timeout: int
) -> dict:
    """Load a user-provided config and override test_name and timeout."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    tests = config.get("tests", [])
    if not tests:
        raise ValueError(f"No tests found in config at {config_path}")

    test_entry = tests[0]
    services = test_entry.get("services", {})
    for svc in services.values():
        svc["timeout"] = timeout
        impl = svc.get("implementation", {})
        if impl.get("type") == "testers":
            impl["test"] = test_name

    return config


def _find_output_dir_deterministic(root: str, run_id: str) -> str | None:
    """Find the output directory by deterministic run_id path."""
    candidate = os.path.join(root, "outputs", f"ivy-iut-{run_id}")
    return candidate if os.path.isdir(candidate) else None


def _find_output_dir_by_timestamp(root: str, start_time: float) -> str | None:
    """Find the newest output directory created after start_time."""
    outputs_base = os.path.join(root, "outputs")
    if not os.path.isdir(outputs_base):
        return None

    candidates = []
    for entry in Path(outputs_base).iterdir():
        if entry.is_dir() and entry.stat().st_mtime >= start_time:
            candidates.append(entry)

    if not candidates:
        return None

    newest = max(candidates, key=lambda d: d.stat().st_mtime)
    return str(newest)


def _load_experiment_summary(output_dir: str | None) -> dict | None:
    """Load experiment_summary.json from the output directory."""
    if not output_dir:
        return None
    summary_path = os.path.join(output_dir, "experiment_summary.json")
    if not os.path.isfile(summary_path):
        return None
    try:
        with open(summary_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse experiment_summary.json: %s", exc)
        return None


def _collect_iut_logs(output_dir: str | None) -> str:
    """Collect test.log content from test subdirectories."""
    if not output_dir or not os.path.isdir(output_dir):
        return ""

    logs: list[str] = []
    for entry in sorted(Path(output_dir).iterdir()):
        if not entry.is_dir():
            continue
        test_log = entry / "test.log"
        if test_log.is_file():
            try:
                content = test_log.read_text(errors="replace")
                logs.append(f"--- {entry.name}/test.log ---\n{content}")
            except OSError:
                pass

    return "\n".join(logs)


def _refine_verdict(subprocess_verdict: str, summary: dict) -> str:
    """Refine verdict using experiment_summary.json per-test status."""
    results = summary.get("tests", {}).get("results", [])
    if not results:
        return subprocess_verdict

    status = results[0].get("status", "").lower()
    if status == "passed":
        return "pass"
    if status == "failed":
        return "fail"
    if status == "timeout":
        return "timeout"
    return subprocess_verdict
```

- [ ] **Step 2: Verify the file is syntactically correct**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "import ast; ast.parse(open('ivy_lsp/mcp/tools/iut_testing.py').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/iut_testing.py
git commit -m "refactor: rewrite iut_testing.py helper functions for extra_params, validation, output parsing"
```

---

## Task 2: Write unit tests for helper functions

**Files:**
- Create: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/test_iut_testing.py`

- [ ] **Step 1: Write the test file**

```python
"""Unit tests for ivy_iut_test MCP tool helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from ivy_lsp.mcp.tools.iut_testing import (
    _build_experiment_config,
    _collect_iut_logs,
    _find_output_dir_by_timestamp,
    _find_output_dir_deterministic,
    _load_experiment_summary,
    _prepare_user_config,
    _refine_verdict,
    _validate_inputs,
)


class TestValidateInputs:
    """Tests for _validate_inputs."""

    def test_missing_protocol(self, tmp_path):
        assert _validate_inputs("", "test", "iut", str(tmp_path)) == "protocol is required"

    def test_missing_test_name(self, tmp_path):
        assert _validate_inputs("bgp", "", "iut", str(tmp_path)) == "test_name is required"

    def test_missing_iut_name(self, tmp_path):
        assert _validate_inputs("bgp", "test", "", str(tmp_path)) == "iut_name is required"

    def test_unknown_protocol(self, tmp_path):
        result = _validate_inputs("nonexistent", "test", "iut", str(tmp_path))
        assert "not found" in result
        assert "Known protocols" in result

    def test_unknown_iut(self, tmp_path):
        proto_dir = tmp_path / "panther" / "plugins" / "protocols" / "client_server" / "bgp"
        proto_dir.mkdir(parents=True)
        result = _validate_inputs("bgp", "test", "bad_iut", str(tmp_path))
        assert "IUT plugin 'bad_iut' not found" in result

    def test_valid_inputs(self, tmp_path):
        proto_dir = tmp_path / "panther" / "plugins" / "protocols" / "client_server" / "bgp"
        proto_dir.mkdir(parents=True)
        iut_dir = tmp_path / "panther" / "plugins" / "services" / "iut" / "bgp" / "frr_bgp"
        iut_dir.mkdir(parents=True)
        assert _validate_inputs("bgp", "test", "frr_bgp", str(tmp_path)) is None


class TestBuildExperimentConfig:
    """Tests for _build_experiment_config."""

    def test_default_config(self):
        config = _build_experiment_config(
            protocol="bgp",
            test_name="bgp_speaker_test_join",
            iut_name="frr_bgp",
            version="",
            timeout=120,
            run_id="abc12345",
        )
        assert config["paths"]["output_dir"] == "outputs/ivy-iut-abc12345"
        test_entry = config["tests"][0]
        assert test_entry["services"]["iut"]["implementation"]["name"] == "frr_bgp"
        assert test_entry["services"]["ivy_tester"]["implementation"]["test"] == "bgp_speaker_test_join"
        assert "version" not in test_entry["services"]["iut"]["protocol"]

    def test_with_extra_params(self):
        config = _build_experiment_config(
            protocol="bgp",
            test_name="test",
            iut_name="frr_bgp",
            version="rfc4271",
            timeout=60,
            run_id="xyz",
            extra_params={"speaker_as": "99"},
        )
        test_entry = config["tests"][0]
        assert test_entry["services"]["iut"]["implementation"]["version_config"] == {"speaker_as": "99"}
        assert test_entry["services"]["ivy_tester"]["implementation"]["version_config"] == {"speaker_as": "99"}
        assert test_entry["services"]["iut"]["protocol"]["version"] == "rfc4271"

    def test_deterministic_output_dir(self):
        config = _build_experiment_config(
            protocol="quic", test_name="t", iut_name="i",
            version="", timeout=60, run_id="deadbeef",
        )
        assert "deadbeef" in config["paths"]["output_dir"]


class TestPrepareUserConfig:
    """Tests for _prepare_user_config."""

    def test_overrides_test_name_and_timeout(self, tmp_path):
        original = {
            "tests": [
                {
                    "name": "Original",
                    "services": {
                        "iut": {
                            "timeout": 30,
                            "implementation": {"name": "frr_bgp", "type": "iut"},
                        },
                        "ivy_tester": {
                            "timeout": 30,
                            "implementation": {
                                "name": "panther_ivy",
                                "type": "testers",
                                "test": "old_test",
                            },
                        },
                    },
                }
            ]
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(original, f)

        result = _prepare_user_config(str(config_file), "new_test", 999)
        svc = result["tests"][0]["services"]
        assert svc["ivy_tester"]["implementation"]["test"] == "new_test"
        assert svc["ivy_tester"]["timeout"] == 999
        assert svc["iut"]["timeout"] == 999

    def test_raises_on_empty_tests(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"tests": []}, f)

        with pytest.raises(ValueError, match="No tests found"):
            _prepare_user_config(str(config_file), "test", 60)


class TestFindOutputDir:
    """Tests for output directory finding."""

    def test_deterministic_found(self, tmp_path):
        out_dir = tmp_path / "outputs" / "ivy-iut-abc123"
        out_dir.mkdir(parents=True)
        assert _find_output_dir_deterministic(str(tmp_path), "abc123") == str(out_dir)

    def test_deterministic_not_found(self, tmp_path):
        assert _find_output_dir_deterministic(str(tmp_path), "nope") is None

    def test_timestamp_finds_newest(self, tmp_path):
        import time as _time

        outputs = tmp_path / "outputs"
        outputs.mkdir()
        old_dir = outputs / "old-run"
        old_dir.mkdir()
        _time.sleep(0.05)
        start = _time.monotonic()
        _time.sleep(0.05)
        new_dir = outputs / "new-run"
        new_dir.mkdir()

        result = _find_output_dir_by_timestamp(str(tmp_path), start)
        assert result == str(new_dir)

    def test_timestamp_no_outputs(self, tmp_path):
        assert _find_output_dir_by_timestamp(str(tmp_path), 0.0) is None


class TestLoadExperimentSummary:
    """Tests for _load_experiment_summary."""

    def test_loads_valid_json(self, tmp_path):
        summary = {"tests": {"results": [{"status": "passed"}]}}
        summary_file = tmp_path / "experiment_summary.json"
        summary_file.write_text(json.dumps(summary))
        result = _load_experiment_summary(str(tmp_path))
        assert result == summary

    def test_returns_none_for_missing_file(self, tmp_path):
        assert _load_experiment_summary(str(tmp_path)) is None

    def test_returns_none_for_none_dir(self):
        assert _load_experiment_summary(None) is None


class TestCollectIutLogs:
    """Tests for _collect_iut_logs."""

    def test_collects_test_log(self, tmp_path):
        test_dir = tmp_path / "0_My_Test_"
        test_dir.mkdir()
        (test_dir / "test.log").write_text("some log output")
        result = _collect_iut_logs(str(tmp_path))
        assert "some log output" in result
        assert "0_My_Test_/test.log" in result

    def test_empty_dir(self, tmp_path):
        assert _collect_iut_logs(str(tmp_path)) == ""

    def test_none_dir(self):
        assert _collect_iut_logs(None) == ""

    def test_truncation(self, tmp_path):
        test_dir = tmp_path / "0_Test_"
        test_dir.mkdir()
        (test_dir / "test.log").write_text("x" * 5000)
        result = _collect_iut_logs(str(tmp_path))
        # The raw result is not truncated by this function — truncation
        # happens in the tool return dict ([-3000:]).
        assert len(result) > 3000


class TestRefineVerdict:
    """Tests for _refine_verdict."""

    def test_summary_passed_overrides_fail(self):
        summary = {"tests": {"results": [{"status": "passed"}]}}
        assert _refine_verdict("fail", summary) == "pass"

    def test_summary_failed_overrides_pass(self):
        summary = {"tests": {"results": [{"status": "failed"}]}}
        assert _refine_verdict("pass", summary) == "fail"

    def test_summary_timeout(self):
        summary = {"tests": {"results": [{"status": "timeout"}]}}
        assert _refine_verdict("fail", summary) == "timeout"

    def test_summary_unknown_keeps_subprocess(self):
        summary = {"tests": {"results": [{"status": "unknown"}]}}
        assert _refine_verdict("fail", summary) == "fail"

    def test_no_results_keeps_subprocess(self):
        assert _refine_verdict("pass", {"tests": {}}) == "pass"

    def test_empty_summary_keeps_subprocess(self):
        assert _refine_verdict("error", {}) == "error"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_iut_testing.py -v`

Expected: All tests PASS (the helpers are already implemented in Task 1)

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/test_iut_testing.py
git commit -m "test: add unit tests for ivy_iut_test helper functions"
```

---

## Task 3: Add MCP tool registration with config_path and output parsing

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/iut_testing.py` (append `register_iut_testing_tools`)
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/__init__.py` (add metadata)

- [ ] **Step 1: Append the registration function to iut_testing.py**

Add to the end of `iut_testing.py`:

```python


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
        config_path: str | None = None,
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
            config_path: Path to existing experiment config YAML. Overrides
                         generated config when provided.
        """
        if not shutil.which("panther"):
            return {
                "success": False,
                "error": "panther CLI not found on PATH. Install PANTHER first.",
            }

        run_id = str(uuid.uuid4())[:8]
        using_user_config = config_path is not None

        if not using_user_config:
            validation_error = _validate_inputs(
                protocol, test_name, iut_name, ctx.root
            )
            if validation_error:
                return {"success": False, "error": validation_error}

        # Build or load config
        tmp_dir = os.path.join(tempfile.gettempdir(), f"ivy-iut-{run_id}")
        os.makedirs(tmp_dir, exist_ok=True)

        try:
            if using_user_config:
                config = _prepare_user_config(config_path, test_name, timeout)
            else:
                version = version or ""
                config = _build_experiment_config(
                    protocol=protocol,
                    test_name=test_name,
                    iut_name=iut_name,
                    version=version,
                    timeout=timeout,
                    run_id=run_id,
                    extra_params=extra_params,
                )

            final_config_path = os.path.join(tmp_dir, "config.yaml")
            with open(final_config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
        except Exception as exc:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return {"success": False, "error": f"Config error: {exc}"}

        # Record start time for timestamp-based output dir fallback
        wall_start = time.time()
        t0 = time.monotonic()
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                "panther",
                "run",
                "--config",
                final_config_path,
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
            verdict = "pass" if proc.returncode == 0 else "fail"

        except asyncio.TimeoutError:
            duration = time.monotonic() - t0
            if proc is not None:
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

        # Find output directory
        if not using_user_config:
            output_dir = _find_output_dir_deterministic(ctx.root, run_id)
        else:
            output_dir = _find_output_dir_by_timestamp(ctx.root, wall_start)

        # Parse output
        summary = _load_experiment_summary(output_dir)
        iut_logs = _collect_iut_logs(output_dir)

        if summary:
            verdict = _refine_verdict(verdict, summary)

        return {
            "verdict": verdict,
            "test_name": test_name,
            "iut_name": iut_name,
            "protocol": protocol,
            "test_stdout": stdout[-5000:],
            "test_stderr": stderr[-2000:],
            "iut_logs": iut_logs[-3000:] if iut_logs else "",
            "duration_seconds": round(duration, 2),
            "output_dir": output_dir or "",
            "experiment_summary": summary,
            "error": stderr if verdict in ("error", "timeout") else None,
        }
```

- [ ] **Step 2: Add timeout and metadata to __init__.py**

In `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/__init__.py`, add to `_TOOL_TIMEOUTS` dict (after line 52, before the closing `}`):

```python
    "ivy_iut_test": 180.0,
```

Add to `_TOOL_METADATA` dict (after line 123, before the closing `}`):

```python
    "ivy_iut_test": {
        "cost": "high",
        "category": "testing",
        "needs_model": False,
    },
```

- [ ] **Step 3: Verify syntax**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "import ast; ast.parse(open('ivy_lsp/mcp/tools/iut_testing.py').read()); ast.parse(open('ivy_lsp/mcp/tools/__init__.py').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/iut_testing.py panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/mcp/tools/__init__.py
git commit -m "feat: complete ivy_iut_test with config_path, output parsing, validation, and metadata"
```

---

## Task 4: Add async tool tests

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/test_iut_testing.py`

- [ ] **Step 1: Append async tool tests to the test file**

Add to the end of `test_iut_testing.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock


class MockToolContext:
    """Minimal mock for the MCP ToolContext."""

    def __init__(self, root: str):
        self.root = root


class TestIutTestTool:
    """Tests for the registered ivy_iut_test MCP tool."""

    def _make_tool(self, root: str):
        """Create the tool function by calling register_iut_testing_tools."""
        from ivy_lsp.mcp.tools.iut_testing import register_iut_testing_tools

        mock_mcp = MagicMock()
        captured_fn = None

        def capture_tool():
            def decorator(fn):
                nonlocal captured_fn
                captured_fn = fn
                return fn
            return decorator

        mock_mcp.tool = capture_tool
        ctx = MockToolContext(root)
        register_iut_testing_tools(mock_mcp, ctx)
        return captured_fn

    def test_panther_not_found(self, tmp_path):
        tool = self._make_tool(str(tmp_path))
        with patch("shutil.which", return_value=None):
            result = asyncio.run(
                tool(protocol="bgp", test_name="t", iut_name="i")
            )
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_validation_failure(self, tmp_path):
        tool = self._make_tool(str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/panther"):
            result = asyncio.run(
                tool(protocol="nonexistent", test_name="t", iut_name="i")
            )
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_timeout_verdict(self, tmp_path):
        # Create required plugin dirs for validation to pass
        proto = tmp_path / "panther" / "plugins" / "protocols" / "client_server" / "bgp"
        proto.mkdir(parents=True)
        iut = tmp_path / "panther" / "plugins" / "services" / "iut" / "bgp" / "frr_bgp"
        iut.mkdir(parents=True)

        tool = self._make_tool(str(tmp_path))

        async def mock_communicate():
            await asyncio.sleep(10)
            return b"", b""

        mock_proc = AsyncMock()
        mock_proc.communicate = mock_communicate
        mock_proc.kill = MagicMock()

        with patch("shutil.which", return_value="/usr/bin/panther"):
            with patch(
                "asyncio.create_subprocess_exec",
                return_value=mock_proc,
            ):
                result = asyncio.run(
                    tool(
                        protocol="bgp",
                        test_name="test",
                        iut_name="frr_bgp",
                        timeout=1,
                    )
                )

        assert result["verdict"] == "timeout"
        assert result["error"] is not None
```

- [ ] **Step 2: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_iut_testing.py -v`

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/test_iut_testing.py
git commit -m "test: add async integration tests for ivy_iut_test tool"
```

---

## Task 5: Add Phase 5 (IUT Testing) to verify workflow

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/verify/SKILL.md`

- [ ] **Step 1: Renumber Phase 5 → Phase 6, Phase 6 → Phase 7**

In `SKILL.md`, replace:

```markdown
## Phase 5 — Diagnose
```

with:

```markdown
## Phase 6 — Diagnose
```

And replace:

```markdown
## Phase 6 — Fix (optional)
```

with:

```markdown
## Phase 7 — Fix (optional)
```

And update the loop reference inside the Fix phase from:

```markdown
Loop back to Phase 3 (recompile). The cycle is: Phase 3 (compile) -> Phase 4 (execute) -> Phase 5 (diagnose) -> Phase 6 (fix) -> Phase 3 again.
```

to:

```markdown
Loop back to Phase 3 (recompile). The cycle is: Phase 3 (compile) → Phase 4 (execute) → Phase 6 (diagnose) → Phase 7 (fix) → Phase 3 again.
```

- [ ] **Step 2: Insert Phase 5 — IUT Testing after Phase 4**

After the Phase 4 section (after line 127 `---`), insert:

```markdown

## Phase 5 — IUT Testing (optional)

Only entered after Phase 4 succeeds (formal verification passes). Skipped when `invocation_depth > 0` (verify called as sub-workflow from build).

### Step 1: Offer IUT testing

Present the user with the option:

> "Formal verification passed. Want to run this test against a real implementation?"

If the user declines, proceed directly to completion (On Completion section).

### Step 2: Select IUT

Scan `panther/plugins/services/iut/{protocol}/` for available IUT plugin directories. Present as numbered options:

```
Available IUTs for {protocol}:
1. frr_bgp
2. (other IUT if multiple exist)
```

If only one IUT exists, suggest it directly and ask for confirmation.

### Step 3: Execute

Call the MCP tool:

```
ivy_iut_test(protocol=<detected>, test_name=<from Phase 2>, iut_name=<selected>)
```

### On PASS

1. Report: "IUT test passed. `<test_name>` succeeded against `<iut_name>` in {duration_seconds}s."
2. Show `output_dir` for reference.
3. Offer follow-ups: "Run another test? Check coverage? Review model quality?"
4. Update phase to `"iut-pass"`, then proceed to completion.

### On FAIL

1. Present the `iut_logs` content from the tool result.
2. Present key details from `experiment_summary` (test status, error message if any).
3. Show `output_dir`: "Full experiment output at `{output_dir}` — use Read to inspect further."
4. Offer: "Want me to investigate the failure? Or fix it yourself?"
5. If user wants investigation, move to Phase 6 (Diagnose) with the IUT failure context.
6. Update phase to `"iut-fail"`.

### On ERROR or TIMEOUT

1. Present the error details from `test_stderr`.
2. Suggest: "Check Docker status (`docker ps`), verify IUT plugin configuration, and ensure the test binary compiled successfully."
3. Update phase to `"iut-error"`.

### Step 4: Update state

Update active-workflow phase via `update_workflow_phase()`.

---
```

- [ ] **Step 3: Update the Integration section at the end of SKILL.md**

Replace the MCP tools used line:

```markdown
- **MCP tools used:** `ivy_compile`, `ivy_verify`, `ivy_workspace`
```

with:

```markdown
- **MCP tools used:** `ivy_compile`, `ivy_verify`, `ivy_workspace`, `ivy_iut_test`
```

- [ ] **Step 4: Verify SKILL.md renders correctly**

Run: `wc -l panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/verify/SKILL.md`

Expected: ~260 lines (was 199, added ~60 for Phase 5)

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/verify/SKILL.md
git commit -m "feat: add Phase 5 (IUT Testing) to verify workflow, renumber Diagnose→6 Fix→7"
```

---

## Task 6: Create /nct-iut-test shortcut command

**Files:**
- Create: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-iut-test.md`

- [ ] **Step 1: Write the command file**

```markdown
---
name: nct-iut-test
description: Run an Ivy test against an IUT via PANTHER's experiment pipeline
arguments:
  - name: protocol
    description: Protocol name (e.g., "bgp", "quic")
    required: true
  - name: test_name
    description: Ivy test file name without .ivy extension (e.g., "bgp_speaker_test_join")
    required: true
  - name: iut_name
    description: Registered IUT plugin name (e.g., "frr_bgp")
    required: true
  - name: version
    description: Protocol version (default uses protocol's default)
    required: false
  - name: timeout
    description: Total timeout in seconds (default 120)
    required: false
---
> **Shortcut command** — directly calls `ivy_iut_test`. For guided testing with failure diagnosis, use the `verify` workflow.

<!-- MODE: FAST — Single IUT test run, no orchestrator required -->

Run an Ivy test binary against a real Implementation Under Test (IUT) via PANTHER's experiment pipeline.

## Instructions

1. Accept the arguments. If required arguments are missing, ask the user:
   - protocol: "Which protocol? (e.g., bgp, quic)"
   - test_name: "Which test? (e.g., bgp_speaker_test_join)"
   - iut_name: "Which IUT implementation? (e.g., frr_bgp)"

2. Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_iut_test` with:
   - `protocol`: the provided protocol
   - `test_name`: the provided test name
   - `iut_name`: the provided IUT name
   - `version`: the version argument if provided, otherwise omit
   - `timeout`: the timeout argument if provided (as integer), otherwise omit

3. Parse the JSON result containing `verdict`, `test_name`, `iut_name`, `protocol`, `test_stdout`, `test_stderr`, `iut_logs`, `duration_seconds`, `output_dir`, `experiment_summary`, and `error`.

4. Present results in this structured format:

### If verdict is "pass":
```
## IUT Test Result: PASS

**Test:** {test_name}
**IUT:** {iut_name}
**Protocol:** {protocol}
**Duration:** {duration_seconds}s

Test executed successfully against the IUT.

**Output directory:** {output_dir}
```

### If verdict is "fail":
```
## IUT Test Result: FAIL

**Test:** {test_name}
**IUT:** {iut_name}
**Protocol:** {protocol}
**Duration:** {duration_seconds}s

### Test Logs
{iut_logs}

### Experiment Summary
{Format experiment_summary test results: status, error_message if any}

**Output directory:** {output_dir}

### Suggested Actions
- Inspect the full output: `Read {output_dir}/experiment_summary.json`
- Check IUT logs: `Read {output_dir}/{test_subdir}/test.log`
- Use the `verify` workflow for guided failure diagnosis
```

### If verdict is "error" or "timeout":
```
## IUT Test Result: {verdict upper}

**Test:** {test_name}
**IUT:** {iut_name}

### Error
{error}

### Suggested Actions
- Check Docker is running: `docker ps`
- Verify IUT plugin exists: check `panther/plugins/services/iut/{protocol}/{iut_name}/`
- Try compiling first: `/nct-compile {test_file}`
```

**IMPORTANT**: Do NOT run `panther run` directly via Bash. Always use `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_iut_test`.
```

- [ ] **Step 2: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-iut-test.md
git commit -m "feat: add /nct-iut-test shortcut command for direct IUT testing"
```

---

## Task 7: Update plugin CLAUDE.md tool references

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/CLAUDE.md`

- [ ] **Step 1: Add ivy_iut_test to Analysis MCP tools section**

At line 66, after `ivy_diagnostics ... ivy_include_graph, ivy_capabilities`, add a new line:

Replace:

```markdown
**Analysis MCP tools** (read-only, no CLI equivalent):
`ivy_diagnostics` (mode="structural" for fast structural check, mode="full" for 5-layer diagnostics), `ivy_include_graph`, `ivy_capabilities`
```

with:

```markdown
**Analysis MCP tools** (read-only, no CLI equivalent):
`ivy_diagnostics` (mode="structural" for fast structural check, mode="full" for 5-layer diagnostics), `ivy_include_graph`, `ivy_capabilities`

**IUT testing**:
`ivy_iut_test` (run compiled Ivy test against a real IUT via PANTHER experiment pipeline; returns verdict, iut_logs, experiment_summary, output_dir)
```

- [ ] **Step 2: Add /nct-iut-test to Shortcut Commands**

At line 92, replace:

```markdown
`/nct-check` (ivy_verify), `/nct-compile` (ivy_compile), `/nct-model-info` (ivy_model_info), `/nct-health` (9-step diagnostic), `/nct-observability` (JSONL logs)
```

with:

```markdown
`/nct-check` (ivy_verify), `/nct-compile` (ivy_compile), `/nct-model-info` (ivy_model_info), `/nct-iut-test` (ivy_iut_test), `/nct-health` (9-step diagnostic), `/nct-observability` (JSONL logs)
```

- [ ] **Step 3: Update Quick Reference at the end**

At line 141, replace:

```markdown
**Shortcuts**: /nct-check, /nct-compile, /nct-model-info, /nct-health, /nct-observability
```

with:

```markdown
**Shortcuts**: /nct-check, /nct-compile, /nct-model-info, /nct-iut-test, /nct-health, /nct-observability
```

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/CLAUDE.md
git commit -m "docs: add ivy_iut_test and /nct-iut-test to plugin CLAUDE.md reference tables"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run full ivy-lsp test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_iut_testing.py -v`

Expected: All tests PASS

- [ ] **Step 2: Verify MCP tool loads**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -c "from ivy_lsp.mcp.tools.iut_testing import register_iut_testing_tools; print('import OK')"`

Expected: `import OK`

- [ ] **Step 3: Verify command file is valid YAML frontmatter**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin && python -c "
import yaml
with open('commands/nct-iut-test.md') as f:
    content = f.read()
# Extract frontmatter between --- markers
parts = content.split('---', 2)
fm = yaml.safe_load(parts[1])
print(f'Command: {fm[\"name\"]}, args: {len(fm[\"arguments\"])}')
"`

Expected: `Command: nct-iut-test, args: 5`

- [ ] **Step 4: Git status check**

Run: `git status`

Expected: Clean working tree (all changes committed in tasks 1-7)
