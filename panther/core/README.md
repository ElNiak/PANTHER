
# :book: Core Module

## Overview
The `core` module is the foundation of the PANTHER framework, providing essential classes and methods for managing experiments, handling results, and implementing the observer pattern. It facilitates the orchestration of experiments and the flow of data between different components of the system.

## Contents

### 1. Experiment Management
- **`experiment_manager.py`**:
  - Manages the lifecycle of experiments, including initialization, execution, and cleanup.
  - Integrates with plugins to execute experiments in diverse environments.
- **`experiment_strategy.py`**:
  - Implements strategies for running experiments, allowing flexibility in execution patterns.

### 2. Observer Pattern
The observer pattern is used to decouple components and enable event-driven updates.
- **`observer`** (submodule):
  - **`event.py`**: Defines events used for communication between components.
  - **`event_manager.py`**: Manages the registration and notification of observers.
  - **`experiment_observer.py`**: Monitors the progress of experiments.
  - **`gui_observer.py`**: Provides hooks for GUI updates.
  - **`logger_observer.py`**: Logs experiment progress and errors.
  - **`observer_interface.py`**: Defines the interface for observers.
  - **`result_observer.py`**: Monitors and collects experiment results.

### 3. Results Handling
- **`results`** (submodule):
  - **`result_collector.py`**: Aggregates results from different parts of the system.
  - **`result_handler.py`**: Processes and validates results.

### 4. Exceptions
Custom exceptions for handling errors in core functionalities:
- **`exceptions/EnvironmentPluginNotFound.py`**: Raised when a required environment plugin is missing.
- **`exceptions/ServicePluginNotFound.py`**: Raised when a required service plugin is missing.
- **`exceptions/TesterPluginNotFound.py`**: Raised when a required tester plugin is missing.

## Usage
1. **Experiment Lifecycle**:
   - Use `experiment_manager` to orchestrate experiments, including loading configurations and executing tasks.

2. **Observer Integration**:
   - Register observers with the `event_manager` to receive updates on experiment progress and results.

3. **Results Processing**:
   - Leverage `result_handler` to validate and process experiment results.

## Extensibility
The `core` module is designed to be extensible:
- Add new observers by implementing the `observer_interface` and registering them with the `event_manager`.
- Extend `result_handler` to support custom result processing logic.

## Key Dependencies
- Plugins: The `core` module heavily relies on plugins for environment and service integration.
- Configuration: Requires configurations from the `config` module for experiments.

---

## Contribution
To contribute to the `core` module:
1. Ensure new features align with the modular design of the framework.
2. Write unit tests for all new methods and classes.
3. Follow the project's coding standards and documentation guidelines.
