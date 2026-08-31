# Phase C Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the aioquic pilot: freeze a campaign, launch six hermetic `claude -p` runs (arms A/B/C × 2 repeats) over the pristine workspace, audit every transcript for arm integrity, recompute outcomes from workspace state, and publish the pilot report with the protocol amendment.

**Architecture:** The `experiment/` package gains `config` (campaign freeze + seeded order), `runner` (one `claude -p` subprocess with streamed capture), `matrix` (frozen order, per-run workspace copy, resume), `audit` (tool-call classification from the stream), `metrics` (pure recomputation from `runs/*/workspace`, `events.jsonl`, `result.json`; gates re-run by the harness on a scratch copy) and `report` (aggregate JSON + markdown). Every test drives a fake `claude` executable that replays scenarios as stream-json and really mutates the workspace through the server core; no network, no model.

**Tech Stack:** Python ≥3.10, stdlib + PyYAML; pytest; git; Claude Code CLI 2.1.246 (pilot only).

**Spec:** `docs/superpowers/specs/2026-08-26-arfc-phase-c-experiment-harness-design.md` §4–§7 (D21–D25, D28). Builds on `docs/superpowers/plans/2026-08-26-arfc-phase-c-foundations.md`, which must be complete (its Task 10 report in hand) before Task 0 here.

## Global Constraints

- Same paths and rules as the foundations plan: `W`, `R`, `S`, `PY`; never `panther_builder.py`; `SSLKEYLOGFILE=` prefix for pytest; nested-`.git` and `~/arfc-experiments` writes need the sandbox off; explicit-path staging; nested-repo commits `feat:`/`test:`/`docs:`; one PANTHER submodule bump at the end; never push without asking.
- Foundations interfaces consumed here (do not redefine): `experiment.arms` (`profile`, `arm_flags`, `constant_flags`, `mcp_config`, `build_argv`), `experiment.render` (`arm_prompt`, `unified_diff`), `experiment.stream` (`parse_stream`, `init_event`, `result_event`, `tool_uses`, `tool_results`, `denials`, `assistant_text`, `usage_series`), `experiment.workspace` (`copy_workspace`, `verify_digest`, `HARNESS_MARKER`, `RECORD_FILE`, `TARGETS`), `experiment.paths`, `experiment.cli` (`_parser`, `_add_root`, `main`), `ai_rfc_server.testing.build_workspace`, `ai_rfc_server.core.{gates,claims,revisions,draft}`.
- The campaign directory is the unit of reproducibility: `~/arfc-experiments/campaigns/<id>/` with `campaign.json`, `prompts/`, `bin/`, `runs/`, `audit/`, `analysis/`. Analysis never writes into `runs/<id>/workspace/`; gate re-runs happen on a scratch copy.
- Per-task gate: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q` plus `$PY -m black` on touched files. **Re-baselined 2026-08-28:** the absolute counts written into each task below assumed a 32-test suite; the suite is now 66, and the denial-fixture refresh adds one more. The **deltas** are what hold, so the expected totals are:

| After task | fixture | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Delta | +1 | +6 | +3 | +6 | +3 | +6 | +6 | +6 |
| Expected total | 67 | 73 | 76 | 82 | 85 | 91 | 97 | **103** |

A total below the table means a test was lost somewhere, not that the table is wrong — find the missing test before continuing.

**Re-baselined again 2026-08-31: the expected total is now 165.** Task 7's 103 is a floor, not a target. Three post-Task-7 commits added tests above it: the guard's in-family fix (`17ba3a1`), the quote-aware operator scan with run B1's Bash corpus frozen as a fixture (+53), and the per-run guard-integrity evidence (+6). Measured: `experiment/tests` 165, `plugins/ai-rfc/server` 38, parent `tests/unit/.../a_rfc/` 207.
- No real `claude` in tests: every launch in tests goes through `experiment/tests/fake_claude/claude`, and `campaign.json` records whichever binary a campaign used.

---

### Task 0: Baseline

- [ ] **Step 1: Foundations landed**

Run: `cd $R && git log --oneline -1 && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q 2>&1 | tail -1 && ls ~/arfc-experiments/pristine/aioquic-w02-11/pristine.sha256 && python3 -c "import json;r=json.load(open('$HOME/arfc-experiments/spike-report.json'));print('go' if r['go'] else 'NO-GO')"`
Expected: the foundations commits through `docs: spike S0 passes; record the measured enforcement mechanism`, `66 passed`, the digest file listed, `go`. Anything else: STOP and report.

> **Verified 2026-08-27: this gate passes.** Spike S0 returned `go: true` on CLI 2.1.247 and the aioquic pristine workspace is built. Before writing the runner, read `ai_rfc/docs/spike-s0.md` and the spec's amended §2: `--allowedTools` does not confine a built-in, so arms B and C are separated by `experiment/guard.py` mounted through `--settings`, and `constant_flags` already carries `--include-hook-events` so the audit can see guard denials. `arm_flags` and `build_argv` take a `guard_settings` path; the campaign must render one settings document per arm into the campaign directory, never into `ARFC_WORKSPACE`.

### Task 1: `experiment/config.py` — campaign freeze and seeded order

**Files:**
- Create: `$R/experiment/config.py`, `$R/experiment/prompts/task.md`, `$R/experiment/tests/test_config.py`

**Interfaces:**
- Consumes: `render.arm_prompt`, `render.unified_diff`, `arms.ARMS`, `workspace.RECORD_FILE`.
- Produces: `Campaign` (frozen dataclass; fields `id, root, target, window, arms, repeats, seed, model, effort, budget_usd, timeout_s, profile_dir, pristine_dir, panther_repo, plugin_root, python, claude_bin, claude_version, run_order, prompt_sha256, pristine_sha256, git, parity, created_at`) with properties `dir` (`root/"campaigns"/id`), `runs_dir`, `prompts_dir`, `bin_dir`, `audit_dir`, `analysis_dir`, `server_src`, and methods `run_spec(run_id) -> tuple[str, int]` (arm, repeat); `run_order(arms, repeats, seed) -> tuple[str, ...]`; `TASK_TEMPLATE`; `render_task(window) -> str`; `init_campaign(*, root, campaign_id, pristine_dir, arms, repeats, seed, model, effort, budget_usd, timeout_s, panther_repo, plugin_root, python, claude_bin, parity) -> Campaign` (writes `campaign.json`, `prompts/arm-{A,B,C}.md`, `prompts/task.md`, `prompts/diff-{A-B,A-C,B-C}.patch`, `bin/arfc`); `load_campaign(campaign_dir) -> Campaign`; `git_describe(path) -> str`.

- [ ] **Step 1: Write the task prompt template** `$R/experiment/prompts/task.md` (a `string.Template`; identical across arms):

```markdown
Reconstruct the specification of this repository progressively, following
the reconstruction loop in your instructions exactly.

- Process the clusters with ordinals $low through $high, in ordinal order,
  one full loop iteration each. Clusters outside that window are already
  marked processed by the harness, so the next-cluster rule starts at
  ordinal $low and reports none after ordinal $high.
- A cluster is finished only when its checkpoint exists, its revision entry
  and tag exist, and both strict gates exit 0.
- Stop when the next-cluster rule reports none. Never ask the user
  anything; there is no user in this session. If an operation is denied, do
  not retry it in another form — note the denial in your final summary and
  continue with what is permitted.
- End with a summary: clusters completed, claims added with their
  adjudicated statuses, revisions tagged, gate status, and every denied or
  failed operation.
```

- [ ] **Step 2: Write the failing tests** (`$R/experiment/tests/test_config.py`):

```python
import json
from pathlib import Path

import pytest

from experiment import ExperimentError
from experiment.config import (
    Campaign,
    git_describe,
    init_campaign,
    load_campaign,
    render_task,
    run_order,
)


def test_run_order_is_seeded_and_covers_every_block():
    order = run_order(("A", "B", "C"), 2, seed=20260826)
    assert len(order) == 6 and len(set(order)) == 6
    assert {o[0] for o in order[:3]} == {"A", "B", "C"}
    assert {o[0] for o in order[3:]} == {"A", "B", "C"}
    assert all(o[1:] == "1" for o in order[:3]) and all(o[1:] == "2" for o in order[3:])
    assert order == run_order(("A", "B", "C"), 2, seed=20260826)
    assert order != run_order(("A", "B", "C"), 2, seed=1)


def test_render_task_states_the_window():
    text = render_task((2, 11))
    assert "ordinals 2 through 11" in text and "$" not in text


@pytest.fixture
def pristine(tmp_path: Path) -> Path:
    root = tmp_path / "pristine" / "fixture-w02-02"
    root.mkdir(parents=True)
    (root / "pristine.sha256").write_text("00  manifest.yaml\n")
    (root / "pristine.json").write_text(
        json.dumps({"target": "fixture", "window": [2, 2], "clone_head": "x", "draft_head": "y"})
    )
    return root


def _init(tmp_path, pristine, panther_repo, plugin_root, **overrides):
    kwargs = dict(
        root=tmp_path / "root",
        campaign_id="pilot-test",
        pristine_dir=pristine,
        arms=("A", "B", "C"),
        repeats=2,
        seed=7,
        model="claude-opus-5",
        effort="high",
        budget_usd=25.0,
        timeout_s=7200,
        panther_repo=panther_repo,
        plugin_root=plugin_root,
        python="/venv/bin/python",
        claude_bin="/bin/echo",
        parity={"passed": True, "summary": "38 passed"},
    )
    kwargs.update(overrides)
    return init_campaign(**kwargs)


def test_init_campaign_freezes_everything(tmp_path, pristine, panther_repo, plugin_root):
    campaign = _init(tmp_path, pristine, panther_repo, plugin_root)
    assert campaign.dir == tmp_path / "root" / "campaigns" / "pilot-test"
    stored = json.loads((campaign.dir / "campaign.json").read_text())
    assert stored["run_order"] == list(campaign.run_order)
    assert stored["window"] == [2, 2] and stored["target"] == "fixture"
    assert stored["pristine_sha256"] == "00  manifest.yaml\n"
    for arm in "ABC":
        prompt = campaign.prompts_dir / f"arm-{arm}.md"
        assert prompt.exists() and stored["prompt_sha256"][f"arm-{arm}.md"]
    assert (campaign.prompts_dir / "task.md").read_text() == render_task((2, 2))
    for pair in ("A-B", "A-C", "B-C"):
        assert (campaign.prompts_dir / f"diff-{pair}.patch").read_text().startswith("--- arm-")
    shim = campaign.bin_dir / "arfc"
    assert shim.exists() and shim.stat().st_mode & 0o111
    assert "/venv/bin/python" in shim.read_text() and str(campaign.server_src) in shim.read_text()
    assert stored["parity"] == {"passed": True, "summary": "38 passed"}
    assert stored["git"]["panther"] and stored["git"]["ai_rfc"]
    assert campaign.run_spec("B2") == ("B", 2)


def test_init_campaign_refuses_to_overwrite(tmp_path, pristine, panther_repo, plugin_root):
    _init(tmp_path, pristine, panther_repo, plugin_root)
    with pytest.raises(ExperimentError):
        _init(tmp_path, pristine, panther_repo, plugin_root)


def test_load_campaign_round_trips(tmp_path, pristine, panther_repo, plugin_root):
    campaign = _init(tmp_path, pristine, panther_repo, plugin_root)
    loaded = load_campaign(campaign.dir)
    assert loaded == campaign
    with pytest.raises(ExperimentError):
        load_campaign(tmp_path / "nowhere")


def test_git_describe_names_a_commit(panther_repo):
    assert git_describe(panther_repo) and " " not in git_describe(panther_repo)
```

- [ ] **Step 3: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment.config'`.

- [ ] **Step 4: Implement `$R/experiment/config.py`**

```python
"""A campaign: every constant of a run matrix, frozen before the first launch.

``campaign.json`` records what the protocol says must be pinned — model,
effort, harness version, prompts and their diffs, the pristine digest, the
run order — so a reviewer can tell exactly what ran. Prompts are rendered
here once; the runner only reads them back.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random
import string
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ExperimentError
from .arms import ARMS
from .render import arm_prompt, unified_diff
from .workspace import DIGEST_FILE, RECORD_FILE

PROMPTS = Path(__file__).parent / "prompts"
TASK_TEMPLATE = PROMPTS / "task.md"
CAMPAIGN_FILE = "campaign.json"
_SHIM = """#!/bin/sh
exec "{python}" -c "import sys; sys.path.insert(0, '{server_src}'); from ai_rfc_server.cli import main; sys.exit(main())" "$@"
"""


@dataclass(frozen=True)
class Campaign:
    """One frozen run matrix and everything needed to launch and analyze it."""

    id: str
    root: Path
    target: str
    window: tuple[int, int]
    arms: tuple[str, ...]
    repeats: int
    seed: int
    model: str
    effort: str
    budget_usd: float
    timeout_s: int
    profile_dir: Path
    pristine_dir: Path
    panther_repo: Path
    plugin_root: Path
    python: str
    claude_bin: str
    claude_version: str
    run_order: tuple[str, ...]
    prompt_sha256: dict[str, str]
    pristine_sha256: str
    git: dict[str, str]
    parity: dict[str, Any] | None
    created_at: str

    @property
    def dir(self) -> Path:
        """The campaign directory."""
        return self.root / "campaigns" / self.id

    @property
    def runs_dir(self) -> Path:
        """Where each run's artifacts live."""
        return self.dir / "runs"

    @property
    def prompts_dir(self) -> Path:
        """Rendered prompts and their diffs."""
        return self.dir / "prompts"

    @property
    def bin_dir(self) -> Path:
        """The shim directory placed first on every run's PATH."""
        return self.dir / "bin"

    @property
    def audit_dir(self) -> Path:
        """Per-run audit records."""
        return self.dir / "audit"

    @property
    def analysis_dir(self) -> Path:
        """Aggregate results."""
        return self.dir / "analysis"

    @property
    def server_src(self) -> Path:
        """The ``ai_rfc_server`` source root under the plugin."""
        return self.plugin_root / "server" / "src"

    def run_spec(self, run_id: str) -> tuple[str, int]:
        """Split a run id like ``B2`` into its arm and repeat."""
        if run_id not in self.run_order:
            raise ExperimentError(f"{run_id} is not in this campaign's run order")
        return run_id[0], int(run_id[1:])


def run_order(arms: tuple[str, ...], repeats: int, seed: int) -> tuple[str, ...]:
    """Seeded interleaving: every repeat block holds every arm, shuffled."""
    order: list[str] = []
    for block in range(1, repeats + 1):
        shuffled = list(arms)
        random.Random(seed + block).shuffle(shuffled)
        order.extend(f"{arm}{block}" for arm in shuffled)
    return tuple(order)


def render_task(window: tuple[int, int]) -> str:
    """The task prompt, identical across arms, with the window spelled out."""
    low, high = window
    return string.Template(TASK_TEMPLATE.read_text()).substitute(low=low, high=high)


def git_describe(path: Path) -> str:
    """``git describe --always --dirty`` of a repository, or ``unknown``."""
    result = subprocess.run(
        ["git", "-C", str(path), "describe", "--always", "--dirty"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _claude_version(claude_bin: str) -> str:
    try:
        result = subprocess.run([claude_bin, "--version"], capture_output=True, text=True)
    except OSError as error:
        raise ExperimentError(f"cannot run {claude_bin}: {error}") from None
    return result.stdout.strip() or result.stderr.strip()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def init_campaign(
    *,
    root: Path,
    campaign_id: str,
    pristine_dir: Path,
    arms: tuple[str, ...],
    repeats: int,
    seed: int,
    model: str,
    effort: str,
    budget_usd: float,
    timeout_s: int,
    panther_repo: Path,
    plugin_root: Path,
    python: str,
    claude_bin: str,
    parity: dict[str, Any] | None,
) -> Campaign:
    """Freeze a campaign on disk.

    Raises:
        ExperimentError: If the campaign exists, an arm is unknown, or the
            pristine workspace lacks its digest or record.
    """
    for arm in arms:
        if arm not in ARMS:
            raise ExperimentError(f"unknown arm {arm!r}")
    campaign_dir = root / "campaigns" / campaign_id
    if campaign_dir.exists():
        raise ExperimentError(f"{campaign_dir} exists; a campaign is frozen once")
    digest_path = pristine_dir / DIGEST_FILE
    record_path = pristine_dir / RECORD_FILE
    if not digest_path.exists() or not record_path.exists():
        raise ExperimentError(f"{pristine_dir} is not a prepared pristine workspace")
    record = json.loads(record_path.read_text())

    prompts_dir = campaign_dir / "prompts"
    prompts_dir.mkdir(parents=True)
    rendered = {arm: arm_prompt(arm, plugin_root) for arm in arms}
    prompt_sha256: dict[str, str] = {}
    for arm, text in rendered.items():
        (prompts_dir / f"arm-{arm}.md").write_text(text)
        prompt_sha256[f"arm-{arm}.md"] = _sha256(text)
    task = render_task(tuple(record["window"]))
    (prompts_dir / "task.md").write_text(task)
    prompt_sha256["task.md"] = _sha256(task)
    for index, first in enumerate(arms):
        for second in arms[index + 1 :]:
            (prompts_dir / f"diff-{first}-{second}.patch").write_text(
                unified_diff(rendered[first], rendered[second], f"arm-{first}", f"arm-{second}")
            )

    bin_dir = campaign_dir / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "arfc"
    shim.write_text(_SHIM.format(python=python, server_src=plugin_root / "server" / "src"))
    shim.chmod(0o755)
    for name in ("runs", "audit", "analysis"):
        (campaign_dir / name).mkdir()

    campaign = Campaign(
        id=campaign_id,
        root=root,
        target=record["target"],
        window=tuple(record["window"]),
        arms=tuple(arms),
        repeats=repeats,
        seed=seed,
        model=model,
        effort=effort,
        budget_usd=budget_usd,
        timeout_s=timeout_s,
        profile_dir=root / "profile",
        pristine_dir=pristine_dir,
        panther_repo=panther_repo,
        plugin_root=plugin_root,
        python=python,
        claude_bin=claude_bin,
        claude_version=_claude_version(claude_bin),
        run_order=run_order(tuple(arms), repeats, seed),
        prompt_sha256=prompt_sha256,
        pristine_sha256=digest_path.read_text(),
        git={"panther": git_describe(panther_repo), "ai_rfc": git_describe(plugin_root)},
        parity=parity,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    (campaign_dir / CAMPAIGN_FILE).write_text(_dump(campaign))
    return campaign


def _dump(campaign: Campaign) -> str:
    payload = dataclasses.asdict(campaign)
    for key, value in payload.items():
        if isinstance(value, Path):
            payload[key] = str(value)
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def load_campaign(campaign_dir: Path) -> Campaign:
    """Read a frozen campaign back.

    Raises:
        ExperimentError: If ``campaign.json`` is missing.
    """
    path = campaign_dir / CAMPAIGN_FILE
    if not path.exists():
        raise ExperimentError(f"{path} is missing; not a campaign directory")
    payload = json.loads(path.read_text())
    for key in ("root", "profile_dir", "pristine_dir", "panther_repo", "plugin_root"):
        payload[key] = Path(payload[key])
    payload["window"] = tuple(payload["window"])
    payload["arms"] = tuple(payload["arms"])
    payload["run_order"] = tuple(payload["run_order"])
    return Campaign(**payload)
```

- [ ] **Step 5: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 73 passed (67 + 6).

- [ ] **Step 6: Commit (nested repo)**

```bash
git -C $R add experiment/config.py experiment/prompts/task.md experiment/tests/test_config.py
git -C $R commit -m "feat: frozen campaigns with seeded interleaved run order"
```

### Task 2: The fake `claude` and the shared harness fixtures

Spec §6: every launch in tests goes through a stand-in that speaks stream-json and really mutates the workspace through the server core, so runner, audit and metrics are tested against arm-shaped transcripts without a model.

**Files:**
- Create: `$R/experiment/tests/fake_claude/claude` (executable), `$R/experiment/tests/test_fake_claude.py`
- Modify: `$R/experiment/tests/conftest.py` (move `template_repo` and the fixture `Target` here from `test_workspace.py`; add `pristine`, `write_scenario`, `FAKE_CLAUDE`), `$R/experiment/tests/test_workspace.py` (drop the moved fixture/helper, import `fixture_target` from conftest)

**Interfaces:**
- Produces: the executable reads `$CLAUDE_CONFIG_DIR/fake-scenarios/<run-id>.json` (run id = parent directory name of `$ARFC_WORKSPACE`; fallback `default.json`), records its argv/env/cwd to `$CLAUDE_CONFIG_DIR/fake-calls/<run-id>.json`, answers `--version` with `fake-claude 0.0.0`, emits an init event shaped by `--tools`/`--mcp-config`/`--model`, replays steps, ends with a result event, exits with the scenario's `exit_code` (default 0). Scenario shape: `{"arm": "A"|"B"|"C", "cost": 1.25, "sleep": 0, "exit_code": 0, "subtype": "success", "steps": [...]}` with step kinds `text`, `claim`, `record_status`, `checkpoint`, `prose`, `revision`, `tag`, `gate`, `citation_gate`, `denied`, `mcp_denied`, `tool_error`, `compact`. Conftest fixtures: `template_repo -> (str, str)`, `fixture_target(source) -> Target`, `pristine -> Path` (prepared from `fixture_workspace`), `write_scenario(profile_dir, run_id, payload)`, `FAKE_CLAUDE: Path`.

- [ ] **Step 1: Write the fake** `$R/experiment/tests/fake_claude/claude` and `chmod +x` it:

```python
#!/usr/bin/env python3
"""A stand-in for ``claude -p`` that replays a scenario as stream-json.

The runner launches it exactly like the real CLI. It reads its scenario from
``$CLAUDE_CONFIG_DIR/fake-scenarios/<run-id>.json`` (the run id is the parent
directory name of ``$ARFC_WORKSPACE``), falling back to ``default.json``;
records how it was called under ``fake-calls/``; emits an init event shaped
by its argv; replays the scenario's steps as tool calls that really mutate
the workspace through the server core; and ends with a result event. Never
used outside the tests.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "plugins" / "ai-rfc" / "server" / "src"))
if os.environ.get("PANTHER_REPO"):
    sys.path.insert(0, os.environ["PANTHER_REPO"])

ARGS = sys.argv[1:]
RAW = "python -m panther.plugins.services.testers.a_rfc"


def _flag(name: str, default: str | None = None) -> str | None:
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


def _emit(event: dict) -> None:
    sys.stdout.write(json.dumps(event, sort_keys=True) + "\n")
    sys.stdout.flush()


def _usage(step: dict) -> dict:
    return {
        "input_tokens": int(step.get("input_tokens", 100)),
        "output_tokens": int(step.get("output_tokens", 20)),
        "cache_creation_input_tokens": int(step.get("cache_creation", 0)),
        "cache_read_input_tokens": int(step.get("cache_read", 0)),
    }


class Session:
    def __init__(self, arm: str, workspace: Path) -> None:
        from ai_rfc_server.paths import resolve_context

        self.arm = arm
        self.workspace = workspace
        self.ctx = resolve_context()
        self.turn = 0
        self.totals = _usage({"input_tokens": 0, "output_tokens": 0})
        self.denials: list[dict] = []

    def _message(self, content: list[dict], step: dict) -> None:
        self.turn += 1
        usage = _usage(step)
        for key in self.totals:
            self.totals[key] += usage[key]
        _emit(
            {
                "type": "assistant",
                "message": {
                    "id": f"m{self.turn}",
                    "role": "assistant",
                    "content": content,
                    "usage": usage,
                },
            }
        )

    def call(
        self,
        name: str,
        tool_input: dict,
        result: str,
        *,
        step: dict,
        is_error: bool = False,
        hooks: bool = False,
    ) -> str:
        use_id = f"tu{self.turn + 1}"
        self._message(
            [{"type": "tool_use", "id": use_id, "name": name, "input": tool_input}], step
        )
        if hooks:
            # Measured on 2.1.247: a PreToolUse denial lands between the call
            # and its result, not before the call.
            _emit({"type": "system", "subtype": "hook_started", "hook_event": "PreToolUse"})
            _emit({"type": "system", "subtype": "hook_response", "hook_event": "PreToolUse"})
        _emit(
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": use_id,
                            "is_error": is_error,
                            "content": result,
                        }
                    ],
                },
            }
        )
        return use_id

    def surface(self, op: str, mcp_input: dict, arfc: str, raw: str | None, result: str, step: dict) -> None:
        if self.arm == "A":
            self.call(f"mcp__arfc__arfc_{op}", mcp_input, result, step=step)
        elif self.arm == "B":
            self.call("Bash", {"command": arfc}, result, step=step)
        else:
            self.call("Bash", {"command": raw or arfc}, result, step=step)

    def edit(self, name: str, step: dict) -> None:
        self.call(
            "Edit",
            {"file_path": str(self.workspace / name), "old_string": "…", "new_string": "…"},
            "ok",
            step=step,
        )

    def cluster_id(self, ordinal: int) -> str:
        for row in (self.workspace / "timeline" / "clusters.jsonl").read_text().splitlines():
            record = json.loads(row)
            if record["ordinal"] == ordinal:
                return record["id"]
        raise SystemExit(f"fake claude: no ordinal {ordinal}")

    def head(self) -> str:
        return subprocess.run(
            ["git", "-C", str(self.workspace / "clone"), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def run(self, step: dict) -> None:
        kind = step["kind"]
        ws = "$ARFC_WORKSPACE"
        if kind == "text":
            self._message([{"type": "text", "text": step.get("text", "…")}], step)
        elif kind == "claim":
            from ai_rfc_server.core.claims import upsert_claim

            fields = {
                "text": step.get("text", "Thing."),
                "section": step.get("section", "9.1"),
                "level": "MAY",
                "layer": "core",
                "intent": "intended",
                "anchors": [{"evidence_class": "code", "locator": "a.txt", "commit": self.head()}],
            }
            stored = upsert_claim(self.ctx, step["id"], fields)
            if self.arm == "C":
                self.edit("manifest.yaml", step)
            else:
                self.surface("claim_upsert", {"claim_id": step["id"], "fields": fields}, f"arfc claim-upsert {step['id']} --text … --section … --level MAY --layer core", None, json.dumps(stored), step)
        elif kind == "record_status":
            from ai_rfc_server.core.claims import record_statuses

            changed = record_statuses(self.ctx)
            if self.arm == "C":
                self.edit("manifest.yaml", step)
            else:
                self.surface("claim_record_status", {}, "arfc claim-record-status", None, json.dumps(changed), step)
        elif kind == "checkpoint":
            from ai_rfc_server.core.gates import write_checkpoint

            cluster = self.cluster_id(step["ordinal"])
            result = write_checkpoint(self.ctx, cluster)
            self.surface("checkpoint", {"cluster_id": cluster}, f"arfc checkpoint {cluster}", f"{RAW}.draft checkpoint {ws}/manifest.yaml --timeline {ws}/timeline --cluster {cluster} --out {ws}/checkpoints", json.dumps(result), step)
        elif kind == "prose":
            from ai_rfc_server.core.draft import commit_draft

            draft = next(self.workspace.glob("draft/draft-*.md"))
            draft.write_text(draft.read_text() + "\n" + step.get("line", "More prose.") + "\n")
            self.edit(f"draft/{draft.name}", step)
            result = commit_draft(self.ctx, step.get("message", "prose"))
            self.surface("draft_commit", {"message": "prose"}, 'arfc draft-commit -m "prose"', f"git -C {ws}/draft add -A && git -C {ws}/draft commit -m prose", json.dumps(result), step)
        elif kind == "revision":
            from ai_rfc_server.core.revisions import record_revision

            cluster = self.cluster_id(step["ordinal"])
            entry = record_revision(self.ctx, step["tag"], cluster, bool(step.get("normative", True)), step.get("note", "n"))
            if self.arm == "C":
                self.edit("revisions.yaml", step)
            else:
                self.surface("revision_record", {"tag": step["tag"], "cluster_id": cluster, "normative_change": True, "note": "n"}, f"arfc revision-record {step['tag']} --cluster {cluster} --normative --note n", None, json.dumps(entry), step)
        elif kind == "tag":
            from ai_rfc_server.core.draft import tag_revision

            result = tag_revision(self.ctx, step["tag"], "rev")
            self.surface("revision_tag", {"tag": step["tag"], "message": "rev"}, f'arfc revision-tag {step["tag"]} -m rev', f'git -C {ws}/draft tag -a {step["tag"]} -m rev', json.dumps(result), step)
        elif kind == "gate":
            from ai_rfc_server.core.gates import manifest_gate

            result = manifest_gate(self.ctx, strict=True)
            self.surface("gate", {"strict": True}, "arfc gate --strict", f"{RAW} {ws}/manifest.yaml --out {ws}/out --repo {ws}/clone --strict", json.dumps(result), step)
        elif kind == "citation_gate":
            from ai_rfc_server.core.gates import citation_gate

            result = citation_gate(self.ctx, strict=True)
            self.surface("citation_gate", {"strict": True}, "arfc citation-gate --strict", f"{RAW}.draft gate {ws}/draft --timeline {ws}/timeline --checkpoints {ws}/checkpoints --questions {ws}/questions.yaml --revisions {ws}/revisions.yaml --out {ws}/out --strict", json.dumps(result), step)
        elif kind == "denied":
            command = step.get("command", "echo x")
            families = step.get("families", "'arfc '")
            tool = step.get("tool", "Bash")
            text = (
                f"PreToolUse:{tool} hook error: [guard]: denied: this arm may run "
                f"only {families}; refused: {command}\n"
            )
            use_id = self.call(tool, {"command": command}, text, step=step, is_error=True, hooks=True)
            self.denials.append({"tool_name": tool, "tool_input": {"command": command}, "tool_use_id": use_id})
        elif kind == "mcp_denied":
            tool = f"mcp__arfc__{step.get('tool', 'arfc_status')}"
            use_id = self.call(tool, {}, "Permission denied: tool is not available in this session", step=step, is_error=True)
            self.denials.append({"tool_name": tool, "tool_input": {}, "tool_use_id": use_id})
        elif kind == "tool_error":
            if self.arm == "A":
                self.call("mcp__arfc__arfc_claim_upsert", {"claim_id": "x", "fields": {"status": "confirmed"}}, "GuardrailError: status is adjudicated from evidence, never asserted", step=step, is_error=True)
            else:
                self.call("Bash", {"command": "arfc claim-upsert --bogus" if self.arm == "B" else f"{RAW} --bogus"}, "exit code 2: usage: arfc [-h] …", step=step, is_error=True)
        elif kind == "compact":
            _emit({"type": "system", "subtype": "compact_boundary"})
        else:
            raise SystemExit(f"fake claude: unknown step kind {kind!r}")


def main() -> int:
    if "--version" in ARGS:
        print("fake-claude 0.0.0")
        return 0
    config_dir = Path(os.environ["CLAUDE_CONFIG_DIR"])
    workspace = Path(os.environ.get("ARFC_WORKSPACE", os.getcwd()))
    run_id = workspace.parent.name
    scenarios = config_dir / "fake-scenarios"
    path = scenarios / f"{run_id}.json"
    if not path.exists():
        path = scenarios / "default.json"
    scenario = json.loads(path.read_text())
    calls = config_dir / "fake-calls"
    calls.mkdir(exist_ok=True)
    (calls / f"{run_id}.json").write_text(
        json.dumps(
            {
                "argv": ARGS,
                "cwd": os.getcwd(),
                "env": {k: os.environ.get(k) for k in ("CLAUDE_CONFIG_DIR", "PANTHER_REPO", "ARFC_WORKSPACE", "PATH", "HOME")},
            },
            indent=2,
            sort_keys=True,
        )
    )
    tools = [tool for tool in (_flag("--tools") or "").split(",") if tool]
    servers = [{"name": "arfc", "status": "connected"}] if _flag("--mcp-config") else []
    _emit({"type": "system", "subtype": "init", "session_id": f"fake-{run_id}", "model": _flag("--model", "fake"), "tools": tools, "mcp_servers": servers, "slash_commands": [], "apiKeySource": "none"})
    if scenario.get("sleep"):
        time.sleep(float(scenario["sleep"]))
    session = Session(scenario.get("arm", "A"), workspace)
    for step in scenario.get("steps", []):
        session.run(step)
    _emit(
        {
            "type": "result",
            "subtype": scenario.get("subtype", "success"),
            "is_error": False,
            "result": "done",
            "total_cost_usd": float(scenario.get("cost", 0.5)),
            "usage": session.totals,
            "modelUsage": {},
            "num_turns": session.turn,
            "duration_ms": 1000 * session.turn,
            "duration_api_ms": 800 * session.turn,
            "session_id": f"fake-{run_id}",
            "permission_denials": session.denials,
        }
    )
    return int(scenario.get("exit_code", 0))


if __name__ == "__main__":
    sys.exit(main())
```


> **The `denied` step's shape is measured, not invented (amended 2026-08-28).**
> On CLI 2.1.247 a Bash denial is produced by `experiment/guard.py` exiting 2, and
> the stream carries it as: the `assistant` tool_use, then `system`/`hook_started`
> and `system`/`hook_response` (both `hook_event: PreToolUse`), then an errored
> `tool_result` whose text is `PreToolUse:Bash hook error: [<argv>]: denied: this
> arm may run only <families>; refused: <command>`, and finally a
> `permission_denials` entry carrying `tool_name`, `tool_input` **and
> `tool_use_id`**. The real transcript is the committed fixture
> `experiment/tests/fixtures/stream/denied-bash.jsonl`; compare against it rather
> than against this plan if the two ever disagree. The older text
> "Permission denied: … is not in the allowed tools" describes allowlist
> enforcement, which spike S0 proved does not exist for built-in tools.
>
> The `mcp_denied` text is **not** measured — no MCP denial was recorded during
> spike S0 — so it remains a plausible stand-in. Nothing downstream may depend on
> its exact wording; Task 5 classifies denials by `tool_use_id`.

Run: `chmod +x $R/experiment/tests/fake_claude/claude`.

- [ ] **Step 2: Extend `conftest.py`** — move `template_repo` and the fixture `Target` out of `test_workspace.py` (delete them there; import `fixture_target` from `conftest` in that test module) and add:

```python
FAKE_CLAUDE = Path(__file__).parent / "fake_claude" / "claude"


@pytest.fixture
def template_repo(tmp_path: Path) -> tuple[str, str]:
    from ai_rfc_server.testing import git

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


def fixture_target(source: Path):
    from experiment.workspace import Target

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


@pytest.fixture
def pristine(fixture_workspace, panther_repo, template_repo, tmp_path) -> Path:
    """A prepared pristine workspace of the fixture target (window 2–2)."""
    from experiment.workspace import prepare

    template, commit = template_repo
    return prepare(
        fixture_target(fixture_workspace),
        root=tmp_path / "root",
        panther_repo=panther_repo,
        template=template,
        template_commit=commit,
    )


@pytest.fixture
def write_scenario():
    def write(profile_dir: Path, run_id: str, payload: dict) -> Path:
        scenarios = profile_dir / "fake-scenarios"
        scenarios.mkdir(parents=True, exist_ok=True)
        path = scenarios / f"{run_id}.json"
        path.write_text(json.dumps(payload, indent=2))
        return path

    return write
```

(`import json` at the top of `conftest.py`.) The fixture `Target`'s draft is `draft-test-fixture.md`, so the loop scenarios below tag `draft-test-fixture-00`; note the `pristine` fixture's window is `(2, 2)` on a two-cluster timeline: ordinal 1 is pre-seeded, ordinal 2 is the only task.

- [ ] **Step 3: Write the fake's own test** (`$R/experiment/tests/test_fake_claude.py`) — it launches the fake by hand the way the runner will:

```python
import json
import os
import subprocess
import sys
from pathlib import Path

from experiment.stream import denials, parse_stream, result_event, tool_results, tool_uses
from experiment.workspace import copy_workspace

from .conftest import FAKE_CLAUDE


def _launch(profile: Path, workspace: Path, panther_repo: Path, *argv: str):
    env = {
        "CLAUDE_CONFIG_DIR": str(profile),
        "PANTHER_REPO": str(panther_repo),
        "ARFC_WORKSPACE": str(workspace),
        "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
    }
    completed = subprocess.run(
        [str(FAKE_CLAUDE), "-p", "go", *argv],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    return parse_stream(completed.stdout)


def test_fake_replays_a_complete_loop_in_every_arm(pristine, panther_repo, tmp_path, write_scenario):
    steps = [
        {"kind": "claim", "id": "t:3.1", "section": "3.1"},
        {"kind": "record_status"},
        {"kind": "checkpoint", "ordinal": 2},
        {"kind": "prose", "line": "Thing three MAY hold. `a_rfc:t:3.1`"},
        {"kind": "revision", "ordinal": 2, "tag": "draft-test-fixture-00", "normative": True},
        {"kind": "tag", "tag": "draft-test-fixture-00"},
        {"kind": "citation_gate"},
    ]
    for arm in "ABC":
        profile = tmp_path / f"profile-{arm}"
        run_dir = tmp_path / "runs" / f"{arm}1"
        workspace = copy_workspace(pristine, run_dir / "workspace")
        write_scenario(profile, f"{arm}1", {"arm": arm, "cost": 1.25, "steps": steps})
        events = _launch(profile, workspace, panther_repo, "--tools", "Read,Edit" + (",Bash" if arm != "A" else ""))
        names = [use["name"] for use in tool_uses(events)]
        assert any(
            p.name.startswith("c0002-") and not (p / "harness.json").exists()
            for p in (workspace / "checkpoints").iterdir()
        ), arm
        tags = subprocess.run(["git", "-C", str(workspace / "draft"), "tag", "-l"], capture_output=True, text=True).stdout.split()
        assert tags == ["draft-test-fixture-00"], arm
        final = result_event(events)
        assert final["total_cost_usd"] == 1.25 and final["num_turns"] == len(names)
        if arm == "A":
            assert all(n.startswith("mcp__arfc__") or n == "Edit" for n in names), names
        elif arm == "B":
            assert any(n == "Bash" for n in names) and not any(n.startswith("mcp__") for n in names)
        else:
            assert "Edit" in names and any("python -m panther" in use["input"].get("command", "") for use in tool_uses(events))
        calls = json.loads((profile / "fake-calls" / f"{arm}1.json").read_text())
        assert calls["cwd"] == str(workspace)


def test_fake_records_denials_and_exit_codes(pristine, panther_repo, tmp_path, write_scenario):
    profile = tmp_path / "profile"
    workspace = copy_workspace(pristine, tmp_path / "runs" / "A1" / "workspace")
    write_scenario(profile, "A1", {"arm": "A", "exit_code": 0, "steps": [{"kind": "denied", "command": "arfc status"}, {"kind": "mcp_denied"}]})
    events = _launch(profile, workspace, panther_repo)
    assert len(denials(events)) == 4
    first = result_event(events)["permission_denials"][0]
    assert first["tool_input"] == {"command": "arfc status"}
    # The shape the guard really produces: hook events bracket the refused call,
    # and the denial names the call it refused.
    hooks = [e for e in events if str(e.get("subtype", "")).startswith("hook_")]
    assert [e["subtype"] for e in hooks] == ["hook_started", "hook_response"]
    assert all(e["hook_event"] == "PreToolUse" for e in hooks)
    bash_call = next(u for u in tool_uses(events) if u["name"] == "Bash")
    assert first["tool_use_id"] == bash_call["id"]
    text = tool_results(events)[bash_call["id"]]["text"]
    assert text.startswith("PreToolUse:Bash hook error:") and "refused: arfc status" in text


def test_fake_answers_version():
    completed = subprocess.run([str(FAKE_CLAUDE), "--version"], capture_output=True, text=True)
    assert completed.stdout.strip() == "fake-claude 0.0.0"
```

- [ ] **Step 4: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 76 passed (73 + 3); `test_workspace.py` still green after the fixture move.

- [ ] **Step 5: Commit (nested repo)**

```bash
git -C $R add experiment/tests/fake_claude/claude experiment/tests/conftest.py experiment/tests/test_workspace.py experiment/tests/test_fake_claude.py
git -C $R commit -m "test: a fake claude that replays arm-shaped scenarios against the core"
```

### Task 3: `experiment/runner.py` — one hermetic launch, everything captured

Spec §4 "runner". One subprocess per run, output streamed to disk as it arrives, a wall-clock cap enforced on the process group, and a status record that resume-by-skip reads.

**Files:**
- Create: `$R/experiment/runner.py`, `$R/experiment/tests/test_runner.py`

**Interfaces:**
- Consumes: `config.Campaign`, `arms.build_argv/mcp_config/profile`, `stream.parse_stream/result_event`.
- Produces: `RunSpec(run_id, arm, repeat, run_dir)` with `.workspace`; `RunStatus(run_id, arm, repeat, started_at, finished_at, exit_code, timed_out, budget_hit, claude_version)` with `.complete`; `run_spec(campaign, run_id) -> RunSpec`; `build_env(campaign, spec) -> dict[str, str]`; `build_run_argv(campaign, spec) -> list[str]` (writes `arfc.json` into the run dir for arm A); `launch(campaign, spec) -> RunStatus`; `load_status(run_dir) -> RunStatus | None`; file names `EVENTS_FILE, RESULT_FILE, STATUS_FILE, STDERR_FILE, ARGV_FILE, ENV_FILE, PROMPT_FILE, MCP_FILE`.

- [ ] **Step 1: Write the failing tests** (`$R/experiment/tests/test_runner.py`):

```python
import dataclasses
import json
import sys
import time
from pathlib import Path

import pytest

from experiment import ExperimentError
from experiment.config import init_campaign
from experiment.runner import (
    EVENTS_FILE,
    RESULT_FILE,
    STATUS_FILE,
    build_env,
    build_run_argv,
    launch,
    load_status,
    run_spec,
)
from experiment.workspace import copy_workspace

from .conftest import FAKE_CLAUDE

COMPLETE = [
    {"kind": "claim", "id": "t:3.1", "section": "3.1"},
    {"kind": "record_status"},
    {"kind": "checkpoint", "ordinal": 2},
    {"kind": "prose", "line": "Thing three MAY hold. `a_rfc:t:3.1`"},
    {"kind": "revision", "ordinal": 2, "tag": "draft-test-fixture-00", "normative": True},
    {"kind": "tag", "tag": "draft-test-fixture-00"},
]


@pytest.fixture
def campaign(pristine, panther_repo, plugin_root, tmp_path):
    return init_campaign(
        root=tmp_path / "root",
        campaign_id="test",
        pristine_dir=pristine,
        arms=("A", "B", "C"),
        repeats=1,
        seed=7,
        model="fake-model",
        effort="high",
        budget_usd=1.0,
        timeout_s=60,
        panther_repo=panther_repo,
        plugin_root=plugin_root,
        python=sys.executable,
        claude_bin=str(FAKE_CLAUDE),
        parity={"passed": True, "summary": "test"},
    )


def _ready(campaign, run_id):
    spec = run_spec(campaign, run_id)
    spec.run_dir.mkdir(parents=True)
    copy_workspace(campaign.pristine_dir, spec.workspace)
    return spec


def test_launch_streams_events_and_records_status(campaign, write_scenario):
    spec = _ready(campaign, "A1")
    write_scenario(campaign.profile_dir, "A1", {"arm": "A", "cost": 1.25, "steps": COMPLETE})
    status = launch(campaign, spec)
    assert status.complete and status.exit_code == 0 and not status.timed_out
    assert status.claude_version == "fake-claude 0.0.0"
    events = (spec.run_dir / EVENTS_FILE).read_text().splitlines()
    assert json.loads(events[0])["subtype"] == "init"
    assert json.loads((spec.run_dir / RESULT_FILE).read_text())["total_cost_usd"] == 1.25
    assert load_status(spec.run_dir) == status
    argv = json.loads((spec.run_dir / "argv.json").read_text())
    assert argv[:2] == [str(FAKE_CLAUDE), "-p"] and "--append-system-prompt-file" in argv
    env = json.loads((spec.run_dir / "env.json").read_text())
    assert env["PATH"].startswith(str(campaign.bin_dir)) and env["ARFC_WORKSPACE"] == str(spec.workspace)
    assert set(env) == {"CLAUDE_CONFIG_DIR", "PANTHER_REPO", "ARFC_WORKSPACE", "PATH", "HOME", "USER", "LANG"}
    prompt = (spec.run_dir / "prompt.md").read_text()
    assert "arfc_cluster_next" in prompt and "ordinals 2 through 2" in prompt
    calls = json.loads((campaign.profile_dir / "fake-calls" / "A1.json").read_text())
    assert calls["cwd"] == str(spec.workspace)
    assert any(
        p.name.startswith("c0002-") and not (p / "harness.json").exists()
        for p in (spec.workspace / "checkpoints").iterdir()
    )


def test_arm_a_mounts_mcp_and_has_no_bash(campaign):
    spec_a = _ready(campaign, "A1")
    argv = build_run_argv(campaign, spec_a)
    assert "--mcp-config" in argv and (spec_a.run_dir / "arfc.json").exists()
    assert "Bash" not in argv[argv.index("--tools") + 1].split(",")
    spec_b = _ready(campaign, "B1")
    argv_b = build_run_argv(campaign, spec_b)
    assert "--mcp-config" not in argv_b and "Bash(arfc *)" in argv_b[argv_b.index("--allowedTools") + 1]
    assert build_env(campaign, spec_b)["CLAUDE_CONFIG_DIR"] == str(campaign.profile_dir)


def test_launch_times_out_and_kills_the_process_group(campaign, write_scenario):
    spec = _ready(campaign, "C1")
    write_scenario(campaign.profile_dir, "C1", {"arm": "C", "sleep": 30, "steps": []})
    short = dataclasses.replace(campaign, timeout_s=1)
    started = time.monotonic()
    status = launch(short, spec)
    assert status.timed_out and status.exit_code is None and not status.complete
    assert time.monotonic() - started < 40
    assert (spec.run_dir / RESULT_FILE).read_text() == "null\n"


def test_launch_records_a_nonzero_exit(campaign, write_scenario):
    spec = _ready(campaign, "B1")
    write_scenario(campaign.profile_dir, "B1", {"arm": "B", "exit_code": 3, "steps": []})
    status = launch(campaign, spec)
    assert status.complete and status.exit_code == 3


def test_launch_refuses_to_relaunch(campaign, write_scenario):
    spec = _ready(campaign, "B1")
    write_scenario(campaign.profile_dir, "B1", {"arm": "B", "steps": []})
    launch(campaign, spec)
    with pytest.raises(ExperimentError):
        launch(campaign, spec)
    assert load_status(run_spec(campaign, "C1").run_dir) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_runner.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment.runner'`.

- [ ] **Step 3: Implement `$R/experiment/runner.py`**

```python
"""Launch one hermetic ``claude -p`` run and capture everything it emits.

The process gets a minimal environment, its stdout streams straight into
``events.jsonl`` as it arrives, a wall-clock cap is enforced on the whole
process group (the MCP server is a child), and ``status.json`` is written
exactly once — a run is never relaunched in place.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import ExperimentError
from .arms import build_argv, mcp_config, profile
from .config import Campaign
from .stream import parse_stream, result_event

EVENTS_FILE = "events.jsonl"
RESULT_FILE = "result.json"
STATUS_FILE = "status.json"
STDERR_FILE = "stderr.log"
ARGV_FILE = "argv.json"
ENV_FILE = "env.json"
PROMPT_FILE = "prompt.md"
MCP_FILE = "arfc.json"
_KILL_GRACE_S = 30


@dataclass(frozen=True)
class RunSpec:
    """One run's identity and directory."""

    run_id: str
    arm: str
    repeat: int
    run_dir: Path

    @property
    def workspace(self) -> Path:
        """The run's private copy of the pristine workspace."""
        return self.run_dir / "workspace"


@dataclass(frozen=True)
class RunStatus:
    """What happened to one launch; written once as ``status.json``."""

    run_id: str
    arm: str
    repeat: int
    started_at: str
    finished_at: str
    exit_code: int | None
    timed_out: bool
    budget_hit: bool
    claude_version: str

    @property
    def complete(self) -> bool:
        """The process ended on its own (any exit code); timeouts are not complete."""
        return not self.timed_out and self.exit_code is not None


def run_spec(campaign: Campaign, run_id: str) -> RunSpec:
    """Resolve a run id from the campaign's frozen order."""
    arm, repeat = campaign.run_spec(run_id)
    return RunSpec(run_id, arm, repeat, campaign.runs_dir / run_id)


def build_env(campaign: Campaign, spec: RunSpec) -> dict[str, str]:
    """The minimal environment of a run: profile, contract, PATH, HOME, LANG."""
    venv_bin = str(Path(campaign.python).parent)
    return {
        "CLAUDE_CONFIG_DIR": str(campaign.profile_dir),
        "PANTHER_REPO": str(campaign.panther_repo),
        "ARFC_WORKSPACE": str(spec.workspace),
        "PATH": f"{campaign.bin_dir}:{venv_bin}:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", ""),
        # Measured on Claude Code 2.1.247 / macOS: drop USER and the CLI cannot
        # reach its stored credentials, answering "Not logged in" however valid
        # the profile. Spike S0 failed on exactly this before it was added.
        "USER": os.environ.get("USER", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }


def build_run_argv(campaign: Campaign, spec: RunSpec) -> list[str]:
    """The argument vector of a run; writes the run's MCP config for arm A."""
    arm_profile = profile(spec.arm)
    mcp_path = None
    if arm_profile.uses_mcp:
        mcp_path = spec.run_dir / MCP_FILE
        mcp_path.write_text(
            json.dumps(
                mcp_config(
                    python=campaign.python,
                    server_src=campaign.server_src,
                    panther_repo=campaign.panther_repo,
                    workspace=spec.workspace,
                ),
                indent=2,
            )
            + "\n"
        )
    return build_argv(
        claude_bin=campaign.claude_bin,
        prompt=(campaign.prompts_dir / "task.md").read_text(),
        arm_profile=arm_profile,
        mcp_config_path=mcp_path,
        model=campaign.model,
        effort=campaign.effort,
        budget_usd=campaign.budget_usd,
        prompt_file=campaign.prompts_dir / f"arm-{spec.arm}.md",
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_status(run_dir: Path) -> RunStatus | None:
    """The run's status record, or ``None`` if it never finished launching."""
    path = run_dir / STATUS_FILE
    if not path.exists():
        return None
    return RunStatus(**json.loads(path.read_text()))


def launch(campaign: Campaign, spec: RunSpec) -> RunStatus:
    """Run one session to completion or timeout, streaming its output to disk.

    Raises:
        ExperimentError: If the workspace is missing or the run already has
            a status record.
    """
    if not spec.workspace.is_dir():
        raise ExperimentError(f"{spec.workspace} is missing; copy the pristine workspace first")
    if (spec.run_dir / STATUS_FILE).exists():
        raise ExperimentError(f"{spec.run_id} already ran; a run is never relaunched in place")
    argv = build_run_argv(campaign, spec)
    env = build_env(campaign, spec)
    (spec.run_dir / ARGV_FILE).write_text(json.dumps(argv, indent=2) + "\n")
    (spec.run_dir / ENV_FILE).write_text(json.dumps(env, indent=2, sort_keys=True) + "\n")
    (spec.run_dir / PROMPT_FILE).write_text(
        (campaign.prompts_dir / f"arm-{spec.arm}.md").read_text()
        + "\n\n---\n\n"
        + (campaign.prompts_dir / "task.md").read_text()
    )
    started = _now()
    timed_out = False
    exit_code: int | None = None
    with open(spec.run_dir / EVENTS_FILE, "wb") as events, open(
        spec.run_dir / STDERR_FILE, "wb"
    ) as stderr:
        process = subprocess.Popen(
            argv,
            cwd=spec.workspace,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=events,
            stderr=stderr,
            start_new_session=True,
        )
        try:
            exit_code = process.wait(timeout=campaign.timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=_KILL_GRACE_S)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    try:
        final = result_event(parse_stream((spec.run_dir / EVENTS_FILE).read_text(errors="replace")))
    except ExperimentError:
        final = None
    (spec.run_dir / RESULT_FILE).write_text(
        json.dumps(final, indent=2, sort_keys=True) + "\n" if final else "null\n"
    )
    subtype = str((final or {}).get("subtype", "")).lower()
    status = RunStatus(
        run_id=spec.run_id,
        arm=spec.arm,
        repeat=spec.repeat,
        started_at=started,
        finished_at=_now(),
        exit_code=None if timed_out else exit_code,
        timed_out=timed_out,
        budget_hit="budget" in subtype,
        claude_version=campaign.claude_version,
    )
    (spec.run_dir / STATUS_FILE).write_text(json.dumps(asdict(status), indent=2, sort_keys=True) + "\n")
    return status
```

- [ ] **Step 4: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 82 passed (76 + 6) — the plan's five plus the guard-mount test.

- [ ] **Step 5: Commit (nested repo)**

```bash
git -C $R add experiment/runner.py experiment/tests/test_runner.py
git -C $R commit -m "feat: hermetic single-run launcher with streamed capture and status"
```

### Task 4: `experiment/matrix.py` — the frozen order, per-run copies, resume

Spec §4 "execute runs in the frozen order". A run directory that exists without a status record is evidence of an interrupted launch and is never reused silently.

**Files:**
- Create: `$R/experiment/matrix.py`, `$R/experiment/tests/test_matrix.py`

**Interfaces:**
- Consumes: `runner.run_spec/launch/load_status/RunStatus`, `workspace.copy_workspace`, `config.Campaign`.
- Produces: `pending_runs(campaign) -> list[str]`; `execute(campaign, *, only: Iterable[str] | None = None, report=print) -> list[RunStatus]`.

- [ ] **Step 1: Write the failing tests** (`$R/experiment/tests/test_matrix.py`; reuse the `campaign` fixture and `COMPLETE` steps by moving both into `conftest.py` — `campaign` becomes a conftest fixture and `COMPLETE_STEPS` a conftest constant imported by `test_runner.py`, `test_matrix.py`, `test_audit.py`, `test_metrics.py`):

```python
import pytest

from experiment import ExperimentError
from experiment.matrix import execute, pending_runs
from experiment.runner import load_status, run_spec

from .conftest import COMPLETE_STEPS


def _scenarios(campaign, write_scenario):
    write_scenario(campaign.profile_dir, "A1", {"arm": "A", "cost": 1.0, "steps": COMPLETE_STEPS})
    write_scenario(campaign.profile_dir, "B1", {"arm": "B", "cost": 0.4, "exit_code": 3, "steps": []})
    write_scenario(campaign.profile_dir, "C1", {"arm": "C", "cost": 1.1, "steps": COMPLETE_STEPS})


def test_execute_follows_the_frozen_order_and_resumes(campaign, write_scenario):
    _scenarios(campaign, write_scenario)
    assert pending_runs(campaign) == list(campaign.run_order)
    lines = []
    statuses = execute(campaign, report=lines.append)
    assert [s.run_id for s in statuses] == list(campaign.run_order)
    assert {s.run_id: s.exit_code for s in statuses} == {"A1": 0, "B1": 3, "C1": 0}
    assert pending_runs(campaign) == []
    again = execute(campaign, report=lines.append)
    assert again == statuses
    assert sum("skipping" in line for line in lines) == 3
    for run_id in campaign.run_order:
        spec = run_spec(campaign, run_id)
        assert (spec.workspace / "pristine.sha256").exists()
        assert load_status(spec.run_dir).run_id == run_id


def test_execute_only_runs_the_requested_subset(campaign, write_scenario):
    _scenarios(campaign, write_scenario)
    statuses = execute(campaign, only=["C1"], report=lambda _: None)
    assert [s.run_id for s in statuses] == ["C1"]
    assert pending_runs(campaign) == [r for r in campaign.run_order if r != "C1"]
    with pytest.raises(ExperimentError):
        execute(campaign, only=["Z9"], report=lambda _: None)


def test_execute_refuses_a_run_dir_without_status(campaign, write_scenario):
    _scenarios(campaign, write_scenario)
    (campaign.runs_dir / campaign.run_order[0]).mkdir(parents=True)
    with pytest.raises(ExperimentError) as excinfo:
        execute(campaign, report=lambda _: None)
    assert "without a status record" in str(excinfo.value)
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_matrix.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment.matrix'`.

- [ ] **Step 3: Implement `$R/experiment/matrix.py`**

```python
"""Execute a campaign's frozen run order: copy, launch, record, resume.

Order comes from ``campaign.json`` and is never recomputed. A run with a
status record is skipped on resume; a run directory without one is an
interrupted launch and is refused rather than reused — it is evidence.
"""

from __future__ import annotations

from typing import Callable, Iterable

from . import ExperimentError
from .config import Campaign
from .runner import RunStatus, launch, load_status, run_spec
from .workspace import copy_workspace


def pending_runs(campaign: Campaign) -> list[str]:
    """Run ids in frozen order that have no status record yet."""
    return [
        run_id
        for run_id in campaign.run_order
        if load_status(campaign.runs_dir / run_id) is None
    ]


def execute(
    campaign: Campaign,
    *,
    only: Iterable[str] | None = None,
    report: Callable[[str], None] = print,
) -> list[RunStatus]:
    """Launch every pending run in the frozen order (or the subset in ``only``).

    Returns:
        One status per selected run, launched or loaded, in frozen order.

    Raises:
        ExperimentError: If ``only`` names a run outside the campaign, or a
            run directory exists without a status record.
    """
    wanted = set(only) if only is not None else set(campaign.run_order)
    unknown = wanted - set(campaign.run_order)
    if unknown:
        raise ExperimentError(f"not in this campaign: {sorted(unknown)}")
    statuses: list[RunStatus] = []
    for run_id in campaign.run_order:
        if run_id not in wanted:
            continue
        spec = run_spec(campaign, run_id)
        existing = load_status(spec.run_dir)
        if existing is not None:
            report(
                f"{run_id}: already ran (exit {existing.exit_code}, "
                f"timed_out={existing.timed_out}); skipping"
            )
            statuses.append(existing)
            continue
        if spec.run_dir.exists():
            raise ExperimentError(
                f"{spec.run_dir} exists without a status record; move it aside "
                f"(it is evidence of an interrupted launch) before resuming"
            )
        spec.run_dir.mkdir(parents=True)
        copy_workspace(campaign.pristine_dir, spec.workspace)
        report(f"{run_id}: launching arm {spec.arm}, repeat {spec.repeat}")
        status = launch(campaign, spec)
        report(
            f"{run_id}: exit {status.exit_code} timed_out={status.timed_out} "
            f"budget_hit={status.budget_hit}"
        )
        statuses.append(status)
    return statuses
```

- [ ] **Step 4: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 85 passed (82 + 3).

- [ ] **Step 5: Commit (nested repo)**

```bash
git -C $R add experiment/matrix.py experiment/tests/test_matrix.py experiment/tests/conftest.py experiment/tests/test_runner.py
git -C $R commit -m "feat: execute the frozen run matrix with per-run copies and resume"
```

### Task 5: `experiment/audit.py` — surface classification, integrity, bypasses, error taxonomy

Spec §5 "Audit". Every tool call is classified by the surface it reached for; executed out-of-arm calls are integrity violations, denied ones are bypass attempts, errors split into the class-1 (typed tool) and class-2 (shell) channels.

> **Amended 2026-08-28.** A denial is identified by `tool_use_id` from the result
> event's `permission_denials`, not by recognising prose — measured on 2.1.247,
> that field links a denial to the exact call it refused. `is_denial` stays as the
> fallback for a denial that never reaches the result event, which is also the
> path the unmeasured `mcp_denied` shape would take. Real transcripts also carry a
> top-level `rate_limit_event` and `system` events with subtypes `hook_started` /
> `hook_response`: `parse_stream` tolerates them and the audit ignores them; they
> are not malformed input.

**Files:**
- Create: `$R/experiment/audit.py`, `$R/experiment/tests/test_audit.py`
- Modify: `$R/experiment/stream.py` (add `is_denial(text) -> bool`, used by `denials` too)

**Interfaces:**
- Produces: `RAW_PREFIX`, `REGISTERS`, `ALLOWED: dict[str, set[str]]`; `ToolCall(index, name, surface, family, target, denied, errored, summary)`; `bash_family(command) -> str` (`bash:arfc | bash:python_a_rfc | bash:git | bash:sqlite3 | bash:other | bash:mixed`); `classify(name, tool_input) -> tuple[str, str, str]` (surface, family, target: surfaces `mcp`, `mcp:other`, `bash:*`, `edit`, `read`, `other`; edit targets `register | prose | other`); `audit_events(events, arm) -> dict`; `audit_run(campaign, run_id) -> dict` (writes `audit/<run_id>.json`); `audit_campaign(campaign) -> dict[str, dict]`.

- [ ] **Step 1: Write the failing tests** (`$R/experiment/tests/test_audit.py`):

```python
import json

from experiment.audit import audit_campaign, audit_events, bash_family, classify
from experiment.matrix import execute
from experiment.stream import parse_stream

from .conftest import COMPLETE_STEPS


def test_bash_family_recognises_each_command_family():
    assert bash_family("arfc status") == "bash:arfc"
    assert bash_family("python -m panther.plugins.services.testers.a_rfc m.yaml --out o") == "bash:python_a_rfc"
    assert bash_family("git -C draft tag -a x -m y") == "bash:git"
    assert bash_family('sqlite3 corpus/index.sqlite "SELECT 1"') == "bash:sqlite3"
    assert bash_family("git -C d add -A && git -C d commit -m m") == "bash:git"
    assert bash_family("arfc status && echo x") == "bash:mixed"
    assert bash_family("echo hi") == "bash:other" and bash_family("") == "bash:other"


def test_classify_maps_tools_to_surfaces():
    assert classify("mcp__arfc__arfc_checkpoint", {"cluster_id": "c"}) == ("mcp", "arfc_checkpoint", "")
    assert classify("mcp__other__thing", {}) == ("mcp:other", "mcp__other__thing", "")
    assert classify("Bash", {"command": "arfc gate --strict"}) == ("bash:arfc", "arfc", "")
    assert classify("Edit", {"file_path": "/w/manifest.yaml"}) == ("edit", "Edit", "register")
    assert classify("Write", {"file_path": "/w/draft/draft-x.md"}) == ("edit", "Write", "prose")
    assert classify("Edit", {"file_path": "/w/notes.txt"}) == ("edit", "Edit", "other")
    assert classify("Grep", {"pattern": "x"}) == ("read", "Grep", "")
    assert classify("WebFetch", {}) == ("other", "WebFetch", "")


def test_audit_events_flags_an_executed_out_of_arm_call():
    events = parse_stream(
        '{"type":"assistant","message":{"id":"m1","content":[{"type":"tool_use","id":"t1","name":"Bash","input":{"command":"arfc status"}}],"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t1","is_error":false,"content":"{}"}]}}\n'
        '{"type":"result","subtype":"success","total_cost_usd":0.1,"usage":{},"permission_denials":[]}\n'
    )
    audit = audit_events(events, "A")
    assert audit["integrity"] is False
    assert audit["executed_out_of_arm"][0]["surface"] == "bash:arfc"
    assert audit_events(events, "B")["integrity"] is True


def test_a_denial_is_recognised_from_its_id_alone():
    """The CLI's own permission_denials entry is authoritative, whatever the text."""
    events = parse_stream(
        '{"type":"assistant","message":{"id":"m1","content":[{"type":"tool_use","id":"t1","name":"Bash","input":{"command":"echo probe"}}],"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t1","is_error":true,"content":"some wording nobody predicted"}]}}\n'
        '{"type":"result","subtype":"success","total_cost_usd":0.1,"usage":{},'
        '"permission_denials":[{"tool_name":"Bash","tool_input":{"command":"echo probe"},"tool_use_id":"t1"}]}\n'
    )
    audit = audit_events(events, "C")
    assert audit["bypass_attempts"]["count"] == 1
    assert audit["integrity"] is True and audit["errors"]["class2"] == 0


def test_a_denial_that_never_reached_the_result_event_falls_back_to_its_text():
    events = parse_stream(
        '{"type":"assistant","message":{"id":"m1","content":[{"type":"tool_use","id":"t1","name":"mcp__arfc__arfc_status","input":{}}],"usage":{"input_tokens":1,"output_tokens":1}}}\n'
        '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t1","is_error":true,"content":"Permission denied: tool is not available in this session"}]}}\n'
        '{"type":"result","subtype":"success","total_cost_usd":0.1,"usage":{},"permission_denials":[]}\n'
    )
    audit = audit_events(events, "B")
    assert audit["bypass_attempts"]["count"] == 1 and audit["errors"]["class1"] == 0


def test_audit_over_fake_runs_counts_bypasses_and_errors(campaign, write_scenario):
    write_scenario(campaign.profile_dir, "A1", {"arm": "A", "steps": COMPLETE_STEPS + [{"kind": "denied", "command": "arfc status"}, {"kind": "tool_error"}, {"kind": "compact"}]})
    write_scenario(campaign.profile_dir, "B1", {"arm": "B", "steps": COMPLETE_STEPS + [{"kind": "mcp_denied"}, {"kind": "tool_error"}]})
    write_scenario(campaign.profile_dir, "C1", {"arm": "C", "steps": COMPLETE_STEPS + [{"kind": "tool_error"}]})
    execute(campaign, report=lambda _: None)
    audits = audit_campaign(campaign)
    assert set(audits) == {"A1", "B1", "C1"}
    a, b, c = audits["A1"], audits["B1"], audits["C1"]
    assert all(audit["integrity"] for audit in (a, b, c))
    assert a["bypass_attempts"]["count"] == 1 and a["bypass_attempts"]["by_surface"] == {"bash:arfc": 1}
    assert a["errors"] == {"class1": 1, "class2": 0, "first_failure_index": a["errors"]["first_failure_index"]}
    assert a["errors"]["first_failure_index"] is not None and a["compaction_events"] == 1
    assert b["bypass_attempts"]["by_surface"] == {"mcp": 1} and b["errors"]["class2"] == 1
    assert c["errors"]["class2"] == 1 and c["bypass_attempts"]["count"] == 0
    assert c["hand_edits"] == {"manifest.yaml": 2, "questions.yaml": 0, "revisions.yaml": 1}
    assert a["hand_edits"] == {"manifest.yaml": 0, "questions.yaml": 0, "revisions.yaml": 0}
    assert a["prose_edits"] == 1 and c["prose_edits"] == 1
    assert a["tool_calls"]["by_surface"]["mcp"] >= 6
    stored = json.loads((campaign.audit_dir / "A1.json").read_text())
    assert stored == a
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_audit.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment.audit'`.

- [ ] **Step 3: Add `is_denial` to `stream.py`** (and use it inside `denials`):

```python
def is_denial(text: str) -> bool:
    """Whether an errored tool result reads as a permission denial."""
    return bool(_DENIAL.search(text))
```

- [ ] **Step 4: Implement `$R/experiment/audit.py`**

```python
"""Classify a run's tool calls by surface and judge arm integrity.

An *executed* call on a surface outside the run's arm is an integrity
violation (impossible by construction, still checked). A *denied* call is a
bypass attempt, kept as data. Errors split into the class-1 channel (typed
tool errors) and the class-2 channel (shell errors), as the protocol's
two-sided taxonomy asks.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from . import ExperimentError
from .config import Campaign
from .runner import EVENTS_FILE, load_status
from .stream import is_denial, parse_stream, result_event, tool_results, tool_uses

RAW_PREFIX = "python -m panther.plugins.services.testers.a_rfc"
REGISTERS = ("manifest.yaml", "questions.yaml", "revisions.yaml")
ALLOWED: dict[str, set[str]] = {
    "A": {"mcp", "edit", "read"},
    "B": {"bash:arfc", "edit", "read"},
    "C": {"bash:python_a_rfc", "bash:git", "bash:sqlite3", "edit", "read"},
}
_SEGMENT = re.compile(r"&&|\|\||;|\|")


@dataclass(frozen=True)
class ToolCall:
    """One classified tool call."""

    index: int
    name: str
    surface: str
    family: str
    target: str
    denied: bool
    errored: bool
    summary: str


def bash_family(command: str) -> str:
    """The command family of a shell line; mixed families are named as such."""
    families = set()
    for segment in (part.strip() for part in _SEGMENT.split(command)):
        if not segment:
            continue
        if segment.startswith("arfc "):
            families.add("bash:arfc")
        elif segment.startswith(RAW_PREFIX):
            families.add("bash:python_a_rfc")
        elif segment.startswith("git "):
            families.add("bash:git")
        elif segment.startswith("sqlite3 "):
            families.add("bash:sqlite3")
        else:
            families.add("bash:other")
    if not families:
        return "bash:other"
    return families.pop() if len(families) == 1 else "bash:mixed"


def classify(name: str, tool_input: dict[str, Any]) -> tuple[str, str, str]:
    """Return ``(surface, family, target)`` for one tool call."""
    if name.startswith("mcp__arfc__"):
        return "mcp", name[len("mcp__arfc__") :], ""
    if name.startswith("mcp__"):
        return "mcp:other", name, ""
    if name == "Bash":
        command = str(tool_input.get("command", "")).strip()
        family = bash_family(command)
        return family, command.split(" ", 1)[0] if command else "", ""
    if name in ("Edit", "Write", "MultiEdit"):
        path = str(tool_input.get("file_path", ""))
        basename = path.rsplit("/", 1)[-1]
        if basename in REGISTERS:
            target = "register"
        elif "/draft/" in path and path.endswith(".md"):
            target = "prose"
        else:
            target = "other"
        return "edit", name, target
    if name in ("Read", "Grep", "Glob"):
        return "read", name, ""
    return "other", name, ""


def _summary(use: dict[str, Any]) -> str:
    tool_input = use["input"]
    for key in ("command", "file_path", "cluster_id", "claim_id", "tag"):
        if key in tool_input:
            return f"{key}={str(tool_input[key])[:120]}"
    return json.dumps(tool_input, sort_keys=True)[:120]


def _denied_ids(events: list[dict[str, Any]]) -> set[str]:
    """The ids of calls the CLI itself reported as denied.

    Measured on 2.1.247: ``permission_denials`` carries ``tool_use_id``, which
    links a denial to the exact call it refused. That is authoritative and needs
    no text matching; ``is_denial`` remains the fallback for a denial that never
    reached the result event.
    """
    final = result_event(events) or {}
    return {
        str(denial["tool_use_id"])
        for denial in final.get("permission_denials") or []
        if isinstance(denial, dict) and denial.get("tool_use_id")
    }


def audit_events(events: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    """Audit one transcript for the arm it was supposed to stay inside."""
    results = tool_results(events)
    denied_ids = _denied_ids(events)
    calls: list[ToolCall] = []
    for use in tool_uses(events):
        surface, family, target = classify(use["name"], use["input"])
        result = results.get(str(use["id"]))
        errored = bool(result and result["is_error"])
        denied = str(use["id"]) in denied_ids or (
            errored and is_denial(result["text"])
        )
        calls.append(
            ToolCall(
                index=use["index"],
                name=use["name"],
                surface=surface,
                family=family,
                target=target,
                denied=denied,
                errored=errored,
                summary=_summary(use),
            )
        )
    allowed = ALLOWED[arm]
    violations = [c for c in calls if c.surface not in allowed and not c.denied]
    bypasses = [c for c in calls if c.denied]
    class1 = [c for c in calls if c.errored and not c.denied and c.surface.startswith("mcp")]
    class2 = [c for c in calls if c.errored and not c.denied and c.surface.startswith("bash")]
    failures = sorted(c.index for c in class1 + class2)
    final = result_event(events) or {}
    return {
        "arm": arm,
        "integrity": not violations,
        "tool_calls": {
            "total": len(calls),
            "by_surface": dict(sorted(Counter(c.surface for c in calls).items())),
        },
        "executed_out_of_arm": [asdict(c) for c in violations],
        "bypass_attempts": {
            "count": len(bypasses),
            "by_surface": dict(sorted(Counter(c.surface for c in bypasses).items())),
            "items": [asdict(c) for c in bypasses],
            "result_permission_denials": len(final.get("permission_denials") or []),
        },
        "errors": {
            "class1": len(class1),
            "class2": len(class2),
            "first_failure_index": failures[0] if failures else None,
        },
        "hand_edits": {
            name: sum(
                1 for c in calls if c.surface == "edit" and c.target == "register" and name in c.summary
            )
            for name in REGISTERS
        },
        "prose_edits": sum(1 for c in calls if c.surface == "edit" and c.target == "prose"),
        "compaction_events": sum(
            1
            for event in events
            if event.get("type") == "system" and "compact" in str(event.get("subtype", ""))
        ),
        "api_errors": sum(1 for event in events if event.get("type") == "error")
        + (1 if final.get("is_error") else 0),
        "event_count": len(events),
    }


def audit_run(campaign: Campaign, run_id: str) -> dict[str, Any]:
    """Audit one run from its transcript and write ``audit/<run_id>.json``."""
    run_dir = campaign.runs_dir / run_id
    status = load_status(run_dir)
    if status is None:
        raise ExperimentError(f"{run_id} has no status record; nothing to audit")
    events = parse_stream((run_dir / EVENTS_FILE).read_text(errors="replace"))
    audit = {"run_id": run_id, **audit_events(events, status.arm)}
    campaign.audit_dir.mkdir(exist_ok=True)
    (campaign.audit_dir / f"{run_id}.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n"
    )
    return audit


def audit_campaign(campaign: Campaign) -> dict[str, dict[str, Any]]:
    """Audit every run that has a status record."""
    return {
        run_id: audit_run(campaign, run_id)
        for run_id in campaign.run_order
        if load_status(campaign.runs_dir / run_id) is not None
    }
```

- [ ] **Step 5: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 91 passed (85 + 6).

- [ ] **Step 6: Commit (nested repo)**

```bash
git -C $R add experiment/audit.py experiment/stream.py experiment/tests/test_audit.py
git -C $R commit -m "feat: transcript audit by surface with integrity, bypass and error channels"
```

### Task 6: `experiment/metrics.py` — outcomes recomputed from artifacts

Spec §5 "Analysis" (D23, D24). Completion is read from checkpoints, revision entries and tags; the strict gates are re-run by the harness on a scratch copy of the final workspace; cost comes from the result event; per-cluster attribution aligns cumulative usage with the checkpoint calls. One strengthening over the spec's wording: a revision's tag is required for every entry, not only normative ones, because the citation gate's tag bijection demands it anyway.

**Files:**
- Create: `$R/experiment/metrics.py`, `$R/experiment/tests/test_metrics.py`
- Modify: `$R/experiment/tests/fake_claude/claude` (add the `overstate` step kind)

**Interfaces:**
- Consumes: `stream.parse_stream/tool_uses/usage_series`, `runner.EVENTS_FILE/RESULT_FILE/load_status`, `workspace.HARNESS_MARKER/RECORD_FILE`, `ai_rfc_server.paths.Context`, `ai_rfc_server.core.gates.manifest_gate/citation_gate`, `panther…a_rfc.report.build/to_json`, `panther…a_rfc.schema.load`.
- Produces: `window_clusters(workspace) -> list[dict]`; `cluster_artifacts(workspace, cluster) -> dict` (`cluster_id, ordinal, checkpoint, pre_seeded, revision_tag, normative_change, tag_exists, artifacts`); `run_gates(workspace, campaign) -> dict` (`manifest_exit, citation_exit, manifest_findings, citation_findings, clean`); `claim_stats(workspace, cluster_id, campaign) -> dict | None`; `checkpoint_calls(events, arm) -> list[dict]` (`index, cluster_id`); `trajectory(events, arm, completed, window_size) -> dict` (`points, tokens_to_first_completion, total_tokens, auc`); `analyze_run(campaign, run_id) -> dict`; `analyze_campaign(campaign) -> dict` (writes `analysis/aggregate.json`); `DEFINITIONS: dict[str, str]`.

- [ ] **Step 1: Add the `overstate` step to the fake** — in `Session.run`, before the final `else`:

```python
        elif kind == "overstate":
            import yaml

            manifest = self.workspace / "manifest.yaml"
            document = yaml.safe_load(manifest.read_text())
            document["requirements"][step["id"]]["status"] = "confirmed"
            manifest.write_text(yaml.safe_dump(document, sort_keys=True))
            self.edit("manifest.yaml", step)
```

- [ ] **Step 2: Write the failing tests** (`$R/experiment/tests/test_metrics.py`):

```python
import json

from experiment.audit import audit_campaign
from experiment.matrix import execute
from experiment.metrics import (
    analyze_campaign,
    analyze_run,
    checkpoint_calls,
    trajectory,
)
from experiment.stream import parse_stream

from .conftest import COMPLETE_STEPS


def _run(campaign, write_scenario, scenarios):
    for run_id, payload in scenarios.items():
        write_scenario(campaign.profile_dir, run_id, payload)
    execute(campaign, only=list(scenarios), report=lambda _: None)
    audit_campaign(campaign)


def test_complete_run_scores_full_completion(campaign, write_scenario):
    _run(campaign, write_scenario, {"A1": {"arm": "A", "cost": 1.0, "steps": COMPLETE_STEPS}})
    result = analyze_run(campaign, "A1")
    assert result["window_size"] == 1
    (cluster,) = result["clusters"]
    assert cluster["checkpoint"] and not cluster["pre_seeded"]
    assert cluster["revision_tag"] == "draft-test-fixture-00" and cluster["tag_exists"]
    assert cluster["artifacts"] and cluster["completed"]
    assert result["gates"]["clean"] and result["gates"]["manifest_exit"] == 0
    assert result["artifacts_fraction"] == 1.0 and result["completed_fraction"] == 1.0
    stats = result["claims"][cluster["cluster_id"]]
    assert stats["claim_count"] == 1 and stats["count_by_supported"] == {"inferred": 1}
    assert stats["unverified_anchors"] == 0 and stats["checked_fraction_by_req_class"]
    assert result["cost"]["total_cost_usd"] == 1.0 and result["cost"]["num_turns"] == 7
    assert result["trajectory"]["tokens_to_first_completion"] > 0
    assert 0.0 < result["trajectory"]["auc"] <= 1.0
    assert result["trajectory"]["points"][0]["cluster_id"] == cluster["cluster_id"]
    assert result["audit"]["integrity"] is True


def test_incomplete_run_scores_zero(campaign, write_scenario):
    steps = [{"kind": "claim", "id": "t:3.1", "section": "3.1"}, {"kind": "checkpoint", "ordinal": 2}]
    _run(campaign, write_scenario, {"B1": {"arm": "B", "cost": 0.3, "steps": steps}})
    result = analyze_run(campaign, "B1")
    (cluster,) = result["clusters"]
    assert cluster["checkpoint"] and cluster["revision_tag"] is None and not cluster["artifacts"]
    assert result["completed_fraction"] == 0.0 and result["gates"]["clean"]
    assert result["trajectory"]["tokens_to_first_completion"] is None
    assert result["trajectory"]["auc"] == 0.0


def test_gate_failure_after_tagging_zeroes_completion(campaign, write_scenario):
    steps = COMPLETE_STEPS + [{"kind": "overstate", "id": "t:3.1"}]
    _run(campaign, write_scenario, {"C1": {"arm": "C", "cost": 0.9, "steps": steps}})
    result = analyze_run(campaign, "C1")
    (cluster,) = result["clusters"]
    assert cluster["artifacts"] and not cluster["completed"]
    assert result["gates"]["manifest_exit"] == 2 and not result["gates"]["clean"]
    assert result["artifacts_fraction"] == 1.0 and result["completed_fraction"] == 0.0
    assert result["audit"]["hand_edits"]["manifest.yaml"] == 3


def test_analyze_campaign_aggregates_per_arm(campaign, write_scenario):
    _run(
        campaign,
        write_scenario,
        {
            "A1": {"arm": "A", "cost": 1.0, "steps": COMPLETE_STEPS},
            "B1": {"arm": "B", "cost": 0.4, "exit_code": 3, "steps": []},
            "C1": {"arm": "C", "cost": 1.1, "steps": COMPLETE_STEPS},
        },
    )
    aggregate = analyze_campaign(campaign)
    assert set(aggregate["runs"]) == {"A1", "B1", "C1"}
    arms = aggregate["arms"]
    assert arms["A"]["completed_fraction_mean"] == 1.0 and arms["B"]["completed_fraction_mean"] == 0.0
    assert arms["B"]["failure_cost_share"] == 1.0 and arms["A"]["failure_cost_share"] == 0.0
    assert arms["A"]["pass_k_mean"] == 1.0 and arms["C"]["cost_per_completed_cluster"] == 1.1
    assert arms["A"]["integrity_rate"] == 1.0 and arms["A"]["runs"] == 1
    assert aggregate["definitions"]["completed"]
    stored = json.loads((campaign.analysis_dir / "aggregate.json").read_text())
    assert stored == aggregate


def test_trajectory_points_follow_checkpoint_calls():
    events = parse_stream(
        '{"type":"assistant","message":{"id":"m1","content":[{"type":"text","text":"a"}],"usage":{"input_tokens":100,"output_tokens":10}}}\n'
        '{"type":"assistant","message":{"id":"m2","content":[{"type":"tool_use","id":"t1","name":"Bash","input":{"command":"arfc checkpoint c0002-x"}}],"usage":{"input_tokens":50,"output_tokens":5}}}\n'
        '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t1","is_error":false,"content":"{}"}]}}\n'
        '{"type":"assistant","message":{"id":"m3","content":[{"type":"text","text":"done"}],"usage":{"input_tokens":30,"output_tokens":5}}}\n'
    )
    assert checkpoint_calls(events, "B") == [{"index": 1, "cluster_id": "c0002-x"}]
    result = trajectory(events, "B", {"c0002-x"}, window_size=2)
    assert result["total_tokens"] == 200
    assert result["points"] == [{"index": 1, "cluster_id": "c0002-x", "cumulative_tokens": 165, "completed_so_far": 1}]
    assert result["tokens_to_first_completion"] == 165
    assert abs(result["auc"] - 0.5 * (1 - 165 / 200)) < 1e-9
    assert trajectory(events, "B", set(), window_size=2)["auc"] == 0.0
```

- [ ] **Step 3: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_metrics.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'experiment.metrics'`.

- [ ] **Step 4: Implement `$R/experiment/metrics.py`**

```python
"""Recompute every outcome from artifacts: workspace state, transcript, result.

Nothing here trusts the model's own account. Cluster completion is read
from checkpoints, revision entries and tags; the strict gates are re-run by
the harness on a scratch copy of the final workspace; cost and tokens come
from the result event; per-cluster attribution aligns cumulative usage with
the checkpoint calls in the transcript. ``analyze`` is idempotent.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from . import ExperimentError
from .config import Campaign
from .runner import EVENTS_FILE, RESULT_FILE, load_status
from .stream import parse_stream, tool_uses, usage_series
from .workspace import HARNESS_MARKER, RECORD_FILE

DEFINITIONS = {
    "artifacts": "checkpoint exists without a harness marker AND a revisions.yaml entry names the cluster AND that entry's tag exists in draft/",
    "completed": "artifacts AND both strict gates exit 0 when the harness re-runs them on the final workspace (run-level)",
    "completed_fraction": "completed clusters / window size (primary outcome, D23)",
    "pass_k": "per cluster: completed in every repeat of the arm; pass_k_mean averages over the window",
    "integrity_rate": "runs whose audit found no executed out-of-arm call / runs",
    "failure_cost_share": "sum of total_cost_usd over runs with zero completed clusters / sum over all runs of the arm",
    "cost_per_completed_cluster": "sum of total_cost_usd / sum of completed clusters (None when nothing completed)",
    "tokens_to_first_completion": "cumulative tokens (input+output+cache_creation+cache_read) at the checkpoint call of the first cluster that ends up completed",
    "auc": "integral over normalized cumulative tokens of completed_so_far/window_size, as a right-continuous step function",
    "checked_fraction": "the substrate's honesty metric, reported per checkpoint; expected 0.0 without interviews or runtime anchors",
}
_USAGE_KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def _substrate(campaign: Campaign) -> None:
    for entry in (str(campaign.server_src), str(campaign.panther_repo)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def window_clusters(workspace: Path) -> list[dict[str, Any]]:
    """The timeline rows inside the pristine record's window, in ordinal order."""
    record = json.loads((workspace / RECORD_FILE).read_text())
    low, high = record["window"]
    rows = [
        json.loads(line)
        for line in (workspace / "timeline" / "clusters.jsonl").read_text().splitlines()
    ]
    return [row for row in rows if low <= row["ordinal"] <= high]


def _tags(draft: Path) -> set[str]:
    result = subprocess.run(["git", "-C", str(draft), "tag", "-l"], capture_output=True, text=True)
    return set(result.stdout.split()) if result.returncode == 0 else set()


def cluster_artifacts(workspace: Path, cluster: dict[str, Any]) -> dict[str, Any]:
    """What the workspace holds for one cluster, read from disk only."""
    checkpoint_dir = workspace / "checkpoints" / cluster["id"]
    checkpoint = (checkpoint_dir / "checkpoint.json").exists()
    pre_seeded = (checkpoint_dir / HARNESS_MARKER).exists()
    document = yaml.safe_load((workspace / "revisions.yaml").read_text()) or {}
    entries = [
        (str(tag), body)
        for tag, body in (document.get("revisions") or {}).items()
        if isinstance(body, dict) and body.get("cluster_id") == cluster["id"]
    ]
    tag, body = entries[0] if entries else (None, None)
    tag_exists = tag in _tags(workspace / "draft") if tag else False
    return {
        "cluster_id": cluster["id"],
        "ordinal": cluster["ordinal"],
        "kind": cluster.get("kind"),
        "provenance": cluster.get("provenance"),
        "checkpoint": checkpoint,
        "pre_seeded": pre_seeded,
        "revision_tag": tag,
        "normative_change": None if body is None else bool(body.get("normative_change")),
        "tag_exists": tag_exists,
        "artifacts": checkpoint and not pre_seeded and tag is not None and tag_exists,
    }


def run_gates(workspace: Path, campaign: Campaign) -> dict[str, Any]:
    """Re-run both strict gates on a scratch copy of the final workspace."""
    _substrate(campaign)
    from ai_rfc_server.core.gates import citation_gate, manifest_gate
    from ai_rfc_server.paths import Context

    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch) / "workspace"
        shutil.copytree(workspace, copy, symlinks=False)
        ctx = Context(panther_repo=campaign.panther_repo, workspace=copy)
        manifest = manifest_gate(ctx, strict=True)
        citation = citation_gate(ctx, strict=True)
    return {
        "manifest_exit": manifest["exit_code"],
        "citation_exit": citation["exit_code"],
        "manifest_findings": manifest["stderr"],
        "citation_findings": citation["findings"],
        "clean": manifest["exit_code"] == 0 and citation["exit_code"] == 0,
    }


def claim_stats(workspace: Path, cluster_id: str, campaign: Campaign) -> dict[str, Any] | None:
    """The substrate's report over one checkpoint manifest, anchors verified."""
    manifest_path = workspace / "checkpoints" / cluster_id / "manifest.yaml"
    if not manifest_path.exists():
        return None
    _substrate(campaign)
    from panther.plugins.services.testers.a_rfc import report, schema

    payload = json.loads(report.to_json(report.build(schema.load(manifest_path), repo=workspace / "clone")))
    return {
        "claim_count": len(payload["claims"]),
        "count_by_status": payload["count_by_status"],
        "count_by_supported": dict(sorted(Counter(c["supported"] for c in payload["claims"]).items())),
        "promotable_count": payload.get("promotable_count"),
        "unverified_anchors": len(payload.get("unverified_anchors", [])),
        "violations": len(payload.get("violations", [])),
        "checked_fraction_by_req_class": payload["checked_fraction_by_req_class"],
    }


def _cluster_of_call(arm: str, name: str, tool_input: dict[str, Any]) -> str | None:
    command = str(tool_input.get("command", "")).strip()
    if arm == "A" and name == "mcp__arfc__arfc_checkpoint":
        return str(tool_input.get("cluster_id") or "")
    if arm == "B" and name == "Bash" and command.startswith("arfc checkpoint"):
        parts = command.split()
        return parts[2] if len(parts) > 2 else ""
    if arm == "C" and name == "Bash" and ".draft checkpoint" in command and "--cluster" in command:
        parts = command.split()
        return parts[parts.index("--cluster") + 1] if parts.index("--cluster") + 1 < len(parts) else ""
    return None


def checkpoint_calls(events: list[dict[str, Any]], arm: str) -> list[dict[str, Any]]:
    """Every checkpoint call in the transcript, with the cluster it named."""
    calls = []
    for use in tool_uses(events):
        cluster = _cluster_of_call(arm, use["name"], use["input"])
        if cluster:
            calls.append({"index": use["index"], "cluster_id": cluster})
    return calls


def trajectory(
    events: list[dict[str, Any]], arm: str, completed: set[str], window_size: int
) -> dict[str, Any]:
    """Cumulative tokens at each checkpoint call, tokens-to-first, and the AUC."""
    series = usage_series(events)
    total = series[-1]["total"] if series else 0

    def cumulative_at(index: int) -> int:
        value = 0
        for point in series:
            if point["index"] <= index:
                value = point["total"]
        return value

    points = []
    done = 0
    for call in checkpoint_calls(events, arm):
        if call["cluster_id"] in completed:
            done += 1
        points.append(
            {
                "index": call["index"],
                "cluster_id": call["cluster_id"],
                "cumulative_tokens": cumulative_at(call["index"]),
                "completed_so_far": done,
            }
        )
    first = next((p["cumulative_tokens"] for p in points if p["completed_so_far"] >= 1), None)
    auc = 0.0
    if total and window_size:
        steps = [(0.0, 0.0)] + [
            (p["cumulative_tokens"] / total, p["completed_so_far"] / window_size) for p in points
        ]
        steps.append((1.0, steps[-1][1]))
        for (x0, y0), (x1, _) in zip(steps, steps[1:]):
            auc += y0 * max(0.0, x1 - x0)
    return {
        "points": points,
        "tokens_to_first_completion": first,
        "total_tokens": total,
        "auc": auc,
    }


def analyze_run(campaign: Campaign, run_id: str) -> dict[str, Any]:
    """Every outcome of one run, recomputed from its artifacts."""
    run_dir = campaign.runs_dir / run_id
    status = load_status(run_dir)
    if status is None:
        raise ExperimentError(f"{run_id} has no status record; nothing to analyze")
    workspace = run_dir / "workspace"
    events = parse_stream((run_dir / EVENTS_FILE).read_text(errors="replace"))
    final = json.loads((run_dir / RESULT_FILE).read_text()) or {}
    clusters = [cluster_artifacts(workspace, row) for row in window_clusters(workspace)]
    gates = run_gates(workspace, campaign)
    for cluster in clusters:
        cluster["completed"] = bool(cluster["artifacts"] and gates["clean"])
    completed = {c["cluster_id"] for c in clusters if c["completed"]}
    window_size = len(clusters)
    audit_path = campaign.audit_dir / f"{run_id}.json"
    return {
        "run_id": run_id,
        "arm": status.arm,
        "repeat": status.repeat,
        "status": asdict(status),
        "window_size": window_size,
        "clusters": clusters,
        "artifacts_fraction": sum(1 for c in clusters if c["artifacts"]) / window_size if window_size else 0.0,
        "completed_fraction": len(completed) / window_size if window_size else 0.0,
        "gates": gates,
        "claims": {
            c["cluster_id"]: claim_stats(workspace, c["cluster_id"], campaign)
            for c in clusters
            if c["checkpoint"] and not c["pre_seeded"]
        },
        "cost": {
            "total_cost_usd": final.get("total_cost_usd"),
            "usage": final.get("usage"),
            "model_usage": final.get("modelUsage"),
            "num_turns": final.get("num_turns"),
            "duration_ms": final.get("duration_ms"),
            "duration_api_ms": final.get("duration_api_ms"),
            "subtype": final.get("subtype"),
        },
        "trajectory": trajectory(events, status.arm, completed, window_size),
        "audit": json.loads(audit_path.read_text()) if audit_path.exists() else None,
    }


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _arm_summary(runs: list[dict[str, Any]], window_ids: list[str], repeats: int) -> dict[str, Any]:
    costs = [r["cost"]["total_cost_usd"] or 0.0 for r in runs]
    completed_counts = [sum(1 for c in r["clusters"] if c["completed"]) for r in runs]
    failed_cost = sum(cost for cost, done in zip(costs, completed_counts) if done == 0)
    audits = [r["audit"] for r in runs if r["audit"] is not None]
    pass_k = {
        cluster_id: (
            len(runs) == repeats
            and all(any(c["cluster_id"] == cluster_id and c["completed"] for c in r["clusters"]) for r in runs)
        )
        for cluster_id in window_ids
    }
    firsts = [r["trajectory"]["tokens_to_first_completion"] for r in runs if r["trajectory"]["tokens_to_first_completion"]]
    return {
        "runs": len(runs),
        "completed_fraction_mean": _mean([r["completed_fraction"] for r in runs]),
        "completed_fraction_min": min((r["completed_fraction"] for r in runs), default=None),
        "artifacts_fraction_mean": _mean([r["artifacts_fraction"] for r in runs]),
        "gates_clean_runs": sum(1 for r in runs if r["gates"]["clean"]),
        "pass_k": pass_k,
        "pass_k_mean": _mean([1.0 if v else 0.0 for v in pass_k.values()]),
        "integrity_rate": _mean([1.0 if a["integrity"] else 0.0 for a in audits]),
        "bypass_attempts": sum(a["bypass_attempts"]["count"] for a in audits),
        "errors_class1": sum(a["errors"]["class1"] for a in audits),
        "errors_class2": sum(a["errors"]["class2"] for a in audits),
        "hand_edits": sum(sum(a["hand_edits"].values()) for a in audits),
        "cost_total": sum(costs),
        "cost_mean": _mean(costs),
        "failure_cost_share": (failed_cost / sum(costs)) if sum(costs) else None,
        "cost_per_completed_cluster": (sum(costs) / sum(completed_counts)) if sum(completed_counts) else None,
        "tokens_to_first_completion_mean": _mean(firsts),
        "auc_mean": _mean([r["trajectory"]["auc"] for r in runs]),
        "timed_out_runs": sum(1 for r in runs if r["status"]["timed_out"]),
        "nonzero_exit_runs": sum(1 for r in runs if r["status"]["exit_code"] not in (0, None)),
    }


def analyze_campaign(campaign: Campaign) -> dict[str, Any]:
    """Analyze every run with a status record and write ``analysis/aggregate.json``."""
    runs = {
        run_id: analyze_run(campaign, run_id)
        for run_id in campaign.run_order
        if load_status(campaign.runs_dir / run_id) is not None
    }
    window_ids: list[str] = []
    for result in runs.values():
        window_ids = [c["cluster_id"] for c in result["clusters"]]
        break
    arms = {
        arm: _arm_summary([r for r in runs.values() if r["arm"] == arm], window_ids, campaign.repeats)
        for arm in campaign.arms
        if any(r["arm"] == arm for r in runs.values())
    }
    aggregate = {
        "campaign": campaign.id,
        "target": campaign.target,
        "window": list(campaign.window),
        "model": campaign.model,
        "effort": campaign.effort,
        "claude_version": campaign.claude_version,
        "git": campaign.git,
        "parity_pre_run": campaign.parity,
        "run_order": list(campaign.run_order),
        "runs": runs,
        "arms": arms,
        "definitions": DEFINITIONS,
    }
    campaign.analysis_dir.mkdir(exist_ok=True)
    (campaign.analysis_dir / "aggregate.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n")
    return aggregate
```

- [ ] **Step 5: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 97 passed (91 + 6) — includes the pass^k-at-k=2 test.

- [ ] **Step 6: Commit (nested repo)**

```bash
git -C $R add experiment/metrics.py experiment/tests/test_metrics.py experiment/tests/fake_claude/claude
git -C $R commit -m "feat: state-verified metrics recomputed from run artifacts"
```

### Task 7: `experiment/report.py` and the campaign CLI (`campaign init`, `run`, `audit`, `analyze`)

**Files:**
- Create: `$R/experiment/report.py`, `$R/experiment/tests/test_report.py`, `$R/experiment/tests/test_cli_campaign.py`
- Modify: `$R/experiment/cli.py`

**Interfaces:**
- Produces: `report.render_report(aggregate: dict) -> str` (markdown: header, per-arm table, per-run table, per-cluster pass^k table, definitions); CLI verbs `campaign init --root --id --pristine <name|path> [--arms A,B,C] [--repeats 2] [--seed 20260826] [--model claude-opus-5] [--effort high] [--budget 25] [--timeout 7200] --panther-repo W [--plugin-dir] [--python] [--claude claude] [--skip-parity]` (exit 2 when the parity pre-run fails), `run <campaign-dir> [--only A1,B1]`, `audit <campaign-dir>`, `analyze <campaign-dir>` (writes `analysis/aggregate.json` and `analysis/report.md`); helpers `cli._default_plugin_dir() -> Path`, `cli._run_parity(plugin_dir, python) -> dict` (`{passed, summary}`).

- [ ] **Step 1: Write the failing tests**

`$R/experiment/tests/test_report.py`:

```python
from experiment.report import render_report


def _aggregate():
    cluster = {"cluster_id": "c0002-x", "ordinal": 2, "completed": True, "artifacts": True}
    run = {
        "run_id": "A1", "arm": "A", "repeat": 1,
        "status": {"exit_code": 0, "timed_out": False},
        "window_size": 1, "clusters": [cluster],
        "artifacts_fraction": 1.0, "completed_fraction": 1.0,
        "gates": {"manifest_exit": 0, "citation_exit": 0, "clean": True},
        "cost": {"total_cost_usd": 1.25, "num_turns": 7, "duration_ms": 7000, "usage": {"input_tokens": 700, "output_tokens": 140, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}},
        "trajectory": {"auc": 0.4, "tokens_to_first_completion": 500, "total_tokens": 840, "points": []},
        "audit": {"integrity": True, "bypass_attempts": {"count": 0}, "errors": {"class1": 0, "class2": 0}},
    }
    arm = {
        "runs": 1, "completed_fraction_mean": 1.0, "completed_fraction_min": 1.0, "artifacts_fraction_mean": 1.0,
        "gates_clean_runs": 1, "pass_k": {"c0002-x": True}, "pass_k_mean": 1.0, "integrity_rate": 1.0,
        "bypass_attempts": 0, "errors_class1": 0, "errors_class2": 0, "hand_edits": 0, "cost_total": 1.25,
        "cost_mean": 1.25, "failure_cost_share": 0.0, "cost_per_completed_cluster": 1.25,
        "tokens_to_first_completion_mean": 500.0, "auc_mean": 0.4, "timed_out_runs": 0, "nonzero_exit_runs": 0,
    }
    return {
        "campaign": "pilot-test", "target": "fixture", "window": [2, 2], "model": "m", "effort": "high",
        "claude_version": "fake-claude 0.0.0", "git": {"panther": "abc", "ai_rfc": "def"},
        "parity_pre_run": {"passed": True, "summary": "ok"}, "run_order": ["A1"],
        "runs": {"A1": run}, "arms": {"A": arm}, "definitions": {"completed": "artifacts AND gates"},
    }


def test_render_report_has_every_section_and_the_numbers():
    text = render_report(_aggregate())
    assert text.startswith("# Campaign pilot-test\n")
    for heading in ("## Per arm", "## Per run", "## Per cluster (pass^k)", "## Definitions"):
        assert heading in text
    assert "| A | 1 | 1.000 / 1.000 |" in text
    assert "| A1 | A | 0 | no | 1/1 |" in text
    assert "| c0002-x | ✓ |" in text
    assert "- **completed**: artifacts AND gates" in text
    assert "fake-claude 0.0.0" in text and "abc" in text


def test_render_report_tolerates_missing_values():
    aggregate = _aggregate()
    aggregate["arms"]["A"]["cost_per_completed_cluster"] = None
    aggregate["runs"]["A1"]["audit"] = None
    text = render_report(aggregate)
    assert "—" in text
```

`$R/experiment/tests/test_cli_campaign.py`:

```python
import json
import sys

from experiment import cli

from .conftest import COMPLETE_STEPS, FAKE_CLAUDE


def _init(tmp_path, pristine, panther_repo, capsys, *extra):
    code = cli.main(
        [
            "campaign", "init", "--root", str(tmp_path / "root"), "--id", "pilot-test",
            "--pristine", str(pristine), "--repeats", "1", "--seed", "3", "--model", "fake",
            "--budget", "1", "--timeout", "60", "--panther-repo", str(panther_repo),
            "--python", sys.executable, "--claude", str(FAKE_CLAUDE), "--skip-parity", *extra,
        ]
    )
    out = capsys.readouterr().out
    return code, out, tmp_path / "root" / "campaigns" / "pilot-test"


def test_campaign_init_run_audit_analyze_round_trip(tmp_path, pristine, panther_repo, write_scenario, capsys):
    code, out, campaign_dir = _init(tmp_path, pristine, panther_repo, capsys)
    assert code == 0 and "run order:" in out and campaign_dir.exists()
    order = json.loads((campaign_dir / "campaign.json").read_text())["run_order"]
    for run_id in order:
        write_scenario(tmp_path / "root" / "profile", run_id, {"arm": run_id[0], "cost": 1.0, "steps": COMPLETE_STEPS})
    assert cli.main(["run", str(campaign_dir), "--only", order[0]]) == 0
    assert cli.main(["run", str(campaign_dir)]) == 0
    err = capsys.readouterr().err
    assert err.count("launching") == 3 and "skipping" in err
    assert cli.main(["audit", str(campaign_dir)]) == 0
    assert "integrity=True" in capsys.readouterr().out
    assert cli.main(["analyze", str(campaign_dir)]) == 0
    assert (campaign_dir / "analysis" / "aggregate.json").exists()
    report = (campaign_dir / "analysis" / "report.md").read_text()
    assert "# Campaign pilot-test" in report and "| A |" in report


def test_run_parity_reports_the_suite(plugin_root):
    result = cli._run_parity(plugin_root, sys.executable)
    assert result["passed"] is True and "passed" in result["summary"]


def test_campaign_init_refuses_unknown_pristine(tmp_path, panther_repo, capsys):
    code = cli.main(
        ["campaign", "init", "--root", str(tmp_path / "root"), "--id", "x", "--pristine", "nope",
         "--panther-repo", str(panther_repo), "--claude", str(FAKE_CLAUDE), "--skip-parity"]
    )
    assert code == 1 and "not a prepared pristine workspace" in capsys.readouterr().err
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests/test_report.py experiment/tests/test_cli_campaign.py -q`
Expected: FAIL (`ModuleNotFoundError: experiment.report`; `argparse` "invalid choice: 'campaign'").

- [ ] **Step 3: Implement `$R/experiment/report.py`**

```python
"""Render a campaign aggregate as markdown, every formula named."""

from __future__ import annotations

from typing import Any


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _arm_rows(arms: dict[str, dict[str, Any]]) -> list[str]:
    header = (
        "| arm | runs | completed (mean / min) | artifacts mean | pass^k mean | integrity | "
        "bypass | errors c1/c2 | hand edits | cost total / mean | failure-cost share | "
        "cost per completed | tokens→first | AUC mean | timeouts | nonzero exits |"
    )
    rows = [header, "|" + "---|" * 16]
    for arm, s in arms.items():
        rows.append(
            f"| {arm} | {s['runs']} | {_fmt(s['completed_fraction_mean'])} / {_fmt(s['completed_fraction_min'])} | "
            f"{_fmt(s['artifacts_fraction_mean'])} | {_fmt(s['pass_k_mean'])} | {_fmt(s['integrity_rate'])} | "
            f"{s['bypass_attempts']} | {s['errors_class1']}/{s['errors_class2']} | {s['hand_edits']} | "
            f"{_fmt(s['cost_total'], 2)} / {_fmt(s['cost_mean'], 2)} | {_fmt(s['failure_cost_share'])} | "
            f"{_fmt(s['cost_per_completed_cluster'], 2)} | {_fmt(s['tokens_to_first_completion_mean'], 0)} | "
            f"{_fmt(s['auc_mean'])} | {s['timed_out_runs']} | {s['nonzero_exit_runs']} |"
        )
    return rows


def _run_rows(runs: dict[str, dict[str, Any]]) -> list[str]:
    rows = [
        "| run | arm | exit | timed out | completed/window | artifacts | gates m/c | cost | turns | tokens | duration ms | integrity | bypass | errors c1/c2 |",
        "|" + "---|" * 14,
    ]
    for run_id, r in runs.items():
        usage = r["cost"].get("usage") or {}
        tokens = sum(int(usage.get(k, 0) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        audit = r.get("audit") or {}
        completed = sum(1 for c in r["clusters"] if c.get("completed"))
        artifacts = sum(1 for c in r["clusters"] if c.get("artifacts"))
        rows.append(
            f"| {run_id} | {r['arm']} | {_fmt(r['status']['exit_code'])} | {_fmt(r['status']['timed_out'])} | "
            f"{completed}/{r['window_size']} | {artifacts} | {r['gates']['manifest_exit']}/{r['gates']['citation_exit']} | "
            f"{_fmt(r['cost'].get('total_cost_usd'), 2)} | {_fmt(r['cost'].get('num_turns'))} | {tokens} | "
            f"{_fmt(r['cost'].get('duration_ms'))} | {_fmt(audit.get('integrity'))} | "
            f"{_fmt((audit.get('bypass_attempts') or {}).get('count'))} | "
            f"{_fmt((audit.get('errors') or {}).get('class1'))}/{_fmt((audit.get('errors') or {}).get('class2'))} |"
        )
    return rows


def _cluster_rows(arms: dict[str, dict[str, Any]]) -> list[str]:
    names = list(arms)
    cluster_ids: list[str] = []
    for s in arms.values():
        for cluster_id in s["pass_k"]:
            if cluster_id not in cluster_ids:
                cluster_ids.append(cluster_id)
    rows = ["| cluster | " + " | ".join(names) + " |", "|" + "---|" * (len(names) + 1)]
    for cluster_id in cluster_ids:
        marks = " | ".join("✓" if arms[a]["pass_k"].get(cluster_id) else "✗" for a in names)
        rows.append(f"| {cluster_id} | {marks} |")
    return rows


def render_report(aggregate: dict[str, Any]) -> str:
    """The human-facing summary of ``aggregate.json``; every number traces to it."""
    git = aggregate.get("git") or {}
    lines = [
        f"# Campaign {aggregate['campaign']}",
        "",
        f"- target: `{aggregate['target']}`, window {aggregate['window']}",
        f"- model: `{aggregate['model']}`, effort `{aggregate['effort']}`, harness `{aggregate['claude_version']}`",
        f"- git: PANTHER `{git.get('panther')}`, ai_rfc `{git.get('ai_rfc')}`",
        f"- parity pre-run: {aggregate.get('parity_pre_run')}",
        f"- run order: {', '.join(aggregate['run_order'])}",
        "",
        "## Per arm",
        "",
        *_arm_rows(aggregate["arms"]),
        "",
        "## Per run",
        "",
        *_run_rows(aggregate["runs"]),
        "",
        "## Per cluster (pass^k)",
        "",
        *_cluster_rows(aggregate["arms"]),
        "",
        "## Definitions",
        "",
        *[f"- **{key}**: {value}" for key, value in aggregate["definitions"].items()],
    ]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Extend `experiment/cli.py`** — add near the top:

```python
import os
import subprocess


def _default_plugin_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "plugins" / "ai-rfc"


def _run_parity(plugin_dir: Path, python: str) -> dict:
    """Run the server parity suite; the protocol's stop-ship construct check."""
    env = {**os.environ, "SSLKEYLOGFILE": ""}
    completed = subprocess.run(
        [python, "-m", "pytest", "-q", "tests/test_parity.py"],
        cwd=plugin_dir / "server",
        capture_output=True,
        text=True,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    return {"passed": completed.returncode == 0, "summary": lines[-1] if lines else completed.stderr[-200:]}
```

(replace the two inline `Path(__file__).resolve().parents[1] / "plugins" / "ai-rfc"` expressions in the `spike` and `render` branches with `_default_plugin_dir()`), add the parsers:

```python
    campaign = commands.add_parser("campaign", help="Frozen run matrices.")
    campaign_verbs = campaign.add_subparsers(dest="verb", required=True)
    init = campaign_verbs.add_parser("init", help="Freeze a campaign.")
    _add_root(init)
    init.add_argument("--id", required=True)
    init.add_argument("--pristine", required=True, help="Name under <root>/pristine, or a path.")
    init.add_argument("--arms", default="A,B,C")
    init.add_argument("--repeats", type=int, default=2)
    init.add_argument("--seed", type=int, default=20260826)
    init.add_argument("--model", default="claude-opus-5")
    init.add_argument("--effort", default="high")
    init.add_argument("--budget", type=float, default=25.0)
    init.add_argument("--timeout", type=int, default=7200)
    init.add_argument("--panther-repo", type=Path, required=True)
    init.add_argument("--plugin-dir", type=Path, default=None)
    init.add_argument("--python", default=sys.executable)
    init.add_argument("--claude", default="claude")
    init.add_argument("--skip-parity", action="store_true")

    run = commands.add_parser("run", help="Launch pending runs in the frozen order.")
    run.add_argument("campaign", type=Path)
    run.add_argument("--only", default=None, help="Comma-separated run ids.")

    audit = commands.add_parser("audit", help="Audit every run's transcript.")
    audit.add_argument("campaign", type=Path)

    analyze = commands.add_parser("analyze", help="Recompute outcomes; write aggregate.json and report.md.")
    analyze.add_argument("campaign", type=Path)
```

and the dispatch branches:

```python
        elif args.command == "campaign" and args.verb == "init":
            from .config import init_campaign

            plugin_dir = (args.plugin_dir or _default_plugin_dir()).resolve()
            pristine = Path(args.pristine)
            if not pristine.is_absolute():
                pristine = root / "pristine" / args.pristine
            parity = None if args.skip_parity else _run_parity(plugin_dir, args.python)
            campaign = init_campaign(
                root=root,
                campaign_id=args.id,
                pristine_dir=pristine,
                arms=tuple(args.arms.split(",")),
                repeats=args.repeats,
                seed=args.seed,
                model=args.model,
                effort=args.effort,
                budget_usd=args.budget,
                timeout_s=args.timeout,
                panther_repo=args.panther_repo.resolve(),
                plugin_root=plugin_dir,
                python=args.python,
                claude_bin=args.claude,
                parity=parity,
            )
            print(f"campaign: {campaign.dir}")
            print(f"run order: {' '.join(campaign.run_order)}")
            print(f"parity: {parity}")
            if parity is not None and not parity["passed"]:
                _report("parity suite FAILED — stop-ship per protocol")
                return 2
        elif args.command == "run":
            from .config import load_campaign
            from .matrix import execute

            statuses = execute(
                load_campaign(args.campaign.resolve()),
                only=args.only.split(",") if args.only else None,
                report=_report,
            )
            for status in statuses:
                print(f"{status.run_id}: exit={status.exit_code} timed_out={status.timed_out}")
        elif args.command == "audit":
            from .audit import audit_campaign
            from .config import load_campaign

            for run_id, audit in audit_campaign(load_campaign(args.campaign.resolve())).items():
                print(
                    f"{run_id}: integrity={audit['integrity']} "
                    f"bypass={audit['bypass_attempts']['count']} "
                    f"errors={audit['errors']['class1']}/{audit['errors']['class2']}"
                )
        elif args.command == "analyze":
            from .audit import audit_campaign
            from .config import load_campaign
            from .metrics import analyze_campaign
            from .report import render_report

            campaign = load_campaign(args.campaign.resolve())
            audit_campaign(campaign)
            aggregate = analyze_campaign(campaign)
            report_path = campaign.analysis_dir / "report.md"
            report_path.write_text(render_report(aggregate))
            print(f"aggregate: {campaign.analysis_dir / 'aggregate.json'}")
            print(f"report: {report_path}")
```

- [ ] **Step 5: Run the tests**

Run: `cd $R && SSLKEYLOGFILE= $PY -m pytest experiment/tests -q`
Expected: 103 passed (97 + 6) — includes the undecided-cluster rendering test.

- [ ] **Step 6: Commit (nested repo)**

```bash
git -C $R add experiment/report.py experiment/cli.py experiment/tests/test_report.py experiment/tests/test_cli_campaign.py
git -C $R commit -m "feat: campaign CLI with markdown report"
```

### Task 8: The aioquic pilot — launch, audit, analyze, deliverables

Spec §7. Real model, real subscription time: every step below that spends is a confirmation point.

**Files:**
- Create (nested repo): `$R/docs/experiments/<date>-pilot-aioquic.md`, `$R/docs/experiments/<date>-pilot-aioquic/{aggregate.json,campaign.json,diff-A-B.patch,diff-A-C.patch,diff-B-C.patch,report.md}`
- Modify (nested repo): `$R/docs/experiment-protocol.md` (§3 amendment, §6 pilot-derived defaults), `$R/README.md` (one line pointing at the pilot report)
- Modify (PANTHER): submodule pointer

- [ ] **Step 0: Prove the guard survives the runner's own mount (added 2026-08-28)**

Spike S0 proved a real CLI honours a guard mounted from `~/arfc-experiments/spike/`;
nothing has yet proved it honours one mounted at `runs/<id>/guard.json` under
`--setting-sources project`. That single assumption stands between the measured
enforcement result and six paid runs, and one cheap live call settles it.

Build an arm-C argv with `runner.build_run_argv` against a throwaway campaign, run
it with the prompt `Run: echo bypass-probe. Then run: git --version.`, and read the
transcript: the `echo` must be refused (an errored `tool_result` starting
`PreToolUse:Bash hook error:` and a `permission_denials` entry) while `git --version`
runs. If the `echo` executes, **STOP** — the arms are not separated and the pilot
would measure nothing.

- [ ] **Step 1: Freeze the campaign (runs the parity pre-run; no model calls yet)**

Run: `cd $R && export DATE=$(date +%Y%m%d) && $PY -m experiment campaign init --root ~/arfc-experiments --id pilot-aioquic-w02-11-$DATE --pristine aioquic-w02-11 --repeats 2 --seed 20260826 --model claude-opus-5 --effort high --budget 25 --timeout 7200 --panther-repo $W`
Expected: `campaign: ~/arfc-experiments/campaigns/pilot-aioquic-w02-11-<date>`, a six-id run order with every repeat block holding A, B and C, `parity: {'passed': True, …}`. Then read `prompts/diff-A-B.patch` and `diff-B-C.patch`: every changed line must be an invocation phrase (no accidental prose asymmetry) — if not, STOP, fix the template/tables (foundations Task 8), and re-init under a new id.

- [ ] **Step 2: Confirmation point** — ask the user (AskUserQuestion) before the first launch, stating: six runs, `claude-opus-5` at effort high, `--max-budget-usd 25` per run, 2 h wall cap per run, up to ~12 h sequential, under the isolated OAuth profile. Proceed only on an explicit yes.

- [ ] **Step 3: Launch in the background (sandbox OFF)**

Run: `C=~/arfc-experiments/campaigns/pilot-aioquic-w02-11-$DATE; nohup $PY -m experiment run $C > $C/run.log 2>&1 &` then watch `$C/run.log` (a Monitor on the file for `launching` / `exit` lines is the right tool; each run ends with `<id>: exit … timed_out=… budget_hit=…`). Expected: six `launching` lines and six exit lines over several hours; `runs/<id>/status.json` appears as each run ends.
If the harness process dies mid-run: nothing is deleted; `run` again resumes (complete runs are skipped); a `runs/<id>/` without `status.json` is moved aside first (`mv $C/runs/A1 $C/runs/A1.interrupted-1`) because it is evidence of what happened.

- [ ] **Step 4: Audit and analyze**

> **Two caveats for whoever reads the numbers (added 2026-08-28).** `pass^k` is
> `null` — rendered `—`, not `✗` — for any arm that has not yet run every repeat,
> so a mid-campaign `analyze` cannot be mistaken for a wave of failures; only run
> the final analysis once all six runs carry a `status.json`. And `hand_edits` is
> counted from each call's file path, not from the truncated display summary that
> an earlier draft used; a run whose workspace path exceeds 120 characters used to
> score zero hand edits silently.


Run: `$PY -m experiment audit $C && $PY -m experiment analyze $C && sed -n '1,60p' $C/analysis/report.md`
Expected: six audit lines with `integrity=True` (any `False` is a harness defect: read the `executed_out_of_arm` entries in `audit/<id>.json` before anything else); `aggregate.json` and `report.md` written. Sanity checks to record: for each run, `result.json.total_cost_usd` versus the sum of `usage` token classes; `gates` per run; bypass attempts by surface; first-failure indices; compaction events; wall time from `status.json`.

- [ ] **Step 5: Parity post-run (stop-ship check)**

Run: `cd $S && SSLKEYLOGFILE= $PY -m pytest tests/test_parity.py -q 2>&1 | tail -1`
Expected: all parity tests passed. A failure means the arms' capabilities diverged during the pilot: the pilot's comparison numbers are void (the instrument numbers stand) and the report must say so.

- [ ] **Step 6: Write the pilot report** `$R/docs/experiments/<date>-pilot-aioquic.md` with exactly these sections, every number copied from `aggregate.json`/`report.md`:

```markdown
# aioquic pilot — <date>

## Setup
campaign id · model/effort · `claude --version` · git (PANTHER, ai_rfc) · pristine record (clone HEAD, template commit, pre-seeded count) · run order · budget/timeout · parity pre/post

## Results (instrument numbers, not effect claims)
per-arm table from report.md · per-run table · per-cluster pass^k

## Integrity and enforcement
integrity rate per arm · bypass attempts by surface with 2–3 verbatim examples (tool name + input) · denial mechanism observed (tool_result text / permission_denials) · hand-edit asymmetry counts

## Errors
class-1 / class-2 counts per arm · first-failure indices · the three most common error texts per channel, verbatim

## Cost and time
per run: cost, tokens by class, turns, duration, wall time · projected main-run cost = mean cost per run × (arms × targets × k) for k = 3 and k = 5 · cache share of tokens

## What broke
every harness defect, prompt defect, enforcement surprise, timeout, compaction event — with the run id and the fix or the deferral

## Decisions for the main run
k · budget cap · timeout · task window(s) · exclusion rule for integrity-violated runs · any prompt/template change (re-freeze required) · whether arm C stays

## Threats observed
anything that would bias the main run (rate limits, API errors, time-of-day effects, workspace copy time)
```

Copy `aggregate.json`, `campaign.json`, `report.md` and the three `diff-*.patch` files into `$R/docs/experiments/<date>-pilot-aioquic/`.

- [ ] **Step 7: Amend the protocol (D23) and pre-fill the preregistration**

In `$R/docs/experiment-protocol.md` §3, replace the sentence fragment "final `checked_fraction` derived by analysis code from checkpoint state, and gate-exit events as raw counts with uncertainty (they are discrete and possibly rare)." with:

> per-cluster completion, where a cluster counts as completed when its checkpoint exists, its revision entry and tag exist, and both strict gates exit 0 when the harness re-runs them on the final workspace; the primary metric is completed clusters over the window size, with pass^k over repeats, and gate-exit events are reported as raw counts with uncertainty (they are discrete and possibly rare). The final `checked_fraction` stays reported as the substrate's honesty metric; it moves only through sign-offs and runtime anchors and is therefore identically 0.0 in model-only runs, which is why it cannot serve as the primary outcome (decision D23, 2026-08-26).

Append to §6 a subsection `### Pilot-derived defaults (<date>)` listing, one bullet each: k, per-run budget cap, timeout, the task window(s), the exclusion rule, the enforcement configuration per arm (the `--tools`/`--allowedTools`/MCP table), model id and `claude --version`, prompt digests, and the parity pre/post results — each marked "from the pilot" or "unchanged from the protocol". Add one line to `$R/README.md` under "Experiment harness" pointing at the pilot report.

- [ ] **Step 8: Commit (nested repo), bump the submodule (PANTHER), report**

```bash
git -C $R add docs/experiments docs/experiment-protocol.md README.md
git -C $R commit -m "docs: aioquic pilot report, protocol §3 amendment, preregistration defaults"
cd $W && git add panther/plugins/services/testers/a_rfc/ai_rfc && git commit -m "chore(a_rfc): bump ai_rfc submodule to the aioquic pilot report"
```

Then report to the user: the per-arm table, cost and wall time per run, integrity rates, what broke, the SHAs in both repos — and ask (AskUserQuestion) whether to push `ai_rfc` to github.com/ElNiak/ai_rfc, which is outward-facing. Do not push on your own.

---

## Self-review (performed while writing)

**Spec coverage.** §4 campaign freeze/order/run layout/env/timeout/resume → Tasks 1, 3, 4; §5 audit definitions → Task 5, analysis and metrics → Task 6, report → Task 7; §6 fake-`claude` testing → Task 2 (every later task's tests go through it); §7 procedure, deliverables, protocol amendment, preregistration prefill, submodule bump → Task 8; D21 (matrix), D22 (model/effort), D23 (completion), D24 (one session per run; per-cluster attribution), D25 (custom runner, stdlib), D28 (`--disable-slash-commands`, prompt file) all appear in the CLI defaults and the runner. Deferred, tracked in Task 8's "Decisions for the main run": the MARK pilot and the preregistered main run.

**Placeholder scan.** No TBD/TODO; every code step carries the code; the only free-text deliverable (the pilot report) has its section list fixed.

**Type consistency.** `Campaign` fields and properties (`dir`, `runs_dir`, `prompts_dir`, `bin_dir`, `audit_dir`, `analysis_dir`, `server_src`, `run_spec`) are used identically in Tasks 3–7; `RunStatus.complete`/`load_status` in Tasks 3, 4, 5, 6; `audit_events` keys (`integrity`, `bypass_attempts.count/by_surface`, `errors.class1/class2/first_failure_index`, `hand_edits`, `prose_edits`, `compaction_events`) are read by `metrics._arm_summary` and `report._run_rows` under the same names; `trajectory` keys (`points`, `tokens_to_first_completion`, `total_tokens`, `auc`) match between test, implementation and report; the fake's scenario keys (`arm`, `cost`, `sleep`, `exit_code`, `subtype`, `steps[].kind`) match every scenario written in Tasks 3–7.

**Known judgement calls.** `RunStatus.complete` is "the process ended on its own", so a crash with exit 3 counts as complete for resume purposes (it is never relaunched in place; a retry is a new id) while its metrics show zero completion. The cost trajectory is reported in tokens; `analysis` does not invent a per-token price table. Gate re-runs copy the whole workspace to scratch so `runs/<id>/workspace` stays the untouched artifact.
