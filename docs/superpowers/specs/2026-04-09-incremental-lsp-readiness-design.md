# Incremental LSP Readiness Design

**Date**: 2026-04-09
**Status**: Approved
**Scope**: ivy-lsp startup sequence, documentSymbol ready gate

## Problem

The LSP `documentSymbol` handler returns "symbol extraction unavailable" when called during server initialization. The handler waits on a single `_ready_event` with a 10-second timeout, but full initialization takes ~25.7 seconds for a 7-protocol workspace. The timeout expires before the parser is available, causing a false degraded-mode response.

### Root cause timeline (observed)

```
T+0.0s    on_initialized starts
T+0.001s  configure_activity_logging (1ms)
T+0.002s  WorkspaceContext.load() begins — loads offline indexes for 7 protocols
T+0.005s  documentSymbol request arrives → _ready_event.wait(10.0)
T+10.0s   *** timeout *** → parser=None, indexer=None → "unavailable"
T+17.1s   WorkspaceContext.load() finishes (offline index loading)
T+17.3s   create_resolver (203ms)
T+18.7s   create_parser (1,386ms) — parser now available
T+25.5s   create_indexer (6,827ms) — indexer now available
T+25.7s   _ready_event.set()
```

The parser is available at T+18.7s but not signaled until T+25.7s. More importantly, the 17-second offline index load blocks parser creation entirely, even though the parser doesn't depend on offline indexes.

## Design

### Two-level readiness model

Replace the single `_ready_event` with two readiness levels:

| Level | Event | Fires at | Enables |
|-------|-------|----------|---------|
| 1 — Parser Ready | `_parser_ready_event` | ~T+1.6s | documentSymbol (AST-based symbol extraction) |
| 2 — Fully Ready | `_ready_event` (existing) | ~T+8.5s | Full indexer, semantic model, analysis pipeline |

### Restructured initialization sequence

Current:
```
1. configure_activity_logging          (1ms)
2. WorkspaceContext.load()             (17,100ms)  ← all offline indexes
3. load_active_workspace               (fast)
4. create_resolver                     (203ms)
5. create_parser                       (1,386ms)
6. create_indexer                      (6,827ms)
7. setup_analysis_pipeline             (112ms)
8. _ready_event.set()                              ← T+25,700ms
```

New:
```
1. configure_activity_logging          (1ms)
2. WorkspaceContext.detect_only()      (<10ms)     ← workspace config only
3. load_active_workspace               (fast)
4. create_resolver                     (203ms)
5. create_parser                       (1,386ms)
6. ★ _parser_ready_event.set()                     ← T+1,600ms
7. Start background thread: load_indexes()
8. create_indexer                      (6,827ms)   ← live scan if offline not ready
9. setup_analysis_pipeline             (112ms)
10. _ready_event.set()                             ← T+8,500ms
```

Improvement: documentSymbol available at T+1.6s instead of T+25.7s (16x faster).

### File changes

#### 1. `ivy_lsp/core/workspace/context.py`

Add `detect_only` classmethod — performs workspace detection, returns `WorkspaceContext` with empty `protocol_indexes`:

```python
@classmethod
def detect_only(cls, start_dir: str) -> WorkspaceContext:
    ws_config = detect_ivy_workspace(start_dir)
    return cls(
        workspace_root=ws_config.workspace_root,
        project_type=ws_config.project_type or "fallback",
        workspace_config=ws_config,
    )
```

Add `load_indexes` instance method — runs the manifest glob + `_load_protocol_index` loop (extracted from current `load()` lines 144-175). Populates `self.protocol_indexes` in place.

```python
def load_indexes(self) -> None:
    pattern = os.path.join(
        self.workspace_root, "protocol-testing", "*",
        ".ivy-index", "manifest.json",
    )
    for manifest_path in sorted(glob.glob(pattern)):
        index_dir = os.path.dirname(manifest_path)
        protocol = os.path.basename(os.path.dirname(index_dir))
        idx = self._load_protocol_index(protocol, index_dir)
        if idx is not None:
            self.protocol_indexes[protocol] = idx
            logger.info(
                "Loaded index for protocol %s (%s, %d symbols files)",
                protocol, idx.staleness.status, len(idx.symbols),
            )
    if not self.protocol_indexes:
        logger.debug(
            "No .ivy-index directories found under %s",
            self.workspace_root,
        )
```

Refactor existing `load()` to call both:
```python
@classmethod
def load(cls, start_dir: str) -> WorkspaceContext:
    ctx = cls.detect_only(start_dir)
    ctx.load_indexes()
    return ctx
```

#### 2. `ivy_lsp/lsp/server.py`

Add `_parser_ready_event` in `__init__`:
```python
self._parser_ready_event: threading.Event = threading.Event()
```

In the `on_initialized` `finally` block (line 451), set both events:
```python
finally:
    self._initializing = False
    self._parser_ready_event.set()  # idempotent if already set
    self._ready_event.set()
```

#### 3. `ivy_lsp/lsp/server_setup.py`

Restructure `_setup_indexer`:

1. Replace `WorkspaceContext.load(ws_root)` with `WorkspaceContext.detect_only(ws_root)`.
2. After `_create_parser(resolver)` succeeds, call `self._parser_ready_event.set()`.
3. Start a daemon thread running `self._workspace_context.load_indexes()`.
4. Proceed with `_create_indexer` as before — `ws_ctx.has_index()` returns False if background thread hasn't finished, so live scan runs instead.

#### 4. `ivy_lsp/lsp/document_symbols.py`

Replace the ready gate (lines 196-202):

```python
parser_ready = getattr(server, "_parser_ready_event", None)
if parser_ready is not None and not parser_ready.is_set():
    loop = asyncio.get_running_loop()
    timed_out = not await loop.run_in_executor(
        None, parser_ready.wait, 30.0
    )
    if timed_out:
        return [_status_document_symbol(
            "server still initializing",
            "Parser initialization exceeded 30s. Check ivy-lsp logs.",
        )]
```

Update the stale comment at line 197 that references "~3s _setup_indexer window".

### What doesn't change

- **goToDefinition, hover, findReferences**: Read `server.indexer` directly, return empty if None.
- **visualization.py**: Checks `server.initializing`, returns "initializing" status.
- **MCP context.py**: Checks `server._initializing` for model status.
- **diagnostics/publisher.py**: Checks `server.indexer is not None`.
- **`_ready_event`**: Still set in `finally` block after full init.
- **`_initializing` flag**: Still cleared in same `finally` block.
- **`WorkspaceContext.load()` external callers**: Refactored internally but behavior identical.

### Edge cases

1. **`_create_parser` fails**: Exception propagates, `_parser_ready_event` is set in the `finally` block of `on_initialized`. documentSymbol proceeds with `parser=None` and falls into existing degraded-mode handling.

2. **`_create_resolver` returns None**: `_setup_indexer` returns early. `_parser_ready_event` is set in the `finally` block. documentSymbol shows degraded status.

3. **Offline index loads after `_create_indexer` starts**: `ws_ctx.has_index()` returns False, live scan runs. The background thread's results are unused for this session. No conflict — `load_indexes` writes to `protocol_indexes` dict, `_prepopulate_from_offline_index` reads from it, and they don't run concurrently because `_create_indexer` already chose the live-scan path.

4. **Offline index loads before `_create_indexer` starts**: `ws_ctx.has_index()` returns True, offline prepopulation runs (existing fast path preserved).

### Testing

1. **Unit**: Mock `WorkspaceContext.detect_only` and `load_indexes`. Verify `_parser_ready_event` is set after `_create_parser` but before `_create_indexer`.
2. **Unit**: Verify documentSymbol returns real symbols when `_parser_ready_event` is set but `_ready_event` is not.
3. **Unit**: Verify documentSymbol returns "server still initializing" when `_parser_ready_event.wait(30)` times out.
4. **Regression**: `WorkspaceContext.load()` produces identical results to `detect_only()` + `load_indexes()`.
