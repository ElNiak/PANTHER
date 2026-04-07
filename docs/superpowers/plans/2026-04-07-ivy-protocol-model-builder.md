# Ivy Protocol Model Builder — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a skill in the panther-ivy-plugin that guides users through building a formal Ivy protocol model for any network protocol, using the existing NCT methodology and panther-ivy-plugin infrastructure.

**Architecture:** One orchestrator SKILL.md (~800 words) that drives a 6-phase interactive workflow, with 8 reference files for progressive disclosure and 1 worked example. The skill integrates with existing panther-ivy-plugin skills (`ivy-writing-guide`, `specification-patterns`, `nct-methodology`) rather than reteaching Ivy basics.

**Tech Stack:** Markdown skill files (SKILL.md + references/), Ivy language examples, panther-ivy-plugin skill infrastructure.

---

**Target directory:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/`

Abbreviated as `SKILL_DIR` below.

## File Map

| File | Responsibility |
|------|----------------|
| `SKILL_DIR/SKILL.md` | Orchestrator: frontmatter, overview, phase map, reference pointers, stop directives |
| `SKILL_DIR/references/phase-1-classification.md` | Protocol profiling questions, pattern selection table |
| `SKILL_DIR/references/phase-2-blueprint.md` | File tree template, module DAG, type mapping table |
| `SKILL_DIR/references/phase-3-core-types.md` | Types/structs/relations tutorial, build order, checkpoint commands |
| `SKILL_DIR/references/phase-4-entity-model.md` | Endpoint modules, shim pattern, behavior action, serialization |
| `SKILL_DIR/references/phase-5-behavioral-specs.md` | around/require/_generating, RFC extraction, debugging |
| `SKILL_DIR/references/phase-6-test-scenarios.md` | Test taxonomy, export/weight/finalize, attack models |
| `SKILL_DIR/references/ivy-quick-reference.md` | Language construct table (28 entries) |
| `SKILL_DIR/references/panther-ivy-infrastructure.md` | Built-in module table, compilation pipeline, include paths |
| `SKILL_DIR/examples/dns_types.ivy` | Minimal worked example: DNS-over-UDP types file |

---

### Task 1: Create Skill Directory Structure

**Files:**
- Create: `SKILL_DIR/SKILL.md`
- Create: `SKILL_DIR/references/` (directory)
- Create: `SKILL_DIR/examples/` (directory)

- [ ] **Step 1: Create the directory tree**

```bash
mkdir -p panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/references
mkdir -p panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/examples
```

- [ ] **Step 2: Verify structure**

```bash
ls -R panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/
```

Expected: `examples/`, `references/` directories visible.

- [ ] **Step 3: Commit**

```bash
git add -f panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/
git commit -m "feat(ivy-plugin): scaffold ivy-protocol-model-builder skill directory"
```

---

### Task 2: Write SKILL.md (Orchestrator)

**Files:**
- Create: `SKILL_DIR/SKILL.md`

The orchestrator must be lean (~800 words). It provides: frontmatter with trigger patterns, overview, phase map with stop directives, and pointers to references. It delegates Ivy language details to `ivy-writing-guide` and NCT methodology to `nct-methodology`.

- [ ] **Step 1: Write SKILL.md**

Write the file with this content:

```markdown
---
name: ivy-protocol-model-builder
description: "This skill should be used when the user asks to 'create an Ivy model', 'build a formal spec for a protocol', 'add a new protocol to panther_ivy', 'write Ivy tests for [protocol]', 'formalize [protocol] in Ivy', or wants to create a new protocol-testing directory with Ivy formal specifications. Guides classification, blueprint, and phased implementation with review checkpoints."
---

# Ivy Protocol Model Builder

> **Workspace**: Set active workspace with `/set-workspace <protocol>` before starting.

Interactive, phased workflow for creating a formal Ivy specification of any network protocol within panther_ivy. Covers protocol classification through test scenario creation. Assumes no Ivy experience — teaches constructs in context.

**Related skills**: `ivy-writing-guide` (Ivy syntax reference), `specification-patterns` (monitor patterns), `nct-methodology` (NCT/NACT/NSCT theory), `incremental-spec-dev` (incremental verification).

## Prerequisites

- panther_ivy submodule initialized
- Docker environment available for `ivyc target=test`
- The QUIC reference model at `protocol-testing/quic/` (200+ files)
- For Phases 5-6: at least one real protocol implementation to test against

## Phase Map

Six phases with mandatory checkpoints. Load the phase reference file at the start of each phase. Complete one phase before starting the next.

### Phase 1: Protocol Classification
**Load**: `references/phase-1-classification.md`

Ask 7 classification questions one at a time. Produce a protocol profile document. The profile resolves all architectural decisions for subsequent phases.

**STOP after Phase 1.** Present the protocol profile and pattern selection to the user. Do NOT proceed until the user confirms the classification is correct.

### Phase 2: Blueprint Generation
**Load**: `references/phase-2-blueprint.md`

Generate directory tree, module dependency graph, and RFC-to-Ivy type mapping table adapted to the protocol profile.

**STOP after Phase 2.** Present the file tree, dependency graph, and type mapping. Do NOT write any `.ivy` files until the user approves the architecture.

### Phase 3: Core Types and Stack
**Load**: `references/phase-3-core-types.md`

Write types, message structs, state tracking, and aggregator files. Verify with `ivy_check` (or `ivy_verify` MCP tool). Consult `ivy-writing-guide` skill for syntax reference.

**STOP after Phase 3.** Run `ivy_check` on the aggregator file. Present results and files to user. Do NOT proceed until user confirms type mappings match the RFC.

### Phase 4: Entity Model
**Load**: `references/phase-4-entity-model.md`

Create endpoint modules, entity files, base shim, role-specific shims, and serialization stubs. Verify with `ivyc target=test` (or `ivy_compile` MCP tool).

**STOP after Phase 4.** Compile a minimal test file. Present the compilation result. Do NOT proceed until user reviews entity architecture.

### Phase 5: Behavioral Specs
**Load**: `references/phase-5-behavioral-specs.md`

Extract RFC requirements, write `around`/`before` advice with `require` statements and `_generating` guards. Write role-specific behavioral files. Consult `specification-patterns` skill for monitor patterns.

**STOP after Phase 5.** Run compiled test against a real implementation. Present pass/fail results. Do NOT proceed until user confirms the requirement-to-`require` mapping.

### Phase 6: Test Scenarios
**Load**: `references/phase-6-test-scenarios.md`

Create conformance tests, feature-specific tests, error handling tests, and (conditionally) attack tests. Consult `nct-methodology` or `nact-methodology` skill for test design patterns.

**STOP after Phase 6.** Run the full test suite. Present results. User reviews pass/fail and confirms model is complete.

## MCP Tool Integration

Use panther-ivy-plugin MCP tools throughout:

| Phase | MCP Tool | Purpose |
|-------|----------|---------|
| 3 | `ivy_verify` | Validate types and state definitions |
| 3-4 | `ivy_diagnostics(mode="structural")` | Fast structural checks after each file |
| 4 | `ivy_compile(target="test")` | Compile to test binary |
| 5 | `ivy_coverage(mode="gaps")` | Find uncovered RFC requirements |
| 5-6 | `ivy_coverage(mode="matrix")` | Requirement-to-assertion mapping |
| 6 | `ivy_patterns(mode="check")` | Layer/pattern completeness |

## Reference Files

For detailed phase instructions and Ivy tutorials:
- **`references/phase-1-classification.md`** — Protocol profiling questions, pattern selection
- **`references/phase-2-blueprint.md`** — File tree templates, module DAG, type mapping
- **`references/phase-3-core-types.md`** — Ivy type system tutorial, build order, checkpoints
- **`references/phase-4-entity-model.md`** — Endpoint/shim/serialization/behavior patterns
- **`references/phase-5-behavioral-specs.md`** — around/require/_generating, RFC extraction, debugging
- **`references/phase-6-test-scenarios.md`** — Test taxonomy, export/weight/finalize, attack models
- **`references/ivy-quick-reference.md`** — Language construct table (28 entries)
- **`references/panther-ivy-infrastructure.md`** — Built-in modules, compilation pipeline

## Worked Example

**`examples/dns_types.ivy`** — Minimal DNS-over-UDP types file demonstrating Phase 3 output.
```

- [ ] **Step 2: Verify word count**

```bash
wc -w panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/SKILL.md
```

Expected: ~600-900 words. If over 1000, move content to references.

- [ ] **Step 3: Commit**

```bash
git add -f SKILL_DIR/SKILL.md
git commit -m "feat(ivy-plugin): add SKILL.md orchestrator for ivy-protocol-model-builder"
```

---

### Task 3: Write Phase 1 Reference — Protocol Classification

**Files:**
- Create: `SKILL_DIR/references/phase-1-classification.md`

Content sourced from design spec Phase 1 (lines 91-143). Includes all 7 classification questions, protocol profile template, and the pattern selection table with 12 entries. Must end with a STOP directive.

- [ ] **Step 1: Write phase-1-classification.md**

Write the file containing:
1. Purpose section (2 sentences)
2. Seven classification questions (numbered list, each with multiple-choice options)
3. Protocol profile output template (code block with 8 fields including the `Extensible` field)
4. Pattern selection table mapping 12 profile traits to architectural effects (from spec lines 126-139)
5. STOP directive: "STOP. Present the protocol profile and pattern selection to the user. Do NOT proceed to Phase 2 until the user explicitly confirms."

Reference the spec lines 91-143 for exact content. The classification questions must be asked ONE AT A TIME during execution — include this instruction prominently.

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/references/phase-1-classification.md
git commit -m "feat(ivy-plugin): add Phase 1 classification reference"
```

---

### Task 4: Write Phase 2 Reference — Blueprint Generation

**Files:**
- Create: `SKILL_DIR/references/phase-2-blueprint.md`

Content sourced from design spec Phase 2 (lines 147-232). Includes the blueprint directory tree template, simplification rules, module dependency DAG description, and type mapping table.

- [ ] **Step 1: Write phase-2-blueprint.md**

Write the file containing:
1. Ivy concepts taught: `include` composition, `#lang ivy1.7`, include DAG direction
2. Blueprint directory tree template (the full tree from spec lines 163-201 with all conditional directories)
3. Simplification rules (6 bullet points from spec lines 204-210)
4. File naming convention: stack files use `{proto}_*.ivy`, infrastructure/entity files use `ivy_{proto}_*.ivy`
5. Module dependency DAG description (explain the include flow from test files down to stack)
6. Type mapping table template (from spec lines 220-228, with note that syntax is explained in Phase 3)
7. STOP directive

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/references/phase-2-blueprint.md
git commit -m "feat(ivy-plugin): add Phase 2 blueprint reference"
```

---

### Task 5: Write Phase 3 Reference — Core Types and Stack

**Files:**
- Create: `SKILL_DIR/references/phase-3-core-types.md`

Content sourced from design spec Phase 3 (lines 236-287). This is the first phase that teaches Ivy constructs. Must cover types, structs, variants, relations, functions, actions, and init blocks. Includes QUIC model references with correct file paths and line numbers.

- [ ] **Step 1: Write phase-3-core-types.md**

Write the file containing:
1. Ivy concepts taught section (13 items from spec lines 244-257): scalar types, bit-vector sizing, enumerations, aliases, definitions, structs, `this` keyword, arrays, variants, relations, functions, `after init`, actions with empty bodies, boolean operators
2. QUIC model references (6 entries from spec lines 261-266 — exact file paths and line numbers)
3. Build order (5 steps from spec lines 270-274)
4. "What this phase does NOT do" section (spec lines 278)
5. Checkpoint section with exact command: `ivy_check {proto}_connection.ivy` (or `ivy_verify` MCP tool), expected output (no errors), and 3 common error types with fixes (spec lines 282-285)
6. Note: "For Ivy syntax details beyond this tutorial, consult the `ivy-writing-guide` skill."
7. STOP directive

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/references/phase-3-core-types.md
git commit -m "feat(ivy-plugin): add Phase 3 core types reference"
```

---

### Task 6: Write Phase 4 Reference — Entity Model

**Files:**
- Create: `SKILL_DIR/references/phase-4-entity-model.md`

Content sourced from design spec Phase 4 (lines 291-366). The most complex reference file — covers endpoint modules, parameter declarations, behavior action (with detailed explanation), shim wiring, serialization strategy.

- [ ] **Step 1: Write phase-4-entity-model.md**

Write the file containing:
1. Ivy concepts taught (8 items from spec lines 299-306): modules, instance, individual, parameter, import action, ip module, net module, behavior action
2. Detailed `behavior` action section (from spec lines 308-319): what it does (5 steps), complexity scaling, incremental approach
3. QUIC model references (4 entries from spec lines 323-326 — note `quic_entities_behavior/` for endpoint.ivy)
4. Entity pattern: three layers per role (from spec lines 329-332)
5. Adaptation by protocol shape table (5 entries from spec lines 337-342)
6. Serialization strategy: pass-through vs full ser/deser, transition point (from spec lines 346-350)
7. Build order (5 steps from spec lines 354-358)
8. Checkpoint: `ivyc target=test` (or `ivy_compile` MCP tool) command, expected output, sample invocation command (from spec lines 362-366)
9. STOP directive

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/references/phase-4-entity-model.md
git commit -m "feat(ivy-plugin): add Phase 4 entity model reference"
```

---

### Task 7: Write Phase 5 Reference — Behavioral Specs

**Files:**
- Create: `SKILL_DIR/references/phase-5-behavioral-specs.md`

Content sourced from design spec Phase 5 (lines 370-458). Covers the heart of the formal model: `around`/`before`/`after` advice, `require` statements, `_generating` predicate, role inversion, debugging.

- [ ] **Step 1: Write phase-5-behavioral-specs.md**

Write the file containing:
1. Ivy concepts taught (7 items from spec lines 378-398): advice blocks, require, `_generating`, `~` as not, role inversion, multiple around blocks, dual-role specification pattern (with code example)
2. QUIC model references (3 entries from spec lines 402-405 — corrected line range 405-729)
3. Requirement extraction process (4 steps from spec lines 409-413)
4. Adaptation by protocol shape table (4 entries from spec lines 417-422)
5. Build order (5 steps from spec lines 426-430)
6. Debugging failing requirements section (4-step methodology from spec lines 432-443)
7. Common failure modes (4 entries from spec lines 446-450)
8. Checkpoint: run command, expected output, how to distinguish model bugs from real spec violations (from spec lines 454-458)
9. Note: "For monitor patterns and specification best practices, consult the `specification-patterns` skill."
10. STOP directive

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/references/phase-5-behavioral-specs.md
git commit -m "feat(ivy-plugin): add Phase 5 behavioral specs reference"
```

---

### Task 8: Write Phase 6 Reference — Test Scenarios

**Files:**
- Create: `SKILL_DIR/references/phase-6-test-scenarios.md`

Content sourced from design spec Phase 6 (lines 462-557). Covers test file composition, role inversion in includes, four test categories, and attack model construction.

- [ ] **Step 1: Write phase-6-test-scenarios.md**

Write the file containing:
1. Ivy concepts taught (4 items from spec lines 470-473): export declarations, action weights, `_finalize`, test file structure
2. QUIC model references (4 entries from spec lines 477-480)
3. Role inversion in test files section with code example (from spec lines 484-490)
4. Test scenario taxonomy (4 categories from spec lines 494-539):
   - Category 1: Basic conformance with code template (from spec lines 498-521 — uses role inversion: `ivy_{proto}_shim_{opposite_role}`)
   - Category 2: Feature-specific (2 sentences)
   - Category 3: Error handling (2 sentences)
   - Category 4: Attack tests (4 requirements, QUIC references)
5. Build order (4 steps from spec lines 542-546)
6. Checkpoint: test suite run command, how to interpret results (from spec lines 550-557)
7. Note: "For NCT/NACT test design methodology, consult the `nct-methodology` or `nact-methodology` skill."
8. STOP directive (final phase — congratulate user on completing the model)

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/references/phase-6-test-scenarios.md
git commit -m "feat(ivy-plugin): add Phase 6 test scenarios reference"
```

---

### Task 9: Write Ivy Quick Reference

**Files:**
- Create: `SKILL_DIR/references/ivy-quick-reference.md`

Content sourced from design spec lines 561-593. A standalone reference table with 28 Ivy language constructs.

- [ ] **Step 1: Write ivy-quick-reference.md**

Write the file containing the full 28-row table from spec lines 565-593. Each row has: Construct, Syntax, Purpose. Include all entries: Type, Enumeration, Alias, Definition, Struct, Variant, Array, Relation, Function, Individual, Parameter, Action, Import action, Around/Before/After advice, Require, Boolean operators, `_generating`, Export, Weight, Finalize, Module, Instance, Include, Init.

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/references/ivy-quick-reference.md
git commit -m "feat(ivy-plugin): add Ivy quick reference table"
```

---

### Task 10: Write panther-ivy Infrastructure Reference

**Files:**
- Create: `SKILL_DIR/references/panther-ivy-infrastructure.md`

Content sourced from design spec lines 595-614 plus the compilation pipeline section (lines 42-59).

- [ ] **Step 1: Write panther-ivy-infrastructure.md**

Write the file containing:
1. Compilation pipeline section (from spec lines 42-59): `ivy_check` vs `ivyc target=test` vs binary execution, with MCP tool alternatives (`ivy_verify`, `ivy_compile`)
2. Built-in modules table (12 entries from spec lines 599-612)
3. Include path resolution note (spec line 614)
4. File naming convention (spec lines 64-70)

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/references/panther-ivy-infrastructure.md
git commit -m "feat(ivy-plugin): add panther-ivy infrastructure reference"
```

---

### Task 11: Write DNS Types Worked Example

**Files:**
- Create: `SKILL_DIR/examples/dns_types.ivy`

A minimal, compilable DNS-over-UDP types file that demonstrates the Phase 3 output. Shows scalar types, enumerations, bit-vector interpretations, a message struct, and an event action declaration.

- [ ] **Step 1: Write dns_types.ivy**

```ivy
#lang ivy1.7

# DNS-over-UDP Types — Minimal Worked Example
# Demonstrates Phase 3 output for the Ivy Protocol Model Builder skill.
# This file defines the core types for a simplified DNS model.

# --- Scalar types with bit-vector interpretations ---

type query_id
interpret query_id -> bv[16]

type rr_count
interpret rr_count -> bv[16]

# --- Enumerations ---

type dns_opcode = {query, iquery, status}

type dns_rcode = {noerror, formerr, servfail, nxdomain, notimp, refused}

type dns_qtype = {a, aaaa, cname, mx, ns, txt, soa, ptr}

type dns_qclass = {in_class, ch_class, hs_class, any_class}

# --- Message struct ---

object dns_message = {
    type this = struct {
        id       : query_id,      # Transaction ID
        is_response : bool,       # QR bit: false=query, true=response
        opcode   : dns_opcode,    # Operation code
        rcode    : dns_rcode,     # Response code (meaningful in responses)
        qdcount  : rr_count,      # Number of questions
        ancount  : rr_count,      # Number of answer RRs
        qtype    : dns_qtype,     # Query type
        qclass   : dns_qclass     # Query class
    }

    instance idx : unbounded_sequence
    instance arr : array(idx, this)
}

# --- Protocol event (empty body — behavior defined by advice in Phase 5) ---

action message_event(src:ip.endpoint, dst:ip.endpoint, msg:dns_message) = {}

# --- State tracking ---

relation query_seen(Q:query_id)
relation query_responded(Q:query_id)
function query_count : rr_count

after init {
    query_seen(Q) := false;
    query_responded(Q) := false;
    query_count := 0;
}
```

- [ ] **Step 2: Commit**

```bash
git add -f SKILL_DIR/examples/dns_types.ivy
git commit -m "feat(ivy-plugin): add DNS types worked example"
```

---

### Task 12: Final Validation

**Files:**
- All files in `SKILL_DIR/`

- [ ] **Step 1: Verify all files exist**

```bash
find panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/ -type f | sort
```

Expected: 11 files (SKILL.md + 8 references + 1 example + possibly .gitkeep).

- [ ] **Step 2: Verify SKILL.md frontmatter**

```bash
head -5 panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/SKILL.md
```

Expected: valid YAML frontmatter with `name` and `description`.

- [ ] **Step 3: Check SKILL.md word count**

```bash
wc -w panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/skills/ivy-protocol-model-builder/SKILL.md
```

Expected: 600-1000 words.

- [ ] **Step 4: Verify all referenced files exist**

```bash
grep -oP 'references/[^\s`*]+\.md' SKILL_DIR/SKILL.md | while read f; do
    test -f "SKILL_DIR/$f" && echo "OK: $f" || echo "MISSING: $f"
done
```

Expected: all OK, no MISSING.

- [ ] **Step 5: Verify examples exist**

```bash
test -f SKILL_DIR/examples/dns_types.ivy && echo "OK" || echo "MISSING"
```

Expected: OK.

- [ ] **Step 6: Final commit with all files**

If any files were missed in per-task commits:
```bash
git add -f SKILL_DIR/
git status
git commit -m "feat(ivy-plugin): complete ivy-protocol-model-builder skill"
```
