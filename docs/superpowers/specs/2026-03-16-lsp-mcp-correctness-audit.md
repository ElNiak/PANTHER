# LSP + MCP Tool Response Correctness Audit

**Date**: 2026-03-16
**Scope**: Ivy LSP (via `.lsp.json` / `uvx`) and MCP tools (via `ivy-tools` plugin)
**Method**: Cross-reference every tool response against source file ground truth

---

## Summary

| Dimension | Tool | Verdict | Issues |
|-----------|------|---------|--------|
| **Semantic** | documentSymbol | **PARTIAL** | 2/29 symbols have wrong line numbers (alias, nested action) |
| **Semantic** | hover | **BUG** | "Defined in" reports wrong file for multi-definition symbols |
| **Semantic** | findReferences | **PASS** | 1392 refs for `cid`, 77 for `endpoint_to_pid` — volumes correct |
| **Semantic** | goToDefinition | **DESIGN ISSUE** | `include` resolves to 180 include-lines, not the module file |
| **Semantic** | workspaceSymbol | **PASS** | Returns correct symbols (truncated at 100) |
| **Schema** | ivy_capabilities | **PASS** | `{success, ivy_check, ivyc, ivy_show}` |
| **Schema** | ivy_lint | **PASS** | All fields present: success, file, diagnostics, counts |
| **Schema** | ivy_coverage(stats) | **PASS** | Math correct: 71+30=101, 70.3% ✓ |
| **Schema** | ivy_coverage(matrix) | **PASS** | Executes but 519K output (too large for context) |
| **Negative** | ivy_lint (bad file) | **PASS** | Catches missing `#lang` header correctly |
| **Negative** | ivy_lint (missing file) | **PASS** | `{success: false, message: "File not found"}` |
| **Negative** | hover (blank line) | **PASS** | Returns empty correctly |
| **Negative** | goToDefinition (blank) | **PASS** | Returns empty correctly |
| **Consistency** | documentSymbol ↔ hover | **BUG** | documentSymbol says file A, hover says "Defined in" file B |

**Overall**: 10 PASS, 2 BUG, 1 PARTIAL, 1 DESIGN ISSUE

---

## Detailed Findings

### Finding 1: documentSymbol Line Number Bugs (Critical)

**Affected symbols**: `alias` declarations and actions inside `object` blocks.

**Evidence** (file: `quic_types.ivy`):

| Symbol | LSP Line | Actual Line | Actual Code |
|--------|----------|-------------|-------------|
| `aid` | **1** | **43** | `alias aid = cid` |
| `next` | **1** | **133** | `action next(e:this) returns (e:this) = {` |

All other 27 symbols in `quic_types.ivy` have correct line numbers (93% accuracy).

**Root cause hypothesis**: The fallback scanner in `ivy_lsp/parsing/fallback_scanner.py` doesn't handle:
1. The `alias` keyword — assigns line 1 as default
2. Actions nested inside `object` blocks — loses scope context and defaults to line 1

**Severity**: Critical — incorrect line numbers cause hover, goToDefinition, and findReferences to target the wrong position when triggered from documentSymbol results.

### Finding 2: hover Reports Wrong Definition File (Critical)

**Evidence**:

| Symbol | File Cursor Is In | hover "Defined in" | Correct? |
|--------|-------------------|---------------------|----------|
| `cid` | `quic_types.ivy` | `quic_types.ivy` | ✓ (only 1 definition) |
| `endpoint_to_pid` | `ivy_quic_server_behavior.ivy` | `ivy_minip_attacker_server_behavior.ivy` | **WRONG** |
| `packet_event` | `ivy_quic_server_behavior.ivy` | `ivy_quic_n_clients_behavior.ivy` | **WRONG** |

**Pattern**: When a symbol is defined in multiple files (common for actions in behavior files), hover picks a *different* file than the one the cursor is in. The selected file appears to be the first match from `indexer.lookup_symbol()`, which likely returns results in index order (not current-file-first).

**Root cause hypothesis**: `hover` handler calls `lookup_symbol(name)` which returns `List[SymbolLocation]` and takes `[0]` without checking if any result is in the current file.

**Severity**: Critical — misleading navigation. User sees "Defined in: file_X.ivy" when they're hovering on the definition in file_Y.ivy.

### Finding 3: goToDefinition on `include` Returns All Include Statements (Design Issue)

**Evidence**: `goToDefinition` on `include order` (line 3 of `ivy_quic_server_behavior.ivy`) returns **180 results** — every `include order` line across the entire workspace.

**Expected behavior**: Should resolve to the actual `order.ivy` module file.

**Actual behavior**: Returns all files that contain `include order`, pointing to their include lines (mostly line 3:1).

**Severity**: Warning — not a crash, but not useful for navigation. The 180-result list is noise.

**Root cause**: The goToDefinition handler likely does a text search for the include target name across all files rather than resolving the include path to the actual module file.

### Finding 4: goToDefinition Picks Up Temporary Files (Info)

**Evidence**: `goToDefinition` on `cid` in `quic_types.ivy` returned 3 results including `/private/tmp/claude-501/test_no_header.ivy:1:1` — a temporary test file we created during validation containing just `type cid`.

**Severity**: Info — correct behavior (it IS a definition of `cid`), but workspace indexing shouldn't include `/tmp` paths. Check `IVY_LSP_EXCLUDE_PATHS` configuration.

### Finding 5: ivy_coverage(matrix) Output Size (Info)

**Evidence**: `ivy_coverage(mode="matrix")` produces 519,443 characters of output. This exceeds typical context window limits and cannot be reviewed inline.

**Severity**: Info — the tool works but the output is too large for practical use in a Claude Code session. Consider adding pagination or a `limit` parameter.

---

## MCP Schema Verification

### ivy_capabilities
```json
{"success": true, "ivy_check": true, "ivyc": true, "ivy_show": true}
```
**Verdict**: PASS — all expected fields present.

### ivy_lint (clean file)
```json
{"success": true, "file": "...", "diagnostics": [], "diagnostic_count": 0, "error_count": 0, "warning_count": 0}
```
**Verdict**: PASS — schema matches `traceability.py` spec.

### ivy_lint (bad file — missing header)
```json
{"success": true, "diagnostics": [{"line": 1, "severity": "warning", "message": "Missing '#lang ivy1.7' header", "source": "ivy-lint", "code": "missing-lang-header"}], "diagnostic_count": 1, "warning_count": 1}
```
**Verdict**: PASS — correctly detects structural issue.

### ivy_lint (nonexistent file)
```json
{"success": false, "message": "File not found: nonexistent/file.ivy"}
```
**Verdict**: PASS — graceful failure.

### ivy_coverage(stats)
```
total=101, covered=71, uncovered=30, coverage_percent=70.3
by_level: MUST(45), SHOULD(17), MAY(24), MUST NOT(12), SHOULD NOT(3) → sum=101 ✓
71/101 = 70.297... → rounded to 70.3 ✓
```
**Verdict**: PASS — all fields present, math is correct.

---

## Cross-Tool Consistency

### Test: Trace `endpoint_to_pid` through all tools

| Step | Tool | Result | Consistent? |
|------|------|--------|-------------|
| 1 | documentSymbol | `endpoint_to_pid` at line 74 in `ivy_quic_server_behavior.ivy` | — |
| 2 | hover at line 74 | Signature correct, but "Defined in: ivy_minip_attacker_server_behavior.ivy" | **INCONSISTENT** |
| 3 | findReferences at line 74 | 77 references across 32 files | ✓ |
| 4 | goToDefinition on param type | 14 definitions for `ip.endpoint` | ✓ |

**Verdict**: documentSymbol and hover **disagree** on which file owns the symbol.

---

## Recommendations

### Must Fix (Critical)
1. **documentSymbol line numbers**: Fix fallback scanner to handle `alias` keyword and nested `action` declarations inside `object` blocks. Both currently default to line 1.
2. **hover "Defined in" file**: When multiple definitions exist, prefer the current file's definition. Fall back to first match only if the symbol isn't defined in the current file.

### Should Fix (Warning)
3. **goToDefinition on includes**: Resolve `include <name>` to the actual `.ivy` module file instead of returning all include statements across the workspace.
4. **ivy_coverage(matrix) output size**: Add a `limit` or `compact` parameter to avoid overwhelming context windows (519K chars).

### Could Fix (Info)
5. **Workspace indexing scope**: Ensure `/tmp` and `/private/tmp` paths are excluded from workspace indexing to prevent temporary files from appearing in results.
6. **definition auto-names**: `def211304` and `def211305` in documentSymbol are auto-generated names for `definition zero = 0` and `definition one = 1`. Consider preserving the actual Ivy names.

---

## Test Files Used

| File | Purpose |
|------|---------|
| `protocol-testing/quic/quic_stack/quic_types.ivy` | Ground truth: 29 type/object symbols |
| `protocol-testing/quic/quic_entities_behavior/ivy_quic_server_behavior.ivy` | Ground truth: actions + before/after monitors |
| `test/test_lexer.ivy` | Negative test: missing `#lang` header |
| `/private/tmp/claude-501/test_no_header.ivy` | Negative test: minimal `type cid` definition |
