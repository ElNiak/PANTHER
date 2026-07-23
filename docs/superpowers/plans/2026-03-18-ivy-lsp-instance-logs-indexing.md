# Ivy LSP Per-Instance Logs + Indexing Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each ivy-lsp server instance its own timestamped log file and add hooks so Claude knows when indexing completes.

**Architecture:** Shell scripts generate `ivy-lsp-<timestamp>-<pid>.log` filenames with a `ivy-lsp-latest.log` symlink. A SessionStart hook polls for the indexing milestone; a PreToolUse hook warns if MCP tools fire before indexing is done. MCP tool model-status feedback already exists in `traceability.py:38-58` via `_model_unavailable_response()`.

**Design note — 30s SessionStart blocking:** The `wait-for-indexing.sh` hook polls for up to 30s (configurable via `IVY_LSP_INDEX_TIMEOUT`). For the QUIC workspace (~50 files), Phase 1 finishes in 2-5s. The 30s cap is generous for larger workspaces. This is intentional — Claude receives degraded results without it.

**Note — dual `mcp__.*ivy` matchers:** Both `check_lsp_log.py` (error surfacing) and `check-indexing-ready.sh` (indexing guard) use the `mcp__.*ivy` matcher. Claude Code runs all matching hooks, so both fire on every MCP ivy tool call. This is by design — they serve complementary purposes.

**Note — `$$` PID:** The `$$` in log filenames captures the shell PID (which `exec` replaces with `uvx`). This provides log uniqueness per launch, not an exact ivy_lsp PID.

**Tech Stack:** Bash (shell scripts, hooks), Python (check_lsp_log.py), JSON (hooks.json)

**Key base paths** (all relative to worktree root):
- `PIV` = `panther/plugins/services/testers/panther_ivy`
- `PLUGIN` = `${PIV}/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin`
- `IVY_LSP_PLUGIN` = `${PIV}/submodules/panther-ivy-plugin/plugins/ivy-lsp`

---

### Task 1: Per-Instance Log Filename in `lsp-start.sh`

**Files:**
- Modify: `${IVY_LSP_PLUGIN}/lsp-start.sh` (line 9)

- [ ] **Step 1: Read current file**

Read `${IVY_LSP_PLUGIN}/lsp-start.sh` to confirm current state.

- [ ] **Step 2: Replace the LOG_FILE line**

Replace line 9:
```bash
LOG_FILE="${IVY_LSP_LOG_FILE:-/tmp/ivy-lsp.log}"
```

With:
```bash
_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-lsp-${_IVY_LOG_TS}-$$.log}"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"
```

- [ ] **Step 3: Verify script syntax**

Run: `bash -n ${IVY_LSP_PLUGIN}/lsp-start.sh`
Expected: Exit 0, no output (valid syntax)

- [ ] **Step 4: Commit**

```bash
git add ${IVY_LSP_PLUGIN}/lsp-start.sh
git commit -m "feat(ivy-lsp): per-instance log filename in lsp-start.sh"
```

---

### Task 2: Per-Instance Log Filename in `start-ivy-tools.sh`

**Files:**
- Modify: `${PLUGIN}/scripts/start-ivy-tools.sh` (line 18)

- [ ] **Step 1: Read current file**

Read `${PLUGIN}/scripts/start-ivy-tools.sh` to confirm current state.

- [ ] **Step 2: Replace the LOG_FILE line**

Replace line 18:
```bash
LOG_FILE="${IVY_LSP_LOG_FILE:-/tmp/ivy-lsp.log}"
```

With:
```bash
_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-lsp-${_IVY_LOG_TS}-$$.log}"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"
```

- [ ] **Step 3: Verify script syntax**

Run: `bash -n ${PLUGIN}/scripts/start-ivy-tools.sh`
Expected: Exit 0

- [ ] **Step 4: Commit**

```bash
git add ${PLUGIN}/scripts/start-ivy-tools.sh
git commit -m "feat(ivy-tools): per-instance log filename in start-ivy-tools.sh"
```

---

### Task 3: Per-Instance Log Filename in `ivy-lsp-wrapper.sh`

**Files:**
- Modify: `${PLUGIN}/scripts/ivy-lsp-wrapper.sh` (line 14)

- [ ] **Step 1: Read current file**

Read `${PLUGIN}/scripts/ivy-lsp-wrapper.sh` to confirm current state.

- [ ] **Step 2: Replace the LOG_FILE line**

Replace line 14:
```bash
LOG_FILE="${IVY_LSP_LOG_FILE:-/tmp/ivy-lsp.log}"
```

With:
```bash
_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-lsp-${_IVY_LOG_TS}-$$.log}"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"
```

- [ ] **Step 3: Verify script syntax**

Run: `bash -n ${PLUGIN}/scripts/ivy-lsp-wrapper.sh`
Expected: Exit 0

- [ ] **Step 4: Commit**

```bash
git add ${PLUGIN}/scripts/ivy-lsp-wrapper.sh
git commit -m "feat(ivy-lsp): per-instance log filename in ivy-lsp-wrapper.sh"
```

---

### Task 4: Update `check_lsp_log.py` Default Path

**Files:**
- Modify: `${PLUGIN}/hooks/scripts/observability/check_lsp_log.py` (line 14)

- [ ] **Step 1: Read current file**

Read `${PLUGIN}/hooks/scripts/observability/check_lsp_log.py` to confirm current state.

- [ ] **Step 2: Change default log path (line 14)**

Replace line 14:
```python
LOG_PATH = os.environ.get("IVY_LSP_LOG_PATH", "/tmp/ivy-lsp.log")
```

With:
```python
LOG_PATH = os.environ.get("IVY_LSP_LOG_PATH", "/tmp/ivy-lsp-latest.log")
```

- [ ] **Step 3: Update docstring (line 4)**

Replace:
```python
Reads the last 50 lines of /tmp/ivy-lsp.log and filters for CRITICAL,
```

With:
```python
Reads the last 50 lines of /tmp/ivy-lsp-latest.log and filters for CRITICAL,
```

- [ ] **Step 4: Commit**

```bash
git add ${PLUGIN}/hooks/scripts/observability/check_lsp_log.py
git commit -m "fix(hooks): check_lsp_log reads ivy-lsp-latest.log symlink"
```

---

### Task 5: Update `nct-health.md` Log Path References

**Files:**
- Modify: `${PLUGIN}/commands/nct-health.md`

- [ ] **Step 1: Read current file**

Read `${PLUGIN}/commands/nct-health.md` and search for `/tmp/ivy-lsp.log`.

- [ ] **Step 2: Replace all occurrences**

Replace all `/tmp/ivy-lsp.log` with `/tmp/ivy-lsp-latest.log` using `replace_all`.

- [ ] **Step 3: Commit**

```bash
git add ${PLUGIN}/commands/nct-health.md
git commit -m "docs(nct-health): update log path to ivy-lsp-latest.log"
```

---

### Task 6: Update `nct-validate.md` Log Path References

**Files:**
- Modify: `${PLUGIN}/commands/nct-validate.md`

- [ ] **Step 1: Read current file and search for log path references**

Grep for `/tmp/ivy-lsp.log` in the file.

- [ ] **Step 2: Replace all occurrences**

Replace all `/tmp/ivy-lsp.log` with `/tmp/ivy-lsp-latest.log` using `replace_all`.

- [ ] **Step 3: Commit**

```bash
git add ${PLUGIN}/commands/nct-validate.md
git commit -m "docs(nct-validate): update log path to ivy-lsp-latest.log"
```

---

### Task 7: Update Plugin CLAUDE.md Log Reference

**Files:**
- Modify: `${PLUGIN}/CLAUDE.md`

- [ ] **Step 1: Read current file and find log path references**

Grep for `ivy-lsp.log` or `/tmp/ivy-lsp` in the file.

- [ ] **Step 2: Update references**

Replace `/tmp/ivy-lsp.log` with `/tmp/ivy-lsp-latest.log` (symlink to current instance).
Add note about per-instance log naming: `ivy-lsp-<timestamp>-<pid>.log`.

- [ ] **Step 3: Commit**

```bash
git add ${PLUGIN}/CLAUDE.md
git commit -m "docs: update CLAUDE.md log path to ivy-lsp-latest.log"
```

---

### Task 8: Propagate Log Path via SessionStart Hook

**Files:**
- Modify: `${PLUGIN}/hooks/scripts/detect-ivy-workspace.sh` (line 17-19)

- [ ] **Step 1: Read current file**

Read `${PLUGIN}/hooks/scripts/detect-ivy-workspace.sh`.

- [ ] **Step 2: Add log path to CLAUDE_ENV_FILE**

After line 19 (`printf 'IVY_WORKSPACE_ROOT=...'`), add:
```bash
    # Propagate log symlink path so downstream hooks find the right log
    printf 'IVY_LSP_LOG_PATH="%s"\n' "${IVY_LSP_LOG_DIR:-/tmp}/ivy-lsp-latest.log" >> "$CLAUDE_ENV_FILE"
```

- [ ] **Step 3: Verify script syntax**

Run: `bash -n ${PLUGIN}/hooks/scripts/detect-ivy-workspace.sh`
Expected: Exit 0

- [ ] **Step 4: Commit**

```bash
git add ${PLUGIN}/hooks/scripts/detect-ivy-workspace.sh
git commit -m "feat(hooks): propagate IVY_LSP_LOG_PATH to CLAUDE_ENV_FILE"
```

---

### Task 9: Create SessionStart Indexing Wait Hook

**Files:**
- Create: `${PLUGIN}/hooks/scripts/wait-for-indexing.sh`

- [ ] **Step 1: Create the hook script**

```bash
#!/usr/bin/env bash
# SessionStart hook: wait for ivy-lsp indexing to complete.
#
# Polls the LSP log for the "Indexed N files" milestone (logged by
# server_setup.py after Phase 1 fast-index).  Surfaces indexing status
# as additionalContext so Claude knows the workspace is ready.
set -euo pipefail

LOG_FILE="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-latest.log}"
MAX_WAIT="${IVY_LSP_INDEX_TIMEOUT:-30}"

for _i in $(seq 1 "$MAX_WAIT"); do
    if [ -f "$LOG_FILE" ] && grep -q "Indexed .* files" "$LOG_FILE" 2>/dev/null; then
        INDEXED_LINE=$(grep "Indexed .* files" "$LOG_FILE" | tail -1)
        # Escape for JSON
        ESCAPED=$(printf '%s' "$INDEXED_LINE" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])" 2>/dev/null || echo "$INDEXED_LINE")
        cat <<EOFJ
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "[ivy-indexing] $ESCAPED. Workspace ready."
  }
}
EOFJ
        exit 0
    fi
    sleep 1
done

# Timeout — warn but don't block
cat <<EOFJ
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "[ivy-indexing] WARNING: Indexing did not complete within ${MAX_WAIT}s. MCP tools may return incomplete results until indexing finishes."
  }
}
EOFJ
```

- [ ] **Step 2: Make executable**

Run: `chmod +x ${PLUGIN}/hooks/scripts/wait-for-indexing.sh`

- [ ] **Step 3: Commit**

```bash
git add ${PLUGIN}/hooks/scripts/wait-for-indexing.sh
git commit -m "feat(hooks): add SessionStart hook to wait for LSP indexing"
```

---

### Task 10: Create PreToolUse Indexing Guard Hook

**Files:**
- Create: `${PLUGIN}/hooks/scripts/check-indexing-ready.sh`

- [ ] **Step 1: Create the hook script**

```bash
#!/usr/bin/env bash
# PreToolUse hook: warn if ivy-lsp indexing has not completed.
#
# Quick check — reads the LSP log symlink for the indexing milestone.
# Always allows the tool call (never blocks); surfaces a warning if
# indexing appears incomplete.
set -euo pipefail

LOG_FILE="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-latest.log}"

# Fast path: log exists and has indexing milestone → allow silently
if [ -f "$LOG_FILE" ] && grep -q "Indexed .* files" "$LOG_FILE" 2>/dev/null; then
    echo '{"decision":"allow"}'
    exit 0
fi

# No milestone found — warn but allow
echo '{"decision":"allow","message":"WARNING: Ivy workspace may not be fully indexed yet. MCP tool results could be incomplete."}'
```

- [ ] **Step 2: Make executable**

Run: `chmod +x ${PLUGIN}/hooks/scripts/check-indexing-ready.sh`

- [ ] **Step 3: Commit**

```bash
git add ${PLUGIN}/hooks/scripts/check-indexing-ready.sh
git commit -m "feat(hooks): add PreToolUse indexing guard hook"
```

---

### Task 11: Register New Hooks in `hooks.json`

**Files:**
- Modify: `${PLUGIN}/hooks/hooks.json`

- [ ] **Step 1: Read current file**

Read `${PLUGIN}/hooks/hooks.json`.

- [ ] **Step 2: Add SessionStart entry for wait-for-indexing**

Add a new entry to the `SessionStart` array (after the existing `obs_session_start.py` entry):
```json
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/wait-for-indexing.sh",
            "timeout": 35
          }
        ]
      }
```

- [ ] **Step 3: Add PreToolUse entry for check-indexing-ready**

Add a new entry to the `PreToolUse` array (before the existing catch-all `obs_pre_tool_use.py` entry, after the `mcp__.*ivy` check_lsp_log entry):
```json
      {
        "matcher": "mcp__.*ivy",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check-indexing-ready.sh",
            "timeout": 3
          }
        ]
      }
```

- [ ] **Step 4: Validate JSON**

Run: `python3 -m json.tool ${PLUGIN}/hooks/hooks.json > /dev/null`
Expected: Exit 0

- [ ] **Step 5: Commit**

```bash
git add ${PLUGIN}/hooks/hooks.json
git commit -m "feat(hooks): register indexing wait and guard hooks"
```

---

### Task 12: Update Ground Truth YAML for New Hooks

**Files:**
- Modify: `${PLUGIN}/tests/ground-truth/quic-workspace.yaml`

- [ ] **Step 1: Read current ground truth**

Read `${PLUGIN}/tests/ground-truth/quic-workspace.yaml` and find the `hooks.expected_scripts` section.

- [ ] **Step 2: Add new scripts to expected lists**

Add to `SessionStart` expected scripts: `wait-for-indexing.sh`
Add to `PreToolUse` expected scripts: `check-indexing-ready.sh`

- [ ] **Step 3: Commit**

```bash
git add ${PLUGIN}/tests/ground-truth/quic-workspace.yaml
git commit -m "fix(ground-truth): add indexing hook scripts to expected_scripts"
```

---

### Task 13: Update `nct-validate.md` Hook Validation Checks

**Files:**
- Modify: `${PLUGIN}/commands/nct-validate.md`

- [ ] **Step 1: Read Phase 3 hook checks**

Read `${PLUGIN}/commands/nct-validate.md` and find the H1-H12 checks and the H12 all-scripts list.

- [ ] **Step 2: Add H13 and H14 checks**

Add after H12:

**H13**: Verify `hooks.json` contains a `SessionStart` hook with command containing `wait-for-indexing.sh`.

**H14**: Verify `hooks.json` contains a `PreToolUse` hook with matcher `mcp__.*ivy` and command containing `check-indexing-ready.sh`.

- [ ] **Step 3: Update H12 script list**

Add `wait-for-indexing.sh` and `check-indexing-ready.sh` to the H12 all-scripts enumeration list.

- [ ] **Step 4: Update Phase 3 summary count**

Change `Hooks | 12` to `Hooks | 14` in the Phase 3 summary table. Update the total `~55` accordingly (to `~57`).

- [ ] **Step 5: Commit**

```bash
git add ${PLUGIN}/commands/nct-validate.md
git commit -m "docs(nct-validate): add H13/H14 for indexing hooks, update counts"
```

---

### Task 14: Integration Verification

- [ ] **Step 1: Run manifest tests**

Run: `cd ${PIV}/submodules/panther-ivy-plugin && python3 -m pytest plugins/panther-ivy-plugin/tests/test_manifests.py -v`
Expected: All tests pass (validates hooks.json structure, script references)

- [ ] **Step 2: Run hook tests**

Run: `cd ${PIV}/submodules/panther-ivy-plugin && python3 -m pytest plugins/panther-ivy-plugin/tests/test_hooks.py -v`
Expected: All existing tests pass

- [ ] **Step 3: Verify shell script syntax for all modified scripts**

Run:
```bash
bash -n ${IVY_LSP_PLUGIN}/lsp-start.sh && \
bash -n ${PLUGIN}/scripts/start-ivy-tools.sh && \
bash -n ${PLUGIN}/scripts/ivy-lsp-wrapper.sh && \
bash -n ${PLUGIN}/hooks/scripts/detect-ivy-workspace.sh && \
bash -n ${PLUGIN}/hooks/scripts/wait-for-indexing.sh && \
bash -n ${PLUGIN}/hooks/scripts/check-indexing-ready.sh
```
Expected: All exit 0

- [ ] **Step 4: Dry-run check_lsp_log.py**

Run: `IVY_LSP_LOG_PATH=/dev/null python3 ${PLUGIN}/hooks/scripts/observability/check_lsp_log.py`
Expected: Outputs `{"decision": "allow"}` (no file = no errors)

- [ ] **Step 5: Manual verification (next Claude session)**

Start a fresh Claude session with the plugin. Verify:
1. `/tmp/ivy-lsp-<date>-<pid>.log` file created
2. `/tmp/ivy-lsp-latest.log` symlink exists and points to the new file
3. Claude context contains `[ivy-indexing] Indexed N files. Workspace ready.`
4. Run `/nct-health` — Step 2 should show 0 errors for the fresh instance
