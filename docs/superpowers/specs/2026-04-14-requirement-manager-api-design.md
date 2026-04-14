# Requirement Manager API Design

**Date:** 2026-04-14
**Status:** Draft
**Scope:** ivy-lsp (core, MCP tools, LSP diagnostics)

## Problem

The `*_requirements.yaml` manifests in `protocol-testing/{protocol}/` are central to ivy-lsp's RFC traceability system (semantic model, coverage tools, diagnostics, code lenses, hover), but their lifecycle is entirely manual. Manifests are loaded once at startup with no file watcher, no creation enforcement, no controlled mutation path, and no live staleness detection. Developers can edit the YAML directly, bypassing validation, or forget to create one entirely.

## Design Principles

1. **MCP owns all writes.** No direct YAML editing. All mutations go through `RequirementManager`, invoked via MCP tools.
2. **LSP is read-only feedback.** Diagnostics, code lenses, and hover show the current state. The LSP never writes requirement YAMLs.
3. **Shared core library.** `RequirementManager` lives in `ivy_lsp/core/requirements/` and is used by both MCP and LSP. Single validation path, no duplication.
4. **Event-driven model updates.** The manager emits events on mutation. The semantic model subscribes and updates incrementally, keeping diagnostics live without restart.

## Architecture

### New Module: `ivy_lsp/core/requirements/`

```
ivy_lsp/core/requirements/
├── __init__.py              # exports RequirementManager
├── manager.py               # RequirementManager class
├── events.py                # Event dataclasses
└── writer.py                # Atomic YAML serialization (temp file + rename)
```

### RequirementManager

Single authority for all requirement YAML operations. Holds in-memory state for each loaded manifest (requirements dict + metadata).

#### Mutation Methods

| Method | Description |
|--------|-------------|
| `create_manifest(protocol, rfc_number, rfc_source=None)` | Scaffolds new manifest. If `rfc_source` provided, fetches RFC and auto-extracts requirements via existing `parse_rfc_text()`. Writes YAML with full metadata block. Fails if manifest already exists. |
| `add_requirement(manifest_path, id, text, section, level, layer, testable)` | Adds single requirement. Validates ID format, level, no duplicates. Updates metadata timestamp. |
| `remove_requirement(manifest_path, id)` | Removes by ID. Warns if `.ivy` files have bracket tags referencing this ID (via semantic model lookup). |
| `update_requirement(manifest_path, id, **fields)` | Partial update of any field. Same validation as add. |
| `bulk_import(manifest_path, rfc_source, sections=None)` | Re-fetches RFC, extracts requirements, merges with existing manifest. Adds new requirements automatically. Requirements in the YAML but absent from the RFC source are flagged in the returned diff summary but **not deleted** — the caller (MCP tool) presents the list and the user decides via `remove_requirement()`. Preserves manual edits to text/layer/testable on existing entries. Returns diff summary (added, potentially_removed, updated). |
| `refresh_metadata(manifest_path)` | Re-fetches RFC source, updates content_hash, checks obsoleted_by/updated_by/errata. Does not modify requirements. |

#### Read Methods

| Method | Description |
|--------|-------------|
| `load_all(workspace_root, protocol=None)` | Discovers and loads all manifests. Replaces direct calls to `find_manifests()` + `load_requirement_manifest()`. |
| `reload(manifest_path)` | Reloads a single manifest from disk. Used by file watcher fallback. |
| `get_manifest(path_or_protocol)` | Returns loaded manifest state. |
| `check_local_staleness(manifest_path)` | Compares metadata content_hash against locally cached RFC hash. No network call. |

#### Events

| Event | Fields | Trigger |
|-------|--------|---------|
| `ManifestCreated` | `path, protocol` | `create_manifest()` |
| `ManifestChanged` | `path, added_ids, removed_ids, updated_ids` | Any mutation method |
| `ManifestDeleted` | `path` | Future: if manifest removal is needed |

The semantic model subscribes to these events and incrementally updates `RfcRequirement` nodes and `COVERS` edges without a full rebuild.

#### Invariants Enforced on Every Write

- ID uniqueness within the manifest
- ID format: `{rfc_lower}:{section}` or `{rfc_lower}:{section}:{qualifier}`
- Level must be one of: MUST, MUST NOT, SHOULD, SHOULD NOT, MAY
- Layer must be a non-empty string
- Metadata block always present and updated on every mutation
- YAML written atomically (write to temp file, then rename)

### MCP Tool Surface

Existing tools refactored to delegate all writes to `RequirementManager`. No new tool names.

#### `ivy_manifest` — expanded modes

| Mode | Manager Method | Read/Write |
|------|---------------|------------|
| `"info"` | (unchanged) | Read |
| `"validate"` | (unchanged) | Read |
| `"staleness"` | `refresh_metadata()` for hash check + existing online check | Read (unless `auto_fix=true`) |
| `"refresh"` | `bulk_import()` | Write |
| `"create"` | **New.** `create_manifest()` | Write |
| `"add"` | **New.** `add_requirement()` | Write |
| `"remove"` | **New.** `remove_requirement()` | Write |
| `"update"` | **New.** `update_requirement()` | Write |

#### `ivy_extract_requirements`

When `output="manifest"`, delegates to `manager.create_manifest()` or `manager.bulk_import()` (depending on whether a manifest already exists) instead of returning raw YAML text. Returns diff summary and path written.

#### `ivy_coverage`

Unchanged. Reads from the semantic model, which stays current via manager events.

#### `ivy_quality(mode='gate')`

Unchanged. More reliable because the manager guarantees well-formed manifests.

### LSP Read-Only Feedback Layer

#### New/Enhanced Diagnostics

| Code | Severity | Trigger | Message |
|------|----------|---------|---------|
| `ivy.rfc.missingManifest` | Warning | `.ivy` files under `protocol-testing/{protocol}/` with no `*_requirements.yaml` | "No requirement manifest for protocol '{protocol}'. Use ivy_manifest(mode='create') to generate one." |
| `ivy.rfc.unmatchedTag` | Warning | Bracket tag `[rfcNNNN:X.Y]` references ID not in any loaded manifest | "Tag '{tag}' has no matching requirement in manifest. Use ivy_manifest(mode='add') to register it." |
| `ivy.rfc.staleManifest` | Info | At startup, local content_hash doesn't match cached RFC hash | "Manifest for {rfc} may be stale (content hash mismatch). Use ivy_manifest(mode='staleness') to check." |
| `ivy.rfc.uncoveredRequirement` | Hint | Manifest requirement has no bracket tag in any `.ivy` file | (Existing, now stays live via event-driven model updates) |

The first two provide creation triggers: directory-level detection at startup, plus per-tag detection while coding.

#### File Watcher (Safety Net)

Registers `workspace/didChangeWatchedFiles` for `*_requirements.yaml` glob pattern. If someone edits the YAML outside the manager (manual edit, git pull), the LSP detects the change and calls `manager.reload(path)`. The LSP never writes — only reads and reloads.

#### Code Lenses and Hover

Unchanged in interface. Always reflect latest state because the semantic model stays current via manager events.

### Staleness Detection

**Tier 1 — LSP startup (local, no network):**

During `manager.load_all()`, calls `check_local_staleness()` on each manifest. Compares `metadata.content_hash` against the locally cached RFC source hash (existing LRU cache in `fetcher.py`). If stale, the manager marks the manifest and the LSP emits `ivy.rfc.staleManifest`. No network call, no false positive when cache is empty.

**Tier 2 — MCP on-demand (network, full check):**

`ivy_manifest(mode='staleness')` calls `manager.refresh_metadata()`, which fetches the live RFC from rfc-editor.org, compares content hash, and queries the RFC metadata API for obsoleted_by/updated_by/errata. Updates the metadata block in the YAML if anything changed. The manager emits `ManifestChanged`, the LSP picks it up and updates diagnostics.

### Modified Files

| File | Change |
|------|--------|
| `ivy_lsp/core/semantic/rfc_annotations.py` | `load_requirement_manifest()` and `find_manifests()` become internal to the manager. 9 existing call sites redirect to `RequirementManager` methods. Functions stay as private helpers. |
| `ivy_lsp/core/semantic/model_builder.py` | Instantiates `RequirementManager`, subscribes semantic model to events, calls `manager.load_all()`. |
| `ivy_lsp/mcp/tools/traceability_extraction.py` | `ivy_manifest` gains new modes. `ivy_extract_requirements(output='manifest')` delegates to manager. |
| `ivy_lsp/mcp/tools/_helpers.py` | `load_requirements_from_manifests()` fallback delegates to manager. |
| `ivy_lsp/lsp/diagnostics/compute.py` | Adds `missingManifest`, `staleManifest`, enhances `unmatchedTag` messages. |
| `ivy_lsp/lsp/server.py` | Registers `didChangeWatchedFiles` for `*_requirements.yaml`. |

### Dependency Direction

```
RequirementManager (core/requirements/)
    ├── reads: rfc_annotations.py (find/load helpers, kept as private)
    ├── reads: fetcher.py, staleness.py, parser.py (RFC fetching)
    ├── writes: YAML files (via writer.py)
    └── emits: events.py

SemanticModel (core/semantic/)
    └── subscribes to: RequirementManager events

MCP tools (mcp/tools/)
    └── calls: RequirementManager write methods

LSP diagnostics/lenses/hover (lsp/)
    └── reads: SemanticModel (unchanged)
```

No circular dependencies.

## Out of Scope

- CI/pre-commit enforcement (deferred by design choice)
- Git hooks for manifest validation
- Claude Code skills/hooks that auto-invoke staleness checks (can be layered on later)
- Changes to the `RfcRequirement`/`RfcAnnotation` data model in `nodes.py`
