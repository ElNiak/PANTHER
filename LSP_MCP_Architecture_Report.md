# LSP and MCP Interaction in Panther-Ivy Plugin

## Executive Summary

The ivy-lsp submodule implements a **unified LSP+MCP system** where:
- **LSP and MCP do NOT inherit from each other** (no multi-protocol base classes)
- **They share underlying workspace state** (semantic model, workspace indexer, include resolver)
- **MCP runs as an HTTP sidecar thread** spawned by the LSP server
- **Data flows bidirectionally** through a ToolContext bridge that exposes LSP's live state to MCP

This is a **federation model** rather than a monolithic architecture—two independent protocol servers backed by shared indexing and analysis infrastructure.

---

## 1. Architecture Overview: Data Flow

```
Claude Code (client)
    ├─ LSP over stdio (JSON-RPC)
    │   └─ IvyLanguageServer (pygls-based)
    │
    └─ MCP over HTTP (via bridge.py)
        └─ MCP bridge (stdio → HTTP relay)
            └─ MCP HTTP sidecar (streamable_http transport)

[Shared by both]
    ├─ WorkspaceIndexer (file cache, include graph)
    ├─ SemanticModel (cached AST + requirement graph)
    ├─ IncludeResolver (file discovery)
    └─ ToolContext (bridge dataclass)
```

### The Three Processes

1. **LSP Server Process** (`python -m ivy_lsp`)
   - Entry point: `ivy_lsp/__main__.py`
   - Main class: `IvyLanguageServer` (extends `pygls.LanguageServer`)
   - Handles LSP requests/notifications over stdio

2. **MCP HTTP Sidecar** (spawned by LSP as daemon thread)
   - Started in: `ivy_lsp/lsp/server.py:_setup_indexer()` → `start_mcp_http_thread()`
   - Runs in: separate asyncio event loop in daemon thread
   - Serves: HTTP endpoint at `http://127.0.0.1:{port}/mcp`
   - Transport: Streamable HTTP (MCP ≥ 1.0)

3. **MCP Bridge** (spawned by Claude Code)
   - Entry point: `python -m ivy_lsp.mcp.bridge <port> [port_file]`
   - Function: stdio ↔ HTTP relay
   - Features: automatic reconnection, fallback to standalone MCP

---

## 2. Bridge Architecture (LSP ↔ MCP Data Sharing)

### The ToolContext Bridge

File: `ivy_lsp/mcp/context.py`

**Key Method:** `ToolContext.from_lsp_server(server: IvyLanguageServer) -> ToolContext`

This method extracts the LSP server's live state and exposes it through callables:

```python
@classmethod
def from_lsp_server(cls, server):
    """Bridge an IvyLanguageServer instance into a ToolContext."""
    indexer = server._indexer

    # Extract live state
    ws_root = indexer._workspace_root
    staging_dir = resolver._staging_dir
    semantic_model = server._semantic_model  # Live reference
    requirement_graph = indexer.requirement_graph

    # Create context with callbacks that delegate to LSP server
    ctx = ToolContext(root=ws_root, staging_dir=staging_dir, ...)

    # Wire up callables
    async def _get_model():
        return server._semantic_model  # Returns live object

    ctx.get_model = _get_model
    ctx.get_req_graph = lambda: indexer.requirement_graph
    # ... more delegates ...

    return ctx
```

**What is shared:**
- `SemanticModel` — AST symbols, type info (same instance)
- `WorkspaceIndexer` — file cache, symbol table, requirement graph
- `IncludeResolver` — file discovery, staging directory
- `BasenameCache` — filename → paths mapping

**What is NOT shared:**
- LSP's request/response handlers
- MCP's tool implementations
- Diagnostic publishing mechanism (LSP-only)

---

## 3. Process Lifecycle

### Startup Sequence (Unified Mode)

1. **Claude Code spawns**: `python -m ivy_lsp`
   - Parses CLI args: `--mcp` (standalone) or default (unified)
   - Imports `IvyLanguageServer` from `pygls.lsp.server`

2. **IvyLanguageServer.__init__()**
   - Registers LSP feature handlers (definition, hover, etc.)
   - Initializes `_indexer = None`, `_semantic_model = None`

3. **Client sends `initialize` request**
   - LSP handler `_setup_indexer()` runs
   - Creates `WorkspaceIndexer` (parses all .ivy files, builds include graph)
   - Builds `SemanticModel` (requires graph, Z3 for full mode)

4. **MCP Sidecar Startup** (in `_setup_indexer`)
   ```python
   from ivy_lsp.mcp.sidecar import start_mcp_http_thread
   thread, actual_port = start_mcp_http_thread(self, port=19847)
   ```
   - Creates `ToolContext.from_lsp_server(self)` — bridges LSP state
   - Spawns HTTP sidecar in daemon thread
   - Writes port file: `/tmp/ivy-mcp-{workspace_hash}.port`
   - LSP initialization completes

5. **Claude Code spawns MCP bridge** (in separate process)
   ```bash
   python -m ivy_lsp.mcp.bridge 19847 /tmp/ivy-mcp-*.port
   ```
   - Reads port file (discovers sidecar port)
   - Connects to sidecar HTTP endpoint
   - Relays JSON-RPC messages: stdin → HTTP → stdout
   - Implements reconnection with exponential backoff
   - Fallback: if sidecar unavailable, spawns standalone `python -m ivy_lsp --mcp`

---

## 4. Tools and Capability Mapping

### MCP Tools Exposed

File: `ivy_lsp/mcp/tools/__init__.py`

**All tools delegate to LSP infrastructure:**

| MCP Tool | LSP Feature | Implementation |
|----------|-------------|-----------------|
| `ivy_verify` | Verification | Calls `run_ivy_check()` (shared) |
| `ivy_compile` | Compilation | Calls `run_ivy_compile()` (shared) |
| `ivy_model_info` | Model inspection | Calls `run_ivy_show()` (shared) |
| `ivy_diagnostics` | Parser diagnostics | Uses `SemanticModel` (LSP's instance) |
| `ivy_include_graph` | Include resolution | Reads `indexer.requirement_graph` (LSP's instance) |
| `ivy_coverage` | RFC coverage | Reads `indexer.requirement_graph` + `SemanticModel` |
| `ivy_extract_requirements` | Requirement extraction | Calls `AnalysisPipeline` (shared) |
| `ivy_visualize` | Graph visualization | Creates proxy view of `SemanticModel` |
| `ivy_model_summary` | Model overview | Reads `SemanticModel` directly |
| `ivy_patterns` | Pattern validation | Reads `SemanticModel` + requirement graph |
| `ivy_quality` | Quality gates | Delegates to `ivy_lsp.lsp.viz_suggestions` |

### LSP Features (not exposed to MCP)

These are **LSP-only**, not available via MCP:
- `textDocument/documentSymbol` — returns symbols (MCP has no equivalent)
- `textDocument/hover` — inline documentation
- `textDocument/completion` — context-aware suggestions
- `textDocument/rename` — refactoring
- `textDocument/publishDiagnostics` — push notifications (MCP has no push)
- `textDocument/codeLens` — inline annotations

### MCP Tools (not available via LSP)

These are **MCP-only**, not available via LSP:
- `ivy_capabilities` — lists all MCP tools
- `ivy_pattern_scaffold` — code generation

---

## 5. Shared State (No Duplication)

### WorkspaceIndexer (Single Instance)

File: `ivy_lsp/core/indexer/workspace_indexer.py`

**Created once** in LSP during initialization:
```python
# ivy_lsp/lsp/server.py
def _setup_indexer(self):
    self._indexer = WorkspaceIndexer(root=ws_root)
```

**Shared with MCP** via ToolContext:
```python
# ivy_lsp/mcp/context.py
ctx = ToolContext.from_lsp_server(lsp_server)
# ctx now has references to:
#   - indexer.requirement_graph
#   - indexer.resolver
#   - indexer file cache
```

**Benefits:**
- File list is built once, reused by both protocols
- Include resolution is consistent
- Symbol table is unified

### SemanticModel (Single Instance)

File: `ivy_lsp/core/semantic/model.py`

**Created once** in LSP:
```python
# ivy_lsp/lsp/server.py
self._semantic_model = await analysis_pipeline.analyze()
```

**Accessed by MCP** via ToolContext callback:
```python
# In MCP tool execution
model = await ctx.get_model()  # Returns LSP's live instance
```

**Persistence:**
- Written to `.ivy-index/semantic_model.pickle.gz` after build
- Next startup loads from cache (avoids rebuild)

### IncludeResolver (Single Instance)

File: `ivy_lsp/core/indexer/include_resolver.py`

**Created once** in WorkspaceIndexer:
```python
self.resolver = IncludeResolver(root, staging_dir=...)
```

**Shared with MCP** via ToolContext:
```python
ctx.include_resolver = indexer.resolver
```

---

## 6. No Protocol Inheritance

### LSP Server Architecture

File: `ivy_lsp/lsp/server.py`

```python
class IvyLanguageServer(BulkOrchestrationMixin, ServerSetupMixin, LanguageServer):
    """Language server for Ivy formal specification files."""

    def __init__(self):
        super().__init__(name="ivy-language-server", version=__version__)
        # Register LSP features (hover, definition, etc.)
        self.__init_features()
        # Create shared state
        self._indexer: Optional[WorkspaceIndexer] = None
        self._semantic_model: Optional[SemanticModel] = None
```

**Inheritance chain:** `IvyLanguageServer` → `BulkOrchestrationMixin` + `ServerSetupMixin` → `pygls.LanguageServer` (LSP only)

### MCP Server Architecture

File: `ivy_lsp/mcp/server.py`

```python
class McpServerState:
    """Mutable state for the MCP server."""

    def __init__(self, root: str, staging_dir: str | None = None, ...):
        self.root = root
        self.context = ToolContext(...)
        # Create tools that use context
```

**No inheritance.** Uses composition with `ToolContext` to access LSP state.

**Why separation?**
- LSP and MCP are fundamentally different protocols (different JSON-RPC schemas)
- Shared state is extracted into dataclass (`ToolContext`)
- Tools are pure functions that read the context, not methods
- Allows standalone MCP mode (`python -m ivy_lsp --mcp`) without LSP

---

## 7. Process Communication Channels

### Within LSP+MCP Unified Process

```
┌─────────────────┐
│  Claude Code    │
└────────┬────────┘
         │ stdio (JSON-RPC)
         ▼
┌─────────────────────────┐
│ LSP Server Process      │
│ ┌───────────────────┐   │
│ │ IvyLanguageServer │   │
│ │  (pygls-based)    │   │
│ └────────┬──────────┘   │
│          │              │
│ Creates & shares        │
│  _indexer               │
│  _semantic_model        │
│          │              │
│          ▼              │
│ ┌─────────────────────┐ │
│ │ ToolContext Bridge  │ │  Shared state
│ │ (from_lsp_server)   │ │  container
│ └─────────┬───────────┘ │
│           │             │
│           ▼ (delegates) │
│ ┌─────────────────────┐ │
│ │ MCP HTTP Sidecar    │ │
│ │ (daemon thread)     │ │
│ │ Serves on :19847    │ │
│ └─────────────────────┘ │
└─────────────────────────┘
         ▲ HTTP
         │ (relay)
┌─────────────────┐
│  MCP Bridge     │
│ (separate proc) │
│ stdio → HTTP    │
└─────────────────┘
```

### Sidecar Monitoring (Dynamic Upgrade)

File: `ivy_lsp/mcp/server.py:_sidecar_monitor()`

The MCP server can **dynamically discover a sidecar**:

1. **Standalone MCP starts** (no sidecar)
2. **Monitor task runs** (polls for port file every 2s)
3. **Port file appears** → LSP sidecar started
4. **Monitor connects** → upgrades to delegating to sidecar
5. **Sidecar unavailable** → reverts to local execution

This allows MCP to be **lazily upgraded** without restart.

---

## 8. Startup Scenarios

### Scenario A: Default (Unified LSP+MCP)

```bash
python -m ivy_lsp
```

Result:
1. LSP server starts
2. MCP sidecar spawned as daemon thread
3. Port file written → Claude's bridge discovers it
4. Both protocols operational, sharing state

### Scenario B: LSP Only

```bash
python -m ivy_lsp --lsp-only
```

Result:
1. LSP server starts
2. MCP sidecar NOT spawned
3. Claude's bridge falls back to standalone MCP

### Scenario C: Standalone MCP

```bash
python -m ivy_lsp --mcp
```

Result:
1. MCP server starts (no LSP)
2. No sidecar (it IS the server)
3. Standalone mode - full rebuild if needed

### Scenario D: MCP Bridge with Fallback

```bash
python -m ivy_lsp.mcp.bridge 19847 /tmp/ivy-mcp-*.port
```

1. Tries to connect to sidecar on port 19847
2. Reads port file for auto-detection
3. If sidecar unavailable:
   - Retries with exponential backoff (2s, 4s, 8s, 16s, 30s)
   - After max attempts, spawns standalone `python -m ivy_lsp --mcp`
4. Timeouts: per-request 120s (configurable via `IVY_LSP_BRIDGE_TIMEOUT`)

---

## 9. Conclusion

### Interaction Model

**Federation, not Inheritance:**
- LSP and MCP are **separate protocol servers**
- No class inheritance between them
- Unified by **shared workspace state** (WorkspaceIndexer, SemanticModel)
- Connected via **ToolContext bridge** that exposes LSP's live instances

### Data Flow

```
Claude Code
    ├─ LSP protocol → IvyLanguageServer → SemanticModel + WorkspaceIndexer
    └─ MCP protocol → Bridge → HTTP Sidecar → ToolContext → Same SemanticModel + WorkspaceIndexer
```

### State Sharing

- **Shared:** indexer, semantic_model, requirement_graph, file cache, include resolver
- **Independent:** LSP handlers, MCP tools, request/response serialization
- **Duplication:** None (single instances referenced from both)
- **Consistency:** Ensured by single-instance design (no concurrent updates)

### Fallback Behavior

1. **Primary:** LSP+MCP unified (sidecar in daemon thread)
2. **Secondary:** Standalone MCP (if sidecar unavailable)
3. **Error Handling:** Bridge implements reconnection + fallback
4. **Graceful Degradation:** Tools work in all scenarios

---

## Key Files Referenced

| File | Role |
|------|------|
| `ivy_lsp/lsp/server.py` | LSP server entry point, sidecar startup |
| `ivy_lsp/mcp/server.py` | MCP server state, tool registration |
| `ivy_lsp/mcp/sidecar.py` | HTTP sidecar startup, port management |
| `ivy_lsp/mcp/bridge.py` | stdio ↔ HTTP relay, reconnection logic |
| `ivy_lsp/mcp/context.py` | ToolContext bridge (LSP → MCP state) |
| `ivy_lsp/mcp/tools/*.py` | Tool implementations (use context) |
| `ivy_lsp/core/indexer/workspace_indexer.py` | File indexing (shared) |
| `ivy_lsp/core/semantic/model.py` | SemanticModel (shared) |
| `ivy_lsp/__main__.py` | CLI entry point (LSP/MCP mode selector) |
