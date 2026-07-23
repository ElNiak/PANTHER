# Pyright-Like Diagnostics for Ivy LSP

**Date**: 2026-03-18
**Scope**: ivy-lsp submodule diagnostic pipeline + MCP tools
**Status**: Design
**Prerequisite**: Pipeline enablers plan (P1-P8, executed)

---

## 1. Context

The Ivy LSP server has a 3-tier diagnostic pipeline (structural/semantic/deep) but error messages are vague and unhelpful — the primary user pain point. Parse errors render as raw tuples (`"Duplicate 'conn_state': quic_shim.ivy:47"`), include resolution issues lack suggestions, and type/scope errors are not caught at the LSP level (only by `ivy_check` on save).

**Goal**: Bring the diagnostic experience closer to Pyright's quality:
- Structured error codes with a naming taxonomy
- Rich messages with related locations and "did you mean" suggestions
- Configurable severity modes (basic/standard/strict)
- Incremental name/type checking at edit time

**Scope**: LSP + MCP tools (shared diagnostic core via `IvyDiagnostic` intermediate representation).
**Depth**: Best-effort fast checks + partial Ivy compiler integration (Python-importable).
**Delivery**: Phased — foundation first, then name resolution, then full experience.

---

## 2. Current State

### 2.1 Existing Diagnostic Tiers

| Tier | Latency | What It Checks | Source Tags |
|------|---------|----------------|-------------|
| T1 (structural) | <50ms | Missing `#lang`, unmatched braces, unresolved includes | `ivy-lsp`, `ivy-lint` |
| T2 (semantic) | <200ms | Parse errors, orphaned RFC tags, unmonitored actions, coverage hints, patterns | `ivy`, `ivy-lsp-reqs`, `ivy-lsp-semantic`, `ivy-lsp-coverage`, `ivy-pattern` |
| T3 (deep) | Background on save | `ivy_check` verification via subprocess | `ivy_check` |

### 2.2 Current Pain Points

1. **Parse errors**: `_convert_error_to_diagnostic()` (`diagnostics.py:122-164`) produces flat messages from parser tuples. A duplicate symbol renders as `"Duplicate 'conn_state': quic_shim.ivy:47, quic_protection.ivy:13"` — no explanation, no related locations.

2. **Include errors**: `"Unresolved include: quic_protection"` with no suggestion of candidate files or search paths tried.

3. **No type/scope checking at T2**: The parser either succeeds (full AST) or fails entirely. No incremental name resolution between parse success and full compilation.

4. **Inconsistent source tags**: 9 different source tags across diagnostic producers with no taxonomy.

5. **Only 4 error codes**: `missing-lang-header`, `unresolved-include`, `ivy.no-monitor`, `ivy.unguarded-write`. All other diagnostics have no `code` field.

6. **MCP duplication**: `ivy_diagnostics` MCP tool reimplements the 5 diagnostic layers separately from `features/diagnostics.py`.

---

## 3. Design

### 3.1 Error Code Taxonomy

**Naming convention**: `ivy.<category>.<specificError>` (dot-delimited, camelCase specific error)

#### Categories

| Category | Prefix | Scope |
|----------|--------|-------|
| Syntax | `ivy.syntax.*` | Lexer/parser errors, missing declarations |
| Naming | `ivy.naming.*` | Undefined symbols, duplicates, conflicts, shadowing |
| Type | `ivy.type.*` | Sort mismatches, arity errors, undefined sorts |
| Module | `ivy.module.*` | Include resolution, circular deps, conflicts |
| Action | `ivy.action.*` | Unmonitored exports, missing finalize, parameter mismatches |
| Invariant | `ivy.invariant.*` | Unguarded writes, violated assertions, quantifier scope |
| RFC | `ivy.rfc.*` | Orphaned tags, missing annotations, stale manifests |
| Verify | `ivy.verify.*` | ivy_check failures, timeouts |

#### Initial Error Codes (~28)

**ivy.syntax.*** (6):
- `missingLangHeader` (W) — Missing `#lang ivy1.7` header
- `unmatchedBrace` (E) — Unmatched `{` or `}`
- `unexpectedToken` (E) — Parser encountered unexpected token
- `lexerError` (E) — PLY lexer illegal character
- `invalidKeyword` (E) — Unrecognized keyword in declaration context
- `malformedDeclaration` (E) — Declaration missing required components

**ivy.naming.*** (4):
- `undefinedSymbol` (E) — Reference to symbol not in scope
- `duplicateDefinition` (E) — Symbol defined more than once
- `symbolConflict` (E) — Same symbol from multiple includes
- `shadowedBinding` (W) — Local name shadows outer declaration

**ivy.type.*** (3):
- `mismatch` (E) — Type mismatch in expression
- `arityMismatch` (E) — Wrong number of arguments to action/sort
- `undefinedSort` (E) — Type name not a known sort

**ivy.module.*** (4):
- `unresolvedInclude` (W) — Include target not found
- `circularDependency` (E) — Circular include chain detected
- `ambiguousInclude` (W) — Include name maps to multiple files
- `duplicateInclude` (W) — Same module included twice

**ivy.action.*** (3):
- `noMonitor` (H) — Exported action with no before/after monitor
- `missingFinalize` (W) — Test file exports but lacks `_finalize`
- `parameterMismatch` (E) — Call has wrong number/type of parameters

**ivy.invariant.*** (3):
- `unguardedWrite` (H) — State variable written without requirement guard
- `violatedAssertion` (E) — ivy_check found counterexample
- `quantifierScope` (W) — Quantifier variable not properly bound

**ivy.rfc.*** (3):
- `orphanedTag` (W) — Bracket tag not matching any manifest
- `missingTag` (H) — Assertion lacks bracket tag annotation
- `staleManifest` (W) — Manifest generated from outdated RFC

**ivy.verify.*** (2):
- `failed` (E) — ivy_check verification failure
- `timeout` (W) — ivy_check timed out

### 3.2 Core Types

#### `ivy_lsp/diagnostics/codes.py` — Error Code Registry

```python
@dataclass(frozen=True)
class DiagnosticDescriptor:
    code: str                    # e.g. "ivy.module.unresolvedInclude"
    title: str                   # Short summary template (f-string with {symbol}, {file}, etc.)
    explanation: str             # Why this is a problem
    default_severity: str        # "error"|"warning"|"info"|"hint"
    source: str                  # Normalized source tag
    has_quick_fix: bool = False
    has_related_info: bool = False

# Registry: dict[str, DiagnosticDescriptor]
DIAGNOSTIC_REGISTRY: dict[str, DiagnosticDescriptor] = { ... }

def get_descriptor(code: str) -> DiagnosticDescriptor | None:
    return DIAGNOSTIC_REGISTRY.get(code)
```

#### `ivy_lsp/diagnostics/rich_diagnostic.py` — Intermediate Representation

```python
@dataclass
class RelatedLocation:
    file: str
    line: int
    col: int = 0
    message: str = ""

@dataclass
class IvyDiagnostic:
    code: str
    message: str               # Rendered from template
    file: str
    line: int
    col: int = 0
    end_line: int | None = None
    end_col: int | None = None
    severity: str = "error"
    source: str = "ivy"
    related: list[RelatedLocation] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    suggested_fix: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_lsp(self) -> lsp.Diagnostic:
        """Convert to LSP protocol diagnostic with code, relatedInformation, codeDescription."""
        ...

    def to_mcp_dict(self) -> dict[str, Any]:
        """Convert to MCP dict with explanation, context, suggested_fix for Claude agents."""
        ...
```

**LSP output**: Short message in squiggly tooltip, full info in problems panel, `relatedInformation` for location chains, `code` field for filtering.

**MCP output**: Richer dict with `explanation` (why it's a problem), `context` (structured data for agent reasoning), `suggested_fix` (prose fix suggestion), `actionable` flag.

#### `ivy_lsp/diagnostics/modes.py` — Severity Profiles

Three modes controlled by `IVY_LSP_DIAGNOSTIC_MODE` env var:

| Mode | Errors | Warnings | Info | Hints | Deep | Default For |
|------|--------|----------|------|-------|------|-------------|
| **basic** | Yes | No | No | No | No | New users |
| **standard** | Yes | Yes | No | Selected | On save | PANTHER workspaces (default) |
| **strict** | Yes | Yes | Yes | All | On save | CI/quality gates |

Implementation: severity-floor filter + per-code promotion table.

### 3.3 Normalized Source Tags

Replace 9 inconsistent tags with 5 clean ones:

| New Tag | Replaces | Scope |
|---------|----------|-------|
| `ivy` | `ivy`, `ivy-lsp`, `ivy-lint`, `ivy-lsp-lexer` | Parse, syntax, structural |
| `ivy-semantic` | `ivy-lsp-reqs`, `ivy-lsp-coverage`, `ivy-pattern` | Requirement analysis, coverage, patterns |
| `ivy-rfc` | `ivy-lsp-semantic` | RFC traceability |
| `ivy_check` | `ivy_check` | Deep verification subprocess |
| `ivy-coverage` | (subset of `ivy-lsp-coverage`) | Coverage gap reporting |

---

## 4. Phased Implementation

### Phase 1: Foundation — Error Codes, Rich Messages, Registry (3-4 days)

**Goal**: Better error messages and structured error codes on all existing diagnostics. No new analysis passes.

#### Step 1.1: Create `ivy_lsp/diagnostics/` package

New files:
- `__init__.py` — package init
- `codes.py` — `DiagnosticDescriptor` dataclass + `DIAGNOSTIC_REGISTRY` with ~28 codes
- `rich_diagnostic.py` — `IvyDiagnostic` dataclass with `to_lsp()` and `to_mcp_dict()`
- `modes.py` — `DiagnosticMode` dataclass with basic/standard/strict definitions

#### Step 1.2: Enhance `_convert_error_to_diagnostic()`

**File**: `ivy_lsp/features/diagnostics.py:122-164`

Refactor to:
1. Classify error tuples into codes (`ivy.naming.duplicateDefinition`, `ivy.naming.undefinedSymbol`, `ivy.naming.symbolConflict`)
2. Render messages from `DiagnosticDescriptor.title` templates
3. Add `relatedInformation` entries for each location in the tuple chain
4. Return `IvyDiagnostic` instead of raw `lsp.Diagnostic`

**Before**: `"Duplicate 'conn_state': quic_shim.ivy:47, quic_protection.ivy:13"`
**After**: `"Duplicate definition of 'conn_state'. First declared at quic_shim.ivy:47, redeclared here."` + 2 `relatedInformation` entries pointing to both sites.

#### Step 1.3: Enhance `format_ivy_error()` with "did you mean"

**File**: `ivy_lsp/utils/ivy_output.py:201-233`

When a symbol is `Unresolved`, check workspace indexer's symbol cache. If found elsewhere: `"Did you mean to include 'file_that_declares_it'?"` as `suggested_fix`.

#### Step 1.4: Enhance structural lint with related info

**File**: `ivy_lsp/utils/structural_lint.py`

- **Unmatched braces**: Report matching open-brace line in `relatedInformation`
- **Unresolved includes**: Show candidate files from other directories
- **New**: Duplicate include detection (same module included twice)

#### Step 1.5: Migrate all existing diagnostic producers to codes

Update all functions in `diagnostics.py` to produce `IvyDiagnostic` with error codes:
- `check_structural_issues()` (line 167) — `ivy.syntax.*`, `ivy.module.*`
- `compute_requirement_diagnostics()` (line 220) — `ivy.action.noMonitor`, `ivy.invariant.highImpactVar`
- `compute_semantic_diagnostics()` (line 385) — `ivy.rfc.orphanedTag`, `ivy.rfc.missingTag`
- Coverage hints — `ivy.action.noMonitor`, `ivy.invariant.unguardedWrite`
- Pattern checks — `ivy.action.missingFinalize`

#### Step 1.6: Update `code_action.py` to new codes

**File**: `ivy_lsp/features/code_action.py`

Rename existing quick fixes:
- `missing-lang-header` → `ivy.syntax.missingLangHeader`
- `unresolved-include` → `ivy.module.unresolvedInclude`
- `ivy.no-monitor` → `ivy.action.noMonitor`
- `ivy.unguarded-write` → `ivy.invariant.unguardedWrite`

Add 4 new quick fixes:
- `ivy.syntax.unmatchedBrace` → Insert missing closing brace
- `ivy.action.missingFinalize` → Insert `_finalize` skeleton
- `ivy.rfc.missingTag` → Insert `# [rfc:section]` comment
- `ivy.naming.undefinedSymbol` → Suggest include for declaring file (when indexer knows it)

#### Step 1.7: Unify MCP `ivy_diagnostics` with shared pipeline

**File**: `ivy_lsp/tools/verification.py:348`

Refactor `ivy_diagnostics` to call shared `compute_diagnostics()` pipeline (now returns `List[IvyDiagnostic]`) and convert via `to_mcp_dict()`. Remove ~200 lines of duplicated diagnostic logic. Add `explanation`, `context`, `suggested_fix` to MCP output.

#### Critical files (Phase 1)
- `ivy_lsp/features/diagnostics.py` — central orchestrator
- `ivy_lsp/utils/ivy_output.py` — error formatting, "did you mean"
- `ivy_lsp/utils/structural_lint.py` — richer structural checks
- `ivy_lsp/features/code_action.py` — expand quick fixes
- `ivy_lsp/tools/verification.py` — unify MCP diagnostics
- NEW: `ivy_lsp/diagnostics/__init__.py`, `codes.py`, `rich_diagnostic.py`, `modes.py`

---

### Phase 2: T2 Name Resolution + Type Checking (4-5 days)

**Goal**: Catch undefined symbols, sort mismatches, and arity errors at edit time (<200ms).

#### Step 2.1: Create `ivy_lsp/diagnostics/name_resolver.py`

New T2 analysis pass after successful parse. Uses parsed AST + `WorkspaceIndexer` symbol index.

**Checks**:
- `ivy.naming.undefinedSymbol` — identifier not declared in current file or includes
- `ivy.type.undefinedSort` — type name not a known sort
- `ivy.naming.symbolConflict` — multiple declarations across includes (with `relatedInformation`)
- `ivy.naming.shadowedBinding` — local shadows included symbol

**Implementation**:
1. Walk parse result AST for symbol references
2. Check against `indexer.lookup_symbol()` + include chain
3. For unresolved: search full workspace index for "did you mean" suggestions
4. When parse fails: regex fallback using fallback scanner symbol list + include index

**Constraint**: Does NOT acquire `_ivy_state_lock`. Works on parse results + pre-built symbol index. Runs in parallel with ongoing parses.

#### Step 2.2: Create `ivy_lsp/diagnostics/type_checker.py`

Lightweight T2 type checker using `AstEnrichmentAdapter.extract_type_info()` + `SemanticModel`:

- `ivy.type.arityMismatch` — action call wrong number of args vs declaration
- `ivy.type.mismatch` — argument sort doesn't match expected (conservative: only when both sides known)

Uses `SymbolNode.params` and `SymbolNode.return_sort`. No inference — only checks explicit types.

#### Step 2.3: Integrate into `AnalysisPipeline.run_tier2()`

**File**: `ivy_lsp/semantic/analysis_pipeline.py`

After existing enrichment, run name resolution and type checking. Results flow into `compute_diagnostics()` via `t2_diagnostics` parameter. Timer guard: skip if over 200ms budget.

#### Step 2.4: Expand code actions

- `ivy.naming.undefinedSymbol` → "Add include for 'X'" (when found in another file)
- `ivy.naming.symbolConflict` → "Qualify as 'module.X'"

#### Risk: AST structure
Ivy AST (`ivy.ivy_ast`) is not well-documented. Mitigation: start with common node types (action calls, sort references), expand incrementally. Test on QUIC model files first.

---

### Phase 3: Deep Diagnostic Enhancement + Full Experience (3-4 days)

**Goal**: Make `ivy_check` errors actionable and close the feedback loop.

#### Step 3.1: Classify `ivy_check` output into error codes

**File**: `ivy_lsp/utils/ivy_output.py`

Add `classify_compiler_error(message: str) -> str`:
- `"module X not found"` → `ivy.module.unresolvedInclude`
- `"undeclared"` → `ivy.naming.undefinedSymbol`
- `"type mismatch"` → `ivy.type.mismatch`
- `"assertion failed"` / `"proof failed"` → `ivy.invariant.violatedAssertion`
- Timeout → `ivy.verify.timeout`

#### Step 3.2: Counterexample formatting

Parse `ivy_check` counterexample traces into structured step-by-step state evolution. Map trace steps to file locations for `relatedInformation` chains.

#### Step 3.3: T3→T2 feedback loop

After successful T3 compilation, store `CompiledModuleIR` resolved sorts/symbols in `SemanticModel` for better T2 accuracy on subsequent edits.

#### Step 3.4: Configurable severity in LSP initialization

**File**: `ivy_lsp/server.py`

Accept `initializationOptions.diagnostics.mode: "basic"|"standard"|"strict"`. Support `workspace/didChangeConfiguration` for runtime switching.

#### Step 3.5: Background compilation priority queue

Add priority queue for T3: active file > files including active > other open files. Use `CompilerManager.compile_async()` with debouncing.

---

## 5. Before/After Examples

### Example 1: Duplicate Definition

**Before**:
```
Line 15: Error — "Duplicate 'conn_state': quic_shim.ivy:47, quic_protection.ivy:13"
Source: ivy | Code: (none)
```

**After**:
```
[ivy.naming.duplicateDefinition] Duplicate definition of 'conn_state'

'conn_state' is defined in two locations. Each symbol must have
exactly one definition per scope.

  First defined: quic_shim.ivy:47         ← relatedInformation[0]
  Also defined:  quic_protection.ivy:13   ← relatedInformation[1]

Suggested fix: Rename one definition or move shared state to a
common module included by both files.
```

### Example 2: Unresolved Include

**Before**:
```
Line 3: Warning — "Unresolved include: quic_protection"
Source: ivy-lint | Code: unresolved-include
Quick fix: Remove unresolved include
```

**After**:
```
[ivy.module.unresolvedInclude] Cannot resolve include 'quic_protection'

No file named quic_protection.ivy found in include search path.
Searched: quic_tests/, quic_stack/, <stdlib>/

  Closest match: quic_stack/quic_protection.ivy   ← relatedInformation

Suggested fix: Check the directory or workspace root configuration.
Quick fixes: (1) Remove include  (2) Use quic_stack.quic_protection
```

### Example 3: Orphaned RFC Tag

**Before**:
```
Line 89: Warning — "Orphaned RFC tag: [rfc9000:4.99] does not match any loaded requirement manifest"
Source: ivy-lsp-semantic | Code: (none)
```

**After**:
```
[ivy.rfc.orphanedTag] Tag [rfc9000:4.99] has no matching requirement

The bracket tag does not match any requirement ID in the loaded
manifest (rfc9000_requirements.yaml).

  Loaded sections: 4.1, 4.2, ..., 4.12
  Closest match: rfc9000:4.9 (edit distance 1)   ← relatedInformation

Quick fix: Correct to [rfc9000:4.9]
```

---

## 6. Migration (No Backward Compatibility)

Old error codes are deleted outright — no aliases, no transition period:
- `missing-lang-header` → deleted, replaced by `ivy.syntax.missingLangHeader`
- `unresolved-include` → deleted, replaced by `ivy.module.unresolvedInclude`
- `ivy.no-monitor` → deleted, replaced by `ivy.action.noMonitor`
- `ivy.unguarded-write` → deleted, replaced by `ivy.invariant.unguardedWrite`

`code_action.py` switches to new codes only. Old source tags (`ivy-lsp`, `ivy-lint`, `ivy-lsp-reqs`, etc.) are replaced by the 5 normalized tags in a single pass. MCP output schema changes in-place (new fields replace old flat format).

---

## 7. Verification

### Tests
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/ -x -v
```

Existing diagnostic test files:
- `tests/test_mcp_lint_diagnostics.py`
- `tests/test_coverage_diagnostics.py`
- `tests/test_semantic_diagnostics.py`
- `tests/test_requirement_diagnostics.py`
- `tests/test_pull_diagnostics.py`
- `tests/test_scoped_diagnostics.py`

New test files:
- `tests/test_diagnostic_registry.py` — codes lookup, mode filtering
- `tests/test_rich_diagnostic.py` — `IvyDiagnostic` to_lsp/to_mcp_dict conversion
- `tests/test_name_resolver.py` (Phase 2) — undefined symbol, duplicate, conflict
- `tests/test_type_checker.py` (Phase 2) — arity, sort mismatch

### MCP verification
```
ivy_lint <file>        → should return new error codes
ivy_diagnostics <file> → should return rich diagnostics with explanation/context/suggested_fix
```

### Manual LSP verification
1. Open `.ivy` file with known parse error (duplicate symbol)
2. Verify diagnostic shows new code, rich message, related locations
3. Verify code action menu shows appropriate quick fix
4. Change severity mode and verify filtering

---

## 8. Critical Files

| File | Phase | Changes |
|------|-------|---------|
| `ivy_lsp/features/diagnostics.py` | 1, 2, 3 | Central orchestrator — `IvyDiagnostic` migration, T2 integration, T3 enrichment |
| `ivy_lsp/utils/ivy_output.py` | 1, 3 | Error formatting, "did you mean", error classification, counterexample formatting |
| `ivy_lsp/utils/structural_lint.py` | 1 | Richer structural checks, related info |
| `ivy_lsp/features/code_action.py` | 1, 2 | Expand from 4 to 12 quick fixes |
| `ivy_lsp/tools/verification.py` | 1 | Unify MCP diagnostics with shared pipeline |
| `ivy_lsp/semantic/analysis_pipeline.py` | 2, 3 | T2 name/type checking, T3→T2 feedback |
| `ivy_lsp/server.py` | 3 | Severity mode initialization |
| NEW: `ivy_lsp/diagnostics/__init__.py` | 1 | Package init |
| NEW: `ivy_lsp/diagnostics/codes.py` | 1 | Error code registry |
| NEW: `ivy_lsp/diagnostics/rich_diagnostic.py` | 1 | `IvyDiagnostic` dataclass + converters |
| NEW: `ivy_lsp/diagnostics/modes.py` | 1 | Severity profile configuration |
| NEW: `ivy_lsp/diagnostics/name_resolver.py` | 2 | T2 name resolution checks |
| NEW: `ivy_lsp/diagnostics/type_checker.py` | 2 | T2 lightweight type checks |
