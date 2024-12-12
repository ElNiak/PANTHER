#


## PluginManager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_manager.py/#L21)
```python
PluginManager(
   plugins_loader: PluginLoader
)
```


---
Manages the loading and instantiation of various plugins for the system.


**Attributes**

* **plugins_loader** (PluginLoader) : The loader responsible for loading plugins.
* **logger** (logging.Logger) : Logger instance for logging messages.
* **protocol_plugins** (Dict[str, IServiceManager]) : Dictionary to store protocol plugins.
* **network_environment_plugins** (Dict[str, INetworkEnvironment]) : Dictionary to store network environment plugins.
* **execution_environment_plugins** (Dict[str, IExecutionEnvironment]) : Dictionary to store execution environment plugins.

---
Methods:
        Creates and returns an instance of an environment manager for the given environment.


**Methods:**


### .create_service_manager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_manager.py/#L47)
```python
.create_service_manager(
   protocol: ProtocolConfig, implementation: ImplementationConfig,
   implementation_dir: Path, service_config_to_test: ServiceConfig
)
```

---
Creates an instance of a service manager for a given protocol and implementation.

This method dynamically loads a service manager class from a specified implementation
directory and creates an instance of it. The service manager class must inherit from
IServiceManager.


**Args**

* **protocol** (ProtocolConfig) : The protocol configuration.
* **implementation** (ImplementationConfig) : The implementation configuration.
* **implementation_dir** (Path) : The directory where the implementation is located.
* **service_config_to_test** (ServiceConfig) : The service configuration to test.


**Returns**

* **IServiceManager**  : An instance of the service manager.


**Raises**

* **FileNotFoundError**  : If the service manager file does not exist.
* **AttributeError**  : If the service manager class is not found or does not inherit from IServiceManager.
* **ImportError**  : If the module cannot be loaded.


### .create_environment_manager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_manager.py/#L133)
```python
.create_environment_manager(
   environment: str, test_config: TestConfig, environment_dir: Path,
   output_dir: Path, event_manager: EventManager
)
```

---
Creates an instance of an environment manager by dynamically loading the appropriate
environment plugin module and class.


**Args**

* **environment** (str) : The name of the environment to be managed.
* **test_config** (TestConfig) : The test configuration object containing environment settings.
* **environment_dir** (Path) : The directory path where environment plugins are located.
* **output_dir** (Path) : The directory path where output files should be stored.
* **event_manager** (EventManager) : The event manager instance to handle events.


**Returns**

* **IEnvironmentPlugin**  : An instance of the environment manager class.


**Raises**

* **FileNotFoundError**  : If the environment plugin file does not exist.
* **AttributeError**  : If the environment class is not found or does not inherit from IEnvironmentPlugin.
* **ImportError**  : If the module cannot be loaded.

