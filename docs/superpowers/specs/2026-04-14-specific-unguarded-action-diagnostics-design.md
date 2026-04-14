# Specific Unguarded-Action Diagnostics

**Date:** 2026-04-14
**Status:** Approved

## Problem

The structural lint `unguarded-action` diagnostic produces a generic message:

```
Action modifies state but has no 'require' precondition — consider adding guards.
```

This doesn't name which action or which state variables are involved, making it hard to act on, especially in large files with many actions.

## Solution

Enhance the graph-based `coverage_hints.py` to produce an **action-centric** diagnostic that names the specific state variables being written without guards. Suppress the generic structural lint when the graph is available.

### New Diagnostic: `ivy.action.unguardedWrite`

**Location:** `ivy_lsp/core/coverage_hints.py`

For each action in the RequirementGraph:
1. Collect state variables the action WRITES (via `EdgeType.WRITES` edges)
2. Filter to variables not in `guarded_vars` (not read by any requirement or property)
3. If non-empty, emit diagnostic at the action's declaration line

**Message format:**
```
Action 'recv_tcp' writes 'sock.data', 'sock.connected' without a 'require' precondition
```

**Properties:**
- Code: `ivy.action.unguardedWrite`
- Severity: Hint
- Source: `ivy-semantic` (via coverage hints pipeline)
- Template: `require <first_var>(...)`

### Deduplication in compute.py

When the graph is available and coverage hints ran successfully, filter structural diagnostics to remove entries with `code == "unguarded-action"`. This prevents showing both the generic and specific versions.

When the graph is NOT available (cold start, parse failure), the structural `unguarded-action` still fires as a fallback.

### Codes Registry

Register in `ivy_lsp/core/diagnostics/codes.py`:
- Code: `ivy.action.unguardedWrite`
- Title: `"Unguarded state writes in action '{action}'"`
- Explanation: `"Action writes state variables not guarded by any requirement. Add require/ensure clauses to constrain writes."`
- Severity: Hint
- Source: `ivy-semantic`
- `has_quick_fix`: True

### Relationship to Existing `ivy.unguarded-write`

The existing variable-centric `ivy.unguarded-write` diagnostic (points to variable declaration line) stays unchanged. It provides a complementary perspective: "this variable is written without guards" vs. "this action writes these variables without guards."

## Files Changed

| File | Change |
|------|--------|
| `ivy_lsp/core/coverage_hints.py` | Add action-centric unguarded write diagnostic |
| `ivy_lsp/core/diagnostics/codes.py` | Register `ivy.action.unguardedWrite` |
| `ivy_lsp/lsp/diagnostics/compute.py` | Suppress structural `unguarded-action` when graph available |
| `tests/test_coverage_hints.py` | Test new diagnostic with variable names |
| `tests/test_structural_lint.py` | Test deduplication behavior |

## Testing

1. Action with unguarded writes produces specific diagnostic naming variables
2. Action with all writes guarded produces no diagnostic
3. Structural `unguarded-action` suppressed when graph available
4. Structural `unguarded-action` still fires when graph unavailable (fallback)
