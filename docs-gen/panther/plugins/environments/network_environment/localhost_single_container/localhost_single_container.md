#


## LocalhostSingleContainerEnvironment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py/#L20)
```python
LocalhostSingleContainerEnvironment(
   env_config_to_test: EnvironmentConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```


---
LocalhostSingleContainerEnvironment is a class that manages a single container environment on localhost for testing purposes.
It extends the INetworkEnvironment interface and provides methods to prepare, set up, deploy, monitor, and tear down the environment.


**Attributes**

* **docker_version** (str) : The version of Docker to use.
* **docker_name** (str) : The name prefix for the Docker container.
* **services_network_config_file_path** (Path) : Path to the generated run.sh file.
* **rendered_services_network_config_file_path** (Path) : Path to the rendered run.sh file.
* **services_network_docker_file_path** (Path) : Path to the generated Dockerfile.
* **rendered_services_network_docker_file_path** (Path) : Path to the rendered Dockerfile.

---
Methods:
    __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
        Initializes the LocalhostSingleContainerEnvironment with the given configuration.
    __str__():
        Returns a string representation of the LocalhostSingleContainerEnvironment instance.
    __repr__():
        Returns a string representation of the LocalhostSingleContainerEnvironment instance.
    prepare_environment():
        Prepares the service manager for use.
    setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
    deploy_services():
        Deploys the services in the Localhost environment.
    generate_environment_services(paths, timestamp):
    launch_environment_services():
    monitor_environment():
    teardown_environment():


**Methods:**


### .prepare_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py/#L102)
```python
.prepare_environment()
```

---
Prepare the service manager for use.

### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py/#L122)
```python
.setup_environment(
   services_managers: list[IServiceManager], test_config: TestConfig,
   global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader,
   execution_environment: list[IExecutionEnvironment]
)
```

---
Sets up the Localhost environment by generating the run.sh file with deployment commands.

### .deploy_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py/#L147)
```python
.deploy_services()
```


### .generate_environment_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py/#L151)
```python
.generate_environment_services(
   paths: dict[str, str], timestamp: str
)
```

---
Generates the run.sh file using the provided services and deployment commands.

:param paths: Dictionary containing various path configurations.
:param timestamp: The timestamp string to include in log paths.

### .launch_environment_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py/#L248)
```python
.launch_environment_services()
```

---
Launches the Localhost environment using the generated run.sh file.

### .monitor_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py/#L311)
```python
.monitor_environment()
```

---
Monitors the Docker Compose environment by checking the status of services.

### .teardown_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py/#L358)
```python
.teardown_environment()
```

---
Tears down the Localhost environment by bringing down services.
