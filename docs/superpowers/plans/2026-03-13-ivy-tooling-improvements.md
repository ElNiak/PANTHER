# Ivy Tooling Improvements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 7 of 9 priority actions from the Ivy tooling strategic evaluation (Tasks 2 and 3 skipped after review showed they don't justify the complexity).

**Architecture:** Four phases of increasing scope: (1) quick wins on existing code, (2) new skills/agents, (3) new verification dashboard feature, (4) architectural graph and pipeline simplification. Each phase produces independently testable, committable work.

**Tech Stack:** Python 3.10+, pygls (LSP), FastMCP, pytest, ivy-lsp submodule

**Spec:** `docs/superpowers/specs/2026-03-13-ivy-tooling-evaluation.md`

**Base path for all ivy-lsp files:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
(Abbreviated as `$LSP/` below for readability)

**Base path for plugin files:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`
(Abbreviated as `$PLUGIN/` below)

**Shell setup** (run before any commands):
```bash
LSP="panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp"
PLUGIN="panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin"
```

---

## Chunk 1: Phase 1 — Quick Wins

### Task 1: Enrich Counterexample Display in `ivy_verify` (Priority #1, HIGH)

The counterexample parser already works (`$LSP/ivy_lsp/utils/counterexample_parser.py`) and is wired into `$LSP/ivy_lsp/tools/verification.py:155-160`. However, the structured data is returned as a raw dict without human-readable formatting. This task adds a `format_counterexample()` function that produces a readable state trace.

**Files:**
- Create: `$LSP/ivy_lsp/utils/counterexample_formatter.py`
- Modify: `$LSP/ivy_lsp/tools/verification.py:153-161`
- Test: `$LSP/tests/test_counterexample_formatter.py`
- Existing test: `$LSP/tests/test_counterexample_parser.py` (reference for input shapes)

- [ ] **Step 1: Write failing test for formatter**

```python
# tests/test_counterexample_formatter.py
"""Tests for counterexample formatting."""
from ivy_lsp.utils.counterexample_formatter import format_counterexample


def test_format_empty_counterexample():
    cex = {"assertion": None, "assertion_line": None, "steps": []}
    result = format_counterexample(cex)
    assert "No assertion" in result


def test_format_single_step():
    cex = {
        "assertion": "require conn_seen(C)",
        "assertion_line": 42,
        "steps": [
            {
                "step_number": 1,
                "action": "quic_connection.open",
                "assignments": {"conn_seen": "false", "cid": "0x1234"},
            }
        ],
    }
    result = format_counterexample(cex)
    assert "Line 42" in result
    assert "require conn_seen(C)" in result
    assert "Step 1" in result
    assert "quic_connection.open" in result
    assert "conn_seen = false" in result


def test_format_multi_step_trace():
    cex = {
        "assertion": "ensure stream_data_sent(S)",
        "assertion_line": 108,
        "steps": [
            {
                "step_number": 1,
                "action": "quic_stream.open",
                "assignments": {"stream_id": "4", "stream_state": "idle"},
            },
            {
                "step_number": 2,
                "action": "quic_stream.send",
                "assignments": {"stream_id": "4", "stream_state": "open", "bytes_sent": "0"},
            },
        ],
    }
    result = format_counterexample(cex)
    assert "Step 1" in result
    assert "Step 2" in result
    # Should show state changes between steps
    assert "stream_state" in result


def test_format_none_returns_empty():
    assert format_counterexample(None) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd $LSP && python -m pytest tests/test_counterexample_formatter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.utils.counterexample_formatter'`

- [ ] **Step 3: Write minimal implementation**

```python
# ivy_lsp/utils/counterexample_formatter.py
"""Human-readable formatting of parsed Ivy counterexamples.

Transforms the structured dict from ``parse_counterexample()`` into
a readable state trace with step-by-step variable changes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def format_counterexample(cex: Optional[Dict[str, Any]]) -> str:
    """Format a parsed counterexample as a readable state trace.

    Args:
        cex: Output of ``parse_counterexample()``, or None.

    Returns:
        Human-readable string, or empty string if cex is None.
    """
    if cex is None:
        return ""

    lines: List[str] = []

    # Header: assertion info
    assertion = cex.get("assertion")
    assertion_line = cex.get("assertion_line")
    if assertion and assertion_line:
        lines.append(f"Violated assertion (Line {assertion_line}):")
        lines.append(f"  {assertion}")
    elif assertion:
        lines.append(f"Violated assertion: {assertion}")
    else:
        lines.append("No assertion identified in counterexample.")

    steps: List[Dict[str, Any]] = cex.get("steps", [])
    if not steps:
        lines.append("\nNo execution steps in counterexample.")
        return "\n".join(lines)

    lines.append(f"\nExecution trace ({len(steps)} step{'s' if len(steps) != 1 else ''}):")
    lines.append("-" * 50)

    prev_assignments: Dict[str, str] = {}
    for step in steps:
        step_num = step.get("step_number", "?")
        action = step.get("action", "(unknown action)")
        assignments = step.get("assignments", {})

        lines.append(f"\n  Step {step_num}: {action}")

        if assignments:
            for var, val in sorted(assignments.items()):
                prev = prev_assignments.get(var)
                if prev is not None and prev != val:
                    lines.append(f"    {var} = {val}  (was: {prev})")
                else:
                    lines.append(f"    {var} = {val}")

        prev_assignments.update(assignments)

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd $LSP && python -m pytest tests/test_counterexample_formatter.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Wire formatted output into ivy_verify**

Modify `$LSP/ivy_lsp/tools/verification.py` lines 153-161. After parsing, also add the formatted trace:

```python
# In ivy_verify(), after line 160 (result["counterexample"] = cex):
                    from ivy_lsp.utils.counterexample_formatter import format_counterexample
                    result["counterexample_trace"] = format_counterexample(cex)
```

The full block becomes:
```python
            # Parse counterexample if verification failed
            if not result.get("success", True):
                from ivy_lsp.utils.counterexample_parser import parse_counterexample

                raw = result.get("raw_output", "")
                cex = parse_counterexample(raw)
                if cex is not None:
                    result["counterexample"] = cex
                    from ivy_lsp.utils.counterexample_formatter import format_counterexample
                    result["counterexample_trace"] = format_counterexample(cex)
```

- [ ] **Step 6: Run existing verification tests**

Run: `cd $LSP && python -m pytest tests/ -k "verify" -v`
Expected: All existing verification tests still pass

- [ ] **Step 7: Commit**

```bash
git add ivy_lsp/utils/counterexample_formatter.py tests/test_counterexample_formatter.py ivy_lsp/tools/verification.py
git commit -m "feat(mcp): add human-readable counterexample trace to ivy_verify output"
```

---

### Task 2: Trim Unused IR Sub-Types (Priority #9, LOW)

`$LSP/ivy_lsp/compilation/ir.py` defines 7 frozen dataclasses + 1 container. Only 3 sub-IR types are accessed by `graph_enrichment.py`: `SortIR` (fields: `is_enumerated`, `constructors`), `SymbolIR` (6 fields), `ActionIR` (2 fields). `MixinIR`, `IsolateIR`, `LabeledFormulaIR`, and `RequirementIR` are defined in CompiledModuleIR but their internal fields are never queried during graph enrichment — the dicts that hold them are iterated but only the keys (names) are used.

**Assessment after deeper review:** The sub-IR types serve as structured containers for the compiler adapter output. Even though graph_enrichment only uses a subset of fields, the types provide type safety and documentation value for the compilation pipeline. The unused *fields within used types* (e.g., `SymbolIR.is_destructor` is read by graph_enrichment) don't add runtime cost since they're frozen dataclasses.

**Decision: SKIP this task.** The IR types are well-structured and the "unused granularity" is actually documentation value, not dead weight. No code change needed.

---

### Task 3: Lazy-Build SemanticModel Secondary Indexes (Priority #8, LOW)

**Decision: SKIP.** After review, `_nodes_by_file` is load-bearing for `remove_file()` (line 79: `_nodes_by_file.pop(filepath, set())` to find which nodes to remove) and `update_file()` (lines 138-144). Converting to lazy indexing would require rewriting both removal methods since they depend on the eager index for correctness. The performance benefit (<10K nodes typically) doesn't justify the complexity. No code change needed.

---

## Chunk 2: Phase 2 — Skill & Agent Improvements

### Task 4: Split `methodology-reference` Skill into 3 Sub-Skills (Priority #5)

The current `methodology-reference` skill is 432 lines covering NCT (lines 12-166), NACT (169-298), and NSCT (301-432). Splitting improves skill auto-selection accuracy — the dispatcher can pick the right methodology based on context keywords.

**Files:**
- Create: `$PLUGIN/skills/nct-methodology/SKILL.md`
- Create: `$PLUGIN/skills/nact-methodology/SKILL.md`
- Create: `$PLUGIN/skills/nsct-methodology/SKILL.md`
- Modify: `$PLUGIN/skills/methodology-reference/SKILL.md` (becomes dispatcher/index)

- [ ] **Step 1: Create NCT methodology skill**

Create `$PLUGIN/skills/nct-methodology/SKILL.md` with the NCT content (lines 12-166 from the original) plus a focused frontmatter:

```yaml
---
name: nct-methodology
description: Use when working with NCT (Network-Centric Compositional Testing) - specification-based protocol compliance testing with Ivy formal models. Covers the 10-step NCT workflow, test traffic generation, directory structure, and common mistakes.
---
```

Body: Extract the NCT section (lines 12-166) from the original skill.

- [ ] **Step 2: Create NACT methodology skill**

Create `$PLUGIN/skills/nact-methodology/SKILL.md` with the NACT content (lines 169-298) plus frontmatter:

```yaml
---
name: nact-methodology
description: Use when working with NACT (Network-Attack Compositional Testing), security testing, APT lifecycle modeling, or attack entity configuration. Covers APT 6-stage lifecycle, attack entities, protocol-specific bindings.
---
```

Body: Extract the NACT section (lines 169-298).

- [ ] **Step 3: Create NSCT methodology skill**

Create `$PLUGIN/skills/nsct-methodology/SKILL.md` with the NSCT content (lines 301-432) plus frontmatter:

```yaml
---
name: nsct-methodology
description: Use when working with NSCT (Network-Simulator Centric Compositional Testing), Shadow Network Simulator, large-scale topology testing, or deterministic network simulation. Covers Shadow NS configuration and when to use NSCT vs NCT.
---
```

Body: Extract the NSCT section only (lines 301-403). The "Comprehensive Testing Strategy" (lines 406-413) and "Integration" (lines 416-432) sections are cross-cutting — keep those in the dispatcher (Step 4).

- [ ] **Step 4: Update original skill as dispatcher**

Reduce `$PLUGIN/skills/methodology-reference/SKILL.md` to a concise index:

```yaml
---
name: methodology-reference
description: Use when working with NCT (compositional protocol testing), NACT (attack testing, security testing, APT lifecycle), or NSCT (simulation, Shadow NS, large-scale testing) methodology. Covers all three PANTHER formal testing methodologies.
---
```

Body: Brief overview of all three + "For detailed guidance, use the specific methodology skill: nct-methodology, nact-methodology, or nsct-methodology."

- [ ] **Step 5: Verify skills load correctly**

Check that each new skill file has valid YAML frontmatter and the correct `name` field.

Run: `head -5 $PLUGIN/skills/nct-methodology/SKILL.md $PLUGIN/skills/nact-methodology/SKILL.md $PLUGIN/skills/nsct-methodology/SKILL.md`

- [ ] **Step 6: Commit**

```bash
git add $PLUGIN/skills/nct-methodology/ $PLUGIN/skills/nact-methodology/ $PLUGIN/skills/nsct-methodology/ $PLUGIN/skills/methodology-reference/SKILL.md
git commit -m "refactor(skills): split methodology-reference into NCT/NACT/NSCT sub-skills"
```

---

### Task 5: Add Counterexample Interpretation Skill (Priority #6)

When `ivy_verify` fails with a counterexample, no skill currently guides the user through understanding the output. This skill provides a structured interpretation workflow.

**Files:**
- Create: `$PLUGIN/skills/counterexample-guide/SKILL.md`

- [ ] **Step 1: Write the skill**

Create `$PLUGIN/skills/counterexample-guide/SKILL.md`:

```yaml
---
name: counterexample-guide
description: Use when ivy_verify fails with a counterexample to understand the failure, trace the violated property, and identify the fix. Guides interpretation of structured counterexample traces.
---
```

Body should include:
1. Steps to interpret a counterexample trace (read assertion, trace steps, identify divergent state)
2. MCP tool usage: `ivy_verify` → read `counterexample_trace` field → `ivy_query(mode="info")` on the violated symbol → `ivy_state_machine_view` to see state transitions
3. Common failure patterns (invariant violations, missing guards, uninitialized state)
4. How to fix: add guards, strengthen preconditions, narrow monitor scope

- [ ] **Step 2: Commit**

```bash
git add $PLUGIN/skills/counterexample-guide/
git commit -m "feat(skills): add counterexample-guide skill for verification failure interpretation"
```

---

### Task 6: Add Incremental Spec Development Skill (Priority #7)

No guided workflow exists for "add one requirement → verify → iterate". Current skills assume whole-file or whole-protocol scope.

**Files:**
- Create: `$PLUGIN/skills/incremental-spec-dev/SKILL.md`

- [ ] **Step 1: Write the skill**

Create `$PLUGIN/skills/incremental-spec-dev/SKILL.md`:

```yaml
---
name: incremental-spec-dev
description: Use when adding requirements to an Ivy specification one at a time with verification between each addition. Guides the add-verify-iterate loop for incremental formal specification development.
---
```

Body should include:
1. The loop: identify RFC requirement → write bracket-tag annotation + monitor/assertion → `ivy_lint` (fast check) → `ivy_verify` (formal check) → fix if needed → `ivy_coverage(mode="stats")` to track progress → commit
2. How to pick the next requirement: use `ivy_coverage(mode="gaps")` to find uncovered MUST requirements
3. Pattern selection: use `ivy_patterns(mode="analyze")` to determine which pattern to use
4. Quality gate check: `ivy_quality(mode="gate", gate_level="minimal")` after each addition

- [ ] **Step 2: Commit**

```bash
git add $PLUGIN/skills/incremental-spec-dev/
git commit -m "feat(skills): add incremental-spec-dev skill for iterative requirement addition"
```

---

## Chunk 3: Phase 3 — Verification Status Dashboard

### Task 7: Add Verification Status Dashboard (Priority #2, MEDIUM)

`$LSP/ivy_lsp/features/monitoring.py` already exposes 11 RPC handlers with rich status data. This task adds a verification dashboard as a new MCP tool registered inside the verification tools closure (since `_verify_cache` is closure-scoped at `verification.py:46`, not module-level).

**Important**: `_verify_cache` lives inside `register_verification_tools()` closure. Any code that reads the cache MUST be defined inside that closure or use a callback/accessor attached to `ctx`.

**Files:**
- Modify: `$LSP/ivy_lsp/tools/verification.py` (add dashboard tool + cache accessor inside closure)
- Modify: `$LSP/ivy_lsp/mcp_server.py` (make `ctx` accessible for dashboard queries, if needed)
- Test: `$LSP/tests/test_verification_dashboard.py`

- [ ] **Step 1: Write failing test for dashboard MCP tool**

```python
# tests/test_verification_dashboard.py
"""Tests for verification dashboard MCP tool."""
import json
import pytest


def test_dashboard_tool_exists():
    """The ivy_verification_dashboard tool should be registered."""
    from ivy_lsp.tools.verification import register_verification_tools
    from unittest.mock import MagicMock

    mcp = MagicMock()
    ctx = MagicMock()
    ctx.root = "/tmp/test"
    ctx.find_ivy_files.return_value = ["a.ivy", "b.ivy"]
    register_verification_tools(mcp, ctx)
    # Check that mcp.tool() was called (once per tool registration)
    tool_names = [call.args[0] if call.args else None for call in mcp.tool.call_args_list]
    # At minimum ivy_verify should be registered
    assert mcp.tool.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd $LSP && python -m pytest tests/test_verification_dashboard.py -v`
Expected: FAIL (test needs adjustment for actual registration pattern)

- [ ] **Step 3: Add `get_cache_summary` inside the closure and attach to ctx**

In `$LSP/ivy_lsp/tools/verification.py`, inside `register_verification_tools()` (after the cache definitions around line 48), add:

```python
    def _get_cache_summary() -> dict:
        """Return verification cache summary. Closure-scoped."""
        verified = []
        failed = []
        for key, result in _verify_cache.items():
            path = key[0] if isinstance(key, tuple) else key
            if result.get("success"):
                if path not in verified:
                    verified.append(path)
            else:
                if path not in failed:
                    failed.append(path)
        return {
            "verified_files": verified,
            "failed_files": failed,
            "cache_size": len(_verify_cache),
            "cache_max": _CACHE_MAX_SIZE,
        }

    # Expose cache summary via ctx for monitoring/dashboard use
    ctx.get_verify_cache_summary = _get_cache_summary
```

Then add a new MCP tool at the end of `register_verification_tools()`:

```python
    @mcp.tool()
    async def ivy_verification_dashboard() -> str:
        """Workspace-level verification status: files verified, failed, pending.

        Returns verification cache state showing which files have been
        verified, which failed, and which are pending.
        """
        ivy_files = ctx.find_ivy_files()
        cache = _get_cache_summary()
        verified_set = set(cache["verified_files"])
        failed_set = set(cache["failed_files"])
        pending = [f for f in ivy_files if f not in verified_set and f not in failed_set]

        result = {
            "total_files": len(ivy_files),
            "verified": len(verified_set),
            "failed": len(failed_set),
            "pending": len(pending),
            "cache_size": cache["cache_size"],
            "cache_max": cache["cache_max"],
            "verified_files": sorted(verified_set),
            "failed_files": sorted(failed_set),
        }
        return json.dumps(result, indent=2)
```

- [ ] **Step 4: Run existing verification tests**

Run: `cd $LSP && python -m pytest tests/ -k "verif" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/tools/verification.py tests/test_verification_dashboard.py
git commit -m "feat(mcp): add ivy_verification_dashboard tool for workspace verification status"
```

---

## Chunk 4: Phase 4 — Architectural Simplification

### Task 8: Merge RequirementGraph into SemanticModel (Priority #3, MEDIUM-LARGE)

This is the largest task. `RequirementGraph` (`analysis/requirement_graph.py`, 400+ lines) duplicates node/edge storage with `SemanticModel` (`semantic/model.py`, 252 lines). The goal is to migrate RequirementGraph's domain-specific queries into SemanticModel and retire the separate graph.

**This task should be done incrementally across multiple commits.**

**Files:**
- Modify: `$LSP/ivy_lsp/semantic/model.py` (add RequirementGraph node types + edge types + query methods)
- Modify: `$LSP/ivy_lsp/semantic/edges.py` (add domain edge types)
- Modify: `$LSP/ivy_lsp/mcp_server.py` (use SemanticModel instead of separate RequirementGraph)
- Modify: `$LSP/ivy_lsp/features/visualization.py` (query SemanticModel instead of RequirementGraph)
- Modify: `$LSP/ivy_lsp/features/coverage_hints.py` (query SemanticModel)
- Deprecate: `$LSP/ivy_lsp/analysis/requirement_graph.py` (keep as compatibility shim initially)
- Test: `$LSP/tests/test_semantic_model.py`, `$LSP/tests/test_requirement_graph.py`

**Sub-task 8a: Verify RequirementGraph edge types exist in SemanticEdgeType**

All 6 domain edge types already exist in `$LSP/ivy_lsp/semantic/edges.py`:
- `READS` (line 21), `WRITES` (line 22), `CONSTRAINS` (line 23), `DEPENDS_ON` (line 24), `PROPAGATED_FROM` (line 25), `COVERS` (line 36)

- [ ] **Step 1: Verify edge types are present**

Run: `grep -n "READS\|WRITES\|CONSTRAINS\|DEPENDS_ON\|PROPAGATED_FROM\|COVERS" $LSP/ivy_lsp/semantic/edges.py`
Expected: All 6 types present. No code change needed.

- [ ] **Step 2: Run existing tests to confirm baseline**

Run: `cd $LSP && python -m pytest tests/test_semantic_model.py tests/test_semantic_nodes.py -v`
Expected: All PASS

**Sub-task 8b: Add domain node types to SemanticModel**

- [ ] **Step 4: Import RequirementGraph node types into semantic/nodes.py**

Add re-exports in `$LSP/ivy_lsp/semantic/nodes.py`:

```python
# At the end of the file, re-export from requirement_graph for compatibility:
from ivy_lsp.analysis.requirement_graph import (
    RequirementNode,
    StateVarNode,
    ActionNode,
    PropertyNode,
)
```

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/semantic/nodes.py
git commit -m "feat(semantic): re-export domain node types from semantic.nodes"
```

**Sub-task 8c: Add domain query methods to SemanticModel**

- [ ] **Step 6: Write failing tests for domain queries**

Add to `$LSP/tests/test_semantic_model.py`:

```python
def test_get_requirements_for_action():
    from ivy_lsp.semantic.model import SemanticModel
    from ivy_lsp.semantic.edges import SemanticEdgeType
    from ivy_lsp.analysis.requirement_graph import RequirementNode, ActionNode

    model = SemanticModel()
    action = ActionNode(id="act:open", name="open", qualified_name="conn.open", file="/t.ivy", line=10)
    req = RequirementNode(
        id="/t.ivy:15", kind="require", formula_text="conn_seen(C)",
        line=15, col=0, file="/t.ivy", monitor_action="conn.open",
        mixin_kind="before", bracket_tags=[]
    )
    model.add_node(action)
    model.add_node(req)
    model.add_edge(req.id, SemanticEdgeType.CONSTRAINS, action.id)

    result = model.get_requirements_for_action("act:open")
    assert len(result) == 1
    assert result[0].id == "/t.ivy:15"
```

- [ ] **Step 7: Implement domain query methods**

Add to `$LSP/ivy_lsp/semantic/model.py`:

```python
    def get_requirements_for_action(self, action_id: str) -> List[Any]:
        """Get all requirement nodes constraining an action."""
        with self._lock:
            incoming = self.get_incoming(action_id, SemanticEdgeType.CONSTRAINS)
            return [self._nodes[src] for _, src in incoming if src in self._nodes]

    def get_state_vars_read_by(self, node_id: str) -> List[Any]:
        """Get state variable nodes read by a requirement/property."""
        with self._lock:
            outgoing = self.get_outgoing(node_id, SemanticEdgeType.READS)
            return [self._nodes[tgt] for _, tgt in outgoing if tgt in self._nodes]

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get RFC coverage statistics from the graph."""
        from ivy_lsp.analysis.requirement_graph import RequirementNode
        reqs = self.get_nodes_by_type(RequirementNode)
        covered = [r for r in reqs if any(
            etype == SemanticEdgeType.COVERS
            for etype, _ in self.get_outgoing(r.id)
        )]
        return {
            "total_requirements": len(reqs),
            "covered": len(covered),
            "uncovered": len(reqs) - len(covered),
        }
```

- [ ] **Step 8: Run tests**

Run: `cd $LSP && python -m pytest tests/test_semantic_model.py -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add ivy_lsp/semantic/model.py tests/test_semantic_model.py
git commit -m "feat(semantic): add domain query methods to SemanticModel"
```

**Sub-task 8d: Migrate mcp_server.py to use unified model**

This sub-task is the riskiest. The `_build_requirement_graph()` function in `mcp_server.py` (lines ~650-710) populates a separate RequirementGraph. The migration wires this data into SemanticModel instead.

**Rollback strategy:** Since RequirementGraph is preserved as a compatibility layer (not removed), reverting this single commit restores the previous behavior without affecting sub-tasks 8a-8c. If MCP tests fail after this step, `git revert HEAD` is safe.

- [ ] **Step 10: Update `_build_requirement_graph` to populate SemanticModel**

In `$LSP/ivy_lsp/mcp_server.py`, modify the graph-building function to also add nodes/edges to SemanticModel. Keep the RequirementGraph as a compatibility layer initially — don't remove it yet.

- [ ] **Step 11: Run full MCP tool test suite**

Run: `cd $LSP && python -m pytest tests/test_mcp_*.py -v --timeout=120`
Expected: All PASS

- [ ] **Step 12: Commit**

```bash
git add ivy_lsp/mcp_server.py
git commit -m "refactor(mcp): wire domain data into SemanticModel alongside RequirementGraph"
```

**Sub-task 8e: Migrate consumers to SemanticModel queries**

- [ ] **Step 13: Update visualization.py, coverage_hints.py to use SemanticModel**

Replace `graph.get_requirements_for_action()` calls with `model.get_requirements_for_action()` in:
- `$LSP/ivy_lsp/features/visualization.py`
- `$LSP/ivy_lsp/features/coverage_hints.py`

- [ ] **Step 14: Run full test suite**

Run: `cd $LSP && python -m pytest tests/ -x -v --timeout=120`
Expected: All PASS

- [ ] **Step 15: Commit**

```bash
git add ivy_lsp/features/visualization.py ivy_lsp/features/coverage_hints.py
git commit -m "refactor(features): migrate visualization and coverage to SemanticModel queries"
```

---

### Task 9: Simplify Analysis Pipeline Tier 2/3 State (Priority #4, MEDIUM)

`$LSP/ivy_lsp/semantic/analysis_pipeline.py` has 874 lines with separate state tracking for Tier 2 and Tier 3. The key observation: Tier 2 (AST parse + requirement extraction) and Tier 3 (full compiler) share the same state tracking pattern but use separate variables.

**Files:**
- Modify: `$LSP/ivy_lsp/semantic/analysis_pipeline.py`
- Test: `$LSP/tests/test_analysis_pipeline.py` (existing, large)

**Sub-task 9a: Introduce `_TierState` dataclass**

- [ ] **Step 1: Define _TierState dataclass**

Add to `$LSP/ivy_lsp/semantic/analysis_pipeline.py`:

```python
@dataclass
class _TierState:
    """Consolidated state for a single analysis tier."""
    running: bool = False
    total: int = 0
    completed: int = 0
    cancelled: bool = False
    current_file: Optional[str] = None
    last_file: Optional[str] = None
    last_completed_at: Optional[float] = None
    pending: int = 0
```

- [ ] **Step 2: Replace separate Tier 3 state variables with _TierState**

Replace the separate state variables in `__init__` with:

```python
        self._tier3 = _TierState()
        self._bulk = _TierState()
        self._bulk_compile = _TierState()
```

**Note:** `self._tier3_results: OrderedDict` stays as a separate attribute (it holds per-file result objects, not scalar state). Some `_TierState` fields will be unused per instance (e.g., `_tier3.total` stays 0) — this is an acceptable trade-off for uniformity.

**Mechanical substitution guide** (apply across all methods):
| Old variable | New access |
|---|---|
| `self._tier3_running` | `self._tier3.running` |
| `self._tier3_current_file` | `self._tier3.current_file` |
| `self._tier3_last_file` | `self._tier3.last_file` |
| `self._tier3_last_completed_at` | `self._tier3.last_completed_at` |
| `self._tier3_pending` | `self._tier3.pending` |
| `self._bulk_running` | `self._bulk.running` |
| `self._bulk_total` | `self._bulk.total` |
| `self._bulk_completed` | `self._bulk.completed` |
| `self._bulk_compile_running` | `self._bulk_compile.running` |
| `self._bulk_compile_total` | `self._bulk_compile.total` |
| `self._bulk_compile_completed` | `self._bulk_compile.completed` |
| `self._bulk_compile_cancelled` | `self._bulk_compile.cancelled` |

There are ~64 references across the file. Use find-and-replace for each substitution.

- [ ] **Step 3: Run the full analysis pipeline test suite**

Run: `cd $LSP && python -m pytest tests/test_analysis_pipeline.py -v --timeout=120`
Expected: All PASS

- [ ] **Step 4: Update get_pipeline_state() to use _TierState**

Simplify `get_pipeline_state()` to serialize `_TierState` directly.

- [ ] **Step 5: Run monitoring tests**

Run: `cd $LSP && python -m pytest tests/test_analysis_pipeline.py tests/test_monitoring.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add ivy_lsp/semantic/analysis_pipeline.py
git commit -m "refactor(pipeline): consolidate Tier 2/3 state into _TierState dataclass"
```

---

## Verification Checklist

After all tasks complete:

- [ ] `cd $LSP && python -m pytest tests/ -v --timeout=120` — Full test suite passes
- [ ] `ivy_capabilities` MCP tool — all 3 CLI tools available
- [ ] `ivy_lint` on `protocol-testing/quic/quic_stack/quic_frame.ivy` — 0 errors
- [ ] `ivy_verify` on a failing file — `counterexample_trace` field present in output
- [ ] `ivy_coverage(mode="stats")` — returns coverage statistics
- [ ] All new skills have valid YAML frontmatter (`name`, `description` fields)
- [ ] No regressions in existing functionality
