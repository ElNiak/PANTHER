# PANTHER CLI - Developer Guide

Development setup, testing, debugging, and contribution guidelines for the PANTHER CLI module.

## Development Environment Setup

### Prerequisites

- Python 3.8+ with development headers
- argcomplete for bash completion testing
- Terminal with color support (recommended)
- IDE with Python language server support

### Local Setup

```bash
# Install CLI development dependencies
pip install -e ".[dev,cli]"

# Install argcomplete for testing bash completion
pip install argcomplete

# Enable bash completion for development
eval "$(register-python-argcomplete panther)"

# Verify CLI installation
panther --version
panther --help
```

### IDE Configuration for CLI Development

#### VS Code Extensions
```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.pylint",
        "ms-python.black-formatter",
        "redhat.vscode-yaml",
        "yzhang.markdown-all-in-one"
    ]
}
```

#### CLI-Specific Settings
```json
{
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.defaultProfile.osx": "bash",
    "yaml.schemas": {
        "./schema/experiment.json": "**/*experiment*.yaml",
        "./schema/global.json": "**/*global*.yaml"
    }
}
```

## Running and Testing CLI Commands

### Local Development Testing

```bash
# Test basic CLI functionality
python -m panther --help
python -m panther run --help

# Test with sample configurations
python -m panther config validate --config tests/fixtures/valid_config.yaml
python -m panther plugins list --format json

# Test interactive features
python -m panther config design --output test_config.yaml
python -m panther tutorial run basic
```

### Debug Mode Testing

```bash
# Enable debug mode for detailed output
export PANTHER_DEBUG=1
python -m panther run --debug --config test_config.yaml

# Test error handling
python -m panther config validate --config tests/fixtures/invalid_config.yaml --debug

# Interactive debugging
python -c "
import pdb; pdb.set_trace()
from panther.cli.main import main
main(['run', '--help'])
"
```

### CLI Integration Testing

```bash
# Run CLI-specific tests
python -m pytest tests/cli/ -v

# Test bash completion
source <(python -m panther --completion bash)
python -m panther plugins <TAB><TAB>

# Test different output formats
python -m panther plugins list --format table
python -m panther plugins list --format json
python -m panther plugins list --format yaml
```

## CLI Architecture Deep Dive

### Command Registration Pattern

```python
# Pattern used in all subcommands
class MyCommand(BaseCommand):
    """Command description for help text."""

    @classmethod
    def register_parser(cls, subparsers) -> ArgumentParser:
        """Register command arguments and options."""
        parser = subparsers.add_parser(
            'mycommand',
            help='Brief help text',
            description=cls.__doc__,
            formatter_class=RawDescriptionHelpFormatter
        )

        # Add arguments
        parser.add_argument('--option', help='Option description')
        parser.set_defaults(func=cls.handle)
        return parser

    @classmethod
    def handle(cls, args) -> int:
        """Execute the command logic."""
        try:
            # Command implementation
            result = perform_operation(args)
            print(f"✅ Success: {result}")
            return 0
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
```

### Error Handling Strategy

```python
# Consistent error handling pattern
def handle_cli_errors(func):
    """Decorator for consistent CLI error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n⚠️  Operation cancelled by user")
            return 130
        except FileNotFoundError as e:
            print(f"❌ File not found: {e}")
            return 2
        except ValidationError as e:
            print(f"❌ Validation error: {e}")
            if hasattr(e, 'suggestions'):
                print(f"💡 Suggestion: {e.suggestions}")
            return 1
        except Exception as e:
            if os.getenv('PANTHER_DEBUG'):
                import traceback
                traceback.print_exc()
            else:
                print(f"❌ Unexpected error: {e}")
                print("💡 Run with --debug for more details")
            return 1
    return wrapper
```

### Interactive Component Development

```python
# Interactive CLI component pattern
class ConfigurationBuilder:
    """Interactive configuration builder."""

    def __init__(self):
        self.state = {}
        self.validators = {}

    def prompt_section(self, section_name: str, schema: dict):
        """Prompt user for configuration section."""
        print(f"\n📋 Configuring {section_name}")

        for field, field_schema in schema.items():
            value = self._prompt_field(field, field_schema)
            self.state[section_name][field] = value

    def _prompt_field(self, field: str, schema: dict):
        """Prompt for individual field with validation."""
        prompt = f"{field}"
        if 'description' in schema:
            prompt += f" ({schema['description']})"
        if 'default' in schema:
            prompt += f" [{schema['default']}]"
        prompt += ": "

        while True:
            value = input(prompt)
            if not value and 'default' in schema:
                return schema['default']

            try:
                validated = self._validate_field(value, schema)
                return validated
            except ValidationError as e:
                print(f"❌ {e}")
                continue
```

## Testing CLI Components

### Unit Testing CLI Commands

```python
import pytest
from unittest.mock import Mock, patch
from panther.cli.subcommands.plugins import PluginsCommand

class TestPluginsCommand:
    """Test suite for plugins command."""

    def test_list_command_basic(self, capsys):
        """Test basic plugin listing."""
        args = Mock(format='table', type=None)

        with patch('panther.plugins.plugin_manager.PluginManager') as mock_manager:
            mock_manager.return_value.discover_plugins.return_value = {
                'picoquic': Mock(name='picoquic', version='1.0.0')
            }

            result = PluginsCommand.handle(args)

            assert result == 0
            captured = capsys.readouterr()
            assert 'picoquic' in captured.out

    def test_list_command_json_format(self, capsys):
        """Test JSON output format."""
        args = Mock(format='json', type=None)

        with patch('panther.plugins.plugin_manager.PluginManager') as mock_manager:
            mock_manager.return_value.discover_plugins.return_value = {}

            result = PluginsCommand.handle(args)

            assert result == 0
            captured = capsys.readouterr()
            # Should be valid JSON
            import json
            json.loads(captured.out)
```

### Integration Testing

```python
import subprocess
import tempfile
from pathlib import Path

class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_config_validate_valid_file(self):
        """Test config validation with valid file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
            f.write("""
            experiment:
              name: test_experiment
              protocol: quic
              test_cases:
                - name: basic_test
                  implementation: picoquic
            """)
            f.flush()

            result = subprocess.run([
                'python', '-m', 'panther', 'config', 'validate',
                '--config', f.name
            ], capture_output=True, text=True)

            assert result.returncode == 0
            assert '✅' in result.stdout

    def test_config_validate_invalid_file(self):
        """Test config validation with invalid file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
            f.write("invalid: yaml: content:")
            f.flush()

            result = subprocess.run([
                'python', '-m', 'panther', 'config', 'validate',
                '--config', f.name
            ], capture_output=True, text=True)

            assert result.returncode != 0
            assert '❌' in result.stdout
```

### Interactive Testing

```python
import pytest
from unittest.mock import patch
from panther.cli.interactive.experiment_designer import ExperimentDesigner

class TestInteractiveComponents:
    """Test interactive CLI components."""

    @patch('builtins.input')
    def test_experiment_designer_basic_flow(self, mock_input):
        """Test basic experiment design flow."""
        mock_input.side_effect = [
            'test_experiment',  # experiment name
            'quic',            # protocol
            'picoquic',        # implementation
            'yes'              # confirm
        ]

        designer = ExperimentDesigner()
        config = designer.design_experiment()

        assert config['experiment']['name'] == 'test_experiment'
        assert config['experiment']['protocol'] == 'quic'

    @patch('builtins.input')
    def test_validation_helper_error_explanation(self, mock_input):
        """Test validation error explanation."""
        from panther.cli.interactive.validation_helper import ValidationHelper

        helper = ValidationHelper()
        explanation = helper.explain_error('missing_required_field', 'name')

        assert 'required' in explanation.lower()
        assert 'name' in explanation
        assert len(explanation) > 50  # Should be detailed
```

## Debugging CLI Issues

### Common CLI Problems

#### Argument Parsing Issues

```bash
# Debug argument parsing
python -c "
from panther.cli.main import create_parser
parser = create_parser()
args = parser.parse_args(['run', '--config', 'test.yaml', '--debug'])
print(f'Parsed args: {args}')
"

# Test subcommand registration
python -c "
from panther.cli.main import create_parser
parser = create_parser()
parser.print_help()
"
```

#### Interactive Component Debugging

```python
# Debug interactive prompts
import sys
from io import StringIO
from panther.cli.interactive.experiment_designer import ExperimentDesigner

# Simulate user input
test_input = "test_experiment\nquic\npicoquic\nyes\n"
sys.stdin = StringIO(test_input)

designer = ExperimentDesigner()
try:
    config = designer.design_experiment()
    print(f"Generated config: {config}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

#### Output Formatting Debugging

```bash
# Test different output formats
python -m panther plugins list --format table --debug
python -m panther plugins list --format json --debug
python -m panther plugins list --format yaml --debug

# Test color output
FORCE_COLOR=1 python -m panther plugins list
NO_COLOR=1 python -m panther plugins list
```

### Performance Profiling

```bash
# Profile CLI startup time
time python -m panther --help

# Profile command execution
python -m cProfile -o cli_profile.stats -m panther plugins list
python -c "
import pstats
stats = pstats.Stats('cli_profile.stats')
stats.sort_stats('cumulative').print_stats(20)
"

# Memory profiling
python -m memory_profiler -m panther plugins list
```

## Contributing New CLI Commands

### Command Development Checklist

1. **Design Phase**
   - [ ] Define command purpose and scope
   - [ ] Design argument structure
   - [ ] Plan error handling strategy
   - [ ] Consider interactive vs. batch modes

2. **Implementation Phase**
   - [ ] Create command module in `subcommands/`
   - [ ] Inherit from `BaseCommand`
   - [ ] Implement `register_parser()` method
   - [ ] Implement `handle()` method with error handling
   - [ ] Add comprehensive docstrings

3. **Testing Phase**
   - [ ] Write unit tests for command logic
   - [ ] Write integration tests for CLI interface
   - [ ] Test error conditions and edge cases
   - [ ] Test help text and argument parsing

4. **Documentation Phase**
   - [ ] Update CLI module README
   - [ ] Add command examples
   - [ ] Document any new features or patterns

### Example: Adding a New Command

```python
# File: panther/cli/subcommands/analyze.py
from argparse import ArgumentParser, _SubParsersAction
from panther.cli.base import BaseCommand

class AnalyzeCommand(BaseCommand):
    """Analyze experiment results and generate reports.

    This command provides various analysis tools for experiment results,
    including statistical analysis, performance metrics, and comparison
    reports between different experiments.

    Examples:
        panther analyze results --experiment exp_20231201 --format html
        panther analyze compare --experiment1 exp1 --experiment2 exp2
        panther analyze trends --experiments exp* --metric latency
    """

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the analyze command parser."""
        parser = subparsers.add_parser(
            'analyze',
            help='Analyze experiment results',
            description=cls.__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        # Subcommands for different analysis types
        analyze_subparsers = parser.add_subparsers(
            dest='analyze_command',
            help='Analysis commands'
        )

        # Results analysis
        results_parser = analyze_subparsers.add_parser(
            'results',
            help='Analyze single experiment results'
        )
        results_parser.add_argument(
            '--experiment',
            required=True,
            help='Experiment name or path'
        )
        results_parser.add_argument(
            '--format',
            choices=['html', 'json', 'text'],
            default='html',
            help='Output format'
        )

        # Comparison analysis
        compare_parser = analyze_subparsers.add_parser(
            'compare',
            help='Compare multiple experiments'
        )
        compare_parser.add_argument(
            '--experiments',
            nargs='+',
            required=True,
            help='Experiments to compare'
        )

        parser.set_defaults(func=cls.handle)
        return parser

    @classmethod
    def handle(cls, args) -> int:
        """Handle the analyze command."""
        try:
            if args.analyze_command == 'results':
                return cls._handle_results(args)
            elif args.analyze_command == 'compare':
                return cls._handle_compare(args)
            else:
                print("❌ No analysis command specified")
                return 1

        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            if os.getenv('PANTHER_DEBUG'):
                import traceback
                traceback.print_exc()
            return 1

    @classmethod
    def _handle_results(cls, args) -> int:
        """Handle results analysis."""
        from panther.analysis.experiment_analyzer import ExperimentAnalyzer

        print(f"🔍 Analyzing experiment: {args.experiment}")

        analyzer = ExperimentAnalyzer(args.experiment)
        report = analyzer.generate_report(format=args.format)

        print(f"✅ Analysis complete: {report.output_path}")
        return 0

    @classmethod
    def _handle_compare(cls, args) -> int:
        """Handle comparison analysis."""
        from panther.analysis.experiment_comparator import ExperimentComparator

        print(f"🔍 Comparing {len(args.experiments)} experiments")

        comparator = ExperimentComparator(args.experiments)
        comparison = comparator.compare()

        print(f"✅ Comparison complete: {comparison.summary}")
        return 0
```

### Register New Command

```python
# File: panther/cli/subcommands/__init__.py
from .analyze import AnalyzeCommand  # Add import
from .run import RunCommand
from .config import ConfigCommand
# ... other imports

# Update __all__ list
__all__ = [
    'AnalyzeCommand',  # Add to exports
    'RunCommand',
    'ConfigCommand',
    # ... other commands
]
```

```python
# File: panther/cli/main.py
from panther.cli.subcommands import (
    AnalyzeCommand,  # Add import
    RunCommand,
    ConfigCommand,
    # ... other imports
)

def create_parser():
    """Create and configure the main argument parser."""
    # ... existing code ...

    # Register commands
    AnalyzeCommand.register_parser(subparsers)  # Add registration
    RunCommand.register_parser(subparsers)
    ConfigCommand.register_parser(subparsers)
    # ... other registrations
```

## Advanced CLI Features

### Custom Output Formatters

```python
# Custom formatter for specialized output
class MetricsFormatter:
    """Custom formatter for metrics output."""

    @staticmethod
    def format_table(metrics: dict) -> str:
        """Format metrics as ASCII table."""
        from tabulate import tabulate

        rows = []
        for name, value in metrics.items():
            rows.append([name, value['current'], value['average']])

        return tabulate(
            rows,
            headers=['Metric', 'Current', 'Average'],
            tablefmt='grid'
        )

    @staticmethod
    def format_json(metrics: dict) -> str:
        """Format metrics as JSON."""
        import json
        return json.dumps(metrics, indent=2)

    @staticmethod
    def format_prometheus(metrics: dict) -> str:
        """Format metrics in Prometheus format."""
        output = []
        for name, value in metrics.items():
            output.append(f"panther_{name} {value['current']}")
        return '\n'.join(output)
```

### Bash Completion Enhancement

```python
# Enhanced completion for dynamic values
def plugin_name_completer(prefix, **kwargs):
    """Complete plugin names dynamically."""
    from panther.plugins.plugin_manager import PluginManager

    manager = PluginManager()
    plugins = manager.discover_plugins()

    return [name for name in plugins.keys() if name.startswith(prefix)]

# Register completion
import argcomplete
parser.add_argument(
    '--plugin',
    help='Plugin name'
).completer = plugin_name_completer
```

### Configuration Validation Integration

```python
# CLI-specific validation helpers
class CLIValidationHelper:
    """Helper for CLI-specific validation tasks."""

    @staticmethod
    def validate_experiment_config(config_path: str) -> tuple[bool, list]:
        """Validate experiment configuration with CLI-friendly output."""
        errors = []

        try:
            config = load_config(config_path)
            validator = ExperimentConfigValidator()
            validator.validate(config)
            return True, []

        except ValidationError as e:
            return False, [str(e)]
        except Exception as e:
            return False, [f"Unexpected error: {e}"]

    @staticmethod
    def suggest_fixes(errors: list) -> list:
        """Suggest fixes for common validation errors."""
        suggestions = []

        for error in errors:
            if 'required field' in error.lower():
                suggestions.append("Add missing required fields")
            elif 'invalid plugin' in error.lower():
                suggestions.append("Check plugin name and availability")
            # ... more suggestions

        return suggestions
```

## Performance Optimization

### CLI Startup Optimization

```python
# Lazy loading pattern for CLI
class LazyModule:
    """Lazy loading wrapper for heavy modules."""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self._module = None

    def __getattr__(self, name):
        if self._module is None:
            self._module = __import__(self.module_name, fromlist=[name])
        return getattr(self._module, name)

# Use in CLI modules
plugin_manager = LazyModule('panther.plugins.plugin_manager')
```

### Caching CLI Data

```python
# Cache expensive operations
import functools
import time

@functools.lru_cache(maxsize=1)
def get_plugin_list_cached():
    """Cached plugin discovery for CLI."""
    from panther.plugins.plugin_manager import PluginManager

    manager = PluginManager()
    return manager.discover_plugins()

# Cache with TTL
class TTLCache:
    def __init__(self, ttl: int = 300):  # 5 minutes
        self.ttl = ttl
        self.cache = {}

    def get(self, key: str, factory_func):
        now = time.time()
        if key in self.cache:
            value, timestamp = self.cache[key]
            if now - timestamp < self.ttl:
                return value

        value = factory_func()
        self.cache[key] = (value, now)
        return value
```

## Quality Assurance

### CLI Testing Best Practices

1. **Test All Output Formats**: Ensure JSON, YAML, and table formats work correctly
2. **Test Error Conditions**: Verify proper error messages and exit codes
3. **Test Interactive Flows**: Mock user input for interactive commands
4. **Test Help Text**: Ensure all help text is accurate and helpful
5. **Test Completion**: Verify bash completion works for all commands

### Code Quality Standards

```bash
# Lint CLI code
pylint panther/cli/

# Check type hints
mypy panther/cli/

# Test CLI documentation
python -m doctest panther/cli/subcommands/*.py

# Check argument parsing
python -m panther --help | grep -E "usage:|error:"
```

### User Experience Testing

```bash
# Test user workflows
python scripts/test_cli_ux.py

# Measure CLI responsiveness
time python -m panther plugins list >/dev/null

# Test error message quality
python -m panther config validate --config nonexistent.yaml
```

This comprehensive developer guide provides everything needed to develop, test, and contribute to the PANTHER CLI module, following modern CLI development best practices and maintaining consistency with the overall PANTHER framework architecture.
