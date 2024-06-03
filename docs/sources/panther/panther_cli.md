#


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
   command, tmux = None, cwd = None
)
```


----


### get_current_branch
```python
.get_current_branch()
```


----


### start_tool
```python
.start_tool(
   config, swarm = False
)
```


----


### install_tool
```python
.install_tool(
   config, branch = None
)
```


----


### clean_tool
```python
.clean_tool(
   config
)
```


----


### build_webapp
```python
.build_webapp(
   push = False
)
```


----


### build_worker
```python
.build_worker(
   implem, config, push = False
)
```


----


### build_docker_visualizer
```python
.build_docker_visualizer(
   push = False
)
```


----


### stop_tool
```python
.stop_tool()
```


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


### is_tmux_session
```python
.is_tmux_session()
```

---
Check if running inside a tmux session.
