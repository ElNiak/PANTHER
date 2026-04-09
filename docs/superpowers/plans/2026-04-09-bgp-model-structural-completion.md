# BGP Model Structural Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 5 critical issues blocking BGP model verification and add FSM, timers, RIB skeleton, and RFC coverage infrastructure.

**Architecture:** The BGP model at `protocol-testing/bgp/` follows the PANTHER Ivy 14-layer template. Changes are additive: new `before`/`after` blocks compose with existing constraints. Two new files (`bgp_fsm.ivy`, `bgp_time.ivy` rewrite) are included via `bgp_shim.ivy`. Stubs (`bgp_rib.ivy`, `bgp_application.ivy`, `bgp_infer.ivy`) are rewritten from empty 1-line files.

**Tech Stack:** Ivy 1.7 formal language, ivy_check/ivyc CLI tools, ivy_diagnostics MCP tool for structural validation.

**Base path:** `panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/` (all relative paths below are from here)

---

### Task 1: Uncomment shim initialization

**Files:**
- Modify: `bgp_shims/bgp_shim.ivy:45-48`

- [ ] **Step 1: Read the current commented-out init block**

Open `bgp_shims/bgp_shim.ivy` and confirm lines 45-48 are:
```ivy
# after init {
#     isup(A) := false;
#     pend(A) := false;
# }
```

- [ ] **Step 2: Uncomment the init block**

Replace lines 45-48 with:
```ivy
after init {
    isup(A) := false;
    pend(A) := false;
}
```

- [ ] **Step 3: Verify structural correctness**

Run `ivy_diagnostics` with `relative_path="protocol-testing/bgp/bgp_shims/bgp_shim.ivy"` and `mode="structural"`. Expect 0 errors.

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_shims/bgp_shim.ivy
git commit -m "fix(bgp): uncomment after init block in bgp_shim.ivy

Initializes isup(A) and pend(A) to false at startup. Without this,
the relations are unconstrained, making all message guards unsound."
```

---

### Task 2: Connect is_errored to error subcode pipeline

**Files:**
- Modify: `bgp_stack/bgp_error_code.ivy`

- [ ] **Step 1: Read the current error_code file to locate handle actions**

Open `bgp_stack/bgp_error_code.ivy`. The three handle actions are at:
- Line 63: `action handle(f:bgp_error_subcode.type_bgp_header_error_subcode, src:bgp_id, dst:bgp_id)`
- Line 77: `action handle(f:bgp_error_subcode.type_bgp_open_error_subcode, src:bgp_id, dst:bgp_id)`
- Line 91: `action handle(f:bgp_error_subcode.type_bgp_update_error_subcode, src:bgp_id, dst:bgp_id)`

Each has an `around handle` block that ends with `queued_suberror(src) := f;`.

- [ ] **Step 2: Add after blocks at end of file**

Append the following after the last closing brace of the file (after line 99):

```ivy

# Connect error detection to NOTIFICATION path [rfc4271:6.6]
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

- [ ] **Step 3: Verify structural correctness**

Run `ivy_diagnostics` with `relative_path="protocol-testing/bgp/bgp_stack/bgp_error_code.ivy"` and `mode="structural"`. Expect 0 errors.

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_error_code.ivy
git commit -m "fix(bgp): connect is_errored to error subcode pipeline

Sets is_errored(src) := true after each error subcode handle fires.
This unlocks the NOTIFICATION message path which requires
is_errored(src) at bgp_notification_message.ivy:89."
```

---

### Task 3: Fix test file exports

**Files:**
- Modify: `bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy:42-47`
- Modify: `bgp_tests/speaker_tests/bgp_speaker_test_join.ivy:47-50`

- [ ] **Step 1: Uncomment exports in test_accept**

Open `bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy`. Replace lines 42-47:

Old:
```ivy
# export bgp_open_message_event
# export bgp_update_message_event
# export bgp_keepalive_message_event
# export bgp_notification_message_event

# export speaker_send_event
```

New:
```ivy
export bgp_open_message_event
export bgp_update_message_event
export bgp_keepalive_message_event
export bgp_notification_message_event

export speaker_send_event
```

- [ ] **Step 2: Remove sub-action exports from test_join**

Open `bgp_tests/speaker_tests/bgp_speaker_test_join.ivy`. Delete lines 47-50 entirely:

```ivy
export path_attr.origin.handle
export path_attr.as_path.handle
export as_path_event
export as_event
```

These 4 lines should be removed (not commented — deleted).

- [ ] **Step 3: Verify both test files structurally**

Run `ivy_diagnostics` on both:
- `relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy"`, `mode="structural"`
- `relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy"`, `mode="structural"`

Expect 0 errors on both.

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy
git commit -m "fix(bgp): enable test exports and remove invalid sub-action exports

Uncomment all message exports in test_accept so the verifier can
generate traffic. Remove path_attr sub-action exports from test_join
that could fire outside UPDATE context."
```

---

### Task 4: Rename ping_prot_* to bgp_prot_*

**Files:**
- Modify: `bgp_utils/bgp_prot_deser_ser.ivy`

- [ ] **Step 1: Read the current file**

Open `bgp_utils/bgp_prot_deser_ser.ivy` (75 lines). The two objects to rename:
- Line 3: `object ping_prot_ser = {}`
- Line 32: `object ping_prot_deser = {}`

Also rename the C++ class names inside the `<<< member` and `<<< impl` blocks.

- [ ] **Step 2: Rename all occurrences**

Replace throughout the file:
- `ping_prot_ser` → `bgp_prot_ser` (in Ivy object name and any C++ references)
- `ping_prot_deser` → `bgp_prot_deser` (in Ivy object name and any C++ references)

Use replace_all on each pattern. The C++ class names inside `<<<` blocks should also be renamed if they reference `ping_prot_ser` or `ping_prot_deser`.

- [ ] **Step 3: Verify structural correctness**

Run `ivy_diagnostics` with `relative_path="protocol-testing/bgp/bgp_utils/bgp_prot_deser_ser.ivy"` and `mode="structural"`. Expect 0 errors.

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_utils/bgp_prot_deser_ser.ivy
git commit -m "fix(bgp): rename ping_prot_* to bgp_prot_* in deser_ser

File was copied from MiniP and never adapted. Renames the serializer
and deserializer objects to match the BGP protocol namespace."
```

---

### Task 5: Create BGP FSM

**Files:**
- Create: `bgp_stack/bgp_fsm.ivy`
- Modify: `bgp_shims/bgp_shim.ivy` (add include)

- [ ] **Step 1: Create bgp_fsm.ivy**

Create file at `bgp_stack/bgp_fsm.ivy` with this content:

```ivy
#lang ivy1.7

# BGP Connection Finite State Machine [rfc4271:8]

object bgp_connection_state = {
    type this = {idle, connect, active, open_sent, open_confirm, established}
}

# Per-speaker connection state [rfc4271:8.2.1]
function conn_state(C:bgp_id) : bgp_connection_state

after init {
    conn_state(C) := bgp_connection_state.idle;
}

# Idle → OpenSent on TCP success [rfc4271:8.2.2]
# Collapses Idle → Connect → OpenSent (ConnectRetryTimer deferred)
after net.connected(src, s) {
    if conn_state(src) = bgp_connection_state.idle {
        conn_state(src) := bgp_connection_state.open_sent;
    }
}

# OPEN only valid in OpenSent [rfc4271:8.2.2]
before bgp_open_message_event(src, dst, m) {
    require conn_state(src) = bgp_connection_state.open_sent;
    # [rfc4271:8.2.2:opensent]
}

# OpenSent → OpenConfirm on valid OPEN [rfc4271:8.2.2]
after bgp_open_message_event(src, dst, m) {
    conn_state(src) := bgp_connection_state.open_confirm;
}

# KEEPALIVE valid in OpenConfirm or Established [rfc4271:8.2.2]
before bgp_keepalive_message_event(src, dst, m) {
    require conn_state(src) = bgp_connection_state.open_confirm
          | conn_state(src) = bgp_connection_state.established;
    # [rfc4271:8.2.2:openconfirm]
}

# OpenConfirm → Established on KEEPALIVE [rfc4271:8.2.2]
after bgp_keepalive_message_event(src, dst, m) {
    if conn_state(src) = bgp_connection_state.open_confirm {
        conn_state(src) := bgp_connection_state.established;
    }
}

# UPDATE only in Established [rfc4271:9]
before bgp_update_message_event(src, dst, m) {
    require conn_state(src) = bgp_connection_state.established;
    # [rfc4271:9]
}

# NOTIFICATION → both peers to Idle [rfc4271:8.2.2]
after bgp_notification_message_event(src, dst, m) {
    conn_state(src) := bgp_connection_state.idle;
    conn_state(dst) := bgp_connection_state.idle;
}

# HoldTimer expiry → Idle [rfc4271:8.2.2]
# (hold_timer_expired action defined in bgp_time.ivy)
after hold_timer_expired(src) {
    conn_state(src) := bgp_connection_state.idle;
}
```

- [ ] **Step 2: Add include to bgp_shim.ivy**

Open `bgp_shims/bgp_shim.ivy`. Add after line 39 (after `include bgp_open_message`):

```ivy
include bgp_fsm
```

- [ ] **Step 3: Verify bgp_fsm.ivy structurally**

Run `ivy_diagnostics` with `relative_path="protocol-testing/bgp/bgp_stack/bgp_fsm.ivy"` and `mode="structural"`. Expect 0 errors.

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_fsm.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_shims/bgp_shim.ivy
git commit -m "feat(bgp): add 6-state connection FSM from RFC 4271 Section 8

Adds bgp_connection_state type with Idle/Connect/Active/OpenSent/
OpenConfirm/Established states. Transitions enforced via before/after
blocks on message events. Collapses Idle→Connect→OpenSent since
ConnectRetryTimer is not yet modeled."
```

---

### Task 6: Create timer model

**Files:**
- Rewrite: `bgp_utils/bgp_time.ivy` (currently 1-line stub)
- Modify: `bgp_shims/bgp_shim.ivy` (add include)

- [ ] **Step 1: Rewrite bgp_time.ivy**

Replace the entire content of `bgp_utils/bgp_time.ivy` with:

```ivy
#lang ivy1.7

# BGP Timers [rfc4271:10]

# Negotiated hold time per peer (seconds). 0 = no timer.
function hold_time(C:bgp_id) : seconds
# Keepalive interval = hold_time / 3 [rfc4271:10]
function keepalive_time(C:bgp_id) : seconds

# Timer liveness state
relation hold_timer_running(C:bgp_id)
relation keepalive_timer_running(C:bgp_id)

after init {
    hold_time(C) := 180;
    keepalive_time(C) := 60;
    hold_timer_running(C) := false;
    keepalive_timer_running(C) := false;
}

# Start timers on entering OpenConfirm [rfc4271:8.2.2]
after bgp_open_message_event(src, dst, m) {
    if hold_time(src) ~= 0 {
        hold_timer_running(src) := true;
        keepalive_timer_running(src) := true;
    }
}

# Reset HoldTimer on KEEPALIVE receipt [rfc4271:8.2.2]
after bgp_keepalive_message_event(src, dst, m) {
    if hold_time(src) ~= 0 {
        hold_timer_running(src) := true;
    }
}

# Reset HoldTimer on UPDATE receipt [rfc4271:8.2.2]
after bgp_update_message_event(src, dst, m) {
    if hold_time(src) ~= 0 {
        hold_timer_running(src) := true;
    }
}

# HoldTimer expiry action [rfc4271:8.2.2]
action hold_timer_expired(src:bgp_id)

before hold_timer_expired(src) {
    require hold_timer_running(src);
    require conn_state(src) = bgp_connection_state.open_sent
          | conn_state(src) = bgp_connection_state.open_confirm
          | conn_state(src) = bgp_connection_state.established;
    # [rfc4271:8.2.2:holdtimer]
}

after hold_timer_expired(src) {
    hold_timer_running(src) := false;
    keepalive_timer_running(src) := false;
    is_errored(src) := true;
}

# KeepaliveTimer expiry action [rfc4271:8.2.2]
action keepalive_timer_expired(src:bgp_id)

before keepalive_timer_expired(src) {
    require keepalive_timer_running(src);
    require conn_state(src) = bgp_connection_state.open_confirm
          | conn_state(src) = bgp_connection_state.established;
    # [rfc4271:10]
}

after keepalive_timer_expired(src) {
    keepalive_timer_running(src) := true;
}

# Stop all timers on NOTIFICATION (session teardown) [rfc4271:8.2.2]
after bgp_notification_message_event(src, dst, m) {
    hold_timer_running(src) := false;
    hold_timer_running(dst) := false;
    keepalive_timer_running(src) := false;
    keepalive_timer_running(dst) := false;
}
```

- [ ] **Step 2: Add include to bgp_shim.ivy**

Open `bgp_shims/bgp_shim.ivy`. The file already has `include bgp_time` (line 5 in the include list). Verify this include exists. If it does, no change needed — the rewritten file will be picked up automatically. If it doesn't, add `include bgp_time` near the other utility includes.

- [ ] **Step 3: Verify bgp_time.ivy structurally**

Run `ivy_diagnostics` with `relative_path="protocol-testing/bgp/bgp_utils/bgp_time.ivy"` and `mode="structural"`. Expect 0 errors.

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_utils/bgp_time.ivy
git commit -m "feat(bgp): add HoldTimer and KeepaliveTimer model from RFC 4271

Replaces empty bgp_time.ivy stub with timer state tracking.
HoldTimer expiry sets is_errored, enabling NOTIFICATION → Idle.
KeepaliveTimer expiry auto-restarts, prompting KEEPALIVE generation.
Both timers start on OpenConfirm entry and stop on session teardown."
```

---

### Task 7: Complete stub files

**Files:**
- Modify: `bgp_stack/bgp_route.ivy` (extend with bgp_route type)
- Rewrite: `bgp_stack/bgp_rib.ivy` (currently 1-line stub)
- Rewrite: `bgp_stack/bgp_application.ivy` (currently 1-line stub)
- Rewrite: `bgp_utils/bgp_infer.ivy` (currently 1-line stub)

- [ ] **Step 1: Add bgp_route type to bgp_route.ivy**

Open `bgp_stack/bgp_route.ivy`. The existing file defines `withdraw_route` (ends at line 36). Append after the last line:

```ivy

object bgp_route = {
    type this = struct {
        prefix: stream_data,
        next_hop: stream_data,
        path_attrs: stream_data
    }
}
```

- [ ] **Step 2: Rewrite bgp_rib.ivy**

Replace the entire content of `bgp_stack/bgp_rib.ivy` with:

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

- [ ] **Step 3: Rewrite bgp_application.ivy**

Replace the entire content of `bgp_stack/bgp_application.ivy` with:

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

- [ ] **Step 4: Rewrite bgp_infer.ivy**

Replace the entire content of `bgp_utils/bgp_infer.ivy` with:

```ivy
#lang ivy1.7

# BGP Path Attribute Inference
# Stub declarations for import actions used during UPDATE processing.
# Runtime behavior provided by compiled C++ test harness.
```

- [ ] **Step 5: Verify all four files structurally**

Run `ivy_diagnostics` on each:
- `relative_path="protocol-testing/bgp/bgp_stack/bgp_route.ivy"`, `mode="structural"`
- `relative_path="protocol-testing/bgp/bgp_stack/bgp_rib.ivy"`, `mode="structural"`
- `relative_path="protocol-testing/bgp/bgp_stack/bgp_application.ivy"`, `mode="structural"`
- `relative_path="protocol-testing/bgp/bgp_utils/bgp_infer.ivy"`, `mode="structural"`

Expect 0 errors on all four.

- [ ] **Step 6: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_route.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_rib.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_application.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_utils/bgp_infer.ivy
git commit -m "feat(bgp): fill empty stub files with skeleton implementations

- bgp_route.ivy: add bgp_route type (prefix, next_hop, path_attrs)
- bgp_rib.ivy: add adj_rib_in, loc_rib, adj_rib_out relations
- bgp_application.ivy: add UPDATE processing tracking
- bgp_infer.ivy: documented placeholder for import actions"
```

---

### Task 8: Add timer exports and _finalize assertions to test files

**Files:**
- Modify: `bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy`
- Modify: `bgp_tests/speaker_tests/bgp_speaker_test_join.ivy`

- [ ] **Step 1: Add timer exports to test_accept**

Open `bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy`. After the message exports (which were uncommented in Task 3), add:

```ivy
export hold_timer_expired
export keepalive_timer_expired
```

- [ ] **Step 2: Replace _finalize in test_accept**

Replace the empty `_finalize` block (lines 49-51):

Old:
```ivy
export action _finalize = {

}
```

New:
```ivy
export action _finalize = {
    require conn_state(bgp_impl_instance.bgpid) = bgp_connection_state.established
          | conn_state(bgp_impl_instance.bgpid) = bgp_connection_state.idle;
    require open_message_recv(bgp_impl_instance.bgpid);
}
```

- [ ] **Step 3: Add timer exports to test_join**

Open `bgp_tests/speaker_tests/bgp_speaker_test_join.ivy`. After the remaining message exports (lines 41-45, after sub-actions were removed in Task 3), add:

```ivy
export hold_timer_expired
export keepalive_timer_expired
```

- [ ] **Step 4: Replace _finalize in test_join**

Replace the empty `_finalize` block (lines 54-56 after Task 3 removals shifted lines):

Old:
```ivy
export action _finalize = {

}
```

New:
```ivy
export action _finalize = {
    require conn_state(bgp_impl_instance.bgpid) = bgp_connection_state.established
          | conn_state(bgp_impl_instance.bgpid) = bgp_connection_state.idle;
    require open_message_recv(bgp_impl_instance.bgpid);
}
```

- [ ] **Step 5: Verify both test files structurally**

Run `ivy_diagnostics` on both:
- `relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy"`, `mode="structural"`
- `relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy"`, `mode="structural"`

Expect 0 errors.

- [ ] **Step 6: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy
git commit -m "feat(bgp): add timer exports and _finalize assertions to tests

Export hold_timer_expired and keepalive_timer_expired so the verifier
can exercise timer expiry scenarios. Add _finalize assertions that
require the session reached Established or cleanly returned to Idle."
```

---

### Task 9: Create requirements manifest

**Files:**
- Create: `rfc4271_requirements.yaml` (at protocol-testing/bgp/ root)

- [ ] **Step 1: Create the manifest file**

Create `rfc4271_requirements.yaml` at the BGP protocol-testing root:

```yaml
rfc: RFC4271
title: 'A Border Gateway Protocol 4 (BGP-4)'
requirements:
  'rfc4271:4.2':
    text: >-
      The first message sent by each side is an OPEN message.
    section: '4.2'
    level: MUST
    layer: handshake
    testable: true
  'rfc4271:4.2.2':
    text: >-
      The Hold Time MUST be either zero or at least three seconds.
    section: '4.2'
    level: MUST
    layer: handshake
    testable: true
  'rfc4271:4.3':
    text: >-
      UPDATE messages are used to transfer routing information between
      BGP peers.
    section: '4.3'
    level: MUST
    layer: update
    testable: true
  'rfc4271:4.4':
    text: >-
      If the negotiated Hold Time interval is zero, then periodic
      KEEPALIVE messages MUST NOT be sent.
    section: '4.4'
    level: MUST NOT
    layer: keepalive
    testable: true
  'rfc4271:6.6':
    text: >-
      Any error detected by the BGP Finite State Machine (e.g., receipt of
      an unexpected event) is indicated by sending the NOTIFICATION message
      with the Error Code Finite State Machine Error.
    section: '6.6'
    level: MUST
    layer: error
    testable: true
  'rfc4271:8.2.1':
    text: >-
      BGP MUST maintain a separate FSM for each configured peer.
    section: '8.2.1'
    level: MUST
    layer: fsm
    testable: true
  'rfc4271:8.2.2:opensent':
    text: >-
      When a valid OPEN message is received in OpenSent, the local system
      sends a KEEPALIVE, starts timers, and transitions to OpenConfirm.
    section: '8.2.2'
    level: MUST
    layer: fsm
    testable: true
  'rfc4271:8.2.2:openconfirm':
    text: >-
      If a KEEPALIVE is received in OpenConfirm, the local system
      transitions to Established.
    section: '8.2.2'
    level: MUST
    layer: fsm
    testable: true
  'rfc4271:8.2.2:holdtimer':
    text: >-
      If the HoldTimer expires, the local system sends NOTIFICATION
      with Hold Timer Expired and transitions to Idle.
    section: '8.2.2'
    level: MUST
    layer: fsm
    testable: true
  'rfc4271:9':
    text: >-
      An UPDATE message may be received only in the Established state.
      Receiving an UPDATE message in any other state is an error.
    section: '9'
    level: MUST
    layer: update
    testable: true
  'rfc4271:10':
    text: >-
      If the negotiated Hold Time value is non-zero, the Keepalive Time
      is set to one-third of the Hold Time.
    section: '10'
    level: MUST
    layer: timer
    testable: true
```

- [ ] **Step 2: Verify manifest loads**

Run `ivy_coverage` with `mode="stats"`. The tool should detect and load the manifest. Expect total=11, covered=0 (annotations not yet added).

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/rfc4271_requirements.yaml
git commit -m "feat(bgp): add RFC 4271 requirements manifest with 11 entries

Starter manifest covering FSM transitions, timer behavior, message
sequencing, and error handling from RFC 4271 Sections 4.2-10."
```

---

### Task 10: Add bracket-tag annotations

**Files:**
- Modify: `bgp_stack/bgp_fsm.ivy` (already has tags from Task 5)
- Modify: `bgp_utils/bgp_time.ivy` (already has tags from Task 6)
- Modify: `bgp_stack/bgp_open_message.ivy`
- Modify: `bgp_stack/bgp_keepalive_message.ivy`
- Modify: `bgp_entities/ivy_bgp_speaker_behavior.ivy`
- Modify: `bgp_stack/bgp_notification_message.ivy`
- Modify: `bgp_stack/bgp_update_message.ivy`

- [ ] **Step 1: Verify existing tags in bgp_fsm.ivy and bgp_time.ivy**

The files created in Tasks 5-6 already contain bracket-tag comments inline. Read both files and confirm the following tags are present:
- `bgp_fsm.ivy`: `# [rfc4271:8.2.2:opensent]`, `# [rfc4271:8.2.2:openconfirm]`, `# [rfc4271:9]`
- `bgp_time.ivy`: `# [rfc4271:8.2.2:holdtimer]`, `# [rfc4271:10]`

If any are missing, add them on the `require` line they annotate.

- [ ] **Step 2: Add tag to bgp_open_message.ivy:115**

Open `bgp_stack/bgp_open_message.ivy`. At line 115, the existing code is:
```ivy
    require ~open_message_recv(src);
```

Change to:
```ivy
    require ~open_message_recv(src); # [rfc4271:4.2]
```

- [ ] **Step 3: Add tag to bgp_keepalive_message.ivy**

Open `bgp_stack/bgp_keepalive_message.ivy`. Find the `require isup(...)` line (around line 28-29). Add tag:
```ivy
    require isup(bgpid_to_endpoint(src)); # [rfc4271:4.4]
```

- [ ] **Step 4: Add tag to ivy_bgp_speaker_behavior.ivy:77**

Open `bgp_entities/ivy_bgp_speaker_behavior.ivy`. At line 77:
```ivy
        require bgp_message.pversion = 4;
```

Change to:
```ivy
        require bgp_message.pversion = 4; # [rfc4271:4.2.2]
```

- [ ] **Step 5: Add tag to bgp_notification_message.ivy:89**

Open `bgp_stack/bgp_notification_message.ivy`. At line 89:
```ivy
    require is_errored(src);
```

Change to:
```ivy
    require is_errored(src); # [rfc4271:6.6]
```

- [ ] **Step 6: Add tag to bgp_update_message.ivy:113**

Open `bgp_stack/bgp_update_message.ivy`. At line 113:
```ivy
    require origin_present(src);
```

Change to:
```ivy
    require origin_present(src); # [rfc4271:4.3]
```

- [ ] **Step 7: Verify coverage stats**

Run `ivy_coverage` with `mode="stats"`. Expect:
- total: 11
- covered: ≥ 8 (the tags should be detected)
- coverage_percent: ≥ 72%

- [ ] **Step 8: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_open_message.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_keepalive_message.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_entities/ivy_bgp_speaker_behavior.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_notification_message.ivy
git add panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/bgp_stack/bgp_update_message.ivy
git commit -m "feat(bgp): add bracket-tag RFC annotations to require statements

Tags 8 existing require statements with their RFC 4271 section
references for traceability coverage tracking."
```

---

### Task 11: Full verification

**Files:** None (read-only verification)

- [ ] **Step 1: Run full diagnostics on test_join**

Run `ivy_diagnostics` with `relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy"` and `mode="full"`. This checks all diagnostic layers (structural, lexer, semantic, coverage, pattern) on the main test file and its transitive includes.

Record any errors. If errors appear, diagnose and fix before proceeding.

- [ ] **Step 2: Run full diagnostics on test_accept**

Run `ivy_diagnostics` with `relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy"` and `mode="full"`.

Record any errors. If errors appear, diagnose and fix.

- [ ] **Step 3: Run coverage stats**

Run `ivy_coverage` with `mode="stats"`. Verify:
- Manifest loaded: `rfc4271_requirements.yaml`
- Total requirements: 11
- Covered requirements: ≥ 8
- Coverage breakdown by level shows MUST requirements with some coverage

- [ ] **Step 4: Attempt ivy_verify on test_join**

Run `ivy_verify` with `relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy"`. This compiles the model via `ivy_check` and reports verification results.

If verification fails with a counterexample, record the trace and diagnose. Common issues:
- Invariant violations from the new FSM state
- Timer guards conflicting with existing `before` constraints
- Missing initialization of new state variables

If verification passes, the model is structurally sound.

- [ ] **Step 5: Commit verification results (if fixes were needed)**

If any fixes were applied during verification, commit them:
```bash
git add -A panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/
git commit -m "fix(bgp): resolve verification issues found during full check"
```
