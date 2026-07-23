# Propagation Engine: MiniP End-to-End Proof of Concept

**Date:** 2026-04-07
**Status:** Design approved, ready for implementation planning
**Prerequisite:** [Problem Analysis](2026-04-07-propagation-engine-problem-analysis.md)
**Scope:** MiniP protocol only. Proves architecture that scales to QUIC/BGP.

---

## 1. Problem

When an Ivy type definition changes, the change must propagate to ser/deser state machines, tests, shims, and behavior files. For MiniP this means 7-10 files; for QUIC it means 96. Today this is entirely manual. This PoC builds and validates an automated propagation pipeline using MiniP as the test case.

## 2. Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Target protocol | MiniP | 19 files, 1,231 lines, 4-state ser/deser. Small enough to complete and validate quickly. |
| Execution mode | Interactive first, designed for headless | All edits go through MCP (panther-serena), not native Claude Code tools. Same flow works in future headless mode. |
| Change types | New scalar field + new frame variant | Together these cover the two most common propagation patterns (struct field and variant dispatch). |
| Validation | Compilation only (`ivyc`) | Formal verification (`ivy_check`) is orthogonal to propagation correctness. Compilation catches structural errors. |
| New tools | 3 new ivy-lsp MCP tools | `ivy_find_variants`, `ivy_serdes_correlation`, `ivy_change_impact`. Analysis-focused, protocol-agnostic. |
| Architecture | Skill-driven | ivy-lsp provides analysis data, skill provides pattern knowledge, Claude generates code, panther-serena executes edits. |
| Rollback | In-memory diff log | Store original file contents before editing. Revert all on compilation failure. No Git commits during propagation. |

## 3. System Architecture

Four layers, each with one responsibility:

### Layer 1 — Analysis (ivy-lsp, read-only)

Three new MCP tools compute what needs to change. They return structured JSON. They never modify files. They build on ivy-lsp's existing semantic model, include graph, and pattern library.

### Layer 2 — Pattern Knowledge (propagation skill, panther-ivy-plugin)

A skill that teaches Claude the exact ser/deser patterns: how an Ivy struct field maps to a C++ state machine state, how a frame variant maps to an `open_tag` case, what encoding to use for each Ivy type. Contains measured examples from all protocols. Encodes what the engine should not auto-edit (tests, behavior, shims get flagged for manual review).

### Layer 3 — Orchestration (`/nct-propagate` command, panther-ivy-plugin)

The interactive entry point. Calls analysis tools to build a propagation plan, presents it to the user, manages the transaction log, executes edits through panther-serena, runs `ivyc` compilation, and reverts on failure.

### Layer 4 — Editing (panther-serena, existing tools)

Existing Serena tools (`ReadFileTool`, `ReplaceContent`, `InsertAtLine`, `ReplaceSymbolBody`) handle all file modifications. No new Serena tools needed for the MiniP PoC.

### Data Flow

```
User describes change
  -> /nct-propagate command
    -> ivy_change_impact (ivy-lsp) -> categorized file list
    -> ivy_serdes_correlation (ivy-lsp) -> ser/deser file mapping
    -> ivy_find_variants (ivy-lsp) -> variant definitions (if frame change)
    -> propagation skill -> Claude generates edit plan
    -> User approves plan
    -> For each file in auto_propagate:
        -> ReadFile (serena) -> store original in transaction log
        -> Claude generates code edit (guided by skill)
        -> User approves diff
        -> ReplaceContent/InsertAtLine (serena) -> apply edit
    -> ivy_compile (ivy-lsp) -> validate
    -> Success: report + list manual-review files
    -> Failure: revert all from transaction log, report error
```

## 4. New ivy-lsp MCP Tools

All three tools are registered in a new `mcp/tools/propagation.py` module. All read-only.

### 4.1 `ivy_find_variants`

**Purpose:** Enumerate the structure of a type — struct fields or variant members.

**Parameters:**
- `type_name` (required): e.g., `"ping_frame"` or `"ping_packet"`
- `protocol` (optional): scope to a specific protocol workspace

**Note on Ivy naming:** In Ivy source, types are often named without a protocol prefix. The MiniP frame type is `frame` (not `ping_frame`), and the packet type is `ping_packet`. The `type_name` parameter accepts either the bare Ivy name or a protocol-qualified name; the tool resolves via the semantic model.

**Returns for variant type (`frame`):**
```json
{
  "type_name": "frame",
  "kind": "variant",
  "file": "minip_stack/ping_frame.ivy",
  "line": 12,
  "members": [
    {"name": "ping", "tag": 0, "wire_type": "0x01", "fields": [{"name": "data", "type": "stream_data"}]},
    {"name": "pong", "tag": 1, "wire_type": "0x02", "fields": [{"name": "data", "type": "stream_data"}]},
    {"name": "timestamp", "tag": 2, "wire_type": "0x03", "fields": [{"name": "time", "type": "microseconds"}]}
  ]
}
```

**Returns for struct type (`ping_packet`):**
```json
{
  "type_name": "ping_packet",
  "kind": "struct",
  "file": "minip_stack/ping_packet.ivy",
  "line": 14,
  "fields": [
    {"name": "payload", "type": "frame.arr", "is_array": true}
  ]
}
```

**Implementation:** Requires substantial new logic beyond existing `detect_variants()`.

1. **Struct fields:** `detect_variants()` returns `PatternInstance` with a flat `fields` list. New parsing logic must split field declarations by `:`, trim whitespace, and resolve type names. The `TypeNode.variants` list provides variant names but not field data.
2. **Variant members:** The pattern library's `VARIANT_RE` detects `variant this of X = struct { ... }` declarations and returns the parent type name. New logic must: (a) enumerate all `object` blocks nested inside the parent, (b) parse each variant's struct fields, (c) determine member names from the object name (e.g., `object ping` → member name `ping`).
3. **Tag integers:** Tag-to-variant mappings live exclusively in the C++ `open_tag()` implementation inside `<<< impl >>>` blocks. There is no existing extraction path in the semantic model. The tool must use `impl_block_parser.py` to parse the serializer's `open_tag()` method and extract the `tag → frame_type → state` mappings. Tag order is inferred from declaration order in the Ivy source and cross-validated against the `open_tag()` dispatch branches.
4. **Wire type codes:** Extracted from the same `open_tag()` C++ block (e.g., `frame_type = 0x01`).

**Timeout:** 30s. **Cost:** low.

### 4.2 `ivy_serdes_correlation`

**Purpose:** Given a type name, find which ser/deser files handle it and through which `serdes` instance.

**Parameters:**
- `type_name` (required): e.g., `"ping_packet"`
- `protocol` (optional)

**Returns:**
```json
{
  "type_name": "ping_packet",
  "correlations": [
    {
      "serializer": {"file": "minip_stack/ping_ser.ivy", "class": "ping_ser", "base": "ivy_binary_ser_128", "states": 4},
      "deserializer": {"file": "minip_stack/ping_deser.ivy", "class": "ping_deser", "base": "ivy_binary_deser_128", "states": 4},
      "instance": {"name": "ping_packet_serdes", "file": "minip_stack/ping_shim.ivy", "line": 40}
    }
  ]
}
```

**Implementation:** Two-step resolution with known limitations.
1. Search for `instance X : serdes(<type_name>, ...)` declarations across the protocol. The pattern library's `detect_serdes()` already finds these and extracts `ser_name` and `deser_name` from positional args.
2. Resolve ser/deser object names to source files. **Known gap:** C++ class names inside `<<< impl >>>` blocks are not `SymbolNode` entries. Resolution uses the `PatternInstance.file` field from `detect_serdes()`'s class-based serializer detection (matching `SER_BASE_RE` / `DESER_BASE_RE`). If a `ser_name` is not found among detected patterns, the tool returns a structured error indicating the linkage failed.
3. State count comes from the first `EnumState` block found by `impl_block_parser.py`. This is correct for MiniP and BGP (single enum per file) but fragile for protocols with multiple enum blocks.

For BGP (split per-message ser/deser), this returns multiple correlations.

**Timeout:** 30s. **Cost:** low.

### 4.3 `ivy_change_impact`

**Purpose:** Given a type and change category, return the categorized list of files that need modification, split into auto-propagate and manual-review.

**Note:** The broader design doc defines this tool as `ivy_change_impact(file, symbol)`. This PoC supersedes that signature with `(type_name, change_type)` because the propagation engine needs change-type-aware categorization, not generic symbol impact analysis.

**Parameters:**
- `type_name` (required): e.g., `"ping_packet"`
- `change_type` (required): `"add_field"` or `"add_variant"`
- `protocol` (optional)

**Returns:**
```json
{
  "type_name": "ping_packet",
  "change_type": "add_field",
  "auto_propagate": [
    {"file": "minip_stack/ping_packet.ivy", "category": "type_definition", "edit": "add_field_to_struct"},
    {"file": "minip_stack/ping_ser.ivy", "category": "serializer", "edit": "add_state_and_set_case"},
    {"file": "minip_stack/ping_deser.ivy", "category": "deserializer", "edit": "add_state_and_get_case"}
  ],
  "manual_review": [
    {"file": "minip_stack/ping_shim.ivy", "category": "shim", "reason": "contains serdes instance; check if field affects network I/O"},
    {"file": "minip_stack/ping_shim_client.ivy", "category": "shim", "reason": "calls ping_packet_serdes.to_bytes(); check if field affects client send logic"},
    {"file": "minip_stack/ping_shim_server.ivy", "category": "shim", "reason": "calls ping_packet_serdes; check if field affects server receive logic"},
    {"file": "minip_stack/ping_endpoint.ivy", "category": "entity", "reason": "check if field needs constraint logic"},
    {"file": "minip_stack/ping_client.ivy", "category": "entity", "reason": "client entity role definition"},
    {"file": "minip_stack/ping_server.ivy", "category": "entity", "reason": "server entity role definition"},
    {"file": "minip_tests/server_tests/ping_server_test.ivy", "category": "test", "reason": "may need test coverage"},
    {"file": "minip_tests/client_tests/ping_client_test.ivy", "category": "test", "reason": "may need test coverage"},
    {"file": "minip_stack/ivy_ping_client_behavior.ivy", "category": "behavior", "reason": "check if field affects behavior"},
    {"file": "minip_stack/ivy_ping_server_behavior.ivy", "category": "behavior", "reason": "check if field affects behavior"}
  ],
  "unaffected": [
    "minip_stack/ping_types.ivy",
    "minip_stack/ping_byte_stream.ivy",
    "minip_stack/ping_time.ivy",
    "minip_stack/ping_file.ivy",
    "minip_stack/ping_application.ivy",
    "minip_stack/ping_frame.ivy"
  ]
}
```

**Implementation:** Combines `ivy_serdes_correlation` output (ser/deser files) with include graph traversal (which files include the type's file, transitively) and pattern-based categorization (the pattern library classifies files as SHIM, ENTITY, MONITOR, etc.). Auto-propagate contains only type definitions and their correlated ser/deser. Manual-review includes all files that transitively depend on the changed type through the include chain. Unaffected lists files in the protocol that do not depend on the changed type. The tool is authoritative for this classification; the propagation skill defers to it.

**Timeout:** 60s. **Cost:** medium.

### Auto-propagate vs Manual-review Split

The split is the key design choice. For `add_field`: only the type definition and its correlated ser/deser are auto-propagated. For `add_variant`: only the variant type definition and the ser/deser `open_tag` dispatch are auto-propagated. Everything else (shims, tests, behavior, entities) goes to manual review because the research showed those edits require protocol-level judgment.

**Authority rule:** The `ivy_change_impact` tool output is the single source of truth for the auto-propagate/manual-review classification. The propagation skill does not re-classify files. If the tool categorizes a file as manual-review, the skill does not override it to auto-propagate (or vice versa).

## 5. Propagation Skill

A single skill `propagation-patterns` in the panther-ivy-plugin's `skills/` directory. Protocol-agnostic; references analysis tool output rather than hardcoding protocol specifics.

**Note:** The broader design doc names this skill `serdes-generation`. This PoC supersedes that name because the skill covers more than ser/deser generation (it also handles variant dispatch, type definitions, and asymmetry warnings).

### 5.1 Ivy Type-to-C++ Encoding Table

| Ivy Type | Byte Count | Ser Method | Deser Method | State Name Convention |
|---|---|---|---|---|
| `byte` | 1 | `setn(res, 1)` | `getn(res, 1)` | `{prot}_s_{field_name}` |
| `stream_data` / `cid` | variable | byte-by-byte loop via `data_remaining` | byte-by-byte loop via `data_remaining` | `{prot}_s_{field_name}` |
| `microseconds` / timestamp | 8 | `setn(res, 8)` | `getn(res, 8)` + check for `reverse_bytes` | `{prot}_s_{field_name}` |
| `pkt_num` / integer | 1-4 | `setn(res, N)` | `getn(res, N)` | `{prot}_s_{field_name}` |
| `frame.arr` | variable | `open_tag`/`close_tag` dispatch | `open_tag`/`close_tag` dispatch | `{prot}_s_payload` |

### 5.2 Add-Field Pattern

1. **Type definition file:** Add `field_name : ivy_type` to the struct after the specified position.
2. **Serializer:** Add enum state `{prot}_s_{field_name}`. Add `case` in `set()` calling `setn(res, byte_count)` and transitioning to the next state. Update the preceding state's transition target to point to the new state.
3. **Deserializer:** Mirror the serializer but use `getn(res, byte_count)`. Check existing deser for byte-order handling convention (e.g., `reverse_bytes` for multi-byte fields) and apply the same convention.
4. **Hardcoded counters:** Check the deserializer for hardcoded payload length values (e.g., MiniP's `payload_length = 12`) and fixed iteration caps (e.g., `current_ping_size == 5`). Adding a field changes the wire length, so these constants may need updating. `ivyc` compilation will NOT catch incorrect hardcoded values — they are semantic errors, not structural ones. The skill must flag these for the user.

**MiniP concrete example:** In `ping_ser.ivy`, the `ping_s_init` case transitions directly to `ping_s_payload` (line 36: `state = ping_s_payload`). `ping_s_payload` has no `set()` case — it's a sentinel for `open_tag()`/`close_tag()`. To add `seq_num : byte` between packet header and payload:
- Add `ping_s_seq_num` to the enum after `ping_s_init`
- Change `ping_s_init` transition: `state = ping_s_seq_num` (was `ping_s_payload`)
- Add case `ping_s_seq_num`: `setn(res, 1); state = ping_s_payload;`
- In `ping_deser.ivy`: mirror the above, also updating `payload_length` if hardcoded

The skill includes this and a second before/after example for the variant case.

### 5.3 Add-Variant Pattern

1. **Variant type definition file:** Add `object {variant_name} = { variant this of {parent} = struct { ... } }` as a new nested object inside the parent type's object block. Note: Ivy uses `variant this of frame = struct { ... }` syntax, NOT `type this = struct { ... }` for variant members.
2. **Serializer `open_tag()`:** Add a new `case` for `tag == N` that sets `frame_type` to the wire type code and transitions to the variant's initial state. Add the variant's field states to the enum and `set()`.
3. **Deserializer `open_tag()`:** Add a new `if (frame_type == 0xNN)` branch that transitions to the variant's initial state and returns the tag index. Add the variant's field states to `get()`.
4. **Tag index rule:** Must be the next sequential integer after the last existing variant. The WARNING at `quic_frame.ivy:45` mandates that variant tag order match `open_tag` integer values. Cross-validate: the new tag integer in the C++ `open_tag()` must match the variant's declaration order in the Ivy source.
5. **Iteration caps:** Check the deserializer for hardcoded iteration limits (e.g., MiniP's `current_ping_size == 5`). Adding a new variant may require updating these caps if they constrain the number of elements per frame type.

The skill includes a concrete example showing the diff for adding an `error` frame variant to `frame` (in `ping_frame.ivy`).

### 5.4 Ser/Deser Asymmetry Warnings

Explicit callouts encoded in the skill:
- Serializer and deserializer are NOT mirrors. Always read both files before editing either.
- Check for byte-order handling (`reverse_bytes`) in the existing deser. Apply the same convention to new fields.
- State counts may differ between ser and deser (QUIC: 55 vs 53).
- The `data_remaining` counter management differs between ser and deser for variable-length fields.
- **Hardcoded constants:** MiniP's deser has `payload_length = 12` (hardcoded wire length) and `current_ping_size == 5` (iteration cap). These are semantic values that `ivyc` compilation cannot validate. Adding a field or variant may require updating them. The skill must always flag hardcoded integer literals in the deser's `set()`/`get()`/`open_list_elem()` methods for user review.

### 5.5 What NOT to Auto-Edit

The skill defers to `ivy_change_impact`'s classification (see Section 4.3 Authority Rule). It does not independently classify files. Instead, it instructs Claude:
- Only edit files listed in `auto_propagate`. Do not edit files in `manual_review` or `unaffected`.
- For each `manual_review` file, present its `reason` string to the user.
- For hardcoded constants found during editing (e.g., `payload_length`, iteration caps), always warn the user even if the file is in `auto_propagate`.

## 6. `/nct-propagate` Command

A new command at `commands/nct-propagate.md` in the panther-ivy-plugin.

### 6.1 User Interaction Flow

**Step 0 — Workspace.** Ensure ivy-lsp workspace is set to `minip`. Call `ivy_workspace(action="set", target="minip")`. If the workspace is already set, this is a no-op. If the index is stale or missing, call `ivy_index(protocol="minip")` and wait for completion before proceeding.

**Step 1 — Input.** User invokes `/nct-propagate` and describes the change:
- "Add a `seq_num : byte` field to `ping_packet` after `payload`"
- "Add an `error` frame variant to `frame` with `error_code : byte`"

The command parses this into: `{type_name, change_type, field_spec or variant_spec, position}`.

**Step 2 — Analysis.** Call ivy-lsp tools:
1. `ivy_find_variants` — current type structure (validates type exists, determines insertion point)
2. `ivy_serdes_correlation` — ser/deser file mapping
3. `ivy_change_impact` — categorized file list (authoritative for auto-propagate/manual-review split)

**Step 3 — Plan presentation.** Present the propagation plan:
```
Propagation plan for: add field `seq_num : byte` to `ping_packet`

Auto-propagate (3 files):
  1. minip_stack/ping_packet.ivy — add field to struct
  2. minip_stack/ping_ser.ivy — add state + set() case
  3. minip_stack/ping_deser.ivy — add state + get() case

Manual review needed (10 files):
  - ping_shim.ivy, ping_shim_client.ivy, ping_shim_server.ivy,
    ping_endpoint.ivy, ping_client.ivy, ping_server.ivy,
    ping_server_test.ivy, ping_client_test.ivy,
    ivy_ping_client_behavior.ivy, ivy_ping_server_behavior.ivy

WARNING: ping_deser.ivy has hardcoded payload_length=12 and
current_ping_size cap=5 — these may need manual adjustment.

Proceed? (y/n)
```

**Step 4 — Execution.** For each file in `auto_propagate`, in order:
1. Read file via `ReadFileTool` (panther-serena)
2. Store `{file_path, original_content}` in transaction log
3. Claude generates the specific edit (guided by propagation skill)
4. Present proposed diff to user for approval
5. On approval, apply via `ReplaceContent` or `InsertAtLine` (panther-serena)

**Step 5 — Validation.** After all edits:
1. Call `ivy_compile` on `ping_server_test.ivy` (server-side test)
2. If that passes, call `ivy_compile` on `ping_client_test.ivy` (client-side test)
3. Both pass: report success + print manual-review list + print hardcoded-constant warnings
4. Either fails: report the compilation error, ask user whether to revert or keep for debugging

**Step 6 — Revert (on failure or user request).** For each entry in transaction log (reverse order):
1. Write back full original content via `ReplaceContent` (panther-serena) — this tool accepts full-file content replacement
2. Confirm file matches original

### 6.4 Mid-Propagation Rejection

If the user approves file 1's diff but rejects file 2's diff during Step 4:
1. The command asks: "Revert file 1 and abort, or skip file 2 and continue?"
2. **Revert and abort:** Restore file 1 from transaction log, discard the plan.
3. **Skip and continue:** Leave file 1 as edited, skip file 2, proceed to remaining files. At validation (Step 5), compilation may fail due to the incomplete propagation; the revert path handles this.

### 6.2 Transaction Log

In-memory ordered list in the command's execution context:
```
[
  {file: "minip_stack/ping_packet.ivy", original: "<full content>"},
  {file: "minip_stack/ping_ser.ivy", original: "<full content>"},
  {file: "minip_stack/ping_deser.ivy", original: "<full content>"}
]
```

Reverted in reverse order on failure. Discarded on command completion. Not persisted. In future headless mode, the same structure lives in the Agent SDK's execution context.

### 6.3 Per-Diff User Approval

In interactive mode, the user sees and approves each individual diff before it is applied. In future headless mode, this approval gate is removed; the engine applies all edits, validates, and escalates to a human only if compilation fails.

## 7. Testing Strategy

### 7.1 ivy-lsp Tool Tests (unit)

Pytest tests inside ivy-lsp's test suite. Fixtures point to the real MiniP `.ivy` files in `protocol-testing/minip/` via `PANTHER_IVY_PROTOCOL_DIR` environment variable (matching the existing ivy-lsp test pattern). Tests require a pre-built MiniP index.

- `ivy_find_variants("frame")` returns exactly 3 variants with correct tags (0,1,2), wire types (0x01,0x02,0x03), fields, and types
- `ivy_find_variants("ping_packet")` returns struct with 1 field (`payload : frame.arr`)
- `ivy_serdes_correlation("ping_packet")` returns `ping_ser.ivy` + `ping_deser.ivy` + `serdes` instance at `ping_shim.ivy:40`
- `ivy_change_impact("ping_packet", "add_field")` returns 3 auto-propagate + 10 manual-review + 6 unaffected files
- `ivy_change_impact("frame", "add_variant")` returns 3 auto-propagate files (ping_frame.ivy + ping_ser.ivy + ping_deser.ivy)
- **Tag ordering cross-check:** `ivy_find_variants("frame")` tag integers match the `open_tag()` dispatch order in `ping_ser.ivy` and `ping_deser.ivy`

### 7.2 End-to-End Propagation Test (integration)

Runs in an isolated Git worktree created by a pytest fixture. The fixture:
1. Creates a temporary worktree via `git worktree add`
2. Sets `PANTHER_IVY_PROTOCOL_DIR` to the worktree's `protocol-testing/minip/`
3. Builds the MiniP index in the worktree
4. Tears down the worktree after the test (via `git worktree remove`)

Test steps:
1. Start from clean MiniP state
2. Run propagation: "add `seq_num : byte` to `ping_packet`"
3. Verify: 3 files modified, `ivyc` compilation passes on both test files
4. Revert via transaction log
5. Verify: all 3 files match originals
6. Run propagation: "add `error` variant to `frame` with `error_code : byte`"
7. Verify: 3 files modified, `ivyc` compilation passes on both test files

### 7.3 Revert Test (integration)

1. Run a normal propagation (add field) through the pipeline with approval auto-accepted (test mode bypasses the interactive approval gate by providing a callback that always returns True)
2. After successful edit, manually corrupt one file (wrong byte count in serializer)
3. Trigger compilation validation — verify `ivyc` fails
4. Trigger revert
5. Verify all files match pre-propagation state (not just the corrupted file)

### 7.4 Mid-Propagation Rejection Test (integration)

1. Run a propagation with a callback that approves file 1 but rejects file 2
2. Verify the command offers "revert and abort" vs "skip and continue"
3. Choose "revert and abort" — verify file 1 is restored to original
4. Repeat with "skip and continue" — verify file 1 remains edited, file 2 is unchanged, and compilation validation runs (likely fails due to incomplete propagation)

## 8. Scope Boundaries

**In scope:**
- MiniP protocol only
- Interactive mode with per-diff user approval
- Two change types: new scalar field, new frame variant
- Unconditional fixed-length fields only
- 3 new ivy-lsp MCP tools
- 1 new propagation skill
- 1 new `/nct-propagate` command
- Transaction log with revert
- `ivyc` compilation validation

**Out of scope:**
- QUIC, BGP, CoAP (separate design cycle after PoC validates)
- Headless/CI/CD mode (architecture supports it, not shipped in PoC)
- Auto-editing tests, shims, behavior, entities (flagged for manual review)
- Lore trailer integration (Phase 3)
- mcp-server-git (not wired in)
- Formal verification via `ivy_check`
- Conditional field propagation (e.g., QUIC's `long_format`-gated fields)
- Variable-length encoding (varint) validation (skill documents the pattern, PoC only validates with fixed-length)

## 9. Deliverables

| # | Deliverable | Location | Type |
|---|---|---|---|
| 1 | `ivy_find_variants` tool | `ivy-lsp/ivy_lsp/mcp/tools/propagation.py` | New file |
| 2 | `ivy_serdes_correlation` tool | `ivy-lsp/ivy_lsp/mcp/tools/propagation.py` | Same file |
| 3 | `ivy_change_impact` tool | `ivy-lsp/ivy_lsp/mcp/tools/propagation.py` | Same file |
| 4 | Tool registration: `register_propagation_tools()` call + `_TOOL_TIMEOUTS` + `_TOOL_METADATA` entries | `ivy-lsp/ivy_lsp/mcp/tools/__init__.py` | Edit |
| 5 | `propagation-patterns` skill with `SKILL.md` (frontmatter: `name`, `description`) | `panther-ivy-plugin/.claude-plugin/skills/propagation-patterns/SKILL.md` | New directory + file |
| 6 | `/nct-propagate` command | `panther-ivy-plugin/.claude-plugin/commands/nct-propagate.md` | New file |
| 7 | Tool unit tests | `ivy-lsp/tests/test_propagation_tools.py` | New file |
| 8 | Integration tests (e2e + revert + mid-rejection) | `ivy-lsp/tests/test_propagation_e2e.py` | New file |
| 9 | Integration test fixture (Git worktree management) | `ivy-lsp/tests/conftest.py` or `ivy-lsp/tests/fixtures/` | Edit or new |

## 10. Dependencies

- ivy-lsp's semantic model and pattern library must successfully index MiniP (verified: `.ivy-index/` exists for QUIC, needs verification for MiniP — the command's Step 0 handles this)
- panther-serena must be running and reachable via MCP (gated by `PANTHER_IVY_ENABLE_SERENA=1`)
- `ivyc` must be installed and accessible for compilation validation
- MiniP `.ivy` files must be in a compilable state before propagation
- The `apt/apt_protocols/minip/` tree (if present) must be excluded from analysis by ensuring the workspace is set to `minip` (not `apt`) before any tool calls
