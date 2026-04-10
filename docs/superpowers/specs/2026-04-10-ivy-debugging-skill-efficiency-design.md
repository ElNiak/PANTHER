# Ivy Debugging Skill Efficiency Improvement

**Date:** 2026-04-10
**Status:** Design approved, pending implementation
**Scope:** panther-ivy-plugin skills and agents

## Problem

When Claude encounters Ivy verification or compilation errors, it jumps directly to proposing fixes without:
- Consulting the `ivy-model-editing` skill for syntax rules
- Running the linter (`ivy_lint`) for fast structural checks
- Searching existing protocol models in `protocol-testing/` for working examples
- Using LSP diagnostics for additional context

This leads to incorrect fixes, wasted verification cycles, and frustration. Example: the error `'src' not found` on `relation update_processed(src:bgp_id, dst:bgp_id)` is cryptic, but searching existing models would immediately reveal the correct declaration pattern.

## Approach: Layered Architecture

Three layers, matching the existing plugin pattern of skills for knowledge and agents for orchestration:

1. **`ivy-debugging-methodology` skill** — Mandatory pre-fix workflow (process)
2. **`ivy-error-patterns` skill** — Error-to-fix lookup table with working examples (knowledge)
3. **Updates to existing skills and agents** — Enforce the methodology and cross-reference patterns

## Artifact 1: `ivy-debugging-methodology` Skill

**Path:** `skills/ivy-debugging-methodology/SKILL.md`
**Size:** ~120 lines

### Purpose

Enforces a structured debugging process that must be followed before proposing any fix to an Ivy spec. Gates fix attempts behind mandatory research steps.

### Mandatory Pre-Fix Checklist

All steps are mandatory and must be completed in order:

1. **Parse the error** — Extract error type, line number, and the specific symbol/construct that failed. Map cryptic messages to known patterns using the `ivy-error-patterns` skill.

2. **Consult skills** — Load `ivy-model-editing` to check syntax rules for the failing construct. Load `ivy-error-patterns` to look up the specific error pattern.

3. **Run linter first** — Call `ivy_lint` via MCP for fast structural checks (milliseconds) before running full verification. Many errors (missing includes, unmatched braces, syntax issues) are caught immediately.

4. **Search existing models for working examples** — Use `Grep` to find similar constructs in `protocol-testing/`. For example, if debugging a `relation` declaration, grep for `^relation ` across `.ivy` files. Prioritize models for the same protocol family.

5. **Use LSP diagnostics** — Check if the native Ivy LSP provides additional diagnostic information (hover, go-to-definition) for the failing symbol.

6. **Formulate theory** — State a specific hypothesis about the root cause before editing anything. The theory must reference evidence from steps 1-5.

7. **Apply minimal fix** — Only now propose a change, making it minimal.

8. **Verify** — Run `ivy_verify` or `ivy_lint` to confirm the fix works.

### Hard Rule

Steps 1-6 are mandatory. Skipping to step 7 is explicitly forbidden. If Claude cannot find a working example or skill reference that explains the error, it must say so rather than guessing.

## Artifact 2: `ivy-error-patterns` Skill

**Path:** `skills/ivy-error-patterns/SKILL.md`
**Size:** ~250 lines

### Purpose

Lookup table mapping cryptic Ivy error messages to root causes, correct patterns, and pointers to working examples in existing protocol models.

### Entry Format

Each entry follows:
```
### Error Pattern: "<error message substring>"
- **Trigger:** What the user wrote that caused it
- **Root Cause:** Why Ivy rejects it
- **Correct Pattern:** The right syntax with explanation
- **Working Example:** File path in protocol-testing/ where this is done correctly
- **Related Skill Section:** Pointer to ivy-model-editing section
```

### Initial Error Catalog

#### 1. `'<name>' not found` on relation/function declaration

- **Trigger:** `relation update_processed(src:bgp_id, dst:bgp_id)` — using a parameter name that collides with an existing symbol or is parsed as an unresolved reference
- **Root Cause:** In Ivy, the token before `:` in a parameter list is resolved as a symbol in the current scope. If `src` exists as a declared object, type, or individual, it binds to that instead of being treated as a fresh parameter name. If `src` does not exist at all, Ivy reports `'src' not found` because it tried to resolve it as a reference. The convention in existing models is to use single uppercase letters (C, S, P, N) that are unambiguous fresh binders.
- **Correct Pattern:** Use short conventional parameter names that don't collide with existing symbols:
  ```ivy
  relation update_processed(S:bgp_id, D:bgp_id)
  ```
- **Working Examples:**
  - `protocol-testing/quic/quic_stack/quic_packet.ivy:229` — `relation conn_seen(C:cid)`
  - `protocol-testing/bgp/bgp_shims/bgp_shim.ivy:41` — `relation isup(A:ip.addr)`
- **Related Skill Section:** `ivy-model-editing` > Relations

#### 2. `ungrounded variable X in relation`

- **Trigger:** Free variable in a relation expression not bound by quantifier or head
- **Root Cause:** All variables in relation expressions must be bound
- **Correct Pattern:** Bind with explicit quantifiers or ensure variables appear in the head
- **Working Examples:**
  - `protocol-testing/bgp/bgp_utils/bgp_network.ivy:56` — `require exists S. req(other,S,self);`
- **Related Skill Section:** `ivy-model-editing` > Invariants

#### 3. `invariant ... failed` / `failed to verify invariant preservation`

- **Trigger:** An action modifies state in a way that violates a declared invariant
- **Root Cause:** Missing state update, missing precondition, or invariant too strong
- **Correct Pattern:** Check all modified relations are updated consistently; add `require` guards
- **Working Examples:**
  - `protocol-testing/quic/quic_stack/quic_packet.ivy:300` — `after init` block initializing all relations
  - `protocol-testing/bgp/bgp_utils/bgp_network.ivy:56-70` — `require` guards on actions
- **Related Skill Section:** `ivy-model-editing` > Invariants, Actions

#### 4. `assumption failed` (isolate assumption violation)

- **Trigger:** An isolate's assumptions about another isolate's behavior are not satisfied
- **Root Cause:** The specification of the assumed isolate doesn't guarantee what the assuming isolate expects
- **Correct Pattern:** Use `ivy_model_info` to list isolates, check each isolate's assumptions against its specification
- **Working Examples:** Search for `object` and `specification` blocks in the protocol family
- **Related Skill Section:** `ivy-model-editing` > Isolates

#### 5. `type mismatch` / `type error`

- **Trigger:** Incompatible types in expression (e.g., using `nat` where `packet_type` expected)
- **Root Cause:** Ivy's type system is strict; no implicit coercions
- **Correct Pattern:** Ensure all variables and expressions have consistent types; check type declarations
- **Working Examples:**
  - `protocol-testing/quic/quic_stack/quic_transport_parameters.ivy:226` — function with explicit return type
- **Related Skill Section:** `ivy-model-editing` > Type Declarations

#### 6. `circular dependency`

- **Trigger:** Two or more modules or objects depend on each other via includes
- **Root Cause:** Ivy does not support circular include dependencies
- **Correct Pattern:** Structure files as a DAG; introduce abstract interfaces to break cycles
- **Working Examples:**
  - `protocol-testing/quic/quic_stack/quic_transport_parameters.ivy:3-5` — linear include chain
  - `protocol-testing/bgp/bgp_utils/random_value.ivy:3` — single include
- **Related Skill Section:** `ivy-model-editing` > Include Directives

#### 7. `not well-founded`

- **Trigger:** A recursive definition does not terminate
- **Root Cause:** Ivy requires well-founded recursion for soundness
- **Correct Pattern:** Add a termination measure or restructure to avoid recursion
- **Related Skill Section:** `ivy-model-editing` > Definitions

#### 8. `uninterpreted sort has no instances`

- **Trigger:** A type was declared but never given concrete values
- **Root Cause:** The type is abstract with no constructors or axioms
- **Correct Pattern:** Add at least one constructor or axiom providing instances
- **Related Skill Section:** `ivy-model-editing` > Type Declarations

#### 9. Z3 timeout / `unknown`

- **Trigger:** Verification takes too long; solver cannot decide
- **Root Cause:** Proof obligation too complex (deep quantifier nesting, large isolates)
- **Correct Pattern:** Break into smaller lemmas, add ghost state, use isolate boundaries
- **Related Skill Section:** `ivy-verification` > Z3 timeout section

#### 10. `multiple definitions`

- **Trigger:** Same symbol declared in multiple included files
- **Root Cause:** Include graph brings in conflicting declarations
- **Correct Pattern:** Use `ivy_include_graph` to trace the duplicate, remove or namespace one
- **Related Skill Section:** `ivy-model-editing` > Module System

#### 11. `cannot find isolate X`

- **Trigger:** Misspelled isolate name or missing declaration
- **Root Cause:** The isolate name in the command doesn't match any declaration in the file
- **Correct Pattern:** Check spelling; use `ivy_model_info` to list declared isolates
- **Related Skill Section:** `ivy-model-editing` > Isolates

#### 12. Missing `after init` causing arbitrary initial values

- **Trigger:** Invariant fails on initial state; relations have unexpected values
- **Root Cause:** Without `after init`, relations start with arbitrary (unconstrained) values
- **Correct Pattern:** Explicitly initialize all mutable relations in `after init` blocks
- **Working Examples:**
  - `protocol-testing/quic/quic_stack/quic_packet.ivy:300` — `after init { conn_seen(C) := false; ... }`
  - `protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy:10` — `after init {`
- **Related Skill Section:** `ivy-model-editing` > Common Pitfalls > Forgetting `after init` blocks

### Growth Strategy

New error patterns are added as they're encountered. The skill includes a "Protocol-Specific Patterns" section for protocol-family-specific gotchas (e.g., BGP initialization patterns vs. QUIC connection ID handling).

## Artifact 3: Updates to Existing Skills

### 3a. `ivy-model-editing` — Add "Common Syntax Traps" Section

**~40 lines added** after the "Common Pitfalls and Best Practices" section.

New section pairs wrong vs. right patterns side by side:

```ivy
# WRONG — 'src' not found (parameter name resolved as symbol)
relation update_processed(src:bgp_id, dst:bgp_id)

# RIGHT — short conventional parameter names
relation update_processed(S:bgp_id, D:bgp_id)
```

Covers the top 5-6 traps that produce misleading error messages. Each links to the corresponding `ivy-error-patterns` entry.

Also adds a **"Before You Write"** callout at the top of the Relations, Functions, and Actions sections:

> Before writing a new declaration, grep `protocol-testing/` for similar constructs to see the canonical pattern for your protocol family.

### 3b. `ivy-verification` — Replace Debugging Workflow

**~20 lines changed.**

Replace the current "Debugging Workflow" section with:

> When verification fails, follow the `ivy-debugging-methodology` skill. Do NOT attempt fixes without completing the pre-fix checklist.

Keep the "Common Ivy Verification Errors" section but add cross-references to `ivy-error-patterns` for the full lookup table.

## Artifact 4: Updates to Existing Agents

### 4a. `spec-verifier` Agent

**~15 lines changed.**

Add mandatory skill loading before diagnosis:

> Before diagnosing any failure, you MUST:
> 1. Load and follow the `ivy-debugging-methodology` skill
> 2. Consult `ivy-error-patterns` for the specific error message
> 3. Search `protocol-testing/` for working examples of the failing construct

### 4b. `ivy-model-reviewer` Agent

**~10 lines added.**

Add to the "Common Anti-patterns" checklist:
- Flag relation/function declarations using parameter names that could collide with existing symbols (prefer single-letter conventional names)
- Flag missing `after init` blocks for mutable relations
- Cross-reference `ivy-error-patterns` for known syntax traps

## File Inventory

### New Files

| File | Type | Est. Size |
|---|---|---|
| `skills/ivy-debugging-methodology/SKILL.md` | Skill | ~120 lines |
| `skills/ivy-error-patterns/SKILL.md` | Skill | ~250 lines |

### Modified Files

| File | Change Scope |
|---|---|
| `skills/ivy-model-editing/SKILL.md` | +40 lines (syntax traps + callouts) |
| `skills/ivy-verification/SKILL.md` | ~20 lines changed (workflow replacement) |
| `agents/spec-verifier.md` | ~15 lines changed (mandatory skill loading) |
| `agents/ivy-model-reviewer.md` | ~10 lines added (anti-pattern entries) |

All paths relative to `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/`.

### Out of Scope

- No changes to MCP tools, hooks, commands, or LSP config
- No changes to protocol models
- No new agents or commands
- `ivy-tools-reference` and `ivy-tooling-guide` skills unchanged
