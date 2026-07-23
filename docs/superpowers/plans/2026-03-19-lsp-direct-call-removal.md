# LSP Direct Call Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop Claude from calling the LSP tool directly on `.ivy` files — redirect via CLAUDE.md update and PreToolUse hook, and fix the off-by-one bug in `word_at_position()`.

**Architecture:** Three independent changes: (1) CLAUDE.md removes the "use LSP directly" instruction for navigation, (2) a PreToolUse hook intercepts LSP calls on `.ivy` files and warns Claude, (3) the `word_at_position()` boundary check is fixed from `<=` to `<`.

**Tech Stack:** Bash (hook script), JSON (hooks.json), Markdown (CLAUDE.md), Python (position_utils.py + tests)

---

### Task 1: Update CLAUDE.md — remove "use LSP directly" instruction

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/CLAUDE.md:36-55`

- [ ] **Step 1: Replace the "Semantic query" section (lines 36-37)**

Replace:
```markdown
**Semantic query** (via LSP -- `ivy_query` has been removed):
Use LSP `hover` for symbol info, LSP `findReferences` for cross-references, and LSP `incomingCalls`/`outgoingCalls` for impact analysis.
```

With:
```markdown
**Semantic query**:
The Ivy LSP runs internally via `.lsp.json` and powers MCP tools. Do not call the `LSP` tool directly — use `Read`/`Grep`/`Glob` for navigation, `ivy_model_info` for model structure, and `ivy_diagnostics` for analysis.
```

- [ ] **Step 2: Remove the "Ivy LSP" direct-call table (lines 45-55)**

Remove this entire block:
```markdown
**Ivy LSP** (for `.ivy` files — use the `LSP` tool explicitly):

| Category | Operations |
|----------|-----------|
| Navigation | `goToDefinition` (cross-include), `goToImplementation` (action→before/after monitors), `findReferences` |
| Inspection | `hover` (type info + RFC annotations), `documentSymbol` (file outline), `workspaceSymbol` (cross-file search) |
| Call graph | `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls` (not yet implemented -- may return empty results) |

**Note**: Claude Code does not receive automatic diagnostics — use `ivy_diagnostics` MCP tool instead (mode="structural" for fast checks, or omit mode for full 5-layer analysis). See the `tooling-reference` skill for usage patterns.

**Claude native tools**: `Read`/`Grep`/`Glob` for navigation, `Edit`/`Write` for modification.
```

Replace with:
```markdown
**Note**: Claude Code does not receive automatic diagnostics — use `ivy_diagnostics` MCP tool instead (mode="structural" for fast checks, or omit mode for full 5-layer analysis). See the `tooling-reference` skill for usage patterns.

**Claude native tools**: `Read`/`Grep`/`Glob` for navigation, `Edit`/`Write` for modification.
```

- [ ] **Step 3: Verify the edit is coherent**

Read the CLAUDE.md from line 19 to line 60 and confirm:
- No mention of "use the `LSP` tool explicitly"
- No table of LSP operations directing Claude to call them
- The "Semantic query" section redirects to MCP tools and native tools
- The diagnostics note and native tools note are preserved

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/CLAUDE.md
git commit -m "docs: remove 'use LSP directly' instruction from plugin CLAUDE.md

The Ivy LSP runs internally via .lsp.json and MCP bridge.
Claude should use MCP tools and native tools (Read/Grep/Glob)
instead of calling the LSP tool directly, which requires
guessing (line, character) positions and often resolves to
the wrong symbol."
```

---

### Task 2: Add PreToolUse hook for LSP

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/hooks.json:3-47` (PreToolUse array)

- [ ] **Step 1: Add LSP matcher entry to hooks.json**

Insert after the existing `"matcher": "Bash"` block (after line 12, before the `ivy_verify` block at line 14), add:

```json
      {
        "matcher": "LSP",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Do not call the LSP tool directly on .ivy files. The Ivy LSP runs internally via .lsp.json and MCP bridge. Use MCP tools (ivy_model_info, ivy_diagnostics, ivy_coverage) for analysis, and Read/Grep/Glob for navigation. If you need symbol references, use Grep with \\b word boundaries."
          }
        ]
      },
```

- [ ] **Step 2: Validate JSON syntax**

```bash
python3 -c "import json; json.load(open('panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/hooks.json'))" && echo "JSON valid"
```

Expected: `JSON valid`

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/hooks.json
git commit -m "feat: add PreToolUse hook to redirect LSP calls on .ivy files

Adds a prompt-type hook matching the LSP tool that warns Claude
to use MCP tools and Read/Grep/Glob instead of calling the LSP
tool directly. Same pattern as the existing Bash hook for
ivy_check/ivyc CLI commands."
```

---

### Task 3: Fix `word_at_position()` off-by-one

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/utils/position_utils.py:108`
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/test_task_1_8_position_utils.py`

- [ ] **Step 1: Write failing tests for boundary cases**

Add to `tests/test_task_1_8_position_utils.py` inside `TestWordAtPosition`:

```python
    def test_cursor_between_tokens_returns_empty(self):
        """Character at the space between 'object' and 'ack' should return ''."""
        from ivy_lsp.utils.position_utils import word_at_position

        lines = ["    object ack = {"]
        # character=10 is the space after 'object' (end of match is exclusive)
        pos = Position(line=0, character=10)
        assert word_at_position(lines, pos) == ""

    def test_cursor_at_token_exclusive_end(self):
        """m.end() is exclusive — cursor there should NOT match the token."""
        from ivy_lsp.utils.position_utils import word_at_position

        lines = ["type cid"]
        # character=4 is the space after 'type', m.end()=4 for 'type'
        pos = Position(line=0, character=4)
        assert word_at_position(lines, pos) == ""

    def test_cursor_at_second_token_start(self):
        """Cursor at start of 'ack' on 'object ack' line resolves to 'ack'."""
        from ivy_lsp.utils.position_utils import word_at_position

        lines = ["    object ack = {"]
        pos = Position(line=0, character=11)  # 'a' of 'ack'
        assert word_at_position(lines, pos) == "ack"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_task_1_8_position_utils.py::TestWordAtPosition::test_cursor_between_tokens_returns_empty tests/test_task_1_8_position_utils.py::TestWordAtPosition::test_cursor_at_token_exclusive_end -v
```

Expected: 2 FAIL (they currently return `"object"` instead of `""` due to the `<=` bug)

- [ ] **Step 3: Fix the boundary check**

In `ivy_lsp/utils/position_utils.py` line 108, change:

```python
        if m.start() <= position.character <= m.end():
```

to:

```python
        if m.start() <= position.character < m.end():
```

- [ ] **Step 4: Run all word_at_position tests**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_task_1_8_position_utils.py::TestWordAtPosition -v
```

Expected: ALL PASS (8 tests — 5 existing + 3 new)

- [ ] **Step 5: Run the full position_utils test suite**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_task_1_8_position_utils.py -v
```

Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/utils/position_utils.py panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/tests/test_task_1_8_position_utils.py
git commit -m "fix: off-by-one in word_at_position() boundary check

Python re.Match.end() is exclusive, so the check should use '<'
not '<='. The old check caused cursor positions at the space
between tokens (e.g., between 'object' and 'ack') to resolve
to the preceding token instead of returning empty.

Adds 3 boundary-case tests covering the fix."
```
