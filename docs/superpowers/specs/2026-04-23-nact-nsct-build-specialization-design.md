# Design — panther-ivy-plugin NACT/NSCT Build-Workflow Specialization

Status: proposed
Author: workflow-audit follow-up (cluster-9 grilling session)
Date: 2026-04-23
Depends-on: `2026-04-23-workflow-state-model-refactor-design.md` (cluster 1) — the NSCT sidecar emission extends Phase 6 Wrap-up, which cluster 1 also touches; specs must be applied in order (cluster 1 first, cluster 9 second).
Scope: close audit cluster 9 (NACT/NSCT missing workflow specialization) — the two Major findings that NACT and NSCT methodologies lack workflow-level support despite being first-class in `.claude/rules/nct-methodology.md`.

## Context

The workflow audit on 2026-04-23 identified that `build/SKILL.md:99-101` detects NCT/NACT/NSCT as methodology keywords but `build/SKILL.md` Phase 2 Blueprint proposes the generic 14-layer template regardless of methodology. Two Major findings:

- NACT lacks the 6 APT lifecycle files (reconnaissance → exfiltration) + attack entities + white_noise per `.claude/rules/nct-methodology.md:39-53`.
- NSCT lacks the Shadow-NS experiment-config YAML sidecar per `.claude/rules/nct-methodology.md:55-60`. The NSCT methodology does not require new `.ivy` files — only a different experiment runtime.

Grilling established that these are different concerns: NACT is a build-time concern (what files to author), NSCT is an experiment-runtime concern (what YAML to emit). Both land in `build`, but in different phases (NACT in Phase 2/3; NSCT in Phase 6 Wrap-up).

## Decisions

1. **Single `build` workflow, methodology-conditional Phase 2 Blueprint branches.**
2. **NACT branch**: Phase 2 Step 3 presents a multi-select checklist via AskUserQuestion. Options: full APT lifecycle (6 files), white_noise, attack entities package. Base NCT minimum (7 layers) is always included. User-selected subset is recorded in `build-state.yaml.layers`.
3. **NACT layer names reuse `.claude/rules/nct-methodology.md:39-53`** — the canonical reference. No new layer-catalog file.
4. **NSCT branch**: Phase 2 Blueprint is NCT-identical (no `.ivy` difference). Phase 6 Wrap-up gains a sidecar emission: scaffold `experiment-config/protocols/{protocol}/experiment_config_{protocol}_shadow.yaml` from a template.
5. **NSCT template lives in `skills/methodology-reference/references/nsct-experiment-template.md`** — new file. Placeholder-marked (`{{protocol}}`, `{{version}}`, `{{test_file_list}}`).
6. **Directory creation**: the `experiment-config/protocols/{protocol}/` path may not exist for a new protocol; the Phase 6 sidecar step uses `mkdir -p` before Write.

## Architecture

### Build Phase 2 Step 3 (methodology-conditional)

```
Current Step 3: propose layer structure from 14-layer template.

New Step 3 (methodology branch):

  if methodology == "nct":
      present the 14-layer / 7-minimum-viable template as before.
  elif methodology == "nact":
      Load .claude/rules/nct-methodology.md (NACT table at lines 39-53).
      AskUserQuestion(multiSelect=true) with options:
        - "Full APT lifecycle (6 stages)"
        - "Cross-cutting white_noise"
        - "Attack entities package"
      Always-included prefix: 7-layer base NCT minimum.
      Record chosen subset in build-state.yaml.layers.
  elif methodology == "nsct":
      Use NCT layer proposal verbatim (no .ivy difference).
      Note to user: "NSCT adds a Shadow-NS experiment-config YAML at Phase 6 Wrap-up."
```

### Build Phase 6 Step 1 (NSCT sidecar emission)

```
Current Step 1: present summary (layers, verification status, coverage, decisions).

Added (conditional):

  if methodology == "nsct":
      Read skills/methodology-reference/references/nsct-experiment-template.md.
      Substitute placeholders:
        {{protocol}}     -> build-state.yaml.protocol
        {{version}}      -> build-state.yaml.decisions['version'] or "<fill-in>"
        {{test_file_list}} -> build-state.yaml.layers filtered to test specs
      Ensure experiment-config/protocols/{protocol}/ exists (mkdir -p).
      Write experiment-config/protocols/{protocol}/experiment_config_{protocol}_shadow.yaml.
      Append progress journal event: {detail: "NSCT experiment-config scaffolded at <path>"}.
```

## File change inventory (4 files)

| File | Change |
|---|---|
| `skills/build/SKILL.md` | Phase 2 Step 3 gains the three-branch conditional (see Architecture). Phase 6 Step 1 gains the NSCT sidecar emission (see Architecture). Integration block at end of file adds `methodology-reference/references/nsct-experiment-template.md` to the "Knowledge skills loaded" list. |
| `skills/methodology-reference/references/nsct-experiment-template.md` | NEW. Shadow-NS experiment-config template (see Proposed template below). Placeholder-marked. |
| `skills/methodology-reference/SKILL.md` | Integration block: one-line addition mentioning `references/nsct-experiment-template.md` so future readers discover it. |
| `.claude/rules/nct-methodology.md` | No change. NACT layer table at lines 39-53 is already the authoritative source; build Phase 2 reads it directly. Verify no cross-reference updates after the build-SKILL rewrite. |

## Proposed template (`skills/methodology-reference/references/nsct-experiment-template.md`)

Concrete content (not TBD):

```yaml
# NSCT Shadow-NS simulation experiment (scaffold emitted by build Phase 6)
#
# Edit topology, services, and IUT plugin names to your scenario.
# This file is a template intended to be customized; it is not ready-to-run.
#
# Source of truth for canonical experiment-config fields:
# experiment-config/base/experiment_config_example_minimal.yaml

logging:
  level: INFO

tests:
  - name: "{{protocol}} NSCT simulation scaffold"
    network_environment:
      type: shadow_ns
      seed: 42  # deterministic execution; change per scenario
      topology:
        nodes: 2
        links:
          - endpoints: [client, server]
            latency_ms: 0
            loss_percent: 0
            bandwidth_mbps: unlimited
    services:
      client:
        implementation:
          name: <fill-in-iut-plugin-name>
          type: iut
        protocol:
          name: {{protocol}}
          version: {{version}}
          role: client
      server:
        implementation:
          name: <fill-in-iut-plugin-name>
          type: iut
        protocol:
          name: {{protocol}}
          version: {{version}}
          role: server
```

## Migration plan

Single commit. Docs-and-template only (no code changes, no hook changes). Tests:

- Integration: invoke `build` with methodology=nact on a fresh protocol; confirm Phase 2 presents the multi-select checklist; confirm selection is recorded in `build-state.yaml`.
- Integration: invoke `build` with methodology=nsct; confirm Phase 2 uses NCT blueprint; confirm Phase 6 emits the YAML file at the expected path with proper placeholder substitution.
- Run pytest; no test impact expected (changes are in SKILL.md and a new reference file).

## Risks

1. **Partial NACT selection**. A user picking only 2 of 6 APT stages produces an incomplete NACT model. Mitigation: checklist description notes "A full NACT build per the methodology reference requires all 6 stages. Subsets are supported for staged builds."
2. **NSCT template staleness**. The template may drift from `experiment-config/base/experiment_config_example_minimal.yaml` as the PANTHER config schema evolves. Mitigation: the template file includes a pointer comment to the canonical example.
3. **Directory creation race**. Under heavy parallelism (unlikely here — build is user-interactive), `mkdir -p` is race-safe. Under a read-only filesystem the write fails cleanly.
4. **Placeholder mismatch**. `{{version}}` may not be known when the user has not chosen a version. Mitigation: fall back to literal `<fill-in>` in that case; the template is explicitly scaffold-grade, not runnable.
5. **Interaction with cluster 1**. Phase 6 Wrap-up is one of the places cluster 1 rewrites (simplifying On Completion). Cluster 1's rewrite must land first; cluster 9's Phase 6 sidecar extension builds on that rewrite. Listed in spec frontmatter as a dependency.

## Out of scope

- Authoring the NACT Ivy models for each protocol (QUIC/BGP/etc.) — per-protocol work outside workflow plumbing.
- Changes to `/nct-iut-test` or the PANTHER experiment-runtime for Shadow-NS — pre-existing capability.
- An interactive topology/network-conditions editor — users hand-edit the scaffolded YAML.
- Running NSCT experiments from within the `build` workflow — deliberate separation (build emits; experiment-runtime runs via `/nct-iut-test`).

## Verification

- Spot-check: read `skills/build/SKILL.md` Phase 2 Step 3 after the change. Three methodology branches must be present with the described behavior.
- Spot-check: read `skills/build/SKILL.md` Phase 6 Step 1 after the change. Conditional sidecar emission must be present.
- Spot-check: read `skills/methodology-reference/references/nsct-experiment-template.md`. Template must be valid YAML (check with `python -c "import yaml; yaml.safe_load(open(...))"`) after placeholder substitution.
- Manual: fresh `build` session with methodology=nact. Phase 2 presents the multi-select UI; `build-state.yaml` records the subset.
- Manual: fresh `build` session with methodology=nsct on a protocol that doesn't yet have `experiment-config/protocols/{protocol}/`. Phase 6 creates the directory + emits the YAML.
