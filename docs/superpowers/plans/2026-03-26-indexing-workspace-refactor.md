# Indexing & Workspace Management Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix O(N) symbol lookups, consolidate 5 divergent session ID resolution paths into one canonical function, extract duplicated reference extraction code, and remove dead code/fix bugs across ivy-lsp and panther-ivy-plugin.

**Architecture:** 3 independent workstreams (indexing, state, cleanup) implemented in 10 phases. Workstream 1 touches only ivy-lsp. Workstream 2 bridges both repos. Workstream 3 is independent fixes. All changes are TDD where applicable.

**Tech Stack:** Python 3.10+, pytest, lsprotocol, pygls, asyncio. Shell scripts (bash) for plugin hooks.

**Spec:** `docs/superpowers/specs/2026-03-26-indexing-workspace-refactor-design.md`

**Coordination note:** The plan `2026-03-26-ivy-health-check-bugs.md` also modifies `mcp/tools/analysis.py` (different section: probe_tiers timeout vs legacy flat keys) and addresses circuit breaker behavior (server.py reset vs plugin hooks locking). Run that plan first or coordinate merge order.

**Base paths:**
- **IVY-LSP:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
- **PLUGIN:** `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

---

## Phase 1: SemanticModel Name Index + Version Counter (1A + 1G)

### Task 1: Add `_nodes_by_name` index to SemanticModel

**Files:**
- Modify: `IVY-LSP/ivy_lsp/core/semantic/model.py`
- Test: `IVY-LSP/tests/test_semantic_model.py` (extend)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_semantic_model.py`:

```python
class TestNodesByNameIndex:
    """Tests for the _nodes_by_name O(1) lookup index."""

    def _make_node(self, node_id, name, file=None, tier=None):
        """Create a minimal node with required attributes."""
        from types import SimpleNamespace
        return SimpleNamespace(id=node_id, name=name, file=file, tier=tier)

    def test_get_nodes_by_name_returns_matching(self):
        model = SemanticModel()
        n1 = self._make_node("n1", "send", file="a.ivy")
        n2 = self._make_node("n2", "recv", file="a.ivy")
        n3 = self._make_node("n3", "send", file="b.ivy")
        model.add_node(n1)
        model.add_node(n2)
        model.add_node(n3)
        result = model.get_nodes_by_name("send")
        assert len(result) == 2
        assert {r.id for r in result} == {"n1", "n3"}

    def test_get_nodes_by_name_empty_for_missing(self):
        model = SemanticModel()
        assert model.get_nodes_by_name("nonexistent") == []

    def test_remove_file_cleans_name_index(self):
        model = SemanticModel()
        n1 = self._make_node("n1", "send", file="a.ivy")
        n2 = self._make_node("n2", "send", file="b.ivy")
        model.add_node(n1)
        model.add_node(n2)
        model.remove_file("a.ivy")
        result = model.get_nodes_by_name("send")
        assert len(result) == 1
        assert result[0].id == "n2"

    def test_add_node_replace_updates_name_index(self):
        """Replacing a node with a different name must clean old name entry."""
        model = SemanticModel()
        n1 = self._make_node("n1", "old_name", file="a.ivy")
        model.add_node(n1)
        assert len(model.get_nodes_by_name("old_name")) == 1

        n1_updated = self._make_node("n1", "new_name", file="a.ivy")
        model.add_node(n1_updated)
        assert model.get_nodes_by_name("old_name") == []
        assert len(model.get_nodes_by_name("new_name")) == 1

    def test_pickle_backward_compat_rebuilds_name_index(self):
        """Old pickled models without _nodes_by_name should rebuild on load."""
        import pickle
        model = SemanticModel()
        n1 = self._make_node("n1", "action_send", file="a.ivy")
        model.add_node(n1)

        # Simulate old pickle: remove _nodes_by_name before serializing
        state = model.__getstate__()
        state.pop("_nodes_by_name", None)
        old_model = SemanticModel.__new__(SemanticModel)
        old_model.__setstate__(state)

        # Should still work after rebuild
        result = old_model.get_nodes_by_name("action_send")
        assert len(result) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd IVY-LSP && python -m pytest tests/test_semantic_model.py::TestNodesByNameIndex -v`
Expected: FAIL — `get_nodes_by_name` doesn't exist.

- [ ] **Step 3: Implement `_nodes_by_name` in model.py**

In `ivy_lsp/core/semantic/model.py`:

1. In `__init__`: Add `self._nodes_by_name: Dict[str, List[Any]] = defaultdict(list)`
2. In `add_node()`, insert BEFORE line 69 (`self._nodes[node_id] = node`) — the old node must be readable before it is overwritten:
```python
            # Name index — handle replace semantics (must be BEFORE self._nodes[node_id] = node)
            name = getattr(node, "name", None)
            old_node = self._nodes.get(node_id)  # read OLD node before overwrite
            if old_node is not None:
                old_name = getattr(old_node, "name", None)
                if old_name and old_name != name:
                    name_list = self._nodes_by_name.get(old_name)
                    if name_list:
                        self._nodes_by_name[old_name] = [
                            n for n in name_list if n.id != node_id
                        ]
                        if not self._nodes_by_name[old_name]:
                            del self._nodes_by_name[old_name]
            # Now update the primary storage (line 69 in original)
            # self._nodes[node_id] = node  ← existing line, keep as-is
            # After the overwrite, index the new name:
            if name:
                existing = self._nodes_by_name.get(name, [])
                self._nodes_by_name[name] = [
                    n for n in existing if n.id != node_id
                ] + [node]
```
   **CRITICAL:** The replace-semantics cleanup MUST run before `self._nodes[node_id] = node` at line 69. The new-name indexing runs after it (referencing the `node` parameter, not the dict).

3. In `remove_file()` (inside the `for nid in node_ids` loop, after popping node):
```python
                name = getattr(node, "name", None)
                if name:
                    name_list = self._nodes_by_name.get(name)
                    if name_list:
                        self._nodes_by_name[name] = [
                            n for n in name_list if n.id != nid
                        ]
                        if not self._nodes_by_name[name]:
                            del self._nodes_by_name[name]
```

4. In `update_file()` phase 1 (inside `for nid in ids_to_remove` loop):
```python
                name = getattr(node, "name", None) if node else None
                if name:
                    name_list = self._nodes_by_name.get(name)
                    if name_list:
                        self._nodes_by_name[name] = [
                            n for n in name_list if n.id != nid
                        ]
                        if not self._nodes_by_name[name]:
                            del self._nodes_by_name[name]
```

5. In `update_file()` phase 2 (AFTER the tier-check `continue` at line 186-187):
```python
                name = getattr(node, "name", None)
                if name:
                    existing = self._nodes_by_name.get(name, [])
                    self._nodes_by_name[name] = [
                        n for n in existing if n.id != nid
                    ] + [node]
```

6. In `merge_from()` (inside the node loop):
```python
                name = getattr(node, "name", None)
                if name:
                    existing = self._nodes_by_name.get(name, [])
                    self._nodes_by_name[name] = [
                        n for n in existing if n.id != node_id
                    ] + [node]
```

7. In `__setstate__()` (after `self._lock = threading.RLock()`):
```python
        if not hasattr(self, "_nodes_by_name"):
            self._nodes_by_name = defaultdict(list)
            for node in self._nodes.values():
                name = getattr(node, "name", None)
                if name:
                    self._nodes_by_name[name].append(node)
```

8. Add query method:
```python
    def get_nodes_by_name(self, name: str) -> List[Any]:
        """Return all nodes with the given name (O(1) lookup)."""
        with self._lock:
            return list(self._nodes_by_name.get(name, []))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd IVY-LSP && python -m pytest tests/test_semantic_model.py::TestNodesByNameIndex -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd IVY-LSP && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: No regressions.

- [ ] **Step 6: Commit**

```bash
cd IVY-LSP
git add ivy_lsp/core/semantic/model.py tests/test_semantic_model.py
git commit -m "$(cat <<'EOF'
feat: add _nodes_by_name index to SemanticModel for O(1) name lookups

Adds a name-keyed index alongside existing _nodes_by_type and
_nodes_by_file indices. Handles replace semantics (same id, different
name), tier-check skips in update_file(), and pickle backward
compatibility with old models.
EOF
)"
```

---

### Task 2: Add version counter to SemanticModel (1G)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/core/semantic/model.py`
- Modify: `IVY-LSP/ivy_lsp/mcp/context.py`
- Test: `IVY-LSP/tests/test_semantic_model.py` (extend)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_semantic_model.py`:

```python
class TestVersionCounter:
    def _make_node(self, node_id, name, file=None, tier=None):
        from types import SimpleNamespace
        return SimpleNamespace(id=node_id, name=name, file=file, tier=tier)

    def test_version_starts_at_zero(self):
        assert SemanticModel().version == 0

    def test_add_node_increments_version(self):
        m = SemanticModel()
        m.add_node(self._make_node("n1", "a"))
        assert m.version == 1
        m.add_node(self._make_node("n2", "b"))
        assert m.version == 2

    def test_remove_file_increments_version(self):
        m = SemanticModel()
        m.add_node(self._make_node("n1", "a", file="f.ivy"))
        v = m.version
        m.remove_file("f.ivy")
        assert m.version == v + 1

    def test_version_survives_pickle(self):
        import pickle
        m = SemanticModel()
        m.add_node(self._make_node("n1", "a"))
        data = pickle.dumps(m)
        m2 = pickle.loads(data)
        assert m2.version == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd IVY-LSP && python -m pytest tests/test_semantic_model.py::TestVersionCounter -v`
Expected: FAIL — `version` property doesn't exist.

- [ ] **Step 3: Implement version counter**

In `model.py`:
- `__init__`: Add `self._version: int = 0`
- End of `add_node()`, `remove_file()`, `update_file()`, `merge_from()` (inside lock): `self._version += 1`
- Add property: `@property` / `def version(self) -> int:` / `with self._lock: return self._version`

In `mcp/context.py`, in `ToolContext.from_lsp_server()`, add:
```python
get_index_version=lambda: server._semantic_model.version if server._semantic_model else 0,
```

- [ ] **Step 4: Run tests**

Run: `cd IVY-LSP && python -m pytest tests/test_semantic_model.py::TestVersionCounter -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd IVY-LSP
git add ivy_lsp/core/semantic/model.py ivy_lsp/mcp/context.py tests/test_semantic_model.py
git commit -m "feat: add monotonic version counter to SemanticModel for MCP cache invalidation"
```

---

### Task 3: Update consumer callsites to use `get_nodes_by_name()` (1A consumers)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/lsp/navigation/definition.py:146-166`
- Modify: `IVY-LSP/ivy_lsp/lsp/navigation/hover.py` (2 locations)
- Modify: `IVY-LSP/ivy_lsp/lsp/navigation/call_hierarchy.py:100,106`
- Modify: `IVY-LSP/ivy_lsp/lsp/completion.py:552`
- Modify: `IVY-LSP/ivy_lsp/core/semantic/model_builder.py`

- [ ] **Step 1: Update definition.py**

Replace `_lookup_via_semantic_model` (lines 146-166) with:
```python
def _lookup_via_semantic_model(word: str, semantic_model: Any) -> list:
    """Query the SemanticModel for symbol locations using O(1) name index."""
    try:
        results = []
        for node in semantic_model.get_nodes_by_name(word):
            if getattr(node, "file", None) and getattr(node, "line", None):
                results.append(_SemanticSymbolLoc(node.file, node.line))
        return results
    except Exception:
        logger.debug("semantic model lookup failed", exc_info=True)
        return []
```

- [ ] **Step 2: Update hover.py, call_hierarchy.py, completion.py**

Replace each `for node in semantic_model.get_nodes_by_type(SomeType)` + name comparison pattern with `semantic_model.get_nodes_by_name(word)`.

- [ ] **Step 3: Update model_builder.py**

Replace local `type_by_name`/`symbol_by_name` dict construction with `get_nodes_by_name()` calls.

- [ ] **Step 4: Run full test suite**

Run: `cd IVY-LSP && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: No regressions.

- [ ] **Step 5: Commit**

```bash
cd IVY-LSP
git add ivy_lsp/lsp/navigation/definition.py ivy_lsp/lsp/navigation/hover.py \
        ivy_lsp/lsp/navigation/call_hierarchy.py ivy_lsp/lsp/completion.py \
        ivy_lsp/core/semantic/model_builder.py
git commit -m "refactor: replace O(N) semantic model scans with get_nodes_by_name() in all LSP handlers"
```

---

## Phase 2: SymbolTable Kind Index + Reference Extraction (1B + 1C)

### Task 4: Add `_by_kind` index to SymbolTable (1B)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/core/parsing/symbols.py`
- Test: extend existing `test_symbol_table*.py`

- [ ] **Step 1: Write tests, Step 2: Implement, Step 3: Verify, Step 4: Commit**

Add `_by_kind = defaultdict(list)` to `SymbolTable.__init__`. Update `add_symbol` and `remove_file`. Add `symbols_by_kind(kind)` method. ~20 lines total.

```bash
cd IVY-LSP
git add ivy_lsp/core/parsing/symbols.py tests/
git commit -m "feat: add _by_kind index to SymbolTable for efficient kind-based queries"
```

---

### Task 5: Extract shared reference extraction (1C)

**Files:**
- Create: `IVY-LSP/ivy_lsp/core/parsing/reference_extraction.py`
- Modify: `IVY-LSP/ivy_lsp/core/parsing/tiered_extractor.py`
- Test: extend `IVY-LSP/tests/test_reference_extraction.py`

- [ ] **Step 1: Write test verifying extraction function produces same output as inlined code**

```python
def test_extract_references_regex_matches_tier3_inline():
    """Extracted function must produce identical output to the old inline code."""
    source = '''
action send(x: packet) = {
    call transport.send(x)
}
instance net : tcp_connection
before recv(p: packet) {
    require p.valid
}
'''
    from ivy_lsp.core.parsing.reference_extraction import extract_references_regex
    from ivy_lsp.core.parsing.symbols import IvySymbol, SymbolKind
    symbols = [
        IvySymbol(name="send", kind=SymbolKind.Function, range=(1, 0, 3, 1), file_path="test.ivy"),
    ]
    refs = extract_references_regex(source, "test.ivy", symbols)
    kinds = {r.kind for r in refs}
    assert "call" in kinds
    assert "instance" in kinds
    assert "monitor" in kinds
```

- [ ] **Step 2: Create `reference_extraction.py`**

Move `_CALL_STMT_RE`, `_INSTANCE_RE`, `_MONITOR_RE` patterns and the extraction loops from `tiered_extractor.py`. Create `extract_references_regex(source, filepath, symbols)` and `_find_enclosing_action(symbols, line_idx)`.

- [ ] **Step 3: Update `tiered_extractor.py`**

In `_try_lexer()` (lines 396-448): Replace inline loop with:
```python
from ivy_lsp.core.parsing.reference_extraction import extract_references_regex
references = extract_references_regex(source, filepath, declaration_symbols)
```

In `_try_regex()` (lines 578-642): Same replacement.

- [ ] **Step 4: Run tests, Step 5: Commit**

```bash
cd IVY-LSP
git add ivy_lsp/core/parsing/reference_extraction.py ivy_lsp/core/parsing/tiered_extractor.py tests/
git commit -m "refactor: extract shared reference extraction regex into dedicated module"
```

---

## Phase 3: Session/State Unification (2A + 2B)

### Task 6: Extend `session.py` with canonical resolver (2A)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/infra/observability/session.py`
- Test: extend `IVY-LSP/tests/test_session_observability.py` (or similar)

- [ ] **Step 1: Write test for canonical resolution priority**

```python
def test_resolve_session_id_priority_chain(monkeypatch, tmp_path):
    """Priority: hook_payload > CLAUDE_SESSION_ID > CLAUDE_CODE_SESSION_ID > IVY_SESSION_ID > file."""
    from ivy_lsp.infra.observability.session import resolve_session_id, reset_session_cache
    reset_session_cache()

    # Clear all env vars
    for var in ("IVY_SESSION_ID", "CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "IVY_WORKSPACE_ROOT"):
        monkeypatch.delenv(var, raising=False)

    # Step 6: no info -> "unknown"
    assert resolve_session_id() == "unknown"

    # Step 4: IVY_SESSION_ID wins over file
    monkeypatch.setenv("IVY_SESSION_ID", "from-ivy-env")
    reset_session_cache()
    assert resolve_session_id() == "from-ivy-env"

    # Step 2: CLAUDE_SESSION_ID wins over IVY_SESSION_ID
    monkeypatch.setenv("CLAUDE_SESSION_ID", "from-claude")
    reset_session_cache()
    assert resolve_session_id() == "from-claude"

    # Step 1: hook_payload wins over everything
    assert resolve_session_id(hook_payload={"session_id": "from-hook"}) == "from-hook"
```

- [ ] **Step 2: Implement `resolve_session_id()` and make `workspace_hash()` public**

Add to `session.py`:
```python
def resolve_session_id(
    hook_payload: dict | None = None,
    *,
    session_dir: str = "/tmp",
) -> str:
    """Canonical session ID resolution matching detect-ivy-workspace.sh boot order."""
    # 1. Hook payload (boot-time primary)
    if hook_payload:
        sid = hook_payload.get("session_id", "").strip()
        if sid:
            return sid
    # 2. CLAUDE_SESSION_ID
    sid = os.environ.get("CLAUDE_SESSION_ID", "").strip()
    if sid:
        return sid
    # 3. CLAUDE_CODE_SESSION_ID
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if sid:
        return sid
    # 4. IVY_SESSION_ID (already date-prefixed by boot hook)
    sid = os.environ.get("IVY_SESSION_ID", "").strip()
    if sid:
        return sid
    # 5. /tmp session file
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip() or os.getcwd()
    from_file = _read_session_file(ws_root, session_dir=session_dir)
    if from_file:
        return from_file
    # 6. Fallback
    return "unknown"

# Make workspace_hash public (rename from _workspace_hash)
def workspace_hash(workspace_root: str) -> str:
    """12-char SHA-256 hex hash matching the shell convention."""
    return hashlib.sha256(workspace_root.encode()).hexdigest()[:12]
```

Keep `_workspace_hash` as an alias for backward compat: `_workspace_hash = workspace_hash`.

- [ ] **Step 3: Run tests, Step 4: Commit**

```bash
cd IVY-LSP
git add ivy_lsp/infra/observability/session.py tests/
git commit -m "feat: add resolve_session_id() canonical resolver and make workspace_hash() public"
```

---

### Task 7: Update ivy-lsp consumers to use canonical functions (2A internal)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/mcp/sidecar.py` (replace local `_workspace_hash`)
- Modify: `IVY-LSP/ivy_lsp/mcp/client.py` (redirect import)

- [ ] **Step 1: Update sidecar.py**

Replace `_workspace_hash` definition with import:
```python
from ivy_lsp.infra.observability.session import workspace_hash as _workspace_hash
```

- [ ] **Step 2: Update client.py**

Replace local `workspace_hash` with re-export:
```python
from ivy_lsp.infra.observability.session import workspace_hash  # re-export
```

- [ ] **Step 3: Run tests, Step 4: Commit**

```bash
cd IVY-LSP
git add ivy_lsp/mcp/sidecar.py ivy_lsp/mcp/client.py
git commit -m "refactor: deduplicate workspace_hash by importing from canonical session module"
```

---

### Task 8: Update plugin consumers to delegate to ivy-lsp (2B)

**Files:**
- Modify: `PLUGIN/scripts/workspace-common.sh`
- Modify: `PLUGIN/scripts/start-ivy-server.sh`
- Modify: `PLUGIN/hooks/scripts/check-workspace-scope.py`
- Modify: `PLUGIN/hooks/scripts/observability/log_event.py`
- Modify: `PLUGIN/hooks/scripts/observability/obs_session_end.py`

- [ ] **Step 1: Add `resolve_session_id()` to workspace-common.sh**

```bash
resolve_session_id() {
    local ws_root="${1:-${IVY_WORKSPACE_ROOT:-$PWD}}"
    # Delegate to Python canonical implementation
    if [ -n "${IVY_LSP_SRC:-}" ]; then
        local result
        result=$(PYTHONPATH="$IVY_LSP_SRC" python3 -c \
            "from ivy_lsp.infra.observability.session import resolve_session_id; print(resolve_session_id())" \
            2>/dev/null) || true
        if [ -n "$result" ] && [ "$result" != "unknown" ]; then
            echo "$result"
            return 0
        fi
    fi
    # Bash fallback (same priority chain minus hook_payload: 2→3→4→5)
    [ -n "${CLAUDE_SESSION_ID:-}" ] && { echo "$CLAUDE_SESSION_ID"; return 0; }
    [ -n "${CLAUDE_CODE_SESSION_ID:-}" ] && { echo "$CLAUDE_CODE_SESSION_ID"; return 0; }
    [ -n "${IVY_SESSION_ID:-}" ] && { echo "$IVY_SESSION_ID"; return 0; }
    local ws_hash
    ws_hash="$(printf '%s' "$ws_root" | shasum -a 256 | cut -c1-12)"
    local session_file="/tmp/ivy-session-${ws_hash}.id"
    [ -s "$session_file" ] && { head -n 1 "$session_file" | tr -d '\r\n'; return 0; }
    echo "unknown"
}
```

- [ ] **Step 2: Update start-ivy-server.sh** (lines 70-82)

Replace inline resolution with `IVY_SESSION_ID=$(resolve_session_id)`.

- [ ] **Step 3: Update Python hooks**

In `check-workspace-scope.py`, `log_event.py`, and `obs_session_end.py`: replace local `_resolve_session_id()` with `try: from ivy_lsp.infra.observability.session import resolve_session_id` with fallback.

- [ ] **Step 4: Run plugin tests**

Run: `cd PLUGIN && python -m pytest tests/ -v`

- [ ] **Step 5: Commit**

```bash
cd PLUGIN
git add scripts/ hooks/scripts/
git commit -m "refactor: delegate session ID resolution to ivy-lsp canonical resolver"
```

---

## Phase 4: Scope Projection + Cut-off Optimization (1E + 1F)

### Task 9: Add ScopeProjection (1E)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/core/workspace/active_workspace.py`
- Test: extend `IVY-LSP/tests/test_active_workspace.py`

- [ ] **Step 1: Write test**

```python
def test_scope_projection_visibility():
    from ivy_lsp.core.workspace.active_workspace import ScopeProjection
    proj = ScopeProjection(
        active_layers={"quic", "quic_tests"},
        file_to_layer={"a.ivy": "quic", "b.ivy": "apt", "c.ivy": "quic_tests"},
    )
    assert proj.is_visible("a.ivy") is True
    assert proj.is_visible("b.ivy") is False
    assert proj.is_visible("c.ivy") is True
    assert proj.is_visible("unknown.ivy") is True  # not in mapping -> visible
```

- [ ] **Step 2: Implement frozen dataclass, Step 3: Run tests, Step 4: Commit**

```bash
cd IVY-LSP
git add ivy_lsp/core/workspace/active_workspace.py tests/
git commit -m "feat: add ScopeProjection frozen dataclass for query-time workspace filtering"
```

---

### Task 10: Cut-off optimization in scope_manager (1F)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/core/indexer/scope_manager.py`

- [ ] **Step 1: Write test verifying cut-off skips re-wiring**
- [ ] **Step 2: Add `_file_signature_hashes` dict and comparison logic in `reindex_file()`**
- [ ] **Step 3: Run tests, Step 4: Commit**

```bash
cd IVY-LSP
git add ivy_lsp/core/indexer/scope_manager.py tests/
git commit -m "perf: skip requirement re-wiring when file exports unchanged (cut-off optimization)"
```

---

## Phase 5: State Migration (2C + 2D + 2E + 2F)

### Task 11: Move progressive narrowing state to session directory (2C)

**Files:**
- Modify: `PLUGIN/hooks/scripts/check-workspace-scope.py` (~lines 148, 195)

- [ ] **Step 1: Change state path from `/tmp/ivy-inferred-protocol-{sid}.json` to `{ws_root}/.observability/sessions/{sid}/inferred-protocol.json`**
- [ ] **Step 2: Ensure directory creation**
- [ ] **Step 3: Commit**

```bash
cd PLUGIN && git add hooks/scripts/check-workspace-scope.py
git commit -m "refactor: move progressive narrowing state from /tmp to session directory"
```

---

### Task 12: Add file locking to health state + move to session dir (2D)

**Files:**
- Modify: `PLUGIN/hooks/scripts/check-mcp-health.py`
- Modify: `PLUGIN/hooks/scripts/observability/obs_post_tool_use_failure.py`

- [ ] **Step 1: Add `fcntl.flock(LOCK_EX)` wrapper around JSON read-modify-write**
- [ ] **Step 2: Change state path to session directory**
- [ ] **Step 3: Commit**

```bash
cd PLUGIN && git add hooks/scripts/check-mcp-health.py hooks/scripts/observability/obs_post_tool_use_failure.py
git commit -m "fix: add file locking to health state and move to session directory"
```

---

### Task 13: Session GC + stop-session-summary update (2E + 2F)

**Files:**
- Modify: `PLUGIN/hooks/scripts/detect-ivy-workspace.sh`
- Modify: `PLUGIN/hooks/scripts/stop-session-summary.sh`

- [ ] **Step 1: Add 3-line session GC in detect-ivy-workspace.sh**
```bash
# Prune sessions older than 7 days
find "${IVY_WORKSPACE_ROOT}/.observability/sessions" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
```

- [ ] **Step 2: Update stop-session-summary.sh** fallback path from `/tmp/ivy-observability/sessions` to workspace-based path

- [ ] **Step 3: Commit**

```bash
cd PLUGIN && git add hooks/scripts/detect-ivy-workspace.sh hooks/scripts/stop-session-summary.sh
git commit -m "feat: add 7-day session GC and update stop-session-summary fallback path"
```

---

## Phase 6: Bug Fixes & Dead Code (3A + 3B + 3C)

### Task 14: Fix ivy_quality file_path bug (3A)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/lsp/viz_suggestions.py`

- [ ] **Step 1: Add `"file": sv.file` to `state_var` suggestion dict (~line 63)**
- [ ] **Step 2: Add `"file": sv.file` to `missing_guard` suggestion dict (~line 86)**
- [ ] **Step 3: Run tests, Step 4: Commit**

```bash
cd IVY-LSP && git add ivy_lsp/lsp/viz_suggestions.py
git commit -m "fix: add 'file' key to state_var and missing_guard suggestions for ivy_quality file_path filtering"
```

---

### Task 15: Dead code removal (3B)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/core/adapters/compiler_adapter.py` (remove legacy in-process paths)
- Remove: `PLUGIN/scripts/start-ivy-tools.sh`
- Modify: `IVY-LSP/ivy_lsp/mcp/tools/analysis.py` (remove legacy flat keys — coordinate with health-check plan Task 2 which also modifies this file)
- Move: `PLUGIN/hooks/scripts/interaction-checkpoint-test.py` → `PLUGIN/tests/`
- Modify: `PLUGIN/hooks/scripts/observability/check_lsp_log.py` (fix output format)

- [ ] **Step 1-5: One commit per dead code item**

---

### Task 16: Documentation updates (3C)

**Files:**
- Modify: `PLUGIN/CLAUDE.md`, `PLUGIN/commands/nct-health.md`, `PLUGIN/commands/nct-validate.md`, `PLUGIN/commands/nct-observability.md`

- [ ] **Step 1: Update all `/tmp/` path references to reflect new session directory locations**
- [ ] **Step 2: Commit**

```bash
cd PLUGIN && git add CLAUDE.md commands/
git commit -m "docs: update /tmp path references to session-based state locations"
```

---

## Phase 7: Include Resolver Refactor (1D)

### Task 17: Refactor `resolve()` into chain (1D)

**Files:**
- Modify: `IVY-LSP/ivy_lsp/core/indexer/include_resolver.py`

- [ ] **Step 1: Extract `_resolve_same_dir`, `_resolve_via_layers`, `_resolve_via_flat_staging`, `_resolve_via_stdlib` from the existing `resolve()` method**
- [ ] **Step 2: Replace `resolve()` body with 20-line chain calling the 4 sub-methods**
- [ ] **Step 3: Run include resolver tests**

Run: `cd IVY-LSP && python -m pytest tests/unit/test_include_resolver*.py tests/unit/test_task_2_1_include_resolver.py -v`

- [ ] **Step 4: Commit**

```bash
cd IVY-LSP && git add ivy_lsp/core/indexer/include_resolver.py
git commit -m "refactor: decompose include_resolver.resolve() into 4 chained strategy methods"
```

---

## Final Verification

### Task 18: Full regression test

- [ ] **Step 1: Run ivy-lsp full suite**

```bash
cd IVY-LSP && python -m pytest tests/ -q --timeout=30 2>&1 | tail -30
```

- [ ] **Step 2: Run plugin full suite**

```bash
cd PLUGIN && python -m pytest tests/ -v
```

- [ ] **Step 3: Verify git log shows clean commit history**

```bash
cd IVY-LSP && git log --oneline -20
```

Expected: ~12-15 focused commits, each touching one concern.
