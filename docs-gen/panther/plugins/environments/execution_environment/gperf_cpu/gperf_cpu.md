#


## GperfCpuEnvironment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/gperf_cpu/gperf_cpu.py/#L16)
```python
GperfCpuEnvironment(
   env_config_to_test: GperfCpuConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```




**Methods:**


### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/gperf_cpu/gperf_cpu.py/#L31)
```python
.setup_environment(
   services_managers: list[IServiceManager], test_config: TestConfig,
   global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader
)
```


### .to_command
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/gperf_cpu/gperf_cpu.py/#L66)
```python
.to_command(
   service_name: str
)
```

---
Generate the gperf command based on the configuration.
