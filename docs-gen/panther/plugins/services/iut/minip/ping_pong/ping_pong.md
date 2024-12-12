#


## PingPongServiceManager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/minip/ping_pong/ping_pong.py/#L10)
```python
PingPongServiceManager(
   service_config_to_test: PingPongConfig, service_type: str,
   protocol: ProtocolConfig, implementation_name: str
)
```




**Methods:**


### .generate_pre_compile_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/minip/ping_pong/ping_pong.py/#L29)
```python
.generate_pre_compile_commands()
```

---
Generates pre-compile commands.

### .generate_run_command
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/minip/ping_pong/ping_pong.py/#L63)
```python
.generate_run_command()
```

---
Generates the run command.

### .generate_post_run_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/minip/ping_pong/ping_pong.py/#L80)
```python
.generate_post_run_commands()
```

---
Generates post-run commands.

### .prepare
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/minip/ping_pong/ping_pong.py/#L88)
```python
.prepare(
   plugin_loader: (PluginLoader|None) = None
)
```

---
Prepare the service manager for use.

### .generate_deployment_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/minip/ping_pong/ping_pong.py/#L111)
```python
.generate_deployment_commands()
```

---
Generates deployment commands and collects volume mappings based on service parameters.

:param service_params: Parameters specific to the service.
:param environment: The environment in which the services are being deployed.
:return: A dictionary with service name as key and a dictionary containing command and volumes.
