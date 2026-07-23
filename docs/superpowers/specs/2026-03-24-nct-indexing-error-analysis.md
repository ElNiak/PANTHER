# NCT Indexing Error Analysis — Deleted APT Fork Files

**Date**: 2026-03-24
**Branch**: `production` (worktree: `lsp-to-claude`)
**Scope**: Analysis of `ivy-lsp index --all --force` errors, identification of mis-deleted files, and restoration plan

---

## 1. Executive Summary

Running `ivy-lsp index --all --force` on the PANTHER Ivy workspace produces **314 Tier 1 (AST parser) failures out of 1007 files** (31.2%), forcing fallback to the less accurate Tier 2 (PLY lexer) parser. The majority of these failures originate from **files that were deleted from the APT protocol fork** while still being actively referenced by other APT files via `include` statements.

**Root cause**: Three `.ivy` files were deleted from the APT fork across two commits, but the `include` references to them were either not updated or were changed to cross-protocol references that the per-protocol indexer cannot resolve.

**Required actions**:
- **Restore 3 deleted files** (+ 1 `.md` companion)
- **Revert 34 `.ivy` files** that had `include apt_time` changed to `include quic_time`
- **Review 1 file** (`quic_types.ivy`) for a related addition

**Secondary issue**: The indexer's `build_protocol()` function at `index_builder.py:121` creates per-protocol `IncludeResolver` instances without passing `workspace_layers`, preventing cross-protocol resolution even when legitimately needed. This is documented but not addressed by the file restorations.

---

## 2. NCT Workspace Model

### Self-Contained Workspace Principle

Each protocol directory under `protocol-testing/` must be **self-contained**. The Ivy compiler (`ivyc`) works in a single flat directory — PANTHER's Docker build process copies all relevant `.ivy` files into `$PYTHON_IVY_DIR/ivy/include/1.7/` before compilation. The `ivy-lsp` indexer mirrors this by processing each protocol independently.

### Indexing Pipeline

```
ivy-lsp index --all --force
  → detect_ivy_workspace() → loads .ivyworkspace (12 layers with depends_on)
  → IndexBuilder.build_all()
    → for each protocol-testing/*/:
        → build_protocol(protocol_dir)
          → IncludeResolver(include_paths=[protocol_rel])  ← only current protocol
          → create_staging_directory()                      ← flat symlinks of protocol files
          → TieredExtractor(resolve_callback=resolver.resolve)
            → Tier 1 (AST/Z3): full parser, needs all includes resolvable
            → Tier 2 (PLY lexer): token-based, no include resolution
            → Tier 3 (regex): pattern matching, always succeeds
```

### APT Fork Architecture

APT (Advanced Persistent Threat testing) maintains **forked copies** of base protocols:

```
protocol-testing/apt/
├── apt_entities/          # APT-specific entity roles (attacker, bot, c2_server, target, mim)
├── apt_entities_behavior/ # Behavioral constraints for APT entities
├── apt_lifecycle/         # 6-stage APT lifecycle (recon, infiltration, c2, privesc, persist, exfil)
├── apt_network/           # Network-level APT abstractions (apt_time.ivy lived here)
├── apt_shims/             # Bridge between APT model and implementations
├── apt_stack/             # Core APT model
├── apt_utils/             # Shared utilities
├── apt_protocols/         # FORKED copies of base protocols
│   ├── quic/              # Modified QUIC model for APT context
│   ├── minip/             # Modified MiniP model for APT context
│   └── tls/               # Modified TLS model for APT context
└── apt_tests/             # APT test specifications
```

Each forked protocol (`apt_protocols/quic/`, `apt_protocols/minip/`) must contain all files needed to compile — it cannot reference files from the standard protocol directories.

---

## 3. Per-Protocol Analysis

| Protocol | Files | Tier 1 OK | Tier 1 Fail | % OK | Primary Missing Modules |
|----------|-------|-----------|-------------|------|------------------------|
| **apt** | 326 | ~204 | ~244 | 62% | `quic_frame` (276 errors), `quic_time` (120), `ping_byte_stream` (20) |
| **quic** | 201 | ~388 | ~16 | 96% | `ivy_quic_attacker_client` (16), `ping_file` (8), `tls_intf` arity (2) |
| **coap** | 36 | ~28 | ~34 | 45% | `byte_stream` (12), `random_value` (4) |
| **patterns** | 13 | ~6 | ~20 | 23% | `byte_stream` (4), template errors |
| **bgp** | 39 | all | 0 | 100% | None |
| **minip** | 19 | all | 0 | 100% | None |
| **new_prot** | 10 | N/A | 0 | N/A | No test files |
| **http** | 0 | — | — | — | Empty directory |
| **system** | 0 | — | — | — | Empty directory |

**Notes**: Error counts are from log analysis and may include cascading errors (one missing module causes multiple files to fail). Tier 1 counts include staging duplicates from the indexer's two-pass approach.

---

## 4. Deleted Files Inventory

### 4.1 Commit `78ef4c80` (2026-03-18) — "resolve workspace diagnostics"

This commit intended to "delete redundant" files and "standardize 68 APT files on quic_time." However, the APT fork requires its own copies because each workspace must be self-contained.

#### Deleted: `quic_frame.ivy` and `quic_frame.md`

- **Path**: `protocol-testing/apt/apt_protocols/quic/quic_stack/quic_frame.ivy`
- **Size**: 206 lines (`.ivy`) + 281 lines (`.md`)
- **Originally added**: Commits `0ca33e57` / `507779d1` ("fix bugs on atp")
- **Content**: QUIC frame type definitions (STREAM, ACK, CRYPTO, etc.) — the APT fork's version

**Files still referencing `include quic_frame`** (10 `.ivy` files in APT):

| File | Line |
|------|------|
| `apt_protocols/quic/quic_stack/quic_connection.ivy` | 41 |
| `apt_protocols/quic/quic_stack/quic_packet.ivy` | 7 |
| `apt_protocols/quic/quic_stack/quic_packet_0rtt.ivy` | 5 |
| `apt_protocols/quic/quic_stack/quic_packet_coal_0rtt.ivy` | 5 |
| `apt_protocols/quic/quic_stack/quic_packet_retry.ivy` | 5 |
| `apt_protocols/quic/quic_stack/quic_packet_vn.ivy` | 5 |
| `apt_protocols/quic/quic_recovery/quic_loss_recovery.ivy` | 6 |
| `apt_lifecycle/quic_apt_lifecycle/malicious_quic_frame.ivy` | 3 |

**Cascading impact**: `quic_frame` is included by `quic_connection`, `quic_packet`, etc., which are in turn included by shims, entities, and tests → **~276 Tier 1 failures**.

#### Deleted: `apt_time.ivy`

- **Path**: `protocol-testing/apt/apt_network/apt_time.ivy`
- **Size**: 30 lines
- **History**: Originally existed as `apt_protocols/quic/quic_utils/quic_time.ivy` → renamed to `apt_network/apt_time.ivy` in `235d090a` (2024-06-05) → deleted in `78ef4c80` (2026-03-18)
- **Content**: Time abstraction for APT protocol model

**What was changed instead**: 34 `.ivy` files + 34 `.md` files had `include apt_time` replaced with `include quic_time`. Since `quic_time.ivy` only exists in `protocol-testing/quic/quic_utils/`, this cross-protocol reference breaks the indexer and would break `ivyc` compilation within the APT workspace.

### 4.2 Commit `5e243284` (2024-07-22) — "using packet object"

#### Deleted: `ping_byte_stream.ivy`

- **Path**: `protocol-testing/apt/apt_protocols/minip/minip_stack/ping_byte_stream.ivy`
- **Size**: 22 lines
- **Content**: Byte stream abstraction for MiniP protocol in APT context
- **Same commit added**: `ping_frame_v_random.ivy` (141 lines) — likely a replacement, but the include reference was not updated

**File still referencing `include ping_byte_stream`**:

| File | Line |
|------|------|
| `apt_protocols/minip/minip_stack/ping_application.ivy` | 3 |

### 4.3 Related Change: `quic_types.ivy` Addition

Commit `78ef4c80` added 2 lines to `apt_protocols/quic/quic_stack/quic_types.ivy`:

```ivy
+relation zero_rtt_allowed
```

This may have been added to compensate for something previously defined in `quic_frame.ivy`. **Needs review** when restoring `quic_frame.ivy` — check if `zero_rtt_allowed` is defined in the restored `quic_frame.ivy` to avoid duplication.

---

## 5. Include Changes to Revert

### 5.1 Files Requiring `include quic_time` → `include apt_time` Revert

All 34 `.ivy` files below had `include apt_time` changed to `include quic_time` in commit `78ef4c80`. Since `apt_time.ivy` is being restored, these must be reverted:

**APT Shims (2 files)**:
1. `protocol-testing/apt/apt_shims/apt_shim.ivy` (line 12)
2. `protocol-testing/apt/apt_shims/stream_data/ivy_stream_data_shim.ivy`

**APT Protocol MiniP (3 files)**:
3. `protocol-testing/apt/apt_protocols/minip/minip_entities/ping_client.ivy`
4. `protocol-testing/apt/apt_protocols/minip/minip_entities/ping_server.ivy`
5. `protocol-testing/apt/apt_protocols/minip/minip_stack/ping_frame.ivy`

**APT Protocol QUIC — Entities/Shims (5 files)**:
6. `protocol-testing/apt/apt_protocols/quic/quic_entities_behavior/ivy_quic_n_clients_behavior.ivy`
7. `protocol-testing/apt/apt_protocols/quic/quic_shims/quic_shim.ivy`
8. `protocol-testing/apt/apt_protocols/quic/quic_shims/quic_shim_example_ext.ivy`
9. `protocol-testing/apt/apt_protocols/quic/quic_shims/todo/quic_shim_mim.ivy`
10. `protocol-testing/apt/apt_protocols/quic/quic_shims/todo/quic_shim_multiple_client.ivy`

**APT Protocol QUIC — Client Tests (8 files)**:
11. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test.ivy`
12. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test_deadconnection.ivy`
13. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test_deadconnection_no_sleep.ivy`
14. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test_deadconnection_no_sleep_validation.ivy`
15. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test_deadconnection_signal.ivy`
16. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test_ext_min_ack_delay.ivy`
17. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test_timeout.ivy`
18. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test_timeout_no_sleep.ivy`
19. `protocol-testing/apt/apt_protocols/quic/quic_tests/client_tests/quic_client_test_timeout_no_sleep_validation.ivy`

**APT Protocol QUIC — Server Tests (13 files)**:
20. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test.ivy`
21. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_deadconnection.ivy`
22. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_deadconnection_no_sleep.ivy`
23. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_deadconnection_no_sleep_migration.ivy`
24. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_deadconnection_no_sleep_validation.ivy`
25. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_deadconnection_signal.ivy`
26. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_ext_min_ack_delay.ivy`
27. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_ext_min_ack_delay_example.ivy`
28. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_timeout.ivy`
29. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_timeout_no_sleep.ivy`
30. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_timeout_no_sleep_migration.ivy`
31. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_timeout_no_sleep_validation.ivy`
32. `protocol-testing/apt/apt_protocols/quic/quic_tests/server_tests/quic_server_test_version_negociation_ext.ivy`

**APT Tests (3 files)**:
33. `protocol-testing/apt/apt_tests/attacker_server_tests/minip_attacker_server_test_bo.ivy`
34. `protocol-testing/apt/apt_tests/attacker_server_tests/minip_attacker_server_test_flood.ivy`

Plus corresponding `.md` companion files (34 more files).

### 5.2 Changes in `78ef4c80` That Should NOT Be Reverted

These were valid fixes for real issues:

| Change | Files | Reason to Keep |
|--------|-------|----------------|
| `include endpoint` → `include apt_quic_endpoint` / `include apt_minip_endpoint` | 7 | Fixed phantom include — `endpoint.ivy` doesn't exist |
| `include ivy_stream_data_attacker` → split into `_client` / `_server` | 2 | Fixed phantom include — unsplit version doesn't exist |
| `include ivy_minip_attacker` → split into `_client` / `_server` | 1 | Fixed phantom include |
| Remove `include ivy_system_shim` | 1 | Dead code removal |
| Rename `attack_exflitration` → `attack_exfiltration` | 2 | Typo fix |
| `quic_shim.ivy` — remove 1 line | 1 | Unrelated cleanup |

### 5.3 APT Tests With `apt_time` → `quic_time` Change

The attacker test files in `apt_tests/attacker_server_tests/` also had this change but via a different include chain. These 12 files were also changed:

35-46. All `quic_attacker_server_test_*.ivy` files (10 files) + `minip_attacker_server_test_*.ivy` (2 files) — see full list in git diff output above.

**Plus 2 MIM test files**:
47. `protocol-testing/apt/apt_tests/mim_tests/minip_mim_test_delay.ivy`
48. `protocol-testing/apt/apt_tests/mim_tests/stream_data_mim_test_forward.ivy`

---

## 6. Root Cause: Code Path Trace

### 6.1 Why the Indexer Fails

When `ivy-lsp index --all` processes the APT protocol:

```
build_protocol("protocol-testing/apt")
  → IncludeResolver(include_paths=["protocol-testing/apt"])   ← only APT dir
  → create_staging_directory()                                  ← symlinks only APT files
  → TieredExtractor.extract("apt_shim.ivy")
    → Tier 1 parser encounters: include quic_time
    → _lsp_importer("quic_time") calls resolver.resolve()
      → Step 1: same-dir check → apt_shims/quic_time.ivy NOT FOUND
      → Step 2: layer staging → EMPTY (no workspace_layers passed to resolver)
      → Step 3: flat staging → only APT files in staging dir
      → Step 4: workspace root → protocol-testing/quic_time.ivy NOT FOUND
      → Step 5: stdlib → ivy/include/1.7/quic_time.ivy NOT FOUND
      → Returns None
    → IvyError("module quic_time.ivy not found")
    → Tier 1 FAILS → falls back to Tier 2 (PLY lexer)
```

### 6.2 The Indexer Bug (Secondary Issue)

At `index_builder.py:118-122`, the `IncludeResolver` is created without `workspace_layers`:

```python
resolver = IncludeResolver(
    workspace_root=self.workspace_root,
    exclude_paths=self.workspace_config.exclude_paths,
    include_paths=[protocol_rel],          # ← only current protocol
    # workspace_layers NOT PASSED           # ← missing parameter
)
```

The `.ivyworkspace` file declares `apt_core depends_on ["quic", "minip"]`, and the `IncludeResolver.__init__()` at `include_resolver.py:142` accepts a `workspace_layers` parameter. But `build_protocol()` never passes it. Even `build_layered_staging()` (called at line 127) returns early because the resolver has no layers.

This bug means **even legitimate cross-protocol includes would fail** during indexing. However, per the self-contained workspace principle, cross-protocol includes should be avoided by maintaining forked copies.

---

## 7. Impact Assessment: What Tier 2 Loses

| Capability | Tier 1 (AST Parser) | Tier 2 (PLY Lexer) |
|------------|--------------------|--------------------|
| Symbol names | Full + qualified (e.g., `quic_packet_type.initial`) | Basename only |
| Parameter types | Extracted from AST | Not available |
| Scope nesting | Accurate (module/object/isolate boundaries) | Flat (file-level only) |
| Include resolution | Full chain via resolve callback | Regex match only |
| Call relationships | From AST (who calls whom) | Not available |
| Expression trees | Full Z3-compatible AST | Not available |
| Local variables | Extracted from AST | Not available |
| Confidence | ~95%+ | ~30-50% |

**LSP features degraded when Tier 2 is used**:
- **Hover**: No parameter type information
- **Go-to-definition**: Less accurate, may miss nested symbols
- **Rename**: Unsafe — cannot determine scope boundaries
- **Completion**: No type-aware suggestions
- **Diagnostics**: Cannot detect type mismatches or arity errors

---

## 8. File Comparison: Standard vs APT Fork

### 8.1 QUIC Stack (`quic_stack/`)

| File | Standard QUIC | APT Fork | Status |
|------|:---:|:---:|--------|
| `quic_application.ivy` | ✓ | ✓ | Present |
| `quic_connection.ivy` | ✓ | ✓ | Present |
| **`quic_frame.ivy`** | ✓ | **✗** | **DELETED — RESTORE** |
| `quic_h3_error_code.ivy` | ✓ | ✗ | Not in APT (intentional — HTTP/3 not used in APT) |
| `quic_packet.ivy` | ✓ | ✓ | Present |
| `quic_packet_0rtt.ivy` | ✓ | ✓ | Present |
| `quic_packet_coal_0rtt.ivy` | ✓ | ✓ | Present |
| `quic_packet_retry.ivy` | ✓ | ✓ | Present |
| `quic_packet_stateless_reset.ivy` | ✓ | ✓ | Present |
| `quic_packet_vn.ivy` | ✓ | ✓ | Present |
| `quic_protection.ivy` | ✓ | ✓ | Present |
| `quic_security.ivy` | ✓ | ✓ | Present |
| `quic_stream.ivy` | ✓ | ✓ | Present |
| `quic_transport_error_code.ivy` | ✓ | ✓ | Present |
| `quic_transport_parameters.ivy` | ✓ | ✓ | Present |
| `quic_types.ivy` | ✓ | ✓ | Present (APT has `+relation zero_rtt_allowed`) |

### 8.2 QUIC Utils (`quic_utils/`)

The APT QUIC utils have **diverged significantly** from standard QUIC — APT has additional serializer/deserializer variants for encrypted packets. Key missing files:

| File | Standard QUIC | APT Fork | Status |
|------|:---:|:---:|--------|
| `quic_locale.ivy` | ✓ | ✗ | Replaced by `quic_random_value.ivy` in APT |
| **`quic_time.ivy`** | ✓ | **✗** | **DELETED** — covered by `apt_time.ivy` restoration |
| `random_value.ivy` | ✓ | ✗ | APT uses `quic_random_value.ivy` instead |

### 8.3 MiniP Stack (`minip_stack/`)

The APT MiniP fork is substantially smaller than standard MiniP — many files were never added (design choice, not deletions):

| File | Standard MiniP | APT Fork | Status |
|------|:---:|:---:|--------|
| **`ping_byte_stream.ivy`** | ✓ | **✗** | **DELETED — RESTORE** |
| `ping_frame_v_random.ivy` | ✗ | ✓ | APT-only addition |
| `ivy_ping_client_behavior.ivy` | ✓ | ✗ | Never added (design choice) |
| `ivy_ping_server_behavior.ivy` | ✓ | ✗ | Never added |
| `ping_client.ivy` | ✓ | ✗ | Never added |
| `ping_deser.ivy` | ✓ | ✗ | Never added |
| `ping_endpoint.ivy` | ✓ | ✗ | Never added |
| `ping_ser.ivy` | ✓ | ✗ | Never added |
| `ping_server.ivy` | ✓ | ✗ | Never added |
| `ping_shim*.ivy` (4 files) | ✓ | ✗ | Never added |
| `ping_time.ivy` | ✓ | ✗ | Never added |

---

## 9. Recommendations

### Phase 1: Restore Deleted Files (Immediate)

**Action 1**: Restore `quic_frame.ivy` and `quic_frame.md` from commit `78ef4c80^`:
```bash
cd panther/plugins/services/testers/panther_ivy
git show 78ef4c80^:protocol-testing/apt/apt_protocols/quic/quic_stack/quic_frame.ivy \
  > protocol-testing/apt/apt_protocols/quic/quic_stack/quic_frame.ivy
git show 78ef4c80^:protocol-testing/apt/apt_protocols/quic/quic_stack/quic_frame.md \
  > protocol-testing/apt/apt_protocols/quic/quic_stack/quic_frame.md
```

**Action 2**: Restore `apt_time.ivy` from commit `78ef4c80^`:
```bash
git show 78ef4c80^:protocol-testing/apt/apt_network/apt_time.ivy \
  > protocol-testing/apt/apt_network/apt_time.ivy
```

**Action 3**: Restore `ping_byte_stream.ivy` from commit `5e243284^`:
```bash
git show 5e243284^:protocol-testing/apt/apt_protocols/minip/minip_stack/ping_byte_stream.ivy \
  > protocol-testing/apt/apt_protocols/minip/minip_stack/ping_byte_stream.ivy
```

**Action 4**: Revert `include quic_time` → `include apt_time` in 34 `.ivy` files + 34 `.md` files:
```bash
# For each file, change 'include quic_time' back to 'include apt_time'
find protocol-testing/apt -name "*.ivy" -exec grep -l "include quic_time" {} \; | \
  xargs sed -i '' 's/include quic_time/include apt_time/g'
find protocol-testing/apt -name "*.md" -exec grep -l "include quic_time" {} \; | \
  xargs sed -i '' 's/include quic_time/include apt_time/g'
```

**Action 5**: Review `quic_types.ivy` — check if `relation zero_rtt_allowed` is also defined in the restored `quic_frame.ivy`. If so, remove the duplicate from `quic_types.ivy`.

### Phase 2: Validation

Re-run the indexer and verify APT's Tier 1 success rate improves:
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
PYTHONPATH="." IVY_LSP_LOG_LEVEL=DEBUG python -m ivy_lsp index --all --force 2> logs.indexing.post-restore.log
```

**Expected improvement**: APT should go from ~62% Tier 1 success to ~90%+ (the remaining failures would be from other issues like `tls_intf` arity mismatch).

### Phase 3: Future Work

1. **Review remaining APT fork divergences** — the MiniP fork is missing many files. Determine if this causes compilation failures.
2. **Fix indexer `workspace_layers` passthrough** — thread `.ivyworkspace` layer dependencies into `IncludeResolver` for protocols that legitimately need cross-protocol resolution (e.g., CoAP depends on QUIC utilities).
3. **Audit other protocols** — CoAP (45% Tier 1) and Patterns (23% Tier 1) have their own missing module issues unrelated to APT.

---

## 10. Missing Module Inventory

Complete table of every missing module discovered during indexing:

| Missing Module | Actual Location | Referenced By | Error Count | Root Cause | Action |
|---|---|---|---|---|---|
| `quic_frame.ivy` | `quic/quic_stack/` | APT (10 files) | ~276 | Deleted from APT fork in `78ef4c80` | **RESTORE** |
| `quic_time.ivy` | `quic/quic_utils/` | APT (34 files via `include quic_time`) | ~120 | `apt_time.ivy` deleted, includes changed to cross-protocol ref | **RESTORE apt_time.ivy + REVERT includes** |
| `ping_byte_stream.ivy` | `minip/minip_stack/` | APT (`ping_application.ivy`) | ~20 | Deleted from APT minip fork in `5e243284` | **RESTORE** |
| `byte_stream.ivy` | `quic/quic_utils/`, `bgp/bgp_utils/` | CoAP, Patterns | ~16 | Never added to CoAP/Patterns directories | Separate issue |
| `ivy_quic_attacker_client.ivy` | `apt/apt_entities/quic/` | QUIC (attacker tests) | ~16 | Cross-protocol ref from QUIC to APT entity | Separate issue |
| `random_value.ivy` | `quic/quic_utils/`, `bgp/bgp_utils/` | CoAP | ~4 | Never added to CoAP directory | Separate issue |
| `ping_file.ivy` | `minip/minip_stack/`, `apt_protocols/minip/` | QUIC | ~8 | Cross-protocol ref from QUIC to MiniP | Separate issue |
| `tls_intf` (arity) | `quic/tls_stack/` | APT, QUIC | ~4 | Module interface mismatch (wrong arg count) | Code bug |

---

## Appendix: Git Commit History

| Commit | Date | Description | Impact |
|--------|------|-------------|--------|
| `78ef4c80` | 2026-03-18 | "resolve workspace diagnostics" | Deleted `quic_frame.ivy`, `apt_time.ivy`; changed 68 includes |
| `235d090a` | 2024-06-05 | "fix apt refactor + remove old quic model" | Renamed `quic_time.ivy` → `apt_time.ivy`, deleted from APT QUIC utils |
| `5e243284` | 2024-07-22 | "using packet object" | Deleted `ping_byte_stream.ivy` from APT MiniP fork |
| `dbb35619` | — | "fixing ivy legacy errors" | Added `quic_frame.ivy` docs |
| `0ca33e57` / `507779d1` | — | "fix bugs on atp" | Originally added `quic_frame.ivy` to APT fork |
