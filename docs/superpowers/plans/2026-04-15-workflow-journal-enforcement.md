# Workflow Journal Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an append-only workflow journal to track intermediate decisions, session lifecycle, progress, errors, and context switches across Ivy workflow sessions.

**Architecture:** New `workflow-journal.yaml` file per protocol directory, managed by journal helper functions (hook-side) and two new MCP actions (`append_journal`, `get_journal`). Hooks handle mechanical events automatically; skills handle semantic events via explicit instructions.

**Tech Stack:** Python 3.10+, PyYAML, Claude Code hooks (SessionStart, Stop, PostToolUse, UserPromptSubmit), MCP tool extensions

**Submodule layout:** All changes land in two git submodules:
- **panther-ivy-plugin** (`plugins/panther-ivy-plugin/`): hooks, skills, tests, hooks.json
- **ivy-lsp** (`submodules/ivy-lsp/`): MCP tool handler

Commit within each submodule separately, then update the submodule pointer in the PANTHER parent repo as a final task.

**Base paths (used throughout):**
- `PLUGIN` = `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin`
- `IVY_LSP` = `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp`

---

### Task 1: Journal helper functions in hook-side workflow_state.py

**Files:**
- Modify: `PLUGIN/hooks/scripts/workflow_state.py`
- Test: `PLUGIN/tests/test_workflow_state.py`

Add three functions to the existing `workflow_state.py` module: `append_journal_event()`, `get_journal_entries()`, and `rotate_journal()`.

- [ ] **Step 1: Write failing tests for journal helpers**

Add to `PLUGIN/tests/test_workflow_state.py`:

```python
import os
import yaml
from datetime import datetime, timezone

# --- Add these test classes after existing tests ---

class TestAppendJournalEvent:
    """Tests for append_journal_event()."""

    def test_creates_journal_file_on_first_append(self, protocol_dir):
        from workflow_state import append_journal_event

        append_journal_event(
            protocol_dir,
            event_type="session_start",
            payload={"resumed_from": None},
            workflow="build",
            phase="init",
        )
        journal_path = os.path.join(protocol_dir, ".panther-ivy", "workflow-journal.yaml")
        assert os.path.exists(journal_path)
        with open(journal_path) as f:
            entries = yaml.safe_load(f)
        assert len(entries) == 1
        assert entries[0]["type"] == "session_start"
        assert entries[0]["workflow"] == "build"
        assert entries[0]["phase"] == "init"
        assert entries[0]["payload"] == {"resumed_from": None}
        assert "ts" in entries[0]

    def test_appends_to_existing_journal(self, protocol_dir):
        from workflow_state import append_journal_event

        append_journal_event(protocol_dir, "session_start", {"resumed_from": None}, "build", "init")
        append_journal_event(protocol_dir, "decision", {"summary": "defer group D", "context": "needs 3-speaker"}, "build", "scoped")

        journal_path = os.path.join(protocol_dir, ".panther-ivy", "workflow-journal.yaml")
        with open(journal_path) as f:
            entries = yaml.safe_load(f)
        assert len(entries) == 2
        assert entries[1]["type"] == "decision"
        assert entries[1]["payload"]["summary"] == "defer group D"

    def test_rejects_invalid_event_type(self, protocol_dir):
        from workflow_state import append_journal_event

        result = append_journal_event(protocol_dir, "invalid_type", {}, "build", "init")
        assert result is False

    def test_allows_append_without_active_workflow(self, protocol_dir):
        from workflow_state import append_journal_event

        result = append_journal_event(protocol_dir, "session_start", {"resumed_from": None}, None, None)
        assert result is True
        journal_path = os.path.join(protocol_dir, ".panther-ivy", "workflow-journal.yaml")
        with open(journal_path) as f:
            entries = yaml.safe_load(f)
        assert entries[0]["workflow"] is None


class TestGetJournalEntries:
    """Tests for get_journal_entries()."""

    def test_returns_empty_list_when_no_journal(self, protocol_dir):
        from workflow_state import get_journal_entries

        entries = get_journal_entries(protocol_dir)
        assert entries == []

    def test_returns_last_n_entries(self, protocol_dir):
        from workflow_state import append_journal_event, get_journal_entries

        for i in range(10):
            append_journal_event(protocol_dir, "progress", {"detail": f"step {i}"}, "build", "init")

        entries = get_journal_entries(protocol_dir, last_n=3)
        assert len(entries) == 3
        assert entries[0]["payload"]["detail"] == "step 7"
        assert entries[2]["payload"]["detail"] == "step 9"

    def test_returns_all_when_fewer_than_last_n(self, protocol_dir):
        from workflow_state import append_journal_event, get_journal_entries

        append_journal_event(protocol_dir, "session_start", {"resumed_from": None}, "build", "init")
        entries = get_journal_entries(protocol_dir, last_n=20)
        assert len(entries) == 1


class TestRotateJournal:
    """Tests for rotate_journal()."""

    def test_rotates_when_exceeding_max_entries(self, protocol_dir):
        from workflow_state import append_journal_event, get_journal_entries, rotate_journal

        for i in range(210):
            append_journal_event(protocol_dir, "progress", {"detail": f"step {i}"}, "build", "init")

        rotate_journal(protocol_dir, max_entries=200)

        entries = get_journal_entries(protocol_dir, last_n=999)
        assert len(entries) == 100  # kept the newest half

        archive_dir = os.path.join(protocol_dir, ".panther-ivy", "journal-archive")
        assert os.path.isdir(archive_dir)
        archive_files = os.listdir(archive_dir)
        assert len(archive_files) == 1

    def test_no_rotation_when_under_max(self, protocol_dir):
        from workflow_state import append_journal_event, rotate_journal

        for i in range(50):
            append_journal_event(protocol_dir, "progress", {"detail": f"step {i}"}, "build", "init")

        rotate_journal(protocol_dir, max_entries=200)

        archive_dir = os.path.join(protocol_dir, ".panther-ivy", "journal-archive")
        assert not os.path.exists(archive_dir)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd PLUGIN && python -m pytest tests/test_workflow_state.py -v -k "TestAppendJournal or TestGetJournal or TestRotateJournal"`
Expected: FAIL — `ImportError: cannot import name 'append_journal_event'`

- [ ] **Step 3: Implement journal helper functions**

Add to `PLUGIN/hooks/scripts/workflow_state.py` after the existing constants:

```python
_JOURNAL_FILE = "workflow-journal.yaml"
_JOURNAL_ARCHIVE_DIR = "journal-archive"

_VALID_EVENT_TYPES = frozenset({
    "session_start",
    "session_end",
    "decision",
    "phase_transition",
    "progress",
    "error",
    "context_switch",
})
```

Add these functions at the end of the file (after `set_build_state`):

```python
def append_journal_event(
    protocol_dir: str,
    event_type: str,
    payload: dict,
    workflow: str | None,
    phase: str | None,
) -> bool:
    """Append a single event to the workflow journal.

    Args:
        protocol_dir: Path to the protocol directory.
        event_type: One of the valid event types.
        payload: Type-specific event data.
        workflow: Current workflow name (can be None for pre-activation events).
        phase: Current phase (can be None).

    Returns:
        True if the event was appended, False if the event type is invalid.
    """
    if event_type not in _VALID_EVENT_TYPES:
        return False

    state_path = _state_dir(protocol_dir)
    state_path.mkdir(parents=True, exist_ok=True)

    journal_path = state_path / _JOURNAL_FILE
    entries: list[dict] = []
    if journal_path.exists():
        try:
            with open(journal_path) as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    entries = loaded
        except (OSError, yaml.YAMLError):
            pass

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "workflow": workflow,
        "phase": phase,
        "payload": payload,
    }
    entries.append(entry)

    with open(journal_path, "w") as f:
        yaml.safe_dump(entries, f, default_flow_style=False)

    return True


def get_journal_entries(protocol_dir: str, last_n: int = 20) -> list[dict]:
    """Read the last N entries from the workflow journal.

    Args:
        protocol_dir: Path to the protocol directory.
        last_n: Number of recent entries to return.

    Returns:
        List of journal entry dicts, newest last.
    """
    journal_path = _state_dir(protocol_dir) / _JOURNAL_FILE
    if not journal_path.exists():
        return []
    try:
        with open(journal_path) as f:
            entries = yaml.safe_load(f)
            if not isinstance(entries, list):
                return []
            return entries[-last_n:] if last_n < len(entries) else entries
    except (OSError, yaml.YAMLError):
        return []


def rotate_journal(protocol_dir: str, max_entries: int = 200) -> None:
    """Archive oldest entries when journal exceeds max_entries.

    Moves the oldest half to ``journal-archive/YYYY-MM-DD.yaml``.

    Args:
        protocol_dir: Path to the protocol directory.
        max_entries: Threshold to trigger rotation.
    """
    journal_path = _state_dir(protocol_dir) / _JOURNAL_FILE
    if not journal_path.exists():
        return

    try:
        with open(journal_path) as f:
            entries = yaml.safe_load(f)
            if not isinstance(entries, list) or len(entries) <= max_entries:
                return
    except (OSError, yaml.YAMLError):
        return

    split_at = len(entries) // 2
    archive_entries = entries[:split_at]
    keep_entries = entries[split_at:]

    archive_dir = _state_dir(protocol_dir) / _JOURNAL_ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".yaml"
    archive_path = archive_dir / archive_name

    existing_archive: list[dict] = []
    if archive_path.exists():
        try:
            with open(archive_path) as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    existing_archive = loaded
        except (OSError, yaml.YAMLError):
            pass

    with open(archive_path, "w") as f:
        yaml.safe_dump(existing_archive + archive_entries, f, default_flow_style=False)

    with open(journal_path, "w") as f:
        yaml.safe_dump(keep_entries, f, default_flow_style=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd PLUGIN && python -m pytest tests/test_workflow_state.py -v -k "TestAppendJournal or TestGetJournal or TestRotateJournal"`
Expected: All PASS

- [ ] **Step 5: Commit in panther-ivy-plugin submodule**

```bash
cd PLUGIN
git add hooks/scripts/workflow_state.py tests/test_workflow_state.py
git commit -m "feat: add journal helper functions (append, get, rotate)"
```

---

### Task 2: MCP tool extensions (append_journal, get_journal)

**Files:**
- Modify: `IVY_LSP/ivy_lsp/mcp/tools/workflow_state.py`

- [ ] **Step 1: Update the Literal type and add new constants**

In `IVY_LSP/ivy_lsp/mcp/tools/workflow_state.py`, update the action Literal type and add journal constants after the existing constants:

```python
_JOURNAL_FILE = "workflow-journal.yaml"
_JOURNAL_ARCHIVE_DIR = "journal-archive"

_VALID_EVENT_TYPES = frozenset({
    "session_start",
    "session_end",
    "decision",
    "phase_transition",
    "progress",
    "error",
    "context_switch",
})
```

- [ ] **Step 2: Update the tool function signature**

Change the `action` parameter type from:
```python
action: Literal["set", "get", "clear", "get_build", "set_build"],
```
to:
```python
action: Literal["set", "get", "clear", "get_build", "set_build", "append_journal", "get_journal"],
```

Add a new parameter `event_type: str | None = None` and `last_n: int = 20` to the function signature. Also add `payload: str | None = None` (JSON string for journal payload).

Update the docstring Args section to include:
```
event_type: For action="append_journal": event type (e.g. "decision", "error").
payload: For action="append_journal": JSON-encoded event payload dict.
last_n: For action="get_journal": number of recent entries (default 20).
```

- [ ] **Step 3: Add routing in the tool function body**

Add these two elif branches after the `set_build` branch:

```python
elif action == "append_journal":
    return _handle_append_journal(ctx, protocol, event_type, state)
elif action == "get_journal":
    return _handle_get_journal(ctx, protocol, last_n)
```

Update the error message to include the new actions:
```python
return error_response(
    f"Unknown action '{action}'. "
    "Valid: set, get, clear, get_build, set_build, append_journal, get_journal."
)
```

- [ ] **Step 4: Implement _handle_append_journal**

Add after `_handle_set_build`:

```python
def _handle_append_journal(
    ctx: Any,
    protocol: str | None,
    event_type: str | None,
    payload_json: str | None,
) -> dict:
    if not event_type:
        return error_response("action='append_journal' requires 'event_type' parameter.")
    if event_type not in _VALID_EVENT_TYPES:
        return error_response(
            f"Invalid event_type '{event_type}'. "
            f"Valid: {', '.join(sorted(_VALID_EVENT_TYPES))}."
        )

    payload: dict = {}
    if payload_json:
        try:
            payload = json.loads(payload_json)
        except (json.JSONDecodeError, TypeError) as exc:
            return error_response(f"Invalid JSON in 'payload' parameter: {exc}")
        if not isinstance(payload, dict):
            return error_response("'payload' must be a JSON object.")

    protocol_dir = _resolve_protocol_dir(ctx, protocol)
    if protocol_dir is None:
        return error_response(
            "Cannot resolve protocol directory. "
            "Provide 'protocol' parameter or set an active workspace."
        )

    state_path = _ensure_state_dir(protocol_dir)

    # Read current workflow context for auto-fill
    workflow = None
    phase = None
    active_path = os.path.join(state_path, _ACTIVE_WORKFLOW_FILE)
    if os.path.exists(active_path):
        try:
            with open(active_path) as f:
                active_data = yaml.safe_load(f)
            if isinstance(active_data, dict):
                workflow = active_data.get("workflow")
                phase = active_data.get("phase")
        except (OSError, yaml.YAMLError):
            pass

    # Read existing journal
    journal_path = os.path.join(state_path, _JOURNAL_FILE)
    entries: list[dict] = []
    if os.path.exists(journal_path):
        try:
            with open(journal_path) as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    entries = loaded
        except (OSError, yaml.YAMLError):
            pass

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "workflow": workflow,
        "phase": phase,
        "payload": payload,
    }
    entries.append(entry)

    with open(journal_path, "w") as f:
        yaml.safe_dump(entries, f, default_flow_style=False)

    # Auto-rotate if needed
    if len(entries) > 200:
        _rotate_journal(state_path, entries)

    logger.info("Journal event appended: %s in %s", event_type, protocol_dir)
    return {
        "success": True,
        "action": "append_journal",
        "protocol_dir": protocol_dir,
        "event": entry,
    }


def _rotate_journal(state_path: str, entries: list[dict]) -> None:
    """Archive oldest half of journal entries."""
    split_at = len(entries) // 2
    archive_entries = entries[:split_at]
    keep_entries = entries[split_at:]

    archive_dir = os.path.join(state_path, _JOURNAL_ARCHIVE_DIR)
    os.makedirs(archive_dir, exist_ok=True)
    archive_name = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".yaml"
    archive_path = os.path.join(archive_dir, archive_name)

    existing: list[dict] = []
    if os.path.exists(archive_path):
        try:
            with open(archive_path) as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    existing = loaded
        except (OSError, yaml.YAMLError):
            pass

    with open(archive_path, "w") as f:
        yaml.safe_dump(existing + archive_entries, f, default_flow_style=False)

    journal_path = os.path.join(state_path, _JOURNAL_FILE)
    with open(journal_path, "w") as f:
        yaml.safe_dump(keep_entries, f, default_flow_style=False)
```

- [ ] **Step 5: Implement _handle_get_journal**

Add after `_handle_append_journal`:

```python
def _handle_get_journal(
    ctx: Any,
    protocol: str | None,
    last_n: int = 20,
) -> dict:
    protocol_dir = _resolve_protocol_dir(ctx, protocol)
    if protocol_dir is None:
        return {
            "success": True,
            "action": "get_journal",
            "entries": [],
            "message": "No protocol directory resolved.",
        }

    journal_path = os.path.join(_state_dir(protocol_dir), _JOURNAL_FILE)
    if not os.path.exists(journal_path):
        return {
            "success": True,
            "action": "get_journal",
            "entries": [],
            "count": 0,
            "protocol_dir": protocol_dir,
        }

    try:
        with open(journal_path) as f:
            entries = yaml.safe_load(f)
            if not isinstance(entries, list):
                entries = []
    except (OSError, yaml.YAMLError):
        entries = []

    result_entries = entries[-last_n:] if last_n < len(entries) else entries
    return {
        "success": True,
        "action": "get_journal",
        "entries": result_entries,
        "count": len(result_entries),
        "total": len(entries),
        "protocol_dir": protocol_dir,
    }
```

- [ ] **Step 6: Run existing workflow_state tests to verify no regressions**

Run: `cd IVY_LSP && python -m pytest tests/ -v -k "workflow_state"`
Expected: All existing tests PASS

- [ ] **Step 7: Commit in ivy-lsp submodule**

```bash
cd IVY_LSP
git add ivy_lsp/mcp/tools/workflow_state.py
git commit -m "feat: add append_journal and get_journal MCP actions"
```

---

### Task 3: SessionStart hook — journal session_start event

**Files:**
- Modify: `PLUGIN/hooks/scripts/cleanup-stale-workflow.py`

- [ ] **Step 1: Add journal import**

Add `append_journal_event` to the existing import from `workflow_state`:

```python
from workflow_state import (
    append_journal_event,
    clear_active_workflow,
    find_protocol_dir,
    get_active_workflow,
    is_workflow_stale,
)
```

- [ ] **Step 2: Add journal event after staleness check**

Replace the `main()` function body (after `protocol_dir` and `active` checks) to append journal events:

```python
def main() -> None:
    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        return

    active = get_active_workflow(protocol_dir)
    if not active:
        append_journal_event(
            protocol_dir,
            event_type="session_start",
            payload={"resumed_from": None},
            workflow=None,
            phase=None,
        )
        return

    if is_workflow_stale(protocol_dir):
        append_journal_event(
            protocol_dir,
            event_type="session_start",
            payload={"resumed_from": active.get("phase"), "stale_cleared": True},
            workflow=active.get("workflow"),
            phase=active.get("phase"),
        )
        clear_active_workflow(protocol_dir)
        emit_hook_output(
            "SessionStart",
            additional_context=(
                f"Cleared stale workflow '{active.get('workflow', '?')}' "
                f"(phase: {active.get('phase', '?')}) from a previous session."
            ),
        )
    else:
        append_journal_event(
            protocol_dir,
            event_type="session_start",
            payload={"resumed_from": active.get("phase")},
            workflow=active.get("workflow"),
            phase=active.get("phase"),
        )
        emit_hook_output(
            "SessionStart",
            additional_context=(
                f"Active workflow: {active.get('workflow', '?')} "
                f"(phase: {active.get('phase', '?')})"
            ),
        )
```

- [ ] **Step 3: Verify the hook runs correctly**

Run: `cd PLUGIN/hooks/scripts && echo '{}' | python3 cleanup-stale-workflow.py`
Expected: No crash (may produce no output if no protocol dir is found in cwd)

- [ ] **Step 4: Commit in panther-ivy-plugin submodule**

```bash
cd PLUGIN
git add hooks/scripts/cleanup-stale-workflow.py
git commit -m "feat: append session_start journal event on SessionStart hook"
```

---

### Task 4: Stop hook — journal session_end event

**Files:**
- Create: `PLUGIN/hooks/scripts/record-session-end.py`
- Modify: `PLUGIN/hooks/hooks.json`

- [ ] **Step 1: Create the Stop hook script**

Create `PLUGIN/hooks/scripts/record-session-end.py`:

```python
#!/usr/bin/env python3
"""Stop hook: record session_end event in workflow journal.

Appends a session_end event when Claude's turn ends and a workflow is active.
Non-blocking -- always exits 0.
"""

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"
    ),
)
from hook_utils import read_stdin
from workflow_state import (
    append_journal_event,
    find_protocol_dir,
    get_active_workflow,
    rotate_journal,
)


def main() -> None:
    read_stdin()  # consume stdin

    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        return

    active = get_active_workflow(protocol_dir)
    if not active:
        return

    append_journal_event(
        protocol_dir,
        event_type="session_end",
        payload={
            "clean": True,
            "phase_at_exit": active.get("phase", "unknown"),
        },
        workflow=active.get("workflow"),
        phase=active.get("phase"),
    )

    rotate_journal(protocol_dir)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Register in hooks.json**

In `PLUGIN/hooks/hooks.json`, add a new entry to the `"Stop"` array, BEFORE the existing `render-summary.py` entry (so journal is written before summary reads it):

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/record-session-end.py",
      "timeout": 5
    }
  ]
}
```

The `"Stop"` array should now look like:

```json
"Stop": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/record-session-end.py",
        "timeout": 5
      }
    ]
  },
  {
    "hooks": [
      {
        "type": "command",
        "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/render-summary.py",
        "timeout": 10
      }
    ]
  },
  {
    "hooks": [
      {
        "type": "command",
        "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/observability/observe.py --event Stop",
        "timeout": 5
      }
    ]
  }
]
```

- [ ] **Step 3: Verify the hook runs without error**

Run: `cd PLUGIN/hooks/scripts && echo '{}' | python3 record-session-end.py`
Expected: No crash, exits 0

- [ ] **Step 4: Commit in panther-ivy-plugin submodule**

```bash
cd PLUGIN
git add hooks/scripts/record-session-end.py hooks/hooks.json
git commit -m "feat: add Stop hook to record session_end journal events"
```

---

### Task 5: PostToolUse hook — journal phase_transition event

**Files:**
- Modify: `PLUGIN/hooks/scripts/track-workflow-skill.py`

- [ ] **Step 1: Add journal import and previous-phase tracking**

Add import at the top (after existing imports from `workflow_state`):

```python
from workflow_state import resolve_protocol_from_workspace, find_protocol_dir, get_active_workflow, append_journal_event
```

- [ ] **Step 2: Add phase_transition journaling**

After the existing code that writes the `active-workflow` file (after the `yaml.safe_dump` / fallback write block), and before the `emit_hook_output` call, add:

```python
    # Record phase transition in journal if workflow was already active
    if previous_phase is not None and previous_phase != "init":
        append_journal_event(
            protocol_dir,
            event_type="phase_transition",
            payload={"from": previous_phase, "to": "init"},
            workflow=workflow_name,
            phase="init",
        )
```

Also, before the state directory creation block, read the previous phase:

```python
    # Read previous phase for transition tracking
    previous_state = get_active_workflow(protocol_dir)
    previous_phase = previous_state.get("phase") if previous_state else None
```

- [ ] **Step 3: Verify the hook runs without error**

Run: `cd PLUGIN/hooks/scripts && echo '{"tool_name":"Skill","tool_input":{"skill":"panther-ivy-plugin:build","args":"bgp"}}' | python3 track-workflow-skill.py`
Expected: No crash (may emit hook output or not depending on protocol dir resolution)

- [ ] **Step 4: Commit in panther-ivy-plugin submodule**

```bash
cd PLUGIN
git add hooks/scripts/track-workflow-skill.py
git commit -m "feat: record phase_transition journal events in track-workflow-skill hook"
```

---

### Task 6: PostToolUse hook — journal error events

**Files:**
- Create: `PLUGIN/hooks/scripts/record-workflow-error.py`
- Modify: `PLUGIN/hooks/hooks.json`

- [ ] **Step 1: Create the error detection hook**

Create `PLUGIN/hooks/scripts/record-workflow-error.py`:

```python
#!/usr/bin/env python3
"""PostToolUse hook: record error events in workflow journal during active workflows.

Detects compilation failures, verification failures, and tool errors from
MCP tool results when a workflow is active.
Non-blocking -- always exits 0.
"""

import os
import re
import sys

sys.path.insert(
    0,
    os.path.join(
        os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"
    ),
)
from hook_utils import read_stdin
from workflow_state import (
    append_journal_event,
    find_protocol_dir,
    get_active_workflow,
)

_ERROR_PATTERNS = [
    (re.compile(r"compilation failed", re.IGNORECASE), "Ivy compilation failed"),
    (re.compile(r"FAIL\b.*isolate", re.IGNORECASE), "Verification failure"),
    (re.compile(r"error:.*\.ivy", re.IGNORECASE), "Ivy file error"),
    (re.compile(r'"success":\s*false', re.IGNORECASE), "MCP tool returned failure"),
    (re.compile(r"timeout", re.IGNORECASE), "Operation timed out"),
]

_WATCHED_TOOLS = {
    "ivy_verify", "ivy_compile", "ivy_diagnostics",
    "ivy_coverage", "ivy_iut_test", "ivy_quality",
}


def _extract_error_summary(tool_result: str) -> str | None:
    """Check tool result for error patterns and return summary."""
    for pattern, summary in _ERROR_PATTERNS:
        if pattern.search(tool_result):
            return summary
    return None


def main() -> None:
    hook_input = read_stdin()
    tool_name = hook_input.get("tool_name", "")

    if tool_name not in _WATCHED_TOOLS:
        return

    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        return

    active = get_active_workflow(protocol_dir)
    if not active:
        return

    tool_result = hook_input.get("tool_result", "")
    if isinstance(tool_result, dict):
        import json
        tool_result = json.dumps(tool_result)

    error_summary = _extract_error_summary(str(tool_result))
    if not error_summary:
        return

    append_journal_event(
        protocol_dir,
        event_type="error",
        payload={
            "summary": error_summary,
            "tool": tool_name,
            "recoverable": True,
        },
        workflow=active.get("workflow"),
        phase=active.get("phase"),
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Register in hooks.json**

Add a new entry to the `"PostToolUse"` array in `PLUGIN/hooks/hooks.json`:

```json
{
  "matcher": "ivy_verify|ivy_compile|ivy_diagnostics|ivy_coverage|ivy_iut_test|ivy_quality",
  "hooks": [
    {
      "type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/record-workflow-error.py",
      "timeout": 5
    }
  ]
}
```

Place it after the existing `render-tool-result.py` entry (around line 128).

- [ ] **Step 3: Verify the hook runs without error**

Run: `cd PLUGIN/hooks/scripts && echo '{"tool_name":"ivy_verify","tool_result":"compilation failed: error in bgp_fsm.ivy"}' | python3 record-workflow-error.py`
Expected: No crash, exits 0

- [ ] **Step 4: Commit in panther-ivy-plugin submodule**

```bash
cd PLUGIN
git add hooks/scripts/record-workflow-error.py hooks/hooks.json
git commit -m "feat: add PostToolUse hook to record error journal events"
```

---

### Task 7: UserPromptSubmit hook — journal context_switch events

**Files:**
- Modify: `PLUGIN/hooks/scripts/route-user-prompt.py`

- [ ] **Step 1: Add journal import**

Add `append_journal_event` to the import from `workflow_state`:

```python
from workflow_state import find_protocol_dir, get_active_workflow, append_journal_event
```

- [ ] **Step 2: Add context_switch detection**

In the `main()` function, after the block that checks whether the best match is the same as active workflow (around line 138, where it does `if active_workflow_name in best_names: return`), add context_switch journaling when the user's intent diverges from the active workflow:

Find the block:
```python
    if active_workflow_name and scored and not prompt_has_switch_intent(prompt_lower):
        best_names = [name for s, name in scored if s == scored[0][0]]
        if active_workflow_name in best_names:
            return
```

After this block, add:

```python
    # Record context switch when active workflow doesn't match best intent
    if active_workflow_name and scored:
        best_names = [name for s, name in scored if s == scored[0][0]]
        if active_workflow_name not in best_names and protocol_dir:
            append_journal_event(
                protocol_dir,
                event_type="context_switch",
                payload={
                    "away_from": active_workflow_name,
                    "reason": f"user intent matched: {best_names[0]}" if best_names else None,
                },
                workflow=active_workflow_name,
                phase=None,
            )
```

- [ ] **Step 3: Verify the hook runs without error**

Run: `cd PLUGIN/hooks/scripts && echo '{"prompt":"check my health"}' | python3 route-user-prompt.py`
Expected: No crash, exits 0

- [ ] **Step 4: Commit in panther-ivy-plugin submodule**

```bash
cd PLUGIN
git add hooks/scripts/route-user-prompt.py
git commit -m "feat: record context_switch journal events in route-user-prompt hook"
```

---

### Task 8: Stop hook — journal audit in render-summary.py

**Files:**
- Modify: `PLUGIN/hooks/scripts/render-summary.py`

- [ ] **Step 1: Add journal import**

Add `get_journal_entries` to the import from `workflow_state`:

```python
from workflow_state import find_protocol_dir, get_active_workflow, get_build_state, get_journal_entries
```

- [ ] **Step 2: Add journal audit function**

Add after the `gather_tool_metrics()` function:

```python
def audit_journal(protocol_dir: str, workflow: str | None) -> list[str]:
    """Check for gaps in journal entries during this session.

    Returns:
        List of warning strings (empty if no issues found).
    """
    if not workflow:
        return []

    entries = get_journal_entries(protocol_dir, last_n=50)
    if not entries:
        return ["No journal entries for this session. Workflow state tracking may be incomplete."]

    warnings: list[str] = []

    session_starts = [e for e in entries if e.get("type") == "session_start"]
    if not session_starts:
        warnings.append("No session_start event found. SessionStart hook may not have fired.")

    decisions = [e for e in entries if e.get("type") == "decision"]
    phase_transitions = [e for e in entries if e.get("type") == "phase_transition"]

    if workflow == "build" and not decisions:
        build_state = get_build_state(protocol_dir)
        if build_state and build_state.get("decisions"):
            warnings.append(
                "Build state has decisions but no decision events were journaled this session."
            )

    return warnings
```

- [ ] **Step 3: Integrate audit into build_summary**

In the `build_summary()` function, after the tool metrics section and before the knowledge gate section, add:

```python
    # Journal audit
    if protocol_dir and workflow:
        audit_warnings = audit_journal(protocol_dir, workflow)
        if audit_warnings:
            warning_lines = ["[JOURNAL AUDIT]"] + [f"  - {w}" for w in audit_warnings]
            parts.append("\n".join(warning_lines))
```

- [ ] **Step 4: Verify the hook runs without error**

Run: `cd PLUGIN/hooks/scripts && echo '{}' | python3 render-summary.py`
Expected: No crash, exits 0

- [ ] **Step 5: Commit in panther-ivy-plugin submodule**

```bash
cd PLUGIN
git add hooks/scripts/render-summary.py
git commit -m "feat: add journal audit warnings to session summary"
```

---

### Task 9: Skill updates — add journaling instructions

**Files:**
- Modify: `PLUGIN/skills/build/SKILL.md`
- Modify: `PLUGIN/skills/verify/SKILL.md`
- Modify: `PLUGIN/skills/review/SKILL.md`
- Modify: `PLUGIN/skills/triage/SKILL.md`
- Modify: `PLUGIN/skills/navigate/SKILL.md`

- [ ] **Step 1: Add journaling instruction block to build skill**

Add at the top of `PLUGIN/skills/build/SKILL.md`, after the Critical Rules section and before the Phase Flow:

```markdown
### Journal Requirements

Throughout this workflow, record state changes to the workflow journal:

- **Decisions**: When you make or confirm a design/implementation choice (e.g., deferring a requirement, choosing layer order, selecting methodology), immediately call:
  `ivy_workflow_state(action="append_journal", protocol="<protocol>", event_type="decision", payload='{"summary": "<what was decided>", "context": "<why>"}')`

- **Progress**: After completing a meaningful sub-step (e.g., "compiled 3/8 layers", "fixed 2 verification failures"), call:
  `ivy_workflow_state(action="append_journal", protocol="<protocol>", event_type="progress", payload='{"detail": "<what completed>"}')`

These journal entries enable warm session resume and decision traceability across sessions.
```

- [ ] **Step 2: Add the same journaling block to verify, review, and triage skills**

Add the identical `### Journal Requirements` block to each of:
- `PLUGIN/skills/verify/SKILL.md` (after any Critical Rules / before Phase Flow)
- `PLUGIN/skills/review/SKILL.md` (after any Critical Rules / before Phase Flow)
- `PLUGIN/skills/triage/SKILL.md` (after any Critical Rules / before Phase Flow)

- [ ] **Step 3: Add journal-aware warm resume to navigate skill**

In `PLUGIN/skills/navigate/SKILL.md`, in the Phase 1 — Silent Context Scan section, after the existing step that checks build state (step 2), add a new step:

```markdown
**Step 2b: Check workflow journal**
Call `ivy_workflow_state(action="get_journal", protocol="<protocol>", last_n=20)`.

If journal entries exist, compose a session context summary for the situation briefing:
- Count decisions, errors, progress events
- Check if last session ended cleanly (look for `session_end` with `clean: true`)
- If no `session_end` exists after the last `session_start`, the previous session was interrupted

Include this summary in the Situation Briefing: "Last session: [N] decisions, [M] errors, ended [cleanly/interrupted] at phase [phase]."
```

Also update Branch A (Warm Resume) to include:

```markdown
4. **Skip redundant questions** — if journal contains `decision` events, present them as confirmed decisions rather than re-asking.
5. **Flag errors** — if journal contains recent `error` events, present them upfront as potential blockers.
```

- [ ] **Step 4: Commit in panther-ivy-plugin submodule**

```bash
cd PLUGIN
git add skills/build/SKILL.md skills/verify/SKILL.md skills/review/SKILL.md skills/triage/SKILL.md skills/navigate/SKILL.md
git commit -m "feat: add journal requirements to all workflow skills"
```

---

### Task 10: Update submodule pointers in PANTHER parent

**Files:**
- Update submodule pointers for both panther-ivy-plugin and ivy-lsp

- [ ] **Step 1: Verify all submodule commits are clean**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git log --oneline -5

cd ../ivy-lsp
git log --oneline -5
```

- [ ] **Step 2: Update submodule pointers in parent repo**

```bash
cd <repo-root>
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git commit -m "chore: update panther-ivy-plugin and ivy-lsp submodules for workflow journal enforcement"
```

- [ ] **Step 3: Run full test suite to verify no regressions**

```bash
cd PLUGIN && python -m pytest tests/ -v
```
Expected: All tests PASS
