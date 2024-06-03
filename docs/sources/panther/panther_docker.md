#


### log_docker_output
```python
.log_docker_output(
   generator, task_name: str = 'dockercommandexecution'
)
```

---
Log output to console from a generator returned from docker client
:param Any generator: The generator to log the output of
:param str task_name: A name to give the task, i.e. 'Build database image', used for logging

----


### container_exists
```python
.container_exists(
   client, container_name
)
```

---
Check if the Docker container exists.

----


### get_container_ip
```python
.get_container_ip(
   client, container_name
)
```

---
Get the IP address of the Docker container.

----


### get_panther_container
```python
.get_panther_container()
```


----


### push_image_to_registry
```python
.push_image_to_registry(
   image_name, registry_url = 'elniak', tag = 'latest'
)
```

---
Push a Docker image to a registry.

----


### restore_hosts_file
```python
.restore_hosts_file()
```

---
Restore the original /etc/hosts file from the backup.

----


### append_to_hosts_file
```python
.append_to_hosts_file(
   entry
)
```

---
Append a new entry to the /etc/hosts file.

----


### network_exists
```python
.network_exists(
   client, network_name
)
```

---
Check if the Docker network exists.

----


### create_network
```python
.create_network(
   client, network_name, gateway, subnet
)
```

---
Create a Docker network with the specified gateway and subnet.

----


### create_docker_network
```python
.create_docker_network()
```


----


### monitor_docker_usage
```python
.monitor_docker_usage(
   docker_to_monitor, interval = 1.0, duration = 10.0
)
```

---
Monitor the CPU and memory usage of a Docker container.

:param container_name: Name or ID of the Docker container to monitor
:param interval: Time interval (in seconds) between checks
:param duration: Total duration (in seconds) to monitor
