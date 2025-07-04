# Adaptive Command Selection Test Suite

## Overview

This comprehensive test suite validates the AdaptiveCommandSelector functionality, focusing on:
- Context classification accuracy
- Learning system effectiveness
- Integration with other ATLAS components
- Performance and scalability
- Edge case handling

## Test Files

### 1. `test_adaptive_command_selector.py`
**Purpose**: Core unit tests for AdaptiveCommandSelector

**Key Tests**:
- Context classification accuracy (target: 80%+)
- Recommendation generation
- Risk assessment
- Time estimation with complexity factors
- Learning system functionality
- Edge cases (empty history, unknown domains, long sequences)

**Current Issues Found**:
- Context classification accuracy: 62.5% (needs improvement)
- Task descriptions like "Refactor payment module" misclassified as GREENFIELD
- "Debug memory leak" misclassified as MAINTENANCE instead of DEBUGGING

### 2. `test_adaptive_integration.py`
**Purpose**: Integration tests with MCP server and other components

**Key Tests**:
- MCP tool registration and execution
- Integration with TaskManager
- Memory graph integration
- Workflow enforcer compatibility
- Pattern analyzer feedback loop
- Persistence across sessions

### 3. `test_context_classification_improvements.py`
**Purpose**: Focused tests on improving context classification

**Key Tests**:
- Enhanced keyword matching
- Compound task classification
- Noisy/verbose descriptions
- Domain-specific terminology
- Real-world task descriptions
- Weighted scoring approach
- Regex pattern matching

**Improvements Proposed**:
- Priority-based keyword matching
- Weighted scoring instead of simple matching
- Regex patterns for complex cases
- Better handling of compound tasks

### 4. `test_learning_persistence.py`
**Purpose**: Validate learning system persistence and influence

**Key Tests**:
- Cache initialization and management
- Pattern creation and storage
- File persistence (save/load)
- Learning influence on recommendations
- Domain-specific learning
- Temporal pattern decay
- Concurrent access safety
- Cache corruption recovery

### 5. `test_adaptive_performance.py`
**Purpose**: Performance and stress testing

**Key Tests**:
- Baseline recommendation speed (<10ms target)
- Performance with large history
- Memory usage under load
- Concurrent operations
- Pattern matching performance
- Cache persistence performance
- Stress test (>1000 ops/second)
- Scalability with domains

## Running Tests

### Quick Run
```bash
# Run all adaptive tests
./run_adaptive_tests.sh

# Run specific test file
pytest test_adaptive_command_selector.py -v

# Run with coverage
pytest test_adaptive_*.py --cov=atlas_commands.workflow.adaptive_command_selector
```

### Performance Tests Only
```bash
pytest test_adaptive_performance.py -v -s
```

### Classification Tests Only
```bash
pytest test_context_classification_improvements.py -v
```

## Key Findings

### 1. Classification Accuracy Issue
**Problem**: Only 62.5% accuracy in context classification
**Impact**: Wrong command recommendations for 37.5% of cases
**Solution**: Implemented `ImprovedAdaptiveCommandSelector` with:
- Priority-based keyword matching
- Weighted scoring system
- Better handling of compound descriptions

### 2. Learning System
**Status**: Working correctly
**Features**:
- Patterns persist across sessions
- Successfully influences recommendations
- Handles concurrent access safely

### 3. Performance
**Status**: Excellent
- <10ms per recommendation (baseline)
- <50ms with large history (100 patterns)
- Handles >1000 operations/second under stress
- Memory usage reasonable (<100MB for 10k patterns)

### 4. Integration
**Status**: Fully integrated
- MCP server integration working
- Task manager compatibility verified
- Memory graph integration functional

## Recommended Actions

1. **Immediate**: Replace `_classify_context_type` method with improved version
2. **Short-term**: Implement weighted scoring for classification
3. **Long-term**: Consider ML-based classification for better accuracy

## Test Coverage

Current coverage targets:
- Core functionality: 95%+
- Edge cases: 90%+
- Performance scenarios: Comprehensive
- Integration points: All major components

## CI/CD Integration

Add to CI pipeline:
```yaml
- name: Run Adaptive Command Tests
  run: |
    cd mcp-atlas-commands/tests
    ./run_adaptive_tests.sh
```

## Future Enhancements

1. **Fuzzy Matching**: Implement similarity scoring for task descriptions
2. **Context History**: Use previous classifications to improve accuracy
3. **A/B Testing**: Compare original vs improved classification
4. **Metrics Dashboard**: Track classification accuracy over time