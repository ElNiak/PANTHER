#


## IEnvironmentPlugin
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/environment_interface.py/#L8)
```python
IEnvironmentPlugin(
   env_config_to_test: EnvironmentConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```


---
IEnvironmentPlugin is an abstract base class that defines the interface for environment plugins.


**Attributes**

* **templates_dir** (str) : Directory path for templates specific to the environment type and subtype.
* **output_dir** (str) : Directory path for output files.
* **env_type** (str) : Type of the environment.
* **env_sub_type** (str) : Subtype of the environment.
* **log_dirs** (str) : Directory path for log files.
* **plugin_loader**  : Loader for the plugin (initially set to None).
* **env_config_to_test** (EnvironmentConfig) : Configuration of the environment to be tested.
* **event_manager** (EventManager) : Manager for handling events.

---
Methods:
    is_network_environment():
        Abstract method. Returns True if the plugin is a network environment.

    setup_environment():
        Abstract method. Sets up the required environment before running experiments.

    teardown_environment():
        Abstract method. Tears down the environment after experiments are completed.


**Methods:**


### .is_network_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/environment_interface.py/#L54)
```python
.is_network_environment()
```

---
Returns True if the plugin is a network environment.

### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/environment_interface.py/#L61)
```python
.setup_environment()
```

---
Sets up the required environment before running experiments.

### .teardown_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/environment_interface.py/#L68)
```python
.teardown_environment()
```

---
Tears down the environment after experiments are completed.
