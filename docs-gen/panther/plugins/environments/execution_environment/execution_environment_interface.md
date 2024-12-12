#


## IExecutionEnvironment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/execution_environment_interface.py/#L16)
```python
IExecutionEnvironment(
   env_config_to_test: EnvironmentConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```


---
IExecutionEnvironment is an abstract base class that defines the interface for execution environment plugins.


**Attributes**

* **services_managers** (list) : A list to store service managers.
* **test_config** (TestConfig) : Configuration for the test, initially set to None.

---
Methods:
    __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
        Initializes the execution environment with the given configuration.

    is_network_environment():
        Returns True if the plugin is a network environment. Default implementation returns False.

    setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader):
        Abstract method to set up the required environment before running experiments. Must be implemented by subclasses.

    teardown_environment():
        Tears down the environment after experiments are completed. Default implementation does nothing.


**Methods:**


### .is_network_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/execution_environment_interface.py/#L52)
```python
.is_network_environment()
```

---
Returns True if the plugin is an network environment.

### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/execution_environment_interface.py/#L59)
```python
.setup_environment(
   services_managers: list[IServiceManager], test_config: TestConfig,
   global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader
)
```

---
Sets up the required environment before running experiments.

### .teardown_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/execution_environment_interface.py/#L72)
```python
.teardown_environment()
```

---
Tears down the environment after experiments are completed.
