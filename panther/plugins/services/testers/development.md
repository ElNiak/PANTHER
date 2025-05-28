# Tester Plugin Development Guide

This guide provides detailed instructions for creating new tester plugins for the PANTHER framework. Tester plugins are responsible for validating the behavior of implementations under test (IUTs).

## Tester Plugin Architecture

Tester plugins are located in the services/testers directory:

```
plugins/services/testers/
├── panther_ivy/
├── __init__.py
└── ...
```

<!-- src: /panther/plugins/services/services_interface.py -->

## Core Tester Interface

All tester plugins must implement the services interface with specialized behavior for testing:

```python
from panther.plugins.services.services_interface import ServiceInterface

class TesterInterface(ServiceInterface):
    """Interface for tester plugins."""
    
    def initialize(self, config):
        """Initialize the tester with configuration."""
        pass
        
    def execute(self):
        """Execute the tests."""
        pass
    
    def get_test_results(self):
        """Get the results of the tests."""
        pass
    
    def cleanup(self):
        """Clean up resources."""
        pass
```

## Creating a New Tester Plugin

### 1. Set Up the Plugin Directory

Create a directory for your tester in the appropriate location:

```
plugins/services/testers/<tester_name>/
├── __init__.py
├── plugin.py           # Main tester implementation
├── config_schema.py    # Configuration schema
├── README.md           # Tester documentation
└── tests/              # Tester tests
    └── test_plugin.py
```

### 2. Implement the Tester Interface

Create a class that implements the ServiceInterface with testing functionality:

```python
# plugins/services/testers/<tester_name>/plugin.py
from panther.plugins.services.services_interface import ServiceInterface

class MyTester(ServiceInterface):
    """My custom tester implementation."""
    
    def initialize(self, config):
        """Initialize the tester with configuration."""
        self.config = config
        self.test_results = {}
        # Tester initialization
        
    def execute(self):
        """Execute the tests."""
        # Test execution logic
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        # Execute tests and collect results
        # ...
        
        return self.test_results
    
    def get_test_results(self):
        """Get the results of the tests."""
        return self.test_results
        
    def cleanup(self):
        """Clean up resources."""
        # Release resources, close connections, etc.
        pass
```

### 3. Define Configuration Schema

Create a schema for your tester's configuration:

```python
# plugins/services/testers/<tester_name>/config_schema.py
from panther.core.config.schema import Schema, Optional, And, Or

# Define the configuration schema
schema = Schema({
    "test_suite": str,  # Name of the test suite to run
    Optional("timeout_seconds"): And(int, lambda n: n > 0),
    Optional("max_iterations"): And(int, lambda n: n > 0),
    # Tester-specific parameters
})
```

### 4. Register Your Tester Plugin

Make your tester discoverable by updating your `__init__.py`:

```python
# plugins/services/testers/<tester_name>/__init__.py
from .plugin import MyTester

__all__ = ["MyTester"]
```

### 5. Create Tests

Write tests to verify your tester functions correctly:

```python
# plugins/services/testers/<tester_name>/tests/test_plugin.py
import pytest
from panther.plugins.services.testers.<tester_name>.plugin import MyTester

def test_tester_initialization():
    tester = MyTester()
    config = {"test_suite": "basic"}
    tester.initialize(config)
    # Assert expected initialization behavior
    
def test_tester_execution():
    tester = MyTester()
    tester.initialize({"test_suite": "basic"})
    results = tester.execute()
    # Assert test execution and results collection
```

### 6. Document Your Tester

Create a README.md file using the [plugin template](panther/plugins/plugin_template.md) that includes:

- Tester purpose and capabilities
- Supported test types and methodologies
- Configuration options
- Usage examples with different IUTs
- Test result interpretation
- Extension points

## Best Practices for Tester Plugins

1. **Detailed Results**: Provide comprehensive test results with clear pass/fail indicators
2. **Reproducibility**: Ensure tests are reproducible with the same configuration
3. **Independence**: Minimize dependencies on specific IUT implementations
4. **Timeout Handling**: Properly handle test timeouts and failures
5. **Progressive Testing**: Support incremental testing with early termination on failure

## Integration with IUTs

Tester plugins should:

1. **Discover IUTs**: Dynamically identify the IUT they're testing
2. **Configure Tests**: Adjust test parameters based on IUT capabilities
3. **Report Results**: Provide detailed results specific to the IUT

## Documentation Verification

Ensure all tester documentation includes source references:

```markdown
The panther_ivy tester supports formal verification of QUIC implementations.
<!-- src: /panther/plugins/services/testers/panther_ivy/plugin.py:45-50 -->
```
