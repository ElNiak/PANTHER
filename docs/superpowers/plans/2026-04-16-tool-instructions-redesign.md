# Tool Instructions Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure MCP/LSP tool documentation in panther-ivy-plugin to add error handling, timing/concurrency, hook lifecycle docs, and eliminate duplication across 9 layers.

**Architecture:** Three new reference files + rewrite of tool-catalog.md + updates to SKILL.md, CLAUDE.md, lsp-patterns.md. One code change: add `rendering` and `tier` fields to `_TOOL_METADATA`. The design spec at `docs/superpowers/specs/2026-04-16-tool-instructions-redesign.md` defines the exact format for each file — subagents should read it for templates and content structure.

**Tech Stack:** Markdown (documentation), Python (metadata fields), pytest (metadata validation).

**Key paths:**
- Plugin root: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`
- ivy-lsp root: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
- Reference dir: `{plugin}/skills/ivy-toolkit/references/`

---

### Task 1: Add `rendering` and `tier` to `_TOOL_METADATA` (ivy-lsp)

**Files:**
- Modify: `{ivy-lsp}/ivy_lsp/mcp/tools/__init__.py`
- Test: `{ivy-lsp}/tests/test_tool_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tool_metadata.py
"""Tests for tool metadata completeness."""

from ivy_lsp.mcp.tools import get_tool_metadata

VALID_TIERS = {"instant", "fast", "slow", "blocking"}
VALID_RENDERING = {"hook", "raw"}
HOOK_RENDERED_TOOLS = {"ivy_verify", "ivy_compile", "ivy_diagnostics", "ivy_coverage", "ivy_quality"}


class TestToolMetadataFields:
    def test_all_tools_have_tier(self):
        all_meta = get_tool_metadata()
        for name, meta in all_meta.items():
            assert "tier" in meta, f"{name} missing 'tier' field"
            assert meta["tier"] in VALID_TIERS, f"{name} has invalid tier: {meta['tier']}"

    def test_all_tools_have_rendering(self):
        all_meta = get_tool_metadata()
        for name, meta in all_meta.items():
            assert "rendering" in meta, f"{name} missing 'rendering' field"
            assert meta["rendering"] in VALID_RENDERING, f"{name} has invalid rendering: {meta['rendering']}"

    def test_hook_rendered_tools_match(self):
        all_meta = get_tool_metadata()
        actual_hook = {name for name, meta in all_meta.items() if meta.get("rendering") == "hook"}
        assert actual_hook == HOOK_RENDERED_TOOLS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd {ivy-lsp} && python -m pytest tests/test_tool_metadata.py -v`
Expected: FAIL — `'tier' not in meta` and `'rendering' not in meta`

- [ ] **Step 3: Add `rendering` and `tier` fields to every entry in `_TOOL_METADATA`**

Read the existing `_TOOL_METADATA` dict in `ivy_lsp/mcp/tools/__init__.py`. Add two fields to every entry:

- `"rendering": "hook"` for: ivy_verify, ivy_compile, ivy_diagnostics, ivy_coverage, ivy_quality
- `"rendering": "raw"` for all other tools
- `"tier"` values based on `_TOOL_TIMEOUTS` and typical execution time:
  - `"instant"` (<100ms): ivy_capabilities, ivy_health_check, ivy_workspace, ivy_workflow_state
  - `"fast"` (100ms–5s): ivy_model_info, ivy_diagnostics, ivy_scope, ivy_visualize, ivy_model_summary, ivy_patterns, ivy_pattern_scaffold, ivy_manifest, ivy_find_variants, ivy_serdes_correlation, ivy_rfc_get, ivy_rfc_search, ivy_rfc_section
  - `"slow"` (5s–60s): ivy_quality, ivy_coverage, ivy_extract_requirements, ivy_change_impact, ivy_verification_dashboard, ivy_include_graph
  - `"blocking"` (60s+): ivy_verify, ivy_compile, ivy_index, ivy_iut_test

- [ ] **Step 4: Run test to verify it passes**

Run: `cd {ivy-lsp} && python -m pytest tests/test_tool_metadata.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run full test suite**

Run: `cd {ivy-lsp} && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5`
Expected: No regressions

- [ ] **Step 6: Commit**

```bash
cd {ivy-lsp}
git add ivy_lsp/mcp/tools/__init__.py tests/test_tool_metadata.py
git commit -m "feat(tools): add rendering and tier fields to _TOOL_METADATA"
```

---

### Task 2: Rewrite `tool-catalog.md` with standardized entries

**Files:**
- Rewrite: `{plugin}/skills/ivy-toolkit/references/tool-catalog.md`

- [ ] **Step 1: Read the design spec Section 3** for the standardized entry format (table with Parameters, Returns, Timeout, Tier, Rendering, Concurrency + Errors + When to use).

- [ ] **Step 2: Read `_TOOL_METADATA` and `_TOOL_TIMEOUTS`** from `{ivy-lsp}/ivy_lsp/mcp/tools/__init__.py` for exact values per tool.

- [ ] **Step 3: Read each tool's implementation** to extract parameter types, return schemas, and error patterns. Key files:
  - `{ivy-lsp}/ivy_lsp/mcp/tools/verification.py` (ivy_verify, ivy_compile, ivy_model_info)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/analysis.py` (ivy_diagnostics, ivy_include_graph, ivy_capabilities, ivy_scope)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/traceability.py` (ivy_coverage)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/traceability_extraction.py` (ivy_extract_requirements, ivy_manifest)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/rfc_tools.py` (ivy_rfc_get, ivy_rfc_search, ivy_rfc_section)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/visualization.py` (ivy_visualize, ivy_model_summary)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/quality.py` (ivy_quality)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/patterns.py` (ivy_patterns, ivy_pattern_scaffold)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/propagation.py` (ivy_find_variants, ivy_serdes_correlation, ivy_change_impact)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/workspace.py` (ivy_workspace)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/workflow_state.py` (ivy_workflow_state)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/iut_testing.py` (ivy_iut_test)

- [ ] **Step 4: Write tool-catalog.md** with all 25 tools in standardized format. Group into the 8 sections from spec Section 3. Each entry MUST include:
  - Parameters with types and defaults (from docstrings)
  - Returns schema (from docstrings/code)
  - Timeout (from `_TOOL_TIMEOUTS`)
  - Tier (from `_TOOL_METADATA["tier"]`)
  - Rendering (from `_TOOL_METADATA["rendering"]`)
  - Concurrency notes where relevant
  - 1-3 tool-specific error patterns with recovery
  - One-line "When to use" guidance

Example entry for reference (ivy_verify):

```markdown
### ivy_verify
Run ivy_check on an Ivy file for formal property verification.

| Field | Value |
|-------|-------|
| Parameters | relative_path (str), isolate (str \| None = None) |
| Returns | { success, diagnostics, diagnostic_count, raw_output, duration_seconds } |
| Timeout | 600s |
| Tier | blocking |
| Rendering | hook |
| Concurrency | shares compilation semaphore (IVY_LSP_COMPILE_WORKERS=2) |

**Errors:**
- `Model is still building` → model not ready; retry in 30s or use ivy_diagnostics(mode="structural")
- `No .ivy files found` → workspace not set or wrong relative_path
- `TIMEOUT after 600s` → complex proof; try isolating with `isolate` param or increase IVY_LSP_TOOL_TIMEOUT_IVY_VERIFY

**When to use:** After writing or modifying Ivy specs for formal proof. Prefer ivy_diagnostics(mode="structural") for fast edit-verify iteration.
```

- [ ] **Step 5: Verify cross-references** — check that all tool names in the catalog match `_TOOL_METADATA` keys exactly.

- [ ] **Step 6: Commit**

```bash
cd {plugin}
git add skills/ivy-toolkit/references/tool-catalog.md
git commit -m "docs: rewrite tool-catalog.md with standardized entries (errors, tiers, rendering)"
```

---

### Task 3: Create `error-reference.md`

**Files:**
- Create: `{plugin}/skills/ivy-toolkit/references/error-reference.md`

- [ ] **Step 1: Read design spec Section 4** for the 9 error classes to document and the entry format.

- [ ] **Step 2: Read tool implementations** to find actual error messages and response patterns. Key sources:
  - `{ivy-lsp}/ivy_lsp/mcp/tools/__init__.py` — `_model_not_ready_response()` function (model not ready pattern)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/__init__.py` — `safe_tool` decorator (timeout handling)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/rfc_tools.py` — `error_response()` calls (RFC service errors)
  - `{ivy-lsp}/ivy_lsp/mcp/tools/workspace.py` — workspace error patterns
  - `{plugin}/hooks/hooks.json` — hook-related errors

- [ ] **Step 3: Write error-reference.md** with all 9 error classes from the spec. Each class needs: Pattern, Tools affected, Cause, Recovery steps. The spec lists:
  1. Model Not Ready
  2. Workspace Not Set
  3. RFC Service Not Initialized
  4. Network Failure / RFC fetch
  5. Compilation Failure
  6. Verification Failure / Counterexample
  7. Tool Timeout
  8. MCP Server Unreachable
  9. Sidecar Delegation Failure

- [ ] **Step 4: Commit**

```bash
cd {plugin}
git add skills/ivy-toolkit/references/error-reference.md
git commit -m "docs: add cross-cutting error reference with 9 error classes"
```

---

### Task 4: Create `timing-and-concurrency.md`

**Files:**
- Create: `{plugin}/skills/ivy-toolkit/references/timing-and-concurrency.md`

- [ ] **Step 1: Read design spec Section 5** for the tier table, concurrency model, and sequencing rules.

- [ ] **Step 2: Read `_TOOL_TIMEOUTS` and `_TOOL_METADATA`** for exact timeout values and tier assignments.

- [ ] **Step 3: Read `{ivy-lsp}/ivy_lsp/mcp/tools/__init__.py`** for concurrency implementation: `_tool_semaphore`, `_get_effective_timeout`, `IVY_LSP_TOOL_TIMEOUT_SCALE`, `IVY_LSP_MAX_CONCURRENT_TOOLS`. Also read `{ivy-lsp}/ivy_lsp/infra/config.py` for `compile_workers` and `max_concurrent_tools` defaults.

- [ ] **Step 4: Write timing-and-concurrency.md** with:
  - Performance tier table (4 tiers with tool lists — from spec Section 5)
  - Full timeout table (all 28 tools with configured timeout in seconds + env var override)
  - Concurrency model (semaphore, compile workers, model-dependency wait)
  - Sequencing rules (5 rules from spec Section 5)

- [ ] **Step 5: Commit**

```bash
cd {plugin}
git add skills/ivy-toolkit/references/timing-and-concurrency.md
git commit -m "docs: add timing, timeout table, and concurrency model reference"
```

---

### Task 5: Create `hook-lifecycle.md`

**Files:**
- Create: `{plugin}/skills/ivy-toolkit/references/hook-lifecycle.md`

- [ ] **Step 1: Read design spec Section 6** for the lifecycle diagram, hook tables, and rendering rules.

- [ ] **Step 2: Read `{plugin}/hooks/hooks.json`** for the complete hook configuration. Extract: which hooks fire for which events (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart), their matchers, and their script paths.

- [ ] **Step 3: Write hook-lifecycle.md** with:
  - Lifecycle diagram (text: User prompt → UserPromptSubmit → tool selection → PreToolUse → execution → PostToolUse → result)
  - PreToolUse hooks table (4 hooks from spec)
  - PostToolUse hooks table (5+ hooks from spec)
  - Rendering rules (3 bullet points: don't reformat hook-rendered tools, DO format raw tools, style adapts to workflow overlay)
  - Rendered tools table (5 hook-rendered + "all others raw")
  - UserPromptSubmit hooks table
  - SessionStart hooks list

- [ ] **Step 4: Commit**

```bash
cd {plugin}
git add skills/ivy-toolkit/references/hook-lifecycle.md
git commit -m "docs: add hook lifecycle reference documenting full tool invocation pipeline"
```

---

### Task 6: Update `lsp-patterns.md` with standardized entries

**Files:**
- Modify: `{plugin}/skills/ivy-toolkit/references/lsp-patterns.md`

- [ ] **Step 1: Read the existing lsp-patterns.md** (107 lines). Keep: scoping policy, LSP-vs-MCP comparison, end-to-end workflow example, key takeaways.

- [ ] **Step 2: Read design spec Section 9** for the standardized LSP entry format (same table format as tool-catalog.md).

- [ ] **Step 3: Add standardized entries** for all 7 LSP operations (hover, goToDefinition, findReferences, documentSymbol, workspaceSymbol, prepareCallHierarchy/incomingCalls, outgoingCalls). Each entry gets: Parameters, Returns, Tier (instant or fast), Rendering (all raw), Errors, When to use. Insert these AFTER the scoping policy section and BEFORE the LSP-vs-MCP comparison.

- [ ] **Step 4: Commit**

```bash
cd {plugin}
git add skills/ivy-toolkit/references/lsp-patterns.md
git commit -m "docs: add standardized LSP operation entries to lsp-patterns.md"
```

---

### Task 7: Update `SKILL.md` cross-references

**Files:**
- Modify: `{plugin}/skills/ivy-toolkit/SKILL.md`

- [ ] **Step 1: Read current SKILL.md** (164 lines).

- [ ] **Step 2: Update the "Reference Files" section** at the end to list all 5 reference files:
  - `references/tool-catalog.md` — per-tool parameters, errors, tiers, rendering
  - `references/error-reference.md` — cross-cutting error patterns and recovery
  - `references/timing-and-concurrency.md` — performance tiers, timeouts, concurrency model
  - `references/hook-lifecycle.md` — tool invocation pipeline and rendering rules
  - `references/lsp-patterns.md` — LSP operations, scoping policy, coordination examples

- [ ] **Step 3: Add a "Rendering Awareness" note** after the Mode Mapping section:

```markdown
## Rendering Awareness

5 tools have PostToolUse hook formatters that reformat raw JSON into workflow-appropriate prose:
ivy_verify, ivy_compile, ivy_diagnostics, ivy_coverage, ivy_quality.

**Do NOT reformat** results from these tools — they arrive pre-formatted.
**DO format** results from all other tools per ivy-formatting.md rules (prose or tables, no raw JSON).

See references/hook-lifecycle.md for the full rendering pipeline.
```

- [ ] **Step 4: Commit**

```bash
cd {plugin}
git add skills/ivy-toolkit/SKILL.md
git commit -m "docs: update SKILL.md with cross-references to new reference files and rendering awareness"
```

---

### Task 8: Dedup `CLAUDE.md` Tool Rules

**Files:**
- Modify: `{plugin}/CLAUDE.md`

- [ ] **Step 1: Read current CLAUDE.md** lines 54-89 (Tool Rules section).

- [ ] **Step 2: Replace the Tool Rules section** with the deduped version per spec Section 8. Keep:
  - The "## Tool Rules — CRITICAL" heading
  - The CLI-to-MCP mapping table (enforcement — unchanged)
  - The LSP scoping policy paragraph (enforcement — unchanged)
  - The Note about LSP diagnostics push (unchanged)

Replace the 7 tool category paragraphs (Analysis, Workflow state, IUT testing, Coverage, RFC lookup, Visualization, Quality) with compact category listings:

```markdown
**Verification & compilation**: ivy_verify, ivy_compile, ivy_model_info
**Analysis & diagnostics**: ivy_diagnostics (structural/full), ivy_include_graph, ivy_capabilities, ivy_scope
**Workflow & workspace**: ivy_workspace, ivy_workflow_state, ivy_health_check, ivy_index
**Coverage & traceability**: ivy_coverage (stats/gaps/matrix), ivy_extract_requirements, ivy_manifest
**RFC lookup**: ivy_rfc_get, ivy_rfc_search, ivy_rfc_section
**Visualization**: ivy_visualize, ivy_model_summary
**Quality & patterns**: ivy_quality, ivy_patterns, ivy_pattern_scaffold
**Propagation**: ivy_find_variants, ivy_serdes_correlation, ivy_change_impact
**Testing**: ivy_iut_test, ivy_verification_dashboard

For parameters, timeouts, error handling, and rendering details, see the **ivy-toolkit** skill.
```

- [ ] **Step 3: Verify** the CLI-to-MCP table and LSP policy are preserved unchanged.

- [ ] **Step 4: Commit**

```bash
cd {plugin}
git add CLAUDE.md
git commit -m "docs: dedup CLAUDE.md Tool Rules — move operational detail to ivy-toolkit references"
```

---

### Task 9: Update submodule pointers

**Files:**
- Submodule pointer updates in panther_ivy and parent repo

- [ ] **Step 1: Verify all ivy-lsp tests pass**

Run: `cd {ivy-lsp} && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass (1 pre-existing failure in test_include_resolver_fallback is known)

- [ ] **Step 2: Commit ivy-lsp pointer in panther_ivy**

```bash
cd panther/plugins/services/testers/panther_ivy
git add submodules/ivy-lsp submodules/panther-ivy-plugin
git commit -m "chore: update ivy-lsp and panther-ivy-plugin for tool instructions redesign"
```

- [ ] **Step 3: Commit panther_ivy pointer in parent repo**

```bash
cd /Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/lsp-to-claude
git add panther/plugins/services/testers/panther_ivy
git commit -m "chore: update panther_ivy submodule for tool instructions redesign"
```
