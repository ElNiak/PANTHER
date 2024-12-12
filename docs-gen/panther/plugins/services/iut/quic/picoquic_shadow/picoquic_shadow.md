#


## PicoquicShadowServiceManager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L12)
```python
PicoquicShadowServiceManager(
   service_config_to_test: PicoquicShadowConfig, service_type: str,
   protocol: ProtocolConfig, implementation_name: str
)
```


---
PicoquicShadowServiceManager is a service manager for handling Picoquic services.
This class is responsible for initializing the service manager, generating various commands required for the service lifecycle, and preparing the service manager for use.
Methods:
    Initializes the PicoquicShadowServiceManager with the given configuration, service type, protocol, and implementation name.
get_service_name(self) -> str:
    Returns the name of the service.
generate_pre_compile_commands(self):
generate_compile_commands(self):
generate_pre_run_commands(self):
generate_run_command(self):
generate_post_run_commands(self):
    Prepares the service manager for use.
generate_deployment_commands(self) -> str:


**Methods:**


### .get_service_name
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L49)
```python
.get_service_name()
```


### .generate_pre_compile_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L52)
```python
.generate_pre_compile_commands()
```

---
Generates pre-compile commands.

### .generate_compile_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L58)
```python
.generate_compile_commands()
```

---
Generates compile commands.

### .generate_pre_run_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L64)
```python
.generate_pre_run_commands()
```

---
Generates pre-run commands.

### .generate_run_command
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L70)
```python
.generate_run_command()
```

---
Generates the run command.

### .generate_post_run_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L87)
```python
.generate_post_run_commands()
```

---
Generates post-run commands.

### .prepare
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L95)
```python
.prepare(
   plugin_loader: (PluginLoader|None) = None
)
```

---
Prepare the service manager for use.

### .generate_deployment_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py/#L118)
```python
.generate_deployment_commands()
```

---
Generates deployment commands and collects volume mappings based on service parameters.

:param service_params: Parameters specific to the service.
:param environment: The environment in which the services are being deployed.
:return: A dictionary with service name as key and a dictionary containing command and volumes.
