# Phase 3 - Dispatch 4B: Broken Link Audit

**Agent:** doc-miner-evidence-gatherer
**Status:** COMPLETE
**Scope:** 17 high-cross-reference-density markdown files

## Summary

**57 broken / 103 total links (55.3% broken)**. Five distinct failure patterns identified. The worst offenders are `panther/core/README.md` (11/13 broken), `CONTRIBUTING.md` (11/14 broken), and `panther/core/adr/README.md` (9/12 broken). Root `README.md` is the only major file with zero broken links.

## Root Cause Patterns

| Pattern | Count | Description |
|---------|:---:|-------------|
| Absolute-style paths as relative | 29 | Links written as `panther/config/README.md` instead of `../config/README.md` |
| Missing files | 17 | Target files never created (EXPERIMENT_ENGINE.md, cli/adr/, docs/packaging/) |
| Wrong ADR subdirectory prefix | 5 | `utils/adr/` instead of `../utils/adr/` |
| dev/docs-gen/ absent | 10 | Entire `dev/docs-gen/` directory referenced but doesn't exist |
| Case mismatch | 1 | `WORKFLOW.md` vs `workflow.md` |

## Broken Links by Source File

| Source File | Total Links | Broken | % Broken |
|-------------|:---:|:---:|:---:|
| panther/core/README.md | 13 | **11** | 85% |
| panther/core/adr/README.md | 12 | **9** | 75% |
| CONTRIBUTING.md | 14 | **11** | 79% |
| PACKAGING.md | 8 | **7** | 88% |
| panther/plugins/README.md | 7 | **6** | 86% |
| panther/plugins/development.md | 7 | **6** | 86% |
| panther/cli_click/README.md | 5 | **4** | 80% |
| panther/README.md | 3 | **3** | 100% |
| README.md (root) | 31 | **0** | 0% |
| workflow.md | 1 | **0** | 0% |
| QUICK_START.md | 2 | **0** | 0% |
| panther/config/README.md | 0 | **0** | - |
| panther/core/events/README.md | 0 | **0** | - |
| panther/core/observer/README.md | 0 | **0** | - |
| panther/core/command_processor/README.md | 0 | **0** | - |
| panther/core/docker_builder/README.md | 0 | **0** | - |
| **TOTALS** | **103** | **57** | **55.3%** |

## Complete Broken Link Inventory

### panther/core/README.md (11 broken)

| Line | Link Text | Target | Root Cause |
|------|-----------|--------|-----------|
| 47 | Experiment Engine | panther/core/EXPERIMENT_ENGINE.md | Absolute path + file missing |
| 48 | Configuration System | panther/config/README.md | Absolute path in relative context |
| 49 | Event System | panther/core/events/README.md | Absolute path in relative context |
| 50 | Observer Pattern | panther/core/observer/README.md | Absolute path in relative context |
| 51 | Metrics System | panther/core/metrics/README.md | Absolute path in relative context |
| 52 | Command Processor | panther/core/command_processor/README.md | Absolute path in relative context |
| 53 | Reporting System | ../../EXPERIMENT_REPORTING.md | File missing |
| 55 | CLI Interface | panther/README.md | Absolute path in relative context |
| 220 | Configuration Guide | panther/config/README.md | Absolute path in relative context |
| 221 | Plugin Development | panther/plugins/development.md | Absolute path in relative context |
| 222 | Quick Start | QUICK_START.md | Resolves to panther/core/QUICK_START.md |

### panther/core/adr/README.md (9 broken)

| Line | Link Text | Target | Root Cause |
|------|-----------|--------|-----------|
| 11 | Utils ADR 0001 | utils/adr/0001-... | Missing ../ prefix |
| 12 | Utils ADR 0002 | utils/adr/0002-... | Missing ../ prefix |
| 18 | CLI ADR 0001 | ../cli/adr/0001-... | cli/ directory deleted |
| 19 | CLI ADR 0002 | ../cli/adr/0002-... | cli/ directory deleted |
| 20 | CLI ADR 0003 | ../cli/adr/0003-... | cli/ directory deleted |
| 26 | CP ADR 0001 | command_processor/adr/0001-... | Missing ../ prefix |
| 27 | CP ADR 0002 | command_processor/adr/0002-... | Missing ../ prefix |
| 28 | CP ADR 0003 | command_processor/adr/0003-... | Missing ../ prefix |
| 34 | Config ADR 0001 | ../config/adr/0001-... | File never created |

### CONTRIBUTING.md (11 broken)

| Line | Link Text | Target | Root Cause |
|------|-----------|--------|-----------|
| 112 | Documentation CI | dev/docs-gen/documentation-ci.yml | Directory missing |
| 118 | Update Script | dev/docs-gen/update_docs.sh | Directory missing |
| 119 | Link Verification | dev/docs-gen/verify_links.py | Directory missing |
| 120 | Cross-References | dev/docs-gen/add_cross_references.py | Directory missing |
| 121 | MkDocs Configuration | dev/docs-gen/enhance_mkdocs_config.py | Directory missing |
| 125 | Workflow Guide | dev/docs-gen/documentation_WORKFLOW.md | Directory missing |
| 126 | Integration Guide | dev/docs-gen/documentation_integration.md | Directory missing |
| 127 | Link Management | dev/docs-gen/documentation_links.md | Directory missing |
| 128 | System Enhancements | dev/docs-gen/documentation_enhancements.md | Directory missing |
| 132 | Style Guide | dev/docs-gen/style_guide.md | Directory missing |
| 283 | Style Guide (dup) | dev/docs-gen/style_guide.md | Directory missing |

### PACKAGING.md (7 broken)

| Line | Link Text | Target | Root Cause |
|------|-----------|--------|-----------|
| 226 | Troubleshooting | docs/packaging/troubleshooting.md | Directory missing |
| 258 | Migration Guide | docs/packaging/migration-guide.md | Directory missing |
| 262 | User Guide | docs/packaging/user-guide.md | Directory missing |
| 263 | Developer Guide | docs/packaging/developer-guide.md | Directory missing |
| 264 | API Reference | docs/packaging/api-reference.md | Directory missing |
| 265 | Migration Guide (dup) | docs/packaging/migration-guide.md | Directory missing |
| 266 | Troubleshooting (dup) | docs/packaging/troubleshooting.md | Directory missing |

### panther/plugins/README.md (6 broken)

| Line | Link Text | Target | Root Cause |
|------|-----------|--------|-----------|
| 99 | Plugin Loader | panther/plugins/plugin_loader.py | Absolute path + file missing |
| 100 | Plugin Manager | panther/plugins/plugin_manager.py | Absolute path + file missing |
| 101 | Plugin Interface | panther/plugins/plugin_interface.py | Absolute path in relative context |
| 116 | Services Guide | panther/plugins/services/README.md | Absolute path in relative context |
| 144 | Protocol Guide | panther/plugins/protocols/README.md | Absolute path in relative context |
| 155 | Environment Guide | panther/plugins/environments/README.md | Absolute path in relative context |

### panther/plugins/development.md (6 broken)

| Line | Link Text | Target | Root Cause |
|------|-----------|--------|-----------|
| 6 | WORKFLOW.md | ../../WORKFLOW.md | Case mismatch (workflow.md) |
| 12 | Service Development | panther/plugins/services/development.md | Absolute path in relative context |
| 13 | Protocol Development | panther/plugins/protocols/development.md | Absolute path in relative context |
| 14 | Environment Development | panther/plugins/environments/development.md | Absolute path in relative context |
| 15 | General Plugin Dev | panther/plugins/development.md | Absolute path (self-ref) |
| 567 | plugin template | panther/plugins/plugin_template.md | Absolute path in relative context |

### panther/cli_click/README.md (4 broken)

| Line | Link Text | Target | Root Cause |
|------|-----------|--------|-----------|
| 304 | Migration Guide | ../../docs/cli_migration_guide.md | File missing |
| 344 | Migration Guide (dup) | ../../docs/cli_migration_guide.md | File missing |
| 345 | Examples | ../../docs/cli_examples.md | File missing |
| 346 | Quick Reference | ../../docs/cli_quick_reference.md | File missing |

### panther/README.md (3 broken)

| Line | Link Text | Target | Root Cause |
|------|-----------|--------|-----------|
| 454 | Configuration System | panther/config/README.md | Absolute path in relative context |
| 455 | Experiment Engine | panther/core/EXPERIMENT_ENGINE.md | Absolute path + file missing |
| 456 | Plugin Development | panther/plugins/development.md | Absolute path in relative context |

## Files with Zero Broken Links
- `README.md` (root) -- 31 links, all valid
- `workflow.md` -- 1 link, valid
- `QUICK_START.md` -- 2 links, valid
- `panther/core/events/README.md` -- self-contained, no file links
- `panther/core/observer/README.md` -- self-contained, no file links
- `panther/core/command_processor/README.md` -- self-contained, no file links
- `panther/core/docker_builder/README.md` -- self-contained, no file links

## Issues Summary
- **Total broken links:** 57
- **Unique broken targets:** ~30 (after deduplication)
- **Pattern 1 (absolute-style):** 29 links -- fixable with path correction
- **Pattern 2 (missing files):** 17 links -- requires file creation or link removal
- **Pattern 3 (wrong prefix):** 5 links -- fixable with `../` addition
- **Pattern 4 (absent directory):** 10 links -- requires directory creation or link removal
- **Pattern 5 (case mismatch):** 1 link -- fixable with lowercase
