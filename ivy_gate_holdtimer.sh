#!/bin/bash
# Local Ivy typecheck gate (ivy-tools MCP is down this session).
# Recipe from memory/reference_local_ivy_typecheck_gate.md.
# Pass condition: no `error:` line other than the macOS-only linux/if_packet.h,
# and a non-empty <test>.cpp was emitted.
set -u

ROOT="$(pwd)"
VENV="$ROOT/.venv"
BGP="$ROOT/panther/plugins/services/testers/panther_ivy/protocol-testing/bgp"
STAGE="${TMPDIR:-/tmp}/ivy_gate_holdtimer"
TEST="${1:-bgp_speaker_test_error}"

# Use the SUBMODULE's stdlib, not site-packages: memory records the site-packages
# copy as stale, and it disagrees with the model on the network_implementation
# module arity. This is the tree the container entrypoint stages from.
STD="$ROOT/panther/plugins/services/testers/panther_ivy/ivy/include/1.7"
echo "stdlib include dir: $STD"

rm -rf "$STAGE"
mkdir -p "$STAGE"

# 1. Ivy 1.7 stdlib
cp "$STD"/*.ivy "$STAGE"/ 2>/dev/null

# 2. every non-test .ivy in the bgp model
for d in bgp_utils bgp_stack bgp_shims bgp_entities; do
  cp "$BGP/$d"/*.ivy "$STAGE"/ 2>/dev/null
done

# 3. the chosen test file
cp "$BGP/bgp_tests/speaker_tests/$TEST.ivy" "$STAGE"/ 2>/dev/null

echo "staged $(ls "$STAGE"/*.ivy | wc -l | tr -d ' ') .ivy files"

cd "$STAGE" || exit 1
export IVY_INCLUDE_PATH="$STAGE"
"$VENV/bin/ivyc" show_compiled=false trace=false target=test test_iters=300 "$TEST.ivy" > "$STAGE/gate.log" 2>&1
RC=$?

echo "=== ivyc exit code: $RC ==="
echo "=== error lines (excluding macOS-only if_packet/linux headers) ==="
grep -nE "error:|Error:|syntax error|Bad sorts" "$STAGE/gate.log" \
  | grep -viE "if_packet|if_ether|linux/|netinet|sys/socket" | head -40
echo "=== (end error filter) ==="
echo "--- generated cpp ---"
ls -la "$STAGE/$TEST.cpp" 2>/dev/null || echo "NO .cpp EMITTED"
echo "--- last 25 lines of raw log ---"
tail -25 "$STAGE/gate.log"
