# Phase 0 - Dispatch 1F: Test Documentation Evidence

**Agent:** doc-miner-evidence-gatherer
**Status:** COMPLETE
**Files Analyzed:** tests/README.md, tests/COMPREHENSIVE_TESTING_SUMMARY.md, tests/COMPREHENSIVE_TEST_DOCUMENTATION.md, tests/COVERAGE_ANALYSIS_REPORT.md, tests/DEVELOPMENT.md
**Cross-referenced:** pyproject.toml, actual test files in tests/unit/ and tests/integration/

## Critical Findings

### CRITICAL: 8+ Unregistered Pytest Markers
- pyproject.toml has `--strict-markers` enabled
- Documented markers NOT registered in pyproject.toml: `@pytest.mark.smoke`, `@pytest.mark.regression`, `@pytest.mark.performance`, `@pytest.mark.security`, `@pytest.mark.api`, `@pytest.mark.cli`, `@pytest.mark.config`, `@pytest.mark.docker`
- Using these markers with `--strict-markers` causes immediate collection failure
- Only registered: `unit`, `integration`, `requires_docker`, `slow`
- Severity: CRITICAL (ACC-01) - documentation recommends markers that break test collection

### HIGH: Coverage Threshold Mismatch
- tests/README.md claims 85% coverage threshold
- pyproject.toml specifies `--cov-fail-under=70`
- CLAUDE.md also states 70%
- Severity: HIGH (ACC-07)

### HIGH: Coverage Numbers Are "Estimated" Not Measured
- COVERAGE_ANALYSIS_REPORT.md presents detailed per-module percentages
- Report header states these are "estimated" coverage numbers
- No evidence of actual coverage measurement generating these numbers
- Severity: HIGH (ACC-05)

### HIGH: "Zero Technical Debt" Claim Is False
- COMPREHENSIVE_TESTING_SUMMARY.md claims "zero technical debt"
- Multiple TODO comments exist in test files
- Several test files reference deleted modules (panther/cli/)
- Severity: HIGH (ACC-01)

## Major Findings

| Finding | Source | Severity |
|---------|--------|----------|
| Python version documented as 3.8 minimum | tests/README.md | MAJOR (ACC-07) - actual is >=3.10 per pyproject.toml |
| pytest minimum version documented as 6.0.0 | tests/README.md | MAJOR (ACC-07) - actual is 7.3.0 per pyproject.toml |
| Test file paths reference `test_case.py` | Multiple docs | MAJOR (ACC-01) - actual is `test_case_impl.py` |
| Documented test scenarios lack corresponding implementations | COMPREHENSIVE_TEST_DOCUMENTATION.md | MAJOR (CMP-10) |
| Integration test docs reference Docker Compose v1 syntax | tests/README.md | MAJOR (ACC-04) |

## Minor Findings

| Finding | Source | Severity |
|---------|--------|----------|
| conftest.py fixtures documented but some don't exist | tests/README.md | MINOR (ACC-02) |
| Test directory structure diagram outdated | tests/README.md | MINOR (ACC-01) |
| Fixture naming conventions not followed consistently | Multiple files | MINOR (CON-03) |

## Summary Statistics
- **Total claims verified:** ~45
- **ACCURATE:** ~20 (44%)
- **INACCURATE:** ~18 (40%)
- **UNVERIFIABLE:** ~7 (16%)
