# ai_rfc Draft Quality v2 — SP7a "compile and lint" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every tagged draft revision compile through the Internet-Draft template's own toolchain, offline and reproducibly, and measure draft quality with a deterministic lint — the half of draft quality v2 that needs no manifest schema change.

**Architecture:** Two new substrate verbs (`ai-rfc draft build`, `ai-rfc draft lint`) wrap the template's `make` targets and a pure-Python lint; the MCP server and the `ai_rfc` parity CLI expose them as one core each; `revision_tag` gains a build stage before `git tag`. The harness provisions ONE shared, pinned template checkout with its venv, gems, node tools and a seeded reference cache (`toolchain.json` records everything), scaffolds draft repositories in the template's adopter layout, seals a per-workspace reference cache into the pristine digest, and freezes the per-cluster task prompt it actually runs. The skeleton, the rfc-style skill and a new figures skill tell the agent what a specification looks like.

**Tech Stack:** Python 3.10 (stdlib + PyYAML), pytest 8 + pytest-xdist, GNU make 3.81, kramdown-rfc 1.7.43 (Ruby 4.0.1, Bundler 4), xml2rfc 3.34.0, idnits 3.1.0, aasvg 0.5.7, git.

**Spec:** `docs/superpowers/specs/2026-09-02-arfc-draft-quality-design.md` (decisions D38–D52 and the "Settled by the toolchain run-and-see" section). Design-level plan: `~/.claude/plans/explore-deeply-panther-and-rustling-token.md`. Roadmap position: SP7 in `docs/superpowers/specs/2026-09-02-ai-rfc-extraction-and-flow-design.md`; SP7a is its first execution plan (SP7b structures, SP7c consolidation rounds, SP7d instrument follow).

## Global Constraints

- **Layout.** This plan executes AFTER SP1 (extraction) on the ai_rfc repository layout: `AIRFC` = the single submodule at `$PANTHER/panther/plugins/services/testers/ai_rfc` (its own git repository, github.com/ElNiak/ai_rfc). Packages: `ai_rfc/` (substrate), `ai_rfc/server/` (MCP server + parity CLI), `ai_rfc/experiment/` (driver, with `prompts/` and `guard.py`), `plugins/ai-rfc/` (skills, commands, `.mcp.json`), `docs/`. Tests: `tests/substrate/`, `tests/server/`, `tests/experiment/`. `PY` = `$PANTHER/.venv/bin/python`. Before Task 1 verify **all three**: `ls $AIRFC/ai_rfc/draft $AIRFC/tests/substrate`; `cd $AIRFC && $PY -c "import ai_rfc, ai_rfc.draft, ai_rfc.server, ai_rfc.experiment"`; and a clean `git status --short` in both repositories. If SP1 has not landed, or has landed only in part, STOP — do not execute this plan on the old layout. The `ls` alone is not sufficient: SP1's Task 7 is a designated confirmation point whose Step 4 moves the directory and re-adds the submodule *before* Steps 5–7 teach the builder, verify and commit, so a pause inside that window leaves the directories present while the package is not importable and PANTHER's tree is half-migrated and uncommitted.
- **Every file:line anchor in the spec was verified on the pre-move layout** (PANTHER `21523d10c`, harness `26e522a`); the content moved verbatim. Re-anchor by symbol (`grep -n "def <name>"`) before editing, never by remembered line number. Another session (`ai-rfc-extraction-packaging`) owns SP0/SP1 and commits to the same branch; run `git log -1 --format='%h %ad %s' --date=format:'%H:%M:%S'` and `git status --short` in BOTH `$PANTHER` and `$AIRFC` before every task. **If `git status --short` lists files you did not touch, do not commit** — pre-commit stashes and restores a peer's unstaged work around your commit; wait or coordinate.
- **Three Task 4 snippets are SP1-contingent — re-derive, do not trust** (independent review, 2026-09-03). (a) Step 3's `return Context(workspace=..., toolchain=...)` omits `panther_repo`, which today's `server/paths.py` `Context` requires with no default; check SP1's landed `paths.py` and keep the field if it survived the move. (b) Step 1's three new tests take a `fixture_workspace` parameter that today exists only in the experiment suite's `conftest.py` — the server suite provides `make_workspace` and `workspace`; check the landed server conftest first. (c) `recorded`, in `test_tag_revision_refuses_when_the_build_has_findings`, is not a fixture today but a private helper *function* `_recorded(workspace, tag=...)` called inside the test body — a shape change, not a rename.
- **The four build diagnostic regexes are unvalidated against real tool output.** `_OFFLINE_STUB`, `_XML2RFC_UNRESOLVED`, `_KRAMDOWN_WARNING` and `_IDNITS_SUMMARY` are exercised only by tests whose fake `make` stderr was written alongside the regexes, and the one real-toolchain test asserts only `exit_code == 0` and the outputs. Before Task 10, run one real build against a draft citing a deliberately unresolvable reference and confirm the broken-reference path actually fires. A regex that never matches turns the hard build gate (D49) into a no-op that reports success.
- **Two SP7b hooks are named here but not built.** `LintReport.extra` is described as where SP7b adds its `structures` block, but `lint()` never populates it and the dataclass is frozen, so SP7b needs a new `lint()` keyword; and Task 4's `draft_lint` core filters the report through the closed `_METRIC_KEYS` tuple, which has no `extra`, so SP7b must extend it or its structure metrics never reach the tool and CLI output. SP7b owns both; neither is designed in this plan.
- **Stage by explicit path**: never `git add -A` or `git add .`. Commit format in `$AIRFC`: `type: lowercase summary` (no scope — that repository's history); in `$PANTHER`: `type(scope): lowercase summary`. No `--no-verify`; a pre-commit failure is fixed and re-staged. `docs/` under `$PANTHER` is gitignored but tracked → `git add -f`.
- **Tests**: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto` (baseline after SP1: 769 = 390 substrate + 339 experiment + 40 server, all green). Sandbox off for `pytest`, `pip`, `npm`, `bundle`, nested-git writes and `git push`. `mypy --follow-imports=silent`; `flake8 --max-line-length=88`; `black --check`; ruff runs as a pre-commit hook only.
- **Never run** `panther docs build`, `panther_builder.py clean|package-dev` (both `rmtree` `$PANTHER/docs/`), or `python -m ai_rfc.experiment audit|analyze` against `~/ai-rfc-experiments/campaigns/mark-full-1` or `~/arfc-experiments/campaigns/pilot-aioquic-w02-11-20260831` (they rewrite evidence).
- **The substrate stays model-free and, except `forge`, network-free.** `draft build` runs the template's `make` with the network denied (`KRAMDOWN_OFFLINE=1`, `xml2rfc -N --cache`, a black-hole proxy). The only networked step in this plan is `experiment toolchain provision`, run once by an operator.
- **Toolchain facts (verified 2026-09-03, `~/ai-rfc-experiments/tools/toolchain.json`)**: Ruby 4.0.1 runs kramdown-rfc 1.7.43; Bundler 4 puts binstubs under `.gems/ruby/4.0.0/bin` (NOT `.gems/bin`), so make gets `kramdown-rfc=<binstub> GEM_PATH=<gem_path> GEM_HOME=<gem_path>` as command-line variables (make exports those to recipes); `XML2RFC_OPTS` passed on the command line silences `config.mk`'s `+= --cache=…`, so `--cache=<refcache>` is repeated explicitly; never set `CI=true`; the bcp14 boilerplate injects RFC 2119/8174 itself — the skeleton must not list them; `make idnits` needs the draft committed in a clone (`build-targets.sh` reads `HEAD`); Apple make 3.81 suffices.
- Line length 88, Google-style docstrings on public functions, `from __future__ import annotations`, comments only for a non-obvious *why*. No backward-compatibility shims. Fixed dates in every fixture (`2026-01-01T00:00:09+00:00` style, as the existing fixtures do). A test needle must never match a fixture's own name; a RED test must fail at the path the change addresses.

## File Structure

| File (under `$AIRFC`) | Task | Responsibility after the change |
|---|---|---|
| `ai_rfc/draft/gate.py` | 1 | `draft_text(draft_repo, ref)` — the one reader of "the draft file at a ref", used by `cited_ids`, `build` and `lint` |
| `ai_rfc/draft/build.py` (new) | 1 | Load `toolchain.json`, probe the executables, clone the draft at a ref into a scratch directory, run the template's `make` offline, parse the trace, write `build-report.json` |
| `ai_rfc/draft/lint.py` (new) | 2 | Deterministic quality metrics and findings over one draft text (+ optional manifest) → `lint-report.json` |
| `ai_rfc/draft/cli.py` | 1, 2 | Verbs `build` and `lint` beside `checkpoint`, `gate`, `completeness` |
| `ai_rfc/README.md` | 1 | Duplication table row for `build.py`'s `_git`; verb table rows |
| `ai_rfc/pipeline/{stages,state,run,cli}.py` | 3 | Stages 10 `lint`, 11 `build`; one optional-stage predicate shared by `next_stage` and the runner |
| `ai_rfc/server/paths.py` | 4 | `Context.toolchain: Path | None` from `AI_RFC_TOOLCHAIN` |
| `ai_rfc/server/core/build.py` (new) | 4 | `draft_build(ctx, ref)` and `draft_lint(ctx, worktree)` wrappers over the substrate verbs |
| `ai_rfc/server/core/draft.py` | 4 | `tag_revision` runs the build stage between the manifest gate and `git tag` |
| `ai_rfc/server/{tools,cli}.py`, `docs/parity.md` | 4 | Tools `ai_rfc_draft_build`, `ai_rfc_draft_lint`; verbs `draft-build`, `draft-lint`; two parity rows; arm-C column reads "not available" |
| `ai_rfc/experiment/toolchain.py` (new) | 5 | `provision()` (network once) and `verify()` (offline self-test) over one shared template checkout |
| `ai_rfc/experiment/{config,runner,arms,cli}.py` | 5, 8 | `AI_RFC_TOOLCHAIN` in every session env; `campaign init` refuses without a verified toolchain; `Campaign.toolchain_sha256`/`template_home`; frozen `task.tmpl.md`; honest `prompt.md` |
| `ai_rfc/experiment/workspace.py` | 6, 7 | Adopter-layout scaffold; `Target.references`; per-workspace `refcache/`; `migrate_draft()` |
| `ai_rfc/experiment/per_cluster.py` | 8 | Renders each session's task from the campaign's frozen template |
| `ai_rfc/experiment/prompts/{loop.tmpl.md,draft-skeleton.md}`, `ai_rfc/experiment/render.py` | 9 | Build-before-tag step and `{{draft_build}}` slot; full I-D skeleton; new neutral texts |
| `plugins/ai-rfc/skills/ai-rfc-rfc-style/{SKILL.md,references/keyword-policy.md}`, `plugins/ai-rfc/skills/ai-rfc-figures/SKILL.md` (new), `plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` (regenerated) | 9 | What a specification looks like; MUST needs enforcing evidence; how to draw a cited ASCII figure |
| `docs/experiment-protocol.md`, `README.md` | 10 | Build gate, toolchain, arm-C freeze recorded |
| `tests/substrate/draft/{test_build,test_lint}.py`, `tests/substrate/pipeline/test_state.py`, `tests/server/{test_build,test_parity}.py`, `tests/experiment/{test_toolchain,test_workspace,test_config,test_runner,test_per_cluster,test_render}.py` | all | One test module per unit; fixtures with fixed dates |

Vocabulary the tasks share: **toolchain record** = the JSON file `toolchain.json` (`AI_RFC_TOOLCHAIN` names it); **template home** = the pinned library checkout it points at (`main.mk` lives there); **refcache** = a directory of `reference.*.xml` files both kramdown-rfc and xml2rfc read; **scratch** = `<out>/build/scratch`, a clone of the draft at the built ref; **draft file** = the single `draft-*.md` at the repository root.

---

### Task 1: `ai-rfc draft build` — the template toolchain as a substrate verb

**Files:**
- Modify: `ai_rfc/draft/gate.py` (`cited_ids`: extract the tree listing + `git show` into `draft_text`)
- Create: `ai_rfc/draft/build.py`
- Modify: `ai_rfc/draft/cli.py` (verb `build`), `ai_rfc/README.md` (verb table + duplication table)
- Test: `tests/substrate/draft/test_build.py` (new), `tests/substrate/draft/test_gate.py` (one test for `draft_text`)

**Interfaces:**
- Consumes: `ai_rfc.draft.gate.GateError`; the git repository under test fixtures (`tests/substrate/draft/conftest.py` `git()` helper).
- Produces: `draft_text(draft_repo: Path, ref: str) -> tuple[str, str]` (file name, text; raises `GateError` when the ref has no single `draft-*.md`); `load_toolchain(path: Path) -> Toolchain`; `probe_toolchain(toolchain: Toolchain) -> tuple[str, ...]`; `build(draft_repo: Path, *, toolchain: Toolchain, out: Path, ref: str = "HEAD", targets: tuple[str, ...] = DEFAULT_TARGETS, date: str | None = None, refcache: Path | None = None, runner: Runner | None = None) -> BuildReport`; `BuildReport.findings: tuple[str, ...]`, `BuildReport.to_json() -> str`; constants `TOOLCHAIN_ENV = "AI_RFC_TOOLCHAIN"`, `BUILD_DIR = "build"`, `REPORT_FILE = "build-report.json"`, `DEFAULT_TARGETS = ("txt", "html", "lint", "idnits")`; CLI verb `ai-rfc draft build DRAFTREPO --out DIR [--ref REF] [--toolchain PATH] [--refcache DIR] [--targets LIST] [--date YYYY-MM-DD] [--strict]` with exit 0/1/3 per the package table. Tasks 3 and 4 call `build`/the verb; Task 5's `verify()` calls `build` on the template example.

**Why this shape.** The template's `make` is the build; nothing here reimplements kramdown-rfc or xml2rfc. Building in a scratch clone keeps the draft repository's tree clean (make writes `.targets.mk`, `versioned/`, outputs) and gives `make idnits` the committed `HEAD` it reads. The runner is injected exactly as `forge/fetch.py` injects its transport, so every test runs against a fake `make` while the one integration test needs a provisioned toolchain and skips without it.

- [ ] **Step 1: Write the failing `draft_text` test**

Append to `tests/substrate/draft/test_gate.py`:

```python
from ai_rfc.draft.gate import draft_text


def test_draft_text_reads_the_single_draft_at_a_ref(draft_workspace):
    name, text = draft_text(draft_workspace["draft"], "draft-test-spec-00")
    assert name == "draft-test-spec.md"
    assert "`ai_rfc:spec:1.1`" in text and "`ai_rfc:spec:2.1`" not in text


def test_draft_text_refuses_a_ref_without_one_draft(draft_workspace, tmp_path):
    with pytest.raises(GateError) as excinfo:
        draft_text(draft_workspace["draft"], "no-such-ref")
    assert "no-such-ref" in str(excinfo.value)
```

(`draft_workspace` is the existing fixture in `tests/substrate/draft/conftest.py`; its dict key for the repository is whatever the fixture already returns — read the fixture's `return` statement and use that key. `GateError` and `pytest` are already imported in `test_gate.py`.)

- [ ] **Step 2: Run it to verify it fails**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_gate.py -k draft_text -v`
Expected: FAIL with `ImportError: cannot import name 'draft_text'`.

- [ ] **Step 3: Extract `draft_text` from `cited_ids`**

In `ai_rfc/draft/gate.py`, replace the body of `cited_ids` so that the listing and the `git show` live in a new public function. The current `cited_ids` (find it with `grep -n "def cited_ids"`) does `ls-tree`, requires exactly one `draft-*.md`, then `git show`; keep its signature and return type unchanged (`experiment/summary.py` imports it):

```python
def draft_text(draft_repo: Path, ref: str) -> tuple[str, str]:
    """Return the name and text of the single draft file at ``ref``.

    Args:
        draft_repo: The nested prose-draft git repository.
        ref: A tag, branch or commit to read.

    Returns:
        ``(file name, text)``.

    Raises:
        GateError: If the tree cannot be listed, holds zero or several
            ``draft-*.md`` files, or the file cannot be shown.
    """
    listed = _git(draft_repo, "ls-tree", "--name-only", ref)
    if listed.returncode != 0:
        raise GateError(f"{ref}: could not list its tree: {listed.stderr.strip()}")
    drafts = [
        name
        for name in listed.stdout.splitlines()
        if name.startswith("draft-") and name.endswith(".md")
    ]
    if len(drafts) != 1:
        raise GateError(
            f"{ref}: expected exactly one draft-*.md at the ref, found {len(drafts)}"
        )
    shown = _git(draft_repo, "show", f"{ref}:{drafts[0]}")
    if shown.returncode != 0:
        raise GateError(f"{ref}: could not read {drafts[0]}: {shown.stderr.strip()}")
    return drafts[0], shown.stdout


def cited_ids(draft_repo: Path, tag: str) -> tuple[set[str], str | None]:
    """Return the claim ids cited at ``tag``, or a finding when unreadable."""
    try:
        _, text = draft_text(draft_repo, tag)
    except GateError as error:
        return set(), str(error)
    return set(CITATION.findall(text)), None
```

Keep the original docstring of `cited_ids` (Args/Returns) — only the body changes. The finding strings are byte-identical to today's, so no gate test moves.

- [ ] **Step 4: Run the gate tests**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_gate.py -v`
Expected: all PASS, including the two new tests.

- [ ] **Step 5: Write the failing build tests**

Create `tests/substrate/draft/test_build.py`:

```python
"""``draft build``: the template's make, offline, in a scratch clone."""

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from ai_rfc.draft import build as build_module
from ai_rfc.draft.build import (
    BuildError,
    build,
    load_toolchain,
    probe_toolchain,
)
from ai_rfc.draft.cli import main

from .conftest import git

DATE = "2026-01-01T00:00:09+00:00"


def _executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture
def toolchain(tmp_path: Path) -> Path:
    """A toolchain record whose executables exist and do nothing."""
    home = tmp_path / "tools" / "i-d-template"
    (home / "main.mk").parent.mkdir(parents=True)
    (home / "main.mk").write_text("txt:\n")
    refcache = tmp_path / "tools" / ".refcache"
    refcache.mkdir()
    (refcache / "reference.RFC.2119.xml").write_text("<reference/>\n")
    record = {
        "template_home": str(home),
        "template_commit": "0" * 40,
        "make": {"path": str(_executable(tmp_path / "bin" / "make"))},
        "python": {"venv": str(home / ".venv")},
        "ruby": {
            "bin_dir": str(tmp_path / "ruby-bin"),
            "gem_path": str(home / ".gems" / "ruby" / "4.0.0"),
            "kramdown_rfc": str(
                _executable(home / ".gems" / "ruby" / "4.0.0" / "bin" / "kramdown-rfc")
            ),
        },
        "node": {
            "bin_dir": str(tmp_path / "node-bin"),
            "idnits": str(_executable(tmp_path / "tools" / "node_modules" / ".bin" / "idnits")),
        },
        "refcache": {"dir": str(refcache)},
    }
    path = tmp_path / "tools" / "toolchain.json"
    path.write_text(json.dumps(record, indent=2))
    return path


@pytest.fixture
def draft_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "draft"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "draft-test-spec.md").write_text("---\ntitle: T\n---\n\n# Intro\n")
    git(repo, "add", "draft-test-spec.md")
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "revision 00"],
        check=True,
        env={**os.environ, "GIT_AUTHOR_DATE": DATE, "GIT_COMMITTER_DATE": DATE},
    )
    git(repo, "tag", "draft-test-spec-00")
    return repo


def _fake_make(*, returncode=0, trace=(), stderr="", outputs=("draft-test-spec.txt",)):
    """A runner standing in for make: writes the trace and the outputs."""
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        scratch = Path(argv[argv.index("-C") + 1])
        trace_path = Path(next(a for a in argv if a.startswith("TRACE_FILE=")).split("=", 1)[1])
        trace_path.write_text("".join(line + "\n" for line in trace))
        for name in outputs:
            (scratch / name).write_text(f"built {name}\n")
        return subprocess.CompletedProcess(argv, returncode, stdout="", stderr=stderr)

    runner.calls = calls
    return runner


def test_load_toolchain_names_the_missing_key(tmp_path):
    path = tmp_path / "toolchain.json"
    path.write_text(json.dumps({"template_home": "/x"}))
    with pytest.raises(BuildError) as excinfo:
        load_toolchain(path)
    assert "'make'" in str(excinfo.value)


def test_probe_names_missing_executables(toolchain):
    record = load_toolchain(toolchain)
    assert probe_toolchain(record) == ()
    Path(record.idnits).unlink()
    assert probe_toolchain(record) == (f"idnits: {record.idnits}",)


def test_build_runs_make_offline_in_a_scratch_clone(toolchain, draft_repo, tmp_path):
    record = load_toolchain(toolchain)
    runner = _fake_make(trace=("draft-test-spec kramdown-rfc 0", "draft-test-spec xml2rfc-txt 0"))
    out = tmp_path / "out"
    report = build(draft_repo, toolchain=record, out=out, runner=runner)

    argv, kwargs = runner.calls[0]
    scratch = out / "build" / "scratch"
    assert argv[:3] == [record.make, "-C", str(scratch)]
    assert argv[3:5] == ["-f", str(record.template_home / "main.mk")]
    assert f"LIBDIR={record.template_home}" in argv
    assert f"kramdown-rfc={record.kramdown_rfc}" in argv
    assert f"GEM_PATH={record.gem_path}" in argv and f"GEM_HOME={record.gem_path}" in argv
    assert "KRAMDOWN_OFFLINE=1" in argv and "NO_NODEJS=true" in argv
    assert f"idnits={record.idnits}" in argv and "idnits_bin=" in argv
    opts = next(a for a in argv if a.startswith("XML2RFC_OPTS="))
    assert f"-N --cache={record.refcache} -D 2026-01-01" in opts
    assert argv[-4:] == ["txt", "html", "lint", "idnits"]
    env = kwargs["env"]
    assert env["PATH"].startswith(f"{record.bin_dirs[0]}:")
    assert env["http_proxy"] == "http://127.0.0.1:9" and env["KRAMDOWN_OFFLINE"] == "1"
    assert env["KRAMDOWN_REFCACHEDIR"] == str(record.refcache)

    assert git(scratch, "rev-parse", "HEAD").strip() == git(draft_repo, "rev-parse", "HEAD").strip()
    assert git(draft_repo, "status", "--porcelain") == ""
    assert report.exit_code == 0 and report.findings == ()
    assert [s["stage"] for s in report.stages] == ["kramdown-rfc", "xml2rfc-txt"]
    assert report.outputs["draft-test-spec.txt"]["sha256"] == hashlib.sha256(
        b"built draft-test-spec.txt\n"
    ).hexdigest()
    assert (out / "build" / "draft-test-spec.txt").read_text() == "built draft-test-spec.txt\n"
    expected_source = hashlib.sha256((draft_repo / "draft-test-spec.md").read_bytes()).hexdigest()
    assert report.source_sha256 == expected_source and report.date == "2026-01-01"
    written = json.loads((out / "build" / "build-report.json").read_text())
    assert written["exit_code"] == 0 and written["offline"] is True


def test_a_broken_reference_is_a_finding_even_when_make_exits_zero(toolchain, draft_repo, tmp_path):
    record = load_toolchain(toolchain)
    runner = _fake_make(
        trace=("draft-test-spec kramdown-rfc 0",),
        stderr="*** KRAMDOWN_OFFLINE: Inserting broken reference for RFC9999\n",
    )
    report = build(draft_repo, toolchain=record, out=tmp_path / "out", runner=runner)
    assert report.broken_references == ("RFC9999",)
    assert report.findings == ("broken reference RFC9999 (not in the refcache)",)


def test_a_failed_stage_is_named_with_its_stderr(toolchain, draft_repo, tmp_path):
    record = load_toolchain(toolchain)
    runner = _fake_make(
        returncode=2,
        trace=(
            "draft-test-spec kramdown-rfc 1",
            "draft-test-spec kramdown-rfc Error: bad front matter",
        ),
        outputs=(),
    )
    report = build(draft_repo, toolchain=record, out=tmp_path / "out", runner=runner)
    assert report.exit_code == 2
    assert report.stages[0]["status"] == 1
    assert report.stages[0]["stderr"] == ["Error: bad front matter"]
    assert report.findings == ("draft-test-spec: stage kramdown-rfc failed (Error: bad front matter)",)


def test_build_refuses_an_unknown_ref(toolchain, draft_repo, tmp_path):
    with pytest.raises(BuildError) as excinfo:
        build(draft_repo, toolchain=load_toolchain(toolchain), out=tmp_path / "out", ref="nope", runner=_fake_make())
    assert "nope" in str(excinfo.value)


def test_cli_build_exits_three_only_under_strict(toolchain, draft_repo, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        build_module,
        "DEFAULT_RUNNER",
        _fake_make(stderr="*** KRAMDOWN_OFFLINE: Inserting broken reference for RFC9999\n"),
    )
    argv = ["build", str(draft_repo), "--out", str(tmp_path / "out"), "--toolchain", str(toolchain)]
    assert main(argv) == 0
    assert "broken reference RFC9999" in capsys.readouterr().err
    assert main(argv + ["--strict"]) == 3


def test_cli_build_without_a_toolchain_exits_one(draft_repo, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("AI_RFC_TOOLCHAIN", raising=False)
    assert main(["build", str(draft_repo), "--out", str(tmp_path / "out")]) == 1
    assert "AI_RFC_TOOLCHAIN" in capsys.readouterr().err


@pytest.mark.skipif(
    not os.environ.get("AI_RFC_TOOLCHAIN"), reason="needs a provisioned toolchain"
)
def test_the_template_example_builds_with_the_real_toolchain(tmp_path):
    record = load_toolchain(Path(os.environ["AI_RFC_TOOLCHAIN"]))
    repo = tmp_path / "example"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    example = record.template_home / "example" / "draft-todo-yourname-protocol.md"
    (repo / example.name).write_text(example.read_text())
    (repo / "Makefile").write_text((record.template_home / "template" / "Makefile").read_text())
    git(repo, "add", example.name, "Makefile")
    git(repo, "commit", "-q", "-m", "example")
    report = build(repo, toolchain=record, out=tmp_path / "out", targets=("txt", "html"))
    assert report.exit_code == 0 and report.findings == ()
    assert "draft-todo-yourname-protocol.txt" in report.outputs
```

- [ ] **Step 6: Run the build tests to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_build.py -v`
Expected: every test FAILS at import (`ModuleNotFoundError: No module named 'ai_rfc.draft.build'`); the skipif test is SKIPPED unless `AI_RFC_TOOLCHAIN` is exported.

- [ ] **Step 7: Write `ai_rfc/draft/build.py`**

```python
"""Build one draft revision with the Internet-Draft template's own toolchain.

The template (auto-i-d-template, a fork of martinthomson/i-d-template) is the
build: ``make`` renders kramdown-rfc markdown to XML, then xml2rfc to text and
HTML, lints whitespace and the docname, and runs idnits. Nothing here
reimplements any of that; this module clones the draft at a ref into a scratch
directory, runs ``make`` there with the network denied, and turns the
template's trace file into a report.

Offline is a property of the invocation, not of the tools: ``KRAMDOWN_OFFLINE``
makes kramdown-rfc read only its reference cache (and insert a *stub* for a
missing reference, which this module promotes to an error), ``xml2rfc -N``
refuses network fetches outright, and a black-hole proxy catches anything
else. A build therefore reproduces byte-for-byte from the same cache and the
same ``-D`` date.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .gate import GateError, draft_text

Runner = Callable[..., "subprocess.CompletedProcess[str]"]

TOOLCHAIN_ENV = "AI_RFC_TOOLCHAIN"
BUILD_DIR = "build"
SCRATCH_DIR = "scratch"
REPORT_FILE = "build-report.json"
TRACE_FILE = "trace.txt"
DEFAULT_TARGETS: tuple[str, ...] = ("txt", "html", "lint", "idnits")
BLACKHOLE_PROXY = "http://127.0.0.1:9"
XML2RFC_BASE_OPTS = (
    "-q --rfc-base-url https://www.rfc-editor.org/rfc/ "
    "--id-base-url https://datatracker.ietf.org/doc/html/ "
    "--allow-local-file-access -N"
)
OUTPUT_SUFFIXES = (".txt", ".html")

_OFFLINE_STUB = re.compile(r"KRAMDOWN_OFFLINE: Inserting broken reference for (\S+)")
_XML2RFC_UNRESOLVED = re.compile(r"Unable to resolve external request: (\S+)")
_KRAMDOWN_WARNING = re.compile(r"^\*\* \((.*)\)\s*$")
_IDNITS_SUMMARY = re.compile(r"^\s*(ERROR|WARNING|COMMENT)\s+(\d+) nit")
#: The template's ``trace.sh`` writes ``<draft> <stage> <status>`` per stage and,
#: on failure, ``<draft> <stage> <stderr line>`` for the last stderr lines.
_TRACE_STATUS = re.compile(r"^(\S+) (\S+) (\d+)$")

DEFAULT_RUNNER: Runner = subprocess.run


class BuildError(RuntimeError):
    """Raised when the build cannot even start: no toolchain, no such ref."""


@dataclass(frozen=True)
class Toolchain:
    """The executables and directories a build needs, read from ``toolchain.json``."""

    path: Path
    template_home: Path
    template_commit: str
    refcache: Path
    make: str
    kramdown_rfc: str
    gem_path: str
    idnits: str
    #: Prepended to PATH, in order: the Ruby, Node and template-venv bin dirs.
    bin_dirs: tuple[str, ...]


def load_toolchain(path: Path) -> Toolchain:
    """Read a toolchain record.

    Args:
        path: The ``toolchain.json`` written by ``experiment toolchain provision``.

    Returns:
        The toolchain.

    Raises:
        BuildError: If the file is unreadable or lacks a required key.
    """
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise BuildError(f"{path}: unreadable toolchain record: {error}") from None
    try:
        return Toolchain(
            path=path,
            template_home=Path(record["template_home"]),
            template_commit=str(record.get("template_commit", "")),
            refcache=Path(record["refcache"]["dir"]),
            make=record["make"]["path"],
            kramdown_rfc=record["ruby"]["kramdown_rfc"],
            gem_path=record["ruby"]["gem_path"],
            idnits=record["node"]["idnits"],
            bin_dirs=(
                record["ruby"]["bin_dir"],
                record["node"]["bin_dir"],
                str(Path(record["python"]["venv"]) / "bin"),
            ),
        )
    except (KeyError, TypeError) as error:
        raise BuildError(f"{path}: toolchain record lacks {error}") from None


def probe_toolchain(toolchain: Toolchain) -> tuple[str, ...]:
    """Name every executable or directory the record points at that is missing.

    Args:
        toolchain: The record to probe.

    Returns:
        ``"<label>: <path>"`` per missing item; empty when everything exists.
    """
    missing: list[str] = []
    for label, candidate in (
        ("make", toolchain.make),
        ("kramdown-rfc", toolchain.kramdown_rfc),
        ("idnits", toolchain.idnits),
    ):
        if not (Path(candidate).is_file() and os.access(candidate, os.X_OK)):
            missing.append(f"{label}: {candidate}")
    for label, path in (
        ("template_home", toolchain.template_home / "main.mk"),
        ("refcache", toolchain.refcache),
    ):
        if not path.exists():
            missing.append(f"{label}: {path}")
    return tuple(missing)


@dataclass(frozen=True)
class BuildReport:
    """What one build did and what it found."""

    ref: str
    commit: str
    draft: str
    source_sha256: str
    date: str
    targets: tuple[str, ...]
    exit_code: int
    argv: tuple[str, ...]
    template: dict[str, str]
    refcache: str
    stages: tuple[dict[str, Any], ...]
    diagnostics: tuple[dict[str, str], ...]
    broken_references: tuple[str, ...]
    idnits: dict[str, int]
    outputs: dict[str, dict[str, str]]
    offline: bool = True

    @property
    def findings(self) -> tuple[str, ...]:
        """Every reason this revision does not compile cleanly."""
        found: list[str] = []
        for stage in self.stages:
            if stage["status"] != 0:
                detail = "; ".join(stage["stderr"][-3:]) or f"exit {stage['status']}"
                found.append(f"{stage['draft']}: stage {stage['stage']} failed ({detail})")
        if self.exit_code != 0 and not found:
            found.append(f"make exited {self.exit_code} without a failed stage in the trace")
        for reference in self.broken_references:
            found.append(f"broken reference {reference} (not in the refcache)")
        if self.idnits.get("ERROR", 0):
            found.append(f"idnits reported {self.idnits['ERROR']} error(s)")
        return tuple(found)

    def to_json(self) -> str:
        """Serialise deterministically, derived ``findings`` included."""
        payload = asdict(self)
        payload["findings"] = list(self.findings)
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git inside ``repo`` without raising; callers read the exit code."""
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )


def _parse_trace(path: Path) -> tuple[dict[str, Any], ...]:
    stages: dict[tuple[str, str], dict[str, Any]] = {}
    if not path.exists():
        return ()
    for line in path.read_text().splitlines():
        match = _TRACE_STATUS.match(line)
        if match:
            draft, stage, status = match.groups()
            stages[(draft, stage)] = {
                "draft": draft,
                "stage": stage,
                "status": int(status),
                "stderr": [],
            }
            continue
        draft, _, rest = line.partition(" ")
        stage, _, text = rest.partition(" ")
        if (draft, stage) in stages:
            stages[(draft, stage)]["stderr"].append(text)
    return tuple(stages.values())


def _parse_output(text: str) -> tuple[tuple[dict[str, str], ...], tuple[str, ...], dict[str, int]]:
    diagnostics: list[dict[str, str]] = []
    broken: list[str] = []
    idnits: dict[str, int] = {}
    for line in text.splitlines():
        stub = _OFFLINE_STUB.search(line)
        if stub:
            broken.append(stub.group(1))
            diagnostics.append({"tool": "kramdown-rfc", "severity": "error", "message": line.strip()})
            continue
        unresolved = _XML2RFC_UNRESOLVED.search(line)
        if unresolved:
            broken.append(unresolved.group(1))
            diagnostics.append({"tool": "xml2rfc", "severity": "error", "message": line.strip()})
            continue
        warning = _KRAMDOWN_WARNING.match(line)
        if warning:
            diagnostics.append({"tool": "kramdown-rfc", "severity": "warning", "message": warning.group(1)})
            continue
        summary = _IDNITS_SUMMARY.match(line)
        if summary:
            idnits[summary.group(1)] = int(summary.group(2))
    return tuple(diagnostics), tuple(dict.fromkeys(broken)), idnits


def build(
    draft_repo: Path,
    *,
    toolchain: Toolchain,
    out: Path,
    ref: str = "HEAD",
    targets: tuple[str, ...] = DEFAULT_TARGETS,
    date: str | None = None,
    refcache: Path | None = None,
    runner: Runner | None = None,
) -> BuildReport:
    """Build the draft as it stands at ``ref`` and write ``build-report.json``.

    Args:
        draft_repo: The nested prose-draft git repository.
        toolchain: Where the template and its tools are.
        out: Directory that receives ``build/`` (scratch clone, trace, report,
            rendered outputs).
        ref: Tag, branch or commit to build; the working tree is never built.
        targets: The make targets, in order.
        date: ``YYYY-MM-DD`` for xml2rfc ``-D``; defaults to the commit date of
            ``ref`` so a rebuild reproduces the same bytes.
        refcache: A reference cache overriding the toolchain's (a workspace's
            sealed ``refcache/``).
        runner: A ``subprocess.run`` stand-in; tests inject a fake make.

    Returns:
        The report, also written to ``out/build/build-report.json``.

    Raises:
        BuildError: If ``ref`` does not resolve or names no single draft file.
    """
    run = runner or DEFAULT_RUNNER
    resolved = _git(draft_repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        raise BuildError(f"{ref}: not a commit in {draft_repo}: {resolved.stderr.strip()}")
    commit = resolved.stdout.strip()
    try:
        draft, text = draft_text(draft_repo, commit)
    except GateError as error:
        raise BuildError(str(error)) from None
    built_date = date or _git(draft_repo, "log", "-1", "--format=%cs", commit).stdout.strip()
    cache = refcache or toolchain.refcache

    build_dir = out / BUILD_DIR
    scratch = build_dir / SCRATCH_DIR
    if scratch.exists():
        shutil.rmtree(scratch)
    build_dir.mkdir(parents=True, exist_ok=True)
    cloned = _git(draft_repo.parent, "clone", "-q", "--no-hardlinks", str(draft_repo), str(scratch))
    if cloned.returncode != 0:
        raise BuildError(f"could not clone {draft_repo}: {cloned.stderr.strip()}")
    checked = _git(scratch, "checkout", "-q", "--detach", commit)
    if checked.returncode != 0:
        raise BuildError(f"could not check out {commit}: {checked.stderr.strip()}")
    trace = build_dir / TRACE_FILE
    if trace.exists():
        trace.unlink()

    argv = [
        toolchain.make,
        "-C",
        str(scratch),
        "-f",
        str(toolchain.template_home / "main.mk"),
        f"LIBDIR={toolchain.template_home}",
        f"GEM_PATH={toolchain.gem_path}",
        f"GEM_HOME={toolchain.gem_path}",
        f"kramdown-rfc={toolchain.kramdown_rfc}",
        "DEFAULT_BRANCH=main",
        "BRANCH_FETCH=false",
        "NO_NODEJS=true",
        f"KRAMDOWN_REFCACHEDIR={cache}",
        "KRAMDOWN_OFFLINE=1",
        f"XML2RFC_OPTS={XML2RFC_BASE_OPTS} --cache={cache} -D {built_date}",
        f"idnits={toolchain.idnits}",
        "idnits_bin=",
        f"TRACE_FILE={trace}",
        *targets,
    ]
    env = {
        "PATH": ":".join((*toolchain.bin_dirs, "/usr/bin", "/bin")),
        "HOME": os.environ.get("HOME", str(build_dir)),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "KRAMDOWN_OFFLINE": "1",
        "KRAMDOWN_REFCACHEDIR": str(cache),
        "XML2RFC_REFCACHEDIR": str(cache),
        "http_proxy": BLACKHOLE_PROXY,
        "https_proxy": BLACKHOLE_PROXY,
        "HTTP_PROXY": BLACKHOLE_PROXY,
        "HTTPS_PROXY": BLACKHOLE_PROXY,
    }
    result = run(argv, capture_output=True, text=True, env=env, cwd=str(scratch))
    diagnostics, broken, idnits = _parse_output(
        (result.stdout or "") + "\n" + (result.stderr or "")
    )

    outputs: dict[str, dict[str, str]] = {}
    for produced in sorted(scratch.iterdir()):
        if produced.suffix in OUTPUT_SUFFIXES and produced.name.startswith("draft-"):
            copied = build_dir / produced.name
            shutil.copyfile(produced, copied)
            outputs[produced.name] = {
                "path": str(copied),
                "sha256": hashlib.sha256(copied.read_bytes()).hexdigest(),
            }

    report = BuildReport(
        ref=ref,
        commit=commit,
        draft=draft,
        source_sha256=hashlib.sha256(text.encode()).hexdigest(),
        date=built_date,
        targets=tuple(targets),
        exit_code=result.returncode,
        argv=tuple(argv),
        template={
            "path": str(toolchain.template_home),
            "commit": toolchain.template_commit,
        },
        refcache=str(cache),
        stages=_parse_trace(trace),
        diagnostics=diagnostics,
        broken_references=broken,
        idnits=idnits,
        outputs=outputs,
    )
    (build_dir / REPORT_FILE).write_text(report.to_json())
    return report
```

Note on `source_sha256`: `draft_text` returns the file's text as `git show` printed it, so the digest is of the committed bytes (the test computes it from the working-tree file, which is identical right after the commit). Note on `_git(draft_repo.parent, "clone", …)`: the clone runs with `-C` on the parent only so that git does not treat the scratch path as inside the source repository.

- [ ] **Step 8: Add the `build` verb to `ai_rfc/draft/cli.py`**

Below the `completeness` parser in `_parser()`:

```python
    build_verb = verbs.add_parser(
        "build",
        help="Compile a draft revision with the template toolchain, offline.",
    )
    build_verb.add_argument("draftrepo", type=Path, help="The nested draft repository.")
    build_verb.add_argument(
        "--out", type=Path, required=True, help="Directory receiving build/."
    )
    build_verb.add_argument(
        "--ref", default="HEAD", help="Tag, branch or commit to build (default: HEAD)."
    )
    build_verb.add_argument(
        "--toolchain",
        type=Path,
        default=None,
        help=f"toolchain.json (default: ${TOOLCHAIN_ENV}).",
    )
    build_verb.add_argument(
        "--refcache",
        type=Path,
        default=None,
        help="Reference cache overriding the toolchain's (a sealed workspace cache).",
    )
    build_verb.add_argument(
        "--targets",
        default=",".join(DEFAULT_TARGETS),
        help="Comma-separated make targets (default: %(default)s).",
    )
    build_verb.add_argument(
        "--date", default=None, help="xml2rfc -D date; default: the ref's commit date."
    )
    build_verb.add_argument(
        "--strict", action="store_true", help="Exit 3 when the build has findings."
    )
```

In `main()`, before the `completeness` branch's final `return`, add the dispatch:

```python
    if args.verb == "build":
        toolchain_path = args.toolchain or (
            Path(os.environ[TOOLCHAIN_ENV]) if os.environ.get(TOOLCHAIN_ENV) else None
        )
        if toolchain_path is None:
            _report(
                f"error: no toolchain; pass --toolchain or set {TOOLCHAIN_ENV} "
                "(experiment toolchain provision writes it)"
            )
            return 1
        try:
            toolchain = load_toolchain(toolchain_path)
            missing = probe_toolchain(toolchain)
            if missing:
                raise BuildError("toolchain incomplete: " + "; ".join(missing))
            report = build(
                args.draftrepo,
                toolchain=toolchain,
                out=args.out,
                ref=args.ref,
                targets=tuple(t for t in args.targets.split(",") if t),
                date=args.date,
                refcache=args.refcache,
            )
        except (BuildError, OSError) as error:
            _report(f"error: {error}")
            return 1
        for finding in report.findings:
            _report(f"finding: {finding}")
        _report(
            f"note: build of {report.commit[:12]} exited {report.exit_code}; "
            f"report at {args.out / BUILD_DIR / REPORT_FILE}"
        )
        if report.findings and args.strict:
            return 3
        return 0
```

Add `import os` and `from .build import (BUILD_DIR, DEFAULT_TARGETS, REPORT_FILE, TOOLCHAIN_ENV, BuildError, build, load_toolchain, probe_toolchain)` to the imports, and extend the `main()` docstring's exit-code sentence with `build --strict`.

- [ ] **Step 9: Run the build tests**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft -v`
Expected: all PASS (the real-toolchain test SKIPPED unless `AI_RFC_TOOLCHAIN` is exported). Then run it once for real: `AI_RFC_TOOLCHAIN=$HOME/ai-rfc-experiments/tools/toolchain.json SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_build.py -k real_toolchain -v` — Expected: PASS (this proves the argv/env recipe against the actual template).

- [ ] **Step 10: README rows, lint, commit**

In `ai_rfc/README.md`: add a verb-table row `| ai-rfc draft build DRAFTREPO --out DIR [--ref REF] [--toolchain PATH] [--strict] | Compile a revision with the template toolchain, offline; findings exit 3 under --strict |` beside the other `draft` rows, and add `draft/build.py` to the `_git` row of the duplication table (the README's own rule: "Adding a subpackage means adding its copies here" — the count becomes six). Then:

```bash
cd $AIRFC && $PY -m black ai_rfc/draft tests/substrate/draft && $PY -m flake8 --max-line-length=88 ai_rfc/draft tests/substrate/draft && $PY -m mypy --follow-imports=silent ai_rfc/draft/build.py
git status --short   # only your files may be listed
git add ai_rfc/draft/build.py ai_rfc/draft/cli.py ai_rfc/draft/gate.py ai_rfc/README.md tests/substrate/draft/test_build.py tests/substrate/draft/test_gate.py
git commit -m "feat: compile a draft revision with the template toolchain, offline"
```

---

### Task 2: `ai-rfc draft lint` — deterministic quality metrics over one revision

**Files:**
- Create: `ai_rfc/draft/lint.py`
- Modify: `ai_rfc/draft/cli.py` (verb `lint`), `ai_rfc/README.md` (verb row)
- Test: `tests/substrate/draft/test_lint.py` (new)

**Interfaces:**
- Consumes: `draft_text` (Task 1), `ai_rfc.draft.gate.CITATION`, `ai_rfc.schema.load`, `ai_rfc.models.Manifest`.
- Produces: `lint(text: str, *, manifest: Manifest | None = None, manifest_error: str | None = None, source: dict[str, str] | None = None) -> LintReport`; `LintReport.findings: tuple[str, ...]`, `LintReport.to_json()`; constants `REPORT_FILE = "lint-report.json"`, `REQUIRED_SECTIONS`, `STUB_ABSTRACT_MARKER`, `BCP14_TERMS`, `MUST_FRACTION_CEILING = 0.8`, `FIGURE_CITATION_WINDOW = 3`, `NARRATION_PATTERNS`; CLI verb `ai-rfc draft lint DRAFTREPO --out DIR [--ref REF | --worktree] [--manifest PATH] [--strict]`. Task 4 wraps the verb; SP7b adds the `structures` keys to the same report; SP7d reads `lint-report.json` into the analysis.

**Why this shape.** Every metric is a pure function of the draft text (plus the manifest for citation coverage), so the same numbers come out on any machine and any day. The report carries the numbers and the findings separately: the numbers are what the instrument aggregates, the findings are what an agent fixes. The legacy `a_rfc:` token is counted (the six pilot drafts use it) but never accepted as a citation of a known claim — the gate is the authority on tokens; the lint only measures.

- [ ] **Step 1: Write the failing lint tests**

Create `tests/substrate/draft/test_lint.py`:

```python
"""``draft lint``: metrics and findings over one draft text."""

import json
from pathlib import Path

import pytest

from ai_rfc.draft.cli import main
from ai_rfc.draft.lint import (
    MUST_FRACTION_CEILING,
    STUB_ABSTRACT_MARKER,
    lint,
)
from ai_rfc.schema import load

from .conftest import _manifest_text, git

# No bare `---` closer: the skeleton and every draft this tool produces close
# their front matter with `--- abstract`. A fixture that adds one would exercise
# a path no real draft takes and hide a broken `_parts`.
FRONT = (
    "---\n"
    'title: "T"\n'
    "docname: draft-test-spec-latest\n"
    "{refs}"
)
STUB = "This document reconstructs the specification of t from its\nimplementation history. " + STUB_ABSTRACT_MARKER + ".\n"
WRITTEN = "T is a server that stores things and answers queries about them.\n"
MIDDLE = (
    "--- middle\n\n# Introduction\n\n{intro}\n\n# Conventions\n\n{{::boilerplate bcp14-tagged}}\n\n"
    "# Operation\n\n{body}\n\n# Security Considerations\n\nNone known.\n\n# IANA Considerations\n\nNone.\n"
)


def _draft(*, abstract=WRITTEN, intro="T stores things.", body="", refs="normative:\n  RFC9000:\n", back="--- back\n"):
    return (
        FRONT.format(refs=refs)
        + "\n--- abstract\n\n"
        + abstract
        + "\n"
        + MIDDLE.format(intro=intro, body=body)
        + "\n"
        + back
    )


def test_a_skeleton_abstract_is_a_finding():
    report = lint(_draft(abstract=STUB))
    assert report.abstract["is_stub"] is True
    assert "abstract: still the skeleton stub" in report.findings
    assert lint(_draft()).abstract["is_stub"] is False


def test_required_sections_are_checked_by_level_one_heading():
    text = _draft().replace("# IANA Considerations\n\nNone.\n", "")
    report = lint(text)
    assert report.sections["missing"] == ["IANA Considerations"]
    assert "section missing: IANA Considerations" in report.findings
    assert lint(_draft()).sections["missing"] == []


def test_references_are_counted_from_the_front_matter():
    report = lint(_draft(refs="normative:\n  RFC9000:\ninformative:\n  MARK:\n    title: The paper\n    date: 2019\n"))
    assert report.references == {"normative": 1, "informative": 1, "inline": 1}
    empty = lint(_draft(refs="normative:\ninformative:\n"))
    assert empty.references == {"normative": 0, "informative": 0, "inline": 0}
    assert "references: none declared (normative and informative are both empty)" in empty.findings


def test_keywords_are_counted_outside_fences_and_the_boilerplate_line():
    body = (
        "The server MUST answer. It MUST NOT lie. Clients SHOULD retry and MAY log.\n\n"
        "~~~\nMUST inside artwork does not count\n~~~\n"
    )
    report = lint(_draft(body=body))
    assert report.keywords["histogram"] == {"MUST": 1, "MUST NOT": 1, "SHOULD": 1, "MAY": 1}
    assert report.keywords["total"] == 4 and report.keywords["must_fraction"] == 0.5


def test_a_must_monoculture_is_a_finding_only_over_twenty_keywords():
    body = " ".join(["It MUST run."] * 19)
    assert not any(f.startswith("keywords:") for f in lint(_draft(body=body)).findings)
    body = " ".join(["It MUST run."] * 21)
    report = lint(_draft(body=body))
    assert report.keywords["must_fraction"] == 1.0
    assert any(f.startswith(f"keywords: MUST fraction 1.00 exceeds {MUST_FRACTION_CEILING}") for f in report.findings)


def test_figures_need_a_citation_within_three_lines_of_the_closing_fence():
    cited = "~~~\n+---+\n| A |\n+---+\n~~~\n{: #fig-a title=\"A\"}\n\nA holds the thing. `ai_rfc:spec:1.1`\n"
    uncited = "~~~\n+---+\n| B |\n+---+\n~~~\n\nB is drawn above.\n\nMore prose.\n\nEven more.\n"
    report = lint(_draft(body=cited + "\n" + uncited))
    assert report.blocks["figures"] == 2
    assert len(report.blocks["figures_without_caption_citation"]) == 1
    line = report.blocks["figures_without_caption_citation"][0]["line"]
    assert any(f == f"figure at line {line}: no citation within 3 lines of its closing fence" for f in report.findings)


def test_tables_are_counted_by_their_rule_row():
    # `_TABLE_RULE` requires three or more dashes per cell, so an alignment row
    # must be written `|:---:|`, not `|:-:|`. The floor is deliberate: a shorter
    # run would also match a bare `---` thematic break.
    body = "| Field | Type |\n|---|---|\n| a | int |\n\n| X |\n|:---:|\n| 1 |\n"
    assert lint(_draft(body=body)).blocks["tables"] == 2


def test_citations_are_measured_against_the_manifest(tmp_path):
    manifest_path = tmp_path / "m.yaml"
    manifest_path.write_text(_manifest_text(with_second_claim=True))
    manifest = load(manifest_path)
    body = "It does the thing. `ai_rfc:spec:1.1` It is old. `a_rfc:spec:2.1` Unknown. `ai_rfc:spec:9.9`\n"
    report = lint(_draft(body=body), manifest=manifest)
    assert report.citations["tokens"] == 2 and report.citations["legacy_tokens"] == 1
    assert report.citations["cited_unknown"] == ["spec:9.9"]
    assert report.citations["uncited"] == ["spec:2.1"]
    assert report.citations["cited_fraction"] == 0.5
    assert "citation spec:9.9: not in the manifest" in report.findings


def test_narration_is_detected_in_the_introduction_only():
    intro = "The thirty-first cluster is a merge. Forty-five statements are added and four are withdrawn."
    body = "Clients form a cluster of peers.\n"
    report = lint(_draft(intro=intro, body=body))
    patterns = [entry["pattern"] for entry in report.narration]
    assert "ordinal cluster" in patterns and "added/withdrawn count" in patterns
    assert all(entry["line"] < 20 for entry in report.narration)
    assert any(f.startswith("introduction: narrates the reconstruction (") for f in report.findings)
    assert lint(_draft(body=body)).narration == []


def test_an_unloadable_manifest_is_a_finding_not_a_crash():
    report = lint(_draft(), manifest_error="level 'descriptive' is not one of MUST, ...")
    assert "manifest: unloadable (level 'descriptive' is not one of MUST, ...)" in report.findings


@pytest.fixture
def lint_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "draft"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "draft-test-spec.md").write_text(_draft(abstract=STUB))
    git(repo, "add", "draft-test-spec.md")
    git(repo, "commit", "-m", "revision 00")
    git(repo, "tag", "draft-test-spec-00")
    (repo / "draft-test-spec.md").write_text(_draft())
    return repo


def test_cli_lint_reads_a_ref_by_default_and_the_worktree_on_request(lint_repo, tmp_path, capsys):
    out = tmp_path / "out"
    assert main(["lint", str(lint_repo), "--out", str(out)]) == 0
    written = json.loads((out / "lint-report.json").read_text())
    assert written["abstract"]["is_stub"] is True and written["source"]["ref"] == "HEAD"
    assert "abstract: still the skeleton stub" in capsys.readouterr().err
    assert main(["lint", str(lint_repo), "--out", str(out), "--worktree"]) == 0
    written = json.loads((out / "lint-report.json").read_text())
    assert written["abstract"]["is_stub"] is False and written["source"]["ref"] == "worktree"


def test_cli_lint_strict_exits_three_and_the_report_is_byte_stable(lint_repo, tmp_path, capsys):
    out = tmp_path / "out"
    assert main(["lint", str(lint_repo), "--out", str(out), "--strict"]) == 3
    first = (out / "lint-report.json").read_bytes()
    main(["lint", str(lint_repo), "--out", str(out), "--strict"])
    assert (out / "lint-report.json").read_bytes() == first
    capsys.readouterr()
```

- [ ] **Step 2: Run the lint tests to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_lint.py -v`
Expected: FAIL at import (`No module named 'ai_rfc.draft.lint'`).

- [ ] **Step 3: Write `ai_rfc/draft/lint.py`**

```python
"""Deterministic quality metrics and findings over one draft revision.

Everything here is a pure function of the draft text (plus the manifest for
citation coverage): no model, no network, no clock. The report separates the
*numbers* — what an instrument aggregates across runs — from the *findings* —
what an author fixes before tagging. The gate decides what a citation is; the
lint only measures, so the legacy ``a_rfc:`` spelling is counted but never
credited against the manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

from ..models import Manifest
from .gate import CITATION

REPORT_FILE = "lint-report.json"
REQUIRED_SECTIONS: tuple[str, ...] = (
    "Introduction",
    "Security Considerations",
    "IANA Considerations",
)
#: The skeleton's abstract sentence; a draft still carrying it was never written.
STUB_ABSTRACT_MARKER = "Each revision reflects the implementation as it stood at one cluster"
BCP14_TERMS: tuple[str, ...] = (
    "MUST NOT",
    "SHALL NOT",
    "SHOULD NOT",
    "NOT RECOMMENDED",
    "MUST",
    "REQUIRED",
    "SHALL",
    "SHOULD",
    "RECOMMENDED",
    "MAY",
    "OPTIONAL",
)
MUST_FRACTION_CEILING = 0.8
MUST_FRACTION_FLOOR_COUNT = 20
FIGURE_CITATION_WINDOW = 3
LEGACY_CITATION = re.compile(r"`a_rfc:([^`\s]+)`")
_KEYWORD = re.compile(r"\b(" + "|".join(re.escape(t) for t in BCP14_TERMS) + r")\b")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE = re.compile(r"^(~~~+|```+)")
_TABLE_RULE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_ORDINAL = (
    r"(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|"
    r"eighteenth|nineteenth|twentieth|thirtieth|fortieth|fiftieth|sixtieth|"
    r"seventieth|eightieth|ninetieth|hundredth|[a-z]+-[a-z]+th|[a-z]+-(first|second|third))"
)
NARRATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ordinal cluster", re.compile(r"\b" + _ORDINAL + r"\b[^.]{0,40}\bcluster\b", re.I)),
    ("added/withdrawn count", re.compile(r"\b(statements?|claims?) (are|were|is|was) (added|withdrawn)\b", re.I)),
    ("cluster", re.compile(r"\bclusters?\b", re.I)),
    ("this revision", re.compile(r"\bthis revision\b", re.I)),
)


@dataclass(frozen=True)
class LintReport:
    """Numbers and findings for one draft text."""

    source: dict[str, str]
    sections: dict[str, list[str]]
    abstract: dict[str, Any]
    references: dict[str, int]
    keywords: dict[str, Any]
    blocks: dict[str, Any]
    citations: dict[str, Any]
    narration: list[dict[str, Any]]
    manifest_error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def findings(self) -> tuple[str, ...]:
        """What an author must fix, one line each."""
        found: list[str] = []
        if self.manifest_error:
            found.append(f"manifest: unloadable ({self.manifest_error})")
        if self.abstract["is_stub"]:
            found.append("abstract: still the skeleton stub")
        for name in self.sections["missing"]:
            found.append(f"section missing: {name}")
        if self.references["normative"] + self.references["informative"] == 0:
            found.append(
                "references: none declared (normative and informative are both empty)"
            )
        for figure in self.blocks["figures_without_caption_citation"]:
            found.append(
                f"figure at line {figure['line']}: no citation within "
                f"{FIGURE_CITATION_WINDOW} lines of its closing fence"
            )
        for claim_id in self.citations["cited_unknown"]:
            found.append(f"citation {claim_id}: not in the manifest")
        if self.narration:
            found.append(
                f"introduction: narrates the reconstruction ({len(self.narration)} "
                f"line(s), e.g. line {self.narration[0]['line']})"
            )
        total = self.keywords["total"]
        fraction = self.keywords["must_fraction"]
        if total >= MUST_FRACTION_FLOOR_COUNT and fraction > MUST_FRACTION_CEILING:
            found.append(
                f"keywords: MUST fraction {fraction:.2f} exceeds {MUST_FRACTION_CEILING} "
                f"over {total} keywords"
            )
        return tuple(found)

    def to_json(self) -> str:
        """Serialise deterministically, derived ``findings`` included."""
        payload = asdict(self)
        payload["findings"] = list(self.findings)
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"


_SECTION_MARKERS = ("--- abstract", "--- middle", "--- back")


def _parts(text: str) -> dict[str, str]:
    """Split kramdown-rfc source into front matter, abstract, middle and back."""
    parts = {"front": "", "abstract": "", "middle": "", "back": ""}
    lines = text.splitlines()
    front_end = 0
    body_start = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            marker = lines[index].strip()
            if marker == "---":
                front_end, body_start = index, index + 1
                break
            # kramdown-rfc also lets the first section marker close the front
            # matter, and that is what every draft this tool produces does: the
            # skeleton and the MARK draft both go straight from `---` to
            # `--- abstract`. Treating only a bare `---` as the terminator left
            # `front` empty and every reference count permanently zero.
            if marker in _SECTION_MARKERS:
                front_end, body_start = index, index
                break
        parts["front"] = "\n".join(lines[1:front_end]) + "\n"
    current = "preamble"
    buckets: dict[str, list[str]] = {"preamble": [], "abstract": [], "middle": [], "back": []}
    for line in lines[body_start:]:
        marker = line.strip()
        if marker in _SECTION_MARKERS:
            current = marker.split()[1]
            continue
        buckets[current].append(line)
    for name in ("abstract", "middle", "back"):
        parts[name] = "\n".join(buckets[name]) + "\n"
    return parts


def _sections(body: str) -> dict[str, list[str]]:
    present = [
        match.group(2)
        for match in (_HEADING.match(line) for line in body.splitlines())
        if match and len(match.group(1)) == 1
    ]
    return {
        "present": present,
        "missing": [name for name in REQUIRED_SECTIONS if name not in present],
    }


def _references(front: str) -> dict[str, int]:
    try:
        loaded = yaml.safe_load(front) or {}
    except yaml.YAMLError:
        return {"normative": 0, "informative": 0, "inline": 0}
    counts = {"normative": 0, "informative": 0, "inline": 0}
    for kind in ("normative", "informative"):
        entries = loaded.get(kind) if isinstance(loaded, dict) else None
        if not isinstance(entries, dict):
            continue
        counts[kind] = len(entries)
        counts["inline"] += sum(1 for value in entries.values() if isinstance(value, dict))
    return counts


def _prose_lines(body: str) -> list[tuple[int, str]]:
    """Body lines outside fences, comments and directives, with 1-based numbers."""
    kept: list[tuple[int, str]] = []
    fenced = False
    commented = False
    for number, line in enumerate(body.splitlines(), start=1):
        stripped = line.lstrip()
        if _FENCE.match(line):
            fenced = not fenced
            continue
        # kramdown-rfc drops comment blocks, so their bodies never reach the
        # built draft and must not be linted. Skipping only lines starting
        # `{::` left both the body and the `{:/comment}` closer in the prose.
        if stripped.startswith("{::comment}"):
            commented = True
            continue
        if stripped.startswith("{:/comment}"):
            commented = False
            continue
        if fenced or commented or stripped.startswith("{::"):
            continue
        kept.append((number, line))
    return kept


def _keywords(body: str) -> dict[str, Any]:
    histogram: dict[str, int] = {}
    for _, line in _prose_lines(body):
        for match in _KEYWORD.finditer(line):
            histogram[match.group(1)] = histogram.get(match.group(1), 0) + 1
    total = sum(histogram.values())
    must = histogram.get("MUST", 0) + histogram.get("MUST NOT", 0)
    return {
        "histogram": dict(sorted(histogram.items())),
        "total": total,
        "must_fraction": round(must / total, 4) if total else 0.0,
    }


def _blocks(body: str, offset: int) -> dict[str, Any]:
    lines = body.splitlines()
    figures = 0
    uncited: list[dict[str, Any]] = []
    tables = 0
    opened: int | None = None
    for index, line in enumerate(lines):
        if _FENCE.match(line):
            if opened is None:
                opened = index
                continue
            figures += 1
            following = [
                candidate
                for candidate in lines[index + 1 : index + 1 + FIGURE_CITATION_WINDOW + 1]
            ][: FIGURE_CITATION_WINDOW + 1]
            window = "\n".join(following)
            if not CITATION.search(window):
                uncited.append({"line": offset + opened + 1})
            opened = None
            continue
        if opened is None and index > 0 and _TABLE_RULE.match(line) and lines[index - 1].lstrip().startswith("|"):
            tables += 1
    return {
        "figures": figures,
        "tables": tables,
        "figures_without_caption_citation": uncited,
    }


def _citations(body: str, manifest: Manifest | None) -> dict[str, Any]:
    tokens = CITATION.findall(body)
    legacy = LEGACY_CITATION.findall(body)
    distinct = sorted(set(tokens))
    result: dict[str, Any] = {
        "tokens": len(tokens),
        "distinct": len(distinct),
        "legacy_tokens": len(legacy),
        "cited_unknown": [],
        "uncited": [],
        "cited_fraction": None,
    }
    if manifest is not None:
        known = {claim.id for claim in manifest.claims}
        cited = set(distinct)
        result["cited_unknown"] = sorted(cited - known)
        result["uncited"] = sorted(known - cited)
        result["cited_fraction"] = round(len(cited & known) / len(known), 4) if known else None
    return result


def _introduction(body: str) -> list[tuple[int, str]]:
    """The Introduction section's prose lines, with numbers relative to the body."""
    inside = False
    kept: list[tuple[int, str]] = []
    for number, line in _prose_lines(body):
        match = _HEADING.match(line)
        if match and len(match.group(1)) == 1:
            inside = match.group(2) == "Introduction"
            continue
        if inside:
            kept.append((number, line))
    return kept


def _narration(body: str, offset: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for number, line in _introduction(body):
        for name, pattern in NARRATION_PATTERNS:
            if pattern.search(line):
                entries.append({"line": offset + number, "pattern": name, "text": line.strip()})
                break
    return entries


def lint(
    text: str,
    *,
    manifest: Manifest | None = None,
    manifest_error: str | None = None,
    source: dict[str, str] | None = None,
) -> LintReport:
    """Measure one draft text.

    Args:
        text: The kramdown-rfc source of the draft file.
        manifest: The manifest to measure citation coverage against, if any.
        manifest_error: Why the manifest could not be loaded, when it could not;
            reported as a finding rather than raised, because the draft is
            still worth measuring.
        source: Provenance for the report (``path``, ``ref``); the text digest
            is added here.

    Returns:
        The report.
    """
    parts = _parts(text)
    middle_offset = text.count("\n", 0, text.index("--- middle") + 1) + 1 if "--- middle" in text else 0
    body = parts["middle"] + parts["back"]
    abstract_text = parts["abstract"].strip()
    provenance = dict(source or {})
    provenance["sha256"] = hashlib.sha256(text.encode()).hexdigest()
    return LintReport(
        source=provenance,
        sections=_sections(body),
        abstract={
            "is_stub": STUB_ABSTRACT_MARKER in abstract_text,
            "word_count": len(abstract_text.split()),
        },
        references=_references(parts["front"]),
        keywords=_keywords(parts["middle"]),
        blocks=_blocks(body, middle_offset),
        citations=_citations(body, manifest),
        narration=_narration(parts["middle"], middle_offset),
        manifest_error=manifest_error,
    )
```

(`middle_offset` turns body-relative line numbers into draft-file line numbers: the number of lines before and including the `--- middle` marker. The `extra` field is where SP7b adds its `structures` block without changing this dataclass's shape for existing readers.)

- [ ] **Step 4: Add the `lint` verb to `ai_rfc/draft/cli.py`**

Parser, below `build`:

```python
    lint_verb = verbs.add_parser("lint", help="Measure a draft revision's quality.")
    lint_verb.add_argument("draftrepo", type=Path, help="The nested draft repository.")
    lint_verb.add_argument(
        "--out", type=Path, required=True, help="Directory for lint-report.json."
    )
    which = lint_verb.add_mutually_exclusive_group()
    which.add_argument("--ref", default="HEAD", help="Tag, branch or commit to read.")
    which.add_argument(
        "--worktree",
        action="store_true",
        help="Read the uncommitted draft file instead of a ref.",
    )
    lint_verb.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Manifest for citation coverage (unloadable → a finding, not an error).",
    )
    lint_verb.add_argument(
        "--strict", action="store_true", help="Exit 3 when any finding is reported."
    )
```

Dispatch in `main()`:

```python
    if args.verb == "lint":
        try:
            if args.worktree:
                candidates = sorted(
                    p for p in args.draftrepo.iterdir() if p.name.startswith("draft-") and p.suffix == ".md"
                )
                if len(candidates) != 1:
                    raise GateError(
                        f"{args.draftrepo}: expected exactly one draft-*.md, found {len(candidates)}"
                    )
                text, ref = candidates[0].read_text(), "worktree"
            else:
                _, text = draft_text(args.draftrepo, args.ref)
                ref = args.ref
        except (GateError, OSError) as error:
            _report(f"error: {error}")
            return 1
        manifest = None
        manifest_error = None
        if args.manifest is not None:
            try:
                manifest = load(args.manifest)
            except (SchemaError, OSError) as error:
                manifest_error = str(error)
        report = lint(
            text,
            manifest=manifest,
            manifest_error=manifest_error,
            source={"path": str(args.draftrepo), "ref": ref},
        )
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / LINT_REPORT_FILE).write_text(report.to_json())
        for finding in report.findings:
            _report(f"finding: {finding}")
        _report(f"note: lint report at {args.out / LINT_REPORT_FILE}")
        if report.findings and args.strict:
            return 3
        return 0
```

Imports: `from ..schema import SchemaError, load`, `from .gate import GateError, draft_text, run_gate`, `from .lint import REPORT_FILE as LINT_REPORT_FILE, lint`.

- [ ] **Step 5: Run the lint tests**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/draft/test_lint.py -v`
Expected: all PASS. If `test_narration_is_detected_in_the_introduction_only` fails on the "thirty-first" ordinal, the hyphenated alternative in `_ORDINAL` is what matches it — check the regex was copied whole.

- [ ] **Step 6: Lint against the real MARK draft (no assertion, a number to record)**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m ai_rfc.draft lint ~/ai-rfc-experiments/campaigns/mark-full-1/runs/A1/workspace/draft --out /tmp/claude/mark-lint --manifest ~/ai-rfc-experiments/campaigns/mark-full-1/runs/A1/workspace/manifest.yaml`
Expected: exit 0; stderr lists findings including `abstract: still the skeleton stub`, `references: none declared…`, `introduction: narrates the reconstruction (…)` and `keywords: MUST fraction …`. Paste the `findings` list into the commit message body — it is the baseline the spec's Phase 7 compares against.

- [ ] **Step 7: README row, lint, commit**

Add `| ai-rfc draft lint DRAFTREPO --out DIR [--ref REF \| --worktree] [--manifest PATH] [--strict] | Deterministic quality metrics; findings exit 3 under --strict |` to the README verb table. Then:

```bash
cd $AIRFC && $PY -m black ai_rfc/draft tests/substrate/draft && $PY -m flake8 --max-line-length=88 ai_rfc/draft tests/substrate/draft && $PY -m mypy --follow-imports=silent ai_rfc/draft/lint.py
git status --short
git add ai_rfc/draft/lint.py ai_rfc/draft/cli.py ai_rfc/README.md tests/substrate/draft/test_lint.py
git commit -m "feat: measure a draft revision's quality deterministically"
```

---

### Task 3: Pipeline stages `lint` and `build`, with one optional-stage rule

**Files:**
- Modify: `ai_rfc/pipeline/stages.py` (two stages, `OPTIONAL`, `is_optional`), `ai_rfc/pipeline/state.py` (`_lint`, `_build`, `next_stage`), `ai_rfc/pipeline/run.py` (`_Request.toolchain`, `_lint`, `_build`, `DISPATCH`, `perform`), `ai_rfc/pipeline/cli.py` (`--toolchain`, the skip rule), `ai_rfc/pipeline/workspace.py` (a `draft` property if absent), `ai_rfc/pipeline/README.md`
- Test: `tests/substrate/pipeline/test_state.py`, `tests/substrate/pipeline/test_run.py`, `tests/substrate/pipeline/test_cli.py`

**Interfaces:**
- Consumes: `ai_rfc.draft.build.REPORT_FILE`/`BUILD_DIR` (Task 1), the `draft lint`/`draft build` verbs (Tasks 1–2), `ai_rfc.pipeline.stages.STAGES/BY_NAME`, `state.State` members `DONE`, `RECOMPUTED`, `BLOCKED`, `STALE`.
- Produces: `Stage(10, "lint")`, `Stage(11, "build")`; `OPTIONAL: dict[str, str] = {"forge": "--forge-url", "build": "--toolchain"}`; `is_optional(stage: Stage) -> bool`; `perform(..., toolchain: Path | None = None)`; `pipeline run --toolchain PATH` (default `$AI_RFC_TOOLCHAIN`).

**Why this shape.** Forge is skipped in two hardcoded places today (`next_stage` and the runner's loop) and the spec names that duplication as the risk of adding a third; one predicate answers both sites. `build` is the second optional stage: without a toolchain a workspace is still a complete reconstruction, only an unrendered one. **SP0 Task 2 rewrites `pipeline/cli.py` (`_perform_rederivable`) — re-anchor every edit in that file by symbol, and add `"lint"` to whatever tuple that task introduced for the re-derivable stages.**

- [ ] **Step 1: Write the failing tests**

Append to `tests/substrate/pipeline/test_run.py` (it already asserts `DISPATCH` covers exactly the deterministic stages — that assertion will fail until Step 3 and is part of the RED):

```python
def test_lint_and_build_requests_name_the_workspace_paths(tmp_path):
    from ai_rfc.pipeline.run import DISPATCH, _Request
    from ai_rfc.pipeline.workspace import Workspace

    ws = Workspace(tmp_path)
    argv, module = DISPATCH["lint"](_Request(ws, strict=True))
    assert argv == [str(ws.draft), "--out", str(ws.out), "--manifest", str(ws.manifest), "--strict"]
    assert module.__name__ == "ai_rfc.draft.cli"
    argv, module = DISPATCH["build"](_Request(ws, toolchain=tmp_path / "tc.json"))
    assert argv == [str(ws.draft), "--out", str(ws.out), "--toolchain", str(tmp_path / "tc.json")]
```

Append to `tests/substrate/pipeline/test_state.py` (use that module's existing workspace fixture — read its name at the top of the file; below it is called `prepared`, a workspace whose prose stage is DONE):

```python
def test_build_is_blocked_until_prose_then_stale_until_rebuilt(prepared):
    from ai_rfc.pipeline.state import State, state
    from ai_rfc.draft.build import BUILD_DIR, REPORT_FILE

    by_name = {entry.stage.name: entry for entry in state(prepared)}
    assert by_name["lint"].state is State.RECOMPUTED
    assert by_name["build"].state is State.BLOCKED
    report_dir = prepared.out / BUILD_DIR
    report_dir.mkdir(parents=True)
    (report_dir / REPORT_FILE).write_text(
        json.dumps({"commit": "0" * 40, "exit_code": 0, "findings": []})
    )
    by_name = {entry.stage.name: entry for entry in state(prepared)}
    assert by_name["build"].state is State.STALE


def test_optional_stages_are_stepped_over_by_next_stage(prepared):
    from ai_rfc.pipeline.stages import BY_NAME, is_optional
    from ai_rfc.pipeline.state import next_stage

    assert is_optional(BY_NAME["forge"]) and is_optional(BY_NAME["build"])
    assert not is_optional(BY_NAME["lint"])
    outstanding = next_stage(prepared)
    assert outstanding is None or outstanding.stage.name not in ("forge", "build")
```

Append to `tests/substrate/pipeline/test_cli.py` (mirror the existing forge-skip test's shape — find it with `grep -n "forge" tests/substrate/pipeline/test_cli.py`):

```python
def test_run_skips_build_without_a_toolchain_and_says_so(prepared, capsys, monkeypatch):
    from ai_rfc.pipeline.cli import main

    monkeypatch.delenv("AI_RFC_TOOLCHAIN", raising=False)
    assert main(["run", str(prepared.root), "--from", "lint", "--until", "build"]) == 0
    assert "skipping build; no --toolchain given" in capsys.readouterr().err


def test_run_asked_for_build_without_a_toolchain_is_an_error(prepared, capsys, monkeypatch):
    from ai_rfc.pipeline.cli import main

    monkeypatch.delenv("AI_RFC_TOOLCHAIN", raising=False)
    assert main(["run", str(prepared.root), "--from", "build"]) == 1
    assert "build was asked for but no --toolchain was given" in capsys.readouterr().err
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/pipeline -v`
Expected: the new tests FAIL (`KeyError: 'lint'`, `ImportError: is_optional`, choices error on `--from lint`), and the existing DISPATCH-coverage assertion still passes (nothing added yet). Everything else passes.

- [ ] **Step 3: Stages and the optional rule**

In `ai_rfc/pipeline/stages.py`, append after `Stage(9, "gate", …)` inside `STAGES`:

```python
    Stage(10, "lint", Performer.DETERMINISTIC),
    Stage(11, "build", Performer.DETERMINISTIC),
```

and after `BY_NAME`:

```python
#: Stages a workspace may lack without being broken, and the run flag that
#: enables each: a git-only timeline is a narrower reconstruction, and an
#: unrendered draft is still a reconstruction. ``next_stage`` steps over these
#: and the runner skips them when the flag is absent — one rule, two callers.
OPTIONAL: dict[str, str] = {"forge": "--forge-url", "build": "--toolchain"}


def is_optional(stage: Stage) -> bool:
    """Whether ``stage`` may be skipped without leaving the workspace incomplete."""
    return stage.name in OPTIONAL
```

- [ ] **Step 4: State**

In `ai_rfc/pipeline/state.py`, add beside `_prose`/`_checkpoint` (imports: `import json`, `from ..draft.build import BUILD_DIR, REPORT_FILE`, and the module's existing git projection helper — `pipeline/substrate.py`'s `_git` returns `(returncode, stdout)`; import it as `from .substrate import _git as _git_status` or reuse whatever `state.py` already uses for the clone):

```python
def _draft_head(ws: Workspace) -> str | None:
    code, out = _git_status(ws.draft, "rev-parse", "HEAD")
    return out if code == 0 and out else None


def _build(ws: Workspace, prose: State) -> tuple[State, str]:
    if prose is not State.DONE:
        return State.BLOCKED, "there is no prose to build"
    report_path = ws.out / BUILD_DIR / REPORT_FILE
    if not report_path.exists():
        return State.BLOCKED, "no build report yet; run with --toolchain"
    report = json.loads(report_path.read_text())
    head = _draft_head(ws)
    if head is None or report.get("commit") != head:
        return State.STALE, "the build report is for another draft commit"
    if report.get("exit_code", 1) != 0 or report.get("findings"):
        return State.STALE, "the last build had findings"
    return State.DONE, ""
```

In `state()`'s `by_name` dict add `"lint": rederivable if by_name_prose_done else (State.BLOCKED, "there is no prose to lint")` — concretely, compute `prose = _prose(ws, mining[0])` once, then:

```python
        "lint": (
            (State.RECOMPUTED, "") if prose[0] is State.DONE else (State.BLOCKED, "there is no prose to lint")
        ),
        "build": _build(ws, prose[0]),
```

(and use the same `prose` tuple for the `"prose"` entry). In `next_stage`, replace `if entry.stage.name == "forge": continue` with `if is_optional(entry.stage): continue` (import `is_optional` from `.stages`). Update the `next_stage` docstring: "``forge`` and ``build`` never block …".

- [ ] **Step 5: Runner and CLI**

In `ai_rfc/pipeline/run.py`: add `toolchain: Path | None = None` to `_Request`; add the builders and table entries:

```python
def _lint(req: _Request) -> tuple[list[str], CommandModule]:
    argv = [str(req.ws.draft), "--out", str(req.ws.out), "--manifest", str(req.ws.manifest)]
    if req.strict:
        argv.append("--strict")
    return argv, draft_cli


def _build(req: _Request) -> tuple[list[str], CommandModule]:
    argv = [str(req.ws.draft), "--out", str(req.ws.out), "--toolchain", str(req.toolchain)]
    if req.strict:
        argv.append("--strict")
    return argv, draft_cli
```

`DISPATCH` gains `"lint": _lint, "build": _build`; `perform()` gains `toolchain: Path | None = None` and passes it into `_Request`. Check how the existing builders name the verb (the `draft_cli` module's `main` receives `["gate", …]` — look at `_gate` and prefix `"lint"`/`"build"` the same way).

In `ai_rfc/pipeline/cli.py`: add to the `run` parser

```python
    run.add_argument(
        "--toolchain",
        type=Path,
        default=(Path(os.environ["AI_RFC_TOOLCHAIN"]) if os.environ.get("AI_RFC_TOOLCHAIN") else None),
        help="toolchain.json for the build stage (default: $AI_RFC_TOOLCHAIN); without it, build is skipped.",
    )
```

and replace the forge-only skip in the stage loop with the general rule:

```python
        if is_optional(stage):
            flag = OPTIONAL[stage.name]
            given = getattr(args, flag.lstrip("-").replace("-", "_"))
            if given is None:
                if args.start == stage.name:
                    _report(f"error: {stage.name} was asked for but no {flag} was given")
                    return 1
                _report(f"note: skipping {stage.name}; no {flag} given")
                continue
```

Pass `toolchain=args.toolchain` into `perform(...)`. Add `"lint"` to the re-derivable stage tuple SP0 Task 2 introduced (it lists `check` and `gate`). `pipeline/workspace.py`: confirm `Workspace` exposes `draft`, `out` and `manifest` properties (grep `def draft`); add `draft` as `self.root / "draft"` if missing. Update `pipeline/README.md`'s stage table with stages 10 and 11 and the sentence "forge and build are optional: each is skipped without its flag and stepped over by `status`".

- [ ] **Step 6: Run the pipeline tests**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/substrate/pipeline -v`
Expected: all PASS, including the DISPATCH-coverage assertion (it now counts nine deterministic stages).

- [ ] **Step 7: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/pipeline tests/substrate/pipeline && $PY -m flake8 --max-line-length=88 ai_rfc/pipeline tests/substrate/pipeline && $PY -m mypy --follow-imports=silent ai_rfc/pipeline
git status --short
git add ai_rfc/pipeline/stages.py ai_rfc/pipeline/state.py ai_rfc/pipeline/run.py ai_rfc/pipeline/cli.py ai_rfc/pipeline/workspace.py ai_rfc/pipeline/README.md tests/substrate/pipeline/test_state.py tests/substrate/pipeline/test_run.py tests/substrate/pipeline/test_cli.py
git commit -m "feat: add the lint and build stages behind one optional-stage rule"
```

---

### Task 4: One core, two frontends — `draft_build`, `draft_lint`, and the build stage before `git tag`

**Files:**
- Modify: `ai_rfc/server/paths.py` (`Context.toolchain`, `resolve_context`)
- Create: `ai_rfc/server/core/build.py`
- Modify: `ai_rfc/server/core/draft.py` (`tag_revision`), `ai_rfc/server/tools.py` (two tools + `ALL_TOOLS`), `ai_rfc/server/cli.py` (two verbs), `docs/parity.md` (two rows + the `revision_tag` row)
- Test: `tests/server/test_paths.py` (SP1 created it), `tests/server/test_build.py` (new), `tests/server/test_parity.py`, `tests/server/test_draft.py`

**Interfaces:**
- Consumes: `ai_rfc.server.core.gates._run(ctx, module, *args) -> tuple[int, list[str]]` (SP1's signature: module path `ai_rfc.draft`, no `cwd`), `CoreError` (grep `class CoreError` under `ai_rfc/server/core/`), the verbs from Tasks 1–2, `ai_rfc.draft.build.{BUILD_DIR, REPORT_FILE}`, `ai_rfc.draft.lint.REPORT_FILE`.
- Produces: `Context.toolchain: Path | None`; `draft_build(ctx: Context, ref: str = "HEAD") -> dict` (`{exit_code, stderr, findings, commit, outputs}`); `draft_lint(ctx: Context, worktree: bool = True) -> dict` (`{exit_code, stderr, findings, metrics}`); tools `ai_rfc_draft_build(ref="HEAD")`, `ai_rfc_draft_lint(worktree=True)`; verbs `ai_rfc draft-build [--ref REF]`, `ai_rfc draft-lint [--committed]`; `tag_revision` returns `stage: "draft_build"` when the build refuses. Task 5 sets `AI_RFC_TOOLCHAIN` in every session env; Task 9's prompts name the tools.

**Why this shape.** The gate is hard whenever a toolchain is configured, and Task 5 makes `campaign init` refuse to run without one — so in production every tag compiles, while the server tests that never set `AI_RFC_TOOLCHAIN` keep their `tag_revision` behaviour. Arm C gets no raw equivalent (D42): the parity table says so in the row rather than hiding it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/server/test_paths.py`:

```python
def test_the_toolchain_handle_is_optional_but_must_be_a_file(monkeypatch, tmp_path):
    from ai_rfc.server.paths import EnvError, resolve_context

    monkeypatch.setenv("AI_RFC_WORKSPACE", str(tmp_path))
    monkeypatch.delenv("AI_RFC_TOOLCHAIN", raising=False)
    assert resolve_context().toolchain is None
    record = tmp_path / "toolchain.json"
    record.write_text("{}")
    monkeypatch.setenv("AI_RFC_TOOLCHAIN", str(record))
    assert resolve_context().toolchain == record
    monkeypatch.setenv("AI_RFC_TOOLCHAIN", str(tmp_path / "missing.json"))
    with pytest.raises(EnvError):
        resolve_context()
```

Create `tests/server/test_build.py`:

```python
"""The build and lint cores over the substrate verbs."""

import json

import pytest

from ai_rfc.draft.build import BUILD_DIR, REPORT_FILE
from ai_rfc.server import tools
from ai_rfc.server.core import build as build_core
from ai_rfc.server.core.build import CoreError, draft_build, draft_lint
from ai_rfc.server.paths import resolve_context


def _fake_run(report: dict, code: int = 0):
    calls = []

    def run(ctx, module, *args):
        calls.append((module, args))
        target = ctx.workspace / "out" / BUILD_DIR
        target.mkdir(parents=True, exist_ok=True)
        (target / REPORT_FILE).write_text(json.dumps(report))
        return code, ["note: fake"]

    run.calls = calls
    return run


def test_draft_build_needs_a_toolchain(fixture_workspace, monkeypatch):
    monkeypatch.delenv("AI_RFC_TOOLCHAIN", raising=False)
    with pytest.raises(CoreError) as excinfo:
        draft_build(resolve_context())
    assert "AI_RFC_TOOLCHAIN" in str(excinfo.value)


def test_draft_build_runs_the_verb_and_reads_the_report(fixture_workspace, monkeypatch, tmp_path):
    record = tmp_path / "toolchain.json"
    record.write_text("{}")
    monkeypatch.setenv("AI_RFC_TOOLCHAIN", str(record))
    (fixture_workspace / "refcache").mkdir()
    fake = _fake_run({"commit": "c" * 40, "exit_code": 0, "findings": [], "outputs": {"draft-x.txt": {}}})
    monkeypatch.setattr(build_core, "_run", fake)
    result = draft_build(resolve_context(), ref="draft-test-spec-00")
    module, args = fake.calls[0]
    assert module == "ai_rfc.draft" and args[0] == "build"
    assert "--ref" in args and args[args.index("--ref") + 1] == "draft-test-spec-00"
    assert "--toolchain" in args and "--refcache" in args
    assert result == {"exit_code": 0, "stderr": ["note: fake"], "findings": [], "commit": "c" * 40, "outputs": {"draft-x.txt": {}}}


def test_draft_lint_measures_the_worktree_by_default(fixture_workspace):
    result = draft_lint(resolve_context())
    assert result["exit_code"] == 0
    assert set(result["metrics"]) == {"sections", "abstract", "references", "keywords", "blocks", "citations", "narration"}
    assert isinstance(result["findings"], list)
    assert tools.ai_rfc_draft_lint()["metrics"] == result["metrics"]
```

Append to `tests/server/test_draft.py` (it holds the `tag_revision` tests; reuse its fixture that records a revision — read the file for the fixture name, below called `recorded`):

```python
def test_tag_revision_refuses_when_the_build_has_findings(recorded, monkeypatch, tmp_path):
    from ai_rfc.server.core import draft as draft_core
    from ai_rfc.server.core.draft import tag_revision
    from ai_rfc.server.paths import resolve_context

    record = tmp_path / "toolchain.json"
    record.write_text("{}")
    monkeypatch.setenv("AI_RFC_TOOLCHAIN", str(record))
    monkeypatch.setattr(
        draft_core,
        "draft_build",
        lambda ctx, ref="HEAD": {"exit_code": 0, "stderr": [], "findings": ["broken reference RFC9999 (not in the refcache)"], "commit": None, "outputs": {}},
    )
    result = tag_revision(resolve_context(), recorded["tag"], "msg")
    assert result["stage"] == "draft_build" and result["exit_code"] == 3
    assert result["findings"] == ["broken reference RFC9999 (not in the refcache)"]
    assert recorded["tag"] not in draft_core._git(resolve_context(), "tag", "-l").stdout
```

Append to `tests/server/test_parity.py`:

```python
def test_draft_lint_parity(make_workspace, capsys):
    tool_arm, cli_arm, use = _twins(make_workspace)
    use(tool_arm)
    via_tool = tools.ai_rfc_draft_lint()
    use(cli_arm)
    assert cli.main(["draft-lint"]) == 0
    via_cli = json.loads(capsys.readouterr().out)
    assert via_tool["metrics"] == via_cli["metrics"] and via_tool["findings"] == via_cli["findings"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/server -v`
Expected: the new tests FAIL (`AttributeError: toolchain`, `No module named 'ai_rfc.server.core.build'`, `main` rejecting `draft-lint`); `test_every_tool_is_in_the_parity_table` still passes (nothing registered yet).

- [ ] **Step 3: The toolchain handle**

In `ai_rfc/server/paths.py`, add to `Context` a field `toolchain: Path | None = None` (after `workspace`; keep the dataclass frozen), and in `resolve_context()` after the workspace validation:

```python
    toolchain_env = os.environ.get("AI_RFC_TOOLCHAIN")
    toolchain: Path | None = None
    if toolchain_env:
        toolchain = Path(toolchain_env).resolve()
        if not toolchain.is_file():
            raise EnvError(f"AI_RFC_TOOLCHAIN={toolchain} is not a file")
    return Context(workspace=workspace_path, toolchain=toolchain)
```

Extend the module docstring: "`AI_RFC_TOOLCHAIN` is optional; when set it names the `toolchain.json` the build gate uses."

- [ ] **Step 4: The core**

Create `ai_rfc/server/core/build.py`:

```python
"""Draft build and lint over the substrate verbs, exit codes surfaced raw."""

from __future__ import annotations

import json
from typing import Any

from ai_rfc.draft.build import BUILD_DIR
from ai_rfc.draft.build import REPORT_FILE as BUILD_REPORT
from ai_rfc.draft.lint import REPORT_FILE as LINT_REPORT

from ..paths import Context
from . import CoreError
from .gates import _run

_DRAFT = "ai_rfc.draft"
_METRIC_KEYS = ("sections", "abstract", "references", "keywords", "blocks", "citations", "narration")


def draft_build(ctx: Context, ref: str = "HEAD") -> dict[str, Any]:
    """Compile the draft at ``ref`` with the configured toolchain, offline.

    Args:
        ctx: The resolved context; ``ctx.toolchain`` must be set.
        ref: Tag, branch or commit to build.

    Returns:
        ``{exit_code, stderr, findings, commit, outputs}`` from
        ``out/build/build-report.json``; ``findings`` falls back to stderr when
        no report was written.

    Raises:
        CoreError: If no toolchain is configured.
    """
    if ctx.toolchain is None:
        raise CoreError(
            "AI_RFC_TOOLCHAIN is unset; the build gate needs a provisioned "
            "toolchain (experiment toolchain provision)"
        )
    args = [
        "build",
        str(ctx.workspace / "draft"),
        "--out",
        str(ctx.workspace / "out"),
        "--ref",
        ref,
        "--toolchain",
        str(ctx.toolchain),
    ]
    refcache = ctx.workspace / "refcache"
    if refcache.is_dir():
        args += ["--refcache", str(refcache)]
    code, stderr = _run(ctx, _DRAFT, *args)
    report_path = ctx.workspace / "out" / BUILD_DIR / BUILD_REPORT
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    return {
        "exit_code": code,
        "stderr": stderr,
        "findings": report["findings"] if report else stderr,
        "commit": report["commit"] if report else None,
        "outputs": report["outputs"] if report else {},
    }


def draft_lint(ctx: Context, worktree: bool = True) -> dict[str, Any]:
    """Measure the draft's quality against the workspace manifest.

    Args:
        ctx: The resolved context.
        worktree: Measure the uncommitted draft file (the default, so an author
            can lint before committing) rather than ``HEAD``.

    Returns:
        ``{exit_code, stderr, findings, metrics}`` from ``out/lint-report.json``.
    """
    args = [
        "lint",
        str(ctx.workspace / "draft"),
        "--out",
        str(ctx.workspace / "out"),
        "--manifest",
        str(ctx.manifest),
    ]
    if worktree:
        args.append("--worktree")
    code, stderr = _run(ctx, _DRAFT, *args)
    report_path = ctx.workspace / "out" / LINT_REPORT
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    return {
        "exit_code": code,
        "stderr": stderr,
        "findings": report["findings"] if report else stderr,
        "metrics": {key: report[key] for key in _METRIC_KEYS} if report else {},
    }
```

(`from . import CoreError` — adjust to wherever `CoreError` is defined; `core/draft.py` shows the import to copy.)

- [ ] **Step 5: The build stage in `tag_revision`**

In `ai_rfc/server/core/draft.py`, import `from .build import draft_build` and, after the manifest-gate refusal block and before `tagged = _git(ctx, "tag", "-a", tag, "-m", message)`, insert:

```python
    if ctx.toolchain is not None:
        built = draft_build(ctx, "HEAD")
        if built["exit_code"] != 0 or built["findings"]:
            return {
                "exit_code": built["exit_code"] or 3,
                "tag": tag,
                "stage": "draft_build",
                "findings": built["findings"],
                "rolled_back": False,
            }
```

Update the docstring's "Order:" sentence: "the strict manifest gate at 0, the draft built cleanly when a toolchain is configured; then the tag is created …". The monkeypatched name in the test is `draft_core.draft_build`, so import the function by name (not the module).

- [ ] **Step 6: Tools, verbs, parity rows**

`ai_rfc/server/tools.py`, before `ALL_TOOLS`:

```python
def ai_rfc_draft_build(ref: str = "HEAD") -> dict[str, Any]:
    """Compile the draft at a ref with the template toolchain, offline (exit raw)."""
    return build.draft_build(resolve_context(), ref)


def ai_rfc_draft_lint(worktree: bool = True) -> dict[str, Any]:
    """Measure the draft's quality; findings are what to fix before tagging."""
    return build.draft_lint(resolve_context(), worktree)
```

Append both to `ALL_TOOLS` (last two entries; that is the parity-table order). Import `build` beside the other `core` modules.

`ai_rfc/server/cli.py`: after the `revision-tag` parser add

```python
    draft_build = verbs.add_parser("draft-build", help="Compile the draft, offline.")
    draft_build.add_argument("--ref", default="HEAD", help="Tag, branch or commit.")
    draft_lint = verbs.add_parser("draft-lint", help="Measure the draft's quality.")
    draft_lint.add_argument(
        "--committed", action="store_true", help="Lint HEAD instead of the worktree."
    )
```

and in the dispatch, following the module's existing pattern for emitting a result dict as JSON and returning its `exit_code` (copy the `gate` verb's branch):

```python
    elif args.verb == "draft-build":
        result = tools.ai_rfc_draft_build(args.ref)
        _emit(result)
        return result["exit_code"]
    elif args.verb == "draft-lint":
        result = tools.ai_rfc_draft_lint(worktree=not args.committed)
        _emit(result)
        return result["exit_code"]
```

(`_emit` prints JSON and returns `None` — it does **not** return the exit code, so emitting and returning are two statements, exactly as the real `gate` branch does. Grep `def _emit` in `cli.py` to confirm the name before editing; `return _emit(...)` would return `None` and break `main`'s contract.)

`docs/parity.md`: add two rows after `ai_rfc_revision_tag`:

```
| `ai_rfc_draft_build` | `ai_rfc draft-build [--ref REF]` | — (not available in arm C: frozen at the pre-v2 surface, spec D42) |
| `ai_rfc_draft_lint` | `ai_rfc draft-lint [--committed]` | — (not available in arm C, D42) |
```

and extend the `ai_rfc_revision_tag` row's third column with ", and runs `draft build` before the tag when `AI_RFC_TOOLCHAIN` is set".

- [ ] **Step 7: Run the server suite**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/server -v`
Expected: all PASS, including `test_every_tool_is_in_the_parity_table` with 18 tools.

- [ ] **Step 8: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/server tests/server && $PY -m flake8 --max-line-length=88 ai_rfc/server tests/server && $PY -m mypy --follow-imports=silent ai_rfc/server
git status --short
git add ai_rfc/server/paths.py ai_rfc/server/core/build.py ai_rfc/server/core/draft.py ai_rfc/server/tools.py ai_rfc/server/cli.py docs/parity.md tests/server/test_paths.py tests/server/test_build.py tests/server/test_draft.py tests/server/test_parity.py
git commit -m "feat: build and lint the draft through the server, and build before every tag"
```

---

### Task 5: `experiment toolchain provision|verify`, and a campaign that refuses to run without one

**Files:**
- Create: `ai_rfc/experiment/toolchain.py`
- Modify: `ai_rfc/experiment/cli.py` (`toolchain` command; `campaign init --toolchain`), `ai_rfc/experiment/config.py` (`CampaignConfig.toolchain`, `Campaign.toolchain`, `Campaign.toolchain_sha256`, `Campaign.template_home`, the refusal), `ai_rfc/experiment/runner.py` (`build_env`), `ai_rfc/experiment/arms.py` (`mcp_config`)
- Test: `tests/experiment/test_toolchain.py` (new), `tests/experiment/test_config.py`, `tests/experiment/test_runner.py`, `tests/experiment/test_arms.py`

**Interfaces:**
- Consumes: `ai_rfc.draft.build.{load_toolchain, probe_toolchain, build, Toolchain}` (Task 1); `ai_rfc.experiment.workspace.{TEMPLATE_URL, TEMPLATE_COMMIT, _run_git, _git}`; the `template_repo` fixture (Task 6 extends it with `template/Makefile` and `example/`; do Task 6's fixture step first if you execute out of order).
- Produces: `provision(root: Path, *, template: str = TEMPLATE_URL, template_commit: str = TEMPLATE_COMMIT, references: tuple[str, ...] = DEFAULT_REFERENCES, runner: Runner | None = None) -> Path` (the record path); `verify(record: Path, *, runner: Runner | None = None) -> tuple[bool, tuple[str, ...]]`; constants `TOOLS_DIR = "tools"`, `RECORD_FILE = "toolchain.json"`, `REFCACHE_DIGEST = "refcache.sha256"`, `DEFAULT_REFERENCES`; `Campaign.toolchain: str | None = None`, `Campaign.toolchain_sha256: str | None = None`, `Campaign.template_home: str | None = None`; `build_env` and `mcp_config(..., toolchain: Path | None = None)` export `AI_RFC_TOOLCHAIN`. Task 6's `prepare` copies references out of `<root>/tools/.refcache`.

**Why this shape.** Provisioning is the one networked, machine-specific step, so it runs once per machine and writes down everything a build needs; `verify` is what every `campaign init` re-checks (D49) and what the run-and-see of 2026-09-03 proved by hand (`~/ai-rfc-experiments/tools/toolchain.json` is the record `provision` must reproduce). The runner is injected so the tests never install anything.

- [ ] **Step 1: Write the failing tests**

Create `tests/experiment/test_toolchain.py`:

```python
"""Provisioning writes a record a build can trust; verify re-checks it offline."""

import json
import stat
import subprocess
from pathlib import Path

import pytest

from ai_rfc.experiment import ExperimentError
from ai_rfc.experiment.toolchain import (
    DEFAULT_REFERENCES,
    RECORD_FILE,
    REFCACHE_DIGEST,
    TOOLS_DIR,
    provision,
    verify,
)


def _make_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _fake_tools(root: Path):
    """A runner that pretends make, npm and the tools succeeded."""
    calls = []
    home = root / TOOLS_DIR / "i-d-template"

    def run(argv, **kwargs):
        calls.append(argv)
        program = Path(argv[0]).name
        if program == "make":
            if "deps" in argv:
                _make_executable(home / ".venv" / "bin" / "xml2rfc")
                _make_executable(home / ".gems" / "ruby" / "4.0.0" / "bin" / "kramdown-rfc")
                (home / "Gemfile.lock").write_text("GEM\n  kramdown-rfc (1.7.43)\n")
            else:
                scratch = Path(argv[argv.index("-C") + 1])
                cache = Path(next(a for a in argv if a.startswith("KRAMDOWN_REFCACHEDIR=")).split("=", 1)[1])
                cache.mkdir(parents=True, exist_ok=True)
                for reference in DEFAULT_REFERENCES:
                    number = reference[3:]
                    (cache / f"reference.RFC.{number}.xml").write_text(f"<reference anchor='{reference}'/>\n")
                trace = next((a for a in argv if a.startswith("TRACE_FILE=")), None)
                if trace:
                    Path(trace.split("=", 1)[1]).write_text("draft-todo-yourname-protocol xml2rfc-txt 0\n")
                for source in scratch.glob("draft-*.md"):
                    (scratch / (source.stem + ".txt")).write_text(f"rendered {source.stem}\n")
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        if program == "npm":
            _make_executable(root / TOOLS_DIR / "node_modules" / ".bin" / "idnits")
            _make_executable(root / TOOLS_DIR / "node_modules" / ".bin" / "aasvg")
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="9.9.9\n", stderr="")

    run.calls = calls
    return run


def test_provision_writes_a_complete_record(tmp_path, template_repo):
    template, commit = template_repo
    root = tmp_path / "root"
    fake = _fake_tools(root)
    record = provision(root, template=template, template_commit=commit, runner=fake)
    assert record == root / TOOLS_DIR / RECORD_FILE
    payload = json.loads(record.read_text())
    home = root / TOOLS_DIR / "i-d-template"
    assert payload["template_home"] == str(home) and payload["template_commit"] == commit
    assert payload["ruby"]["kramdown_rfc"] == str(home / ".gems" / "ruby" / "4.0.0" / "bin" / "kramdown-rfc")
    assert payload["ruby"]["gem_path"] == str(home / ".gems" / "ruby" / "4.0.0")
    assert payload["node"]["idnits"].endswith("node_modules/.bin/idnits")
    assert payload["refcache"]["entries"] == list(DEFAULT_REFERENCES)
    assert (root / TOOLS_DIR / REFCACHE_DIGEST).read_text().count("\n") == len(DEFAULT_REFERENCES)
    assert (home / "main.mk").exists() and not (home / ".git").exists()
    deps = [argv for argv in fake.calls if Path(argv[0]).name == "make" and "deps" in argv]
    assert deps and f"LIBDIR={home}" in deps[0] and "NO_NODEJS=true" in deps[0]
    seed = [argv for argv in fake.calls if Path(argv[0]).name == "make" and "txt" in argv]
    assert seed and "KRAMDOWN_OFFLINE=1" not in seed[0]


def test_provision_refuses_an_existing_record(tmp_path, template_repo):
    template, commit = template_repo
    root = tmp_path / "root"
    provision(root, template=template, template_commit=commit, runner=_fake_tools(root))
    with pytest.raises(ExperimentError) as excinfo:
        provision(root, template=template, template_commit=commit, runner=_fake_tools(root))
    assert "exists" in str(excinfo.value)


def test_verify_passes_a_fresh_record_and_names_what_broke(tmp_path, template_repo):
    template, commit = template_repo
    root = tmp_path / "root"
    fake = _fake_tools(root)
    record = provision(root, template=template, template_commit=commit, runner=fake)
    ok, reasons = verify(record, runner=fake)
    assert ok and reasons == ()
    (root / TOOLS_DIR / ".refcache" / "reference.RFC.9000.xml").write_text("changed\n")
    ok, reasons = verify(record, runner=fake)
    assert not ok and any("refcache" in reason for reason in reasons)
```

Append to `tests/experiment/test_config.py` (use its existing `CampaignConfig` construction — grep `CampaignConfig(` there and copy the keyword set, adding `toolchain=`):

```python
def test_init_refuses_without_a_verified_toolchain(pristine, tmp_path, plugin_root, monkeypatch):
    from ai_rfc.experiment import toolchain as toolchain_module

    record = tmp_path / "toolchain.json"
    record.write_text('{"template_home": "/t"}\n')
    monkeypatch.setattr(toolchain_module, "verify", lambda record, runner=None: (False, ("refcache digest differs",)))
    with pytest.raises(ExperimentError) as excinfo:
        init_campaign(_init(tmp_path, pristine, plugin_root, toolchain=record))
    assert "refcache digest differs" in str(excinfo.value)
    with pytest.raises(ExperimentError) as excinfo:
        init_campaign(_init(tmp_path, pristine, plugin_root, toolchain=None))
    assert "toolchain" in str(excinfo.value)


def test_init_records_the_toolchain_digest(pristine, tmp_path, plugin_root, monkeypatch):
    from ai_rfc.experiment import toolchain as toolchain_module

    record = tmp_path / "toolchain.json"
    record.write_text('{"template_home": "/t"}\n')
    monkeypatch.setattr(toolchain_module, "verify", lambda record, runner=None: (True, ()))
    campaign = init_campaign(_init(tmp_path, pristine, plugin_root, toolchain=record))
    assert campaign.toolchain == str(record) and campaign.template_home == "/t"
    assert campaign.toolchain_sha256 == hashlib.sha256(record.read_bytes()).hexdigest()
    assert json.loads((campaign.dir / "campaign.json").read_text())["toolchain_sha256"] == campaign.toolchain_sha256
```

(`_init` is that module's existing helper: today `_init(tmp_path, pristine, panther_repo, plugin_root, **overrides)` builds a `CampaignConfig` and returns it, forwarding `**overrides`; SP1 drops its `panther_repo` parameter — match whatever signature SP1 left, and pass `toolchain=` through `**overrides`. Every other `_init(...)` call in the module now needs a toolchain too: give the helper a default `toolchain=tmp_path / "toolchain.json"` written as `{"template_home": "/t"}` and have the module-level autouse fixture monkeypatch `toolchain_module.verify` to `(True, ())`.) In `tests/experiment/test_runner.py`, extend the existing `build_env` test: `assert env["AI_RFC_TOOLCHAIN"] == campaign.toolchain` when the campaign fixture carries one, and `"AI_RFC_TOOLCHAIN" not in env` when `campaign.toolchain is None`. In `tests/experiment/test_arms.py`, extend the `mcp_config` test: `mcp_config(python=..., workspace=..., toolchain=Path("/t/toolchain.json"))["mcpServers"]["ai_rfc"]["env"]["AI_RFC_TOOLCHAIN"] == "/t/toolchain.json"`.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_toolchain.py tests/experiment/test_config.py tests/experiment/test_runner.py tests/experiment/test_arms.py -v`
Expected: `test_toolchain.py` FAILS at import; the config tests FAIL with `TypeError: unexpected keyword 'toolchain'`; the env/mcp assertions FAIL with `KeyError`.

- [ ] **Step 3: Write `ai_rfc/experiment/toolchain.py`**

```python
"""Provision and verify the shared Internet-Draft toolchain, once per machine.

One pinned template checkout under ``<root>/tools/`` carries the venv
(xml2rfc), the gems (kramdown-rfc), the node tools (idnits, aasvg) and a
reference cache seeded by one online build. ``toolchain.json`` records every
path and version; ``ai_rfc.draft.build`` reads it and nothing else. The
2026-09-03 run-and-see is the specification: this module reproduces it.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ai_rfc.draft.build import (
    XML2RFC_BASE_OPTS,
    Toolchain,
    build,
    load_toolchain,
    probe_toolchain,
)

from . import ExperimentError
from .workspace import TEMPLATE_COMMIT, TEMPLATE_URL, _git, _run_git

Runner = Callable[..., "subprocess.CompletedProcess[str]"]

TOOLS_DIR = "tools"
TEMPLATE_DIR = "i-d-template"
RECORD_FILE = "toolchain.json"
REFCACHE_DIGEST = "refcache.sha256"
REFCACHE_DIR = ".refcache"
PROBE_DIR = "probe"
SEED_DRAFT = "draft-seed-refs.md"
EXAMPLE_DRAFT = "draft-todo-yourname-protocol.md"
NODE_PACKAGES = ("aasvg", "@ietf-tools/idnits")
#: Everything the two known targets cite; the seed build caches each once.
DEFAULT_REFERENCES: tuple[str, ...] = (
    "RFC2119", "RFC8174", "RFC9000", "RFC9001", "RFC9002", "RFC9114", "RFC9204",
    "RFC8446", "RFC5280", "RFC6125", "RFC7322", "RFC2360", "RFC3552",
    "RFC9110", "RFC8259",
)
VERIFY_DATE = "2026-08-26"
_SEED_FRONT = """---
title: "Reference Cache Seed"
abbrev: "Ref Seed"
docname: draft-seed-refs-latest
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
    ins: A. Harness
    name: ai-rfc harness
    organization: none
    email: ai-rfc-harness@localhost
"""


def _make_variables(home: Path, record: dict[str, Any] | None = None) -> list[str]:
    variables = [
        f"LIBDIR={home}",
        "DEFAULT_BRANCH=main",
        "BRANCH_FETCH=false",
        "NO_NODEJS=true",
    ]
    if record:
        variables += [
            f"GEM_PATH={record['ruby']['gem_path']}",
            f"GEM_HOME={record['ruby']['gem_path']}",
            f"kramdown-rfc={record['ruby']['kramdown_rfc']}",
        ]
    return variables


def _version(run: Runner, *argv: str) -> str:
    try:
        result = run(list(argv), capture_output=True, text=True)
    except OSError as error:
        raise ExperimentError(f"cannot run {argv[0]}: {error}") from None
    return (result.stdout or result.stderr).strip().splitlines()[-1] if (result.stdout or result.stderr).strip() else ""


def _seed_draft(references: tuple[str, ...]) -> str:
    listed = "\n".join(f"  {ref}:" for ref in references if ref not in ("RFC2119", "RFC8174"))
    cited = ", ".join(f"{{{{{ref}}}}}" for ref in references if ref not in ("RFC2119", "RFC8174"))
    return (
        _SEED_FRONT
        + f"\nnormative:\n{listed}\n\n--- abstract\n\nSeeds a reference cache.\n\n--- middle\n\n"
        "# Introduction\n\n{::boilerplate bcp14-tagged}\n\n"
        f"This draft cites {cited} so that each is fetched once.\n\n"
        "# Security Considerations\n\nNone.\n\n# IANA Considerations\n\nNone.\n\n--- back\n"
    )


def _digest_refcache(refcache: Path) -> str:
    lines = []
    for entry in sorted(refcache.glob("*.xml")):
        lines.append(f"{hashlib.sha256(entry.read_bytes()).hexdigest()}  {entry.name}")
    return "\n".join(lines) + ("\n" if lines else "")


def provision(
    root: Path,
    *,
    template: str = TEMPLATE_URL,
    template_commit: str = TEMPLATE_COMMIT,
    references: tuple[str, ...] = DEFAULT_REFERENCES,
    runner: Runner | None = None,
) -> Path:
    """Install the toolchain under ``root/tools`` and write its record.

    The only networked command in the harness: it clones the template, lets
    the template's ``make deps`` install the venv and gems, installs the node
    tools, and builds a seed draft once online to fill the reference cache.

    Args:
        root: The experiments root (``AI_RFC_EXPERIMENTS_ROOT``).
        template: Template clone source (URL or local path).
        template_commit: The commit to pin.
        references: The reference ids to cache.
        runner: ``subprocess.run`` stand-in for make/npm/version probes.

    Returns:
        The record path.

    Raises:
        ExperimentError: If a record exists or any step fails.
    """
    run = runner or subprocess.run
    tools = root / TOOLS_DIR
    record_path = tools / RECORD_FILE
    if record_path.exists():
        raise ExperimentError(f"{record_path} exists; a toolchain is provisioned once")
    home = tools / TEMPLATE_DIR
    if home.exists():
        raise ExperimentError(f"{home} exists; remove it to re-provision")
    tools.mkdir(parents=True, exist_ok=True)
    cloned = _run_git("clone", "-q", template, str(home))
    if cloned.returncode != 0:
        raise ExperimentError(f"cloning {template} failed: {cloned.stderr.strip()}")
    _git(home, "checkout", "-q", template_commit)
    shutil.rmtree(home / ".git")

    probe = tools / PROBE_DIR
    probe.mkdir(exist_ok=True)
    shutil.copyfile(home / "template" / "Makefile", probe / "Makefile")
    shutil.copyfile(home / "example" / EXAMPLE_DRAFT, probe / EXAMPLE_DRAFT)
    (probe / SEED_DRAFT).write_text(_seed_draft(references))

    make = shutil.which("gmake") or shutil.which("make") or "make"
    deps = run([make, "-C", str(probe), "-f", str(home / "main.mk"), *_make_variables(home), "deps"], capture_output=True, text=True)
    if deps.returncode != 0:
        raise ExperimentError(f"make deps failed:\n{deps.stderr[-2000:]}")
    npm = run(["npm", "install", "--prefix", str(tools), "--no-save", *NODE_PACKAGES], capture_output=True, text=True)
    if npm.returncode != 0:
        raise ExperimentError(f"npm install failed:\n{npm.stderr[-2000:]}")

    binstubs = sorted(home.glob(".gems/ruby/*/bin/kramdown-rfc"))
    if not binstubs:
        raise ExperimentError(f"no kramdown-rfc binstub under {home / '.gems'}; did bundle install run?")
    kramdown = binstubs[-1]
    gem_path = kramdown.parent.parent
    ruby = shutil.which("ruby")
    node = shutil.which("node")
    if ruby is None or node is None:
        raise ExperimentError("ruby and node must be on PATH to provision")
    record: dict[str, Any] = {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "native",
        "template_home": str(home),
        "template_commit": template_commit,
        "template_source": template,
        "make": {"path": make, "version": _version(run, make, "--version")},
        "python": {"venv": str(home / ".venv"), "xml2rfc": str(home / ".venv" / "bin" / "xml2rfc"), "xml2rfc_version": _version(run, str(home / ".venv" / "bin" / "xml2rfc"), "--version")},
        "ruby": {"bin_dir": str(Path(ruby).parent), "version": _version(run, ruby, "--version"), "gem_path": str(gem_path), "kramdown_rfc": str(kramdown), "gemfile_lock": (home / "Gemfile.lock").read_text() if (home / "Gemfile.lock").exists() else ""},
        "node": {"bin_dir": str(Path(node).parent), "version": _version(run, node, "--version"), "idnits": str(tools / "node_modules" / ".bin" / "idnits"), "aasvg": str(tools / "node_modules" / ".bin" / "aasvg")},
        "refcache": {"dir": str(tools / REFCACHE_DIR), "entries": list(references), "seed_draft": str(probe / SEED_DRAFT), "digest_file": str(tools / REFCACHE_DIGEST)},
    }
    seed = run(
        [make, "-C", str(probe), "-f", str(home / "main.mk"), *_make_variables(home, record), f"KRAMDOWN_REFCACHEDIR={tools / REFCACHE_DIR}", "txt"],
        capture_output=True,
        text=True,
    )
    if seed.returncode != 0:
        raise ExperimentError(f"the online seed build failed:\n{seed.stderr[-2000:]}")
    missing = [ref for ref in references if not (tools / REFCACHE_DIR / f"reference.RFC.{ref[3:]}.xml").exists()]
    if missing:
        raise ExperimentError(f"the seed build cached nothing for {', '.join(missing)}")
    (tools / REFCACHE_DIGEST).write_text(_digest_refcache(tools / REFCACHE_DIR))
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    ok, reasons = verify(record_path, runner=run)
    if not ok:
        raise ExperimentError("provisioned, but verify failed: " + "; ".join(reasons))
    return record_path


def verify(record: Path, *, runner: Runner | None = None) -> tuple[bool, tuple[str, ...]]:
    """Re-check a toolchain record offline: executables, refcache, reproducibility.

    Args:
        record: The ``toolchain.json`` to verify.
        runner: ``subprocess.run`` stand-in for the make invocations.

    Returns:
        ``(ok, reasons)``; ``reasons`` is empty when ok.
    """
    reasons: list[str] = []
    try:
        toolchain = load_toolchain(record)
    except Exception as error:  # noqa: BLE001 - every failure is a reason, not a crash
        return False, (str(error),)
    reasons.extend(probe_toolchain(toolchain))
    tools = record.parent
    digest_file = tools / REFCACHE_DIGEST
    if not digest_file.exists():
        reasons.append(f"refcache digest {digest_file} is missing")
    elif digest_file.read_text() != _digest_refcache(toolchain.refcache):
        reasons.append("refcache contents differ from the recorded digest")
    if reasons:
        return False, tuple(reasons)
    example = toolchain.template_home / "example" / EXAMPLE_DRAFT
    scratch = tools / "verify"
    if scratch.exists():
        shutil.rmtree(scratch)
    repo = scratch / "example"
    repo.mkdir(parents=True)
    shutil.copyfile(example, repo / EXAMPLE_DRAFT)
    shutil.copyfile(toolchain.template_home / "template" / "Makefile", repo / "Makefile")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "ai-rfc-harness")
    _git(repo, "config", "user.email", "ai-rfc-harness@localhost")
    _git(repo, "add", EXAMPLE_DRAFT, "Makefile")
    _git(repo, "commit", "-q", "-m", "example", date="2026-08-26T00:00:00+00:00")
    digests = []
    for attempt in ("first", "second"):
        report = build(repo, toolchain=toolchain, out=scratch / attempt, targets=("txt",), date=VERIFY_DATE, runner=runner)
        if report.exit_code != 0 or report.findings:
            reasons.append(f"the example did not build offline ({attempt}): {'; '.join(report.findings) or report.exit_code}")
            return False, tuple(reasons)
        digests.append({name: entry["sha256"] for name, entry in report.outputs.items()})
    if digests[0] != digests[1]:
        reasons.append("two offline builds of the example differ")
    return not reasons, tuple(reasons)
```

(`_run_git` and `_git` are `workspace.py`'s helpers; `_git` accepts `date=`. `XML2RFC_BASE_OPTS` is imported for the docstring's reader only — remove the import if flake8 flags it.)

- [ ] **Step 4: The campaign gate and the session env**

`ai_rfc/experiment/config.py`: add `toolchain: Path | None = None` to `CampaignConfig` and `toolchain: str | None = None`, `toolchain_sha256: str | None = None`, `template_home: str | None = None` to `Campaign` (all with defaults, after `session_mode`, so old `campaign.json` files load). In `init_campaign`, after the arms check:

```python
    if config.toolchain is None:
        raise ExperimentError(
            "a campaign needs a verified toolchain: run `experiment toolchain "
            "provision` once, then pass --toolchain"
        )
    ok, reasons = toolchain_module.verify(config.toolchain)
    if not ok:
        raise ExperimentError(f"toolchain verify failed: {'; '.join(reasons)}")
    toolchain_record = json.loads(config.toolchain.read_text())
```

and in the `Campaign(...)` construction: `toolchain=str(config.toolchain), toolchain_sha256=hashlib.sha256(config.toolchain.read_bytes()).hexdigest(), template_home=toolchain_record.get("template_home")`. Import `from . import toolchain as toolchain_module` (module import, so the tests' monkeypatch of `toolchain_module.verify` takes effect) and `hashlib`.

`ai_rfc/experiment/runner.py` `build_env`: after `"AI_RFC_WORKSPACE"`, add `**({"AI_RFC_TOOLCHAIN": campaign.toolchain} if campaign.toolchain else {})`. `prepare_run_argv`: pass `toolchain=Path(campaign.toolchain) if campaign.toolchain else None` into `mcp_config`. `ai_rfc/experiment/arms.py` `mcp_config(*, python, workspace, toolchain: Path | None = None)`: add `"AI_RFC_TOOLCHAIN": str(toolchain)` to the server env when given.

`ai_rfc/experiment/cli.py`: `campaign init` gains `--toolchain` (type `Path`, default `<root>/tools/toolchain.json` resolved after `_add_root`, help "toolchain.json from `experiment toolchain provision`"); pass it into `CampaignConfig`. New top-level command:

```python
    toolchain = commands.add_parser("toolchain", help="The shared Internet-Draft toolchain.")
    toolchain_verbs = toolchain.add_subparsers(dest="verb", required=True)
    provision = toolchain_verbs.add_parser("provision", help="Install it once (networked).")
    _add_root(provision)
    provision.add_argument("--template", default=TEMPLATE_URL, help="Template repository (default: %(default)s).")
    provision.add_argument("--template-commit", default=TEMPLATE_COMMIT, help="Commit to pin (default: %(default)s).")
    verify_cmd = toolchain_verbs.add_parser("verify", help="Re-check it offline.")
    _add_root(verify_cmd)
```

with dispatch printing the record path on success and, for `verify`, `ok` / one reason per line, exit 0 or 1.

- [ ] **Step 5: Run the experiment tests**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment -n auto`
Expected: all PASS. Existing campaign fixtures construct `CampaignConfig` without `toolchain` and call `init_campaign` — they now need a toolchain: give the shared campaign fixture in `tests/experiment/conftest.py` (or the module-level fixture the failing tests use) a `toolchain=` pointing at a record file written by the fixture, with `toolchain_module.verify` monkeypatched to `(True, ())`. Do this in the conftest so every campaign fixture gets it once.

- [ ] **Step 6: Run the real provisioning once (operator step, network, sandbox off)**

The 2026-09-03 hand-provisioned toolchain lives at `~/ai-rfc-experiments/tools`. `provision` refuses an existing record, so prove the command on a scratch root: `cd $AIRFC && SSLKEYLOGFILE= $PY -m ai_rfc.experiment toolchain provision --root /tmp/claude/tc-probe` then `… toolchain verify --root /tmp/claude/tc-probe`. Expected: both exit 0; `verify` prints `ok`. Then replace the hand-made record: move `~/ai-rfc-experiments/tools` to `~/ai-rfc-experiments/tools.manual-2026-09-03` and re-run `provision --root ~/ai-rfc-experiments` so the production record is the command's own output. Keep the manual copy until SP7d's replay has run.

- [ ] **Step 7: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment tests/experiment && $PY -m flake8 --max-line-length=88 ai_rfc/experiment tests/experiment && $PY -m mypy --follow-imports=silent ai_rfc/experiment/toolchain.py ai_rfc/experiment/config.py
git status --short
git add ai_rfc/experiment/toolchain.py ai_rfc/experiment/config.py ai_rfc/experiment/runner.py ai_rfc/experiment/arms.py ai_rfc/experiment/cli.py tests/experiment/test_toolchain.py tests/experiment/test_config.py tests/experiment/test_runner.py tests/experiment/test_arms.py tests/experiment/conftest.py
git commit -m "feat: provision and verify one shared toolchain, and refuse campaigns without it"
```

---

### Task 6: The draft repository as a real template adopter, with sealed references

**Files:**
- Modify: `ai_rfc/experiment/workspace.py` (`Target.references`, `AIOQUIC`/`MARK`, `scaffold_draft`, remove `TEMPLATE_STRIP`/`_strip_template`, `prepare(..., toolchain=)`, the pristine record), `ai_rfc/experiment/cli.py` (`workspace prepare --toolchain`)
- Test: `tests/experiment/conftest.py` (`template_repo` fixture), `tests/experiment/test_workspace.py`

**Interfaces:**
- Consumes: `ai_rfc.draft.build.load_toolchain` (Task 1) for the refcache location; the template's `template/{Makefile,.gitignore,.editorconfig}` (present at the pin).
- Produces: `Target.references: tuple[str, ...] = ()`; `scaffold_draft(dest, target, *, template, template_commit) -> str` writing the adopter layout (`Makefile`, `.gitignore`, `.editorconfig`, `draft-<name>.md`); `prepare(target, *, root, toolchain: Path | None = None, template=…, template_commit=…) -> Path` writing `<pristine>/references.yaml` and `<pristine>/refcache/`; `pristine.json` keys `scaffold_layout`, `references`, `refcache_sha256`, `toolchain_sha256`, `template_home` (and no `template_stripped`); constants `REFERENCES_FILE = "references.yaml"`, `REFCACHE_DIR = "refcache"`. Task 7 reuses the adopter file list; `draft build` (Task 4's core) picks up `<workspace>/refcache` automatically.

**Why this shape.** The template's `Makefile` expects a library at `LIBDIR` and `draft build` names it explicitly, so a draft repository needs only the three adopter files — no library copy, no `lib` symlink (which `copy_workspace` would dereference and `git add -A` would commit). The references a target may cite are decided at `prepare`, copied out of the toolchain's seeded cache, and sealed into the pristine digest: a build then never asks the network, and a reference the agent invents is a build finding rather than a fetch.

- [ ] **Step 1: Extend the template fixture**

In `tests/experiment/conftest.py`, replace the body of `template_repo` so the stand-in has the adopter files and the example the real template has (keep the fixed commit date):

```python
@pytest.fixture
def template_repo(tmp_path: Path) -> tuple[str, str]:
    """A local stand-in for auto-i-d-template: library root plus template/ and example/."""
    from ai_rfc.server.testing import git

    repo = tmp_path / "template"
    (repo / "template").mkdir(parents=True)
    (repo / "example").mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "main.mk").write_text("txt::\n\t@echo build\n")
    (repo / "CLAUDE.md").write_text("template agent notes\n")
    (repo / "template" / "Makefile").write_text("LIBDIR := lib\ninclude $(LIBDIR)/main.mk\n")
    (repo / "template" / ".gitignore").write_text("*.txt\n*.html\n*.xml\n/versioned\n")
    (repo / "template" / ".editorconfig").write_text("root = true\n")
    (repo / "example" / "draft-todo-yourname-protocol.md").write_text(
        "---\ntitle: TODO\ndocname: draft-todo-yourname-protocol-latest\n---\n\n--- abstract\n\nTODO\n\n--- middle\n\n# Introduction\n\nTODO\n\n--- back\n"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "template", date="2026-01-01T00:00:09+00:00")
    return str(repo), git(repo, "rev-parse", "HEAD")
```

- [ ] **Step 2: Write the failing workspace tests**

In `tests/experiment/test_workspace.py`, replace `test_scaffold_strips_agent_files_and_seeds_the_draft` with:

```python
def test_scaffold_writes_the_adopter_layout_and_seeds_the_draft(template_repo, tmp_path):
    template, commit = template_repo
    dest = tmp_path / "draft"
    head = scaffold_draft(
        dest, fixture_target(tmp_path), template=template, template_commit=commit
    )
    body = (dest / "draft-test-fixture.md").read_text()
    assert (dest / "Makefile").read_text() == "LIBDIR := lib\ninclude $(LIBDIR)/main.mk\n"
    assert (dest / ".editorconfig").exists()
    ignored = (dest / ".gitignore").read_text().splitlines()
    assert "lib" in ignored and ".venv" in ignored and "draft-*" not in ignored
    assert not (dest / "main.mk").exists() and not (dest / "CLAUDE.md").exists()
    assert not (dest / "template").exists() and not (dest / "example").exists()
    assert "docname: draft-test-fixture-latest" in body
    assert 'title: "Fixture"' in body and "specification of fixture" in body
    assert "`ai_rfc:" not in body
    assert sorted(p.name for p in dest.iterdir() if p.name != ".git") == [
        ".editorconfig", ".gitignore", "Makefile", "draft-test-fixture.md"
    ]
    assert git(dest, "log", "--oneline").count("\n") == 0
    assert git(dest, "config", "user.name") == "ai-rfc-harness"
    assert head == git(dest, "rev-parse", "HEAD")
```

and add, using a toolchain record fixture:

```python
@pytest.fixture
def toolchain_record(tmp_path: Path) -> Path:
    tools = tmp_path / "tools"
    cache = tools / ".refcache"
    cache.mkdir(parents=True)
    for number in ("2119", "8174", "9000"):
        (cache / f"reference.RFC.{number}.xml").write_text(f"<reference anchor='RFC{number}'/>\n")
    record = tools / "toolchain.json"
    record.write_text(json.dumps({"template_home": str(tools / "i-d-template"), "refcache": {"dir": str(cache)}, "make": {"path": "/usr/bin/make"}, "python": {"venv": "/v"}, "ruby": {"bin_dir": "/r", "gem_path": "/g", "kramdown_rfc": "/k"}, "node": {"bin_dir": "/n", "idnits": "/i"}}))
    return record


def test_prepare_seals_the_targets_references_into_the_workspace(
    fixture_workspace, template_repo, tmp_path, toolchain_record
):
    from dataclasses import replace

    template, commit = template_repo
    target = replace(fixture_target(fixture_workspace), references=("RFC9000",))
    pristine = prepare(
        target, root=tmp_path / "root", toolchain=toolchain_record, template=template, template_commit=commit
    )
    assert (pristine / "references.yaml").read_text() == "references:\n- RFC9000\n"
    assert (pristine / "refcache" / "reference.RFC.9000.xml").exists()
    assert not (pristine / "refcache" / "reference.RFC.2119.xml").exists()
    record = json.loads((pristine / "pristine.json").read_text())
    assert record["scaffold_layout"] == "adopter" and record["references"] == ["RFC9000"]
    assert record["toolchain_sha256"] == hashlib.sha256(toolchain_record.read_bytes()).hexdigest()
    assert "template_stripped" not in record
    verify_digest(pristine)


def test_prepare_refuses_a_reference_the_toolchain_never_cached(
    fixture_workspace, template_repo, tmp_path, toolchain_record
):
    from dataclasses import replace

    template, commit = template_repo
    target = replace(fixture_target(fixture_workspace), references=("RFC9999",))
    with pytest.raises(ExperimentError) as excinfo:
        prepare(target, root=tmp_path / "root", toolchain=toolchain_record, template=template, template_commit=commit)
    assert "RFC9999" in str(excinfo.value) and "toolchain provision" in str(excinfo.value)


def test_prepare_with_references_needs_a_toolchain(fixture_workspace, template_repo, tmp_path):
    from dataclasses import replace

    template, commit = template_repo
    target = replace(fixture_target(fixture_workspace), references=("RFC9000",))
    with pytest.raises(ExperimentError) as excinfo:
        prepare(target, root=tmp_path / "root", template=template, template_commit=commit)
    assert "--toolchain" in str(excinfo.value)
```

(`fixture_workspace`, `fixture_target`, `verify_digest` already exist in that module's imports/conftest; add `import hashlib` if missing. Remove `template_stripped` assertions elsewhere in the file if any exist — grep.)

- [ ] **Step 3: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_workspace.py -v`
Expected: the adopter test FAILS (`main.mk` exists, `Makefile` content differs), the references tests FAIL with `TypeError: unexpected keyword 'references'`/`'toolchain'`.

- [ ] **Step 4: Targets, scaffold, prepare**

In `ai_rfc/experiment/workspace.py`:

1. `Target` gains `references: tuple[str, ...] = ()` (last field, defaulted). `AIOQUIC` sets `references=("RFC9000", "RFC9001", "RFC9002", "RFC9114", "RFC9204", "RFC8446", "RFC5280", "RFC6125")`; `MARK` sets `references=("RFC9110", "RFC8259")` (HTTP and JSON — what its draft names; JSON-RPC 2.0 has no RFC and stays an inline reference).
2. Delete `TEMPLATE_STRIP` and `_strip_template`. Add:

```python
ADOPTER_FILES = ("Makefile", ".gitignore", ".editorconfig")
EXTRA_IGNORES = ("lib", ".venv", ".gems", "node_modules", "Gemfile.lock", ".refcache")
REFERENCES_FILE = "references.yaml"
REFCACHE_DIR = "refcache"
```

3. Rewrite `scaffold_draft` (same signature, same return, same docstring intent):

```python
    if dest.exists():
        raise ExperimentError(f"{dest} exists; a draft is scaffolded once")
    with tempfile.TemporaryDirectory(prefix="i-d-template-") as staging:
        library = Path(staging) / "template"
        cloned = _run_git("clone", "-q", template, str(library))
        if cloned.returncode != 0:
            raise ExperimentError(f"cloning {template} failed: {cloned.stderr.strip()}")
        _git(library, "checkout", "-q", template_commit)
        dest.mkdir(parents=True)
        for name in ADOPTER_FILES:
            source = library / "template" / name
            if not source.exists():
                raise ExperimentError(f"{template}@{template_commit[:12]} has no template/{name}")
            shutil.copyfile(source, dest / name)
    ignored = [
        line
        for line in (dest / ".gitignore").read_text().splitlines()
        if line.strip() and line.strip() != "draft-*"
    ]
    (dest / ".gitignore").write_text("\n".join([*ignored, *EXTRA_IGNORES]) + "\n")
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
    _git(dest, "commit", "-q", "-m", "adopt the Internet-Draft template", date=PINNED_DATE)
    return _git(dest, "rev-parse", "HEAD")
```

(`import tempfile`; the docstring's first line becomes "Clone the template at its pin, copy its adopter files, seed the draft.")

4. `prepare` gains `toolchain: Path | None = None`. After `scaffold_draft(...)` and before the record:

```python
    refcache_sha256 = None
    toolchain_sha256 = None
    template_home = None
    if target.references:
        if toolchain is None:
            raise ExperimentError(
                f"{target.name} declares references; pass --toolchain so they can be "
                "sealed into the workspace"
            )
        record_toolchain = load_toolchain(toolchain)
        cache = pristine / REFCACHE_DIR
        cache.mkdir()
        missing = []
        for reference in target.references:
            name = f"reference.RFC.{reference[3:]}.xml" if reference.startswith("RFC") else f"reference.{reference}.xml"
            source = record_toolchain.refcache / name
            if not source.exists():
                missing.append(reference)
                continue
            shutil.copyfile(source, cache / name)
        if missing:
            raise ExperimentError(
                f"the toolchain never cached {', '.join(missing)}; add them to the seed "
                "list and re-run `experiment toolchain provision`"
            )
        refcache_sha256 = hashlib.sha256(
            b"".join((cache / p.name).read_bytes() for p in sorted(cache.iterdir()))
        ).hexdigest()
        toolchain_sha256 = hashlib.sha256(toolchain.read_bytes()).hexdigest()
        template_home = str(record_toolchain.template_home)
    (pristine / REFERENCES_FILE).write_text(
        "references:\n" + "".join(f"- {reference}\n" for reference in target.references)
    )
```

and in the record dict replace `"template_stripped": list(TEMPLATE_STRIP)` with `"scaffold_layout": "adopter", "references": list(target.references), "refcache_sha256": refcache_sha256, "toolchain_sha256": toolchain_sha256, "template_home": template_home`. Import `hashlib` and `from ai_rfc.draft.build import load_toolchain`. `write_digest` already walks every file, so `references.yaml` and `refcache/` seal into `pristine.sha256` with no further change.

5. `ai_rfc/experiment/cli.py` `workspace prepare`: add `--toolchain` (type `Path`, default `<root>/tools/toolchain.json` when that file exists, else `None`) and pass it to `prepare`.

- [ ] **Step 5: Run the experiment tests**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment -n auto`
Expected: all PASS. If `test_scaffold_is_byte_deterministic` fails, the culprit is the temp-directory name leaking into a file — it must not; every written file's content is independent of the staging path.

- [ ] **Step 6: Lint and commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment tests/experiment && $PY -m flake8 --max-line-length=88 ai_rfc/experiment tests/experiment && $PY -m mypy --follow-imports=silent ai_rfc/experiment/workspace.py
git status --short
git add ai_rfc/experiment/workspace.py ai_rfc/experiment/cli.py tests/experiment/conftest.py tests/experiment/test_workspace.py
git commit -m "feat: scaffold drafts as template adopters and seal their references"
```

---

### Task 7: `experiment workspace migrate-draft` — an old library-root draft becomes an adopter in one commit

**Files:**
- Modify: `ai_rfc/experiment/workspace.py` (`_write_adopter_files` shared with `scaffold_draft`, `migrate_draft`), `ai_rfc/experiment/cli.py` (`workspace migrate-draft`)
- Test: `tests/experiment/test_workspace.py`

**Interfaces:**
- Consumes: `ADOPTER_FILES`, `EXTRA_IGNORES`, `_run_git`, `_git`, `PINNED_DATE` (Task 6).
- Produces: `migrate_draft(workspace: Path, *, template: str = TEMPLATE_URL, template_commit: str = TEMPLATE_COMMIT) -> str` (the new HEAD); refuses a dirty tree and an already-migrated draft. SP7d's replay runs it on the copy of the finished MARK A1 workspace before `reseal`.

**Why this shape.** The 37-cluster MARK draft was scaffolded as a copy of the template's library root (45 files: `*.mk`, `*.sh`, `doc/`, `docker/`, …). Its tags must keep verifying — the gate lists each tag's own tree, so history is untouched — while HEAD moves to the adopter layout in exactly one commit that a reviewer can read.

- [ ] **Step 1: Write the failing tests**

Append to `tests/experiment/test_workspace.py`:

```python
def _library_root_draft(root: Path) -> Path:
    """A draft scaffolded the old way: the template's library files at the root."""
    from ai_rfc.server.testing import git as g

    draft = root / "draft"
    (draft / "doc").mkdir(parents=True)
    (draft / "template").mkdir()
    g(draft, "init", "-q", "-b", "main")
    g(draft, "config", "user.email", "t@t")
    g(draft, "config", "user.name", "t")
    (draft / "main.mk").write_text("txt::\n")
    (draft / "deps.mk").write_text("deps::\n")
    (draft / "doc" / "TIPS.md").write_text("tips\n")
    (draft / "template" / "Makefile").write_text("LIBDIR := lib\ninclude $(LIBDIR)/main.mk\n")
    (draft / ".gitignore").write_text("*.txt\n")
    (draft / "draft-test-fixture.md").write_text("---\ntitle: T\n---\n\n--- middle\n\n# Introduction\n\nOld.\n")
    g(draft, "add", "-A")
    g(draft, "commit", "-q", "-m", "scaffold from auto-i-d-template", date="2026-01-01T00:00:09+00:00")
    g(draft, "tag", "-a", "draft-test-fixture-00", "-m", "00")
    return draft


def test_migrate_draft_adopts_the_layout_in_one_commit_and_keeps_tags(template_repo, tmp_path):
    from ai_rfc.experiment.workspace import migrate_draft

    template, commit = template_repo
    draft = _library_root_draft(tmp_path / "ws")
    before = git(draft, "rev-parse", "HEAD")
    head = migrate_draft(tmp_path / "ws", template=template, template_commit=commit)
    assert head != before and git(draft, "rev-parse", "HEAD") == head
    assert git(draft, "log", "--format=%s", "-1").strip() == "adopt the Internet-Draft template layout"
    assert git(draft, "log", "--oneline").count("\n") == 1
    assert sorted(git(draft, "ls-files").split()) == [".editorconfig", ".gitignore", "Makefile", "draft-test-fixture.md"]
    assert (draft / "Makefile").read_text() == "LIBDIR := lib\ninclude $(LIBDIR)/main.mk\n"
    assert "lib" in (draft / ".gitignore").read_text().splitlines()
    assert not (draft / "main.mk").exists() and not (draft / "doc").exists()
    assert "main.mk" in git(draft, "ls-tree", "--name-only", "draft-test-fixture-00")
    assert git(draft, "status", "--porcelain") == ""


def test_migrate_draft_refuses_a_dirty_or_already_migrated_draft(template_repo, tmp_path):
    from ai_rfc.experiment.workspace import migrate_draft

    template, commit = template_repo
    draft = _library_root_draft(tmp_path / "ws")
    (draft / "draft-test-fixture.md").write_text("edited\n")
    with pytest.raises(ExperimentError) as excinfo:
        migrate_draft(tmp_path / "ws", template=template, template_commit=commit)
    assert "uncommitted" in str(excinfo.value)
    git(draft, "checkout", "--", "draft-test-fixture.md")
    migrate_draft(tmp_path / "ws", template=template, template_commit=commit)
    with pytest.raises(ExperimentError) as excinfo:
        migrate_draft(tmp_path / "ws", template=template, template_commit=commit)
    assert "already" in str(excinfo.value)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_workspace.py -k migrate -v`
Expected: FAIL with `ImportError: cannot import name 'migrate_draft'`.

- [ ] **Step 3: Factor the adopter files out of `scaffold_draft` and add `migrate_draft`**

In `ai_rfc/experiment/workspace.py`, move the clone-and-copy part of Task 6's `scaffold_draft` into a helper both functions call:

```python
def _write_adopter_files(dest: Path, *, template: str, template_commit: str) -> None:
    """Copy the template's adopter files into ``dest`` and extend its ignores."""
    with tempfile.TemporaryDirectory(prefix="i-d-template-") as staging:
        library = Path(staging) / "template"
        cloned = _run_git("clone", "-q", template, str(library))
        if cloned.returncode != 0:
            raise ExperimentError(f"cloning {template} failed: {cloned.stderr.strip()}")
        _git(library, "checkout", "-q", template_commit)
        for name in ADOPTER_FILES:
            source = library / "template" / name
            if not source.exists():
                raise ExperimentError(f"{template}@{template_commit[:12]} has no template/{name}")
            shutil.copyfile(source, dest / name)
    ignored = [
        line
        for line in (dest / ".gitignore").read_text().splitlines()
        if line.strip() and line.strip() != "draft-*"
    ]
    (dest / ".gitignore").write_text("\n".join([*ignored, *EXTRA_IGNORES]) + "\n")


def migrate_draft(
    workspace: Path, *, template: str = TEMPLATE_URL, template_commit: str = TEMPLATE_COMMIT
) -> str:
    """Move a library-root draft repository to the adopter layout in one commit.

    Every tracked file except the draft file is removed and the three adopter
    files are added; tags are untouched, so every earlier revision still lists
    the tree it was gated against.

    Args:
        workspace: The workspace whose ``draft/`` to migrate.
        template: Template clone source.
        template_commit: The commit the adopter files are taken from.

    Returns:
        The draft repository's new HEAD.

    Raises:
        ExperimentError: If the draft is dirty, already an adopter, or has no
            single draft file.
    """
    draft = workspace / "draft"
    if _git(draft, "status", "--porcelain"):
        raise ExperimentError(f"{draft} has uncommitted changes; commit or discard them first")
    tracked = _git(draft, "ls-files").splitlines()
    drafts = [name for name in tracked if name.startswith("draft-") and name.endswith(".md")]
    if len(drafts) != 1:
        raise ExperimentError(f"{draft} tracks {len(drafts)} draft-*.md files; expected one")
    if "main.mk" not in tracked and "Makefile" in tracked:
        raise ExperimentError(f"{draft} is already an adopter; nothing to migrate")
    for name in tracked:
        if name != drafts[0]:
            _git(draft, "rm", "-q", "--", name)
    _write_adopter_files(draft, template=template, template_commit=template_commit)
    _git(draft, "add", "--", *ADOPTER_FILES)
    _git(draft, "config", "user.name", HARNESS_NAME)
    _git(draft, "config", "user.email", HARNESS_EMAIL)
    _git(draft, "commit", "-q", "-m", "adopt the Internet-Draft template layout", date=PINNED_DATE)
    return _git(draft, "rev-parse", "HEAD")
```

`scaffold_draft` becomes: refuse an existing `dest`; `dest.mkdir(parents=True)`; `(dest / ".gitignore").write_text("")` is NOT needed — `_write_adopter_files` copies the template's `.gitignore` first, then rewrites it; write the skeleton; init, add, commit as before. (`git rm` leaves the now-empty `doc/` and `template/` directories gone, since git removes empty parents.)

CLI: `workspace migrate-draft WORKSPACE [--template] [--template-commit]` with `_add_root`-free arguments (the workspace path is explicit), printing the new HEAD.

- [ ] **Step 4: Run, lint, commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_workspace.py -v` — Expected: all PASS.

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment/workspace.py ai_rfc/experiment/cli.py tests/experiment/test_workspace.py && $PY -m flake8 --max-line-length=88 ai_rfc/experiment/workspace.py ai_rfc/experiment/cli.py tests/experiment/test_workspace.py
git status --short
git add ai_rfc/experiment/workspace.py ai_rfc/experiment/cli.py tests/experiment/test_workspace.py
git commit -m "feat: migrate a library-root draft to the adopter layout in one commit"
```

---

### Task 8: Freeze the task prompt a per-cluster session actually runs

**Files:**
- Modify: `ai_rfc/experiment/config.py` (`TASK_TEMPLATE_FILE`, `render_task(template=)`, `init_campaign`, `Campaign.task_template`), `ai_rfc/experiment/per_cluster.py` (the `render_task` call and the `sessions.jsonl` row), `ai_rfc/experiment/runner.py` (`prepare_run_argv(prompt_file=)`, the `prompt.md` record in `launch`)
- Test: `tests/experiment/test_config.py`, `tests/experiment/test_per_cluster.py`, `tests/experiment/test_runner.py`

**Interfaces:**
- Consumes: `Campaign.prompts_dir`, `Campaign.session_mode`.
- Produces: `render_task(window: tuple[int, int], template: Path = TASK_TEMPLATE) -> str`; `Campaign.task_template -> Path` (`prompts_dir / "task.tmpl.md"`); `prompt_sha256["task.tmpl.md"]`; `prepare_run_argv(campaign, ref, task=None, budget_usd=None, prompt_file=None)`; `sessions.jsonl` rows carry `task_template`. SP7c's consolidation sessions pass their own `prompt_file`.

**Why this shape.** `init_campaign` freezes `task.md` and records its digest, but a per-cluster session renders its one-ordinal task from the *source* template on every launch, so the frozen digest describes a prompt no session ran and an edit to the source changes a running campaign silently. Freezing the template itself, and rendering from the frozen copy, makes the record true; `prompt.md` stops claiming a whole-window task that per-cluster sessions never received.

- [ ] **Step 1: Write the failing tests**

Append to `tests/experiment/test_config.py`:

```python
def test_render_task_reads_the_template_it_is_given(tmp_path):
    template = tmp_path / "task.tmpl.md"
    template.write_text("Ordinals $low..$high, FROZEN COPY.\n")
    assert render_task((3, 3), template=template) == "Ordinals 3..3, FROZEN COPY.\n"


def test_init_freezes_the_task_template_beside_the_rendering(pristine, tmp_path, plugin_root):
    from ai_rfc.experiment.config import TASK_TEMPLATE

    campaign = init_campaign(_init(tmp_path, pristine, plugin_root))
    frozen = campaign.prompts_dir / "task.tmpl.md"
    assert frozen.read_bytes() == TASK_TEMPLATE.read_bytes()
    assert campaign.task_template == frozen
    assert campaign.prompt_sha256["task.tmpl.md"] == hashlib.sha256(frozen.read_bytes()).hexdigest()
    assert "task.md" in campaign.prompt_sha256
```

In `tests/experiment/test_per_cluster.py`, next to the test that uses the `capture` stub for `prepare_run_argv` (grep `def capture(campaign, ref, task=None, budget_usd=None)` and read that test to reuse its setup), add:

```python
def test_per_cluster_sessions_render_from_the_frozen_template(per_cluster_campaign, monkeypatch):
    """Editing the source template after init must not change a running campaign."""
    from ai_rfc.experiment import per_cluster

    frozen = per_cluster_campaign.task_template
    frozen.write_text(frozen.read_text() + "\nFROZEN-MARKER $low\n")
    seen = []

    def capture(campaign, ref, task=None, budget_usd=None, prompt_file=None):
        seen.append(task)
        return ["true"]

    monkeypatch.setattr(per_cluster, "prepare_run_argv", capture)
    _stub_spawn(per_cluster, monkeypatch, sessions_per_cluster=1)
    ref = run_ref(per_cluster_campaign, "A1")
    copy_workspace(per_cluster_campaign.pristine_dir, ref.workspace)
    per_cluster.run_per_cluster(per_cluster_campaign, ref, report=lambda _: None)
    assert seen and all("FROZEN-MARKER 2" in task for task in seen)
    row = json.loads((ref.run_dir / "sessions.jsonl").read_text().splitlines()[0])
    assert row["task_template"] == str(frozen)
```

(`run_ref`, `copy_workspace`, `_stub_spawn` and `per_cluster_campaign` are that module's existing names — confirm each with grep and adapt the setup lines to how the neighbouring loop tests build a run; the assertion that matters is the `FROZEN-MARKER` one.)

In `tests/experiment/test_runner.py`, add beside `test_launch_streams_events_and_records_status`:

```python
def test_per_cluster_prompt_record_names_the_template_not_a_whole_window_task(
    per_cluster_campaign, write_scenario
):
    write_scenario(per_cluster_campaign.profile_dir, "A1", {"arm": "A", "cost": 1.0, "steps": COMPLETE_STEPS})
    ref = run_ref(per_cluster_campaign, "A1")
    copy_workspace(per_cluster_campaign.pristine_dir, ref.workspace)
    launch(per_cluster_campaign, ref, report=lambda _: None)
    prompt = (ref.run_dir / "prompt.md").read_text()
    assert "rendered per session from prompts/task.tmpl.md" in prompt
    assert "ordinals 2 through 2" not in prompt and "$low" in prompt
```

(`per_cluster_campaign`, `COMPLETE_STEPS`, `run_ref`, `copy_workspace` come from `test_per_cluster.py`/`conftest.py`; import them the way `test_runner.py` already imports its helpers.)

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_config.py tests/experiment/test_per_cluster.py tests/experiment/test_runner.py -v -k "template or prompt_record"`
Expected: FAIL — `render_task() got an unexpected keyword argument 'template'`, `AttributeError: task_template`, and the runner assertion on `prompt.md`.

- [ ] **Step 3: Freeze the template**

`ai_rfc/experiment/config.py`:

```python
TASK_TEMPLATE_FILE = "task.tmpl.md"


def render_task(window: tuple[int, int], template: Path = TASK_TEMPLATE) -> str:
    """The task prompt, identical across arms, with the window spelled out.

    Args:
        window: Inclusive first and last cluster ordinals.
        template: The template to render; a campaign passes its frozen copy so
            a session's prompt cannot drift from the campaign record.

    Returns:
        The rendered prompt.
    """
    low, high = window
    return string.Template(template.read_text()).substitute(low=low, high=high)
```

In `init_campaign`, after writing `task.md`:

```python
    frozen_template = prompts_dir / TASK_TEMPLATE_FILE
    frozen_template.write_bytes(TASK_TEMPLATE.read_bytes())
    prompt_sha256[TASK_TEMPLATE_FILE] = _sha256(frozen_template.read_text())
```

On `Campaign`, add:

```python
    @property
    def task_template(self) -> Path:
        """The frozen task template every per-cluster session renders from."""
        return self.prompts_dir / TASK_TEMPLATE_FILE
```

`ai_rfc/experiment/per_cluster.py`: replace `task = render_task((ordinal, ordinal))` with

```python
        template = campaign.task_template if campaign.task_template.exists() else TASK_TEMPLATE
        task = render_task((ordinal, ordinal), template=template)
```

(import `TASK_TEMPLATE` from `.config`; the fallback keeps campaigns frozen before this field readable), and add `"task_template": str(template)` to the `sessions.jsonl` row.

`ai_rfc/experiment/runner.py`: `prepare_run_argv` gains `prompt_file: Path | None = None` and passes `prompt_file=prompt_file or campaign.prompts_dir / f"arm-{ref.arm}.md"` to `claude_argv`. In `launch`, replace the `PROMPT_FILE` write with:

```python
    if campaign.session_mode == "per-cluster":
        task_record = (
            "(per-cluster mode: the task is rendered per session from "
            "prompts/task.tmpl.md for one ordinal; each session's rendered text is "
            "in sessions.jsonl under argv)\n\n"
            + campaign.task_template.read_text()
        )
    else:
        task_record = (campaign.prompts_dir / "task.md").read_text()
    (ref.run_dir / PROMPT_FILE).write_text(
        (campaign.prompts_dir / f"arm-{ref.arm}.md").read_text() + "\n\n---\n\n" + task_record
    )
```

- [ ] **Step 4: Run, lint, commit**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment -n auto` — Expected: all PASS.

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment tests/experiment && $PY -m flake8 --max-line-length=88 ai_rfc/experiment tests/experiment
git status --short
git add ai_rfc/experiment/config.py ai_rfc/experiment/per_cluster.py ai_rfc/experiment/runner.py tests/experiment/test_config.py tests/experiment/test_per_cluster.py tests/experiment/test_runner.py
git commit -m "fix: freeze the task template a per-cluster session renders from"
```

---

### Task 9: What a specification looks like — the build step in the loop, a full I-D skeleton, and the skills

**Files:**
- Modify: `ai_rfc/experiment/prompts/loop.tmpl.md` (steps 6 and 8), `ai_rfc/experiment/prompts/draft-skeleton.md` (whole file), `ai_rfc/experiment/render.py` (`SLOT_TABLES` × 4, `NEUTRAL_TEXTS`, `SKILL_FRONTMATTER` allowed-tools), `plugins/ai-rfc/skills/ai-rfc-rfc-style/SKILL.md` (whole file), `plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md` (regenerated by `experiment render`)
- Create: `plugins/ai-rfc/skills/ai-rfc-rfc-style/references/keyword-policy.md`, `plugins/ai-rfc/skills/ai-rfc-figures/SKILL.md`
- Test: `tests/experiment/test_render.py`, `tests/experiment/test_workspace.py` (skeleton assertions), `tests/substrate/draft/test_lint.py` (the skeleton lints as intended)

**Interfaces:**
- Consumes: the `draft_build` tool/verb names (Task 4); `render_loop`/`arm_prompt`/`write_plugin_skill`; `string.Template` substitution of the skeleton (`$title`, `$abbrev`, `$draft_name`, `$target`; every other `$` must be `$$`); the lint's `STUB_ABSTRACT_MARKER` sentence (Task 2) and required sections.
- Produces: slot `{{draft_build}}` in all four tables; `NEUTRAL_TEXTS` with five entries; a skeleton whose abstract still carries the stub marker, whose middle has the sections `Introduction`, `Conventions and Definitions`, `Architecture Overview`, `Data Model and Structures`, `Protocol Operation`, `Configuration and Defaults`, `Error Handling`, `Observed Accidental Behaviour`, `Security Considerations`, `IANA Considerations`, and whose back has `Change Log`, `Implementation Notes`, `Open Questions`, `Acknowledgements`. SP7b adds the structures step; SP7c adds the consolidation prompt and the editorial skill.

**Why this shape.** The drafts were exactly as good as the rules they were given, and the rules said nothing about figures, references, section ownership or what an introduction is. The skeleton fixes the shape; the skills fix the judgement (MUST needs enforcing evidence; a figure's caption cites; cluster narration goes to the Change Log); the loop makes the build a step, not advice. The per-section guidance lives in kramdown `{::comment}` blocks, which render to nothing, so the skeleton compiles as written and lint sees every required section present but the abstract still a stub.

- [ ] **Step 1: Write the failing tests**

Append to `tests/experiment/test_render.py`:

```python
def test_every_arm_names_its_build_step():
    a, b, c, interactive = (render_loop(arm) for arm in ("A", "B", "C", "interactive"))
    assert "ai_rfc_draft_build" in a and "before" in a
    assert "ai_rfc draft-build" in b
    assert "not available in this arm" in c and "draft-build" not in c
    assert "ai_rfc_draft_build" in interactive and "ai_rfc draft-build" in interactive


def test_arm_prompt_bundles_the_keyword_policy_and_the_figures_skill(plugin_root):
    prompt = arm_prompt("A", plugin_root)
    assert "# Keyword policy" in prompt
    assert "# Figures in a reconstructed specification" in prompt
    assert "CLAUDE.md" not in prompt
```

Append to `tests/experiment/test_workspace.py` (the skeleton is rendered by `scaffold_draft`):

```python
def test_the_skeleton_compiles_as_a_stub_that_lint_recognises(template_repo, tmp_path):
    from ai_rfc.draft.lint import lint

    template, commit = template_repo
    dest = tmp_path / "draft"
    scaffold_draft(dest, fixture_target(tmp_path), template=template, template_commit=commit)
    text = (dest / "draft-test-fixture.md").read_text()
    assert "$" not in text
    assert "RFC2119:" not in text and "RFC8174:" not in text
    report = lint(text)
    assert report.abstract["is_stub"] is True
    assert report.sections["missing"] == []
    assert report.sections["present"][:3] == ["Introduction", "Conventions and Definitions", "Architecture Overview"]
    assert "Change Log" in report.sections["present"] and "Acknowledgements" in report.sections["present"]
    assert report.blocks["figures"] == 0 and report.citations["tokens"] == 0
    # The skeleton declares exactly one informative reference, inline. This
    # asserts against the real closing convention (`--- abstract`, never a bare
    # `---`) and is the cheapest check that `_parts` did not collapse `front`.
    assert report.references == {"normative": 0, "informative": 1, "inline": 1}
    # `## Reconstruction Method` legitimately names the unit of reconstruction,
    # so the bare `cluster` pattern fires twice; none of the shapes the detector
    # actually targets — ordinals, added/withdrawn counts, "this revision" — may.
    assert {entry["pattern"] for entry in report.narration} <= {"cluster"}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py tests/experiment/test_workspace.py -k "build_step or keyword_policy or skeleton" -v`
Expected: FAIL (`ai_rfc_draft_build` absent from the renderings; headings absent from the prompt; skeleton sections missing).

- [ ] **Step 3: The loop and its slot**

In `ai_rfc/experiment/prompts/loop.tmpl.md`, replace step 6 with:

```
6. **Decide spec relevance**:
   - Normative behaviour changed → update the draft per the RFC-style
     rules, citing the new/changed claims. Prose goes to the section that
     owns the behaviour (Protocol Operation, Data Model and Structures,
     Configuration and Defaults, Error Handling) — never to the
     Introduction, which describes the system, not the reconstruction. The
     keyword comes from the claim's level and the keyword policy.
   - Nothing normative → no prose edit; the revision entry will say so.
```

and step 8 with:

```
8. **Record, build and tag the revision**: {{revision_record}} — the tag
   `draft-<name>-NN` (two digits, monotone in cluster ordinal), the cluster
   id, an explicit `normative_change`, a one-line note. Commit any prose
   change ({{draft_commit}}), then **build** it: {{draft_build}}. Exit 0 with
   no findings is the bar before tagging — a failed stage names the line,
   a broken reference names a citation the sealed cache does not hold (cite
   it inline in the front matter instead). Then create the annotated tag
   ({{revision_tag}}). Every revision entry needs its tag, no-change
   revisions included.
```

In `ai_rfc/experiment/render.py`, add to every table:

```python
    # interactive
    "draft_build": (
        "`ai_rfc_draft_build()` or `ai_rfc draft-build` (the template's "
        "`make txt html lint idnits`, offline; the findings name the failed "
        "stage or the broken reference)"
    ),
    # C
    "draft_build": (
        "not available in this arm — skip this step and note it in the summary"
    ),
    # B
    "draft_build": "`ai_rfc draft-build` (exit 0 and no findings before the tag)",
    # A
    "draft_build": (
        "`ai_rfc_draft_build()` — exit 0 and no findings before the tag; "
        "`ai_rfc_revision_tag` runs it again and refuses on findings"
    ),
```

(Table `C` inherits `_RAW`; add the key to `_RAW` for the interactive table only if `C` should not — it should not, so put the interactive text in the `interactive` dict and the C text in the `C` dict, both explicitly.) Extend `NEUTRAL_TEXTS`:

```python
NEUTRAL_TEXTS = (
    ("skills", "ai-rfc-rfc-style", "SKILL.md"),
    ("skills", "ai-rfc-rfc-style", "references", "claim-citation.md"),
    ("skills", "ai-rfc-rfc-style", "references", "keyword-policy.md"),
    ("skills", "ai-rfc-figures", "SKILL.md"),
    ("skills", "ai-rfc-evidence-hygiene", "SKILL.md"),
)
```

and in `SKILL_FRONTMATTER`'s `allowed-tools`, replace the `python -m panther…` pattern with whatever SP1 made `RAW_PREFIX` (`Bash(python -m ai_rfc*)`) if SP1 did not already.

- [ ] **Step 4: The skeleton**

Replace `ai_rfc/experiment/prompts/draft-skeleton.md` with (every literal `$` is doubled; the four `$name` substitutions stay single):

````markdown
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
  SOURCE:
    title: "The $target implementation, as pinned in the reconstruction workspace"
    author:
      -
        org: "The $target developers"


--- abstract

This document reconstructs the specification of $target from its
implementation history. Each revision reflects the implementation as it
stood at one cluster of its development timeline; every normative statement
cites a claim in the accompanying evidence manifest, whose status is
adjudicated from anchored evidence rather than asserted.

{::comment}
Replace the paragraph above once the system is understood: what $target is,
what problem it solves, and who would implement this specification. The
sentence "Each revision reflects the implementation as it stood at one
cluster" is how the lint recognises an unwritten abstract.
{:/comment}


--- middle

# Introduction

{::comment}
What the system is and does, for a reader who has never seen it. Three
paragraphs at most. No cluster ordinals, no counts of statements added or
withdrawn — that history belongs in the Change Log appendix.
{:/comment}

## Scope

{::comment}
Which behaviours this document specifies and which it leaves out.
{:/comment}

## Reconstruction Method

This specification was reconstructed from the implementation's repository
history, one timeline cluster at a time. Each cluster's evidence was mined
into claims, each claim was anchored to code, decision records, papers,
interviews or test runs, and each claim's evidential status was adjudicated
from those anchors rather than asserted. Every normative statement below
cites the claim that supports it, and the manifest checkpointed beside each
revision is what the citation gate verifies those citations against.

## Organization

{::comment}
One sentence per major section, in order.
{:/comment}

# Conventions and Definitions

{::boilerplate bcp14-tagged}

Claim citations are backticked `ai_rfc` tokens that name a claim id in the
evidence manifest checkpointed beside this revision; the citation gate
verifies that every cited claim exists there.

## Terminology

{::comment}
A definition list of the system's own terms, each on first use.
{:/comment}

# Architecture Overview

{::comment}
The components and how they interact, with one figure whose caption cites
the claims it depicts. See the figures skill.
{:/comment}

# Data Model and Structures

{::comment}
Records, messages, enumerations and state machines, as tables and figures.
Structure blocks rendered by the substrate are pasted here verbatim.
{:/comment}

# Protocol Operation

{::comment}
Behaviour, organised by concern (one subsection per concern), never by the
order clusters were processed. Each normative sentence carries one keyword
and one citation.
{:/comment}

# Configuration and Defaults

{::comment}
A table: key, type, default, effect, citation.
{:/comment}

# Error Handling

{::comment}
What the system does on each class of failure, with citations.
{:/comment}

# Observed Accidental Behaviour

{::comment}
Claims with intent accidental — defects the history marks as unintended —
described, never as requirements.
{:/comment}

# Security Considerations

{::comment}
The threats the interface is exposed to and what the implementation does or
does not do about each: authentication, authorization, confidentiality,
integrity, resource exhaustion. "No claim mentions authentication" is a
finding about the system worth stating, not a reason to leave this empty.
{:/comment}

# IANA Considerations

This document has no IANA actions.


--- back

# Change Log

{::comment}
One entry per revision tag: the tag, the cluster, whether the change was
normative, and what moved. The per-cluster narration lives here.
{:/comment}

# Implementation Notes

{::comment}
Implementation facts that are not requirements: class paths, test doubles,
packaging, file locations. Moved here from normative sections, never dropped.
{:/comment}

# Open Questions

{::comment}
Questions from the register that block a section, quoting the claim.
{:/comment}

# Acknowledgements

{::comment}
The developers and authors whose work was reconstructed.
{:/comment}
````

- [ ] **Step 5: The skills**

Replace `plugins/ai-rfc/skills/ai-rfc-rfc-style/SKILL.md` with:

````markdown
---
name: ai-rfc-rfc-style
description: Internet-Draft prose discipline for reconstructed specifications — section ownership, RFC 2119 keyword policy, claim-citation tokens, references, revision tagging, and the template build. Use when writing or revising the draft document of a reconstruction workspace.
---

# RFC prose for a reconstructed specification

The draft lives in `$AI_RFC_WORKSPACE/draft/`, a git repository laid out as an
adopter of `ElNiak/auto-i-d-template` (kramdown-rfc markdown; a `Makefile`
that includes the template's `main.mk`). The prose is yours; every claim of
fact in it is not — it must cite a claim the paired checkpoint manifest holds,
and the citation gate verifies that mechanically.

## Document structure

One source file `draft-<name>.md` at the repo root (exactly one — the gate
refuses zero or several). The skeleton fixes the sections; fill them, never
rename or reorder them:

| Section | Holds |
|---|---|
| Abstract, Introduction, Scope, Organization | What the system is, for a reader who never saw it. No cluster ordinals, no counts of claims added or withdrawn. |
| Conventions and Definitions, Terminology | BCP 14 boilerplate, the citation convention, the system's own terms. |
| Architecture Overview | Components and their interactions, with a cited figure. |
| Data Model and Structures | Records, messages, enumerations, state machines — tables and figures. |
| Protocol Operation | Behaviour by concern, one subsection each; the normative core. |
| Configuration and Defaults, Error Handling | Keys and defaults as a table; failure behaviour. |
| Observed Accidental Behaviour | `intent: accidental` claims, described and never as requirements. |
| Security Considerations | Real analysis of the interface's exposure, even when the answer is "nothing protects it". |
| Change Log (appendix) | One entry per revision tag: the per-cluster narration goes here and nowhere else. |
| Implementation Notes (appendix) | Facts that are not requirements: class paths, test doubles, packaging, `/tmp` paths, literal return strings. Move them here; never drop a cited sentence. |

## What is not specification material

A test double, a fixture value, a class or file path, a build artefact, a
literal return string or a temporary path describes the implementation, not
the behaviour a second implementation must reproduce. It goes to
Implementation Notes with its citation, or nowhere.

## Keywords

A normative statement's keyword comes from the cited claim's `level` and the
keyword policy in `references/keyword-policy.md`: MUST needs enforcing
evidence, a default is a SHOULD, an option is a MAY. Keywords appear only in
normative sections, capitalised, one behaviour per sentence. Prose may be
weaker than the claim's level, never stronger.

## Claim citations

Every normative statement carries a backticked token naming its claim, as
`references/claim-citation.md` describes — read it before writing prose. A
figure's caption sentence cites the claims the figure depicts.

## References

The front matter's `normative:` and `informative:` lists are the document's
references. RFC and Internet-Draft entries are resolved from a sealed cache
the workspace carries; an entry the cache does not hold breaks the build and
must be written inline (`title`, `author`, `target`) instead of by number.
Never list RFC 2119 or RFC 8174: the BCP 14 boilerplate adds them itself, and
listing them again is a build warning.

## Revisions

- One revision per spec-relevant round: extend the prose, commit, build, then
  tag with an **annotated** tag `draft-<name>-NN` (two digits, monotone across
  the sweep).
- Record every revision in `$AI_RFC_WORKSPACE/revisions.yaml` with, at minimum:
  `cluster_id`, `checkpoint_manifest_sha256` (from the checkpoint's
  `checkpoint.json`), an explicit boolean `normative_change`, a one-line
  `note`. A round may carry further fields; this list is not closed.
- A round that changes nothing normative still gets a revision entry with
  `normative_change: false` and a rationale. Its citation set must equal the
  previous revision's; the gate checks.

## The build

The draft is compiled only through `draft build` (the `ai_rfc_draft_build`
tool or the `ai_rfc draft-build` verb): the template's `make txt html lint
idnits`, run offline in a scratch clone of the committed draft. It must exit 0
with no findings before a revision is tagged; the tag tool runs it again and
refuses on findings. Never run `make` yourself and never edit the template's
own files.
````

Create `plugins/ai-rfc/skills/ai-rfc-rfc-style/references/keyword-policy.md`:

````markdown
# Keyword policy

A claim's `level` is chosen when the claim is mined and becomes the keyword
of every sentence that cites it. Choose it from the evidence, not from the
fact that the code does something:

| Level | Requires | Example evidence |
|---|---|---|
| MUST / MUST NOT | The implementation *enforces* it: a rejection, an exception, an assertion, a validation error, or a test that fails without it. | `throw new IllegalArgumentException`, a schema check, a test asserting the refusal. |
| SHOULD / SHOULD NOT | A default, a documented recommendation, or a behaviour the code prefers but does not enforce. | A default parameter value; a retry the caller may disable. |
| MAY | An option, an extension point, a behaviour behind a flag. | A configuration key with no default effect; a plugin hook. |

Implementation facts — how a value is computed, which class holds it, what a
mock returns — carry no keyword: they are descriptive, cited, and placed in
Implementation Notes or omitted.

A document in which most keywords are MUST is a mining problem, not a prose
problem: it means "the code does X" was recorded as "the system MUST X". The
lint reports the MUST fraction; treat a fraction above 0.8 as a signal to
re-examine levels, not to reword sentences.
````

Create `plugins/ai-rfc/skills/ai-rfc-figures/SKILL.md`:

````markdown
---
name: ai-rfc-figures
description: How to draw and cite ASCII-art figures in a reconstructed Internet-Draft — fenced artwork, width limits, titles, and the caption sentence that cites the claims a figure depicts. Use when adding an architecture, sequence or layout figure to the draft.
user-invocable: false
---

# Figures in a reconstructed specification

A figure is prose the reader sees at once; it obeys the same rule as a
sentence: what it asserts, a claim supports.

## Form

- Fence the artwork with `~~~` on its own lines. Plain ASCII, at most 69
  columns, no tabs, no trailing whitespace (the template's lint refuses it).
- Give it an anchor and a title on the line after the closing fence:
  `{: #fig-overview title="Components of the system"}`.
- Draw boxes with `+---+` and `|`, arrows with `--->` and `<---`, and keep
  every label a term from Terminology.

## The caption cites

Within three lines after the closing fence, one sentence states what the
figure shows and cites the claims it depicts, one backticked token per claim,
exactly as a normative sentence would. A figure without such a sentence is a
lint finding.

```
~~~
+--------+   raw data   +--------+   evidence   +---------+
| Client | -----------> | Server | -----------> | Storage |
+--------+              +--------+              +---------+
~~~
{: #fig-overview title="Components of the system"}

Clients submit raw data to the server, which stores the evidence it
derives. `ai_rfc:mark:arch.1` `ai_rfc:mark:store.2`
```

## What not to draw

Nothing the evidence does not support: no boxes for components no claim
names, no arrows for exchanges no claim describes. Structure blocks rendered
by the substrate (bit diagrams, field tables, state tables) are pasted
verbatim and never redrawn by hand.
````

Regenerate the loop skill and check the three files against `.claude/rules/skill-conventions.md` (descriptions under 250 characters, third person, `user-invocable: false` on the figures skill): `cd $AIRFC && $PY -m ai_rfc.experiment render`.

- [ ] **Step 6: Run the tests**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests/experiment/test_render.py tests/experiment/test_workspace.py tests/substrate/draft/test_lint.py -v`
Expected: all PASS, including `test_plugin_skill_is_the_interactive_rendering` (the regenerated SKILL.md) and `test_arm_prompts_differ_only_where_slots_differ` (every differing A/B line still contains `ai_rfc`).

- [ ] **Step 7: Render the skeleton for real once**

Scaffold a throwaway draft and build it with the real toolchain (proves the skeleton compiles, the comments vanish, and the abstract stub lints):

```bash
cd $AIRFC && SSLKEYLOGFILE= AI_RFC_TOOLCHAIN=$HOME/ai-rfc-experiments/tools/toolchain.json $PY - <<'EOF'
from pathlib import Path
import tempfile, os
from ai_rfc.experiment.workspace import scaffold_draft, TEMPLATE_URL, TEMPLATE_COMMIT, MARK
from ai_rfc.draft.build import build, load_toolchain
tmp = Path(tempfile.mkdtemp())
scaffold_draft(tmp / "draft", MARK, template=TEMPLATE_URL, template_commit=TEMPLATE_COMMIT)
report = build(tmp / "draft", toolchain=load_toolchain(Path(os.environ["AI_RFC_TOOLCHAIN"])), out=tmp / "out")
print(report.exit_code, report.findings, sorted(report.outputs))
EOF
```

Expected: `0 () ['draft-elniak-mark-reconstructed.html', 'draft-elniak-mark-reconstructed.txt']`. Open the `.txt` and confirm no `{::comment}` text leaked into it.

- [ ] **Step 8: Commit**

```bash
cd $AIRFC && $PY -m black ai_rfc/experiment/render.py tests/experiment && $PY -m flake8 --max-line-length=88 ai_rfc/experiment/render.py tests/experiment
git status --short
git add ai_rfc/experiment/prompts/loop.tmpl.md ai_rfc/experiment/prompts/draft-skeleton.md ai_rfc/experiment/render.py plugins/ai-rfc/skills/ai-rfc-rfc-style/SKILL.md plugins/ai-rfc/skills/ai-rfc-rfc-style/references/keyword-policy.md plugins/ai-rfc/skills/ai-rfc-figures/SKILL.md plugins/ai-rfc/skills/ai-rfc-reconstruction-loop/SKILL.md tests/experiment/test_render.py tests/experiment/test_workspace.py
git commit -m "feat: build before every tag, and tell the agent what a specification looks like"
```

---

### Task 10: Record the instrument change, and prove SP7a end to end on the finished MARK workspace

**Files:**
- Modify: `docs/experiment-protocol.md`, `README.md` (ai_rfc repo root)
- Create: `docs/experiments/2026-09-03-sp7a-mark-baseline.md`
- Test: the whole suite; `experiment toolchain verify`; `draft build`/`draft lint` on a copy of `~/ai-rfc-experiments/campaigns/mark-full-1/runs/A1/workspace`

**Interfaces:**
- Consumes: everything above.
- Produces: the recorded protocol amendment (18 tools, the build gate, the toolchain record, the frozen task template, the arm-C freeze) and the SP7a baseline numbers SP7d's replay compares against.

- [ ] **Step 1: Protocol and README**

In `docs/experiment-protocol.md`, add a dated subsection "2026-09-03 — draft quality v2, SP7a" stating, in this order: (1) the tool surface is 18 tools (`ai_rfc_draft_build`, `ai_rfc_draft_lint` added; `docs/parity.md` is the table); (2) the raw arm C is frozen at the 16-tool surface (spec D42) and the parity table's third column says "not available in arm C" for the new rows — a v2 campaign compares arms A and B only; (3) every revision tag runs `draft build` first when `AI_RFC_TOOLCHAIN` is set, and `campaign init` refuses without a verified toolchain, so in a campaign every tag compiles; (4) the campaign record freezes `task.tmpl.md` and per-cluster sessions render from it (the previous `task.md` digest described a prompt no per-cluster session ran); (5) `pristine.json` seals `references.yaml` and `refcache/`. In the repository `README.md`: add `AI_RFC_TOOLCHAIN` to the environment-contract table ("optional; names `toolchain.json`; required by the build gate"), the two commands `python -m ai_rfc.experiment toolchain provision` / `verify` under the experiment section, and replace the sentence about the draft being scaffolded from the template root with "scaffolded as a template adopter (`Makefile`, `.gitignore`, `.editorconfig`); the shared library lives under `<root>/tools/i-d-template`".

- [ ] **Step 2: The whole suite**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m pytest tests -n auto 2>&1 | tail -3`
Expected: 0 failed; the count is the SP1 baseline (769) plus every test this plan added (count them from the commits: roughly 40). Record the exact number in the baseline document below.

- [ ] **Step 3: Verify the real toolchain**

Run: `cd $AIRFC && SSLKEYLOGFILE= $PY -m ai_rfc.experiment toolchain verify --root ~/ai-rfc-experiments`
Expected: `ok`, exit 0 (this is the record Task 5 Step 6 re-provisioned).

- [ ] **Step 4: Build and lint the finished MARK draft on a copy**

The campaign directory is evidence; work on a copy:

```bash
cp -R ~/ai-rfc-experiments/campaigns/mark-full-1/runs/A1/workspace /tmp/claude/mark-a1
cd $AIRFC && SSLKEYLOGFILE= $PY -m ai_rfc.experiment workspace migrate-draft /tmp/claude/mark-a1
SSLKEYLOGFILE= AI_RFC_TOOLCHAIN=$HOME/ai-rfc-experiments/tools/toolchain.json $PY -m ai_rfc.draft build /tmp/claude/mark-a1/draft --out /tmp/claude/mark-a1/out
SSLKEYLOGFILE= $PY -m ai_rfc.draft lint /tmp/claude/mark-a1/draft --out /tmp/claude/mark-a1/out --manifest /tmp/claude/mark-a1/manifest.yaml
SSLKEYLOGFILE= $PY -m ai_rfc.draft gate /tmp/claude/mark-a1/draft --timeline /tmp/claude/mark-a1/timeline --checkpoints /tmp/claude/mark-a1/checkpoints --questions /tmp/claude/mark-a1/questions.yaml --revisions /tmp/claude/mark-a1/revisions.yaml --out /tmp/claude/mark-a1/out --strict
```

Expected: `migrate-draft` prints a new HEAD and `git -C /tmp/claude/mark-a1/draft ls-files` lists four files; `build` exits 0 — if it reports `broken reference`, the draft's front matter names a reference outside the sealed set and that is the finding to record, not a plan failure; `lint` exits 0 and prints findings (expected: the skeleton abstract, no references, an Introduction narration count in the hundreds, a MUST fraction near 0.83); `gate --strict` exits 0 (the migration commit is after every tag, so nothing the gate reads changed).

- [ ] **Step 5: Write the baseline document**

Create `docs/experiments/2026-09-03-sp7a-mark-baseline.md` with: the suite count from Step 2; the `toolchain verify` line; the `build-report.json` fields `exit_code`, `findings`, `date`, `outputs` digests; the full `lint-report.json` `findings` list and the `keywords`, `blocks`, `citations` and `sections` blocks verbatim; the gate result. State in the first paragraph that these numbers are the **SP7a waypoint**, measured with SP7a's structure-less lint — *not* SP7d's "before". SP7d's replay re-runs the final (SP7b-extended) lint on a fresh copy so that both sides of its before/after table come from one instrument; a comparison across the two lints would measure instrument drift, not content. State also that the copy under `/tmp/claude` is disposable (the numbers are reproducible from the campaign directory, and a read-only snapshot of the same bytes is sealed at `~/ai-rfc-experiments/baselines/mark-a1-2026-09-03`).

- [ ] **Step 6: Commit**

```bash
cd $AIRFC && git status --short
git add docs/experiment-protocol.md README.md docs/experiments/2026-09-03-sp7a-mark-baseline.md
git commit -m "docs: record the draft quality v2 instrument and the MARK baseline"
```

Then bump the submodule pointer in PANTHER (one commit, `chore(ai_rfc): bump ai_rfc to SP7a (<old>..<new>)`), and push the submodule before the parent, each push confirmed with the user first.

---

## Self-review (run by the plan author on 2026-09-03)

1. **Spec coverage.** D42 → Task 4 (rows, freeze) and Task 10 (protocol). D45 → Tasks 5–7 (toolchain, adopter scaffold, migrate). D46 → Task 6 (references sealed at `prepare`), Task 1 (`--refcache` override), Task 4 (the core passes `<workspace>/refcache`). D49 → Task 4 (build stage in `tag_revision`) and Task 5 (`campaign init` refuses). D51 → Task 8. D52's "lint reports an unloadable manifest" → Task 2. The "Settled by the toolchain run-and-see" section → Task 1's argv/env (binstub, `GEM_PATH`, `XML2RFC_OPTS` in full, no `CI`), Task 9's skeleton (no RFC 2119/8174 in `normative:`), Task 5's `provision`. Not in SP7a by design: structures (D40, D48 → SP7b), consolidation rounds (D43 → SP7c), lint/judge/ground-truth in the analysis and the paid runs (D44, D47 → SP7d).
2. **Placeholder scan.** No "TBD"/"TODO"/"handle edge cases"; every code step shows the code; the two places that say "grep for the name" (`CoreError`'s module, the `_emit` helper) name what to grep and why, because SP1 decides their final location.
3. **Type consistency.** `build(draft_repo, *, toolchain, out, ref, targets, date, refcache, runner)` is called with those keywords in Tasks 1, 4 (via the verb), 5 (`verify`) and 9 (Step 7). `draft_text(repo, ref) -> (name, text)` in Tasks 1, 2. `lint(text, *, manifest, manifest_error, source)` in Tasks 2, 4, 9. `Campaign.toolchain: str | None`, `Campaign.task_template: Path` in Tasks 5, 8. `render_task(window, template=)` in Task 8. `_write_adopter_files(dest, *, template, template_commit)` in Tasks 6–7. `mcp_config(*, python, workspace, toolchain=None)` in Task 5 (SP1's signature plus one keyword).

## Independent review (three reviewers who did not author this plan, 2026-09-03)

Run on the pre-move layout, which is where the plan's anchors were verified and the last point at
which they are cheaply checkable. Paths were judged through the spec's SP1 translation table, so a
path being wrong *today* was not treated as a finding. Fixed in place:

1. **`_parts` never found the end of the front matter** (Critical). It looked only for a bare
   `---`, but the skeleton and the MARK draft both close with `--- abstract` at line 28 and never
   emit a bare closer. `front_end` stayed `0`, `parts["front"]` collapsed to `"\n"`, and
   `_references` returned all zeros for **every real draft**. Task 2's `FRONT` fixture added an
   artificial bare `---`, so the suite passed while the feature was dead. Fixed: `_SECTION_MARKERS`
   also terminate the front matter; the fixture now uses the real convention; and the Task 9
   skeleton test asserts `references == {"normative": 0, "informative": 1, "inline": 1}`, which is
   the discriminating check that would have caught it.
2. **The skeleton lint test asserted `narration == []`, which is false** (Critical). `_prose_lines`
   skipped only lines starting `{::` — not a comment body, and not the `{:/comment}` closer, which
   does not even start with `{::` — and `_introduction` stays inside the section across level-2
   headings, so `## Reconstruction Method`'s legitimate prose ("one timeline cluster at a time")
   matched the bare `\bclusters?\b` pattern. Fixed: `_prose_lines` now tracks comment blocks
   (kramdown-rfc drops them, so linting them was wrong regardless), and the assertion is now
   `{entry["pattern"] for entry in report.narration} <= {"cluster"}`.
3. **`test_tables_are_counted_by_their_rule_row` could not pass** (Critical). `_TABLE_RULE` requires
   `-{3,}`; the fixture's second table used `|:-:|`. Fixed in the fixture, with the three-dash floor
   documented as deliberate.
4. **`return _emit(...)` returns `None`, not an exit code** (Warning). `_emit` is `-> None`; the real
   `gate` branch emits and returns in two statements. Fixed, and the plan's wrong description of
   `_emit` corrected.
5. **The bundled `## Revisions` skill text asserted cluster-only cardinality and a closed field
   list** (Warning). SP7c bundles this same text into the consolidation prompt, where a revision is
   `kind: consolidation` with a `checkpoint` field; SP7c would have had to undo it. Reworded
   round-generic now, which is subtractive and forward-references nothing.
6. Carried into Global Constraints rather than fixed here: the strengthened Task 0 precondition (the
   `ls` alone passes on a half-migrated tree), the three SP1-contingent Task 4 snippets, the four
   unvalidated build-diagnostic regexes, and the two `LintReport.extra` / `_METRIC_KEYS` hooks SP7b
   must build.

Checked and found sound: every path in the File Structure table and every task's `Files:` block
resolves through the translation table to a real pre-move file; SP0 Tasks 3–5 collide with nothing
here (`checkpoint.py` and `coverage/propose.py` are never referenced, `forge/fetch.py` only by
analogy, and `schema.py`'s use already wraps `load()` in a broad `except`); the SP0 Task 2 flag on
`pipeline/cli.py` is adequate; the 18-tool count, the two `parity.md` rows and the `tag_revision`
insertion anchor are byte-exact; and Task 9 leaves `loop.tmpl.md`'s step numbering, `SLOT_TABLES`
and the generated-skill test as clean extension points for SP7c.

## Execution

Subagent-driven (one fresh implementer per task, a reviewer between tasks) is the recommended mode: every task is self-contained, and the two repositories' concurrent history (SP0/SP1 by another session) makes a fresh `git log -1`/`git status --short` at each task start essential. Tasks 1–4 are substrate/server work in one directory and may be dispatched in order without waiting on Tasks 5–9; Tasks 5–9 depend on Task 1's `load_toolchain` (Task 5, 6) and Task 4's tool names (Task 9). Task 10 is last.
