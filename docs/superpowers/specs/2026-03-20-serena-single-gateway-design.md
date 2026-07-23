# Serena as Single MCP Gateway for Ivy Tools

**Date**: 2026-03-20
**Status**: Design — Approved
**Branch**: `refactor/ivy-lsp-cleanup` (worktree: `lsp-to-claude`)
**Supersedes**: MCP tool sections of `panther-ivy-serena-plugin-design.md`, WS2 of `ivy-lsp-indexing-improvements-design.md`
**Depends on**: `unified-workspace-offline-indexing-design.md` (2026-03-20, status: Draft — must be finalized before Phase 3)

---

## 1. Problem Statement

The current architecture has three overlapping tool surfaces:

1. **ivy-lsp MCP sidecar** — 18 tools exposed via HTTP (FastMCP), running as a daemon thread inside the ivy-lsp process. This is the primary tool surface used by Claude Code via `.mcp.json`.
2. **panther-serena** — Fork of Serena with 4 Ivy-specific tools (IvyDiagnosticsTool, IvyGotoDefinitionTool, IvyServerStatusTool, IvyTestScopeTool) plus standard Serena tools (find_symbol, get_symbols_overview, replace_symbol_body, etc.). **Not registered** in the plugin — completely inaccessible from Claude Code.
3. **panther-ivy-plugin CLAUDE.md** — References `mcp__ivy-tools__*` tool names, but the original design doc references `mcp__plugin_serena_serena__*` names for tools that were removed from Serena (IvyCheckTool, IvyCompileTool, IvyModelInfoTool — removed in commit 78ca022d).

### Specific issues

- **Serena's value is inaccessible**: Semantic code editing (replace_symbol_body, insert_after_symbol), project memory, and symbol navigation are not available from Claude Code.
- **Design doc is stale**: `panther-ivy-serena-plugin-design.md` references removed Serena tools and wrong MCP tool names.
- **Serena's `.serena/project.yml` doesn't list Ivy**: Languages are `[python, typescript]` — IvyLanguageServer is never activated.
- **Double-server risk**: Plugin's `.lsp.json` starts ivy-lsp; Serena would start its own ivy-lsp subprocess.
- **No workspace adaptation**: Serena has no concept of `.ivyworkspace`, test scopes, include closures, or per-mirror scoping.

---

## 2. Decision

**Serena becomes the single MCP gateway.** All Ivy tools are Serena `Tool` subclasses backed by a shared `ivy_tools` library extracted from ivy-lsp. The ivy-lsp MCP sidecar is removed after migration.

### Why Serena (not ivy-lsp MCP)

- **Semantic code editing**: `replace_symbol_body`, `insert_after_symbol`, `insert_before_symbol` provide LSP-aware code modification for Ivy files — something neither ivy-lsp MCP nor Claude Code's native Edit tool offers.
- **Project management**: Serena's memory system (`.serena/memories/`), project activation, and onboarding provide persistent project context across sessions.
- **Unified tool surface**: One MCP server for everything — verification, analysis, navigation, editing, memory.

### Why shared library (not re-implementation)

- **No duplication**: One implementation of verification, coverage, diagnostics, etc.
- **No drift**: ivy-lsp's LSP features and Serena's tools use the same computation functions.
- **Shared cache**: `.ivy-index/` on disk, read by both ivy-lsp (fast startup) and Serena tools.

---

## 3. Architecture

### 3.1 Package Structure & Dependency Direction

**Critical constraint**: `ivy_tools` is the foundational library. `ivy_lsp` depends on `ivy_tools`, never the reverse. This means all shared parsing, analysis, and data structures live in `ivy_tools`. `ivy_lsp` is a thin LSP protocol layer that wires pygls to `ivy_tools`' analysis functions.

```
Dependency graph:
  ivy_tools  ← imported by ← ivy_lsp
  ivy_tools  ← imported by ← panther-serena
  (ivy_tools has NO dependency on ivy_lsp or serena)
```

```
ivy-lsp/                              # Git submodule
├── ivy_tools/                        # Package 1: Shared analysis & tool library (NEW)
│   ├── __init__.py                   # Public API
│   ├── context.py                    # IvyToolContext (see Section 3.5)
│   ├── parsing/                      # TieredExtractor (parser→lexer→regex) — MOVED from ivy_lsp
│   ├── analysis/                     # TestScope, requirement analysis — MOVED from ivy_lsp
│   ├── semantic/                     # SemanticModel, RequirementGraph, rfc_annotations — MOVED
│   ├── workspace/                    # WorkspaceContext, ProtocolIndex, .ivyworkspace parser — MOVED
│   │   ├── context.py                # WorkspaceContext, ProtocolIndex
│   │   ├── test_scope.py             # TestScope class
│   │   └── config.py                 # .ivyworkspace parser
│   ├── indexer/                      # WorkspaceIndexer, include resolution — MOVED from ivy_lsp
│   ├── verification.py               # run_ivy_check, run_ivy_compile, run_ivy_show + LRU cache
│   ├── diagnostics.py                # Structural lint + full 5-layer pipeline
│   ├── coverage.py                   # Coverage stats/gaps/matrix/diff
│   ├── include_graph.py              # Include graph reconstruction
│   ├── visualization.py              # Dependency graphs, state machines, layer views
│   ├── patterns.py                   # Pattern analysis/validation/scaffolding
│   ├── quality.py                    # Quality gates + suggestions
│   ├── traceability.py               # RFC extraction, manifest management
│   ├── capabilities.py               # System capability checks, health check
│   ├── staging.py                    # Layer-aware staging path resolution
│   ├── formatters.py                 # JSON→Markdown formatting
│   └── _safe_call.py                 # Timeout, concurrency, metrics decorator
│
├── ivy_lsp/                          # Package 2: Pure LSP server (pygls) — SLIMMED
│   ├── server.py                     # IvyLanguageServer — imports ivy_tools for analysis
│   ├── __main__.py                   # Entry point (--mcp flag removed)
│   └── features/                     # 19 LSP features — import ivy_tools.parsing, .semantic, etc.
│
└── pyproject.toml                    # Exports: ivy_tools (standalone), ivy_lsp (depends on ivy_tools)

panther-serena/                       # Git submodule (fork)
├── src/serena/tools/
│   ├── ivy_tools.py                  # 20 Serena Tool subclasses (18 new + 2 kept)
│   └── ivy_workspace.py              # .ivyworkspace parsing, Serena ProjectConfig adapter
├── src/solidlsp/language_servers/
│   └── ivy_language_server.py        # Extended: custom LSP requests for live state
└── pyproject.toml                    # Adds ivy-tools dependency

panther-ivy-plugin/                   # Git submodule
├── .mcp.json                         # serena MCP server (replaces ivy-tools)
├── .lsp.json                         # ivy-lsp for editor diagnostics (kept)
├── scripts/start-serena.sh           # New startup script
└── ...                               # Agents, skills, commands, hooks
```

### 3.2 Three-Layer Sharing Model

```
┌──────────────────────────────────────────────────────────────┐
│  LAYER 1: Shared Code (ivy_tools library)                    │
│                                                               │
│  TieredExtractor, WorkspaceContext, SemanticModel,           │
│  RequirementGraph, TestScope, verification functions,        │
│  coverage computation, pattern analysis, formatters          │
│                                                               │
│  ivy_tools has ZERO dependency on ivy_lsp or Serena.         │
│  ivy_lsp imports ivy_tools. Serena imports ivy_tools.        │
│  Single implementation, two consumers.                       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  LAYER 2: Shared Disk Cache (.ivy-index/ directories)        │
│                                                               │
│  Built once (ivy_index CLI or session start hook)            │
│  Contains: manifest, symbols, includes, exports,            │
│  requirements, serialized semantic model, test scopes,       │
│  requirement graph snapshot                                  │
│                                                               │
│  Read by BOTH ivy-lsp (fast startup) AND Serena tools        │
│  Staleness: manifest mtime vs source file mtimes             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  LAYER 3: Live State via Custom LSP Requests                 │
│  (Tier 4 model-dependent tools only)                         │
│                                                               │
│  ivy-lsp exposes:                                            │
│    ivy/getCoverageData → pre-computed coverage for scope     │
│    ivy/getVisualization → pre-computed graph data            │
│    ivy/getModelSummary → pre-computed summary                │
│                                                               │
│  Serena calls via IvyLanguageServer.send_custom_request()    │
│  Computation runs in ivy-lsp process (live model)            │
│  Fallback when .ivy-index is stale                           │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Data Flow

```
User calls mcp__serena__ivy_coverage(mode="stats", test_file="quic_server_test.ivy")
  │
  ▼
Serena IvyCoverageTool.apply()
  │
  ├── Try Layer 2: ivy_tools.coverage.compute_stats(workspace_context_from_index)
  │     └── If .ivy-index fresh (mtime OK) → return result
  │
  └── Fallback Layer 3: ivy_ls.send_custom_request("ivy/getCoverageData", params)
        └── ivy-lsp runs ivy_tools.coverage.compute_stats(live_model) → return
```

### 3.4 Serena Workspace Adaptation

New file `src/serena/tools/ivy_workspace.py`:

```
IvyWorkspaceAdapter
  ├── Loads .ivyworkspace         via ivy_tools.workspace.parse_workspace_config()
  ├── Loads .ivy-index/           via ivy_tools.workspace.load_context()
  ├── list_test_scopes()          all endpoint mirrors
  ├── get_test_scope(name)        TestScope with include closure
  ├── get_active_scope()          currently selected scope
  ├── resolve_include(path)       layer-aware include resolution
  └── list_protocols()            available protocols
```

Serena's standard tools (find_symbol, get_symbols_overview, etc.) work as-is — they delegate to LSP which already handles scoping. No modification to standard Serena tools required.

### 3.5 IvyToolContext (Dependency Injection)

`ivy_tools/context.py` defines `IvyToolContext` — the replacement for the MCP sidecar's `ToolContext`. It is the single dependency injection point that all `ivy_tools` functions receive. Serena constructs it from the `IvyWorkspaceAdapter`; ivy-lsp constructs it from its server state.

```python
@dataclass
class IvyToolContext:
    """Dependency injection for ivy_tools functions. No ivy_lsp imports."""
    workspace_root: str
    staging_dir: str | None = None
    ivy_index_dir: str | None = None              # Path to .ivy-index/ (Layer 2 cache)

    # Lazy callables — set by the consumer (Serena or ivy-lsp)
    find_ivy_files: Callable[..., list[str]]       # File discovery
    resolve_include: Callable[[str], str | None]   # Include path resolution
    get_basename_cache: Callable[..., dict]         # Filename→paths mapping

    # Tier 4 only — may be None for Tier 1-3 tools
    get_model_snapshot: Callable[..., dict | None] = None   # Serialized SemanticModel
    get_graph_snapshot: Callable[..., dict | None] = None   # Serialized RequirementGraph
    get_test_scope: Callable[[str], Any | None] = None      # TestScope lookup
```

**Serena constructs it** in `IvyWorkspaceAdapter.make_tool_context()` — from `.ivy-index/` + ivy-lsp LSP fallback.
**ivy-lsp constructs it** in `server.py` — from live in-memory state (for its own LSP features and custom LSP request handlers).

---

## 4. Tool Inventory

**Total: 20 Ivy tools** (18 new ivy_tools-backed + 2 existing LSP wrappers kept as-is).

### 4.1 Tier Definitions

| Tier | Name | Dependencies | Layer Used |
|---|---|---|---|
| 1 | Subprocess | CLI subprocess calls + file I/O only | Layer 1 (code) |
| 2 | Static Analysis | TieredExtractor + file scanning from `.ivy-index/` | Layer 1 + 2 (code + disk cache) |
| 3 | Workspace-Aware | WorkspaceContext, TestScope lookup, manifest | Layer 1 + 2 (code + disk cache) |
| 4 | Semantic Model | SemanticModel + RequirementGraph | Layer 1 + 2 + 3 (code + disk + LSP fallback) |

### 4.2 New Serena Tool Classes (18 tools backed by ivy_tools)

| Serena Tool Class | ivy_tools Function | Tier | Parameters |
|---|---|---|---|
| `IvyVerifyTool` | `verification.run_ivy_check()` | 1 | relative_path, isolate, scope |
| `IvyCompileTool` | `verification.run_ivy_compile()` | 1 | relative_path, target, isolate, scope |
| `IvyModelInfoTool` | `verification.run_ivy_show()` | 1 | relative_path, isolate |
| `IvyCapabilitiesTool` | `capabilities.check_system()` | 1 | — |
| `IvyExtractRequirementsTool` | `traceability.extract_requirements()` | 1 | rfc_source, sections, rfc_name, output |
| `IvyPatternScaffoldTool` | `patterns.scaffold()` | 1 | protocol, pattern |
| `IvyIndexTool` | `workspace.build_index()` | 1 | protocol, mode |
| `IvyHealthCheckTool` | `capabilities.health_check()` | 1 | — |
| `IvyIncludeGraphTool` | `include_graph.compute()` | 2 | relative_path, scope |
| `IvyDiagnosticsTool` | `diagnostics.run()` | 2 | relative_path, mode, layers, min_severity |
| `IvyPatternsTool` | `patterns.analyze()` | 2 | protocol, pattern, mode |
| `IvyVerificationDashboardTool` | `verification.dashboard()` | 2 | — |
| `IvyScopeTool` | `workspace.get_scope_info()` | 3 | relative_path, action |
| `IvyManifestTool` | `traceability.manage_manifest()` | 3 | scope, mode |
| `IvyQualityTool` | `quality.check_gate()` / `quality.suggest()` | 3/4 | file_path, mode, protocol, gate_level |
| `IvyCoverageTool` | `coverage.compute()` | 4 | relative_path, test_file, scope, protocol, mode |
| `IvyVisualizeTool` | `visualization.render()` | 4 | test_file, protocol, view |
| `IvyModelSummaryTool` | `visualization.summarize()` | 4 | test_file, action_name, file_path, detail |

### 4.3 Existing Serena Tools (kept as-is, no code changes needed)

| Tool | Reason |
|---|---|
| `IvyGotoDefinitionTool` | Pure LSP wrapper — no ivy_tools equivalent. Already works. |
| `IvyServerStatusTool` | LSP custom request (`ivy/serverStatus`) — server introspection. Already works. |

These two tools exist today and require zero modification. They are listed in `included_optional_tools` to ensure they're enabled for Ivy projects.

### 4.4 Existing Serena Tools (merged into new tools)

| Old Tool | Merged Into | Mode Mapping |
|---|---|---|
| `IvyDiagnosticsTool` (cached LSP) | New `IvyDiagnosticsTool` | `mode="cached"` → returns LSP publishDiagnostics cache (existing behavior). `mode="structural"` → ivy_tools structural lint. `mode="full"` → ivy_tools 5-layer pipeline. |
| `IvyTestScopeTool` | `IvyScopeTool` | `action="list"/"set"` → LSP test scope management (existing behavior). `action="info"` → ivy_tools workspace scope info (new). |

### 4.5 Standard Serena Tools (available for Ivy)

These require no modification — they work via LSP:

| Tool | Purpose for Ivy |
|---|---|
| `find_symbol` | Locate Ivy symbols (actions, types, relations) by name |
| `get_symbols_overview` | Display structure of an .ivy file |
| `find_referencing_symbols` | Find where a symbol is referenced across .ivy files |
| `replace_symbol_body` | Edit the body of an Ivy action/type/relation in-place |
| `insert_after_symbol` | Insert content after an Ivy symbol definition |
| `insert_before_symbol` | Insert content before an Ivy symbol definition |
| `read_file` | Read .ivy file contents |
| `create_text_file` | Create new .ivy files |
| `search_for_pattern` | Regex search across Ivy codebase |
| `write_memory` / `read_memory` | Persist project knowledge |

---

## 5. Plugin Changes

### 5.1 `.mcp.json`

```json
{
  "mcpServers": {
    "serena": {
      "command": "bash",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/start-serena.sh"],
      "env": {
        "IVY_LSP_LOG_LEVEL": "DEBUG",
        "SERENA_PROJECT_ROOT": "${CLAUDE_PLUGIN_ROOT}/../../.."
      }
    }
  }
}
```

### 5.2 `.lsp.json` — Kept as-is

Two ivy-lsp instances run: one from `.lsp.json` (editor diagnostics push), one from Serena (tool surface). Both read from `.ivy-index/` for fast startup.

**Memory cost**: Both instances build in-memory semantic models (2-4 minute cold start each). This is acceptable because:
- `.ivy-index/` pre-built index significantly reduces cold start time (the unified-workspace-offline-indexing spec addresses this)
- The `.lsp.json` instance is lightweight — it only needs the model for interactive features (hover, definition)
- Serena's instance is the primary workhorse — Tier 1-3 tools don't need the model at all; only Tier 4 tools trigger model building, and they can use the `.ivy-index/` cached snapshot first
- If memory is a concern, Serena's ivy-lsp instance can be started with `--light-mode` (skip eager model building, build on-demand only for Tier 4 fallback)

### 5.3 `.serena/project.yml` — New file at panther_ivy root

Note: `included_optional_tools` uses Serena's tool naming convention (snake_case of class name minus `Tool` suffix). Verify against Serena's `ToolRegistry` auto-discovery logic during Phase 0.

```yaml
project_name: "panther-ivy"
languages:
  - ivy
ignored_paths:
  - "submodules/z3/**"
  - "submodules/picotls/**"
  - "submodules/abc/**"
  - "submodules/aiger/**"
  - "doc/**"
  - "examples/**"
  - "patches/**"
ignore_all_files_in_gitignore: true
read_only: false
included_optional_tools:
  - ivy_verify
  - ivy_compile
  - ivy_model_info
  - ivy_diagnostics
  - ivy_include_graph
  - ivy_capabilities
  - ivy_coverage
  - ivy_extract_requirements
  - ivy_manifest
  - ivy_visualize
  - ivy_model_summary
  - ivy_patterns
  - ivy_pattern_scaffold
  - ivy_quality
  - ivy_scope
  - ivy_health_check
  - ivy_index
  - ivy_verification_dashboard
  - ivy_goto_definition
  - ivy_server_status
```

### 5.4 MCP Tool Name Convention

Claude Code plugin MCP tools are namespaced as `mcp__plugin_<plugin-name>_<server-name>__<tool>`. With the `.mcp.json` server named `serena` in the `panther-ivy-plugin` plugin, the actual tool names will be:

```
mcp__plugin_panther-ivy-plugin_serena__ivy_verify
mcp__plugin_panther-ivy-plugin_serena__find_symbol
mcp__plugin_panther-ivy-plugin_serena__replace_symbol_body
...
```

For brevity, this spec uses `mcp__serena__*` as shorthand. All references to tool names in CLAUDE.md, hooks, commands, and other docs must use the full qualified name.

### 5.5 `start-serena.sh` Script

New script replacing `start-ivy-server.sh` for the MCP server. Responsibilities:

1. Activate the panther_ivy virtualenv (or use `uvx`)
2. Detect workspace root via existing detection logic (`.ivyworkspace` search)
3. Set `IVY_WORKSPACE_ROOT` env var (consumed by Serena's `IvyWorkspaceAdapter`)
4. Run `uv run serena-mcp-server --project-root $SERENA_PROJECT_ROOT`

Unlike `start-ivy-server.sh`, this script does NOT manage PID files or session scoping — Serena handles its own lifecycle. Log output goes to Serena's default log location.

### 5.6 Hook Changes

`block-direct-ivy` hook: tool name references change to the full qualified `mcp__plugin_panther-ivy-plugin_serena__*` prefix.

### 5.7 CLAUDE.md

All tool name references updated to full qualified prefix. Add documentation for Serena-only tools (find_symbol, replace_symbol_body, memory tools).

---

## 6. Phased Implementation Plan

### Phase 0: Foundation

**Goal**: Extract `ivy_tools` package, wire Serena MCP, verify no regressions.

**Tasks** (ivy-lsp side):
1. Create `ivy_tools/` package directory in ivy-lsp repo with `__init__.py`
2. Move `parsing/` (TieredExtractor, lexer, regex fallback) to `ivy_tools/parsing/`
3. Move `analysis/` (TestScope, requirement analysis) to `ivy_tools/analysis/`
4. Move `semantic/` (SemanticModel, RequirementGraph, rfc_annotations) to `ivy_tools/semantic/`
5. Move `workspace_context.py` + `indexer/` to `ivy_tools/workspace/` and `ivy_tools/indexer/`
6. Move `verification.py` (run_ivy_check, run_ivy_compile, run_ivy_show) to `ivy_tools/verification.py`
7. Move staging logic (resolve_staging_path, layer resolution) to `ivy_tools/staging.py`
8. Move formatters to `ivy_tools/formatters.py`
9. Move timeout/metrics decorator to `ivy_tools/_safe_call.py`
10. Create `ivy_tools/context.py` with `IvyToolContext` class (Section 3.5)
11. Update ALL ivy-lsp imports: `ivy_lsp.parsing` → `ivy_tools.parsing`, etc.
12. Update `pyproject.toml`: export `ivy_tools` (standalone) and `ivy_lsp` (depends on ivy_tools)
13. Verify all existing ivy-lsp tests pass (1965+ tests)

**Tasks** (Serena + plugin side):
14. Create `IvyWorkspaceAdapter` in `src/serena/tools/ivy_workspace.py`
15. Create `start-serena.sh` script in panther-ivy-plugin
16. Update `.mcp.json` to register Serena MCP server
17. Create `.serena/project.yml` at panther_ivy root
18. Add `ivy-tools` dependency to panther-serena `pyproject.toml`
19. Verify Serena MCP server starts and standard tools work on .ivy files

**Exit criteria**: `ivy_tools` is importable from both ivy-lsp and Serena. Serena MCP server starts and exposes standard tools. No regressions.

### Phase 1: Subprocess Tools (8 tools)

**Goal**: Basic "build and check" workflow through Serena.

**Tasks**:
1. Implement `IvyVerifyTool` — delegates to `ivy_tools.verification.run_ivy_check()`
2. Implement `IvyCompileTool` — delegates to `ivy_tools.verification.run_ivy_compile()`
3. Implement `IvyModelInfoTool` — delegates to `ivy_tools.verification.run_ivy_show()`
4. Implement `IvyCapabilitiesTool` — delegates to `ivy_tools.capabilities.check_system()`
5. Implement `IvyHealthCheckTool` — delegates to `ivy_tools.capabilities.health_check()`
6. Implement `IvyExtractRequirementsTool` — delegates to `ivy_tools.traceability.extract_requirements()`
7. Implement `IvyPatternScaffoldTool` — delegates to `ivy_tools.patterns.scaffold()`
8. Implement `IvyIndexTool` — delegates to `ivy_tools.workspace.build_index()`
9. Register all 8 as `ToolMarkerOptional` in Serena's tool registry
10. Add tests for each tool (Serena test framework)

**Exit criteria**: `mcp__serena__ivy_verify`, `mcp__serena__ivy_compile`, `mcp__serena__ivy_model_info` work end-to-end. `/nct-check` command works via Serena.

### Phase 2: Static Analysis Tools (4 tools)

**Goal**: Diagnostics, include analysis, and pattern checking through Serena.

**Tasks** (TieredExtractor already in ivy_tools from Phase 0):
1. Create `ivy_tools/diagnostics.py` — wire structural lint + full pipeline using `ivy_tools.parsing.TieredExtractor`
2. Create `ivy_tools/include_graph.py` — include graph computation using `ivy_tools.indexer`
3. Create `ivy_tools/patterns.py` — pattern analysis/validation using file scanning
4. Implement `IvyDiagnosticsTool` — unified tool with 3 modes: `mode="cached"` (LSP publishDiagnostics), `mode="structural"` (ivy_tools lint), `mode="full"` (ivy_tools 5-layer)
5. Implement `IvyIncludeGraphTool` — delegates to `ivy_tools.include_graph.compute()`
6. Implement `IvyPatternsTool` — delegates to `ivy_tools.patterns.analyze()`
7. Implement `IvyVerificationDashboardTool` — delegates to `ivy_tools.verification.dashboard()`
8. Add tests (unit tests with mocked ivy_tools + integration test with real .ivy files from `test/resources/`)

**Exit criteria**: `ivy_diagnostics(mode="structural")`, `ivy_diagnostics(mode="cached")`, and `ivy_include_graph` work via Serena. Pattern analysis works.

**Exit criteria**: `ivy_diagnostics(mode="structural")` and `ivy_include_graph` work via Serena. Pattern analysis works.

### Phase 3: Workspace-Aware Tools (3 tools)

**Goal**: Scope-aware operations through Serena.

**Tasks**:
1. Move TestScope, ProtocolIndex to `ivy_tools/workspace.py`
2. Move manifest management to `ivy_tools/traceability.py`
3. Move quality gate logic to `ivy_tools/quality.py`
4. Wire `IvyWorkspaceAdapter` to load `.ivy-index/` on Serena project activation
5. Implement `IvyScopeTool` — merges existing `IvyTestScopeTool` (LSP) + workspace info (ivy_tools)
6. Implement `IvyManifestTool` — delegates to `ivy_tools.traceability.manage_manifest()`
7. Implement `IvyQualityTool` (gate mode) — delegates to `ivy_tools.quality.check_gate()`
8. Add tests

**Exit criteria**: `ivy_scope`, `ivy_manifest`, `ivy_quality(mode="gate")` work via Serena with test scope filtering.

### Phase 4: Semantic Model Tools (3 tools + quality suggestions)

**Goal**: Full tool parity. All 20 Serena tools operational.

**Tasks** (ivy-lsp side):
1. Create `ivy_tools/coverage.py` — coverage computation using `ivy_tools.semantic.SemanticModel` + `ivy_tools.semantic.RequirementGraph`
2. Create `ivy_tools/visualization.py` — graph/summary generation using same
3. Add custom LSP request handlers in ivy-lsp: `ivy/getCoverageData`, `ivy/getVisualization`, `ivy/getModelSummary`, `ivy/getQualitySuggestions` — each calls the corresponding `ivy_tools` function with live model and returns JSON

**Tasks** (Serena side):
4. Extend `IvyLanguageServer.send_custom_request()` to support the 4 new methods
5. Implement Layer 2→3 fallback in `IvyWorkspaceAdapter`:
   a. Staleness check: compare `.ivy-index/manifest.json` mtime vs source file mtimes
   b. If fresh: load snapshot from `.ivy-index/` → pass to `ivy_tools` function
   c. If stale: call `send_custom_request("ivy/get*")` → format result
   d. If LSP unavailable: return error with "run ivy_index to refresh"
6. Implement `IvyCoverageTool` — calls `ivy_tools.coverage.compute()` with fallback
7. Implement `IvyVisualizeTool` — calls `ivy_tools.visualization.render()` with fallback
8. Implement `IvyModelSummaryTool` — calls `ivy_tools.visualization.summarize()` with fallback
9. Implement `IvyQualityTool` (suggestions mode) — always uses LSP (suggestions need live model)
10. Add tests: unit tests with mock `.ivy-index/` snapshots + integration tests exercising Layer 3 fallback

**Exit criteria**: All 20 tools work via Serena MCP. `ivy_coverage(mode="stats", test_file=...)` returns correct scoped results.

### Phase 5: Cleanup & Plan Updates

**Goal**: Remove ivy-lsp MCP, update all docs.

**Tasks**:
1. Remove `ivy_lsp/mcp_server.py` (standalone MCP entry)
2. Remove `ivy_lsp/mcp_sidecar.py` (HTTP sidecar)
3. Remove `ivy_lsp/tools/` directory
4. Remove `--mcp` flag from `ivy_lsp/__main__.py`
5. Remove MCP deps from ivy-lsp `pyproject.toml` (mcp, uvicorn, httpx)
6. Update `panther-ivy-serena-plugin-design.md` — rewrite Sections 3.3 (commands), 4.2 (dependency), 4.3 (tool params), architecture diagram
7. Update `unified-workspace-offline-indexing-design.md` — consumer = Serena via ivy_tools import
8. Update `lsp-mcp-crash-resilience-design.md` — remove Phase 2 (MCP resilience)
9. Update `layer-aware-mcp-staging` plan (`.superpowers/plans/2026-03-18-layer-aware-mcp-staging.md`) — target = ivy_tools/staging.py
10. Update `nct-validate-redesign-design.md` — tool name prefix to full qualified
11. Update `ivy-lsp-indexing-improvements-design.md` — remove WS2 (MCP tool design)
12. Update plugin CLAUDE.md — all tool references to full qualified names
13. Update hook scripts — tool name references to full qualified names
14. Update all command definitions (`/nct-check`, `/nct-compile`, `/nct-model-info`) — tool invocations
15. Run nct-validate end-to-end to confirm

**Exit criteria**: ivy-lsp has no MCP code. All docs reference Serena. nct-validate passes.

---

## 7. Existing Plan Impact Matrix

| Document | Impact | Change Summary |
|---|---|---|
| `panther-ivy-serena-plugin-design.md` | HIGH | Rewrite MCP tool mapping, architecture diagram. All tools now `mcp__serena__*`. |
| `unified-workspace-offline-indexing-design.md` | HIGH | Consumer = Serena via ivy_tools import (not MCP sidecar via env vars). |
| `lsp-mcp-crash-resilience-design.md` | HIGH | Phase 2 (MCP resilience) removed. Phase 1, 3 kept. |
| `layer-aware-mcp-staging.md` (`.superpowers/plans/`) | MEDIUM | Staging logic moves to ivy_tools/staging.py. Same algorithm, new location. |
| `nct-validate-redesign-design.md` | MEDIUM | Tool name prefix: `mcp__ivy-tools__*` → `mcp__serena__*`. |
| `ivy-lsp-indexing-improvements-design.md` | MEDIUM | WS2 (MCP tool design) removed. WS1 (core) kept. WS3 → ivy_tools. |
| `requirement-coverage-redesign.md` | LOW | Implementation location: `ivy_tools.coverage` not `ivy_lsp.tools.traceability`. |
| `pyright-like-diagnostics-design.md` | LOW | Stays in ivy-lsp. IvyDiagnostic format shared via ivy_tools. |
| `nct-workspace-validation-design.md` | LOW | Layer 6 description update only. |
| `ivy-plugin-evaluation-design.md` | LOW | Tool prefix change in test scenarios. |
| `.superpowers/plans/*` | LOW | Tool name changes only. |

---

## 8. Risk Assessment

| Risk | Mitigation |
|---|---|
| Serena fork diverges further from upstream oraios/serena | Keep Ivy-specific code in `ivy_tools.py` and `ivy_workspace.py` — minimal Serena core changes |
| Two ivy-lsp instances (`.lsp.json` + Serena) use memory | Both build in-memory models. `.ivy-index/` reduces cold start. Serena instance can use `--light-mode` to defer model building. See Section 5.2. |
| ivy_tools extraction breaks ivy-lsp tests | Phase 0 gate: all 1965+ tests must pass before proceeding |
| Custom LSP requests (Phase 4) add complexity | Layer 3 is fallback only — Layer 2 (.ivy-index/) handles most cases |
| Serena startup slower (loads Ivy workspace) | Lazy initialization — IvyWorkspaceAdapter loads on first tool call, not on MCP server start |
| Phase 4 tools require semantic model in Serena process | Solved by Layer 3 (custom LSP requests) — model stays in ivy-lsp process |

---

## 9. Success Criteria

1. All 20 Ivy tools accessible via `mcp__serena__*` from Claude Code
2. Standard Serena tools (find_symbol, replace_symbol_body, memory) work on .ivy files
3. ivy-lsp is a pure LSP server — no MCP code, no tools/ directory
4. No tool duplication — single implementation in `ivy_tools`
5. `.ivy-index/` is the shared cache — no redundant model building
6. All existing design specs updated with correct references
7. nct-validate passes end-to-end with Serena as tool surface
