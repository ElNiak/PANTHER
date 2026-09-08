# ai_rfc One Door — CLI-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One console script `ai-rfc` driven by one `recon.yaml`: `init` builds a workspace from a repository URL, `run` performs every deterministic stage that is next and stops at the agent boundary, `status`/`verify`/`doctor` read one ledger and one config — no `--panther-repo`, no cwd requirement, no closed target table.

**Architecture:** A declarative field table validates `recon.yaml` and renders its own reference; an argparse root mounts every existing sub-CLI through a `configure(parser)` function and adds the lifecycle verbs; `ai_rfc/ledger.py` becomes the single reader of per-cluster progress and the five readers it replaces call it; `init` absorbs the harness's workspace preparation (clone at pin, forge snapshot, adopter draft scaffold, sealed references, sealed config, digest); `run` walks the pipeline's `DISPATCH` for history/timeline/views and stops at mining with the ledger printed. Sessions (CLI-2) and the folding of the agent verbs (CLI-3) come later; nothing here changes the MCP tools, the parity CLI, or the `python -m ai_rfc.<sub>` entry points the server core and the raw arm still use.

**Tech Stack:** Python 3.10 (stdlib + PyYAML), argparse, pytest 8 + pytest-xdist (`--import-mode=importlib`), git.

**Spec:** `docs/superpowers/specs/2026-09-03-arfc-one-door-design.md` (D53–D61; §2 field table, §3 root, §4 ledger, §7 error handling, §8 testing). Roadmap position: CLI-1 satisfies SP3's config+root+doctor and SP4's ledger from `docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md`.

## Global Constraints

- **Layout.** Executes AFTER SP1 (extraction), SP7a and SP7b (D55), on the ai_rfc repository layout: `AIRFC` = `$PANTHER/panther/plugins/services/testers/ai_rfc` (its own git repository). Packages `ai_rfc/` (substrate: `check/`, `history/`, `forge/`, `timeline/`, `views/`, `draft/`, `coverage/`, `pipeline/`, `models.py`, `schema.py`, …), `ai_rfc/server/`, `ai_rfc/experiment/` (with `prompts/`, `toolchain.py` from SP7a, `workspace.py` with the adopter `scaffold_draft` from SP7a), `plugins/ai-rfc/`, `docs/`; tests `tests/substrate/`, `tests/server/`, `tests/experiment/`. `PY` = `$PANTHER/.venv/bin/python`. Precondition (Task 0): `ls $AIRFC/ai_rfc/draft/build.py $AIRFC/ai_rfc/experiment/toolchain.py $AIRFC/tests/substrate` all exist, `$PY -c "import ai_rfc.experiment, ai_rfc.server"` succeeds, both trees clean, full suite green — otherwise STOP.
- **Anchors** in this plan were verified on the pre-move layout (PANTHER `2e5354b6c`, harness `26e522a`) and cite symbols; re-anchor by `grep -n "def <name>"` before editing. Another session commits to the same branch: run `git log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'` and `git status --short` in BOTH repositories before every task; **if `git status --short` lists files you did not touch, do not commit** (pre-commit stashes a peer's unstaged work around your commit).
- **Stage by explicit path**, never `git add -A`/`.`. Commit format in `$AIRFC`: `type: lowercase summary` (no scope); in `$PANTHER`: `type(scope): lowercase summary`. No `--no-verify`. `docs/` under `$PANTHER` is gitignored but tracked → `git add -f`. Every commit ends with the trailer `Claude-Session: <this session's URL>`.
- **Every commit carries an explicit pathspec (D3, non-negotiable).** The `git commit -m "…"` lines in this plan's steps are written **without** one and **must not be run as written**. A bare `git commit` commits the whole index, so a peer who staged a file between your `git add` and your `git commit` rides along in your commit — this has already cost this project one mis-attributed commit (`6892933`), and SP7a recorded the same trap. Rewrite every commit in this plan as `git commit -m "<the plan's message>" -- <exactly the paths you just staged>`, and confirm afterwards with `git show --stat HEAD` that only your files are in it. The `$AIRFC` submodule has **no pre-commit hook**, so nothing stashes a peer's work for you there; `$PANTHER` has one that stashes and restores every unstaged file around your commit. Run `git status --short` in the repository you are committing to immediately before every commit, and if a file you did not touch is *staged* by someone else, use the `--only` form: `git commit --only -m "…" -- <your paths>`.
- **One git command per shell call, with literal paths.** The harness's worktree guard refuses git inside compound (`&&`-chained) commands, loops, variables and heredocs. Several steps in this plan chain `cd $X && git …`; split them.
- **Tests**: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto` (baseline after SP7b: read it from the last SP7b commit's message; record the number in Task 0). Sandbox off for `pytest`, nested git and `git push`. `mypy --follow-imports=silent`; `flake8 --max-line-length=88`; `black --check`.
- **Never run** `panther docs build`, `panther_builder.py clean|package-dev`, or `python -m ai_rfc.experiment audit|analyze` against `~/ai-rfc-experiments/campaigns/mark-full-1` or the pilot. The finished MARK A1 workspace is read-only evidence; work on copies (`~/ai-rfc-experiments/baselines/mark-a1-2026-09-03` is a sealed copy).
- **No shims.** `experiment/workspace.py`'s `Target`/`TARGETS` and `prepare`'s target-table path are removed when `init` replaces them (Task 5); campaigns prepare from a config. `python -m ai_rfc.<sub>` keeps working because each module keeps a `main()` around its `configure()` — that is the server's and the raw arm's door until CLI-3, not a compatibility layer.
- **The substrate stays model-free and, except acquisition (`init`: clone + forge), network-free.** `run` never opens a socket.
- Line length 88, Google docstrings on public functions, `from __future__ import annotations`, comments only for a non-obvious *why*. Fixed dates in fixtures (`2026-01-01T00:00:09+00:00` style). A test needle must never match a fixture's own name; a RED test must fail at the path the change addresses.
- **Registered-verb module layout (D1, non-negotiable — it is test-enforced).** Every row of `ENTRY_POINTS` names a **`cli` module inside its own package**, and that package carries a `__main__.py`. `EntryPoint.module`'s own docstring (`ai_rfc/entrypoints.py:40-41`) states it: "Dotted path of the `cli` module, not of its package — the `__main__` guard test derives that name by trimming one segment." Two tests enforce it: `tests/substrate/test_cli_conventions.py:136-151` asserts **set equality** between `{entry.module for entry in ENTRY_POINTS}` and every `cli.py` found by `rglob` (excluding the root door and anything under `server/` or `experiment/`), and `:48-58` derives `<package>.__main__` by trimming one segment and imports it. All ten existing packages comply. Therefore **each lifecycle verb is its own sub-package**: `ai_rfc/lifecycle/<verb>/{__init__.py,__main__.py,cli.py}`, registered as `f"{PACKAGE}.lifecycle.<verb>.cli"`. The seven verbs are `config`, `init`, `run`, `status`, `verify`, `doctor`, `toolchain`. Shared implementation stays as **flat modules** beside them — `ai_rfc/lifecycle/{workspace,common,profile}.py` — because they are not registered verbs. Inside a verb's `cli.py` the shared imports are therefore two dots (`from ..common import …`, `from ..workspace import Layout`) and the package imports are three (`from ... import __version__`, `from ...config import load_config`). Each `__main__.py` is the existing one-liner pattern the other packages use; copy `ai_rfc/draft/__main__.py`. Do NOT register a flat `ai_rfc/lifecycle/<verb>.py`: it fails both tests above.

## File Structure

| File (under `$AIRFC`) | Task | Responsibility after the change |
|---|---|---|
| `ai_rfc/config.py` (new) | 1 | `FIELDS`, `Field`, `load_config`, `ReconConfig` and its section dataclasses, `ConfigError`, `example()`, `reference_markdown()`, `sealed_copy_drift()` |
| `ai_rfc/cli.py` | 2 | The argparse root: `main(argv)`, `build_parser()`, help sections, `--version`, `config example` |
| `ai_rfc/{check,history,forge,timeline,views,draft,coverage,pipeline}/cli.py` | 2 | `configure(parser)` + `run(args) -> int`; `main(argv)` keeps `python -m ai_rfc.<sub>` working |
| `ai_rfc/entrypoints.py` | 2 | Registry rows gain `configure`/`run`; sections gain "Lifecycle" and "Agent" |
| `ai_rfc/ledger.py` (new) | 3 | `ClusterState`, `clusters(workspace, window)`, `next_cluster`, `partial`, `window_of(workspace)`; the ONE progress reader |
| `ai_rfc/pipeline/state.py`, `ai_rfc/draft/completeness.py`, `ai_rfc/server/core/queries.py`, `ai_rfc/experiment/{progress,metrics,per_cluster}.py` | 3 | Read ledger rows instead of computing progress themselves |
| `ai_rfc/lifecycle/__init__.py`, `ai_rfc/lifecycle/workspace.py` (new, flat) | 4 | `Workspace` gains `config`, `init_record`, `refcache`, `runs`; `acquire()` (clone at pin + forge snapshot), `scaffold()`, `seal()`; digest helpers moved from `experiment/workspace.py` |
| `ai_rfc/lifecycle/init/{__init__,__main__,cli}.py` (new package, D1) | 4 | `ai-rfc init --config` |
| `ai_rfc/experiment/workspace.py` | 4, 5 | `prepare(config, …)` over `lifecycle.workspace`; `Target`/`TARGETS` removed; `preseed`, `reseal`, `copy_workspace` kept |
| `ai_rfc/lifecycle/common.py` (new, flat) | 5 | `load_sealed`, `report`, `add_config_argument`, `config_path_from` — shared by every verb, not itself a verb |
| `ai_rfc/lifecycle/{run,status,verify}/{__init__,__main__,cli}.py` (new packages, D1) | 5 | `ai-rfc run` (deterministic stages, boundary stop), `ai-rfc status`, `ai-rfc verify` |
| `ai_rfc/lifecycle/{doctor,toolchain}/{__init__,__main__,cli}.py` (new packages, D1), `ai_rfc/lifecycle/profile.py` (moved, flat), `ai_rfc/toolchain.py` (moved from `experiment/toolchain.py`) | 6 | `ai-rfc doctor`, `ai-rfc toolchain provision\|verify` |
| `$PANTHER/panther/cli/commands/ai_rfc.py` | 7 | Passthrough onto `ai_rfc.cli.main` (SP1 made it one; Task 7 pins the equality of help) |
| `README.md`, `ai_rfc/README.md`, `docs/experiment-protocol.md` | 7 | The one-door flow documented |
| `tests/cli/{test_config,test_root,test_init,test_run,test_status_verify,test_doctor}.py`, `tests/ledger/test_ledger.py`, `tests/experiment/test_workspace.py` | all | One test module per unit |

Vocabulary: **config** = `recon.yaml` as given; **sealed config** = `<workspace>/recon.yaml` written by `init`; **init record** = `<workspace>/init.json`; **ledger row** = one `ClusterState`; **experiments root** = `AI_RFC_EXPERIMENTS_ROOT` or `~/ai-rfc-experiments`, the default parent of `reconstructions/<name>`, `tools/` and `profile/`.

---

### Task 0: Preconditions and baseline

**Files:** none modified.

- [ ] **Step 1: Verify the layout and the trees**

```bash
cd $AIRFC && ls ai_rfc/draft/build.py ai_rfc/experiment/toolchain.py tests/substrate tests/experiment tests/server
SSLKEYLOGFILE= $PY -c "import ai_rfc.experiment, ai_rfc.server, ai_rfc.draft.build; print('imports ok')"
git status --short; git log -1 --format='%h %ad %s' --date=format:'%Y-%m-%d %H:%M:%S'
cd $PANTHER && git status --short; git log -1 --format='%h %ad %s' --date=format:'%Y-%m-%d %H:%M:%S'
```

Expected: every path exists, the import prints `imports ok`, both trees are clean. If any path is missing, SP7a/SP7b/SP1 have not all landed: STOP and report.

- [ ] **Step 2: Baseline the suite**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -2`
Expected: `N passed`, 0 failed. Write `N` into the commit message of Task 1 ("baseline N").

---

### Task 1: `recon.yaml` — the field table, the loader, the example and the reference

**Files:**
- Create: `ai_rfc/config.py`
- Test: `tests/cli/__init__.py` (empty), `tests/cli/test_config.py`

**Interfaces:**
- Consumes: PyYAML (already a dependency), `ai_rfc.__version__`.
- Produces: `Field(path: str, kind: str, required: bool, default: Any, choices: tuple[str, ...] | None, doc: str)`; `FIELDS: tuple[Field, ...]`; `ConfigError(ValueError)`; `ReconConfig` (frozen) with `name: str`, `workspace: Path`, `source: SourceConfig(repo, host, pin, token_env)`, `window: tuple[int, int] | None`, `draft: DraftConfig(name, title, abbrev, rfc_id, author: dict[str, str])`, `references: tuple[str, ...]`, `sessions: SessionsConfig | None` (`model, effort, budget_usd, timeout_s, attempts_per_cluster, consolidate_every, profile: Path | None, claude: str`), `toolchain: Path | None`, `stages: StagesConfig(history_cap: int | None, timeline_forge: bool, views_patches: str, lint_must_fraction_ceiling: float, build_targets: tuple[str, ...])`, `experiment: ExperimentConfig | None (arms, repeats, seed)`; `load_config(path: Path) -> ReconConfig`; `dump_config(config: ReconConfig) -> str` (byte-stable YAML of the validated values, used for the sealed copy); `example() -> str`; `reference_markdown() -> str`; `experiments_root() -> Path`; `drift(sealed: ReconConfig, given: ReconConfig) -> tuple[list[str], list[str]]` returning `(refused, noted)` per D57. Tasks 4–6 consume `load_config`, `dump_config`, `drift`; SP5 consumes `reference_markdown`.

**Why this shape.** One table drives validation, the starter file and the reference page, so they cannot disagree (R3). Validation is stdlib: a `kind` string per field (`str`, `path`, `int`, `float`, `bool`, `sha_or_ref`, `url_or_path`, `window`, `str_list`, `mapping`) and a `choices` tuple; the loader walks `FIELDS`, so an unknown key anywhere is an error (nothing is silently dropped — the trap `schema.load` had with `structures:`).

- [ ] **Step 1: Write the failing tests**

Create `tests/cli/test_config.py`:

```python
"""recon.yaml: one field table validates, exemplifies and documents itself."""

from pathlib import Path

import pytest
import yaml

from ai_rfc.config import (
    FIELDS,
    ConfigError,
    drift,
    dump_config,
    example,
    load_config,
    reference_markdown,
)

MINIMAL = """\
name: mark
source:
  repo: https://gitlab.cylab.be/cylab/mark
  pin: b901f36095d746ee99dfa85b3d2ad1fbe5f2c533
draft:
  name: draft-elniak-mark-reconstructed
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "recon.yaml"
    path.write_text(text)
    return path


def test_minimal_config_loads_with_documented_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_RFC_EXPERIMENTS_ROOT", str(tmp_path / "root"))
    config = load_config(_write(tmp_path, MINIMAL))
    assert config.name == "mark"
    assert config.source.host == "gitlab" and config.source.token_env == "GITLAB_TOKEN"
    assert config.workspace == tmp_path / "root" / "reconstructions" / "mark"
    assert config.window is None and config.sessions is None
    assert config.draft.title == "mark: A Reconstructed Specification"
    assert config.draft.rfc_id == "MARK-RECON"
    assert config.toolchain == tmp_path / "root" / "tools" / "toolchain.json"
    assert config.stages.timeline_forge is True and config.stages.views_patches == "span"


def test_every_required_field_is_reported_by_path(tmp_path):
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write(tmp_path, "name: mark\n"))
    message = str(excinfo.value)
    assert "source.repo" in message and "source.pin" in message and "draft.name" in message


def test_unknown_keys_and_bad_choices_are_refused(tmp_path):
    with pytest.raises(ConfigError, match="sessions.effort"):
        load_config(_write(tmp_path, MINIMAL + "sessions:\n  budget_usd: 10\n  effort: extreme\n"))
    with pytest.raises(ConfigError, match="source.hots"):
        load_config(_write(tmp_path, MINIMAL.replace("  pin:", "  hots: gitlab\n  pin:")))
    with pytest.raises(ConfigError, match="window"):
        load_config(_write(tmp_path, MINIMAL + "window: [5, 2]\n"))
    with pytest.raises(ConfigError, match="draft.name"):
        load_config(_write(tmp_path, MINIMAL.replace("draft-elniak", "elniak")))


def test_sessions_block_requires_a_budget(tmp_path):
    with pytest.raises(ConfigError, match="sessions.budget_usd"):
        load_config(_write(tmp_path, MINIMAL + "sessions:\n  model: claude-opus-5\n"))
    config = load_config(_write(tmp_path, MINIMAL + "sessions:\n  budget_usd: 200\n"))
    assert config.sessions is not None
    assert config.sessions.attempts_per_cluster == 2 and config.sessions.timeout_s == 7200


def test_example_round_trips_and_documents_every_field(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_RFC_EXPERIMENTS_ROOT", str(tmp_path / "root"))
    text = example()
    config = load_config(_write(tmp_path, text))
    assert config.name == "example"
    for field in FIELDS:
        assert field.doc, field.path
        assert field.path.split(".")[-1] in text, field.path
    reference = reference_markdown()
    for field in FIELDS:
        assert f"`{field.path}`" in reference


def test_dump_is_byte_stable_and_reloads(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_RFC_EXPERIMENTS_ROOT", str(tmp_path / "root"))
    config = load_config(_write(tmp_path, MINIMAL + "window: [1, 69]\n"))
    dumped = dump_config(config)
    again = load_config(_write(tmp_path, dumped))
    assert again == config and dump_config(again) == dumped
    assert yaml.safe_load(dumped)["window"] == [1, 69]


def test_drift_refuses_identity_fields_and_notes_the_rest(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_RFC_EXPERIMENTS_ROOT", str(tmp_path / "root"))
    sealed = load_config(_write(tmp_path, MINIMAL + "window: [1, 69]\nsessions:\n  budget_usd: 200\n"))
    given = load_config(_write(tmp_path, MINIMAL + "window: [1, 70]\nsessions:\n  budget_usd: 250\n"))
    refused, noted = drift(sealed, given)
    assert refused == ["window: [1, 69] -> [1, 70]"]
    assert noted == ["sessions.budget_usd: 200.0 -> 250.0"]
    assert drift(sealed, sealed) == ([], [])
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli/test_config.py -v`
Expected: FAIL at import (`No module named 'ai_rfc.config'`).

- [ ] **Step 3: Write `ai_rfc/config.py`**

```python
"""``recon.yaml``: one declarative field table that validates, exemplifies and documents.

The table is the contract. The loader walks it — so every key the file may
hold is named exactly once, an unknown key is an error rather than something
dropped on the floor, and the starter file and the reference page are rendered
from the same rows the loader checks.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

DEFAULT_ROOT = "~/ai-rfc-experiments"
IDENTITY_FIELDS = ("source.pin", "window", "draft.name")
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_KINDS = (
    "str", "path", "int", "float", "bool", "sha_or_ref", "url_or_path",
    "window", "str_list", "mapping",
)


class ConfigError(ValueError):
    """Raised when ``recon.yaml`` cannot be interpreted as written."""


@dataclass(frozen=True)
class Field:
    """One key of ``recon.yaml``."""

    path: str
    kind: str
    doc: str
    required: bool = False
    default: Any = None
    choices: tuple[str, ...] | None = None
    example: Any = None


FIELDS: tuple[Field, ...] = (
    Field("name", "str", "Short identifier: lowercase, digits, hyphens. Names the workspace.", required=True, example="example"),
    Field("workspace", "path", "Workspace directory; default <experiments root>/reconstructions/<name>.", example="~/ai-rfc-experiments/reconstructions/example"),
    Field("source.repo", "url_or_path", "Repository URL (GitHub or GitLab) or a local clone to copy.", required=True, example="https://github.com/example/project"),
    Field("source.host", "str", "Forge kind; inferred from the URL when omitted. `none` skips the forge snapshot.", choices=("github", "gitlab", "none"), example="github"),
    Field("source.pin", "sha_or_ref", "Commit (sha) or ref the reconstruction is pinned to; init records the resolved sha.", required=True, example="main"),
    Field("source.token_env", "str", "Environment variable holding a forge token; default GITHUB_TOKEN or GITLAB_TOKEN by host. Anonymous fetches work with lower fidelity.", example="GITHUB_TOKEN"),
    Field("window", "window", "Inclusive [low, high] cluster ordinals to reconstruct; default every cluster.", example=[1, 10]),
    Field("draft.name", "str", "Internet-Draft file name without .md; must start with `draft-`.", required=True, example="draft-yourname-example-reconstructed"),
    Field("draft.title", "str", "Document title; default `<name>: A Reconstructed Specification`.", example="Example: A Reconstructed Specification"),
    Field("draft.abbrev", "str", "Running-header abbreviation; default `<name> Reconstructed`.", example="Example Reconstructed"),
    Field("draft.rfc_id", "str", "Manifest `rfc:` identifier; default `<NAME>-RECON`.", example="EXAMPLE-RECON"),
    Field("draft.author", "mapping", "Author block: name, org, email. Default: the harness identity.", example={"name": "Your Name", "org": "Your Org", "email": "you@example.org"}),
    Field("references", "str_list", "RFC and Internet-Draft ids the draft may cite; sealed from the toolchain cache at init.", default=(), example=["RFC9000", "RFC9114"]),
    Field("sessions.model", "str", "Model id every session launches against.", default="claude-opus-5", example="claude-opus-5"),
    Field("sessions.effort", "str", "Reasoning effort per session.", default="high", choices=("low", "medium", "high", "xhigh"), example="high"),
    Field("sessions.budget_usd", "float", "Lifetime USD cap for the whole reconstruction; required when sessions are configured.", example=200.0),
    Field("sessions.timeout_s", "int", "Seconds before one session's process group is killed.", default=7200, example=7200),
    Field("sessions.attempts_per_cluster", "int", "Sessions a cluster may consume before the sweep halts.", default=2, example=2),
    Field("sessions.consolidate_every", "int", "Run a consolidation round after this many clusters, and at the end.", default=10, example=10),
    Field("sessions.profile", "path", "Isolated Claude Code profile (CLAUDE_CONFIG_DIR); default <experiments root>/profile.", example="~/ai-rfc-experiments/profile"),
    Field("sessions.claude", "str", "Claude Code binary; resolved to an absolute path at init.", default="claude", example="claude"),
    Field("toolchain", "path", "toolchain.json from `ai-rfc toolchain provision`; default <experiments root>/tools/toolchain.json.", example="~/ai-rfc-experiments/tools/toolchain.json"),
    Field("stages.history.cap", "int", "Per-commit file-row cap for the corpus; default the history stage's own.", example=1000),
    Field("stages.timeline.forge", "bool", "Enrich the timeline with the forge snapshot.", default=True, example=True),
    Field("stages.views.patches", "str", "Which patches each cluster view carries.", default="span", choices=("span", "members"), example="span"),
    Field("stages.lint.must_fraction_ceiling", "float", "MUST fraction above which the lint reports a finding.", default=0.8, example=0.8),
    Field("stages.build.targets", "str_list", "Make targets `draft build` runs.", default=("txt", "html", "lint", "idnits"), example=["txt", "html", "lint", "idnits"]),
    Field("experiment.arms", "str_list", "Instrument only: arms a campaign runs.", example=["A", "B"]),
    Field("experiment.repeats", "int", "Instrument only: runs per arm.", default=2, example=2),
    Field("experiment.seed", "int", "Instrument only: seed of the frozen run order.", default=20260826, example=20260826),
)
_BY_PATH = {f.path: f for f in FIELDS}


def experiments_root() -> Path:
    """``AI_RFC_EXPERIMENTS_ROOT`` or ``~/ai-rfc-experiments``, expanded."""
    return Path(os.environ.get("AI_RFC_EXPERIMENTS_ROOT", DEFAULT_ROOT)).expanduser()


@dataclass(frozen=True)
class SourceConfig:
    repo: str
    host: str
    pin: str
    token_env: str


@dataclass(frozen=True)
class DraftConfig:
    name: str
    title: str
    abbrev: str
    rfc_id: str
    author: dict[str, str]


@dataclass(frozen=True)
class SessionsConfig:
    model: str
    effort: str
    budget_usd: float
    timeout_s: int
    attempts_per_cluster: int
    consolidate_every: int
    profile: Path | None
    claude: str


@dataclass(frozen=True)
class StagesConfig:
    history_cap: int | None
    timeline_forge: bool
    views_patches: str
    lint_must_fraction_ceiling: float
    build_targets: tuple[str, ...]


@dataclass(frozen=True)
class ExperimentConfig:
    arms: tuple[str, ...]
    repeats: int
    seed: int


@dataclass(frozen=True)
class ReconConfig:
    """A validated ``recon.yaml``."""

    name: str
    workspace: Path
    source: SourceConfig
    window: tuple[int, int] | None
    draft: DraftConfig
    references: tuple[str, ...]
    sessions: SessionsConfig | None
    toolchain: Path | None
    stages: StagesConfig
    experiment: ExperimentConfig | None
    raw: dict[str, Any] = field(default=None, compare=False, repr=False)  # type: ignore[assignment]


def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if path in _BY_PATH and _BY_PATH[path].kind == "mapping":
                flat[path] = value
            elif isinstance(value, dict):
                flat.update(_flatten(value, path))
            else:
                flat[path] = value
    return flat


def _coerce(field_: Field, value: Any) -> Any:
    kind = field_.kind
    path = field_.path
    if kind == "str":
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"{path}: expected a non-empty string, got {value!r}")
        if field_.choices and value not in field_.choices:
            raise ConfigError(f"{path}: {value!r} is not one of {', '.join(field_.choices)}")
        return value
    if kind == "path":
        if not isinstance(value, str) or not value:
            raise ConfigError(f"{path}: expected a path, got {value!r}")
        return Path(value).expanduser()
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ConfigError(f"{path}: expected a non-negative integer, got {value!r}")
        return value
    if kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ConfigError(f"{path}: expected a non-negative number, got {value!r}")
        return float(value)
    if kind == "bool":
        if not isinstance(value, bool):
            raise ConfigError(f"{path}: expected true or false, got {value!r}")
        return value
    if kind == "sha_or_ref":
        if not isinstance(value, str) or not value.strip() or " " in value:
            raise ConfigError(f"{path}: expected a commit sha or ref, got {value!r}")
        return value
    if kind == "url_or_path":
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"{path}: expected a URL or path, got {value!r}")
        return value
    if kind == "window":
        if (
            not isinstance(value, list)
            or len(value) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in value)
            or value[0] > value[1]
        ):
            raise ConfigError(f"{path}: expected [low, high] with 1 <= low <= high, got {value!r}")
        return (value[0], value[1])
    if kind == "str_list":
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            raise ConfigError(f"{path}: expected a list of strings, got {value!r}")
        return tuple(value)
    if kind == "mapping":
        if not isinstance(value, dict) or not all(isinstance(v, str) for v in value.values()):
            raise ConfigError(f"{path}: expected a mapping of strings, got {value!r}")
        return dict(value)
    raise ConfigError(f"{path}: unknown field kind {kind!r}")  # pragma: no cover


def _infer_host(repo: str) -> str:
    netloc = urlparse(repo).netloc.lower()
    if "github" in netloc:
        return "github"
    if "gitlab" in netloc:
        return "gitlab"
    return "none"


def load_config(path: Path) -> ReconConfig:
    """Read and validate ``recon.yaml``.

    Args:
        path: The file to read.

    Returns:
        The validated configuration, defaults applied.

    Raises:
        ConfigError: On an unreadable file, an unknown key, a missing required
            field, a bad value or a bad choice — every problem names its path.
    """
    try:
        document = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise ConfigError(f"{path}: {error}") from None
    if not isinstance(document, dict):
        raise ConfigError(f"{path}: expected a mapping at the top level")
    flat = _flatten(document)
    problems: list[str] = []
    for key in sorted(flat):
        if key not in _BY_PATH:
            problems.append(f"{key}: unknown key")
    values: dict[str, Any] = {}
    for field_ in FIELDS:
        if field_.path in flat and flat[field_.path] is not None:
            try:
                values[field_.path] = _coerce(field_, flat[field_.path])
            except ConfigError as error:
                problems.append(str(error))
        elif field_.required:
            problems.append(f"{field_.path}: required")
        else:
            values[field_.path] = field_.default
    has_sessions = any(key.startswith("sessions.") for key in flat)
    if has_sessions and values.get("sessions.budget_usd") is None:
        problems.append("sessions.budget_usd: required when sessions are configured")
    if "draft.name" in values and values["draft.name"] and not values["draft.name"].startswith("draft-"):
        problems.append("draft.name: must start with `draft-`")
    if "name" in values and values["name"] and not _NAME.match(values["name"]):
        problems.append("name: must match [a-z0-9][a-z0-9-]*")
    if problems:
        raise ConfigError(f"{path}: " + "; ".join(problems))

    name = values["name"]
    root = experiments_root()
    workspace = values["workspace"] or root / "reconstructions" / name
    source = SourceConfig(
        repo=values["source.repo"],
        host=values["source.host"] or _infer_host(values["source.repo"]),
        pin=values["source.pin"],
        token_env=values["source.token_env"]
        or {"github": "GITHUB_TOKEN", "gitlab": "GITLAB_TOKEN"}.get(
            values["source.host"] or _infer_host(values["source.repo"]), ""
        ),
    )
    draft = DraftConfig(
        name=values["draft.name"],
        title=values["draft.title"] or f"{name}: A Reconstructed Specification",
        abbrev=values["draft.abbrev"] or f"{name} Reconstructed",
        rfc_id=values["draft.rfc_id"] or f"{name.upper()}-RECON",
        author=values["draft.author"]
        or {"name": "ai-rfc harness", "org": "none", "email": "ai-rfc-harness@localhost"},
    )
    sessions = None
    if has_sessions:
        sessions = SessionsConfig(
            model=values["sessions.model"],
            effort=values["sessions.effort"],
            budget_usd=values["sessions.budget_usd"],
            timeout_s=values["sessions.timeout_s"],
            attempts_per_cluster=values["sessions.attempts_per_cluster"],
            consolidate_every=values["sessions.consolidate_every"],
            profile=values["sessions.profile"],
            claude=values["sessions.claude"],
        )
    stages = StagesConfig(
        history_cap=values["stages.history.cap"],
        timeline_forge=values["stages.timeline.forge"],
        views_patches=values["stages.views.patches"],
        lint_must_fraction_ceiling=values["stages.lint.must_fraction_ceiling"],
        build_targets=tuple(values["stages.build.targets"]),
    )
    experiment = None
    if any(key.startswith("experiment.") for key in flat):
        experiment = ExperimentConfig(
            arms=tuple(values["experiment.arms"] or ()),
            repeats=values["experiment.repeats"],
            seed=values["experiment.seed"],
        )
    toolchain = values["toolchain"] or root / "tools" / "toolchain.json"
    return ReconConfig(
        name=name,
        workspace=workspace,
        source=source,
        window=values["window"],
        draft=draft,
        references=tuple(values["references"]),
        sessions=sessions,
        toolchain=toolchain,
        stages=stages,
        experiment=experiment,
        raw=document,
    )


def _nest(flat: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for path, value in flat.items():
        node = nested
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return nested


def dump_config(config: ReconConfig) -> str:
    """Serialise the validated values, byte-stably, in field-table order."""
    flat: dict[str, Any] = {
        "name": config.name,
        "workspace": str(config.workspace),
        "source.repo": config.source.repo,
        "source.host": config.source.host,
        "source.pin": config.source.pin,
        "source.token_env": config.source.token_env,
        "draft.name": config.draft.name,
        "draft.title": config.draft.title,
        "draft.abbrev": config.draft.abbrev,
        "draft.rfc_id": config.draft.rfc_id,
        "draft.author": dict(config.draft.author),
        "references": list(config.references),
        "toolchain": str(config.toolchain) if config.toolchain else None,
        "stages.history.cap": config.stages.history_cap,
        "stages.timeline.forge": config.stages.timeline_forge,
        "stages.views.patches": config.stages.views_patches,
        "stages.lint.must_fraction_ceiling": config.stages.lint_must_fraction_ceiling,
        "stages.build.targets": list(config.stages.build_targets),
    }
    if config.window is not None:
        flat["window"] = list(config.window)
    if config.sessions is not None:
        s = config.sessions
        flat.update(
            {
                "sessions.model": s.model,
                "sessions.effort": s.effort,
                "sessions.budget_usd": s.budget_usd,
                "sessions.timeout_s": s.timeout_s,
                "sessions.attempts_per_cluster": s.attempts_per_cluster,
                "sessions.consolidate_every": s.consolidate_every,
                "sessions.profile": str(s.profile) if s.profile else None,
                "sessions.claude": s.claude,
            }
        )
    if config.experiment is not None:
        flat.update(
            {
                "experiment.arms": list(config.experiment.arms),
                "experiment.repeats": config.experiment.repeats,
                "experiment.seed": config.experiment.seed,
            }
        )
    ordered = {f.path: flat[f.path] for f in FIELDS if f.path in flat and flat[f.path] is not None}
    return yaml.safe_dump(_nest(ordered), sort_keys=False, default_flow_style=None, allow_unicode=True)


def example() -> str:
    """A starter ``recon.yaml``: every field with its example value and its doc as a comment."""
    lines = ["# recon.yaml — one reconstruction, declared. Generated by `ai-rfc config example`."]
    document = _nest({f.path: f.example for f in FIELDS if f.example is not None})
    document["name"] = "example"
    body = yaml.safe_dump(document, sort_keys=False, default_flow_style=None, allow_unicode=True)
    docs = {f.path.split(".")[-1]: f.doc for f in FIELDS}
    for line in body.splitlines():
        key = line.strip().split(":")[0]
        if key in docs and not line.startswith("#"):
            lines.append(f"# {docs[key]}")
        lines.append(line)
    return "\n".join(lines) + "\n"


def reference_markdown() -> str:
    """The field table as a Markdown reference page."""
    rows = ["| Field | Kind | Required | Default | Description |", "|---|---|---|---|---|"]
    for f in FIELDS:
        default = "" if f.default is None else f"`{f.default!r}`"
        choices = f" One of: {', '.join(f.choices)}." if f.choices else ""
        rows.append(f"| `{f.path}` | {f.kind} | {'yes' if f.required else 'no'} | {default} | {f.doc}{choices} |")
    return "\n".join(rows) + "\n"


def drift(sealed: ReconConfig, given: ReconConfig) -> tuple[list[str], list[str]]:
    """Compare a sealed config with the file as given now.

    Args:
        sealed: What ``init`` sealed into the workspace.
        given: What the operator passed this time.

    Returns:
        ``(refused, noted)``: identity fields that changed and must be refused
        (D57), and every other change, as ``path: old -> new`` lines.
    """
    before = _flatten(yaml.safe_load(dump_config(sealed)))
    after = _flatten(yaml.safe_load(dump_config(given)))
    refused: list[str] = []
    noted: list[str] = []
    for path in sorted(set(before) | set(after)):
        if before.get(path) != after.get(path):
            line = f"{path}: {before.get(path)!r} -> {after.get(path)!r}".replace("'", "")
            (refused if path in IDENTITY_FIELDS else noted).append(line)
    return refused, noted
```

(`drift`'s `replace("'", "")` renders `[1, 69] -> [1, 70]` and `200.0 -> 250.0` as the tests expect; keep the expected strings and this rendering in step.)

- [ ] **Step 4: Run the tests**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli/test_config.py -v`
Expected: all PASS. If `test_example_round_trips_and_documents_every_field` fails on `example.arms`, the example document carries an `experiment:` block whose `arms` list is valid — check `_coerce`'s `str_list`.

- [ ] **Step 5: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/config.py tests/cli && $PY -m flake8 --max-line-length=88 ai_rfc/config.py tests/cli && $PY -m mypy --follow-imports=silent ai_rfc/config.py
git status --short
git add ai_rfc/config.py tests/cli/__init__.py tests/cli/test_config.py
git commit -m "feat: declare a reconstruction in recon.yaml through one field table (baseline N)"
```

---

### Task 2: The argparse root — every sub-CLI exposes `configure(parser)` and `run(args)`, and `ai-rfc` mounts them all

**Files:**
- Modify: `ai_rfc/cli.py` (replace SP1's dispatcher), `ai_rfc/entrypoints.py` (`EntryPoint` rows and sections), `ai_rfc/{check,history,forge,timeline,views,draft,coverage,pipeline}/cli.py` (the `configure`/`run` split), `ai_rfc/pipeline/cli.py` (`--from`/`--until` choices in pipeline order)
- Create: `ai_rfc/lifecycle/__init__.py`, and the `config` verb package per D1 — `ai_rfc/lifecycle/config/__init__.py`, `ai_rfc/lifecycle/config/__main__.py`, `ai_rfc/lifecycle/config/cli.py` (`ai-rfc config example|reference`)
- Test: `tests/cli/test_root.py` (new), `tests/substrate/test_cli_conventions.py` (extend), `tests/substrate/test_root_cli.py` (update — it holds SP1's three dispatcher tests, see Step 6)

**Interfaces:**
- Consumes: `ai_rfc.entrypoints.ENTRY_POINTS`, `ai_rfc.config.example/reference_markdown` (Task 1).
- Produces: in every sub-CLI module `configure(parser: argparse.ArgumentParser) -> None` and `run(args: argparse.Namespace) -> int`, with `main(argv: list[str] | None = None) -> int` kept as `run(build_standalone_parser().parse_args(argv))`; `ai_rfc.cli.build_parser() -> argparse.ArgumentParser` and `main(argv) -> int`; `EntryPoint` gains nothing (the module contract is by name); sections `LIFECYCLE = "Lifecycle"` and `AGENT = "Agent verbs (used inside sessions)"` in `entrypoints.py`; the `ai-rfc config example` and `ai-rfc config reference` verbs. Tasks 4–6 register their verbs as `EntryPoint` rows pointing at `ai_rfc.lifecycle.<module>` and implement `configure`/`run` the same way.

**Why this shape.** One parser tree gives one `--help`, one `--version`, one exit-code contract, and lets `panther ai-rfc` forward argv untouched (R6). The `configure`/`run` split is mechanical: the body of every `_parser()` moves into `configure`, the body of every `main()` after `parse_args` moves into `run`. `main` stays so `python -m ai_rfc.<sub>` — the server core's and the raw arm's door until CLI-3 — is byte-for-byte unchanged in behaviour.

- [ ] **Step 1: Write the failing root tests**

Create `tests/cli/test_root.py`:

```python
"""The one door: every verb mounts under `ai-rfc`, forwards untouched, and shares one help."""

import importlib

import pytest

from ai_rfc import __version__, cli
from ai_rfc.entrypoints import ENTRY_POINTS
from ai_rfc.pipeline.stages import STAGES


def test_help_lists_every_registered_verb_once_under_its_section(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for entry in ENTRY_POINTS:
        assert out.count(f"  {entry.verb} ") == 1 or out.count(f"  {entry.verb}\n") == 1, entry.verb
        assert entry.section in out


def test_every_registered_module_exposes_the_configure_run_contract():
    for entry in ENTRY_POINTS:
        module = importlib.import_module(entry.module)
        assert callable(module.configure) and callable(module.run), entry.module
        assert callable(module.main), entry.module


def test_version_names_the_one_program(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out == f"ai-rfc {__version__}\n"


def test_an_unknown_verb_exits_two(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["frobnicate"])
    assert excinfo.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_a_verb_forwards_to_its_module_run(tmp_path, capsys):
    """`ai-rfc pipeline status WS` and `python -m ai_rfc.pipeline status WS` agree."""
    from ai_rfc.pipeline import cli as pipeline_cli

    empty = tmp_path / "ws"
    empty.mkdir()
    via_root = cli.main(["pipeline", "status", str(empty)])
    root_out = capsys.readouterr().out
    via_module = pipeline_cli.main(["status", str(empty)])
    assert via_root == via_module and capsys.readouterr().out == root_out


def test_pipeline_from_choices_follow_pipeline_order(capsys):
    with pytest.raises(SystemExit):
        cli.main(["pipeline", "run", "--help"])
    out = capsys.readouterr().out
    names = [stage.name for stage in STAGES]
    positions = [out.find(name) for name in names]
    assert positions == sorted(positions) and -1 not in positions


def test_config_example_prints_a_loadable_starter(tmp_path, capsys):
    from ai_rfc.config import load_config

    assert cli.main(["config", "example"]) == 0
    text = capsys.readouterr().out
    (tmp_path / "recon.yaml").write_text(text)
    assert load_config(tmp_path / "recon.yaml").name == "example"
    assert cli.main(["config", "reference"]) == 0
    assert "| `source.pin` |" in capsys.readouterr().out
```

Append to `tests/substrate/test_cli_conventions.py` (it already iterates `ENTRY_POINTS` for `prog` values — keep those tests; add):

```python
def test_main_is_the_standalone_door_over_configure_and_run(capsys):
    """`python -m ai_rfc.<sub> --help` still works for every registered module."""
    for entry in ENTRY_POINTS:
        module = importlib.import_module(entry.module)
        with pytest.raises(SystemExit) as excinfo:
            module.main(["--help"])
        assert excinfo.value.code == 0, entry.verb
        assert f"usage: {entry.prog}" in capsys.readouterr().out, entry.verb
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli/test_root.py tests/substrate/test_cli_conventions.py -v`
Expected: the contract test FAILS (`module has no attribute 'configure'`), `--help` FAILS (SP1's dispatcher writes its own usage and returns 0 without `SystemExit`), `config` is an unknown verb.

- [ ] **Step 3: Split one sub-CLI as the exemplar — `ai_rfc/draft/cli.py`**

Today: `_parser()` builds `argparse.ArgumentParser(prog="ai-rfc draft", …)`, adds `--version` and the `checkpoint`/`gate`/`completeness`/`build`/`lint`/`render` subparsers; `main(argv)` parses then dispatches on `args.verb`. Rewrite the module's frame to:

```python
def configure(parser: argparse.ArgumentParser) -> None:
    """Add this command's arguments to ``parser`` (the root's subparser or a standalone one)."""
    parser.description = (
        "Freeze manifest checkpoints against timeline clusters, gate a prose "
        "draft's revision map against them, and measure how much of the timeline "
        "the reconstruction has actually specified."
    )
    verbs = parser.add_subparsers(dest="verb", required=True)
    # …every `verbs.add_parser(...)` block exactly as it is today, unchanged…


def build_standalone_parser() -> argparse.ArgumentParser:
    """The parser ``python -m ai_rfc.draft`` uses; identical arguments to the root's mount."""
    parser = argparse.ArgumentParser(prog="ai-rfc draft")
    parser.add_argument("--version", action="version", version=f"ai-rfc draft {__version__}")
    configure(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Perform the parsed verb; the body of the old ``main`` after ``parse_args``."""
    if args.verb == "checkpoint":
        …  # unchanged
    if args.verb == "completeness":
        …  # unchanged
    if args.verb == "build":
        …  # unchanged
    if args.verb == "lint":
        …  # unchanged
    if args.verb == "render":
        …  # unchanged
    if args.verb == "gate":
        …  # the former bottom fallthrough, now an explicit branch
    raise AssertionError(f"unhandled verb {args.verb!r}")  # argparse guarantees a known verb


def main(argv: list[str] | None = None) -> int:
    """Run the requested verb from the command line (``python -m ai_rfc.draft``)."""
    return run(build_standalone_parser().parse_args(argv))
```

Every `…  # unchanged` is the existing code moved verbatim; the only edits are the function boundaries, the `prog`/`--version` moving into `build_standalone_parser`, and `gate` becoming an explicit branch (SP7b's contract item C5 records why: an unguarded fallthrough runs `gate` for any verb that forgot its branch). Keep every docstring's Args/Returns; the `_report` helper is untouched.

- [ ] **Step 4: Apply the same split to the other seven modules**

For each of `ai_rfc/check/cli.py` (no subparsers: `configure` adds `manifest`, `--out`, `--repo`, `--strict`; `run` is the old body), `ai_rfc/history/cli.py`, `ai_rfc/forge/cli.py` (`fetch`/`adopt`), `ai_rfc/timeline/cli.py`, `ai_rfc/views/cli.py`, `ai_rfc/coverage/cli.py`, `ai_rfc/pipeline/cli.py` (`status`/`substrate`/`run`): move the `_parser()` body into `configure(parser)` (dropping the `ArgumentParser(...)` construction and the `--version` argument, which `build_standalone_parser` adds), move the `main` body after `parse_args` into `run(args)`, add `build_standalone_parser()` with the module's existing `prog` and `version` strings, and make `main` the two-liner above. Delete `_parser`. In `ai_rfc/pipeline/cli.py`, replace `choices=sorted(BY_NAME)` on `--from` and `--until` with `choices=[stage.name for stage in STAGES]` (pipeline order; friction 10).

Verify mechanically that no behaviour moved: `grep -n "def _parser\|parse_args" ai_rfc/*/cli.py` must show `parse_args` only inside each `main`.

- [ ] **Step 5: The root**

Replace `ai_rfc/cli.py`:

```python
"""The one door onto the tool: ``ai-rfc <verb> [args]``.

One argparse tree mounts every registered command through its ``configure``
function, so ``ai-rfc <verb>`` and ``python -m ai_rfc.<sub>`` parse the same
arguments and return the same exit codes, and ``panther ai-rfc`` forwards argv
here untouched.
"""

from __future__ import annotations

import argparse
from importlib import import_module

from . import __version__
from .entrypoints import ENTRY_POINTS, SECTIONS

PROG = "ai-rfc"


def _epilog() -> str:
    width = max(len(entry.verb) for entry in ENTRY_POINTS)
    lines: list[str] = []
    for section in SECTIONS:
        rows = [entry for entry in ENTRY_POINTS if entry.section == section]
        if not rows:
            continue
        lines.append(f"{section}:")
        lines.extend(f"  {entry.verb:<{width}}  {entry.summary}" for entry in rows)
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the root parser with every registered verb mounted."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Reconstruct a specification from a repository's history.",
        epilog=_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    verbs = parser.add_subparsers(dest="verb", required=True, metavar="<verb>")
    for entry in ENTRY_POINTS:
        module = import_module(entry.module)
        sub = verbs.add_parser(entry.verb, help=entry.summary, prog=entry.prog)
        module.configure(sub)
        sub.set_defaults(_run=module.run)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse and run one verb.

    Args:
        argv: Argument vector without the program name; ``None`` reads ``sys.argv[1:]``.

    Returns:
        The verb's exit code (0/1/3 per the package table; argparse exits 2 itself).
    """
    args = build_parser().parse_args(argv)
    return args._run(args)
```

In `ai_rfc/entrypoints.py`: add `LIFECYCLE = "Lifecycle: one config, one workspace"` and `AGENT = "Agent verbs (used inside sessions)"`, define `SECTIONS = (LIFECYCLE, DRIVEN, BY_HAND, PERFORMED, AGENT)` (it does not exist today — this creates it), and add the first lifecycle row at the top of `ENTRY_POINTS`:

```python
    EntryPoint(
        "config",
        "ai-rfc config",
        f"{PACKAGE}.lifecycle.config.cli",
        "Print a starter recon.yaml (example) or the field reference (reference)",
        LIFECYCLE,
    ),
```

Every later lifecycle row (Tasks 4, 5, 6) is inserted **immediately after the previous lifecycle row**, never appended elsewhere: `tests/substrate/test_cli_conventions.py:163-175` asserts entries sharing a section are contiguous, because declaration order is help order.

Create `ai_rfc/lifecycle/__init__.py` (docstring only: "Operator lifecycle verbs: one config, one workspace, one command that does what is next." — plus `class LifecycleError(RuntimeError)`, which Task 4 uses), `ai_rfc/lifecycle/config/__init__.py` (docstring only), `ai_rfc/lifecycle/config/__main__.py` (copy the existing pattern verbatim from `ai_rfc/draft/__main__.py`, changing only the docstring to ``` ``python -m ai_rfc.lifecycle.config``. ```):

```python
"""``python -m ai_rfc.lifecycle.config``."""

import sys

from . import cli

if __name__ == "__main__":
    sys.exit(cli.main())
```

and `ai_rfc/lifecycle/config/cli.py` (note the three-dot imports — the module now sits one level deeper than the plan's original flat layout, per D1):

```python
"""``ai-rfc config example|reference``."""

from __future__ import annotations

import argparse

from ... import __version__
from ...config import example, reference_markdown


def configure(parser: argparse.ArgumentParser) -> None:
    """Add the ``example`` and ``reference`` verbs."""
    verbs = parser.add_subparsers(dest="verb", required=True)
    verbs.add_parser("example", help="A starter recon.yaml with every field documented.")
    verbs.add_parser("reference", help="The field table as Markdown.")


def build_standalone_parser() -> argparse.ArgumentParser:
    """The parser ``python -m ai_rfc.lifecycle.config`` uses."""
    parser = argparse.ArgumentParser(prog="ai-rfc config")
    parser.add_argument("--version", action="version", version=f"ai-rfc config {__version__}")
    configure(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Print the requested text."""
    print(example() if args.verb == "example" else reference_markdown(), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Command-line entry."""
    return run(build_standalone_parser().parse_args(argv))
```

- [ ] **Step 6: Run the suites**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli tests/substrate -n auto`
Expected: all PASS. SP1's three dispatcher tests live in **`tests/substrate/test_root_cli.py`** — `test_help_lists_every_verb_in_registration_order:13`, `test_an_unknown_verb_exits_two:33`, `test_a_verb_forwards_its_arguments_untouched:44` — not in `tests/cli/` and not in `test_cli_conventions.py`. They assert the old dispatcher's hand-written usage and must be updated to the argparse behaviour (help via `SystemExit(0)`, unknown verb via `SystemExit(2)` carrying "invalid choice"); the forwarding property is now `test_a_verb_forwards_to_its_module_run` in `tests/cli/test_root.py`. All three are data-driven off `ENTRY_POINTS`, so they will automatically demand the new lifecycle verbs behave — which is the point.

Two conventions tests in `tests/substrate/test_cli_conventions.py` also cover every new row and must pass without being weakened: `test_every_entry_point_reports_its_version` calls `entry.load().main(["--version"])` and requires `SystemExit(0)` printing both `entry.prog` and `__version__` (satisfied by each verb's `build_standalone_parser`), and `test_a_malformed_invocation_exits_two_everywhere` calls `entry.load().main(["--no-such-flag"])` and requires `SystemExit(2)`. If either fails, the fix is the new module, never the test.

- [ ] **Step 7: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc tests/cli tests/substrate/test_cli_conventions.py && $PY -m flake8 --max-line-length=88 ai_rfc tests/cli && $PY -m mypy --follow-imports=silent ai_rfc/cli.py ai_rfc/lifecycle ai_rfc/draft/cli.py ai_rfc/pipeline/cli.py
git status --short
git add ai_rfc/cli.py ai_rfc/entrypoints.py ai_rfc/lifecycle/__init__.py ai_rfc/lifecycle/config/__init__.py ai_rfc/lifecycle/config/__main__.py ai_rfc/lifecycle/config/cli.py ai_rfc/check/cli.py ai_rfc/history/cli.py ai_rfc/forge/cli.py ai_rfc/timeline/cli.py ai_rfc/views/cli.py ai_rfc/draft/cli.py ai_rfc/coverage/cli.py ai_rfc/pipeline/cli.py tests/cli/__init__.py tests/cli/test_root.py tests/substrate/test_cli_conventions.py tests/substrate/test_root_cli.py
git commit -m "feat: one argparse root mounts every command through configure and run"
```

---

### Task 3: The ledger — one reader of per-cluster progress

**Files:**
- Create: `ai_rfc/ledger.py`
- Modify: `ai_rfc/pipeline/state.py` (`_checkpoint`), `ai_rfc/draft/completeness.py` (the computation that fills the `unprocessed_clusters` **field** of `CompletenessReport` — the field is at `completeness.py:223` and is populated at `:269`; it is not a function, so re-anchor on `checkpoint_records:60` and `build:231` as the Interfaces block below correctly names), `ai_rfc/server/core/queries.py` (`_processed_cluster_ids`, `cluster_next`, `status`), `ai_rfc/experiment/progress.py` (`window_progress`), `ai_rfc/experiment/metrics.py` (`cluster_artifacts`), `ai_rfc/experiment/per_cluster.py` (`partial_reason` callers)
- Test: `tests/ledger/__init__.py` (empty), `tests/ledger/test_ledger.py`

**Interfaces:**
- Consumes: `timeline/clusters.jsonl` rows (`id`, `ordinal`, `kind`), `checkpoints/<id>/checkpoint.json`, the pre-seed marker `checkpoints/<id>/harness.json` (`experiment.workspace.HARNESS_MARKER`), `revisions.yaml` (`revisions: {tag: {cluster_id, normative_change, kind?}}`), draft tags (`git -C draft tag -l`), `init.json`/`pristine.json` `window`.
- Produces: `ClusterState` (frozen: `id, ordinal, kind, in_window, pre_seeded, checkpoint, revision_tag, normative_change, tag_exists, done, partial_reason`); `window_of(workspace: Path) -> tuple[int, int] | None`; `clusters(workspace: Path, window: tuple[int, int] | None = None) -> tuple[ClusterState, ...]` (window defaults to `window_of`); `next_cluster(workspace, window=None) -> ClusterState | None` (lowest-ordinal in-window cluster not done); `counts(states) -> dict[str, int]` (`total, in_window, done, partial, outstanding, pre_seeded`); `LedgerError`. Tasks 5–6 and CLI-2's driver consume it; SP7c filters `kind: consolidation` entries here (the filter is written now).

**Why this shape.** Five places compute "which clusters are done" with three different answers (a bare checkpoint directory counts for the server; checkpoint+entry+tag for the harness; checkpoint records for completeness). One reader with the strict definition ends the drift D35 names, and gives the driver the row it plans from.

- [ ] **Step 1: Write the failing tests**

Create `tests/ledger/test_ledger.py`:

```python
"""One reader of per-cluster progress, agreed with by every surface that used to compute it."""

import json
import os
from pathlib import Path

import pytest
import yaml

from ai_rfc.ledger import LedgerError, clusters, counts, next_cluster, window_of
from ai_rfc.server.testing import build_workspace, git

DATE = "2026-01-01T00:00:09+00:00"


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    """The twin-builder workspace (two clusters) with an empty draft repository."""
    root = build_workspace(tmp_path / "ws")
    draft = root / "draft"
    if not (draft / ".git").exists():
        draft.mkdir(exist_ok=True)
        git(draft, "init", "-q", "-b", "main")
        git(draft, "config", "user.email", "t@t")
        git(draft, "config", "user.name", "t")
        (draft / "draft-test-spec.md").write_text("# T\n")
        git(draft, "add", "draft-test-spec.md")
        git(draft, "commit", "-q", "-m", "00", date=DATE)
    return root


def _ids(root: Path) -> list[str]:
    return [json.loads(l)["id"] for l in (root / "timeline" / "clusters.jsonl").read_text().splitlines() if l.strip()]


def _checkpoint(root: Path, cluster_id: str, *, pre_seeded: bool = False, bare: bool = False) -> None:
    directory = root / "checkpoints" / cluster_id
    directory.mkdir(parents=True)
    if bare:
        return
    (directory / "checkpoint.json").write_text(json.dumps({"cluster_id": cluster_id, "manifest_sha256": "0" * 64, "ordinal": 1}))
    if pre_seeded:
        (directory / "harness.json").write_text('{"pre_seeded": true}\n')


def _revision(root: Path, tag: str, cluster_id: str, *, kind: str | None = None, tag_it: bool = True) -> None:
    document = yaml.safe_load((root / "revisions.yaml").read_text()) or {"revisions": {}}
    body = {"cluster_id": cluster_id, "checkpoint_manifest_sha256": "0" * 64, "normative_change": True, "note": "n"}
    if kind:
        body["kind"] = kind
    document.setdefault("revisions", {})[tag] = body
    (root / "revisions.yaml").write_text(yaml.safe_dump(document, sort_keys=False))
    if tag_it:
        git(root / "draft", "tag", "-a", tag, "-m", tag)


def test_a_fresh_workspace_is_all_outstanding(ws):
    states = clusters(ws)
    assert [s.ordinal for s in states] == [1, 2]
    assert all(not s.done and s.partial_reason is None and s.in_window for s in states)
    assert counts(states) == {"total": 2, "in_window": 2, "done": 0, "partial": 0, "outstanding": 2, "pre_seeded": 0}
    assert next_cluster(ws).ordinal == 1


def test_done_needs_checkpoint_entry_and_tag(ws):
    first, second = _ids(ws)
    _checkpoint(ws, first)
    assert clusters(ws)[0].partial_reason == "checkpoint present, no revision entry"
    _revision(ws, "draft-test-spec-01", first, tag_it=False)
    assert clusters(ws)[0].partial_reason == "checkpoint present, revision entry recorded, tag missing"
    git(ws / "draft", "tag", "-a", "draft-test-spec-01", "-m", "01")
    state = clusters(ws)[0]
    assert state.done and state.revision_tag == "draft-test-spec-01" and state.tag_exists
    assert next_cluster(ws).id == second


def test_a_bare_directory_is_not_a_checkpoint(ws):
    first, _ = _ids(ws)
    _checkpoint(ws, first, bare=True)
    state = clusters(ws)[0]
    assert not state.checkpoint and not state.done and state.partial_reason is None


def test_pre_seeded_and_out_of_window_clusters_are_done_by_definition(ws):
    first, second = _ids(ws)
    _checkpoint(ws, first, pre_seeded=True)
    states = clusters(ws)
    assert states[0].done and states[0].pre_seeded
    states = clusters(ws, window=(2, 2))
    assert not states[0].in_window and states[0].done and states[1].in_window
    assert next_cluster(ws, window=(2, 2)).id == second
    assert counts(states)["in_window"] == 1


def test_window_is_read_from_init_json_then_pristine_json(ws):
    assert window_of(ws) is None
    (ws / "pristine.json").write_text(json.dumps({"window": [2, 2]}))
    assert window_of(ws) == (2, 2)
    (ws / "init.json").write_text(json.dumps({"window": [1, 1]}))
    assert window_of(ws) == (1, 1)
    assert next_cluster(ws).ordinal == 1 and clusters(ws)[1].in_window is False


def test_a_consolidation_entry_never_marks_a_cluster_done(ws):
    first, _ = _ids(ws)
    _checkpoint(ws, first)
    _revision(ws, "draft-test-spec-01", first, kind="consolidation")
    state = clusters(ws)[0]
    assert not state.done and state.revision_tag is None


def test_an_unreadable_timeline_is_an_error(tmp_path):
    with pytest.raises(LedgerError):
        clusters(tmp_path)


def test_the_five_old_readers_agree_with_the_ledger(ws, monkeypatch):
    """The surfaces this module replaces must report what it reports."""
    from ai_rfc.experiment.metrics import cluster_artifacts
    from ai_rfc.experiment.progress import window_progress
    from ai_rfc.pipeline.state import State, state
    from ai_rfc.pipeline.workspace import Workspace
    from ai_rfc.server.core import queries
    from ai_rfc.server.paths import resolve_context

    first, second = _ids(ws)
    _checkpoint(ws, first)
    _revision(ws, "draft-test-spec-01", first)
    (ws / "init.json").write_text(json.dumps({"window": [1, 2]}))
    monkeypatch.setenv("AI_RFC_WORKSPACE", str(ws))
    rows = clusters(ws)
    assert queries.cluster_next(resolve_context())["id"] == second == next_cluster(ws).id
    row, artifacts, position, done, total = window_progress(ws)
    assert (row["id"], position, done, total) == (second, 2, 1, 2)
    assert cluster_artifacts(ws, {"id": first, "ordinal": 1, "kind": "pr"})["artifacts"] is True
    by_name = {entry.stage.name: entry for entry in state(Workspace(ws))}
    assert by_name["checkpoint"].state is State.PARTIAL and "1 of 2" in by_name["checkpoint"].reason


@pytest.mark.skipif(
    not Path(os.path.expanduser("~/ai-rfc-experiments/baselines/mark-a1-2026-09-03")).is_dir(),
    reason="the sealed MARK A1 copy is not on this machine",
)
def test_the_finished_mark_run_reads_as_37_done_and_38_partial():
    root = Path(os.path.expanduser("~/ai-rfc-experiments/baselines/mark-a1-2026-09-03"))
    states = clusters(root)
    summary = counts(states)
    assert summary["done"] == 37 and summary["total"] == 69
    partial = [s for s in states if s.partial_reason]
    assert [s.ordinal for s in partial] == [38]
    assert next_cluster(root).ordinal == 38
```

(If `build_workspace` already creates a draft repository, the fixture's `if` skips the creation; read `ai_rfc/server/testing.py` to see which. The `_checkpoint` helper writes the minimal record the readers inspect; `checkpoint.json`'s real fields are richer, which no reader here needs.)

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/ledger -v`
Expected: FAIL at import (`No module named 'ai_rfc.ledger'`).

- [ ] **Step 3: Write `ai_rfc/ledger.py`**

```python
"""One reader of per-cluster progress, for every surface that reports it.

Five places used to compute "which clusters are done" and reached three
different answers: a bare checkpoint directory counted for the MCP status, a
checkpoint plus its revision entry plus its tag for the harness, and checkpoint
records for completeness. A cluster is done here only when the checkpoint
record, the ``kind: cluster`` revision entry and the annotated tag all exist;
what is on disk decides, never a counter in memory.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CHECKPOINT_FILE = "checkpoint.json"
PRESEED_MARKER = "harness.json"
CLUSTERS_FILE = "timeline/clusters.jsonl"
INIT_RECORD = "init.json"
PRISTINE_RECORD = "pristine.json"


class LedgerError(RuntimeError):
    """Raised when the workspace's progress cannot be read as written."""


@dataclass(frozen=True)
class ClusterState:
    """What the workspace holds for one cluster."""

    id: str
    ordinal: int
    kind: str | None
    in_window: bool
    pre_seeded: bool
    checkpoint: bool
    revision_tag: str | None
    normative_change: bool | None
    tag_exists: bool

    @property
    def done(self) -> bool:
        """Finished, by the strict definition, or not this run's work at all."""
        if not self.in_window or self.pre_seeded:
            return True
        return self.checkpoint and self.revision_tag is not None and self.tag_exists

    @property
    def partial_reason(self) -> str | None:
        """Name a half-finished cluster's state, or None when untouched or done."""
        if not self.in_window or self.pre_seeded or not self.checkpoint:
            return None
        if self.revision_tag is None:
            return "checkpoint present, no revision entry"
        if not self.tag_exists:
            return "checkpoint present, revision entry recorded, tag missing"
        return None


def _rows(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / CLUSTERS_FILE
    try:
        lines = path.read_text().splitlines()
    except OSError as error:
        raise LedgerError(f"{path}: {error}") from None
    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError as error:
            raise LedgerError(f"{path}: not JSON Lines: {error}") from None
    return sorted(rows, key=lambda row: row["ordinal"])


def _entries(workspace: Path) -> dict[str, tuple[str, bool | None]]:
    """cluster id → (tag, normative_change) of its first ``kind: cluster`` entry."""
    path = workspace / "revisions.yaml"
    if not path.exists():
        return {}
    try:
        document = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as error:
        raise LedgerError(f"{path}: {error}") from None
    found: dict[str, tuple[str, bool | None]] = {}
    for tag, body in (document.get("revisions") or {}).items():
        if not isinstance(body, dict) or "cluster_id" not in body:
            continue
        if body.get("kind", "cluster") != "cluster":
            continue
        cluster_id = str(body["cluster_id"])
        if cluster_id not in found:
            normative = body.get("normative_change")
            found[cluster_id] = (str(tag), None if normative is None else bool(normative))
    return found


def _tags(draft: Path) -> set[str]:
    if not (draft / ".git").exists():
        return set()
    result = subprocess.run(["git", "-C", str(draft), "tag", "-l"], capture_output=True, text=True)
    return {tag for tag in result.stdout.splitlines() if tag} if result.returncode == 0 else set()


def window_of(workspace: Path) -> tuple[int, int] | None:
    """The window ``init`` (production) or ``prepare`` (campaign) recorded, if any."""
    for name in (INIT_RECORD, PRISTINE_RECORD):
        path = workspace / name
        if path.exists():
            try:
                window = json.loads(path.read_text()).get("window")
            except (OSError, ValueError) as error:
                raise LedgerError(f"{path}: {error}") from None
            if window:
                return int(window[0]), int(window[1])
    return None


def clusters(workspace: Path, window: tuple[int, int] | None = None) -> tuple[ClusterState, ...]:
    """Read every cluster's state off the workspace, in ordinal order.

    Args:
        workspace: The workspace root.
        window: Inclusive ordinal bounds of this reconstruction's work;
            defaults to what the workspace recorded, else every cluster.

    Returns:
        One state per timeline cluster.

    Raises:
        LedgerError: If the timeline, a record or the revision map is unreadable.
    """
    bounds = window or window_of(workspace)
    entries = _entries(workspace)
    tags = _tags(workspace / "draft")
    states = []
    for row in _rows(workspace):
        directory = workspace / "checkpoints" / row["id"]
        tag, normative = entries.get(row["id"], (None, None))
        states.append(
            ClusterState(
                id=row["id"],
                ordinal=int(row["ordinal"]),
                kind=row.get("kind"),
                in_window=bounds is None or bounds[0] <= int(row["ordinal"]) <= bounds[1],
                pre_seeded=(directory / PRESEED_MARKER).exists(),
                checkpoint=(directory / CHECKPOINT_FILE).is_file(),
                revision_tag=tag,
                normative_change=normative,
                tag_exists=tag in tags if tag else False,
            )
        )
    return tuple(states)


def next_cluster(workspace: Path, window: tuple[int, int] | None = None) -> ClusterState | None:
    """The lowest-ordinal in-window cluster that is not done, or None."""
    for state in clusters(workspace, window):
        if not state.done:
            return state
    return None


def counts(states: tuple[ClusterState, ...]) -> dict[str, int]:
    """Totals a status line prints."""
    in_window = [s for s in states if s.in_window and not s.pre_seeded]
    return {
        "total": len(states),
        "in_window": len(in_window),
        "done": sum(1 for s in in_window if s.done),
        "partial": sum(1 for s in in_window if s.partial_reason),
        "outstanding": sum(1 for s in in_window if not s.done),
        "pre_seeded": sum(1 for s in states if s.pre_seeded),
    }
```

- [ ] **Step 4: Point the five readers at the ledger**

1. `ai_rfc/pipeline/state.py` `_checkpoint`: replace the `ids`/`frozen` computation with `states = ledger.clusters(ws.root); total = len(states); frozen = sum(1 for s in states if s.checkpoint)` (import `from .. import ledger`); the PENDING/PARTIAL/DONE messages stay word-for-word.
2. `ai_rfc/draft/completeness.py`: where the `unprocessed_clusters` field is computed from timeline rows minus `checkpoint_records`, compute it as `[s.id for s in ledger.clusters(root) if not s.checkpoint]`. **Derive the root as `checkpoints_dir.parent`; do NOT add a workspace parameter to `build()`.** `build(timeline_dir, checkpoints_dir, manifest_path, revisions_path, draft_repo)` is at `completeness.py:231-237` and its only caller passes those five paths at `draft/cli.py:267-273` — a sixth parameter would change that call site, and `ai_rfc/draft/cli.py` is deliberately **not** in this task's Files list (Task 2 already rewrote it; two tasks editing one file is the collision this ordering exists to avoid). Keep `checkpoint_records` for attribution.
3. `ai_rfc/server/core/queries.py`: delete `_processed_cluster_ids`; `cluster_next` becomes `state = ledger.next_cluster(ctx.workspace); return None if state is None else next(row for row in _clusters(ctx) if row["id"] == state.id)`; in `status()`, `processed` becomes `{s.id for s in ledger.clusters(ctx.workspace) if s.done}` and the payload gains `"ledger": ledger.counts(states)`.
4. `ai_rfc/experiment/progress.py` `window_progress`: `counted = [s for s in ledger.clusters(workspace) if s.in_window and not s.pre_seeded]`; `done = sum(1 for s in counted if s.done)`; the first `not s.done` row is returned as `(row_dict, artifacts_dict, index, done, total)` where `row_dict` is the timeline row (read once via `metrics.window_clusters`) and `artifacts_dict` is `cluster_artifacts(workspace, row)` — keep the tuple shape so `per_cluster.py` is untouched here.
5. `ai_rfc/experiment/metrics.py` `cluster_artifacts`: build the dict from the ledger row for that id (`checkpoint`, `pre_seeded`, `revision_tag`, `normative_change`, `tag_exists`, and `artifacts = state.done and state.in_window and not state.pre_seeded`); `ai_rfc/experiment/per_cluster.py`: replace the body of `partial_reason(artifacts)` callers with `ledger` rows where the row is at hand, or keep `partial_reason` as the one-liner `return ledger.ClusterState(...)`-free version reading the same three keys — its three strings are now defined in one place (`ClusterState.partial_reason`); make `per_cluster.partial_reason` return `state.partial_reason` for the row's ledger state.

`window_progress`, `cluster_artifacts` and `partial_reason` keep their signatures because SP7c's plan (committed `873063ce3`) edits their callers; only their internals now read the ledger.

- [ ] **Step 5: Run the affected suites**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/ledger tests/substrate/pipeline tests/substrate/draft tests/server tests/experiment/test_progress.py tests/experiment/test_metrics.py tests/experiment/test_per_cluster.py -n auto`
Expected: all PASS. One expected behaviour change to confirm in `tests/server`: a test that treated a bare checkpoint directory as processed (if any) now sees it as outstanding — update its assertion, and cite this task in the commit body.

- [ ] **Step 6: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc tests/ledger && $PY -m flake8 --max-line-length=88 ai_rfc/ledger.py tests/ledger && $PY -m mypy --follow-imports=silent ai_rfc/ledger.py
git status --short
git add ai_rfc/ledger.py ai_rfc/pipeline/state.py ai_rfc/draft/completeness.py ai_rfc/server/core/queries.py ai_rfc/experiment/progress.py ai_rfc/experiment/metrics.py ai_rfc/experiment/per_cluster.py tests/ledger/__init__.py tests/ledger/test_ledger.py
git commit -m "feat: read per-cluster progress from one ledger every surface agrees with"
```

---

### Task 4: `ai-rfc init --config` — acquire, scaffold, seal

**Files:**
- Create: `ai_rfc/lifecycle/workspace.py` (flat), `ai_rfc/lifecycle/init/{__init__,__main__,cli}.py` (verb package, D1)
- Modify: `ai_rfc/entrypoints.py` (row `init`), `ai_rfc/experiment/workspace.py` (imports the moved helpers; `Target`/`TARGETS` removed; `prepare(config, …)`), `ai_rfc/experiment/cli.py` (`workspace prepare --config`), `tests/conftest.py` (**APPEND** — the file already exists and owns `pytest_addoption("--update-goldens")`; overwriting it breaks every golden test), `tests/experiment/conftest.py` (`fixture_config` replaces `fixture_target`), `tests/experiment/test_workspace.py`, `tests/experiment/test_per_cluster.py` (it imports `fixture_target` at `:15` and calls it at `:30` inside `prepare(..., panther_repo=panther_repo, ...)` — both change here)
- Test: `tests/cli/test_init.py` (new)

**Interfaces:**
- Consumes: `ai_rfc.config.{load_config, dump_config, ReconConfig}` (Task 1); `ai_rfc.pipeline.workspace.Workspace`; `ai_rfc.pipeline.run.perform` + `ai_rfc.pipeline.stages.BY_NAME` (the forge stage); SP7a's adopter `scaffold_draft`, `_write_empty_state`, the references sealing code and `write_digest`/`verify_digest`/`_digests` currently in `ai_rfc/experiment/workspace.py`; `ai_rfc.draft.build.load_toolchain`.
- Produces: `Layout(Workspace)` with `config`, `init_record`, `refcache`, `runs`, `interviews`, `out` properties; `acquire(config, layout) -> Acquired(resolved_sha: str, forge_snapshot: str | None)`; `scaffold(config, layout, *, template, template_commit) -> str`; `write_registers(config, layout) -> None`; `seal_references(config, layout) -> tuple[str | None, str | None]`; `write_digest(root)`, `verify_digest(root) -> list[str]`; constants `TEMPLATE_URL`, `TEMPLATE_COMMIT`, `HARNESS_NAME`, `HARNESS_EMAIL`, `PINNED_DATE`, `CONFIG_FILE = "recon.yaml"`, `INIT_RECORD = "init.json"`; `initialise(config, *, dest: Path | None = None, template, template_commit) -> Path` (the workspace root; `dest` overrides `config.workspace` for campaign pristines); CLI `ai-rfc init --config PATH [--template] [--template-commit]`; `experiment.workspace.prepare(config, *, root, toolchain, template, template_commit) -> Path`. Task 5 reads `init.json` and the sealed config; Task 7 runs `init` on MARK.

**Why this shape.** Acquisition (clone + forge) is the one networked phase (D34) and belongs to `init`, not to a stage the driver might re-run. Everything the harness's `prepare` did for a campaign pristine — scaffold, registers, references, digest — is exactly what a production workspace needs, so it moves to `lifecycle/` and `prepare` calls it, replacing the closed target table with the config (friction 11).

- [ ] **Step 1: Write the failing init tests**

Create `tests/cli/test_init.py`:

```python
"""`ai-rfc init`: from a recon.yaml to a workspace with a pinned clone, a draft and a sealed config."""

import hashlib
import json
from pathlib import Path

import pytest

from ai_rfc import cli
from ai_rfc.config import load_config
from ai_rfc.lifecycle.workspace import Layout, verify_digest
from ai_rfc.server.testing import git

DATE = "2026-01-01T00:00:09+00:00"


@pytest.fixture
def source_repo(tmp_path: Path) -> Path:
    """A tiny local repository standing in for the implementation under reconstruction."""
    repo = tmp_path / "upstream"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "a.py").write_text("print(1)\n")
    git(repo, "add", "a.py")
    git(repo, "commit", "-q", "-m", "first", date=DATE)
    (repo / "a.py").write_text("print(2)\n")
    git(repo, "add", "a.py")
    git(repo, "commit", "-q", "-m", "second", date="2026-01-02T00:00:09+00:00")
    return repo


def _config(tmp_path: Path, source_repo: Path, extra: str = "") -> Path:
    path = tmp_path / "recon.yaml"
    path.write_text(
        "name: fixture\n"
        f"workspace: {tmp_path / 'ws'}\n"
        "source:\n"
        f"  repo: {source_repo}\n"
        "  host: none\n"
        "  pin: main\n"
        "draft:\n"
        "  name: draft-test-fixture\n"
        + extra
    )
    return path


def test_init_builds_the_workspace_and_seals_the_config(tmp_path, source_repo, template_repo, capsys):
    template, commit = template_repo
    config_path = _config(tmp_path, source_repo)
    assert cli.main(["init", "--config", str(config_path), "--template", template, "--template-commit", commit]) == 0
    ws = Layout(tmp_path / "ws")
    head = git(source_repo, "rev-parse", "HEAD")
    assert git(ws.clone, "rev-parse", "HEAD") == head
    assert (ws.draft / "draft-test-fixture.md").exists() and (ws.draft / "Makefile").exists()
    assert ws.manifest.read_text().startswith("rfc: FIXTURE-RECON\n")
    assert ws.questions.read_text() == "questions: {}\n" and ws.revisions.read_text() == "revisions: {}\n"
    sealed = load_config(ws.config)
    assert sealed.name == "fixture" and sealed.source.pin == "main"
    record = json.loads(ws.init_record.read_text())
    assert record["resolved_pin"] == head and record["forge_snapshot"] is None
    assert record["config_sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    assert record["window"] is None and record["references"] == []
    assert verify_digest(ws.root) == []
    out = capsys.readouterr().out
    assert str(ws.root) in out and "ai-rfc run --config" in out


def test_init_refuses_an_existing_workspace(tmp_path, source_repo, template_repo, capsys):
    template, commit = template_repo
    config_path = _config(tmp_path, source_repo)
    argv = ["init", "--config", str(config_path), "--template", template, "--template-commit", commit]
    assert cli.main(argv) == 0
    assert cli.main(argv) == 1
    assert "exists" in capsys.readouterr().err


def test_init_resolves_a_sha_pin_and_records_the_window(tmp_path, source_repo, template_repo):
    template, commit = template_repo
    first = git(source_repo, "rev-list", "--max-parents=0", "HEAD")
    config_path = _config(tmp_path, source_repo, extra="window: [1, 1]\n")
    text = config_path.read_text().replace("pin: main", f"pin: {first}")
    config_path.write_text(text)
    assert cli.main(["init", "--config", str(config_path), "--template", template, "--template-commit", commit]) == 0
    ws = Layout(tmp_path / "ws")
    assert git(ws.clone, "rev-parse", "HEAD") == first
    assert json.loads(ws.init_record.read_text())["window"] == [1, 1]


def test_init_with_references_needs_a_toolchain_and_seals_them(tmp_path, source_repo, template_repo, toolchain_record, capsys):
    template, commit = template_repo
    config_path = _config(tmp_path, source_repo, extra="references: [RFC9000]\n")
    argv = ["init", "--config", str(config_path), "--template", template, "--template-commit", commit]
    assert cli.main(argv) == 1
    assert "toolchain" in capsys.readouterr().err
    config_path.write_text(config_path.read_text() + f"toolchain: {toolchain_record}\n")
    assert cli.main(argv) == 0
    ws = Layout(tmp_path / "ws")
    assert (ws.refcache / "reference.RFC.9000.xml").exists()
    assert json.loads(ws.init_record.read_text())["references"] == ["RFC9000"]
```

`template_repo` (`tests/experiment/conftest.py:53`, yielding `(str, str)` — a path string and a commit sha, which is why `template, commit = template_repo` destructures correctly) and `toolchain_record` (`tests/experiment/conftest.py:115`) are the fixtures SP7a added. Move both into the repository-root `tests/conftest.py` so `tests/cli` can use them (pytest discovers a root conftest for every subtree).

Two facts the original plan text got wrong, both of which bite silently:

- **`tests/conftest.py` already exists.** It is short and holds only `pytest_addoption` registering `--update-goldens`. **Append** the fixtures to it; do not create or overwrite it, or that option disappears and every golden test errors on an unknown flag.
- **`toolchain_record` is defined twice.** Besides the conftest copy there is a module-local shadow at `tests/experiment/test_workspace.py:370`. Moving only the conftest copy leaves the shadow in force for that module, so the two definitions silently diverge. Delete the shadow when you move the conftest copy, and re-run `tests/experiment/test_workspace.py` specifically to confirm it still passes against the shared fixture.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli/test_init.py -v`
Expected: FAIL at import (`No module named 'ai_rfc.lifecycle.workspace'`).

- [ ] **Step 3: Move the workspace helpers into `ai_rfc/lifecycle/workspace.py`**

Create the module by moving, verbatim, from `ai_rfc/experiment/workspace.py`: `TEMPLATE_URL`, `TEMPLATE_COMMIT`, `HARNESS_NAME`, `HARNESS_EMAIL`, `PINNED_DATE`, `ADOPTER_FILES`, `EXTRA_IGNORES`, `REFERENCES_FILE`, `REFCACHE_DIR`, `DIGEST_FILE`, `RECORD_FILE` (keep the name for `pristine.json`), `_SKIP_FROM_DIGEST` (add `INIT_RECORD` and `CONFIG_FILE` to it — the sealed config and the init record are digested, so do NOT add them; keep the set as it is), `_run_git`, `_git`, `_write_adopter_files`, `scaffold_draft` (renamed `scaffold`, taking `(config, layout, *, template, template_commit)` and reading `draft.name/title/abbrev` and `name` from the config), `_write_empty_state` (renamed `write_registers(config, layout)`, writing `rfc: <draft.rfc_id>`, `title: <draft.title>`), the references-sealing block of `prepare` (as `seal_references(config, layout) -> (refcache_sha256, template_home)`), `_digests`, `write_digest`, `verify_digest`. Then add:

```python
CONFIG_FILE = "recon.yaml"
INIT_RECORD = "init.json"


class Layout(Workspace):
    """A production workspace: the pipeline's layout plus the operator's records."""

    @property
    def config(self) -> Path:
        """The sealed copy of ``recon.yaml``."""
        return self.root / CONFIG_FILE

    @property
    def init_record(self) -> Path:
        """What ``init`` resolved and froze."""
        return self.root / INIT_RECORD

    @property
    def refcache(self) -> Path:
        """Sealed reference cache for offline builds."""
        return self.root / REFCACHE_DIR

    @property
    def runs(self) -> Path:
        """One directory per ``run`` invocation (CLI-2)."""
        return self.root / "runs"

    @property
    def interviews(self) -> Path:
        """Interview transcripts the question register points at."""
        return self.root / "interviews"

    @property
    def out(self) -> Path:
        """Reports the stages write."""
        return self.root / "out"


@dataclass(frozen=True)
class Acquired:
    """What acquisition pinned."""

    resolved_sha: str
    forge_snapshot: str | None


def acquire(config: ReconConfig, layout: Layout) -> Acquired:
    """Clone the source at its pin and fetch the forge snapshot — the networked phase.

    Args:
        config: The validated configuration.
        layout: The workspace to fill.

    Returns:
        The resolved pin and the snapshot directory name, if a forge was fetched.

    Raises:
        LifecycleError: If the clone or the checkout fails, or the forge stage refuses.
    """
    cloned = _run_git("clone", "-q", config.source.repo, str(layout.clone))
    if cloned.returncode != 0:
        raise LifecycleError(f"cloning {config.source.repo} failed: {cloned.stderr.strip()}")
    checked = _run_git("-C", str(layout.clone), "checkout", "-q", "--detach", config.source.pin)
    if checked.returncode != 0:
        raise LifecycleError(f"{config.source.pin}: not a commit or ref in {config.source.repo}: {checked.stderr.strip()}")
    resolved = _git(layout.clone, "rev-parse", "HEAD")
    snapshot: str | None = None
    if config.source.host != "none":
        result = perform(BY_NAME["forge"], layout, forge_url=config.source.repo, host=config.source.host)
        if not result.ok:
            raise LifecycleError(f"forge fetch exited {result.exit_code}; see stderr")
        latest = layout.latest_forge_snapshot()
        snapshot = latest.name if latest else None
    return Acquired(resolved_sha=resolved, forge_snapshot=snapshot)
```

with `from ..config import ReconConfig`, `from ..pipeline.run import perform`, `from ..pipeline.stages import BY_NAME`, `from ..pipeline.workspace import Workspace`, and `class LifecycleError(RuntimeError)` in `ai_rfc/lifecycle/__init__.py`. (`Workspace.latest_forge_snapshot()` exists in `pipeline/workspace.py`; `perform`'s forge builder passes `--repo <clone> --out <forge root> --host`.) The forge stage reads the token from `config.source.token_env`'s variable through the forge CLI's own environment handling, so nothing here touches tokens.

- [ ] **Step 4: Write the `init` verb package**

Create `ai_rfc/lifecycle/init/__init__.py` (docstring only) and `ai_rfc/lifecycle/init/__main__.py` (the `ai_rfc/draft/__main__.py` pattern, docstring ``` ``python -m ai_rfc.lifecycle.init``. ```), then `ai_rfc/lifecycle/init/cli.py` — note the three-dot package imports and two-dot shared-module imports required by D1:

```python
"""``ai-rfc init --config recon.yaml``: build the workspace a reconstruction runs in."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ... import __version__
from ...config import ConfigError, ReconConfig, dump_config, load_config
from .. import LifecycleError
from ..workspace import (
    TEMPLATE_COMMIT,
    TEMPLATE_URL,
    Layout,
    acquire,
    scaffold,
    seal_references,
    write_digest,
    write_registers,
)

CONFIG_ENV = "AI_RFC_CONFIG"


def _report(message: str) -> None:
    """Diagnostics to stderr — the ``panther.*`` loggers swallow warnings."""
    import sys

    print(message, file=sys.stderr)


def config_path_from(args: argparse.Namespace) -> Path:
    """``--config`` or ``$AI_RFC_CONFIG``; nothing is guessed."""
    if args.config is not None:
        return args.config
    if os.environ.get(CONFIG_ENV):
        return Path(os.environ[CONFIG_ENV])
    raise LifecycleError(f"no config: pass --config or set {CONFIG_ENV}")


def add_config_argument(parser: argparse.ArgumentParser) -> None:
    """The one argument every lifecycle verb shares."""
    parser.add_argument(
        "--config", type=Path, default=None, help=f"recon.yaml (default: ${CONFIG_ENV})."
    )


def initialise(
    config: ReconConfig,
    *,
    config_path: Path,
    dest: Path | None = None,
    template: str = TEMPLATE_URL,
    template_commit: str = TEMPLATE_COMMIT,
) -> Path:
    """Create and fill the workspace.

    Args:
        config: The validated configuration.
        config_path: Where it was read from; its digest is recorded.
        dest: Workspace root overriding ``config.workspace`` (campaign pristines).
        template: Internet-Draft template clone source.
        template_commit: The commit the draft scaffold is pinned to.

    Returns:
        The workspace root.

    Raises:
        LifecycleError: If the workspace exists, references are declared without a
            toolchain, or acquisition fails.
    """
    layout = Layout(dest or config.workspace)
    if layout.root.exists() and any(layout.root.iterdir()):
        raise LifecycleError(f"{layout.root} exists; a workspace is initialised once")
    if config.references and (config.toolchain is None or not config.toolchain.exists()):
        raise LifecycleError(
            f"{config.name} declares references but no toolchain record exists at "
            f"{config.toolchain}; run `ai-rfc toolchain provision` first"
        )
    layout.root.mkdir(parents=True, exist_ok=True)
    acquired = acquire(config, layout)
    draft_head = scaffold(config, layout, template=template, template_commit=template_commit)
    write_registers(config, layout)
    refcache_sha256, template_home = seal_references(config, layout)
    layout.config.write_text(dump_config(config))
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "name": config.name,
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "sealed_config_sha256": hashlib.sha256(layout.config.read_bytes()).hexdigest(),
        "source": config.source.repo,
        "pin": config.source.pin,
        "resolved_pin": acquired.resolved_sha,
        "forge_snapshot": acquired.forge_snapshot,
        "window": list(config.window) if config.window else None,
        "draft_head": draft_head,
        "template": template,
        "template_commit": template_commit,
        "references": list(config.references),
        "refcache_sha256": refcache_sha256,
        "toolchain": str(config.toolchain) if config.toolchain else None,
        "toolchain_sha256": (
            hashlib.sha256(config.toolchain.read_bytes()).hexdigest()
            if config.toolchain and config.toolchain.exists()
            else None
        ),
        "template_home": template_home,
        "ai_rfc_version": __version__,
    }
    layout.init_record.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    write_digest(layout.root)
    return layout.root


def configure(parser: argparse.ArgumentParser) -> None:
    """Arguments of ``ai-rfc init``."""
    parser.description = "Create the workspace: clone at the pin, fetch the forge, scaffold the draft, seal the config."
    add_config_argument(parser)
    parser.add_argument("--template", default=TEMPLATE_URL, help="Draft template repository (default: %(default)s).")
    parser.add_argument("--template-commit", default=TEMPLATE_COMMIT, help="Template commit to pin (default: %(default)s).")


def build_standalone_parser() -> argparse.ArgumentParser:
    """The parser ``python -m ai_rfc.lifecycle.init`` uses (its ``cli`` module)."""
    parser = argparse.ArgumentParser(prog="ai-rfc init")
    parser.add_argument("--version", action="version", version=f"ai-rfc init {__version__}")
    configure(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Perform ``init``; 0 on success, 1 on any refusal."""
    try:
        config_path = config_path_from(args)
        config = load_config(config_path)
        root = initialise(
            config,
            config_path=config_path,
            template=args.template,
            template_commit=args.template_commit,
        )
    except (LifecycleError, ConfigError, OSError) as error:
        _report(f"error: {error}")
        return 1
    print(f"workspace: {root}")
    print(f"next: ai-rfc run --config {config_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Command-line entry."""
    return run(build_standalone_parser().parse_args(argv))
```

Register `EntryPoint("init", "ai-rfc init", f"{PACKAGE}.lifecycle.init.cli", "Create the workspace from recon.yaml: clone at the pin, fetch the forge, scaffold the draft", LIFECYCLE)` **immediately after the `config` row** in `ENTRY_POINTS` — the section-contiguity test requires it, and the module path ends in `.cli` per D1.

- [ ] **Step 5: Re-point the harness at the moved helpers and make `prepare` take a config**

In `ai_rfc/experiment/workspace.py`: delete the moved definitions and import them from `ai_rfc.lifecycle.workspace`; delete `Target`, `AIQUIC`/`MARK`, `TARGETS`, `_copy_substrate`, `_emit_and_verify_views`; rewrite `prepare`:

```python
def prepare(
    config: ReconConfig,
    *,
    root: Path,
    config_path: Path,
    template: str = TEMPLATE_URL,
    template_commit: str = TEMPLATE_COMMIT,
) -> Path:
    """Build a campaign's pristine workspace from a config, under ``root/pristine/``.

    Initialises the workspace exactly as ``ai-rfc init`` does, performs the
    deterministic stages up to views, pre-seeds every out-of-window cluster and
    seals the digest a campaign copies from.
    """
    low, high = config.window or (1, 1)
    pristine = root / "pristine" / f"{config.name}-w{low:02d}-{high:02d}"
    if pristine.exists():
        raise ExperimentError(f"{pristine} exists; a pristine workspace is prepared once")
    initialise(config, config_path=config_path, dest=pristine, template=template, template_commit=template_commit)
    layout = Layout(pristine)
    for name in ("history", "timeline", "views"):
        result = perform(BY_NAME[name], layout)
        if not result.ok:
            raise ExperimentError(f"{name} exited {result.exit_code}; see stderr")
    ordinals = [row["ordinal"] for row in read_clusters(pristine / "timeline")]
    window = config.window or (min(ordinals), max(ordinals))
    seeded = preseed(pristine, out_of_window(ordinals, window))
    record = json.loads(layout.init_record.read_text())
    record.update({"target": config.name, "window": list(window), "pre_seeded": seeded, "clone_head": record["resolved_pin"]})
    (pristine / RECORD_FILE).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    write_digest(pristine)
    return pristine
```

(`preseed` lost its `panther_repo` parameter in SP1; `read_clusters` is `ai_rfc.timeline.store.read_clusters`; `out_of_window` stays. `pristine.json` keeps `target`, `window`, `clone_head`, `draft_head`, `pre_seeded` because `campaign init`, `copy_workspace` and `metrics.window_clusters` read them.) In `ai_rfc/experiment/cli.py`, `workspace prepare` drops the positional target and `--panther-repo`, gains `--config` (required) and loads it with `load_config`. In `tests/experiment/conftest.py`, replace `fixture_target(source, window)` with `fixture_config(tmp_path, source: Path, window=(2, 2)) -> tuple[ReconConfig, Path]` that writes a `recon.yaml` (`name: fixture`, `source.repo: <source>/clone`, `host: none`, `pin: <HEAD of that clone>`, `draft.name: draft-test-fixture`, `window: [low, high]`) and returns `(load_config(path), path)`; the `pristine` fixture calls `prepare(config, root=…, config_path=path, template=…, template_commit=…)`. Update every `fixture_target` caller in `tests/experiment/test_workspace.py` (the scaffold tests call `scaffold(config, Layout(dest), template=…, template_commit=…)` now).

**`fixture_target` has 16 call sites across three files, not one.** It is a plain module-level function at `tests/experiment/conftest.py:80`, not a pytest fixture, so callers reach it by `from .conftest import fixture_target`. The sites are `tests/experiment/conftest.py:107`; `tests/experiment/test_workspace.py` (import `:24`; calls `:33, :42, :72, :78, :91, :296, :361, :401, :434, :456, :475, :497, :642, :678`); and **`tests/experiment/test_per_cluster.py`** (import `:15`; call `:30`). The last file is the one the original plan missed. Its `wide_pristine` fixture calls `prepare(fixture_target(fixture_workspace, window=(1, 2)), root=…, panther_repo=panther_repo, template=…, template_commit=commit)` — both the positional `Target` and the `panther_repo=` keyword disappear in this step, so it must become `prepare(config, root=…, config_path=path, template=…, template_commit=commit)` built from `fixture_config`. Verify with `grep -rn "fixture_target\|panther_repo" tests/` before committing: zero hits outside a deliberate CLI-3 leftover.

- [ ] **Step 6: Run the suites**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli/test_init.py tests/experiment -n auto`
Expected: all PASS. `test_scaffold_is_byte_deterministic` still holds (the config carries no clock). Campaign tests that read `pristine.json["target"]` still find it.

- [ ] **Step 7: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc tests && $PY -m flake8 --max-line-length=88 ai_rfc/lifecycle ai_rfc/experiment/workspace.py tests/cli && $PY -m mypy --follow-imports=silent ai_rfc/lifecycle
git status --short
git add ai_rfc/lifecycle/workspace.py ai_rfc/lifecycle/init/__init__.py ai_rfc/lifecycle/init/__main__.py ai_rfc/lifecycle/init/cli.py ai_rfc/lifecycle/__init__.py ai_rfc/entrypoints.py ai_rfc/experiment/workspace.py ai_rfc/experiment/cli.py tests/conftest.py tests/cli/test_init.py tests/experiment/conftest.py tests/experiment/test_workspace.py tests/experiment/test_per_cluster.py
git commit -m "feat: initialise a workspace from recon.yaml, and prepare campaign pristines from it"
```

---

### Task 5: `ai-rfc run`, `ai-rfc status`, `ai-rfc verify` — the deterministic half behind one config

**Files:**
- Create: `ai_rfc/lifecycle/common.py` (flat — shared, not a verb), and three verb packages per D1: `ai_rfc/lifecycle/{run,status,verify}/{__init__,__main__,cli}.py`
- Modify: `ai_rfc/pipeline/cli.py` (`status_payload`/`print_status` made public), `ai_rfc/entrypoints.py` (rows `run`, `status`, `verify`, each inserted immediately after the previous lifecycle row), `ai_rfc/lifecycle/init/cli.py` (loses `add_config_argument`/`config_path_from`/`_report` to `common.py` and imports them back)
- Test: `tests/cli/test_run.py`, `tests/cli/test_status_verify.py` (new); `tests/conftest.py` (**append** `source_repo` and `initialised` fixtures — the file exists)

**Interfaces:**
- Consumes: `load_config`, `drift`, `dump_config` (Task 1); `Layout`, `initialise`, `verify_digest` (Task 4); `ledger.clusters/next_cluster/counts` (Task 3); `ai_rfc.pipeline.run.perform`, `ai_rfc.pipeline.stages.{STAGES, BY_NAME, Performer, is_optional}`, `ai_rfc.pipeline.state.{state, State}`; `ai_rfc.draft.cli.main` (completeness).
- Produces: `common.load_sealed(config_path) -> tuple[ReconConfig, ReconConfig, Layout]` (given, sealed, layout; raises `LifecycleError` on refused drift, returns noted drift lines via `common.drift_notes`); `run.run_stages(config_path, *, until: str | None = None, report=print) -> int`; `status.status_payload(config_path) -> dict` and the verb; `verify.verify(config_path, *, strict: bool) -> int`; the verbs `ai-rfc run --config [--until STAGE]`, `ai-rfc status --config [--json]`, `ai-rfc verify --config [--strict]`. CLI-2 extends `run_stages` into the session loop; Task 7 runs all three on MARK.

**Why this shape.** `run` is the deterministic half of the autonomous command: it performs whatever pipeline stage is next through the existing `DISPATCH`, and stops at the mining boundary with the ledger printed instead of an instruction alone (D54's first half). `status` and `verify` read the same config, the same layout and the same ledger, so an operator never types a path twice. The `stages:` tuning fields the config validates are not yet wired into the stage builders here — CLI-2 threads them through `_Request` when it rewrites the walk; `run` says so in its `--help`.

- [ ] **Step 1: Shared fixtures and the failing tests**

Move `source_repo` from `tests/cli/test_init.py` into `tests/conftest.py`, and add there:

```python
@pytest.fixture
def initialised(tmp_path, source_repo, template_repo):
    """A config file and the workspace `ai-rfc init` built from it (host none, no references)."""
    from ai_rfc import cli

    template, commit = template_repo
    config_path = tmp_path / "recon.yaml"
    config_path.write_text(
        "name: fixture\n"
        f"workspace: {tmp_path / 'ws'}\n"
        "source:\n"
        f"  repo: {source_repo}\n"
        "  host: none\n"
        "  pin: main\n"
        "draft:\n"
        "  name: draft-test-fixture\n"
    )
    assert cli.main(["init", "--config", str(config_path), "--template", template, "--template-commit", commit]) == 0
    return config_path, tmp_path / "ws"
```

Create `tests/cli/test_run.py`:

```python
"""`ai-rfc run`: perform what is next, stop at the boundary with the ledger in hand."""

import json

from ai_rfc import cli
from ai_rfc.lifecycle.workspace import Layout


def test_run_performs_the_deterministic_stages_and_stops_at_mining(initialised, capsys):
    config_path, root = initialised
    assert cli.main(["run", "--config", str(config_path)]) == 0
    ws = Layout(root)
    assert ws.commits.exists() and ws.timeline_json.exists()
    assert any((ws.clusters).glob("*/view.json"))
    err = capsys.readouterr().err
    assert "history" in err and "timeline" in err and "views" in err
    assert "boundary: mining" in err
    assert "clusters: 0 of" in err and "done" in err
    assert "sessions: not configured" in err


def test_a_second_run_performs_nothing_new(initialised, capsys):
    config_path, _ = initialised
    cli.main(["run", "--config", str(config_path)])
    capsys.readouterr()
    assert cli.main(["run", "--config", str(config_path)]) == 0
    err = capsys.readouterr().err
    assert "performed: nothing" in err and "boundary: mining" in err


def test_until_stops_after_the_named_stage(initialised, capsys):
    config_path, root = initialised
    assert cli.main(["run", "--config", str(config_path), "--until", "history"]) == 0
    ws = Layout(root)
    assert ws.commits.exists() and not ws.timeline_json.exists()
    assert "stopped after history" in capsys.readouterr().err


def test_a_drifted_pin_is_refused_before_anything_runs(initialised, capsys):
    config_path, root = initialised
    config_path.write_text(config_path.read_text().replace("pin: main", "pin: v9"))
    assert cli.main(["run", "--config", str(config_path)]) == 1
    err = capsys.readouterr().err
    assert "refused" in err and "source.pin" in err
    assert not Layout(root).commits.exists()


def test_a_noted_drift_is_reported_and_run_continues(initialised, capsys):
    config_path, _ = initialised
    config_path.write_text(config_path.read_text() + "sessions:\n  budget_usd: 5\n")
    assert cli.main(["run", "--config", str(config_path)]) == 0
    err = capsys.readouterr().err
    assert "note: config drift" in err and "sessions.budget_usd" in err
    assert "sessions: configured" in err


def test_run_needs_an_initialised_workspace(tmp_path, source_repo, capsys):
    config_path = tmp_path / "recon.yaml"
    config_path.write_text(
        f"name: fixture\nworkspace: {tmp_path / 'nope'}\nsource:\n  repo: {source_repo}\n  host: none\n  pin: main\ndraft:\n  name: draft-test-fixture\n"
    )
    assert cli.main(["run", "--config", str(config_path)]) == 1
    assert "ai-rfc init" in capsys.readouterr().err
```

Create `tests/cli/test_status_verify.py`:

```python
"""`ai-rfc status` and `ai-rfc verify` read the same config, layout and ledger as `run`."""

import json

from ai_rfc import cli


def test_status_json_carries_stages_ledger_init_and_drift(initialised, capsys):
    config_path, root = initialised
    cli.main(["run", "--config", str(config_path)])
    capsys.readouterr()
    assert cli.main(["status", "--config", str(config_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"] == str(root)
    assert {s["name"] for s in payload["stages"]} >= {"history", "timeline", "views", "mining"}
    assert payload["ledger"]["done"] == 0 and payload["ledger"]["outstanding"] == payload["ledger"]["in_window"]
    assert payload["next_cluster"]["ordinal"] == 1
    assert payload["init"]["resolved_pin"] and payload["drift"] == {"refused": [], "noted": []}


def test_status_prints_a_human_table(initialised, capsys):
    config_path, _ = initialised
    assert cli.main(["status", "--config", str(config_path)]) == 0
    out = capsys.readouterr().out
    assert "history" in out and "clusters:" in out and "next:" in out


def test_verify_strict_names_every_unprocessed_cluster(initialised, capsys):
    config_path, _ = initialised
    cli.main(["run", "--config", str(config_path)])
    capsys.readouterr()
    assert cli.main(["verify", "--config", str(config_path), "--strict"]) == 3
    captured = capsys.readouterr()
    assert "completeness: findings" in captured.err
    assert "check: ok" in captured.err and "gate: ok" in captured.err
    assert "build: skipped" in captured.err


def test_verify_without_strict_reports_and_exits_zero(initialised, capsys):
    config_path, _ = initialised
    cli.main(["run", "--config", str(config_path)])
    capsys.readouterr()
    assert cli.main(["verify", "--config", str(config_path)]) == 0


def test_verify_reports_a_refused_drift_as_a_finding(initialised, capsys):
    config_path, _ = initialised
    config_path.write_text(config_path.read_text().replace("draft-test-fixture", "draft-other"))
    assert cli.main(["verify", "--config", str(config_path), "--strict"]) == 3
    assert "drift: refused" in capsys.readouterr().err
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli/test_run.py tests/cli/test_status_verify.py -v`
Expected: every test FAILS with `invalid choice: 'run'` (or `status`/`verify`).

- [ ] **Step 3: `common.py` — one loader for every lifecycle verb**

```python
"""What every lifecycle verb does first: read the config, find the workspace, check drift."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ..config import ConfigError, ReconConfig, drift, load_config
from . import LifecycleError
from .workspace import Layout

CONFIG_ENV = "AI_RFC_CONFIG"


def report(message: str) -> None:
    """Diagnostics to stderr — the ``panther.*`` loggers swallow warnings."""
    print(message, file=sys.stderr)


def add_config_argument(parser: argparse.ArgumentParser) -> None:
    """The one argument every lifecycle verb shares."""
    parser.add_argument("--config", type=Path, default=None, help=f"recon.yaml (default: ${CONFIG_ENV}).")


def config_path_from(args: argparse.Namespace) -> Path:
    """``--config`` or ``$AI_RFC_CONFIG``; nothing is guessed."""
    if args.config is not None:
        return args.config
    if os.environ.get(CONFIG_ENV):
        return Path(os.environ[CONFIG_ENV])
    raise LifecycleError(f"no config: pass --config or set {CONFIG_ENV}")


def load_sealed(config_path: Path) -> tuple[ReconConfig, ReconConfig, Layout, list[str]]:
    """Load the config as given and as sealed, refusing identity drift.

    Args:
        config_path: The file the operator passed.

    Returns:
        ``(given, sealed, layout, noted)`` — ``noted`` lists non-identity drift lines.

    Raises:
        LifecycleError: If the workspace was never initialised or an identity field drifted.
        ConfigError: If either file does not validate.
    """
    given = load_config(config_path)
    layout = Layout(given.workspace)
    if not layout.init_record.exists() or not layout.config.exists():
        raise LifecycleError(f"{layout.root} is not an initialised workspace; run: ai-rfc init --config {config_path}")
    sealed = load_config(layout.config)
    refused, noted = drift(sealed, given)
    if refused:
        raise LifecycleError("config drift refused (re-run ai-rfc init into a new workspace to change these): " + "; ".join(refused))
    return given, sealed, layout, noted
```

`common.py` is a **flat module** at `ai_rfc/lifecycle/common.py`, not a verb package — it registers no `EntryPoint`, so D1 does not apply to it. Its own imports stay two-dot (`from ..config import …`, `from . import LifecycleError`, `from .workspace import Layout`) exactly as written above. Move `add_config_argument`/`config_path_from`/`_report` out of `ai_rfc/lifecycle/init/cli.py` into it, and import them back there as `from ..common import add_config_argument, config_path_from, report` (renaming `_report` to `report`, which is what every other verb calls it).

- [ ] **Step 4: the `run` verb package**

Create `ai_rfc/lifecycle/run/{__init__.py,__main__.py}` per D1, then `ai_rfc/lifecycle/run/cli.py`:

```python
"""``ai-rfc run --config``: perform every deterministic stage that is next, then stop at the boundary."""

from __future__ import annotations

import argparse

from ... import __version__, ledger
from ...config import ConfigError
from ...pipeline.run import perform
from ...pipeline.stages import BY_NAME, STAGES, Performer, is_optional
from ...pipeline.state import State, state
from .. import LifecycleError
from ..common import add_config_argument, config_path_from, load_sealed, report

BOUNDARY = "mining"


def run_stages(config_path, *, until: str | None = None) -> int:
    """Walk the pipeline from what state says is pending up to the agent boundary.

    Args:
        config_path: The operator's ``recon.yaml``.
        until: Stop after this stage instead of at the boundary.

    Returns:
        0 when the boundary (or ``until``) was reached; the failing stage's exit code otherwise.
    """
    given, sealed, layout, noted = load_sealed(config_path)
    for line in noted:
        report(f"note: config drift: {line}")
    by_name = {entry.stage.name: entry for entry in state(layout)}
    if by_name["pin"].state is not State.DONE:
        raise LifecycleError(f"the clone is not pinned: {by_name['pin'].reason}; run: ai-rfc init --config {config_path}")
    performed: list[str] = []
    for stage in STAGES:
        if stage.performer is not Performer.DETERMINISTIC:
            if stage.name == BOUNDARY:
                break
            continue
        if stage.ordinal >= BY_NAME[BOUNDARY].ordinal:
            break
        if is_optional(stage):
            continue  # forge was acquired at init; build needs sessions first (CLI-2)
        entry = by_name[stage.name]
        if entry.state in (State.DONE, State.RECOMPUTED):
            continue
        result = perform(stage, layout)
        performed.append(stage.name)
        if not result.ok:
            report(f"error: {stage.name} exited {result.exit_code}")
            return result.exit_code
        report(f"performed: {stage.name}")
        if until == stage.name:
            report(f"stopped after {stage.name}")
            return 0
        by_name = {e.stage.name: e for e in state(layout)}
    if not performed:
        report("performed: nothing (every deterministic stage is current)")
    states = ledger.clusters(layout.root)
    summary = ledger.counts(states)
    nxt = ledger.next_cluster(layout.root)
    report(f"boundary: {BOUNDARY} — {BY_NAME[BOUNDARY].instruction}")
    report(f"clusters: {summary['done']} of {summary['in_window']} done, {summary['partial']} partial, {summary['outstanding']} outstanding")
    if nxt is not None:
        report(f"next cluster: {nxt.id} (ordinal {nxt.ordinal})")
    report("sessions: configured (ai-rfc run drives them once CLI-2 lands)" if given.sessions else "sessions: not configured (add a sessions: block to let ai-rfc run drive model sessions)")
    return 0


def configure(parser: argparse.ArgumentParser) -> None:
    """Arguments of ``ai-rfc run``."""
    parser.description = "Perform every deterministic stage that is next; stop at the agent boundary with the ledger printed."
    add_config_argument(parser)
    parser.add_argument("--until", choices=[s.name for s in STAGES if s.performer is Performer.DETERMINISTIC and s.ordinal < BY_NAME[BOUNDARY].ordinal and not is_optional(s)], default=None, help="Stop after this stage.")


def build_standalone_parser() -> argparse.ArgumentParser:
    """The parser ``python -m ai_rfc.lifecycle.run`` uses."""
    parser = argparse.ArgumentParser(prog="ai-rfc run")
    parser.add_argument("--version", action="version", version=f"ai-rfc run {__version__}")
    configure(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Perform the verb; 1 on a refusal or an unreadable input."""
    try:
        return run_stages(config_path_from(args), until=args.until)
    except (LifecycleError, ConfigError, OSError) as error:
        report(f"error: {error}")
        return 1


def main(argv: list[str] | None = None) -> int:
    """Command-line entry."""
    return run(build_standalone_parser().parse_args(argv))
```

(`state()` takes a `Workspace`; `Layout` is one. `is_optional` is SP7a Task 3's predicate; `OPTIONAL` is exactly `{"forge", "build"}` at `pipeline/stages.py:82`. The `until` choices are `history`, `timeline`, `views` — and the `and not is_optional(s)` clause above is what makes that true: `STAGES` holds twelve stages and `forge` is a fourth DETERMINISTIC stage at ordinal 2, before `mining` at ordinal 5. Without that clause argparse would offer `--until forge`, the walk would skip `forge` via `is_optional`, the `until == stage.name` test would never fire, and `run` would silently continue to the boundary instead of stopping. The walk itself is correct as written: `pin` is MANUAL at ordinal 0 and falls through the first branch, `forge` is skipped, and `mining` — the first AGENT stage — breaks the loop.)

- [ ] **Step 5: `status.py` and `verify.py`**

In `ai_rfc/pipeline/cli.py`, rename `_status_payload` → `status_payload` (`:122`) and `_print_status` → `print_status` (`:154`); both are private today with exactly two internal call sites, at `:388` and `:392`, and no references anywhere else in `ai_rfc/` or `tests/`. Then create the `status` and `verify` verb packages per D1 (`{__init__,__main__}.py` each) and write `ai_rfc/lifecycle/status/cli.py`:

```python
"""``ai-rfc status --config``: stages, ledger, init record and config drift in one view."""

from __future__ import annotations

import argparse
import json

from ... import __version__, ledger
from ...config import ConfigError, drift, load_config
from ...pipeline.cli import print_status, status_payload
from .. import LifecycleError
from ..common import add_config_argument, config_path_from, report
from ..workspace import Layout


def payload(config_path) -> dict:
    """Everything ``status`` prints, as one dict."""
    given = load_config(config_path)
    layout = Layout(given.workspace)
    if not layout.init_record.exists():
        raise LifecycleError(f"{layout.root} is not an initialised workspace; run: ai-rfc init --config {config_path}")
    sealed = load_config(layout.config)
    refused, noted = drift(sealed, given)
    states = ledger.clusters(layout.root)
    nxt = ledger.next_cluster(layout.root)
    body = status_payload(layout.root)
    body.update(
        {
            "ledger": ledger.counts(states),
            "partial": [{"id": s.id, "ordinal": s.ordinal, "reason": s.partial_reason} for s in states if s.partial_reason],
            "next_cluster": None if nxt is None else {"id": nxt.id, "ordinal": nxt.ordinal},
            "init": json.loads(layout.init_record.read_text()),
            "drift": {"refused": refused, "noted": noted},
            "sessions": given.sessions is not None,
        }
    )
    return body


def configure(parser: argparse.ArgumentParser) -> None:
    """Arguments of ``ai-rfc status``."""
    parser.description = "Where the reconstruction stands: stage states, the cluster ledger, the pin, config drift."
    add_config_argument(parser)
    parser.add_argument("--json", action="store_true", dest="as_json", help="Machine-readable output.")


def build_standalone_parser() -> argparse.ArgumentParser:
    """The parser ``python -m ai_rfc.lifecycle.status`` uses."""
    parser = argparse.ArgumentParser(prog="ai-rfc status")
    parser.add_argument("--version", action="version", version=f"ai-rfc status {__version__}")
    configure(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Print the status; 1 when the workspace or config cannot be read."""
    try:
        body = payload(config_path_from(args))
    except (LifecycleError, ConfigError, OSError, ledger.LedgerError) as error:
        report(f"error: {error}")
        return 1
    if args.as_json:
        print(json.dumps(body, indent=2, sort_keys=True))
        return 0
    print_status(body)
    counts = body["ledger"]
    print(f"clusters: {counts['done']} of {counts['in_window']} done, {counts['partial']} partial, {counts['outstanding']} outstanding")
    for entry in body["partial"]:
        print(f"  partial: {entry['id']} (ordinal {entry['ordinal']}): {entry['reason']}")
    nxt = body["next_cluster"]
    print(f"next: {nxt['id']} (ordinal {nxt['ordinal']})" if nxt else "next: every in-window cluster is done")
    print(f"pin: {body['init']['resolved_pin']}  forge: {body['init']['forge_snapshot'] or 'none'}")
    for line in body["drift"]["refused"]:
        print(f"drift (refused): {line}")
    for line in body["drift"]["noted"]:
        print(f"drift (noted): {line}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Command-line entry."""
    return run(build_standalone_parser().parse_args(argv))
```

`ai_rfc/lifecycle/verify/cli.py`:

```python
"""``ai-rfc verify --config``: every gate the workspace can pass, in one command."""

from __future__ import annotations

import argparse

from ... import __version__
from ...config import ConfigError, drift, load_config
from ...draft import cli as draft_cli
from ...pipeline.run import perform
from ...pipeline.stages import BY_NAME
from .. import LifecycleError
from ..common import add_config_argument, config_path_from, report
from ..workspace import Layout


def verify(config_path, *, strict: bool) -> int:
    """Run drift, strict check, strict gate, completeness, lint and build.

    Returns:
        0 clean; 3 findings (only under ``strict``); 1 when any check could not run.
    """
    given = load_config(config_path)
    layout = Layout(given.workspace)
    if not layout.init_record.exists():
        raise LifecycleError(f"{layout.root} is not an initialised workspace; run: ai-rfc init --config {config_path}")
    sealed = load_config(layout.config)
    refused, noted = drift(sealed, given)
    codes: list[int] = []
    if refused:
        report("drift: refused — " + "; ".join(refused))
        codes.append(3)
    else:
        report("drift: ok" + (f" ({len(noted)} noted)" if noted else ""))
    for name in ("check", "gate", "lint"):
        result = perform(BY_NAME[name], layout, strict=True)
        report(f"{name}: {'ok' if result.exit_code == 0 else 'findings' if result.exit_code == 3 else f'error ({result.exit_code})'}")
        codes.append(result.exit_code)
    completeness = draft_cli.main(["completeness", str(layout.root), "--out", str(layout.out), "--strict"])
    report(f"completeness: {'ok' if completeness == 0 else 'findings' if completeness == 3 else f'error ({completeness})'}")
    codes.append(completeness)
    if given.toolchain is not None and given.toolchain.exists():
        result = perform(BY_NAME["build"], layout, strict=True, toolchain=given.toolchain)
        report(f"build: {'ok' if result.exit_code == 0 else 'findings' if result.exit_code == 3 else f'error ({result.exit_code})'}")
        codes.append(result.exit_code)
    else:
        report("build: skipped (no toolchain record; see ai-rfc doctor)")
    if any(code not in (0, 3) for code in codes):
        return 1
    if 3 in codes:
        return 3 if strict else 0
    return 0


def configure(parser: argparse.ArgumentParser) -> None:
    """Arguments of ``ai-rfc verify``."""
    parser.description = "Config drift, strict manifest check, citation gate, completeness, lint and build, in one exit code."
    add_config_argument(parser)
    parser.add_argument("--strict", action="store_true", help="Exit 3 when any check reports findings.")


def build_standalone_parser() -> argparse.ArgumentParser:
    """The parser ``python -m ai_rfc.lifecycle.verify`` uses."""
    parser = argparse.ArgumentParser(prog="ai-rfc verify")
    parser.add_argument("--version", action="version", version=f"ai-rfc verify {__version__}")
    configure(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Perform the verb."""
    try:
        return verify(config_path_from(args), strict=args.strict)
    except (LifecycleError, ConfigError, OSError) as error:
        report(f"error: {error}")
        return 1


def main(argv: list[str] | None = None) -> int:
    """Command-line entry."""
    return run(build_standalone_parser().parse_args(argv))
```

(`perform(..., strict=True)` passes `--strict` to check, gate and lint through their builders; `lint` and `build` are SP7a Task 3's stages; `perform`'s `toolchain=` keyword is SP7a Task 3's addition. The `gate` builder needs `revisions.yaml`, `questions.yaml`, checkpoints and the draft — all present after `init`, so a fresh workspace gates clean; completeness reports every cluster unprocessed, which is the finding the test expects.) Register the three `EntryPoint` rows (`run`, `status`, `verify`; module `f"{PACKAGE}.lifecycle.<verb>.cli"` per D1; prog `ai-rfc <verb>`; section `LIFECYCLE`; summaries "Perform every deterministic stage that is next, then stop at the agent boundary", "Where the reconstruction stands", "Every gate in one exit code"), inserted **immediately after the `init` row** so the LIFECYCLE block stays contiguous.

- [ ] **Step 6: Run the suites**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli tests/substrate/pipeline -n auto`
Expected: all PASS. If `test_run_performs_the_deterministic_stages_and_stops_at_mining` fails on `views`, the `views` builder needs the forge snapshot only when one exists — check `pipeline/run._views` handles `latest_forge_snapshot() is None`.

- [ ] **Step 7: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc tests && $PY -m flake8 --max-line-length=88 ai_rfc/lifecycle ai_rfc/pipeline/cli.py tests/cli && $PY -m mypy --follow-imports=silent ai_rfc/lifecycle
git status --short
git add ai_rfc/lifecycle/common.py ai_rfc/lifecycle/run/__init__.py ai_rfc/lifecycle/run/__main__.py ai_rfc/lifecycle/run/cli.py ai_rfc/lifecycle/status/__init__.py ai_rfc/lifecycle/status/__main__.py ai_rfc/lifecycle/status/cli.py ai_rfc/lifecycle/verify/__init__.py ai_rfc/lifecycle/verify/__main__.py ai_rfc/lifecycle/verify/cli.py ai_rfc/lifecycle/init/cli.py ai_rfc/pipeline/cli.py ai_rfc/entrypoints.py tests/conftest.py tests/cli/test_init.py tests/cli/test_run.py tests/cli/test_status_verify.py
git commit -m "feat: run, status and verify a reconstruction from one config"
```

---

### Task 6: `ai-rfc doctor` and `ai-rfc toolchain provision|verify` — the environment, checked once

**Files:**
- Move: `ai_rfc/experiment/toolchain.py` → `ai_rfc/toolchain.py`; `ai_rfc/experiment/profile.py` → `ai_rfc/lifecycle/profile.py` (flat — not a verb); `tests/experiment/test_toolchain.py` → `tests/cli/test_toolchain.py`; `tests/experiment/test_profile.py` → `tests/cli/test_profile.py` (orphaned by the `profile.py` move — it imports all three names from `ai_rfc.experiment.profile` at `:5`)
- Create: `ai_rfc/lifecycle/{toolchain,doctor}/{__init__,__main__,cli}.py` (verb packages, D1)
- Modify: `ai_rfc/experiment/{config,cli,preflight,paths}.py` (imports; the `toolchain` command leaves `experiment`), `ai_rfc/experiment/optimize/claude_cli.py` (**imports `profile_env` — see Step 1; the original grep does not find it**), `ai_rfc/config.py` (gains `profile_dir`/`default_root`), `ai_rfc/entrypoints.py` (rows `toolchain`, `doctor`, inserted after `verify`)
- Modify (test patch sites that bind the moved module by object — all six must be re-pointed or they silently stop patching): `tests/experiment/conftest.py`, `tests/experiment/test_config.py`, `tests/experiment/test_cli_optimize.py`
- Test: `tests/cli/test_doctor.py` (new)

**Interfaces:**
- Consumes: `ai_rfc.toolchain.{provision, verify, RECORD_FILE, TOOLS_DIR}` (SP7a Task 5, moved); `ai_rfc.lifecycle.profile.{init_profile, login_command, profile_env}` (moved from `experiment/profile.py`); `ai_rfc.config.{load_config, experiments_root, profile_dir}`; `ai_rfc.draft.build.load_toolchain`.
- **Corrected contract for the moved `profile` module.** It defines exactly three public functions: `login_command(root: Path) -> str` (`:19`), `init_profile(root: Path) -> Path` (`:24`) and **`profile_env(profile: Path) -> dict[str, str]`** (`:41`). `profile_env` is a GEPA-NO-KEY addition that postdates this plan; it is public, it is load-bearing, and it must survive the move. `profile_dir` is **not** defined here — it lives in `experiment/paths.py:16` and this task moves it into `ai_rfc/config.py`. Note the asymmetry that Step 5 depends on: `init_profile` and `login_command` both take the **experiments root** and derive `root / "profile"` themselves; only `profile_env` takes the profile directory itself.
- The module has **four** importers, all of which must keep working: `ai_rfc/experiment/cli.py:18`, `ai_rfc/experiment/preflight.py:26`, `ai_rfc/experiment/optimize/claude_cli.py:20`, and `tests/experiment/test_profile.py:5` (moved by this task).
- Produces: verbs `ai-rfc toolchain provision [--root] [--template] [--template-commit]` and `ai-rfc toolchain verify [--root|--record PATH]`; `ai-rfc doctor [--config PATH] [--json]`; `doctor.checks(config: ReconConfig | None) -> list[Check]` with `Check(name, ok, severity: "error"|"warning"|"info", detail, fix)`. CLI-2's `run` calls `doctor.checks` before launching sessions; Task 7 documents both.

**Why this shape.** Every environment failure the pilot met was discovered mid-run (missing `USER`, an unmounted MCP server, a toolchain that was never installed). `doctor` asks each question once, names the fix, and exits non-zero only for what a run cannot survive. Moving `toolchain.py` and `profile.py` out of `experiment/` is the first step of the D58 split: production needs both; the instrument imports them back.

- [ ] **Step 1: Move the modules and re-point the imports**

Run each move as its own plain command with literal paths — the worktree guard refuses git inside compound (`&&`-chained) commands:

```bash
git mv ai_rfc/experiment/toolchain.py ai_rfc/toolchain.py
git mv ai_rfc/experiment/profile.py ai_rfc/lifecycle/profile.py
git mv tests/experiment/test_toolchain.py tests/cli/test_toolchain.py
git mv tests/experiment/test_profile.py tests/cli/test_profile.py
```

**The discovery grep in the original plan is defective and must not be used as written.** Measured against the landed tree, its pattern returns for `ai_rfc/experiment/optimize/claude_cli.py` **only line 5 — a docstring sentence**, matched because the `.` in `experiment.profile` matches a space. Line 20, the real `from ..profile import profile_env`, scores zero. An implementer following the original grep sees a hit for the file, opens line 5, finds prose, and moves on — and the GEPA-NO-KEY proposer breaks silently. Use this instead:

```bash
grep -rn "experiment\.toolchain\|from \.toolchain\|from \. import toolchain\|experiment\.profile\|from \.profile\|from \.\.profile\|profile_env\|from \.paths import profile_dir\|default_root" ai_rfc tests plugins docs
```

Do not rely on the grep alone. These are the complete, measured lists; every one must be rewritten.

**Importers of `experiment.profile` (4).** `ai_rfc/experiment/cli.py:18` (`from .profile import init_profile, login_command`) → `from ..lifecycle.profile import init_profile, login_command`; `ai_rfc/experiment/preflight.py:26` (`from .profile import profile_env`) → `from ..lifecycle.profile import profile_env`; **`ai_rfc/experiment/optimize/claude_cli.py:20`** (`from ..profile import profile_env`, used at `:179`) → `from ...lifecycle.profile import profile_env`; `tests/cli/test_profile.py:5` (after the move) → `from ai_rfc.lifecycle.profile import init_profile, login_command, profile_env`.

**Importers of `experiment.toolchain` (8), and the patch-site trap.** `ai_rfc/experiment/config.py:23` (`from . import toolchain as toolchain_module`) → `from .. import toolchain as toolchain_module`; `ai_rfc/experiment/cli.py:472, :1060, :1067` (`from .toolchain import …`) → `from ..toolchain import …`, and delete the `toolchain` command block there — Step 4 re-homes it. Then the trap: **six sites bind the module object and monkeypatch `verify` on it** — `tests/experiment/conftest.py:178`, `tests/experiment/test_config.py:152, :172, :389`, `tests/experiment/test_cli_optimize.py:703`, and `tests/cli/test_toolchain.py:175` (after the move). If they keep patching `ai_rfc.experiment.toolchain` while `config.py` binds `ai_rfc.toolchain`, the patches become invisible and those tests silently run the **real** `verify`, which builds drafts. Re-point every one to `ai_rfc.toolchain`. In `tests/cli/test_toolchain.py` the direct symbol import at `:11-19` also becomes `from ai_rfc.toolchain import …`.

**The layering fix (do not skip — it is the reason the move exists).** `toolchain.py` reaches back into the instrument twice today: `:23` `from . import ExperimentError` and `:24` `from .workspace import TEMPLATE_COMMIT, TEMPLATE_URL, _git, _run_git`. Left alone, a top-level `ai_rfc/toolchain.py` would import `ai_rfc.experiment`, inverting the dependency the move is meant to remove (`experiment/__init__.py:6`: "Nothing here is imported by the plugin or the substrate"). Both are already solved by Task 4, which moved `TEMPLATE_URL`, `TEMPLATE_COMMIT`, `_run_git` and `_git` into `ai_rfc/lifecycle/workspace.py`. So rewrite `:24` to `from .lifecycle.workspace import TEMPLATE_COMMIT, TEMPLATE_URL, _git, _run_git` (production → production, no cycle: `lifecycle/workspace.py` does not import `toolchain`).

**The error type (ruling D2, replacing the original plan's self-contradictory note).** Define `class ToolchainError(RuntimeError)` in `ai_rfc/toolchain.py` and replace the eleven `ExperimentError` raises (`:97, :169, :172, :176, :201, :208, :212, :220, :274, :281, :289`) with it, deleting the `from . import ExperimentError` at `:23`. Four consequences, all of which must land in the same commit or the suite goes red:

1. `ai_rfc/toolchain.py:349`'s internal `except (OSError, ExperimentError)` inside `verify` becomes `except (OSError, ToolchainError, LifecycleError)`, or it raises `NameError` the first time it fires.
2. `provision` calls `_git`/`_run_git`, which raise `LifecycleError` after Task 4's move, so `ExperimentError` would otherwise still leak out of a "pure" `ToolchainError` function. Wrap those calls and re-raise as `ToolchainError`.
3. `ai_rfc/experiment/cli.py:1290`'s `except (ExperimentError, OSError)` — the only handler that actually guards the `provision` call site at `:1060` — must gain `ToolchainError`.
4. `tests/cli/test_toolchain.py:115` and `:183` assert `pytest.raises(ExperimentError)`; both become `ToolchainError`. This task owns that file, so the change is in scope.

The original plan justified the rename by saying "`experiment/config.py`'s `init_campaign` catches it the same way". **That premise is false and must not be relied on**: `init_campaign` calls `verify`, not `provision` (`config.py:295`), and `config.py` contains no `except ExperimentError` at all — its only handler is `except OSError` at `:232`. `verify` returns `(ok, reasons)` and raises nothing, so `config.py` needs no change beyond its import.

**`profile_dir` and `default_root`.** Move both from `experiment/paths.py` into `ai_rfc/config.py` beside `experiments_root()`, keeping `profile_dir(root) -> root / "profile"` and `default_root()` byte-identical in behaviour, and reduce `experiment/paths.py` to the re-export `from ..config import experiments_root as default_root, profile_dir`. The five real importers keep working unchanged: `ai_rfc/experiment/profile.py:8`, `ai_rfc/experiment/config.py:25`, `ai_rfc/experiment/preflight.py:26`, `ai_rfc/experiment/cli.py:17`, `tests/cli/test_profile.py:4` (after the move). The moved `lifecycle/profile.py` must import from `ai_rfc.config`, never from `experiment/paths.py` — that would be the production→instrument import this step exists to remove.

Run each, separately, and expect all to pass — this is a move plus an error-type change, not a behaviour change:

```bash
SSLKEYLOGFILE= $PY -m pytest tests/cli/test_toolchain.py tests/cli/test_profile.py -v
SSLKEYLOGFILE= $PY -m pytest tests/experiment -n auto
```

Then prove the patch sites still bite, because a silently-dead monkeypatch is the one failure this step can hide: `grep -rn "toolchain_module\|ai_rfc.experiment.toolchain" tests/` must return zero references to the old path.

- [ ] **Step 2: Write the failing doctor tests**

Create `tests/cli/test_doctor.py`:

```python
"""`ai-rfc doctor`: each environment question asked once, each failure named with its fix."""

import json
import stat
from pathlib import Path

import pytest

from ai_rfc import cli, toolchain
from ai_rfc.lifecycle.doctor import cli as doctor  # the verb's cli module, per D1


def _fake_claude(tmp_path: Path) -> Path:
    binary = tmp_path / "bin" / "claude"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\necho '2.1.258 (Claude Code)'\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary


def _config(tmp_path: Path, extra: str = "") -> Path:
    path = tmp_path / "recon.yaml"
    path.write_text(
        "name: fixture\n"
        f"workspace: {tmp_path / 'ws'}\n"
        "source:\n  repo: https://github.com/example/project\n  pin: main\n"
        "draft:\n  name: draft-test-fixture\n"
        + extra
    )
    return path


def test_doctor_reports_a_missing_claude_binary_as_an_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AI_RFC_EXPERIMENTS_ROOT", str(tmp_path / "root"))
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert cli.main(["doctor", "--config", str(_config(tmp_path))]) == 1
    out = capsys.readouterr().out
    assert "claude: error" in out and "not found on PATH" in out


def test_doctor_passes_with_a_binary_a_profile_and_a_verified_toolchain(tmp_path, monkeypatch, capsys):
    root = tmp_path / "root"
    monkeypatch.setenv("AI_RFC_EXPERIMENTS_ROOT", str(root))
    monkeypatch.setenv("PATH", str(_fake_claude(tmp_path).parent))
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    record = root / "tools" / "toolchain.json"
    record.parent.mkdir(parents=True)
    record.write_text("{}")
    monkeypatch.setattr(toolchain, "verify", lambda record, runner=None: (True, ()))
    assert cli.main(["doctor", "--config", str(_config(tmp_path)), "--json"]) == 0
    checks = {c["name"]: c for c in json.loads(capsys.readouterr().out)["checks"]}
    assert checks["claude"]["ok"] and "2.1.258" in checks["claude"]["detail"]
    assert checks["profile"]["ok"] and (root / "profile").is_dir()
    assert checks["toolchain"]["ok"]
    assert checks["token"]["ok"] and checks["deps"]["ok"]


def test_doctor_warns_about_a_claude_md_ancestor_and_a_missing_token(tmp_path, monkeypatch, capsys):
    root = tmp_path / "root"
    monkeypatch.setenv("AI_RFC_EXPERIMENTS_ROOT", str(root))
    monkeypatch.setenv("PATH", str(_fake_claude(tmp_path).parent))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    (tmp_path / "CLAUDE.md").write_text("project notes\n")
    assert cli.main(["doctor", "--config", str(_config(tmp_path)), "--json"]) == 0
    checks = {c["name"]: c for c in json.loads(capsys.readouterr().out)["checks"]}
    assert checks["workspace"]["severity"] == "warning" and "CLAUDE.md" in checks["workspace"]["detail"]
    assert checks["token"]["severity"] == "warning" and "GITHUB_TOKEN" in checks["token"]["detail"]
    assert checks["toolchain"]["severity"] == "warning" and "toolchain provision" in checks["toolchain"]["fix"]


def test_doctor_fails_when_a_present_toolchain_record_does_not_verify(tmp_path, monkeypatch, capsys):
    root = tmp_path / "root"
    monkeypatch.setenv("AI_RFC_EXPERIMENTS_ROOT", str(root))
    monkeypatch.setenv("PATH", str(_fake_claude(tmp_path).parent))
    record = root / "tools" / "toolchain.json"
    record.parent.mkdir(parents=True)
    record.write_text("{}")
    monkeypatch.setattr(toolchain, "verify", lambda record, runner=None: (False, ("refcache contents differ from the recorded digest",)))
    assert cli.main(["doctor"]) == 1
    assert "refcache contents differ" in capsys.readouterr().out


def test_toolchain_verbs_are_mounted_on_the_root(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["toolchain", "--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "provision" in out and "verify" in out
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli/test_doctor.py -v`
Expected: FAIL (`invalid choice: 'doctor'`, `invalid choice: 'toolchain'`).

- [ ] **Step 4: the `toolchain` verb package**

Create `ai_rfc/lifecycle/toolchain/{__init__.py,__main__.py}` per D1, then `ai_rfc/lifecycle/toolchain/cli.py`. Note that it imports `ToolchainError` from the moved production module and **not** `ExperimentError` from the instrument — that is ruling D2 in Step 1:

```python
"""``ai-rfc toolchain provision|verify``: the shared Internet-Draft toolchain, once per machine."""

from __future__ import annotations

import argparse
from pathlib import Path

from ... import __version__
from ...config import experiments_root
from ...toolchain import RECORD_FILE, TOOLS_DIR, ToolchainError, provision, verify
from ..common import report
from ..workspace import TEMPLATE_COMMIT, TEMPLATE_URL


def configure(parser: argparse.ArgumentParser) -> None:
    """Add the ``provision`` and ``verify`` verbs."""
    parser.description = "Install once (networked) or re-check offline the template toolchain every build uses."
    verbs = parser.add_subparsers(dest="verb", required=True)
    prov = verbs.add_parser("provision", help="Install it once (networked).")
    prov.add_argument("--root", type=Path, default=None, help="Experiments root (default: $AI_RFC_EXPERIMENTS_ROOT or ~/ai-rfc-experiments).")
    prov.add_argument("--template", default=TEMPLATE_URL, help="Template repository (default: %(default)s).")
    prov.add_argument("--template-commit", default=TEMPLATE_COMMIT, help="Commit to pin (default: %(default)s).")
    ver = verbs.add_parser("verify", help="Re-check it offline.")
    ver.add_argument("--root", type=Path, default=None, help="Experiments root holding tools/toolchain.json.")
    ver.add_argument("--record", type=Path, default=None, help="A toolchain.json elsewhere.")


def build_standalone_parser() -> argparse.ArgumentParser:
    """The parser ``python -m ai_rfc.lifecycle.toolchain_cmd`` uses."""
    parser = argparse.ArgumentParser(prog="ai-rfc toolchain")
    parser.add_argument("--version", action="version", version=f"ai-rfc toolchain {__version__}")
    configure(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Perform the verb; ``verify`` exits 1 with one reason per line when it fails."""
    root = args.root or experiments_root()
    if args.verb == "provision":
        try:
            record = provision(root, template=args.template, template_commit=args.template_commit)
        except ToolchainError as error:
            report(f"error: {error}")
            return 1
        print(f"toolchain: {record}")
        return 0
    record = args.record or root / TOOLS_DIR / RECORD_FILE
    ok, reasons = verify(record)
    if ok:
        print("ok")
        return 0
    for reason in reasons:
        report(f"toolchain: {reason}")
    return 1


def main(argv: list[str] | None = None) -> int:
    """Command-line entry."""
    return run(build_standalone_parser().parse_args(argv))
```

(`provision` raises `ExperimentError` today only because it was written under `experiment/`. Ruling D2 in Step 1 defines `ToolchainError` in the moved module and lists the four call sites that must change with it. Do not leave a production module raising the instrument's error type, and do not import `ExperimentError` here — the original plan's code block did both, and its stated justification about `init_campaign` was factually wrong.)

Also note `build_standalone_parser`'s docstring becomes ``` ``python -m ai_rfc.lifecycle.toolchain`` ```.

- [ ] **Step 5: the `doctor` verb package**

Create `ai_rfc/lifecycle/doctor/{__init__.py,__main__.py}` per D1, then `ai_rfc/lifecycle/doctor/cli.py`:

```python
"""``ai-rfc doctor``: every environment question a run would otherwise fail on, asked once."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from ... import __version__, toolchain
from ...config import ConfigError, ReconConfig, experiments_root, load_config, profile_dir
from ...toolchain import RECORD_FILE, TOOLS_DIR
from ..common import CONFIG_ENV, report
from ..profile import init_profile, login_command


@dataclass(frozen=True)
class Check:
    """One question and its answer."""

    name: str
    ok: bool
    severity: str  # "error" fails doctor; "warning" and "info" do not
    detail: str
    fix: str = ""


def _claude(config: ReconConfig | None) -> Check:
    name = config.sessions.claude if config and config.sessions else "claude"
    resolved = shutil.which(name)
    if resolved is None:
        return Check("claude", False, "error", f"{name!r} not found on PATH", "install Claude Code or set sessions.claude to its absolute path")
    try:
        version = subprocess.run([resolved, "--version"], capture_output=True, text=True, timeout=30)
        text = (version.stdout or version.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return Check("claude", False, "error", f"{resolved}: {error}", "reinstall Claude Code")
    return Check("claude", True, "info", f"{resolved}: {text}")


def _profile(config: ReconConfig | None) -> Check:
    """The isolated Claude Code profile sessions launch against.

    ``init_profile`` and ``login_command`` both take the experiments ROOT and
    derive ``root / "profile"`` themselves, so a configured profile is only
    expressible when it is named ``profile`` inside its parent.
    """
    configured = config.sessions.profile if config and config.sessions and config.sessions.profile else None
    directory = configured or profile_dir(experiments_root())
    if directory.name != "profile":
        return Check(
            "profile",
            False,
            "warning",
            f"sessions.profile is {directory}; init_profile derives <root>/profile, so this path is not created for you",
            f"name it 'profile' under its parent ({directory.parent / 'profile'}), or create the directory yourself",
        )
    root = directory.parent
    created = not directory.exists()
    init_profile(root)
    detail = f"{directory} ({'created' if created else 'present'}); log in once with: {login_command(root)}"
    return Check("profile", True, "info", detail)


def _toolchain(config: ReconConfig | None) -> Check:
    record = config.toolchain if config and config.toolchain else experiments_root() / TOOLS_DIR / RECORD_FILE
    if not record.exists():
        return Check("toolchain", False, "warning", f"no record at {record}; draft builds will be skipped", "ai-rfc toolchain provision")
    ok, reasons = toolchain.verify(record)
    if ok:
        return Check("toolchain", True, "info", f"{record} verifies")
    return Check("toolchain", False, "error", "; ".join(reasons), "ai-rfc toolchain provision into a fresh root, or repair the recorded paths")


def _token(config: ReconConfig | None) -> Check:
    if config is None or config.source.host == "none" or not config.source.token_env:
        return Check("token", True, "info", "no forge token needed")
    if os.environ.get(config.source.token_env):
        return Check("token", True, "info", f"{config.source.token_env} is set")
    return Check("token", False, "warning", f"{config.source.token_env} is not set; the forge is fetched anonymously at lower fidelity", f"export {config.source.token_env}=…")


def _deps() -> Check:
    missing = []
    for module in ("yaml", "mcp"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        return Check("deps", False, "error", "missing: " + ", ".join(missing), "pip install -e $AIRFC")
    return Check("deps", True, "info", "yaml, mcp importable")


def _workspace(config: ReconConfig | None) -> Check:
    if config is None:
        return Check("workspace", True, "info", "no config given; workspace not checked")
    for ancestor in (config.workspace, *config.workspace.parents):
        if (ancestor / "CLAUDE.md").exists() or (ancestor / ".claude").is_dir():
            return Check("workspace", False, "warning", f"{ancestor} holds a CLAUDE.md or .claude/; sessions run with project settings from the workspace and would load it", "move the workspace outside every CLAUDE.md ancestry (the experiments root exists for this)")
    return Check("workspace", True, "info", f"{config.workspace} has no CLAUDE.md ancestor")


def checks(config: ReconConfig | None) -> list[Check]:
    """Every check, in the order they are printed."""
    return [_claude(config), _profile(config), _toolchain(config), _token(config), _deps(), _workspace(config)]


def configure(parser: argparse.ArgumentParser) -> None:
    """Arguments of ``ai-rfc doctor``."""
    parser.description = "Check the environment a reconstruction runs in; exit 1 only for what a run cannot survive."
    parser.add_argument("--config", type=Path, default=None, help=f"recon.yaml to check against (default: ${CONFIG_ENV}, else generic checks).")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Machine-readable output.")


def build_standalone_parser() -> argparse.ArgumentParser:
    """The parser ``python -m ai_rfc.lifecycle.doctor`` uses."""
    parser = argparse.ArgumentParser(prog="ai-rfc doctor")
    parser.add_argument("--version", action="version", version=f"ai-rfc doctor {__version__}")
    configure(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Print every check; 1 when any error-severity check failed."""
    config = None
    config_path = args.config or (Path(os.environ[CONFIG_ENV]) if os.environ.get(CONFIG_ENV) else None)
    if config_path is not None:
        try:
            config = load_config(config_path)
        except ConfigError as error:
            report(f"error: {error}")
            return 1
    results = checks(config)
    if args.as_json:
        print(json.dumps({"checks": [asdict(c) for c in results]}, indent=2))
    else:
        for check in results:
            status = "ok" if check.ok else check.severity
            line = f"{check.name}: {status} — {check.detail}"
            if check.fix and not check.ok:
                line += f" (fix: {check.fix})"
            print(line)
    return 1 if any(not c.ok and c.severity == "error" for c in results) else 0


def main(argv: list[str] | None = None) -> int:
    """Command-line entry."""
    return run(build_standalone_parser().parse_args(argv))
```

(Measured contract, which the original `_profile` got wrong in two ways: `profile_dir(root)` returns `root / "profile"` (`paths.py:16-18`), and **both** `init_profile(root)` (`profile.py:24`) and `login_command(root)` (`:19`) take the experiments **root**, deriving the profile directory themselves. The original code passed `directory.parent` conditionally to one and unconditionally to the other, so the two disagreed whenever the profile directory was passed directly — printing a wrong `CLAUDE_CONFIG_DIR` in user-facing login instructions. Do **not** change the signatures in Step 1; the move is a move. The test's `(root / "profile").is_dir()` stays true because the default path is unchanged.)

Register `EntryPoint("toolchain", "ai-rfc toolchain", f"{PACKAGE}.lifecycle.toolchain.cli", "Install (once, networked) or verify (offline) the Internet-Draft toolchain", LIFECYCLE)` and `EntryPoint("doctor", "ai-rfc doctor", f"{PACKAGE}.lifecycle.doctor.cli", "Check the environment a reconstruction runs in", LIFECYCLE)`, both **immediately after the `verify` row** so the LIFECYCLE block stays contiguous. With these two the section holds all seven lifecycle verbs and `ENTRY_POINTS` is complete for CLI-1.

- [ ] **Step 6: Run the suites**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/cli tests/experiment -n auto`
Expected: all PASS, including the moved toolchain tests and `test_help_lists_every_registered_verb_once_under_its_section` with the two new rows.

- [ ] **Step 7: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc tests && $PY -m flake8 --max-line-length=88 ai_rfc/lifecycle ai_rfc/toolchain.py ai_rfc/config.py tests/cli && $PY -m mypy --follow-imports=silent ai_rfc/lifecycle ai_rfc/toolchain.py
git status --short
git add ai_rfc/toolchain.py ai_rfc/lifecycle/profile.py ai_rfc/lifecycle/toolchain/__init__.py ai_rfc/lifecycle/toolchain/__main__.py ai_rfc/lifecycle/toolchain/cli.py ai_rfc/lifecycle/doctor/__init__.py ai_rfc/lifecycle/doctor/__main__.py ai_rfc/lifecycle/doctor/cli.py ai_rfc/config.py ai_rfc/entrypoints.py ai_rfc/experiment/config.py ai_rfc/experiment/cli.py ai_rfc/experiment/preflight.py ai_rfc/experiment/paths.py ai_rfc/experiment/optimize/claude_cli.py tests/cli/test_toolchain.py tests/cli/test_profile.py tests/cli/test_doctor.py tests/experiment/conftest.py tests/experiment/test_config.py tests/experiment/test_cli_optimize.py
git commit -m "feat: doctor and toolchain verbs check the environment once, before any run"
```

---

### Task 7: The `panther ai-rfc` passthrough, the documentation, and the gate on MARK

**Files:**
- Modify: `$PANTHER/panther/cli/commands/ai_rfc.py` (only if SP1 left anything but a passthrough), `$PANTHER/tests/unit/test_cli/test_ai_rfc_commands.py`, `$AIRFC/README.md`, `$AIRFC/ai_rfc/README.md`, `$AIRFC/docs/experiment-protocol.md`, `$AIRFC/docs/parity.md` (one sentence)
- Create: `$AIRFC/docs/experiments/2026-09-03-cli1-mark-gate.md`

**Interfaces:**
- Consumes: everything above; SP1's passthrough `ai_rfc.cli.main`.
- Produces: the CLI-1 gate record the spec's sub-project table names; documentation that shows the one-door flow first and the leaf programs second.

- [ ] **Step 1: Pin the passthrough**

**Measured 2026-09-08: this step's edit is already done and should be a no-op.** `$PANTHER/panther/cli/commands/ai_rfc.py` is already 38 lines — one `@click.command` with `ignore_unknown_options=True`, `add_help_option=False`, a single `click.UNPROCESSED` varargs argument, `import sys` at `:16`, a lazy `from ai_rfc.cli import main` at `:31` and `sys.exit(main(list(args)))` at `:38`. `ENTRY_POINTS` has zero hits anywhere under `panther/` outside the submodule. Read the file and confirm; if it matches the shape below, change nothing and say so in the task report. The block is kept only as the specification of what it must remain:

```python
@click.command(
    name="ai-rfc",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True, "help_option_names": []},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def ai_rfc(args: tuple[str, ...]) -> None:
    """Reconstruct a specification from a repository's history (forwards to ``ai-rfc``)."""
    from ai_rfc.cli import main

    sys.exit(main(list(args)))
```

Add to `$PANTHER/tests/unit/test_cli/test_ai_rfc_commands.py`:

```python
def test_panther_ai_rfc_help_is_the_root_help():
    """`panther ai-rfc --help` is `ai-rfc --help`, forwarded untouched."""
    result = CliRunner().invoke(cli, ["ai-rfc", "--help"])
    assert result.exit_code == 0
    assert "Lifecycle" in result.output
    assert "init" in result.output and "run" in result.output
```

**Measured facts about that test module, because the original plan named three things that do not exist in it.** `$PANTHER/tests/unit/test_cli/test_ai_rfc_commands.py` is 57 lines with 5 tests and **zero fixtures**: `test_the_door_reaches_the_panther_cli:16`, `test_help_is_the_tools_own:21`, `test_a_malformed_invocation_still_exits_two:27`, `test_an_unreadable_manifest_exits_one:32`, `test_a_strict_finding_exits_three:41`. There is **no `cli_runner` fixture** in scope (`tests/unit/conftest.py` does not exist, and the two `cli_runner` definitions elsewhere in the repo are not ancestors of this path), **no `capsys_output_of` helper** anywhere under `tests/`, and **no import named `panther_cli`**. The module constructs `CliRunner()` inline and imports `from panther.cli.commands.ai_rfc import ai_rfc` at `:10` and `from panther.cli.core.main import cli` at `:11`. Follow that existing style, as the snippet above does. Run: `cd $PANTHER && SSLKEYLOGFILE= $PY -m pytest tests/unit/test_cli/test_ai_rfc_commands.py -v` — Expected: 6 passed (the 5 existing plus this one). Sandbox OFF: this module's collection binds a socket through `nicegui` and fails under the sandbox with `PermissionError: [Errno 1] Operation not permitted`.

- [ ] **Step 2: Documentation**

`$AIRFC/README.md`: **re-anchored 2026-09-08 — the original instruction named a table and a row that do not exist.** `## Environment contract` is a heading at `:38`, but its body at `:40-58` is **prose, not a table** (the file's only tables are at `:62-66` and `:78-84`), and `PANTHER_REPO` appears **nowhere** in the file — it is already a retired variable, and `tests/server/test_plugin_manifest.py:15-22` actively asserts its absence from command documentation. There is therefore nothing to replace, and this is consistent with ruling R3, which leaves `PANTHER_REPO`'s retirement to CLI-3. Instead: **add** `AI_RFC_CONFIG` to that prose ("the `recon.yaml` every lifecycle verb reads; `--config` overrides it"), and extend the existing `AI_RFC_WORKSPACE` sentence at `:42` with "read by the MCP server and the agent verbs until CLI-3 derives it from the config". Do not introduce a `PANTHER_REPO` row: adding one would document a retired variable and could trip that manifest test. replace the "Install"/"Experiment harness" opening with the six-line operator flow from the spec §1 (`config example`, `doctor`, `init`, `run`, `status`, `verify`), state that `run` stops at the agent boundary until CLI-2 lands, and move the campaign commands under a heading "The experiment instrument" that starts with `python -m ai_rfc.experiment workspace prepare --config recon.yaml`. `$AIRFC/ai_rfc/README.md`: the command table is at `:108-121`, columns `Command | Purpose`, 12 rows of `ai-rfc <verb>` substrate commands; note it sits under the `## The pipeline/ subpackage` heading (`:93`), not under `## CLI` (`:123`, which holds only a code block and the exit-code table at `:146-151`) — re-measure before editing. In that table add the lifecycle rows (`ai-rfc config example|reference`, `ai-rfc init --config`, `ai-rfc run --config [--until]`, `ai-rfc status --config [--json]`, `ai-rfc verify --config [--strict]`, `ai-rfc doctor [--config]`, `ai-rfc toolchain provision|verify`) above the stage rows, and rewrite "How to use" so the config-driven flow is the primary one and the explicit-path verbs are described as what `run` performs (their retirement from the operator's help is CLI-3). `docs/experiment-protocol.md`: a dated subsection "2026-09-03 — CLI-1" stating that pristines are now prepared from a config (`Target` retired), that progress is read by one ledger with the strict definition (checkpoint + entry + tag), and that `experiment toolchain` moved to `ai-rfc toolchain`. `docs/parity.md`: **re-anchored 2026-09-08 (ruling R4)** — SP7b grew this file by 19 lines in exactly the two regions a parity note would live, so "under the table" is now ambiguous. The file is 75 lines: title `:1`, framing prose `:3-11`, the main tool table `:13-34` (header `:13`, separator `:14`, 20 rows ending at `:34`), the arm-C freeze paragraph `:36-42`, `## Exit codes` `:44` with its table `:50-55`, then prose to `:75`. Insert the sentence **immediately after line 34**, before the arm-C paragraph — not after `:42`: "The `ai_rfc` verbs are unchanged by CLI-1; CLI-3 folds them into `ai-rfc`." Re-measure the line numbers before editing; another row may have moved them again.

- [ ] **Step 3: The gate — MARK through the one door**

On a scratch experiments root so nothing touches the real one (network once, sandbox off):

```bash
export AI_RFC_EXPERIMENTS_ROOT=/tmp/claude/one-door
mkdir -p $AI_RFC_EXPERIMENTS_ROOT && cd $AIRFC
cat > /tmp/claude/one-door/mark.yaml <<'EOF'
name: mark
source:
  repo: https://gitlab.cylab.be/cylab/mark
  host: gitlab
  pin: b901f36095d746ee99dfa85b3d2ad1fbe5f2c533
draft:
  name: draft-elniak-mark-reconstructed
  title: "MARK: A Reconstructed Specification"
  abbrev: "MARK Reconstructed"
  rfc_id: MARK-RECON-1
references: [RFC9110, RFC8259]
toolchain: /Users/elniak/ai-rfc-experiments/tools/toolchain.json
EOF
SSLKEYLOGFILE= $PY -m ai_rfc doctor --config /tmp/claude/one-door/mark.yaml
SSLKEYLOGFILE= $PY -m ai_rfc init --config /tmp/claude/one-door/mark.yaml
SSLKEYLOGFILE= $PY -m ai_rfc run --config /tmp/claude/one-door/mark.yaml
SSLKEYLOGFILE= $PY -m ai_rfc status --config /tmp/claude/one-door/mark.yaml
SSLKEYLOGFILE= $PY -m ai_rfc verify --config /tmp/claude/one-door/mark.yaml --strict; echo "verify exit: $?"
```

Expected: `doctor` exits 0 (claude found, profile present, toolchain verifies, `GITLAB_TOKEN` warning, no CLAUDE.md ancestor); `init` prints the workspace and the next command, and `init.json` records `resolved_pin: b901f360…` and a `forge_snapshot`; `run` performs `history`, `timeline` (69 clusters, 37 pr / 32 epoch — the same ids as the pristine `mark-w01-69`, which `diff <(cut …)` of the two `clusters.jsonl` files confirms), `views`, then prints `boundary: mining`, `clusters: 0 of 69 done, 0 partial, 69 outstanding`, `next cluster: c0001-epoch-c84a5f082e40 (ordinal 1)`, `sessions: not configured`; `status` prints the same numbers and `pin: b901f360…`; `verify --strict` exits 3 with `completeness: findings` and every other check `ok` (build: `ok` because the skeleton compiles against the sealed refcache — if it prints `broken reference`, the two references were not in the toolchain cache: re-provision with them in the seed list). Then the ledger against the finished run: `SSLKEYLOGFILE= $PY -m pytest tests/ledger -k finished_mark -v` — Expected: PASS (37 done, ordinal 38 partial).

- [ ] **Step 4: Record the gate**

Create `docs/experiments/2026-09-03-cli1-mark-gate.md` with the five commands, their exact stdout/stderr (trimmed to the lines above), the `init.json` contents, the cluster-id diff result, and the ledger test's output. First paragraph: "CLI-1's gate from the one-door spec: MARK initialised from a config, run to the boundary, verified, with the ledger agreeing on the finished A1 run."

- [ ] **Step 5: Commit both repositories**

```bash
cd $AIRFC
git status --short
git add README.md ai_rfc/README.md docs/experiment-protocol.md docs/parity.md docs/experiments/2026-09-03-cli1-mark-gate.md
git commit -m "docs: the one-door flow, and the CLI-1 gate on MARK"
cd $PANTHER
git status --short
git add panther/cli/commands/ai_rfc.py tests/unit/test_cli/test_ai_rfc_commands.py
git commit -m "feat(ai_rfc): forward panther ai-rfc to the one argparse root"
```

Then bump the submodule pointer in PANTHER (`chore(ai_rfc): bump ai_rfc to CLI-1 (<old>..<new>)`) and push the submodule before the parent, each push confirmed with the user first.

---

## Self-review (run by the plan author on 2026-09-03)

1. **Spec coverage.** §1 operator flow → Tasks 2 (`config example`), 6 (`doctor`, `toolchain`), 4 (`init`), 5 (`run`, `status`, `verify`). §2 field table → Task 1 (every field, the defaults, `example`/`reference_markdown`, `drift`). §3 root → Task 2 (`configure`/`run`, sections, `--from` order, `python -m` doors kept). §4 ledger → Task 3 (strict done, five readers, consolidation filter, window from `init.json`/`pristine.json`). §7 error handling → every verb's `run()` maps `LifecycleError`/`ConfigError`/`OSError` to exit 1 with the artifact and the fix named; `verify` exits 3 only under `--strict`. §8 testing → `tests/cli`, `tests/ledger`, the agreement test with the five readers, the finished-MARK ledger test, `panther ai-rfc --help` equality. D57 drift policy → Task 1 `drift` + Task 5 `load_sealed`. D61's "leaf verbs stay mounted until CLI-3" → Task 2. Deferred by design and stated in the tasks: sessions and `next` (CLI-2), the `stages:` tuning wiring into the builders (CLI-2), folding the agent verbs and retiring `ai_rfc`/`PANTHER_REPO` (CLI-3), prompt freezing at `init` (CLI-2).
2. **Placeholder scan.** No "TBD"/"TODO"/"handle edge cases"; the two "read the module first" instructions (Task 7 Step 1's click test helper, Task 6 Step 1's `profile_dir` signature) name what to read and the assertion that must hold either way.
3. **Type consistency.** `load_config(path) -> ReconConfig`, `dump_config(config) -> str`, `drift(sealed, given) -> (refused, noted)` in Tasks 1, 4, 5. `Layout(root)` with `config`, `init_record`, `refcache`, `runs`, `interviews`, `out` in Tasks 4, 5, 6. `initialise(config, *, config_path, dest, template, template_commit) -> Path` in Tasks 4 (init, prepare). `ledger.clusters(workspace, window)`, `next_cluster`, `counts` in Tasks 3, 5. `perform(stage, ws, *, strict, cluster, forge_url, host, toolchain)` (SP7a's signature) in Tasks 4, 5. `configure(parser)`/`run(args)`/`main(argv)` in every verb module (Tasks 2, 4, 5, 6). `toolchain.verify(record, runner=None) -> (ok, reasons)` in Tasks 6 and the SP7a-provided module.

## Execution

Subagent-driven, one fresh implementer per task with a reviewer between tasks, from `$AIRFC`. Order is the task order: 1 → 2 → 3 are independent of each other except that 2 must precede 4–6 (they register verbs) and 3 must precede 5 (status/run read the ledger); 4 precedes 5 (fixtures initialise a workspace); 6 is independent of 4–5 but after 2; 7 last. Keep a deviation log at `docs/superpowers/plans/2026-09-03-arfc-one-door-cli1-deviations.md`; CLI-2's plan is repaired from it before it is written.
