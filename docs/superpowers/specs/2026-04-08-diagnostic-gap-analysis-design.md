# Ivy-LSP Diagnostic Gap Analysis: Protocol Conformance Coverage

**Date:** 2026-04-08
**Status:** Draft
**Scope:** Gap analysis of ivy-lsp diagnostic codes vs. protocol-testing specs (QUIC + APT), with concrete proposals for new diagnostics

## 1. Context

The ivy-lsp diagnostic registry (`core/diagnostics/codes.py`) defines 26 codes across 8 categories. The protocol-testing specs in `protocol-testing/quic/` and `protocol-testing/apt/` contain 220+ `require` statements, error code predicates, `_finalize` assertions, and attack-specific patterns (`handle_maliciously`, dual-path `around` advice). This spec documents gaps between what the codebase checks and what the LSP reports, and proposes 8 new diagnostic codes plus 4 informal code unifications.

### Design Decisions

- **Universal diagnostics only.** Every proposal detects a pattern that generalizes across protocol models (QUIC, APT, and future protocols like BGP, CoAP, HTTP). No `ivy.quic.*` or `ivy.apt.*` categories.
- **Hybrid approach (Approach C).** Extend existing 8 categories where proposals fit naturally. Add one new category (`ivy.conformance.*`) for protocol-modeling patterns that don't map to existing buckets. Boundary criterion: if the diagnostic fires because of how Ivy-the-language is used (syntax, naming, types, modules), it goes in an existing category; if it fires because of how a protocol model is structured (error predicates, test finalization, attack paths), it goes in `ivy.conformance.*`.
- **Commented-out FSM guards ignored.** The sending/receiving FSM files have extensive commented-out `require` statements. These represent theoretical design, not executable checks.
- **Cross-file diagnostics use confidence gating.** Diagnostics that depend on the indexer's include chain resolution suppress themselves when the chain is reported as incomplete, avoiding false positives from stale or partial indexes.

## 2. Gap Analysis

### 2.1 Error Predicate Usage

Every test spec's `_finalize` calls predicates like `is_no_error`, `is_protocol_violation`, or `is_no_error_h3`, defined in protocol-specific error code modules (`quic_transport_error_code.ivy`, `quic_h3_error_code.ivy`). No existing diagnostic checks whether the file's include chain reaches the defining module. A broken chain causes an opaque `ivy_check` failure that the LSP could catch statically.

**Covered by existing codes:** No.
**Gap:** Proposal #1 (`ivy.conformance.missingErrorImport`).

### 2.2 _finalize Completeness

`_finalize` is the standard test assertion point. Two patterns are near-universal: error state check (`require is_no_error`) and data flow check (`require conn_total_data(the_cid) > 0`). The existing `ivy.action.missingFinalize` checks whether `_finalize` exists but not whether its body follows expected patterns.

**Covered by existing codes:** Partially (`ivy.action.missingFinalize` covers absence only).
**Gap:** Proposal #2 (`ivy.conformance.incompleteFinalize`).

### 2.3 handle_maliciously Structure

APT specs use a dual-path pattern in `around` advice: `_generating` injects attack constraints, `~_generating` verifies compliance. Both paths must be present. Additionally, `handle_maliciously` requires importing the protocol-specific malicious frame module. Neither structural requirement has a diagnostic.

**Covered by existing codes:** No.
**Gaps:** Proposals #3 (`ivy.conformance.maliciousNoImport`) and #4 (`ivy.conformance.incompleteDualPath`).

### 2.4 RFC Tag Coverage for require Statements

The existing `ivy.rfc.missingTag` fires on "assertions without RFC tags." In protocol specs, conformance checks are overwhelmingly `require` statements inside monitors, not `assert` statements. If the current implementation only matches `assert`, it misses the primary conformance annotation surface (74 `require` statements in `quic_packet.ivy` alone).

**Covered by existing codes:** Possibly — depends on implementation. See Section 5.1.
**Gap (conditional):** Proposal #5 (`ivy.conformance.untaggedRequire`), pending investigation.

### 2.5 Monitor-Action Binding

Test specs define `before`/`after`/`around` advice on actions like `packet_event`, `frame.ack.handle`. If the include chain doesn't define the target action, the monitor is orphaned and has no effect. `ivy.naming.undefinedSymbol` may not cover monitor-style action references.

**Covered by existing codes:** Possibly partially by `ivy.naming.undefinedSymbol`.
**Gap:** Proposal #6 (`ivy.action.orphanedMonitor`).

### 2.6 Import/Export Pairing

APT CVE test specs use `import action show_cve_*()` to declare attack entry points. An unmatched `import action` (no corresponding `export` in scope) is a silent error — the action never fires.

**Covered by existing codes:** No.
**Gap:** Proposal #7 (`ivy.action.unmatchedImport`).

### 2.7 RFC-Tagged Verification Failures

When `ivy_check` fails on a `require` that has an RFC section tag, the existing `ivy.verify.checkError` gives a generic message. Extracting the tag and surfacing it in the diagnostic bridges verification failures to specific RFC requirements.

**Covered by existing codes:** Generic coverage by `ivy.verify.checkError`.
**Gap:** Proposal #8 (`ivy.verify.conformanceFailure`).

## 3. Tier 1 Proposals: LSP-Native (Static)

All Tier 1 diagnostics emit during the **full diagnostics** pipeline stage (debounced, ~300ms). They use the indexer's include chain and symbol table, with confidence gating to suppress when the indexer reports incomplete resolution.

### 3.1 `ivy.conformance.missingErrorImport`

| Field | Value |
|-------|-------|
| **Code** | `ivy.conformance.missingErrorImport` |
| **Severity** | Warning |
| **Source** | `ivy-semantic` |
| **Message** | `Error predicate '{predicate}' used but '{module}' not in include chain` |
| **Explanation** | Test specifications that reference error predicates (is_no_error, is_protocol_violation, etc.) must include the module that defines them. Without it, ivy_check will fail with an undefined symbol error. |
| **has_quick_fix** | Yes — insert the missing `include` directive |
| **has_related_info** | Yes — location of the predicate definition in the error code module |
| **Pipeline stage** | Full diagnostics (Tier 2) |

**Confidence gate:** Suppress when indexer reports include chain as incomplete.

**Detection pattern:** File uses an identifier matching a known error-predicate naming convention (e.g., `is_*_error`, `is_no_error`), indexer confirms no transitive include reaches the defining module.

**Example:** In `quic_server_test.ivy`, `_finalize` calls `require is_no_error`. If the include chain to `quic_transport_error_code.ivy` is broken, fires on the `require` line.

### 3.2 `ivy.conformance.incompleteFinalize`

| Field | Value |
|-------|-------|
| **Code** | `ivy.conformance.incompleteFinalize` |
| **Severity** | Hint |
| **Source** | `ivy-semantic` |
| **Message** | `_finalize may be incomplete: missing {check_type} check` |
| **Explanation** | Protocol test specifications conventionally check error state and data flow in _finalize. Missing one of these checks may indicate an incomplete test assertion. |
| **has_quick_fix** | Yes — insert template `require` statements |
| **has_related_info** | No |
| **Pipeline stage** | Full diagnostics (Tier 2) |

**Confidence gate:** Only fires in files containing `export action _finalize`. Does not fire if `_finalize` body contains custom assertions that don't follow the standard pattern.

**Example:** `quic_server_test_0rtt.ivy` has `_finalize` with data check but no error state check. Fires with `check_type = "error state (e.g., is_no_error)"`.

**Severity note:** Hint rather than Warning because omitting the error check is sometimes intentional (tests that expect errors). A Warning would create noise in those cases.

### 3.3 `ivy.conformance.maliciousNoImport`

| Field | Value |
|-------|-------|
| **Code** | `ivy.conformance.maliciousNoImport` |
| **Severity** | Warning |
| **Source** | `ivy-semantic` |
| **Message** | `'{action}' requires import of malicious module '{module}'` |
| **Explanation** | Attack specifications using handle_maliciously or malicious frame/packet actions must include the protocol-specific malicious module. Without it, the attack path has no effect. |
| **has_quick_fix** | Yes — insert the missing `include` |
| **has_related_info** | Yes — location of the `handle_maliciously` definition |
| **Pipeline stage** | Full diagnostics (Tier 2) |

**Confidence gate:** Same indexer-completeness check as `missingErrorImport`.

**Detection pattern:** File contains `handle_maliciously` or `malicious_`-prefixed identifiers, but include chain doesn't reach a module matching `malicious_*`.

### 3.4 `ivy.conformance.incompleteDualPath`

| Field | Value |
|-------|-------|
| **Code** | `ivy.conformance.incompleteDualPath` |
| **Severity** | Warning |
| **Source** | `ivy-semantic` |
| **Message** | `Around advice on '{action}' missing {missing_path} path` |
| **Explanation** | Attack specifications using around advice conventionally define both a _generating path (attack injection) and a ~_generating path (compliance verification). Missing one makes the attack model incomplete. |
| **has_quick_fix** | Yes — insert skeleton `if _generating { ... }` or `if ~_generating { ... }` block |
| **has_related_info** | No |
| **Pipeline stage** | Full diagnostics (Tier 2) |

**Confidence gate:** Only fires in files that also contain `handle_maliciously` or are in an APT-like directory context.

**Feasibility caveat:** Detecting `_generating` branch presence requires parsing `if` conditions inside `around` blocks. Regex-based detection may be fragile for nested conditionals. A more robust approach would use the AST from the indexer.

### 3.5 `ivy.conformance.untaggedRequire` (conditional)

| Field | Value |
|-------|-------|
| **Code** | `ivy.conformance.untaggedRequire` |
| **Severity** | Hint |
| **Source** | `ivy-rfc` |
| **Message** | `Conformance require in monitor lacks RFC section tag` |
| **Explanation** | Require statements in before/after/around monitors typically represent protocol conformance checks and should be annotated with an RFC section reference (e.g., # [4]) for traceability. |
| **has_quick_fix** | Yes — insert `# []` placeholder tag |
| **has_related_info** | No |
| **Pipeline stage** | Full diagnostics (Tier 2) |

**Confidence gate:** Only fires on `require` inside `before`/`after`/`around` blocks. Does not fire on `require` in regular actions, `_finalize`, or top-level specs.

**Conditional on investigation:** If `ivy.rfc.missingTag` already covers `require` in monitors, this proposal is redundant. Instead, update the existing descriptor message from "Assertion" to "Assertion or conformance require." See Section 5.1.

### 3.6 `ivy.action.orphanedMonitor`

| Field | Value |
|-------|-------|
| **Code** | `ivy.action.orphanedMonitor` |
| **Severity** | Warning |
| **Source** | `ivy-semantic` |
| **Message** | `Monitor on '{action}' — action not found in include chain` |
| **Explanation** | A before/after/around advice block references an action that is not defined or reachable through the current file's include chain. The monitor will have no effect. |
| **has_quick_fix** | No |
| **has_related_info** | No |
| **Pipeline stage** | Full diagnostics (Tier 2) |

**Confidence gate:** Suppress when indexer reports include chain as incomplete.

### 3.7 `ivy.action.unmatchedImport`

| Field | Value |
|-------|-------|
| **Code** | `ivy.action.unmatchedImport` |
| **Severity** | Warning |
| **Source** | `ivy-semantic` |
| **Message** | `import action '{action}' has no matching export in scope` |
| **Explanation** | An import action declaration requires a corresponding export action in a reachable module. Without it, the action is never called. |
| **has_quick_fix** | No |
| **has_related_info** | Yes — if the export exists in a non-included module, show its location |
| **Pipeline stage** | Full diagnostics (Tier 2) |

**Confidence gate:** Suppress when indexer reports include chain as incomplete. Also suppress for well-known framework imports (like `_finalize`) where the export is provided by the test harness at runtime.

## 4. Tier 2 Proposal: ivy_check-Dependent

### 4.1 `ivy.verify.conformanceFailure`

| Field | Value |
|-------|-------|
| **Code** | `ivy.verify.conformanceFailure` |
| **Severity** | Error |
| **Source** | `ivy_check` |
| **Message** | `Conformance check failed: {require_text} [{rfc_tag}]` |
| **Explanation** | A require statement annotated with an RFC section tag failed verification. This indicates the implementation under test violates the referenced protocol requirement. |
| **has_quick_fix** | No |
| **has_related_info** | Yes — the RFC section tag links to the specific requirement; counterexample trace if available |
| **Pipeline stage** | Deep diagnostics (Tier 3, async on save) |

**Implementation:** When `ivy_check` produces a counterexample for a `require` that has an RFC tag comment, the deep diagnostics parser extracts the tag and emits this code instead of `ivy.verify.checkError`. The current parser already maps line numbers; tag extraction is a regex on the matched source line.

**Why only one Tier 2 proposal:** Other ivy_check-dependent patterns (error code mutex violations, transport parameter failures, stream state errors) are already caught by `ivy.verify.checkError` and `ivy.verify.counterexample`. Further sub-classification would require heuristic analysis of counterexample variable names, which is fragile and protocol-specific. The RFC tag approach is robust because the tag is explicit author annotation.

## 5. Informal Code Unification

The 4 informal codes are semantic duplicates of registered descriptors, emitted as raw dicts that bypass the registry. The fix for each is a routing change.

### 5.1 `missing-lang-header` → `ivy.syntax.missingLangHeader`

- **Location:** `structural_lint.py:36`, `check_structural_issues_raw()`
- **Change:** Replace raw dict with `IvyDiagnostic(code="ivy.syntax.missingLangHeader", ...)`. Update `code_action.py:40-57` code match from `"missing-lang-header"` to `"ivy.syntax.missingLangHeader"`.

### 5.2 `unresolved-include` → `ivy.module.unresolvedInclude`

- **Location:** `structural_lint.py:107`, `check_unresolved_includes_raw()`
- **Change:** Replace raw dict with `IvyDiagnostic(code="ivy.module.unresolvedInclude", ...)`. Update `code_action.py:59-89` code match.

### 5.3 `ivy.no-monitor` → `ivy.action.noMonitor`

- **Location:** `coverage_hints.py:58`, `compute_coverage_hints()`
- **Change:** Replace raw dict with `IvyDiagnostic(code="ivy.action.noMonitor", ...)`. Update `code_action.py:91-100` code match. Check MCP tool output and diagnostic filters for the old string.

### 5.4 `ivy.unguarded-write` → `ivy.invariant.unguardedWrite`

- **Location:** `coverage_hints.py:99`, `compute_coverage_hints()`
- **Change:** Replace raw dict with `IvyDiagnostic(code="ivy.invariant.unguardedWrite", ...)`. Update `code_action.py:111-127` code match.

### Cross-Cutting Refactor

All four helpers should return `IvyDiagnostic` instances instead of raw dicts. `compute.py` should call `.to_lsp()` on them instead of manual dict-to-Diagnostic conversion. This also gives all four codes the `code_description` URL, `related` location support, and MCP-compatible output that the raw path lacks.

## 6. Existing Diagnostic Coverage Gaps

### 6.1 `ivy.rfc.missingTag` — require coverage

**Issue:** Descriptor says "Assertion without RFC tag." In protocol specs, conformance checks are `require` statements in monitors, not `assert` statements. If the implementation only matches `assert`, it misses the primary annotation surface.

**Action:** Read the detection implementation. If only `assert`: extend to `require` in monitor blocks, update descriptor message to "Assertion or require statement without RFC tag," and drop proposal #5. If already covers `require`: update descriptor message for accuracy and drop proposal #5.

### 6.2 `ivy.naming.undefinedSymbol` — action body tracing

**Issue:** May not resolve symbols inside action bodies (like `_finalize`). An undefined predicate inside `_finalize` always causes `ivy_check` failure, but static detection would surface it immediately.

**Action:** Verify indexer symbol resolution depth. If action bodies are not traced, extending this would partially subsume proposal #1, though proposal #1 adds specific "which include to add" guidance.

### 6.3 `ivy.action.missingFinalize` — body validation relationship

**Issue:** Checks absence of `_finalize` but not body quality. This is intentional scope, not a bug. Proposal #2 (`ivy.conformance.incompleteFinalize`) is the complementary extension.

**Action:** None — documenting the relationship to prevent implementation confusion.

## 7. Registry Impact Summary

| # | Code | Category | Tier | Severity | Type |
|---|------|----------|------|----------|------|
| 1 | `ivy.conformance.missingErrorImport` | conformance (new) | 1 | Warning | New code |
| 2 | `ivy.conformance.incompleteFinalize` | conformance (new) | 1 | Hint | New code |
| 3 | `ivy.conformance.maliciousNoImport` | conformance (new) | 1 | Warning | New code |
| 4 | `ivy.conformance.incompleteDualPath` | conformance (new) | 1 | Warning | New code |
| 5 | `ivy.conformance.untaggedRequire` | conformance (new) | 1 | Hint | New code (conditional) |
| 6 | `ivy.action.orphanedMonitor` | action (existing) | 1 | Warning | New code |
| 7 | `ivy.action.unmatchedImport` | action (existing) | 1 | Warning | New code |
| 8 | `ivy.verify.conformanceFailure` | verify (existing) | 2 | Error | New code |

Plus 4 informal code unifications (routing changes, no new descriptors) and 3 existing coverage gap investigations.

Total registry after implementation: 33-34 codes across 9 categories (up from 26 across 8).
