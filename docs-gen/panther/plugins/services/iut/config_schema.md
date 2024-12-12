#


## Parameter
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/config_schema.py/#L6)
```python
Parameter()
```



----


## VersionBase
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/config_schema.py/#L12)
```python
VersionBase()
```



----


## ImplementationConfig
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/config_schema.py/#L25)
```python
ImplementationConfig()
```


---
ImplementationConfig class represents the configuration for an implementation.


**Attributes**

* **name** (str) : The name of the implementation (e.g., picoquic, panther_ivy).
* **type** (ImplementationType) : The type of implementation, must be either "iut" or "testers".
* **shadow_compatible** (bool) : Indicates if the implementation is compatible with shadow. This field must be ignored by OmegaConf.
* **gperf_compatible** (bool) : Indicates if the implementation is compatible with gperf.

