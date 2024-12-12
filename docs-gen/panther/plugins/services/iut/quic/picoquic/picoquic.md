#


## PicoquicServiceManager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic/picoquic.py/#L16)
```python
PicoquicServiceManager(
   service_config_to_test: PicoquicConfig, service_type: str,
   protocol: ProtocolConfig, implementation_name: str
)
```




**Methods:**


### .generate_run_command
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic/picoquic.py/#L35)
```python
.generate_run_command()
```

---
Generates the run command.

### .generate_post_run_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic/picoquic.py/#L52)
```python
.generate_post_run_commands()
```

---
Generates post-run commands.

### .prepare
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic/picoquic.py/#L60)
```python
.prepare(
   plugin_loader: (PluginLoader|None) = None
)
```

---
Prepare the service manager for use.

### .generate_deployment_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic/picoquic.py/#L83)
```python
.generate_deployment_commands()
```

---
Generates deployment commands and collects volume mappings based on service parameters.

:param service_params: Parameters specific to the service.
:param environment: The environment in which the services are being deployed.
:return: A dictionary with service name as key and a dictionary containing command and volumes.
