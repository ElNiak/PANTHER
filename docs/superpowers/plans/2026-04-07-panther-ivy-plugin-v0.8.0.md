# panther-ivy-plugin v0.8.0: Cleanup, Simplification, Platform Adoption

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.8.0 of the panther-ivy-plugin with all bugs fixed, dead references removed, documentation accurate, observability consolidated, shared utilities extracted, and official plugin platform features adopted.

**Architecture:** Three-phase approach: (A) surgical cleanup of bugs and stale docs, (B) consolidate 14 observability scripts into one parametric module and extract shared hook utilities, (C) adopt plugin platform features (userConfig, settings.json, skill/agent frontmatter). Each phase produces a separate commit.

**Tech Stack:** Bash, Python 3.10+, JSON, Markdown (Claude Code plugin system)

**Plugin root:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

Throughout this plan, all file paths are relative to the plugin root unless prefixed with a repository-level path.

---

## File Map

### Files to Modify

| File | Responsibility | Tasks |
|------|---------------|-------|
| `hooks/scripts/check-mcp-health.py` | MCP circuit breaker | 1 |
| `hooks/scripts/cleanup-ivy-lsp.sh` | SessionEnd cleanup | 1 |
| `hooks/scripts/cleanup-stale-pids.sh` | SessionStart PID cleanup | 1 |
| `hooks/scripts/wait-for-indexing.sh` | MCP readiness polling | 1 |
| `scripts/start-ivy-server.sh` | LSP/MCP launcher | 1 |
| `hooks/scripts/detect-ivy-workspace.sh` | Workspace detection | 2 |
| `commands/nct-validate.md` | Validation command | 3 |
| `agents/README.md` | Agent catalog | 3, 4 |
| `CLAUDE.md` | Plugin operating guide | 4, 5 |
| `hooks/hooks.json` | Hook registry | 6, 8 |
| `../../README.md` (repo root) | Top-level README | 5 |
| `../../.claude-plugin/marketplace.json` (repo root) | Marketplace manifest | 5 |
| `.claude-plugin/plugin.json` | Plugin manifest | 5, 10 |
| `hooks/scripts/observability/log_event.py` | Event logger (keep) | 8 |
| `hooks/scripts/check-workspace-scope.py` | Workspace scope hook | 9 |
| `hooks/scripts/interaction-checkpoint.py` | Checkpoint hook | 9 |
| `hooks/scripts/observability/obs_post_tool_use_failure.py` | Failure + circuit breaker | 8 |
| All 20 `skills/*/SKILL.md` | Skill definitions | 11 |
| All 5 `agents/*.md` | Agent definitions | 12 |

### Files to Create

| File | Responsibility | Task |
|------|---------------|------|
| `hooks/scripts/observability/observe.py` | Unified parametric observer | 8 |
| `hooks/scripts/hook_utils.py` | Shared hook utilities | 9 |
| `settings.json` | Default plugin settings | 10 |
| `tests/test_observe.py` | Tests for consolidated observer | 8 |
| `tests/test_hook_utils.py` | Tests for shared utilities | 9 |

### Files to Delete

| File | Reason | Task |
|------|--------|------|
| `hooks/scripts/observability/obs_session_start.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_session_end.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_pre_tool_use.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_post_tool_use.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_stop.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_subagent_start.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_subagent_stop.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_user_prompt_submit.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_notification.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_permission_request.py` | Replaced by observe.py | 8 |
| `hooks/scripts/observability/obs_pre_compact.py` | Replaced by observe.py | 8 |

**Note:** `obs_post_tool_use_failure.py` and `check_lsp_log.py` are NOT deleted because they have unique logic (circuit breaker increment, LSP log scanning) beyond simple event logging. They will import from `hook_utils.py` instead.

---

## Phase A: Surgical Cleanup

### Task 1: Replace `kill -0` with `ps -p` across 6 files

**Files:**
- Modify: `hooks/scripts/check-mcp-health.py:103`
- Modify: `scripts/start-ivy-server.sh:126,137`
- Modify: `hooks/scripts/cleanup-ivy-lsp.sh:12`
- Modify: `hooks/scripts/cleanup-stale-pids.sh:13`
- Modify: `hooks/scripts/wait-for-indexing.sh:52`
- Test: `tests/test_hooks.py` (existing tests cover these scripts)

- [ ] **Step 1: Fix `check-mcp-health.py`**

In `hooks/scripts/check-mcp-health.py`, replace the `os.kill(pid, 0)` block in `_check_pid_alive()`:

```python
# OLD (line 103):
            os.kill(pid, 0)  # signal 0: check existence
            return True  # At least one live process
        except ProcessLookupError:
            try:
                os.unlink(pf)
            except OSError:
                pass
            continue  # Dead PID, cleaned up stale file
        except PermissionError:
            return True  # Process exists but owned by another user

# NEW:
            import subprocess
            result = subprocess.run(
                ["ps", "-p", str(pid)],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                return True  # At least one live process
            # Dead PID — clean up stale file
            try:
                os.unlink(pf)
            except OSError:
                pass
            continue
```

Remove the `except ProcessLookupError` and `except PermissionError` blocks since `ps -p` doesn't raise them.

- [ ] **Step 2: Fix `cleanup-ivy-lsp.sh`**

In `hooks/scripts/cleanup-ivy-lsp.sh`, line 12:

```bash
# OLD:
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then

# NEW:
        if [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1; then
```

- [ ] **Step 3: Fix `cleanup-stale-pids.sh`**

In `hooks/scripts/cleanup-stale-pids.sh`, line 13:

```bash
# OLD:
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then

# NEW:
    if [ -n "$pid" ] && ! ps -p "$pid" >/dev/null 2>&1; then
```

- [ ] **Step 4: Fix `wait-for-indexing.sh`**

In `hooks/scripts/wait-for-indexing.sh`, line 52:

```bash
# OLD:
        if ! kill -0 "$mcp_pid" 2>/dev/null; then

# NEW:
        if ! ps -p "$mcp_pid" >/dev/null 2>&1; then
```

- [ ] **Step 5: Fix `start-ivy-server.sh`**

In `scripts/start-ivy-server.sh`, lines 126 and 137:

```bash
# OLD (line 126):
    if kill -0 "$old_pid" 2>/dev/null; then

# NEW (line 126):
    if ps -p "$old_pid" >/dev/null 2>&1; then

# OLD (line 137):
    if ! kill -0 "$old_pid" 2>/dev/null; then

# NEW (line 137):
    if ! ps -p "$old_pid" >/dev/null 2>&1; then
```

- [ ] **Step 6: Run existing tests**

Run: `cd <plugin_root> && python -m pytest tests/test_hooks.py tests/test_workspace_detection.py -v`

Expected: All existing tests pass (the `kill -0` to `ps -p` change is backward-compatible).

- [ ] **Step 7: Commit**

```bash
git add hooks/scripts/check-mcp-health.py hooks/scripts/cleanup-ivy-lsp.sh \
       hooks/scripts/cleanup-stale-pids.sh hooks/scripts/wait-for-indexing.sh \
       scripts/start-ivy-server.sh
git commit -m "fix: replace kill -0 with ps -p for process liveness checks"
```

---

### Task 2: Fix unsanitized path injection in `detect-ivy-workspace.sh`

**Files:**
- Modify: `hooks/scripts/detect-ivy-workspace.sh:95-108`

- [ ] **Step 1: Replace inline Python with stdin piping**

In `hooks/scripts/detect-ivy-workspace.sh`, replace lines 95-108:

```bash
# OLD (lines 95-108):
    ACTIVE_GROUP=$(python3 -c "
import json, sys
try:
    d = json.load(open('$STATE_FILE'))
    print(d.get('active_group', ''))
except: pass
" 2>/dev/null)
    SET_BY=$(python3 -c "
import json, sys
try:
    d = json.load(open('$STATE_FILE'))
    print(d.get('set_by', ''))
except: pass
" 2>/dev/null)

# NEW (single python3 call, reads file via stdin):
    read -r ACTIVE_GROUP SET_BY <<< "$(python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get('active_group', ''), d.get('set_by', ''))
except: print(' ')
" "$STATE_FILE" 2>/dev/null)"
```

This passes `$STATE_FILE` as `sys.argv[1]` instead of interpolating it into the Python source, which prevents injection when the path contains quotes or special characters.

- [ ] **Step 2: Run tests**

Run: `cd <plugin_root> && python -m pytest tests/test_hooks.py::TestDetectIvyWorkspaceHook -v`

Expected: All 5 tests pass.

- [ ] **Step 3: Commit**

```bash
git add hooks/scripts/detect-ivy-workspace.sh
git commit -m "fix: prevent path injection in detect-ivy-workspace state file parsing"
```

---

### Task 3: Remove dead `ivy_query` and `ivy_lint` references

**Files:**
- Modify: `commands/nct-validate.md`
- Modify: `agents/README.md`
- Modify: `commands/nct-add-pattern.md:96`
- Modify: `hooks/scripts/stop-session-summary.sh:131`
- Modify: `commands/nct-observability.md`

- [ ] **Step 1: Fix `agents/README.md`**

In `agents/README.md`, line 110, replace the tool list to remove `ivy_lint` and `ivy_query`:

```markdown
# OLD:
- **ivy-tools MCP** -- 15 consolidated tools including `ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_lint`, `ivy_coverage` (mode=matrix/stats/gaps), `ivy_query` (mode=impact/xrefs/info), `ivy_visualize` (view=dependencies/state_machine/layers), `ivy_quality` (mode=suggestions/gate), `ivy_patterns` (mode=analyze/validate/compare/check) configured via `.mcp.json`

# NEW:
- **ivy-tools MCP** -- consolidated tools including `ivy_verify`, `ivy_compile`, `ivy_model_info`, `ivy_diagnostics` (mode=structural/full), `ivy_coverage` (mode=matrix/stats/gaps), `ivy_visualize` (view=dependencies/state_machine/layers), `ivy_quality` (mode=suggestions/gate), `ivy_patterns` (mode=analyze/validate/compare/check), `ivy_extract_requirements`, `ivy_model_summary`, `ivy_include_graph`, `ivy_capabilities`, `ivy_workspace`, `ivy_pattern_scaffold` configured via `.mcp.json`
```

- [ ] **Step 2: Fix `nct-validate.md` — replace `ivy_query` with LSP equivalents**

This file has 12+ references to `ivy_query`. Replace each `ivy_query(mode="info")` call with the LSP `hover` or `goToDefinition` equivalent. Replace `ivy_query(mode="impact")` with LSP `incomingCalls`/`outgoingCalls`. Replace `ivy_query(mode="xrefs")` with LSP `findReferences`.

For each occurrence, the pattern is:

```markdown
# OLD:
Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_query` with:
- mode: "info"
- symbol: "cid"

# NEW:
Use LSP `hover` on the `cid` symbol in its definition file to retrieve type info.
If the file is not open, use `Grep` to locate the definition first.
```

Apply this replacement for all 12+ `ivy_query` references. Also update the surface coverage table (lines ~679-685) to replace `ivy_query` rows with LSP operation equivalents and mark them "covered via LSP".

- [ ] **Step 3: Fix `nct-validate.md` — replace `ivy_lint` with `ivy_diagnostics`**

Replace all `ivy_lint` MCP calls (lines ~371, 400, 418, 434) with `ivy_diagnostics(mode="structural")`:

```markdown
# OLD:
Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint` with:

# NEW:
Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics` with:
- mode: "structural"
```

Update the surface coverage table to rename `ivy_lint` to `ivy_diagnostics(structural)`.

- [ ] **Step 4: Fix `nct-add-pattern.md`**

Line 96:

```markdown
# OLD:
Run `ivy_lint` on the generated files to verify structural correctness.

# NEW:
Run `ivy_diagnostics(mode="structural")` on the generated files to verify structural correctness.
```

- [ ] **Step 5: Fix `stop-session-summary.sh`**

Line 131:

```bash
# OLD:
  SUMMARY="[IVY SESSION SUMMARY] $FILE_COUNT .ivy file(s) modified, $ISSUE_COUNT with lint issues:\\n${ISSUES}Run ivy_lint on flagged files before committing.${CLAIM_SECTION}${METRICS_SECTION}"

# NEW:
  SUMMARY="[IVY SESSION SUMMARY] $FILE_COUNT .ivy file(s) modified, $ISSUE_COUNT with lint issues:\\n${ISSUES}Run ivy_diagnostics(mode=\"structural\") on flagged files before committing.${CLAIM_SECTION}${METRICS_SECTION}"
```

- [ ] **Step 6: Fix `nct-observability.md`**

Replace the `ivy_lint` row in the metrics table with `ivy_diagnostics`.

- [ ] **Step 7: Commit**

```bash
git add commands/nct-validate.md agents/README.md commands/nct-add-pattern.md \
       hooks/scripts/stop-session-summary.sh commands/nct-observability.md
git commit -m "fix: remove dead ivy_query and ivy_lint references, replace with LSP/ivy_diagnostics"
```

---

### Task 4: Add `ivy_health_check` to CLAUDE.md tool table

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add `ivy_health_check` to the MCP Tool Name Reference table**

In `CLAUDE.md`, after the `ivy_workspace` row in the MCP Tool Name Reference table, add:

```markdown
| `ivy_health_check` | -- | -- |
```

- [ ] **Step 2: Verify consistency**

Search for other `ivy_health_check` references in `CLAUDE.md` (lines 399-400) and `healthcheck/SKILL.md` — they should now be consistent with the tool table.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "fix: add ivy_health_check to CLAUDE.md MCP tool reference table"
```

---

### Task 5: Align versions and rewrite README

**Files:**
- Modify: `../../.claude-plugin/marketplace.json`
- Modify: `../../README.md`
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Bump marketplace.json versions**

In `../../.claude-plugin/marketplace.json`, change both `"version": "0.5.0"` entries (lines 13 and 42) to `"version": "0.8.0"`.

- [ ] **Step 2: Update plugin.json version**

In `.claude-plugin/plugin.json`, change `"version": "0.7.0"` to `"version": "0.8.0"`.

- [ ] **Step 3: Rewrite README.md**

In `../../README.md`, make these changes:

Line 5 — version:
```markdown
# OLD:
**Version:** 0.5.0 | **License:** MIT | **Author:** [ElNiak](https://github.com/ElNiak)

# NEW:
**Version:** 0.8.0 | **License:** MIT | **Author:** [ElNiak](https://github.com/ElNiak)
```

Lines 48-54 — component count table:
```markdown
# OLD:
| Agents | 4 | Methodology guide, model reviewer, spec analyst, traceability agent | [agents/](agents/) |
| Commands | 7 | Slash commands for verification, compilation, and scaffolding | [commands/](commands/) |
| Skills | 6 | Domain knowledge for Ivy language, methodologies, and tooling | [skills/](skills/) |
| Hooks | 3 | PreToolUse (warn CLI), PostToolUse (lint .ivy), SessionStart (workspace detection) | -- |

# NEW:
| Agents | 5 | Navigator, methodology guide, model reviewer, spec analyst, traceability agent | [agents/](agents/) |
| Commands | 10 | Slash commands for verification, compilation, scaffolding, review, health, observability | [commands/](commands/) |
| Skills | 20 | Domain knowledge, methodologies, tooling, interaction patterns, workspace management | [skills/](skills/) |
| Hooks | 25 | 12 event types: PreToolUse, PostToolUse, PostToolUseFailure, SessionStart/End, Stop, Subagent, Compact, Prompt, Notification, Permission | [hooks/](hooks/) |
```

Lines 113-148 — directory tree. Replace the entire `## Directory Structure` section with an accurate tree. Include all 5 agents, all 10 commands (list the 3 missing ones), show the full hooks structure with `observability/` subdirectory, and list all 20 skill directories.

- [ ] **Step 4: Update CLAUDE.md available skills and agents lists**

In `CLAUDE.md`, find the "Available Skills" line and add the 7 missing skills:
- `adaptive-interview`
- `claim-discussion`
- `clear-workspace`
- `healthcheck`
- `interaction-patterns`
- `ivy-protocol-model-builder`
- `set-workspace`

In `CLAUDE.md`, find the "Available Agents" line and add `navigator`.

In `CLAUDE.md`, find the "Quick Reference" commands line and add `/nct-serena-health` and `/nct-review`.

- [ ] **Step 5: Commit**

```bash
git add ../../.claude-plugin/marketplace.json ../../README.md .claude-plugin/plugin.json CLAUDE.md
git commit -m "docs: align versions to 0.8.0, rewrite README with accurate component counts"
```

---

### Task 6: Add `async: true` to observability hooks

**Files:**
- Modify: `hooks/hooks.json`

- [ ] **Step 1: Add `async: true` to all observability hook entries**

In `hooks/hooks.json`, find every hook entry whose command path contains `/observability/` and add `"async": true` to the hook object. There are 14 such entries across these event types: PreToolUse (last entry), PostToolUse (last entry), PostToolUseFailure, SessionStart (3rd entry), SessionEnd (2nd entry), Stop (2nd entry), SubagentStart, SubagentStop, PreCompact, UserPromptSubmit, Notification, PermissionRequest.

Example change for the PreToolUse observability hook (the last PreToolUse entry in hooks.json, around line 62):

```json
// OLD:
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_pre_tool_use.py",
            "timeout": 5
          }

// NEW:
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_pre_tool_use.py",
            "timeout": 5,
            "async": true
          }
```

Apply the same `"async": true` addition to all 14 observability hooks. Do NOT add `async` to behavioral hooks (block-direct-ivy, check-workspace-scope, check-mcp-health, check-indexing-ready, post-write-ivy-lint, interaction-checkpoint, detect-ivy-workspace, cleanup-ivy-lsp, cleanup-stale-pids, wait-for-indexing, stop-session-summary, check_lsp_log).

- [ ] **Step 2: Run manifest tests**

Run: `cd <plugin_root> && python -m pytest tests/test_manifests.py -v`

Expected: All tests pass. The `async` field is an optional addition to hook entries.

- [ ] **Step 3: Commit**

```bash
git add hooks/hooks.json
git commit -m "perf: make all observability hooks async to reduce tool call latency"
```

---

## Phase B: Architectural Simplification

### Task 7: (no-op placeholder — numbering alignment)

Skipped. Task numbering continues from Phase A.

---

### Task 8: Consolidate 14 observability scripts into `observe.py`

**Files:**
- Create: `hooks/scripts/observability/observe.py`
- Create: `tests/test_observe.py`
- Modify: `hooks/hooks.json` (update all observability command paths)
- Modify: `hooks/scripts/observability/obs_post_tool_use_failure.py` (import from hook_utils later in Task 9)
- Delete: 11 `obs_*.py` scripts (listed in File Map above)
- Keep: `log_event.py`, `check_lsp_log.py`, `obs_post_tool_use_failure.py`

- [ ] **Step 1: Write the failing test for `observe.py`**

Create `tests/test_observe.py`:

```python
"""Tests for the consolidated observe.py observability script."""

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

OBSERVE_SCRIPT = (
    Path(__file__).parent.parent
    / "hooks"
    / "scripts"
    / "observability"
    / "observe.py"
)


def _run_observe(event_type: str, json_input: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    import os
    run_env = os.environ.copy()
    run_env["IVY_OBSERVABILITY_ENABLED"] = "1"
    if env:
        run_env.update(env)
    return subprocess.run(
        ["python3", str(OBSERVE_SCRIPT), "--event", event_type],
        input=json.dumps(json_input),
        capture_output=True,
        text=True,
        timeout=10,
        env=run_env,
    )


class TestObserveParametric:
    """Test that the parametric observer handles all event types."""

    @pytest.mark.parametrize("event_type", [
        "SessionStart", "SessionEnd", "Stop",
        "SubagentStart", "SubagentStop",
        "UserPromptSubmit", "Notification",
        "PermissionRequest", "PreCompact",
        "PreToolUse", "PostToolUse",
    ])
    def test_event_logged(self, event_type, tmp_path):
        """Each event type should produce a JSONL event in the log directory."""
        session_dir = tmp_path / "sessions" / "test-sess"
        result = _run_observe(
            event_type,
            {"session_id": "test-sess", "tool_name": "Bash", "command": "ls"},
            env={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        events_file = session_dir / "events.jsonl"
        assert events_file.exists(), f"No events.jsonl for {event_type}"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) >= 1
        event = json.loads(lines[-1])
        assert event["event_type"] == event_type

    def test_pre_tool_use_skips_read_tools(self, tmp_path):
        """PreToolUse should skip Read/Grep/Glob unless IVY_OBSERVABILITY_ALL_TOOLS."""
        session_dir = tmp_path / "sessions" / "test-sess"
        result = _run_observe(
            "PreToolUse",
            {"session_id": "test-sess", "tool_name": "Read"},
            env={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        events_file = session_dir / "events.jsonl"
        assert not events_file.exists()

    def test_session_end_includes_tool_summary(self, tmp_path):
        """SessionEnd should read back events and produce a tool summary."""
        session_dir = tmp_path / "sessions" / "test-sess"
        session_dir.mkdir(parents=True)
        events_file = session_dir / "events.jsonl"
        events_file.write_text(
            json.dumps({"event_type": "PreToolUse", "payload": {"tool_name": "Bash"}}) + "\n"
            + json.dumps({"event_type": "PreToolUse", "payload": {"tool_name": "Bash"}}) + "\n"
            + json.dumps({"event_type": "PreToolUse", "payload": {"tool_name": "Read"}}) + "\n"
        )
        result = _run_observe(
            "SessionEnd",
            {"session_id": "test-sess", "reason": "logout"},
            env={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        lines = events_file.read_text().strip().split("\n")
        last = json.loads(lines[-1])
        assert last["event_type"] == "SessionEnd"
        assert "tool_summary" in last.get("payload", {})

    def test_invalid_json_graceful(self):
        """Invalid JSON on stdin should exit 0 silently."""
        import os
        result = subprocess.run(
            ["python3", str(OBSERVE_SCRIPT), "--event", "Stop"],
            input="not json",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "IVY_OBSERVABILITY_ENABLED": "1"},
        )
        assert result.returncode == 0

    def test_disabled_via_env(self, tmp_path):
        """IVY_OBSERVABILITY_ENABLED=0 should skip logging."""
        result = _run_observe(
            "SessionStart",
            {"session_id": "test-sess"},
            env={
                "IVY_OBSERVABILITY_DIR": str(tmp_path),
                "IVY_OBSERVABILITY_ENABLED": "0",
            },
        )
        assert result.returncode == 0
        session_dir = tmp_path / "sessions" / "test-sess"
        assert not session_dir.exists() or not (session_dir / "events.jsonl").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <plugin_root> && python -m pytest tests/test_observe.py -v`

Expected: FAIL — `observe.py` does not exist yet.

- [ ] **Step 3: Create `observe.py`**

Create `hooks/scripts/observability/observe.py`:

```python
#!/usr/bin/env python3
"""Unified parametric observability hook for panther-ivy-plugin.

Replaces 11 individual obs_*.py scripts. Called with --event <EventType>
to handle any Claude Code lifecycle event.

Usage:
    python3 observe.py --event PreToolUse < hook_input.json
    python3 observe.py --event SessionEnd < hook_input.json
"""

import argparse
import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_SKIP_TOOLS = {"Read", "Grep", "Glob", "LS"}


def _summarize_tool_input(tool_name: str, tool_input: dict) -> dict:
    """Produce a privacy-safe summary of tool input."""
    if tool_name == "Bash":
        return {"command": tool_input.get("command", "")[:200]}
    if tool_name in ("Write", "Edit"):
        return {
            "file_path": tool_input.get("file_path", ""),
            "content_length": len(tool_input.get("content", tool_input.get("new_string", ""))),
        }
    if tool_name == "Read":
        return {"file_path": tool_input.get("file_path", "")}
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 3)
        return {
            "mcp_server": parts[1] if len(parts) > 1 else "",
            "mcp_tool": parts[-1] if len(parts) > 2 else tool_name,
        }
    return {"keys": list(tool_input.keys())[:10]}


def _build_payload(event_type: str, data: dict) -> dict | None:
    """Build event-specific payload from hook input data.

    Returns None to signal the event should be skipped (e.g., high-frequency tools).
    """
    tool_name = data.get("tool_name", "")

    if event_type == "PreToolUse":
        if tool_name in _SKIP_TOOLS and not os.environ.get("IVY_OBSERVABILITY_ALL_TOOLS"):
            return None
        tool_input = data.get("tool_input", {})
        return {
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id", ""),
            "tool_summary": _summarize_tool_input(tool_name, tool_input if isinstance(tool_input, dict) else {}),
            "active_workspace": os.environ.get("IVY_ACTIVE_WORKSPACE", ""),
        }

    if event_type == "PostToolUse":
        if tool_name in _SKIP_TOOLS and not os.environ.get("IVY_OBSERVABILITY_ALL_TOOLS"):
            return None
        is_mcp = tool_name.startswith("mcp__") if tool_name else False
        payload = {
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id", ""),
            "is_mcp_tool": is_mcp,
        }
        if is_mcp:
            parts = tool_name.split("__", 3)
            payload["mcp_server"] = parts[1] if len(parts) > 1 else ""
            payload["mcp_tool_name"] = parts[-1] if len(parts) > 2 else tool_name
        return payload

    if event_type == "SessionStart":
        return {
            "source": data.get("source", ""),
            "model": data.get("model", ""),
            "agent_type": data.get("agent_type", ""),
            "permission_mode": data.get("permission_mode", ""),
            "workspace_root": os.environ.get("IVY_WORKSPACE_ROOT", ""),
        }

    if event_type == "SessionEnd":
        payload = {"reason": data.get("reason", "")}
        payload.update(_session_end_tool_summary(data.get("session_id", "")))
        return payload

    if event_type == "Stop":
        message = data.get("last_assistant_message", "")
        return {
            "stop_hook_active": data.get("stop_hook_active", False),
            "message_length": len(message) if isinstance(message, str) else 0,
        }

    if event_type == "SubagentStart":
        return {
            "agent_id": data.get("agent_id", ""),
            "agent_type": data.get("agent_type", ""),
        }

    if event_type == "SubagentStop":
        message = data.get("last_assistant_message", "")
        return {
            "agent_id": data.get("agent_id", ""),
            "agent_type": data.get("agent_type", ""),
            "stop_hook_active": data.get("stop_hook_active", False),
            "message_length": len(message) if isinstance(message, str) else 0,
        }

    if event_type == "UserPromptSubmit":
        prompt = data.get("prompt", "")
        return {
            "prompt_length": len(prompt) if isinstance(prompt, str) else 0,
            "prompt_preview": prompt[:100] if isinstance(prompt, str) else "",
        }

    if event_type == "Notification":
        message = data.get("message", "")
        return {
            "notification_type": data.get("notification_type", ""),
            "title": data.get("title", ""),
            "message_length": len(message) if isinstance(message, str) else 0,
        }

    if event_type == "PermissionRequest":
        suggestions = data.get("permission_suggestions", [])
        return {
            "tool_name": data.get("tool_name", ""),
            "suggestion_count": len(suggestions) if isinstance(suggestions, list) else 0,
        }

    if event_type == "PreCompact":
        return {
            "trigger": data.get("trigger", ""),
            "has_custom_instructions": bool(data.get("custom_instructions")),
        }

    return {}


def _session_end_tool_summary(session_id: str) -> dict:
    """Read back events.jsonl to produce a tool usage summary for SessionEnd."""
    obs_dir = os.environ.get("IVY_OBSERVABILITY_DIR", "").strip()
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()

    candidates = []
    if obs_dir:
        candidates.append(Path(obs_dir) / "sessions" / session_id / "events.jsonl")
    if ws_root:
        candidates.append(Path(ws_root) / ".observability" / "sessions" / session_id / "events.jsonl")
    candidates.append(Path("/tmp/ivy-observability") / "sessions" / session_id / "events.jsonl")

    for events_file in candidates:
        if events_file.exists():
            try:
                tool_counts = collections.Counter()
                for line in events_file.read_text().splitlines():
                    try:
                        evt = json.loads(line)
                        if evt.get("event_type") == "PreToolUse":
                            tool_name = (evt.get("payload") or {}).get("tool_name", "?")
                            tool_counts[tool_name] += 1
                    except (json.JSONDecodeError, TypeError):
                        continue
                if tool_counts:
                    return {
                        "tool_summary": dict(tool_counts.most_common(10)),
                        "total_tool_calls": sum(tool_counts.values()),
                    }
            except OSError:
                pass
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    args = parser.parse_args()

    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            data = {}
    except (json.JSONDecodeError, EOFError, ValueError):
        data = {}

    session_id = data.get("session_id", "")
    payload = _build_payload(args.event, data)

    if payload is None:
        return

    try:
        from log_event import log_event
        log_event(args.event, session_id, payload)
    except Exception:
        pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd <plugin_root> && python -m pytest tests/test_observe.py -v`

Expected: All tests PASS.

- [ ] **Step 5: Update `hooks.json` to use `observe.py --event`**

In `hooks/hooks.json`, replace every observability hook command that currently points to an individual `obs_*.py` script with the parametric version. Here is the mapping (11 replacements):

| Old command | New command |
|-------------|------------|
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_pre_tool_use.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event PreToolUse` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_post_tool_use.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event PostToolUse` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_session_start.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event SessionStart` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_session_end.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event SessionEnd` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_stop.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event Stop` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_subagent_start.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event SubagentStart` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_subagent_stop.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event SubagentStop` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_user_prompt_submit.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event UserPromptSubmit` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_notification.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event Notification` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_permission_request.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event PermissionRequest` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/obs_pre_compact.py` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event PreCompact` |

Do NOT replace `obs_post_tool_use_failure.py` (has circuit breaker logic) or `check_lsp_log.py` (has LSP log scanning logic).

- [ ] **Step 6: Run all tests**

Run: `cd <plugin_root> && python -m pytest tests/ -v`

Expected: All tests pass. The manifest tests will validate that all script paths in hooks.json exist.

- [ ] **Step 7: Delete the 11 replaced scripts**

```bash
cd <plugin_root>
rm hooks/scripts/observability/obs_session_start.py
rm hooks/scripts/observability/obs_session_end.py
rm hooks/scripts/observability/obs_pre_tool_use.py
rm hooks/scripts/observability/obs_post_tool_use.py
rm hooks/scripts/observability/obs_stop.py
rm hooks/scripts/observability/obs_subagent_start.py
rm hooks/scripts/observability/obs_subagent_stop.py
rm hooks/scripts/observability/obs_user_prompt_submit.py
rm hooks/scripts/observability/obs_notification.py
rm hooks/scripts/observability/obs_permission_request.py
rm hooks/scripts/observability/obs_pre_compact.py
```

- [ ] **Step 8: Update `test_observability.py` to test `observe.py`**

In `tests/test_observability.py`, update the `TestObsHooksHappyPath` class to call `observe.py --event <type>` instead of the individual scripts. The test structure stays the same; only the subprocess command changes.

- [ ] **Step 9: Run all tests again**

Run: `cd <plugin_root> && python -m pytest tests/ -v`

Expected: All tests pass.

- [ ] **Step 10: Commit**

```bash
git add hooks/scripts/observability/observe.py tests/test_observe.py \
       hooks/hooks.json tests/test_observability.py
git rm hooks/scripts/observability/obs_session_start.py \
      hooks/scripts/observability/obs_session_end.py \
      hooks/scripts/observability/obs_pre_tool_use.py \
      hooks/scripts/observability/obs_post_tool_use.py \
      hooks/scripts/observability/obs_stop.py \
      hooks/scripts/observability/obs_subagent_start.py \
      hooks/scripts/observability/obs_subagent_stop.py \
      hooks/scripts/observability/obs_user_prompt_submit.py \
      hooks/scripts/observability/obs_notification.py \
      hooks/scripts/observability/obs_permission_request.py \
      hooks/scripts/observability/obs_pre_compact.py
git commit -m "refactor: consolidate 11 observability scripts into parametric observe.py"
```

---

### Task 9: Extract `hook_utils.py` for shared utilities

**Files:**
- Create: `hooks/scripts/hook_utils.py`
- Create: `tests/test_hook_utils.py`
- Modify: `hooks/scripts/check-workspace-scope.py`
- Modify: `hooks/scripts/interaction-checkpoint.py`
- Modify: `hooks/scripts/observability/obs_post_tool_use_failure.py`
- Modify: `hooks/scripts/check-mcp-health.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_hook_utils.py`:

```python
"""Tests for shared hook utilities."""

import json

import pytest

pytestmark = pytest.mark.unit


class TestResolveSessionId:
    def test_env_var_priority(self, monkeypatch):
        monkeypatch.setenv("IVY_SESSION_ID", "from-ivy")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "from-claude")
        from hooks.scripts.hook_utils import resolve_session_id
        assert resolve_session_id() == "from-ivy"

    def test_fallback_to_unknown(self, monkeypatch):
        monkeypatch.delenv("IVY_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        from hooks.scripts.hook_utils import resolve_session_id
        result = resolve_session_id()
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetStatePath:
    def test_returns_path_in_observability_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.setenv("IVY_SESSION_ID", "test-sess")
        from hooks.scripts.hook_utils import get_mcp_health_state_path
        path = get_mcp_health_state_path()
        assert "test-sess" in path
        assert "mcp-health-state.json" in path


class TestEmitHookOutput:
    def test_emit_additional_context(self, capsys):
        from hooks.scripts.hook_utils import emit_hook_output
        emit_hook_output("PreToolUse", additional_context="test message")
        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["additionalContext"] == "test message"

    def test_emit_deny(self, capsys):
        from hooks.scripts.hook_utils import emit_hook_output
        emit_hook_output("PreToolUse", deny_reason="blocked")
        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <plugin_root> && python -m pytest tests/test_hook_utils.py -v`

Expected: FAIL — module not found.

- [ ] **Step 3: Create `hook_utils.py`**

Create `hooks/scripts/hook_utils.py`:

```python
#!/usr/bin/env python3
"""Shared utilities for panther-ivy-plugin hook scripts.

Centralizes session ID resolution, workspace detection, MCP health state
management, and JSON hook output formatting.
"""

import json
import os
import sys
from pathlib import Path

try:
    from ivy_lsp.infra.observability.session import resolve_session_id as _canonical_resolve
except ImportError:
    _canonical_resolve = None


def resolve_session_id(hook_input: dict | None = None) -> str:
    """Resolve Claude session ID using canonical priority chain.

    Priority: ivy-lsp canonical > hook_payload > IVY_SESSION_ID >
    CLAUDE_SESSION_ID > CLAUDE_CODE_SESSION_ID > session file > "unknown"
    """
    if _canonical_resolve is not None:
        try:
            return _canonical_resolve(hook_payload=hook_input)
        except Exception:
            pass

    if hook_input:
        payload_session = str(hook_input.get("session_id", "")).strip()
        if payload_session:
            return payload_session

    for var in ("IVY_SESSION_ID", "CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        value = os.environ.get(var, "").strip()
        if value:
            return value

    return "unknown"


def get_workspace_root() -> str:
    """Get workspace root from environment, with walk-up fallback."""
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if ws_root:
        return ws_root
    check = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(check, "panther", "plugins", "services",
                                 "testers", "panther_ivy")
        if os.path.isdir(os.path.join(candidate, "protocol-testing")):
            return candidate
        parent = os.path.dirname(check)
        if parent == check:
            break
        check = parent
    return os.getcwd()


def get_mcp_health_state_path() -> str:
    """Get the path to the MCP health state file for the current session."""
    ws_root = get_workspace_root()
    sid = resolve_session_id()
    state_dir = os.path.join(ws_root, ".observability", "sessions", sid)
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "mcp-health-state.json")


def read_stdin() -> dict:
    """Read and parse JSON from stdin. Returns empty dict on failure."""
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def emit_hook_output(
    event_name: str,
    *,
    additional_context: str | None = None,
    deny_reason: str | None = None,
    system_message: str | None = None,
) -> None:
    """Print structured hook JSON output to stdout."""
    hook_output: dict = {"hookEventName": event_name}
    if deny_reason:
        hook_output["permissionDecision"] = "deny"
        hook_output["permissionDecisionReason"] = deny_reason
    if additional_context:
        hook_output["additionalContext"] = additional_context
    output: dict = {"hookSpecificOutput": hook_output}
    if system_message:
        output["systemMessage"] = system_message
    print(json.dumps(output))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <plugin_root> && python -m pytest tests/test_hook_utils.py -v`

Expected: PASS.

- [ ] **Step 5: Refactor `check-workspace-scope.py` to use `hook_utils`**

In `hooks/scripts/check-workspace-scope.py`:

1. Add import at top: `sys.path.insert(0, str(Path(__file__).parent))` then `from hook_utils import resolve_session_id, emit_hook_output, read_stdin`
2. Delete the `_resolve_session_id` function (lines 136-148) — replaced by `hook_utils.resolve_session_id`
3. Replace all `print(json.dumps(output))` calls with `emit_hook_output(...)` calls
4. Replace `json.load(sys.stdin)` with `read_stdin()`

- [ ] **Step 6: Refactor `check-mcp-health.py` to use `hook_utils`**

In `hooks/scripts/check-mcp-health.py`:

1. Add import: `sys.path.insert(0, os.path.join(os.path.dirname(__file__)))` then `from hook_utils import get_mcp_health_state_path, emit_hook_output`
2. Delete `_get_state_path()` function (lines 27-47) — replaced by `hook_utils.get_mcp_health_state_path`
3. Replace `_emit_result()` with `emit_hook_output()` calls

- [ ] **Step 7: Refactor `obs_post_tool_use_failure.py` to use `hook_utils`**

In `hooks/scripts/observability/obs_post_tool_use_failure.py`:

1. Add: `sys.path.insert(0, str(Path(__file__).parent.parent))` then `from hook_utils import get_mcp_health_state_path`
2. Delete the local `_get_state_path()` function (lines 19-24)
3. Replace `state_path = _get_state_path()` with `state_path = get_mcp_health_state_path()`

- [ ] **Step 8: Run all tests**

Run: `cd <plugin_root> && python -m pytest tests/ -v`

Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add hooks/scripts/hook_utils.py tests/test_hook_utils.py \
       hooks/scripts/check-workspace-scope.py hooks/scripts/check-mcp-health.py \
       hooks/scripts/observability/obs_post_tool_use_failure.py
git commit -m "refactor: extract hook_utils.py for shared session ID, workspace, output formatting"
```

---

## Phase C: Platform Feature Adoption

### Task 10: Add `userConfig` and `settings.json`

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Create: `settings.json`

- [ ] **Step 1: Add `userConfig` to `plugin.json`**

In `.claude-plugin/plugin.json`, add the `userConfig` field after `homepage`:

```json
{
  "name": "panther-ivy-plugin",
  "description": "Unified Ivy formal protocol testing plugin providing both LSP (diagnostics, navigation, hover) and MCP (ivy-tools: verification, compilation, coverage analysis) servers. NCT/NACT/NSCT methodology guidance with agents, skills, and commands for formal protocol specification, attack modeling, and simulation-based testing using the 14-layer template architecture.",
  "version": "0.8.0",
  "author": {
    "name": "ElNiak",
    "email": "elniak@github.com"
  },
  "repository": "https://github.com/ElNiak/panther-ivy-plugin",
  "license": "MIT",
  "keywords": ["ivy", "formal-verification", "protocol-testing", "panther", "interactive"],
  "homepage": "https://github.com/ElNiak/panther-ivy-plugin",
  "userConfig": {
    "log_level": {
      "description": "Ivy LSP/MCP log verbosity (DEBUG, INFO, WARN, ERROR)",
      "sensitive": false
    },
    "enable_serena": {
      "description": "Enable the Serena MCP server for semantic code intelligence (requires panther-serena submodule)",
      "sensitive": false
    },
    "force_reinstall": {
      "description": "Force uvx to reinstall ivy-lsp on every server start (use when modifying local ivy-lsp source)",
      "sensitive": false
    },
    "observability_enabled": {
      "description": "Enable observability event logging to JSONL files (true/false)",
      "sensitive": false
    }
  }
}
```

- [ ] **Step 2: Create `settings.json`**

Create `settings.json` at the plugin root:

```json
{
  "env": {
    "IVY_LSP_LOG_LEVEL": "${user_config.log_level:INFO}",
    "PANTHER_IVY_ENABLE_SERENA": "${user_config.enable_serena:0}",
    "IVY_LSP_FORCE_REINSTALL": "${user_config.force_reinstall:0}",
    "IVY_OBSERVABILITY_ENABLED": "${user_config.observability_enabled:1}"
  }
}
```

- [ ] **Step 3: Run manifest tests**

Run: `cd <plugin_root> && python -m pytest tests/test_manifests.py -v`

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json settings.json
git commit -m "feat: add userConfig and settings.json for configurable log level, serena, observability"
```

---

### Task 11: Add skill frontmatter features

**Files:**
- Modify: All 20 `skills/*/SKILL.md` files

- [ ] **Step 1: Add `allowed-tools` to read-only reference skills**

For these 4 skills, add `allowed-tools` to the YAML frontmatter (these skills provide reference material and should never write files):

`skills/methodology-reference/SKILL.md`:
```yaml
---
name: methodology-reference
description: "Use when working with NCT (compositional protocol testing), NACT (attack testing, security testing, APT lifecycle), or NSCT (simulation, Shadow NS, large-scale testing) methodology. Covers all three PANTHER formal testing methodologies."
allowed-tools: "Read Grep Glob ToolSearch"
---
```

`skills/specification-patterns/SKILL.md`:
```yaml
---
name: specification-patterns
description: "Use when structuring a new formal protocol specification into modular Ivy layers, choosing which layers to scaffold first, or selecting formal model patterns (variants, serdes, shims, monitors, entities, modules)."
allowed-tools: "Read Grep Glob ToolSearch"
---
```

`skills/workflow-reference/SKILL.md`:
```yaml
---
name: workflow-reference
description: "Use when translating RFC normative language into Ivy constructs, running verification and debugging failures, or understanding the quality evaluation pipeline."
allowed-tools: "Read Grep Glob ToolSearch"
---
```

`skills/tooling-reference/SKILL.md`:
```yaml
---
name: tooling-reference
description: "Use when choosing between LSP, MCP tools, and Claude native tools for an Ivy task, looking up tool parameters and usage patterns, or navigating Ivy specifications with LSP operations."
allowed-tools: "Read Grep Glob ToolSearch"
---
```

- [ ] **Step 2: Add `context: fork` to large reference skills**

For skills with heavy reference material that shouldn't bloat the main context window, add `context: fork`:

`skills/ivy-writing-guide/SKILL.md` (~348 lines with references):
```yaml
---
name: ivy-writing-guide
description: "Use when editing .ivy files, creating test specifications, or adding RFC bracket-tag annotations. Covers Ivy syntax, declaration types, module system, test spec patterns, and annotated specification writing."
context: fork
---
```

`skills/counterexample-guide/SKILL.md` (~330 lines):
```yaml
---
name: counterexample-guide
description: Use when ivy_verify fails with a counterexample to understand the failure, trace the violated property, and identify the fix. Guides interpretation of structured counterexample traces.
prerequisites:
  - ivy-writing-guide
  - workflow-reference
context: fork
---
```

`skills/claim-discussion/SKILL.md` (~263 lines):
```yaml
---
name: claim-discussion
description: "Use when discussing verification claims, RFC requirement interpretations, or coverage gap priorities with the user. Provides structured decision trees for each claim type."
prerequisites: ["interaction-patterns", "counterexample-guide"]
context: fork
---
```

- [ ] **Step 3: Add `paths` to auto-activate skill when editing `.ivy` files**

`skills/ivy-writing-guide/SKILL.md` — add to frontmatter:
```yaml
paths: "**/*.ivy"
```

This makes the skill auto-activate when Claude is working with `.ivy` files.

- [ ] **Step 4: Commit**

```bash
git add skills/*/SKILL.md
git commit -m "feat: add allowed-tools, context:fork, and paths to skill frontmatter"
```

---

### Task 12: Add agent frontmatter features

**Files:**
- Modify: `agents/navigator.md`
- Modify: `agents/methodology-guide.md`
- Modify: `agents/spec-analyst.md`
- Modify: `agents/model-reviewer.md`
- Modify: `agents/traceability-agent.md`

- [ ] **Step 1: Add `skills` preloading and `model` optimization to `navigator.md`**

```yaml
---
name: navigator
description: "Adaptive navigator agent for Ivy protocol testing. Detects user expertise, goals, and context to guide them through NCT/NACT/NSCT workflows with continuous interaction. Use when the user needs guidance on what to do next, wants to start a new testing workflow, or needs help choosing between approaches."
model: sonnet
color: green
tools: ["Read", "Grep", "Glob", "Bash", "ToolSearch"]
maxTurns: 10
skills:
  - adaptive-interview
  - interaction-patterns
---
```

Changes: `model: sonnet` (routing doesn't need Opus), removed Write/Edit (navigator routes, doesn't edit), added `maxTurns: 10`, added `skills` preload.

- [ ] **Step 2: Add features to `methodology-guide.md`**

```yaml
---
name: methodology-guide
description: "Use this agent when the user is working with NCT (compositional protocol testing), NACT (attack testing, security testing, APT lifecycle), or NSCT (simulation, Shadow NS, large-scale testing) methodology. Covers all three PANTHER formal testing methodologies."
model: sonnet
color: cyan
tools: ["Read", "Grep", "Glob", "Bash", "Write", "Edit", "ToolSearch"]
maxTurns: 30
skills:
  - methodology-reference
  - specification-patterns
  - workflow-reference
  - tooling-reference
  - interaction-patterns
---
```

Changes: `model: sonnet`, added `maxTurns: 30`, added `skills` preload.

- [ ] **Step 3: Add features to `spec-analyst.md`**

```yaml
---
name: spec-analyst
description: "Use this agent when the user wants to understand, explore, navigate, verify, diagnose, or debug Ivy protocol specifications. Handles both specification exploration (structure, dependencies, coverage) and verification (formal checking, compilation, error diagnosis)."
model: sonnet
color: blue
tools: ["Read", "Grep", "Glob", "Bash", "Write", "Edit", "ToolSearch"]
maxTurns: 25
skills:
  - workflow-reference
  - counterexample-guide
  - tooling-reference
  - interaction-patterns
---
```

- [ ] **Step 4: Add features to `model-reviewer.md`**

```yaml
---
name: model-reviewer
description: "Use this agent when the user asks to review Ivy formal specification models for correctness, completeness, or adherence to Ivy modeling best practices. Use before committing changes to .ivy files. **This agent should be used proactively** after writing or modifying `.ivy` files, especially before committing changes to the specification. When Claude has just edited `.ivy` files via Write or Edit tools, it should automatically dispatch this agent."
model: opus
color: magenta
tools: ["Read", "Grep", "Glob", "ToolSearch"]
maxTurns: 15
skills:
  - interaction-patterns
  - claim-discussion
---
```

Changes: `model: opus` (review requires deep reasoning), added `maxTurns: 15`, added `skills` preload.

- [ ] **Step 5: Add features to `traceability-agent.md`**

```yaml
---
name: traceability-agent
description: "Use this agent when the user wants to extract RFC requirements, create or update requirement manifests, review RFC coverage, analyze traceability gaps, or audit the mapping between RFC requirements and Ivy assertions. **This agent should be invoked proactively** after adding RFC bracket-tag annotations (`# [rfcNNNN:X.Y]`) to Ivy files, or after extracting new requirements from RFC text."
model: sonnet
color: orange
tools: ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "ToolSearch"]
maxTurns: 20
skills:
  - workflow-reference
  - tooling-reference
  - interaction-patterns
---
```

- [ ] **Step 6: Run manifest tests**

Run: `cd <plugin_root> && python -m pytest tests/test_manifests.py -v`

Expected: All tests pass (agent frontmatter fields are optional additions).

- [ ] **Step 7: Commit**

```bash
git add agents/*.md
git commit -m "feat: add skills preloading, model optimization, and maxTurns to all agents"
```

---

## Self-Review Checklist

1. **Spec coverage**: All items from the design proposal (A1-A8, B1-B2, C1-C4) have corresponding tasks.
2. **Placeholder scan**: No TBDs, TODOs, or "implement later" in any step. All code blocks are complete.
3. **Type consistency**: `emit_hook_output` signature matches across Task 9 steps. `resolve_session_id` signature matches across hook_utils creation and usage.
4. **File path consistency**: All paths are relative to plugin root as stated in the header.
5. **Test coverage**: Tasks 8, 9 include dedicated test files. Tasks 1-6 rely on existing tests plus manual verification.
