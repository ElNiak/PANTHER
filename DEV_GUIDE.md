
# Developer Documentation for PANTHER

This guide provides technical details for contributors and maintainers of PANTHER. Learn about the codebase, design principles, and guidelines for extending the system.

---

## Code Architecture

### Overview
PANTHER is built with modularity and extensibility in mind. Key directories:
- **`core/`**: Contains core logic for experiment execution and management.
- **`config/`**: Handles experiment configurations and schema validation.
- **`plugins/`**: Houses plugins for protocols, services, and environments.
- **`outputs/`**: Stores logs and results.

---

## Design Principles

1. **Modularity**:
   - Each component has a specific responsibility, making the system easier to extend and maintain.

2. **Dynamic Loading**:
   - Plugins and configurations are dynamically loaded to support extensibility.

3. **Error Handling**:
   - Comprehensive logging and exception management ensure robustness.

---

## Key Components

### ExperimentManager
- Orchestrates the execution of experiments.
- Responsible for initializing test cases, deploying services, and managing results.

### TestCase
- Represents individual tests within an experiment.
- Encapsulates service deployment, step execution, and assertion validation.

### PluginLoader
- Dynamically loads and validates plugins (e.g., protocols, environments).
- Handles Docker integration for plugins requiring containerized environments.

---

## Adding New Features

1. **Define Requirements**:
   - Clearly define the feature's purpose and scope.

2. **Modify Core Components** (if necessary):
   - Update `ExperimentManager` or `TestCase` for new test types.

3. **Develop Plugins**:
   - Create new plugins in `plugins/` if extending protocols or services.

4. **Update Configuration Schema**:
   - Modify `config_schema.py` to support new configuration options.

5. **Write Unit Tests**:
   - Add tests in `tests/` to ensure feature reliability.

---

## Refactoring Guidelines

1. **Follow DRY**:
   - Avoid duplicating code; extract common functionality into reusable functions.

2. **Preserve Backward Compatibility**:
   - Ensure existing experiments and configurations remain functional.

3. **Write Comprehensive Tests**:
   - Validate changes using unit and integration tests.

---

## Error Handling

### Logging
- All components use Python’s `logging` module for structured logging.
- Logs are saved in `outputs/logs` for debugging.

### Exceptions
- Raise meaningful exceptions with descriptive messages.
- Catch and log exceptions in critical areas (e.g., `ExperimentManager`).

---

## Contributing

1. Fork the repository and create a new branch for your feature or bug fix.
2. Run the tests to ensure stability:
   ```bash
   pytest tests/
   ```
3. Submit a pull request with detailed explanations of your changes.

---

For additional guidance, consult the [Main README](README.md) or contact the development team.