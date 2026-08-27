# Phase C Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Everything the experiment harness needs before a run can launch: the hermeticity spike (S0), the two missing draft operations with tool/CLI parity, the templated loop prompt with per-arm renderings, and the pristine aioquic workspace with the 2–11 window pre-seeded.

**Architecture:** Product changes land in the `ai_rfc` nested repo's server (`core/draft.py`, tools + CLI twins, parity). The new `experiment/` package (stdlib + PyYAML) sits beside `plugins/` in the same repo and imports the PANTHER substrate as a library via `PANTHER_REPO`, exactly as the server does. The runner/matrix/audit/metrics half of the harness is the follow-up plan `2026-08-26-arfc-phase-c-harness.md`, which consumes the interfaces produced here.

**Tech Stack:** Python ≥3.10, stdlib + PyYAML (`mcp` only for the FastMCP server); pytest; git; Claude Code CLI 2.1.246 (spike only, never in tests).

**Spec:** `docs/superpowers/specs/2026-08-26-arfc-phase-c-experiment-harness-design.md` (D19–D28, §1–§3, §6) on top of `docs/superpowers/specs/2026-08-25-arfc-progressive-rfc-design.md` (D1–D18).

## Global Constraints

- Paths (every command below assumes these shell variables):
  - `W=/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/iut-ai-rfc` (PANTHER worktree root; run PANTHER commands from here)
  - `R=$W/panther/plugins/services/testers/a_rfc/ai_rfc` (the nested `ai_rfc` git repo — its own history, commits styled `feat: …`/`test: …`/`docs: …`/`refactor: …` with no scope)
  - `S=$R/plugins/ai-rfc/server` (the MCP server + `arfc` CLI package)
  - `PY=/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.venv/bin/python` (imports `panther` from this worktree, has `mcp` and `pyyaml`)
- **NEVER run `panther_builder.py package-dev`/`clean` in this tree** — it rm -rf's `docs/` (memory `feedback_panther_builder_wipes_docs`).
- Pytest needs the `SSLKEYLOGFILE=` prefix (the env var trips the sandbox at aiohttp import).
- Writes into a nested `.git` (commits/tags/clone/init inside `$R`, inside test-built draft repos run by hand, or under `~/arfc-experiments`) need the sandbox disabled; pytest-created temp repos are fine.
- Two repos, two commit targets: PANTHER commits use `feat(a_rfc): …`/`test(a_rfc): …`/`docs(a_rfc): …`/`chore(a_rfc): …`; nested-repo commits use `git -C $R add <explicit paths> && git -C $R commit -m "…"`. Never `git add -A`/`.`. The submodule pointer is bumped in PANTHER once, in Task 10. Never push the nested repo without asking (outward-facing).
- `experiment/` and the server stay stdlib + PyYAML; no network in tests; no real `claude` in tests; diagnostics to stderr via a `_report` helper (never `logging` — `panther.*` loggers swallow warnings); Google-style docstrings on public functions; no WHAT comments; black at 88.
- Environment contract everywhere: `PANTHER_REPO=$W`, `ARFC_WORKSPACE=<one workspace>`; the runs root is `ARFC_EXPERIMENTS_ROOT` (default `~/arfc-experiments`), always outside the PANTHER tree.
- Per-task gates: server suite `cd $S && SSLKEYLOGFILE= $PY -m pytest -q`; experiment suite `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`; PANTHER a_rfc suite `cd $W && SSLKEYLOGFILE= $PY -m pytest tests/unit/plugins/services/testers/a_rfc -n auto -q`. Format touched Python with `$PY -m black` (88).
- The nested repo has no pre-commit; PANTHER's pre-commit (black/isort/ruff D1xx) runs on PANTHER commits only.

---

### Task 0: Baseline

**Files:** none modified.

- [ ] **Step 1: Verify both repos are clean and where the spec says**

Run: `cd $W && git status --short && git branch --show-current && git log --oneline -1 && git -C $R status --short && git -C $R log --oneline -1`
Expected: no status lines; `feat/arfc-progressive-rfc`; PANTHER HEAD at or after `f9c73ef5b docs(a_rfc): Phase C experiment harness design spec`; nested repo clean at `51bdcb9`.

- [ ] **Step 2: Verify the toolchain**

Run: `$PY -c "import mcp, yaml, panther; print(panther.__file__)" && claude --version && which sqlite3`
Expected: the `panther/__init__.py` path under `$W`; `2.1.246 (Claude Code)`; `/usr/bin/sqlite3`.

- [ ] **Step 3: Baseline test runs**

Run: `cd $W && SSLKEYLOGFILE= $PY -m pytest tests/unit/plugins/services/testers/a_rfc -n auto -q 2>&1 | tail -2 && cd $S && SSLKEYLOGFILE= $PY -m pytest -q 2>&1 | tail -2`
Expected: `206 passed` (PANTHER a_rfc) and `25 passed` (server). If either differs, STOP and report the failure verbatim.

### Task 1: Prove an empty manifest checkpoints (PANTHER)

The pre-seeding design (D27) rests on `write_checkpoint` accepting `requirements: {}`. Code reading says it does; no test says so.

**Files:**
- Test: `tests/unit/plugins/services/testers/a_rfc/draft/test_checkpoint.py` (append)

- [ ] **Step 1: Append the characterization test**

```python
def test_empty_manifest_checkpoints_with_zero_counts(
    timeline_dir: Path, tmp_path: Path
):
    import yaml

    manifest = tmp_path / "empty.yaml"
    manifest.write_text("rfc: SPEC-0\ntitle: 'Nothing yet'\nrequirements: {}\n")
    checkpoint_dir = write_checkpoint(
        manifest, timeline_dir, _pr_cluster_id(timeline_dir), tmp_path / "c"
    )
    record = json.loads((checkpoint_dir / "checkpoint.json").read_text())
    zero = {"gap": 0, "inferred": 0, "confirmed": 0}
    assert record["adjudication"] == {
        "count_by_stored": zero,
        "count_by_supported": zero,
        "promotable_count": 0,
        "violation_count": 0,
    }
    stored = yaml.safe_load((checkpoint_dir / "manifest.yaml").read_text())
    assert stored == {"rfc": "SPEC-0", "title": "Nothing yet", "requirements": {}}
    assert verify_checkpoint(checkpoint_dir) is None
```

- [ ] **Step 2: Run it**

Run: `cd $W && SSLKEYLOGFILE= $PY -m pytest tests/unit/plugins/services/testers/a_rfc/draft/test_checkpoint.py -q -k empty_manifest`
Expected: PASS on the first run — this is a characterization test guarding an existing behaviour. If it FAILS, the pre-seeding design is blocked: STOP and report (do not change the substrate on your own).

- [ ] **Step 3: Commit (PANTHER)**

```bash
cd $W && git add tests/unit/plugins/services/testers/a_rfc/draft/test_checkpoint.py
git commit -m "test(a_rfc): checkpoint an empty manifest with zero counts"
```

### Task 2: Expose the fixture workspace builder as `ai_rfc_server.testing`

The experiment tests (Tasks 5, 9 and the harness plan) need the same twin-capable workspace the server tests build. Move it out of `conftest.py` so it is importable.

**Files:**
- Create: `$S/src/ai_rfc_server/testing.py`
- Modify: `$S/tests/conftest.py` (drop the moved code, import instead)

**Interfaces:**
- Produces: `ai_rfc_server.testing.build_workspace(root: Path) -> Path` (builds `root` as a complete workspace: `clone/`, `corpus/`, `timeline/`, `clusters/`, `manifest.yaml` with claims `t:1.1` and `t:2.1`, empty `questions.yaml`/`revisions.yaml`, `interviews/`, and a `draft/` git repo whose `draft-test-spec.md` cites `` `a_rfc:t:1.1` ``, all with pinned commit dates so two builds are byte-identical) and `ai_rfc_server.testing.git(repo: Path, *args: str, date: str | None = None) -> str` (checked git call returning stripped stdout; `date` pins both author and committer dates).

- [ ] **Step 1: Create `testing.py`** with the module docstring below, then move `_run` (renamed `git`) and `_build_workspace` (renamed `build_workspace`) from `conftest.py` into it **unchanged in behaviour** (same commands, same dates, same manifest text). Module docstring:

```python
"""Fixture workspaces built through the substrate's own code.

Commit dates are pinned so two builds produce byte-identical corpora; the
parity tests compare twin workspaces byte-for-byte, and the experiment
harness reuses the same builder for its own tests. Importable without the
``mcp`` package.
"""
```

`build_workspace` keeps its lazy `from panther.plugins.services.testers.a_rfc…` imports inside the function (the caller puts `PANTHER_REPO` on `sys.path`; nothing here guesses where PANTHER is).

- [ ] **Step 2: Rewrite `conftest.py`** to keep only the `sys.path` setup and the two fixtures, importing the builder:

```python
import sys
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[1]
PANTHER_ROOT = Path(__file__).resolve().parents[10]

for entry in (str(SERVER_ROOT / "src"), str(PANTHER_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from ai_rfc_server.testing import build_workspace  # noqa: E402


@pytest.fixture
def make_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A workspace factory plus an env switcher, for twin-workspace tests."""

    def build(name: str) -> Path:
        return build_workspace(tmp_path / name)

    def use(root: Path) -> None:
        monkeypatch.setenv("PANTHER_REPO", str(PANTHER_ROOT))
        monkeypatch.setenv("ARFC_WORKSPACE", str(root))

    return build, use


@pytest.fixture
def workspace(make_workspace):
    build, use = make_workspace
    root = build("ws")
    use(root)

    from ai_rfc_server.paths import resolve_context

    return resolve_context()
```

- [ ] **Step 3: Run the server suite**

Run: `cd $S && SSLKEYLOGFILE= $PY -m pytest -q 2>&1 | tail -2`
Expected: `25 passed`.

- [ ] **Step 4: Commit (nested repo)**

```bash
git -C $R add plugins/ai-rfc/server/src/ai_rfc_server/testing.py plugins/ai-rfc/server/tests/conftest.py
git -C $R commit -m "refactor: expose the fixture workspace builder as ai_rfc_server.testing"
```

### Task 3: `experiment/` package scaffold, roots, profile init, CLI

**Files:**
- Create: `$R/experiment/__init__.py`, `$R/experiment/paths.py`, `$R/experiment/profile.py`, `$R/experiment/cli.py`, `$R/experiment/__main__.py`, `$R/experiment/tests/__init__.py`, `$R/experiment/tests/conftest.py`, `$R/experiment/tests/test_profile.py`
- Modify: `$R/README.md` (add the "Experiment harness" paragraph at the end)

**Interfaces:**
- Produces: `experiment.ExperimentError(RuntimeError)`; `experiment.paths.default_root() -> Path` (`ARFC_EXPERIMENTS_ROOT` or `~/arfc-experiments`, expanded); `experiment.paths.profile_dir(root: Path) -> Path` (`root/"profile"`); `experiment.profile.init_profile(root: Path) -> Path` (creates the profile dir, idempotent); `experiment.profile.login_command(root: Path) -> str`; `experiment.cli.main(argv: list[str] | None = None) -> int` with subcommand `profile init [--root PATH]`; every later task registers its subcommand in `experiment.cli._parser`.

- [ ] **Step 1: Write the failing tests** (`experiment/tests/conftest.py` first — every experiment test depends on it):

```python
"""Path setup shared by the experiment tests.

The experiment package imports the server core and the PANTHER substrate
as libraries; the paths are derived from this file's location so the
tests run from any cwd without an installed package.
"""

import sys
from pathlib import Path

import pytest

AI_RFC_ROOT = Path(__file__).resolve().parents[2]
SERVER_SRC = AI_RFC_ROOT / "plugins" / "ai-rfc" / "server" / "src"
PANTHER_ROOT = AI_RFC_ROOT.parents[5]

for entry in (str(AI_RFC_ROOT), str(SERVER_SRC), str(PANTHER_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)


@pytest.fixture
def panther_repo() -> Path:
    assert (PANTHER_ROOT / "panther" / "plugins").is_dir(), PANTHER_ROOT
    return PANTHER_ROOT


@pytest.fixture
def plugin_root() -> Path:
    return AI_RFC_ROOT / "plugins" / "ai-rfc"


@pytest.fixture
def fixture_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One complete fixture workspace with the env contract pointing at it."""
    from ai_rfc_server.testing import build_workspace

    root = build_workspace(tmp_path / "ws")
    monkeypatch.setenv("PANTHER_REPO", str(PANTHER_ROOT))
    monkeypatch.setenv("ARFC_WORKSPACE", str(root))
    return root
```

`experiment/tests/test_profile.py`:

```python
from pathlib import Path

from experiment import cli
from experiment.paths import default_root, profile_dir
from experiment.profile import init_profile, login_command


def test_default_root_honours_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ARFC_EXPERIMENTS_ROOT", str(tmp_path / "exp"))
    assert default_root() == tmp_path / "exp"
    monkeypatch.delenv("ARFC_EXPERIMENTS_ROOT")
    assert default_root() == Path("~/arfc-experiments").expanduser()


def test_init_profile_creates_dir_and_names_login(tmp_path):
    profile = init_profile(tmp_path)
    assert profile == profile_dir(tmp_path) and profile.is_dir()
    assert (profile / "README-arfc.txt").exists()
    assert init_profile(tmp_path) == profile
    assert login_command(tmp_path) == (
        f"CLAUDE_CONFIG_DIR={profile} claude auth login"
    )


def test_cli_profile_init_prints_login_command(tmp_path, capsys):
    assert cli.main(["profile", "init", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "claude auth login" in out and str(tmp_path / "profile") in out
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment'`.

- [ ] **Step 3: Implement**

`experiment/__init__.py`:

```python
"""The AI+MCP vs AI+CLI experiment harness over the ai_rfc plugin.

Model-driven orchestration lives here, outside PANTHER's framework
boundary: preparing pristine workspaces, launching hermetic ``claude -p``
sessions per arm, auditing their transcripts and recomputing outcomes from
workspace state. Nothing here is imported by the plugin or the substrate.
"""

from __future__ import annotations


class ExperimentError(RuntimeError):
    """Raised when the harness cannot proceed as asked."""
```

`experiment/paths.py`:

```python
"""Where the harness keeps its state: a runs root outside every CLAUDE.md ancestry."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ROOT = "~/arfc-experiments"


def default_root() -> Path:
    """The runs root: ``ARFC_EXPERIMENTS_ROOT`` or ``~/arfc-experiments``."""
    return Path(os.environ.get("ARFC_EXPERIMENTS_ROOT", DEFAULT_ROOT)).expanduser()


def profile_dir(root: Path) -> Path:
    """The isolated Claude Code config directory under ``root``."""
    return root / "profile"
```

`experiment/profile.py`:

```python
"""The isolated Claude Code profile every experiment session runs under."""

from __future__ import annotations

from pathlib import Path

from .paths import profile_dir

_README = """This directory is a CLAUDE_CONFIG_DIR for the a_rfc experiment harness.
It holds no user settings, plugins or hooks on purpose. Log in once with:

    {login}

and never point an interactive session here.
"""


def login_command(root: Path) -> str:
    """The one-time login the user runs to authenticate the profile."""
    return f"CLAUDE_CONFIG_DIR={profile_dir(root)} claude auth login"


def init_profile(root: Path) -> Path:
    """Create the profile directory (idempotent) and its README.

    Args:
        root: The runs root.

    Returns:
        The profile directory.
    """
    profile = profile_dir(root)
    profile.mkdir(parents=True, exist_ok=True)
    (profile / "README-arfc.txt").write_text(_README.format(login=login_command(root)))
    return profile
```

`experiment/cli.py`:

```python
"""The ``python -m experiment`` command-line surface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import ExperimentError
from .paths import default_root
from .profile import init_profile, login_command


def _report(message: str) -> None:
    print(message, file=sys.stderr)


def _add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Runs root (default: ARFC_EXPERIMENTS_ROOT or ~/arfc-experiments).",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="experiment",
        description="AI+MCP vs AI+CLI experiment harness over the ai_rfc plugin.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    profile = commands.add_parser("profile", help="Isolated Claude Code profile.")
    profile_verbs = profile.add_subparsers(dest="verb", required=True)
    profile_init = profile_verbs.add_parser("init", help="Create the profile dir.")
    _add_root(profile_init)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one harness command.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, 1 when the harness refused or an input was unusable.
    """
    args = _parser().parse_args(argv)
    root = args.root if getattr(args, "root", None) else default_root()
    try:
        if args.command == "profile" and args.verb == "init":
            profile = init_profile(root)
            print(f"profile: {profile}")
            print(f"log in once with:\n  {login_command(root)}")
    except (ExperimentError, OSError) as error:
        _report(f"error: {error}")
        return 1
    return 0
```

`experiment/__main__.py`:

```python
import sys

from .cli import main

sys.exit(main())
```

`experiment/tests/__init__.py`: empty. README paragraph (append to `$R/README.md`):

```markdown
## Experiment harness

`experiment/` runs the AI+MCP vs AI+CLI comparison the protocol in
`docs/experiment-protocol.md` describes: `python -m experiment profile init`
creates the isolated Claude Code profile, `workspace prepare` builds a
pristine reconstruction workspace, and the campaign commands (see the
harness plan) launch, audit and analyze runs. State lives under
`ARFC_EXPERIMENTS_ROOT` (default `~/arfc-experiments`), never inside a
repository.
```

- [ ] **Step 4: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 3 passed.

- [ ] **Step 5: Commit (nested repo)**

```bash
git -C $R add experiment/__init__.py experiment/paths.py experiment/profile.py experiment/cli.py experiment/__main__.py experiment/tests/__init__.py experiment/tests/conftest.py experiment/tests/test_profile.py README.md
git -C $R commit -m "feat: experiment package scaffold with the isolated profile"
```

### Task 4: `experiment/arms.py` — enforcement profiles and flag rendering

The per-arm surface table of spec §2, as data plus two pure renderers. The spike (Task 5) and the runner (harness plan) both consume it.

**Files:**
- Create: `$R/experiment/arms.py`, `$R/experiment/tests/test_arms.py`

**Interfaces:**
- Produces: `ARMS = ("A", "B", "C")`; `READ_TOOLS`; `RAW_SUBSTRATE`; `ArmProfile(arm, label, tools, allowed_tools, uses_mcp)`; `PROFILES: dict[str, ArmProfile]`; `profile(arm: str) -> ArmProfile`; `constant_flags(*, model, effort, budget_usd, prompt_file) -> list[str]`; `arm_flags(arm_profile, mcp_config_path: Path | None) -> list[str]`; `mcp_config(*, python, server_src, panther_repo, workspace) -> dict`; `build_argv(*, claude_bin, prompt, arm_profile, mcp_config_path, model, effort, budget_usd, prompt_file) -> list[str]`.

- [ ] **Step 1: Write the failing tests** (`experiment/tests/test_arms.py`):

```python
import pytest

from experiment import ExperimentError
from experiment.arms import (
    ARMS,
    arm_flags,
    build_argv,
    constant_flags,
    mcp_config,
    profile,
)


def _value(flags: list[str], name: str) -> str:
    return flags[flags.index(name) + 1]


def test_arm_a_has_no_bash_and_mounts_mcp(tmp_path):
    flags = arm_flags(profile("A"), tmp_path / "arfc.json")
    assert "Bash" not in _value(flags, "--tools").split(",")
    assert "mcp__arfc" in _value(flags, "--allowedTools").split(",")
    assert _value(flags, "--mcp-config") == str(tmp_path / "arfc.json")
    assert "--strict-mcp-config" in flags


def test_arms_b_and_c_allow_exactly_their_command_family():
    b = arm_flags(profile("B"), None)
    c = arm_flags(profile("C"), None)
    assert "Bash" in _value(b, "--tools").split(",")
    assert _value(b, "--allowedTools").split(",")[-1] == "Bash(arfc *)"
    allowed_c = _value(c, "--allowedTools").split(",")
    assert "Bash(python -m panther.plugins.services.testers.a_rfc*)" in allowed_c
    assert "Bash(git *)" in allowed_c and "Bash(sqlite3 *)" in allowed_c
    assert "Bash(arfc *)" not in allowed_c and "mcp__arfc" not in allowed_c
    for flags in (b, c):
        assert "--mcp-config" not in flags and "--strict-mcp-config" in flags


def test_mcp_mount_is_required_and_refused_per_arm(tmp_path):
    with pytest.raises(ExperimentError):
        arm_flags(profile("A"), None)
    with pytest.raises(ExperimentError):
        arm_flags(profile("B"), tmp_path / "x.json")
    with pytest.raises(ExperimentError):
        profile("D")
    assert ARMS == ("A", "B", "C")


def test_constant_flags_pin_the_harness(tmp_path):
    flags = constant_flags(
        model="claude-opus-5", effort="high", budget_usd=25, prompt_file=tmp_path / "p"
    )
    assert _value(flags, "--model") == "claude-opus-5"
    assert _value(flags, "--effort") == "high"
    assert _value(flags, "--permission-mode") == "dontAsk"
    assert _value(flags, "--max-budget-usd") == "25"
    assert _value(flags, "--setting-sources") == "project"
    assert _value(flags, "--output-format") == "stream-json"
    assert "--disable-slash-commands" in flags and "--verbose" in flags
    assert _value(flags, "--append-system-prompt-file") == str(tmp_path / "p")


def test_mcp_config_uses_absolute_paths(tmp_path):
    config = mcp_config(
        python="/venv/bin/python",
        server_src=tmp_path / "src",
        panther_repo=tmp_path / "W",
        workspace=tmp_path / "ws",
    )
    server = config["mcpServers"]["arfc"]
    assert server["command"] == "/venv/bin/python"
    assert server["args"][0] == "-c" and str(tmp_path / "src") in server["args"][1]
    assert server["env"] == {
        "PANTHER_REPO": str(tmp_path / "W"),
        "ARFC_WORKSPACE": str(tmp_path / "ws"),
    }


def test_build_argv_starts_with_print_mode(tmp_path):
    argv = build_argv(
        claude_bin="claude",
        prompt="go",
        arm_profile=profile("B"),
        mcp_config_path=None,
        model="m",
        effort="high",
        budget_usd=1,
        prompt_file=tmp_path / "p",
    )
    assert argv[:3] == ["claude", "-p", "go"]
    assert "--tools" in argv and "--allowedTools" in argv
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_arms.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment.arms'`.

- [ ] **Step 3: Implement `experiment/arms.py`**

```python
"""Per-arm enforcement profiles: which surfaces a session may reach.

Enforcement is by removal (arm A has no Bash tool at all) or by allowlist
(arms B and C may run exactly one command family); everything else is
auto-denied by ``claude -p`` and counted by the audit as a bypass attempt.
The MCP server is mounted only in arm A, through a rendered config with
absolute paths, and ``--strict-mcp-config`` keeps every other server out.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import ExperimentError

ARMS = ("A", "B", "C")
READ_TOOLS = ("Read", "Edit", "Write", "Grep", "Glob")
RAW_SUBSTRATE = "Bash(python -m panther.plugins.services.testers.a_rfc*)"


@dataclass(frozen=True)
class ArmProfile:
    """One arm's surface: built-in tools, allowlist, and whether MCP mounts."""

    arm: str
    label: str
    tools: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    uses_mcp: bool


PROFILES: dict[str, ArmProfile] = {
    "A": ArmProfile(
        arm="A",
        label="class 1: structured-typed (arfc MCP tools)",
        tools=READ_TOOLS,
        allowed_tools=READ_TOOLS + ("mcp__arfc",),
        uses_mcp=True,
    ),
    "B": ArmProfile(
        arm="B",
        label="class 2: hybrid shell-via-tool (arfc CLI through Bash)",
        tools=READ_TOOLS + ("Bash",),
        allowed_tools=READ_TOOLS + ("Bash(arfc *)",),
        uses_mcp=False,
    ),
    "C": ArmProfile(
        arm="C",
        label="class 2: hybrid shell-via-tool (raw substrate through Bash)",
        tools=READ_TOOLS + ("Bash",),
        allowed_tools=READ_TOOLS + (RAW_SUBSTRATE, "Bash(git *)", "Bash(sqlite3 *)"),
        uses_mcp=False,
    ),
}


def profile(arm: str) -> ArmProfile:
    """Return the enforcement profile of ``arm``.

    Raises:
        ExperimentError: If ``arm`` is not one of :data:`ARMS`.
    """
    try:
        return PROFILES[arm]
    except KeyError:
        raise ExperimentError(
            f"unknown arm {arm!r}; arms are {', '.join(ARMS)}"
        ) from None


def constant_flags(
    *, model: str, effort: str, budget_usd: float, prompt_file: Path
) -> list[str]:
    """Flags identical across arms — the protocol's "one harness" constant."""
    return [
        "--output-format",
        "stream-json",
        "--verbose",
        "--append-system-prompt-file",
        str(prompt_file),
        "--disable-slash-commands",
        "--setting-sources",
        "project",
        "--model",
        model,
        "--effort",
        effort,
        "--permission-mode",
        "dontAsk",
        "--max-budget-usd",
        f"{budget_usd:g}",
    ]


def arm_flags(arm_profile: ArmProfile, mcp_config_path: Path | None) -> list[str]:
    """Flags that differ by arm: built-in tool set, allowlist, MCP mount.

    Tool lists are passed comma-joined as one argument so a following flag
    can never be swallowed as a tool name.

    Raises:
        ExperimentError: If an MCP config is missing for arm A or given for
            an arm that must not mount one.
    """
    if arm_profile.uses_mcp and mcp_config_path is None:
        raise ExperimentError(
            f"arm {arm_profile.arm} mounts the MCP server; a config path is required"
        )
    if not arm_profile.uses_mcp and mcp_config_path is not None:
        raise ExperimentError(f"arm {arm_profile.arm} must not mount an MCP server")
    flags = [
        "--tools",
        ",".join(arm_profile.tools),
        "--allowedTools",
        ",".join(arm_profile.allowed_tools),
        "--strict-mcp-config",
    ]
    if mcp_config_path is not None:
        flags += ["--mcp-config", str(mcp_config_path)]
    return flags


def mcp_config(
    *, python: str, server_src: Path, panther_repo: Path, workspace: Path
) -> dict[str, Any]:
    """The rendered MCP config mounting the ``arfc`` server for one run."""
    bootstrap = (
        f"import sys; sys.path.insert(0, {str(server_src)!r}); "
        "from ai_rfc_server.server import main; main()"
    )
    return {
        "mcpServers": {
            "arfc": {
                "command": python,
                "args": ["-c", bootstrap],
                "env": {
                    "PANTHER_REPO": str(panther_repo),
                    "ARFC_WORKSPACE": str(workspace),
                },
            }
        }
    }


def build_argv(
    *,
    claude_bin: str,
    prompt: str,
    arm_profile: ArmProfile,
    mcp_config_path: Path | None,
    model: str,
    effort: str,
    budget_usd: float,
    prompt_file: Path,
) -> list[str]:
    """The complete ``claude -p`` argument vector for one run."""
    return [
        claude_bin,
        "-p",
        prompt,
        *constant_flags(
            model=model, effort=effort, budget_usd=budget_usd, prompt_file=prompt_file
        ),
        *arm_flags(arm_profile, mcp_config_path),
    ]
```

- [ ] **Step 4: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 9 passed.

- [ ] **Step 5: Commit (nested repo)**

```bash
git -C $R add experiment/arms.py experiment/tests/test_arms.py
git -C $R commit -m "feat: per-arm enforcement profiles and claude flag rendering"
```

### Task 5: Spike S0 — stream readers, the spike module, the manual run, go/no-go

Spec §2 "Spike S0". Tests cover the stream readers and the pure parts of the spike (invocation building, evaluation on canned events); the real `claude` calls happen once, by hand, in Step 8.

**Files:**
- Create: `$R/experiment/stream.py`, `$R/experiment/spike.py`, `$R/experiment/tests/test_stream.py`, `$R/experiment/tests/test_spike.py`, `$R/experiment/tests/fixtures/stream/denied-bash.jsonl`, `$R/docs/spike-s0.md` (Step 9)
- Modify: `$R/experiment/cli.py` (add `spike`)

**Interfaces:**
- Produces (`experiment.stream`): `parse_stream(text) -> list[dict]`; `init_event(events) -> dict | None`; `result_event(events) -> dict | None`; `tool_uses(events) -> list[dict]` (`{index, id, name, input}`); `tool_results(events) -> dict[str, dict]` (tool_use_id → `{index, is_error, text}`); `denials(events) -> list[dict]` (`{source, tool, detail}`); `assistant_text(events) -> str`; `usage_series(events) -> list[dict]` (cumulative `input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, total` after each distinct assistant message). The harness plan's audit and metrics consume these.
- Produces (`experiment.spike`): `CHECKS`; `Invocation(name, argv, env, cwd)`; `build_invocations(*, root, panther_repo, plugin_dir, workspace, claude_bin, model) -> list[Invocation]`; `run_claude(invocation, timeout_s) -> dict` (`{exit_code, events, stderr, timed_out}`); `evaluate(outcomes: dict[str, dict], workspace: Path) -> list[dict]` (`{check, passed, required, evidence}`); `run_spike(*, root, panther_repo, plugin_dir, claude_bin, model, timeout_s) -> dict` (writes `<root>/spike-report.json`).

- [ ] **Step 1: Write the stream fixture** `experiment/tests/fixtures/stream/denied-bash.jsonl` (the documented stream-json envelope; the manual run in Step 8 captures the real shape and the harness plan replaces this fixture where they differ):

```json
{"type":"system","subtype":"init","session_id":"s1","model":"claude-opus-5","tools":["Read","Edit","Write","Grep","Glob","Bash"],"mcp_servers":[],"slash_commands":[],"apiKeySource":"none"}
{"type":"assistant","message":{"id":"m1","role":"assistant","content":[{"type":"tool_use","id":"tu1","name":"Bash","input":{"command":"echo bypass-probe"}}],"usage":{"input_tokens":10,"output_tokens":5,"cache_creation_input_tokens":0,"cache_read_input_tokens":0}}}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"tu1","is_error":true,"content":"Permission denied: Bash(echo bypass-probe) is not in the allowed tools"}]}}
{"type":"assistant","message":{"id":"m2","role":"assistant","content":[{"type":"text","text":"DENIED"}],"usage":{"input_tokens":12,"output_tokens":3,"cache_creation_input_tokens":4,"cache_read_input_tokens":6}}}
{"type":"result","subtype":"success","is_error":false,"result":"DENIED","total_cost_usd":0.01,"usage":{"input_tokens":22,"output_tokens":8,"cache_creation_input_tokens":4,"cache_read_input_tokens":6},"modelUsage":{},"num_turns":2,"duration_ms":1000,"duration_api_ms":800,"session_id":"s1","permission_denials":[{"tool_name":"Bash","tool_input":{"command":"echo bypass-probe"}}]}
```

- [ ] **Step 2: Write the failing tests**

`experiment/tests/test_stream.py`:

```python
from pathlib import Path

import pytest

from experiment import ExperimentError
from experiment.stream import (
    assistant_text,
    denials,
    init_event,
    parse_stream,
    result_event,
    tool_results,
    tool_uses,
    usage_series,
)

FIXTURES = Path(__file__).parent / "fixtures" / "stream"


@pytest.fixture
def denied():
    return parse_stream((FIXTURES / "denied-bash.jsonl").read_text())


def test_parse_stream_rejects_malformed_lines():
    with pytest.raises(ExperimentError) as excinfo:
        parse_stream('{"type":"result"}\nnot json\n')
    assert "line 2" in str(excinfo.value)
    assert parse_stream("\n\n") == []


def test_init_and_result_events(denied):
    assert init_event(denied)["tools"][-1] == "Bash"
    assert result_event(denied)["total_cost_usd"] == 0.01
    assert init_event([]) is None and result_event([]) is None


def test_tool_uses_and_results_are_linked(denied):
    uses = tool_uses(denied)
    assert uses == [
        {"index": 1, "id": "tu1", "name": "Bash", "input": {"command": "echo bypass-probe"}}
    ]
    results = tool_results(denied)
    assert results["tu1"]["is_error"] is True
    assert "Permission denied" in results["tu1"]["text"]


def test_denials_come_from_both_sources(denied):
    found = denials(denied)
    assert [d["source"] for d in found] == ["tool_result", "result"]
    assert found[0]["tool"] == "Bash" and found[1]["tool"] == "Bash"


def test_assistant_text_and_usage_series(denied):
    assert assistant_text(denied) == "DENIED"
    series = usage_series(denied)
    assert [s["total"] for s in series] == [15, 40]
    assert series[-1]["cache_read_input_tokens"] == 6


def test_usage_series_counts_each_message_once():
    events = parse_stream(
        '{"type":"assistant","message":{"id":"m1","content":[{"type":"text","text":"a"}],"usage":{"input_tokens":5,"output_tokens":1}}}\n'
        '{"type":"assistant","message":{"id":"m1","content":[{"type":"text","text":"b"}],"usage":{"input_tokens":5,"output_tokens":1}}}\n'
    )
    assert [s["total"] for s in usage_series(events)] == [6]
```

`experiment/tests/test_spike.py`:

```python
import json
from pathlib import Path

from experiment.spike import CHECKS, build_invocations, evaluate
from experiment.stream import parse_stream

FIXTURES = Path(__file__).parent / "fixtures" / "stream"


def _outcome(events, exit_code=0):
    return {"exit_code": exit_code, "events": events, "stderr": "", "timed_out": False}


def _invocations(tmp_path):
    return build_invocations(
        root=tmp_path / "root",
        panther_repo=tmp_path / "W",
        plugin_dir=tmp_path / "plugin",
        workspace=tmp_path / "ws",
        claude_bin="claude",
        model="claude-opus-5",
    )


def test_invocations_cover_every_check_in_order(tmp_path):
    names = [inv.name for inv in _invocations(tmp_path)]
    assert names == [
        "auth",
        "hooks_isolated",
        "hooks_control",
        "claude_md_control",
        "claude_md_isolated",
        "arm_surface_A",
        "arm_surface_B",
        "arm_surface_C",
        "draft_commit",
        "plugin_mcp_env",
        "plugin_mcp_noenv",
        "denial",
        "append_prompt",
    ]
    assert len(CHECKS) == 9


def test_isolated_invocations_use_the_profile_and_controls_do_not(tmp_path):
    by_name = {inv.name: inv for inv in _invocations(tmp_path)}
    profile = str(tmp_path / "root" / "profile")
    assert by_name["auth"].env["CLAUDE_CONFIG_DIR"] == profile
    assert "CLAUDE_CONFIG_DIR" not in by_name["hooks_control"].env
    assert by_name["hooks_control"].cwd == tmp_path / "W"
    assert by_name["claude_md_control"].cwd == tmp_path / "root" / "spike" / "canary" / "sub"
    assert by_name["plugin_mcp_env"].env["PANTHER_REPO"] == str(tmp_path / "W")
    assert "PANTHER_REPO" not in by_name["plugin_mcp_noenv"].env
    for name, inv in by_name.items():
        assert inv.argv[:2] == ("claude", "-p"), name
        assert "--max-budget-usd" in inv.argv, name


def test_arm_surface_invocations_carry_their_arm_flags(tmp_path):
    by_name = {inv.name: inv for inv in _invocations(tmp_path)}
    a = by_name["arm_surface_A"].argv
    assert "--mcp-config" in a and "Bash" not in a[a.index("--tools") + 1].split(",")
    b = by_name["arm_surface_B"].argv
    assert "Bash(arfc *)" in b[b.index("--allowedTools") + 1]
    assert "--disable-slash-commands" in a and "--disable-slash-commands" in b


def test_evaluate_denial_check_on_fixture(tmp_path):
    events = parse_stream((FIXTURES / "denied-bash.jsonl").read_text())
    checks = {c["check"]: c for c in evaluate({"denial": _outcome(events)}, tmp_path)}
    assert checks["denial"]["passed"] is True
    leaked = json.loads(json.dumps(events))
    leaked[2]["message"]["content"][0]["is_error"] = False
    leaked[2]["message"]["content"][0]["content"] = "bypass-probe"
    leaked[4]["permission_denials"] = []
    checks = {c["check"]: c for c in evaluate({"denial": _outcome(leaked)}, tmp_path)}
    assert checks["denial"]["passed"] is False


def test_evaluate_marks_missing_outcomes_failed(tmp_path):
    checks = {c["check"]: c for c in evaluate({}, tmp_path)}
    assert set(checks) == set(CHECKS)
    assert all(check["passed"] is False for check in checks.values())
    assert checks["auth"]["required"] is True and checks["draft_commit"]["required"] is False
```

- [ ] **Step 3: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_stream.py experiment/tests/test_spike.py -q`
Expected: FAIL with `ModuleNotFoundError` for `experiment.stream` / `experiment.spike`.

- [ ] **Step 4: Implement `experiment/stream.py`**

```python
"""Readers for the ``claude -p --output-format stream-json`` event stream.

One JSON object per line. The helpers tolerate absent fields — the stream's
shape is documented only in part, and spike S0 records the real one — but
never a malformed line, which is a harness failure worth stopping on.
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import ExperimentError

_DENIAL = re.compile(
    r"permission|not allowed|denied|not in the allowed|requires approval",
    re.IGNORECASE,
)
_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def parse_stream(text: str) -> list[dict[str, Any]]:
    """Parse a stream-json transcript into its events.

    Raises:
        ExperimentError: If a non-blank line is not a JSON object.
    """
    events: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ExperimentError(f"stream line {lineno} is not JSON: {error}") from None
        if not isinstance(event, dict):
            raise ExperimentError(f"stream line {lineno} is not a JSON object")
        events.append(event)
    return events


def init_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The session's init event, if any."""
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            return event
    return None


def result_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The final result event, if any."""
    for event in reversed(events):
        if event.get("type") == "result":
            return event
    return None


def _blocks(event: dict[str, Any]) -> list[Any]:
    content = (event.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    return "" if content is None else str(content)


def tool_uses(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every tool call the model made, in stream order."""
    uses = []
    for index, event in enumerate(events):
        if event.get("type") != "assistant":
            continue
        for block in _blocks(event):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                uses.append(
                    {
                        "index": index,
                        "id": block.get("id"),
                        "name": str(block.get("name", "")),
                        "input": block.get("input") or {},
                    }
                )
    return uses


def tool_results(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Every tool result keyed by the id of the call it answers."""
    results: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        if event.get("type") != "user":
            continue
        for block in _blocks(event):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                results[str(block.get("tool_use_id"))] = {
                    "index": index,
                    "is_error": bool(block.get("is_error")),
                    "text": _text_of(block.get("content")),
                }
    return results


def denials(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Permission denials, from errored tool results and the result event."""
    found = []
    names = {use["id"]: use["name"] for use in tool_uses(events)}
    for use_id, result in tool_results(events).items():
        if result["is_error"] and _DENIAL.search(result["text"]):
            found.append(
                {
                    "source": "tool_result",
                    "tool": names.get(use_id),
                    "detail": result["text"][:200],
                }
            )
    final = result_event(events) or {}
    for denial in final.get("permission_denials") or []:
        if isinstance(denial, dict):
            found.append(
                {
                    "source": "result",
                    "tool": denial.get("tool_name"),
                    "detail": json.dumps(denial.get("tool_input"), sort_keys=True)[:200],
                }
            )
    return found


def assistant_text(events: list[dict[str, Any]]) -> str:
    """The model's visible text, joined in stream order."""
    parts = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in _blocks(event):
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
    return "\n".join(parts)


def usage_series(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cumulative token usage after each distinct assistant message.

    A message split over several events (one per content block) carries the
    same ``message.id`` and usage; it is counted once.
    """
    series: list[dict[str, Any]] = []
    running = {key: 0 for key in _USAGE_KEYS}
    seen: set[str] = set()
    for index, event in enumerate(events):
        if event.get("type") != "assistant":
            continue
        message = event.get("message") or {}
        usage = message.get("usage") or {}
        if not usage:
            continue
        message_id = message.get("id")
        if message_id is not None:
            if message_id in seen:
                continue
            seen.add(message_id)
        for key in _USAGE_KEYS:
            running[key] += int(usage.get(key, 0) or 0)
        series.append({"index": index, **running, "total": sum(running.values())})
    return series
```

- [ ] **Step 5: Implement `experiment/spike.py`**

```python
"""Spike S0: prove the isolated profile is hermetic before any product code.

Thirteen real ``claude -p`` calls with a one-dollar budget each feed nine
checks. The report is the go/no-go for D20: if auth, hooks or CLAUDE.md
isolation fail, the documented fallback is ``--bare`` with an API key.
Nothing here runs under pytest; the pure parts are tested, the calls are
made once by hand.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ExperimentError
from .arms import arm_flags, mcp_config, profile
from .paths import profile_dir
from .stream import (
    assistant_text,
    denials,
    init_event,
    parse_stream,
    result_event,
    tool_results,
    usage_series,
)

CHECKS = (
    "auth",
    "hooks",
    "claude_md",
    "arm_surface",
    "draft_commit",
    "plugin_mcp",
    "result_fields",
    "denial",
    "append_prompt",
)
REQUIRED = frozenset(CHECKS) - {"draft_commit", "plugin_mcp"}
CANARY = "ARFC-CANARY-7731"
PASSPHRASE = "PASS-4412"
_LIST_TOOLS = (
    "List the names of the tools available to you, one per line, then reply "
    "DONE. Do not call any tool."
)
_ECHO = "Use the Bash tool to run exactly: echo hook-probe . Then reply DONE."
_CODEWORD = "What is the secret codeword? Reply with just the codeword, or NONE."
_STATUS = "Call the arfc_status tool and reply with only the value of clusters_total."


@dataclass(frozen=True)
class Invocation:
    """One ``claude -p`` call: what to run, where, and in which environment."""

    name: str
    argv: tuple[str, ...]
    env: dict[str, str]
    cwd: Path


def _base_env(profile_path: Path | None) -> dict[str, str]:
    env = {
        "HOME": os.environ.get("HOME", ""),
        "PATH": os.environ.get("PATH", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    if profile_path is not None:
        env["CLAUDE_CONFIG_DIR"] = str(profile_path)
    return env


def _common(model: str, *extra: str) -> tuple[str, ...]:
    return (
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--max-budget-usd",
        "1",
        "--permission-mode",
        "dontAsk",
        *extra,
    )


def build_invocations(
    *,
    root: Path,
    panther_repo: Path,
    plugin_dir: Path,
    workspace: Path,
    claude_bin: str = "claude",
    model: str = "claude-opus-5",
) -> list[Invocation]:
    """Every call the spike makes, in order. Pure: nothing runs here."""
    scratch = root / "spike"
    cwd = scratch / "cwd"
    canary_sub = scratch / "canary" / "sub"
    isolated = _base_env(profile_dir(root))
    inherited = _base_env(None)
    plugin_env = {
        **isolated,
        "PANTHER_REPO": str(panther_repo),
        "ARFC_WORKSPACE": str(workspace),
    }
    mcp_path = scratch / "arfc.json"
    prompt_file = scratch / "append.md"
    project = ("--setting-sources", "project")
    no_tools = ("--tools", "")

    def call(name: str, prompt: str, *flags: str, env: dict[str, str], where: Path):
        return Invocation(
            name, (claude_bin, "-p", prompt, *_common(model, *flags)), env, where
        )

    hook_flags = ("--include-hook-events", "--tools", "Bash", "--allowedTools", "Bash(echo *)")
    surface = ("--disable-slash-commands",)
    return [
        call("auth", "Reply with exactly: ARFC-OK", *project, *no_tools, env=isolated, where=cwd),
        call("hooks_isolated", _ECHO, *project, *hook_flags, env=isolated, where=cwd),
        call("hooks_control", _ECHO, *hook_flags, env=inherited, where=panther_repo),
        call("claude_md_control", _CODEWORD, *project, *no_tools, env=isolated, where=canary_sub),
        call("claude_md_isolated", _CODEWORD, *project, *no_tools, env=isolated, where=cwd),
        call("arm_surface_A", _LIST_TOOLS, *project, *surface, *arm_flags(profile("A"), mcp_path), env=isolated, where=workspace),
        call("arm_surface_B", _LIST_TOOLS, *project, *surface, *arm_flags(profile("B"), None), env=isolated, where=workspace),
        call("arm_surface_C", _LIST_TOOLS, *project, *surface, *arm_flags(profile("C"), None), env=isolated, where=workspace),
        call(
            "draft_commit",
            f"Append the line 'probe' to {workspace}/draft/draft-test-spec.md using the "
            f"Edit tool. Then use the Bash tool to run exactly: git -C {workspace}/draft "
            f"add -A && git -C {workspace}/draft commit -m probe . Then reply DONE.",
            *project,
            *arm_flags(profile("C"), None),
            env=isolated,
            where=workspace,
        ),
        call("plugin_mcp_env", _STATUS, *project, "--plugin-dir", str(plugin_dir), *no_tools, "--allowedTools", "mcp__arfc", env=plugin_env, where=workspace),
        call("plugin_mcp_noenv", _STATUS, *project, "--plugin-dir", str(plugin_dir), *no_tools, "--allowedTools", "mcp__arfc", env=isolated, where=workspace),
        call(
            "denial",
            "Use the Bash tool to run exactly: echo bypass-probe . If the call is "
            "denied, reply DENIED; otherwise reply with the command output.",
            *project,
            *arm_flags(profile("B"), None),
            env=isolated,
            where=cwd,
        ),
        call("append_prompt", "What is the passphrase? Reply with just the passphrase.", *project, *no_tools, "--append-system-prompt-file", str(prompt_file), env=isolated, where=cwd),
    ]


def prepare_scratch(
    *, root: Path, panther_repo: Path, server_src: Path, python: str
) -> Path:
    """Create the scratch tree the invocations refer to; returns the workspace."""
    scratch = root / "spike"
    if scratch.exists():
        raise ExperimentError(f"{scratch} exists; remove it to re-run the spike")
    (scratch / "cwd").mkdir(parents=True)
    canary = scratch / "canary"
    (canary / "sub").mkdir(parents=True)
    (canary / "CLAUDE.md").write_text(f"The secret codeword is {CANARY}.\n")
    (scratch / "append.md").write_text(
        f"When asked for the passphrase, answer {PASSPHRASE}.\n"
    )
    for entry in (str(server_src), str(panther_repo)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    from ai_rfc_server.testing import build_workspace

    workspace = build_workspace(scratch / "ws")
    (scratch / "arfc.json").write_text(
        json.dumps(
            mcp_config(
                python=python,
                server_src=server_src,
                panther_repo=panther_repo,
                workspace=workspace,
            ),
            indent=2,
        )
        + "\n"
    )
    return workspace


def run_claude(invocation: Invocation, timeout_s: int) -> dict[str, Any]:
    """Run one invocation; never raises on a non-zero exit."""
    try:
        completed = subprocess.run(
            list(invocation.argv),
            cwd=invocation.cwd,
            env=invocation.env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as expired:
        return {
            "exit_code": None,
            "events": parse_stream(expired.stdout or "") if expired.stdout else [],
            "stderr": expired.stderr or "",
            "timed_out": True,
        }
    except FileNotFoundError as missing:
        raise ExperimentError(f"cannot run {invocation.argv[0]}: {missing}") from None
    try:
        events = parse_stream(completed.stdout)
    except ExperimentError:
        events = []
    return {
        "exit_code": completed.returncode,
        "events": events,
        "stderr": completed.stderr,
        "timed_out": False,
    }


def _answer(outcome: dict[str, Any]) -> str:
    events = outcome.get("events") or []
    final = result_event(events) or {}
    return str(final.get("result") or assistant_text(events))


def _hook_events(events: list[dict[str, Any]]) -> int:
    return sum(
        1
        for event in events
        if str(event.get("type", "")).startswith("hook") or "hook_event_name" in event
    )


def _mcp_status(events: list[dict[str, Any]]) -> dict[str, str]:
    init = init_event(events) or {}
    servers = init.get("mcp_servers") or []
    status = {}
    for server in servers:
        if isinstance(server, dict):
            status[str(server.get("name"))] = str(server.get("status"))
    return status


def _tools(events: list[dict[str, Any]]) -> list[str]:
    return [str(t) for t in ((init_event(events) or {}).get("tools") or [])]


def evaluate(outcomes: dict[str, dict[str, Any]], workspace: Path) -> list[dict[str, Any]]:
    """Turn raw outcomes into the nine check verdicts (pure)."""

    def got(name: str) -> dict[str, Any]:
        return outcomes.get(name) or {"exit_code": None, "events": [], "stderr": "missing", "timed_out": False}

    checks: list[dict[str, Any]] = []

    def add(check: str, passed: bool, evidence: dict[str, Any]) -> None:
        checks.append({"check": check, "passed": bool(passed), "required": check in REQUIRED, "evidence": evidence})

    auth = got("auth")
    auth_ok = auth["exit_code"] == 0 and "ARFC-OK" in _answer(auth) and not (result_event(auth["events"]) or {}).get("is_error", True)
    add("auth", auth_ok, {"exit_code": auth["exit_code"], "api_key_source": (init_event(auth["events"]) or {}).get("apiKeySource"), "stderr_tail": auth["stderr"][-300:]})

    isolated, control = got("hooks_isolated"), got("hooks_control")
    add("hooks", isolated["exit_code"] == 0 and _hook_events(isolated["events"]) == 0, {"isolated_hook_events": _hook_events(isolated["events"]), "control_hook_events": _hook_events(control["events"])})

    md_control, md_isolated = got("claude_md_control"), got("claude_md_isolated")
    add("claude_md", md_isolated["exit_code"] == 0 and CANARY not in _answer(md_isolated), {"control_leaked": CANARY in _answer(md_control), "isolated_answer": _answer(md_isolated)[:80]})

    surfaces = {arm: got(f"arm_surface_{arm}") for arm in ("A", "B", "C")}
    tools = {arm: _tools(o["events"]) for arm, o in surfaces.items()}
    mcp = {arm: _mcp_status(o["events"]) for arm, o in surfaces.items()}
    slash = {arm: (init_event(o["events"]) or {}).get("slash_commands") or [] for arm, o in surfaces.items()}
    surface_ok = (
        all(surfaces[arm]["exit_code"] == 0 for arm in surfaces)
        and "Bash" not in tools["A"]
        and "Bash" in tools["B"]
        and "Bash" in tools["C"]
        and mcp["A"].get("arfc") == "connected"
        and not mcp["B"]
        and not mcp["C"]
        and not any(slash.values())
    )
    add("arm_surface", surface_ok, {"tools": tools, "mcp_servers": mcp, "slash_commands": slash})

    committed = subprocess.run(["git", "-C", str(workspace / "draft"), "log", "--oneline", "-1"], capture_output=True, text=True)
    add("draft_commit", committed.returncode == 0 and "probe" in committed.stdout, {"head": committed.stdout.strip(), "exit_code": got("draft_commit")["exit_code"]})

    env_run, noenv_run = got("plugin_mcp_env"), got("plugin_mcp_noenv")
    env_connected = _mcp_status(env_run["events"]).get("arfc") == "connected"
    noenv_connected = _mcp_status(noenv_run["events"]).get("arfc") == "connected"
    add("plugin_mcp", env_connected and "2" in _answer(env_run), {"env_connected": env_connected, "noenv_connected": noenv_connected, "answer": _answer(env_run)[:40], "note": "env_connected False with arm_surface A connected ⇒ drop the env block from plugins/ai-rfc/.mcp.json (spec §1)"})

    final = result_event(auth["events"]) or {}
    required_keys = ("total_cost_usd", "usage", "num_turns", "duration_ms")
    optional_keys = ("modelUsage", "duration_api_ms", "permission_denials", "session_id")
    series = usage_series(auth["events"])
    add("result_fields", all(key in final for key in required_keys), {"present": sorted(k for k in final), "missing_required": [k for k in required_keys if k not in final], "missing_optional": [k for k in optional_keys if k not in final], "series_total": series[-1]["total"] if series else None, "result_usage": final.get("usage")})

    denial = got("denial")
    leaked = any(not r["is_error"] and "bypass-probe" in r["text"] for r in tool_results(denial["events"]).values())
    found = denials(denial["events"])
    add("denial", denial["exit_code"] == 0 and not leaked and bool(found), {"leaked": leaked, "denials": found[:3], "answer": _answer(denial)[:40]})

    appended = got("append_prompt")
    add("append_prompt", appended["exit_code"] == 0 and PASSPHRASE in _answer(appended), {"answer": _answer(appended)[:40]})

    return checks


def run_spike(
    *,
    root: Path,
    panther_repo: Path,
    plugin_dir: Path,
    claude_bin: str = "claude",
    model: str = "claude-opus-5",
    timeout_s: int = 300,
) -> dict[str, Any]:
    """Prepare the scratch tree, make every call, evaluate, write the report.

    Returns:
        The report; ``report["go"]`` is True when every required check passed.
    """
    server_src = plugin_dir / "server" / "src"
    workspace = prepare_scratch(root=root, panther_repo=panther_repo, server_src=server_src, python=sys.executable)
    invocations = build_invocations(root=root, panther_repo=panther_repo, plugin_dir=plugin_dir, workspace=workspace, claude_bin=claude_bin, model=model)
    outcomes: dict[str, dict[str, Any]] = {}
    log: list[dict[str, Any]] = []
    for invocation in invocations:
        outcome = run_claude(invocation, timeout_s)
        outcomes[invocation.name] = outcome
        log.append({"name": invocation.name, "argv": list(invocation.argv), "cwd": str(invocation.cwd), "exit_code": outcome["exit_code"], "timed_out": outcome["timed_out"], "events": len(outcome["events"]), "stderr_tail": outcome["stderr"][-500:]})
        (root / "spike" / f"{invocation.name}.jsonl").write_text("\n".join(json.dumps(e, sort_keys=True) for e in outcome["events"]) + "\n")
        if invocation.name == "auth" and outcome["exit_code"] != 0:
            break
    checks = evaluate(outcomes, workspace)
    version = subprocess.run([claude_bin, "--version"], capture_output=True, text=True)
    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claude_version": version.stdout.strip(),
        "model": model,
        "go": all(c["passed"] for c in checks if c["required"]),
        "checks": checks,
        "invocations": log,
    }
    (root / "spike-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
```

- [ ] **Step 6: Register the `spike` subcommand** in `experiment/cli.py` — add to `_parser()`:

```python
    spike = commands.add_parser("spike", help="S0: prove the profile is hermetic.")
    _add_root(spike)
    spike.add_argument("--panther-repo", type=Path, required=True)
    spike.add_argument("--plugin-dir", type=Path, default=None, help="Default: the ai-rfc plugin beside this package.")
    spike.add_argument("--claude", default="claude")
    spike.add_argument("--model", default="claude-opus-5")
    spike.add_argument("--timeout", type=int, default=300)
```

and to `main()` (inside the `try`):

```python
        elif args.command == "spike":
            from .spike import run_spike

            plugin_dir = args.plugin_dir or Path(__file__).resolve().parents[1] / "plugins" / "ai-rfc"
            report = run_spike(root=root, panther_repo=args.panther_repo.resolve(), plugin_dir=plugin_dir.resolve(), claude_bin=args.claude, model=args.model, timeout_s=args.timeout)
            for check in report["checks"]:
                flag = "PASS" if check["passed"] else "FAIL"
                need = "required" if check["required"] else "product"
                print(f"{flag}  {check['check']:<14} ({need})")
            print(f"report: {root / 'spike-report.json'}")
            return 0 if report["go"] else 2
```

- [ ] **Step 7: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 20 passed (3 profile + 6 arms + 6 stream + 5 spike).

- [ ] **Step 8: The manual run (sandbox OFF; the user is in the loop)**

1. Ask the user to authenticate the profile once (interactive, theirs to run): `! CLAUDE_CONFIG_DIR=~/arfc-experiments/profile claude auth login` — after `cd $R && $PY -m experiment profile init` has created the directory.
2. Run the spike (spawns `claude` 13 times, ≈ $1 cap each, ~5–10 min): `cd $R && $PY -m experiment spike --root ~/arfc-experiments --panther-repo $W`
   Expected: `PASS` on every required check, exit 0, `~/arfc-experiments/spike-report.json` written, per-call transcripts under `~/arfc-experiments/spike/*.jsonl`.
3. Read `spike-report.json`. Interpretation table:
   - `auth`/`hooks`/`claude_md` FAIL → **no-go**: stop, report to the user, propose the `--bare` + `ANTHROPIC_API_KEY` fallback (spec §2) via AskUserQuestion. Nothing below proceeds.
   - `arm_surface` FAIL because `Bash` still appears in arm A's `tools` → `--tools` does not remove built-ins; record it, and note that enforcement in A degrades to allowlist-only (the harness plan's runner reads this from `spike-report.json`).
   - `plugin_mcp` with `env_connected: false` while `arm_surface` A shows `arfc: connected` → `${PANTHER_REPO}` does not expand in the plugin's `.mcp.json`: edit `$R/plugins/ai-rfc/.mcp.json` to delete the whole `"env": {…}` block, re-run only that check by hand (`CLAUDE_CONFIG_DIR=~/arfc-experiments/profile PANTHER_REPO=$W ARFC_WORKSPACE=~/arfc-experiments/spike/ws claude -p "Call the arfc_status tool and reply with only the value of clusters_total." --setting-sources project --plugin-dir $R/plugins/ai-rfc --tools "" --allowedTools mcp__arfc --output-format json --max-budget-usd 1`), expect `2`, and commit `fix: let the arfc MCP server inherit its environment`.
   - `result_fields` missing `permission_denials` → denials are read from tool results only; record it.
   - `denial` FAIL with `leaked: true` → the allowlist did not hold: **no-go**, report.
4. Copy the real `denial.jsonl` over `experiment/tests/fixtures/stream/denied-bash.jsonl` **only if** the tests in Step 7 still pass against it (adjust the fixture-specific assertions — token totals, indices — to the captured values; keep the semantics). If the real shape differs in a way the readers cannot parse, fix the readers, not the fixture.

- [ ] **Step 9: Record the outcome** in `$R/docs/spike-s0.md`: date, `claude --version`, model, a table (check → PASS/FAIL → one-line evidence), the decisions taken (`.mcp.json` env block kept/dropped; enforcement mode per arm; denial source), and the exact commands run. Then commit:

```bash
git -C $R add experiment/stream.py experiment/spike.py experiment/cli.py experiment/tests/test_stream.py experiment/tests/test_spike.py experiment/tests/fixtures/stream/denied-bash.jsonl docs/spike-s0.md
git -C $R commit -m "feat: spike S0 hermeticity checks with stream-json readers"
```

(If `.mcp.json` changed, commit it separately as `fix: let the arfc MCP server inherit its environment`.)

### Task 6: `core/draft.py` — commit the prose, tag a revision

Spec §1 "Draft operations" (D26). The tag order is forced by `a_rfc/draft/gate.py:183-195`: a recorded-but-untagged revision is itself a finding, so the citation gate can only run after the tag exists.

**Files:**
- Create: `$S/src/ai_rfc_server/core/draft.py`, `$S/tests/test_draft.py`

**Interfaces:**
- Consumes: `ai_rfc_server.core.gates.manifest_gate(ctx, strict) -> {exit_code, stderr, report}`, `citation_gate(ctx, strict) -> {exit_code, stderr, findings}`; `panther.plugins.services.testers.a_rfc.draft.gate.REVISION_TAG`, `load_revisions`, `GateError`.
- Produces: `commit_draft(ctx: Context, message: str) -> dict` (`{commit, files}`); `tag_revision(ctx: Context, tag: str, message: str) -> dict` (`{exit_code, tag, commit?, stage?, findings, rolled_back}`; `stage` ∈ `manifest_gate | citation_gate` when `exit_code != 0`).

- [ ] **Step 1: Write the failing tests** (`$S/tests/test_draft.py`):

```python
import pytest
import yaml

from ai_rfc_server.core import CoreError
from ai_rfc_server.core.draft import commit_draft, tag_revision
from ai_rfc_server.core.gates import citation_gate, write_checkpoint
from ai_rfc_server.core.queries import cluster_next
from ai_rfc_server.core.revisions import record_revision
from ai_rfc_server.testing import git


def _draft(workspace):
    return workspace.workspace / "draft"


def _recorded(workspace, tag="draft-test-spec-00"):
    first = cluster_next(workspace)
    assert write_checkpoint(workspace, first["id"])["exit_code"] == 0
    record_revision(workspace, tag, first["id"], True, "initial")
    return first["id"]


def test_commit_draft_refuses_a_clean_tree(workspace):
    with pytest.raises(CoreError) as excinfo:
        commit_draft(workspace, "noop")
    assert "nothing to commit" in str(excinfo.value)


def test_commit_draft_commits_every_change(workspace):
    prose = _draft(workspace) / "draft-test-spec.md"
    prose.write_text(prose.read_text() + "\nMore prose.\n")
    result = commit_draft(workspace, "more prose")
    assert result["files"] == ["draft-test-spec.md"]
    assert git(_draft(workspace), "rev-parse", "HEAD") == result["commit"]
    assert git(_draft(workspace), "status", "--porcelain") == ""


def test_commit_draft_needs_a_message(workspace):
    with pytest.raises(CoreError):
        commit_draft(workspace, "   ")


def test_tag_revision_requires_a_recorded_entry(workspace):
    with pytest.raises(CoreError) as excinfo:
        tag_revision(workspace, "draft-test-spec-00", "rev 00")
    assert "record the revision first" in str(excinfo.value)


def test_tag_revision_rejects_a_malformed_tag(workspace):
    with pytest.raises(CoreError):
        tag_revision(workspace, "v1", "rev")


def test_tag_revision_refuses_a_dirty_tree(workspace):
    _recorded(workspace)
    prose = _draft(workspace) / "draft-test-spec.md"
    prose.write_text(prose.read_text() + "\nUncommitted.\n")
    with pytest.raises(CoreError) as excinfo:
        tag_revision(workspace, "draft-test-spec-00", "rev 00")
    assert "uncommitted" in str(excinfo.value)
    assert git(_draft(workspace), "tag", "-l") == ""


def test_tag_revision_creates_the_tag_when_both_gates_pass(workspace):
    _recorded(workspace)
    result = tag_revision(workspace, "draft-test-spec-00", "revision 00")
    assert result["exit_code"] == 0 and result["rolled_back"] is False
    assert git(_draft(workspace), "tag", "-l") == "draft-test-spec-00"
    assert (
        git(_draft(workspace), "rev-list", "-n", "1", "draft-test-spec-00")
        == result["commit"]
    )
    assert citation_gate(workspace, strict=True)["exit_code"] == 0
    with pytest.raises(CoreError):
        tag_revision(workspace, "draft-test-spec-00", "again")


def test_tag_revision_stops_on_manifest_gate_findings(workspace):
    _recorded(workspace)
    document = yaml.safe_load(workspace.manifest.read_text())
    document["requirements"]["t:1.1"]["status"] = "confirmed"
    workspace.manifest.write_text(yaml.safe_dump(document, sort_keys=True))
    result = tag_revision(workspace, "draft-test-spec-00", "revision 00")
    assert result["exit_code"] == 2 and result["stage"] == "manifest_gate"
    assert git(_draft(workspace), "tag", "-l") == ""


def test_tag_revision_rolls_back_on_citation_findings(workspace):
    prose = _draft(workspace) / "draft-test-spec.md"
    prose.write_text(prose.read_text() + "\nGhost. `a_rfc:t:9.9`\n")
    commit_draft(workspace, "cite a ghost")
    _recorded(workspace)
    result = tag_revision(workspace, "draft-test-spec-00", "revision 00")
    assert result["exit_code"] == 2 and result["stage"] == "citation_gate"
    assert result["rolled_back"] is True
    assert any("t:9.9" in finding for finding in result["findings"])
    assert git(_draft(workspace), "tag", "-l") == ""
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $S && SSLKEYLOGFILE= $PY -m pytest tests/test_draft.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_rfc_server.core.draft'`.

- [ ] **Step 3: Implement `core/draft.py`**

```python
"""Draft-repository operations: commit prose, tag a revision.

Both exist so the tool arm can finish a normative revision without a
shell. A tag is created only after the strict manifest gate passes and is
deleted again if the strict citation gate then finds anything, so a tag
that survives is one both gates accepted. Exit codes are surfaced, never
reinterpreted.
"""

from __future__ import annotations

import subprocess
from typing import Any

from ..paths import Context
from . import CoreError
from .gates import citation_gate, manifest_gate


def _git(ctx: Context, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ctx.workspace / "draft"), *args],
        capture_output=True,
        text=True,
    )


def _require_repo(ctx: Context) -> None:
    if not (ctx.workspace / "draft" / ".git").exists():
        raise CoreError(f"{ctx.workspace / 'draft'} is not a git repository")


def _dirty(ctx: Context) -> list[str]:
    status = _git(ctx, "status", "--porcelain")
    if status.returncode != 0:
        raise CoreError(f"git status failed: {status.stderr.strip()}")
    return [line for line in status.stdout.splitlines() if line.strip()]


def commit_draft(ctx: Context, message: str) -> dict[str, Any]:
    """Stage and commit every change in the draft repository.

    Args:
        ctx: The resolved context.
        message: The commit message.

    Returns:
        ``{commit, files}`` — the new HEAD and the paths it touched.

    Raises:
        CoreError: If there is no repository, no message, nothing to
            commit, or git fails.
    """
    _require_repo(ctx)
    if not message.strip():
        raise CoreError("a commit needs a non-empty message")
    if not _dirty(ctx):
        raise CoreError("nothing to commit; the draft tree is clean")
    added = _git(ctx, "add", "-A")
    if added.returncode != 0:
        raise CoreError(f"git add failed: {added.stderr.strip()}")
    committed = _git(ctx, "commit", "-q", "-m", message)
    if committed.returncode != 0:
        raise CoreError(f"git commit failed: {committed.stderr.strip()}")
    head = _git(ctx, "rev-parse", "HEAD").stdout.strip()
    files = _git(ctx, "show", "--pretty=", "--name-only", head).stdout.split()
    return {"commit": head, "files": sorted(files)}


def tag_revision(ctx: Context, tag: str, message: str) -> dict[str, Any]:
    """Create the annotated tag for a recorded revision, gated twice.

    Order: the tag must be well-formed and recorded in ``revisions.yaml``,
    the draft tree clean, the strict manifest gate at 0; then the tag is
    created and the strict citation gate runs — on findings the tag is
    deleted again. The citation gate cannot run first: it reports a
    recorded-but-untagged revision as a finding.

    Args:
        ctx: The resolved context.
        tag: The revision tag (``draft-<name>-NN``).
        message: The annotated tag message.

    Returns:
        ``{exit_code, tag, commit?, stage?, findings, rolled_back}``; a
        non-zero ``exit_code`` names the ``stage`` that refused.

    Raises:
        CoreError: On a malformed or unrecorded tag, a dirty tree, an
            existing tag, or a git failure.
    """
    from panther.plugins.services.testers.a_rfc.draft.gate import (
        REVISION_TAG,
        GateError,
        load_revisions,
    )

    _require_repo(ctx)
    if not REVISION_TAG.match(tag):
        raise CoreError(f"{tag}: not a revision tag; expected draft-<name>-NN")
    if not message.strip():
        raise CoreError("a tag needs a non-empty message")
    try:
        recorded = {entry.tag for entry in load_revisions(ctx.revisions)}
    except GateError as error:
        raise CoreError(str(error)) from None
    if tag not in recorded:
        raise CoreError(f"{tag} is not in revisions.yaml; record the revision first")
    if _dirty(ctx):
        raise CoreError(
            "the draft tree has uncommitted changes; commit before tagging"
        )
    if _git(ctx, "tag", "-l", tag).stdout.strip():
        raise CoreError(f"tag {tag} already exists")

    manifest = manifest_gate(ctx, strict=True)
    if manifest["exit_code"] != 0:
        return {
            "exit_code": manifest["exit_code"],
            "tag": tag,
            "stage": "manifest_gate",
            "findings": manifest["stderr"],
            "rolled_back": False,
        }
    tagged = _git(ctx, "tag", "-a", tag, "-m", message)
    if tagged.returncode != 0:
        raise CoreError(f"git tag failed: {tagged.stderr.strip()}")
    citation = citation_gate(ctx, strict=True)
    if citation["exit_code"] != 0:
        deleted = _git(ctx, "tag", "-d", tag)
        if deleted.returncode != 0:
            raise CoreError(
                f"citation gate refused {tag} and the tag could not be removed: "
                f"{deleted.stderr.strip()}"
            )
        return {
            "exit_code": citation["exit_code"],
            "tag": tag,
            "stage": "citation_gate",
            "findings": citation["findings"] or citation["stderr"],
            "rolled_back": True,
        }
    commit = _git(ctx, "rev-list", "-n", "1", tag).stdout.strip()
    return {
        "exit_code": 0,
        "tag": tag,
        "commit": commit,
        "findings": [],
        "rolled_back": False,
    }
```

- [ ] **Step 4: Run the tests**

Run: `cd $S && SSLKEYLOGFILE= $PY -m pytest -q`
Expected: 34 passed (25 + 9).

- [ ] **Step 5: Commit (nested repo)**

```bash
git -C $R add plugins/ai-rfc/server/src/ai_rfc_server/core/draft.py plugins/ai-rfc/server/tests/test_draft.py
git -C $R commit -m "feat: draft commit and gated revision tag in the shared core"
```

### Task 7: Tool + CLI twins, parity rows and tests, release command, README

**Files:**
- Modify: `$S/src/ai_rfc_server/tools.py`, `$S/src/ai_rfc_server/cli.py`, `$S/tests/test_cli.py` (append), `$S/tests/test_parity.py` (append + one import), `$R/docs/parity.md`, `$R/plugins/ai-rfc/commands/arfc-release-revision.md` (rewrite), `$R/README.md` (guardrails list)

**Interfaces:**
- Produces: tools `arfc_draft_commit(message: str) -> dict`, `arfc_revision_tag(tag: str, message: str) -> dict` (appended to `ALL_TOOLS`); verbs `arfc draft-commit -m MSG` (exit 0/1) and `arfc revision-tag TAG -m MSG` (exit code = result `exit_code`).

- [ ] **Step 1: Write the failing tests**

Append to `$S/tests/test_cli.py`:

```python
def test_draft_commit_verb(workspace, capsys):
    prose = workspace.workspace / "draft" / "draft-test-spec.md"
    prose.write_text(prose.read_text() + "\nMore.\n")
    assert cli.main(["draft-commit", "-m", "more"]) == 0
    assert _emit(capsys)["files"] == ["draft-test-spec.md"]
    assert cli.main(["draft-commit", "-m", "again"]) == 1
    assert "nothing to commit" in capsys.readouterr().err


def test_revision_tag_verb_passes_gate_codes_through(workspace, capsys):
    assert cli.main(["cluster-next"]) == 0
    first = _emit(capsys)
    assert cli.main(["checkpoint", first["id"]]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "revision-record",
                "draft-test-spec-00",
                "--cluster",
                first["id"],
                "--normative",
                "--note",
                "n",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["revision-tag", "draft-test-spec-00", "-m", "rev 00"]) == 0
    assert _emit(capsys)["exit_code"] == 0
    assert cli.main(["revision-tag", "draft-test-spec-00", "-m", "dup"]) == 1
    assert "already exists" in capsys.readouterr().err
```

Append to `$S/tests/test_parity.py` (and add `from ai_rfc_server.testing import git` to its imports):

```python
_PINNED = "2026-01-02T00:00:00+00:00"


def test_draft_commit_parity(make_workspace, capsys, monkeypatch):
    tool_arm, cli_arm, use = _twins(make_workspace)
    monkeypatch.setenv("GIT_AUTHOR_DATE", _PINNED)
    monkeypatch.setenv("GIT_COMMITTER_DATE", _PINNED)
    for root in (tool_arm, cli_arm):
        prose = root / "draft" / "draft-test-spec.md"
        prose.write_text(prose.read_text() + "\nMore prose.\n")
    use(tool_arm)
    from_tool = tools.arfc_draft_commit("more prose")
    use(cli_arm)
    assert cli.main(["draft-commit", "-m", "more prose"]) == 0
    from_cli = json.loads(capsys.readouterr().out)
    assert from_tool == from_cli
    assert git(tool_arm / "draft", "rev-parse", "HEAD") == git(
        cli_arm / "draft", "rev-parse", "HEAD"
    )


def test_revision_tag_parity(make_workspace, capsys, monkeypatch):
    tool_arm, cli_arm, use = _twins(make_workspace)
    monkeypatch.setenv("GIT_AUTHOR_DATE", _PINNED)
    monkeypatch.setenv("GIT_COMMITTER_DATE", _PINNED)
    for root in (tool_arm, cli_arm):
        use(root)
        first = tools.arfc_cluster_next()
        tools.arfc_checkpoint(first["id"])
        tools.arfc_revision_record("draft-test-spec-00", first["id"], True, "initial")
    use(tool_arm)
    from_tool = tools.arfc_revision_tag("draft-test-spec-00", "revision 00")
    use(cli_arm)
    assert cli.main(["revision-tag", "draft-test-spec-00", "-m", "revision 00"]) == 0
    from_cli = json.loads(capsys.readouterr().out)
    assert from_tool == from_cli and from_tool["exit_code"] == 0
    assert git(tool_arm / "draft", "cat-file", "-p", "draft-test-spec-00") == git(
        cli_arm / "draft", "cat-file", "-p", "draft-test-spec-00"
    )
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $S && SSLKEYLOGFILE= $PY -m pytest tests/test_cli.py tests/test_parity.py -q`
Expected: the four new tests FAIL (`argparse` "invalid choice: 'draft-commit'", `AttributeError: arfc_draft_commit`), and `test_every_tool_is_in_the_parity_table` still passes (nothing added yet).

- [ ] **Step 3: Wire the tools** — in `$S/src/ai_rfc_server/tools.py` change the core import to `from .core import claims, draft, gates, queries, questions, revisions`, add after `arfc_citation_gate`:

```python
def arfc_draft_commit(message: str) -> dict[str, Any]:
    """Commit every change in the draft repository; a clean tree is an error."""
    return draft.commit_draft(resolve_context(), message)


def arfc_revision_tag(tag: str, message: str) -> dict[str, Any]:
    """Tag a recorded revision once both strict gates accept it (exit code raw)."""
    return draft.tag_revision(resolve_context(), tag, message)
```

and append `arfc_draft_commit, arfc_revision_tag,` to `ALL_TOOLS` (after `arfc_citation_gate`).

- [ ] **Step 4: Wire the verbs** — in `$S/src/ai_rfc_server/cli.py` add to `_parser()` after the `citation` parser:

```python
    draft_commit = verbs.add_parser(
        "draft-commit", help="Commit every change in draft/ (clean tree is an error)."
    )
    draft_commit.add_argument("-m", "--message", required=True)

    revision_tag = verbs.add_parser(
        "revision-tag",
        help="Create the annotated revision tag once both strict gates accept it.",
    )
    revision_tag.add_argument("tag")
    revision_tag.add_argument("-m", "--message", required=True)
```

change the lazy import in `main()` to `from .core import claims, draft, gates, queries, questions, revisions`, and add before the `except CoreError` line:

```python
        elif args.verb == "draft-commit":
            _emit(draft.commit_draft(ctx, args.message))
        elif args.verb == "revision-tag":
            result = draft.tag_revision(ctx, args.tag, args.message)
            _emit(result)
            return result["exit_code"]
```

- [ ] **Step 5: Parity table and docs** — append two rows to the table in `$R/docs/parity.md`:

```markdown
| `arfc_draft_commit` | `arfc draft-commit -m MSG` | `git -C draft add -A && git -C draft commit -m MSG` |
| `arfc_revision_tag` | `arfc revision-tag TAG -m MSG` | `git -C draft tag -a TAG -m MSG`, then `python -m …a_rfc.draft gate … --strict` (the tool deletes the tag on findings; the raw route leaves that to the author) |
```

and extend the closing "Asymmetries" paragraph with: "The raw arm's only corpus-index path is the `sqlite3` CLI over `corpus/index.sqlite` (the index is derived and disposable; a write through it is detected by nothing), and its tag is not rolled back on citation findings." Rewrite `$R/plugins/ai-rfc/commands/arfc-release-revision.md` to:

```markdown
---
description: Tag the current draft state as the next revision after all gates pass
---

Release the current draft state of `$ARFC_WORKSPACE` as revision `-NN`
(next number, monotone in cluster ordinal):

1. Confirm `revisions.yaml` carries the entry for this tag (cluster id,
   checkpoint sha, explicit `normative_change`, note); record it with
   `arfc_revision_record` / `arfc revision-record` if the loop left it
   pending. The citation gate reports a recorded-but-untagged revision as a
   finding, so it cannot be a precondition here.
2. Commit any prose change (`arfc_draft_commit` / `arfc draft-commit -m …`);
   a dirty tree refuses the tag.
3. Create the tag with `arfc_revision_tag` / `arfc revision-tag TAG -m …`:
   it runs the strict manifest gate first, creates the annotated tag, then
   runs the strict citation gate and deletes the tag again on findings.
   Report every finding verbatim and do not work around any of them.
4. Exit code 0 closes the release.

Building txt/html via the template's Makefile is optional; when asked for
it, follow the draft repo's own CLAUDE.md.
```

In `$R/README.md`, add to "Guardrails the tools enforce": "- `arfc_revision_tag` creates a tag only after the strict manifest gate passes and deletes it again if the strict citation gate finds anything."

- [ ] **Step 6: Run the server suite**

Run: `cd $S && SSLKEYLOGFILE= $PY -m pytest -q`
Expected: 38 passed (34 + 2 CLI + 2 parity), including `test_every_tool_is_in_the_parity_table`.

- [ ] **Step 7: Commit (nested repo)**

```bash
git -C $R add plugins/ai-rfc/server/src/ai_rfc_server/tools.py plugins/ai-rfc/server/src/ai_rfc_server/cli.py plugins/ai-rfc/server/tests/test_cli.py plugins/ai-rfc/server/tests/test_parity.py docs/parity.md plugins/ai-rfc/commands/arfc-release-revision.md README.md
git -C $R commit -m "feat: draft-commit and revision-tag twins with parity"
```

### Task 8: One loop template, four renderings (plugin SKILL.md + arms A/B/C)

Spec §1 "One template, four renderings" (D27). After this task the plugin's `SKILL.md` can only change through the template, and the arm prompts differ from each other exactly where a slot names the arm's surface.

**Files:**
- Create: `$R/experiment/prompts/loop.tmpl.md`, `$R/experiment/render.py`, `$R/experiment/tests/test_render.py`
- Modify: `$R/experiment/cli.py` (add `render`), `$R/plugins/ai-rfc/skills/arfc-reconstruction-loop/SKILL.md` (regenerated in Step 6)

**Interfaces:**
- Produces: `experiment.render.INVOCATIONS: dict[str, dict[str, str]]` (keys `interactive`, `A`, `B`, `C`; slots `guidance, preamble, runtime, cluster_next, cluster_get, corpus_query, claim_upsert, lint, record_status, gate, checkpoint, revision_record, draft_commit, revision_tag, citation_gate, question_draft`); `SKILL_FRONTMATTER: str`; `render_loop(arm: str) -> str`; `strip_frontmatter(text: str) -> str`; `arm_prompt(arm: str, plugin_root: Path) -> str` (rendered loop + rfc-style + claim-citation + evidence-hygiene bodies, verbatim, no frontmatter); `write_plugin_skill(plugin_root: Path) -> Path`; `unified_diff(a: str, b: str, a_label: str, b_label: str) -> str`.

- [ ] **Step 1: Write the template** `$R/experiment/prompts/loop.tmpl.md` (the current SKILL.md body with every surface-specific phrase replaced by a `{{slot}}`; keep the failure table verbatim):

````markdown
# The reconstruction loop

One iteration turns one timeline cluster into evidence-honest claims and,
when it changed normative behaviour, a new draft revision. Work through the
clusters in ordinal order; never skip silently.

{{guidance}}

{{preamble}}

## Preconditions

- `PANTHER_REPO` and `ARFC_WORKSPACE` are set; {{runtime}}.
- The workspace holds `corpus/`, `timeline/`, `clusters/` and the pinned
  `clone/`. When a forge snapshot exists, the timeline MUST have been built
  with `--forge` **before any checkpoint is written** — forge data
  restructures cluster ids, and checkpoints pin them.

## One iteration

1. **Pick the next cluster**: {{cluster_next}}.
2. **Read its evidence**: {{cluster_get}}. For context beyond the cluster,
   query the corpus index — churn-ranked reading beats the directory tree:
   {{corpus_query}}.
3. **Mine claims**: behaviours the cluster introduces or changes, each with
   pinned anchors (the cluster's member commits are the natural pins) and
   NO `status`: {{claim_upsert}}. A commit message stating a decision is an
   `adr` anchor; PR discussion explaining intent supports `intent:` but is
   not itself an anchor class.
4. **Lint**: {{lint}} — fix every unverified anchor (wrong paths, wrong
   commits, wrong lines) BEFORE anything is built on top.
5. **Record statuses**: {{record_status}}. Then the strict gate:
   {{gate}} — exit 0 is the bar.
6. **Decide spec relevance**:
   - Normative behaviour changed → update the draft per the RFC-style
     rules, citing the new/changed claims.
   - Nothing normative → no prose edit; the revision entry will say so.
7. **Checkpoint**: {{checkpoint}}.
8. **Record and tag the revision**: {{revision_record}} — the tag
   `draft-<name>-NN` (two digits, monotone in cluster ordinal), the cluster
   id, an explicit `normative_change`, a one-line note. Commit any prose
   change ({{draft_commit}}), then create the annotated tag
   ({{revision_tag}}). Every revision entry needs its tag, no-change
   revisions included.
9. **Gate**: {{citation_gate}} — exit 0 before advancing.
10. **Open questions**: any claim stuck at `gap`/`inferred` that blocks a
    section gets a question: {{question_draft}}.

## Failure recovery

| Failure | Response |
|---|---|
| Strict gate exit 2 | The system working. Fix anchors first (weakest link), re-adjudicate, re-run. Never hand-edit a status upward, never bypass. |
| `StaleIndexError` | Rebuild the index (`build_index`), never migrate. If the corpus itself moved, STOP — every anchor needs re-verification. |
| Citation-gate finding | Reconcile prose or claims. Never delete a claim to silence a citation. |
| Checkpoint refused (exists) | The cluster was processed; re-running is a new decision — investigate before deleting anything. |
| Giant epoch cluster | Read paginated, mine what you can carry; claims may cover a subset — understatement is safe. |
| Clone HEAD ≠ corpus tip | Someone moved the clone. Restore the pin; never re-anchor to the new HEAD. |
````

- [ ] **Step 2: Write the failing tests** (`$R/experiment/tests/test_render.py`):

```python
import pytest

from experiment import ExperimentError
from experiment.render import (
    INVOCATIONS,
    SKILL_FRONTMATTER,
    arm_prompt,
    render_loop,
    unified_diff,
    write_plugin_skill,
)


def test_every_table_fills_every_slot():
    for arm in INVOCATIONS:
        text = render_loop(arm)
        assert "{{" not in text and "}}" not in text, arm


def test_unknown_arm_is_refused():
    with pytest.raises(ExperimentError):
        render_loop("Z")


def test_plugin_skill_is_the_interactive_rendering(plugin_root):
    skill = plugin_root / "skills" / "arfc-reconstruction-loop" / "SKILL.md"
    assert skill.read_text() == SKILL_FRONTMATTER + render_loop("interactive")


def test_write_plugin_skill_round_trips(tmp_path):
    root = tmp_path / "plugin"
    (root / "skills" / "arfc-reconstruction-loop").mkdir(parents=True)
    written = write_plugin_skill(root)
    assert written.read_text() == SKILL_FRONTMATTER + render_loop("interactive")


def test_arm_renderings_name_only_their_surface():
    a, b, c = (render_loop(arm) for arm in "ABC")
    assert "arfc_cluster_next" in a
    assert "arfc cluster-next" not in a and "python -m panther" not in a
    assert "arfc cluster-next" in b
    assert "arfc_cluster_next" not in b and "python -m panther" not in b
    assert "python -m panther.plugins.services.testers.a_rfc" in c
    assert "arfc_" not in c and "arfc cluster" not in c


def test_arm_prompt_bundles_the_neutral_texts(plugin_root):
    prompt = arm_prompt("A", plugin_root)
    assert "# RFC prose for a reconstructed specification" in prompt
    assert "# The claim-citation convention" in prompt
    assert "# Evidence hygiene for reconstruction manifests" in prompt
    assert "\nname: arfc-" not in prompt and not prompt.startswith("---")


def test_arm_prompts_differ_only_where_slots_differ(plugin_root):
    a, b = arm_prompt("A", plugin_root), arm_prompt("B", plugin_root)
    diff = unified_diff(a, b, "arm-A", "arm-B")
    assert diff.startswith("--- arm-A") and "+++ arm-B" in diff
    changed = [
        line
        for line in diff.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    assert changed and all("arfc" in line for line in changed)
```

- [ ] **Step 3: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_render.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment.render'`.

- [ ] **Step 4: Implement `$R/experiment/render.py`**

```python
"""Render the reconstruction-loop prompt for the plugin and for each arm.

One template, four invocation tables: ``interactive`` becomes the plugin's
SKILL.md (a test pins the file to this rendering), ``A``/``B``/``C`` become
the appended system prompts of the experiment arms. Every arm prompt is the
rendered loop plus the arm-neutral style and hygiene texts verbatim, so the
arms differ only where a slot names the arm's surface.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from . import ExperimentError

PROMPTS = Path(__file__).parent / "prompts"
TEMPLATE = PROMPTS / "loop.tmpl.md"
SLOT = re.compile(r"\{\{([a-z_]+)\}\}")
NEUTRAL_TEXTS = (
    ("skills", "arfc-rfc-style", "SKILL.md"),
    ("skills", "arfc-rfc-style", "references", "claim-citation.md"),
    ("skills", "arfc-evidence-hygiene", "SKILL.md"),
)

SKILL_FRONTMATTER = """---
name: arfc-reconstruction-loop
description: The cluster-by-cluster reconstruction driver — read evidence, mine claims, adjudicate, revise the draft, gate, checkpoint, advance. Use when processing timeline clusters of a reconstruction workspace or when asked to continue a reconstruction.
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(python -m panther.plugins.services.testers.a_rfc*), Bash(git *), Bash(arfc *), Bash(sqlite3 *)
---

"""

_CHURN = "SELECT path, COUNT(*) c FROM file_changes GROUP BY path ORDER BY c DESC LIMIT 20"
_EXPERIMENT_GUIDANCE = (
    "The evidence-hygiene, RFC-style and claim-citation rules follow this "
    "procedure; apply them throughout."
)

_RAW = {
    "cluster_next": (
        "read `$ARFC_WORKSPACE/timeline/clusters.jsonl` in ordinal order and take "
        "the first id that has neither a `checkpoints/<id>/` directory nor a "
        "`revisions.yaml` entry"
    ),
    "cluster_get": (
        "read `$ARFC_WORKSPACE/clusters/<id>/view.json` (file set, PR number), "
        "`span.diff` (paginate long diffs with `sed -n`) and `evidence/pr.json` "
        "when present"
    ),
    "corpus_query": f'`sqlite3 $ARFC_WORKSPACE/corpus/index.sqlite "{_CHURN}"`',
    "claim_upsert": (
        "edit `$ARFC_WORKSPACE/manifest.yaml` by hand — quote every id and "
        "section, never write `status`"
    ),
    "lint": (
        "`python -m panther.plugins.services.testers.a_rfc "
        "$ARFC_WORKSPACE/manifest.yaml --out $ARFC_WORKSPACE/out --repo "
        "$ARFC_WORKSPACE/clone`"
    ),
    "record_status": (
        "read `$ARFC_WORKSPACE/out/report.json` (`claims[]`) and set each claim's "
        "`status` in `manifest.yaml` to exactly its `supported` value"
    ),
    "gate": (
        "`python -m panther.plugins.services.testers.a_rfc "
        "$ARFC_WORKSPACE/manifest.yaml --out $ARFC_WORKSPACE/out --repo "
        "$ARFC_WORKSPACE/clone --strict`"
    ),
    "checkpoint": (
        "`python -m panther.plugins.services.testers.a_rfc.draft checkpoint "
        "$ARFC_WORKSPACE/manifest.yaml --timeline $ARFC_WORKSPACE/timeline "
        "--cluster <id> --out $ARFC_WORKSPACE/checkpoints`"
    ),
    "revision_record": (
        "append the entry to `$ARFC_WORKSPACE/revisions.yaml` under `revisions:` "
        "(`cluster_id`, `checkpoint_manifest_sha256` copied from the checkpoint's "
        "`checkpoint.json`, `normative_change`, `note`)"
    ),
    "draft_commit": (
        '`git -C $ARFC_WORKSPACE/draft add -A && git -C $ARFC_WORKSPACE/draft '
        'commit -m "<message>"`'
    ),
    "revision_tag": (
        '`git -C $ARFC_WORKSPACE/draft tag -a draft-<name>-NN -m "<message>"` — '
        "only after the strict manifest gate exited 0"
    ),
    "citation_gate": (
        "`python -m panther.plugins.services.testers.a_rfc.draft gate "
        "$ARFC_WORKSPACE/draft --timeline $ARFC_WORKSPACE/timeline --checkpoints "
        "$ARFC_WORKSPACE/checkpoints --questions $ARFC_WORKSPACE/questions.yaml "
        "--revisions $ARFC_WORKSPACE/revisions.yaml --out $ARFC_WORKSPACE/out "
        "--strict`"
    ),
    "question_draft": (
        "append a `q-NNN` entry (`question`, `claim_ids`, `status: open`, "
        "`asked_at`) to `$ARFC_WORKSPACE/questions.yaml`"
    ),
}

INVOCATIONS: dict[str, dict[str, str]] = {
    "interactive": {
        **_RAW,
        "guidance": (
            "Load `arfc-evidence-hygiene` before touching claims and "
            "`arfc-rfc-style` before touching prose."
        ),
        "preamble": (
            "When the `arfc` MCP server is connected, prefer its tools "
            "(`arfc_cluster_next`, `arfc_claim_upsert`, `arfc_claim_record_status`, "
            "`arfc_checkpoint`, `arfc_gate`, `arfc_revision_tag`, …) or the "
            "equivalent `arfc <verb>` CLI — same core, guardrails enforced up "
            "front (see `docs/parity.md`). The raw substrate commands below "
            "remain the documented fallback and the raw experiment arm."
        ),
        "runtime": (
            "commands below run with an interpreter that imports `panther` "
            "first on `PATH` (`python -m …`)"
        ),
    },
    "C": {
        **_RAW,
        "guidance": _EXPERIMENT_GUIDANCE,
        "preamble": (
            "This session has no MCP server and no `arfc` command: drive the "
            "workspace with the raw substrate commands through Bash, exactly as "
            "written below, and edit YAML by hand where no command exists."
        ),
        "runtime": (
            "`python` on `PATH` imports `panther`; run every `python -m …` "
            "command as written"
        ),
    },
    "B": {
        "guidance": _EXPERIMENT_GUIDANCE,
        "preamble": (
            "This session has no MCP server: drive the workspace with the `arfc` "
            "command through Bash, exactly as written below."
        ),
        "runtime": "`arfc` is on `PATH` and reads both variables",
        "cluster_next": (
            "`arfc cluster-next` (prints the lowest-ordinal cluster with neither "
            "checkpoint nor revision entry, or `null`)"
        ),
        "cluster_get": (
            "`arfc cluster-get <id> --patch` (add `--patch-offset N "
            "--patch-limit N` to page through long diffs)"
        ),
        "corpus_query": f'`arfc corpus-query "{_CHURN}"`',
        "claim_upsert": (
            "`arfc claim-upsert <id> --text … --section … --level … --layer … "
            "[--field intent=…] [--anchor '{\"evidence_class\": \"code\", "
            "\"locator\": \"…\", \"commit\": \"<sha>\", \"line\": N}']` (repeat "
            "`--anchor`; the verb refuses `status`)"
        ),
        "lint": "`arfc gate` (the linter; fix every entry under `unverified_anchors`)",
        "record_status": (
            "`arfc claim-adjudicate` to see stored vs supported, then "
            "`arfc claim-record-status`"
        ),
        "gate": "`arfc gate --strict`",
        "checkpoint": "`arfc checkpoint <id>`",
        "revision_record": (
            "`arfc revision-record draft-<name>-NN --cluster <id> "
            '--normative|--no-normative --note "…"`'
        ),
        "draft_commit": '`arfc draft-commit -m "<message>"`',
        "revision_tag": (
            '`arfc revision-tag draft-<name>-NN -m "<message>"` — it runs the '
            "strict manifest gate, creates the tag, runs the strict citation gate "
            "and deletes the tag again on findings"
        ),
        "citation_gate": "`arfc citation-gate --strict`",
        "question_draft": (
            '`arfc question-draft "<question quoting the claim text verbatim>" '
            "--claim <id>`"
        ),
    },
    "A": {
        "guidance": _EXPERIMENT_GUIDANCE,
        "preamble": (
            "This session has no shell: drive the workspace with the `arfc_*` MCP "
            "tools, exactly as named below, and edit prose with the Edit/Write "
            "tools."
        ),
        "runtime": "the `arfc` MCP server is connected and reads both variables",
        "cluster_next": (
            "`arfc_cluster_next` (returns the lowest-ordinal cluster with neither "
            "checkpoint nor revision entry, or null)"
        ),
        "cluster_get": (
            "`arfc_cluster_get(cluster_id, include_patch=true)` (page long diffs "
            "with `patch_offset`/`patch_limit`)"
        ),
        "corpus_query": f'`arfc_corpus_query(sql="{_CHURN}")`',
        "claim_upsert": (
            "`arfc_claim_upsert(claim_id, fields)` with `text`, `section`, "
            "`level`, `layer`, optional `intent`/`req_class`, and `anchors` as a "
            "list of `{evidence_class, locator, commit, line}` (the tool refuses "
            "`status`)"
        ),
        "lint": (
            "`arfc_gate(strict=false)` (the linter; fix every entry under "
            "`unverified_anchors`)"
        ),
        "record_status": (
            "`arfc_claim_adjudicate()` to see stored vs supported, then "
            "`arfc_claim_record_status()`"
        ),
        "gate": "`arfc_gate(strict=true)`",
        "checkpoint": "`arfc_checkpoint(cluster_id)`",
        "revision_record": (
            '`arfc_revision_record(tag="draft-<name>-NN", cluster_id, '
            "normative_change, note)`"
        ),
        "draft_commit": "`arfc_draft_commit(message)`",
        "revision_tag": (
            "`arfc_revision_tag(tag, message)` — it runs the strict manifest gate, "
            "creates the tag, runs the strict citation gate and deletes the tag "
            "again on findings"
        ),
        "citation_gate": "`arfc_citation_gate(strict=true)`",
        "question_draft": (
            '`arfc_question_draft(question="<question quoting the claim text '
            'verbatim>", claim_ids=[<id>])`'
        ),
    },
}


def render_loop(arm: str) -> str:
    """Render the loop template with one invocation table.

    Raises:
        ExperimentError: If ``arm`` has no table or a slot stays unfilled.
    """
    if arm not in INVOCATIONS:
        raise ExperimentError(
            f"no invocation table for {arm!r}; tables: {', '.join(INVOCATIONS)}"
        )
    table = INVOCATIONS[arm]
    template = TEMPLATE.read_text()
    missing = sorted(set(SLOT.findall(template)) - set(table))
    if missing:
        raise ExperimentError(f"table {arm!r} leaves slots unfilled: {missing}")
    return SLOT.sub(lambda match: table[match.group(1)], template)


def strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block, if any."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    return text if end < 0 else text[end + len("\n---\n") :].lstrip("\n")


def arm_prompt(arm: str, plugin_root: Path) -> str:
    """The appended system prompt of one arm: loop plus the neutral texts."""
    parts = [render_loop(arm)]
    for relative in NEUTRAL_TEXTS:
        parts.append(strip_frontmatter(plugin_root.joinpath(*relative).read_text()))
    return "\n\n".join(part.rstrip("\n") for part in parts) + "\n"


def write_plugin_skill(plugin_root: Path) -> Path:
    """Regenerate the plugin's loop SKILL.md from the interactive table."""
    target = plugin_root / "skills" / "arfc-reconstruction-loop" / "SKILL.md"
    target.write_text(SKILL_FRONTMATTER + render_loop("interactive"))
    return target


def unified_diff(a: str, b: str, a_label: str, b_label: str) -> str:
    """A unified diff of two renderings, labelled for publication."""
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile=a_label,
            tofile=b_label,
        )
    )
```

- [ ] **Step 5: Register `render`** in `experiment/cli.py` — parser:

```python
    render = commands.add_parser("render", help="Regenerate the plugin SKILL.md.")
    render.add_argument("--plugin-dir", type=Path, default=None)
```

dispatch:

```python
        elif args.command == "render":
            from .render import write_plugin_skill

            plugin_dir = args.plugin_dir or Path(__file__).resolve().parents[1] / "plugins" / "ai-rfc"
            print(f"wrote {write_plugin_skill(plugin_dir.resolve())}")
```

- [ ] **Step 6: Regenerate the plugin skill and run the tests**

Run: `cd $R && $PY -m experiment render && git -C $R diff --stat plugins/ai-rfc/skills/arfc-reconstruction-loop/SKILL.md && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: `wrote …/SKILL.md`; the diff shows the preamble now naming `arfc_revision_tag`, step 8 naming the commit/tag operations, and `Bash(sqlite3 *)` in `allowed-tools`; 27 passed (20 + 7).

- [ ] **Step 7: Commit (nested repo)**

```bash
git -C $R add experiment/prompts/loop.tmpl.md experiment/render.py experiment/cli.py experiment/tests/test_render.py plugins/ai-rfc/skills/arfc-reconstruction-loop/SKILL.md
git -C $R commit -m "feat: render the loop skill and the arm prompts from one template"
```

### Task 9: `experiment/workspace.py` — pristine workspace, window pre-seeding, digest, per-run copy

> **SUPERSEDED — done on 2026-08-27.** This task was re-cut into four reviewer-gated tasks and executed as `docs/superpowers/plans/2026-08-27-arfc-phase-c-workspace.md` (nested-repo commits `2e3a24c`, `17da2bc`, `24320a4`, `9e20d2d`). That plan also corrects two defects below: Step 2's drift assertion lists its entries in the wrong order (`verify_digest` returns them path-sorted, so `unexpected: extra.txt` precedes `modified: manifest.yaml`), and Step 6's `32 passed` was computed from a stale baseline — the suite now gates at 46. Read the 2026-08-27 plan, not this section.

Spec §3 (D27). Tests drive the whole pipeline on the fixture workspace with a local git repo standing in for the auto-i-d-template; the real aioquic run is Task 10.

**Files:**
- Create: `$R/experiment/workspace.py`, `$R/experiment/prompts/draft-skeleton.md`, `$R/experiment/tests/test_workspace.py`
- Modify: `$R/experiment/cli.py` (add `workspace prepare`)

**Interfaces:**
- Consumes: `panther.plugins.services.testers.a_rfc.draft.checkpoint.write_checkpoint(manifest_path, timeline_dir, cluster_id, out) -> Path`; `…a_rfc.timeline.store.read_clusters(dir) -> tuple[dict, ...]`; `…a_rfc.views.cli.main(argv) -> int`.
- Produces: `Target(name, source, forge_snapshot, window, draft_name, rfc_id, title, abbrev)` with `.pristine_name`; `AIOQUIC`, `TARGETS`; `TEMPLATE_URL`, `TEMPLATE_COMMIT`, `TEMPLATE_STRIP`, `HARNESS_MARKER = "harness.json"`, `DIGEST_FILE = "pristine.sha256"`, `RECORD_FILE = "pristine.json"`; `out_of_window(ordinals, window) -> list[int]`; `scaffold_draft(dest, target, *, template, template_commit) -> str`; `preseed(workspace, panther_repo, ordinals) -> list[str]`; `write_digest(root) -> Path`; `verify_digest(root) -> list[str]`; `copy_workspace(pristine, dest) -> Path`; `prepare(target, *, root, panther_repo, template, template_commit) -> Path`.

- [ ] **Step 1: Write the draft skeleton** `$R/experiment/prompts/draft-skeleton.md` (a `string.Template`; the author block is the one the MARK draft already uses; note the Conventions sentence deliberately carries no backticked `a_rfc:` token, which the citation gate would otherwise extract as a cited claim):

```markdown
---
title: "$title"
abbrev: "$abbrev"
docname: $draft_name-latest
category: info

ipr: trust200902
area: General
workgroup: Individual Submission
keyword: Internet-Draft

stand_alone: yes
smart_quotes: no
pi: [toc, sortrefs, symrefs]

author:
 -
    ins: C. Crochet
    name: Christophe Crochet
    organization: UCLouvain
    email: christophe.cr.dev@gmail.com

normative:

informative:


--- abstract

This document reconstructs the specification of $target from its
implementation history. Each revision reflects the implementation as it
stood at one cluster of its development timeline; every normative statement
cites a claim in the accompanying evidence manifest, whose status is
adjudicated from anchored evidence rather than asserted.


--- middle

# Introduction

This document is reconstructed from the implementation's repository
history, one timeline cluster at a time. This revision holds no normative
statements yet.

# Conventions and Definitions

{::boilerplate bcp14-tagged}

Claim citations are backticked tokens that name a claim id in the evidence
manifest checkpointed beside this revision; the citation gate verifies that
every cited claim exists there.


--- back
```

- [ ] **Step 2: Write the failing tests** (`$R/experiment/tests/test_workspace.py`):

```python
import json
from pathlib import Path

import pytest

from ai_rfc_server.testing import git
from experiment import ExperimentError
from experiment.workspace import (
    Target,
    copy_workspace,
    out_of_window,
    prepare,
    verify_digest,
)


@pytest.fixture
def template_repo(tmp_path: Path) -> tuple[str, str]:
    repo = tmp_path / "template"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / ".gitignore").write_text("draft-*\n*.swp\n")
    (repo / "Makefile").write_text("all:\n\t@echo build\n")
    (repo / "CLAUDE.md").write_text("template agent notes\n")
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text("{}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "template", date="2026-01-01T00:00:09+00:00")
    return str(repo), git(repo, "rev-parse", "HEAD")


def _target(source: Path) -> Target:
    return Target(
        name="fixture",
        source=source,
        forge_snapshot=None,
        window=(2, 2),
        draft_name="draft-test-fixture",
        rfc_id="FIX-1",
        title="Fixture",
        abbrev="Fix",
    )


def _cluster_ids(pristine: Path) -> list[str]:
    rows = (pristine / "timeline" / "clusters.jsonl").read_text().splitlines()
    return [json.loads(row)["id"] for row in rows]


def _prepare(fixture_workspace, panther_repo, template_repo, tmp_path):
    template, commit = template_repo
    return prepare(
        _target(fixture_workspace),
        root=tmp_path / "root",
        panther_repo=panther_repo,
        template=template,
        template_commit=commit,
    )


def test_out_of_window_keeps_order():
    assert out_of_window(range(1, 8), (2, 4)) == [1, 5, 6, 7]


def test_prepare_builds_the_pristine_tree(
    fixture_workspace, panther_repo, template_repo, tmp_path
):
    pristine = _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    assert pristine == tmp_path / "root" / "pristine" / "fixture-w02-02"
    ids = _cluster_ids(pristine)
    assert sorted(p.name for p in (pristine / "clusters").iterdir()) == sorted(ids)
    assert (pristine / "manifest.yaml").read_text() == (
        "rfc: FIX-1\ntitle: Fixture\nrequirements: {}\n"
    )
    assert (pristine / "questions.yaml").read_text() == "questions: {}\n"
    assert (pristine / "interviews").is_dir()
    draft = pristine / "draft"
    assert (draft / "draft-test-fixture.md").exists() and (draft / "Makefile").exists()
    assert not (draft / "CLAUDE.md").exists() and not (draft / ".claude").exists()
    assert "draft-*" not in (draft / ".gitignore").read_text()
    assert "docname: draft-test-fixture-latest" in (draft / "draft-test-fixture.md").read_text()
    assert git(draft, "log", "--oneline").count("\n") == 0
    assert git(draft, "config", "user.name") == "arfc-harness"
    record = json.loads((pristine / "pristine.json").read_text())
    assert record["template_commit"] == template_repo[1]
    assert record["pre_seeded"] == [ids[0]]
    assert record["draft_head"] == git(draft, "rev-parse", "HEAD")
    assert (pristine / "checkpoints" / ids[0] / "harness.json").exists()
    assert (pristine / "checkpoints" / ids[0] / "checkpoint.json").exists()
    assert not (pristine / "checkpoints" / ids[1]).exists()
    assert verify_digest(pristine) == []


def test_prepare_refuses_to_overwrite(
    fixture_workspace, panther_repo, template_repo, tmp_path
):
    _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    with pytest.raises(ExperimentError) as excinfo:
        _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    assert "prepared once" in str(excinfo.value)


def test_copy_verifies_and_tamper_is_detected(
    fixture_workspace, panther_repo, template_repo, tmp_path
):
    pristine = _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    copy = copy_workspace(pristine, tmp_path / "run" / "workspace")
    assert verify_digest(copy) == []
    assert git(copy / "draft", "rev-parse", "HEAD") == git(pristine / "draft", "rev-parse", "HEAD")
    (copy / "manifest.yaml").write_text("rfc: X\ntitle: t\nrequirements: {}\n")
    (copy / "extra.txt").write_text("x\n")
    assert verify_digest(copy) == ["modified: manifest.yaml", "unexpected: extra.txt"]
    with pytest.raises(ExperimentError):
        copy_workspace(pristine, tmp_path / "run" / "workspace")


def test_window_is_the_only_unprocessed_range(
    fixture_workspace, panther_repo, template_repo, tmp_path, monkeypatch
):
    pristine = _prepare(fixture_workspace, panther_repo, template_repo, tmp_path)
    monkeypatch.setenv("ARFC_WORKSPACE", str(pristine))
    from ai_rfc_server.core.queries import cluster_next, status
    from ai_rfc_server.paths import resolve_context

    ctx = resolve_context()
    assert cluster_next(ctx)["ordinal"] == 2
    composite = status(ctx)
    assert composite["clusters_total"] == 2 and composite["clusters_processed"] == 1
```

- [ ] **Step 3: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_workspace.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment.workspace'`.

- [ ] **Step 4: Implement `$R/experiment/workspace.py`**

```python
"""Pristine reconstruction workspaces: prepared once, copied per run.

A pristine workspace is the deterministic output of the substrate stages
plus the window pre-seeding of D27, digest-manifested so every run starts
from bytes the campaign recorded. Nothing here mutates a substrate artifact:
out-of-window clusters are marked processed by checkpoints of the empty
manifest, each carrying a harness sidecar the analysis excludes.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from . import ExperimentError

PROMPTS = Path(__file__).parent / "prompts"
DRAFT_SKELETON = PROMPTS / "draft-skeleton.md"
TEMPLATE_URL = "https://github.com/ElNiak/auto-i-d-template"
TEMPLATE_COMMIT = "dcdd985a86afad97a50f7b5e1b613f57c194b774"
TEMPLATE_STRIP = (
    ".claude",
    ".claude-plugin",
    ".codacy",
    ".serena",
    ".specify",
    "CLAUDE.md",
    ".mcp.example.json",
    ".mcp.json",
)
HARNESS_NAME = "arfc-harness"
HARNESS_EMAIL = "arfc-harness@localhost"
PINNED_DATE = "2026-08-26T00:00:00+00:00"
HARNESS_MARKER = "harness.json"
DIGEST_FILE = "pristine.sha256"
RECORD_FILE = "pristine.json"
_SKIP_FROM_DIGEST = frozenset({DIGEST_FILE, RECORD_FILE})


@dataclass(frozen=True)
class Target:
    """One reconstruction target and the window the experiment processes."""

    name: str
    source: Path
    forge_snapshot: Path | None
    window: tuple[int, int]
    draft_name: str
    rfc_id: str
    title: str
    abbrev: str

    @property
    def pristine_name(self) -> str:
        """Directory name encoding target and window, e.g. ``aioquic-w02-11``."""
        low, high = self.window
        return f"{self.name}-w{low:02d}-{high:02d}"


AIOQUIC = Target(
    name="aioquic",
    source=Path("reconstructions/aioquic"),
    forge_snapshot=Path(
        "forge/github.com__aiortc__aioquic/snapshot-2026-08-25T15-16-59Z"
    ),
    window=(2, 11),
    draft_name="draft-elniak-aioquic-reconstructed",
    rfc_id="AIOQUIC-RECON",
    title="aioquic: A Reconstructed Specification",
    abbrev="aioquic Reconstructed",
)
TARGETS: dict[str, Target] = {"aioquic": AIOQUIC}


def _substrate(panther_repo: Path):  # noqa: ANN202 - substrate modules, resolved lazily
    if str(panther_repo) not in sys.path:
        sys.path.insert(0, str(panther_repo))
    from panther.plugins.services.testers.a_rfc.draft.checkpoint import (
        write_checkpoint,
    )
    from panther.plugins.services.testers.a_rfc.timeline.store import read_clusters
    from panther.plugins.services.testers.a_rfc.views import cli as views_cli

    return write_checkpoint, read_clusters, views_cli


def _git(repo: Path, *args: str, date: str | None = None) -> str:
    env = dict(os.environ)
    if date is not None:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        raise ExperimentError(
            f"git {' '.join(args)} in {repo} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _git_version() -> str:
    return subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()


def out_of_window(ordinals: Iterable[int], window: tuple[int, int]) -> list[int]:
    """The ordinals outside ``window`` (inclusive bounds), in input order."""
    low, high = window
    return [ordinal for ordinal in ordinals if ordinal < low or ordinal > high]


def scaffold_draft(
    dest: Path, target: Target, *, template: str, template_commit: str
) -> str:
    """Clone the template at its pin, strip its agent files, seed the draft.

    Args:
        dest: Where the draft repository is created (must not exist).
        target: Names the draft file and its front matter.
        template: Clone source (URL or local path).
        template_commit: The commit the scaffold is pinned to.

    Returns:
        The draft repository's HEAD after the scaffold commit.

    Raises:
        ExperimentError: If ``dest`` exists or any git step fails.
    """
    if dest.exists():
        raise ExperimentError(f"{dest} exists; a draft is scaffolded once")
    cloned = subprocess.run(
        ["git", "clone", "-q", template, str(dest)], capture_output=True, text=True
    )
    if cloned.returncode != 0:
        raise ExperimentError(f"cloning {template} failed: {cloned.stderr.strip()}")
    _git(dest, "checkout", "-q", template_commit)
    shutil.rmtree(dest / ".git")
    for name in TEMPLATE_STRIP:
        path = dest / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    ignore = dest / ".gitignore"
    if ignore.exists():
        kept = [line for line in ignore.read_text().splitlines() if line.strip() != "draft-*"]
        ignore.write_text("\n".join(kept) + "\n")
    skeleton = string.Template(DRAFT_SKELETON.read_text()).substitute(
        title=target.title,
        abbrev=target.abbrev,
        draft_name=target.draft_name,
        target=target.name,
    )
    (dest / f"{target.draft_name}.md").write_text(skeleton)
    _git(dest, "init", "-q", "-b", "main")
    _git(dest, "config", "user.name", HARNESS_NAME)
    _git(dest, "config", "user.email", HARNESS_EMAIL)
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "scaffold from auto-i-d-template", date=PINNED_DATE)
    return _git(dest, "rev-parse", "HEAD")


def preseed(workspace: Path, panther_repo: Path, ordinals: Iterable[int]) -> list[str]:
    """Checkpoint the workspace manifest against each ordinal and mark it pre-seeded.

    Returns:
        The cluster ids checkpointed, in the order given.

    Raises:
        ExperimentError: If an ordinal has no cluster.
    """
    write_checkpoint, read_clusters, _ = _substrate(panther_repo)
    by_ordinal = {row["ordinal"]: row["id"] for row in read_clusters(workspace / "timeline")}
    seeded = []
    for ordinal in ordinals:
        cluster_id = by_ordinal.get(ordinal)
        if cluster_id is None:
            raise ExperimentError(f"no cluster with ordinal {ordinal}")
        checkpoint_dir = write_checkpoint(
            workspace / "manifest.yaml",
            workspace / "timeline",
            cluster_id,
            workspace / "checkpoints",
        )
        (checkpoint_dir / HARNESS_MARKER).write_text(
            json.dumps(
                {"pre_seeded": True, "reason": "outside window", "ordinal": ordinal},
                sort_keys=True,
            )
            + "\n"
        )
        seeded.append(cluster_id)
    return seeded


def _digests(root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root)
        if ".git" in relative.parts or relative.name in _SKIP_FROM_DIGEST:
            continue
        found[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def write_digest(root: Path) -> Path:
    """Write ``pristine.sha256`` over every regular file outside ``.git``."""
    lines = [f"{digest}  {relative}" for relative, digest in _digests(root).items()]
    target = root / DIGEST_FILE
    target.write_text("\n".join(lines) + "\n")
    return target


def verify_digest(root: Path) -> list[str]:
    """Differences between a tree and its digest manifest; empty means verified."""
    manifest_path = root / DIGEST_FILE
    if not manifest_path.exists():
        return [f"{DIGEST_FILE} is missing"]
    expected: dict[str, str] = {}
    for line in manifest_path.read_text().splitlines():
        if line.strip():
            digest, _, relative = line.partition("  ")
            expected[relative] = digest
    actual = _digests(root)
    problems = []
    for relative in sorted(set(expected) | set(actual)):
        if relative not in actual:
            problems.append(f"missing: {relative}")
        elif relative not in expected:
            problems.append(f"unexpected: {relative}")
        elif actual[relative] != expected[relative]:
            problems.append(f"modified: {relative}")
    return problems


def copy_workspace(pristine: Path, dest: Path) -> Path:
    """Copy a pristine workspace for one run and verify the copy.

    Raises:
        ExperimentError: If ``dest`` exists, the copy does not reproduce the
            digest manifest, or a nested repository HEAD moved.
    """
    if dest.exists():
        raise ExperimentError(f"{dest} exists; a run never reuses a workspace")
    shutil.copytree(pristine, dest, symlinks=False)
    problems = verify_digest(dest)
    if problems:
        raise ExperimentError(f"copied workspace does not verify: {problems[:5]}")
    record = json.loads((dest / RECORD_FILE).read_text())
    for name, key in (("clone", "clone_head"), ("draft", "draft_head")):
        head = _git(dest / name, "rev-parse", "HEAD")
        if head != record[key]:
            raise ExperimentError(f"{name} HEAD {head} differs from recorded {record[key]}")
    return dest


def prepare(
    target: Target,
    *,
    root: Path,
    panther_repo: Path,
    template: str = TEMPLATE_URL,
    template_commit: str = TEMPLATE_COMMIT,
) -> Path:
    """Build the pristine workspace of ``target`` under ``root/pristine/``.

    Steps: copy the substrate outputs, emit and verify every view, write the
    empty manifest and registers, scaffold the draft, pre-seed every
    out-of-window ordinal, record provenance, write the digest manifest.

    Returns:
        The pristine directory.

    Raises:
        ExperimentError: If the pristine directory exists, a source part is
            missing, or a substrate stage fails.
    """
    pristine = root / "pristine" / target.pristine_name
    if pristine.exists():
        raise ExperimentError(f"{pristine} exists; a pristine workspace is prepared once")
    source = target.source if target.source.is_absolute() else panther_repo / target.source
    for part in ("clone", "corpus", "timeline"):
        if not (source / part).is_dir():
            raise ExperimentError(f"{source / part} is missing")
    pristine.mkdir(parents=True)
    for part in ("clone", "corpus", "timeline"):
        shutil.copytree(source / part, pristine / part, symlinks=False)
    snapshot = None
    if target.forge_snapshot is not None:
        snapshot = pristine / target.forge_snapshot
        shutil.copytree(source / target.forge_snapshot, snapshot, symlinks=False)
    clone_head = _git(pristine / "clone", "rev-parse", "HEAD")

    _, read_clusters, views_cli = _substrate(panther_repo)
    views_args = [
        str(pristine / "timeline"),
        "--corpus",
        str(pristine / "corpus"),
        "--repo",
        str(pristine / "clone"),
        "--out",
        str(pristine / "clusters"),
    ]
    if snapshot is not None:
        views_args += ["--forge", str(snapshot)]
    if views_cli.main(views_args) != 0:
        raise ExperimentError("view emission failed; see stderr")
    if views_cli.main(views_args + ["--verify"]) != 0:
        raise ExperimentError("views do not reproduce byte-for-byte; see stderr")

    (pristine / "manifest.yaml").write_text(
        yaml.safe_dump(
            {"rfc": target.rfc_id, "title": target.title, "requirements": {}},
            sort_keys=False,
        )
    )
    (pristine / "questions.yaml").write_text("questions: {}\n")
    (pristine / "revisions.yaml").write_text("revisions: {}\n")
    (pristine / "interviews").mkdir()
    draft_head = scaffold_draft(
        pristine / "draft", target, template=template, template_commit=template_commit
    )

    ordinals = [row["ordinal"] for row in read_clusters(pristine / "timeline")]
    seeded = preseed(pristine, panther_repo, out_of_window(ordinals, target.window))

    record: dict[str, Any] = {
        "target": target.name,
        "window": list(target.window),
        "source": str(source),
        "clone_head": clone_head,
        "draft_head": draft_head,
        "template": template,
        "template_commit": template_commit,
        "template_stripped": list(TEMPLATE_STRIP),
        "forge_snapshot": str(target.forge_snapshot) if target.forge_snapshot else None,
        "cluster_count": len(ordinals),
        "pre_seeded": seeded,
        "git_version": _git_version(),
        "python": sys.version.split()[0],
    }
    (pristine / RECORD_FILE).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    write_digest(pristine)
    return pristine
```

- [ ] **Step 5: Register `workspace prepare`** in `experiment/cli.py` — parser:

```python
    workspace = commands.add_parser("workspace", help="Pristine workspaces.")
    workspace_verbs = workspace.add_subparsers(dest="verb", required=True)
    prepare = workspace_verbs.add_parser("prepare", help="Build a pristine workspace.")
    _add_root(prepare)
    prepare.add_argument("target", choices=sorted(TARGETS))
    prepare.add_argument("--panther-repo", type=Path, required=True)
    prepare.add_argument("--template", default=TEMPLATE_URL)
    prepare.add_argument("--template-commit", default=TEMPLATE_COMMIT)
```

(import `TARGETS, TEMPLATE_COMMIT, TEMPLATE_URL, prepare as prepare_workspace` from `.workspace` at the top of `cli.py`) and dispatch:

```python
        elif args.command == "workspace" and args.verb == "prepare":
            pristine = prepare_workspace(
                TARGETS[args.target],
                root=root,
                panther_repo=args.panther_repo.resolve(),
                template=args.template,
                template_commit=args.template_commit,
            )
            record = json.loads((pristine / "pristine.json").read_text())
            print(f"pristine: {pristine}")
            print(f"clusters: {record['cluster_count']}  pre-seeded: {len(record['pre_seeded'])}  window: {record['window']}")
```

(add `import json` to `cli.py`).

- [ ] **Step 6: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 32 passed (27 + 5).

- [ ] **Step 7: Commit (nested repo)**

```bash
git -C $R add experiment/workspace.py experiment/prompts/draft-skeleton.md experiment/cli.py experiment/tests/test_workspace.py
git -C $R commit -m "feat: pristine workspaces with window pre-seeding and digest verification"
```

### Task 10: The real aioquic pristine workspace, submodule bump, wrap-up

**Files:**
- Create (outside both repos): `~/arfc-experiments/pristine/aioquic-w02-11/`
- Modify (PANTHER): the `ai_rfc` submodule pointer

- [ ] **Step 1: Prepare aioquic (sandbox OFF: clones github.com/ElNiak/auto-i-d-template and writes under `~`)**

Run: `cd $R && $PY -m experiment profile init --root ~/arfc-experiments && $PY -m experiment workspace prepare aioquic --root ~/arfc-experiments --panther-repo $W`
Expected (5–15 min; view emission plus verification over 342 clusters): `pristine: ~/arfc-experiments/pristine/aioquic-w02-11` and `clusters: 342  pre-seeded: 332  window: [2, 11]`.

- [ ] **Step 2: Sanity-check the pristine tree**

Run: `P=~/arfc-experiments/pristine/aioquic-w02-11; ls $P/clusters | wc -l; ls $P/checkpoints | wc -l; ls $P/checkpoints/c0001-epoch-a80c3bdd1e02; git -C $P/draft log --oneline; git -C $P/clone rev-parse HEAD; cd $S/src && PANTHER_REPO=$W ARFC_WORKSPACE=$P $PY -m ai_rfc_server.cli cluster-next | head -5 && PANTHER_REPO=$W ARFC_WORKSPACE=$P $PY -m ai_rfc_server.cli status | grep -E '"clusters_(total|processed)"|next_cluster'`
Expected: `342`; `332`; `checkpoint.json harness.json manifest.yaml`; one scaffold commit; `6d36838d008c2202c337142fa07e8bf80e96bac8`; `cluster-next` prints `"id": "c0002-pr-60258445de47"`; status shows `clusters_total: 342`, `clusters_processed: 332`, `next_cluster: "c0002-pr-60258445de47"`.

- [ ] **Step 3: Bump the submodule pointer (PANTHER)**

Run: `cd $W && git -C $R log --oneline -1 && git add panther/plugins/services/testers/a_rfc/ai_rfc && git commit -m "chore(a_rfc): bump ai_rfc submodule to the Phase C foundations commit" && git submodule status panther/plugins/services/testers/a_rfc/ai_rfc`
Expected: the submodule status line shows the nested repo's new HEAD without a `+`/`-` prefix.

- [ ] **Step 4: Full verification**

Run: `cd $W && SSLKEYLOGFILE= $PY -m pytest tests/unit/plugins/services/testers/a_rfc -n auto -q 2>&1 | tail -1; cd $S && SSLKEYLOGFILE= $PY -m pytest -q 2>&1 | tail -1; cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q 2>&1 | tail -1; cd $W && SSLKEYLOGFILE= $PY -m pytest tests/ -n auto -m unit -q 2>&1 | tail -1`
Expected: `207 passed`; `38 passed`; `46 passed`; the full unit suite at the Task-0 baseline plus one (the 19 failures + 4 errors outside a_rfc are pre-existing: webapp observer, docker templates, panther_ivy collection — report them, do not touch them).

- [ ] **Step 5: Report** — commits in both repos (SHAs), the spike verdict from `docs/spike-s0.md`, the pristine record (`pristine.json`), and anything deferred. Do not push.

---

## Self-review (performed while writing)

**Spec coverage.** §1 draft operations → Tasks 6–7; §1 template/renderings + SKILL.md byte-equality → Task 8; §1 `.mcp.json` decision → Task 5 Step 8; §1 empty-manifest test → Task 1; §2 profile → Task 3; §2 flag table → Task 4; §2 spike S0 checks 1–9 and fallback → Task 5; §3 prepare/pre-seed/digest/copy → Task 9, real run → Task 10; §6 (tests without network or model; `_build_workspace` moved to `ai_rfc_server/testing.py`) → Tasks 2–9. Not in this plan, by design: §4 runner/matrix, §5 audit/metrics/report, §7 pilot — the harness plan.

**Placeholder scan.** No TBD/TODO; every code step carries the code; the only user-run command (the profile login) is spelled out.

**Type consistency.** `build_workspace`/`git` names match between Task 2 and Tasks 3, 6, 7, 9; `arm_flags`/`profile`/`mcp_config` match between Tasks 4 and 5; `render_loop`/`SKILL_FRONTMATTER`/`arm_prompt`/`unified_diff` match between Task 8's tests and implementation; `Target` fields, `HARNESS_MARKER`, `RECORD_FILE`, `DIGEST_FILE` match between Task 9's tests and implementation and are what the harness plan imports.

**Known judgement calls.** `commit_draft` stages with `git add -A` inside the draft repo only (the template's `.gitignore` governs what lands). `tag_revision` returns exit codes from the gates rather than raising, because a gate refusal is information, not an error. Pre-seeding 331 checkpoints costs a few seconds in-process; it was chosen over truncating `clusters.jsonl` to keep every substrate artifact untouched.
