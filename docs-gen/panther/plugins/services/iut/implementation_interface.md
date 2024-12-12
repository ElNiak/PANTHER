#


## IImplementationManager
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/implementation_interface.py/#L7)
```python
IImplementationManager(
   service_config_to_test: ServiceConfig, service_type: str,
   protocol: ProtocolConfig, implementation_name: str
)
```


---
IImplementationManager is an abstract base class that inherits from IServiceManager and ABC.


**Attributes**

* **service_config_to_test** (ServiceConfig) : The configuration of the service to be tested.
* **service_type** (str) : The type of the service.
* **protocol** (ProtocolConfig) : The protocol configuration.
* **implementation_name** (str) : The name of the implementation.

---
Methods:
    __init__(service_config_to_test, service_type, protocol, implementation_name):
        Initializes the IImplementationManager with the given service configuration, service type, protocol, and implementation name.

    is_tester():
        Returns False indicating that this implementation is not a tester.


**Methods:**


### .is_tester
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/implementation_interface.py/#L36)
```python
.is_tester()
```

