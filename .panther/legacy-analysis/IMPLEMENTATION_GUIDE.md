# PANTHER Legacy Code Refactoring Implementation Guide

This guide provides step-by-step instructions for implementing the refactoring recommendations from the legacy detection analysis.

## Overview

The refactoring effort is divided into 4 phases over 4 weeks:
- **Phase 1 (Week 1)**: Critical fixes
- **Phase 2 (Week 2-3)**: QUIC consolidation  
- **Phase 3 (Week 3-4)**: Complexity reduction
- **Phase 4 (Week 4)**: Polish and documentation

## Phase 1: Critical Fixes (Days 1-5)

### 1.1 Error Management Strategy (Day 1-2)

**File**: `panther/core/experiment_manager.py`  
**Issue**: Missing error management strategy (TODO comment)  
**Solution**: Implement comprehensive error handling with retry logic

#### Implementation Steps:

1. **Copy the error handling framework**:
   ```bash
   cp .panther/legacy-analysis/refactoring_examples/error_handling_strategy.py \
      panther/core/exceptions/error_management.py
   ```

2. **Update experiment_manager.py**:
   ```python
   # In panther/core/experiment_manager.py
   from panther.core.exceptions.error_management import (
       ErrorManagementStrategy, 
       with_error_handling,
       error_context
   )
   
   class ExperimentManager:
       def __init__(self, ...):
           # Add error strategy
           self.error_strategy = ErrorManagementStrategy()
           
       @with_error_handling("experiment", "initialization")
       def initialize(self, config):
           # Existing initialization code
           pass
   ```

3. **Add retry logic to test execution**:
   ```python
   def run_tests(self, tests):
       for test in tests:
           with error_context(test["name"], "execution", self.error_strategy) as ctx:
               ctx.max_attempts = test.get("retry_count", 3)
               self._execute_test(test)
   ```

### 1.2 Event Store Transactions (Day 2-3)

**File**: `panther/core/storage/event_store.py`  
**Issue**: Missing transaction support  
**Solution**: Implement SQLite transactions with WAL mode

#### Implementation Steps:

1. **Backup existing event_store.py**:
   ```bash
   cp panther/core/storage/event_store.py \
      panther/core/storage/event_store.py.backup
   ```

2. **Integrate transaction support**:
   ```python
   # Replace the store_event method
   def store_event(self, event):
       with self.transaction() as ctx:
           return ctx.add_event(event)
   
   # Add batch support
   def store_events_batch(self, events):
       with self.transaction() as ctx:
           return ctx.add_events(events)
   ```

3. **Update callers to use batch operations**:
   ```bash
   # Find all calls to store_event
   grep -r "store_event" panther/ --include="*.py" | grep -v "def store_event"
   ```

### 1.3 Complete Template Renderer (Day 3-4)

**File**: `panther/core/template/template_renderer.py`  
**Issue**: Incomplete implementation  
**Solution**: Complete the TODO sections

#### Implementation Steps:

1. **Identify incomplete sections**:
   ```bash
   grep -n "TODO" panther/core/template/template_renderer.py
   ```

2. **Implement missing functionality**:
   ```python
   def render_template(self, template_name, context):
       # TODO: Add template caching
       template = self._load_template(template_name)
       return self._render_with_context(template, context)
   ```

### 1.4 Shell Utils Complexity (Day 4-5)

**File**: `panther/core/command_processor/shell_utils.py`  
**Issue**: Cyclomatic complexity of 67  
**Solution**: Break into smaller, focused classes

#### Implementation Steps:

1. **Create new modular structure**:
   ```bash
   # Create new files
   touch panther/core/command_processor/shell_construct_detector.py
   touch panther/core/command_processor/shell_command_builder.py
   ```

2. **Move detection logic**:
   ```python
   # In shell_construct_detector.py
   from abc import ABC, abstractmethod
   
   class ShellConstructDetector(ABC):
       @abstractmethod
       def matches(self, line: str) -> bool:
           pass
   ```

3. **Refactor main function**:
   ```python
   # In shell_utils.py
   def combine_shell_constructs(cmd_parts):
       detector = ShellConstructManager()
       builder = ShellCommandBuilder()
       
       # Simplified logic using new classes
       return builder.build_from_parts(cmd_parts, detector)
   ```

## Phase 2: QUIC Service Consolidation (Days 6-15)

### 2.1 Create Enhanced Base Classes (Day 6-7)

#### Implementation Steps:

1. **Update base QUIC class**:
   ```bash
   cp .panther/legacy-analysis/refactoring_examples/quic_base_refactored.py \
      panther/plugins/services/base/quic_service_base_v2.py
   ```

2. **Create migration script**:
   ```python
   # migrate_quic_services.py
   import ast
   import os
   
   def migrate_service(old_file, new_base):
       # Parse old implementation
       # Extract custom logic
       # Generate new implementation using base class
       pass
   ```

### 2.2 Migrate Individual Implementations (Day 8-12)

#### Order of Migration (easiest to hardest):

1. **Quant** (134 LOC → ~50 LOC)
2. **Quiche** (190 LOC → ~80 LOC)
3. **Quinn** (191 LOC → ~80 LOC)
4. **Lsquic** (184 LOC → ~70 LOC)
5. **Mvfst** (194 LOC → ~70 LOC)
6. **Aioquic** (236 LOC → ~100 LOC)
7. **Picoquic** (629 LOC → ~150 LOC)

#### Migration Template:

```python
# Example: Migrating Quant
from panther.plugins.services.base.quic_service_base_v2 import BaseQUICServiceManager

class QuantServiceManager(BaseQUICServiceManager):
    def _initialize_implementation(self, **kwargs):
        self.quant_version = kwargs.get("version", "latest")
    
    @property
    def binary_path(self):
        return "/opt/quant/bin/client"
    
    def _get_implementation_client_args(self, params, **kwargs):
        # Only Quant-specific args here
        return ["--cc", kwargs.get("cc_algo", "cubic")]
```

### 2.3 Add Comprehensive Tests (Day 13-15)

#### Test Structure:

```python
# tests/test_quic_refactoring.py
import pytest
from panther.plugins.services.iut.quic.quant.quant import QuantServiceManager

class TestQUICRefactoring:
    def test_command_generation_compatibility(self):
        """Ensure commands are identical before/after refactoring."""
        old_manager = OldQuantServiceManager(...)
        new_manager = QuantServiceManager(...)
        
        old_cmd = old_manager.generate_deployment_commands(...)
        new_cmd = new_manager.generate_deployment_commands(...)
        
        assert old_cmd == new_cmd
```

## Phase 3: Complexity Reduction (Days 16-20)

### 3.1 Complex Function Refactoring

Target functions by priority:
1. `combine_shell_constructs` (complexity: 67)
2. `handle` in cli/run.py (complexity: 39)
3. `_get_raw_metrics` (complexity: 36)

### 3.2 Error Handling Standardization

Create consistent error handling patterns:
```python
# Standard error handling template
try:
    result = operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    if self.fail_fast:
        raise
    return default_value
```

## Phase 4: Polish and Documentation (Days 21-25)

### 4.1 Update Documentation

1. **Architecture diagrams**:
   ```mermaid
   classDiagram
       BaseQUICServiceManager <|-- PythonQUICServiceManager
       BaseQUICServiceManager <|-- RustQUICServiceManager
       PythonQUICServiceManager <|-- AioquicServiceManager
       RustQUICServiceManager <|-- QuinnServiceManager
       RustQUICServiceManager <|-- QuicheServiceManager
   ```

2. **Migration guide for external developers**

3. **Updated plugin development guide**

### 4.2 Performance Benchmarks

```python
# benchmark_refactoring.py
import time

def benchmark_command_generation():
    iterations = 1000
    
    # Old implementation
    start = time.time()
    for _ in range(iterations):
        old_manager.generate_deployment_commands(...)
    old_time = time.time() - start
    
    # New implementation
    start = time.time()
    for _ in range(iterations):
        new_manager.generate_deployment_commands(...)
    new_time = time.time() - start
    
    print(f"Performance improvement: {old_time/new_time:.2f}x")
```

## Validation Checklist

### Phase 1 Validation
- [ ] All tests pass after error handling implementation
- [ ] Event store supports transactions
- [ ] Template renderer complete
- [ ] Shell utils complexity < 10 per function

### Phase 2 Validation  
- [ ] All QUIC services use new base class
- [ ] Command generation identical to original
- [ ] 40%+ code reduction achieved
- [ ] All QUIC tests pass

### Phase 3 Validation
- [ ] No functions with complexity > 30
- [ ] Consistent error handling patterns
- [ ] All bare raise statements addressed

### Phase 4 Validation
- [ ] Documentation updated
- [ ] Performance benchmarks show improvement
- [ ] External plugin compatibility maintained
- [ ] Code review completed

## Rollback Plan

If issues arise:

1. **Immediate rollback**:
   ```bash
   git checkout main
   git branch -D refactoring-legacy
   ```

2. **Partial rollback**:
   ```bash
   # Revert specific file
   git checkout main -- path/to/file.py
   ```

3. **Feature flag approach**:
   ```python
   if os.environ.get("USE_NEW_QUIC_BASE"):
       from .quic_service_base_v2 import BaseQUICServiceManager
   else:
       from .quic_service_base import BaseQUICServiceManager
   ```

## Success Metrics

Track these metrics throughout implementation:

1. **Code Metrics**:
   - LOC reduction: Target 48% in QUIC module
   - Complexity reduction: Target <10 per function
   - Duplication: Target <10%

2. **Quality Metrics**:
   - Test coverage: Maintain or improve
   - Bug reports: Track pre/post refactoring
   - Performance: Benchmark critical paths

3. **Developer Metrics**:
   - Time to implement new QUIC service
   - Code review time
   - Bug fix time

## Support Resources

- **Slack Channel**: #panther-refactoring
- **Documentation**: /docs/refactoring-guide.md
- **Issue Tracking**: GitHub Issues with label "refactoring"
- **Code Reviews**: Require 2 approvals for refactoring PRs

---

Remember: This is a living document. Update it as you learn and adapt during the refactoring process.