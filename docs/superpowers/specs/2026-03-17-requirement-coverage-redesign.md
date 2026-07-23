# Requirement Coverage Redesign: Correctness, RFC Sourcing, Multi-Protocol

**Date**: 2026-03-17
**Scope**: ivy-lsp (submodule) + panther-ivy-plugin (MCP tools)
**Approach**: Integrated Phased (4 phases, each independently useful)

## Context

The ivy-lsp requirement coverage system tracks RFC traceability through bracket-tag annotations (`# [rfc9000:4.1]`) in `.ivy` files matched against YAML requirement manifests. While functional, it has correctness issues that inflate coverage statistics, no RFC sourcing pipeline (only raw text paste), no version/staleness tracking, and limited multi-protocol management. This redesign addresses all four concerns in priority order.

## Current Architecture

```
.ivy files                    YAML manifests
  # [rfc9000:4.1]    ──→    rfc9000_requirements.yaml
  parse_rfc_tags()           load_requirement_manifest()
        │                           │
        ▼                           ▼
  RfcAnnotation nodes        RfcRequirement nodes
        │                           │
        └───────── coverage ────────┘
              normalize_tag_to_manifest_ids()
              compute_coverage()
```

**Key files**:
- `ivy_lsp/semantic/rfc_annotations.py` — Tag parsing, manifest loading, coverage computation
- `ivy_lsp/semantic/nodes.py` — `RfcRequirement`, `RfcAnnotation` dataclasses
- `ivy_lsp/tools/traceability.py` — MCP tools (`ivy_coverage`, `ivy_extract_requirements`, etc.)
- `ivy_lsp/features/diagnostics.py` — LSP diagnostics (orphan tag detection)
- `ivy_lsp/tools/verification.py` — MCP diagnostics tool (orphan tag detection)
- `protocol-testing/quic/rfc9000_requirements.yaml` — Only production manifest (90 requirements)

## Problems Found

### P1: False-Positive Tag Parsing (Coverage Inflation)
`parse_rfc_tags()` in `rfc_annotations.py:72-96` filters lines starting with `#` but passes code lines with trailing bracket comments like `sent_pkt(...) := true; # [1]`. The bare numeric `[1]` then matches `rfc*:1.*` via `normalize_tag_to_manifest_ids()`, creating phantom coverage. Found 144 bracket-tag occurrences in QUIC files — many are structural comments, not RFC annotations.

### P2: Orphan Detection Inconsistency
Orphan tag check in `diagnostics.py` and `verification.py` uses `tag not in req_ids` (exact match). Coverage computation uses `normalize_tag_to_manifest_ids()` (prefix/bare matching). A valid prefix tag like `rfc9000:4` is flagged as orphan despite legitimately matching `rfc9000:4.1`, `rfc9000:4.6` during coverage.

### P3: Missing Manifest = Silent Zero
When `.ivy` files have bracket tags but no `*_requirements.yaml` manifest exists, coverage tools report 0 total / 0 covered with no warning. Users can't distinguish "no coverage" from "no manifest."

### P4: No Manifest Validation
Invalid levels (e.g., `ALWAYS`), missing `text` fields, malformed IDs, duplicate IDs across manifests — all pass silently through `load_requirement_manifest()`.

### P5: No RFC Lifecycle Tracking
Manifests have no metadata about when they were generated, from which RFC version, or whether the source RFC has been updated/obsoleted/errata'd.

### P6: No RFC Sourcing Pipeline
`ivy_extract_requirements` only accepts raw pasted text. No online RFC fetch, no local file import, no section-aware parsing.

### P7: Limited Multi-Protocol Management
Only QUIC has a manifest. No tooling to manage manifests across protocols, discover missing manifests, or handle custom spec documents.

---

## Design

### Phase 1: Tag Disambiguation + Manifest Validation

**Goal**: Make existing coverage stats trustworthy.

#### 1a. Filter false-positive bare numeric tags at annotation level

**File**: `ivy_lsp/semantic/rfc_annotations.py`

**Important**: `parse_rfc_tags()` intentionally parses all bracket tags including bare numerics on code lines — this is tested behavior (`test_single_numeric_tag`, `test_struct_field_tag_still_parsed`, `test_live_code_tag_still_parsed`). The filtering must happen at a higher level to preserve the low-level parser's predictability.

**Approach**: Add filtering in `parse_file_rfc_annotations()`, which has full line context. After calling `parse_rfc_tags(line)`, apply a post-filter:

```python
def _is_rfc_annotation(line_text: str, tags: list[str]) -> bool:
    """Distinguish RFC annotations from structural/positional bracket comments."""
    m = _BRACKET_RE.search(line_text)
    if not m:
        return False
    code_before = line_text[:m.start()].strip()
    # If line has code before the bracket comment and ALL tags are purely numeric,
    # this is likely a structural comment (e.g., "ptype : quic_packet_type, # [2]")
    if code_before and all(re.match(r"^\d+$", t) for t in tags):
        return False
    return True
```

**Test updates required**: 3 existing tests assert bare numerics on code lines are parsed by `parse_rfc_tags()` — these tests remain unchanged. New tests in `test_tag_disambiguation.py` verify that `parse_file_rfc_annotations()` filters them out:
- `"payload : frame.arr # [8]"` → 0 annotations (filtered)
- `"require x > 0; # [4]"` → 0 annotations (filtered: bare numeric on code line)
- `"require x > 0; # [rfc9000:4.1]"` → 1 annotation (qualified tag, always accepted)
- `"require x > 0; # [4.1]"` → 1 annotation (dotted tag, always accepted)
- `"# [8]"` → 1 annotation (standalone comment, accepted)

#### 1b. Align orphan detection with coverage computation

**Files**: `ivy_lsp/features/diagnostics.py`, `ivy_lsp/tools/verification.py`

Create a shared function in `rfc_annotations.py`:
```python
def is_tag_covered(tag: str, manifest_keys: set[str]) -> bool:
    """Check if a bracket tag resolves to at least one manifest requirement."""
    return bool(normalize_tag_to_manifest_ids(tag, manifest_keys))
```

Replace `tag not in req_ids` with `not is_tag_covered(tag, req_ids)` in both orphan detection locations.

#### 1c. Add manifest field validation

**File**: `ivy_lsp/semantic/rfc_annotations.py`

New function called from `load_requirement_manifest()`:

```python
def validate_manifest(data: dict) -> list[str]:
    """Validate manifest fields, return list of warning strings."""
```

Checks:
- `rfc` field present and non-empty
- `requirements` key exists (warn if `sections` key found, suggesting legacy format)
- Each requirement: `text` non-empty, `level` in `{MUST, MUST NOT, SHOULD, SHOULD NOT, MAY}`, `section` present
- **Level normalization**: Non-canonical synonyms are normalized during loading: `SHALL→MUST`, `SHALL NOT→MUST NOT`, `RECOMMENDED→SHOULD`, `OPTIONAL→MAY` (matching `_ivy_extract_requirements_logic()` behavior). Unknown levels (e.g., `ALWAYS`) produce a warning.
- Requirement ID format matches `{rfc_lower}:{section}` pattern (warn if mismatched)
- Duplicate ID detection

Warnings logged at WARNING level. Invalid entries still load (graceful degradation).

#### 1d. Missing manifest warning in coverage tools

**File**: `ivy_lsp/tools/traceability.py`

In `_ivy_requirement_coverage()` and `_ivy_traceability_matrix()`, after getting the model: if `RfcAnnotation` node count > 0 but `RfcRequirement` count == 0, add to response:
```json
{
  "warnings": ["Found N bracket-tag annotations but 0 requirement manifests. Create *_requirements.yaml in protocol-testing/{protocol}/"]
}
```

#### 1e. Ambiguous tag warning

In `normalize_tag_to_manifest_ids()`, when a bare tag (no `:`) matches requirements from multiple RFC prefixes, the coverage computation should still work correctly but the tool responses should surface a warning: "Ambiguous bare tag [4.1] matches requirements from multiple RFCs: rfc9000, rfc9001. Consider using qualified tags."

Add a new function:
```python
@dataclass
class TagResolution:
    matched_ids: set[str]
    warnings: list[str]  # e.g. "Ambiguous bare tag [4.1] matches 2 RFCs"

def normalize_tag_with_diagnostics(
    tag: str, manifest_keys: set[str]
) -> TagResolution:
    """Like normalize_tag_to_manifest_ids but also returns warnings."""
```

Coverage computation continues using `normalize_tag_to_manifest_ids()` for performance. The diagnostics variant is used only by MCP tools that surface warnings to users.

---

### Phase 2: RFC Fetcher + Section-Aware Parser

**Goal**: Enable RFC acquisition from online and local sources with intelligent section detection.

#### 2a. New module structure

```
ivy_lsp/rfc/
    __init__.py          # Public API: fetch_rfc, parse_rfc_text
    fetcher.py           # Online + local RFC acquisition
    parser.py            # Section-aware text parsing
```

#### 2b. `fetcher.py` — RFC acquisition

```python
@dataclass
class FetchResult:
    text: str
    source: str               # "online:rfc-editor.org" | "local:/path" | "cache"
    fetched_at: str            # ISO 8601
    content_hash: str          # SHA-256 of text
    rfc_number: str | None     # e.g. "9000"
    is_draft: bool
    draft_version: str | None

async def fetch_rfc(
    identifier: str,
    cache_dir: str | None = None,
    cache_ttl_days: int = 30,
) -> FetchResult:
    """Fetch RFC text.

    identifier can be:
    - 'RFC9000' or '9000' → online fetch from rfc-editor.org
    - 'draft-ietf-quic-transport-34' → fetch from ietf.org
    - '/path/to/spec.txt' → read local file
    """
```

- Uses stdlib `urllib.request` (no new dependency)
- Local cache: `{workspace}/.ivy-lsp-cache/rfcs/{identifier}.txt`
- Cache is optional (pass `cache_dir=None` to skip)
- `asyncio.to_thread()` wraps synchronous I/O for async context

**Network safety** (addresses review M3):
- Connection timeout: 15 seconds (`urllib.request.urlopen(..., timeout=15)`)
- Max response size: 2 MB (read in chunks, abort if exceeded). RFC 9000 is ~350 KB; 2 MB covers any RFC with margin.
- HTTP error handling: `urllib.error.HTTPError` → raise `FetchError` with status code and message
- Network failure: `urllib.error.URLError` → raise `FetchError` with "Network unreachable" or similar
- No retry logic — caller can retry explicitly if desired
- Rate limiting: not needed since fetches are always user-initiated (no automated polling)

URL patterns:
- IETF RFC: `https://www.rfc-editor.org/rfc/rfc{N}.txt`
- Internet-Draft: `https://www.ietf.org/archive/id/{draft_name}.txt`

#### 2c. `parser.py` — Section-aware parser

```python
@dataclass
class RfcSection:
    number: str          # "4.1"
    title: str           # "Flow Control"
    start_line: int
    end_line: int
    text: str

@dataclass
class ParsedRfc:
    rfc_number: str
    title: str
    sections: list[RfcSection]
    full_text: str

def parse_rfc_text(text: str, rfc_number: str = "") -> ParsedRfc:
    """Parse RFC plain text into structured sections."""
```

Section header detection uses a multi-signal heuristic (not just regex) to avoid false positives from numbered lists/tables:
1. Regex candidate: `^(\d+(?:\.\d+)*)\.?\s+(.+)$`
2. Filters: reject lines inside ASCII art tables (preceded by `+---`), reject lines where the "title" part is all digits or starts with lowercase, require blank line before the section header (standard RFC formatting)
3. Validation: section numbers must be monotonically increasing within their depth level

This enables correct section attribution when extracting requirements, replacing the crude sequential numbering in `_ivy_generate_manifest()`.

#### 2d. Enhanced `ivy_extract_requirements`

**File**: `ivy_lsp/tools/traceability.py`

Add optional parameter:
```python
async def ivy_extract_requirements(
    rfc_text: str = "",             # Existing
    rfc_source: str = "",           # NEW: RFC number or local path
    output: str = "structured",     # Existing
    rfc_name: str = "",             # Existing
    protocol: str = "",             # Existing
    base_section: str = "",         # Existing
    sections: str = "",             # NEW: section filter e.g. "4,5,8"
) -> str:
```

When `rfc_source` is provided:
1. Fetch via `fetch_rfc(rfc_source)`
2. Parse via `parse_rfc_text()` for section structure
3. If `sections` specified, filter to only those sections
4. Extract requirements with auto-detected section numbers
5. If `output="manifest"`, include `metadata` section

Backward-compatible: `rfc_text` still works if `rfc_source` is empty.

---

### Phase 3: Manifest Metadata + Staleness Detection

**Goal**: Track RFC lifecycle — detect when manifests are stale.

#### 3a. Extended manifest format

Add optional `metadata` section (backward-compatible):

```yaml
rfc: RFC9000
title: 'QUIC: A UDP-Based Multiplexed and Secure Transport'
metadata:
  generated_at: '2026-03-17T10:30:00Z'
  generator_version: '0.11.1'
  source: 'online:rfc-editor.org'
  content_hash: 'sha256:abc123...'
  last_checked: '2026-03-17T10:30:00Z'
  obsoleted_by: null
  updated_by: []
  errata_ids: []
  is_draft: false
  draft_name: null
  draft_version: null
requirements:
  # ... unchanged ...
```

#### 3b. `ManifestMetadata` dataclass

**File**: `ivy_lsp/semantic/nodes.py` (co-located with `RfcRequirement` and `RfcAnnotation` for import convenience)

```python
@dataclass
class ManifestMetadata:
    generated_at: str = ""
    generator_version: str = ""
    source: str = ""
    content_hash: str = ""
    last_checked: str = ""
    obsoleted_by: str | None = None
    updated_by: list[str] = field(default_factory=list)
    errata_ids: list[str] = field(default_factory=list)
    is_draft: bool = False
    draft_name: str | None = None
    draft_version: str | None = None
```

#### 3c. New `load_manifest_with_metadata()` function (no breaking changes)

**File**: `ivy_lsp/semantic/rfc_annotations.py`

Keep `load_requirement_manifest()` signature unchanged (`-> Dict[str, RfcRequirement]`). It has 9 call sites (`mcp_server.py` x2, `workspace_indexer.py` x1, tests x6) — changing the return type would break all of them.

Add a new companion function:
```python
@dataclass
class ManifestLoadResult:
    requirements: dict[str, RfcRequirement]
    metadata: ManifestMetadata | None
    warnings: list[str]
    path: str = ""

def load_manifest_with_metadata(path: str) -> ManifestLoadResult:
    """Load manifest with metadata and validation warnings.

    New callers (ivy_manifest tool, staleness checks) should use this.
    Existing callers continue using load_requirement_manifest() unchanged.
    """
```

Internally, `load_requirement_manifest()` can delegate to `load_manifest_with_metadata()` and return just `.requirements`, but its signature never changes. New code (Phase 3-4 MCP tools) uses `load_manifest_with_metadata()` to get metadata access.

#### 3d. Staleness detection

**New file**: `ivy_lsp/rfc/staleness.py`

```python
@dataclass
class StalenessReport:
    manifest_path: str
    rfc: str
    is_stale: bool
    reasons: list[str]
    severity: str              # "info" | "warning" | "critical"
    suggested_action: str

async def check_staleness(
    manifest_path: str,
    metadata: ManifestMetadata,
    check_online: bool = True,
) -> StalenessReport:
```

Checks:
1. No `content_hash` → info: "No baseline hash, re-generate to track changes"
2. Hash mismatch with current RFC text → warning: "RFC text changed since manifest generation"
3. `obsoleted_by` set → critical: "RFC obsoleted by {rfc}"
4. `last_checked` > 90 days old → info: "Metadata not checked recently"
5. New errata found → warning: "New errata affect normative text"

Online checks use RFC editor JSON endpoint: `https://www.rfc-editor.org/rfc/rfc{N}.json` (lightweight, returns metadata including `obsoleted-by`, `updated-by`, `errata-url`).

**API resilience** (addresses review M5): The RFC editor JSON endpoint is undocumented. Staleness checks must handle:
- HTTP 404/500 → gracefully degrade: report "Unable to check online staleness" as info, not error
- Unexpected JSON schema → parse defensively with `.get()` and fallback to empty values
- Network timeout (same 15s as fetcher) → degrade gracefully
- The errata endpoint (`rfc-editor.org/errata_search.php?...&format=json`) is even more fragile. Errata checking should be best-effort: parse what's available, skip on any error.

#### 3e. Auto-populate metadata on generation

When `ivy_extract_requirements(output="manifest", rfc_source=...)` generates a manifest, metadata is auto-filled with `generated_at`, `source`, `content_hash`, `generator_version`.

---

### Phase 4: MCP Tool Updates + Multi-Protocol Management

**Goal**: Surface all capabilities to users via MCP tools.

#### 4a. New MCP tool: `ivy_manifest`

**File**: `ivy_lsp/tools/traceability.py`

```python
@mcp.tool()
async def ivy_manifest(
    mode: Literal["validate", "staleness", "info", "refresh"] = "info",
    manifest_path: str = "",
    protocol: str = "",
    check_online: bool = False,
) -> str:
    """Manifest lifecycle management.

    Modes:
    - "info": Summary of discovered manifests (count, metadata, protocols).
    - "validate": Run field-level validation, report issues.
    - "staleness": Check if manifests are stale (requires metadata).
    - "refresh": Re-fetch RFC text, diff against current manifest (non-destructive).
    """
```

`mode="info"` without args lists ALL manifests across all protocols:
```json
{
  "manifests": [
    {
      "path": "protocol-testing/quic/rfc9000_requirements.yaml",
      "rfc": "RFC9000",
      "requirement_count": 90,
      "has_metadata": false,
      "protocol_dir": "quic"
    }
  ],
  "protocols_without_manifests": ["coap", "dns"]
}
```

`mode="validate"` runs Phase 1 validation and returns structured issues:
```json
{
  "issues": [
    {"field": "rfc9000:4.1.level", "message": "Unknown level 'ALWAYS'", "severity": "error"}
  ],
  "valid": false
}
```

`mode="staleness"` delegates to `check_staleness()` and returns the report.

`mode="refresh"` fetches the RFC, extracts requirements, and diffs against current manifest. Does NOT overwrite — returns the diff for user review.

**Diff algorithm** (addresses review M4): Requirements are matched by ID (e.g., `rfc9000:4.1`). For each ID:
- Present in both → compare `text` and `level`. If different, report as "changed" with old/new values.
- Present only in fresh extraction → report as "added" (new requirement in RFC).
- Present only in current manifest → report as "removed" (requirement no longer in RFC or extraction missed it).

Output format:
```json
{
  "added": [{"id": "rfc9000:4.7", "text": "...", "level": "MUST"}],
  "removed": [{"id": "rfc9000:4.3", "text": "...", "level": "SHOULD"}],
  "changed": [{"id": "rfc9000:4.1", "field": "text", "old": "...", "new": "..."}],
  "unchanged_count": 85
}
```

On network failure: returns `{"error": "Failed to fetch RFC: <reason>", "manifest_info": {...}}` instead of crashing.

#### 4b. Enhanced `ivy_coverage` output

Add to `stats` and `gaps` responses:

```json
{
  "manifests": [
    {"path": "...", "rfc": "RFC9000", "requirement_count": 90, "has_metadata": true, "is_stale": false}
  ],
  "warnings": [
    "Found 42 annotations but 0 manifests for protocol coap",
    "Ambiguous bare tag [4.1] matches 2 RFCs"
  ],
  // ... existing fields unchanged ...
}
```

#### 4c. Multi-protocol considerations

- `find_manifests()` already auto-discovers per-protocol directories — no changes needed
- Layer vocabulary is protocol-specific, not enforced at schema level
- `ivy_manifest(mode="validate", protocol="coap")` can accept optional `valid_layers` for per-protocol checking
- Multiple RFCs per protocol supported (QUIC: RFC9000 + RFC9001 + RFC9002 → 3 manifests in same directory)

#### 4d. Custom protocol workflow

For non-IETF structured specs:
1. `ivy_extract_requirements(rfc_source="/path/to/myspec.txt", output="manifest", rfc_name="CUSTOM-MYPROTO-v2", protocol="myproto")`
2. Manifest generated at `protocol-testing/myproto/custom-myproto-v2_requirements.yaml`
3. Bracket tags use `custom-myproto-v2:` prefix: `# [custom-myproto-v2:4.1]`
4. Coverage tools automatically discover and include it

---

## File Change Summary

### New Files
| File | Phase | Purpose |
|------|-------|---------|
| `ivy_lsp/rfc/__init__.py` | 2 | Public API |
| `ivy_lsp/rfc/fetcher.py` | 2 | Online + local RFC acquisition |
| `ivy_lsp/rfc/parser.py` | 2 | Section-aware text parsing |
| `ivy_lsp/rfc/staleness.py` | 3 | Staleness detection |

### Modified Files
| File | Phase | Changes |
|------|-------|---------|
| `ivy_lsp/semantic/rfc_annotations.py` | 1, 3 | Tag filtering, `validate_manifest()`, `is_tag_covered()`, `ManifestLoadResult`, metadata parsing |
| `ivy_lsp/semantic/nodes.py` | 3 | `ManifestMetadata` dataclass |
| `ivy_lsp/tools/traceability.py` | 1, 2, 4 | Warnings in coverage responses, `rfc_source`/`sections` params, `ivy_manifest` tool |
| `ivy_lsp/features/diagnostics.py` | 1 | Use `is_tag_covered()` for orphan detection |
| `ivy_lsp/tools/verification.py` | 1 | Use `is_tag_covered()` for orphan detection |

### New Test Files
| File | Phase | Tests |
|------|-------|-------|
| `tests/test_tag_disambiguation.py` | 1 | Bare numeric rejection, ambiguity warnings, **prefix tag `rfc9000:4` not flagged as orphan** |
| `tests/test_manifest_validation.py` | 1 | Field validation, duplicate detection, level normalization |
| `tests/test_rfc_fetcher.py` | 2 | Online fetch, local file, caching |
| `tests/test_rfc_parser.py` | 2 | Section detection, requirement attribution |
| `tests/test_staleness.py` | 3 | Content/metadata/time drift detection |
| `tests/test_manifest_tool.py` | 4 | ivy_manifest modes |

---

## Phase Dependencies

Phases 1 and 2 are independently implementable with no cross-dependencies. Phase 3 depends on Phase 2 (the fetcher is needed for staleness content-hash checks). Phase 4 depends on Phase 3 (the `ivy_manifest` tool uses `ManifestMetadata` and `check_staleness()`). The recommended implementation order is 1 → 2 → 3 → 4, but Phase 1 can be implemented and shipped alone.

## Backward Compatibility

- **Existing manifests**: Load identically. `metadata` section is optional.
- **Existing bracket tags**: All currently valid tags remain valid. Only purely numeric tags on code lines are newly rejected.
- **Existing MCP tool calls**: All parameters unchanged. New parameters are optional with defaults.
- **Existing tool responses**: New fields (`warnings`, `manifests`) are additive.

## Dependencies

- No new Python package dependencies (uses stdlib `urllib.request`, `hashlib`, `json`, `re`)
- `PyYAML` already required (used by `load_requirement_manifest`)

## Verification Plan

### Phase 1 Verification
1. Run `ivy_coverage(mode="stats")` before and after tag disambiguation — coverage numbers should decrease (fewer false positives)
2. Run `ivy_manifest(mode="validate", protocol="quic")` — should report any field issues in existing `rfc9000_requirements.yaml`
3. Check that prefix tags like `rfc9000:4` are NOT flagged as orphaned in `ivy_diagnostics`
4. Run existing test suite: `pytest tests/ -x`

### Phase 2 Verification
1. `ivy_extract_requirements(rfc_source="RFC9000", output="structured")` — should fetch and extract requirements with correct section numbers
2. `ivy_extract_requirements(rfc_source="/path/to/local/spec.txt", output="manifest", rfc_name="TEST", protocol="test")` — should generate manifest from local file
3. Compare auto-detected sections against manual `rfc9000_requirements.yaml`

### Phase 3 Verification
1. Generate manifest with `rfc_source` → verify `metadata` section present
2. `ivy_manifest(mode="staleness", protocol="quic", check_online=True)` — should report staleness status
3. Manually edit `content_hash` in manifest → staleness check should detect mismatch

### Phase 4 Verification
1. `ivy_manifest(mode="info")` — should list all manifests across protocols
2. `ivy_manifest(mode="refresh", protocol="quic", check_online=True)` — should show diff
3. `ivy_coverage(mode="stats")` response should include `manifests` and `warnings` fields
4. End-to-end: create custom protocol manifest → verify coverage works
