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


### load_config
```python
.load_config(
   config_path
)
```


----


### execute_command
```python
.execute_command(
   command
)
```


----


### get_current_branch
```python
.get_current_branch()
```


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


### create_docker_compose_config
```python
.create_docker_compose_config()
```


----


### start_tool
```python
.start_tool(
   config_file
)
```


----


### monitor_docker_usage
```python
.monitor_docker_usage(
   container_name, interval = 1.0, duration = 10.0
)
```

---
Monitor the CPU and memory usage of a Docker container.

:param container_name: Name or ID of the Docker container to monitor
:param interval: Time interval (in seconds) between checks
:param duration: Total duration (in seconds) to monitor

----


### update_docker_compose
```python
.update_docker_compose(
   config_file, yaml_path = 'docker-compose.yml'
)
```


----


### install_tool
```python
.install_tool(
   config_file, branch = None
)
```


----


### clean_tool
```python
.clean_tool(
   config_file
)
```


----


### build_ivy_webapp
```python
.build_ivy_webapp()
```


----


### build_worker
```python
.build_worker(
   implem, config_file
)
```


----


### build_docker_visualizer
```python
.build_docker_visualizer()
```


----


### stop_tool
```python
.stop_tool()
```


----


### get_nproc
```python
.get_nproc()
```

---
Get the number of processors available.

----


### start_bash_container
```python
.start_bash_container(
   implem
)
```

---
Start a Docker container with the specified parameters.

----


### cli
```python
.cli()
```

