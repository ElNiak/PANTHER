# BGP Model Structural Completion Design

**Date:** 2026-04-09
**Protocol:** BGP-4 (RFC 4271)
**Approach:** B — Structural Completion (~15 files modified, 3 created)

## Context

The BGP protocol model at `protocol-testing/bgp/` has 39 Ivy files across 5 directories (bgp_stack, bgp_utils, bgp_entities, bgp_shims, bgp_tests). A comprehensive review identified 5 critical issues blocking verification, 5 important quality concerns, and 4 suggestions. The model cannot currently compile or generate meaningful test traffic.

The root causes: uninitialized state variables, a dead NOTIFICATION path, commented-out test exports, no FSM, empty stub files (RIB, application, timers, inference), and no traceability coverage. This design fixes all critical and important issues and adds the missing architectural components.

## Section 1: Critical Fixes

### 1a. Uncomment `after init` in `bgp_shim.ivy:45-48`

**File:** `bgp_shims/bgp_shim.ivy`

Uncomment:
```ivy
after init {
    isup(A) := false;
    pend(A) := false;
}
```

Without this, `isup(A)` is unconstrained at startup. Every message guard in the model uses `require isup(bgpid_to_endpoint(src))`, making the entire constraint system unsound when `isup` can be arbitrarily true.

### 1b. Connect `is_errored` to error subcode pipeline

**File:** `bgp_stack/bgp_error_code.ivy`

Add `after` blocks on each error subcode handle variant:

```ivy
after bgp_error_subcode.type_bgp_header_error_subcode.handle(f, src, dst) {
    is_errored(src) := true;
}
after bgp_error_subcode.type_bgp_open_error_subcode.handle(f, src, dst) {
    is_errored(src) := true;
}
after bgp_error_subcode.type_bgp_update_error_subcode.handle(f, src, dst) {
    is_errored(src) := true;
}
```

This connects the existing two-stage error pipeline: Stage 1 (error subcode handle queues the error) now triggers Stage 2 (`is_errored(src) := true`), which unlocks `bgp_notification_message_event` via its `require is_errored(src)` guard at `bgp_notification_message.ivy:89`.

### 1c. Uncomment exports in `bgp_speaker_test_accept.ivy:42-47`

**File:** `bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy`

Uncomment:
```ivy
export bgp_open_message_event
export bgp_update_message_event
export bgp_keepalive_message_event
export bgp_notification_message_event
export speaker_send_event
```

Without exports, the test generates no traffic and trivially passes.

### 1d. Remove sub-action exports from `bgp_speaker_test_join.ivy:47-50`

**File:** `bgp_tests/speaker_tests/bgp_speaker_test_join.ivy`

Remove:
```ivy
# export path_attr.origin.handle
# export path_attr.as_path.handle
# export as_path_event
# export as_event
```

These sub-actions can fire outside UPDATE context when exported independently, producing invalid intermediate states.

### 1e. Rename `ping_prot_*` to `bgp_prot_*`

**File:** `bgp_utils/bgp_prot_deser_ser.ivy`

Rename all occurrences of `ping_prot_ser` to `bgp_prot_ser` and `ping_prot_deser` to `bgp_prot_deser`, including C++ class names. This file was copied from MiniP and never adapted.

## Section 2: FSM Addition

**New file:** `bgp_stack/bgp_fsm.ivy`
**Modified file:** `bgp_shims/bgp_shim.ivy` (add `include bgp_fsm`)

### 2.0 State Type

```ivy
object bgp_connection_state = {
    type this = {idle, connect, active, open_sent, open_confirm, established}
}
function conn_state(C:bgp_id) : bgp_connection_state

after init {
    conn_state(C) := bgp_connection_state.idle;
}
```

Six states per [rfc4271:8]. One `conn_state` per `bgp_id` per [rfc4271:8.2.1].

### 2.1 Idle → OpenSent (TCP Success)

In `bgp_fsm.ivy`, add an `after` block on `net.connected`:
```ivy
after net.connected(src, s) {
    if conn_state(src) = bgp_connection_state.idle {
        conn_state(src) := bgp_connection_state.open_sent;
    }
}
```

All FSM transitions live in `bgp_fsm.ivy`. The shim's `implement net.connected` handles socket state (`isup`, `getsock`); the FSM's `after` handles the state transition. Collapses Idle → Connect → OpenSent. Connect and Active states require ConnectRetryTimer (deferred).

### 2.2 OpenSent → OpenConfirm (OPEN Received)

```ivy
before bgp_open_message_event(src, dst, m) {
    require conn_state(src) = bgp_connection_state.open_sent;
    # [rfc4271:8.2.2] OPEN only valid in OpenSent
}
after bgp_open_message_event(src, dst, m) {
    conn_state(src) := bgp_connection_state.open_confirm;
    # [rfc4271:8.2.2] OpenSent + valid OPEN → OpenConfirm
}
```

### 2.3 OpenConfirm → Established (KEEPALIVE Received)

```ivy
before bgp_keepalive_message_event(src, dst, m) {
    require conn_state(src) = bgp_connection_state.open_confirm
          | conn_state(src) = bgp_connection_state.established;
    # [rfc4271:8.2.2] KEEPALIVE in OpenConfirm or Established
}
after bgp_keepalive_message_event(src, dst, m) {
    if conn_state(src) = bgp_connection_state.open_confirm {
        conn_state(src) := bgp_connection_state.established;
        # [rfc4271:8.2.2] OpenConfirm + KEEPALIVE → Established
    }
}
```

### 2.4 UPDATE Only in Established

```ivy
before bgp_update_message_event(src, dst, m) {
    require conn_state(src) = bgp_connection_state.established;
    # [rfc4271:9] UPDATE only in Established state
}
```

Strictly stronger than existing `isup`/`open_message_recv` boolean guards: catches UPDATE in OpenConfirm, which the booleans miss.

### 2.5 NOTIFICATION → Idle

```ivy
after bgp_notification_message_event(src, dst, m) {
    conn_state(src) := bgp_connection_state.idle;
    conn_state(dst) := bgp_connection_state.idle;
    # [rfc4271:8.2.2] NOTIFICATION → both peers to Idle
}
```

### 2.6 HoldTimer Expiry → Idle

```ivy
after hold_timer_expired(src) {
    conn_state(src) := bgp_connection_state.idle;
    # [rfc4271:8.2.2] HoldTimer expiry → Idle
}
```

Timer action defined in Section 3. FSM only records the transition.

### Deferred

- Connect/Active as distinct reachable states (needs ConnectRetryTimer)
- Collision detection (Event 23) — single-connection model
- DelayOpen variants (Events 4-7, 12, 20) — optional per RFC

## Section 3: Timer Model

**File:** `bgp_utils/bgp_time.ivy` (rewrite from empty stub)

### State

```ivy
function hold_time(C:bgp_id) : seconds
function keepalive_time(C:bgp_id) : seconds
relation hold_timer_running(C:bgp_id)
relation keepalive_timer_running(C:bgp_id)

after init {
    hold_time(C) := 180;
    keepalive_time(C) := 60;
    hold_timer_running(C) := false;
    keepalive_timer_running(C) := false;
}
```

180s default hold time. 60s keepalive (hold_time/3) per [rfc4271:10].

### Timer Start on OPEN Exchange

```ivy
after bgp_open_message_event(src, dst, m) {
    if hold_time(src) ~= 0 {
        hold_timer_running(src) := true;
        keepalive_timer_running(src) := true;
    }
}
```

### HoldTimer Reset on Message Receipt

```ivy
after bgp_keepalive_message_event(src, dst, m) {
    if hold_time(src) ~= 0 { hold_timer_running(src) := true; }
}
after bgp_update_message_event(src, dst, m) {
    if hold_time(src) ~= 0 { hold_timer_running(src) := true; }
}
```

### HoldTimer Expiry Action

```ivy
action hold_timer_expired(src:bgp_id)

before hold_timer_expired(src) {
    require hold_timer_running(src);
    require conn_state(src) = bgp_connection_state.open_sent
          | conn_state(src) = bgp_connection_state.open_confirm
          | conn_state(src) = bgp_connection_state.established;
    # [rfc4271:8.2.2] HoldTimer only fires in active states
}
after hold_timer_expired(src) {
    hold_timer_running(src) := false;
    keepalive_timer_running(src) := false;
    is_errored(src) := true;
    # Enables NOTIFICATION path (Section 1b) → FSM → Idle (Section 2.6)
}
```

### KeepaliveTimer Expiry Action

```ivy
action keepalive_timer_expired(src:bgp_id)

before keepalive_timer_expired(src) {
    require keepalive_timer_running(src);
    require conn_state(src) = bgp_connection_state.open_confirm
          | conn_state(src) = bgp_connection_state.established;
    # [rfc4271:8.2.2] KeepaliveTimer in OpenConfirm or Established
}
after keepalive_timer_expired(src) {
    keepalive_timer_running(src) := true;
    # Auto-restart. Verifier generates KEEPALIVE via existing event.
}
```

### Timer Stop on Teardown

```ivy
after bgp_notification_message_event(src, dst, m) {
    hold_timer_running(src) := false;
    hold_timer_running(dst) := false;
    keepalive_timer_running(src) := false;
    keepalive_timer_running(dst) := false;
}
```

### Deferred

- ConnectRetryTimer (Connect/Active states collapsed)
- Hold Time negotiation min(local, remote) from OPEN message

## Section 4: Stub Completion

### `bgp_stack/bgp_route.ivy` (extend)

The existing file defines `withdraw_route` but no general `bgp_route` type. Add:

```ivy
object bgp_route = {
    type this = struct {
        prefix: stream_data,
        next_hop: stream_data,
        path_attrs: stream_data
    }
}
```

This provides a minimal route representation for the RIB relations below.

### `bgp_stack/bgp_rib.ivy` (rewrite)

```ivy
#lang ivy1.7

# BGP Routing Information Base [rfc4271:3.2]

relation adj_rib_in(peer:bgp_id, r:bgp_route)
relation loc_rib(r:bgp_route)
relation adj_rib_out(peer:bgp_id, r:bgp_route)

after init {
    adj_rib_in(P, R) := false;
    loc_rib(R) := false;
    adj_rib_out(P, R) := false;
}
```

Three RIB partitions per [rfc4271:3.2]. Skeleton for route storage; Decision Process deferred.

### `bgp_stack/bgp_application.ivy` (rewrite)

```ivy
#lang ivy1.7

# BGP Application Layer [rfc4271:9]

relation update_processed(src:bgp_id, dst:bgp_id)

after init {
    update_processed(S, D) := false;
}

after bgp_update_message_event(src, dst, m) {
    update_processed(src, dst) := true;
}
```

Minimal hook point for UPDATE tracking. Route extraction deferred to `bgp_infer`.

### `bgp_utils/bgp_infer.ivy` (rewrite)

```ivy
#lang ivy1.7

# BGP Path Attribute Inference
# Stub declarations for import actions used during UPDATE processing.
# Runtime behavior provided by compiled C++ test harness.
```

Documented placeholder. Import action interface preserved; no new constraints.

## Section 5: Test Improvements

### Export Timer Actions

Add to both `bgp_speaker_test_accept.ivy` and `bgp_speaker_test_join.ivy`:

```ivy
export hold_timer_expired
export keepalive_timer_expired
```

### `_finalize` Assertions

Replace empty `_finalize` in both test files:

```ivy
export action _finalize = {
    require conn_state(bgp_impl_instance.bgpid) = bgp_connection_state.established
          | conn_state(bgp_impl_instance.bgpid) = bgp_connection_state.idle;
    require open_message_recv(bgp_impl_instance.bgpid);
}
```

Asserts the session either reached Established or cleanly returned to Idle. Prevents tests that end in intermediate states.

## Section 6: Coverage Infrastructure

### Requirements Manifest

**New file:** `protocol-testing/bgp/rfc4271_requirements.yaml`

Starter manifest with 10 requirements covering the modeled FSM transitions, timer behavior, and message sequencing from RFC 4271 Sections 4.2, 4.3, 4.4, 8.2.1, 8.2.2, 9, and 10.

### Bracket-Tag Annotations

Add `# [rfc4271:X.Y]` tags to ~10 existing and new `require` statements:

| File | Requirement | Tag |
|---|---|---|
| bgp_fsm.ivy | OPEN guard | `# [rfc4271:8.2.2:opensent]` |
| bgp_fsm.ivy | UPDATE guard | `# [rfc4271:9]` |
| bgp_fsm.ivy | KEEPALIVE guard | `# [rfc4271:8.2.2:openconfirm]` |
| bgp_time.ivy | HoldTimer guard | `# [rfc4271:8.2.2:holdtimer]` |
| bgp_open_message.ivy | No duplicate OPEN | `# [rfc4271:4.2]` |
| bgp_keepalive_message.ivy | KEEPALIVE preconditions | `# [rfc4271:4.4]` |
| ivy_bgp_speaker_behavior.ivy | Version = 4 | `# [rfc4271:4.2]` |
| bgp_notification_message.ivy | is_errored guard | `# [rfc4271:6.6]` |
| bgp_update_message.ivy | origin_present | `# [rfc4271:4.3]` |
| bgp_time.ivy | KeepaliveTimer guard | `# [rfc4271:10]` |

## Implementation Note: `after` Block Composition

Sections 2 (FSM) and 3 (Timers) both add `after` blocks on the same events:
`bgp_open_message_event`, `bgp_keepalive_message_event`, `bgp_update_message_event`,
and `bgp_notification_message_event`. Ivy composes multiple `after` blocks — all
run in include order. The FSM and timer `after` blocks are independent (neither
reads the other's state within the same event), so execution order does not matter.
Both files should be included from `bgp_shim.ivy`.

## File Change Summary

| Section | Files Modified | Files Created |
|---|---|---|
| 1. Critical Fixes | bgp_shim.ivy, bgp_error_code.ivy, bgp_speaker_test_accept.ivy, bgp_speaker_test_join.ivy, bgp_prot_deser_ser.ivy | — |
| 2. FSM | bgp_shim.ivy (include) | bgp_fsm.ivy |
| 3. Timers | — | bgp_time.ivy (rewrite) |
| 4. Stubs | bgp_route.ivy (extend) | bgp_rib.ivy, bgp_application.ivy, bgp_infer.ivy (rewrites) |
| 5. Tests | bgp_speaker_test_accept.ivy, bgp_speaker_test_join.ivy | — |
| 6. Coverage | ~8 files (annotations) | rfc4271_requirements.yaml |
| **Total** | ~15 files | 3 new + 1 manifest |

## Verification

After implementation, verify with:

1. `ivy_diagnostics(mode="structural")` on all modified `.ivy` files — expect 0 errors
2. `ivy_diagnostics(mode="full")` on both test files — check for unresolved includes, type errors
3. `ivy_coverage(mode="stats")` — confirm manifest loads, annotations are counted
4. `ivy_verify` on `bgp_speaker_test_join.ivy` — the primary compilation + verification test
5. Check that `conn_state` transitions correctly through OPEN → KEEPALIVE → Established in a test trace
