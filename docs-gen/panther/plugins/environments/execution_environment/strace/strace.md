#


## StraceEnvironment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/strace/strace.py/#L18)
```python
StraceEnvironment(
   env_config_to_test: StraceConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```




**Methods:**


### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/strace/strace.py/#L34)
```python
.setup_environment(
   services_managers: list[IServiceManager], test_config: TestConfig,
   global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader
)
```


### .to_command
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/strace/strace.py/#L58)
```python
.to_command(
   pid: (int|None) = None
)
```

---
Generate the strace command for execution.
:param pid: Optional process ID to attach to.
:return: Strace command as a string.
