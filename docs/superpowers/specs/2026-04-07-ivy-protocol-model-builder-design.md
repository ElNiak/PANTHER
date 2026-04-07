# Ivy Protocol Model Builder — Skill Design Spec

**Date**: 2026-04-07
**Status**: Draft
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
- `quic_entities/` — endpoint definitions (client, server, MiM, attacker, victim)
- `quic_entities_behavior/` — role-specific behavioral constraints
- `quic_shims/` — bridges between the formal model and real network I/O
- `quic_config/` — transport parameter configurations
- `quic_tests/` — ~95 test specifications (conformance, feature-specific, error handling, attack)
- `quic_attacks_stack/` — forged/replayed/modified message types
- `quic_recovery/` — loss recovery and congestion control models
- `quic_fsm/` — finite state machine models for stream states

The model evolved over 4+ years from a monolithic QUIC-only tool (2021) to the current compositional architecture.

## Approach

Hybrid of pattern catalog with protocol classification (to handle diverse protocol shapes) and incremental model building (to teach Ivy constructs hands-on). The classification determines which architectural patterns apply; each phase builds incrementally with compile-check-review cycles.

---

## Phase Structure

Six phases with checkpoints:

| Phase | Name | Output | Checkpoint |
|-------|------|--------|------------|
| 1 | Protocol Classification | Protocol profile document | User confirms classification |
| 2 | Blueprint Generation | File list, module graph, type mappings | User approves architecture |
| 3 | Core Types and Stack | Compilable `.ivy` files for types, messages, state | `ivy_check` passes |
| 4 | Entity Model | Endpoint modules, shim bridges, serialization | Compiles with `ivyc target=test` |
| 5 | Behavioral Specs | Role-specific constraints, `_generating` guards | First test runs against real impl |
| 6 | Test Scenarios | Conformance tests, attack models, finalization | Full test suite passes |

Each phase begins with an Ivy tutorial section that teaches exactly the constructs needed, using the QUIC model as reference.

---

## Phase 1: Protocol Classification

### Purpose

Determine the protocol's shape through 5-7 concrete questions to produce a protocol profile that drives all subsequent phases.

### Classification Questions

1. **Communication pattern**: Client-server (one side initiates), peer-to-peer (either side initiates), or request-response (stateless exchanges)?
2. **Connection model**: Persistent connections with state, or independent message exchanges?
3. **Message structure**: Fixed-format binary, variable-format (TLV/tagged), text-based, or other?
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
Messages: [format description]
Security: [security model]
States: [count] ([brief description])
Testing goals: [selected goals]
```

### Pattern Selection

The profile maps to which QUIC model architectural elements apply:

| Profile Trait | Effect |
|---|---|
| Stateless protocol | Skip connection state tracking, no FSM directory |
| No own crypto | Skip protection/security files, shims pass plaintext |
| P2P / symmetric | Single entity module with symmetric instantiation, shared shim |
| Simple state machine | Inline state in stack module, no separate FSM files |
| Complex state machine | Separate `{proto}_fsm/` directory with per-role FSM files |
| Attack testing desired | Add `{proto}_attacks_stack/` directory |
| Layered on another protocol | Shims interface with underlying protocol API, not raw UDP |
| Request-response | Simpler `_generating` guards, minimal inter-event state |

### Checkpoint

User reviews and confirms the protocol profile and pattern selection.

---

## Phase 2: Blueprint Generation

### Purpose

Produce a concrete file architecture adapted to the protocol profile.

### Ivy Concepts Taught

- `include` composition (textual insertion, not module import)
- `#lang ivy1.7` file header
- Include DAG flows one direction: test files include everything transitively

### Blueprint Template

Directory tree adapted from the QUIC model based on classification:

```
protocol-testing/{proto}/
+-- {proto}_stack/                    # Core protocol model
|   +-- {proto}_types.ivy             # Base types, enums, bit-vector interpretations
|   +-- {proto}_message.ivy           # Message structs + message_event actions
|   +-- {proto}_state.ivy             # State tracking (relations, functions, after init)
|   +-- {proto}_connection.ivy        # Aggregator: includes all stack files in order
+-- {proto}_entities/                 # Network endpoints
|   +-- {proto}_endpoint.ivy          # Parameterized endpoint modules
|   +-- ivy_{proto}_{role_a}.ivy      # Role A entity instantiation
|   +-- ivy_{proto}_{role_b}.ivy      # Role B entity instantiation
+-- {proto}_entities_behavior/        # Role-specific constraints
|   +-- ivy_{proto}_{role_a}_behavior.ivy
|   +-- ivy_{proto}_{role_b}_behavior.ivy
+-- {proto}_shims/                    # Wire format bridges
|   +-- {proto}_shim.ivy              # Base shim (central composition point)
|   +-- ivy_{proto}_shim_{role_a}.ivy # Role A send/receive
|   +-- ivy_{proto}_shim_{role_b}.ivy # Role B send/receive
+-- {proto}_config/                   # Parameter configurations
|   +-- ivy_{proto}_standard_config.ivy
+-- {proto}_tests/                    # Test specifications
|   +-- {role_b}_tests/              # Tests targeting role B (Ivy acts as role A)
|   |   +-- {proto}_{role_b}_test.ivy
|   +-- {role_a}_tests/              # Tests targeting role A (Ivy acts as role B)
|       +-- {proto}_{role_a}_test.ivy
+-- {proto}_attacks_stack/            # (conditional on classification)
    +-- forged_{proto}_message.ivy
```

Simplifications based on classification:
- Stateless: no `_state.ivy`, no `_connection.ivy` aggregator (types + message suffice)
- No attacks: omit `_attacks_stack/`
- P2P: single entity file, single shim
- No FSM: omit `_fsm/` directory
- No crypto: omit protection/security files

### Module Dependency Graph

The skill produces a DAG showing include relationships, flowing from test files down through shims to the stack.

### Type Mapping Table

A mapping from RFC concepts to Ivy constructs:

```
RFC Concept              -> Ivy Construct               -> File
[protocol-specific ID]   -> type {name}                 -> {proto}_types.ivy
[message type enum]      -> type {name} = {v1, v2, ...} -> {proto}_types.ivy
[message format]         -> object {name} = struct{...}  -> {proto}_message.ivy
[protocol event]         -> action {name}_event(src,dst) -> {proto}_message.ivy
[session state]          -> relation {name}(S:session_id)-> {proto}_state.ivy
```

### Checkpoint

User reviews file tree, dependency graph, and type mapping table. Approves before any `.ivy` files are written.

---

## Phase 3: Core Types and Stack

### Purpose

Write the first compilable `.ivy` files: types, message structures, state tracking.

### Ivy Concepts Taught

- **Scalar types**: `type query_id` (abstract), `interpret query_id -> bv[16]` (bit-vector)
- **Enumerations**: `type rcode = {noerror, formerr, servfail, nxdomain}`
- **Structs**: `type this = struct { field : type, ... }` inside an `object` block
- **`this` keyword**: means "the enclosing object's type"
- **Arrays**: `instance idx : unbounded_sequence` + `instance arr : array(idx, this)`
- **Variants**: `variant this of base_type = struct { ... }` for tagged unions (frame-like sub-types)
- **Relations**: `relation name(X:type)` — boolean predicates over typed parameters
- **Functions**: `function name(X:type) : return_type` — mappings
- **`after init` blocks**: initialize all relations to false, functions to defaults
- **Actions with empty bodies**: `action event_name(params) = {}` — behavior defined by advice elsewhere

### QUIC Model References

- Types: `quic_types.ivy` — `cid`, `pkt_num`, `version`, `quic_packet_type` enum
- Structs: `quic_packet.ivy:94-102` — `quic_packet` struct with ptype, dst_cid, src_cid, seq_num, payload
- Variants: `quic_frame.ivy:47-83` — `frame.ping`, `frame.ack`, `frame.stream` as variants of `frame`
- State: `quic_packet.ivy:229-329` — `conn_seen`, `sent_pkt`, `last_pkt_num`, `connected`, etc.
- Aggregator: `quic_connection.ivy` — includes all stack files in dependency order
- Actions: `quic_packet.ivy:137` — `action packet_event(src, dst, pkt) = {}`

### Build Order

1. **Types file** — scalars, enums, bit-vector interpretations. No dependencies. Compile with `ivy_check`.
2. **Message struct file** — struct definitions, array instances, main event action. Includes types.
3. **Sub-message types** (if variants needed) — frame-like sub-structures. Skip for single-message protocols.
4. **State tracking file** — relations, functions, `after init` block. Includes types.
5. **Aggregator file** — includes all stack files in correct order. Single entry point for the shim layer.

### What This Phase Does NOT Do

No `around`/`require` specifications. No entity definitions. No serialization. The stack defines the data model and declares events with empty bodies. Specification logic comes in Phase 5.

### Checkpoint

All files pass `ivy_check`. User reviews and confirms type mappings match the RFC.

---

## Phase 4: Entity Model

### Purpose

Create endpoints that send/receive protocol messages and the shim bridges connecting the formal model to real network I/O.

### Ivy Concepts Taught

- **Modules**: `module client_ep(address:ip.addr, port:ip.port) = { ... }` — parameterized code templates
- **`instance`**: `instance server : endpoint.server_ep(addr, port)` — module instantiation
- **`individual`**: singleton values scoped to a module instance (like global variables)
- **The `ip` module**: built-in panther_ivy infrastructure for `ip.endpoint`, `ip.addr`, `ip.port`, `net.open`, `net.send`
- **The `behavior` action**: the receive path that deserializes incoming bytes into Ivy structs

### QUIC Model References

- Endpoint module: `quic_endpoint.ivy:27-80` — `client_ep` module with socket setup and `behavior` action
- Entity file: `ivy_quic_server.ivy` — instantiates `quic_endpoint.server_ep(server_addr, server_port)`
- Base shim: `quic_shim.ivy` — central composition point including stack, entities, serialization
- Role shim: `ivy_quic_shim_server.ivy:39-56` — `after packet_event` serializes and sends via `net.send`

### Entity Pattern (Three Layers Per Role)

1. **Endpoint module** (`{proto}_endpoint.ivy`): parameterized module with `individual` socket, `after init` setup, `behavior` action for receive path.
2. **Entity file** (`ivy_{proto}_{role}.ivy`): declares parameters (address, port), instantiates endpoint module, includes shim.
3. **Shim file** (`ivy_{proto}_shim_{role}.ivy`): implements `after message_event` for serialize+send, delegates incoming bytes to `behavior` for deserialize.

### Adaptation by Protocol Shape

| Shape | Entity Pattern |
|---|---|
| Client-server | Asymmetric: separate client_ep and server_ep modules |
| P2P | Symmetric: single peer_ep module, instantiated multiple times |
| Stateless | Simplified behavior action: no connection tracking, just message parse |
| Layered on QUIC | Shim reads from QUIC streams instead of raw UDP sockets |

### Serialization Strategy

Two approaches:
- **Pass-through** (for early prototyping): skip ser/deser, pass Ivy structs directly. Works for `ivy_check` but not runnable tests.
- **Full ser/deser** (for real implementation testing): field-by-field byte packing/unpacking. Protocol-specific, maps to wire format.

The skill recommends starting with pass-through, validating the model logically through Phase 5, then implementing full ser/deser before Phase 6's integration tests against real implementations. The transition point is explicit: Phase 5 step 5 ("Integration test with stub") requires full ser/deser to be in place. If the user is only doing model validation (no real implementation testing), pass-through is sufficient for all phases.

### Build Order

1. **Endpoint module** — parameterized modules per role, `individual` declarations, `after init`.
2. **Entity files** — one per role, instantiate endpoint modules.
3. **Base shim** — central composition point, includes stack aggregator + all entities + serialization.
4. **Role-specific shims** — `after message_event` for outgoing, receive callback for incoming.
5. **Serialization** (if targeting real impl testing) — `{proto}_ser.ivy` and `{proto}_deser.ivy`.

### Checkpoint

Full model compiles with `ivyc target=test`. Compiled binary can be invoked (no meaningful behavior yet). User reviews entity architecture and shim wiring.

---

## Phase 5: Behavioral Specs

### Purpose

Translate RFC requirements into machine-checkable constraints. This is the heart of the formal model.

### Ivy Concepts Taught

- **`around`/`before`/`after` advice**: attach preconditions, postconditions, and state updates to actions declared elsewhere
- **`require` statements**: `require expr` fails the test if `expr` is false. Each maps to an RFC MUST/SHALL.
- **`_generating` predicate**: built-in boolean. `true` when Ivy runtime generates events (tester role), `false` when observing events from the IUT.
- **Role inversion**: testing a server means Ivy acts as a client. `ivy_{proto}_{tested_role}_behavior.ivy` constrains the tester's opposite role.
- **The dual-role specification pattern**:
  ```ivy
  around message_event(src, dst, msg) {
      if _generating {
          # Constraints on tester-generated traffic (ensure validity)
      };
      # Universal constraints (RFC requirements for all senders)
      if ~_generating {
          # Constraints on IUT traffic (spec violations = test failures)
      };
      ...
      # State updates (apply to all events)
  }
  ```

### QUIC Model References

- Main event spec: `quic_packet.ivy:405-600` — `around packet_event` with ~200 lines of `require` statements, `_generating` guards, and state updates
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

### Common Failure Modes

- **Test never progresses** (e.g., handshake never completes): missing `export` or action weight too low.
- **Test always fails immediately**: `require` too strict — the IUT does something valid that the model rejects.
- **Test always passes**: `require` too loose or `_finalize` doesn't check enough.

### Checkpoint

Model compiles, runs against at least one real implementation, produces meaningful pass/fail. User confirms requirement-to-`require` mapping.

---

## Phase 6: Test Scenarios

### Purpose

Create top-level test files that compose everything into runnable test cases.

### Ivy Concepts Taught

- **`export` declarations**: tell the Ivy runtime which actions to randomly invoke
- **Action weights**: `attribute action.weight = "5"` biases random exploration
- **`_finalize`**: special action for end-of-test assertions
- **Test file structure**: includes + `after init` socket setup + exports + `_finalize`

### QUIC Model References

- Basic test: `quic_server_test.ivy` — 72 lines: includes, exports, init, finalize
- Feature test: `quic_server_test_0rtt.ivy` — adds 0-RTT exports and config
- Error test: `quic_server_test_tp_error.ivy` — intentionally invalid transport parameters
- Attack test: `quic_mim_test_forward.ivy` — includes MiM shim, exports forwarding actions

### Test Scenario Taxonomy

#### Category 1: Basic Conformance

Minimum viable test per role. Standard behavioral spec, standard config, core action exports. Corresponds to `quic_server_test.ivy`.

```ivy
#lang ivy1.7
include ivy_{proto}_shim_{role_a}
include ivy_{proto}_{role_a}_behavior
include ivy_{proto}_standard_config

after init {
    sock := net.open(endpoint_id.{role_a}, {role_a}.ep);
    # ... protocol-specific setup
}

export message_event
export {additional_actions}

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
1. **Forged message type** in `{proto}_attacks_stack/` — same struct as normal message but with relaxed constraints (e.g., raw payload instead of decoded fields).
2. **Attack actions** — `forged_message_event`, `replay_message_event`, `forward_to_{role}_event`. Each has `around` advice enforcing attacker capabilities.
3. **Attacker entity** — MiM (two sockets, configurable forwarding/replay/modification) or direct attacker (single socket).
4. **Attack test file** — includes both normal shim and attack shim, exports both normal and attack actions.

QUIC reference: `forged_quic_packet.ivy` defines forged packet types. `ivy_quic_mim.ivy` defines MiM entity. `quic_mim_test_forward.ivy` exports forwarding actions alongside normal protocol actions.

### Build Order

1. **Basic conformance test per role** — write, compile, run. Tune weights until test reaches meaningful states.
2. **Feature-specific tests** — one at a time, incremental deltas from basic test.
3. **Error handling tests** — invalid configs, verify IUT rejects them.
4. **Attack tests** — build attack stack, create attacker entities, write test files.

### Checkpoint

Full test suite runs against at least one real implementation. User reviews pass/fail results, confirms failures represent genuine spec violations.

---

## Ivy Language Quick Reference

Collected from all phases for skill users to reference:

| Construct | Syntax | Purpose |
|---|---|---|
| Type (abstract) | `type query_id` | Declare a new type |
| Type (bit-vector) | `interpret query_id -> bv[16]` | Give type a concrete representation |
| Enumeration | `type rcode = {noerror, formerr}` | Finite set of values |
| Struct | `type this = struct { f : T }` | Composite data type |
| Variant | `variant this of base = struct { f : T }` | Tagged union member |
| Array | `instance arr : array(idx, this)` | Array type for a struct |
| Relation | `relation seen(C:cid)` | Boolean predicate |
| Function | `function count(C:cid) : nat` | Value mapping |
| Individual | `individual ep : ip.endpoint` | Singleton value |
| Action | `action event(src, dst, msg) = {}` | Protocol event (body defined by advice) |
| Around advice | `around event(params) { ... }` | Wrap action with pre/post conditions |
| Before advice | `before event(params) { ... }` | Precondition check |
| After advice | `after event(params) { ... }` | Postcondition / state update |
| Require | `require expr` | Assertion (test fails if false) |
| `_generating` | `if _generating { ... }` | Guard for tester-generated events |
| Export | `export action_name` | Make action available to random testing |
| Weight | `attribute action.weight = "5"` | Bias random selection |
| Finalize | `export action _finalize = { ... }` | End-of-test assertions |
| Module | `module name(params) = { ... }` | Parameterized code template |
| Instance | `instance x : module(args)` | Module instantiation |
| Include | `include filename` | Textual file insertion |
| Init | `after init { ... }` | Initialization block |

## panther_ivy Infrastructure Reuse

The skill assumes these panther_ivy built-in modules are available:

| Module | Provides | Used In |
|---|---|---|
| `ip` | `ip.endpoint`, `ip.addr`, `ip.port`, `ip.udp` | Entity setup |
| `net` | `net.open`, `net.send`, `net.recv`, `net.socket` | Shim I/O |
| `tls_api` | TLS handshake, key exchange, encryption | Crypto-enabled protocols |
| `prot` | `prot.encrypt`, `prot.decrypt`, `prot.arr` | Packet protection |
| `collections` | Sequences, arrays, maps | Data structures |
| `order` | Ordered types, comparison | Sorting, ranges |
| `random_value` | Nondeterministic value generation | Config, behavioral specs |
| `file` | File I/O for logging | Test output |
| `time_api` | `c_timer`, `chrono_timer`, timestamps | Timeout testing |

## Skill Metadata

- **Name**: ivy-protocol-model-builder
- **Type**: Rigid (follow phases exactly, checkpoints are mandatory)
- **Prerequisites**: panther_ivy Docker environment, at least one real protocol implementation to test against
- **Estimated phases**: 6 phases, each 1-3 sessions depending on protocol complexity
- **Output**: A complete `protocol-testing/{proto}/` directory with compilable, runnable Ivy test suite
