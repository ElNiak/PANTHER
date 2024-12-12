#


## ShadowNsEnvironment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L22)
```python
ShadowNsEnvironment(
   env_config_to_test: EnvironmentConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```


---
ShadowNsEnvironment is a class that manages the Shadow NS environment for testing purposes.
It extends the INetworkEnvironment interface and provides methods to prepare, set up, deploy,
monitor, and tear down the environment.

- Real Applications:
  Shadow directly executes real, unmodified application binaries natively in Linux as standard OS
  processes and co-opts them into a discrete-event simulation.

- Simulated Networks:
  Shadow intercepts and emulates system calls made by the co-opted processes, connecting them through
  an internal network using simulated implementations of common network protocols (e.g., TCP and UDP).
  (Reproducible experiments)

- High Performance:
  Shadow focuses on high performance simulation, efficiently simulating both small client/server networks
  and large distributed systems. Shadow has been used to simulate real-world peer-to-peer networks such
  as Tor and Bitcoin.

<!> Not all IUTs are compatible with Shadow (missing system calls, etc.)

This network environment encapsulates the Shadow NS and all the services in a *single* Docker container.

See: https://shadow.github.io/


**Attributes**

* **docker_version** (str) : The version of the Docker image.
* **docker_name** (str) : The name of the Docker container.
* **services_network_config_file_path** (Path) : Path to the generated services network configuration file.
* **rendered_services_network_config_file_path** (Path) : Path to the rendered services network configuration file.
* **services_network_docker_file_path** (Path) : Path to the generated Dockerfile for services network.
* **rendered_services_network_docker_file_path** (Path) : Path to the rendered Dockerfile for services network.

---
Methods:
        Reads the generated shadow.yml file and returns its contents as a dictionary.


**Methods:**


### .prepare_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L137)
```python
.prepare_environment()
```

---
Prepare the service manager for use.

### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L158)
```python
.setup_environment(
   services_managers: list[IServiceManager], test_config: TestConfig,
   global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader,
   execution_environment: list[IExecutionEnvironment]
)
```

---
Sets up the Shadow NS environment by generating the shadow.yml file with deployment commands.

### .deploy_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L183)
```python
.deploy_services()
```


### .generate_environment_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L187)
```python
.generate_environment_services(
   paths: dict[str, str], timestamp: str
)
```

---
Generates the shadow.yml file using the provided services and deployment commands.

:param paths: Dictionary containing various path configurations.
:param timestamp: The timestamp string to include in log paths.

### .launch_environment_services
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L279)
```python
.launch_environment_services()
```

---
Launches the Shadow NS environment using the generated shadow.yml file.

### .monitor_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L344)
```python
.monitor_environment()
```

---
Monitors the Docker Compose environment by checking the status of services.

### .teardown_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L391)
```python
.teardown_environment()
```

---
Tears down the Shadow NS environment by bringing down services.

### .read_shadow_file
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py/#L430)
```python
.read_shadow_file()
```

---
Reads the generated shadow.yml file.
