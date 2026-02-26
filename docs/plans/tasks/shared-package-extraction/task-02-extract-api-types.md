# Task 02: Extract API Types to panther-ivy-types

## Goal
Copy the 6 pure dataclasses from `panther_ivy/api/types.py` into `panther_ivy_types/api.py`.

## Prerequisites
- Task 01 completed (package scaffolded)

## Source File
`panther/plugins/services/testers/panther_ivy/api/types.py` (79 lines)

## Context
These 6 dataclasses are the public API types for panther_ivy. They are pure Python (stdlib only) with no external dependencies. They use `dataclasses.dataclass` and `dataclasses.asdict`.

## Steps

### Step 1: Write panther_ivy_types/api.py

Copy the full content of `panther_ivy/api/types.py` into `panther_ivy_types/api.py`:

```python
# packages/panther-ivy-types/panther_ivy_types/api.py
"""Data types for the panther_ivy public API.

These types define the command generation and execution result structures
used across the PANTHER Ivy toolchain.
"""
from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class CommandResult:
    """Shell commands with their environment and working directory."""

    commands: List[str]
    environment: Dict[str, str]
    working_dir: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CompileResult:
    """Result of generating compilation commands."""

    setup_commands: CommandResult
    compile_commands: CommandResult

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestRunResult:
    """Result of generating full test execution commands."""

    compile: CompileResult
    run_commands: CommandResult

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiagnosticItem:
    """A single diagnostic (error/warning) from compilation."""

    file: str
    line: int
    column: int
    severity: str  # "error" | "warning" | "info"
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestInfo:
    """Metadata about an available Ivy test specification."""

    name: str
    protocol: str
    version: str
    role: str  # "server" | "client"
    ivy_file: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExecutionResult:
    """Result of executing commands in Docker or on host."""

    exit_code: int
    stdout: str
    stderr: str
    target: str  # "docker" | "host"

    def to_dict(self) -> dict:
        return asdict(self)
```

### Step 2: Write tests

```python
# packages/panther-ivy-types/tests/test_api_types.py
"""Tests for API types."""
from panther_ivy_types.api import (
    CommandResult,
    CompileResult,
    DiagnosticItem,
    ExecutionResult,
    TestInfo,
    TestRunResult,
)


class TestCommandResult:
    def test_create(self):
        r = CommandResult(commands=["echo hi"], environment={"A": "1"}, working_dir="/tmp")
        assert r.commands == ["echo hi"]
        assert r.environment == {"A": "1"}
        assert r.working_dir == "/tmp"

    def test_to_dict(self):
        r = CommandResult(commands=["echo hi"], environment={}, working_dir="/tmp")
        d = r.to_dict()
        assert d == {"commands": ["echo hi"], "environment": {}, "working_dir": "/tmp"}


class TestCompileResult:
    def test_create(self):
        setup = CommandResult(commands=["setup"], environment={}, working_dir="/")
        compile_cmds = CommandResult(commands=["compile"], environment={}, working_dir="/")
        r = CompileResult(setup_commands=setup, compile_commands=compile_cmds)
        assert r.setup_commands.commands == ["setup"]

    def test_to_dict_nested(self):
        setup = CommandResult(commands=[], environment={}, working_dir="/")
        compile_cmds = CommandResult(commands=[], environment={}, working_dir="/")
        r = CompileResult(setup_commands=setup, compile_commands=compile_cmds)
        d = r.to_dict()
        assert "setup_commands" in d
        assert "compile_commands" in d


class TestDiagnosticItem:
    def test_create(self):
        d = DiagnosticItem(file="test.ivy", line=10, column=5, severity="error", message="fail")
        assert d.severity == "error"

    def test_to_dict(self):
        d = DiagnosticItem(file="f.ivy", line=1, column=1, severity="warning", message="warn")
        assert d.to_dict()["severity"] == "warning"


class TestTestInfo:
    def test_create(self):
        t = TestInfo(name="quic_server_test_stream", protocol="quic", version="rfc9000", role="server", ivy_file="test.ivy")
        assert t.protocol == "quic"


class TestExecutionResult:
    def test_create(self):
        r = ExecutionResult(exit_code=0, stdout="ok", stderr="", target="docker")
        assert r.exit_code == 0
        assert r.target == "docker"
```

## Verification
```bash
cd packages/panther-ivy-types
pip install -e ".[dev]"
pytest tests/test_api_types.py -v
```

All 7 tests should pass.

## Commit Message
```
feat(panther-ivy-types): add API types module

Extract 6 dataclasses (CommandResult, CompileResult, TestRunResult,
DiagnosticItem, TestInfo, ExecutionResult) from panther_ivy/api/types.py
into panther_ivy_types/api.py.
```

## Files Modified
- `packages/panther-ivy-types/panther_ivy_types/api.py` (populated)
- `packages/panther-ivy-types/tests/test_api_types.py` (new)
