#


## GperfHeapEnvironment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/gperf_heap/gperf_heap.py/#L18)
```python
GperfHeapEnvironment(
   env_config_to_test: GperfHeapConfig, output_dir: str, env_type: str,
   env_sub_type: str, event_manager: EventManager
)
```




**Methods:**


### .setup_environment
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/gperf_heap/gperf_heap.py/#L33)
```python
.setup_environment(
   services_managers: list[IServiceManager], test_config: TestConfig,
   global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader
)
```


### .to_command
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/environments/execution_environment/gperf_heap/gperf_heap.py/#L67)
```python
.to_command(
   service_name: str
)
```

---
Generate the gperf command based on the configuration.
