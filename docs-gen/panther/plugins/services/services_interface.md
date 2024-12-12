#


## IServiceManager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L73)
```python
IServiceManager(
   service_config_to_test: ServiceConfig, service_type: str,
   protocol: ProtocolConfig, implementation_name: str
)
```


---
IServiceManager is an interface for managing services within the PANTHER-SCP framework. It extends the IPlugin class and provides methods for initializing and rendering commands, as well as generating various types of commands required for service deployment and execution.


**Attributes**

* **available_types** (list) : List of valid service types.
* **service_type** (str) : Type of the service (e.g., "testers", "iut").
* **templates_dir** (str) : Directory path for service templates.
* **config_versions_dir** (str) : Directory path for service configuration versions.
* **plugin_loader** (Optional[PluginLoader]) : Loader for the plugin.
* **service_config_to_test** (ServiceConfig) : Configuration for the service to be tested.
* **jinja_env** (Environment) : Jinja2 environment for template rendering.
* **implementation_name** (str) : Name of the service implementation.
* **service_name** (str) : Name of the service.
* **service_protocol** (ProtocolConfig) : Protocol configuration for the service.
* **service_targets** (str) : Targets for the service.
* **service_version** (str) : Version of the service.
* **working_dir** (Optional[str]) : Working directory for the service.
* **process** (Optional[subprocess.Popen]) : Process for the service.
* **available_roles** (list) : List of available roles for the service.
* **volumes** (list) : List of volumes for the service.
* **role** (str) : Role of the service.
* **environments** (dict) : Environment variables for the service.
* **run_cmd** (dict) : Dictionary containing commands for various stages of service execution.

---
Methods:
    generate_deployment_commands(service_params: ServiceConfig, environment: str) -> Dict[str, str]: Abstract method to generate deployment commands based on service parameters.


**Methods:**


### .render_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L192)
```python
.render_commands(
   params, template_name
)
```


### .get_service_name
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L204)
```python
.get_service_name()
```


### .initialize_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L208)
```python
.initialize_commands()
```

---
Initializes and generates a dictionary of commands to be executed at different stages
of the process (pre-compile, compile, post-compile, pre-run, run, post-run).

The dictionary keys are:
- "pre_compile_cmds": Commands to be executed before compilation.
- "compile_cmds": Commands to be executed during compilation.
- "post_compile_cmds": Commands to be executed after compilation.
- "pre_run_cmds": Commands to be executed before running.
- "run_cmd": Command to be executed to run the main process.
- "post_run_cmds": Commands to be executed after running.


**Returns**

* **dict**  : A dictionary containing the commands for each stage.


### .generate_pre_compile_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L235)
```python
.generate_pre_compile_commands()
```

---
Generates a list of shell commands to be executed before compilation.

**Returns**

* **list**  : A list of strings, each representing a shell command.


### .generate_compile_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L249)
```python
.generate_compile_commands()
```

---
This method generates and returns a list of compile commands.
Generates compile commands.


**Returns**

* **list**  : An empty list representing the compile commands.


### .generate_post_compile_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L259)
```python
.generate_post_compile_commands()
```

---
Generate a list of post-compile commands.
This method returns an empty list of strings representing commands
to be executed after the compilation process.

**Returns**

* An empty list of post-compile commands.


### .generate_pre_run_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L270)
```python
.generate_pre_run_commands()
```

---
Generates a list of pre-run commands.
This method returns an empty list of strings, which can be overridden by subclasses
to provide specific pre-run commands required for their execution context.

**Returns**

* An empty list of strings representing pre-run commands.


### .generate_run_command
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L281)
```python
.generate_run_command()
```

---
Generates a dictionary containing the run command configuration.

**Returns**

* **dict**  : A dictionary with the following keys:
* The working directory for the command.
* The binary or executable to run.
* The arguments to pass to the command.
* The timeout value for the command execution.
* The environment variables for the command.


### .generate_post_run_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L301)
```python
.generate_post_run_commands()
```

---
Generates post-run commands.

### .get_implementation_name
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L307)
```python
.get_implementation_name()
```


### .is_tester
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L310)
```python
.is_tester()
```

---
Returns True if the plugin is a network service.

### .prepare
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L317)
```python
.prepare(
   plugin_loader: (PluginLoader|None) = None
)
```

---
Builds the Docker image for the implementation based on the environment.

### .generate_deployment_commands
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L324)
```python
.generate_deployment_commands(
   service_params: ServiceConfig, environment: str
)
```

---
Generates deployment commands based on service parameter

----


### validate_cmd
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L26)
```python
.validate_cmd(
   func
)
```


----


### validate_structure
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/services_interface.py/#L35)
```python
.validate_structure(
   data, schema, path = 'root'
)
```

---
Recursively validates a dictionary or list structure against a schema.


**Args**

* **data**  : The data to validate.
* **schema**  : The expected schema structure.
* **path**  : The current path in the nested structure (for error messages).


**Raises**

* **ValueError**  : If the structure does not match the schema.
* **TypeError**  : If a value does not match the expected type.

