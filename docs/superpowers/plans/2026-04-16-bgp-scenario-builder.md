# BGP Scenario Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate per-test Z3 solver workarounds by introducing scenario-driven message generation for the BGP Ivy formal model.

**Architecture:** A finite `update_scenario` enum type interpreted to `bv[3]` gives Z3 a trivial enumeration problem. A `generate_update` action constructs the full UPDATE message deterministically per scenario, then fires the original `bgp_update_message_event`. The test file exports `generate_update` instead of 3 handle actions + message event, reducing Z3's action space from 7 to 3.

**Tech Stack:** Ivy 1.7, Z3 SMT solver, PANTHER experiment framework (Docker)

**Spec:** `docs/superpowers/specs/2026-04-16-bgp-scenario-builder-design.md`

**Working directory:** All paths relative to `panther/plugins/services/testers/panther_ivy/protocol-testing/bgp/`

---

### Task 1: Create scenario type definitions

**Files:**
- Create: `bgp_stack/bgp_scenario.ivy`

- [ ] **Step 1: Create bgp_scenario.ivy with UPDATE scenario enum**

```ivy
#lang ivy1.7

# BGP test scenario types for Z3-friendly message generation [rfc4271:4.3]
#
# Each scenario represents an RFC-valid message template. Z3 picks a
# scenario (finite enum); the builder constructs the message deterministically.

type update_scenario = {announce_single, announce_multihop, withdraw_single, replace_route, empty_update}
interpret update_scenario -> bv[3]
```

- [ ] **Step 2: Verify include resolution**

Run: `ivy_compile` on the UPDATE test (unchanged) to confirm the new file doesn't break existing includes.

```
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_update.ivy", target="test")
```

Expected: SUCCESS (bgp_scenario.ivy is not included yet, so no impact)

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy
git add protocol-testing/bgp/bgp_stack/bgp_scenario.ivy
git commit -m "feat(bgp): add scenario type definitions for Z3-friendly generation"
```

---

### Task 2: Add generation guard to bgp_update_message.ivy

The `around bgp_update_message_event` currently has NLRI constraints that Z3 can't satisfy. Wrap them in `if ~_generating` so the builder can pass pre-constructed NLRI through.

**Files:**
- Modify: `bgp_stack/bgp_update_message.ivy:111-134`

- [ ] **Step 1: Add generation guard around NLRI constraints**

In `bgp_stack/bgp_update_message.ivy`, replace lines 122-124:

```ivy
    # Constrain NLRI to valid IPv4 /24 prefix [rfc4271:4.3]
    require bgp_message.network_layer_reach_infos.len = 24;
    require bgp_message.network_layer_reach_infos.route_prefix.end = 3;
```

With:

```ivy
    if ~_generating {
        # Full NLRI validation for received messages [rfc4271:4.3]
        require bgp_message.network_layer_reach_infos.len = 24;
        require bgp_message.network_layer_reach_infos.route_prefix.end = 3;
    };
```

- [ ] **Step 2: Compile to verify no regressions**

```
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy", target="test")
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy", target="test")
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_error.ivy", target="test")
```

Expected: All 3 compile successfully. These tests don't generate UPDATEs, so the guard has no effect.

- [ ] **Step 3: Commit**

```bash
git add protocol-testing/bgp/bgp_stack/bgp_update_message.ivy
git commit -m "fix(bgp): add generation guard around NLRI constraints in UPDATE event"
```

---

### Task 3: Implement the scenario builder with announce_single

This is the core task. The builder action constructs a complete UPDATE from the scenario, populating path attributes and NLRI with concrete values, then fires the original event.

**Files:**
- Create: `bgp_stack/bgp_scenario_builder.ivy`

**Key constraint:** The builder must populate `queued_path_attr(src)` and `path_attr_size(src)` to match what the `around bgp_update_message_event` expects at lines 120-121. Study how the existing handle actions populate these.

- [ ] **Step 1: Study how handles populate queued state**

Read `bgp_stack/bgp_path_attribute.ivy` to understand:
- How `enqueue_path_attr(src, f)` works (appends to `queued_path_attr`)
- How `path_attr_size(src)` is computed (accumulates per handle)
- How `origin_present`, `as_path_present`, `next_hop_present` are set

Read `bgp_tests/speaker_tests/bgp_speaker_test_update.ivy` to understand what the current `after init` pre-populates for AS_PATH.

- [ ] **Step 2: Create bgp_scenario_builder.ivy**

```ivy
#lang ivy1.7

# BGP scenario builder — deterministic message construction for Z3
#
# Z3 picks a scenario (finite enum); this module constructs the full
# message. Eliminates per-test solver hints for array-based constraints.

include bgp_scenario

# ── UPDATE Builder ──────────────────────────────────────────────

action generate_update(src:bgp_id, dst:bgp_id, scenario:update_scenario)

implement generate_update {
    # FSM preconditions — the only thing Z3 must solve
    require conn_state(src) = bgp_connection_state.established;
    require open_message_recv(src) & open_message_recv(dst);

    # Reset attr state for clean construction
    origin_present(src) := false;
    as_path_present(src) := false;
    next_hop_present(src) := false;
    queued_path_attr(src) := path_attr.arr.empty;
    num_queued_path_attr(src) := 0;
    path_attr_size(src) := 0;

    if scenario = announce_single {
        call _build_announce_single(src, dst);
    };
    if scenario = empty_update {
        call _build_empty_update(src, dst);
    };
    # Other scenarios: announce_multihop, withdraw_single, replace_route
    # Added in Task 6.

    var msg : bgp_update_message;
    msg.withdraw_routes_len := 0;
    msg.withdraw_routes := withdraw_route.arr.empty;
    msg.total_path_attr_len := path_attr_size(src);
    msg.path_attrs := queued_path_attr(src);

    if scenario = announce_single {
        msg.network_layer_reach_infos.len := 24;
        # 192.168.1.0/24 — concrete bytes for NLRI
        msg.network_layer_reach_infos.route_prefix :=
            stream_data.empty.append(192).append(168).append(1);
    };
    if scenario = empty_update {
        msg.network_layer_reach_infos.len := 0;
        msg.network_layer_reach_infos.route_prefix := stream_data.empty;
        # Empty update: no path attrs
        msg.total_path_attr_len := 0;
        msg.path_attrs := path_attr.arr.empty;
    };

    call bgp_update_message_event(src, dst, msg);
}

# ── Private helpers: populate path attrs via existing handles ───

action _build_announce_single(src:bgp_id, dst:bgp_id)

implement _build_announce_single {
    # ORIGIN=IGP (0) [rfc4271:5.1.1]
    var origin_attr : path_attr.origin;
    origin_attr.transitive := true;
    origin_attr.optional := false;
    origin_attr.partial := false;
    origin_attr.value := 0;
    call path_attr.origin.handle(origin_attr, src, src, bgp_message_type.update_mess);

    # AS_PATH=empty AS_SEQUENCE (locally originated) [rfc4271:5.1.2]
    # Pre-populate queued segment state (same as current test after init)
    var seg_idx : path_attr.as_path.as_path_segment.idx := 0;
    queued_segment_type(src, seg_idx) := 2;
    num_queued_segment_value(src, seg_idx) := 0;
    num_queued_as_path(src) := 1;

    var as_path_attr : path_attr.as_path;
    as_path_attr.transitive := true;
    as_path_attr.optional := false;
    as_path_attr.partial := false;
    # Construct path with 1 segment: AS_SEQUENCE, 0 AS numbers
    as_path_attr.path := path_attr.as_path.as_path_segment.arr.empty;
    var seg : path_attr.as_path.as_path_segment;
    seg.segment_type := 2;
    seg.segment_len := 0;
    seg.segment_value := autonomous_system.arr.empty;
    as_path_attr.path := as_path_attr.path.append(seg);
    call path_attr.as_path.handle(as_path_attr, src, src, bgp_message_type.update_mess);

    # NEXT_HOP=0.0.0.0 (self, resolved at runtime) [rfc4271:5.1.3]
    var next_hop_attr : path_attr.next_hop;
    next_hop_attr.transitive := true;
    next_hop_attr.optional := false;
    next_hop_attr.partial := false;
    next_hop_attr.next_hop := 0;
    call path_attr.next_hop.handle(next_hop_attr, src, src, bgp_message_type.update_mess);
}

action _build_empty_update(src:bgp_id, dst:bgp_id)

implement _build_empty_update {
    # End-of-RIB marker: set attr-present flags but no actual attrs
    # The around block requires these to be true even for empty updates
    origin_present(src) := true;
    as_path_present(src) := true;
    next_hop_present(src) := true;
}
```

**IMPORTANT NOTE:** The `stream_data.empty.append(192)` syntax may not work in Ivy 1.7 `implement` blocks. If compilation fails on array construction, the fallback is a C++ shim in `<<< impl >>>` that builds the byte array. See Step 4.

- [ ] **Step 3: Compile the builder standalone**

Check if bgp_scenario_builder.ivy has syntax errors by compiling the UPDATE test (which will include it in the next task). For now, just verify no parse errors:

```
ivy_diagnostics(mode="structural", relative_path="bgp/bgp_stack/bgp_scenario_builder.ivy")
```

- [ ] **Step 4: Handle array construction fallback**

If `stream_data.empty.append(192)` doesn't compile, replace the NLRI construction with a C++ shim:

```ivy
# At the top of bgp_scenario_builder.ivy, add:

<<< member
    std::vector<char> _make_prefix_bytes(int b0, int b1, int b2);
>>>

<<< impl
    std::vector<char> _make_prefix_bytes(int b0, int b1, int b2) {
        std::vector<char> v;
        v.push_back((char)b0);
        v.push_back((char)b1);
        v.push_back((char)b2);
        return v;
    }
>>>

action make_nlri_prefix(b0:stream_pos, b1:stream_pos, b2:stream_pos) returns (r:stream_data)

implement make_nlri_prefix {
    <<<
        r = _make_prefix_bytes((int)b0, (int)b1, (int)b2);
    >>>
}
```

Then replace `stream_data.empty.append(192).append(168).append(1)` with `make_nlri_prefix(192, 168, 1)`.

Apply the same pattern for AS_PATH segment array construction if `arr.empty.append(seg)` fails.

- [ ] **Step 5: Commit**

```bash
git add protocol-testing/bgp/bgp_stack/bgp_scenario_builder.ivy
git commit -m "feat(bgp): implement scenario builder with announce_single"
```

---

### Task 4: Redesign the UPDATE test to use the builder

Replace the current inline solver hints with a clean test that exports `generate_update`.

**Files:**
- Modify: `bgp_tests/speaker_tests/bgp_speaker_test_update.ivy` (full rewrite)

- [ ] **Step 1: Rewrite bgp_speaker_test_update.ivy**

```ivy
#lang ivy1.7

# BGP UPDATE Compliance Test [rfc4271:4.3]
#
# Tests UPDATE message generation via scenario builder and IUT acceptance:
# 1. Establish a BGP session (OPEN + KEEPALIVE exchange) [rfc4271:8.2.2]
# 2. Generate UPDATE via scenario builder (ORIGIN, AS_PATH, NEXT_HOP, NLRI)
# 3. Verify IUT accepts the UPDATE (no NOTIFICATION in response)

include order
include file
include bgp_shim
include ivy_bgp_speaker_behavior
include bgp_scenario_builder

relation update_sent
relation session_established
relation keepalive_sent

after init {
    getsock(bgp_impl_instance.ep.addr) := net.connect_accept(endpoint_id.ivy_speaker, endpoint_id.impl_speaker, bgp_impl_instance.ep.addr);
    pend(bgp_impl_instance.ep.addr) := true;
    update_sent := false;
    session_established := false;
    keepalive_sent := false;
    acceptable_error(bgp_error_code.hold_timer_expire) := true;
    acceptable_error(bgp_error_code.fsm_error) := true;
}

before bgp_open_message_event(src:bgp_id,dst:bgp_id,bgp_message:bgp_open_message){
    if _generating {
    }
}

# KEEPALIVE gate: allow one, then block until UPDATE sent [rfc4271:8.2.2:opensent]
before bgp_keepalive_message_event(src:bgp_id,dst:bgp_id,bgp_message:bgp_keepalive_message){
    if _generating {
        require ~keepalive_sent | ~session_established | update_sent;
    }
}

# No NOTIFICATION generation in this test
before bgp_notification_message_event(src:bgp_id,dst:bgp_id,bgp_message:bgp_notification_message){
    if _generating {
        require false;
    }
}

after bgp_keepalive_message_event {
    if _generating {
        keepalive_sent := true;
    };
    if ~_generating {
        session_established := true;
    }
}

after generate_update {
    if _generating {
        update_sent := true;
    }
}

# 3 exports (was 7) — Z3 converges faster
export bgp_open_message_event
export bgp_keepalive_message_event
export bgp_notification_message_event
export generate_update

export action _finalize = {
    require open_message_recv(bgp_impl_instance.bgpid); # [rfc4271:4.2]
    require conn_state(bgp_impl_instance.bgpid) = bgp_connection_state.established;
    require update_sent; # [rfc4271:4.3]
    require ~received_unexpected_notification; # [rfc4271:6]
}
```

- [ ] **Step 2: Compile the redesigned test**

```
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_update.ivy", target="test")
```

Expected: SUCCESS. If array construction fails, apply the C++ shim fallback from Task 3 Step 4.

- [ ] **Step 3: Compile the other 3 tests to verify no regressions**

```
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy", target="test")
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy", target="test")
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_error.ivy", target="test")
```

Expected: All 3 SUCCESS.

- [ ] **Step 4: Commit**

```bash
git add protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_update.ivy
git commit -m "feat(bgp): redesign UPDATE test to use scenario builder"
```

---

### Task 5: End-to-end IUT validation

Run the UPDATE test against FRR to confirm the scenario builder generates valid UPDATE messages.

**Files:**
- None (uses existing experiment config)

**Prerequisites:** Docker image must be rebuilt to pick up the new files. Delete the cached image first.

- [ ] **Step 1: Delete cached Ivy tester image**

```bash
docker rmi panther_ivy-rfc4271:latest-z3pip-linux-amd64 2>/dev/null
```

- [ ] **Step 2: Run IUT test**

```bash
source .venv/bin/activate
panther run --config experiment-config/protocols/bgp/experiment_config_bgp_update_only.yaml
```

Expected: Docker rebuilds, test runs, look for in stdout:
- `generate_update` called with a scenario
- `bgp_update_message_event` fired with valid path attrs
- No `assumption_failed` or `assertion_failed`
- `_finalize` passes (`update_sent` is true)

- [ ] **Step 3: Analyze pcap**

```bash
tshark -r outputs/<latest>/0_BGP_UPDATE_Compliance/logs/ivy_tester/ivy_tester.pcap -Y 'bgp' -o 'bgp.desegment:TRUE'
```

Expected: OPEN → OPEN → KEEPALIVE → KEEPALIVE → UPDATE (from Ivy) with valid path attributes and NLRI.

- [ ] **Step 4: Check FRR accepted the UPDATE**

Look for NO NOTIFICATION from FRR after the UPDATE:

```bash
grep -E 'NOTIFICATION|error_code|assertion' outputs/<latest>/0_BGP_UPDATE_Compliance/logs/ivy_tester/stderr.log
```

Expected: No NOTIFICATION errors. If FRR sends a NOTIFICATION, check the error code and adjust the scenario's message construction.

- [ ] **Step 5: Commit submodule pointer update**

```bash
cd <panther_root>
git add panther/plugins/services/testers/panther_ivy
git commit -m "chore: update panther_ivy submodule for scenario builder"
```

---

### Task 6: Add remaining UPDATE scenarios

Add the other 4 scenarios: announce_multihop, withdraw_single, replace_route.

**Files:**
- Modify: `bgp_stack/bgp_scenario_builder.ivy`

- [ ] **Step 1: Add _build_announce_multihop**

```ivy
action _build_announce_multihop(src:bgp_id, dst:bgp_id)

implement _build_announce_multihop {
    # ORIGIN=IGP [rfc4271:5.1.1]
    var origin_attr : path_attr.origin;
    origin_attr.transitive := true;
    origin_attr.optional := false;
    origin_attr.partial := false;
    origin_attr.value := 0;
    call path_attr.origin.handle(origin_attr, src, src, bgp_message_type.update_mess);

    # AS_PATH=[AS_SEQUENCE: AS 65001, AS 65002, AS 65003] [rfc4271:5.1.2]
    var seg_idx : path_attr.as_path.as_path_segment.idx := 0;
    queued_segment_type(src, seg_idx) := 2;
    num_queued_segment_value(src, seg_idx) := 3;
    num_queued_as_path(src) := 1;
    # Pre-populate segment values
    var as0 : autonomous_system;
    as0.id := 65001;
    var as1 : autonomous_system;
    as1.id := 65002;
    var as2 : autonomous_system;
    as2.id := 65003;
    queued_segment_value(src, seg_idx) :=
        autonomous_system.arr.empty.append(as0).append(as1).append(as2);

    var as_path_attr : path_attr.as_path;
    as_path_attr.transitive := true;
    as_path_attr.optional := false;
    as_path_attr.partial := false;
    var seg : path_attr.as_path.as_path_segment;
    seg.segment_type := 2;
    seg.segment_len := 3;
    seg.segment_value := queued_segment_value(src, seg_idx);
    as_path_attr.path := path_attr.as_path.as_path_segment.arr.empty.append(seg);
    call path_attr.as_path.handle(as_path_attr, src, src, bgp_message_type.update_mess);

    # NEXT_HOP [rfc4271:5.1.3]
    var next_hop_attr : path_attr.next_hop;
    next_hop_attr.transitive := true;
    next_hop_attr.optional := false;
    next_hop_attr.partial := false;
    next_hop_attr.next_hop := 0;
    call path_attr.next_hop.handle(next_hop_attr, src, src, bgp_message_type.update_mess);
}
```

- [ ] **Step 2: Add scenario dispatch in generate_update**

Add to the `generate_update` implement block:

```ivy
    if scenario = announce_multihop {
        call _build_announce_multihop(src, dst);
    };
```

And for NLRI:

```ivy
    if scenario = announce_multihop {
        msg.network_layer_reach_infos.len := 24;
        msg.network_layer_reach_infos.route_prefix := make_nlri_prefix(10, 0, 0);
    };
```

- [ ] **Step 3: Add _build_withdraw_single and _build_replace_route**

Follow the same pattern. For withdraw_single, set `msg.withdraw_routes_len` and populate withdrawn routes instead of NLRI. For replace_route, use same NLRI as announce_single but ORIGIN=EGP (1).

- [ ] **Step 4: Compile and verify**

```
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_update.ivy", target="test")
```

- [ ] **Step 5: Commit**

```bash
git add protocol-testing/bgp/bgp_stack/bgp_scenario_builder.ivy
git commit -m "feat(bgp): add multihop, withdraw, and replace UPDATE scenarios"
```

---

### Task 7: Create scenario-specific test variants

Create dedicated test files that restrict which scenarios Z3 can pick.

**Files:**
- Create: `bgp_tests/speaker_tests/bgp_speaker_test_update_multihop.ivy`
- Create: `bgp_tests/speaker_tests/bgp_speaker_test_update_withdraw.ivy`

- [ ] **Step 1: Create multihop test**

Copy `bgp_speaker_test_update.ivy` and add a before-block that restricts the scenario:

```ivy
before generate_update(src:bgp_id, dst:bgp_id, scenario:update_scenario) {
    if _generating {
        require scenario = announce_multihop;
    }
}
```

- [ ] **Step 2: Create withdraw test**

Same pattern with `require scenario = withdraw_single`.

- [ ] **Step 3: Compile both**

```
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_update_multihop.ivy", target="test")
ivy_compile(relative_path="bgp/bgp_tests/speaker_tests/bgp_speaker_test_update_withdraw.ivy", target="test")
```

- [ ] **Step 4: Add experiment configs**

Add test sections for each variant in `experiment_config_bgp.yaml`.

- [ ] **Step 5: Commit**

```bash
git add protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_update_multihop.ivy
git add protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_update_withdraw.ivy
git commit -m "feat(bgp): add scenario-specific UPDATE test variants"
```

---

### Verification Checklist

After all tasks are complete, verify:

- [ ] `bgp_speaker_test_update.ivy` has zero inline solver hints (no `before` blocks with `require` for array construction)
- [ ] UPDATE generation succeeds in < 10 iterations (check stdout for iteration count before `generate_update` fires)
- [ ] All 3 existing tests (accept, join, error) compile and pass unchanged
- [ ] New test variants (multihop, withdraw) compile without adding solver hints
- [ ] Pcap shows valid UPDATE messages accepted by FRR
