# Ivy Debugging Skill Efficiency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve how Claude debugs Ivy specs by enforcing a mandatory research-before-fix workflow, providing an error pattern lookup table, enriching existing skills/agents, and adding new LSP and linter diagnostics.

**Architecture:** Two new skills (methodology + error patterns) provide debugging knowledge. Four existing skill/agent files get surgical updates to enforce the methodology. Three ivy-lsp source files get new diagnostic checks. The ivy-lsp changes are TDD with pytest.

**Tech Stack:** Markdown (skills/agents), Python 3.10+ (ivy-lsp), pytest (tests)

**Repos:**
- Plugin: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/` (skills + agents, Markdown only)
- ivy-lsp: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/` (Python + tests)

**Deferred to future work:**
- Unused include detection (spec 5b item 3) — requires full symbol table to track which included symbols are referenced; Info severity, low priority. Can be added later when the LSP's semantic model is enriched.

---

## Phase A: Plugin Skills and Agents (Markdown only, no tests needed)

### Task 1: Create `ivy-debugging-methodology` Skill

**Files:**
- Create: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/skills/ivy-debugging-methodology/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: ivy-debugging-methodology
description: Use when debugging Ivy verification or compilation errors. Enforces a mandatory pre-fix research workflow. Must be followed before proposing any fix to an Ivy spec. Triggers on "debugging ivy", "fix ivy error", "verification failed", "compilation error", "ivy_check failed", "diagnose ivy", or any attempt to fix a failing Ivy specification.
---

# Ivy Debugging Methodology

## Hard Rule

You MUST complete steps 1-6 before proposing ANY fix. Skipping directly to a fix is forbidden.
If you cannot find a working example or skill reference that explains the error, say so explicitly rather than guessing.

## Mandatory Pre-Fix Checklist

### Step 1: Parse the Error

Extract from the error output:
- **Error type** (the key phrase: `not found`, `invariant failed`, `type mismatch`, etc.)
- **Line number** and **file path**
- **Symbol or construct** that failed

### Step 2: Diagnostic Interpretation Protocol

If the error came from `ivy_verify`, `ivy_lint`, or LSP diagnostics, read the **full `diagnostics` array**, not just `error_summary`.

Classify each diagnostic by its `source` field:

| Source | Layer | What It Means |
|--------|-------|---------------|
| `"ivy"` | Parser | Syntax or parse error in the Ivy file |
| `"ivy-lint"` | Structural | Fast structural check (braces, headers, includes) |
| `"ivy-lsp"` | LSP analysis | In-process semantic check (collisions, missing init) |
| `"ivy-lsp-reqs"` | Requirements | Requirement coverage gap |
| `"ivy-lsp-semantic"` | RFC tags | Orphaned or missing bracket tags |
| `"ivy-lsp-coverage"` | Coverage | Unmonitored actions or unguarded state |
| `"ivy_check"` | Verification | Full formal verification result |

**Priority cascade:** Fix Error-severity diagnostics first. Then Warning. Then Info/Hint.

When a diagnostic points to a specific line, read 5 lines above and below before forming a hypothesis.

### Step 3: Consult Skills

Load and check these skills for the failing construct:
- `ivy-error-patterns` — look up the specific error message substring
- `ivy-model-editing` — check syntax rules for the construct type (relation, function, action, invariant, etc.)

### Step 4: Run Linter

Call `ivy_lint` via MCP before running full verification:
```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint(relative_path="<file>")
```
This runs in milliseconds and catches structural issues (missing `#lang`, unmatched braces, unresolved includes, parameter name collisions, missing init) without the cost of full `ivy_check`.

### Step 5: Search Existing Models for Working Examples

Use `Grep` to find similar constructs in `protocol-testing/`:

- For `relation` issues: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/")`
- For `function` issues: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/")`
- For `after init` issues: `Grep(pattern="after init", glob="*.ivy", path="protocol-testing/")`
- For `invariant` issues: `Grep(pattern="^invariant ", glob="*.ivy", path="protocol-testing/")`
- For `action` issues: `Grep(pattern="^action |^    action ", glob="*.ivy", path="protocol-testing/")`

**Prioritize models for the same protocol family** (e.g., when debugging BGP, search `protocol-testing/bgp/` first).

### Step 6: Formulate Theory

Before editing anything, state a specific hypothesis:
- "The error `'src' not found` occurs because Ivy resolves parameter names as symbols. Existing QUIC models use single uppercase letters (C, S, P). The fix is to rename `src` to `S`."

The theory MUST reference evidence from steps 2-5. If you have no evidence, say so.

### Step 7: Apply Minimal Fix

Only now propose a change. Make it minimal — change only what's needed to fix the specific error.

### Step 8: Verify

Run verification to confirm the fix:
```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify(relative_path="<file>")
```
If the fix introduces new errors, return to Step 1 for the new error.
```

- [ ] **Step 2: Verify the skill file renders correctly**

Read the file back and confirm frontmatter is valid (name, description, no syntax errors in the markdown).

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add skills/ivy-debugging-methodology/SKILL.md
git commit -m "feat: add ivy-debugging-methodology skill with mandatory pre-fix checklist"
```

---

### Task 2: Create `ivy-error-patterns` Skill

**Files:**
- Create: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/skills/ivy-error-patterns/SKILL.md`

- [ ] **Step 1: Create the skill file**

```markdown
---
name: ivy-error-patterns
description: Use when encountering any Ivy error message to look up the root cause and correct fix. Lookup table mapping cryptic Ivy errors to causes, correct patterns, and working examples. Triggers on any Ivy error message including "not found", "ungrounded", "invariant failed", "assumption failed", "type mismatch", "type error", "circular dependency", "not well-founded", "no instances", "timeout", "unknown", "multiple definitions", "cannot find isolate".
---

# Ivy Error Patterns Reference

Lookup table for Ivy error messages. Each entry maps a cryptic error to its root cause and the correct fix, with pointers to working examples in `protocol-testing/`.

## How to Use

1. Find the error message substring in the section headings below
2. Read the root cause and correct pattern
3. Check the working example to confirm the fix matches existing conventions
4. Apply the fix

---

## 1. `'<name>' not found` on relation/function declaration

**Trigger:** Using a parameter name that collides with an existing symbol or is parsed as an unresolved reference.

```ivy
# WRONG — Ivy resolves 'src' as a symbol reference, not a fresh binder
relation update_processed(src:bgp_id, dst:bgp_id)
# Error: 'src' not found
```

**Root Cause:** In Ivy, the token before `:` in a parameter list is resolved as a symbol in the current scope. If `src` exists as a declared object, type, or individual, it binds to that instead of being treated as a fresh parameter name. If `src` does not exist at all, Ivy reports `'src' not found` because it tried to resolve it as a reference.

**Correct Pattern:** Use single uppercase letter parameter names that are unambiguous fresh binders:

```ivy
# RIGHT — conventional single-letter parameter names
relation update_processed(S:bgp_id, D:bgp_id)
```

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_packet.ivy:229` — `relation conn_seen(C:cid)`
- `protocol-testing/bgp/bgp_shims/bgp_shim.ivy:41` — `relation isup(A:ip.addr)`

**Related:** `ivy-model-editing` skill > Relations section

---

## 2. `ungrounded variable X in relation`

**Trigger:** Free variable in a relation expression not bound by a quantifier or the head of a rule.

**Root Cause:** All variables in relation expressions must be bound. A variable that appears in the body but not in the head and not under a quantifier is "ungrounded."

**Correct Pattern:** Bind with explicit quantifiers or ensure variables appear in the head:

```ivy
# WRONG — X is free
invariant recv(X,Y) -> sent(X,Y)

# RIGHT — X and Y are implicitly universally quantified (this is fine for invariants)
# But in action bodies or requires, use explicit quantifiers:
require exists S. req(other, S, self);
```

**Working Examples:**
- `protocol-testing/bgp/bgp_utils/bgp_network.ivy:56` — `require exists S. req(other,S,self);`

**Related:** `ivy-model-editing` skill > Invariants section

---

## 3. `invariant ... failed` / `failed to verify invariant preservation`

**Trigger:** An action modifies state in a way that violates a declared invariant.

**Root Cause:** One of:
- Missing state update (a relation is modified but a dependent relation is not updated)
- Missing precondition (the action is called in a state where the invariant cannot be maintained)
- Invariant too strong (it cannot be maintained by any correct action sequence)

**Correct Pattern:**
1. Check all modified relations are updated consistently
2. Add `require` guards to actions
3. Verify `after init` blocks set initial state compatible with the invariant

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_packet.ivy:300` — `after init` block initializing all relations
- `protocol-testing/bgp/bgp_utils/bgp_network.ivy:56-70` — `require` guards on actions

**Related:** `ivy-model-editing` skill > Invariants, Actions sections

---

## 4. `assumption failed` (isolate assumption violation)

**Trigger:** An isolate's assumptions about another isolate's behavior are not satisfied.

**Root Cause:** The specification of the assumed isolate does not guarantee what the assuming isolate expects.

**Correct Pattern:**
1. Run `ivy_model_info` to list all isolates
2. Check each isolate's assumptions against its specification
3. Strengthen the assumed isolate's specification, or weaken the assumption

**Working Examples:** Search for `object` and `specification` blocks in the protocol family.

**Related:** `ivy-model-editing` skill > Isolates section

---

## 5. `type mismatch` / `type error`

**Trigger:** Incompatible types in an expression (e.g., using `nat` where `packet_type` is expected).

**Root Cause:** Ivy's type system is strict with no implicit coercions.

**Correct Pattern:** Ensure all variables and expressions have consistent types. Check type declarations.

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_transport_parameters.ivy:226` — `function initial_max_stream_data_uni_server_0rtt : stream_pos`

**Related:** `ivy-model-editing` skill > Type Declarations section

---

## 6. `circular dependency`

**Trigger:** Two or more modules or objects depend on each other via includes.

**Root Cause:** Ivy does not support circular include dependencies.

**Correct Pattern:** Structure files as a DAG. Introduce abstract interfaces to break cycles.

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_transport_parameters.ivy:3-5` — linear include chain: `include quic_types`, `include quic_transport_error_code`, `include quic_stream`
- `protocol-testing/bgp/bgp_utils/random_value.ivy:3` — single include: `include bgp_type`

**Related:** `ivy-model-editing` skill > Include Directives section

---

## 7. `not well-founded`

**Trigger:** A recursive definition does not terminate.

**Root Cause:** Ivy requires well-founded recursion for soundness.

**Correct Pattern:** Add a termination measure or restructure to avoid recursion.

**Related:** `ivy-model-editing` skill > Definitions section

---

## 8. `uninterpreted sort has no instances`

**Trigger:** A type was declared but never given concrete values.

**Root Cause:** The type is abstract with no constructors or axioms.

**Correct Pattern:** Add at least one constructor or axiom providing instances of the sort.

**Related:** `ivy-model-editing` skill > Type Declarations section

---

## 9. Z3 timeout / `unknown`

**Trigger:** Verification takes too long; the SMT solver cannot decide.

**Root Cause:** Proof obligation too complex (deep quantifier nesting, large isolates, complex arithmetic).

**Correct Pattern:**
1. Break into smaller lemmas
2. Add ghost state or auxiliary invariants to guide the prover
3. Use `isolate` boundaries to limit what the solver must reason about
4. Reduce quantifier nesting depth

**Related:** `ivy-verification` skill > Z3 timeout section

---

## 10. `multiple definitions`

**Trigger:** Same symbol declared in multiple included files.

**Root Cause:** Include graph brings in conflicting declarations.

**Correct Pattern:**
1. Run `ivy_include_graph` to trace the duplicate
2. Remove one declaration or namespace it inside an `object`

**Related:** `ivy-model-editing` skill > Module System section

---

## 11. `cannot find isolate X`

**Trigger:** Misspelled isolate name or missing declaration.

**Root Cause:** The isolate name in the command does not match any declaration in the file.

**Correct Pattern:**
1. Check spelling of the isolate name
2. Run `ivy_model_info` to list declared isolates

**Related:** `ivy-model-editing` skill > Isolates section

---

## 12. Missing `after init` causing arbitrary initial values

**Trigger:** Invariant fails on initial state; relations have unexpected values.

**Root Cause:** Without `after init`, relations start with arbitrary (unconstrained) values.

**Correct Pattern:** Explicitly initialize all mutable relations in `after init` blocks:

```ivy
after init {
    conn_seen(C) := false;
    last_pkt_num(C,L) := 0;
    conn_closed(C) := false;
}
```

**Working Examples:**
- `protocol-testing/quic/quic_stack/quic_packet.ivy:300` — `after init { conn_seen(C) := false; ... }`
- `protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy:10` — `after init {`

**Related:** `ivy-model-editing` skill > Common Pitfalls > Forgetting `after init` blocks

---

## Protocol-Specific Patterns

This section will grow as new protocol-specific errors are encountered. Add entries here when an error pattern is specific to a protocol family (BGP, QUIC, CoAP, etc.) rather than being a general Ivy language issue.
```

- [ ] **Step 2: Verify the skill file renders correctly**

Read the file back and confirm frontmatter is valid.

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add skills/ivy-error-patterns/SKILL.md
git commit -m "feat: add ivy-error-patterns skill with 12-entry error-to-fix lookup table"
```

---

### Task 3: Update `ivy-model-editing` Skill — Add Syntax Traps + Callouts

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/skills/ivy-model-editing/SKILL.md:36-38` (Relations section) and `:322-367` (after Common Pitfalls)

- [ ] **Step 1: Add "Before You Write" callout to Relations section**

Find this text at line 36:

```markdown
### Relations

Relations declare state predicates over typed arguments.
```

Replace with:

```markdown
### Relations

> **Before writing a new relation**, grep `protocol-testing/` for similar declarations to see the canonical pattern for your protocol family: `Grep(pattern="^relation ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

Relations declare state predicates over typed arguments.
```

- [ ] **Step 2: Add "Before You Write" callout to Functions section**

Find this text at line 48:

```markdown
### Functions and Individuals
```

Replace with:

```markdown
### Functions and Individuals

> **Before writing a new function**, grep `protocol-testing/` for similar declarations: `Grep(pattern="^function ", glob="*.ivy", path="protocol-testing/<your-protocol>/")`
```

- [ ] **Step 3: Add "Before You Write" callout to Actions section**

Find this text at line 58:

```markdown
### Actions

Actions model state transitions.
```

Replace with:

```markdown
### Actions

> **Before writing a new action**, grep `protocol-testing/` for similar patterns: `Grep(pattern="action.*=", glob="*.ivy", path="protocol-testing/<your-protocol>/")`

Actions model state transitions.
```

- [ ] **Step 4: Add "Common Syntax Traps" section after Best Practices**

Find the `**IMPORTANT**:` footer at line 367 and insert before it:

```markdown
## Common Syntax Traps

These patterns produce misleading error messages. See `ivy-error-patterns` skill for the full catalog.

### Trap 1: Parameter Name Collision

```ivy
# WRONG — 'src' not found (Ivy resolves parameter names as symbol references)
relation update_processed(src:bgp_id, dst:bgp_id)

# RIGHT — single uppercase letter parameter names are unambiguous fresh binders
relation update_processed(S:bgp_id, D:bgp_id)
```

Ivy resolves the token before `:` in a parameter list as a symbol. Use single uppercase letters (C, S, P, N, D) as parameter names. See `ivy-error-patterns` entry #1.

### Trap 2: Missing `after init` with Misleading Invariant Failure

```ivy
# Invariant fails on initial state — but the invariant is correct!
relation conn_seen(C:cid)
invariant conn_seen(C) -> connected(C)
# Error: invariant failed (because conn_seen starts as arbitrary, not false)

# FIX — initialize the relation
after init {
    conn_seen(C) := false;
}
```

See `ivy-error-patterns` entry #12.

### Trap 3: `assume` vs `require` Confusion

```ivy
# WRONG — weakens the model; the assumption is never verified
action handle(p:packet) = {
    assume valid(p);
    # ...
}

# RIGHT — precondition that callers must satisfy, verified by ivy_check
action handle(p:packet) = {
    require valid(p);
    # ...
}
```

### Trap 4: Ungrounded Variable in Invariant

```ivy
# WRONG — "for all P and N, sent(P,N) is true" (probably not intended)
invariant sent(P, N)

# RIGHT — constrained relationship
invariant sent(P, N) -> connected(source(P), N)
```

See `ivy-error-patterns` entry #2.

### Trap 5: Overly Strong Invariant

```ivy
# WRONG — fails immediately because conn_seen starts false for some C
invariant connected(C)

# RIGHT — conditional invariant
invariant connected(C) -> conn_seen(C)
```

```

- [ ] **Step 5: Verify the file reads correctly**

Read the file back and confirm edits are in the right places.

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add skills/ivy-model-editing/SKILL.md
git commit -m "feat: add syntax traps section and Before You Write callouts to ivy-model-editing"
```

---

### Task 4: Update `ivy-verification` Skill — Replace Debugging Workflow

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/skills/ivy-verification/SKILL.md:76-88`

- [ ] **Step 1: Replace the Debugging Workflow section**

Find lines 76-88:

```markdown
## Debugging Workflow

Follow this cycle when verification fails:

1. **Check**: Run verification via `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify`.
2. **Read the error**: Note the line number, error type, and any counterexample trace.
3. **Locate the issue**: Use Claude's `Grep` tool or native LSP go-to-definition to navigate to the failing symbol.
4. **Diagnose**: Determine if the issue is:
   - A missing invariant (the model under-specifies expected behavior)
   - A bug in the action logic (the model is incorrect)
   - A missing precondition (the action is called in unexpected contexts)
5. **Fix**: Apply the minimal fix using Claude's `Edit` tool. Prefer adding invariants over weakening specifications.
6. **Re-check**: Run verification again. Repeat until all checks pass.
```

Replace with:

```markdown
## Debugging Workflow

**When verification fails, you MUST follow the `ivy-debugging-methodology` skill.** Do NOT attempt fixes without completing the pre-fix checklist (parse error → interpret diagnostics → consult skills → run linter → search examples → formulate theory → fix → verify).

For quick error lookups, consult the `ivy-error-patterns` skill which maps cryptic error messages to root causes, correct patterns, and working examples from `protocol-testing/`.
```

- [ ] **Step 2: Add cross-references to Common Errors section**

Find line 90:

```markdown
## Common Ivy Verification Errors and Fixes
```

Replace with:

```markdown
## Common Ivy Verification Errors and Fixes

> For the full error pattern catalog with working examples, see the `ivy-error-patterns` skill. The entries below are a quick reference subset.
```

- [ ] **Step 3: Verify the file**

Read the file back to confirm edits.

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add skills/ivy-verification/SKILL.md
git commit -m "feat: replace debugging workflow with mandatory methodology reference"
```

---

### Task 5: Update `spec-verifier` Agent — Mandatory Skill Loading + Diagnostic Breakdown

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/agents/spec-verifier.md:57-73`

- [ ] **Step 1: Add mandatory pre-diagnosis requirements**

Find lines 57-73 (the "Verification Workflow" section):

```markdown
**Verification Workflow:**

Step 1: Run `ivy_check` on the target file
- Parse the JSON result (stdout, stderr, return_code)
- Return code 0 = all checks pass
- Non-zero = failures detected

Step 2: Interpret results
- Identify the type of failure from stderr output
- Cross-reference with spec structure using `Grep` (or native LSP go-to-definition) and `Read`

Step 3: Present structured results
- Format: PASS/FAIL with details
- For failures: identify the failing isolate/invariant/property, the source location, and the likely cause

Step 4: Suggest fixes
- Based on the failure type, suggest specific changes to the spec
```

Replace with:

```markdown
**Mandatory Pre-Diagnosis Requirements:**

Before diagnosing ANY failure, you MUST:
1. Load and follow the `ivy-debugging-methodology` skill (mandatory pre-fix checklist)
2. Consult `ivy-error-patterns` for the specific error message
3. Run `ivy_lint` first for fast structural checks before full verification
4. Search `protocol-testing/` for working examples of the failing construct using `Grep`

**Verification Workflow:**

Step 1: Run `ivy_lint` for fast structural checks (milliseconds)
- Parse the result for structural issues (missing headers, braces, includes, parameter collisions)
- If structural issues found, fix those first before running full verification

Step 2: Run `ivy_check` on the target file
- Parse the JSON result (stdout, stderr, return_code)
- Return code 0 = all checks pass
- Non-zero = failures detected

Step 3: Interpret results using Diagnostic Breakdown
- Read the FULL `diagnostics` array, not just `error_summary`
- Present all diagnostics in structured table format (see Output Format below)
- Cross-reference each diagnostic with `ivy-error-patterns` for known causes
- Cross-reference with spec structure using `Grep` (or native LSP go-to-definition) and `Read`

Step 4: Search for working examples
- Before suggesting any fix, grep `protocol-testing/` for the construct that failed
- Compare the failing code with working examples from the same protocol family

Step 5: Present structured results
- Format: PASS/FAIL with Diagnostic Breakdown table
- For failures: identify the failing isolate/invariant/property, the source location, the known pattern (if any), and the likely cause

Step 6: Suggest fixes
- Based on the failure type AND working examples found, suggest specific changes
- Each fix must reference evidence (error pattern entry or working example)
```

- [ ] **Step 2: Add Diagnostic Breakdown to the Output Format**

Find the output format template at line 116:

```markdown
**Output Format:**
```
## Verification Result: {PASS|FAIL}
```

Replace with:

```markdown
**Output Format:**
```
## Verification Result: {PASS|FAIL}

**File:** {relative_path}
**Tool:** ivy_lint / ivy_check / ivy_compile / ivy_model_info

### Diagnostic Breakdown
| # | Severity | Source | Line | Message | Known Pattern? |
|---|----------|--------|------|---------|----------------|
| 1 | error | ivy_check | 42 | invariant failed | Entry #3: missing state update |
| 2 | warning | ivy-lsp | 15 | param name collision | Entry #1: use single-letter names |
```

Remove the old output format block that starts with `## Verification Result: {PASS|FAIL}` and ends with `{What to do next}` and replace the full block with:

```markdown
**Output Format:**
```
## Verification Result: {PASS|FAIL}

**File:** {relative_path}
**Tool:** ivy_lint / ivy_check / ivy_compile / ivy_model_info

### Diagnostic Breakdown
| # | Severity | Source | Line | Message | Known Pattern? |
|---|----------|--------|------|---------|----------------|
| {n} | {severity} | {source} | {line} | {message} | {ivy-error-patterns entry or "—"} |

### Issues Found (if FAIL)
1. **{Issue Type}** at {location}
   - Description: {what failed}
   - Known pattern: {ivy-error-patterns entry # or "not in catalog"}
   - Working example: {file:line from protocol-testing/ or "none found"}
   - Likely cause: {why it failed}
   - Suggested fix: {how to fix, referencing the working example}

### Next Steps
{What to do next}
```
```

- [ ] **Step 3: Verify the file**

Read the file back to confirm edits.

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add agents/spec-verifier.md
git commit -m "feat: add mandatory skill loading and diagnostic breakdown to spec-verifier"
```

---

### Task 6: Update `ivy-model-reviewer` Agent — Add Syntax Trap Anti-Patterns

**Files:**
- Modify: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/agents/ivy-model-reviewer.md:97-103`

- [ ] **Step 1: Add syntax trap anti-patterns to the checklist**

Find lines 97-103 (end of "Common Anti-patterns" section):

```markdown
### Common Anti-patterns

- Flag use of `assume` where `require` would be more appropriate.
- Flag unprotected actions (no `require` clause) that modify critical state.
- Flag relations with no invariants constraining them.
- Flag deeply nested quantifiers in invariants (may cause solver timeouts).
- Flag large isolates that combine many unrelated concerns.
```

Replace with:

```markdown
### Common Anti-patterns

- Flag use of `assume` where `require` would be more appropriate.
- Flag unprotected actions (no `require` clause) that modify critical state.
- Flag relations with no invariants constraining them.
- Flag deeply nested quantifiers in invariants (may cause solver timeouts).
- Flag large isolates that combine many unrelated concerns.
- Flag relation/function declarations using multi-character lowercase parameter names (e.g., `src`, `dst`, `conn`) — prefer single uppercase letters (S, D, C) to avoid symbol collision. See `ivy-error-patterns` entry #1.
- Flag mutable relations or functions without a corresponding `after init` block — uninitialized state causes invariant failures on the initial state. See `ivy-error-patterns` entry #12.
- Cross-reference the `ivy-error-patterns` skill for known syntax traps when reviewing declarations.
```

- [ ] **Step 2: Verify the file**

Read the file back to confirm edits.

- [ ] **Step 3: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
git add agents/ivy-model-reviewer.md
git commit -m "feat: add syntax trap anti-patterns to ivy-model-reviewer"
```

---

## Phase B: ivy-lsp Diagnostic Improvements (Python, TDD)

All paths in this phase are relative to `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`.

### Task 7: Add Parameter Name Style Check to `structural_lint.py`

**Files:**
- Modify: `ivy_lsp/utils/structural_lint.py`
- Test: `tests/test_structural_lint.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_structural_lint.py`:

```python
def test_param_name_collision_lowercase_multi_char():
    source = "#lang ivy1.7\nrelation update_processed(src:bgp_id, dst:bgp_id)\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "param-name-style" in codes


def test_param_name_single_letter_ok():
    source = "#lang ivy1.7\nrelation conn_seen(C:cid)\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "param-name-style" not in codes


def test_param_name_function_declaration():
    source = "#lang ivy1.7\nfunction getsock(addr:ip.addr) : net.socket\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "param-name-style" in codes


def test_param_name_in_comment_ignored():
    source = "#lang ivy1.7\n# relation foo(src:bar)\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "param-name-style" not in codes
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v -k "param_name"
```

Expected: FAIL (4 failures, `param-name-style` not in codes)

- [ ] **Step 3: Implement the check**

Add to `ivy_lsp/utils/structural_lint.py`, inside `check_structural_issues_raw()`, after the unmatched braces check (before `return diags`):

```python
    # 3. Parameter name style — flag multi-char lowercase param names
    _DECL_RE = re.compile(
        r"^(?:relation|function)\s+\w+\(([^)]+)\)", re.MULTILINE
    )
    for m in _DECL_RE.finditer(source):
        decl_line = source[: m.start()].count("\n")
        # Skip if line is a comment
        line_text = lines[decl_line].lstrip()
        if line_text.startswith("#"):
            continue
        params_str = m.group(1)
        for param in params_str.split(","):
            param = param.strip()
            if ":" not in param:
                continue
            name = param.split(":")[0].strip()
            # Flag multi-char lowercase names (not single uppercase letter)
            if len(name) > 1 and name[0].islower():
                diags.append({
                    "line": decl_line + 1,
                    "severity": "warning",
                    "message": (
                        f"Parameter name '{name}' is a multi-character lowercase "
                        f"identifier — may collide with Ivy symbols. "
                        f"Prefer single uppercase letters (e.g., S, D, C)."
                    ),
                    "source": "ivy-lint",
                    "code": "param-name-style",
                })
```

Also add `import re` at the top of the file if not already present.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/utils/structural_lint.py tests/test_structural_lint.py
git commit -m "feat: add param-name-style check to structural linter"
```

---

### Task 8: Add Missing `after init` Heuristic to `structural_lint.py`

**Files:**
- Modify: `ivy_lsp/utils/structural_lint.py`
- Test: `tests/test_structural_lint.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_structural_lint.py`:

```python
def test_missing_after_init_relation():
    source = "#lang ivy1.7\nrelation conn_seen(C:cid)\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "missing-init" in codes


def test_relation_with_after_init_ok():
    source = "#lang ivy1.7\nrelation conn_seen(C:cid)\nafter init {\n    conn_seen(C) := false;\n}\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "missing-init" not in codes


def test_missing_after_init_function():
    source = "#lang ivy1.7\nfunction last_pkt(C:cid) : nat\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "missing-init" in codes


def test_type_declaration_no_init_needed():
    source = "#lang ivy1.7\ntype packet_id\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "missing-init" not in codes
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v -k "missing_after_init or relation_with_after or type_declaration_no_init"
```

Expected: FAIL

- [ ] **Step 3: Implement the check**

Add to `ivy_lsp/utils/structural_lint.py`, inside `check_structural_issues_raw()`, before `return diags`:

```python
    # 4. Missing after init — heuristic for uninitialized mutable state
    _MUTABLE_RE = re.compile(
        r"^(?:relation|function)\s+(\w+)", re.MULTILINE
    )
    mutable_names = set()
    mutable_lines: dict[str, int] = {}
    for m in _MUTABLE_RE.finditer(source):
        line_text = lines[source[: m.start()].count("\n")].lstrip()
        if line_text.startswith("#"):
            continue
        name = m.group(1)
        mutable_names.add(name)
        mutable_lines[name] = source[: m.start()].count("\n") + 1

    # Find names that appear in after init blocks
    initialized = set()
    in_init = False
    init_depth = 0
    for i, line_text in enumerate(lines):
        stripped = line_text.strip()
        if "after init" in stripped:
            in_init = True
            init_depth = 0
        if in_init:
            for ch in stripped:
                if ch == "{":
                    init_depth += 1
                elif ch == "}":
                    init_depth -= 1
                    if init_depth <= 0:
                        in_init = False
            # Check for assignments: name(...) := or name :=
            assign_match = re.match(r"(\w+)(?:\(.*?\))?\s*:=", stripped)
            if assign_match:
                initialized.add(assign_match.group(1))

    for name in mutable_names - initialized:
        diags.append({
            "line": mutable_lines[name],
            "severity": "warning",
            "message": (
                f"'{name}' is never initialized in an 'after init' block "
                f"— it will start with arbitrary values."
            ),
            "source": "ivy-lint",
            "code": "missing-init",
        })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/utils/structural_lint.py tests/test_structural_lint.py
git commit -m "feat: add missing-init heuristic to structural linter"
```

---

### Task 9: Add Empty `after init`, Duplicate Declaration, and Unguarded Action Checks

**Files:**
- Modify: `ivy_lsp/utils/structural_lint.py`
- Test: `tests/test_structural_lint.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_structural_lint.py`:

```python
def test_empty_after_init_block():
    source = "#lang ivy1.7\nrelation foo(C:cid)\nafter init {\n}\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "empty-init" in codes


def test_nonempty_after_init_ok():
    source = "#lang ivy1.7\nrelation foo(C:cid)\nafter init {\n    foo(C) := false;\n}\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "empty-init" not in codes


def test_duplicate_declaration_same_file():
    source = "#lang ivy1.7\nrelation foo(C:cid)\nrelation foo(C:cid)\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "duplicate-decl" in codes


def test_no_duplicate_different_names():
    source = "#lang ivy1.7\nrelation foo(C:cid)\nrelation bar(C:cid)\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "duplicate-decl" not in codes


def test_unguarded_action():
    source = "#lang ivy1.7\naction send(S:cid) = {\n    sent(S) := true;\n}\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "unguarded-action" in codes


def test_guarded_action_ok():
    source = "#lang ivy1.7\naction send(S:cid) = {\n    require connected(S);\n    sent(S) := true;\n}\n"
    issues = check_structural_issues_raw(source, "/fake/test.ivy")
    codes = [i.get("code") for i in issues]
    assert "unguarded-action" not in codes
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v -k "empty_after_init or nonempty_after or duplicate_ or unguarded"
```

Expected: FAIL

- [ ] **Step 3: Implement the three checks**

Add to `ivy_lsp/utils/structural_lint.py`, inside `check_structural_issues_raw()`, before `return diags`:

```python
    # 5. Empty after init blocks
    _INIT_BLOCK_RE = re.compile(
        r"after\s+init\s*\{([^}]*)\}", re.MULTILINE | re.DOTALL
    )
    for m in _INIT_BLOCK_RE.finditer(source):
        body = m.group(1).strip()
        if not body:
            line_no = source[: m.start()].count("\n") + 1
            diags.append({
                "line": line_no,
                "severity": "warning",
                "message": "Empty 'after init' block — no state is initialized.",
                "source": "ivy-lint",
                "code": "empty-init",
            })

    # 6. Duplicate top-level declarations (same file)
    _TOP_DECL_RE = re.compile(
        r"^(relation|function|type|individual)\s+(\w+)", re.MULTILINE
    )
    seen_decls: dict[str, int] = {}
    for m in _TOP_DECL_RE.finditer(source):
        line_no = source[: m.start()].count("\n")
        line_text = lines[line_no].lstrip()
        if line_text.startswith("#"):
            continue
        name = m.group(2)
        if name in seen_decls:
            diags.append({
                "line": line_no + 1,
                "severity": "error",
                "message": (
                    f"Duplicate declaration of '{name}' "
                    f"(first declared at line {seen_decls[name]})."
                ),
                "source": "ivy-lint",
                "code": "duplicate-decl",
            })
        else:
            seen_decls[name] = line_no + 1

    # 7. Action without require (unguarded state modification)
    _ACTION_RE = re.compile(
        r"^(\s*)action\s+\w+[^=]*=\s*\{", re.MULTILINE
    )
    for m in _ACTION_RE.finditer(source):
        action_start = m.end()
        action_line = source[: m.start()].count("\n")
        line_text = lines[action_line].lstrip()
        if line_text.startswith("#"):
            continue
        # Find the matching closing brace
        depth = 1
        pos = action_start
        while pos < len(source) and depth > 0:
            if source[pos] == "{":
                depth += 1
            elif source[pos] == "}":
                depth -= 1
            pos += 1
        action_body = source[action_start:pos - 1] if pos > action_start else ""
        has_require = "require " in action_body or "require(" in action_body
        has_assignment = ":=" in action_body
        if has_assignment and not has_require:
            diags.append({
                "line": action_line + 1,
                "severity": "hint",
                "message": (
                    "Action modifies state but has no 'require' precondition "
                    "— consider adding guards."
                ),
                "source": "ivy-lint",
                "code": "unguarded-action",
            })
```

- [ ] **Step 4: Run all structural lint tests**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/utils/structural_lint.py tests/test_structural_lint.py
git commit -m "feat: add empty-init, duplicate-decl, unguarded-action lint checks"
```

---

### Task 10: Add Cross-File Duplicate Detection (Mirror-Aware) to `ivy_lint` MCP Tool

**Files:**
- Modify: `ivy_lsp/mcp_server.py:296-322` (ivy_lint tool)
- Modify: `ivy_lsp/utils/structural_lint.py` (new function)
- Test: `tests/test_structural_lint.py`

- [ ] **Step 1: Write the failing tests for the cross-file helper**

Add to `tests/test_structural_lint.py`:

```python
import os
import tempfile

from ivy_lsp.utils.structural_lint import check_cross_file_duplicates_raw


def test_cross_file_duplicate_top_level():
    """Two files with same top-level relation — flag as duplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = os.path.join(tmpdir, "a.ivy")
        f2 = os.path.join(tmpdir, "b.ivy")
        main = os.path.join(tmpdir, "main.ivy")
        with open(f1, "w") as fh:
            fh.write("#lang ivy1.7\nrelation foo(C:cid)\n")
        with open(f2, "w") as fh:
            fh.write("#lang ivy1.7\nrelation foo(C:cid)\n")
        with open(main, "w") as fh:
            fh.write("#lang ivy1.7\ninclude a\ninclude b\n")
        issues = check_cross_file_duplicates_raw(main, tmpdir)
        codes = [i.get("code") for i in issues]
        assert "duplicate-symbol" in codes


def test_cross_file_scoped_no_duplicate():
    """Same symbol inside different objects — not a duplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = os.path.join(tmpdir, "a.ivy")
        f2 = os.path.join(tmpdir, "b.ivy")
        main = os.path.join(tmpdir, "main.ivy")
        with open(f1, "w") as fh:
            fh.write("#lang ivy1.7\nobject client = {\n    relation ready(C:cid)\n}\n")
        with open(f2, "w") as fh:
            fh.write("#lang ivy1.7\nobject server = {\n    relation ready(C:cid)\n}\n")
        with open(main, "w") as fh:
            fh.write("#lang ivy1.7\ninclude a\ninclude b\n")
        issues = check_cross_file_duplicates_raw(main, tmpdir)
        codes = [i.get("code") for i in issues]
        assert "duplicate-symbol" not in codes


def test_cross_file_no_co_include_no_duplicate():
    """Same symbol in files that are never co-included — not a duplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = os.path.join(tmpdir, "a.ivy")
        f2 = os.path.join(tmpdir, "b.ivy")
        with open(f1, "w") as fh:
            fh.write("#lang ivy1.7\nrelation foo(C:cid)\n")
        with open(f2, "w") as fh:
            fh.write("#lang ivy1.7\nrelation foo(C:cid)\n")
        # No main file including both — check from a.ivy only
        issues = check_cross_file_duplicates_raw(f1, tmpdir)
        codes = [i.get("code") for i in issues]
        assert "duplicate-symbol" not in codes
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v -k "cross_file"
```

Expected: FAIL (ImportError — function doesn't exist yet)

- [ ] **Step 3: Implement `check_cross_file_duplicates_raw`**

Add to `ivy_lsp/utils/structural_lint.py`:

```python
def check_cross_file_duplicates_raw(
    filepath: str,
    workspace_root: str,
) -> List[Dict[str, Any]]:
    """Cross-file duplicate detection with mirror-type awareness.

    Resolves the include tree for ``filepath``, then checks for duplicate
    top-level symbol declarations across co-included files. Symbols inside
    different ``object`` or ``module`` blocks are NOT flagged (mirror pattern).
    """
    diags: List[Dict[str, Any]] = []

    # Build include tree (direct includes only, one level)
    includes = _resolve_includes(filepath, workspace_root)
    if not includes:
        return diags

    # Collect scoped symbols from each included file
    # symbol_map: {(scope, name) -> [(file, line), ...]}
    symbol_map: Dict[tuple, List[tuple]] = {}
    all_files = [filepath] + includes
    for fpath in all_files:
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                src = f.read()
        except OSError:
            continue
        for scope, name, line_no in _extract_scoped_symbols(src):
            key = (scope, name)
            symbol_map.setdefault(key, []).append((fpath, line_no))

    # Flag duplicates: same (scope, name) in different files
    for (scope, name), locations in symbol_map.items():
        files_involved = {loc[0] for loc in locations}
        if len(files_involved) > 1:
            severity = "error" if scope == "" else "warning"
            for fpath, line_no in locations:
                others = [
                    os.path.basename(f)
                    for f, _ in locations
                    if f != fpath
                ]
                diags.append({
                    "line": line_no,
                    "severity": severity,
                    "message": (
                        f"Symbol '{name}' also declared in "
                        f"{', '.join(others)}"
                        + (f" (scope: {scope})" if scope else " (top-level)")
                    ),
                    "source": "ivy-lint",
                    "code": "duplicate-symbol",
                    "file": fpath,
                })

    return diags


def _resolve_includes(filepath: str, workspace_root: str) -> List[str]:
    """Resolve direct includes for a file (non-recursive)."""
    if not os.path.isfile(filepath):
        return []
    parent = os.path.dirname(filepath)
    includes = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            src = f.read()
    except OSError:
        return []
    for match in re.finditer(r"^include\s+(\w+)", src, re.MULTILINE):
        name = match.group(1)
        # Check parent dir first, then workspace root
        for base in [parent, workspace_root]:
            candidate = os.path.join(base, name + ".ivy")
            if os.path.isfile(candidate):
                includes.append(candidate)
                break
    return includes


def _extract_scoped_symbols(source: str) -> List[tuple]:
    """Extract (scope, name, line_no) for declarations.

    scope is "" for top-level, or "object_name" / "module_name" for scoped.
    """
    symbols = []
    lines = source.split("\n")
    current_scope = ""
    scope_stack: List[tuple] = []  # (scope_name, brace_depth)
    brace_depth = 0

    _SCOPE_RE = re.compile(r"^\s*(object|module)\s+(\w+)")
    _DECL_RE = re.compile(r"^\s*(relation|function|type|individual)\s+(\w+)")

    for i, line_text in enumerate(lines):
        stripped = line_text.strip()
        if stripped.startswith("#"):
            continue

        # Track scope entry
        scope_match = _SCOPE_RE.match(line_text)
        if scope_match and "{" in line_text:
            scope_name = scope_match.group(2)
            scope_stack.append((current_scope, brace_depth))
            current_scope = scope_name
            brace_depth = 0

        # Track braces
        code = line_text.split("#")[0]  # remove comments
        for ch in code:
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth <= 0 and scope_stack:
                    current_scope, brace_depth = scope_stack.pop()

        # Extract declarations
        decl_match = _DECL_RE.match(line_text)
        if decl_match:
            name = decl_match.group(2)
            symbols.append((current_scope, name, i + 1))

    return symbols
```

- [ ] **Step 4: Run cross-file tests**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v -k "cross_file"
```

Expected: ALL PASS

- [ ] **Step 5: Wire cross-file mode into `ivy_lint` MCP tool**

In `ivy_lsp/mcp_server.py`, modify the `ivy_lint` tool to accept an optional `cross_file` parameter. Find line 296:

```python
    @mcp.tool()
    async def ivy_lint(relative_path: str) -> str:
        """Fast structural lint of an Ivy file (milliseconds, no subprocess).

        Checks: missing #lang header, unmatched braces, unresolved includes.

        Args:
            relative_path: Relative path to the .ivy file to lint.
        """
```

Replace with:

```python
    @mcp.tool()
    async def ivy_lint(relative_path: str, cross_file: bool = False) -> str:
        """Fast structural lint of an Ivy file (milliseconds, no subprocess).

        Checks: missing #lang header, unmatched braces, unresolved includes,
        parameter name style, missing after init, empty init blocks,
        duplicate declarations, unguarded actions.

        With cross_file=True, also checks for duplicate symbols across
        co-included files (mirror-type aware).

        Args:
            relative_path: Relative path to the .ivy file to lint.
            cross_file: Enable cross-file duplicate detection (default False).
        """
```

Then after line 314 (`diagnostics = _check_structural_issues(source, abs_path)`), add:

```python
        if cross_file:
            from ivy_lsp.utils.structural_lint import check_cross_file_duplicates_raw
            diagnostics.extend(check_cross_file_duplicates_raw(abs_path, root))
```

- [ ] **Step 6: Run all tests**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/test_structural_lint.py -v
```

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/utils/structural_lint.py ivy_lsp/mcp_server.py tests/test_structural_lint.py
git commit -m "feat: add mirror-aware cross-file duplicate detection to ivy_lint"
```

---

### Task 11: Add Parameter Collision and Missing Init Diagnostics to LSP

**Files:**
- Modify: `ivy_lsp/features/diagnostics.py:79-120` (check_structural_issues function)

- [ ] **Step 1: Verify that structural lint changes propagate to LSP diagnostics**

The `check_structural_issues()` function in `diagnostics.py` already calls `check_structural_issues_raw()` and converts results to LSP Diagnostic objects. Since we added our new checks to `check_structural_issues_raw()` in Tasks 7-9, they should automatically propagate to LSP diagnostics.

Read `diagnostics.py:79-120` to confirm the wiring:

```python
def check_structural_issues(source, filepath, indexer=None):
    from ivy_lsp.utils.structural_lint import (
        check_structural_issues_raw,
        check_unresolved_includes_raw,
    )
    raw = check_structural_issues_raw(source, filepath)
    raw.extend(check_unresolved_includes_raw(source, filepath, resolve_callback=...))
    # Converts raw dicts to lsp.Diagnostic objects
    ...
```

The new checks (param-name-style, missing-init, empty-init, duplicate-decl, unguarded-action) are all added inside `check_structural_issues_raw()`, so they will automatically appear as LSP diagnostics with no additional wiring needed.

- [ ] **Step 2: Map severity for the new hint-level check**

The current converter only handles `"error"` and `"warning"` severity (line 103-106). We need to add `"hint"` for the `unguarded-action` check. Find line 103:

```python
        severity = (
            lsp.DiagnosticSeverity.Error
            if entry["severity"] == "error"
            else lsp.DiagnosticSeverity.Warning
        )
```

Replace with:

```python
        _SEVERITY_MAP = {
            "error": lsp.DiagnosticSeverity.Error,
            "warning": lsp.DiagnosticSeverity.Warning,
            "hint": lsp.DiagnosticSeverity.Hint,
            "information": lsp.DiagnosticSeverity.Information,
        }
        severity = _SEVERITY_MAP.get(
            entry["severity"], lsp.DiagnosticSeverity.Warning
        )
```

- [ ] **Step 3: Run the full LSP diagnostics test suite**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/ -v -k "diagnostic or structural" --timeout=30
```

Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/features/diagnostics.py
git commit -m "feat: map hint/info severity levels for new structural lint checks in LSP"
```

---

### Task 12: Run Full Test Suite and Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full ivy-lsp test suite**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/ -v --timeout=60
```

Expected: ALL PASS (or only pre-existing failures unrelated to our changes)

- [ ] **Step 2: Verify new skills are loadable**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
cat skills/ivy-debugging-methodology/SKILL.md | head -5
cat skills/ivy-error-patterns/SKILL.md | head -5
```

Expected: Valid YAML frontmatter with `---` delimiters, `name:` and `description:` fields.

- [ ] **Step 3: Verify modified skills and agents are valid**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
head -5 skills/ivy-model-editing/SKILL.md
head -5 skills/ivy-verification/SKILL.md
head -5 agents/spec-verifier.md
head -5 agents/ivy-model-reviewer.md
```

Expected: All files have valid frontmatter.

- [ ] **Step 4: Count new lint checks**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
grep -c '"code":' ivy_lsp/utils/structural_lint.py
```

Expected: At least 8 (3 original + 5 new: param-name-style, missing-init, empty-init, duplicate-decl, unguarded-action) plus duplicate-symbol in cross-file function.
