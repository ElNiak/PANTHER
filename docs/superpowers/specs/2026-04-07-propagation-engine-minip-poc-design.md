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

**Returns for variant type (`ping_frame`):**
```json
{
  "type_name": "ping_frame",
  "kind": "variant",
  "file": "minip_stack/ping_frame.ivy",
  "line": 12,
  "members": [
    {"name": "ping", "tag": 0, "fields": [{"name": "data", "type": "byte"}]},
    {"name": "pong", "tag": 1, "fields": [{"name": "data", "type": "byte"}]},
    {"name": "timestamp", "tag": 2, "fields": [{"name": "time", "type": "microseconds"}]}
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

**Implementation:** Uses existing `detect_variants()` from `pattern_library.py` plus the semantic model's `TypeNode` data. New logic: extracting individual field definitions with their types from the AST (Tier 1) or regex fallback (Tier 3).

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
      "serializer": {"file": "minip_stack/ping_ser.ivy", "class": "ping_ser", "states": 4},
      "deserializer": {"file": "minip_stack/ping_deser.ivy", "class": "ping_deser", "states": 4},
      "instance": {"name": "ping_packet_serdes", "file": "minip_stack/ping_shim.ivy", "line": 18},
      "encoding_base": "ivy_binary_ser_128"
    }
  ]
}
```

**Implementation:** Two-step resolution.
1. Search for `instance X : serdes(<type_name>, ...)` declarations across the protocol. The pattern library's `detect_serdes()` already finds these.
2. From the `serdes` instance, extract the serializer and deserializer object names, then look up their files via the include graph and symbol model.

For BGP (split per-message ser/deser), this returns multiple correlations.

**Timeout:** 30s. **Cost:** low.

### 4.3 `ivy_change_impact`

**Purpose:** Given a type and change category, return the categorized list of files that need modification, split into auto-propagate and manual-review.

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
    {"file": "minip_stack/ping_shim.ivy", "category": "shim", "reason": "check if field affects network I/O"},
    {"file": "minip_stack/ping_endpoint.ivy", "category": "entity", "reason": "check if field needs constraint logic"},
    {"file": "minip_tests/server_tests/ping_server_test.ivy", "category": "test", "reason": "may need test coverage"},
    {"file": "minip_tests/client_tests/ping_client_test.ivy", "category": "test", "reason": "may need test coverage"},
    {"file": "minip_stack/ivy_ping_client_behavior.ivy", "category": "behavior", "reason": "check if field affects behavior"},
    {"file": "minip_stack/ivy_ping_server_behavior.ivy", "category": "behavior", "reason": "check if field affects behavior"}
  ]
}
```

**Implementation:** Combines `ivy_serdes_correlation` output (ser/deser files) with include graph traversal (which files include the type's file, transitively) and pattern-based categorization (the pattern library classifies files as SHIM, ENTITY, MONITOR, etc.). Auto-propagate contains only type definitions and their correlated ser/deser. Everything else goes to manual-review.

**Timeout:** 60s. **Cost:** medium.

### Auto-propagate vs Manual-review Split

The split is the key design choice. For `add_field`: only the type definition and its correlated ser/deser are auto-propagated. For `add_variant`: only the variant type definition and the ser/deser `open_tag` dispatch are auto-propagated. Everything else (shims, tests, behavior, entities) goes to manual review because the research showed those edits require protocol-level judgment.

## 5. Propagation Skill

A single skill `propagation-patterns` in the panther-ivy-plugin's `skills/` directory. Protocol-agnostic; references analysis tool output rather than hardcoding protocol specifics.

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

The skill includes a concrete before/after example showing the exact diff for adding `seq_num : byte` to `ping_packet`.

### 5.3 Add-Variant Pattern

1. **Variant type definition file:** Add `object {variant_name} = {type this = struct { ... }}` as a new variant member.
2. **Serializer `open_tag()`:** Add a new `case` for `tag == N` that sets `frame_type` to the wire type code and transitions to the variant's initial state. Add the variant's field states to the enum and `set()`.
3. **Deserializer `open_tag()`:** Add a new `if (frame_type == 0xNN)` branch that transitions to the variant's initial state and returns the tag index. Add the variant's field states to `get()`.
4. **Tag index rule:** Must be the next sequential integer after the last existing variant. The WARNING at `quic_frame.ivy:45` mandates that variant tag order match `open_tag` integer values.

The skill includes a concrete example showing the diff for adding an `error` frame variant to `ping_frame`.

### 5.4 Ser/Deser Asymmetry Warnings

Explicit callouts encoded in the skill:
- Serializer and deserializer are NOT mirrors. Always read both files before editing either.
- Check for byte-order handling (`reverse_bytes`) in the existing deser. Apply the same convention to new fields.
- State counts may differ between ser and deser (QUIC: 55 vs 53).
- The `data_remaining` counter management differs between ser and deser for variable-length fields.

### 5.5 What NOT to Auto-Edit

The skill explicitly instructs Claude to skip these file categories:
- Test files: flag for manual review
- Behavior/constraint files: flag for manual review
- Shim files: flag for manual review (the `serdes` instance declaration does not change for field additions)
- Entity files: flag for manual review

## 6. `/nct-propagate` Command

A new command at `commands/nct-propagate.md` in the panther-ivy-plugin.

### 6.1 User Interaction Flow

**Step 1 — Input.** User invokes `/nct-propagate` and describes the change:
- "Add a `seq_num : byte` field to `ping_packet` after `payload`"
- "Add an `error` frame variant to `ping_frame` with `error_code : byte`"

The command parses this into: `{type_name, change_type, field_spec or variant_spec, position}`.

**Step 2 — Analysis.** Call ivy-lsp tools:
1. `ivy_find_variants` — current type structure
2. `ivy_serdes_correlation` — ser/deser file mapping
3. `ivy_change_impact` — categorized file list

**Step 3 — Plan presentation.** Present the propagation plan:
```
Propagation plan for: add field `seq_num : byte` to `ping_packet`

Auto-propagate (3 files):
  1. minip_stack/ping_packet.ivy — add field to struct
  2. minip_stack/ping_ser.ivy — add state + set() case
  3. minip_stack/ping_deser.ivy — add state + get() case

Manual review needed (6 files):
  - ping_shim.ivy, ping_endpoint.ivy, ping_server_test.ivy,
    ping_client_test.ivy, ivy_ping_client_behavior.ivy,
    ivy_ping_server_behavior.ivy

Proceed? (y/n)
```

**Step 4 — Execution.** For each file in `auto_propagate`, in order:
1. Read file via `ReadFileTool` (panther-serena)
2. Store `{file_path, original_content}` in transaction log
3. Claude generates the specific edit (guided by propagation skill)
4. Present proposed diff to user for approval
5. On approval, apply via `ReplaceContent` or `InsertAtLine` (panther-serena)

**Step 5 — Validation.** After all edits:
1. Call `ivy_compile` on MiniP test file
2. Success: report + print manual-review list
3. Failure: report error, ask user whether to revert or keep for debugging

**Step 6 — Revert (on failure).** For each entry in transaction log (reverse order):
1. Write back original content via panther-serena
2. Confirm file matches original

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

Pytest tests inside ivy-lsp's test suite, using real MiniP `.ivy` files as fixtures:

- `ivy_find_variants("ping_frame")` returns exactly 3 variants with correct tags, fields, types
- `ivy_find_variants("ping_packet")` returns struct with 1 field
- `ivy_serdes_correlation("ping_packet")` returns `ping_ser.ivy` + `ping_deser.ivy` + `serdes` instance in `ping_shim.ivy`
- `ivy_change_impact("ping_packet", "add_field")` returns 3 auto-propagate + 6 manual-review files
- `ivy_change_impact("ping_frame", "add_variant")` returns 3 auto-propagate files

### 7.2 End-to-End Propagation Test (integration)

Runs in an isolated Git worktree copy of MiniP:

1. Start from clean MiniP state
2. Run propagation: "add `seq_num : byte` to `ping_packet`"
3. Verify: 3 files modified, `ivyc` compilation passes
4. Revert via transaction log
5. Verify: all 3 files match originals
6. Run propagation: "add `error` variant to `ping_frame` with `error_code : byte`"
7. Verify: 3 files modified, `ivyc` compilation passes

### 7.3 Revert Test (integration)

1. Introduce a deliberately bad edit (wrong byte count in serializer)
2. Verify `ivyc` compilation fails
3. Trigger revert
4. Verify all files match pre-propagation state

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
| 4 | Tool registration | `ivy-lsp/ivy_lsp/mcp/tools/__init__.py` | Edit |
| 5 | `propagation-patterns` skill | `panther-ivy-plugin/.claude-plugin/skills/propagation-patterns/` | New directory |
| 6 | `/nct-propagate` command | `panther-ivy-plugin/.claude-plugin/commands/nct-propagate.md` | New file |
| 7 | Tool unit tests | `ivy-lsp/tests/test_propagation_tools.py` | New file |
| 8 | Integration tests | `ivy-lsp/tests/test_propagation_e2e.py` | New file |

## 10. Dependencies

- ivy-lsp's semantic model and pattern library must successfully index MiniP (verified: `.ivy-index/` exists for QUIC, needs verification for MiniP)
- panther-serena must be running and reachable via MCP (gated by `PANTHER_IVY_ENABLE_SERENA=1`)
- `ivyc` must be installed and accessible for compilation validation
- MiniP `.ivy` files must be in a compilable state before propagation
