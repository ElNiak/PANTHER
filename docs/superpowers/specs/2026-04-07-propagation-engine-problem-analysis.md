# Propagation Engine Problem Analysis

**Date:** 2026-04-07
**Type:** Research Report (facts only, no recommendations)
**Scope:** Ivy formal protocol specifications maintenance burden in PANTHER

---

## 1. Protocol Blast Radius Tables

### 1.1 QUIC: `quic_packet` (96 files, ~28,000 total lines)

| Category | File Count | Total Lines | Example File Path |
|---|---|---|---|
| Type definition (struct) | 1 | 1,695 | `quic_stack/quic_packet.ivy` |
| Type definition (sub-types) | 4 | 1,237 | `quic_stack/quic_packet_0rtt.ivy` |
| Ser/Deser | 10 | 4,177 | `quic_utils/quic_ser.ivy` |
| Test | 59 | ~7,990 | `quic_tests/server_tests/quic_server_test.ivy` |
| Shim | 15 | 5,469 | `quic_shims/quic_shim.ivy` |
| Attack variant | 8 | 2,275 | `quic_attacks_stack/forged_quic_packet.ivy` |
| Config | 1 | 231 | `quic_stack/quic_transport_parameters.ivy` |
| Constraint/Behavior | 9 | 4,583 | `quic_entities_behavior/quic_endpoint.ivy` |
| Utility/Other | 7 | 1,700 | `quic_stack/quic_types.ivy` |

Sub-type files: `quic_packet_0rtt.ivy` (406 lines), `quic_packet_coal_0rtt.ivy` (383), `quic_packet_retry.ivy` (264), `quic_packet_vn.ivy` (184).

Ser/Deser files form 5 matched pairs: main (633+740), forged (197+280), retry (178+270), VN (173+276), 0-RTT (807+623).

### 1.2 QUIC: `quic_frame` (15 direct files, 96 transitive)

| Category | File Count | Total Lines | Example File Path |
|---|---|---|---|
| Type definition | 1 | 2,221 | `quic_stack/quic_frame.ivy` |
| Attack variant | 7 | 2,236 | `quic_attacks_stack/forged_quic_packet.ivy` |
| Constraint/Behavior | 2 | 812 | `quic_stack/quic_connection.ivy` |
| FSM | 1 | 206 | `quic_fsm/quic_fsm_receiving.ivy` |
| Recovery | 1 | 762 | `quic_recovery/quic_loss_recovery.ivy` |
| Stack (packet sub-types) | 5 | 1,932 | `quic_stack/quic_packet.ivy` |

Direct references total ~8,169 lines. The true blast radius equals `quic_packet`'s 96 files because every file using `quic_packet` transitively depends on `quic_frame` through the `payload : frame.arr` field.

An explicit WARNING at `quic_frame.ivy:45` mandates that variant tag order match serializer/deserializer `open_tag` integer values.

### 1.3 BGP (39 files, 4,045 total lines)

Central hub type: `bgp_header_message` (envelope dispatching to 4 sub-message types).

| Category | File Count | Total Lines | Example File Path |
|---|---|---|---|
| Type Definition | 12 | 1,164 | `bgp_stack/bgp_update_message.ivy` (127) |
| Ser/Deser | 10 | 1,353 | `bgp_utils/bgp_ser_update.ivy` (427) |
| Test | 2 | 107 | `bgp_tests/speaker_tests/bgp_speaker_test_join.ivy` |
| Shim | 1 | 158 | `bgp_shims/bgp_shim.ivy` |
| Behavior/Constraint | 1 | 151 | `bgp_entities/ivy_bgp_speaker_behavior.ivy` |
| Entity | 2 | 81 | `bgp_entities/bgp_speaker.ivy` |
| Network | 1 | 143 | `bgp_utils/bgp_network.ivy` |
| Utility | 6 | 297 | `bgp_utils/file.ivy` |
| Config/Type Alias | 2 | 33 | `bgp_utils/bgp_type.ivy` |
| Stub/Empty | 2 | 2 | `bgp_stack/bgp_rib.ivy` |

BGP uses split per-message-type serialization: 5 matched ser/deser pairs (header, open, update, notification, keepalive) with separate `serdes` instances per message type in the shim.

### 1.4 MiniP (19 files, 1,231 total lines)

Core type: `ping_packet` (single `payload : frame.arr` field).

| Category | File Count | Total Lines | Example File Path |
|---|---|---|---|
| Type Definition | 3 | 320 | `minip_stack/ping_packet.ivy` (40) |
| Ser/Deser | 3 | 328 | `minip_stack/ping_ser.ivy` (107) |
| Test | 2 | 62 | `minip_tests/server_tests/ping_server_test.ivy` |
| Shim | 3 | 70 | `minip_stack/ping_shim.ivy` (40) |
| Behavior/Constraint | 2 | 157 | `minip_stack/ivy_ping_client_behavior.ivy` |
| Entity | 3 | 150 | `minip_stack/ping_endpoint.ivy` |
| Utility | 3 | 181 | `minip_stack/ping_file.ivy` |

Single-layer architecture. No connection layer, no attack stack, no TLS/protection.

### 1.5 CoAP (37 files, 3,071 total lines)

Core type: `coap_message` (8 fields).

| Category | File Count | Total Lines | Example File Path |
|---|---|---|---|
| Type Definition | 9 | 585 | `coap_stack/coap_message.ivy` (77) |
| Ser/Deser (CoAP level) | 2 | 0 | `coap_utils/coap_ser.ivy` (EMPTY) |
| Ser/Deser (DTLS level) | 1 | 587 | `dtls_stack/tls_deser_ser.ivy` |
| Entity | 2 | 28 | `coap_entities/ivy_coap_client.ivy` |
| Behavior/Constraint | 3 | 284 | `coap_enntities_behavior/coap_endpoint.ivy` |
| Shim | 3 | 96 | `coap_shim/coap_shim.ivy` |
| Congestion/Network | 3 | 332 | `coap_congestion/coap_retransmission.ivy` |
| DTLS/TLS Stack | 3 | 1,174 | `dtls_stack/tls_record.ivy` |
| Utility | 5 | 302 | `coap_utils/coap_file.ivy` |
| Stub/Empty | 4 | 1 | `coap_stack/coap_multicast.ivy` |

CoAP-level serialization is structurally declared but entirely unimplemented. Both `coap_ser.ivy` and `coap_deser.ivy` are 0-line files. The referenced `coap_ser_deser.h` header does not exist. Only the DTLS transport layer has functional ser/deser.

### 1.6 Cross-Protocol Summary

| Metric | QUIC | BGP | MiniP | CoAP |
|---|---|---|---|---|
| Total .ivy files | 199 | 39 | 19 | 37 |
| Total lines | 40,554 | 4,045 | 1,231 | 3,071 |
| Core type blast radius (files) | 96 | ~25 | ~15 | N/A |
| Ser/Deser files | 10 | 10 | 3 | 3 (2 empty) |
| Ser/Deser lines | 4,177 | 1,353 | 328 | 587 (DTLS only) |
| Max enum states | 55 (ser), 63 (0-RTT ser) | 20 (update) | 4 | N/A (fence-stack) |
| Attack variants | 8 files | 0 | 0 | 0 |
| Test files | 107 total (59 ref quic_packet) | 2 | 2 | 0 |

---

## 2. Ser/Deser Pattern Analysis

### 2.1 QUIC State Machine (Main Pair)

All QUIC ser/deser files are C++ classes embedded via `<<< impl >>>` blocks, inheriting from `ivy_binary_ser_128` / `ivy_binary_deser_128`. They share a common header `quic_utils/quic_ser_deser.h`.

**quic_ser.ivy** (633 lines, 55 states, lines 24-78):
Two-phase state machine:
- Phase 1 (Packet Header, lines 100-153): `quic_s_init` -> `quic_s_version` -> `quic_s_dcid` -> `quic_s_scid` -> `quic_s_retry_token` -> `quic_s_pkt_num` -> `quic_s_payload`
- Phase 2 (Frame Payload, lines 442-572): Entered via `open_tag()` with integer tag (0-26) selecting frame type. Each tag maps to a frame-specific sub-state-machine. `close_tag()` resets to `quic_s_payload`.

**quic_deser.ivy** (740 lines, 53 states, lines 60-114): Mirrors the serializer. Two fewer states (`quic_malicious` and `quic_s_retry_token_length` absent; `quic_s_type` added).

**Conditional fields:**
- `long_format` (determined by `res != 3` at line 103): gates version (4 bytes), DCID/SCID length prefixes, payload length field
- Packet type bits (`hdr_type & 0x30`): gates retry token (Initial only), 1200-byte minimum padding (Initial only)
- STREAM frame bits: OFF bit (`frame_type & 0x04`) gates offset field; LEN bit (`frame_type & 0x02`) gates length field; FIN bit encoded in `frame_type & 0x01`

**Encoding types:**
- Fixed-length: header byte (1B), version (4B), CID length prefix (1B), CID value (8B default), packet number (1-4B from header bits), payload length (2B backpatched), NCID token (16B), AEAD tag (16B)
- Variable-length (varint, RFC 9000 Section 16): stream ID, stream offset/length, crypto offset/length, ACK fields, RESET_STREAM fields, STOP_SENDING fields, CONNECTION_CLOSE fields, MAX_DATA, NCID seq_num/retire_prior_to, ACK_FREQUENCY fields
- Byte-by-byte (`data_remaining` loop): stream data, crypto data, CC reason, retry token, path challenge data, padding

**Struct-to-state-machine coupling:** The `quic_packet` struct field order (`ptype`, `pversion`, `dst_cid`, `src_cid`, `token`, `seq_num`, `payload`) maps 1:1 to the state machine processing order. Adding, removing, or reordering a field requires a corresponding state machine change.

### 2.2 QUIC Variant Ser/Deser Pairs

| Pair | States (ser/deser) | Purpose | Key difference from main |
|---|---|---|---|
| Forged | 10/12 | MitM attack headers | Header-only, no frame payload parsing |
| Retry | 9/9 | Retry packets | Token + integrity tag, no frames |
| VN | 7/8 | Version Negotiation | Version list, no frames |
| 0-RTT | 63/50 | Coalesced Initial+0-RTT | Superset of main, adds `_z` suffixed states for 0-RTT portion |

### 2.3 BGP State Machines

BGP uses per-message-type serializers with separate `serdes` instances:

**Header (bgp_ser/bgp_deser):** 4 states (`bgp_s_init`, `bgp_s_len`, `bgp_s_type`, `bgp_s_payload`). All fields unconditional and fixed-length except payload (variable, length-delimited). Marker=16B, length=2B, type=1B.

**Open (bgp_ser_open/bgp_deser_open):** 8 states. First 5 fields unconditional and fixed-length (version 1B, AS 2B, hold_time 2B, identifier 4B, opt_parm_len 1B). Optional parameters are variable-length, iterated via `open_tag()`/`open_list_elem()` with nested type+length+value structure.

**Update (bgp_ser_update/bgp_deser_update):** 20 states. Most complex BGP ser/deser (427/441 lines). Four sections: withdrawn routes (length-prefixed array), path attributes length (2B), path attribute variants (dispatched via `open_tag()` mapping type codes 0x01-0x07 to attribute-specific states), NLRI (prefix-length + prefix-bytes). Notable asymmetry: serializer uses 0-indexed type codes; deserializer uses 1-indexed hex codes.

**Notification (bgp_ser_notification/bgp_deser_notification):** 3 states (`error_code`, `error_subcode`, `payload`). Unconditional. Ser/deser asymmetry: ser writes data as 8 bytes; deser reads 1 byte at a time.

**Keepalive (bgp_ser_keepalive/bgp_deser_keepalive):** 1 state. Empty struct, no fields to serialize.

### 2.4 MiniP State Machine

**ping_ser.ivy / ping_deser.ivy:** 4 states each (`ping_s_init`, `ping_s_frame`, `ping_s_time`, `ping_s_payload`).

Single-layer: packet has one field (`payload : frame.arr`). Frame variant dispatch via `open_tag()`:
- tag 0 -> type `0x01` (ping), 1 byte data
- tag 1 -> type `0x02` (pong), 1 byte data
- tag 2 -> type `0x03` (timestamp), 8 bytes fixed

Timestamp asymmetry: deser applies `reverse_bytes()` for big-endian to host conversion; ser does not. Deser has a hardcoded `payload_length = 12` and `current_ping_size` cap of 5.

### 2.5 CoAP Ser/Deser

CoAP-level serialization is empty (0 lines). The DTLS layer (`tls_deser_ser.ivy`, 587 lines) uses a fundamentally different architecture: fence-stack model with field name dispatch via `open_field()`/`close_field()` maps instead of enum state machines. Uses deferred-length encoding with backpatching. The referenced `coap_ser_deser.h` header is missing from the repository.

---

## 3. Mechanicality Classification

Hypothetical change: "Add a new fixed-length scalar field to the core type."

### 3.1 QUIC (adding field to `quic_packet`)

| File Category | Edit Description | Classification | Why |
|---|---|---|---|
| Type definition (1 file) | Add field declaration to struct | Mechanical | Field name and type are given; insertion position follows struct convention |
| Sub-type definitions (4 files) | Add same field to sub-type structs | Heuristic | Which sub-types include the field depends on protocol semantics (does 0-RTT have it? Retry? VN?); position must match parent |
| Main ser/deser (2 files) | Add enum state, add `set()`/`get()` case, update state transitions | Heuristic | State name derivable from field name, byte count from type. But insertion position in state order must match struct field order. Encoding choice (fixed vs varint) follows type conventions |
| Variant ser/deser (8 files) | Add state to forged/retry/VN/0-RTT pairs | Judgment | Whether the field appears in each packet variant depends on protocol-level semantics. Forged packets may or may not include it. Retry and VN have different wire formats |
| Test files (59 files) | Add field references, update invariant checks | Judgment | Whether tests need updating depends on whether the field affects testable behavior. Most tests reference `quic_packet` but may not exercise the new field |
| Shim files (15 files) | Update if field affects network I/O, encrypt/decrypt, or connection state | Judgment | Depends on whether the field participates in cryptographic operations, triggers new events, or changes dispatch logic |
| Attack variants (8 files) | Add field to duplicated structs | Mechanical (struct) + Judgment (events) | Struct field addition is mechanical copy-paste. But updating the duplicated event specification requires understanding what constraints the field introduces for attack scenarios |
| Config (1 file) | Update if field is a transport parameter | Judgment | Whether the field is a negotiated parameter depends on RFC semantics |
| Constraint/Behavior (9 files) | Add invariants and constraints on new field | Judgment | Requires understanding of protocol state machine, what values are valid, when the field is set/read, and how it interacts with existing fields |
| Utility/Other (7 files) | Rarely need changes | Mechanical or N/A | Only if field introduces a new base type not already in `quic_types.ivy` |

Summary: Of the ~96 affected files, approximately 3 files (type definition + main ser + main deser) involve mechanical or heuristic edits. The remaining ~93 files range from heuristic to full judgment depending on the field's protocol semantics.

### 3.2 BGP (adding field to `bgp_update_message`)

| File Category | Edit Description | Classification | Why |
|---|---|---|---|
| Type definition (1 file) | Add field to struct | Mechanical | Given |
| bgp_ser_update (1 file) | Add state, `set()` case | Heuristic | Position in state order must match struct. Encoding follows BGP conventions (fixed-length for most fields) |
| bgp_deser_update (1 file) | Add state, `get()` case | Heuristic | Mirror of serializer |
| Outer ser/deser (2 files) | No change needed | N/A | Envelope handles marker/length/type only; inner payload is opaque |
| Other message ser/deser (6 files) | No change needed | N/A | Per-message-type split means only the UPDATE pair is affected |
| Shim (1 file) | Likely no change | N/A | Shim instantiates `serdes` instance; no field-level logic |
| Tests (2 files) | Update if tests reference field | Judgment | Depends on semantics |
| Behavior (1 file) | Add constraints | Judgment | Protocol understanding needed |

Summary: 3 files mechanical/heuristic (type + ser + deser), 3 files judgment (tests + behavior), 24 files unaffected. BGP's split ser/deser architecture localizes changes to the specific message type.

### 3.3 MiniP (adding field to `ping_packet`)

| File Category | Edit Description | Classification | Why |
|---|---|---|---|
| Type definition (1 file) | Add field to struct | Mechanical | Given |
| ping_ser (1 file) | Add state, `set()` case | Heuristic | Position in state order; encoding type |
| ping_deser (1 file) | Add state, `get()` case | Heuristic | Mirror; may need byte-order handling |
| Shim (3 files) | Likely no change | N/A | No field-level logic |
| Tests (2 files) | Update if needed | Judgment | Depends on semantics |
| Behavior (2 files) | Add constraints | Judgment | Protocol understanding |
| Entity (3 files) | Likely no change | N/A | Role definitions don't reference individual fields |

Summary: 3 files mechanical/heuristic, 4 files judgment, 12 files unaffected. MiniP has the simplest propagation path.

### 3.4 Mechanicality Spectrum

| Protocol | Mechanical/Heuristic Files | Judgment Files | Unaffected Files | Mechanical % of Affected |
|---|---|---|---|---|
| QUIC | 3-11 (type+ser/deser+attack structs) | 82-90 (tests+shims+behavior+attack events) | 3-7 | 3-12% |
| BGP | 3 | 3 | 33 | 50% of affected |
| MiniP | 3 | 4 | 12 | 43% of affected |
| CoAP | N/A | N/A | N/A | Ser/deser unimplemented |

The design doc's claim of "65% mechanical" for QUIC appears to overcount. The struct additions to attack variant files are mechanical, but the event specification updates in those same files require judgment. The 65% figure likely refers to lines changed rather than files affected, where the bulk of mechanical lines are in the 10 ser/deser files.

---

## 4. Dependency Flow Maps

### 4.1 Include/Import Mechanism

Ivy uses a single `include` keyword for file dependencies. The `SYMBOL` is a bare name (no extension, no path separators). Resolution (from `ivy/ivy_compiler.py:2300`):
1. Try `<name>.ivy` in the current working directory
2. On failure, try in the standard library directory (`ivy/include/1.7/`)

No relative paths, no recursive directory search, no multi-path include. All `.ivy` files in a compilation must be reachable from the same cwd. Include is idempotent (already-included files are skipped).

Three dependency-related keywords:
- `include` -- textual inclusion (C-like `#include`), the dominant mechanism
- `import` -- FFI import of a C++ runtime action, not file-level
- `interpret` -- maps abstract Ivy types to concrete bit-vector representations

### 4.2 QUIC Dependency Flow

```
quic_server_test.ivy
  -> ivy_quic_shim_client.ivy
    -> quic_shim.ivy
      -> quic_connection.ivy
        -> quic_packet.ivy  <-- type defined here (line 94)
          -> quic_types.ivy <-- base types (cid, version, etc.)
          -> quic_frame.ivy <-- frame variants
          -> quic_transport_parameters.ivy
          -> quic_fsm_sending.ivy / quic_fsm_receiving.ivy
```

Total depth: 5 levels of transitive include.

The shim layer (`quic_shim.ivy:3-59`) is the aggregation point, pulling in:
- `quic_connection` (transitively brings all packet/frame types)
- `attack_connection` (all attack variants)
- All 10 ser/deser files
- `quic_protection`, `quic_endpoint`, entity files, recovery/CC

Role-specific shims (`ivy_quic_shim_client.ivy`, `ivy_quic_shim_server.ivy`, etc.) include `quic_shim` and add role-specific event handling.

### 4.3 MiniP Dependency Flow

```
ping_server_test.ivy
  -> ping_shim_client.ivy
    -> ping_shim.ivy
      -> ping_packet.ivy  <-- type defined here (line 14)
        -> ping_byte_stream.ivy
        -> ping_frame.ivy
```

Total depth: 4 levels. No connection layer, no attack stack, no TLS/protection.

### 4.4 BGP Dependency Flow

```
bgp_speaker_test_accept.ivy
  -> bgp_shim.ivy
    -> bgp_header_message.ivy, bgp_open_message.ivy, bgp_update_message.ivy, ...
    -> bgp_ser.ivy, bgp_deser.ivy, bgp_ser_open.ivy, bgp_deser_open.ivy, ...
    -> bgp_speaker.ivy
    -> bgp_network.ivy
```

Key structural differences from QUIC:
- Split ser/deser: one `serdes` instance per message type, instantiated at `bgp_shim.ivy:154-158`
- TCP transport: `net.connect_accept` / `net.connected` / `net.recv` callbacks instead of UDP `net.recv`
- No role-specific shim variants (single `bgp_shim.ivy`)

### 4.5 Shim Mapping Pattern

Shim files serve as the FFI between Ivy's abstract model and the C++ runtime. Three mechanisms:

**Mechanism 1: C++ embedding** (`<<< member >>>` / `<<< impl >>>` blocks)
Ser/deser files embed C++ classes inheriting from `ivy_binary_ser_128` / `ivy_binary_deser_128`. The backtick syntax (`` `ping_ser` ``) references the Ivy object's mangled C++ name.

**Mechanism 2: Advice** (`implement`, `after`, `before`, `around`)
Shim files attach behavior to abstract actions. Example: `ivy_quic_shim_client.ivy:37` uses `after packet_event(...)` to serialize, encrypt, and send packets when `_generating` is true.

**Mechanism 3: Parameterized module instantiation** (`instance`)
`instance prot : quic_protection(tls_api.id, tls_api.upper)` creates a concrete protection module. `instance pkt_serdes : serdes(quic_packet, stream_data, quic_ser, quic_deser)` wires serialization.

### 4.6 Attack Variant Pattern

Attack variants use **copy-paste with selective field modification**. Ivy does not support struct inheritance or type extension.

Evidence: `forged_quic_packet.ivy:72-81` defines a struct byte-for-byte identical to `quic_packet.ivy:94-101` (only the object name differs). `forged_protected_quic_packet.ivy` replaces `seq_num + payload` with `protected_payload : stream_data`. `replayed_quic_packet_0rtt.ivy` removes the `token` field.

Each attack variant:
1. Duplicates the base type's includes independently
2. Duplicates the struct definition (modifying 0-2 fields)
3. Duplicates the event specification (lines 165-398 of `forged_quic_packet.ivy` mirror `quic_packet.ivy`'s `packet_event` specification)
4. Defines its own action names (`forged_packet_event` vs `packet_event`)

`attack_connection.ivy:36-39` aggregates all variants via includes.

### 4.7 Generated Files / Boilerplate

**No automated code generation exists.** The `patterns/` directory contains 13 template `.ivy` files with `{placeholder}` syntax (e.g., `binary_ser_template.ivy`, `shim_udp_template.ivy`), but these are human-readable reference patterns. There is no Makefile, Jinja renderer, or script that instantiates them. `collect_protocols_parameters.py` is an empty file.

Comparing `patterns/serdes/binary_ser_template.ivy` against `minip_stack/ping_ser.ivy` confirms exact structural match: same `ivy_binary_ser_128` base, same enum pattern, same virtual methods. MiniP's serializer is a hand-instantiated copy of the template.

Many MiniP `.ivy` files have parallel `.md` copies maintained in the same directory (not generated; manually maintained).

---

## 5. Tooling Inventory

### 5.1 ivy-lsp (20 MCP tools)

Base path: `panther_ivy/submodules/ivy-lsp/ivy_lsp/`

| # | Tool | Parameters | Purpose | Timeout | Cost |
|---|---|---|---|---|---|
| 1 | `ivy_verify` | `relative_path`, `isolate?`, `use_cache?`, `compact?`, `scope?` | Formal verification via `ivy_check` | 180s | high |
| 2 | `ivy_compile` | `relative_path`, `target?`, `isolate?`, `scope?` | Compile to test executable via `ivyc` | 360s | high |
| 3 | `ivy_model_info` | `relative_path`, `isolate?` | Model structure via `ivy_show` | 60s | medium |
| 4 | `ivy_diagnostics` | `relative_path`, `mode?`, `layers?`, `min_severity?`, `scope?` | 5-layer diagnostic analysis or structural lint | 120s | medium |
| 5 | `ivy_verification_dashboard` | (none) | Workspace verification status | 30s | low |
| 6 | `ivy_include_graph` | `relative_path?`, `detail?`, `limit?`, `scope?` | Include dependency graph | 60s | medium |
| 7 | `ivy_capabilities` | (none) | Available CLI/MCP tools and staging health | 10s | low |
| 8 | `ivy_scope` | `relative_path` | Endpoint mirror scope info | 30s | low |
| 9 | `ivy_health_check` | (none) | Server health and cache status | 10s | low |
| 10 | `ivy_index` | `protocol?`, `fast?`, `status?` | Build/check offline `.ivy-index/` | 300s | high |
| 11 | `ivy_coverage` | `mode?`, `relative_path?`, `test_file?`, `protocol?`, `compact?`, `max_items?`, `scope?` | RFC coverage: stats, matrix, gaps, diff | 120s | high |
| 12 | `ivy_extract_requirements` | `rfc_text?`, `output?`, `rfc_name?`, `protocol?`, `base_section?`, `rfc_source?`, `sections?` | Parse RFC to extract MUST/SHOULD/MAY | 30s | low |
| 13 | `ivy_manifest` | `mode?`, `protocol?`, `rfc_source?`, `check_online?` | Manage requirement manifests | 60s | medium |
| 14 | `ivy_visualize` | `view?`, `test_file?`, `protocol?`, `include_state_vars?`, `state_var_filter?`, `group_by?`, `max_items?` | Dependency graph, state machine, layers | 60s | medium |
| 15 | `ivy_model_summary` | `detail?`, `test_file?`, `protocol?`, `sort_by?`, `limit?`, `action_name?`, `file_path?`, `offset?`, `max_items?` | Per-action stats or requirement detail | 60s | medium |
| 16 | `ivy_patterns` | `protocol`, `mode?`, `pattern?`, `reference_protocol?` | Pattern detection, validation, comparison | 60s | medium |
| 17 | `ivy_pattern_scaffold` | `protocol`, `pattern`, `wire_format?`, `role_type?`, `variant_names?`, `roles?` | Generate Ivy source from pattern template | 30s | low |
| 18 | `ivy_quality` | `mode?`, `file_path?`, `line?`, `context?`, `protocol?`, `gate_level?`, `max_items?` | Context-aware suggestions or quality gate | 60s | medium |
| 19 | `ivy_workspace` | `action`, `target?`, `roles?` | Manage active protocol workspace | 10s | low |

Note: `ivy_extract_requirements` and `ivy_manifest` are registered within `register_traceability_tools`, not via a separate call from `register_all_tools`.

### 5.2 ivy-lsp Semantic Model

**6 Node Types** (defined in `core/semantic/nodes.py:1-123`):

| Node | Key Fields | Purpose |
|---|---|---|
| `SymbolNode` | `qualified_name`, `kind` (10 kinds: action, relation, function, individual, module, object, isolate, destructor, constructor, instance), `sort_name`, `arity`, `params`, `return_sort`, `tier` | Any symbol in workspace |
| `TypeNode` | `qualified_name`, `sort_name`, `is_enum`, `variants`, `tier` | Type declaration |
| `MonitorNode` | `action_name`, `mixin_kind` (before/after/around), `requirement_ids` | Monitor block |
| `RfcRequirement` | `rfc`, `section`, `text`, `level` (MUST/SHOULD/MAY/MUST NOT/SHOULD NOT), `layer`, `testable` | RFC requirement from manifest |
| `ManifestMetadata` | `generated_at`, `content_hash`, `obsoleted_by`, `is_draft` | Manifest staleness |
| `RfcAnnotation` | `tags`, `node_id` | `# [rfcNNNN:X.Y]` bracket-tag in source |

**16 Edge Types** (defined in `core/semantic/edges.py:14-35`):
READS, WRITES, CONSTRAINS, DEPENDS_ON, PROPAGATED_FROM, HAS_TYPE, HAS_PARAM, RETURNS_TYPE, MONITORS, EXPORTS, IMPORTS, CONTAINS, INCLUDES, COVERS, CALLS, USES

**Indexing:** `SemanticModel` stores nodes by id, type, file, name, and tier. 3-tier concurrent analysis: Tier 1 (parser), Tier 2 (lexer), Tier 3 (regex fallback). Higher tiers overwrite lower-tier data.

### 5.3 ivy-lsp Analysis Capabilities

**Impl Block Parser** (`core/analysis/impl_block_parser.py:1-199`):
Detects 10 C++ patterns: `<<< impl >>>` blocks, `<<< member >>>` blocks, inline C++, enum state machines, socket operations, class inheritance, ser/deser base classes (`ivy_binary_ser_N`/`ivy_binary_deser_N`), setn/getn call counts.

**Pattern Library** (`core/analysis/pattern_library.py:1-600+`):
7 pattern kinds: SERDES, VARIANTS, MONITORS, SHIM, MODULE, ENTITY, INCLUDE_CHAIN.
- SERDES: detects C++ classes inheriting ser/deser bases + `instance X : serdes(...)` declarations
- VARIANTS: detects struct types, variant types, type enums
- MONITORS: detects before/after/around/implement blocks, `_finalize`, export actions
- SHIM: detects `implement net.recv`/`.connected`/`.accept`, connection state relations, socket ops, transport protocol
- MODULE: detects `module X(params) = {...}` and `instance X : module(args)`
- ENTITY: detects variant modules, behavior actions, role type (asymmetric vs symmetric)

**Requirement Graph** (`core/analysis/requirement_graph.py:1-699`):
`wire_propagation_edges()` exists at line 539-549. Takes `include_graph`, finds files including the requirement's source, creates `PROPAGATED_FROM` edges. Graph is adjacency-list with forward/backward indices, thread-safe via RLock, supports versioned snapshots.

5 wiring methods: `add_file_requirements()` (CONSTRAINS, WRITES), `wire_state_var_edges()` (READS), `wire_dependency_edges()` (DEPENDS_ON), `wire_coverage_edges()` (COVERS), `wire_propagation_edges()` (PROPAGATED_FROM).

### 5.4 panther-serena (44 tool classes)

Base path: `panther_ivy/submodules/panther-serena/src/serena/`

| File | Tools | Purpose |
|---|---|---|
| `file_tools.py` | ReadFile, CreateTextFile, ListDir, FindFile, ReplaceContent, DeleteLines, ReplaceLines, InsertAtLine, SearchForPattern | File system operations (9) |
| `symbol_tools.py` | RestartLanguageServer, GetSymbolsOverview, FindSymbol, FindReferencingSymbols, ReplaceSymbolBody, InsertAfterSymbol, InsertBeforeSymbol, RenameSymbol | Language-aware symbol operations (8) |
| `memory_tools.py` | WriteMemory, ReadMemory, ListMemories, DeleteMemory, RenameMemory, EditMemory | Markdown persistence (6) |
| `cmd_tools.py` | ExecuteShellCommand | Shell execution (1) |
| `config_tools.py` | OpenDashboard, ActivateProject, RemoveProject, SwitchModes, GetCurrentConfig | Project management (5) |
| `workflow_tools.py` | CheckOnboardingPerformed, Onboarding, ThinkAboutCollectedInformation, ThinkAboutTaskAdherence, ThinkAboutWhetherYouAreDone, SummarizeChanges, PrepareForNewConversation, InitialInstructions | Workflow meta-ops (8) |
| `jetbrains_tools.py` | JBFindSymbol, JBFindReferencingSymbols, JBGetSymbolsOverview, JBTypeHierarchy | JetBrains IDE (4) |
| `ivy_tools.py` | IvyDiagnostics, IvyGotoDefinition, IvyServerStatus, IvyTestScope | Ivy LSP integration (4) |
| `query_project_tools.py` | ListQueryableProjects, QueryProject | Cross-project queries (2) |

**Ivy-Specific Tools** (all marked `ToolMarkerOptional`):
1. `IvyDiagnosticsTool` — returns cached LSP `publishDiagnostics` without running `ivy_check`
2. `IvyGotoDefinitionTool` — LSP `textDocument/definition` with context lines
3. `IvyServerStatusTool` — custom `ivy/serverStatus` LSP request
4. `IvyTestScopeTool` — custom `ivy/listTests` and `ivy/setActiveTest`

**Configuration** (`serena_config.py`):
- `DEFAULT_TOOL_TIMEOUT`: 240 seconds
- `default_max_tool_answer_chars`: 150,000 characters
- Context/mode system: contexts define tool sets for environments; modes define operational patterns

**Transaction/Rollback:** None. `TaskExecutor` is a sequential task queue, not a transaction manager. Individual tasks run to completion or fail. No multi-file atomicity, no commit/rollback, no journaling. Failed task exceptions propagate to caller; executor continues with next task. Task cancellation only prevents unstarted tasks.

### 5.5 panther-ivy-plugin (v0.7.0)

Base path: `panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

**Components:**
- 5 agents: methodology-guide, model-reviewer, navigator, spec-analyst, traceability-agent
- 10 commands: nct-add-pattern, nct-check, nct-compile, nct-health, nct-model-info, nct-observability, nct-review, nct-scaffold, nct-serena-health, nct-validate
- 20 skills: adaptive-interview, claim-discussion, clear-workspace, counterexample-guide, healthcheck, incremental-spec-dev, interaction-patterns, ivy-lsp-walkthrough, ivy-toolkit, ivy-workflow-orchestrator, ivy-writing-guide, methodology-reference, nact-methodology, nct-methodology, nsct-methodology, set-workspace, specification-patterns, tooling-reference, workflow-reference
- 12 hook event types (27 total scripts): PreToolUse (6), PostToolUse (3), PostToolUseFailure (1), SessionStart (4), SessionEnd (2), Stop (2), SubagentStart (1), SubagentStop (1), PreCompact (1), UserPromptSubmit (1), Notification (1), PermissionRequest (1)

**MCP Wiring** (`.mcp.json`):
1. `ivy-tools` — starts ivy-lsp in MCP mode (env: `IVY_LSP_MAX_CONCURRENT_TOOLS=4`, `IVY_LSP_PREWARM_MODEL=1`)
2. `serena` — starts panther-serena (env: `PANTHER_IVY_ENABLE_SERENA=1`)

**Feature flag `PANTHER_IVY_ENABLE_SERENA`:** Referenced in 7 files. Gates Serena startup in `start-serena.sh:11-13` (if not `"1"`, script exits with "Disabled"). Documented in CLAUDE.md, referenced in nct-serena-health troubleshooting, echoed in healthcheck, tested in 3 test cases.

**`/nct-propagate`:** Does not exist. No file, command, or skill.
**`/nct-serena-health`:** Exists as command. Validates Serena integration chain across 3 layers with 7 sequential checks.

---

## 6. Hard Constraints (with numbers)

### 6.1 Context Window

**QUIC full protocol:**
- 199 .ivy files, 40,554 total lines
- At ~7 tokens/line: **~283,878 tokens** for raw file content
- With system prompt, tool calls, and conversation overhead (~50K tokens): **~334K tokens total**

**QUIC `quic_packet` propagation subset:**
- 96 files, ~28,000 lines
- At ~7 tokens/line: **~196,000 tokens** for file content
- With overhead: **~246K tokens total**

| Model | Context Window | Fits Full QUIC? | Fits quic_packet subset? |
|---|---|---|---|
| Sonnet (200K) | 200,000 | No (334K > 200K) | No (246K > 200K) |
| Opus (1M) | 1,000,000 | Yes (334K < 1M) | Yes (246K < 1M) |

For Sonnet, a propagation session would need to be batched in chunks of ~20-25 files (~140K tokens of file content plus overhead). For Opus, all 96 files fit in a single context but consume ~25% of the window, leaving limited room for iterative editing.

**BGP full protocol:** 39 files, 4,045 lines, ~28K tokens. Fits any model easily.
**MiniP full protocol:** 19 files, 1,231 lines, ~8.6K tokens. Trivial.

### 6.2 Serena Throughput

**Per-tool-call timeout:** 240 seconds (from `serena_config.py:47`).
**Execution model:** Sequential task queue (`TaskExecutor`). One tool call at a time.
**Max concurrent MCP tools (ivy-lsp):** 4 (from `.mcp.json` env).

**Estimated wall-clock for a full QUIC propagation (96 files):**

| Operation | Count | Est. Time/Op | Total |
|---|---|---|---|
| File reads (via Serena) | 96 | 2-5s | 192-480s (3.2-8 min) |
| File edits (via Serena) | ~30 (non-test affected files) | 5-15s | 150-450s (2.5-7.5 min) |
| Verification calls (ivy_check) | 5-10 | 60-180s | 300-1800s (5-30 min) |
| **Total** | | | **10.7-45.5 min** |

**Practical ceiling:** At 240s per-tool-call timeout, a single stuck verification or slow edit kills the pipeline. With 30 edits, the probability of at least one timeout (assuming 5% per-call failure rate) is `1 - 0.95^30 = 78.5%`. For a pipeline of 60 total tool calls: `1 - 0.95^60 = 95.4%` failure probability.

The practical ceiling before timeout fragility dominates is approximately **15-20 tool calls per session**, which means a QUIC propagation would need to be split into **4-6 sequential sessions** with checkpoint/resume.

### 6.3 Rollback

**Atomic multi-file transactions:** Not supported by any component in the stack.

| Component | Transaction Support | Recovery |
|---|---|---|
| ivy-lsp | None (read-only analysis) | N/A |
| panther-serena TaskExecutor | Sequential queue, no rollback | Failed task exception; next task continues |
| panther-ivy-plugin | None | N/A |
| Git (underlying) | Full (via commit/revert) | `git checkout -- .` or `git stash` |

**Recovery path if validation fails mid-propagation:** The only rollback mechanism is Git. If a propagation edits 15 files and then verification fails on file 16, the options are:
1. `git diff` to see what changed, manually fix the failing file
2. `git checkout -- .` to revert all changes (loses all progress)
3. `git stash` to save progress, fix the issue, then reapply

None of these are automated. A propagation engine would need to implement its own transaction log (list of files modified + original content) or use Git commits as checkpoints (commit after each successful edit, revert to last good commit on failure).

### 6.4 Parser Depth

**Scoped symbol resolution:**
The semantic model tracks `SymbolNode.qualified_name`, so it can distinguish `quic_packet.ptype` from `bgp_message.ptype` at Tier 1 (parser level). The `FindSymbol` and `FindReferencingSymbols` tools in panther-serena delegate to the language server, which uses the semantic model for resolution.

**Analysis tiers:**
- Tier 1 (Parser): Full AST-like analysis. Can resolve qualified names, track includes, build requirement graph. Available when `ivy_to_python` parser succeeds.
- Tier 2 (Lexer): Token-level analysis. Can identify keywords, brackets, basic structure. Fallback when parser fails.
- Tier 3 (Regex): Line-level pattern matching. Detects `include`, `object`, `type this = struct`, etc. Always available.

**What is possible:**
- Include graph construction (all tiers)
- Symbol definition/reference lookup (Tier 1)
- Pattern detection: serdes, variants, monitors, shims, modules, entities (Tier 1-3, varying accuracy)
- Requirement propagation via include chain (Tier 1)
- Impl block C++ pattern extraction: enum states, class inheritance, ser/deser bases (regex-based, all tiers)

**What is not possible with current parser:**
- Call graph (edge type CALLS exists but `wire_call_edges()` is not implemented)
- Ser/deser-to-type correlation (no tool maps which serializer handles which struct)
- Symbol-level test impact analysis (no tool traces which tests exercise which symbols)
- Change propagation chains (no tool computes "if field X changes, which files need updating")
- Variant enumeration for attack types (no tool lists all copy-paste variants of a base type)
- C++ semantic analysis within `<<< impl >>>` blocks (regex-based detection only, no C++ AST)

---

## 7. WP2 Context

### 7.1 WP2 Success Criteria

The primary WP2 document (`05_maintenance_burden.md`) lives outside the repository at `/Users/elniak/Documents/Documents/Work/AMC3/11_SmartAgents/WP2-current-tasks/` and was not directly readable. Derived metrics from the in-repo design spec (`docs/superpowers/specs/2026-04-07-propagation-engine-design.md`):

**Quoted claim:** "Every code change potentially invalidates existing proofs, requiring re-verification effort."

**Measured blast radius data (from design doc Section 5):**

| Scenario | Files Affected | Lines Changed | Claimed Mechanical % |
|---|---|---|---|
| New field in `quic_packet` | 97 | 2000-3000 | 65% |
| New frame variant in `quic_frame` | 50-70 | 300-500 | 75% |
| Field type change in BGP message | 6-9 | 30-50 | 60% |

**WP2 success metric (Phase 4):** "specification maintenance effort as a percentage of code change effort." Goal: reduce the 60-75% mechanical portion to near-zero.

**Complexity spectrum for generatability:**
- MiniP/BGP: claimed 100% mechanically generatable
- QUIC simple packets: claimed ~90%
- QUIC complex frames: claimed ~60%

### 7.2 Architecture (from paper references)

**Paper title:** "Automated Formal Specification Maintenance via Git Commit History Analysis: Integrating the Claude Agent SDK within the WP2 Framework"

**Proposed dual-mode architecture:**
1. **Interactive mode:** Claude Code plugin with native tools (Read, Edit, Grep, Write) plus user approval gates
2. **Headless CI/CD mode:** Claude Agent SDK triggered by pre-commit hooks, all file access through MCP servers (panther-serena for editing, mcp-server-git for history)

**Shared layer:** MCP tools and skills shared between both modes.

**Key components:**
- ivy-lsp (read-only code intelligence)
- panther-serena (code editing MCP)
- panther-ivy-plugin (user-facing commands/skills/agents)
- mcp-server-git (diff, log, commit, Lore trailer extraction)
- Claude Agent SDK (headless orchestration)

**Lore protocol integration** (arxiv.org/abs/2603.15566): Git trailers encode semantic intent (Constraint, Rejected, Scope-risk, Confidence) to drive verification depth and change classification.

### 7.3 Architecture Divergence

**What exists vs. what the paper requires:**

| Capability | Status | Gap |
|---|---|---|
| ivy-lsp MCP tools (15+ features) | Exists (v0.11.1, 20 tools) | Missing: call graph, ser/deser-to-type correlation, symbol-level test impact, change propagation chains, variant enumeration |
| panther-serena symbol editing | Exists (replace_symbol_body, insert, rename) | Missing: Ivy-specific editing tools, ser/deser generation, Lore trailer parsing, atomic transactions, rollback/dry-run |
| panther-ivy-plugin | Exists (v0.7.0, 5 agents/10 commands/20 skills) | Missing: `/nct-propagate` command, propagation-specific skills |
| Lore trailer enforcement | Not implemented | No trailer parsing, no semantic intent extraction from commits |
| mcp-server-git | Not integrated | No diff/log/commit MCP tools wired |
| Claude Agent SDK headless pipeline | Not implemented | No pre-commit hook trigger, no headless orchestration |
| Hallucination mitigation skills | Not implemented | serdes-generation, lore-to-ivy-mapping, constraint-patterns skills do not exist |

**Open architectural questions (from design doc Section 9):**
1. Whether to use Claude Agent SDK or Claude Code headless mode (`-p` flag)
2. Whether new Ivy editing tools belong in panther-serena or a new dedicated MCP server
3. Whether to start proof-of-concept with MiniP (simplest) or QUIC (most impact)

### 7.4 Additional WP2 Documents

**Within repo:** `docs/superpowers/specs/2026-04-07-propagation-engine-design.md` (214 lines) — primary in-repo WP2-derived design document.

**Outside repo (inaccessible):**
- `/Users/elniak/Documents/Documents/Work/AMC3/11_SmartAgents/WP2-current-tasks/00_index.md` through `07_supplementary_ai_assistance.md` — 8 WP2 problem documents
- `/Users/elniak/Documents/Documents/Work/AMC3/11_SmartAgents/WP2-current-tasks/Claude-Code SDK for Git Analysis.md` — full research paper

---

## Appendix: Noted Ser/Deser Asymmetries

During analysis, several ser/deser asymmetries were identified that could affect propagation correctness:

| Protocol | File Pair | Asymmetry |
|---|---|---|
| QUIC | quic_ser/quic_deser | Ser has 55 states, deser has 53 (missing `quic_malicious`, `quic_s_retry_token_length`; extra `quic_s_type`) |
| BGP (update) | bgp_ser_update/bgp_deser_update | Ser uses 0-indexed type codes for path attributes; deser uses 1-indexed hex codes (0x01-0x07) |
| BGP (notification) | bgp_ser_notification/bgp_deser_notification | Ser writes data as 8 bytes fixed; deser reads 1 byte at a time |
| MiniP | ping_ser/ping_deser | Deser applies `reverse_bytes()` on timestamps; ser does not |

These asymmetries mean a propagation engine cannot simply mirror serializer changes into the deserializer; each pair must be analyzed independently.
