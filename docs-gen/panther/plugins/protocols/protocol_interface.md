#


## IProtocolManager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/protocols/protocol_interface.py/#L8)
```python
IProtocolManager(
   service_type: str
)
```


---
IProtocolManager is a class that manages protocol configurations for a given service type.


**Attributes**

* **service_config_to_test_path** (str) : The path to the service configuration file.
* **service_config_to_test** (dict) : The loaded configuration data.

---
Methods:
        Loads the YAML configuration file and returns its contents as a dictionary.


**Methods:**


### .validate_config
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/protocols/protocol_interface.py/#L36)
```python
.validate_config()
```

---
Validates the configuration file.

### .load_config
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/protocols/protocol_interface.py/#L42)
```python
.load_config()
```

---
Loads the YAML configuration file.
