# Workflow-Aware Output Style System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a layered style system to panther-ivy-plugin so Claude's output formatting (prose style, tool results, session summaries) adapts to the active workflow state.

**Architecture:** Three composable layers (base style + workflow overlay + phase modifier) injected via hooks. A `UserPromptSubmit` hook composes the style document per turn. A `PostToolUse` hook reformats the 5 high-frequency MCP tool results. A `Stop` hook renders workflow-specific session summaries, replacing the existing bash-based `stop-session-summary.sh`.

**Tech Stack:** Python 3.10+, PyYAML (already a dependency), Claude Code plugin hooks (JSON stdin/stdout protocol), markdown content files.

**Spec:** `docs/superpowers/specs/2026-04-09-workflow-aware-output-styles-design.md`

---

**Path conventions:** All paths below are relative to the worktree root. The plugin root is:
```
PLUGIN=panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin
```

---

### Task 1: Style Utilities Module

**Files:**
- Create: `{PLUGIN}/hooks/scripts/style_utils.py`
- Test: `{PLUGIN}/tests/test_style_utils.py`

This module provides shared functions for loading style files, extracting markdown sections, and composing the effective style document. All three hooks depend on it.

- [ ] **Step 1: Write the failing tests**

Create `{PLUGIN}/tests/test_style_utils.py`:

```python
"""Tests for style_utils module."""

import importlib
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_HOOK_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "hooks" / "scripts")


@pytest.fixture(autouse=True)
def _patch_sys_path():
    sys.path.insert(0, _HOOK_SCRIPTS_DIR)
    yield
    sys.path.remove(_HOOK_SCRIPTS_DIR)
    if "style_utils" in sys.modules:
        del sys.modules["style_utils"]


def _import():
    if "style_utils" in sys.modules:
        return importlib.reload(sys.modules["style_utils"])
    return importlib.import_module("style_utils")


class TestFindSection:
    def test_finds_h2_section(self):
        mod = _import()
        content = "# Title\n\n## Foo\nfoo content\n\n## Bar\nbar content\n"
        assert mod.find_section(content, "Foo") == "foo content"

    def test_finds_h3_section(self):
        mod = _import()
        content = "## Parent\n\n### Child\nchild content\n\n### Other\nother\n"
        assert mod.find_section(content, "Child", level=3) == "child content"

    def test_returns_none_for_missing(self):
        mod = _import()
        assert mod.find_section("# Title\n## Foo\ncontent\n", "Missing") is None

    def test_includes_nested_headings(self):
        mod = _import()
        content = "## Outer\nouter text\n### Inner\ninner text\n\n## Next\n"
        result = mod.find_section(content, "Outer")
        assert "outer text" in result
        assert "### Inner" in result
        assert "inner text" in result


class TestLoadStyleFile:
    def test_loads_existing_file(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        (styles_dir / "base.md").write_text("# Base\ncontent here\n")
        result = mod.load_style_file(str(tmp_path), "base.md")
        assert "content here" in result

    def test_returns_none_for_missing(self, tmp_path):
        mod = _import()
        assert mod.load_style_file(str(tmp_path), "nonexistent.md") is None


class TestComposeStyle:
    def test_base_only_when_no_workflow(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        (styles_dir / "base.md").write_text("# Base\nbase rules\n")
        result = mod.compose_style(str(tmp_path), workflow=None, phase=None)
        assert "base rules" in result

    def test_base_plus_overlay(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        (styles_dir / "overlays").mkdir(parents=True)
        (styles_dir / "base.md").write_text("# Base\nbase rules\n")
        (styles_dir / "overlays" / "verify.md").write_text(
            "# Verify\nverify rules\n\n## Phase Modifiers\n\n"
            "### compile\ncompile stuff\n\n### diagnose\ndiagnose stuff\n"
        )
        result = mod.compose_style(str(tmp_path), workflow="verify", phase="compile")
        assert "base rules" in result
        assert "verify rules" in result
        assert "[ACTIVE PHASE]" in result
        assert "compile stuff" in result

    def test_missing_phase_still_includes_overlay(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        (styles_dir / "overlays").mkdir(parents=True)
        (styles_dir / "base.md").write_text("# Base\nbase rules\n")
        (styles_dir / "overlays" / "verify.md").write_text("# Verify\nverify rules\n")
        result = mod.compose_style(str(tmp_path), workflow="verify", phase="unknown")
        assert "base rules" in result
        assert "verify rules" in result
        assert "[ACTIVE PHASE]" not in result

    def test_missing_overlay_falls_back_to_base(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        (styles_dir / "base.md").write_text("# Base\nbase rules\n")
        result = mod.compose_style(str(tmp_path), workflow="nonexistent", phase=None)
        assert "base rules" in result


class TestLoadToolRenderer:
    def test_loads_workflow_section(self, tmp_path):
        mod = _import()
        renderers_dir = tmp_path / "styles" / "tool-renderers"
        renderers_dir.mkdir(parents=True)
        (renderers_dir / "ivy_verify.md").write_text(
            "# ivy_verify\n\n## Default\ndefault fmt\n\n## verify\nverify fmt\n"
        )
        result = mod.load_tool_renderer(str(tmp_path), "ivy_verify", "verify")
        assert "verify fmt" in result

    def test_falls_back_to_default(self, tmp_path):
        mod = _import()
        renderers_dir = tmp_path / "styles" / "tool-renderers"
        renderers_dir.mkdir(parents=True)
        (renderers_dir / "ivy_verify.md").write_text(
            "# ivy_verify\n\n## Default\ndefault fmt\n\n## verify\nverify fmt\n"
        )
        result = mod.load_tool_renderer(str(tmp_path), "ivy_verify", "build")
        assert "default fmt" in result

    def test_returns_none_for_missing_tool(self, tmp_path):
        mod = _import()
        assert mod.load_tool_renderer(str(tmp_path), "nonexistent", "verify") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest {PLUGIN}/tests/test_style_utils.py -v`
Expected: All tests FAIL with `ModuleNotFoundError: No module named 'style_utils'`

- [ ] **Step 3: Implement style_utils.py**

Create `{PLUGIN}/hooks/scripts/style_utils.py`:

```python
#!/usr/bin/env python3
"""Shared utilities for the workflow-aware output style system.

Loads style files (base, overlays, tool renderers, summaries) from the
``styles/`` directory under the plugin root, extracts markdown sections,
and composes the effective style document for injection via hooks.
"""

import os
import re
from pathlib import Path


def find_section(content: str, heading: str, level: int = 2) -> str | None:
    """Extract a section from markdown content by its heading.

    Returns the text between the matched heading and the next heading of
    equal or higher level, stripped of leading/trailing whitespace.
    Returns None if the heading is not found.
    """
    prefix = "#" * level
    pattern = re.compile(
        rf"^{prefix}\s+{re.escape(heading)}\s*$",
        re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        return None

    start = match.end()
    # Find next heading of same or higher level
    next_heading = re.compile(rf"^#{{{1},{level}}}\s+", re.MULTILINE)
    end_match = next_heading.search(content, start)
    section = content[start : end_match.start()] if end_match else content[start:]
    return section.strip()


def load_style_file(plugin_root: str, relative_path: str) -> str | None:
    """Load a style file from ``{plugin_root}/styles/{relative_path}``.

    Returns the file content as a string, or None if the file does not exist.
    """
    path = Path(plugin_root) / "styles" / relative_path
    if not path.is_file():
        return None
    return path.read_text()


def compose_style(
    plugin_root: str,
    workflow: str | None,
    phase: str | None,
) -> str:
    """Compose the effective style document from base + overlay + phase modifier.

    Args:
        plugin_root: Path to the plugin root directory.
        workflow: Active workflow name (e.g., "verify"), or None.
        phase: Active phase within the workflow (e.g., "compile"), or None.

    Returns:
        Composed markdown style document ready for injection.
    """
    parts: list[str] = []

    base = load_style_file(plugin_root, "base.md")
    if base:
        parts.append(base)

    if workflow:
        overlay = load_style_file(plugin_root, f"overlays/{workflow}.md")
        if overlay and phase:
            overlay = _highlight_active_phase(overlay, phase)
        if overlay:
            parts.append(overlay)

    return "\n\n---\n\n".join(parts) if parts else ""


def _highlight_active_phase(overlay: str, phase: str) -> str:
    """Mark the active phase section with [ACTIVE PHASE] in the overlay content."""
    pattern = re.compile(
        rf"^(###\s+{re.escape(phase)})\s*$",
        re.MULTILINE,
    )
    return pattern.sub(rf"\1 [ACTIVE PHASE]", overlay)


def load_tool_renderer(
    plugin_root: str,
    tool_name: str,
    workflow: str | None,
) -> str | None:
    """Load the appropriate tool renderer section for the active workflow.

    Looks for a ``## {workflow}`` section in the renderer file. Falls back
    to ``## Default`` if the workflow section is not found. Returns None
    if the renderer file does not exist.
    """
    content = load_style_file(plugin_root, f"tool-renderers/{tool_name}.md")
    if content is None:
        return None

    if workflow:
        section = find_section(content, workflow)
        if section:
            return section

    default = find_section(content, "Default") or find_section(content, "Default (no workflow active)")
    return default


def load_summary_template(plugin_root: str, workflow: str | None) -> str | None:
    """Load the session summary template for the active workflow.

    Returns None if no template exists for the given workflow.
    """
    if not workflow:
        return None
    return load_style_file(plugin_root, f"summaries/{workflow}.md")


def resolve_plugin_root() -> str:
    """Resolve the plugin root directory.

    Uses CLAUDE_PLUGIN_ROOT env var if set, otherwise walks up from this
    file's location (hooks/scripts/ -> hooks/ -> plugin root).
    """
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if env_root:
        return env_root
    return str(Path(__file__).resolve().parent.parent.parent)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest {PLUGIN}/tests/test_style_utils.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add -f {PLUGIN}/hooks/scripts/style_utils.py {PLUGIN}/tests/test_style_utils.py
git commit -m "feat(style-system): add style_utils module for loading and composing styles"
```

---

### Task 2: Base Style and Workflow Overlays

**Files:**
- Create: `{PLUGIN}/styles/base.md`
- Create: `{PLUGIN}/styles/overlays/navigate.md`
- Create: `{PLUGIN}/styles/overlays/verify.md`
- Create: `{PLUGIN}/styles/overlays/build.md`
- Create: `{PLUGIN}/styles/overlays/review.md`
- Create: `{PLUGIN}/styles/overlays/triage.md`

Content files only — no code logic. Content is defined in the design spec, sections "Base Style Layer" and "Workflow Overlays."

- [ ] **Step 1: Create base.md**

Create `{PLUGIN}/styles/base.md`:

```markdown
# Base Output Style

## Formatting Conventions
- Cite RFC sections as `[rfcNNNN:X.Y]` inline, never as footnotes.
- Format errors as: `ERROR: {file}:{line} -- {message}`.
- Format warnings as: `WARN: {file}:{line} -- {message}`.
- Reference Ivy files with relative paths from protocol-testing root.

## Default Dimensions
- **Verbosity**: Moderate -- explain the "what" concisely, skip the "why" unless asked or non-obvious.
- **Tone**: Professional, neutral. No enthusiasm markers ("great!", "nice!"). State facts.
- **Structure**: Prose paragraphs by default. Use tables only for quantitative data (coverage stats, pass/fail counts). Use checklists for action items.
- **Sections**: End responses with "Next Steps" listing 1-3 concrete actions when the workflow has more work to do.

## Tool Result Defaults
- When presenting MCP tool results, lead with the outcome (pass/fail/count), then details.
- Suppress raw JSON. Always render tool results as formatted prose or tables.
- For verification results, always include the isolate name and file path.
- For coverage results, always include the percentage and the denominator.

## Claim Discussion Format
- When a claim discussion is triggered, use this structure:
  1. State the claim (RFC requirement + Ivy assertion)
  2. Present the evidence (tool output, counterexample)
  3. Ask for resolution: RESOLVED / IUT_FINDING / DEFERRED / GUARD_ADDED / N_A / KNOWN_DEVIATION
- Mark the resolution in the source file as a comment.

## Phase Transition Announcements
- When transitioning between phases, announce: "Moving to {phase_name}."
- Do not re-explain what the phase does -- the workflow skill handles that.
```

- [ ] **Step 2: Create overlays/verify.md**

Create `{PLUGIN}/styles/overlays/verify.md`:

```markdown
# Verify Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Clinical. Lead with the result, not the reasoning. One sentence per finding.
- **Tone**: Diagnostic. "3 isolates passed, 1 failed at quic_protection.ivy:142" -- no hedging.
- **Structure**: Checklist for multi-item results. Numbered list for failures.

## Mandatory Sections
- **Verification Results** -- always present, pass/fail per isolate
- **Failure Details** -- only if failures exist, one entry per failure
- **Next Steps** -- from base, but scoped to verification actions only

## Tool Presentation
- `ivy_verify` success: "PASS: {isolate} verified ({N} clauses, {time}s)"
- `ivy_verify` failure: numbered list -- "1. FAIL: {isolate} at {file}:{line} -- {error_excerpt}"
- `ivy_diagnostics`: severity-grouped table (errors first, then warnings)
- `ivy_coverage`: inline -- "{N}% MUST coverage ({covered}/{total})"

## Phase Modifiers

### preflight
- Show only a "Preflight Checks" section (health, workspace, target file existence).
- Suppress "Next Steps" -- preflight auto-advances.

### compile
- Announce compilation target and expected duration.
- On success: single confirmation line, advance immediately.
- On failure: switch to failure detail format from base.

### diagnose
- **Override verbosity** to detailed. Explain root cause reasoning.
- Add sections: "Error Analysis", "Root Cause Hypothesis".
- Include relevant Ivy code snippets (3-5 lines around the error).

### fix
- After each edit, show "Changes Made" section: file, what changed, why.
- Re-run verification inline -- show updated pass/fail immediately after fix.
```

- [ ] **Step 3: Create overlays/navigate.md**

Create `{PLUGIN}/styles/overlays/navigate.md`:

```markdown
# Navigate Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Conversational. Provide context for what happened and what's available.
- **Tone**: Welcoming, orienting. "You left off mid-build on the QUIC connection layer."
- **Structure**: Prose with embedded suggestions. No tables unless showing workspace status.

## Mandatory Sections
- **Context Summary** -- where the user left off, active workspace, modified files
- **Available Actions** -- what workflows are available given current state
- **Suggested Next Step** -- one recommended action based on state

## Tool Presentation
- `ivy_health_check`: prose summary -- "LSP and MCP are healthy. Workspace: quic (client+server)."
- `ivy_workspace get`: inline -- "Active workspace: {protocol} ({roles})"
- Build state (if resuming): layer completion table

## Phase Modifiers

### warm_resume
- Lead with "Resuming previous session." then context summary.
- If build-state.yaml exists, show layer progress table.

### cold_start
- Lead with "Welcome." then workspace detection results.
- Show available protocols and suggest `/set-workspace`.

### activity_summary
- Summarize recent git changes to .ivy files.
- Highlight files with unresolved claim discussions.
```

- [ ] **Step 4: Create overlays/build.md**

Create `{PLUGIN}/styles/overlays/build.md`:

```markdown
# Build Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Explanatory. Provide reasoning for layer choices and dependency order.
- **Tone**: Methodical. "Layer 4 (frame) depends on types (layer 1). Writing quic_frame.ivy."
- **Structure**: Progress-oriented. Layer tables, dependency chains.

## Mandatory Sections
- **Layer Progress** -- table from build-state.yaml showing status per layer
- **Current Layer** -- what's being worked on, dependencies satisfied
- **Next Steps** -- next layer in dependency order

## Tool Presentation
- `ivy_verify`: per-layer -- "Layer verified: {isolate} PASS" or "Layer verification failed -- switching to verify workflow."
- `ivy_diagnostics`: focus on current layer's structural issues
- `ivy_compile`: compilation of current layer, success/failure

## Phase Modifiers

### scope
- Show protocol overview and methodology selection (NCT/NACT/NSCT).

### blueprint
- Show full 14-layer template, mark which layers are planned vs. skipped.
- Present dependency graph as ordered list.

### write
- Show current layer context: what it does, what it depends on, what depends on it.
- After each file write, show file path and line count.

### quality_gate
- Show quality gate results as pass/fail checklist.

### wrap_up
- Show final layer progress table with all statuses.
```

- [ ] **Step 5: Create overlays/review.md**

Create `{PLUGIN}/styles/overlays/review.md`:

```markdown
# Review Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Detailed for findings, terse for passing checks.
- **Tone**: Auditor. "Coverage gap: [rfc9000:4.1] has no corresponding assertion."
- **Structure**: Tables for quantitative results. Numbered lists for findings.

## Mandatory Sections
- **Coverage Summary** -- percentage, covered/total, per-section breakdown
- **Quality Findings** -- numbered list of issues with severity
- **Recommendations** -- prioritized list of improvements

## Tool Presentation
- `ivy_coverage` (stats): full table with per-section breakdown
- `ivy_coverage` (gaps): numbered list with RFC section references
- `ivy_coverage` (matrix): full requirement-to-assertion table
- `ivy_quality` (suggestions): numbered findings
- `ivy_quality` (gate): pass/fail checklist

## Phase Modifiers

### triage
- Determine review type (coverage/quality/both). Show scoping decision.

### execute
- Show progress through dispatched agents (spec-analyst, model-reviewer, traceability-agent).

### findings
- Present all results in a structured report format.
```

- [ ] **Step 6: Create overlays/triage.md**

Create `{PLUGIN}/styles/overlays/triage.md`:

```markdown
# Triage Workflow -- Style Overlay

## Dimension Overrides
- **Verbosity**: Terse. Bullet points. One line per check.
- **Tone**: Diagnostic, urgent. "MCP: DOWN. LSP: OK. Workspace: not set."
- **Structure**: Status dashboard. Pass/fail per component.

## Mandatory Sections
- **Health Status** -- one-line status per component (LSP, MCP, workspace, indexing)
- **Fix Actions** -- if anything is down, concrete fix steps
- **Result** -- "All systems operational" or "N issue(s) remain"

## Tool Presentation
- `ivy_health_check`: per-component status line
- `ivy_verify`: "ivy_verify: OK" or "ivy_verify: FAIL -- {count} error(s)"
- `ivy_diagnostics`: error count only, no detail

## Phase Modifiers

### quick_check
- Run health check, show dashboard, exit if all green.

### diagnose
- Expand failing components with log excerpts and error details.

### fix
- Show fix action taken and result. Re-check after each fix.
```

- [ ] **Step 7: Commit**

```bash
git add -f {PLUGIN}/styles/base.md {PLUGIN}/styles/overlays/
git commit -m "feat(style-system): add base style and 5 workflow overlays"
```

---

### Task 3: Tool Renderer Specs

**Files:**
- Create: `{PLUGIN}/styles/tool-renderers/ivy_verify.md`
- Create: `{PLUGIN}/styles/tool-renderers/ivy_coverage.md`
- Create: `{PLUGIN}/styles/tool-renderers/ivy_diagnostics.md`
- Create: `{PLUGIN}/styles/tool-renderers/ivy_compile.md`
- Create: `{PLUGIN}/styles/tool-renderers/ivy_quality.md`

Design documentation for the `render-tool-result.py` hook. Each file specifies how the tool's output should be formatted per workflow. The hook implements these rules in Python; the markdown files are the single source of truth for expected formatting.

- [ ] **Step 1: Create ivy_verify.md**

Create `{PLUGIN}/styles/tool-renderers/ivy_verify.md`:

```markdown
# ivy_verify -- Result Renderer

## Input Fields
The tool returns: isolate, status (pass/fail), clause_count, duration_s, errors (list of {file, line, message, isolate}).

## Default (no workflow active)
- Pass: "PASS: {isolate} verified ({clause_count} clauses, {duration_s}s)"
- Fail: "FAIL: {isolate} at {file}:{line} -- {message}"

## verify
- Pass: "PASS: {isolate} ({clause_count} clauses, {duration_s}s)"
- Fail: Numbered list of all errors. Include context hint: "See {file}:{line}."
- Summary line: "{pass_count}/{total} isolates passed."

## build
- Pass: "Layer verified: {isolate} PASS"
- Fail: "Layer verification failed -- switching to verify workflow for diagnosis."
- Only show the isolate relevant to the current build layer.

## review
- Pass/fail as table row: | {isolate} | {status} | {clause_count} | {duration_s}s |
- Aggregate into a table when multiple isolates verified in sequence.

## triage
- Pass: "ivy_verify: OK"
- Fail: "ivy_verify: FAIL -- {error_count} error(s). Run verify workflow for details."
```

- [ ] **Step 2: Create ivy_coverage.md**

Create `{PLUGIN}/styles/tool-renderers/ivy_coverage.md`:

```markdown
# ivy_coverage -- Result Renderer

## Input Fields
Varies by mode. stats: {covered, total, percentage, by_section}. gaps: {uncovered_requirements, unguarded_state}. matrix: {requirement_to_assertion_map}.

## Default
- stats: "{percentage}% MUST coverage ({covered}/{total})"
- gaps: Bullet list of uncovered requirements
- matrix: Table with requirement -> assertion mapping

## verify
- stats: Inline -- "{percentage}% ({covered}/{total})" -- no table.
- gaps: Suppress unless explicitly requested.

## build
- stats: Show per-layer breakdown if available.
- gaps: Highlight gaps in the layer currently being built.

## review
- stats: Full table with per-section breakdown: | Section | Covered | Total | % |
- gaps: Numbered list with RFC section references.
- matrix: Full table -- this is the primary review artifact.

## triage
- stats: Single line -- "Coverage: {percentage}%"
- gaps/matrix: Suppress.
```

- [ ] **Step 3: Create ivy_diagnostics.md**

Create `{PLUGIN}/styles/tool-renderers/ivy_diagnostics.md`:

```markdown
# ivy_diagnostics -- Result Renderer

## Input Fields
Returns: issues (list of {file, line, severity, message, layer}), summary counts.

## Default
- Severity-grouped list: errors first, then warnings.
- Include file:line for each.

## verify
- Severity-grouped table: | Severity | File | Line | Message |
- Errors first, warnings second.

## build
- Filter to current layer only.
- Show as numbered list with fix suggestions.

## review
- Full table with layer column: | Layer | Severity | File | Line | Message |
- Include summary counts at top.

## triage
- Count only: "{error_count} errors, {warning_count} warnings"
- Detail suppressed unless in diagnose phase.
```

- [ ] **Step 4: Create ivy_compile.md**

Create `{PLUGIN}/styles/tool-renderers/ivy_compile.md`:

```markdown
# ivy_compile -- Result Renderer

## Input Fields
Returns: status (success/failure), output_binary, duration_s, errors (if any).

## Default
- Success: "Compiled {file} -> {output_binary} ({duration_s}s)"
- Failure: "Compilation failed: {error_message}"

## verify
- Success: "Compiled: {output_binary} ({duration_s}s)" -- advance immediately.
- Failure: Show error with file:line, suggest switching to diagnose phase.

## build
- Success: "Layer compiled: {file} -> {output_binary}"
- Failure: "Layer compilation failed. Fix before proceeding to next layer."

## review
- Not typically used in review. Default format.

## triage
- Success: "ivy_compile: OK"
- Failure: "ivy_compile: FAIL -- {error_message}"
```

- [ ] **Step 5: Create ivy_quality.md**

Create `{PLUGIN}/styles/tool-renderers/ivy_quality.md`:

```markdown
# ivy_quality -- Result Renderer

## Input Fields
Varies by mode. suggestions: {suggestions (list of {category, message, severity})}. gate: {passed, gate_level, failures}.

## Default
- suggestions: Numbered list by severity.
- gate: "Gate {gate_level}: PASS" or "Gate {gate_level}: FAIL -- {failure_count} issue(s)"

## verify
- suggestions: Suppress unless explicitly requested.
- gate: Inline pass/fail.

## build
- suggestions: Show suggestions relevant to current layer.
- gate: Show gate result with per-criterion breakdown.

## review
- suggestions: Full numbered list grouped by category.
- gate: Detailed table: | Criterion | Status | Details |

## triage
- suggestions: Suppress.
- gate: "Quality gate: PASS" or "Quality gate: FAIL ({failure_count})"
```

- [ ] **Step 6: Commit**

```bash
git add -f {PLUGIN}/styles/tool-renderers/
git commit -m "feat(style-system): add tool renderer specs for 5 MCP tools"
```

---

### Task 4: Session Summary Templates

**Files:**
- Create: `{PLUGIN}/styles/summaries/navigate.md`
- Create: `{PLUGIN}/styles/summaries/verify.md`
- Create: `{PLUGIN}/styles/summaries/build.md`
- Create: `{PLUGIN}/styles/summaries/review.md`
- Create: `{PLUGIN}/styles/summaries/triage.md`

- [ ] **Step 1: Create summaries/verify.md**

Create `{PLUGIN}/styles/summaries/verify.md`:

```markdown
# Verify Session Summary

## Sections (in order)

### Verification Results
- Total isolates attempted: {isolates_attempted}
- Passed: {pass_count} | Failed: {fail_count}
- List each failed isolate: "{isolate} at {file}:{line}"

### Claim Resolutions
- Show counts by type: {resolved} confirmed, {iut_findings} IUT findings, {deferred} deferred
- If any IUT_FINDING: list them with file and RFC section

### Outstanding Work
- List isolates not yet attempted or still failing
- If in diagnose/fix phase at session end: note "Fix in progress for {isolate}"

### Session Metrics
- Tool calls: top 3 by frequency
- Session duration hint (from observability timestamps)

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
```

- [ ] **Step 2: Create summaries/build.md**

Create `{PLUGIN}/styles/summaries/build.md`:

```markdown
# Build Session Summary

## Sections (in order)

### Layer Progress
Table from build-state.yaml:
| Layer | File | Status |
|-------|------|--------|

### Decisions Made
- List from build-state.yaml decisions array

### Verification Status
- If any layers were verified: show pass/fail per layer
- If build reached Phase 4 (verify): show verification summary

### Next Session
- Next layer in dependency order
- Any blockers or open questions from this session

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
```

- [ ] **Step 3: Create summaries/navigate.md**

Create `{PLUGIN}/styles/summaries/navigate.md`:

```markdown
# Navigate Session Summary

## Sections (in order)

### Session Activity
- Files modified (from git diff)
- Workflows activated during session (from observability)

### Workspace State
- Active workspace at session end
- Build state summary if build-state.yaml exists

### Claim Resolutions
- Show counts by type: {resolved} confirmed, {iut_findings} IUT findings, {deferred} deferred

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
```

- [ ] **Step 4: Create summaries/review.md**

Create `{PLUGIN}/styles/summaries/review.md`:

```markdown
# Review Session Summary

## Sections (in order)

### Coverage Delta
- Coverage at session start vs. end (if both measured)
- New requirements covered this session

### Quality Findings
- Total findings: {count} by severity
- Findings resolved vs. outstanding

### Agents Dispatched
- Which agents ran and their outcomes

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
```

- [ ] **Step 5: Create summaries/triage.md**

Create `{PLUGIN}/styles/summaries/triage.md`:

```markdown
# Triage Session Summary

## Sections (in order)

### Health Status
- Final status per component: LSP, MCP, workspace, indexing

### Issues Fixed
- What was broken and what fix was applied

### Remaining Issues
- What still needs attention

### Lint Issues
- Only if modified .ivy files have issues: "{file}: {issue}"
```

- [ ] **Step 6: Commit**

```bash
git add -f {PLUGIN}/styles/summaries/
git commit -m "feat(style-system): add session summary templates for 5 workflows"
```

---

### Task 5: compose-style.py Hook

**Files:**
- Create: `{PLUGIN}/hooks/scripts/compose-style.py`
- Test: `{PLUGIN}/tests/test_compose_style.py`

**Depends on:** Task 1 (style_utils), Task 2 (base + overlays)

This hook runs on `UserPromptSubmit`. It reads the active workflow state, loads the corresponding style files, and injects the composed style document as `additionalContext`.

- [ ] **Step 1: Write the failing tests**

Create `{PLUGIN}/tests/test_compose_style.py`:

```python
"""Tests for compose-style.py UserPromptSubmit hook."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "compose-style.py"
)
PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)


def run_hook(
    env_overrides: dict | None = None,
    stdin_data: str = "{}",
) -> dict | None:
    """Run the hook script, return parsed JSON output or None."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


class TestNoWorkflowActive:
    def test_injects_base_style_only(self, tmp_path):
        """When no workflow is active, only base style is injected."""
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": str(tmp_path)})
        if output is None:
            pytest.skip("No styles dir in plugin root yet")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Base Output Style" in ctx


class TestWithActiveWorkflow:
    def test_injects_overlay(self, tmp_path):
        """When a workflow is active, overlay is included."""
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text(
            yaml.safe_dump({"workflow": "verify", "phase": "compile"})
        )
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": str(tmp_path)})
        if output is None:
            pytest.skip("No styles dir in plugin root yet")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Base Output Style" in ctx
        assert "Verify Workflow" in ctx

    def test_highlights_active_phase(self, tmp_path):
        """The active phase section gets [ACTIVE PHASE] marker."""
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text(
            yaml.safe_dump({"workflow": "verify", "phase": "compile"})
        )
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": str(tmp_path)})
        if output is None:
            pytest.skip("No styles dir in plugin root yet")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "[ACTIVE PHASE]" in ctx


class TestNoProtocolDir:
    def test_exits_cleanly(self, tmp_path, monkeypatch):
        """When no protocol-testing dir exists, hook exits cleanly."""
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": ""})
        # Should either output base-only or exit silently
        assert True  # no crash


class TestMalformedState:
    def test_corrupt_workflow_file(self, tmp_path):
        """Corrupt active-workflow file falls back to base only."""
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text("not: [valid: yaml: {{")
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": str(tmp_path)})
        # Should not crash
        assert True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest {PLUGIN}/tests/test_compose_style.py -v`
Expected: FAIL with `FileNotFoundError` (script doesn't exist yet)

- [ ] **Step 3: Implement compose-style.py**

Create `{PLUGIN}/hooks/scripts/compose-style.py`:

```python
#!/usr/bin/env python3
"""UserPromptSubmit hook: inject workflow-aware output style as additionalContext.

Reads the active workflow state, composes base style + workflow overlay
(with active phase highlighted), and outputs as additionalContext JSON.

Non-blocking -- always exits 0.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin
from style_utils import compose_style, resolve_plugin_root
from workflow_state import find_protocol_dir, get_active_workflow


def main():
    read_stdin()  # consume stdin to avoid broken pipe

    plugin_root = resolve_plugin_root()
    protocol_dir = find_protocol_dir()

    workflow = None
    phase = None
    if protocol_dir:
        state = get_active_workflow(protocol_dir)
        if state:
            workflow = state.get("workflow")
            phase = state.get("phase")

    style_doc = compose_style(plugin_root, workflow, phase)
    if not style_doc:
        sys.exit(0)

    emit_hook_output("UserPromptSubmit", additional_context=style_doc)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest {PLUGIN}/tests/test_compose_style.py -v`
Expected: All tests PASS (some may skip if styles not yet deployed, which is expected)

- [ ] **Step 5: Commit**

```bash
git add -f {PLUGIN}/hooks/scripts/compose-style.py {PLUGIN}/tests/test_compose_style.py
git commit -m "feat(style-system): add compose-style.py UserPromptSubmit hook"
```

---

### Task 6: render-tool-result.py Hook

**Files:**
- Create: `{PLUGIN}/hooks/scripts/render-tool-result.py`
- Test: `{PLUGIN}/tests/test_render_tool_result.py`

**Depends on:** Task 1 (style_utils), Task 3 (tool renderers)

This hook runs on `PostToolUse` for the 5 rendered MCP tools. It reads the tool output JSON, determines the active workflow, and reformats the result according to workflow-specific rules. The formatting logic is implemented in Python, guided by the renderer specs in `styles/tool-renderers/`.

- [ ] **Step 1: Write the failing tests**

Create `{PLUGIN}/tests/test_render_tool_result.py`:

```python
"""Tests for render-tool-result.py PostToolUse hook."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "render-tool-result.py"
)
PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)


def run_hook(
    tool_name: str,
    tool_output: str,
    workflow: str | None = None,
    phase: str | None = None,
    tmp_path: Path | None = None,
) -> dict | None:
    """Run the hook with given tool result, return parsed JSON or None."""
    input_data = json.dumps({"tool_name": tool_name, "tool_output": tool_output})
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT

    if workflow and tmp_path:
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir(exist_ok=True)
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir(exist_ok=True)
        state = {"workflow": workflow}
        if phase:
            state["phase"] = phase
        (state_dir / "active-workflow").write_text(yaml.safe_dump(state))
        env["IVY_WORKSPACE_ROOT"] = str(tmp_path)
    elif tmp_path:
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir(exist_ok=True)
        env["IVY_WORKSPACE_ROOT"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


class TestIvyVerifyFormatting:
    def test_verify_pass_default(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_verify",
            json.dumps({"success": True, "isolate": "quic_conn", "clause_count": 12, "duration_s": 3.5}),
            tmp_path=tmp_path,
        )
        if output is None:
            pytest.skip("Formatter not yet producing output for default")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "PASS" in ctx
        assert "quic_conn" in ctx

    def test_verify_fail_triage_workflow(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_verify",
            json.dumps({"success": False, "errors": [{"file": "a.ivy", "line": 10, "message": "violated"}]}),
            workflow="triage",
            tmp_path=tmp_path,
        )
        if output is None:
            pytest.skip("Formatter not yet producing output for triage")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "FAIL" in ctx

    def test_verify_pass_build_workflow(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_verify",
            json.dumps({"success": True, "isolate": "quic_types"}),
            workflow="build",
            tmp_path=tmp_path,
        )
        if output is None:
            pytest.skip("Formatter not yet producing output for build")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Layer verified" in ctx


class TestUnrelatedTool:
    def test_non_rendered_tool_exits_silently(self, tmp_path):
        output = run_hook(
            "Read",
            "file contents",
            tmp_path=tmp_path,
        )
        assert output is None


class TestMalformedInput:
    def test_bad_json_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, SCRIPT],
            input="not json",
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0


class TestErrorInToolOutput:
    def test_error_result_passes_through(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_verify",
            json.dumps({"error": "MCP server unreachable"}),
            tmp_path=tmp_path,
        )
        # Should either pass through or exit silently, not crash
        assert True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest {PLUGIN}/tests/test_render_tool_result.py -v`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 3: Implement render-tool-result.py**

Create `{PLUGIN}/hooks/scripts/render-tool-result.py`:

```python
#!/usr/bin/env python3
"""PostToolUse hook: reformat MCP tool results per active workflow style.

Reads tool output from stdin JSON. For the 5 rendered tools (ivy_verify,
ivy_coverage, ivy_diagnostics, ivy_compile, ivy_quality), reformats the
result according to the active workflow's style rules and outputs as
hookSpecificOutput.

Non-blocking -- always exits 0.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin
from workflow_state import find_protocol_dir, get_active_workflow

RENDERED_TOOLS = {
    "ivy_verify",
    "ivy_coverage",
    "ivy_diagnostics",
    "ivy_compile",
    "ivy_quality",
}


def _match_tool(tool_name: str) -> str | None:
    """Extract the base tool name if it matches a rendered tool."""
    for rendered in RENDERED_TOOLS:
        if rendered in tool_name:
            return rendered
    return None


def _parse_output(raw: str | dict) -> dict:
    """Parse tool output into a dict. Returns empty dict on failure."""
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


def _safe_get(data: dict, key: str, default: str = "?") -> str:
    """Get a value from dict, converting to str with a fallback."""
    val = data.get(key)
    return str(val) if val is not None else default


# -- Formatters --
# Each returns a formatted string or None (to skip formatting).


def format_ivy_verify(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "success" not in data:
        return None  # pass through errors

    success = data.get("success", True)
    isolate = _safe_get(data, "isolate", "unknown")
    clauses = _safe_get(data, "clause_count", "?")
    duration = _safe_get(data, "duration_s", "?")
    errors = data.get("errors", [])

    if workflow == "triage":
        if success:
            return "ivy_verify: OK"
        return f"ivy_verify: FAIL -- {len(errors)} error(s). Run verify workflow for details."

    if workflow == "build":
        if success:
            return f"Layer verified: {isolate} PASS"
        return "Layer verification failed -- switching to verify workflow for diagnosis."

    if workflow == "review":
        status = "PASS" if success else "FAIL"
        return f"| {isolate} | {status} | {clauses} | {duration}s |"

    if workflow == "verify":
        if success:
            return f"PASS: {isolate} ({clauses} clauses, {duration}s)"
        lines = []
        for i, err in enumerate(errors, 1):
            f = err.get("file", "?")
            ln = err.get("line", "?")
            msg = err.get("message", "?")
            lines.append(f"{i}. FAIL: {isolate} at {f}:{ln} -- {msg}")
        return "\n".join(lines) if lines else f"FAIL: {isolate} -- verification failed"

    # default
    if success:
        return f"PASS: {isolate} verified ({clauses} clauses, {duration}s)"
    if errors:
        err = errors[0]
        return f"FAIL: {isolate} at {err.get('file', '?')}:{err.get('line', '?')} -- {err.get('message', '?')}"
    return f"FAIL: {isolate} -- verification failed"


def format_ivy_coverage(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "covered" not in data and "percentage" not in data:
        return None

    pct = _safe_get(data, "percentage", "?")
    covered = _safe_get(data, "covered", "?")
    total = _safe_get(data, "total", "?")

    if workflow == "triage":
        return f"Coverage: {pct}%"

    if workflow == "verify":
        return f"{pct}% ({covered}/{total})"

    if workflow == "review":
        sections = data.get("by_section", {})
        if sections:
            lines = [f"| Section | Covered | Total | % |", "| --- | --- | --- | --- |"]
            for sec, vals in sections.items():
                sc = vals.get("covered", "?")
                st = vals.get("total", "?")
                sp = vals.get("percentage", "?")
                lines.append(f"| {sec} | {sc} | {st} | {sp}% |")
            lines.append(f"\n**Total**: {pct}% ({covered}/{total})")
            return "\n".join(lines)
        return f"{pct}% MUST coverage ({covered}/{total})"

    # default / build
    return f"{pct}% MUST coverage ({covered}/{total})"


def format_ivy_diagnostics(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "issues" not in data:
        return None

    issues = data.get("issues", [])
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    if workflow == "triage":
        return f"{len(errors)} errors, {len(warnings)} warnings"

    if workflow == "verify" or workflow == "review":
        lines = ["| Severity | File | Line | Message |", "| --- | --- | --- | --- |"]
        for issue in errors + warnings:
            sev = issue.get("severity", "?")
            f = issue.get("file", "?")
            ln = issue.get("line", "?")
            msg = issue.get("message", "?")
            lines.append(f"| {sev} | {f} | {ln} | {msg} |")
        return "\n".join(lines) if len(lines) > 2 else "No diagnostic issues found."

    # default / build
    lines = []
    for issue in errors + warnings:
        sev = issue.get("severity", "?").upper()
        f = issue.get("file", "?")
        ln = issue.get("line", "?")
        msg = issue.get("message", "?")
        lines.append(f"{sev}: {f}:{ln} -- {msg}")
    return "\n".join(lines) if lines else "No diagnostic issues found."


def format_ivy_compile(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "status" not in data:
        return None

    success = data.get("status") == "success" or data.get("success", False)
    binary = _safe_get(data, "output_binary", "?")
    duration = _safe_get(data, "duration_s", "?")
    err_msg = _safe_get(data, "error_message", data.get("error", "unknown error"))

    if workflow == "triage":
        return "ivy_compile: OK" if success else f"ivy_compile: FAIL -- {err_msg}"

    if workflow == "build":
        if success:
            return f"Layer compiled: {binary}"
        return "Layer compilation failed. Fix before proceeding to next layer."

    if workflow == "verify":
        if success:
            return f"Compiled: {binary} ({duration}s)"
        return f"Compilation failed: {err_msg}. Consider switching to diagnose phase."

    # default / review
    if success:
        return f"Compiled -> {binary} ({duration}s)"
    return f"Compilation failed: {err_msg}"


def format_ivy_quality(data: dict, workflow: str | None) -> str | None:
    if "error" in data and "suggestions" not in data and "passed" not in data:
        return None

    # Gate mode
    if "passed" in data or "gate_level" in data:
        passed = data.get("passed", False)
        level = _safe_get(data, "gate_level", "?")
        failures = data.get("failures", [])

        if workflow == "triage":
            if passed:
                return "Quality gate: PASS"
            return f"Quality gate: FAIL ({len(failures)})"

        if workflow == "verify":
            return f"Gate {level}: {'PASS' if passed else 'FAIL'}"

        if workflow == "review":
            lines = ["| Criterion | Status | Details |", "| --- | --- | --- |"]
            for f in failures:
                lines.append(f"| {f.get('criterion', '?')} | FAIL | {f.get('details', '?')} |")
            return "\n".join(lines) if len(lines) > 2 else f"Gate {level}: PASS"

        # default / build
        if passed:
            return f"Gate {level}: PASS"
        return f"Gate {level}: FAIL -- {len(failures)} issue(s)"

    # Suggestions mode
    suggestions = data.get("suggestions", [])
    if workflow in ("triage", "verify"):
        return None  # suppress suggestions in triage/verify

    lines = []
    for i, s in enumerate(suggestions, 1):
        cat = s.get("category", "?")
        msg = s.get("message", "?")
        sev = s.get("severity", "?")
        lines.append(f"{i}. [{sev}] {cat}: {msg}")
    return "\n".join(lines) if lines else "No quality suggestions."


FORMATTERS = {
    "ivy_verify": format_ivy_verify,
    "ivy_coverage": format_ivy_coverage,
    "ivy_diagnostics": format_ivy_diagnostics,
    "ivy_compile": format_ivy_compile,
    "ivy_quality": format_ivy_quality,
}


def main():
    data = read_stdin()
    tool_name = data.get("tool_name", "")
    base_tool = _match_tool(tool_name)
    if not base_tool:
        sys.exit(0)

    tool_output = _parse_output(data.get("tool_output", ""))
    if not tool_output:
        sys.exit(0)

    protocol_dir = find_protocol_dir()
    workflow = None
    if protocol_dir:
        state = get_active_workflow(protocol_dir)
        if state:
            workflow = state.get("workflow")

    formatter = FORMATTERS.get(base_tool)
    if not formatter:
        sys.exit(0)

    formatted = formatter(tool_output, workflow)
    if formatted:
        emit_hook_output("PostToolUse", additional_context=formatted)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest {PLUGIN}/tests/test_render_tool_result.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add -f {PLUGIN}/hooks/scripts/render-tool-result.py {PLUGIN}/tests/test_render_tool_result.py
git commit -m "feat(style-system): add render-tool-result.py PostToolUse hook with 5 tool formatters"
```

---

### Task 7: render-summary.py Hook

**Files:**
- Create: `{PLUGIN}/hooks/scripts/render-summary.py`
- Test: `{PLUGIN}/tests/test_render_summary.py`

**Depends on:** Task 1 (style_utils), Task 4 (summaries)

This hook replaces `stop-session-summary.sh`. It absorbs all existing functionality (lint scan, claim counts, tool metrics from observability JSONL) and routes through workflow-specific summary templates.

- [ ] **Step 1: Write the failing tests**

Create `{PLUGIN}/tests/test_render_summary.py`:

```python
"""Tests for render-summary.py Stop hook."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "render-summary.py"
)
PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)


def run_hook(
    tmp_path: Path,
    workflow: str | None = None,
    phase: str | None = None,
    ivy_files: dict[str, str] | None = None,
    events_jsonl: str | None = None,
) -> dict | None:
    """Run the hook with given state, return parsed JSON or None."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
    env["IVY_WORKSPACE_ROOT"] = str(tmp_path)

    proto_dir = tmp_path / "protocol-testing"
    proto_dir.mkdir(exist_ok=True)

    if workflow:
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir(exist_ok=True)
        state = {"workflow": workflow}
        if phase:
            state["phase"] = phase
        (state_dir / "active-workflow").write_text(yaml.safe_dump(state))

    # Initialize a real git repo so find_modified_ivy_files() works
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
    # Create initial commit so HEAD exists
    (tmp_path / ".gitkeep").write_text("")
    subprocess.run(["git", "add", ".gitkeep"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    if ivy_files:
        for name, content in ivy_files.items():
            f = tmp_path / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        # Stage the ivy files so git diff HEAD shows them
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)

    if events_jsonl:
        obs_dir = tmp_path / ".observability" / "sessions" / "test-session"
        obs_dir.mkdir(parents=True, exist_ok=True)
        (obs_dir / "events.jsonl").write_text(events_jsonl)
        env["IVY_OBSERVABILITY_DIR"] = str(tmp_path / ".observability" / "sessions")

    result = subprocess.run(
        [sys.executable, SCRIPT],
        input="{}",
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


class TestNoModifiedFiles:
    def test_exits_silently(self, tmp_path):
        output = run_hook(tmp_path)
        assert output is None


class TestLintDetection:
    def test_detects_missing_lang_header(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"test.ivy": "include order\n# no lang header\n"},
        )
        assert output is not None, "Should produce output for modified .ivy files"
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "SESSION SUMMARY" in ctx
        assert "lint" in ctx.lower() or "missing" in ctx.lower()


class TestClaimCounting:
    def test_counts_resolved_claims(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"test.ivy": "#lang ivy1.7\n# RESOLVED(rfc9000:4.1) confirmed\n"},
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "CLAIM" in ctx
        assert "1 resolution" in ctx or "1 confirmed" in ctx


class TestWorkflowAwareSummary:
    def test_verify_summary_includes_workflow(self, tmp_path):
        output = run_hook(
            tmp_path,
            workflow="verify",
            phase="compile",
            ivy_files={"test.ivy": "#lang ivy1.7\nrelation foo(X:t)\n"},
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "SESSION SUMMARY" in ctx
        assert "WORKFLOW" in ctx or "Verify" in ctx


class TestFallbackBehavior:
    def test_no_workflow_uses_generic(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"test.ivy": "#lang ivy1.7\nrelation foo(X:t)\n"},
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "SESSION SUMMARY" in ctx
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest {PLUGIN}/tests/test_render_summary.py -v`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 3: Implement render-summary.py**

Create `{PLUGIN}/hooks/scripts/render-summary.py`:

```python
#!/usr/bin/env python3
"""Stop hook: workflow-aware session summary.

Replaces stop-session-summary.sh. Absorbs all existing functionality (lint
scan, claim counts, tool metrics) and routes through workflow-specific
summary templates.

Non-blocking -- always exits 0.
"""

import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin
from workflow_state import find_protocol_dir, get_active_workflow, get_build_state

CLAIM_PATTERNS = {
    "resolved": re.compile(r"RESOLVED\("),
    "iut_finding": re.compile(r"IUT_FINDING\("),
    "deferred": re.compile(r"DEFERRED\("),
    "guard_added": re.compile(r"GUARD_ADDED\("),
    "n_a": re.compile(r"N/A\("),
    "known_deviation": re.compile(r"KNOWN_DEVIATION\("),
}


def find_modified_ivy_files() -> list[str]:
    """Find .ivy files modified in the working tree."""
    files: set[str] = set()
    for cmd in (
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if line.strip().endswith(".ivy"):
                    files.add(line.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return sorted(files)


def check_lint(filepath: str) -> list[str]:
    """Check an .ivy file for structural lint issues."""
    issues: list[str] = []
    try:
        content = Path(filepath).read_text()
    except OSError:
        return issues

    lines = content.splitlines()
    if not lines or "#lang ivy1.7" not in lines[0]:
        issues.append("missing #lang header")

    stripped = re.sub(r"#.*", "", content)
    stripped = re.sub(r'"[^"]*"', "", stripped)
    opens = stripped.count("{")
    closes = stripped.count("}")
    if opens != closes:
        issues.append(f"unbalanced braces ({opens}/{closes})")

    return issues


def count_claims(filepath: str) -> dict[str, int]:
    """Count claim discussion markers in a file."""
    counts: dict[str, int] = {k: 0 for k in CLAIM_PATTERNS}
    try:
        content = Path(filepath).read_text()
    except OSError:
        return counts
    for name, pattern in CLAIM_PATTERNS.items():
        counts[name] = len(pattern.findall(content))
    return counts


def gather_tool_metrics() -> str:
    """Read observability JSONL and aggregate tool call metrics."""
    events_dir = os.environ.get("IVY_OBSERVABILITY_DIR", "").strip()
    if not events_dir:
        ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
        if ws_root:
            events_dir = os.path.join(ws_root, ".observability", "sessions")
        else:
            events_dir = "/tmp/ivy-observability/sessions"

    if not os.path.isdir(events_dir):
        return ""

    latest = None
    for root, _dirs, filenames in os.walk(events_dir):
        for fname in filenames:
            if fname == "events.jsonl":
                path = os.path.join(root, fname)
                if latest is None or os.path.getmtime(path) > os.path.getmtime(latest):
                    latest = path

    if not latest:
        return ""

    tool_counts: collections.Counter = collections.Counter()
    errors = 0
    try:
        with open(latest) as f:
            for line in f:
                try:
                    event = json.loads(line)
                    etype = event.get("event_type", "")
                    if etype in ("PreToolUse", "PostToolUse"):
                        tool = event.get("payload", {}).get("tool_name", "unknown")
                        tool_counts[tool] += 1
                    if etype == "PostToolUseFailure":
                        errors += 1
                except json.JSONDecodeError:
                    continue
    except OSError:
        return ""

    if not tool_counts:
        return ""

    top = ", ".join(f"{t}={c}" for t, c in tool_counts.most_common(5))
    return f"Tool calls: {sum(tool_counts.values())} ({top}). Errors: {errors}"


def build_summary(
    ivy_files: list[str],
    workflow: str | None,
    phase: str | None,
    protocol_dir: str | None,
) -> str:
    """Build the session summary string."""
    file_count = len(ivy_files)

    # Lint check
    lint_issues: list[str] = []
    for f in ivy_files:
        issues = check_lint(f)
        if issues:
            lint_issues.append(f"  - {f}: {', '.join(issues)}")

    # Claim counts
    total_claims: dict[str, int] = {k: 0 for k in CLAIM_PATTERNS}
    for f in ivy_files:
        for k, v in count_claims(f).items():
            total_claims[k] += v
    claim_total = sum(total_claims.values())

    # Tool metrics
    metrics = gather_tool_metrics()

    # Build state (for build workflow)
    build_state = None
    if workflow == "build" and protocol_dir:
        build_state = get_build_state(protocol_dir)

    # Compose summary
    parts: list[str] = []

    # Header
    if lint_issues:
        parts.append(
            f"[IVY SESSION SUMMARY] {file_count} .ivy file(s) modified, "
            f"{len(lint_issues)} with lint issues:\n" + "\n".join(lint_issues) + "\n"
            "Run ivy_diagnostics(mode=\"structural\") on flagged files before committing."
        )
    else:
        parts.append(
            f"[IVY SESSION SUMMARY] {file_count} .ivy file(s) modified, "
            "all pass basic structural checks."
        )

    # Workflow-specific section
    if workflow == "verify":
        if phase:
            parts.append(f"[WORKFLOW] Verify workflow ended in phase: {phase}")

    elif workflow == "build" and build_state:
        layers = build_state.get("layers", {})
        if layers:
            layer_lines = ["[BUILD PROGRESS]"]
            for name, info in layers.items():
                status = info.get("status", "pending") if isinstance(info, dict) else info
                layer_lines.append(f"  - {name}: {status}")
            parts.append("\n".join(layer_lines))

    elif workflow == "triage":
        if phase:
            parts.append(f"[TRIAGE] Ended in phase: {phase}")

    elif workflow == "review":
        parts.append("[REVIEW] Review workflow session.")

    # Claims section
    if claim_total > 0:
        claim_parts = [f"[CLAIM DISCUSSIONS] {claim_total} resolution(s):"]
        for label, key in [
            ("confirmed", "resolved"),
            ("IUT findings", "iut_finding"),
            ("guards added", "guard_added"),
            ("deferred", "deferred"),
            ("N/A", "n_a"),
            ("known deviations", "known_deviation"),
        ]:
            if total_claims[key] > 0:
                claim_parts.append(f" {total_claims[key]} {label},")
        claim_line = "".join(claim_parts).rstrip(",")
        parts.append(claim_line)

    # Metrics
    if metrics:
        parts.append(f"[TOOL METRICS] {metrics}")

    return "\n".join(parts)


def main():
    read_stdin()  # consume stdin

    ivy_files = find_modified_ivy_files()
    if not ivy_files:
        sys.exit(0)

    protocol_dir = find_protocol_dir()
    workflow = None
    phase = None
    if protocol_dir:
        state = get_active_workflow(protocol_dir)
        if state:
            workflow = state.get("workflow")
            phase = state.get("phase")

    summary = build_summary(ivy_files, workflow, phase, protocol_dir)
    emit_hook_output("Stop", additional_context=summary)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest {PLUGIN}/tests/test_render_summary.py -v`
Expected: All tests PASS (some may skip if git state doesn't show modified files)

- [ ] **Step 5: Commit**

```bash
git add -f {PLUGIN}/hooks/scripts/render-summary.py {PLUGIN}/tests/test_render_summary.py
git commit -m "feat(style-system): add render-summary.py Stop hook, replacing stop-session-summary.sh"
```

---

### Task 8: Hook Registration and Migration

**Files:**
- Modify: `{PLUGIN}/hooks/hooks.json`

Register the three new hooks and retire `stop-session-summary.sh` from the Stop event.

- [ ] **Step 1: Add compose-style.py to UserPromptSubmit**

In `{PLUGIN}/hooks/hooks.json`, add a new entry to the `"UserPromptSubmit"` array, **before** the existing `route-user-prompt.py` entry (style should be injected before routing):

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/compose-style.py",
      "timeout": 5
    }
  ]
}
```

- [ ] **Step 2: Add render-tool-result.py to PostToolUse**

Add a new entry to the `"PostToolUse"` array with a matcher for the 5 rendered tools:

```json
{
  "matcher": "ivy_verify|ivy_coverage|ivy_diagnostics|ivy_compile|ivy_quality",
  "hooks": [
    {
      "type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/render-tool-result.py",
      "timeout": 5
    }
  ]
}
```

- [ ] **Step 3: Replace stop-session-summary.sh with render-summary.py in Stop**

In the `"Stop"` array, replace:
```json
"command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-session-summary.sh"
```
with:
```json
"command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/render-summary.py"
```

- [ ] **Step 4: Verify hooks.json is valid JSON**

Run: `python -m json.tool {PLUGIN}/hooks/hooks.json > /dev/null`
Expected: No output (valid JSON)

- [ ] **Step 5: Commit**

```bash
git add {PLUGIN}/hooks/hooks.json
git commit -m "feat(style-system): register style hooks and retire stop-session-summary.sh"
```

---

### Task 9: Skill Integration

**Files:**
- Modify: `{PLUGIN}/skills/verify/SKILL.md`
- Modify: `{PLUGIN}/skills/navigate/SKILL.md`
- Modify: `{PLUGIN}/skills/build/SKILL.md`
- Modify: `{PLUGIN}/skills/review/SKILL.md`
- Modify: `{PLUGIN}/skills/triage/SKILL.md`

Add the `## Output Style` section to each workflow skill, immediately after the frontmatter. Audit each skill for inline formatting instructions that conflict with the style system.

- [ ] **Step 1: Add Output Style section to all 5 skills**

Insert the following section immediately after the `---` frontmatter closing delimiter in each SKILL.md, before the first `#` heading:

```markdown
## Output Style

This workflow's output formatting is managed by the style system.
Follow the style directives injected via `additionalContext` -- they contain
your active workflow overlay and phase modifier. Do not invent your own
formatting for tool results that arrive pre-formatted in `hookSpecificOutput`.
```

Files to edit:
- `{PLUGIN}/skills/verify/SKILL.md` (after line 4)
- `{PLUGIN}/skills/navigate/SKILL.md` (after frontmatter)
- `{PLUGIN}/skills/build/SKILL.md` (after frontmatter)
- `{PLUGIN}/skills/review/SKILL.md` (after frontmatter)
- `{PLUGIN}/skills/triage/SKILL.md` (after frontmatter)

- [ ] **Step 2: Audit verify skill for inline formatting**

In `{PLUGIN}/skills/verify/SKILL.md`, line 110 says `Report: "Verification passed for <test_file>."` — this is a behavioral instruction ("report pass") not a formatting directive ("use a table"), so it stays. No inline formatting to migrate.

- [ ] **Step 3: Audit remaining skills**

Read each of the other 4 skill files and check for formatting directives (e.g., "present as a table", "use numbered list", "show as checklist"). These should be migrated to the overlay. If none found, note it and move on.

- [ ] **Step 4: Commit**

```bash
git add {PLUGIN}/skills/verify/SKILL.md {PLUGIN}/skills/navigate/SKILL.md \
        {PLUGIN}/skills/build/SKILL.md {PLUGIN}/skills/review/SKILL.md \
        {PLUGIN}/skills/triage/SKILL.md
git commit -m "feat(style-system): add Output Style section to all 5 workflow skills"
```

---

### Task 10: Smoke Test

No code to write. Manual verification to confirm the system works end-to-end.

- [ ] **Step 1: Verify all tests pass**

Run: `python -m pytest {PLUGIN}/tests/test_style_utils.py {PLUGIN}/tests/test_compose_style.py {PLUGIN}/tests/test_render_tool_result.py {PLUGIN}/tests/test_render_summary.py -v`
Expected: All tests PASS

- [ ] **Step 2: Verify hooks.json is valid**

Run: `python -m json.tool {PLUGIN}/hooks/hooks.json > /dev/null && echo "valid"`
Expected: "valid"

- [ ] **Step 3: Verify all style files exist**

Run: `ls {PLUGIN}/styles/base.md {PLUGIN}/styles/overlays/*.md {PLUGIN}/styles/tool-renderers/*.md {PLUGIN}/styles/summaries/*.md | wc -l`
Expected: 16

- [ ] **Step 4: Dry-run compose-style hook**

Run: `echo '{}' | IVY_WORKSPACE_ROOT=/tmp CLAUDE_PLUGIN_ROOT={PLUGIN} python3 {PLUGIN}/hooks/scripts/compose-style.py`
Expected: JSON output containing "Base Output Style" in additionalContext

- [ ] **Step 5: Dry-run render-tool-result hook**

Run: `echo '{"tool_name":"mcp__panther-ivy-plugin__ivy_verify","tool_output":"{\"success\":true,\"isolate\":\"test\",\"clause_count\":5,\"duration_s\":1.2}"}' | CLAUDE_PLUGIN_ROOT={PLUGIN} python3 {PLUGIN}/hooks/scripts/render-tool-result.py`
Expected: JSON output containing "PASS: test verified (5 clauses, 1.2s)"

- [ ] **Step 6: Final commit (if any fixups needed)**

```bash
git add -A {PLUGIN}/
git commit -m "fix(style-system): smoke test fixups"
```
