# Deletions for Task REFACTOR_IVY_001: Refactor panther_ivy.py Command Generation

## Methods to Delete from panther_ivy.py

### Command Generation Methods (Lines 287-787)
```python
# DELETE ENTIRE METHODS:

def generate_pre_compile_commands(self):  # Lines 287-345
    """Generates pre-compile commands."""
    # DELETE ENTIRE METHOD

def generate_compile_commands(self):  # Lines 347-384
    """Generates compile commands."""
    # DELETE ENTIRE METHOD

def generate_run_command(self):  # Lines 386-421
    """Generates the run command."""
    # DELETE ENTIRE METHOD

def generate_pre_run_commands(self):  # Lines 423-437
    """Generates pre-run commands using the new chain architecture."""
    # DELETE ENTIRE METHOD

def generate_post_compile_commands(self):  # Lines 439-456
    """Generates post-compile commands using the new chain architecture."""
    # DELETE ENTIRE METHOD

def generate_compilation_commands(self) -> List[str]:  # Lines 458-494
    """Generates compilation commands using structured approach."""
    # DELETE ENTIRE METHOD

def _build_ivy_update_commands(self) -> List[str]:  # Lines 496-525
    """Build Ivy tool update commands using structured approach."""
    # DELETE ENTIRE METHOD

def _build_quic_setup_commands(self) -> List[str]:  # Lines 527-550
    """Build QUIC-specific setup commands."""
    # DELETE ENTIRE METHOD

def _build_ivy_model_setup_commands(self) -> List[str]:  # Lines 552-561
    """Build Ivy model setup commands."""
    # DELETE ENTIRE METHOD

def build_tests(self, test_name=None) -> List[str]:  # Lines 563-620
    """Builds test compilation commands."""
    # DELETE ENTIRE METHOD

def generate_deployment_commands(self) -> str:  # Lines 622-761
    """Generates deployment command arguments for Ivy test execution."""
    # DELETE ENTIRE METHOD

def generate_post_run_commands(self):  # Lines 763-787
    """Generates post-run commands."""
    # DELETE ENTIRE METHOD
```

## Code Blocks to Remove

### Duplicate Logic Patterns
- [ ] Remove any inline command building logic that's now in IvyCommandGenerator
- [ ] Remove IP resolution command construction (now in component)
- [ ] Remove template parameter building (now in component)
- [ ] Remove path construction logic that's duplicated

### Legacy Comments to Clean
- [ ] Remove TODO comments related to command generation
- [ ] Remove commented-out code blocks in deleted method areas
- [ ] Remove obsolete inline comments about command building

## Import Statements to Remove (if unused)
```python
# Check if these imports are still needed after refactoring:
import subprocess  # If only used in build_submodules, keep it
import re  # If not used elsewhere, remove
```

## Total Lines to Delete
- **Method Deletions**: ~500 lines
- **Command generation logic**: Lines 287-787
- **Net deletion**: ~500 lines of duplicate code

## Validation After Deletion
1. Ensure no orphaned references to deleted methods
2. Verify all command generation flows through IvyCommandGenerator
3. Check that no command building logic remains in main class
4. Confirm all tests still pass with delegated implementation