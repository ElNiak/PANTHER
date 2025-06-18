# Plugin Config Migration Report

Found 0 files importing plugin configs from core models:


# Duplicate Config Definitions Found

## GperfCpuConfig defined in multiple locations:
  - /Users/elniak/Documents/Project/PANTHER/tests/tests_ressources/fake_plugins/fake_exec_plugin/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/plugins/environments/execution_environment/gperf_cpu/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/panther/config/core/models/environment.py
  - /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/execution_environment/gperf_cpu/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/plugins/environments/execution_environment/gperf_cpu/config_schema.py
## DockerComposeConfig defined in multiple locations:
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/config/config_manager.py
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/plugins/environments/network_environment/docker_compose/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/panther/config/core/models/environment.py
  - /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/network_environment/docker_compose/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/config/config_manager.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/plugins/environments/network_environment/docker_compose/config_schema.py
## LocalhostSingleContainerConfig defined in multiple locations:
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/plugins/environments/network_environment/localhost_single_container/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/panther/config/core/models/environment.py
  - /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/network_environment/localhost_single_container/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/plugins/environments/network_environment/localhost_single_container/config_schema.py
## GperfHeapConfig defined in multiple locations:
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/plugins/environments/execution_environment/gperf_heap/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/panther/config/core/models/environment.py
  - /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/execution_environment/gperf_heap/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/plugins/environments/execution_environment/gperf_heap/config_schema.py
## MemcheckConfig defined in multiple locations:
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/plugins/environments/execution_environment/memcheck/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/panther/config/core/models/environment.py
  - /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/execution_environment/memcheck/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/plugins/environments/execution_environment/memcheck/config_schema.py
## HelgrindConfig defined in multiple locations:
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/plugins/environments/execution_environment/helgrind/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/panther/config/core/models/environment.py
  - /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/execution_environment/helgrind/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/plugins/environments/execution_environment/helgrind/config_schema.py
## StraceConfig defined in multiple locations:
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/plugins/environments/execution_environment/strace/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/panther/config/core/models/environment.py
  - /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/execution_environment/strace/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/plugins/environments/execution_environment/strace/config_schema.py
## IterationsConfig defined in multiple locations:
  - /Users/elniak/Documents/Project/PANTHER/.venv/lib/python3.11/site-packages/panther/plugins/environments/execution_environment/iterations/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/panther/config/core/models/environment.py
  - /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/execution_environment/iterations/config_schema.py
  - /Users/elniak/Documents/Project/PANTHER/build/lib/panther/plugins/environments/execution_environment/iterations/config_schema.py