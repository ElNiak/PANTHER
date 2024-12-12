#


## ServiceConfig
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/config_schema.py/#L9)
```python
ServiceConfig()
```


---
ServiceConfig class represents the configuration for a service.


**Attributes**

* **name** (str) : Service name.
* **timeout** (int) : Timeout for the service. Defaults to 100.
* **implementation** (ImplementationConfig) : Implementation details. Defaults to an ImplementationConfig instance with name "implem_name".
* **protocol** (ProtocolConfig) : Protocol configuration. Defaults to a ProtocolConfig instance.
* **ports** (List[str]) : List of ports. Defaults to an empty list.
* **generate_new_certificates** (bool) : Flag to generate new certificates. Defaults to False.
* **volumes** (List[str]) : List of volumes. Defaults to an empty list.
* **directories_to_start** (List[str]) : List of directories to start. Defaults to an empty list.

