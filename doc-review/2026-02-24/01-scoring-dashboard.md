# Documentation Review Scoring Dashboard

**Date:** 2026-02-24
**Branch:** `validate/ivy-pr9-vmt-rf`
**Agents Dispatched:** 25 across 4 phases
**Files Analyzed:** ~180 markdown + ~200 Python files

---

## Overall Project Score

| Dimension | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| Accuracy | 30% | 2.8 / 10 | 0.84 |
| Completeness | 30% | 3.5 / 10 | 1.05 |
| Consistency | 20% | 4.2 / 10 | 0.84 |
| Maintainability | 20% | 4.8 / 10 | 0.96 |
| **Overall** | **100%** | **3.69 / 10** | **Grade: D** |

---

## Module Scoring Table

Scoring: `score = 10 - (critical * 2.0) - (major * 1.0) - (minor * 0.3)`, clamped [0, 10].

| Module | Crit | Maj | Min | ACC | CMP | CON | MNT | Overall | Grade |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| core/state | 0 | 1 | 1 | 9.0 | 8.0 | 9.0 | 8.7 | **8.6** | A- |
| core/outputs | 2 | 2 | 2 | 7.0 | 7.5 | 7.0 | 8.0 | **7.4** | B+ |
| core/command_processor | 1 | 3 | 3 | 7.5 | 6.5 | 7.0 | 6.0 | **6.8** | B |
| core/storage | 0 | 2 | 1 | 8.0 | 6.0 | 7.0 | 6.0 | **6.8** | B |
| core/events | 3 | 5 | 3 | 4.0 | 5.5 | 7.0 | 7.0 | **5.6** | C |
| core/observer | 2 | 6 | 2 | 4.0 | 4.5 | 7.0 | 6.5 | **5.2** | C |
| core/reporting | 2 | 2 | 2 | 5.0 | 6.0 | 6.0 | 5.0 | **5.5** | C |
| core/exceptions | 4 | 5 | 3 | 4.0 | 6.0 | 5.0 | 6.0 | **5.2** | C |
| root-level docs | 5 | 8 | 4 | 3.0 | 5.0 | 5.5 | 5.0 | **4.5** | C |
| core/experiment_manager | 5 | 8 | 5 | 2.0 | 5.5 | 6.0 | 5.0 | **4.4** | C |
| cli_click | 8 | 8 | 4 | 3.0 | 5.0 | 5.0 | 3.0 | **4.0** | C |
| core/template | 2 | 2 | 3 | 4.0 | 5.0 | 4.0 | 5.0 | **4.5** | C |
| core/docker_builder | 5 | 6 | 2 | 2.5 | 3.0 | 5.0 | 4.0 | **3.4** | D |
| plugins/protocols | 3 | 4 | 2 | 3.0 | 3.5 | 4.0 | 4.0 | **3.6** | D |
| core/test_cases | 8 | 9 | 3 | 2.0 | 4.0 | 4.0 | 3.0 | **3.2** | D |
| config | 8 | 15 | 5 | 1.5 | 3.0 | 4.0 | 3.5 | **2.8** | D |
| tools | 8 | 11 | 4 | 1.5 | 3.0 | 3.0 | 2.5 | **2.4** | D |
| plugins/core | 6 | 7 | 5 | 2.0 | 2.0 | 4.0 | 3.5 | **2.7** | D |
| plugins/environments | 10 | 12 | 5 | 1.5 | 2.0 | 3.0 | 3.0 | **2.2** | D |
| plugins/services | 15 | 14 | 6 | 1.0 | 2.0 | 3.0 | 3.0 | **2.1** | D |
| core/results | 8 | 3 | 2 | 0.5 | 2.0 | 3.0 | 2.0 | **1.7** | F |
| tests (docs) | 5 | 6 | 3 | 1.0 | 2.0 | 2.0 | 1.5 | **1.6** | F |

---

## Grade Distribution

| Grade | Count | Modules |
|-------|:---:|---------|
| A / A- | 1 | state |
| B+ / B | 3 | outputs, command_processor, storage |
| C | 8 | events, observer, reporting, exceptions, root-level, experiment_manager, cli_click, template |
| D | 8 | docker_builder, protocols, test_cases, config, tools, plugins/core, plugins/environments, plugins/services |
| F | 2 | results, tests (docs) |

---

## Dimension Averages Across All Modules

| Dimension | Average | Best Module | Worst Module |
|-----------|---------|-------------|-------------|
| Accuracy | 3.4 | state (9.0) | results (0.5) |
| Completeness | 4.2 | state (8.0) | plugins/services (2.0) |
| Consistency | 5.0 | state (9.0) | tests docs (2.0) |
| Maintainability | 4.5 | outputs (8.0) | tests docs (1.5) |

---

## Issue Count Aggregate

| Severity | Count | Top Contributing Modules |
|----------|:---:|--------------------------|
| CRITICAL | ~107 | plugins/services (15), plugins/environments (10), config (8), tools (8), test_cases (8), results (8) |
| MAJOR | ~130 | config (15), plugins/services (14), plugins/environments (12), tools (11), test_cases (9) |
| MINOR | ~62 | plugins/services (6), config (5), plugins/core (5), plugins/environments (5), experiment_manager (5) |
| **TOTAL** | **~299** | |

---

## Cross-Cutting Issue Patterns

### Pattern 1: Fabricated Documentation (39 instances)
- All 8 standard QUIC IUT config tables entirely fabricated (2G, 3D)
- results/ module docstrings describe phantom capabilities (2B)
- gperf_cpu/gperf_heap READMEs document wrong tool entirely (2H, 3D, 4D)
- tests/README.md fabricated coverage and "zero technical debt" (1F, 4C)

### Pattern 2: Broken Links (57 instances)
- 29 absolute-style paths used as relative (4B)
- 17 targets never created (4B)
- 10 references to absent dev/docs-gen/ directory (4B)
- 5 wrong ADR subdirectory prefixes (4B)
- Worst file: panther/core/README.md (11/13 broken, 85%)

### Pattern 3: API Reference Rot (~45 instances)
- Events: emit/publish/notify method name confusion (1E)
- Observer: wrong class names, fabricated methods (1E)
- Config: 5 wrong method names in api_reference.md (1C)
- Test cases: wrong mixin names, wrong state enum values (1B)

### Pattern 4: Schema-README Divergence (187 undocumented fields)
- 229 config fields total, only 42 (18.3%) documented correctly (3D)
- 157 phantom fields in READMEs that don't exist in code (3D)
- gdb: 24 fields, 0 documented, no README at all (2H, 3D)

### Pattern 5: Stale Post-Migration Artifacts (~35 instances)
- 20+ "BEHAVIORAL EQUIVALENCE" markers in cli_click/ (2E)
- 9 argparse references in cli_click module docstrings (2E)
- CLAUDE.md references deleted panther/cli/ directory (1A)
- 3 broken ADR links to deleted cli/adr/ (1B, 3E)

---

## Exemplary Documentation (Reference Patterns)

| Module | Why It's Good | Reference File |
|--------|--------------|----------------|
| core/state | Proportional docstrings, accurate, complete Google-style | state_manager.py |
| core/outputs | Gold-standard module docstring, architecture overview | outputs/__init__.py |
| core/command_processor | ADRs tightly coupled to code, mostly accurate api_reference | adr/0001-0003 |
| core/storage | All 9 public methods properly documented | event_store.py |
| Plugin facades | Concise facade pattern explanation, backward compat notes | iut_event_mixin.py |

---

## Agent Report Index

| Phase | Dispatch | Agent | Report |
|-------|----------|-------|--------|
| 0 | 1A | doc-miner-evidence-gatherer | [Root-level docs](agents/phase0-1A-root-level-docs.md) |
| 0 | 1B | doc-miner-evidence-gatherer | [Core architecture](agents/phase0-1B-core-architecture.md) |
| 0 | 1C | doc-miner-evidence-gatherer | [Config system](agents/phase0-1C-config-system.md) |
| 0 | 1D | doc-miner-evidence-gatherer | [Plugin system](agents/phase0-1D-plugin-system.md) |
| 0 | 1E | feature-dev:code-explorer | [Events/Observer/CmdProc](agents/phase0-1E-events-observer-cmdproc.md) |
| 0 | 1F | doc-miner-evidence-gatherer | [Test documentation](agents/phase0-1F-test-documentation.md) |
| 1 | 2A | comment-analyzer | [test_cases + outputs](agents/phase1-2A-test-cases-outputs.md) |
| 1 | 2B | comment-analyzer | [reporting/results/state/storage/template](agents/phase1-2B-reporting-results-state.md) |
| 1 | 2C | comment-analyzer | [plugins/core](agents/phase1-2C-plugins-core.md) |
| 1 | 2D | comment-analyzer | [core/exceptions](agents/phase1-2D-core-exceptions.md) |
| 1 | 2E | comment-analyzer | [cli_click](agents/phase1-2E-cli-click.md) |
| 1 | 2F | comment-analyzer | [tools](agents/phase1-2F-tools-module.md) |
| 1 | 2G | rfc-reviewer | [QUIC IUT READMEs](agents/phase1-2G-quic-iut-readmes.md) |
| 1 | 2H | rfc-reviewer | [Environment READMEs](agents/phase1-2H-environment-readmes.md) |
| 2 | 3A | code-reviewer | [experiment_manager.py](agents/phase2-3A-experiment-manager.md) |
| 2 | 3B | type-design-analyzer | [Config model types](agents/phase2-3B-config-model-types.md) |
| 2 | 3C | type-design-analyzer | [Plugin interface types](agents/phase2-3C-plugin-interface-types.md) |
| 2 | 3D | doc-miner-evidence-gatherer | [Config schema accuracy](agents/phase2-3D-config-schema-accuracy.md) |
| 2 | 3E | rfc-reviewer | [ADR quality](agents/phase2-3E-adr-quality.md) |
| 2 | 3F | code-reviewer | [Docker builder](agents/phase2-3F-docker-builder.md) |
| 2 | 3G | comment-analyzer | [Service mixin comments](agents/phase2-3G-service-mixin-comments.md) |
| 3 | 4A | code-explorer | [MkDocs pipeline](agents/phase3-4A-mkdocs-pipeline.md) |
| 3 | 4B | doc-miner-evidence-gatherer | [Broken links](agents/phase3-4B-broken-links.md) |
| 3 | 4C | rfc-reviewer | [Style consistency](agents/phase3-4C-style-consistency.md) |
| 3 | 4D | code-reviewer | [Modified files staleness](agents/phase3-4D-modified-files-staleness.md) |
