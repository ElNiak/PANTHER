# Ivy Protocol Model Builder — Skill Design Spec

**Date**: 2026-04-07
**Status**: Draft (post-review revision)
**Goal**: Create a skill that guides users through building a formal Ivy specification for any network protocol within the panther_ivy framework.

## Scope

A skill for creating new Ivy formal models for protocols of any shape (client-server, P2P, stateless, application-layer), working within the panther_ivy infrastructure. Assumes no Ivy experience. Produces an interactive, phased workflow with review checkpoints between layers.

## Non-Goals

- Creating PANTHER Python plugin code (protocol definitions, IUT service managers, config schemas). That is a separate skill.
- Teaching Ivy as a standalone language outside the panther_ivy context.
- Modifying the panther_ivy compiler pipeline or runtime.

## Reference Implementation

The QUIC formal model at `panther/plugins/services/testers/panther_ivy/protocol-testing/quic/` serves as the reference. It contains ~200 `.ivy` files spanning:

- `quic_stack/` — core protocol model (types, packets, frames, connections, streams, transport parameters, FSMs)
- `quic_entities/` — entity instantiation files (client, server, MiM, attacker, victim)
- `quic_entities_behavior/` — endpoint modules and role-specific behavioral constraints (note: `quic_endpoint.ivy` lives here, not in `quic_entities/`)
- `quic_shims/` — bridges between the formal model and real network I/O
- `quic_config/` — transport parameter configurations
- `quic_tests/` — ~95 test specifications (conformance, feature-specific, error handling, attack)
- `quic_attacks_stack/` — forged/replayed/modified message types
- `quic_recovery/` — loss recovery and congestion control models
- `quic_fsm/` — finite state machine models for stream states
- `quic_utils/` — serialization, deserialization, locale, byte streams, timing, random values (~15 files)
- `quic_extensions/` — protocol extensions (ACK frequency)
- `tls_stack/` — TLS 1.3 formal model (for QUIC's crypto layer)

The model evolved over 4+ years from a monolithic QUIC-only tool (2021) to the current compositional architecture.

## Approach

Hybrid of pattern catalog with protocol classification (to handle diverse protocol shapes) and incremental model building (to teach Ivy constructs hands-on). The classification determines which architectural patterns apply; each phase builds incrementally with compile-check-review cycles.

---

## Ivy Compilation Pipeline

Before diving into phases, users need to understand how Ivy code becomes a runnable test.

1. **`ivy_check model.ivy`** — validates the model for type correctness and well-formedness. Fast (seconds). No binary produced. Use during Phases 3-4 for quick feedback.

2. **`ivyc target=test test_iters=100 model.ivy`** — translates the Ivy model to C++, then compiles the C++ into a native binary. Slow (minutes, because of C++ compilation). The binary lands in `$PYTHON_IVY_DIR/ivy/include/1.7/` with the test file's name. Use from Phase 4 onward.

3. **Run the binary** — the compiled binary takes command-line arguments for network addresses, ports, random seed, etc.:
   ```bash
   ./{proto}_{role}_test seed=42 server_addr=0x0a000001 server_port=4443 \
       client_addr=0x0a000002 client_port=4987
   ```

4. **Test output** — the binary prints event traces (actions being called) to stdout. On success, it terminates normally after exhausting iterations. On failure, it prints an assertion error with the Ivy source file and line number:
   ```
   FAIL: require at quic_packet.ivy:558 (sent_pkt constraint violated)
   ```

---

## File Naming Convention

The QUIC model uses two naming patterns:

- **Stack/protocol files**: `{proto}_*.ivy` (e.g., `quic_packet.ivy`, `quic_frame.ivy`). These model the protocol itself.
- **Infrastructure/entity files**: `ivy_{proto}_*.ivy` (e.g., `ivy_quic_server.ivy`, `ivy_quic_shim_client.ivy`). These are Ivy testing infrastructure that wraps the protocol model.

Follow this convention for new protocols.

---

## Phase Structure

Six phases with checkpoints:

| Phase | Name | Output | Checkpoint |
|-------|------|--------|------------|
| 1 | Protocol Classification | Protocol profile document | User confirms classification |
| 2 | Blueprint Generation | File list, module graph, type mappings | User approves architecture |
| 3 | Core Types and Stack | Compilable `.ivy` files for types, messages, state | `ivy_check` passes on aggregator |
| 4 | Entity Model | Endpoint modules, shim bridges, serialization | `ivyc target=test` produces binary |
| 5 | Behavioral Specs | Role-specific constraints, `_generating` guards | First test runs against real impl |
| 6 | Test Scenarios | Conformance tests, attack models, finalization | Full test suite passes |

Each phase begins with an Ivy tutorial section that teaches exactly the constructs needed, using the QUIC model as reference.

---

## Phase 1: Protocol Classification

### Purpose

Determine the protocol's shape through 5-7 concrete questions to produce a protocol profile that drives all subsequent phases.

### Classification Questions

1. **Communication pattern**: Client-server (one side initiates), peer-to-peer (either side initiates), request-response (stateless exchanges), or multicast (one-to-many)?
2. **Connection model**: Persistent connections with state, or independent message exchanges?
3. **Message structure**: Fixed-format binary, variable-format (TLV/tagged), text-based, or format that changes mid-connection (e.g., handshake vs. data phase)?
4. **Layering**: Self-contained on a transport, or layered on another protocol (e.g., DNS over QUIC)?
5. **Security model**: Own encryption/authentication, relies on underlying transport, or none?
6. **State machine complexity**: Approximate state count (2-3 simple, 5-10 moderate, 10+ complex).
7. **Testing goals**: Conformance, malformed input resilience, active attacker resistance, or all?

### Protocol Profile Output

A structured summary:

```
Protocol: [name] ([RFC/spec reference])
Pattern: [communication pattern], [connection model]
Transport: [underlying transport and relationship]
Messages: [format description, including mid-connection changes if any]
Security: [security model]
States: [count] ([brief description])
Testing goals: [selected goals]
Extensible: [yes/no — does the protocol support negotiated extensions?]
```

### Pattern Selection

The profile maps to which QUIC model architectural elements apply:

| Profile Trait | Effect |
|---|---|
| Stateless protocol | Skip connection state tracking, no FSM directory |
| No own crypto | Skip protection/security files and `tls_stack/`, shims pass plaintext |
| Own crypto layer | Add `tls_stack/` equivalent for the security protocol |
| P2P / symmetric | Single entity module with symmetric instantiation, shared shim |
| Multicast | Publisher entity module with multiple destination endpoints |
| Simple state machine | Inline state in stack module, no separate FSM files |
| Complex state machine | Separate `{proto}_fsm/` directory with per-role FSM files |
| Mid-connection format change | Multiple message struct types, packet type dispatch in `behavior` action |
| Attack testing desired | Add `{proto}_attacks_stack/` directory |
| Layered on another protocol | Shims interface with underlying protocol API, not raw UDP |
| Request-response | Simpler `_generating` guards, minimal inter-event state |
| Extensible protocol | Add `{proto}_extensions/` directory for negotiated capabilities |

### Checkpoint

User reviews and confirms the protocol profile and pattern selection.

---

## Phase 2: Blueprint Generation

### Purpose

Produce a concrete file architecture adapted to the protocol profile.

### Ivy Concepts Taught

- `include` composition (textual insertion, not module import — the included file is pasted in place)
- `#lang ivy1.7` file header (required on every `.ivy` file)
- Include DAG flows one direction: test files include everything transitively

### Blueprint Template

Directory tree adapted from the QUIC model based on classification:

```
protocol-testing/{proto}/
+-- {proto}_stack/                        # Core protocol model
|   +-- {proto}_types.ivy                 # Base types, enums, bit-vector interpretations
|   +-- {proto}_message.ivy               # Message structs + message_event actions
|   +-- {proto}_state.ivy                 # State tracking (relations, functions, after init)
|   +-- {proto}_connection.ivy            # Aggregator: includes all stack files in order
+-- {proto}_utils/                        # Serialization, helpers, locale
|   +-- {proto}_ser.ivy                   # Struct-to-bytes serialization
|   +-- {proto}_deser.ivy                 # Bytes-to-struct deserialization
|   +-- {proto}_locale.ivy                # Network locale setup
+-- {proto}_entities/                     # Entity instantiation (one file per role)
|   +-- ivy_{proto}_{role_a}.ivy          # Role A entity: parameters + endpoint instantiation
|   +-- ivy_{proto}_{role_b}.ivy          # Role B entity: parameters + endpoint instantiation
+-- {proto}_entities_behavior/            # Endpoint modules + role-specific constraints
|   +-- {proto}_endpoint.ivy              # Parameterized endpoint modules (behavior action)
|   +-- ivy_{proto}_{role_a}_behavior.ivy # Role A behavioral constraints
|   +-- ivy_{proto}_{role_b}_behavior.ivy # Role B behavioral constraints
+-- {proto}_shims/                        # Wire format bridges
|   +-- {proto}_shim.ivy                  # Base shim (central composition point)
|   +-- ivy_{proto}_shim_{role_a}.ivy     # Role A send/receive
|   +-- ivy_{proto}_shim_{role_b}.ivy     # Role B send/receive
+-- {proto}_config/                       # Parameter configurations
|   +-- ivy_{proto}_standard_config.ivy
+-- {proto}_tests/                        # Test specifications
|   +-- {role_b}_tests/                   # Tests targeting role B (Ivy acts as role A)
|   |   +-- {proto}_{role_b}_test.ivy
|   +-- {role_a}_tests/                   # Tests targeting role A (Ivy acts as role B)
|       +-- {proto}_{role_a}_test.ivy
+-- {proto}_attacks_stack/                # (conditional: attack testing)
|   +-- forged_{proto}_message.ivy
|   +-- attack_connection.ivy             # Aggregator for attack types
+-- {proto}_extensions/                   # (conditional: extensible protocol)
|   +-- {proto}_{extension_name}.ivy
+-- {proto}_fsm/                          # (conditional: complex state machine)
|   +-- {proto}_fsm_sending.ivy
|   +-- {proto}_fsm_receiving.ivy
+-- tls_stack/                            # (conditional: own crypto layer)
    +-- tls_protocol.ivy
```

Simplifications based on classification:
- Stateless: no `_state.ivy`, no `_connection.ivy` aggregator (types + message suffice)
- No attacks: omit `_attacks_stack/`
- P2P: single entity file, single shim
- No FSM: omit `_fsm/` directory
- No crypto: omit `tls_stack/` and protection files
- Not extensible: omit `_extensions/`

### Module Dependency Graph

The skill produces a DAG showing include relationships, flowing from test files down through shims to the stack.

### Type Mapping Table

A mapping from RFC concepts to Ivy constructs. The Ivy syntax used here is explained in Phase 3; this table is a preview of the mapping only:

```
RFC Concept                  -> Ivy Construct                    -> File
[protocol-specific ID]       -> type {name}                      -> {proto}_types.ivy
[message type enum]          -> type {name} = {v1, v2, ...}      -> {proto}_types.ivy
[message format]             -> struct { field : type, ... }      -> {proto}_message.ivy
[protocol event]             -> action {name}_event(src,dst,msg)  -> {proto}_message.ivy
[session state]              -> relation {name}(S:session_id)     -> {proto}_state.ivy
[negotiated parameters]      -> variant types in config file      -> {proto}_config/
```

### Checkpoint

User reviews file tree, dependency graph, and type mapping table. Approves before any `.ivy` files are written.

---

## Phase 3: Core Types and Stack

### Purpose

Write the first compilable `.ivy` files: types, message structures, state tracking.

### Ivy Concepts Taught

- **Scalar types**: `type query_id` (abstract), `interpret query_id -> bv[16]` (bit-vector interpretation for compilation)
- **Bit-vector sizing**: choose width to match the field's wire format width. If variable-length, choose a width large enough for the maximum value needed in testing. E.g., a 16-bit DNS query ID uses `bv[16]`, a 4-bit QUIC CID length uses `bv[4]`.
- **Enumerations**: `type rcode = {noerror, formerr, servfail, nxdomain}`
- **Aliases**: `alias aid = cid` — creates a type alias (used in `quic_types.ivy:43`)
- **Definitions**: `definition zero = 0` — named constants
- **Structs**: `type this = struct { field : type, ... }` inside an `object` block
- **`this` keyword**: means "the enclosing object's type"
- **Arrays**: `instance idx : unbounded_sequence` + `instance arr : array(idx, this)`
- **Variants**: `variant this of base_type = struct { ... }` — declares a subtype of a base type. Ivy dispatches on variant types at runtime. Used for frame-like sub-types where one base type has multiple formats.
- **Relations**: `relation name(X:type)` — boolean predicates over typed parameters
- **Functions**: `function name(X:type) : return_type` — value mappings
- **`after init` blocks**: initialize all relations to false, functions to defaults
- **Actions with empty bodies**: `action event_name(params) = {}` — behavior defined by advice elsewhere. These are placeholders; in Phase 5, you will attach behavior to them using `around` and `before` advice blocks.
- **Boolean operators**: `~` (not), `&` (and), `|` (or) — used in `require` expressions

### QUIC Model References

- Types: `quic_types.ivy` — `cid`, `pkt_num`, `version`, `quic_packet_type` enum, `alias aid = cid`
- Structs: `quic_packet.ivy:94-102` — `quic_packet` struct with fields: `ptype`, `pversion`, `dst_cid`, `src_cid`, `token`, `seq_num`, `payload`
- Variants: `quic_frame.ivy:47-83` — `frame.ping`, `frame.ack` as variants of `frame`
- State: `quic_packet.ivy:229-329` — `conn_seen`, `sent_pkt`, `last_pkt_num`, `connected`, etc., with `after init` block
- Aggregator: `quic_connection.ivy` — includes all stack files in dependency order
- Actions: `quic_packet.ivy:137` — `action packet_event(src:ip.endpoint, dst:ip.endpoint, pkt:quic_packet) = {}`

### Build Order

1. **Types file** — scalars, enums, aliases, bit-vector interpretations. No dependencies. Compile with `ivy_check`.
2. **Message struct file** — struct definitions, array instances, main event action. Includes types.
3. **Sub-message types** (if variants needed) — frame-like sub-structures. Skip for single-message protocols.
4. **State tracking file** — relations, functions, `after init` block. Includes types.
5. **Aggregator file** — includes all stack files in correct order. Single entry point for the shim layer.

### What This Phase Does NOT Do

No `around`/`require` specifications. No entity definitions. No serialization. The stack defines the data model and declares events with empty bodies. Specification logic comes in Phase 5.

### Checkpoint

Run `ivy_check {proto}_connection.ivy` (the aggregator). All files must pass. Expected output is no errors. Common errors at this stage:
- **"sort mismatch"**: type error — check field types in structs match declared types.
- **"cannot find module"**: include path wrong — Ivy resolves includes relative to the working directory.
- **"multiple definitions"**: name collision — two included files define the same name.

User reviews and confirms type mappings match the RFC.

---

## Phase 4: Entity Model

### Purpose

Create endpoints that send/receive protocol messages and the shim bridges connecting the formal model to real network I/O.

### Ivy Concepts Taught

- **Modules**: `module client_ep(address:ip.addr, port:ip.port) = { ... }` — parameterized code templates
- **`instance`**: `instance server : endpoint.server_ep(addr, port)` — module instantiation with concrete values
- **`individual`**: singleton values scoped to a module instance (like global variables)
- **`parameter`**: `parameter server_addr : ip.addr = 0x0a000001` — declares a value settable from the command line when the compiled binary runs. This is how entity files receive IP addresses and ports at runtime. Every entity file uses this.
- **`import action`**: `import action show_debug(msg:stream_data)` — declares an action implemented in C++ (not Ivy). Used for debug output and integration with native code. The QUIC model uses ~10 `import action show_*` declarations in `quic_packet.ivy` for observability.
- **The `ip` module**: built-in panther_ivy infrastructure providing `ip.endpoint` (address + port + protocol), `ip.addr`, `ip.port`, and socket interfaces
- **The `net` module**: `net.open`, `net.send`, `net.recv` — socket operations used in shims
- **The `behavior` action**: the receive path that deserializes incoming UDP bytes into Ivy model events. This is the most complex part of the entity model. See below.

### The `behavior` Action (Detailed)

The `behavior` action is the bridge from raw bytes to formal model events. In the QUIC model (`quic_entities_behavior/quic_endpoint.ivy:57`), it is ~200 lines that:
1. Receive a raw byte array from `net.recv`
2. Parse header bytes using bit manipulation (`bvand`, `bfe` for bit-field extraction)
3. Determine the message/packet type from header bits
4. Dispatch to the appropriate deserialization path
5. Call the formal model's event action (e.g., `packet_event`) with the deserialized struct

For a simpler protocol, `behavior` can be much shorter. A DNS-over-UDP model might have a 20-line `behavior` that reads a DNS header (12 bytes), extracts the query ID and flags, and calls `message_event`. The complexity scales with the protocol's wire format complexity.

The skill guides users through writing `behavior` incrementally: start with the simplest message type, get it parsing correctly, then add dispatch for additional types.

### QUIC Model References

- Endpoint module: `quic_entities_behavior/quic_endpoint.ivy:27-80` — `client_ep` module with socket setup and `behavior` action
- Entity file: `quic_entities/ivy_quic_server.ivy` — declares `parameter server_addr`, instantiates `quic_endpoint.server_ep(server_addr, server_port)`
- Base shim: `quic_shims/quic_shim.ivy` — central composition point including stack aggregator, all entity files, serialization (19 includes total), attack connection, TLS messages, locale
- Role shim: `quic_shims/ivy_quic_shim_server.ivy:39-56` — `after packet_event` serializes outgoing packets and calls `net.send`. Note: role shims use `after` advice (not `around`) because they add side effects (sending), not preconditions.

### Entity Pattern (Three Layers Per Role)

1. **Endpoint module** (`{proto}_entities_behavior/{proto}_endpoint.ivy`): parameterized module with `individual` socket, `after init` setup, `behavior` action for the receive path.
2. **Entity file** (`{proto}_entities/ivy_{proto}_{role}.ivy`): declares `parameter` values (address, port), instantiates endpoint module, includes the shim.
3. **Shim file** (`{proto}_shims/ivy_{proto}_shim_{role}.ivy`): implements `after message_event` for serialize+send, delegates incoming bytes to `behavior` for deserialize.

### Adaptation by Protocol Shape

| Shape | Entity Pattern |
|---|---|
| Client-server | Asymmetric: separate client_ep and server_ep modules |
| P2P | Symmetric: single peer_ep module, instantiated multiple times |
| Stateless | Simplified behavior action: no connection tracking, just message parse |
| Layered on QUIC | Shim reads from QUIC streams instead of raw UDP sockets |
| Mid-connection format change | behavior action uses packet type dispatch (if/else on header bits) |

### Serialization Strategy

Two approaches:
- **Pass-through** (for early prototyping): skip ser/deser, pass Ivy structs directly. Works for `ivy_check` but not runnable tests.
- **Full ser/deser** (for real implementation testing): field-by-field byte packing/unpacking in `{proto}_utils/{proto}_ser.ivy` and `{proto}_deser.ivy`. Protocol-specific, maps to wire format.

The skill recommends starting with pass-through, validating the model logically through Phase 5, then implementing full ser/deser before Phase 6's integration tests against real implementations. The transition point is explicit: Phase 5 step 5 ("Integration test with stub") requires full ser/deser to be in place. If the user is only doing model validation (no real implementation testing), pass-through is sufficient for all phases.

### Build Order

1. **Endpoint module** — parameterized modules per role, `individual` declarations, `after init`.
2. **Entity files** — one per role, `parameter` declarations, instantiate endpoint modules.
3. **Base shim** — central composition point: includes stack aggregator, all entity files, serialization modules, locale, and (if crypto) protection module.
4. **Role-specific shims** — `after message_event` for outgoing (serialize + `net.send`), receive callback delegates to `behavior` for incoming.
5. **Serialization** (if targeting real impl testing) — `{proto}_ser.ivy` and `{proto}_deser.ivy` in `{proto}_utils/`.

### Checkpoint

Run `ivyc target=test {proto}_{role}_test.ivy` (create a minimal test file that just includes the shim and exports one action). The binary should compile. Invoke it with:
```bash
./{proto}_{role}_test seed=1 server_addr=0x7f000001 server_port=4443 client_addr=0x7f000001 client_port=4987
```
It will start and immediately terminate (no meaningful behavior yet, since no `require` constraints or useful exports exist). Success means compilation works. User reviews entity architecture and shim wiring.

---

## Phase 5: Behavioral Specs

### Purpose

Translate RFC requirements into machine-checkable constraints. This is the heart of the formal model.

### Ivy Concepts Taught

- **`around`/`before`/`after` advice**: attach preconditions, postconditions, and state updates to actions declared elsewhere
- **`require` statements**: `require expr` fails the test if `expr` is false. Each maps to an RFC MUST/SHALL.
- **`_generating` predicate**: built-in boolean. `true` when Ivy runtime generates events (tester role), `false` when observing events from the IUT.
- **`~` as "not"**: `~_generating` means "not generating" (observing IUT events).
- **Role inversion**: testing a server means Ivy acts as a client. The test file for server testing includes the **client** shim and **client** behavior, not the server shim. `ivy_{proto}_{tested_role}_behavior.ivy` constrains the tester's opposite role. The `oppose_role()` function in panther_ivy handles this mapping.
- **Multiple `around` blocks**: a single file can have multiple `around` blocks for different actions. The QUIC model's `quic_packet.ivy` has four: `around packet_event` (line 405, ~325 lines), `around send_ack_eliciting_handshake_packet` (line 735), `around send_ack_eliciting_application_packet` (line 974), `around send_ack_eliciting_initial_packet` (line 1218). For protocols with multiple message types or sub-events, plan for one `around` block per major event.
- **The dual-role specification pattern**:
  ```ivy
  around message_event(src, dst, msg) {
      if _generating {
          # Constraints on tester-generated traffic (ensure validity)
      };
      # Universal constraints (RFC requirements for all senders)
      require msg.length > 0;  # RFC Section X.Y: messages MUST NOT be empty
      if ~_generating {
          # Constraints on IUT traffic (spec violations = test failures)
      };
      ...  # original action body runs here (three literal dots)
      # State updates (apply to all events)
      message_seen(msg.id) := true;
  }
  ```

### QUIC Model References

- Main event spec: `quic_packet.ivy:405-729` — `around packet_event` with ~325 lines of `require` statements, `_generating` guards, and state updates
- Behavioral constraints: `ivy_quic_server_behavior.ivy` — `before frame.stream.handle` with `_generating` guards constraining tester's stream usage
- Frame handlers: `quic_frame.ivy` — sub-actions with `before` advice for frame-level constraints

### Requirement Extraction Process

The skill walks through the protocol spec:
1. Identify every MUST/SHALL/MUST NOT statement.
2. For each, determine: universal (all senders), tester-only (`_generating`), or IUT-only (`~_generating`).
3. Translate to `require` with appropriate guards.
4. Note the RFC section reference as a comment.

### Adaptation by Protocol Shape

| Shape | Behavioral Spec Pattern |
|---|---|
| Request-response | Simpler `_generating` guards: tester generates requests, checks responses |
| Stateless | Minimal inter-event state, mostly message-level validity checks |
| P2P symmetric | One behavioral spec for both roles, same constraints regardless |
| Complex state machine | Boolean relations per state per session, transition actions, FSM guards |

### Build Order

1. **Extract RFC requirements** — walk through spec, tag each MUST/SHALL as universal/tester/IUT.
2. **Main event specification** — `around` block for primary event, starting with 3-5 core requirements. Compile and test. Add incrementally.
3. **Sub-event specifications** — `before` advice on message-type handlers with `_generating` guards.
4. **Role-specific behavioral files** — one per tested role, constraining the tester's behavior.
5. **Integration test** — run against a real or known-good implementation. Verify pass/fail results.

### Debugging Failing Requirements

When a `require` fires, the test binary prints the source location:
```
FAIL: require at {proto}_message.ivy:42
```

Debugging methodology:
1. **Identify which `require`** — the line number points to the exact constraint.
2. **Add `import action show_*` for observability** — declare debug output actions and call them before the failing `require` to see the state. The QUIC model does this extensively (e.g., `import action show_queued_frames(scid:cid, frames:frame.arr)` in `quic_packet.ivy:402`).
3. **Bisect by commenting out requirements** — temporarily comment out groups of `require` statements to isolate which constraint is too strict or which state is wrong.
4. **Check `_generating` guards** — a common bug is a `require` that should be guarded by `_generating` but isn't, causing it to fire on IUT events that don't need that constraint.

### Common Failure Modes

- **Test never progresses** (e.g., handshake never completes): missing `export` or action weight too low.
- **Test always fails immediately**: `require` too strict — the IUT does something valid that the model rejects. Add `import action show_*` to inspect state.
- **Test always passes**: `require` too loose or `_finalize` doesn't check enough.
- **Test fails nondeterministically**: the random exploration sometimes takes paths that reveal real bugs and sometimes doesn't. Increase `test_iters` or add action weights.

### Checkpoint

Run the compiled binary against a real implementation:
```bash
./{proto}_{role}_test seed=42 test_iters=100 server_addr=... client_addr=...
```
The test should produce event traces on stdout and terminate with either normal completion (pass) or a `require` failure (fail with line number). User confirms that failures represent genuine spec violations (not model bugs) and that passes involve meaningful protocol exchanges. User reviews the requirement-to-`require` mapping.

---

## Phase 6: Test Scenarios

### Purpose

Create top-level test files that compose everything into runnable test cases.

### Ivy Concepts Taught

- **`export` declarations**: tell the Ivy runtime which actions to randomly invoke during testing
- **Action weights**: `attribute action.weight = "5"` biases random exploration (higher = more frequent)
- **`_finalize`**: special action called by the Ivy runtime when test iterations are exhausted. Used for end-of-test assertions. Without it, a test that exchanged zero messages would still pass.
- **Test file structure**: includes + `after init` socket setup + exports + `_finalize`

### QUIC Model References

- Basic test: `quic_tests/server_tests/quic_server_test.ivy` — 72 lines: includes, exports, init, finalize
- Feature test: `quic_tests/server_tests/quic_server_test_0rtt.ivy` — adds 0-RTT exports and config
- Error test: `quic_tests/server_tests/quic_server_test_tp_error.ivy` — intentionally invalid transport parameters
- Attack test: `quic_tests/mim_tests/quic_mim_test_forward.ivy` — includes MiM shim, exports forwarding actions

### Role Inversion in Test Files

This is critical: a test targeting a server includes the **client** shim and **client** behavior, because Ivy acts as the opposite role. From `quic_server_test.ivy`:
```ivy
#lang ivy1.7
include ivy_quic_shim_client        # NOT shim_server — Ivy acts as client
include ivy_quic_client_behavior    # NOT server_behavior
include ivy_quic_client_standard_tp # Client transport parameters
```

### Test Scenario Taxonomy

#### Category 1: Basic Conformance

Minimum viable test per role. Standard behavioral spec, standard config, core action exports. Corresponds to `quic_server_test.ivy`.

```ivy
#lang ivy1.7
include order
include {proto}_infer              # inference engine (if applicable)
include file
include ivy_{proto}_shim_{opposite_role}   # Role inversion!
include {proto}_locale
include ivy_{proto}_{opposite_role}_behavior
include ivy_{proto}_{opposite_role}_standard_config

after init {
    sock := net.open(endpoint_id.{opposite_role}, {opposite_role}.ep);
    {opposite_role}.set_tls_id(0);  # if crypto
    {tested_role}.set_tls_id(1);    # if crypto
    # ... protocol-specific setup
}

export message_event
export {sub_event_handles}

export action _finalize = {
    require {meaningful_exchange_happened};
}
```

#### Category 2: Feature-Specific

Small deltas from basic test: add an export, swap a config, add a `before` constraint. One per protocol feature of interest.

#### Category 3: Error Handling

Intentionally invalid configs or messages. `_finalize` asserts specific error was produced. Tests that IUT correctly rejects invalid input.

#### Category 4: Attack Tests (Conditional)

Requires:
1. **Forged message type** in `{proto}_attacks_stack/` — same struct as normal message but with relaxed constraints (e.g., raw `protected_payload` instead of decoded fields).
2. **Attack actions** — `forged_message_event`, `replay_message_event`, `forward_to_{role}_event`. Each has `around` advice enforcing attacker capabilities.
3. **Attacker entity** — MiM (two sockets, configurable forwarding/replay/modification booleans) or direct attacker (single socket).
4. **Attack test file** — includes both normal shim and attack shim, exports both normal and attack actions.

QUIC reference: `quic_attacks_stack/forged_quic_packet.ivy` defines forged packet types. `quic_entities/ivy_quic_mim.ivy` defines MiM entity with `is_mim`, `forward_packets`, `modify_packets`, `replay_packets` booleans. `quic_tests/mim_tests/quic_mim_test_forward.ivy` exports `forward_packet_to_client_event` and `forward_packet_to_server_event` alongside normal protocol actions.

### Build Order

1. **Basic conformance test per role** — write, compile, run. Tune weights until test reaches meaningful states.
2. **Feature-specific tests** — one at a time, incremental deltas from basic test.
3. **Error handling tests** — invalid configs, verify IUT rejects them.
4. **Attack tests** — build attack stack, create attacker entities, write test files.

### Checkpoint

Run the full test suite:
```bash
for test in {proto}_tests/**/*.ivy; do
    ivyc target=test test_iters=100 "$test"
    ./$(basename "$test" .ivy) seed=42 server_addr=... client_addr=...
done
```
User reviews pass/fail results. To distinguish model bugs from real spec violations: if a test fails on a known-good implementation, the model is too strict (fix the `require`). If it passes on a known-buggy implementation, the model is too loose (add `require` constraints).

---

## Ivy Language Quick Reference

Collected from all phases for skill users to reference:

| Construct | Syntax | Purpose |
|---|---|---|
| Type (abstract) | `type query_id` | Declare a new type |
| Type (bit-vector) | `interpret query_id -> bv[16]` | Give type a concrete representation for compilation |
| Enumeration | `type rcode = {noerror, formerr}` | Finite set of values |
| Alias | `alias aid = cid` | Type alias |
| Definition | `definition zero = 0` | Named constant |
| Struct | `type this = struct { f : T }` | Composite data type |
| Variant | `variant this of base = struct { f : T }` | Subtype of a base type (dispatched at runtime) |
| Array | `instance arr : array(idx, this)` | Array type for a struct |
| Relation | `relation seen(C:cid)` | Boolean predicate |
| Function | `function count(C:cid) : nat` | Value mapping |
| Individual | `individual ep : ip.endpoint` | Singleton value (scoped to module instance) |
| Parameter | `parameter addr : ip.addr = 0x0a000001` | Command-line-settable value |
| Action | `action event(src, dst, msg) = {}` | Protocol event (body defined by advice) |
| Import action | `import action show_debug(x:T)` | Action implemented in C++ (for debug output) |
| Around advice | `around event(params) { ... }` | Wrap action with pre/post conditions |
| Before advice | `before event(params) { ... }` | Precondition check |
| After advice | `after event(params) { ... }` | Side effect / state update |
| Require | `require expr` | Assertion (test fails if false) |
| Not / And / Or | `~expr`, `e1 & e2`, `e1 \| e2` | Boolean operators |
| `_generating` | `if _generating { ... }` | Guard for tester-generated events |
| Export | `export action_name` | Make action available to random testing |
| Weight | `attribute action.weight = "5"` | Bias random selection (higher = more frequent) |
| Finalize | `export action _finalize = { ... }` | End-of-test assertions (called by runtime) |
| Module | `module name(params) = { ... }` | Parameterized code template |
| Instance | `instance x : module(args)` | Module instantiation |
| Include | `include filename` | Textual file insertion (no `.ivy` suffix) |
| Init | `after init { ... }` | Initialization block |

## panther_ivy Infrastructure Reuse

The skill assumes these panther_ivy built-in modules are available:

| Module | Provides | Used In |
|---|---|---|
| `ip` | `ip.endpoint`, `ip.addr`, `ip.port`, `ip.udp`, `ip.lo`, `ip.ivy` (interface types) | Entity setup |
| `net` | `net.open`, `net.send`, `net.recv`, `net.socket` | Shim I/O |
| `tls_api` | `tls_api.id`, `tls_api.upper.create`, TLS handshake, key exchange | Crypto-enabled protocols |
| `prot` | `prot.encrypt`, `prot.decrypt`, `prot.arr` (instantiated from protection module) | Packet protection |
| `serdes` | Serialization/deserialization framework | `{proto}_utils/` ser/deser |
| `collections` | Sequences, arrays, maps (included transitively) | Data structures |
| `order` | Ordered types, comparison | Sorting, ranges |
| `random_value` | Nondeterministic value generation (`random_stream_pos`, `random_microsecs`) | Config, behavioral specs |
| `byte_stream` | Byte array utilities | Serialization helpers |
| `file` | File I/O for logging | Test output |
| `time_api` | `c_timer`, `chrono_timer`, `now_millis_last_bp`, timestamps | Timeout testing |
| `{proto}_locale` | Network locale setup (per-protocol, created in `{proto}_utils/`) | Entity wiring |

Note: modules resolve from the Ivy include path (`$PYTHON_IVY_DIR/ivy/include/1.7/`). The working directory must be set correctly for includes to resolve.

---

## Skill Implementation Plan

Based on reviewer feedback, the skill should be structured for progressive disclosure.

### File Structure

```
ivy-protocol-model-builder/
  SKILL.md                              # ~800 words: overview, phase map, checkpoints
  references/
    phase-1-classification.md           # Protocol profiling questions, pattern selection
    phase-2-blueprint.md                # File tree templates, module DAG, type mapping
    phase-3-core-types.md               # Ivy type system tutorial + build order
    phase-4-entity-model.md             # Endpoint/shim/serialization/behavior patterns
    phase-5-behavioral-specs.md         # around/require/_generating tutorial + RFC extraction
    phase-6-test-scenarios.md           # Test taxonomy, export/weight/finalize patterns
    ivy-quick-reference.md              # Language reference table
    panther-ivy-infrastructure.md       # Built-in module table
  examples/
    dns_types.ivy                       # Minimal worked example: DNS types file
```

### Key Design Decisions

- **One skill, progressive disclosure**: SKILL.md stays lean (~800 words) and points to phase-specific reference files. Only the current phase's reference is loaded into context at a time.
- **Protocol profile resolves all branches**: Phase 1 produces a protocol profile document. Each subsequent phase consults the profile rather than embedding inline if/else conditionals.
- **Explicit stop directives**: each phase reference file ends with "STOP. Present output to user. Do NOT proceed until user confirms."
- **Standalone skill**: does not depend on superpowers:brainstorming or superpowers:executing-plans, but cross-references them for users who want to use them.
- **Worked example**: a minimal DNS-over-UDP types file threads through the spec to ground abstract patterns.

### Trigger Patterns

The skill should activate when the user asks to "create an Ivy model", "build a formal spec for a protocol", "add a new protocol to panther_ivy", "write Ivy tests for [protocol name]", or "formalize [protocol] in Ivy".

### Tool Requirements

- **Write** for creating `.ivy` files
- **Bash** for `ivy_check` and `ivyc target=test` compilation
- **Read** for consulting QUIC reference files
- **Grep** for searching existing Ivy patterns

### Prerequisites

- panther_ivy submodule initialized (`git submodule update --init panther/plugins/services/testers/panther_ivy`)
- Docker environment available for `ivyc target=test` compilation
- At least one real protocol implementation to test against (for Phases 5-6)
- The QUIC reference model at `panther/plugins/services/testers/panther_ivy/protocol-testing/quic/`

## Skill Metadata

- **Name**: ivy-protocol-model-builder
- **Type**: Rigid (follow phases exactly, checkpoints are mandatory)
- **Estimated phases**: 6 phases, each 1-3 sessions depending on protocol complexity
- **Output**: A complete `protocol-testing/{proto}/` directory with compilable, runnable Ivy test suite
