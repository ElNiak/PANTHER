# Tool Instructions Redesign for panther-ivy-plugin

**Date:** 2026-04-16
**Status:** Draft
**Scope:** Restructure MCP/LSP tool documentation across the panther-ivy-plugin to eliminate duplication, add error handling guidance, document timing/concurrency, and make the rendering pipeline visible.

## Summary

The panther-ivy-plugin's tool documentation is spread across 9 layers (CLAUDE.md, tool-reference.md, ivy-toolkit SKILL.md, tool-catalog.md, workflow skills, agent prompts, hooks, lsp-patterns.md, and MCP server instructions). These layers serve different audiences at different times — that's correct and should be preserved. The problem is duplication between layers, missing error/timing/rendering documentation, and no clear charter for what each layer owns.

This redesign gives each layer a clear charter, adds three new reference files (error patterns, timing/concurrency, hook lifecycle), restructures the tool catalog with standardized entries, and adds `rendering` and `tier` fields to `_TOOL_METADATA` as the source of truth.

## Goals

1. **Error handling guidance** — Every tool gets documented error patterns with recovery actions. Cross-cutting errors (model not ready, workspace not set, network failure) live in a shared reference.
2. **Timing and concurrency** — Performance tiers, timeout table, concurrency model, and sequencing rules so Claude can make informed tool selection decisions.
3. **Rendering pipeline visibility** — Claude knows which tools have PostToolUse formatters (don't reformat) and which return raw JSON (format per ivy-formatting.md).
4. **Layer deduplication** — Each layer has a charter. No layer duplicates another's content. CLAUDE.md shrinks to safety rules + tool name lists. Operational detail lives in ivy-toolkit references.

## Non-Goals

- Changing tool behavior or parameters.
- Adding new tools.
- Building a doc generator script (manual docs are sufficient for 25 tools).
- Changing workflow skill logic (only their tool documentation sections).

## Design

### 1. Layer Charters

| Layer | Loaded When | Owns | Must NOT Contain |
|-------|------------|------|------------------|
| CLAUDE.md Tool Rules | Every `.ivy` file interaction | Safety rules (CLI-vs-MCP enforcement), tool category listing (names only), LSP scoping policy, workspace rules | Parameter details, timeouts, error patterns, usage examples |
| tool-reference.md rule | Every `.ivy` file interaction | Quick-lookup table (tool → modes → key params) | Usage guidance, error patterns, rendering notes |
| ivy-toolkit SKILL.md | On demand (skill activation) | Tool architecture overview, quick reference table (purpose + when-to-use + mode), mode mapping (FAST/DEEP), tool selection decision matrix, coordination workflows | Full parameter docs, error patterns, timeout details |
| ivy-toolkit references/ | Loaded by SKILL.md | Per-tool parameters, errors, timing, concurrency, hook lifecycle, LSP patterns | Workflow sequencing, safety rules |
| Workflow skills | Per workflow activation | Phase-specific tool sequencing with parameter values | Tool parameter docs, error interpretation |
| Agent prompts | Per agent dispatch | Agent-specific tool selection strategies, domain-specific error interpretation | Duplicates of error-reference.md content |

### 2. Reference Directory Structure

```
skills/ivy-toolkit/references/
├── tool-catalog.md            # Standardized per-tool entries (params, returns, timeout, tier, rendering, errors)
├── error-reference.md         # Cross-cutting error patterns and recovery strategies
├── timing-and-concurrency.md  # Performance tiers, timeout table, concurrency model, sequencing rules
├── hook-lifecycle.md          # Full tool lifecycle: PreToolUse → execution → PostToolUse → rendering
└── lsp-patterns.md            # LSP operations in same format + scoping policy + LSP-vs-MCP comparison
```

### 3. Standardized Tool Entry Format (tool-catalog.md)

Each of the 25 MCP tools gets this structure:

```markdown
### tool_name
One-line description.

| Field | Value |
|-------|-------|
| Parameters | param1 (type), param2 (type, default) |
| Returns | { field1, field2, ... } |
| Timeout | Ns |
| Tier | instant/fast/slow/blocking |
| Rendering | hook / raw |
| Concurrency | notes (e.g., "shares compilation semaphore") |

**Errors:**
- `error message pattern` → what it means; recovery action

**When to use:** One sentence guidance on when to prefer this tool.
```

Tools are grouped by function (8 sections):
1. Verification and Compilation (ivy_verify, ivy_compile, ivy_model_info)
2. Analysis and Diagnostics (ivy_diagnostics, ivy_include_graph, ivy_capabilities, ivy_scope)
3. Coverage and Traceability (ivy_coverage, ivy_extract_requirements, ivy_manifest)
4. RFC Lookup (ivy_rfc_get, ivy_rfc_search, ivy_rfc_section)
5. Visualization (ivy_visualize, ivy_model_summary)
6. Quality and Patterns (ivy_quality, ivy_patterns, ivy_pattern_scaffold)
7. Propagation (ivy_find_variants, ivy_serdes_correlation, ivy_change_impact)
8. Workspace and State (ivy_workspace, ivy_workflow_state, ivy_health_check, ivy_index, ivy_verification_dashboard, ivy_iut_test)

### 4. Error Reference (error-reference.md)

Organized by error class (not by tool). Each entry:

```markdown
## Error Class Name
Pattern: "error message text" or { structured response pattern }
Tools: list of tools that produce this error
Cause: Why this happens.
Recovery: Step-by-step recovery actions.
```

Cross-cutting error classes to document:
- Model Not Ready (6+ tools affected)
- Workspace Not Set (3+ tools affected)
- RFC Service Not Initialized (3 tools)
- Network Failure / RFC fetch (3 tools)
- Compilation Failure (ivy_compile)
- Verification Failure / Counterexample (ivy_verify)
- Tool Timeout (any tool)
- MCP Server Unreachable (any tool)
- Sidecar Delegation Failure (non-local_only tools)

Tool-specific errors stay in tool-catalog.md per-tool entries. This file covers patterns that span multiple tools or need non-obvious recovery strategies.

### 5. Timing and Concurrency (timing-and-concurrency.md)

**Performance tiers:**

| Tier | Typical Time | Tools |
|------|-------------|-------|
| instant | <100ms | ivy_capabilities, ivy_health_check, ivy_workspace, ivy_workflow_state, ivy_rfc_get (cached) |
| fast | 100ms–5s | ivy_diagnostics(structural), ivy_model_info, ivy_scope, ivy_visualize, ivy_model_summary, ivy_patterns, ivy_pattern_scaffold, ivy_rfc_get, ivy_rfc_search, ivy_rfc_section, ivy_manifest, ivy_find_variants, ivy_serdes_correlation |
| slow | 5s–60s | ivy_diagnostics(full), ivy_quality, ivy_coverage (all modes), ivy_extract_requirements, ivy_change_impact, ivy_verification_dashboard, ivy_include_graph |
| blocking | 60s–600s | ivy_verify (600s), ivy_compile (360s), ivy_index (300s), ivy_iut_test (180s) |

**Timeout table:** Every tool with its configured timeout in seconds and the env var override pattern (`IVY_LSP_TOOL_TIMEOUT_<TOOL_NAME_UPPER>`). Documents `IVY_LSP_TOOL_TIMEOUT_SCALE` for global scaling.

**Concurrency model:**
- Maximum 4 concurrent tool calls (`IVY_LSP_MAX_CONCURRENT_TOOLS`, configurable)
- Semaphore-based: 5th call blocks until a slot opens
- ivy_verify and ivy_compile share the compilation semaphore (2 workers, `IVY_LSP_COMPILE_WORKERS`)
- Model-dependent tools (`needs_model: true`) wait for model build before executing (don't block the semaphore while waiting)

**Sequencing rules:**
- Prefer ivy_diagnostics(mode="structural") (instant) over ivy_verify (blocking) during edit-verify loops
- Never call a blocking tool inside a tight retry loop
- After ivy_verify, the model is warm — ivy_coverage will be fast
- Don't dispatch 4 blocking tools in parallel — stagger: verify first, then compile
- RFC tools are instant when cached, fast on first fetch — safe to call inline

### 6. Hook Lifecycle (hook-lifecycle.md)

Documents the full tool invocation lifecycle:

```
User prompt → UserPromptSubmit hooks → Claude selects tool
  → PreToolUse hooks → Tool execution → PostToolUse hooks → Result to Claude
```

**PreToolUse hooks:**

| Hook | Applies to | Effect |
|------|-----------|--------|
| block-direct-ivy.sh | Bash `ivy_check`/`ivyc`/`ivy_show`/`ivy_to_cpp` | Blocks with error; enforces MCP-only |
| check-workspace-scope.py | Write/Edit on `.ivy` files | Blocks writes outside active workspace |
| ivy_verify prompt tip | ivy_verify | Suggests ivy_diagnostics(structural) first |
| MCP health check | Any mcp__ tool | Validates server is alive |

**PostToolUse hooks:**

| Hook | Applies to | Effect |
|------|-----------|--------|
| render-tool-result.py | ivy_verify, ivy_coverage, ivy_diagnostics, ivy_compile, ivy_quality | Reformats JSON to workflow-appropriate prose/tables |
| post-write-ivy-lint.sh | Write/Edit on `.ivy` files | Runs ivy_diagnostics(structural) automatically |
| track-workflow-skill.py | Skill invocations | Records phase transitions |
| auto-load-skill-references.py | Skill invocations | Injects reference files |
| record-workflow-error.py | Tool errors | Captures for debugging |

**Rendering rules:**
- Do NOT reformat results from: ivy_verify, ivy_coverage, ivy_diagnostics, ivy_compile, ivy_quality (hook-rendered)
- DO format results from all other tools per ivy-formatting.md (prose/tables, no raw JSON)
- Rendering style adapts to active workflow overlay

**UserPromptSubmit hooks:**

| Hook | Effect |
|------|--------|
| compose-style.py | Injects active workflow overlay |
| route-user-prompt.py | Routes to active workflow skill |

**SessionStart hooks:** cleanup-stale-pids.sh, cleanup-stale-workflow.py, detect-ivy-workspace.sh, wait-for-indexing.sh

### 7. Metadata Source of Truth

Add two new fields to `_TOOL_METADATA` in `ivy_lsp/mcp/tools/__init__.py`:

**`rendering`** — `"hook"` for the 5 tools with PostToolUse formatters, `"raw"` for all others. The hook-lifecycle.md and tool-catalog.md reference this field.

**`tier`** — `"instant"`, `"fast"`, `"slow"`, or `"blocking"`. The timing-and-concurrency.md references this field.

These fields join the existing `cost`, `category`, `needs_model`, and `local_only` fields.

### 8. CLAUDE.md Dedup

Replace the current ~35-line Tool Rules section with a compact version:

- CLI-to-MCP mapping table: unchanged (enforcement)
- LSP scoping policy: unchanged (enforcement)
- Tool categories: tool names grouped by function, one line per category, no inline parameter descriptions
- Footer: "For parameters, timeouts, error handling, and rendering details, see the ivy-toolkit skill."

Estimated reduction: ~35 lines → ~20 lines, with zero information loss (moved to ivy-toolkit references).

### 9. lsp-patterns.md Update

Each of the 7 LSP operations gets the same standardized entry format as MCP tools:

```markdown
### operation_name
One-line description.

| Field | Value |
|-------|-------|
| Parameters | filePath (str), line (int), character (int) |
| Returns | description |
| Tier | instant/fast |
| Rendering | raw |

**Errors:**
- common error → cause; recovery

**When to use:** guidance
```

The scoping policy, LSP-vs-MCP comparison, and end-to-end workflow example sections stay.

## Files Changed

**New files (in panther-ivy-plugin):**
- `skills/ivy-toolkit/references/error-reference.md`
- `skills/ivy-toolkit/references/timing-and-concurrency.md`
- `skills/ivy-toolkit/references/hook-lifecycle.md`

**Modified files (in panther-ivy-plugin):**
- `skills/ivy-toolkit/references/tool-catalog.md` — rewrite with standardized entries
- `skills/ivy-toolkit/references/lsp-patterns.md` — add standardized LSP operation entries
- `skills/ivy-toolkit/SKILL.md` — update quick reference, add cross-references to new files
- `CLAUDE.md` — dedup Tool Rules section
- `.claude/rules/tool-reference.md` — no changes needed (already concise)

**Modified files (in ivy-lsp):**
- `ivy_lsp/mcp/tools/__init__.py` — add `rendering` and `tier` fields to `_TOOL_METADATA`

## Testing

- Verify SKILL.md loads correctly via skill activation
- Verify reference files are accessible from SKILL.md (file references)
- Verify `_TOOL_METADATA` fields are valid (unit test for `rendering` in {"hook", "raw"} and `tier` in {"instant", "fast", "slow", "blocking"})
- Manual test: activate ivy-toolkit skill, confirm all cross-references resolve
- Manual test: trigger each workflow, confirm tool results still render correctly (PostToolUse hooks unaffected)
