#


## DockerComposeEnvironment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/docker_compose/docker_compose.py/#L20)
```python
DockerComposeEnvironment(
   env_config_to_test: EnvironmentConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```


---
DockerComposeEnvironment is a class that manages the setup, deployment, monitoring, and teardown of a
Docker Compose environment.


**Attributes**

* **services_network_config_file_path** (Path) : Path to the generated Docker Compose configuration file.
* **rendered_services_network_config_file_path** (Path) : Path to the rendered Docker Compose configuration file.

---
Methods:
    __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
        Initializes the DockerComposeEnvironment with the given configuration and paths.
    __str__():
        Returns a string representation of the DockerComposeEnvironment instance.
    __repr__():
        Returns a string representation of the DockerComposeEnvironment instance.
    setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
    prepare_environment():
        Prepares the environment (currently not implemented).
    deploy_services():
        Deploys the services defined in the Docker Compose environment.
    generate_environment_services(paths, timestamp):
    launch_environment_services():
    monitor_environment():
    teardown_environment():


**Methods:**


### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/docker_compose/docker_compose.py/#L78)
```python
.setup_environment(
   services_managers: list[IServiceManager], test_config: TestConfig,
   global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader,
   execution_environment: list[IExecutionEnvironment]
)
```

---
Sets up the Docker Compose environment by generating the docker-compose.yml file with deployment commands.

### .prepare_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/docker_compose/docker_compose.py/#L102)
```python
.prepare_environment()
```


### .deploy_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/docker_compose/docker_compose.py/#L105)
```python
.deploy_services()
```


### .generate_environment_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/docker_compose/docker_compose.py/#L109)
```python
.generate_environment_services(
   paths: dict[str, str], timestamp: str
)
```

---
Generates the docker-compose.yml file using the provided services and deployment commands.

:param paths: Dictionary containing various path configurations.
:param timestamp: The timestamp string to include in log paths.

### .launch_environment_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/docker_compose/docker_compose.py/#L183)
```python
.launch_environment_services()
```

---
Launches the Docker Compose environment using the generated docker-compose.yml file.

### .monitor_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/docker_compose/docker_compose.py/#L242)
```python
.monitor_environment()
```

---
Monitors the Docker Compose environment by checking the status of services.

### .teardown_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/docker_compose/docker_compose.py/#L290)
```python
.teardown_environment()
```

---
Tears down the Docker Compose environment by bringing down services.
