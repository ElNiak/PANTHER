# Modifications for Task REFACTOR_IVY_001: Refactor panther_ivy.py Command Generation

## Core Files to Modify

### panther/plugins/services/testers/panther_ivy/panther_ivy.py
- [ ] Lines 287-345: DELETE generate_pre_compile_commands() - Replace with delegation
- [ ] Lines 347-384: DELETE generate_compile_commands() - Replace with delegation
- [ ] Lines 386-421: DELETE generate_run_command() - Replace with delegation
- [ ] Lines 423-437: DELETE generate_pre_run_commands() - Replace with delegation
- [ ] Lines 439-456: DELETE generate_post_compile_commands() - Replace with delegation
- [ ] Lines 458-494: DELETE generate_compilation_commands() - Replace with delegation
- [ ] Lines 496-525: DELETE _build_ivy_update_commands()
- [ ] Lines 527-550: DELETE _build_quic_setup_commands()
- [ ] Lines 552-561: DELETE _build_ivy_model_setup_commands()
- [ ] Lines 563-620: DELETE build_tests() - Replace with delegation
- [ ] Lines 622-761: DELETE generate_deployment_commands() - Replace with delegation
- [ ] Lines 763-787: DELETE generate_post_run_commands() - Replace with delegation
- [ ] Lines 789-791: MODIFY test_success() to potentially use test_executor
- [ ] Lines 803-1044: MODIFY analyze_outputs() to potentially use log_analyzer
- [ ] Lines 1046-1072: MODIFY analyze() to use output_manager if available
- [ ] Lines 1074-1091: MODIFY get_test_results() to use test_executor if available
- [ ] Lines 241-257: MODIFY _setup_volumes() to use environment_setup if available
- [ ] Lines 226-239: CONSIDER using protocol_handler for _get_protocol_name()
- [ ] Add new _get_build_dir() helper method
- [ ] Update class docstring to reflect modular architecture
- [ ] Remove unused imports after refactoring

### Component Integration Points (Optional Enhancements)

#### Using IvyLogAnalyzer
- [ ] Delegate analyze_outputs() logic to log_analyzer.analyze_all_outputs()
- [ ] Use log_analyzer for test success detection

#### Using IvyOutputManager  
- [ ] Delegate output organization to output_manager.get_organized_outputs()
- [ ] Use output_manager for file collection patterns

#### Using IvyTestExecutor
- [ ] Delegate _do_run_tests() to test_executor.execute_test()
- [ ] Use test_executor for test result aggregation

#### Using IvyEnvironmentSetup
- [ ] Delegate _setup_volumes() to environment_setup.get_docker_volumes()
- [ ] Use environment_setup for build_submodules() if applicable

#### Using IvyProtocolHandler
- [ ] Delegate _get_protocol_name() to protocol_handler.get_protocol_name()
- [ ] Use protocol_handler for protocol-specific configuration

## Expected Line Count Changes
- **Lines to Remove**: ~500 lines (287-787)
- **Lines to Add**: ~100 lines (delegation methods)
- **Net Reduction**: ~400 lines

## Import Changes
### Imports to Remove (if unused after refactoring)
```python
# Remove if no longer needed:
import subprocess
import re
from typing import List
```

### Imports to Keep
```python
# Keep these as they're used elsewhere:
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING
```