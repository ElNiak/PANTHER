# Log Statistics Features - Concrete Implementation Plan

## Overview
Implement a comprehensive log statistics system that integrates with PANTHER's granular feature logging to provide real-time and post-analysis metrics about logging activity across all features and components.

## Phase 1: Core Statistics Collection Infrastructure

### 1.1 Create LogStatisticsCollector (`panther/core/utils/log_statistics_collector.py`)
```python
class LogStatisticsCollector:
    def __init__(self):
        self.stats = {
            'total_messages': 0,
            'by_level': defaultdict(int),
            'by_feature': defaultdict(int),
            'by_module': defaultdict(int),
            'by_time_interval': defaultdict(int),
            'error_patterns': defaultdict(int),
            'start_time': datetime.now(),
            'last_update': datetime.now()
        }
        self.performance_metrics = {
            'collection_overhead_ms': [],
            'buffer_usage': 0,
            'memory_usage_mb': 0
        }
    
    def record_log_message(self, record: LogRecord):
        # Track message counts, feature detection, timing
    
    def get_real_time_stats(self) -> Dict:
        # Return current statistics snapshot
    
    def generate_summary_report(self) -> Dict:
        # Generate comprehensive statistics report
```

### 1.2 Create Custom LogStatisticsHandler (`panther/core/utils/log_statistics_handler.py`)
```python
class LogStatisticsHandler(logging.Handler):
    def __init__(self, collector: LogStatisticsCollector):
        super().__init__()
        self.collector = collector
        self.feature_registry = feature_registry
    
    def emit(self, record: LogRecord):
        # Intercept log messages and collect statistics
        # Detect feature from record.name or record.pathname
        # Forward to collector for processing
        
    def flush(self):
        # Flush buffered statistics
```

### 1.3 Extend LoggerFactory with Statistics Support (`panther/core/utils/logger_factory.py`)
```python
# Add to LoggerFactory class:
@classmethod
def enable_statistics(cls, config: Dict[str, Any]) -> None:
    """Enable log statistics collection with configuration."""
    if not hasattr(cls, '_statistics_collector'):
        cls._statistics_collector = LogStatisticsCollector()
        cls._statistics_handler = LogStatisticsHandler(cls._statistics_collector)
        
        # Add statistics handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(cls._statistics_handler)

@classmethod
def get_log_statistics(cls) -> Optional[Dict]:
    """Get current log statistics if enabled."""
    if hasattr(cls, '_statistics_collector'):
        return cls._statistics_collector.get_real_time_stats()
    return None
```

### 1.4 Configuration Schema Extension (`panther/config/config_global_schema.py`)
```python
@dataclass
class LogStatisticsConfig:
    enabled: bool = False
    collection_interval: int = 10  # seconds
    buffer_size: int = 1000
    real_time_display: bool = False
    generate_reports: bool = True
    export_formats: List[str] = field(default_factory=lambda: ["json"])
    track_performance: bool = True
    track_features: bool = True
    track_modules: bool = True

@dataclass
class LoggingConfig:
    # ... existing fields ...
    statistics: Optional[LogStatisticsConfig] = None
```

## Phase 2: Real-time Display and Basic Reporting

### 2.1 Create LogStatisticsReporter (`panther/core/utils/log_statistics_reporter.py`)
```python
class LogStatisticsReporter:
    def __init__(self, collector: LogStatisticsCollector):
        self.collector = collector
        
    def print_real_time_stats(self):
        """Print live statistics to console."""
        stats = self.collector.get_real_time_stats()
        # Format and display current statistics
        
    def generate_text_report(self) -> str:
        """Generate human-readable text report."""
        
    def generate_json_report(self) -> Dict:
        """Generate JSON statistics report."""
        
    def export_to_file(self, filepath: Path, format: str = "json"):
        """Export statistics to file."""
```

### 2.2 Create Real-time Display Thread (`panther/core/utils/log_statistics_display.py`)
```python
class LogStatisticsDisplay:
    def __init__(self, collector: LogStatisticsCollector, interval: int = 10):
        self.collector = collector
        self.interval = interval
        self.running = False
        self.thread = None
        
    def start_display(self):
        """Start real-time statistics display in separate thread."""
        
    def stop_display(self):
        """Stop real-time display."""
        
    def _display_loop(self):
        """Main display loop running in separate thread."""
        while self.running:
            self._print_current_stats()
            time.sleep(self.interval)
```

### 2.3 Integration with ExperimentManager
```python
# Add to ExperimentManager:
def _setup_log_statistics(self):
    """Setup log statistics if enabled in configuration."""
    if self.config.logging.statistics and self.config.logging.statistics.enabled:
        LoggerFactory.enable_statistics(self.config.logging.statistics.__dict__)
        
        if self.config.logging.statistics.real_time_display:
            self.log_display = LogStatisticsDisplay(
                LoggerFactory._statistics_collector,
                self.config.logging.statistics.collection_interval
            )
            self.log_display.start_display()

def _generate_final_log_report(self):
    """Generate final logging statistics report."""
    if hasattr(LoggerFactory, '_statistics_collector'):
        reporter = LogStatisticsReporter(LoggerFactory._statistics_collector)
        # Generate and save final report
```

## Phase 3: Advanced Analytics and Feature Correlation

### 3.1 Feature Activity Analyzer (`panther/core/utils/log_feature_analyzer.py`)
```python
class LogFeatureAnalyzer:
    def __init__(self, collector: LogStatisticsCollector):
        self.collector = collector
        
    def analyze_feature_activity(self) -> Dict[str, Any]:
        """Analyze logging activity by feature."""
        return {
            'most_active_features': self._get_top_features_by_count(),
            'most_verbose_features': self._get_top_features_by_volume(),
            'feature_error_rates': self._calculate_feature_error_rates(),
            'feature_level_distribution': self._get_feature_level_distribution()
        }
    
    def compare_with_configuration(self, config_levels: Dict[str, str]) -> Dict:
        """Compare actual activity with configured levels."""
        
    def suggest_level_optimizations(self) -> Dict[str, str]:
        """Suggest optimal logging levels based on activity."""
```

### 3.2 Performance Impact Analyzer (`panther/core/utils/log_performance_analyzer.py`)
```python
class LogPerformanceAnalyzer:
    def __init__(self, collector: LogStatisticsCollector):
        self.collector = collector
        
    def analyze_logging_overhead(self) -> Dict[str, Any]:
        """Analyze performance impact of logging."""
        return {
            'total_overhead_ms': sum(self.collector.performance_metrics['collection_overhead_ms']),
            'average_overhead_per_message': self._calculate_avg_overhead(),
            'memory_usage_mb': self.collector.performance_metrics['memory_usage_mb'],
            'bottleneck_features': self._identify_bottlenecks()
        }
    
    def recommend_optimizations(self) -> List[str]:
        """Recommend performance optimizations."""
```

## Phase 4: CLI Integration and Export Features

### 4.1 CLI Commands (`panther/cli/commands/logs.py`)
```python
@click.group()
def logs():
    """Log analysis and statistics commands."""
    pass

@logs.command()
@click.option('--format', default='text', help='Output format (text, json, csv)')
@click.option('--feature', help='Filter by specific feature')
def stats(format, feature):
    """Display current log statistics."""
    
@logs.command()
@click.option('--config', required=True, help='Configuration file to analyze')
@click.option('--output', help='Output file for report')
def analyze(config, output):
    """Analyze logging configuration and suggest optimizations."""
    
@logs.command()
@click.option('--experiment-dir', required=True, help='Experiment output directory')
def report(experiment_dir):
    """Generate logging report from experiment output."""
```

### 4.2 Export Utilities (`panther/core/utils/log_statistics_exporter.py`)
```python
class LogStatisticsExporter:
    def __init__(self, collector: LogStatisticsCollector):
        self.collector = collector
        
    def export_csv(self, filepath: Path):
        """Export statistics as CSV."""
        
    def export_json(self, filepath: Path):
        """Export statistics as JSON."""
        
    def export_html_dashboard(self, filepath: Path):
        """Export interactive HTML dashboard."""
        
    def export_prometheus_metrics(self, filepath: Path):
        """Export in Prometheus metrics format."""
```

## Phase 5: Integration with Existing PANTHER Systems

### 5.1 Metrics Observer Integration
```python
# Extend MetricsObserver to include logging statistics
def _collect_logging_metrics(self):
    """Collect logging statistics as standard metrics."""
    if hasattr(LoggerFactory, '_statistics_collector'):
        stats = LoggerFactory._statistics_collector.get_real_time_stats()
        # Convert to standard PANTHER metrics events
```

### 5.2 Storage Observer Integration
```python
# Extend StorageObserver to store logging statistics
def _store_logging_statistics(self):
    """Store logging statistics in experiment storage."""
```

### 5.3 Configuration Examples
```yaml
# experiment-config/test_logging_with_stats.yaml
logging:
  level: INFO
  enable_colors: true
  
  statistics:
    enabled: true
    collection_interval: 5
    real_time_display: true
    generate_reports: true
    export_formats: ["json", "csv", "html"]
    track_performance: true
    
  feature_levels:
    docker_operations: DEBUG
    service_managers: TRACE
    # ... other features
```

## Implementation Order and Dependencies

### **Week 1: Core Infrastructure**
1. LogStatisticsCollector basic implementation
2. LogStatisticsHandler custom handler
3. LoggerFactory integration
4. Configuration schema updates
5. Basic unit tests

### **Week 2: Real-time Features**
1. LogStatisticsReporter implementation
2. Real-time display system
3. ExperimentManager integration
4. End-to-end testing with simple scenarios

### **Week 3: Advanced Analytics**
1. LogFeatureAnalyzer implementation
2. LogPerformanceAnalyzer implementation
3. Feature correlation and optimization suggestions
4. Comprehensive testing with all logging scenarios

### **Week 4: CLI and Export Features**
1. CLI commands implementation
2. Export utilities (CSV, JSON, HTML)
3. Integration with existing PANTHER systems
4. Documentation and examples
5. Performance optimization and final testing

## Success Metrics

### **Functional Requirements**
- ✅ Real-time logging statistics display during experiments
- ✅ Comprehensive post-experiment logging reports
- ✅ Feature-specific activity analysis
- ✅ Performance impact measurement
- ✅ Configuration optimization recommendations

### **Performance Requirements**
- < 5% overhead when statistics enabled
- < 1MB memory usage for typical experiments
- Real-time updates every 5-10 seconds
- Export reports in < 5 seconds

### **Integration Requirements**
- Seamless integration with existing logging system
- Backward compatibility with all current configurations
- CLI commands follow existing PANTHER patterns
- Statistics available via standard metrics system

## Key Features Summary

### **Real-time Statistics**
- Messages per second by feature
- Error rate trends
- Most active modules
- Memory usage by logging
- Feature-specific verbosity levels

### **Post-Experiment Analysis**
- Total messages by feature/level
- Logging overhead analysis  
- Error distribution and patterns
- Feature activity comparison
- Performance impact assessment

### **Configuration-driven Control**
- Enable/disable statistics collection
- Configurable collection intervals
- Multiple export formats
- Real-time display options
- Performance tracking settings

This concrete plan provides a step-by-step implementation approach with specific code structures, integration points, and measurable success criteria.