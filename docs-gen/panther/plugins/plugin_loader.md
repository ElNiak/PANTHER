#


## PluginLoader
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_loader.py/#L10)
```python
PluginLoader(
   plugins_base_dir: str = 'panther/plugins', plugins_optional_dir: (str|None) = None
)
```


---
PluginLoader is responsible for discovering, registering, and building Docker images for protocol, environment, and tester plugins.

**Attributes**

* **logger** (logging.Logger) : Logger instance for the PluginLoader.
* **plugins_base_dir** (Path) : Base directory for plugins.
* **plugins_optional_dir** (Optional[Path]) : Optional directory for additional plugins.
* **docker_builder** (DockerBuilder) : Instance of DockerBuilder for building Docker images.
* **built_images** (Dict[str, str]) : Dictionary mapping implementation names to Docker image tags.
* **protocol_plugins** (Dict[str, Path]) : Dictionary mapping protocol plugin names to their paths.
* **environment_plugins** (Dict[str, Path]) : Dictionary mapping environment plugin names to their paths.
* **tester_plugins** (Dict[str, Path]) : Dictionary mapping tester plugin names to their paths.
* **dockerfiles** (Dict[str, Path]) : Dictionary mapping implementation names to Dockerfile paths.

---
Methods:
        Discovers and registers all protocol, environment, and tester plugins.


**Methods:**


### .get_class_name
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_loader.py/#L59)
```python
.get_class_name(
   plugin_name, suffix = 'Config'
)
```


### .build_docker_image
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_loader.py/#L65)
```python
.build_docker_image(
   impl_name: str, versions: str
)
```

---
Builds a Docker image for a given implementation and version.

:param impl_name: Name of the implementation.
:param version: Version of the implementation.

### .build_docker_image_from_path
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_loader.py/#L108)
```python
.build_docker_image_from_path(
   path: Path, name: str, version: (str|None) = None
)
```

---
Builds a Docker image for a given implementation and version.

:param impl_name: Name of the implementation.
:param version: Version of the implementation.

### .get_implementations_for_protocol
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_loader.py/#L143)
```python
.get_implementations_for_protocol(
   protocol: str
)
```

---
Retrieves a list of implementations under a given protocol.

:param protocol: Name of the protocol.
:return: List of implementation names.

### .get_testers
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_loader.py/#L170)
```python
.get_testers()
```

---
Retrieves a list of implementations under a given protocol.

:param protocol: Name of the protocol.
:return: List of implementation names.

### .load_plugins
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/plugin_loader.py/#L191)
```python
.load_plugins()
```

---
Discovers and registers all protocol and environment plugins.
