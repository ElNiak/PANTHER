#


## PicoquicShadowVersion
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/config_schema.py/#L12)
```python
PicoquicShadowVersion()
```



----


## PicoquicShadowConfig
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/config_schema.py/#L21)
```python
PicoquicShadowConfig()
```


---
PicoquicShadowConfig class is a configuration class for the PicoquicShadow implementation.

**Attributes**

* **name** (str) : Implementation name, default is "picoquic_shadow".
* **type** (ImplementationType) : Default type for picoquic, default is ImplementationType.iut.
* **shadow_compatible** (bool) : Indicates if the implementation is shadow compatible, default is True.
* **version** (PicoquicShadowVersion) : Version configuration loaded dynamically from YAML files.

---
Methods:
        Loads version configurations dynamically from YAML files located in the specified directory.


**Methods:**


### .load_versions_from_files
[source](https://github.com/ElNiak/PANTHER/blob/production/panther/plugins/services/iut/quic/picoquic_shadow/config_schema.py/#L43)
```python
.load_versions_from_files(
   version_configs_dir: str = 'panther/plugins/services/iut/quic/picoquic/version_configs/'
)
```

---
Load version configurations dynamically from YAML files.
