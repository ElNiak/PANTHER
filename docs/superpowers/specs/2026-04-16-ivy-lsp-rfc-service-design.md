# ivy-lsp RFC Service Integration

**Date:** 2026-04-16
**Status:** Draft
**Scope:** Native integration of RFC lookup, search, and structured analysis into ivy-lsp MCP tools

## Summary

Extend ivy-lsp with a unified RFC service layer and three new MCP tools (`ivy_rfc_get`, `ivy_rfc_search`, `ivy_rfc_section`) that provide RFC document retrieval, keyword search, and structured section analysis with normative statement extraction. Inspired by [mcp-rfc](https://github.com/mjpitz/mcp-rfc), but implemented natively in Python, sharing ivy-lsp's workspace context and caching infrastructure.

## Goals

1. **RFC lookup during spec authoring** — Pull up normative text for a specific RFC section without leaving the MCP workflow.
2. **Automated gap-filling** — RFC content enriches traceability tools (e.g., `ivy_coverage` gaps can be followed by `ivy_rfc_section` to see the uncovered text).
3. **RFC discovery** — Search for related RFCs when starting work on a new protocol.
4. **Tag-to-text correlation** — Bracket-tag annotations in Ivy source (e.g., `# [rfc4271:6.2]`) resolve directly to RFC section text and normative statements.

## Non-Goals

- Modifying existing MCP tools (`ivy_coverage`, `ivy_manifest`, etc.). Composition happens at the Claude orchestration layer.
- HTML rendering or rich formatting of RFC content.
- Full-text indexing of RFC corpus.

## Design

### 1. RFC Service Layer (`core/rfc/service.py`)

A single `RfcService` class that becomes the unified entry point for all RFC operations. It composes the existing fetcher and parser, adds new capabilities, and manages a two-tier cache.

```python
class RfcService:
    def __init__(self, cache_dir: Path | None = None, cache_ttl: int = 3600):
        ...

    # Fetch & parse
    async def get_rfc(self, number: str, format: str = "full") -> RfcDocument
    async def get_section(self, number: str, section: str) -> RfcSection

    # Search
    async def search(self, query: str, limit: int = 10) -> list[RfcSearchResult]

    # Structured analysis
    def extract_normative_statements(self, section: RfcSection) -> list[NormativeStatement]
    def extract_cross_references(self, section: RfcSection) -> list[CrossReference]

    # Tag correlation
    def resolve_tag_to_section(self, tag: str) -> RfcSection | None

    # Cache management
    def set_local_cache_dir(self, path: Path) -> None
    def clear_cache(self) -> None
```

**Resolution order for `get_rfc`:**
1. In-memory cache (existing `fetcher.py` behavior)
2. On-disk local cache (`{cache_dir}/{rfc_number}/`)
3. Remote fetch from IETF (HTML first via `datatracker.ietf.org`, TXT fallback via `rfc-editor.org`)
4. Fetched results written back to disk cache

### 2. Data Types

```python
@dataclass
class RfcDocument:
    number: str
    title: str
    sections: list[RfcSection]
    metadata: RfcMetadata  # authors, date, status, obsoletes/updates

@dataclass
class NormativeStatement:
    keyword: str           # MUST, SHOULD, MAY, etc.
    text: str              # full sentence
    section: str           # e.g. "6.2"
    rfc: str               # e.g. "rfc4271"
    tag: str               # e.g. "rfc4271:6.2" — directly usable as manifest ID

@dataclass
class CrossReference:
    source_section: str
    target_rfc: str | None  # None if same-document
    target_section: str
    context: str            # surrounding sentence

@dataclass
class RfcSearchResult:
    number: str
    title: str
    date: str
    status: str
    abstract: str
```

### 3. MCP Tools (`mcp/tools/rfc_tools.py`)

#### `ivy_rfc_get`

Retrieve an RFC document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `number` | str | yes | RFC number (e.g. "4271", "rfc9000") or draft ID |
| `format` | str | no | `"full"` (default), `"metadata"`, `"sections"` (TOC only) |

- Metadata mode: title, authors, date, status, obsoletes/updates as structured fields.
- Sections mode: table of contents with section numbers and titles (no body text).
- Full mode: complete parsed `RfcDocument` with all section text included.

#### `ivy_rfc_search`

Search for RFCs by keyword.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | str | yes | Search terms |
| `limit` | int | no | Max results (default 10) |

Queries the IETF Datatracker API (`datatracker.ietf.org/api/v1/doc/document/`). Returns RFC number, title, date, status, and abstract snippet for each result.

#### `ivy_rfc_section`

Extract a specific section with structured analysis.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `number` | str | yes | RFC number |
| `section` | str | yes | Section number (e.g. "6.2", "4.1.1") |
| `analyze` | bool | no | If true (default), include normative statements and cross-references |

Returns section text plus, when `analyze=true`, a structured breakdown: normative statements with their RFC 2119 keywords and generated tag IDs (e.g. `rfc4271:6.2`), and cross-references to other sections/RFCs. Tag IDs match the bracket-tag format used in Ivy annotations.

**Tool metadata:**

| Tool | Category | Cost | needs_model | Timeout |
|------|----------|------|-------------|---------|
| `ivy_rfc_get` | rfc | low | false | 30s |
| `ivy_rfc_search` | rfc | medium | false | 15s |
| `ivy_rfc_section` | rfc | low | false | 30s |

### 4. Structured Analyzer (`core/rfc/analyzer.py`)

Separate from `parser.py` to keep section detection and semantic analysis as distinct concerns.

**Normative statement extraction:**

1. Split section text into sentences (handling RFC formatting: line-wrapped sentences, indented continuation).
2. Match sentences containing RFC 2119 keywords: `MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `SHOULD`, `SHOULD NOT`, `MAY`, `REQUIRED`, `RECOMMENDED`, `OPTIONAL`.
3. Generate tag ID from RFC number and section number (e.g., `rfc4271:6.2`).
4. Deduplicate when multiple keywords appear in the same sentence.

**Cross-reference extraction:**

- Same-document: `"Section 4.1"`, `"see Section 8.2.1"` → `CrossReference(target_rfc=None, target_section="4.1")`
- Other-RFC: `"[RFC4271] Section 6.3"`, `"as defined in RFC 9000"` → `CrossReference(target_rfc="rfc9000", target_section="6.3")`
- Bare RFC mentions without section number: `target_section=None`

**Tag-to-section correlation:**

`resolve_tag_to_section("rfc4271:6.2")` parses the tag, fetches the RFC (from cache if available), and returns the matching `RfcSection`.

### 5. Two-Tier Cache (`core/rfc/cache.py`)

**In-memory tier:** Unchanged from existing `fetcher.py` behavior. TTL-based, keyed by RFC number.

**On-disk tier:** Persistent cache. Default location: `{workspace_root}/.ivy-cache/rfc/`.

```
.ivy-cache/rfc/
├── rfc4271/
│   ├── raw.txt          # fetched text
│   ├── parsed.json      # cached ParsedRfc (sections, metadata)
│   └── meta.json        # fetch timestamp, content hash, source URL
├── rfc9000/
│   └── ...
└── local/               # user-provided RFC files (symlinks or copies)
```

**Local RFC support:** Users place RFC files in `.ivy-cache/rfc/local/` or configure `IVY_LSP_RFC_LOCAL_DIR`. The service checks local files first when a filename matches (e.g., `rfc4271.txt`).

**Cache invalidation:** `meta.json` stores content hash and fetch timestamp. If disk cache is younger than TTL, used directly. If stale, re-fetch and update.

### 6. IETF Datatracker Search (`core/rfc/search.py`)

Async client for the IETF Datatracker REST API.

- Endpoint: `https://datatracker.ietf.org/api/v1/doc/document/?format=json&name__contains={query}&type=rfc&limit={limit}`
- Returns: document name, title, date, status (rfc/bcp/std), abstract
- Timeout: 10s per request
- Results cached in memory with 5-minute TTL (search results change infrequently)

### 7. Configuration

New environment variables following existing `IVY_LSP_*` convention:

| Env var | Default | Description |
|---------|---------|-------------|
| `IVY_LSP_RFC_CACHE_DIR` | `{workspace}/.ivy-cache/rfc/` | Disk cache location |
| `IVY_LSP_RFC_CACHE_TTL` | `3600` | Seconds before disk cache is stale |
| `IVY_LSP_RFC_LOCAL_DIR` | None | Additional directory of local RFC files |
| `IVY_LSP_RFC_OFFLINE` | `false` | If true, never attempt remote fetch |

## File Layout

**New files:**

```
ivy_lsp/core/rfc/
├── service.py        # RfcService — unified entry point
├── analyzer.py       # NormativeStatement/CrossReference extraction
├── cache.py          # Two-tier cache manager (memory + disk)
└── search.py         # IETF Datatracker API client

ivy_lsp/mcp/tools/
└── rfc_tools.py      # ivy_rfc_get, ivy_rfc_search, ivy_rfc_section
```

**Modified files:**

| File | Change |
|------|--------|
| `core/rfc/__init__.py` | Export `RfcService` and new data types |
| `mcp/tools/__init__.py` | Register 3 new tools in metadata registry |
| `mcp/server.py` | Instantiate `RfcService` in `McpServerState`, pass to `ToolContext` |
| `mcp/context.py` | Add `rfc_service: RfcService` field to `ToolContext` |
| `infra/config.py` | Add 4 new `IVY_LSP_RFC_*` env var mappings |

**Unchanged files:** `fetcher.py`, `parser.py`, `staleness.py`, `rfc_annotations.py`, and all existing MCP tools.

## Testing

- **Unit tests:** `RfcService`, `RfcAnalyzer`, `RfcCache`, `DataTrackerClient` — each with mocked I/O.
- **Integration tests:** MCP tools via `safe_tool` test patterns with fixture RFCs.
- **Mock data:** Fixture RFC text files for deterministic section/normative extraction tests. Mock IETF API JSON responses for search tests.
- **Edge cases:** Malformed section numbers, RFCs with unusual formatting, offline mode with empty cache, draft IDs, bare numeric tags.
