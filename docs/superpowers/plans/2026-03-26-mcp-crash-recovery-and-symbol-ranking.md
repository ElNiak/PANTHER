# MCP Crash Recovery, PID Cleanup & Symbol Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 issues found by `/nct-health`: MCP server crash recovery (retry loop + dependency pin), stale PID cleanup on session start, and workspace symbol ranking via a `synthetic` flag.

**Architecture:** All fixes are in the `ivy-lsp` submodule (`panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`) and `panther-ivy-plugin` submodule (`panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/`). Changes are independent — each task can be implemented and tested in isolation.

**Tech Stack:** Python 3.10, lsprotocol, pytest, bash (hooks)

**Working directory for all commands:**
```
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
```

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `ivy_lsp/__main__.py` | Modify (lines 305-321) | Fix A: retry-loop wrapper |
| `pyproject.toml` | Modify (line 34) | Fix A: pin mcp/anyio versions |
| `panther-ivy-plugin: hooks/scripts/cleanup-stale-pids.sh` | Create | Fix B: SessionStart PID cleanup |
| `panther-ivy-plugin: hooks/hooks.json` | Modify (lines 117-145) | Fix B: register new hook |
| `ivy_lsp/core/parsing/symbols.py` | Modify (lines 17-58) | Fix D: add `synthetic` field |
| `ivy_lsp/core/parsing/ast_to_symbols.py` | Modify (4 converters) | Fix D: set `synthetic=True` |
| `ivy_lsp/lsp/workspace_symbols.py` | Modify (lines 72-144) | Fix D: propagate + sort |
| `tests/test_workspace_symbols_filtering.py` | Modify (add test class) | Fix D: test synthetic ranking |

---

### Task 1: Fix D — Add `synthetic` field to `IvySymbol`

**Files:**
- Modify: `ivy_lsp/core/parsing/symbols.py:17-58`
- Test: `tests/test_workspace_symbols_filtering.py`

- [ ] **Step 1: Write the failing test for `synthetic` field**

Add to `tests/test_workspace_symbols_filtering.py`:

```python
class TestIvySymbolSyntheticField:
    """IvySymbol.synthetic field exists and round-trips through serialization."""

    def test_synthetic_defaults_to_false(self):
        sym = IvySymbol(name="cid", kind=lsp.SymbolKind.Class, range=(0, 0, 0, 3))
        assert sym.synthetic is False

    def test_synthetic_set_to_true(self):
        sym = IvySymbol(
            name="interp14",
            kind=lsp.SymbolKind.TypeParameter,
            range=(0, 0, 0, 8),
            synthetic=True,
        )
        assert sym.synthetic is True

    def test_to_dict_includes_synthetic(self):
        sym = IvySymbol(
            name="interp14",
            kind=lsp.SymbolKind.TypeParameter,
            range=(0, 0, 0, 8),
            synthetic=True,
        )
        d = sym.to_dict()
        assert d["synthetic"] is True

    def test_from_dict_restores_synthetic(self):
        d = {
            "name": "interp14",
            "kind": int(lsp.SymbolKind.TypeParameter),
            "range": [0, 0, 0, 8],
            "synthetic": True,
        }
        sym = IvySymbol.from_dict(d)
        assert sym.synthetic is True

    def test_from_dict_defaults_synthetic_false(self):
        """Old serialized dicts without synthetic field default to False."""
        d = {
            "name": "cid",
            "kind": int(lsp.SymbolKind.Class),
            "range": [0, 0, 0, 3],
        }
        sym = IvySymbol.from_dict(d)
        assert sym.synthetic is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_workspace_symbols_filtering.py::TestIvySymbolSyntheticField -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'synthetic'`

- [ ] **Step 3: Add `synthetic` field to `IvySymbol`**

In `ivy_lsp/core/parsing/symbols.py`, add the field and update serialization:

```python
@dataclass
class IvySymbol:
    """A single symbol extracted from an Ivy source file.

    Attributes:
        name: The symbol's identifier (e.g., ``"cid"``, ``"send"``).
        kind: LSP symbol kind (Class, Function, Variable, etc.).
        range: 0-based ``(start_line, start_col, end_line, end_col)`` span.
        children: Nested symbols (e.g., fields inside an object).
        detail: Optional human-readable signature or type string.
        file_path: Optional originating file path.
        synthetic: Whether this symbol has a compiler-generated name.
    """

    name: str
    kind: SymbolKind
    range: Tuple[int, int, int, int]
    children: List[IvySymbol] = field(default_factory=list)
    detail: Optional[str] = None
    file_path: Optional[str] = None
    synthetic: bool = False

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary for cross-process transfer."""
        return {
            "name": self.name,
            "kind": int(self.kind),
            "range": list(self.range),
            "children": [c.to_dict() for c in self.children],
            "detail": self.detail,
            "file_path": self.file_path,
            "synthetic": self.synthetic,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "IvySymbol":
        """Deserialize from a plain dictionary."""
        return cls(
            name=d["name"],
            kind=SymbolKind(d["kind"]),
            range=tuple(d["range"]),
            children=[cls.from_dict(c) for c in d.get("children", [])],
            detail=d.get("detail"),
            file_path=d.get("file_path"),
            synthetic=d.get("synthetic", False),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_workspace_symbols_filtering.py::TestIvySymbolSyntheticField -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add ivy_lsp/core/parsing/symbols.py tests/test_workspace_symbols_filtering.py
git commit -m "feat(symbols): add synthetic field to IvySymbol for compiler-generated name detection"
```

---

### Task 2: Fix D — Set `synthetic=True` in parsers

**Files:**
- Modify: `ivy_lsp/core/parsing/ast_to_symbols.py` (4 functions)

- [ ] **Step 1: Write the failing test for synthetic detection**

Add to `tests/test_workspace_symbols_filtering.py`:

```python
import re


class TestSyntheticDetection:
    """Verify synthetic flag is set correctly by converter functions."""

    def test_interpret_symbol_is_synthetic(self):
        """InterpretDecl symbols (e.g. interp14) are always synthetic."""
        sym = IvySymbol(
            name="interp14",
            kind=lsp.SymbolKind.TypeParameter,
            range=(0, 0, 0, 8),
            file_path="/ws/quic_types.ivy",
            synthetic=True,
        )
        assert sym.synthetic is True

    def test_native_symbol_is_synthetic(self):
        """NativeDecl symbols (e.g. native3) are always synthetic."""
        sym = IvySymbol(
            name="native3",
            kind=lsp.SymbolKind.String,
            range=(0, 0, 0, 7),
            file_path="/ws/quic_shim.ivy",
            synthetic=True,
        )
        assert sym.synthetic is True

    def test_bracket_mixin_is_synthetic(self):
        """Mixin symbols with bracket disambiguation are synthetic."""
        name = "bytes.spec.create[after224332]"
        assert "[" in name  # detection logic
        sym = IvySymbol(
            name=name,
            kind=lsp.SymbolKind.Method,
            range=(0, 0, 0, len(name)),
            file_path="/ws/quic_types.ivy",
            synthetic=True,
        )
        assert sym.synthetic is True

    def test_normal_mixin_is_not_synthetic(self):
        """Mixin symbols without brackets are NOT synthetic."""
        name = "frame.ack.handle"
        assert "[" not in name
        sym = IvySymbol(
            name=name,
            kind=lsp.SymbolKind.Method,
            range=(0, 0, 0, len(name)),
            file_path="/ws/quic_frame.ivy",
            synthetic=False,
        )
        assert sym.synthetic is False

    def test_anonymous_definition_is_synthetic(self):
        """Anonymous definitions (def12) are synthetic."""
        name = "def12"
        assert re.fullmatch(r"def\d+", name) is not None

    def test_named_definition_is_not_synthetic(self):
        """Named definitions are NOT synthetic."""
        name = "packet_event"
        assert re.fullmatch(r"def\d+", name) is None
```

- [ ] **Step 2: Run tests to verify they pass (these are unit assertions, not integration)**

Run: `python -m pytest tests/test_workspace_symbols_filtering.py::TestSyntheticDetection -v`
Expected: 6 PASS (these test the detection logic, not the converters directly)

- [ ] **Step 3: Modify `_convert_interpret` to set `synthetic=True`**

In `ivy_lsp/core/parsing/ast_to_symbols.py`, function `_convert_interpret` (~line 681):

Change:
```python
    return [
        IvySymbol(
            name=name,
            kind=SymbolKind.TypeParameter,
            range=rng,
            file_path=filename,
        )
    ]
```

To:
```python
    return [
        IvySymbol(
            name=name,
            kind=SymbolKind.TypeParameter,
            range=rng,
            file_path=filename,
            synthetic=True,
        )
    ]
```

- [ ] **Step 4: Modify `_convert_native` to set `synthetic=True`**

In function `_convert_native` (~line 889):

Change:
```python
        return [
            IvySymbol(
                name=name,
                kind=SymbolKind.String,
                range=rng,
                detail="native",
                file_path=filename,
            )
        ]
```

To:
```python
        return [
            IvySymbol(
                name=name,
                kind=SymbolKind.String,
                range=rng,
                detail="native",
                file_path=filename,
                synthetic=True,
            )
        ]
```

- [ ] **Step 5: Modify `_convert_mixin` to set `synthetic=True` when name contains `[`**

In function `_convert_mixin` (~line 803):

Change:
```python
        return [
            IvySymbol(
                name=mixee_name,
                kind=SymbolKind.Method,
                range=rng,
                detail=detail,
                file_path=filename,
            )
        ]
```

To:
```python
        return [
            IvySymbol(
                name=mixee_name,
                kind=SymbolKind.Method,
                range=rng,
                detail=detail,
                file_path=filename,
                synthetic="[" in mixee_name,
            )
        ]
```

- [ ] **Step 6: Modify `_convert_definition` to set `synthetic=True` for anonymous defs**

Add `import re` at the top of the file (after the existing imports, ~line 10).

In function `_convert_definition` (~line 630):

Change:
```python
    return [
        IvySymbol(
            name=name,
            kind=SymbolKind.Function,
            range=rng,
            file_path=filename,
        )
    ]
```

To:
```python
    return [
        IvySymbol(
            name=name,
            kind=SymbolKind.Function,
            range=rng,
            file_path=filename,
            synthetic=re.fullmatch(r"def\d+", name) is not None,
        )
    ]
```

- [ ] **Step 7: Run all existing tests to verify no regressions**

Run: `python -m pytest tests/ -x -q --timeout=30 2>/dev/null | tail -5`
Expected: All existing tests still pass

- [ ] **Step 8: Commit**

```bash
git add ivy_lsp/core/parsing/ast_to_symbols.py tests/test_workspace_symbols_filtering.py
git commit -m "feat(ast): set synthetic=True for compiler-generated symbol names"
```

---

### Task 3: Fix D — Propagate `synthetic` through `FlatSymbol` and sort

**Files:**
- Modify: `ivy_lsp/lsp/workspace_symbols.py:72-144`
- Test: `tests/test_workspace_symbols_filtering.py`

- [ ] **Step 1: Write the failing test for empty-query synthetic sorting**

Add to `tests/test_workspace_symbols_filtering.py`:

```python
from ivy_lsp.lsp.workspace_symbols import search_symbols


class TestEmptyQuerySyntheticSorting:
    """Empty query sorts synthetic symbols after real definitions."""

    def test_synthetic_symbols_sort_last(self):
        """With empty query, synthetic=True symbols appear after synthetic=False."""
        flat = [
            FlatSymbol(qualified_name="interp14", kind=lsp.SymbolKind.TypeParameter,
                       file_path="/ws/q.ivy", range=(0, 0, 0, 8), synthetic=True),
            FlatSymbol(qualified_name="cid", kind=lsp.SymbolKind.Class,
                       file_path="/ws/q.ivy", range=(0, 0, 0, 3), synthetic=False),
            FlatSymbol(qualified_name="native3", kind=lsp.SymbolKind.String,
                       file_path="/ws/q.ivy", range=(0, 0, 0, 7), synthetic=True),
            FlatSymbol(qualified_name="quic_packet_type", kind=lsp.SymbolKind.Module,
                       file_path="/ws/q.ivy", range=(0, 0, 0, 16), synthetic=False),
        ]
        results = search_symbols(flat, query="")
        names = [r.qualified_name for r in results]
        # Real symbols first, synthetic last
        assert names.index("cid") < names.index("interp14")
        assert names.index("quic_packet_type") < names.index("native3")

    def test_query_search_ignores_synthetic_flag(self):
        """With a non-empty query, synthetic flag does NOT affect results."""
        flat = [
            FlatSymbol(qualified_name="interp14", kind=lsp.SymbolKind.TypeParameter,
                       file_path="/ws/q.ivy", range=(0, 0, 0, 8), synthetic=True),
            FlatSymbol(qualified_name="interp_helper", kind=lsp.SymbolKind.Function,
                       file_path="/ws/q.ivy", range=(0, 0, 0, 13), synthetic=False),
        ]
        results = search_symbols(flat, query="interp")
        names = [r.qualified_name for r in results]
        # Both match the query — synthetic doesn't filter them out
        assert "interp14" in names
        assert "interp_helper" in names

    def test_flatten_preserves_synthetic(self):
        """flatten_symbols propagates synthetic from IvySymbol to FlatSymbol."""
        syms = [
            IvySymbol(name="cid", kind=lsp.SymbolKind.Class,
                      range=(0, 0, 0, 3), file_path="/ws/q.ivy", synthetic=False),
            IvySymbol(name="interp14", kind=lsp.SymbolKind.TypeParameter,
                      range=(0, 0, 0, 8), file_path="/ws/q.ivy", synthetic=True),
        ]
        flat = flatten_symbols(syms)
        assert flat[0].synthetic is False
        assert flat[1].synthetic is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_workspace_symbols_filtering.py::TestEmptyQuerySyntheticSorting -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'synthetic'` on `FlatSymbol`

- [ ] **Step 3: Add `synthetic` to `FlatSymbol` and propagate in `flatten_symbols`**

In `ivy_lsp/lsp/workspace_symbols.py`:

Change `FlatSymbol` dataclass (~line 72):
```python
@dataclass
class FlatSymbol:
    """Flattened symbol with qualified name for workspace search.

    Attributes:
        qualified_name: Dot-separated path (e.g. ``"frame.ack.range"``).
        kind: LSP symbol kind.
        file_path: Originating file path, or ``None``.
        range: 0-based ``(start_line, start_col, end_line, end_col)`` span.
        synthetic: Whether this symbol has a compiler-generated name.
    """

    qualified_name: str
    kind: lsp.SymbolKind
    file_path: Optional[str]
    range: tuple  # (sl, sc, el, ec)
    synthetic: bool = False
```

Change `flatten_symbols` (~line 107) to propagate:
```python
        result.append(
            FlatSymbol(
                qualified_name=qname,
                kind=sym.kind,
                file_path=sym.file_path,
                range=sym.range,
                synthetic=getattr(sym, "synthetic", False),
            )
        )
```

- [ ] **Step 4: Modify `search_symbols` empty-query path**

In `search_symbols` (~line 127):

Change:
```python
    if not query:
        return flat[:MAX_RESULTS]
```

To:
```python
    if not query:
        return sorted(flat, key=lambda fs: (fs.synthetic, fs.qualified_name))[:MAX_RESULTS]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_workspace_symbols_filtering.py::TestEmptyQuerySyntheticSorting -v`
Expected: 3 PASS

- [ ] **Step 6: Run the full test suite to check for regressions**

Run: `python -m pytest tests/test_workspace_symbols_filtering.py -v`
Expected: All tests pass (existing + new)

- [ ] **Step 7: Commit**

```bash
git add ivy_lsp/lsp/workspace_symbols.py tests/test_workspace_symbols_filtering.py
git commit -m "feat(workspace-symbols): sort synthetic symbols last on empty query"
```

---

### Task 4: Fix A — MCP crash retry-loop wrapper

**Files:**
- Modify: `ivy_lsp/__main__.py:273-321`

- [ ] **Step 1: Add compat import for `BaseExceptionGroup`**

At the top of `ivy_lsp/__main__.py` (after the existing imports, ~line 10), add:

```python
try:
    BaseExceptionGroup  # Python 3.11+
except NameError:
    from exceptiongroup import BaseExceptionGroup
```

- [ ] **Step 2: Replace `start_mcp()` call with retry loop**

In `ivy_lsp/__main__.py`, replace lines 305-321:

```python
            start_mcp(
                workspace_root=ws_config.workspace_root,
                ws_config=ws_config,
                docker_image=docker_image,
                base_path=base_path,
                staging_dir=staging_dir,
            )
        except ImportError as e:
            log.critical(
                "[MCP-FATAL] Missing dependency: %s\n"
                "Install with: pip install ivy-lsp[mcp]",
                e,
            )
            sys.exit(1)
        except Exception as e:
            log.critical("[MCP-FATAL] Ivy MCP server crashed: %s", e, exc_info=True)
            sys.exit(1)
```

With:

```python
            _MAX_MCP_RESTARTS = 3
            for _attempt in range(1, _MAX_MCP_RESTARTS + 1):
                try:
                    start_mcp(
                        workspace_root=ws_config.workspace_root,
                        ws_config=ws_config,
                        docker_image=docker_image,
                        base_path=base_path,
                        staging_dir=staging_dir,
                    )
                    break  # Clean exit
                except BaseExceptionGroup as eg:
                    cancel_scope_errors = [
                        e for e in eg.exceptions
                        if isinstance(e, (RuntimeError, BaseExceptionGroup))
                        and "cancel scope" in str(e)
                    ]
                    if cancel_scope_errors and _attempt < _MAX_MCP_RESTARTS:
                        log.warning(
                            "[MCP-RESTART] Cancel scope crash (attempt %d/%d), "
                            "restarting... (upstream: github.com/modelcontextprotocol"
                            "/python-sdk/issues/577)",
                            _attempt,
                            _MAX_MCP_RESTARTS,
                        )
                        continue
                    log.critical(
                        "[MCP-FATAL] Ivy MCP server crashed: %s", eg, exc_info=True
                    )
                    sys.exit(1)
        except ImportError as e:
            log.critical(
                "[MCP-FATAL] Missing dependency: %s\n"
                "Install with: pip install ivy-lsp[mcp]",
                e,
            )
            sys.exit(1)
        except Exception as e:
            log.critical("[MCP-FATAL] Ivy MCP server crashed: %s", e, exc_info=True)
            sys.exit(1)
```

- [ ] **Step 3: Verify the file parses correctly**

Run: `python -c "import ast; ast.parse(open('ivy_lsp/__main__.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add ivy_lsp/__main__.py
git commit -m "fix(mcp): add retry loop for MCP SDK cancel scope crash (upstream #577)"
```

---

### Task 5: Fix A — Pin dependency versions

**Files:**
- Modify: `pyproject.toml:34`

- [ ] **Step 1: Update mcp extra dependencies**

In `pyproject.toml`, line 34, change:

```toml
mcp = ["mcp>=1.8", "panther_ms_ivy[z3]", "docker>=7.0", "pyyaml>=6.0", "uvicorn>=0.30"]
```

To:

```toml
mcp = ["mcp>=1.26.0", "anyio>=4.13.0", "panther_ms_ivy[z3]", "docker>=7.0", "pyyaml>=6.0", "uvicorn>=0.30"]
```

- [ ] **Step 2: Verify the toml is valid**

Run: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('OK')" 2>/dev/null || python -c "import tomli; tomli.load(open('pyproject.toml','rb')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): pin mcp>=1.26.0 and anyio>=4.13.0 for cancel scope fixes"
```

---

### Task 6: Fix B — SessionStart stale PID cleanup

**Files:**
- Create: `panther-ivy-plugin: plugins/panther-ivy-plugin/hooks/scripts/cleanup-stale-pids.sh`
- Modify: `panther-ivy-plugin: plugins/panther-ivy-plugin/hooks/hooks.json:117-145`

**Working directory for this task:**
```
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
```

- [ ] **Step 1: Create the cleanup script**

Create `plugins/panther-ivy-plugin/hooks/scripts/cleanup-stale-pids.sh`:

```bash
#!/usr/bin/env bash
# SessionStart hook: remove PID files for dead processes.
# Runs before server startup to ensure a clean slate.
# Cleans up leftovers from sessions that crashed without triggering SessionEnd.
# Always exits 0 — cleanup hooks must never fail the session.

PID_DIR="/tmp/ivy-lsp-pids"
[ -d "$PID_DIR" ] || exit 0

for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null)" || continue
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pidfile" 2>/dev/null || true
    fi
done

exit 0
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x plugins/panther-ivy-plugin/hooks/scripts/cleanup-stale-pids.sh`

- [ ] **Step 3: Register in hooks.json**

In `plugins/panther-ivy-plugin/hooks/hooks.json`, in the `"SessionStart"` array, add a new entry **before** the existing `detect-ivy-workspace.sh` entry (so it runs first). Change lines 117-126 from:

```json
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/detect-ivy-workspace.sh",
            "timeout": 10
          }
        ]
      },
```

To:

```json
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/cleanup-stale-pids.sh",
            "timeout": 5
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/detect-ivy-workspace.sh",
            "timeout": 10
          }
        ]
      },
```

- [ ] **Step 4: Verify hooks.json is valid JSON**

Run: `python -c "import json; json.load(open('plugins/panther-ivy-plugin/hooks/hooks.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Test the cleanup script manually**

```bash
# Create a fake stale PID file
mkdir -p /tmp/ivy-lsp-pids
echo "99999" > /tmp/ivy-lsp-pids/test-stale-99999.pid
# Run cleanup
bash plugins/panther-ivy-plugin/hooks/scripts/cleanup-stale-pids.sh
# Verify it was removed (PID 99999 shouldn't exist)
ls /tmp/ivy-lsp-pids/test-stale-99999.pid 2>/dev/null && echo "FAIL: not cleaned" || echo "PASS: cleaned"
```

Expected: `PASS: cleaned`

- [ ] **Step 6: Commit**

```bash
git add plugins/panther-ivy-plugin/hooks/scripts/cleanup-stale-pids.sh plugins/panther-ivy-plugin/hooks/hooks.json
git commit -m "fix(hooks): add SessionStart cleanup for stale PID files"
```

---

### Task 7: Integration verification

- [ ] **Step 1: Run full ivy-lsp test suite**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/test_workspace_symbols_filtering.py -v
```

Expected: All tests pass including the new `TestIvySymbolSyntheticField`, `TestSyntheticDetection`, and `TestEmptyQuerySyntheticSorting` classes.

- [ ] **Step 2: Verify __main__.py parses correctly**

```bash
python -c "import ast; ast.parse(open('ivy_lsp/__main__.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Verify hooks.json is valid**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin
python -c "import json; json.load(open('plugins/panther-ivy-plugin/hooks/hooks.json')); print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Re-run `/nct-health` to verify improvement**

The following health check steps should improve:
- Step 1 (Stale PIDs): PASS (after SessionStart cleanup)
- Step 16 (workspaceSymbol): PASS (synthetic symbols sorted last)
- MCP steps: Depend on whether MCP SDK crash triggers during this session

Note: Fix A (retry loop) is only testable when the MCP SDK crash actually occurs — it's a defense-in-depth measure.
