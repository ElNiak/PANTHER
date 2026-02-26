# Task 04: Create Re-export Shims for panther-ivy-types

## Goal
Replace original type definitions in panther_ivy and ivy-lsp with re-export shims that import from `panther_ivy_types`, maintaining full backward compatibility.

## Prerequisites
- Task 02 completed (API types in panther_ivy_types/api.py)
- Task 03 completed (analysis/scope types in panther_ivy_types/)

## Context
Three source files need to become re-export shims:
1. `panther_ivy/api/types.py` - currently defines 6 dataclasses
2. `ivy-lsp/ivy_lsp/analysis/requirement_graph.py` - currently defines RequirementNode, StateVarNode inline
3. `ivy-lsp/ivy_lsp/analysis/test_scope.py` - currently defines ExportImportInfo, TestScope inline

After this task, all three files import from `panther_ivy_types` instead of defining types locally. Existing consumers that import from these files see no change.

## Steps

### Step 1: Update panther_ivy/api/types.py

Replace the entire file content with re-exports:

```python
# panther/plugins/services/testers/panther_ivy/api/types.py
"""Data types for the panther_ivy public API.

Re-exported from panther_ivy_types for backward compatibility.
Canonical source: panther_ivy_types.api
"""
from panther_ivy_types.api import (  # noqa: F401
    CommandResult,
    CompileResult,
    DiagnosticItem,
    ExecutionResult,
    TestInfo,
    TestRunResult,
)

__all__ = [
    "CommandResult",
    "CompileResult",
    "DiagnosticItem",
    "ExecutionResult",
    "TestInfo",
    "TestRunResult",
]
```

### Step 2: Update ivy-lsp requirement_graph.py

In `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/requirement_graph.py`:

Replace the local RequirementNode and StateVarNode dataclass definitions with imports from panther_ivy_types. Keep ActionNode, PropertyNode, EdgeType, and RequirementGraph as-is.

**Before** (lines 1-97):
```python
from __future__ import annotations
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from ivy_lsp.semantic.nodes import RfcRequirement

# ... logger ...

@dataclass
class RequirementNode:
    # ... 15 lines of definition ...

@dataclass
class StateVarNode:
    # ... 12 lines of definition ...

@dataclass
class ActionNode:
    # ... (keep as-is) ...
```

**After**:
```python
from __future__ import annotations
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from panther_ivy_types.analysis import RequirementNode, StateVarNode  # noqa: F401

if TYPE_CHECKING:
    from ivy_lsp.semantic.nodes import RfcRequirement

# ... logger ...

# RequirementNode and StateVarNode are imported from panther_ivy_types above.
# They are re-exported for backward compatibility.

@dataclass
class ActionNode:
    # ... (unchanged) ...
```

**Critical**: The rest of requirement_graph.py (ActionNode, PropertyNode, EdgeType, RequirementGraph) must remain UNCHANGED.

### Step 3: Update ivy-lsp test_scope.py

In `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/test_scope.py`:

Replace local ExportImportInfo and TestScope dataclass definitions with imports from panther_ivy_types. Keep all functions and ScopedRequirementModel as-is.

**Before** (lines 1-50):
```python
from __future__ import annotations
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set

from ivy_lsp.analysis.requirement_graph import RequirementGraph, RequirementNode

# ... logger ...

@dataclass
class ExportImportInfo:
    # ... definition ...

@dataclass(frozen=True)
class TestScope:
    # ... definition ...

def detect_test_role(...):
    # ... (keep as-is) ...
```

**After**:
```python
from __future__ import annotations
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set

from panther_ivy_types.analysis import RequirementNode  # noqa: F401 (re-exported)
from panther_ivy_types.scope import ExportImportInfo, TestScope  # noqa: F401

from ivy_lsp.analysis.requirement_graph import RequirementGraph

# ... logger ...

# ExportImportInfo and TestScope are imported from panther_ivy_types above.
# RequirementNode is also re-imported from panther_ivy_types.

def detect_test_role(...):
    # ... (unchanged) ...
```

**Critical**: Note that `RequirementNode` was previously imported from `ivy_lsp.analysis.requirement_graph`. Now it comes from `panther_ivy_types.analysis`. The `RequirementGraph` import stays from ivy-lsp since that class is NOT extracted.

### Step 4: Verify no other files import the old types directly

Search for imports that reference the old locations:
```bash
# Check for direct imports of types from panther_ivy.api.types
grep -rn "from panther_ivy.api.types import\|from panther.plugins.services.testers.panther_ivy.api.types import" panther/ --include="*.py"

# Check for imports from ivy_lsp.analysis.requirement_graph that get RequirementNode/StateVarNode
grep -rn "from ivy_lsp.analysis.requirement_graph import.*RequirementNode\|from ivy_lsp.analysis.requirement_graph import.*StateVarNode" panther/ --include="*.py"

# Check for imports from ivy_lsp.analysis.test_scope that get ExportImportInfo/TestScope
grep -rn "from ivy_lsp.analysis.test_scope import.*ExportImportInfo\|from ivy_lsp.analysis.test_scope import.*TestScope" panther/ --include="*.py"
```

Any hits need to be updated to either:
- Import from `panther_ivy_types` directly (preferred), OR
- Continue importing from the shim files (backward compatible)

## Verification
```bash
# 1. Verify panther_ivy re-exports work
python -c "from panther_ivy.api.types import DiagnosticItem; print(DiagnosticItem.__module__)"
# Should print: panther_ivy_types.api

# 2. Verify ivy-lsp imports work (from within the ivy-lsp directory context)
python -c "from ivy_lsp.analysis.requirement_graph import RequirementNode; print(RequirementNode.__module__)"
# Should print: panther_ivy_types.analysis

# 3. Verify backward compatibility - all old import paths still work
python -c "
from panther_ivy.api.types import CommandResult, CompileResult, TestRunResult, DiagnosticItem, TestInfo, ExecutionResult
print('panther_ivy imports OK')
"
```

## Important Notes

- The ivy-lsp files are inside a git submodule. Modifying them means the submodule will show as dirty. This is expected - the submodule pointer will be updated when ivy-lsp is committed.
- `panther_ivy_types` must be installed (`pip install -e packages/panther-ivy-types/`) BEFORE the shims will work, since they import from it.
- The `# noqa: F401` comments suppress flake8 "imported but unused" warnings for re-exports.

## Commit Message
```
refactor: replace type definitions with panther-ivy-types re-exports

Update panther_ivy/api/types.py, requirement_graph.py, and
test_scope.py to import types from panther_ivy_types package instead
of defining them locally. All existing import paths remain backward
compatible via re-exports.
```

## Files Modified
- `panther/plugins/services/testers/panther_ivy/api/types.py` (rewritten as re-export shim)
- `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/requirement_graph.py` (replace local dataclasses with imports)
- `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/ivy_lsp/analysis/test_scope.py` (replace local dataclasses with imports)
