# ADR-0003: Interactive Component Architecture

## Status

Accepted

## Date

2023-12-01

## Context

Protocol testing requires complex configuration that can be overwhelming for new users. The PANTHER CLI needs interactive components that:

- **Guide new users** through configuration creation
- **Validate input** at each step to prevent errors
- **Provide contextual help** and suggestions
- **Support different user expertise levels** (novice to expert)
- **Integrate seamlessly** with non-interactive workflows

Traditional approaches have limitations:
- **Static templates** don't adapt to user choices
- **Configuration files** require deep domain knowledge
- **Documentation** becomes quickly outdated
- **Trial-and-error** leads to frustration

## Decision

Implement a modular interactive component architecture with:

1. **State Machine-Based Wizards** for multi-step processes
2. **Validation-First Design** preventing invalid configurations
3. **Progressive Disclosure** adapting to user expertise
4. **Builder Pattern** for modular configuration assembly
5. **Escape Hatches** for expert users and automation

### Core Components

```python
# State machine for complex workflows
class ExperimentDesigner:
    def __init__(self):
        self.state = 'initial'
        self.config = {}
        self.context = {}

    def design_experiment(self) -> dict:
        """Main wizard flow"""
        self.gather_basic_info()
        self.select_protocol()
        self.configure_implementation()
        self.setup_tests()
        self.review_and_confirm()
        return self.config

# Modular builders for sections
class GlobalConfigBuilder:
    def build_section(self, existing_config: dict) -> dict:
        """Interactive builder for global configuration"""

# Enhanced validation with helpful errors
class ValidationHelper:
    def explain_error(self, error_type: str, context: str) -> str:
        """Provide detailed explanation and suggestions"""
```

### Integration Pattern

Interactive components integrate with CLI commands:

```python
class ConfigCommand(BaseCommand):
    @classmethod
    def handle(cls, args):
        if args.config_action == 'design':
            designer = ExperimentDesigner()
            config = designer.design_experiment()
            save_config(config, args.output)
            return 0
```

## Consequences

### Positive

- **Lower Barrier to Entry**: New users can create valid configurations without deep knowledge
- **Error Prevention**: Validation at each step prevents invalid configurations
- **Learning Tool**: Interactive process teaches PANTHER concepts
- **Consistency**: Generated configurations follow best practices
- **Flexibility**: Can start from existing configurations or templates

### Negative

- **Development Complexity**: More complex than static configuration
- **Testing Challenges**: Interactive components harder to test
- **Maintenance Overhead**: Need to update for new features/plugins
- **Terminal Dependencies**: Requires interactive terminal support

### Mitigation Strategies

1. **Modular Design**: Independent builders reduce complexity
2. **Mock-Based Testing**: Simulate user input for testing
3. **Plugin Integration**: Dynamic discovery keeps components current
4. **Fallback Options**: Always provide non-interactive alternatives

## Implementation Details

### State Machine Design

```python
class DesignerState(Enum):
    INITIAL = "initial"
    BASIC_INFO = "basic_info"
    PROTOCOL_SELECTION = "protocol_selection"
    IMPLEMENTATION_CONFIG = "implementation_config"
    TEST_CONFIGURATION = "test_configuration"
    REVIEW = "review"
    COMPLETE = "complete"

class ExperimentDesigner:
    def __init__(self):
        self.state = DesignerState.INITIAL
        self.config = {}
        self.history = []  # For back navigation

    def transition_to(self, new_state: DesignerState):
        """State transition with history tracking"""
        self.history.append(self.state)
        self.state = new_state

    def can_go_back(self) -> bool:
        return len(self.history) > 0

    def go_back(self):
        if self.can_go_back():
            self.state = self.history.pop()
```

### Validation Integration

```python
class ValidationHelper:
    def __init__(self):
        self.error_explanations = {
            'missing_required_field': self._explain_missing_field,
            'invalid_plugin': self._explain_invalid_plugin,
            'incompatible_options': self._explain_incompatible_options
        }

    def explain_error(self, error_type: str, context: dict) -> str:
        """Provide contextual error explanation"""
        explainer = self.error_explanations.get(error_type)
        if explainer:
            return explainer(context)
        return f"Validation error: {error_type}"

    def _explain_missing_field(self, context: dict) -> str:
        field_name = context['field']
        suggestions = self._get_field_suggestions(field_name)
        return f"""
        Missing required field: '{field_name}'

        This field is required because: {context['reason']}

        Suggestions:
        {chr(10).join(f'  • {s}' for s in suggestions)}
        """
```

### Progressive Disclosure

```python
class ConfigurationPrompt:
    def __init__(self, user_level: str = 'beginner'):
        self.user_level = user_level

    def prompt_for_value(self, field_config: dict):
        """Adapt prompts to user expertise level"""
        if self.user_level == 'beginner':
            return self._beginner_prompt(field_config)
        elif self.user_level == 'intermediate':
            return self._intermediate_prompt(field_config)
        else:
            return self._expert_prompt(field_config)

    def _beginner_prompt(self, field_config: dict):
        """Detailed explanations and guided choices"""
        print(f"\n📋 {field_config['description']}")
        print(f"ℹ️  {field_config['help_text']}")

        if 'examples' in field_config:
            print("Examples:")
            for example in field_config['examples'][:3]:
                print(f"  • {example}")

        return self._get_input_with_validation(field_config)
```

### Builder Pattern Implementation

```python
class ConfigurationBuilder:
    """Abstract base for configuration section builders"""

    def __init__(self, context: dict):
        self.context = context
        self.validators = []

    def add_validator(self, validator: callable):
        self.validators.append(validator)

    def build_section(self, existing_config: dict) -> dict:
        """Build configuration section interactively"""
        section_config = {}

        for field in self.get_required_fields():
            value = self.prompt_for_field(field, existing_config)
            section_config[field['name']] = value

        self.validate_section(section_config)
        return section_config

    @abstractmethod
    def get_required_fields(self) -> list:
        """Return list of required field definitions"""

    def validate_section(self, config: dict):
        """Run all validators on completed section"""
        for validator in self.validators:
            validator(config)

class ExperimentInfoBuilder(ConfigurationBuilder):
    """Builder for experiment metadata section"""

    def get_required_fields(self) -> list:
        return [
            {
                'name': 'name',
                'description': 'Experiment name (used for output directories)',
                'help_text': 'Choose a descriptive name without spaces',
                'validator': self.validate_experiment_name,
                'examples': ['quic_latency_test', 'http3_performance']
            },
            {
                'name': 'description',
                'description': 'Brief description of what this experiment tests',
                'help_text': 'Helps identify the experiment purpose later',
                'required': False
            }
        ]
```

### Testing Strategy

```python
class TestInteractiveComponents:
    """Test interactive components with mocked input"""

    @patch('builtins.input')
    def test_experiment_designer_full_flow(self, mock_input):
        """Test complete experiment design workflow"""
        # Simulate user responses
        mock_input.side_effect = [
            'test_experiment',     # name
            'QUIC latency test',   # description
            'quic',               # protocol
            'picoquic',           # implementation
            'basic',              # test type
            'yes'                 # confirm
        ]

        designer = ExperimentDesigner()
        config = designer.design_experiment()

        # Validate generated configuration
        assert config['experiment']['name'] == 'test_experiment'
        assert config['experiment']['protocol'] == 'quic'
        assert 'iut' in config
        assert 'tester' in config

    def test_validation_helper_error_explanation(self):
        """Test that validation helper provides useful explanations"""
        helper = ValidationHelper()

        explanation = helper.explain_error('missing_required_field', {
            'field': 'experiment.name',
            'reason': 'Used to create output directories'
        })

        assert 'experiment.name' in explanation
        assert 'required' in explanation.lower()
        assert 'output directories' in explanation

    @patch('builtins.input')
    def test_back_navigation(self, mock_input):
        """Test that users can navigate back in wizard"""
        mock_input.side_effect = [
            'test_name',
            'back',  # Go back
            'better_name',  # Try again
            'quic'
        ]

        designer = ExperimentDesigner()
        # Test navigation logic...
```

### Error Recovery

```python
class RecoverableInteraction:
    """Handle errors gracefully in interactive mode"""

    def prompt_with_retry(self, prompt_func: callable, max_retries: int = 3):
        """Prompt with retry logic for validation errors"""
        for attempt in range(max_retries):
            try:
                return prompt_func()
            except ValidationError as e:
                print(f"❌ {e}")
                if attempt < max_retries - 1:
                    print(f"💡 Please try again ({max_retries - attempt - 1} attempts remaining)")
                    continue
                else:
                    print("❌ Too many invalid attempts. Exiting.")
                    raise

    def offer_alternatives(self, error: ValidationError, context: dict):
        """Suggest alternatives when validation fails"""
        if error.error_type == 'invalid_plugin':
            available = context.get('available_plugins', [])
            suggestions = get_close_matches(error.attempted_value, available, n=3)

            if suggestions:
                print("💡 Did you mean one of these?")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")

                choice = input("Enter number (or 'no' to enter manually): ")
                if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                    return suggestions[int(choice) - 1]
```

## Alternatives Considered

### Rich TUI Framework
- **Pros**: Professional interface, keyboard navigation, complex layouts
- **Cons**: External dependency, terminal compatibility issues, learning curve
- **Decision**: Rejected for complexity; simple prompts sufficient for MVP

### Web-Based Configuration Interface
- **Pros**: Rich UI capabilities, cross-platform, familiar interface patterns
- **Cons**: Requires web server, port management, authentication complexity
- **Decision**: Deferred to future enhancement; CLI-first approach preferred

### YAML Template with Comments
- **Pros**: Simple implementation, version control friendly, no terminal requirements
- **Cons**: Static, no validation, overwhelming for beginners
- **Decision**: Implemented as complement, not replacement to interactive design

### Configuration DSL
- **Pros**: Powerful, programmatic, composable
- **Cons**: Learning curve, additional language complexity, harder debugging
- **Decision**: Rejected due to complexity; YAML sufficient for configuration needs

## Monitoring

Interactive component effectiveness measured by:

- **Completion Rate**: Percentage of users who complete configuration wizard
- **Error Rate**: Frequency of validation errors during interactive sessions
- **User Feedback**: Qualitative feedback on ease of use
- **Configuration Quality**: Validity rate of generated configurations
- **Support Requests**: Reduction in configuration-related support needs

## Integration Points

### Plugin System Integration
Interactive components automatically discover available plugins:

```python
def get_available_implementations(protocol: str) -> list:
    """Dynamically discover available implementations"""
    plugin_manager = PluginManager()
    plugins = plugin_manager.discover_plugins(type='iut', protocol=protocol)
    return [(name, plugin.description) for name, plugin in plugins.items()]
```

### Template System Integration
Interactive design can start from templates:

```python
designer = ExperimentDesigner()
if args.from_template:
    designer.load_template(args.template_name)
config = designer.design_experiment()
```

### Configuration Validation Integration
Real-time validation during design:

```python
def validate_current_config(self):
    """Validate configuration at current state"""
    try:
        validator = ConfigurationValidator()
        validator.validate_partial(self.config, self.state)
        return True
    except ValidationError as e:
        self.show_validation_error(e)
        return False
```

## Related Decisions

- [ADR-0001: Command Pattern Architecture](0001-command-pattern-architecture.md) - Provides command integration framework
- [ADR-0002: Error Handling and Exit Codes](0002-error-handling-exit-codes.md) - Error handling for interactive failures
- Future ADR: Plugin Discovery Architecture - Dynamic plugin integration

---

*This ADR establishes the foundation for user-friendly interactive components that make PANTHER accessible to users with varying levels of expertise.*
