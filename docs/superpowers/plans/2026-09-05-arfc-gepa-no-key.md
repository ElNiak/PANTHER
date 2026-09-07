# GEPA-NO-KEY Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Where this file lands.** Drafted in plan mode on 2026-09-05, as a draft only: approving it accepts the draft for the executor session, and nothing in it runs in the drafting session. The executor session (`NEXT=GEPA-NO-KEY` in the 2026-09-05 executor prompt) copies it verbatim to `docs/superpowers/plans/2026-09-05-arfc-gepa-no-key.md` in the PANTHER worktree (`git add -f`, since `docs/` is gitignored but tracked), commits it as `docs(ai_rfc): add the GEPA-NO-KEY plan` (Task 0, Step 5), and keeps its deviation log beside it at `docs/superpowers/plans/2026-09-05-arfc-gepa-no-key-deviations.md`. Code and tests land in the ai_rfc submodule. The row's ledger is `.superpowers/sdd/2026-09-05-arfc-gepa-no-key/progress.md`.

**Goal:** The GEPA pilot's proposer and judge run through `claude -p` on the experiment profile, so a pilot needs no Anthropic API key.

**Architecture:** One new module `ai_rfc/experiment/optimize/claude_cli.py` holds `ClaudeCliCall`, a callable that serves both as gepa's reflection LM (`__call__(prompt) -> str`) and as the judge's `Transport` (the same shape; `judge.py:31`). It runs `claude -p --output-format stream-json` with the prompt on stdin, under a five-variable environment with `CLAUDE_CONFIG_DIR` on the profile, and reads the reply with the package's existing `stream.py` parsers. The CLI accepts `claude-cli:<model>` for `--reflection-lm` and `--judge-model`, refuses `--max-token-cost` beside a CLI proposer, skips the litellm pricing check for one, and prints a consent text in sessions and calls rather than USD. The litellm and `anthropic_transport` paths stay as they are, unused by the pilot.

**Tech Stack:** Python 3.10 (stdlib), pytest 8 + pytest-xdist, `claude` CLI 2.1.261, git. The 3.11 venv is needed only for the three tests marked `with_gepa` and the fake-stage rehearsal.

**Spec:** the GEPA-NO-KEY row and its design paragraph in `docs/superpowers/plans/2026-09-05-plan-executor-prompt.md` (PANTHER `5f7a268b8`, lines 66 and 77), read together with the user's ruling `feedback_no_anthropic_api_key.md` and the measured `claude -p` facts in memory `reference-claude-headless-judge-flags.md`. Three departures from the design paragraph were confirmed with the user on 2026-09-05 and are listed under *Rulings taken in plan mode* below.

## Context

Stage 1 of the GEPA track landed at ai_rfc `07a02fb`: the optimizer wiring, the score, the anti-forgery fixes, the pristines, the examples spec and a zero-spend rehearsal. The pilot cannot run because its proposer (a litellm id) and its judge (`anthropic_transport`, `judge.py:83`) both need `ANTHROPIC_API_KEY`, and the user ruled on 2026-09-05 that no API key is used anywhere in this project. Everything else already runs through `claude -p` on the Max-subscription profile at `~/ai-rfc-experiments/profile`. This row closes that gap so `NEXT=GEPA-PILOT` can launch with the subscription as its only meter.

## Global Constraints

Carried from the executor prompt's generic core; every task implicitly includes them.

- **Layout.** PANTHER worktree `/Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/iut-ai-rfc`, branch `feat/arfc-pipeline-and-runtime-anchors`. `AIRFC` = `$PANTHER/panther/plugins/services/testers/ai_rfc` (its own repository, remote `ElNiak/ai_rfc`, branch `main`). `PY` = `$PANTHER/.venv/bin/python` (3.10). `PY311` = `$PANTHER/.superpowers/venv-optimize/bin/python` (the only interpreter that imports gepa).
- **Every `pytest` and `python -m` invocation is prefixed `SSLKEYLOGFILE=`** and runs with the sandbox off (pytest spawns subprocesses; the two `slow` gepa tests bind a socket).
- **No API key, ever.** No task sets, reads or prints `ANTHROPIC_API_KEY`; tests that need it absent use `monkeypatch.delenv`, tests that prove it does not leak set a dummy value with `monkeypatch.setenv` and assert its absence in the child. A step that would need a key is a stop, reported.
- **Spend.** Nothing that calls a model runs without the user's approval in the session, each time, with the printed worst case. This plan has exactly one such step, Task 4's probe (one `claude -p` on the experiment profile, subscription quota).
- **Git hygiene.** `git status --short` before every `git add`; stage by explicit path; never `-A` or `.`; `git commit --only -m "<message>" -- <paths>` when a peer session has staged files; never `--no-verify`; never `git stash`; never amend a commit already on the branch; never move a submodule pointer backwards (`git ls-tree HEAD panther/plugins/services/testers/ai_rfc` before any bump). Commit messages: ai_rfc `type(scope): lowercase summary`, PANTHER `type(scope): lowercase summary`, no trailing period, and every commit ends with the trailer `Claude-Session: <the executing session's URL>`.
- **Peer sessions.** `land-structures-registry-sp7b` is live in this same checkout, mid-way through SP7b (Task 1 of 10 landed as ai_rfc `6e06ac2` + `7a4d6f9`, unbumped), and holds `docs/superpowers/plans/2026-09-03-arfc-draft-quality-sp7b-deviations.md` uncommitted; do not touch that file. Its Task 10 edits `README.md`, which Task 5 here also edits: anchor Task 5's README edits by sentence, not line, and send the peer one factual note naming the spans and the commit message before Task 5 is dispatched. Send one factual note before touching any file a peer holds; never wait for a reply. (D1)
- **Style.** Google-style docstrings on public functions, line length 88, `from __future__ import annotations` (every module touched here has it), comments only where the why is not obvious, no backward-compatibility shims, no new dependencies. Lint each task's own files: `black`, `isort --profile black`, `flake8 --max-line-length=88`, `mypy --follow-imports=silent`.
- **Tests.** Every task's RED test is seen failing at the exact path the change addresses before the implementation is written. A RED test that passes against the unfixed code is a stop.
- **Evidence roots are read-only.** `~/ai-rfc-experiments/` and `~/arfc-experiments/` are never written except by Task 4's probe, which runs with cwd under `/tmp/claude/gepa-no-key/` and `--no-session-persistence`, and by the gate's rehearsal, which writes only under `~/ai-rfc-experiments/optimize/<new name>/`. Never write into `~/ai-rfc-experiments/profile/`.
- **Never run** `panther docs build`, `panther_builder.py clean|package-dev`, `python -m ai_rfc.experiment audit|analyze` against any existing campaign, or two `claude -p` roles concurrently against one profile.

## Rulings taken in plan mode (2026-09-05)

Confirmed with the user, one `AskUserQuestion`; each departs from the row's design paragraph and is recorded here so the deviation log can cite it as entry 0.

1. **Isolation flags.** The argv carries `--safe-mode --setting-sources "" --permission-mode dontAsk --tools "" --no-session-persistence` beyond the paragraph's bare `-p --output-format … --model`. Measured 2026-09-04 (CLI 2.1.260): without `--setting-sources ""` and `--permission-mode dontAsk` a judge answer cited "Plan mode active"; without `--tools ""` the proposer is an agent that can load the skills it is rewriting. `claude --help` on 2.1.261 documents `--safe-mode` as disabling CLAUDE.md, skills, plugins, hooks and MCP while "auth, model selection, built-in tools, and permissions work normally". Cost if wrong: the flag set fails to authenticate against the profile; Task 4's probe is what detects that before the CLI is wired.
2. **Output format.** `--output-format stream-json --verbose`, parsed with the existing `stream.parse_stream`, `result_event` and `assistant_text` (`ai_rfc/experiment/stream.py:28,166,401`), instead of the paragraph's `text`. Text has no parser in the package and no error signal: a refusal or a usage-limit message would reach gepa as a proposal. Stream-json carries `is_error` and the `rate_limit_event` quota signal. Cost if wrong: none beyond a slightly larger stub.
3. **Effort and timeout per role.** `ClaudeCliCall` takes `effort`; the proposer inherits `--effort` and `--timeout-s` (2400 s in the pilot); the judge is fixed at effort `low` with a 120 s timeout (`JUDGE_EFFORT`, `JUDGE_TIMEOUT_S` in `cli.py`). Measured: 112 s per short call at default effort, 3 to 4 s at low; the judge makes one call per anchored claim per evaluation, fourteen on the largest seed run. The paragraph's single `timeout_s=120` stays as the constructor default.

Rulings the planner made alone (no user question needed):

4. `__call__` accepts `str | list[dict[str, Any]]` because gepa's protocol is that union (`gepa/proposer/reflective_mutation/base.py:27`); a message list is flattened to one stdin string.
5. `__repr__` is exactly `claude-cli:<model>` because `run.py:329` writes `repr()` of a callable into `result.json`; the class holds only `str`, `Path` and `int` attributes because `asdict(settings)` deep-copies it at the end of a finished run (`run.py:365`).
6. The environment is the five-variable dict `preflight._base_env` already builds (`preflight.py:79`), lifted into `profile.py` as a public helper rather than copied a third time; `USER` is load-bearing (without it the CLI answers "Not logged in", `runner.py:104`).
7. The fake stage refuses any given `--reflection-lm` or `--judge-model`, not only the `claude-cli:` form, on the rationale the existing `--model` refusal states (`cli.py:324`): a rehearsal calls nothing, so a named model would be paid for in a pilot.
8. Refusals for the new form live in the pilot block before the consent print, so `--max-token-cost` beside a CLI proposer fails before `--yes` is read.
9. The consent text keeps "one judge call per anchored claim per evaluation" rather than the paragraph's "fourteen": the CLI cannot know the count, and GEPA-PILOT states it at launch approval.
10. No call cap in the wrapper. gepa calls the reflection LM once per iteration (`reflection_lm.py:142`), so proposer calls are bounded by `--max-evals`; the routing harness's cap (`claude_lm.py:113`) guarded an eval loop this design does not have. Recorded as a ruling not taken.
11. `cwd` is a required keyword argument; the CLI passes `<root>/optimize/<name>`, created lazily on the first call so a refusal creates nothing.
12. The stub's control channel is `$CLAUDE_CONFIG_DIR/fake-lm.json` and its record goes under `$CLAUDE_CONFIG_DIR/fake-lm-calls/`, mirroring the existing fake agent's `fake-scenarios/` and `fake-calls/`, instead of the paragraph's "an environment variable the test sets": the wrapper's five-variable environment strips any variable the test exports, and the stub finding its control file through `CLAUDE_CONFIG_DIR` is itself the proof that the variable reached the child.

## File Structure

| File | Responsibility |
|---|---|
| `AIRFC/ai_rfc/experiment/profile.py` | Modify: add `profile_env(profile: Path) -> dict[str, str]`, the minimal environment a one-shot `claude -p` runs in. |
| `AIRFC/ai_rfc/experiment/preflight.py` | Modify: `_base_env` deleted; its one caller (`:119`) uses `profile_env`. |
| `AIRFC/tests/experiment/test_profile.py` | Modify: tests for `profile_env`. |
| `AIRFC/tests/experiment/fake_claude/claude-lm` | Create (mode 100755): a one-shot stand-in for `claude -p` driven by `$CLAUDE_CONFIG_DIR/fake-lm.json`, recording each call under `$CLAUDE_CONFIG_DIR/fake-lm-calls/`. |
| `AIRFC/tests/experiment/test_fake_claude.py` | Modify: tests of the new stub's contract. |
| `AIRFC/ai_rfc/experiment/optimize/claude_cli.py` | Create: `PREFIX`, `cli_model`, `ClaudeCliError`, `ClaudeCliCall`, `quota`. |
| `AIRFC/tests/experiment/optimize/test_claude_cli.py` | Create: the wrapper against the stub, `build_judge` through the wrapper. |
| `AIRFC/tests/experiment/optimize/test_run.py` | Modify: `_write_result` records the `claude-cli:` form. |
| `AIRFC/ai_rfc/experiment/cli.py` | Modify: `_optimize_run` pilot and fake blocks, consent text, help text, two constants. |
| `AIRFC/tests/experiment/test_cli_optimize.py` | Modify: the refusal matrix for the new form. |
| `AIRFC/README.md` | Modify: "The environment" and "Stage `pilot`" paragraphs (`:155-168`, `:198-212`). |
| `$PANTHER/docs/superpowers/plans/2026-09-05-arfc-gepa-no-key-deviations.md` | Create: numbered deviation entries, committed with the task that produced each. |

Nothing else is touched. `runner.py`, `arms.py`, `spawn.py`, `judge.py`, `run.py`, `evaluator.py`, `scoring.py` are read, not edited.

---

### Task 0: Precondition gate and baseline

**Files:** none edited.

- [ ] **Step 1: Confirm the landed state.** In `AIRFC`: `git branch --show-current` prints `main`; `git log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'` shows `07a02fb` or a descendant; `git status --short` is empty or lists only files the peer ledger attributes. In `$PANTHER`: branch `feat/arfc-pipeline-and-runtime-anchors`, HEAD `5f7a268b8` or a descendant, `git status --short` shows only `M docs/superpowers/plans/2026-09-03-arfc-draft-quality-sp7b.md` (the SP7b peer's file). Any other dirty file you cannot attribute is a stop.
- [ ] **Step 2: Confirm the tools.** `command -v claude` resolves; `claude --version` is `2.1.261` or later; `claude --help | grep -c -E -- '--safe-mode|--setting-sources|--tools|--no-session-persistence'` prints `4` or more, and each of the four flags starts its own help line (2.1.261 prints `5`: `--tools` is also mentioned inside another flag's text; D2). `test -z "$ANTHROPIC_API_KEY" && echo unset` prints `unset`. `CLAUDE_CONFIG_DIR=~/ai-rfc-experiments/profile claude auth status` prints logged in (read-only; no model call).
- [ ] **Step 3: Measure the baseline.** From `AIRFC`, sandbox off:

```bash
SSLKEYLOGFILE= $PY -m pytest tests -q -n auto -p no:cacheprovider 2>&1 | tail -3
SSLKEYLOGFILE= $PY311 -m pytest tests/experiment/optimize tests/experiment/test_cli_optimize.py -q -m "not slow" -p no:cacheprovider 2>&1 | tail -3
```

Expected at `07a02fb`: `1118 passed, 10 skipped` and `189 passed, 2 skipped`. Measured at `7a4d6f9` on 2026-09-05: `1129 passed, 10 skipped` and `189 passed, 2 skipped, 2 deselected` (the SP7b peer's Task 1 added eleven; D3). Record the measured numbers in the ledger; the measured number wins over these.

- [ ] **Step 4: Open the ledger** at `$PANTHER/.superpowers/sdd/2026-09-05-arfc-gepa-no-key/progress.md` with the baseline counts, the CLI version and the peer sessions `ListAgents` shows.

- [ ] **Step 5: Land the plan and its log in PANTHER.** Write this file to `$PANTHER/docs/superpowers/plans/2026-09-05-arfc-gepa-no-key.md` and create `2026-09-05-arfc-gepa-no-key-deviations.md` beside it with entry 0 (the twelve rulings under *Rulings taken in plan mode*, one line each, citing the plan section). Then, in `$PANTHER`, `git status --short`: PANTHER's pre-commit hook stashes and restores every unstaged file around a commit, and the SP7b peer's `2026-09-03-arfc-draft-quality-sp7b.md` is unstaged in this checkout right now. **Do not commit in PANTHER while a foreign modified file shows.** The plan and the log are used from disk meanwhile; re-check before each later PANTHER commit (the deviation entries and the pointer bump) and commit the first time the tree shows only your files:

```bash
git add -f docs/superpowers/plans/2026-09-05-arfc-gepa-no-key.md docs/superpowers/plans/2026-09-05-arfc-gepa-no-key-deviations.md
git commit -m "docs(ai_rfc): add the GEPA-NO-KEY plan and its deviation log"
```

If the peer's file is still unstaged when the row ends, report the uncommitted plan and log under "For the user" with this exact command; never stash and never commit around it.

---

### Task 1: `profile_env`, the one-shot environment

**Files:**
- Modify: `AIRFC/ai_rfc/experiment/profile.py`
- Modify: `AIRFC/ai_rfc/experiment/preflight.py:79-88` (delete `_base_env`) and `:119` (call site)
- Test: `AIRFC/tests/experiment/test_profile.py`

**Interfaces:**
- Produces: `profile_env(profile: Path) -> dict[str, str]` in `ai_rfc.experiment.profile`, returning exactly `{"HOME", "USER", "PATH", "LANG", "CLAUDE_CONFIG_DIR"}`. Task 3 consumes it.

- [ ] **Step 1: Write the failing tests.** Append the three tests to `tests/experiment/test_profile.py`, and add `profile_env` to the module's existing `from ai_rfc.experiment.profile import init_profile, login_command` line (`:5`) rather than placing an import below code (flake8 E402; D6):

```python
from ai_rfc.experiment.profile import init_profile, login_command, profile_env


def test_profile_env_carries_the_five_variables_a_login_needs(tmp_path, monkeypatch):
    """USER is load-bearing: without it the CLI answers "Not logged in"."""
    monkeypatch.setenv("HOME", "/home/t")
    monkeypatch.setenv("USER", "t")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("LANG", "en_US.UTF-8")

    env = profile_env(tmp_path / "profile")

    assert env == {
        "HOME": "/home/t",
        "USER": "t",
        "PATH": "/usr/bin",
        "LANG": "en_US.UTF-8",
        "CLAUDE_CONFIG_DIR": str(tmp_path / "profile"),
    }


def test_profile_env_inherits_nothing_else(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-leak")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("SSLKEYLOGFILE", "/tmp/keys")

    env = profile_env(tmp_path / "profile")

    assert "ANTHROPIC_API_KEY" not in env
    assert "CLAUDECODE" not in env
    assert "SSLKEYLOGFILE" not in env


def test_profile_env_defaults_lang_when_the_shell_has_none(tmp_path, monkeypatch):
    monkeypatch.delenv("LANG", raising=False)

    assert profile_env(tmp_path / "profile")["LANG"] == "C.UTF-8"
```

- [ ] **Step 2: Run them to verify they fail.** `SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_profile.py -q -p no:cacheprovider` → FAIL with `ImportError: cannot import name 'profile_env'`.

- [ ] **Step 3: Implement.** In `profile.py`, add `import os` and, after `init_profile`:

```python
def profile_env(profile: Path) -> dict[str, str]:
    """The complete environment of a one-shot ``claude -p`` on ``profile``.

    Args:
        profile: The ``CLAUDE_CONFIG_DIR`` the call authenticates through.

    Returns:
        Five variables and nothing else inherited, so no credential the shell
        holds can reach the call.
    """
    # Measured on Claude Code 2.1.247 / macOS: drop USER and the CLI cannot
    # reach its stored credentials, answering "Not logged in" however valid
    # the profile. Spike S0 failed on exactly this before it was added.
    return {
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
        "PATH": os.environ.get("PATH", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "CLAUDE_CONFIG_DIR": str(profile),
    }
```

In `preflight.py`: delete `_base_env` (`:79-88`), add `from .profile import profile_env` to the imports, and change `:119` to `isolated = profile_env(profile_dir(root))`. If `os` is then unused in `preflight.py`, remove the import (check with flake8).

- [ ] **Step 4: Run to verify.** The three new tests PASS; `SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_preflight.py tests/experiment/test_profile.py -q -p no:cacheprovider` all green. Lint the three files.

- [ ] **Step 5: Commit** (from `AIRFC`, after `git status --short`):

```bash
git add ai_rfc/experiment/profile.py ai_rfc/experiment/preflight.py tests/experiment/test_profile.py
git commit -m "refactor(experiment): lift the one-shot claude environment into profile.py"
```

---

### Task 2: `claude-lm`, the one-shot stand-in

**Files:**
- Create: `AIRFC/tests/experiment/fake_claude/claude-lm` (executable)
- Modify: `AIRFC/tests/experiment/conftest.py:16` (add `FAKE_CLAUDE_LM = Path(__file__).parent / "fake_claude" / "claude-lm"` beside `FAKE_CLAUDE`, the repository's pattern for the stub path; both test modules import it rather than each defining its own)
- Test: `AIRFC/tests/experiment/test_fake_claude.py`

**Interfaces:**
- Produces a script invoked exactly like `claude -p …` with the prompt on stdin. Control file `$CLAUDE_CONFIG_DIR/fake-lm.json`, a JSON object with `reply` in `{"fenced", "verdict", "error", "nonzero", "hang", "garbage"}` plus optional `proposal` (default `"PROPOSAL"`), `score` (default `1`), `message`, `stderr`, `exit_code` (default `3`), `seconds` (default `30`), `rate_limit` (an object echoed as a `rate_limit_event`). Missing file means `fenced`. Each call writes `$CLAUDE_CONFIG_DIR/fake-lm-calls/<n>.json` holding `{"argv": [...], "env": {...}, "stdin": "...", "cwd": "..."}`. Output is stream-json: a `system/init` event, the optional `rate_limit_event`, an `assistant` text event and a `result` event whose `result` is the reply text; `error` emits a `result` with `is_error: true` and no assistant event.

- [ ] **Step 1: Write the failing tests.** Append to `tests/experiment/test_fake_claude.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ai_rfc.experiment.stream import parse_stream, result_event

from .conftest import FAKE_CLAUDE_LM


def _run_lm(profile, prompt, control=None, timeout=10):
    if control is not None:
        (profile / "fake-lm.json").write_text(json.dumps(control))
    return subprocess.run(
        [str(FAKE_CLAUDE_LM), "-p", "--output-format", "stream-json"],
        input=prompt,
        cwd=profile,
        env={
            "CLAUDE_CONFIG_DIR": str(profile),
            "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
            "MARK": "x",
        },
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture
def lm_profile(tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    return profile


def test_claude_lm_is_executable():
    assert FAKE_CLAUDE_LM.stat().st_mode & 0o111


def test_claude_lm_echoes_a_fenced_proposal_and_records_the_call(lm_profile):
    completed = _run_lm(lm_profile, "Rewrite it.", {"reply": "fenced", "proposal": "NEW"})

    assert completed.returncode == 0, completed.stderr
    events = parse_stream(completed.stdout)
    assert events[0]["type"] == "system" and events[0]["subtype"] == "init"
    final = result_event(events)
    assert final["result"] == "```\nNEW\n```" and final["is_error"] is False
    (record,) = [json.loads(p.read_text()) for p in (lm_profile / "fake-lm-calls").iterdir()]
    assert record["argv"][1:] == ["-p", "--output-format", "stream-json"]
    assert record["stdin"] == "Rewrite it."
    assert record["env"]["MARK"] == "x"
    assert record["cwd"] == str(lm_profile)


def test_claude_lm_defaults_to_a_fenced_proposal_without_a_control_file(lm_profile):
    completed = _run_lm(lm_profile, "x")

    assert result_event(parse_stream(completed.stdout))["result"] == "```\nPROPOSAL\n```"


def test_claude_lm_prints_a_verdict(lm_profile):
    completed = _run_lm(lm_profile, "x", {"reply": "verdict", "score": 0.5})

    reply = result_event(parse_stream(completed.stdout))["result"]
    assert json.loads(reply) == {"score": 0.5, "rationale": "stub verdict"}


def test_claude_lm_reports_an_error_result_with_a_quota_event(lm_profile):
    completed = _run_lm(
        lm_profile,
        "x",
        {
            "reply": "error",
            "message": "usage limit reached",
            "rate_limit": {"unifiedWindows": {"seven_day": {"utilization": 1.0}}},
        },
    )

    events = parse_stream(completed.stdout)
    assert completed.returncode == 0
    assert [e["type"] for e in events] == ["system", "rate_limit_event", "result"]
    assert result_event(events)["is_error"] is True
    assert result_event(events)["result"] == "usage limit reached"


def test_claude_lm_exits_nonzero_with_the_stderr_it_was_given(lm_profile):
    completed = _run_lm(
        lm_profile, "x", {"reply": "nonzero", "stderr": "boom\n", "exit_code": 7}
    )

    assert completed.returncode == 7
    assert completed.stderr == "boom\n"
    assert completed.stdout == ""


def test_claude_lm_hangs_when_told_to(lm_profile):
    with pytest.raises(subprocess.TimeoutExpired):
        _run_lm(lm_profile, "x", {"reply": "hang", "seconds": 5}, timeout=1)


def test_claude_lm_can_print_something_that_is_not_stream_json(lm_profile):
    completed = _run_lm(lm_profile, "x", {"reply": "garbage"})

    assert completed.returncode == 0
    assert completed.stdout == "this is not stream-json\n"


def test_claude_lm_numbers_its_calls(lm_profile):
    _run_lm(lm_profile, "one")
    _run_lm(lm_profile, "two")

    names = sorted(p.name for p in (lm_profile / "fake-lm-calls").iterdir())
    assert names == ["1.json", "2.json"]
```

If `test_fake_claude.py` already imports any of these names, do not import them twice; merge into the existing import block.

- [ ] **Step 2: Run to verify they fail.** First add the `FAKE_CLAUDE_LM` line to `conftest.py:16` (without it the module fails at import, which is not the RED this task needs). Then `SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_fake_claude.py -q -p no:cacheprovider -k claude_lm` → FAIL: `test_claude_lm_is_executable` with `FileNotFoundError`, the rest with `FileNotFoundError` or `PermissionError` from `subprocess.run`.

- [ ] **Step 3: Write the stub** at `tests/experiment/fake_claude/claude-lm`:

```python
#!/usr/bin/env python3
"""A stand-in for one ``claude -p`` language-model call.

The wrapper under test launches it exactly like the real CLI, with the prompt
on stdin. It reads what to answer from ``$CLAUDE_CONFIG_DIR/fake-lm.json``
(absent means a fenced proposal), records how it was called under
``$CLAUDE_CONFIG_DIR/fake-lm-calls/``, and prints its reply as stream-json.
Stdlib only, so it runs under whichever ``python3`` is on the child's PATH.
Never used outside the tests.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def _emit(event: dict) -> None:
    sys.stdout.write(json.dumps(event, sort_keys=True) + "\n")
    sys.stdout.flush()


def main() -> int:
    profile = Path(os.environ["CLAUDE_CONFIG_DIR"])
    control_path = profile / "fake-lm.json"
    control = json.loads(control_path.read_text()) if control_path.exists() else {}
    prompt = sys.stdin.read()

    calls = profile / "fake-lm-calls"
    calls.mkdir(exist_ok=True)
    number = len(list(calls.iterdir())) + 1
    (calls / f"{number}.json").write_text(
        json.dumps(
            {
                "argv": sys.argv,
                "env": dict(os.environ),
                "stdin": prompt,
                "cwd": os.getcwd(),
            },
            indent=2,
            sort_keys=True,
        )
    )

    reply = control.get("reply", "fenced")
    if reply == "nonzero":
        sys.stderr.write(control.get("stderr", "the stub was told to fail\n"))
        return int(control.get("exit_code", 3))
    if reply == "hang":
        time.sleep(float(control.get("seconds", 30)))
        return 0
    if reply == "garbage":
        sys.stdout.write("this is not stream-json\n")
        return 0

    _emit({"type": "system", "subtype": "init", "model": "fake-lm", "tools": []})
    if "rate_limit" in control:
        _emit({"type": "rate_limit_event", "rate_limit_info": control["rate_limit"]})
    if reply == "error":
        _emit(
            {
                "type": "result",
                "subtype": "error_during_execution",
                "is_error": True,
                "result": control.get("message", "the stub was told to error"),
                "num_turns": 0,
            }
        )
        return 0
    if reply == "verdict":
        text = json.dumps(
            {"score": control.get("score", 1), "rationale": "stub verdict"}
        )
    else:
        text = "```\n" + str(control.get("proposal", "PROPOSAL")) + "\n```"
    _emit(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": text}],
            },
        }
    )
    _emit(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": text,
            "num_turns": 1,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Then `chmod +x tests/experiment/fake_claude/claude-lm`.

- [ ] **Step 4: Run to verify.** The nine tests PASS. Also `SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_fake_claude.py -q -p no:cacheprovider` (whole module) green. `git ls-files -s tests/experiment/fake_claude/claude-lm` must show mode `100755` after staging; if it shows `100644`, run `git update-index --chmod=+x tests/experiment/fake_claude/claude-lm`.

- [ ] **Step 5: Commit:**

```bash
git add tests/experiment/fake_claude/claude-lm tests/experiment/conftest.py tests/experiment/test_fake_claude.py
git commit -m "test(experiment): add claude-lm, a one-shot stand-in for claude -p"
```

---

### Task 3: `ClaudeCliCall`, the no-key proposer and judge transport

**Files:**
- Create: `AIRFC/ai_rfc/experiment/optimize/claude_cli.py`
- Create: `AIRFC/tests/experiment/optimize/test_claude_cli.py`
- Modify: `AIRFC/tests/experiment/optimize/test_run.py` (one test appended)

**Interfaces:**
- Consumes: `profile_env` (Task 1); `parse_stream`, `result_event`, `assistant_text` from `ai_rfc.experiment.stream`; `ExperimentError` from `ai_rfc.experiment`; the stub from Task 2 (tests only).
- Produces, all in `ai_rfc.experiment.optimize.claude_cli`:
  - `PREFIX = "claude-cli:"`
  - `cli_model(value: str) -> str | None`: the model inside a `claude-cli:<model>` id, `None` for any other id; raises `ExperimentError` on `claude-cli:` with nothing after it.
  - `class ClaudeCliError(ExperimentError)` with attributes `exit_code: int | None` and `stderr_tail: str`.
  - `class ClaudeCliCall` with `__init__(self, claude_bin: str, profile_dir: Path, model: str, *, cwd: Path, effort: str = "high", timeout_s: int = 120)`, attributes of the same names, `argv() -> list[str]`, `env() -> dict[str, str]`, `__call__(prompt: str | list[dict[str, Any]]) -> str`, `__repr__() -> str` returning `f"claude-cli:{model}"`.
  - `quota(events: list[dict[str, Any]]) -> dict[str, Any] | None`: the last `rate_limit_event`'s `rate_limit_info`.
  - Canonical argv, in this order: `[claude_bin, "-p", "--output-format", "stream-json", "--verbose", "--model", model, "--effort", effort, "--safe-mode", "--setting-sources", "", "--permission-mode", "dontAsk", "--tools", "", "--no-session-persistence"]`. Task 5 consumes the class and `cli_model`; Task 4 probes the argv.

- [ ] **Step 1: Write the failing tests.** Create `tests/experiment/optimize/test_claude_cli.py`:

```python
"""``claude -p`` as a one-shot model: argv, stdin, environment, and failures.

Every test drives the ``claude-lm`` stub that ships with the tests. Nothing
here reaches a real CLI; the one real call is the row's probe step.
"""

import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from ai_rfc.experiment import ExperimentError
from ai_rfc.experiment.optimize.claude_cli import (
    PREFIX,
    ClaudeCliCall,
    ClaudeCliError,
    cli_model,
    quota,
)
from ai_rfc.experiment.optimize.judge import RUBRIC, JudgeError, build_judge
from ai_rfc.experiment.optimize.scoring import ClaimHunk, Judgement

from ..conftest import FAKE_CLAUDE_LM as STUB


@pytest.fixture
def profile(tmp_path):
    path = tmp_path / "profile"
    path.mkdir()
    return path


def control(profile, **payload):
    (profile / "fake-lm.json").write_text(json.dumps(payload))


def calls(profile):
    folder = profile / "fake-lm-calls"
    return [json.loads(p.read_text()) for p in sorted(folder.iterdir())]


def call(profile, tmp_path, model="some-model", **overrides):
    return ClaudeCliCall(str(STUB), profile, model, cwd=tmp_path / "cwd", **overrides)


def hunk(claim_id="t:1.1", text="A peer MUST close the connection.", body="def x():"):
    return ClaimHunk(
        claim_id=claim_id,
        text=text,
        level="MUST",
        path="src/peer.py",
        commit="a" * 40,
        line=12,
        hunk=body,
    )


# --- the form -------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("claude-cli:claude-opus-5", "claude-opus-5"),
        ("claude-cli: opus ", "opus"),
        ("anthropic/claude-sonnet-4-6", None),
        ("claude-opus-5", None),
    ],
)
def test_cli_model_reads_the_form_and_ignores_every_other_id(value, expected):
    assert cli_model(value) == expected


def test_cli_model_refuses_the_prefix_alone():
    with pytest.raises(ExperimentError, match="names no model"):
        cli_model("claude-cli:")


def test_repr_is_the_form_the_result_file_records(profile, tmp_path):
    assert repr(call(profile, tmp_path, model="claude-opus-5")) == PREFIX + "claude-opus-5"


# --- the call -------------------------------------------------------------


def test_the_argv_is_exact_and_the_prompt_travels_on_stdin(profile, tmp_path):
    control(profile, reply="fenced", proposal="NEW")

    reply = call(profile, tmp_path, effort="high")("Rewrite it.")

    assert reply == "```\nNEW\n```"
    (recorded,) = calls(profile)
    assert recorded["argv"][1:] == [
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        "some-model",
        "--effort",
        "high",
        "--safe-mode",
        "--setting-sources",
        "",
        "--permission-mode",
        "dontAsk",
        "--tools",
        "",
        "--no-session-persistence",
    ]
    assert recorded["stdin"] == "Rewrite it."
    assert "Rewrite it." not in " ".join(recorded["argv"])
    assert recorded["cwd"] == str(tmp_path / "cwd")


def test_the_environment_is_the_profile_and_nothing_the_shell_holds(
    profile, tmp_path, monkeypatch
):
    """The proposer reads every skill body; a key in its environment would be
    one process away from the model. It gets five variables and no more."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-leak")
    monkeypatch.setenv("CLAUDECODE", "1")

    call(profile, tmp_path)("x")

    (recorded,) = calls(profile)
    assert recorded["env"]["CLAUDE_CONFIG_DIR"] == str(profile)
    assert "ANTHROPIC_API_KEY" not in recorded["env"]
    assert "CLAUDECODE" not in recorded["env"]
    # The child's os.environ may gain a loader variable or two on macOS, so
    # the proof of "nothing inherited" is the two planted names being absent.
    assert {"HOME", "USER", "PATH", "LANG", "CLAUDE_CONFIG_DIR"} <= set(recorded["env"])


def test_a_message_list_is_flattened_onto_stdin(profile, tmp_path):
    call(profile, tmp_path)(
        [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": [{"type": "text", "text": "Rewrite it."}]},
        ]
    )

    (recorded,) = calls(profile)
    assert recorded["stdin"] == "[System]\nBe brief.\n\n[User]\nRewrite it."


def test_the_cwd_is_created_on_the_first_call_not_before(profile, tmp_path):
    wrapper = call(profile, tmp_path)
    assert not (tmp_path / "cwd").exists()

    wrapper("x")

    assert (tmp_path / "cwd").is_dir()


# --- failures -------------------------------------------------------------


def test_a_nonzero_exit_raises_with_the_code_and_the_stderr_tail(profile, tmp_path):
    control(profile, reply="nonzero", stderr="x" * 3000 + "TAIL\n", exit_code=7)

    with pytest.raises(ClaudeCliError) as caught:
        call(profile, tmp_path)("x")

    error = caught.value
    assert error.exit_code == 7
    assert error.stderr_tail.endswith("TAIL\n") and len(error.stderr_tail) <= 2000
    assert "exited 7" in str(error) and "TAIL" in str(error)
    assert "claude-cli:some-model" in str(error)


def test_a_timeout_raises_and_names_the_cap(profile, tmp_path):
    control(profile, reply="hang", seconds=5)

    with pytest.raises(ClaudeCliError, match="within 1 s") as caught:
        call(profile, tmp_path, timeout_s=1)("x")

    assert caught.value.exit_code is None


def test_an_error_result_raises_with_its_message_and_the_quota(profile, tmp_path):
    control(
        profile,
        reply="error",
        message="usage limit reached",
        rate_limit={"unifiedWindows": {"seven_day": {"utilization": 1.0}}},
    )

    with pytest.raises(ClaudeCliError) as caught:
        call(profile, tmp_path)("x")

    assert "usage limit reached" in str(caught.value)
    assert "seven_day" in str(caught.value)
    assert caught.value.exit_code == 0


def test_output_that_is_not_stream_json_raises(profile, tmp_path):
    control(profile, reply="garbage")

    with pytest.raises(ClaudeCliError, match="not stream-json"):
        call(profile, tmp_path)("x")


def test_a_missing_binary_raises_naming_it(profile, tmp_path):
    wrapper = ClaudeCliCall(
        str(tmp_path / "no-such-claude"), profile, "m", cwd=tmp_path / "cwd"
    )

    with pytest.raises(ClaudeCliError, match="no-such-claude"):
        wrapper("x")


def test_quota_reads_the_last_rate_limit_event():
    events = [
        {"type": "system", "subtype": "init"},
        {"type": "rate_limit_event", "rate_limit_info": {"a": 1}},
        {"type": "rate_limit_event", "rate_limit_info": {"a": 2}},
        {"type": "result", "result": "x"},
    ]
    assert quota(events) == {"a": 2}
    assert quota([{"type": "result"}]) is None


# --- as the judge's transport ------------------------------------------------


def test_build_judge_reads_the_verdict_through_the_wrapper(profile, tmp_path):
    control(profile, reply="verdict", score=0.5)
    wrapper = call(profile, tmp_path, model="judge-model", effort="low", timeout_s=30)

    (judgement,) = build_judge(wrapper)([hunk()])

    assert judgement == Judgement("t:1.1", 0.5, "stub verdict")
    (recorded,) = calls(profile)
    assert recorded["stdin"].startswith(RUBRIC)
    assert recorded["argv"][recorded["argv"].index("--effort") + 1] == "low"


def test_a_call_failing_on_every_claim_is_the_harness_fault_the_evaluator_retries(
    profile, tmp_path
):
    """One stub answers every call the same way, so every hunk fails, and
    that is the case ``build_judge`` turns into a ``JudgeError`` rather than
    a batch of zeros: the evaluator reads it as infrastructure and retries."""
    control(profile, reply="nonzero", stderr="down\n")

    with pytest.raises(JudgeError, match="exited 3: down"):
        build_judge(call(profile, tmp_path))([hunk(), hunk("t:2.1", text="Two.")])


# --- as a settings value ----------------------------------------------------


def test_the_wrapper_survives_the_deep_copy_asdict_performs(profile, tmp_path):
    wrapper = call(profile, tmp_path)

    twin = copy.deepcopy(wrapper)

    assert repr(twin) == repr(wrapper) and twin.argv() == wrapper.argv()
```

Append to `tests/experiment/optimize/test_run.py` (after `_settings`):

```python
def test_a_claude_cli_proposer_is_recorded_by_its_form(tmp_path, plugin_root):
    """A result read months later must name the proposer, not an address."""
    from ai_rfc.experiment.optimize.claude_cli import ClaudeCliCall
    from ai_rfc.experiment.optimize.run import _write_result

    settings = _settings(
        root=tmp_path,
        reflection_lm=ClaudeCliCall(
            "claude", tmp_path / "profile", "some-model", cwd=tmp_path / "cwd"
        ),
    )
    evaluator = SimpleNamespace(
        settings=SimpleNamespace(source_plugin_root=plugin_root), evaluations=0
    )
    result = SimpleNamespace(
        best_candidate="seed",
        best_score=0.0,
        candidates=[],
        val_subscores=[],
        best_idx=0,
        total_evals=0,
        metadata={},
    )

    path = _write_result(settings, evaluator, result, tmp_path / "result.json")

    record = json.loads(path.read_text())
    assert record["settings"]["reflection_lm"] == "claude-cli:some-model"
```

- [ ] **Step 2: Run to verify they fail**, as two commands, because a collection error in the first file would interrupt the session before the second ran:

```bash
SSLKEYLOGFILE= $PY -m pytest tests/experiment/optimize/test_claude_cli.py -q -p no:cacheprovider
SSLKEYLOGFILE= $PY -m pytest tests/experiment/optimize/test_run.py -q -p no:cacheprovider -k claude_cli_proposer
```

Expected: the first errors at collection with `ModuleNotFoundError: No module named 'ai_rfc.experiment.optimize.claude_cli'` (that collection error is the RED evidence for the module); the second fails with the same error at the test's import line.

- [ ] **Step 3: Implement** `ai_rfc/experiment/optimize/claude_cli.py`:

```python
"""``claude -p`` as a one-shot language model: the pilot's proposer and judge.

The optimizer's reflection LM and the judge's transport are the same shape,
one prompt in and one raw reply out, and both run through the CLI on the
experiment profile so that a pilot draws on the subscription behind it and
never on an API key. The prompt travels on stdin (a reflection prompt carries
four skill bodies), the reply is read from the stream-json result event, and
the child gets the five-variable environment every experiment session gets,
so nothing the shell holds reaches it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .. import ExperimentError
from ..profile import profile_env
from ..stream import assistant_text, parse_stream, result_event

#: The id form the CLI accepts for a proposer or judge that runs through
#: ``claude -p``; also what :class:`ClaudeCliCall` reports as its ``repr``,
#: which is what ``result.json`` records for a callable.
PREFIX = "claude-cli:"

#: How much of a failed call's stderr an error carries.
_STDERR_TAIL = 2000


def cli_model(value: str) -> str | None:
    """The model inside a ``claude-cli:<model>`` id.

    Args:
        value: A ``--reflection-lm`` or ``--judge-model`` argument.

    Returns:
        The model, or ``None`` when the id is not in that form and belongs to
        the litellm or API path.

    Raises:
        ExperimentError: If the form carries no model.
    """
    if not value.startswith(PREFIX):
        return None
    model = value[len(PREFIX) :].strip()
    if not model:
        raise ExperimentError(f"{value!r} names no model after {PREFIX}")
    return model


class ClaudeCliError(ExperimentError):
    """Raised when one ``claude -p`` call returns no usable reply.

    A proposer that raises stops the optimization, which is the intended
    reading: the run's own log names the cause and a relaunch under the same
    name resumes it. A judge that raises scores that one claim zero.
    """

    def __init__(
        self, message: str, *, exit_code: int | None = None, stderr_tail: str = ""
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr_tail = stderr_tail


def quota(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The last ``rate_limit_event``'s ``rate_limit_info``, if the stream had one.

    Under a subscription this is the only signal that a run is approaching
    its limit; a USD budget never fills.
    """
    for event in reversed(events):
        if event.get("type") == "rate_limit_event":
            info = event.get("rate_limit_info")
            return info if isinstance(info, dict) else {}
    return None


def _flatten(messages: list[dict[str, Any]]) -> str:
    """One prompt from a chat-messages list, each turn under its role."""
    parts = []
    for message in messages:
        role = str(message.get("role", "user")).capitalize()
        content = message.get("content", "")
        if not isinstance(content, str):
            content = "\n".join(
                str(block.get("text", "")) if isinstance(block, dict) else str(block)
                for block in content
            )
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


def _decoded(data: str | bytes | None) -> str:
    if data is None:
        return ""
    return data if isinstance(data, str) else data.decode("utf-8", "replace")


class ClaudeCliCall:
    """One ``claude -p`` per call, on a model, through a profile.

    Holds only strings, paths and numbers: a run's settings are deep-copied
    into ``result.json`` at the end, and its ``repr`` is what lands there.

    Args:
        claude_bin: The CLI to launch.
        profile_dir: The authenticated ``CLAUDE_CONFIG_DIR`` the call runs
            under; the subscription behind it is what the call draws on.
        model: The model id, as ``--model`` takes it.
        cwd: Where the child runs; created on the first call. Every
            customization source is disabled by the argv, so this only has
            to exist.
        effort: The CLI's ``--effort`` level.
        timeout_s: Seconds before the child is killed and the call raises.
    """

    def __init__(
        self,
        claude_bin: str,
        profile_dir: Path,
        model: str,
        *,
        cwd: Path,
        effort: str = "high",
        timeout_s: int = 120,
    ) -> None:
        self.claude_bin = claude_bin
        self.profile_dir = profile_dir
        self.model = model
        self.cwd = cwd
        self.effort = effort
        self.timeout_s = timeout_s

    def __repr__(self) -> str:
        return f"{PREFIX}{self.model}"

    def argv(self) -> list[str]:
        """The complete argument vector.

        Measured on Claude Code 2.1.260 (2026-09-04): with ``--safe-mode``
        alone the child still read an output style and plan mode from the
        settings on disk, and a judge answer cited "Plan mode active";
        ``--setting-sources ""`` and ``--permission-mode dontAsk`` closed
        that. ``--tools ""`` makes the proposer a model rather than an agent
        that could load the very skills it is rewriting.
        """
        return [
            self.claude_bin,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.model,
            "--effort",
            self.effort,
            "--safe-mode",
            "--setting-sources",
            "",
            "--permission-mode",
            "dontAsk",
            "--tools",
            "",
            "--no-session-persistence",
        ]

    def env(self) -> dict[str, str]:
        """The child's whole environment; nothing else is inherited."""
        return profile_env(self.profile_dir)

    def __call__(self, prompt: str | list[dict[str, Any]]) -> str:
        """Send one prompt and return the model's reply text.

        Args:
            prompt: The text, or a chat-messages list as gepa may pass one.

        Returns:
            The result event's text.

        Raises:
            ClaudeCliError: On a missing binary, a non-zero exit, a timeout,
                output that is not stream-json, a result marked as an error,
                or an empty reply.
        """
        text = prompt if isinstance(prompt, str) else _flatten(prompt)
        self.cwd.mkdir(parents=True, exist_ok=True)
        try:
            completed = subprocess.run(
                self.argv(),
                input=text,
                cwd=self.cwd,
                env=self.env(),
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except FileNotFoundError as missing:
            raise ClaudeCliError(f"cannot run {self.claude_bin}: {missing}") from None
        except subprocess.TimeoutExpired as expired:
            tail = _decoded(expired.stderr)[-_STDERR_TAIL:]
            raise ClaudeCliError(
                f"{self!r} gave no reply within {self.timeout_s} s",
                stderr_tail=tail,
            ) from None
        tail = completed.stderr[-_STDERR_TAIL:]
        if completed.returncode != 0:
            raise ClaudeCliError(
                f"{self!r} exited {completed.returncode}: {tail}",
                exit_code=completed.returncode,
                stderr_tail=tail,
            )
        try:
            events = parse_stream(completed.stdout)
        except ExperimentError as error:
            raise ClaudeCliError(
                f"{self!r} wrote something that is not stream-json: {error}",
                exit_code=completed.returncode,
                stderr_tail=tail,
            ) from None
        final = result_event(events)
        if final is None:
            raise ClaudeCliError(
                f"{self!r} ended without a result event",
                exit_code=completed.returncode,
                stderr_tail=tail,
            )
        if final.get("is_error"):
            limit = quota(events)
            suffix = "" if limit is None else f" (rate limit: {json.dumps(limit)})"
            raise ClaudeCliError(
                f"{self!r} reported an error: {str(final.get('result', ''))[:500]}"
                f"{suffix}",
                exit_code=completed.returncode,
                stderr_tail=tail,
            )
        reply = str(final.get("result") or assistant_text(events))
        if not reply.strip():
            raise ClaudeCliError(
                f"{self!r} returned an empty reply",
                exit_code=completed.returncode,
                stderr_tail=tail,
            )
        return reply
```

- [ ] **Step 4: Run to verify.** All tests in `test_claude_cli.py` and the new `test_run.py` test PASS: `SSLKEYLOGFILE= $PY -m pytest tests/experiment/optimize/test_claude_cli.py tests/experiment/optimize/test_run.py tests/experiment/optimize/test_judge.py -q -p no:cacheprovider`. Lint `claude_cli.py` and both test files (mypy: `subprocess.run(..., input=text, text=True)` types cleanly; `ClaudeCliCall.__call__` satisfies `Callable[[str], str]` by contravariance).

- [ ] **Step 5: Commit:**

```bash
git add ai_rfc/experiment/optimize/claude_cli.py tests/experiment/optimize/test_claude_cli.py tests/experiment/optimize/test_run.py
git commit -m "feat(optimize): ClaudeCliCall runs claude -p as the proposer and the judge"
```

---

### Task 4: Real-tool probe of the wrapper on the experiment profile

**Files:** none edited unless the probe shows a mismatch (then `claude_cli.py` and `test_claude_cli.py`, one fix commit). Everything the probe prints goes into the ledger.

This is the plan's real-tool probe: the argv, the environment and the stream-json reader were written against `claude --help` and a measurement from 2026-09-04, never against this CLI on this profile. It is **subscription spend** (one short call on the Max profile) and is run only after the user approves it in the session, with the exact command in front of them.

- [ ] **Step 1: Announce and get approval.** Put to the user with `AskUserQuestion`: up to two `claude -p` calls on `~/ai-rfc-experiments/profile`, model `claude-sonnet-5`, effort `low`, a three-line prompt asking for a fenced block, cwd `/tmp/claude/gepa-no-key/probe`, `--no-session-persistence`; worst case two short subscription-metered requests. Proceed only on an explicit yes.

- [ ] **Step 2: Run the probe** (sandbox off; the keychain is outside the allowlist), from `AIRFC`. The first call runs the wrapper's own argv and environment raw, so the whole event stream is captured (event types, any `rate_limit_event` on a successful call, the result's fields); the second runs the shipping path, `ClaudeCliCall.__call__`:

```bash
mkdir -p /tmp/claude/gepa-no-key/probe
test -z "$ANTHROPIC_API_KEY" && echo key-unset
ls -la ~/ai-rfc-experiments/profile ~/ai-rfc-experiments/profile/projects 2>/dev/null > /tmp/claude/gepa-no-key/profile-before.txt
SSLKEYLOGFILE= $PY -c '
import json, subprocess
from pathlib import Path
from ai_rfc.experiment.optimize.claude_cli import ClaudeCliCall, quota
from ai_rfc.experiment.stream import parse_stream, result_event
prompt = "Reply with exactly one fenced code block.\nInside it put the single word PROBE.\nNothing else."
call = ClaudeCliCall("claude", Path.home() / "ai-rfc-experiments" / "profile",
                     "claude-sonnet-5", cwd=Path("/tmp/claude/gepa-no-key/probe"),
                     effort="low", timeout_s=120)
print("argv:", call.argv())
print("env keys:", sorted(call.env()))
call.cwd.mkdir(parents=True, exist_ok=True)
raw = subprocess.run(call.argv(), input=prompt, cwd=call.cwd, env=call.env(),
                     capture_output=True, text=True, timeout=120)
print("exit:", raw.returncode)
print("stderr tail:", raw.stderr[-500:])
events = parse_stream(raw.stdout)
print("event types:", [e.get("type") + ("/" + e["subtype"] if e.get("subtype") else "") for e in events])
print("rate limit on success:", json.dumps(quota(events)))
print("result fields:", sorted((result_event(events) or {}).keys()))
print("result:", repr((result_event(events) or {}).get("result")))
print("wrapper reply:", repr(call(prompt)))
'
ls -la ~/ai-rfc-experiments/profile ~/ai-rfc-experiments/profile/projects 2>/dev/null > /tmp/claude/gepa-no-key/profile-after.txt
diff /tmp/claude/gepa-no-key/profile-before.txt /tmp/claude/gepa-no-key/profile-after.txt
```

Paste the raw stdout, the diff and any traceback into the ledger under "Task 4 probe". The CLI rewrites `.claude.json` in the config dir on every launch, so its size and mtime may change, and it rotates a backup of that file under `backups/` (one appears, one ages out; D11); what must not appear is a new transcript under `projects/` (that is what `--no-session-persistence` prevents) or any other new file.

- [ ] **Step 3: Rule on every mismatch.** The expected outcome is a reply containing a fenced block with `PROBE`. Anything else is a numbered deviation entry and, where the fix is in the wrapper, one commit `fix(optimize): <what the probe showed>` with its test adjusted:
  - `Not logged in` or an auth error: `--setting-sources ""` or `--safe-mode` interferes with the profile's OAuth. Drop the offending flag, keep the rest, re-probe, and record the leak that flag was closing as a known residual.
  - a `rate_limit_event` present: paste its `rate_limit_info` shape and confirm `quota()` reads it; adjust `quota` if the key is not `rate_limit_info`. Record in the ledger whether the event appears on a successful call: the GEPA-PILOT procedure assumes the quota signal is visible in the run's log, and today the wrapper surfaces it only inside an error.
  - the CLI rejects a flag: paste the message, remove the flag, re-probe.
  - `is_error` on a plain refusal text: the error path works; note the wording.
  - a new transcript under `profile/projects/` or any other new file in the profile: stop, report, and do not run Task 5 until the cause is found.

- [ ] **Step 4: Mark the task complete** in the ledger with the pasted output and the profile diff.

---

### Task 5: The `claude-cli:` form in `optimize run`, its refusals, its consent text, and the README

**Files:**
- Modify: `AIRFC/ai_rfc/experiment/cli.py` (`:35` constants, `:222-231` imports, `:264-336` pilot and fake blocks, `:342-355` consent, `:366-367` pricing check, `:393-410` evaluator, `:796-813` help text)
- Modify: `AIRFC/tests/experiment/test_cli_optimize.py`
- Modify: `AIRFC/README.md:155-168` and `:198-212`

**Interfaces:**
- Consumes: `ClaudeCliCall`, `cli_model`, `PREFIX` (Task 3); `OPTIMIZE_DIR` from `.optimize.run`; `profile_dir` from `.paths` (already imported).
- Produces: `JUDGE_EFFORT = "low"` and `JUDGE_TIMEOUT_S = 120` in `cli.py`; `optimize run --stage pilot` accepting `claude-cli:<model>` for `--reflection-lm` and `--judge-model`.

- [ ] **Step 1: Write the failing tests.** Append to `tests/experiment/test_cli_optimize.py` (after `_priced`):

```python
def _no_key(*extra):
    """A pilot whose proposer and judge both run through claude -p."""
    return [
        "--max-evals",
        "30",
        "--model",
        "some-agent-model",
        "--reflection-lm",
        "claude-cli:some-proposer",
        "--judge-model",
        "claude-cli:some-judge",
        *extra,
    ]


def test_a_cli_proposer_refuses_a_token_cost_before_asking_for_yes(
    tmp_path, examples_file, toolchain_record, monkeypatch, capsys
):
    """gepa meters a callable at 0.00, so the cap would be a promise nothing
    enforces; naming it beside a claude-cli: proposer is refused, and refused
    before consent so a wrong launch line never reaches --yes."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    code = cli.main(
        _pilot(
            tmp_path,
            examples_file,
            toolchain_record,
            *_no_key("--max-token-cost", "5", "--yes"),
        )
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "--max-token-cost" in captured.err and "claude-cli:" in captured.err
    assert "worst case" not in captured.out
    assert not (tmp_path / "root").exists()


def test_a_cli_proposer_does_not_want_a_token_cost(
    tmp_path, examples_file, toolchain_record, monkeypatch, capsys
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    code = cli.main(
        _pilot(
            tmp_path,
            examples_file,
            toolchain_record,
            "--reflection-lm",
            "claude-cli:some-proposer",
            "--yes",
        )
    )

    err = capsys.readouterr().err
    assert code == 1
    for flag in ("--max-evals", "--model", "--judge-model"):
        assert flag in err
    assert "--max-token-cost" not in err


def test_a_no_key_pilot_reaches_the_consent_print_and_waits_for_yes(
    tmp_path, examples_file, toolchain_record, monkeypatch, capsys
):
    """Nothing bills a key, so the worst case is counted in sessions and calls
    against the subscription, with --max-evals and --timeout-s as the caps."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    code = cli.main(
        _pilot(tmp_path, examples_file, toolchain_record, *_no_key("--timeout-s", "2400"))
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "2 x 30 harness sessions" in captured.out
    assert "2400 s" in captured.out
    assert "claude-cli:some-proposer" in captured.out
    assert "claude-cli:some-judge" in captured.out
    assert "one judge call per anchored claim" in captured.out
    assert "subscription" in captured.out
    assert captured.out.startswith("worst case: 2 x 30 harness sessions")
    assert "--yes" in captured.err
    assert "ANTHROPIC_API_KEY" not in captured.err
    assert not (tmp_path / "root").exists()


def test_a_cli_proposer_beside_an_api_judge_still_wants_the_key(
    tmp_path, examples_file, toolchain_record, monkeypatch, capsys
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    code = cli.main(
        _pilot(
            tmp_path,
            examples_file,
            toolchain_record,
            *_no_key("--judge-model", "some-api-judge", "--yes"),
        )
    )

    assert code == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err
    assert not (tmp_path / "root").exists()


def test_a_mixed_pilot_says_which_role_bills_the_key(
    tmp_path, examples_file, toolchain_record, monkeypatch, capsys
):
    """A CLI proposer beside an API judge is allowed; the consent text must
    then say the judge bills the key while the rest draws on the profile."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-used-by-this-test")

    code = cli.main(
        _pilot(
            tmp_path,
            examples_file,
            toolchain_record,
            *_no_key("--judge-model", "some-api-judge"),
        )
    )

    captured = capsys.readouterr()
    assert code == 1
    assert "the judge on some-api-judge bills ANTHROPIC_API_KEY" in captured.out
    assert "nothing here bills a key" not in captured.out
    assert "--yes" in captured.err


@with_gepa
def test_a_no_key_pilot_starts_with_the_wrapper_in_both_roles(
    tmp_path, examples_file, toolchain_record, monkeypatch, capsys
):
    """The pricing refusal is skipped for a claude-cli: proposer, and the
    settings the search receives carry the form, no cost cap, and a judge."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")

    from ai_rfc.experiment.optimize import run as run_module

    searched = []

    def _search_nothing(settings, evaluator):
        searched.append((settings, evaluator))
        return SimpleNamespace(best_score=0.0, candidates=[], total_evals=0)

    monkeypatch.setattr(run_module, "run", _search_nothing)

    code = cli.main(
        _pilot(
            tmp_path,
            examples_file,
            toolchain_record,
            *_no_key("--yes", "--effort", "xhigh", "--timeout-s", "2400"),
        )
    )

    assert code == 0, capsys.readouterr().err
    ((settings, evaluator),) = searched
    assert repr(settings.reflection_lm) == "claude-cli:some-proposer"
    assert settings.max_token_cost is None
    assert settings.reflection_lm.effort == "xhigh"
    assert settings.reflection_lm.timeout_s == 2400
    assert settings.reflection_lm.cwd == tmp_path / "root" / "optimize" / "pilot-1"
    assert settings.reflection_lm.profile_dir == tmp_path / "root" / "profile"
    assert callable(evaluator.settings.judge)


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--reflection-lm", "claude-cli:some-proposer"),
        ("--judge-model", "claude-cli:some-judge"),
        ("--reflection-lm", "anthropic/claude-sonnet-4-6"),
    ],
)
def test_the_fake_stage_refuses_a_named_proposer_or_judge(
    tmp_path, examples_file, toolchain_record, capsys, flag, value
):
    """A rehearsal proposes the seed back and rates every claim itself; a
    model named here is one that would be paid for in a pilot."""
    code = cli.main(_rehearsal(tmp_path, examples_file, toolchain_record, flag, value))

    err = capsys.readouterr().err
    assert code == 1
    assert flag in err and "--stage pilot" in err
    assert not (tmp_path / "root").exists()
```

`_rehearsal` is defined later in the module (`:559`); place the fake-stage test after it, or move `_rehearsal` above the new tests. Keep every existing test unchanged; the litellm path's refusals, the `245.00` consent figure and the unpriced-id refusal must stay green.

- [ ] **Step 2: Run to verify they fail.** `SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_cli_optimize.py -q -p no:cacheprovider` → the seven new tests FAIL (`--max-token-cost` reported missing, `ANTHROPIC_API_KEY` refusal from `anthropic_transport`, no "harness sessions" line, fake stage exiting 0 or on another refusal); `test_a_no_key_pilot_starts_with_the_wrapper_in_both_roles` skips on 3.10 and fails on 3.11 (`SSLKEYLOGFILE= $PY311 -m pytest tests/experiment/test_cli_optimize.py -q -p no:cacheprovider -k no_key`).

- [ ] **Step 3: Implement.** In `cli.py`:

(a) After `FAKE_MODEL` (`:35`):

```python
#: What a ``claude-cli:`` judge runs at. Measured on 2026-09-04: a short
#: grading call takes 3 to 4 s at low effort and 112 s at the default, and
#: the judge makes one call per anchored claim per evaluation, fourteen on
#: the largest seed run, so the default would add half an hour to each.
JUDGE_EFFORT = "low"
JUDGE_TIMEOUT_S = 120
```

(b) In `_optimize_run`'s imports (`:222-231`), add a line `from .optimize.claude_cli import ClaudeCliCall, cli_model` and add `OPTIMIZE_DIR` to the existing `from .optimize.run import RESULT_FILE, RunSettings, SeedEchoLM, load_examples, log` line (isort keeps one import per module).

(c) Replace `:264-293` (from `plugin_root = …` through the pilot branch's `build = None`) with:

```python
    plugin_root = (args.plugin_root or _default_plugin_dir()).resolve()
    seed = seed_from_plugin(plugin_root)
    max_evals = args.max_evals
    max_token_cost = args.max_token_cost
    profile = args.profile_dir or profile_dir(root)
    judge: Judge
    reflection_lm: str | SeedEchoLM | ClaudeCliCall
    build: Callable[[Campaign, Path], BuildReport | None] | None

    if args.stage == "pilot":
        proposer = None if args.reflection_lm is None else cli_model(args.reflection_lm)
        cli_judge = None if args.judge_model is None else cli_model(args.judge_model)
        wanted = [
            ("--max-evals", args.max_evals),
            ("--model", args.model),
            ("--reflection-lm", args.reflection_lm),
            ("--judge-model", args.judge_model),
        ]
        if proposer is None:
            wanted.insert(1, ("--max-token-cost", args.max_token_cost))
        missing = [flag for flag, value in wanted if value is None]
        if missing:
            raise ExperimentError(
                "a pilot pays for every evaluation and every proposal, so it "
                f"names each cost itself; missing {', '.join(missing)}"
            )
        if proposer is not None and max_token_cost is not None:
            raise ExperimentError(
                "--max-token-cost cannot bind with a claude-cli: proposer: gepa "
                "meters a callable at 0.00, so the cap would be a promise nothing "
                "enforces. Drop it; --max-evals and --timeout-s are the caps"
            )
        claude_bin = args.claude_bin or "claude"
        # Where the one-shot calls run; created on their first call, so a
        # refusal below still leaves nothing behind.
        calls_dir = root / OPTIMIZE_DIR / args.name
        if cli_judge is None:
            judge = build_judge(anthropic_transport(args.judge_model))
        else:
            judge = build_judge(
                ClaudeCliCall(
                    claude_bin,
                    profile,
                    cli_judge,
                    cwd=calls_dir,
                    effort=JUDGE_EFFORT,
                    timeout_s=JUDGE_TIMEOUT_S,
                )
            )
        if proposer is None:
            reflection_lm = args.reflection_lm
        else:
            reflection_lm = ClaudeCliCall(
                claude_bin,
                profile,
                proposer,
                cwd=calls_dir,
                effort=args.effort,
                timeout_s=args.timeout_s,
            )
        model = args.model
        build = None
```

(d) In the fake branch, after the `--claude-bin` identity refusal (`:307-314`) and before the `LITELLM_LOCAL_MODEL_COST_MAP` comment, insert:

```python
        named = [
            flag
            for flag, value in (
                ("--reflection-lm", args.reflection_lm),
                ("--judge-model", args.judge_model),
            )
            if value is not None
        ]
        if named:
            raise ExperimentError(
                f"--stage fake proposes the seed back and rates every claim "
                f"itself, so {', '.join(named)} names a model this stage never "
                "calls and a pilot would pay for. Use --stage pilot to name one"
            )
```

(e) Replace the consent block (`:342-355`) with:

```python
    if args.stage == "pilot":
        per_example = max(example.budget_usd for example in examples)
        if max_token_cost is None:
            print(
                f"worst case: 2 x {max_evals} harness sessions on {model} of up to "
                f"{args.timeout_s} s each (${per_example:.2f} is one session's own "
                f"cap, not a bill), plus up to {max_evals} proposer calls on "
                f"{reflection_lm!r} of up to {args.timeout_s} s each, plus one "
                f"judge call per anchored claim per evaluation on {args.judge_model}"
            )
            meter = (
                "nothing here bills a key: every call draws on the subscription "
                "behind the profile, whose usage limit is the only meter"
                if cli_judge is not None
                else f"the judge on {args.judge_model} bills ANTHROPIC_API_KEY; "
                "the sessions and the proposer draw on the subscription behind "
                "the profile, whose usage limit is their only meter"
            )
            print(
                "the factor of two is the evaluator's one retry per faulted run; "
                f"{meter}, and --max-evals and --timeout-s are the only caps"
            )
        else:
            worst_case = 2 * max_evals * per_example + max_token_cost
            print(
                f"worst case: 2 x {max_evals} evaluations x ${per_example:.2f} + "
                f"${max_token_cost:.2f} proposer = ${worst_case:.2f}"
            )
            print(
                "the factor of two is the evaluator's one retry per faulted run; "
                "plus judge calls (one short request per anchored claim per "
                "evaluation), which are not in the figure above"
            )
        if not args.yes:
            raise ExperimentError("pass --yes to spend it")
```

(f) Change `:366-367` to skip the pricing check for a CLI proposer:

```python
    if args.stage == "pilot":
        if cli_model(args.reflection_lm) is None:
            _refuse_an_unpriced_reflection_model(args.reflection_lm)
```

(g) In the `EvaluatorSettings(...)` call (`:396`), replace `profile_dir=args.profile_dir or profile_dir(root),` with `profile_dir=profile,`.

(h) Help text (`:796-813`):

```python
    optimize_run.add_argument(
        "--max-token-cost",
        type=float,
        default=None,
        help="USD ceiling on the proposer's own spend; required by a pilot whose "
        "--reflection-lm is a LiteLLM id, refused beside a claude-cli: one, which "
        "gepa meters at zero.",
    )
    optimize_run.add_argument(
        "--reflection-lm",
        type=_model,
        default=None,
        help="Pilot only: the proposer. A LiteLLM model id, or claude-cli:<model> "
        "to run it through `claude -p` on --profile-dir with no API key.",
    )
    optimize_run.add_argument(
        "--judge-model",
        type=_model,
        default=None,
        help="Pilot only: the model rating each anchored claim. An Anthropic API "
        "id (needs ANTHROPIC_API_KEY), or claude-cli:<model> to run it through "
        "`claude -p` on --profile-dir at low effort.",
    )
```

Update the `_optimize_run` docstring's first paragraph to say "names each model and, for a LiteLLM proposer, both ceilings itself".

(i) README. Replace `:198-212` (the two "Stage `pilot`" paragraphs up to "…never fetches that map.") with:

```markdown
**Stage `pilot`** spends and says so first. It refuses to start unless
`--max-evals`, `--model`, `--reflection-lm` and `--judge-model` are all given —
nothing that costs is defaulted — then prints the worst case and stops until
`--yes`. The proposer and the judge each take one of two forms:

- `claude-cli:<model>` runs the role through `claude -p` on the profile under
  `--profile-dir`, with the prompt on stdin, every customization source
  disabled, and no tools. Nothing bills a key: every call draws on the
  subscription behind that profile, whose usage limit is the only meter. The
  proposer runs at `--effort` with `--timeout-s`; the judge at low effort with
  a 120 s cap. `--max-token-cost` is refused beside a `claude-cli:` proposer,
  because gepa meters a callable at 0.00 and the cap would be a promise nothing
  enforces; `--max-evals` and `--timeout-s` are the caps, and the worst case is
  printed in sessions and calls: twice `--max-evals` harness sessions, up to
  `--max-evals` proposer calls, and one judge call per anchored claim per
  evaluation. The CLI exposes no temperature, so a rerun may grade a hunk
  differently; the judge cache dedups only identical level, text and hunk
  triples. This is the form this project's pilot uses.
- A LiteLLM id for `--reflection-lm` and an Anthropic API id for
  `--judge-model` bill `ANTHROPIC_API_KEY`, which must then be set. The worst
  case is printed in USD: twice `--max-evals` × the largest example budget,
  plus `--max-token-cost`, which is required here and binds only for an id
  litellm can price — the pilot refuses an unpriced one. The factor of two is
  the evaluator's one retry per faulted run; judge calls sit on top of that
  figure. This project does not use this form.

Stage `fake` sets `LITELLM_LOCAL_MODEL_COST_MAP=True`, so a rehearsal never
fetches litellm's cost map, and refuses any `--reflection-lm` or
`--judge-model`: it proposes the seed back and rates every claim itself.
```

And in "The environment" (`:155-168`), after the sentence ending "binds a TCP socket.", add:

```markdown
A pilot also needs the `claude` CLI on `PATH` and an authenticated profile:
`python -m ai_rfc.experiment profile init` creates one and prints the one-time
`claude auth login` command for it. No API key is needed or read.
```

Check the README's `preflight.py` mention at `:211` is gone with the replaced paragraph (the `:96` mention is the harness's own `preflight` verb and stays). The paragraph that follows the replaced block begins "It builds each\ndraft for real, so its `--toolchain` record must name executables that exist:"; after the rewrite its nearest antecedent would be Stage `fake`, so change that opening to "A pilot builds each draft for real, so its `--toolchain` record …" (D5).

- [ ] **Step 4: Run to verify.** Under 3.10: `SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_cli_optimize.py tests/experiment/optimize -q -p no:cacheprovider` all green (the gepa tests skip). Under 3.11, sandbox off: `SSLKEYLOGFILE= $PY311 -m pytest tests/experiment/optimize tests/experiment/test_cli_optimize.py -q -m "not slow" -p no:cacheprovider` green, count = baseline + the new tests. Then `SSLKEYLOGFILE= $PY311 -m ai_rfc.experiment optimize run --help` and read the three help strings. Lint `cli.py` and the test file on their own (the repository carries flake8 debt elsewhere).

- [ ] **Step 5: Commit:**

```bash
git add ai_rfc/experiment/cli.py tests/experiment/test_cli_optimize.py README.md
git commit -m "feat(optimize): accept claude-cli:<model> for the pilot's proposer and judge"
```

---

## Verification (the row's gate)

Run after Task 5, in this order, all from `AIRFC` with the sandbox off. Paste each output into the ledger and the final report.

1. **Both suites green with their counts.**

```bash
SSLKEYLOGFILE= $PY -m pytest tests -q -n auto -p no:cacheprovider 2>&1 | tail -3
SSLKEYLOGFILE= $PY311 -m pytest tests/experiment/optimize tests/experiment/test_cli_optimize.py -q -m "not slow" -p no:cacheprovider 2>&1 | tail -3
SSLKEYLOGFILE= $PY311 -m pytest tests/experiment/optimize/test_run.py -q -m slow -p no:cacheprovider 2>&1 | tail -3
```

Expected on 3.10: the measured baseline plus 40 passed and plus 1 skipped (Task 1 adds 3, Task 2 adds 9, Task 3 adds 19 plus 1 in `test_run.py`, Task 5 adds 9 of which the `with_gepa` one skips); from the 2026-09-05 baseline of 1129 / 10 that is 1169 passed and 11 skipped if no peer commit lands meanwhile (D3). On 3.11 the `not slow` selection rises by the 20 optimize tests and the 9 CLI tests, all passing (189 / 2 → 218 / 2). The two slow gepa tests pass. Peer commits landing mid-run move the totals; each task boundary attributes its delta by commit. The measured numbers are what the report states; these are the expectation to compare against.

2. **The dry pilot form reaches the consent print with no key.** Sandbox off (the toolchain verify probe writes outside the allowlist):

```bash
test -z "$ANTHROPIC_API_KEY" && echo key-unset
SSLKEYLOGFILE= $PY311 -m ai_rfc.experiment optimize run \
  --stage pilot --name gate-dry-2026-09-05 \
  --examples ~/ai-rfc-experiments/optimize/pilot-examples.json \
  --toolchain ~/ai-rfc-experiments/tools/toolchain.json \
  --panther-repo $PANTHER \
  --max-evals 30 --effort high --timeout-s 2400 \
  --model claude-sonnet-5 --judge-model claude-cli:claude-opus-5 \
  --reflection-lm claude-cli:claude-opus-5
```

Expected: the two consent lines on stdout naming `2 x 30 harness sessions`, `2400 s`, both `claude-cli:` ids and the subscription; `error: pass --yes to spend it` on stderr; exit 1; `ls ~/ai-rfc-experiments/optimize/` shows no `gate-dry-2026-09-05` directory. Paste it.

3. **The fake-stage rehearsal still completes** against the real examples spec and the scratch profile, under a fresh name so the 2026-09-05 rehearsal is untouched:

```bash
SSLKEYLOGFILE= $PY311 -m ai_rfc.experiment optimize run \
  --stage fake --name rehearsal-gate-2026-09-05 \
  --examples ~/ai-rfc-experiments/optimize/pilot-examples.json \
  --toolchain ~/ai-rfc-experiments/tools/toolchain.json \
  --profile-dir ~/ai-rfc-experiments/profile-rehearsal \
  --panther-repo $PANTHER
```

Expected: `best score: …`, `candidates: 1  evaluations: 9`, a `result.json` under `~/ai-rfc-experiments/optimize/rehearsal-gate-2026-09-05/`. Paste the three printed lines. (This is the only write under the evidence root the gate makes; leave the directory in place and list it in the report.)

4. **The probe** from Task 4 is already pasted in the ledger; cite it in the report.

5. **Trees and pointer.** `git status --short` clean in both repositories apart from the SP7b peer's file; `git ls-tree HEAD panther/plugins/services/testers/ai_rfc` in `$PANTHER` compared with `git rev-parse HEAD` in `AIRFC`. Pushing ai_rfc `main`, bumping the pointer (`chore(ai_rfc): bump to <sha> — the no-key proposer and judge`) and pushing the feature branch are each asked first, per the constraints.

## Deviation log

`docs/superpowers/plans/2026-09-05-arfc-gepa-no-key-deviations.md` in PANTHER, `git add -f`, committed with the task that produced each entry. Entry 0 records the three user-confirmed rulings and the eight planner rulings above, citing this plan's *Rulings taken in plan mode* section. Every later entry has the three fields: what the plan said, what the code or the tool showed, what was done.

## Out of scope, recorded for GEPA-PILOT

- The judge cannot pin temperature through the CLI; determinism rests on the judge cache (not wired in the CLI, a known follow-up) and on `--effort low`.
- The pilot's model ids, the fourteen-claim judge figure and the quota picture are stated by the GEPA-PILOT session at launch approval, not by this code.
- The isolation flags apply only to the proposer and the judge. Harness sessions are launched by `arms.claude_argv` (`arms.py:165`) with `--setting-sources project` and their plugin, and this row does not touch them.
- The GEPA-PILOT procedure in the executor prompt already says to read the refusals from `optimize run --help` and the README rather than from memory, so it needs no edit for this row.
