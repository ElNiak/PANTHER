# Ivy-LSP Diagnostic Gap Analysis: Bottom-Up Code Proposals

**Date:** 2026-04-08
**Status:** Proposed
**Scope:** New diagnostic codes for the ivy-lsp language server, derived from git history mining and source code pattern analysis

## Methodology

This spec was produced through bottom-up analysis of three sources:

1. **ivy-lsp submodule git history** (~100 commits at `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`). Every `fix:` commit was diffed and categorized by bug type. Bug fix patterns were evaluated for whether the root cause could have been caught by a static diagnostic on `.ivy` source files.

2. **QUIC protocol-testing source files** (~200 `.ivy` files across 12 subdirectories in `protocol-testing/quic/`). Structural patterns scanned: require statements, includes, monitors, RFC tags, state variables, type/variant declarations, C++ implementation blocks, and parameter declarations.

3. **APT protocol-testing source files** (~362 `.ivy` files across 10 subdirectories in `protocol-testing/apt/`). Lighter cross-validation pass to confirm whether QUIC patterns generalize across protocols.

## Naming Convention

All new diagnostic codes use the three-part convention `ivy.category.specificName`:

| Category | Scope |
|---|---|
| `ivy.include` | Include resolution, cross-layer, near-miss, shadowing |
| `ivy.type` | Type/variant checks (duplicate tags, declaration collisions) |
| `ivy.require` | Require statement patterns (commented-out, dead guards) |
| `ivy.param` | Parameter checks (default divergence) |
| `ivy.rfc` | RFC tag tracking (gaps, duplicates, orphaned annotations) |
| `ivy.state` | State variable analysis (unused vars) |
| `ivy.monitor` | Monitor/action consistency (orphaned hooks) |

Existing diagnostics that currently use kebab-case (`missing-lang-header`, `unresolved-include`) or lack codes entirely should be migrated to this convention in a follow-up. The migration is not part of this spec.

## Summary Table

| Code | Severity | Tier | Description | Confidence |
|---|---|---|---|---|
| `ivy.include.nearMiss` | Warning | 1 | Include fails to resolve but a close filename match exists | High |
| `ivy.include.crossLayer` | Warning | 1 | Include resolves outside the current workspace layer | High |
| `ivy.type.duplicateTag` | Warning | 1 | Two variant types share the same numeric tag value within a file | High |
| `ivy.require.commentedOut` | Hint | 1 | Commented-out `require` statement detected | Medium |
| `ivy.require.deadGuard` | Information | 1 | `require false` used as unreachability sentinel | Medium |
| `ivy.rfc.tagGap` | Information | 1 | Gap in sequential RFC bracket tag numbering within a file | Medium |
| `ivy.rfc.tagDuplicate` | Warning | 1 | Same bracket tag number on multiple assertions in one block | Medium |
| `ivy.include.shadowDeclaration` | Hint | 2 | File re-declares a symbol already in its include closure | Medium |
| `ivy.type.duplicateDeclaration` | Warning | 2 | Same top-level name declared in multiple files within include closure | High |
| `ivy.param.defaultDivergence` | Warning | 2 | Same-named parameter has different default values across files | High |
| `ivy.state.unusedStateVar` | Hint | 2 | State variable declared but has no reads or writes in the requirement graph | High |
| `ivy.monitor.orphanedHook` | Warning | 2 | Monitor (before/after/around) targets an action with no symbol definition | Medium |
| `ivy.rfc.orphanedTag` | Warning | 2 | RFC bracket tag has no corresponding requirement (existing, needs code) | High |
| `ivy.rfc.missingBracketTag` | Hint | 2 | Assertion lacks RFC bracket tag (existing, needs code) | High |

**Tier 1** = implementable with regex/text matching plus the existing include resolver and basename cache. No semantic model needed.
**Tier 2** = requires the include graph, requirement graph, or cross-file symbol resolution from the semantic model.

---

## Tier 1 Diagnostics

### D1: `ivy.include.nearMiss`

**Severity:** Warning
**Source:** `ivy-lint`

**Pattern detected:** An `include` statement fails to resolve, but a filename within edit distance 2 (or a segment permutation) exists in the workspace.

**Evidence:** Commit `640b5f36` in panther_ivy. The file `quic_server_test_ext_min_ack_delay_example.ivy` had `include ivy_quic_shim_client_example_ext` but the actual file was `ivy_quic_shim_client_ext_example` — segments "example" and "ext" were transposed. This compiled silently as "module not found" with no suggestion. The project's naming convention uses multi-segment underscore-joined names (often 5-7 segments like `ivy_quic_shim_client_ext_example`), making transposition errors structurally likely.

**APT cross-validation:** APT filenames follow the same multi-segment pattern (`ivy_minip_shim_attacker_server`, `apt_quic_endpoint`). Same transposition risk applies.

**Recurrence reasoning:** The naming convention is deeply embedded. Every new shim variant, test file, or entity file uses 4-7 underscore-joined segments. With 200+ files in QUIC and 362 in APT, segment transposition is a recurring typo class. The single known occurrence caused silent compilation failure.

**Implementation notes:**
- When `unresolved-include` fires, run the unresolved name against the `BasenameCache` (already maintained at `infra/utils/basename_cache.py`).
- Compute Levenshtein distance and underscore-segment permutations against all cached basenames.
- If a match scores within threshold (distance <= 2, or exact segment set with different ordering), emit `ivy.include.nearMiss` instead of `ivy.include.unresolvedInclude`.
- Message format: `Cannot resolve include 'foo_bar_baz'. Did you mean 'foo_baz_bar'?`
- Integration point: `structural_lint.py:96`, where `unresolved-include` is currently emitted.
- Requires: basename cache (available), string distance function (new, ~20 LOC).

---

### D2: `ivy.include.crossLayer`

**Severity:** Warning
**Source:** `ivy-lint`

**Pattern detected:** An `include` statement resolves, but the target file lives in a workspace layer that is neither the current file's layer nor one of its `depends_on` layers.

**Evidence:** This is the highest-impact bug pattern in the project's history:

- Commit `3e9f5974` (panther_ivy): reverted 35 APT `.ivy` files that had been changed from `include apt_time` to `include quic_time`. The `quic_time.ivy` file lived in the standard QUIC layer, not the APT layer. This broke the entire APT workspace ("module not found" cascading to every APT file that transitively included time utilities).

- Commit `be7c1ec` (ivy-lsp): removed the cross-layer proximity fallback from the include resolver. Before the fix, when a file wasn't found in the correct layer, the resolver guessed by finding the closest-path match in *any* layer. This caused APT files to silently resolve to standard QUIC variants (e.g., APT's `quic_frame.ivy` resolving to standard QUIC's `quic_frame.ivy`), producing 888 staging misses.

**APT cross-validation:** Confirmed. APT's 3 minip shim files include `quic_shim` and `quic_types` directly. These currently work because minip's layer declares `depends_on: [quic]`, but they represent tight coupling that would break if the dependency were removed.

**Recurrence reasoning:** The project maintains multiple workspace layers with overlapping filenames (both QUIC and APT have `quic_frame.ivy`, `quic_time.ivy`, `quic_protection.ivy`). Every time a developer adds or renames a file, there is a risk of writing an include that accidentally resolves to a different layer's file.

**Implementation notes:**
- The `IncludeResolver` already performs strict layer checking after commit `be7c1ec`.
- When an include resolves only via cross-layer fallback (or fails to resolve but would succeed in another layer), emit `ivy.include.crossLayer`.
- Message format: `Include 'quic_time' resolves to layer 'quic_standard' but current file is in layer 'apt_core'. Add 'quic_standard' to depends_on or create a local copy.`
- Integration point: `include_resolver.py`, in the strategy chain methods added in commit `de2c550`.
- Requires: `.ivyworkspace` layer configuration (available), resolver internals (available).

---

### D3: `ivy.type.duplicateTag`

**Severity:** Warning
**Source:** `ivy-lint`

**Pattern detected:** Two `variant` declarations in the same file share the same numeric tag comment (`# tag = N`).

**Evidence:** In `quic_stack/quic_transport_parameters.ivy`:
- Line 33: `object original_destination_connection_id` with `# tag = 15`
- Line 146: `object initial_source_connection_id` with `# tag = 15`

Per RFC 9000, `original_destination_connection_id` should be transport parameter ID 0x00 (tag 0), not 15. This is a real specification bug: the tag comment is wrong, and the LSP currently provides no indication. Additionally, line 210 has `# tag = x` (placeholder) for `unknown_transport_parameter`.

**APT cross-validation:** APT's forked `quic_transport_parameters.ivy` inherits the same tag 15 duplication (the file was copied, not independently authored).

**Recurrence reasoning:** Protocol specifications routinely define enumerated type discriminators (QUIC transport parameter IDs, frame types, error codes). Every new variant type added to these enumerations carries a risk of tag collision, especially during copy-paste-modify workflows. The tag comment convention (`# tag = N`) is informal (not parsed by Ivy), making it invisible to the compiler.

**Implementation notes:**
- Regex scan: `#\s*tag\s*=\s*(\w+)` within each file.
- Collect all (tag_value, line_number) pairs. Flag duplicate numeric values.
- Also flag non-numeric tags (like `x`) with a distinct message: `Tag value 'x' is not numeric — placeholder?`
- Message format: `Duplicate tag value 15 — also used at line 33.`
- Integration point: `structural_lint.py`, as a new check alongside `missing-lang-header` and `unresolved-include`.
- Requires: regex only (~30 LOC).

---

### D4: `ivy.require.commentedOut`

**Severity:** Hint
**Source:** `ivy-lint`

**Pattern detected:** A line matching `#\s*require\s+` appears, indicating a commented-out require statement.

**Evidence:** 683 commented-out require statements across QUIC files (26% of all requires). 183 in APT (with only 12 active requires, a 15:1 ratio). Key concentrations:

- `quic_fsm/quic_fsm_receiving.ivy` lines 86-158: entire state-machine guard blocks disabled.
- `quic_fsm/quic_fsm_sending.ivy` lines 86-148: same pattern.
- APT `quic_mim_test_replay_0rtt.ivy`: MiM replay test with disabled verification guards.

The last case is particularly concerning: commented-out requires in a security-oriented test mean the formal model is not checking the properties it appears to check.

**APT cross-validation:** Confirmed with extreme ratio (15:1 commented-out to active). The pattern is even more prevalent during early protocol development.

**Recurrence reasoning:** Protocol specs evolve iteratively. Developers disable requires during debugging ("comment it out to see if the rest passes") and forget to re-enable them. The informal convention of commenting rather than deleting preserves intent but creates silent verification gaps. Every new protocol added to PANTHER will go through this iteration cycle.

**Ambiguity:** A commented-out require could be intentional documentation ("this is what the RFC says, but we deliberately don't enforce it"). The Hint severity and phrasing accommodate this.

**Implementation notes:**
- Regex: `^\s*#\s*require\b`
- Emit per-line, but aggregate into a file-level count in the message: `Commented-out require statement (12 total in this file). Consider removing or re-enabling.`
- Heuristic for intentional vs accidental: if the line has an adjacent comment containing `TODO`, `FIXME`, `disabled`, `skip`, or `intentional`, suppress or downgrade to Information.
- Integration point: `structural_lint.py`.
- Requires: regex only (~20 LOC).

---

### D5: `ivy.require.deadGuard`

**Severity:** Information
**Source:** `ivy-lint`

**Pattern detected:** `require false` used as an unreachability sentinel, marking an action that should never be called at runtime.

**Evidence:** `quic_stack/quic_frame.ivy:403` contains `require false` with comment "this generic action should never be called." This is a deliberate pattern: the base `frame` object declares a generic `handle` action for the type system, but only variant-specific `handle` implementations should be called. The `require false` ensures that calling the generic action fails the formal verification.

**APT cross-validation:** Not found in APT's current files. However, the variant dispatch pattern exists in APT's entity and lifecycle layers, making this structurally likely to appear as APT specs mature.

**Recurrence reasoning:** Ivy's type system uses variant dispatch where a base type declares actions and variants override them. Any protocol spec that adds variant types (new frame types, new packet types, new attack types) may need dead guard sentinels for the base action.

**Implementation notes:**
- Regex: `require\s+false\s*[;]?\s*(#.*)?$`
- Message: `Dead guard: 'require false' marks this action as unreachable. Called only through variant specializations.`
- Information severity because this is always intentional — the diagnostic serves as documentation, not a warning.
- Integration point: `structural_lint.py`.
- Requires: regex only (~10 LOC).

---

### D6: `ivy.rfc.tagGap`

**Severity:** Information
**Source:** `ivy-lint`

**Pattern detected:** Sequential RFC bracket tags within a file skip a number (e.g., tags [1], [2], [4] with [3] missing).

**Evidence:** In `quic_stack/quic_transport_parameters.ivy`, tag numbering jumps from 12 to 14. Tag 13 is reserved in RFC 9000 (it was removed during the standardization process), so the gap is intentional here. In `quic_stack/quic_frame.ivy`, tags [1], [4], [6], [8], [9], [11] are used — these reference RFC section numbers directly rather than local sequential invariants.

**Recurrence reasoning:** The project uses two tagging conventions: local sequential invariant numbers (where gaps indicate missing coverage) and direct RFC section references (where gaps are expected). New protocol specs will use one or both conventions. When using sequential numbering, gaps often indicate a requirement that was deleted or moved without updating the surrounding tags.

**Implementation notes:**
- Regex scan: `\[(\d+)\]` in comment lines.
- Collect all tag numbers per file. Compute the gap ratio: `(max - min + 1 - count) / (max - min + 1)`.
- Only flag when the gap ratio is below 0.3 (mostly sequential, with a few gaps) AND the tag range is at least 5. This filters out sparse RFC section references.
- Message: `RFC tag gap: [3] is missing between [2] and [4].`
- Integration point: `structural_lint.py`.
- Requires: regex + simple arithmetic (~40 LOC).

---

### D7: `ivy.rfc.tagDuplicate`

**Severity:** Warning (within-block), Information (cross-block)
**Source:** `ivy-lint`

**Pattern detected:** The same bracket tag number appears on multiple assertions within a single code block (action, before, after, around).

**Evidence:** In `quic_stack/quic_packet.ivy`, tags [1]-[10] are duplicated across 8 parallel packet handler blocks (initial, handshake, 0-RTT, 1-RTT, etc.). Each block applies the same invariants to different packet types, so cross-block duplication is intentional. Within-block duplication would indicate a copy-paste error where a tag wasn't updated after duplicating a require statement.

**APT cross-validation:** APT has sparse RFC tagging. The pattern would apply once APT specs mature to include per-requirement RFC annotations.

**Recurrence reasoning:** The project's workflow involves writing one handler per packet type, then copy-pasting invariant checks with adjusted parameters. The tag is the part most likely to be forgotten during the copy.

**Ambiguity:** Cross-block duplication is the norm. Only within-block duplication is a likely error.

**Implementation notes:**
- Scan `\[(\d+)\]` on lines containing or following `require` statements.
- Detect block boundaries via `before`, `after`, `around`, `action`, or `implement` keywords at lower indentation.
- Within each block, flag duplicate tag numbers as Warning.
- Cross-block duplicates: suppress entirely (or emit as Information behind a config toggle, off by default).
- Message: `Duplicate RFC tag [4] within this block — also at line 87.`
- Integration point: `structural_lint.py`.
- Requires: regex + block boundary heuristic (~60 LOC).

---

## Tier 2 Diagnostics

### D8: `ivy.include.shadowDeclaration`

**Severity:** Hint
**Source:** `ivy-lsp-semantic`

**Pattern detected:** A file declares a top-level symbol (relation, function, object, type, individual) that is already declared with the same name in one of its transitively included files.

**Evidence:** Commit `78ef4c80` (panther_ivy): `relation zero_rtt_allowed` was declared in `quic_shim.ivy` (canonical) and also in `quic_shim_example_ext.ivy`, `quic_shim_mim.ivy`, and `quic_shim_multiple_client.ivy`. These shim variants all include `quic_shim` transitively, so the duplicate declarations shadowed the canonical one silently. The fix deleted the duplicates from the 3 variant shims.

Commit `381c3bf` (ivy-lsp): the symbol extractor was processing foreign declarations merged by Ivy's `include` mechanism, producing inflated symbol counts (2,581 from a single file). The fix added `is_from_included_file()` filtering, but the source-level shadowing still occurs silently.

**APT cross-validation:** APT's shim structure mirrors QUIC's. 3 commented-out `variant endpoint of client_attacker_endpoint` declarations in APT endpoint files are a milder form of this pattern.

**Recurrence reasoning:** The shim variant workflow (copy `quic_shim.ivy` to `quic_shim_mim.ivy`, add MiM-specific overrides) is the standard way to create specialized configurations. Every new variant risks carrying over declarations that should only exist in the base shim.

**Heuristic for intentional vs accidental:** If the shadowing file has a variant suffix (`_ext`, `_mim`, `_multiple_client`) and the shadowed symbol is an action that the variant explicitly overrides (has a `before`/`after`/`around` hook on it), it's likely intentional. If the symbol is a `relation` or `function` with identical signature and no associated hooks, it's likely accidental.

**Implementation notes:**
- After include resolution, for each top-level declaration in the current file, check `SemanticModel._nodes_by_name` for pre-existing entries from included files.
- The `_nodes_by_name` index (commit `7ccdc23`) supports O(1) lookups.
- Emit with `DiagnosticRelatedInformation` pointing to the shadowed declaration.
- Message: `'zero_rtt_allowed' shadows a declaration in included file 'quic_shim.ivy' (line 42).`
- Integration point: `compute_semantic_diagnostics()` in `diagnostics.py`, after the semantic model is available.
- Requires: semantic model + include closure (~50 LOC).

---

### D9: `ivy.type.duplicateDeclaration`

**Severity:** Warning
**Source:** `ivy-lsp-semantic`

**Pattern detected:** Two files within the same workspace layer both declare a top-level `object`, `type`, `relation`, or `function` with the same name, and neither file includes the other.

**Evidence:** Commit `78ef4c80` (panther_ivy): both `apt_time.ivy` and `quic_time.ivy` defined `object time_api` with the same structure. When both were in scope via cross-layer includes, Ivy's compiler either picked one silently or produced a confusing "duplicate definition" error with no guidance about which file to fix.

**APT cross-validation:** This was the specific bug that motivated reverting all cross-protocol includes in commit `3e9f5974`. The `time_api` collision cascaded into workspace-wide compilation failure.

**Recurrence reasoning:** The project maintains parallel file hierarchies across workspace layers (QUIC standard, QUIC attacks, APT core, APT protocols). Files are routinely forked from one layer to another. Any forked file that doesn't rename its top-level objects creates a collision risk when the layers are composed.

**Implementation notes:**
- During semantic model construction, build a name-to-file multimap for all top-level declarations within a workspace layer (and its `depends_on` layers).
- Names mapping to 2+ files where neither file includes the other are collisions.
- Exclude the include-chain case (handled by `ivy.include.shadowDeclaration`).
- Emit on both declaring lines with `DiagnosticRelatedInformation` cross-linking.
- Message: `'time_api' is also declared in 'quic_time.ivy' (line 5). One declaration will shadow the other.`
- Integration point: post-construction pass in `SemanticModel`, surfaced via `compute_semantic_diagnostics()`.
- Requires: semantic model + cross-file name index (~70 LOC).

---

### D10: `ivy.param.defaultDivergence`

**Severity:** Warning
**Source:** `ivy-lsp-semantic`

**Pattern detected:** Two or more files in the workspace declare a `parameter` with the same name but different default values.

**Evidence:** From the QUIC source scan:
- `client_port_vn` defined as `4987` in `ivy_quic_n_clients_behavior.ivy` (with comment `#4986 # bind failed: Address already in use`) and as `4986` in `quic_server_test_version_negociation_ext.ivy:18`. The comment reveals this was a workaround for a port conflict, but the divergence is invisible without reading both files.
- `the_cid`, `server_port`, `server_addr` are declared in 3+ files with identical defaults (no divergence, but same structural risk).

**APT cross-validation:** APT inherits the same transport parameter configuration files. `iversion` and `vnversion` appear in multiple shim files with `= 0x1` and `# TODO` comments, suggesting values that may diverge as development continues.

**Recurrence reasoning:** The project configures protocol parameters via `parameter` declarations scattered across shim, behavior, and test files. When a parameter needs to change (e.g., a port conflict), only one file is updated. The 57 `parameter` declarations across QUIC files create a combinatorial space where divergence is easy to introduce and hard to detect manually.

**Implementation notes:**
- Scan all `.ivy` files for `parameter\s+(\w+)\s*:\s*\w+\s*=\s*(.+)` during indexing.
- Build a name-to-list-of-(file, value, line) map.
- Flag entries where the same name has different values (after normalizing whitespace and hex/decimal equivalents like `0xd` vs `13`).
- Emit on each divergent declaration with `DiagnosticRelatedInformation` linking to the others.
- Message: `Parameter 'client_port_vn' has value 4987 here but 4986 in 'quic_server_test_version_negociation_ext.ivy' (line 18).`
- Integration point: post-indexing phase, alongside the semantic model construction.
- Requires: cross-file parameter registry (~60 LOC).

---

### D11: `ivy.state.unusedStateVar`

**Severity:** Hint
**Source:** `ivy-lsp-coverage`

**Pattern detected:** A state variable (declared via `var`, `relation`, or `function` at module scope) has no read or write edges in the requirement graph, meaning no action reads it and no action writes it.

**Evidence:** In `quic_stack/quic_packet.ivy:258`, `relation issued_zero_length_cid` has a TODO comment `#(S:ip.endpoint,D:ip.endpoint) TODO pass that to handle function of frames`, indicating an incomplete parameterization. In APT, `ivy_quic_target.ivy:35-37` has 3 commented-out variable declarations (`the_cid_vn`, `client_alt`, `client_vn`) that were active at some point but are now dead. `malicious_quic_frame.ivy` has a module-level `some_max_streams` at line 545 that is commented out but may have active counterparts elsewhere.

The deeper investigation revealed that the requirement graph infrastructure is approximately 80% complete for this diagnostic:
- `populate_state_vars()` creates `StateVarNode` entries for all known vars from the symbol table.
- `wire_state_var_edges()` connects vars to their readers (READS edges) and writers (WRITES edges).
- After wiring, any `StateVarNode` with no entries in `self._outgoing[var_id]` and no entries in `self._incoming[var_id]` is unused.

**APT cross-validation:** Confirmed. APT lifecycle and entity files contain both active and commented-out variable declarations with unclear usage status.

**Recurrence reasoning:** Protocol specs accumulate state variables during development. Variables are added for new features, then the feature is deferred or redesigned, leaving orphaned declarations. The iterative development cycle (add var, test, comment out, forget) is endemic to formal verification workflows.

**Implementation notes:**
- After `wire_state_var_edges()` completes in the requirement graph, iterate over `self.state_vars`.
- For each `StateVarNode`, check `len(self._outgoing.get(var_id, [])) == 0 and len(self._incoming.get(var_id, [])) == 0`.
- Emit as Hint severity (the var might be used in a way the graph doesn't track, e.g., in C++ implementation blocks).
- Message: `State variable 'issued_zero_length_cid' has no reads or writes in the requirement graph.`
- Integration point: `coverage_hints.py`, alongside `ivy.unguarded-write`.
- Requires: requirement graph (available), ~15 LOC.

---

### D12: `ivy.monitor.orphanedHook`

**Severity:** Warning
**Source:** `ivy-lsp-coverage`

**Pattern detected:** A `before`, `after`, or `around` hook targets an action name that has no real symbol definition in the include closure — it exists only as a backfilled placeholder in the requirement graph.

**Evidence:** The deeper investigation found that `lexer_requirement_extractor.py` already extracts monitor target action names (line 24: `_MONITOR_TOKENS = frozenset({"BEFORE", "AFTER", "AROUND", "IMPLEMENT"})`). The `RequirementNode` stores `monitor_action`. The graph's `populate_actions_from_symbols()` creates action nodes from the symbol table, then backfills missing actions from monitor references (lines 503-513). This backfill masks the diagnostic signal: if a monitor references a typo'd action name, the graph silently creates a placeholder action for it instead of flagging the error.

While no orphaned monitors were found in the current codebase (confirming the initial scan), the detection mechanism is trivially implementable and would catch future errors. The Ivy compiler catches truly unresolved references at compilation time, but the LSP could catch them at edit time (before the developer runs `ivyc`), reducing the feedback loop from minutes to milliseconds.

**APT cross-validation:** APT's `ivy_minip_shim_mim.ivy` has commented-out `after forward_to_client` and `after forward_to_server` hooks. If these were uncommented with a typo in the action name, no existing diagnostic would catch it until compilation.

**Recurrence reasoning:** The project's workflow involves adding new actions to base files and then writing monitors in variant/test files. Typos in action names, especially qualified names like `quic_packet.send_ack_eliciting_handshake_packet`, are structurally likely. The `get_last_component()` utility (commit `9130737`) was extracted specifically because qualified name handling was error-prone across 29 call sites.

**Implementation notes:**
- After `populate_actions_from_symbols()` runs, track which action nodes came from the symbol table vs. backfill.
- For each `RequirementNode` with a `monitor_action`, check if the action's node was symbol-table-derived or backfill-only.
- Backfill-only actions with monitors targeting them are orphaned hooks.
- Use `get_last_component()` for qualified name matching to reduce false positives.
- Message: `Monitor targets action 'send_ack_elicting_packet' which has no definition in the include closure. Did you mean 'send_ack_eliciting_packet'?`
- Integration point: `coverage_hints.py`, after requirement graph construction.
- Requires: requirement graph (available), symbol table (available), ~25 LOC.

---

### D13: `ivy.rfc.orphanedTag` (code assignment)

**Severity:** Warning
**Source:** `ivy-lsp-semantic`

**Pattern detected:** An RFC bracket tag `[N]` appears in a comment but no corresponding `require` statement references it.

**Evidence:** Already implemented in `diagnostics.py:339` using the semantic model's `RfcAnnotation` and `RfcRequirement` nodes. Currently emitted without a `code` field, preventing LSP clients from filtering or grouping these diagnostics.

**Implementation notes:**
- Add `"code": "ivy.rfc.orphanedTag"` to the diagnostic dict at `diagnostics.py:339`.
- One-line change.

---

### D14: `ivy.rfc.missingBracketTag` (code assignment)

**Severity:** Hint
**Source:** `ivy-lsp-semantic`

**Pattern detected:** A `require` statement inside a `before`/`after` monitor lacks an RFC bracket tag annotation, meaning the requirement is not traced to a specific RFC section.

**Evidence:** Already implemented in `diagnostics.py:356`. Currently emitted without a `code` field.

**Implementation notes:**
- Add `"code": "ivy.rfc.missingBracketTag"` to the diagnostic dict at `diagnostics.py:356`.
- One-line change.

---

## Investigated but Excluded

### E1: C++ delimiter mismatch (`<<<`/`>>>`)

All 149 opening delimiters have matching closing delimiters across the QUIC codebase. The Ivy parser catches mismatches as parse errors, making an LSP diagnostic redundant with the existing parse error pipeline.

### E2: Synthetic name collision (`def\d+`)

Commit `c5dea75` fixed a tooling bug where qualified names like `quic.def12` weren't detected as compiler-generated. This was a regex bug in the LSP, not a source-level pattern. The chance of a human author naming something `def12` is negligible. Single occurrence, no structural recurrence risk.

### E3: File size regression detection — FUTURE CONSIDERATION

Commit `99c2f077` restored 8 APT files truncated by a merge conflict (194 cascading parse failures). Initially excluded because the LSP has no historical baseline. Deeper investigation revealed the `PersistentFileCache` (SQLite at `~/.cache/ivy-lsp/<hash>/index.db`) stores file metadata across sessions. Adding a `file_size` column and comparing on re-index would be approximately 20 LOC. Not promoted because file size regressions are better caught by git tooling (pre-commit hooks), but the infrastructure makes it feasible if git-level checks prove insufficient.

### E4: Stale TODO comments — FUTURE CONSIDERATION

10+ `#TODO update rfc9000` comments in APT transport parameter configs. Initially excluded as a generic lint concern. Deeper investigation found that many TODOs are Ivy/protocol-spec-specific: `#TODO update rfc9000` (14 config files), `#TODO update v29` (draft version references), `TODO RETRY VULN` (security-specific). A narrowly scoped `ivy.rfc.staleTodo` diagnostic matching `#\s*TODO.*rfc\d+` or `#\s*TODO.*update.*v\d+` would be Ivy-specific and actionable. Not promoted because the 10 proposed diagnostics represent higher-impact work, but this would be a natural extension of the `ivy.rfc.*` category.

### E5: Inconsistent test file include sets — FUTURE CONSIDERATION

Three distinct include patterns in QUIC test files (base delegation, standard full, standard + transport parameters). The variation is intentional for existing tests. Deeper investigation found that the `.ivyworkspace` v3 schema and `workspace_groups` configuration could support a per-test-type "expected include set" declaration. Not promoted because the configuration burden is high (each test type needs its expected set defined), but the infrastructure exists for future implementation.

### E6: Unused state variables — PROMOTED TO D11

Initially excluded as too expensive. Deeper investigation revealed the requirement graph already tracks READS/WRITES edges via `wire_state_var_edges()`, and `coverage_hints.py` has 80% of the infrastructure needed. A `StateVarNode` with no incoming or outgoing edges is unused. Promoted to diagnostic D11 (`ivy.state.unusedStateVar`), approximately 15 LOC.

### E7: Orphaned monitor hooks — PROMOTED TO D12

Initially excluded due to zero instances found and high false-positive risk. Deeper investigation revealed the requirement graph's `populate_actions_from_symbols()` silently backfills placeholder nodes for monitor targets (lines 503-513), masking the diagnostic signal. Checking whether a monitor's target action has a real symbol definition (vs backfill-only placeholder) is trivially implementable and would catch typos at edit time rather than compilation time. Promoted to diagnostic D12 (`ivy.monitor.orphanedHook`), approximately 25 LOC.

### E8: Cross-protocol contamination in MiniP — FUTURE CONSIDERATION

Initially excluded as an architectural decision beyond LSP scope. Deeper investigation showed the `.ivyworkspace` `depends_on` mechanism already partially enforces protocol boundaries, but the flat staging fallback in `include_resolver.py:479` bypasses layer scoping. A diagnostic warning when an include resolves via flat staging rather than the layer chain would catch contamination. Not promoted because `ivy.include.crossLayer` (D2) already covers the most impactful cases. Revisit if flat staging fallback is retained long-term.

### E9: Require with suspicious constant deviation — FUTURE CONSIDERATION

Initially excluded as a one-off. Deeper investigation strengthened the case significantly: in `quic_packet.ivy`, the same constraint block is repeated 4 times for different packet types. Three blocks use `require pkt.seq_num = last_pkt_num(scid,pkt.ptype) + 0x1` and the fourth (line 1295) uses `+ 0x15`. All 4 blocks have commented-out `+ 0x15` lines above, indicating the migration from `0x15` to `0x1` was applied to 3 of 4 blocks — strongly suggesting a copy-paste miss. Implementing a general "sibling constant deviation" detector requires clone detection (substantial). A narrow regex version (same `require ... + CONST` pattern, supermajority of N-1 blocks agreeing, flag the outlier) would be approximately 60 LOC. Not promoted due to implementation complexity relative to the 10 proposed diagnostics, but the evidence strongly suggests a real bug at `quic_packet.ivy:1295`.
