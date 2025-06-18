# PANTHER Legacy Code Initial Analysis
Generated: $(date +%Y-%m-%d)

## Executive Summary
Initial scan reveals manageable technical debt with clear refactoring opportunities in the QUIC service implementations.

## Key Findings

### 1. Legacy Comments (TODO/FIXME)
- **Total Found**: 10+ instances
- **Priority Areas**:
  - `panther/core/experiment_manager.py` - Missing error management strategy
  - `panther/core/storage/event_store.py` - Transaction handling needed
  - `panther/core/template/template_renderer.py` - Incomplete implementation
  - `panther/core/workflow/workflow_tracker.py` - Hardcoded logging level

### 2. Code Duplication Patterns
- **QUIC Services**: 28 implementation files with similar patterns
- **Service Managers**: Multiple implementations following BaseServiceManager pattern
- **Common Files**: Duplicate `config_schema.py` and `__init__.py` structures

### 3. Deprecated/Legacy Code
- `panther/core/metrics/metrics_collector.py` - Deprecated `details` parameter
- `panther/tools/plugins/plugin_migration_tool.py` - Contains "old_" migration code
- `panther/core/observer/impl/storage_observer.py` - Has `cleanup_old_data()` method

### 4. Refactoring Opportunities
- **High Priority**: Consolidate QUIC service implementations using template method pattern
- **Medium Priority**: Extract common service manager functionality to base classes
- **Low Priority**: Clean up TODO comments and deprecated parameters

## Recommendations

### Immediate Actions
1. Address critical TODOs in experiment_manager.py (error handling)
2. Implement transaction handling in event_store.py
3. Complete template_renderer.py implementation

### Short-term Improvements
1. Create unified base class for QUIC services with:
   - Common command generation
   - Shared configuration handling
   - Standardized error handling
   
2. Refactor service managers to reduce duplication:
   - Extract common patterns to mixins
   - Use composition over inheritance where appropriate

### Long-term Goals
1. Establish code quality metrics baseline
2. Implement automated legacy detection in CI/CD
3. Create refactoring roadmap for major components

## Next Steps
1. Run full `/detect-legacy --scan-type=all --fix-suggestions --export-report`
2. Review function similarity analysis results
3. Create technical debt backlog items
4. Prioritize refactoring based on impact and effort