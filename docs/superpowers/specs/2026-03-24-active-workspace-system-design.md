# Active Workspace System for NCT Ivy Protocol Testing

**Date**: 2026-03-24
**Status**: Draft
**Scope**: ivy-lsp, panther-ivy-plugin, .ivyworkspace, per-protocol markers

## Problem Statement

The PANTHER/Ivy NCT ecosystem has three related problems:

1. **Cross-protocol name collisions**: Files like `quic_frame.ivy`, `quic_locale.ivy` exist in both standard QUIC and APT with different content. The LSP indexes everything, making `include quic_frame` ambiguous.
2. **No Claude edit isolation**: No hooks prevent editing APT files when working on QUIC.
3. **No active workspace concept**: The LSP has `set_active_test()` for test-level scoping but no protocol-level workspace activation.

**Root cause**: `.ivyworkspace` v3 has layers and collision detection, but no runtime activation mechanism and no per-protocol markers for auto-scoping.

**Key assumption**: Protocols are autonomous — only depend on `ivy/include/1.7` stdlib. APT has its own copies of quic files. The `apt_core.depends_on: ["quic", "minip"]` in `.ivyworkspace` is **false** and must be removed. Intra-APT dependencies (`apt_quic_fork` → `apt_core`) are real.

## Design: Two-Tier Active Workspace

### Architecture

```
ActiveWorkspace
├── CoarseGate (layer-based, immediate at startup)
│   active_layers: Set[str]           # from workspace_groups or per-protocol marker
│   file_to_layer: Dict[str, str]     # existing in IncludeResolver
│   is_gated(filepath) -> bool        # O(1) lookup
│
├── FineLens (TestScope-based, available after Phase 1 indexing)
│   active_views: Dict[str, TestScopeView]  # existing in WorkspaceContext
│   is_in_scope(filepath) -> bool     # O(1) set membership
│
└── Combined:
    is_in_active_workspace(filepath) -> (allowed, reason)
      fine_lens if ready, else coarse_gate
      stdlib always allowed
```

### Activation Triggers (priority order)

1. `/set-workspace quic` slash command → explicit runtime activation
2. `ivy_workspace(action="set", target="quic")` MCP tool → programmatic activation
3. Per-protocol `.ivyworkspace` marker → auto-detected when opening files in protocol dir
4. Root `.ivyworkspace` → fallback, all protocols visible

### Granularity Levels

| Level | Example | Active Layers |
|-------|---------|--------------|
| Protocol | `/set-workspace quic` | `{quic, quic_tests}` |
| Role-pair | `/set-workspace quic client+server` | Same, with role-filtered scopes |
| Test | `/set-workspace quic_client_test_max.ivy` | Layers inferred from test file's include closure → `_file_to_layer` |
| Clear | `/clear-workspace` | All layers |

### Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Persistence | Auto-restore with notice | Reduces friction for multi-session work |
| Activation | Explicit + interactive picker + per-protocol markers | Three tiers of convenience |
| Edit scope | Write-only isolation (.ivy files) | Reads allowed for cross-protocol reference |
| Resolution | Hard-fail (active layers + stdlib only) | Clean isolation, no ambiguous fallback |
| Dependencies | Protocols autonomous, intra-APT deps real | Only `apt_core→quic/minip` is false |
| Auto-detection | Progressive narrowing (suggest, don't block) | First edit suggests, cross-protocol warns |
| Staging | Rebuild layered staging on workspace change | Thin filter insufficient — stale symlinks |
| LSP↔MCP sync | State file + LSP workspace/didChangeConfiguration notification | Sidecar architecture requires disk-based sync |

---

## Component Designs

### 1. Per-Protocol `.ivyworkspace` Markers

Each protocol directory gets its own marker file enabling walk-up auto-detection.

**`protocol-testing/quic/.ivyworkspace`**:
```json
{
  "version": 3,
  "standard_library": "ivy/include/1.7",
  "scope_detection": "auto",
  "protocol_id": "quic",
  "workspace_root_offset": "../..",
  "workspace_layers": [
    {"id": "quic", "include_paths": [
      "protocol-testing/quic/quic_stack",
      "protocol-testing/quic/quic_utils",
      "protocol-testing/quic/tls_stack",
      "protocol-testing/quic/quic_shims",
      "protocol-testing/quic/quic_config",
      "protocol-testing/quic/quic_entities",
      "protocol-testing/quic/quic_entities_behavior",
      "protocol-testing/quic/quic_extensions",
      "protocol-testing/quic/quic_fsm",
      "protocol-testing/quic/quic_recovery"
    ], "priority": 1},
    {"id": "quic_tests", "include_paths": [
      "protocol-testing/quic/quic_tests",
      "protocol-testing/quic/quic_attacks_stack"
    ], "priority": 2, "depends_on": ["quic"]}
  ],
  "exclude_paths": ["doc", "examples", "test"]
}
```

**New schema fields**:
- `protocol_id`: Protocol identifier for workspace groups lookup
- `workspace_root_offset`: Relative path from marker to panther_ivy root (for stdlib resolution)

**Auto-detection flow**: When opening `quic/quic_stack/quic_types.ivy`, the LSP walk-up finds `quic/.ivyworkspace` → sets `protocol_id = "quic"` → activates `{"quic", "quic_tests"}` layers automatically.

Similarly create: `protocol-testing/apt/.ivyworkspace`, `protocol-testing/minip/.ivyworkspace`, `protocol-testing/bgp/.ivyworkspace`, `protocol-testing/coap/.ivyworkspace`.

**Migration script**: `ivy-lsp/scripts/generate_protocol_markers.py` — reads root `.ivyworkspace`, generates per-protocol markers. Idempotent, re-runnable.

### 2. Root `.ivyworkspace` Changes

```json
{
  "version": 3,
  "workspace_groups": {
    "quic": ["quic", "quic_tests"],
    "apt": ["apt_core", "apt_quic_fork", "apt_minip_fork", "apt_tls_fork", "apt_tests"],
    "apt_quic": ["apt_core", "apt_quic_fork", "apt_tests"],
    "minip": ["minip"],
    "bgp": ["bgp"],
    "coap": ["coap"],
    "scaffolds": ["scaffolds"]
  }
}
```

**Changes**:
- Added `workspace_groups` mapping
- **Removed** `depends_on: ["quic", "minip"]` from `apt_core`
- **Investigate** `depends_on: ["quic"]` on `coap` before removing (must verify CoAP doesn't include standard QUIC files)
- Added `scaffolds` group (only usable via explicit `/set-workspace scaffolds`)

### 3. ActiveWorkspace State

**New file**: `ivy_lsp/active_workspace.py` (~150 LOC)

```python
@dataclass
class ActiveWorkspace:
    active_group: Optional[str]
    active_layers: Set[str]
    active_tests: List[str]
    granularity: str              # "protocol" | "role_pair" | "test" | "none"
    set_by: str                   # "explicit" | "auto" | "marker" | "cleared"

    def is_file_allowed(self, filepath, file_to_layer, scope_views=None):
        """stdlib always allowed; coarse: file_to_layer check; fine: include_closures"""

    @classmethod
    def from_test_file(cls, test_file, file_to_layer):
        """Infer active_layers from a test file's layer membership."""
        layer = file_to_layer.get(os.path.normpath(test_file))
        # Walk workspace_groups to find which group contains this layer
        ...
```

State file: `.ivy-workspace-state.json` (gitignored), persists until explicitly cleared (no 24h expiry).

### 4. MCP Tool: `ivy_workspace`

**New file**: `ivy_lsp/tools/workspace.py` (~120 LOC)

```
ivy_workspace(action="set", target="quic")                         # Protocol
ivy_workspace(action="set", target="quic", roles="client,server")  # Role-pair
ivy_workspace(action="set", target="quic_client_test_max.ivy")     # Test
ivy_workspace(action="get")                                        # Current state
ivy_workspace(action="list")                                       # Available groups
ivy_workspace(action="clear")                                      # Reset
```

**Test-level target resolution**: When `target` ends in `.ivy`, infer the protocol by looking up the file in `_file_to_layer`, then find which `workspace_groups` entry contains that layer. Set `active_layers` to the group's layers, and `active_tests` to `[target]`.

**LSP↔MCP synchronization** (sidecar fix): After writing `.ivy-workspace-state.json`, the tool sends an LSP notification via `workspace/didChangeConfiguration` with the new active layers. In standalone mode, direct resolver mutation works. In sidecar mode, the LSP reads the state file on receiving the notification.

### 5. Include Resolver — Staging Rebuild

**Modify**: `ivy_lsp/indexer/include_resolver.py`

Instead of a thin filter on `resolve()`, rebuild layered staging when workspace changes:

```python
def set_active_workspace(self, active_layers: Set[str]):
    """Rebuild staging with only active layers."""
    self._active_layers = active_layers
    if active_layers:
        filtered_layers = [l for l in self._workspace_layers if l.id in active_layers]
    else:
        filtered_layers = self._workspace_layers
    self.build_layered_staging(filtered_layers)
```

This ensures the flat staging directory only contains symlinks for active layers — no stale cross-layer symlinks. Cost: ~50-100ms per workspace switch (acceptable since switches are rare).

**Hard-fail**: If `include quic_frame` is not found in active layers + stdlib → unresolved. No cross-layer fallback.

### 6. Workspace Symbol Filtering

**Modify**: `ivy_lsp/features/workspace_symbols.py`

When active workspace set, filter symbol results to files in active layers:

```python
if active_workspace.is_set():
    flat = [f for f in flat if file_to_layer.get(f.file_path) in active_workspace.active_layers]
```

### 7. Edit Isolation Hook

**New file**: `panther-ivy-plugin/hooks/scripts/check-workspace-scope.py` (~100 LOC)

PreToolUse for `Write|Edit`:
1. Read `.ivy-workspace-state.json` (missing/corrupt → ALLOW)
2. Not .ivy → ALLOW
3. Stdlib → ALLOW
4. Layer in active_layers → ALLOW
5. Layer NOT in active_layers → BLOCK with suggestion
6. No layer match → WARN

**Progressive narrowing** (when no workspace set): Track inferred protocol in `$TMPDIR/ivy-inferred-protocol-$$-$PPID.json` (using shell PID as session proxy since `IVY_SESSION_ID` is set by `detect-ivy-workspace.sh`).

### 8. Slash Commands

**`/set-workspace`**: With args → parse + call MCP tool. Without args → interactive picker (protocol → optional role).

**`/clear-workspace`**: Call `ivy_workspace(action="clear")`.

### 9. Session Start Integration

**Modify**: `detect-ivy-workspace.sh`:
- Set `IVY_SESSION_ID=$$` in `CLAUDE_ENV_FILE`
- Check `.ivy-workspace-state.json`: if exists, inject `IVY_ACTIVE_WORKSPACE` + report in `additionalContext`
- If no state: report available workspaces

### 10. Collision Diagnostics

**Modify**: `ivy_lsp/tools/analysis.py`

New mode value (not reusing "structural"): `ivy_diagnostics(mode="collisions")`

- Intra-layer: ERROR
- Cross-layer in scope: WARNING
- Cross-boundary: INFO

### 11. PANTHER Heuristic Cleanup

**Modify**: `workspace_detection.py` lines 208-286

Replace hardcoded `quic`, `minip`, `apt` in PANTHER heuristic with dynamic protocol directory discovery via per-protocol markers.

---

## Files to Modify

### ivy-lsp submodule

| File | Change | LOC |
|------|--------|-----|
| `active_workspace.py` | **NEW** — state class + from_test_file | ~150 |
| `tools/workspace.py` | **NEW** — ivy_workspace MCP tool | ~120 |
| `scripts/generate_protocol_markers.py` | **NEW** — migration script | ~80 |
| `workspace_detection.py` | MODIFY — protocol_id, workspace_root_offset, workspace_groups, heuristic cleanup | ~50 |
| `workspace_context.py` | MODIFY — integrate ActiveWorkspace, protocol-scoped loading | ~30 |
| `indexer/include_resolver.py` | MODIFY — set_active_workspace() + staging rebuild | ~60 |
| `features/workspace_symbols.py` | MODIFY — layer-based symbol filtering | ~20 |
| `server_setup.py` | MODIFY — store protocol_id, workspace state init | ~15 |
| `tools/analysis.py` | MODIFY — collision diagnostics (mode="collisions") | ~60 |
| `tools/__init__.py` | MODIFY — register ivy_workspace | ~5 |

### panther-ivy-plugin submodule

| File | Change | LOC |
|------|--------|-----|
| `hooks/scripts/check-workspace-scope.py` | **NEW** — edit isolation + progressive narrowing | ~100 |
| `hooks/hooks.json` | MODIFY — add PreToolUse entry | ~8 |
| `skills/set-workspace/SKILL.md` | **NEW** — /set-workspace command | ~40 |
| `skills/clear-workspace/SKILL.md` | **NEW** — /clear-workspace command | ~20 |
| `CLAUDE.md` | MODIFY — workspace awareness section | ~80 |
| 16 skill files | MODIFY — workspace guidance | ~160 total |
| 5 agent files | MODIFY — workspace context in dispatch | ~80 total |
| 10 command files | MODIFY — workspace in output | ~80 total |
| `hooks/scripts/detect-ivy-workspace.sh` | MODIFY — state restore + session ID | ~20 |
| `hooks/scripts/post-write-ivy-lint.sh` | MODIFY — scope to workspace | ~15 |
| `hooks/scripts/wait-for-indexing.sh` | MODIFY — workspace size reporting | ~10 |
| 7 observability hooks | MODIFY — workspace tag | ~70 total |

### panther_ivy root

| File | Change | LOC |
|------|--------|-----|
| `.ivyworkspace` | MODIFY — add groups, remove false deps | ~15 |
| `protocol-testing/quic/.ivyworkspace` | **NEW** — per-protocol marker | ~25 |
| `protocol-testing/apt/.ivyworkspace` | **NEW** — per-protocol marker | ~30 |
| `protocol-testing/minip/.ivyworkspace` | **NEW** — per-protocol marker | ~10 |
| `protocol-testing/bgp/.ivyworkspace` | **NEW** — per-protocol marker | ~10 |
| `protocol-testing/coap/.ivyworkspace` | **NEW** — per-protocol marker | ~10 |
| `.gitignore` | MODIFY — add state file | ~1 |

---

## Implementation Phases

**Critical ordering**: Phase 1 (.ivyworkspace cleanup) must deploy WITH or BEFORE Phase 2 (hard-fail resolution). Otherwise false `depends_on` will inject wrong files into staging.

### Phase 1: Schema + Markers + Cleanup
- Root `.ivyworkspace`: add `workspace_groups`, remove false `depends_on`
- Investigate CoAP dependency before removing
- `workspace_detection.py`: parse `protocol_id`, `workspace_root_offset`, `workspace_groups`
- Per-protocol `.ivyworkspace` markers (5 files)
- Migration script

### Phase 2: ActiveWorkspace Core + MCP Tool
- `active_workspace.py` — state class
- `tools/workspace.py` — ivy_workspace MCP tool
- `workspace_context.py` — integrate ActiveWorkspace
- `include_resolver.py` — `set_active_workspace()` with staging rebuild
- `server_setup.py` — init active workspace from state file or per-protocol marker
- LSP↔MCP sync: `workspace/didChangeConfiguration` notification path

### Phase 3: Claude Plugin Hooks + Commands
- `check-workspace-scope.py` — PreToolUse edit isolation
- Progressive narrowing with session-scoped temp file
- `/set-workspace` and `/clear-workspace` skills
- `detect-ivy-workspace.sh` — state restore + session ID

### Phase 4: Symbol Filtering + Collision Diagnostics
- `workspace_symbols.py` — filter to active layers
- `analysis.py` — `ivy_diagnostics(mode="collisions")`
- PANTHER heuristic cleanup (dynamic protocol discovery)

### Phase 5: Plugin Ecosystem Updates
- CLAUDE.md — workspace awareness section
- 16 skills — workspace guidance
- 5 agents — workspace context
- 10 commands — workspace in output
- Hook scripts — workspace scoping + observability

---

## Verification Plan

### Unit Tests
1. `ActiveWorkspace.is_file_allowed()` — granularity levels, stdlib always-allow
2. `ActiveWorkspace.from_test_file()` — layer inference from test path
3. `ivy_workspace` MCP tool — set/get/list/clear, persistence
4. `include_resolver.set_active_workspace()` — staging rebuild, APT vs standard resolution
5. Per-protocol marker walk-up — file in `quic/quic_stack/` finds `quic/.ivyworkspace`
6. `workspace_root_offset` — resolves to panther_ivy root
7. `check-workspace-scope.py` — block/allow/warn, progressive narrowing
8. Workspace symbol filtering — only active-layer symbols returned

### Integration Tests
1. `/set-workspace quic` → `include quic_frame` → standard QUIC; APT edit → blocked
2. `/set-workspace apt_quic` → `include quic_frame` → APT fork; `apt_core` accessible
3. `/clear-workspace` → all edits allowed
4. Session restart → workspace auto-restored
5. Open file in `protocol-testing/quic/` → auto-scoped via per-protocol marker

### Smoke Test
```bash
# 1. /set-workspace quic
# 2. Edit quic_connection.ivy → succeeds
# 3. Edit apt_connection.ivy → blocked
# 4. /set-workspace apt_quic
# 5. Edit apt_connection.ivy → succeeds
# 6. /clear-workspace → all edits allowed
# 7. ivy_diagnostics(mode="collisions") → report
# 8. Open quic/quic_stack/quic_types.ivy → auto-scoped via marker
```

---

## Invariants

These must hold at all times after the system is deployed:

1. **`active_layers ⊆ workspace_layers`**: Active layers must be a subset of layers defined in the loaded `.ivyworkspace`.
2. **Stdlib always searchable**: `ivy/include/1.7/` is always included in resolution and symbol results, regardless of active workspace.
3. **`_file_to_layer` populated before `set_active_workspace()`**: If the resolver hasn't built its layer map yet (pre-Phase 1 indexing), `set_active_workspace()` is a no-op with a warning.
4. **State file matches runtime**: After `set_active_workspace()`, the state file and in-memory `ActiveWorkspace` agree. Corrupt state file → fail open (ALLOW all, log warning).
5. **Explicit overrides auto-detect**: `/set-workspace` (explicit, `set_by="explicit"`) always wins over per-protocol marker auto-detection (`set_by="marker"`).
6. **Staging consistency**: After `set_active_workspace()`, both flat staging (`_staging_dir`) and layered staging (`_partition_staging`) reflect only active layers. No stale symlinks.

---

## Review Fixes (from UX, Implementation, Quality reviews)

### RF-1: WorkspaceConfig Dataclass Changes (Critical)

Add to `WorkspaceConfig` in `workspace_detection.py`:
```python
@dataclass
class WorkspaceConfig:
    workspace_root: str
    workspace_layers: List[WorkspaceLayer] = field(default_factory=list)
    # ... existing fields ...
    # NEW FIELDS:
    workspace_groups: Dict[str, List[str]] = field(default_factory=dict)
    protocol_id: Optional[str] = None
    workspace_root_offset: Optional[str] = None
```

In `_apply_marker()`: parse these three new fields from JSON. When `workspace_root_offset` is present, compute `workspace_root = normpath(join(marker_dir, offset))` and use that as the join base for `include_paths`.

### RF-2: Thread Safety — `_staging_lock` (Critical)

Add `threading.Lock()` to `IncludeResolver`:
```python
def __init__(self):
    self._staging_lock = threading.Lock()
    # ...

def set_active_workspace(self, active_layers):
    with self._staging_lock:
        self._active_layers = active_layers
        filtered = [l for l in self._workspace_layers if l.id in active_layers] if active_layers else self._workspace_layers
        self.cleanup_staging()
        self.build_layered_staging(layers=filtered)
        self.create_staging_directory()  # rebuild flat staging too

def resolve(self, include_name, from_file):
    with self._staging_lock:
        # ... existing resolution logic
```

`build_layered_staging()` needs an optional `layers=None` parameter (defaults to `self._workspace_layers`).

### RF-3: Flat Staging Cleanup (Critical)

When `set_active_workspace()` is called, both `cleanup_staging()` AND `create_staging_directory()` must be re-run with only active-layer files. This ensures the flat fallback in `resolve()` step 3 doesn't find stale cross-layer symlinks.

### RF-4: Block Message Template (Critical)

```
BLOCKED: '{filename}' is in layer '{file_layer}' (workspace group: {file_group}).
Active workspace: '{active_group}' (set by: {set_by}).
To allow: /set-workspace {file_group} | /clear-workspace
```

Example: `BLOCKED: 'quic_frame.ivy' is in layer 'apt_quic_fork' (workspace group: apt). Active workspace: 'quic' (set by: auto-restore from previous session). To allow: /set-workspace apt | /clear-workspace`

### RF-5: Marker vs Persisted State Tiebreak (Critical)

When session starts and both a persisted state file AND a per-protocol marker exist:
- **Persisted state with `set_by="explicit"` wins** over marker auto-detection
- **Persisted state with `set_by="marker"` is overridden** by a new marker detection if the marker's protocol differs
- SessionStart hook reports which activation source was used

### RF-6: Session ID (Important)

`detect-ivy-workspace.sh` already writes `IVY_SESSION_ID="$$"` at line 44. The hook reads it from the environment: `$IVY_SESSION_ID`. Progressive narrowing temp file: `$TMPDIR/ivy-inferred-protocol-${IVY_SESSION_ID}.json`. No `$$-$PPID` composite.

### RF-7: Standalone vs Sidecar LSP↔MCP Sync (Important)

| Mode | MCP→Resolver Path | Reverse Path |
|------|-------------------|--------------|
| **In-process** (ToolContext.from_lsp_server) | Direct mutation via shared `resolver` reference | N/A (same process) |
| **Sidecar** (lazy-bridge) | Write state file → LSP reads on next `detect_ivy_workspace` or startup | No reverse channel — workspace changes only apply on LSP restart |

In sidecar mode, workspace changes take effect fully on next LSP restart. The state file is the synchronization point. No `workspace/didChangeConfiguration` notification needed — remove this from the design (the reverse channel doesn't exist in lazy-bridge).

### RF-8: `/set-workspace` Without Args (UX)

Replace interactive picker with list + error:
```
/set-workspace → prints "Current workspace: quic (set by: explicit). Available: quic, apt, apt_quic, minip, bgp, coap, scaffolds"
/set-workspace foo → prints "Unknown workspace 'foo'. Available: quic, apt, apt_quic, minip, bgp, coap, scaffolds"
```

Also: `/set-workspace` always shows current workspace as first line, making it the "what workspace am I in?" command too.

### RF-9: User-Facing Terminology (UX)

All user-facing messages use "active workspace" only. Never mention CoarseGate, FineLens, layer gates, scope lens. The two-tier system is an implementation detail.

Auto-detection notification: "Auto-scoped to QUIC workspace because you opened a file in protocol-testing/quic/. Use /clear-workspace to disable."

### RF-10: New Protocol Onboarding (UX)

When `no layer match` occurs:
```
"This file has no registered workspace layer. If creating a new protocol:
 1. Create protocol-testing/<name>/.ivyworkspace marker
 2. Or run scripts/generate_protocol_markers.py after adding to root .ivyworkspace"
```

### RF-11: Workspace Symbol Filtering — Stdlib Fix (Quality)

```python
if active_workspace.is_set():
    flat = [f for f in flat
            if file_to_layer.get(f.file_path) in active_workspace.active_layers
            or _is_stdlib(f.file_path)]  # stdlib always included
```

### RF-12: `from_test_file()` Fallback (Quality)

When test file's layer is not in any `workspace_groups`: set `active_layers` to just that layer (+ its `depends_on` chain from `.ivyworkspace`). Log a warning. Don't return empty/None.

### RF-13: CoAP Investigation Gate (Quality)

Phase 1 is blocked on CoAP investigation. Investigate BEFORE removing `depends_on`. If CoAP genuinely includes QUIC files, create `coap_quic` group analogous to `apt_quic`.

### RF-14: Per-Phase Acceptance Criteria

| Phase | Done When |
|-------|-----------|
| Phase 1 | Root `.ivyworkspace` updated, per-protocol markers created, `WorkspaceConfig` parses all new fields, CoAP investigated, existing tests pass |
| Phase 2 | `ivy_workspace(action="set/get/list/clear")` works, `set_active_workspace()` rebuilds staging correctly with lock, `resolve()` respects active layers with hard-fail, state file persists |
| Phase 3 | PreToolUse hook blocks out-of-scope .ivy writes, `/set-workspace quic` works end-to-end, session restore works, progressive narrowing suggests on first edit |
| Phase 4 | `ivy_diagnostics(mode="collisions")` returns classified collisions, workspace symbols filtered to active layers (including stdlib), PANTHER heuristic uses dynamic discovery |
| Phase 5 | All 16 skills mention workspace, all 5 agents pass workspace context, all 10 commands report workspace, CLAUDE.md has workspace section |

---

## Estimated Scope

- **Core system (Phases 1-4)**: ~850 LOC new, ~300 LOC modified (17 files)
- **Plugin ecosystem (Phase 5)**: ~520 lines across 35 files
- **Grand total**: ~1,670 lines across ~50 files
- **Order**: Phase 1 → Phase 2 (must be together) → Phase 3 → Phase 4 → Phase 5
