# Contributing to PANTHER Core Utilities

## Welcome Contributors

We welcome contributions to PANTHER's core utilities! This module provides the foundation for feature-aware logging across the entire PANTHER framework, so quality and reliability are paramount.

## Development Setup

### Prerequisites

- Python 3.10+
- Git for version control
- Understanding of Python logging module
- Basic knowledge of software testing

### Local Environment Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ElNiak/PANTHER.git
   cd panther/panther/core/utils
   ```

2. **Install Development Dependencies**:
   ```bash
   pip install -e ".[tests,lint]"
   ```

3. **Verify Installation**:
   ```bash
   python -c "from panther.core.utils import LoggerFactory; print('Setup successful')"
   ```

## Code Standards

### Code Style

We follow strict code quality standards to ensure maintainability and reliability.

#### Python Code Style
- **Formatter**: Black with 88-character line limit
- **Linter**: Flake8 with custom configuration
- **Type Checking**: MyPy for all public APIs
- **Import Sorting**: isort with profile "black"

#### Example Configuration
```python
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 88

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Documentation Standards

#### Docstring Requirements
All public functions and classes must have comprehensive docstrings following Google style:

```python
def example_function(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """Brief description under 72 characters.

    Detailed explanation of the function's purpose, behavior, and any
    important implementation details or constraints.

    Args:
        param1: Description of the first parameter
        param2: Description of optional parameter with default value

    Returns:
        Dictionary containing result data with specific structure

    Raises:
        ValueError: When param1 is empty or invalid
        RuntimeError: When system resources are unavailable

    Examples:
        >>> result = example_function("test", 42)
        >>> assert "status" in result
        >>> assert result["status"] == "success"
    """
    # Implementation here
```

#### Documentation Files
- Use present tense only (no "will", "shall", "going to")
- Follow Diátaxis structure (Tutorial, How-to, Reference, Explanation)
- Include runnable examples that pass doctest
- Maximum line length: 120 characters

### Testing Requirements

#### Test Coverage
- Minimum 80% code coverage for all new code
- 90% coverage for critical logging infrastructure
- 100% coverage for public API methods

#### Test Categories
1. **Unit Tests**: Individual function/method testing
2. **Integration Tests**: Component interaction testing
3. **Performance Tests**: Benchmarking and regression detection
4. **Documentation Tests**: Doctest validation

#### Example Test Structure
```python
import pytest
from unittest.mock import Mock, patch
from panther.core.utils import LoggerFactory, FeatureLoggerMixin

class TestLoggerFactory:
    """Test suite for LoggerFactory functionality."""

    def test_initialization_basic(self):
        """Test basic factory initialization."""
        config = {"level": "INFO", "enable_colors": True}
        LoggerFactory.initialize(config)

        assert LoggerFactory._initialized is True
        assert LoggerFactory._config["level"] == "INFO"

    def test_get_logger_feature_detection(self):
        """Test automatic feature detection for loggers."""
        LoggerFactory.initialize({"level": "DEBUG"})

        # Test known pattern
        logger = LoggerFactory.get_logger("docker_builder")
        # Feature detection should categorize this appropriately
        # Implementation-specific assertions here

    @pytest.mark.performance
    def test_logger_creation_performance(self):
        """Test logger creation performance meets requirements."""
        import time

        LoggerFactory.initialize({"level": "INFO"})

        start = time.time()
        for i in range(1000):
            LoggerFactory.get_logger(f"test_logger_{i}")
        duration = time.time() - start

        # Should create 1000 loggers in under 100ms
        assert duration < 0.1, f"Logger creation too slow: {duration:.3f}s"
```

## Contribution Workflow

### 1. Issue Identification

Before starting work, ensure there's a clear issue to address:

#### Bug Reports
Include:
- Python version and environment details
- PANTHER version
- Minimal reproduction code
- Expected vs actual behavior
- Error messages with full stack traces

#### Feature Requests
Include:
- Clear use case description
- Proposed API design
- Performance implications
- Backward compatibility considerations

### 2. Development Process

#### Branch Strategy
```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b bugfix/issue-number-description
```

#### Development Cycle
1. **Write Tests First**: Follow TDD when possible
2. **Implement Feature**: Write minimal code to pass tests
3. **Add Documentation**: Update relevant docs
4. **Performance Check**: Run benchmarks for performance-sensitive changes
5. **Integration Test**: Test with broader PANTHER framework

#### Code Quality Checks
```bash
# Format code
black panther/core/utils/

# Check linting
flake8 panther/core/utils/

# Type checking
mypy panther/core/utils/

# Run tests
pytest panther/core/utils/ --cov=panther.core.utils --cov-report=html

# Check documentation
python -m doctest panther/core/utils/*.py -v
```

### 3. Pull Request Process

#### Before Submitting
- [ ] All tests pass locally
- [ ] Code coverage meets requirements (80%+)
- [ ] Documentation updated
- [ ] Performance benchmarks run (if applicable)
- [ ] CHANGELOG.md updated

#### Pull Request Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing API)
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Performance tests run (if applicable)
- [ ] Documentation examples verified

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests provide adequate coverage
- [ ] Performance impact assessed
```

#### Review Process
1. **Automated Checks**: CI pipeline runs all validation
2. **Code Review**: Maintainer review focusing on:
   - Code quality and architecture
   - Test completeness
   - Documentation accuracy
   - Performance implications
3. **Testing**: Reviewer tests changes in different environments
4. **Approval**: Two approvals required for significant changes

### 4. Specific Contribution Areas

#### Adding New Features

##### Feature Detection Patterns
When adding new feature detection patterns:

```python
# In feature_registry.py or LoggerFactory.FEATURE_MAPPINGS
NEW_FEATURE_PATTERNS = {
    "new_feature_category": [
        "pattern1", "pattern2", "keyword"
    ]
}

# Add comprehensive tests
def test_new_feature_detection():
    """Test detection of new feature category."""
    test_cases = [
        ("component_with_pattern1", "new_feature_category"),
        ("pattern2_service", "new_feature_category"),
        ("unrelated_component", None)  # Should not match
    ]

    for component_name, expected_feature in test_cases:
        detected = LoggerFactory._detect_feature_from_name(component_name)
        assert detected == expected_feature
```

##### Statistics Collection
When extending statistics collection:

```python
class CustomStatisticsCollector(LogStatisticsCollector):
    """Custom collector with additional metrics."""

    def collect_message(self, record: logging.LogRecord) -> None:
        """Override to add custom metric collection."""
        super().collect_message(record)

        # Add custom metrics
        self.custom_metrics[record.levelname] += 1

    def get_custom_stats(self) -> Dict[str, Any]:
        """Get custom statistics."""
        return {
            "custom_metric": self.custom_metrics,
            "derived_metric": self._calculate_derived_metric()
        }
```

#### Performance Optimizations

All performance changes must include benchmarks:

```python
# Include performance test
@pytest.mark.performance
def test_optimization_performance():
    """Verify performance improvement from optimization."""
    # Measure before optimization (baseline)
    baseline_time = measure_baseline_performance()

    # Measure after optimization
    optimized_time = measure_optimized_performance()

    # Verify improvement
    improvement = (baseline_time - optimized_time) / baseline_time
    assert improvement > 0.1, f"Expected >10% improvement, got {improvement:.1%}"
```

#### Documentation Improvements

Documentation contributions are valuable and welcomed:

- **Tutorials**: Step-by-step learning content
- **How-to Guides**: Problem-solving recipes
- **API Reference**: Complete method documentation
- **Examples**: Real-world usage patterns

## Testing Guidelines

### Test Organization

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_logger_factory.py
│   ├── test_feature_logger_mixin.py
│   └── test_statistics_collector.py
├── integration/             # Integration tests
│   ├── test_full_workflow.py
│   └── test_framework_integration.py
├── performance/             # Performance benchmarks
│   ├── test_initialization_performance.py
│   └── test_throughput_benchmarks.py
└── conftest.py             # Shared test configuration
```

### Test Data and Fixtures

```python
# conftest.py
import pytest
from panther.core.utils import LoggerFactory

@pytest.fixture
def clean_logger_factory():
    """Provide clean LoggerFactory state for tests."""
    # Reset factory state
    LoggerFactory._initialized = False
    LoggerFactory._config = {}
    LoggerFactory._feature_levels = {}
    LoggerFactory._handler_cache = {}

    yield LoggerFactory

    # Cleanup after test
    LoggerFactory.disable_statistics()

@pytest.fixture
def sample_config():
    """Provide standard test configuration."""
    return {
        "level": "DEBUG",
        "format": "%(asctime)s [%(levelname)s] - %(name)s - %(message)s",
        "enable_colors": False  # Avoid color codes in test output
    }
```

### Performance Testing

```python
import time
import pytest
from panther.core.utils import LoggerFactory

@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks for regression detection."""

    def test_logger_creation_speed(self, clean_logger_factory, sample_config):
        """Logger creation should be fast enough for production use."""
        LoggerFactory.initialize(sample_config)

        start = time.time()
        loggers = []
        for i in range(1000):
            logger = LoggerFactory.get_logger(f"benchmark_{i}")
            loggers.append(logger)
        duration = time.time() - start

        # Should create 1000 loggers in under 50ms
        assert duration < 0.05, f"Logger creation too slow: {duration:.3f}s"

        # Verify all loggers are functional
        for logger in loggers[:10]:  # Test first 10
            logger.info("Performance test message")
```

## Release Process

### Version Management

We follow semantic versioning (SemVer):

- **MAJOR**: Breaking changes to public API
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Checklist

1. **Pre-release Testing**:
   ```bash
   # Run full test suite
   pytest --cov=panther.core.utils --cov-report=html

   # Performance regression check
   python benchmarks/performance_suite.py

   # Documentation validation
   mkdocs build --strict
   ```

2. **Version Update**:
   ```bash
   # Update version in __init__.py
   __version__ = "1.2.3"

   # Update CHANGELOG.md
   # Add release notes
   ```

3. **Release Notes**: Include:
   - New features and improvements
   - Bug fixes
   - Performance improvements
   - Breaking changes (if any)
   - Migration instructions

## Communication

### Getting Help

- **Documentation**: Start with [README](README.md) and [API Reference](api_reference.md)
- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and design discussions
- **Code Review**: For feedback on implementation approaches

### Community Guidelines

- **Be Respectful**: Treat all community members with respect
- **Be Constructive**: Provide helpful feedback and suggestions
- **Be Patient**: Maintainers are volunteers balancing multiple priorities
- **Be Thorough**: Provide complete information in issues and PRs

## Recognition

Contributors are recognized in:

- **CHANGELOG.md**: Credit for each contribution
- **GitHub Contributors**: Automatic recognition
- **Documentation**: Major contributors acknowledged

We appreciate all contributions, from code to documentation to bug reports. Every contribution helps make PANTHER better for everyone!

## Questions?

Don't hesitate to ask questions:

- Open a GitHub Discussion for design questions
- Comment on relevant issues for clarification
- Include questions in your pull request description

Welcome to the PANTHER community! 🎉
