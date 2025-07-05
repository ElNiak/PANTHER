# ADR-0002: Centralized Statistics Collection Architecture

## Status

Accepted

## Context

PANTHER framework processes high volumes of log messages across multiple features and components. Understanding logging patterns, performance characteristics, and system behavior requires comprehensive statistics collection.

Requirements:
- Real-time statistics without significant performance impact
- Configurable collection scope and detail level
- Multiple export formats for different analysis tools
- Integration with existing logging infrastructure

Constraints:
- Must not degrade logging performance by more than 5%
- Memory usage should be bounded and configurable
- Statistics collection should be optional/configurable

## Decision

Implement a layered statistics collection architecture with pluggable collectors, handlers, and analyzers.

### Architecture Layers

1. **Collection Layer** (`LogStatisticsCollector`)
   - Core statistics gathering and buffering
   - Configurable buffer sizes and retention policies
   - Real-time metric calculation

2. **Handler Layer** (`LogStatisticsHandler`, `BufferedLogStatisticsHandler`)
   - Integration with Python logging infrastructure
   - Buffered vs real-time collection strategies
   - Handler performance monitoring

3. **Analysis Layer** (`LogFeatureAnalyzer`, `LogPerformanceAnalyzer`)
   - Feature-specific analysis and reporting
   - Performance bottleneck detection
   - Trend analysis and anomaly detection

4. **Display Layer** (`LogStatisticsDisplay`, `StatisticsDisplayManager`)
   - Multiple output formats (JSON, CSV, text)
   - Real-time dashboard capabilities
   - Export and integration APIs

### Data Collection Strategy

**Buffered Collection**: Messages stored in circular buffer for analysis
```python
LogStatisticsCollector(buffer_size=1000, track_performance=True)
```

**Real-time Metrics**: Key statistics updated on each message
- Message counts by level, feature, component
- Processing times and performance metrics
- Error rates and pattern detection

**Optional Deep Analysis**: Configurable detailed tracking
- Message content analysis
- Call stack and context information
- Resource usage correlation

## Consequences

### Positive

- **Operational Visibility**: Clear insight into logging patterns and system behavior
- **Performance Monitoring**: Identify logging bottlenecks and optimization opportunities
- **Debugging Support**: Historical context for troubleshooting complex issues
- **Capacity Planning**: Data-driven decisions for log infrastructure scaling

### Negative

- **Performance Overhead**: Additional processing per log message (~2-5%)
- **Memory Usage**: Buffered messages consume additional RAM
- **Complexity**: Multiple configuration options and analysis tools

### Risk Mitigation

- **Performance Gates**: Automatic disabling if overhead exceeds thresholds
- **Bounded Memory**: Circular buffers with configurable size limits
- **Graceful Degradation**: Core logging continues if statistics fail

## Implementation Details

### Configuration Options

```python
LoggerFactory.enable_statistics({
    "enabled": True,
    "buffer_size": 1000,           # Message buffer size
    "track_performance": True,      # Enable timing metrics
    "handler_type": "buffered",     # vs "standard"
    "flush_interval": 1.0,         # Buffered handler flush frequency
    "export_formats": ["json", "csv"]  # Available export formats
})
```

### Statistics Categories

**Message Statistics**:
- Total message count
- Counts by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Counts by feature category
- Messages per time period

**Performance Statistics**:
- Handler processing times
- Message formatting overhead
- Buffer flush performance
- Export operation timing

**Feature Statistics**:
- Most active features
- Error rates by feature
- Feature-specific message patterns

### Export Formats

**JSON Export**: Machine-readable for integration
```json
{
    "collection_period": "120.5s",
    "total_messages": 1547,
    "level_counts": {"INFO": 892, "DEBUG": 421, "ERROR": 234},
    "feature_counts": {"docker_operations": 612, "event_system": 341}
}
```

**CSV Export**: Spreadsheet analysis
```csv
timestamp,level,feature,component,message_count
2024-07-05T10:30:00,INFO,docker_operations,docker_builder,156
```

**Text Export**: Human-readable reports
```
Logging Statistics Report
=========================
Collection Period: 2024-07-05 10:30:00 - 10:32:00
Total Messages: 1,547
...
```

### Integration Points

**LoggerFactory Integration**:
```python
# Automatic enablement
LoggerFactory.enable_statistics(config)

# Access statistics
stats = LoggerFactory.get_log_statistics()
report = LoggerFactory.generate_statistics_report()
```

**Handler Integration**:
```python
# Custom handler creation
handler = create_statistics_handler(
    collector,
    handler_type="buffered",
    level=logging.DEBUG
)
```

## Performance Characteristics

### Benchmarks

- **Standard Handler**: <1ms overhead per message
- **Buffered Handler**: <0.1ms overhead per message (batch processing)
- **Memory Usage**: ~1KB per 100 buffered messages
- **Export Performance**: <100ms for 10,000 message export

### Optimization Strategies

1. **Lazy Calculation**: Compute expensive metrics only when requested
2. **Circular Buffers**: Bounded memory usage with FIFO replacement
3. **Batch Processing**: Group operations for efficiency
4. **Optional Features**: Disable unused analysis components

## Monitoring and Alerting

### Health Checks

```python
# Monitor collector health
health = LoggerFactory.get_statistics_handler_stats()
if health["processing_time_ms"] > 10:
    # Alert on performance degradation
```

### Self-Monitoring

Statistics system monitors its own performance:
- Collection overhead tracking
- Buffer utilization monitoring
- Export operation performance
- Memory usage tracking

## Future Enhancements

- **Streaming Analytics**: Real-time pattern detection
- **Machine Learning**: Anomaly detection and predictive analysis
- **Distributed Collection**: Multi-process/multi-host aggregation
- **Integration APIs**: Prometheus, Grafana, ELK stack connectors

## Related Decisions

- ADR-0001: Feature-aware logging architecture (statistics categorization)
- ADR-0003: Performance optimization strategies (overhead management)

## References

- Python logging module documentation
- Time series analysis patterns
- Circular buffer implementation strategies
- Performance monitoring best practices
