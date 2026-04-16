# BGP Scenario Builder — Design Spec

**Date:** 2026-04-16
**Status:** Draft
**Goal:** Eliminate per-test Z3 solver workarounds by introducing scenario-driven message generation for the BGP Ivy formal model.

## Problem

Z3 (the SMT solver used by Ivy for test generation) cannot:
1. Construct arrays to target lengths (NLRI `route_prefix.end = 3`)
2. Reason through while-loop array iteration (AS_PATH segment validation)
3. Reliably select complex multi-step action sequences (handle → handle → handle → UPDATE)

Current workaround: each test file contains inline `before` blocks with hardcoded concrete values that bypass Z3's limitations. This is:
- Non-reusable (each test duplicates 15-20 lines of solver hints)
- Fragile (hints must stay in sync with model `around` block changes)
- Inflexible (hardcoded to a single message variant per test)

## Approach: Scenario-Driven Generation (Approach E)

Z3 picks from a **finite set of scenarios** (small enum). The model deterministically constructs the full message for each scenario. Z3 only solves what it's good at: finite enumeration and FSM timing.

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hint location | In the model (generation guards) | Single source of truth; no drift between test and model |
| Handle actions | Absorbed into builder (Path B) | Handles exist for receive-side RFC validation; generation side constructs attrs directly |
| Scenario extensibility | Fixed in model, not per-test | Scenarios represent RFC-valid message templates; tests select which scenarios to enable |
| Receive-side validation | Unchanged | Original `around` blocks with full RFC constraints validate IUT responses |

## Architecture

### New Files

```
bgp_stack/
├── bgp_scenario.ivy              # Scenario type definitions
└── bgp_scenario_builder.ivy      # Builder actions (one per message type)
```

### Scenario Types

```ivy
# bgp_scenario.ivy

# UPDATE scenarios — each represents a complete RFC-valid UPDATE template
type update_scenario = {
    announce_single,        # Single /24 route, ORIGIN=IGP, empty AS_PATH, self NEXT_HOP
    announce_multihop,      # Single /24 route with 3-hop AS_PATH
    withdraw_single,        # Withdraw a previously announced prefix
    replace_route,          # Re-announce same prefix with different ORIGIN (implicit withdraw)
    empty_update            # End-of-RIB marker (no NLRI, no withdrawn, no path attrs)
}
interpret update_scenario -> bv[3]

# OPEN scenarios
type open_scenario = {
    standard_open,          # BGP-4, hold_time=180, no capabilities
    open_4byte_as           # BGP-4 with 4-octet AS capability
}
interpret open_scenario -> bv[1]

# NOTIFICATION scenarios
type notification_scenario = {
    cease_notification,     # Administrative shutdown
    header_error,           # Message header error
    update_error            # UPDATE message error
}
interpret notification_scenario -> bv[2]
```

### Builder Actions

Each builder action:
1. Checks FSM preconditions (Z3 must satisfy these)
2. Constructs the message deterministically from the scenario
3. Sets model state (attr-present flags, queued data)
4. Fires the original message event (triggers monitors and serialization)

```ivy
# bgp_scenario_builder.ivy

include bgp_scenario

# ── UPDATE Builder ──────────────────────────────────────────────

action generate_update(src:bgp_id, dst:bgp_id, scenario:update_scenario)

implement generate_update {
    # FSM precondition — the only thing Z3 must solve
    require conn_state(src) = bgp_connection_state.established;
    require open_message_recv(src) & open_message_recv(dst);

    # Path B: directly set attr-present flags (bypass handles)
    origin_present(src) := true;
    as_path_present(src) := true;
    next_hop_present(src) := true;

    # Scenario-specific message construction
    var msg : bgp_update_message;
    msg.withdraw_routes_len := 0;
    msg.withdraw_routes := withdraw_route.arr.empty;

    if scenario = announce_single {
        # ORIGIN=IGP [rfc4271:5.1.1]
        # AS_PATH=empty AS_SEQUENCE (locally originated) [rfc4271:5.1.2]
        # NEXT_HOP=self [rfc4271:5.1.3]
        # NLRI=192.168.1.0/24 [rfc4271:4.3]
        call _build_announce_single(src, dst, msg);
    };
    if scenario = announce_multihop {
        # ORIGIN=IGP, AS_PATH=[AS_SEQUENCE: AS1, AS2, AS3], NLRI=10.0.0.0/24
        call _build_announce_multihop(src, dst, msg);
    };
    if scenario = withdraw_single {
        # Withdrawn routes: 192.168.1.0/24, no NLRI, no path attrs
        call _build_withdraw_single(src, dst, msg);
    };
    if scenario = replace_route {
        # Same NLRI as announce_single but ORIGIN=EGP (implicit withdraw)
        call _build_replace_route(src, dst, msg);
    };
    if scenario = empty_update {
        # End-of-RIB marker [rfc4271:4.3]
        call _build_empty_update(src, dst, msg);
    };

    # Fire the original event — triggers monitors, serialization, shim
    call bgp_update_message_event(src, dst, msg);
}

# Private helper actions for each scenario
action _build_announce_single(src:bgp_id, dst:bgp_id, msg:bgp_update_message)
action _build_announce_multihop(src:bgp_id, dst:bgp_id, msg:bgp_update_message)
action _build_withdraw_single(src:bgp_id, dst:bgp_id, msg:bgp_update_message)
action _build_replace_route(src:bgp_id, dst:bgp_id, msg:bgp_update_message)
action _build_empty_update(src:bgp_id, dst:bgp_id, msg:bgp_update_message)

# NOTE: Each _build_* helper populates msg fields and queued_path_attr(src)
# using concrete RFC-compliant values. Implementation details (exact byte
# values, path_attr_size computation) are deferred to the implementation plan.
# The key constraint: the msg must pass all `require` checks in the
# existing `around bgp_update_message_event` block.
```
```

### Test File Structure (After)

```ivy
# bgp_speaker_test_update.ivy (redesigned)

include order
include file
include bgp_shim
include ivy_bgp_speaker_behavior
include bgp_scenario_builder      # <-- new include

relation update_sent
relation session_established
relation keepalive_sent

after init {
    # TCP setup only — no solver hints needed
    getsock(bgp_impl_instance.ep.addr) := net.connect_accept(...);
    pend(bgp_impl_instance.ep.addr) := true;
    update_sent := false;
    session_established := false;
    keepalive_sent := false;
    acceptable_error(bgp_error_code.hold_timer_expire) := true;
    acceptable_error(bgp_error_code.fsm_error) := true;
}

# KEEPALIVE gate: allow one, then block until UPDATE sent
before bgp_keepalive_message_event(src, dst, bgp_message) {
    if _generating {
        require ~keepalive_sent | ~session_established | update_sent;
    }
}

# No NOTIFICATION generation
before bgp_notification_message_event(src, dst, bgp_message) {
    if _generating { require false; }
}

after bgp_keepalive_message_event {
    if _generating { keepalive_sent := true; };
    if ~_generating { session_established := true; }
}

after generate_update {
    if _generating { update_sent := true; }
}

# 3 exports (was 7) — Z3 converges faster
export bgp_open_message_event
export bgp_keepalive_message_event
export generate_update

export action _finalize = {
    require update_sent;
    require ~received_unexpected_notification;
}
```

### Receive-Side (Unchanged)

The original `around bgp_update_message_event` in `bgp_update_message.ivy` stays exactly as-is. When FRR sends an UPDATE:
1. The shim deserializes it
2. `bgp_update_message_event` fires with `~_generating`
3. The `around` block validates per RFC (all existing `require` checks)
4. Monitors fire (coverage annotations, error tracking)

The builder's `call bgp_update_message_event(src, dst, msg)` also goes through the `around` block, but since the builder constructed a valid message, all `require` checks pass.

### Model State Changes

The `around bgp_update_message_event` needs a generation guard to skip array-based constraints when the message comes from the builder:

```ivy
around bgp_update_message_event(src, dst, bgp_message) {
    require isup(bgpid_to_endpoint(src));
    require open_message_recv(src) & open_message_recv(dst);
    require origin_present(src);
    require as_path_present(src);
    require next_hop_present(src);
    require bgp_message.total_path_attr_len = path_attr_size(src);
    require bgp_message.path_attrs = queued_path_attr(src);

    if ~_generating {
        # Full RFC validation for received messages
        require bgp_message.network_layer_reach_infos.len = 24;
        require bgp_message.network_layer_reach_infos.route_prefix.end = 3;
    };
    # Generation path: builder already constructed valid NLRI

    bgp_update_event := true;
    ...
}
```

## Z3 Action Space Comparison

| | Before (Current) | After (Scenario Builder) |
|---|---|---|
| Exported actions | 7 (4 messages + 3 handles) | 3 (OPEN + KEEPALIVE + generate_update) |
| Z3 constraint complexity | High (arrays, while loops, struct construction) | Low (FSM state + enum selection) |
| Action sequence to UPDATE | OPEN → KEEPALIVE → origin.handle → as_path.handle → next_hop.handle → UPDATE (6 steps, order-dependent) | OPEN → KEEPALIVE → generate_update (3 steps) |
| NLRI construction | Z3 must build array to length 3 | Builder constructs deterministically |
| AS_PATH construction | Z3 must satisfy while-loop constraints | Builder constructs deterministically |

## Soundness Argument

The builder is sound because:
1. Each scenario constructs a message that satisfies all `require` constraints in `around bgp_update_message_event`
2. The builder calls the original event, so all monitors and verification hooks fire
3. The receive-side `around` block is unchanged — IUT responses are validated against full RFC constraints
4. The scenario enum is finite and each variant is manually verified against RFC 4271

The builder does NOT bypass verification. It bypasses Z3's constraint solving for generation, not the model's property checking.

## Implementation Order

1. **Phase 1: bgp_scenario.ivy** — Define scenario types with `interpret`
2. **Phase 2: bgp_scenario_builder.ivy** — Implement `generate_update` with `announce_single` only
3. **Phase 3: Modify bgp_update_message.ivy** — Add `if ~_generating` guard for NLRI constraints
4. **Phase 4: Redesign bgp_speaker_test_update.ivy** — Use `generate_update`, remove inline hints
5. **Phase 5: Compile + IUT test** — Verify announce_single works end-to-end
6. **Phase 6: Add remaining scenarios** — announce_multihop, withdraw, replace, empty
7. **Phase 7: Extend to OPEN/NOTIFICATION** — If needed, add `generate_open`, `generate_notification`

## Open Questions

1. **Array construction in implement blocks**: Can Ivy's `stream_data.empty.append(192)` work inside `implement`? If not, need C++ shim for byte array construction.
2. **Path attribute serialization**: The builder sets `queued_path_attr` but the serializer reads from it. Need to verify the builder populates it in the same format the serializer expects.
3. **Hold timer interaction**: With fewer exported actions, Z3 may call `generate_update` before the session is established. The FSM `require` should prevent this, but needs testing.

## Success Criteria

- [ ] `bgp_speaker_test_update.ivy` has zero inline solver hints (no `before` blocks with `require` for generation)
- [ ] UPDATE generation succeeds in < 10 iterations (currently fails in 100)
- [ ] All 3 existing tests (accept, join, error) still pass unchanged
- [ ] New test variants (multihop, withdraw) work without adding solver hints
- [ ] `ivy_verify` passes on the builder module
