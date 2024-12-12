#


## INetworkEnvironment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L24)
```python
INetworkEnvironment(
   env_config_to_test: EnvironmentConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```


---
INetworkEnvironment is an abstract class that defines the interface for network environment plugins.
It inherits from IEnvironmentPlugin and provides methods for setting up, updating, and managing network environments.

**Attributes**

* **docker_name** (str) : Name of the Docker container.
* **execution_environment** (list) : List of execution environments.
* **network_name** (str) : Name of the network.
* **execution_environments** (list) : List of execution environments.
* **services** (dict) : Dictionary of services.
* **deployment_commands** (dict) : Dictionary of deployment commands.
* **timeout** (int) : Timeout value.
* **global_config** (GlobalConfig) : Global configuration.
* **test_config** (TestConfig) : Test configuration.
* **services_managers** (list) : List of service managers.
* **logger** (Logger) : Logger instance.
* **jinja_env** (Environment) : Jinja2 environment for template rendering.

---
Methods:
    __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
        Initializes the network environment with the given configuration.
    setup_execution_plugins(timestamp):
        Sets up execution plugins for the environment.
    update_environment(execution_environment, global_config, plugin_loader, services_managers, test_config):
        Updates the environment with the given configuration and services.
    create_log_dir(service):
        Creates a log directory for the given service.
    generate_from_template(template_name, paths, timestamp, rendered_out_file, out_file, additional_param=None):
        Generates a file from a Jinja2 template.
    get_docker_name():
        Retrieves the Docker container name.
    resolve_environment_variables(env_vars):
        Resolves environment variables incrementally, ensuring no duplication and preserving unresolved tokens.
    is_network_environment():
    generate_environment_services(paths, timestamp):
        Abstract method to generate the services required for the network environment.
    prepare_environment():
        Abstract method to prepare the environment for running experiments.
    launch_environment_services():
        Abstract method to launch the services in the network environment.
    deploy_services():
        Abstract method to deploy the specified services in the network environment.
    setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
        Abstract method to set up the required environment before running experiments.
    teardown_environment():
        Abstract method to tear down the environment after experiments are completed.


**Methods:**


### .setup_execution_plugins
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L104)
```python
.setup_execution_plugins(
   timestamp
)
```

---
Sets up the execution plugins for each execution environment.

This method iterates through the list of execution environments and sets up each one by calling its
`setup_environment` method with the necessary parameters. If an error occurs during the setup of any
execution environment, it logs the error along with the traceback.


**Args**

* **timestamp** (str) : The timestamp to be used during the setup of the execution environments.


**Raises**

* **Exception**  : If an error occurs during the setup of any execution environment, it is caught and logged.


### .update_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L133)
```python
.update_environment(
   execution_environment, global_config, plugin_loader, services_managers,
   test_config
)
```

---
Updates the network environment with the provided configuration and services.


**Args**

* **execution_environment** (Any) : The execution environment to be used.
* **global_config** (OmegaConf) : The global configuration settings.
* **plugin_loader** (Any) : The plugin loader instance.
* **services_managers** (List[IServiceManager]) : A list of service manager instances.
* **test_config** (OmegaConf) : The test configuration settings.


**Returns**

None

### .create_log_dir
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L165)
```python
.create_log_dir(
   service: IServiceManager
)
```

---
Creates a log directory for the given service if it does not already exist.


**Args**

* **service** (IServiceManager) : The service manager instance containing the service name.

---
Logs:
    Info: Logs the creation of the log directory if it was created.

### .generate_from_template
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L180)
```python
.generate_from_template(
   template_name, paths, timestamp, rendered_out_file, out_file,
   additional_param = None
)
```

---
Generates a configuration file from a Jinja2 template.


**Args**

* **template_name** (str) : The name of the Jinja2 template to use.
* **paths** (dict) : A dictionary of paths to be used in the template.
* **timestamp** (str) : A timestamp to be included in the rendered template.
* **rendered_out_file** (str) : The file path where the rendered template will be saved.
* **out_file** (str) : The file path where the final output will be saved.
* **additional_param** (dict, optional) : Additional parameters to be passed to the template. Defaults to None.


**Returns**

None

### .get_docker_name
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L222)
```python
.get_docker_name()
```

---
Retrieves and sets the Docker container name by building a Docker image from a specified path.

This method uses the `plugin_loader` to build a Docker image from the provided Dockerfile path,
Docker name, and Docker version. It then extracts and sets the Docker container name by splitting
the resulting Docker image name at the colon (':') character.


**Returns**

* **str**  : The name of the Docker container.


### .resolve_environment_variables
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L240)
```python
.resolve_environment_variables(
   env_vars
)
```

---
Resolves environment variables incrementally, ensuring no duplication
and preserving unresolved tokens. Processes variables in dependency order.

:param env_vars: dict, environment variables with potential references.
:return: dict, resolved environment variables.

### .is_network_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L286)
```python
.is_network_environment()
```

---
Returns True if the plugin is a network environment.

### .generate_environment_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L293)
```python
.generate_environment_services(
   paths: dict[str, str], timestamp: str
)
```

---
Generates the services required for the network environment.

:param services: A dictionary containing the services to be generated.
:return: A list of generated services.

### .prepare_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L303)
```python
.prepare_environment()
```

---
Prepares the environment for running experiments.

### .launch_environment_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L310)
```python
.launch_environment_services()
```

---
Launches the services in the network environment.

### .deploy_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L317)
```python
.deploy_services()
```

---
Deploys the specified services in the network environment.

### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L324)
```python
.setup_environment(
   services_managers: list[IServiceManager], test_config: TestConfig,
   global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader,
   execution_environment: list[IExecutionEnvironment]
)
```

---
Sets up the required environment before running experiments.

### .teardown_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/network_environment_interface.py/#L339)
```python
.teardown_environment()
```

---
Tears down the environment after experiments are completed.
