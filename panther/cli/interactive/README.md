# Interactive CLI Components

This module provides interactive user interface components for the PANTHER CLI, focusing on guided configuration creation and enhanced user experience.

## Overview

The interactive components transform the complex task of creating PANTHER experiment configurations from manual YAML editing to a guided, step-by-step process. This significantly reduces the learning curve and configuration errors.

## Components

### 1. ExperimentDesigner (`experiment_designer.py`)

**Purpose**: Main orchestrator for interactive experiment configuration creation

**Key Features**:

- State machine-driven wizard flow
- Support for starting from existing configurations
- Multiple test creation within single experiment
- Quick mode for rapid prototyping
- Real-time validation at each step
- Configuration preview and review

**Usage Flow**:

```python
designer = ExperimentDesigner(
    output_path="my_experiment.yaml",
    from_file="existing.yaml",  # Optional
    quick_mode=True            # Optional
)
success = designer.run()
```

**State Management**:

1. **Welcome Phase**: Introduction and mode selection
2. **Loading Phase**: Load existing config if specified
3. **Building Phase**: Interactive configuration building
4. **Review Phase**: Validation and final review
5. **Save Phase**: Write configuration to file

**Design Patterns**:

- **Builder Pattern**: Delegates specific sections to specialized builders
- **State Machine**: Manages complex user interaction flow
- **Template Method**: Consistent structure for different modes

### 2. ValidationHelper (`validation_helper.py`)

**Purpose**: Enhanced validation with user-friendly error messages and suggestions

**Key Features**:

- Pattern-based error recognition
- Contextual suggestions for fixes
- Plugin availability checking
- Service relationship validation
- Configuration structure analysis

**Error Solution Database**:

```python
ERROR_SOLUTIONS = {
    "Plugin not found": {
        "cause": "The specified plugin does not exist or is not installed",
        "solutions": [
            "Check the plugin name spelling",
            "Use 'panther plugins list' to see available plugins",
            # ... more solutions
        ]
    },
    # ... more error patterns
}
```

**Validation Methods**:

- `explain_validation_error()`: Convert technical errors to user-friendly explanations
- `validate_service_relationships()`: Check client-server dependencies
- `get_available_plugins()`: Discover available plugins by type
- `suggest_fixes()`: Provide specific suggestions based on config content

### 3. ConfigurationBuilders (`builders.py`)

**Purpose**: Modular builders for each configuration section

**Builder Hierarchy**:

```
BaseBuilder
├── GlobalConfigBuilder      # Global settings (logging, paths, docker)
└── TestConfigBuilder       # Individual test configurations
    ├── NetworkEnvironmentBuilder
    ├── ExecutionEnvironmentBuilder
    ├── ServiceConfigBuilder
    └── StepConfigBuilder
```

**BaseBuilder Features**:

- Consistent prompting interface
- Input validation
- Default value handling
- Choice menus
- Boolean prompts with defaults
- Integer prompts with range validation

**Prompt Types**:

```python
# Text input with default
response = self.prompt("Service name", default="server")

# Multiple choice
env_type = self.prompt(
    "Select network environment",
    choices=["docker_compose", "shadow_ns", "localhost_single_container"]
)

# Boolean prompt
enable_feature = self.prompt_bool("Enable feature?", default=True)

# Integer with validation
timeout = self.prompt_int("Timeout (seconds)", default=60, min_val=10, max_val=600)
```

## Implementation Details

### User Experience Design

**Progressive Disclosure**:

- Start with simple questions
- Offer advanced options when relevant
- Provide sensible defaults
- Allow skipping optional sections

**Error Prevention**:

- Validate input at each step
- Provide immediate feedback
- Suggest valid alternatives
- Prevent invalid combinations

**Context Awareness**:

- Remember previous choices
- Suggest compatible options
- Validate relationships between services
- Check plugin availability

### Plugin Discovery Integration

The interactive components integrate deeply with PANTHER's plugin system:

```python
# Auto-discover available implementations
implementations = self.available_plugins["iut"].get(protocol, [])

# Validate plugin exists before offering
if plugin_name in available_plugins:
    # Offer as option
    pass
```

**Plugin Information Display**:

- Show plugin descriptions
- List capabilities
- Display parameter requirements
- Indicate compatibility

### Configuration Templates

**Quick Mode Templates**:

- Minimal viable configurations
- Sensible defaults for all fields
- Skip optional advanced features
- Focus on getting started quickly

**Full Mode Options**:

- Complete control over all settings
- Advanced configuration options
- Multiple test scenarios
- Fine-grained parameter control

### Validation Integration

**Real-time Validation**:

```python
# Validate as user builds configuration
errors = self.validation_helper.validate_service_relationships(services)
if errors:
    for error in errors:
        logging.info(f"❌ {error}")
    # Allow user to fix or continue
```

**Final Validation**:

- Complete schema validation
- Plugin availability check
- Service dependency verification
- Port conflict detection

## Error Handling Patterns

### Graceful Degradation

**Plugin Not Found**:

1. Show available alternatives
2. Suggest similar plugins
3. Allow manual entry
4. Provide installation instructions

**Invalid Configuration**:

1. Explain the problem clearly
2. Show correct format
3. Offer to fix automatically
4. Allow manual correction

**Interruption Handling**:

```python
try:
    # Interactive prompts
    pass
except KeyboardInterrupt:
    logging.info("\n⚠️  Configuration cancelled by user")
    # Offer to save partial configuration
    return False
```

### User Guidance

**Help at Every Step**:

- Explain what each section does
- Provide examples
- Link to documentation
- Offer to skip non-essential parts

**Learning Mode**:

- Explain concepts as they're configured
- Show the generated YAML
- Explain relationships between settings
- Provide best practice tips

## Future Enhancements

### Planned Features

1. **Configuration Diff Tool**
   - Compare configurations visually
   - Highlight differences
   - Merge configurations
   - Version control integration

2. **Template Marketplace**
   - Community-contributed templates
   - Template versioning
   - Template validation
   - Usage analytics

3. **Visual Configuration Builder**
   - Web-based interface
   - Drag-and-drop service creation
   - Visual network topology
   - Real-time preview

4. **Smart Suggestions**
   - Machine learning-based recommendations
   - Learn from successful configurations
   - Suggest optimal parameters
   - Detect anti-patterns

5. **Configuration Validation Service**
   - Remote validation API
   - Community-driven rule sets
   - Best practice enforcement
   - Security checking

### Technical Improvements

1. **Performance Optimization**
   - Lazy loading of plugins
   - Cached validation results
   - Asynchronous plugin discovery
   - Progressive loading

2. **Enhanced User Experience**
   - Rich terminal UI with cursor navigation
   - Form-based input
   - Progress indicators
   - Undo/redo functionality

3. **Accessibility**
   - Screen reader support
   - Keyboard navigation
   - High contrast mode
   - Alternative input methods

4. **Internationalization**
   - Multi-language support
   - Localized error messages
   - Cultural considerations
   - Right-to-left language support

### Integration Opportunities

1. **IDE Integration**
   - VS Code extension
   - IntelliJ plugin
   - Language server protocol
   - Syntax highlighting

2. **CI/CD Integration**
   - Configuration generation in pipelines
   - Automated validation
   - Template deployment
   - Version management

3. **Cloud Integration**
   - Remote configuration storage
   - Collaborative editing
   - Configuration sharing
   - Cloud validation

## Testing Strategy

### Unit Testing

**Builder Tests**:

- Test each prompt type
- Validate input handling
- Check default behaviors
- Test error conditions

**Validation Tests**:

- Test error pattern recognition
- Validate suggestion quality
- Check plugin discovery
- Test relationship validation

### Integration Testing

**End-to-End Flows**:

- Complete configuration creation
- Starting from existing configs
- Error recovery scenarios
- Plugin interaction

**User Journey Testing**:

- New user experience
- Power user workflows
- Error recovery paths
- Performance under load

### Manual Testing

**Usability Testing**:

- Time to complete tasks
- Error frequency
- User satisfaction
- Learning curve measurement

**Accessibility Testing**:

- Screen reader compatibility
- Keyboard-only navigation
- Color contrast
- Font size adjustments

## Best Practices

### For Developers

1. **Consistent UX Patterns**
   - Use established prompt patterns
   - Maintain consistent terminology
   - Follow error message formats
   - Provide clear feedback

2. **Robust Error Handling**
   - Validate all user input
   - Provide helpful error messages
   - Allow graceful recovery
   - Log errors for debugging

3. **Extensible Design**
   - Use plugin patterns
   - Abstract common functionality
   - Make builders easily extendable
   - Design for future features

### For Users

1. **Start Simple**
   - Use quick mode first
   - Start with templates
   - Build complexity gradually
   - Validate frequently

2. **Leverage Help**
   - Read explanations carefully
   - Use provided examples
   - Don't skip validation
   - Save work frequently

## Conclusion

The interactive CLI components represent a significant improvement in PANTHER's usability. By providing guided configuration creation, enhanced validation, and user-friendly error messages, these components make PANTHER accessible to a much broader audience while maintaining the power and flexibility that advanced users require.

The modular design ensures that new features can be added easily, and the consistent patterns make the interface predictable and learnable. Future enhancements will continue to improve the user experience while maintaining backward compatibility and performance.
