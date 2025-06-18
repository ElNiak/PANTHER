# PANTHER Logging Cleanup Implementation Plan

## Overview

This document outlines a comprehensive plan to reduce logging verbosity in PANTHER while maintaining useful debugging capabilities. The goal is to achieve a 70% reduction in log volume while improving signal-to-noise ratio.

## Key Principles

1. **Progressive Disclosure**: Show summaries at INFO, details at DEBUG, full data at TRACE
2. **Smart Filtering**: Skip no-op operations, redundant events, and unchanged data
3. **Context-Aware**: Different log levels for different operations
4. **Performance-First**: Lazy evaluation and buffering for high-frequency logs
5. **User-Centric**: Clear progress indicators and meaningful summaries

## Implementation Phases

### Phase 1: Critical Verbosity Reduction (Week 1)

#### CONFIG-001: Implement Smart Config Logging

- [ ] **Task 1.1**: Create config summarizer utility
  - Location: `panther/core/utils/config_summarizer.py`
  - Implement `summarize_config()` to show only non-default values
  - Add `diff_configs()` to show changes between configs
  - Create `sanitize_config()` to mask sensitive data

- [ ] **Task 1.2**: Update ConfigManager logging
  - File: `panther/config/config_manager.py`
  - Replace full config dumps with summaries at lines 60-61, 463-468, 495-499
  - Add TRACE level logging for full configs
  - Implement config change tracking

- [ ] **Task 1.3**: Add sensitive data masking
  - Identify patterns: passwords, tokens, certificates
  - Create regex-based masking for common patterns
  - Add configurable masking rules

- [ ] **Task 1.4**: Update LoggingMixin
  - File: `panther/core/utils/logging_mixin.py`
  - Add TRACE level support
  - Implement smart object logging at lines 58-61
  - Add context-based log level switching

#### DOCKER-001: Streamline Docker Build Logging

- [ ] **Task 2.1**: Create Docker output parser
  - Location: `panther/core/docker_builder/output_parser.py`
  - Parse Docker build stages and progress
  - Extract meaningful milestones
  - Implement progress percentage calculation

- [ ] **Task 2.2**: Update DockerBuilder logging
  - File: `panther/core/docker_builder/docker_builder.py`
  - Replace line-by-line logging at lines 126, 138, 181-186
  - Add progress bar support using tqdm
  - Create build summary at completion

- [ ] **Task 2.3**: Consolidate Docker operations logging
  - File: `panther/core/docker_builder/docker_operations_mixin.py`
  - Batch similar operations
  - Log only significant state changes
  - Add operation timing summaries

#### EVENT-001: Event Data Filtering

- [ ] **Task 3.1**: Create event summarizer
  - Location: `panther/core/events/event_summarizer.py`
  - Implement event importance classification
  - Create data payload summaries
  - Add event batching logic

- [ ] **Task 3.2**: Update LoggerObserver
  - File: `panther/core/observer/impl/logger_observer.py`
  - Refactor lines 286-320 to use summarizer
  - Add configurable event filtering
  - Implement event importance levels

- [ ] **Task 3.3**: Optimize event emitters
  - Directory: `panther/core/events/*/emitter.py`
  - Add event deduplication
  - Implement rapid transition filtering
  - Create event batch emissions

### Phase 2: Command and Service Logging (Week 2)

#### CMD-001: Eliminate No-Op Command Logs

- [ ] **Task 4.1**: Add command validation
  - File: `panther/plugins/services/services_interface.py`
  - Check for actual commands before logging at lines 509-512, 526-527, 551-554
  - Skip empty/no-op command events
  - Add command complexity classification

- [ ] **Task 4.2**: Create command summarizer
  - Location: `panther/plugins/services/command_summarizer.py`
  - Summarize long commands
  - Group similar commands
  - Extract key parameters only

- [ ] **Task 4.3**: Update command generation logging
  - Directory: `panther/plugins/services/iut/`
  - Move detailed commands to DEBUG
  - Log command count and types at INFO
  - Add command execution timing

#### SERVICE-001: Service Lifecycle Consolidation

- [ ] **Task 5.1**: Create service state tracker
  - Location: `panther/plugins/services/service_state_tracker.py`
  - Track service lifecycle events
  - Consolidate rapid state changes
  - Generate lifecycle summaries

- [ ] **Task 5.2**: Update service event methods
  - File: `panther/plugins/services/service_event_methods.py`
  - Batch service creation events
  - Create setup completion summaries
  - Add service health indicators

- [ ] **Task 5.3**: Optimize tester logging
  - Directory: `panther/plugins/services/testers/`
  - Reduce Ivy compilation verbosity
  - Add test progress indicators
  - Summarize test results

### Phase 3: Environment and Plugin Optimization (Week 3)

#### ENV-001: Environment Setup Summarization

- [ ] **Task 6.1**: Create setup progress tracker
  - Location: `panther/plugins/environments/setup_tracker.py`
  - Track environment preparation stages
  - Calculate progress percentages
  - Identify critical milestones

- [ ] **Task 6.2**: Update network environment logging
  - File: `panther/plugins/environments/network_environment/docker_compose/docker_compose.py`
  - Consolidate logs at lines 98-100, 216, 239-241
  - Add setup stage summaries
  - Create readiness indicators

- [ ] **Task 6.3**: Optimize file generation logging
  - Move template rendering logs to DEBUG
  - Log only file count and types at INFO
  - Add generation timing summaries

#### PLUGIN-001: Plugin Discovery Optimization

- [ ] **Task 7.1**: Implement plugin cache
  - Location: `panther/plugins/plugin_cache.py`
  - Cache discovered plugins between runs
  - Detect plugin changes efficiently
  - Add cache invalidation logic

- [ ] **Task 7.2**: Update plugin manager logging
  - File: `panther/plugins/plugin_manager.py`
  - Log only new/changed plugins
  - Create plugin loading summary
  - Move validation details to DEBUG

- [ ] **Task 7.3**: Optimize plugin loader
  - File: `panther/plugins/plugin_loader_utils.py`
  - Batch plugin validation logs
  - Add plugin count summaries
  - Create capability matrix logging

### Phase 4: Advanced Features (Week 4)

#### LOG-001: Implement Contextual Logging

- [ ] **Task 8.1**: Create log context managers
  - Location: `panther/core/utils/log_context.py`
  - Implement operation-specific contexts
  - Add hierarchical log suppression
  - Create context-based filtering

- [ ] **Task 8.2**: Add dynamic log levels
  - Implement runtime level adjustment
  - Add per-component log levels
  - Create log level profiles

- [ ] **Task 8.3**: Integrate with experiment flow
  - Add context switching in ExperimentManager
  - Create phase-specific logging
  - Implement smart log rotation

#### PERF-001: Logging Performance

- [ ] **Task 9.1**: Add lazy evaluation
  - Location: `panther/core/utils/lazy_logging.py`
  - Implement lazy string formatting
  - Add expensive operation deferral
  - Create conditional evaluation

- [ ] **Task 9.2**: Implement log buffering
  - Add buffering for high-frequency logs
  - Create flush strategies
  - Implement buffer size limits

- [ ] **Task 9.3**: Add log sampling
  - Implement repetition detection
  - Add statistical sampling
  - Create sample rate configuration

#### UI-001: User-Friendly Output

- [ ] **Task 10.1**: Add progress indicators
  - Integrate tqdm for long operations
  - Create operation-specific spinners
  - Add ETA calculations

- [ ] **Task 10.2**: Implement structured logging
  - Add JSON output option
  - Create machine-parseable formats
  - Implement log streaming APIs

- [ ] **Task 10.3**: Create output modes
  - Add quiet/normal/verbose modes
  - Implement interactive mode
  - Create report generation

## Testing and Validation

### Unit Tests

- [ ] Test config summarizer with various config sizes
- [ ] Validate sensitive data masking
- [ ] Test event batching and deduplication
- [ ] Verify command filtering logic
- [ ] Test progress calculation accuracy

### Integration Tests

- [ ] Run full experiment with old vs new logging
- [ ] Compare log file sizes
- [ ] Validate no loss of critical information
- [ ] Test performance improvements
- [ ] Verify user experience improvements

### Performance Benchmarks

- [ ] Measure logging overhead reduction
- [ ] Test memory usage with buffering
- [ ] Validate I/O improvements
- [ ] Benchmark with high-frequency events
- [ ] Test scalability with large experiments

## Configuration Updates

### New Configuration Options

```yaml
logging:
  level: INFO
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
  
  # New options
  progressive_disclosure:
    enabled: true
    summary_level: INFO
    detail_level: DEBUG
    full_data_level: TRACE
  
  filtering:
    skip_no_ops: true
    deduplicate_events: true
    batch_rapid_transitions: true
    
  performance:
    lazy_evaluation: true
    buffer_size: 1000
    sampling_rate: 0.1  # For repetitive logs
    
  output:
    mode: normal  # quiet, normal, verbose
    progress_indicators: true
    structured_format: false
```

### Observer Configuration

```yaml
observers:
  logger:
    enabled: true
    log_level: "INFO"
    
    # New options
    summarization:
      configs: true
      events: true
      commands: true
      
    filtering:
      event_importance_threshold: "medium"
      max_event_data_length: 100
      skip_empty_commands: true
      
    batching:
      enabled: true
      window_ms: 100
      max_batch_size: 10
```

## Migration Guide

### For Developers

1. Replace direct config logging with summarizer calls
2. Use new context managers for operation logging
3. Implement importance levels for new events
4. Add progress indicators for long operations
5. Use lazy evaluation for expensive log operations

### For Users

1. Update configuration files with new options
2. Use `--log-mode` CLI option for output control
3. Enable progress indicators for better UX
4. Use structured logging for automation
5. Adjust filtering thresholds as needed

## Success Metrics

- [ ] 70% reduction in log file size for typical experiments
- [ ] 90% reduction in configuration-related log entries
- [ ] 50% improvement in log processing performance
- [ ] 95% of users report improved clarity
- [ ] No loss of debugging capability

## Rollback Plan

1. Keep original logging methods as deprecated
2. Add feature flags for new logging behavior
3. Provide conversion scripts for log analysis tools
4. Maintain backward compatibility for 2 releases
5. Document all breaking changes

## Timeline

- **Week 1**: Phase 1 implementation and testing
- **Week 2**: Phase 2 implementation and integration
- **Week 3**: Phase 3 implementation and optimization
- **Week 4**: Phase 4 features and final testing
- **Week 5**: Documentation and migration support
- **Week 6**: Release and monitoring

## Dependencies

- tqdm: For progress indicators
- structlog: For structured logging (optional)
- colorama: For colored output (already present)
- pytest: For comprehensive testing

## Notes

- All file paths are relative to project root
- Line numbers reference current state and may change
- TRACE level is new and needs logging framework update
- Performance metrics should be collected before/after
- User feedback should guide priority adjustments