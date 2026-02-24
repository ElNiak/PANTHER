# Phase 0 - Dispatch 1A: Root-Level Documentation Accuracy

**Agent:** doc-miner-evidence-gatherer
**Status:** COMPLETE
**Files Analyzed:** README.md, CLAUDE.md, CONTRIBUTING.md, INSTALL.md, INSTALL_NOTES.md, PACKAGING.md, QUICK_START.md, workflow.md, CHANGELOG.md
**Cross-referenced:** pyproject.toml, actual filesystem

## Critical Findings

### CRITICAL: Broken Entry Points in pyproject.toml
- `panther-metrics = "panther.metrics.cli:main"` - `panther/metrics/` directory does not exist (ACC-06)
- `panther-plugin-tool = "panther.plugins.plugin_migration_tool:create_cli"` - file does not exist (ACC-06)
- These will fail at install time

### HIGH: `panther/cli/` Claimed But Deleted
- CLAUDE.md:9,116 claims argparse CLI still present at `panther/cli/`
- Directory does not exist on disk; only `panther/cli_click/` exists
- Severity: HIGH (ACC-01)

### HIGH: CHANGELOG Missing 2 Versions
- CHANGELOG.md only documents up to v1.1.3
- pyproject.toml shows v1.1.5
- Versions v1.1.4 and v1.1.5 missing from changelog
- Severity: HIGH (ACC-07)

### HIGH: Config ADR File Missing
- CLAUDE.md:183 references `panther/config/adr/0001-hybrid-pydantic-omegaconf-architecture.md`
- No `adr/` subdirectory exists inside `panther/config/`
- Severity: HIGH (ACC-06)

### HIGH: 9 Broken Links in CONTRIBUTING.md
- All `dev/docs-gen/` links (9 total) point to non-existent `dev/` directory
- Severity: HIGH (ACC-06)

### HIGH: 5 Broken Links in PACKAGING.md
- All `docs/packaging/` links point to non-existent directory
- `pyproject_hatchling.toml` referenced but doesn't exist
- `--list-plugins` CLI flag doesn't exist (correct: `panther plugins list`)
- Severity: HIGH (ACC-06)

## Medium Findings

| Finding | Source | Category |
|---------|--------|----------|
| PANTHER acronym differs between README and pyproject.toml | README.md:1 vs pyproject.toml:50 | ACC-01 |
| `test_case.py` path wrong in workflow.md; actual is `test_case_impl.py` | workflow.md:63 | ACC-01 |
| Qodana badge points to deleted workflow | README.md:15 | MNT-01 |
| CHANGELOG contains TODO comment | CHANGELOG.md:42 | MNT-02 |

## Low Findings

| Finding | Source | Category |
|---------|--------|----------|
| `argcomplete` referenced but not in pyproject.toml | INSTALL.md:152 | ACC-01 |
| Python 3.8 annotation wrong (requires >=3.10) | INSTALL.md:138 | ACC-07 |
| Config example path wrong in QUICK_START.md | QUICK_START.md:133 | ACC-06 |
| `.yml` extension used but files use `.yaml` | QUICK_START.md:185 | ACC-01 |

## Summary Statistics
- **Total claims verified:** 110
- **ACCURATE:** 71 (64.5%)
- **INACCURATE:** 31 (28.2%)
- **UNVERIFIABLE:** 8 (7.3%)
