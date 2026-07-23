# ivy-lsp RFC Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add RFC lookup, search, and structured normative analysis as native MCP tools in ivy-lsp.

**Architecture:** A new `RfcService` facade composes the existing `fetcher.py` and `parser.py` with three new modules (analyzer, cache, search). Three MCP tools (`ivy_rfc_get`, `ivy_rfc_search`, `ivy_rfc_section`) delegate to the service. Two-tier cache (memory + disk) with local RFC file support.

**Tech Stack:** Python 3.10+, asyncio, urllib.request + asyncio.to_thread (for IETF Datatracker API, matching existing fetcher pattern), existing `mcp` FastMCP framework, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-04-16-ivy-lsp-rfc-service-design.md`

**Scope simplifications from spec:**
- TXT-only fetch from `rfc-editor.org` (existing fetcher behavior). The spec mentioned HTML-first, but the existing `parser.py` is TXT-only and there's no HTML parser in the codebase. Adding one would be significant scope creep for marginal benefit.
- Reuses existing `RfcSection` and `ParsedRfc` from `parser.py` instead of creating new types.

**Important notes:**
- All code lives in the ivy-lsp submodule at `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`. All file paths below are relative to `ivy_lsp/` within that submodule.
- All commits happen inside the submodule directory. A final task updates the submodule pointer in the parent repo.
- Network calls to `datatracker.ietf.org` and `rfc-editor.org` are blocked by sandbox. All tests MUST use mocks/fixtures.

---

### Task 1: Data Types (`core/rfc/types.py`)

**Files:**
- Create: `ivy_lsp/core/rfc/types.py`
- Test: `tests/test_rfc_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rfc_types.py
"""Tests for RFC service data types."""

from ivy_lsp.core.rfc.types import (
    CrossReference,
    NormativeStatement,
    RfcDocument,
    RfcMetadata,
    RfcSearchResult,
)
from ivy_lsp.core.rfc.parser import RfcSection


class TestNormativeStatement:
    def test_create(self):
        stmt = NormativeStatement(
            keyword="MUST",
            text="Endpoints MUST accept frames.",
            section="4.1",
            rfc="rfc9000",
        )
        assert stmt.tag == "rfc9000:4.1"

    def test_tag_generation(self):
        stmt = NormativeStatement(
            keyword="SHOULD NOT",
            text="Implementations SHOULD NOT send data.",
            section="6.2.1",
            rfc="rfc4271",
        )
        assert stmt.tag == "rfc4271:6.2.1"


class TestCrossReference:
    def test_same_document(self):
        ref = CrossReference(
            source_section="4.1",
            target_rfc=None,
            target_section="8.2",
            context="See Section 8.2 for details.",
        )
        assert ref.target_rfc is None
        assert ref.target_section == "8.2"

    def test_bare_rfc_mention(self):
        ref = CrossReference(
            source_section="3.0",
            target_rfc="rfc4271",
            target_section=None,
            context="As defined in RFC 4271.",
        )
        assert ref.target_section is None


class TestRfcMetadata:
    def test_create(self):
        meta = RfcMetadata(
            authors=["J. Doe"],
            date="2020-01",
            status="Standards Track",
            obsoletes=["rfc2616"],
            updates=[],
        )
        assert meta.authors == ["J. Doe"]
        assert meta.obsoletes == ["rfc2616"]


class TestRfcDocument:
    def test_create(self):
        doc = RfcDocument(
            number="rfc9000",
            title="QUIC: A UDP-Based Multiplexed and Secure Transport",
            sections=[
                RfcSection(number="1", title="Introduction", start_line=0, text="..."),
            ],
            metadata=RfcMetadata(
                authors=[], date="2021-05", status="Standards Track",
            ),
        )
        assert doc.number == "rfc9000"
        assert len(doc.sections) == 1


class TestRfcSearchResult:
    def test_create(self):
        result = RfcSearchResult(
            number="rfc4271",
            title="A Border Gateway Protocol 4 (BGP-4)",
            date="2006-01",
            status="Standards Track",
            abstract="This document discusses...",
        )
        assert result.number == "rfc4271"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.core.rfc.types'`

- [ ] **Step 3: Write minimal implementation**

```python
# ivy_lsp/core/rfc/types.py
"""Data types for the RFC service layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ivy_lsp.core.rfc.parser import RfcSection


@dataclass
class NormativeStatement:
    """A normative statement extracted from RFC text."""

    keyword: str
    text: str
    section: str
    rfc: str

    @property
    def tag(self) -> str:
        return f"{self.rfc}:{self.section}"


@dataclass
class CrossReference:
    """A cross-reference to another RFC or section."""

    source_section: str
    target_rfc: Optional[str]
    target_section: Optional[str]
    context: str


@dataclass
class RfcMetadata:
    """Metadata extracted from an RFC document header."""

    authors: List[str] = field(default_factory=list)
    date: str = ""
    status: str = ""
    obsoletes: List[str] = field(default_factory=list)
    updates: List[str] = field(default_factory=list)


@dataclass
class RfcDocument:
    """A fully parsed RFC document."""

    number: str
    title: str
    sections: List[RfcSection]
    metadata: RfcMetadata = field(default_factory=RfcMetadata)


@dataclass
class RfcSearchResult:
    """A single result from an IETF Datatracker search."""

    number: str
    title: str
    date: str
    status: str
    abstract: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_types.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/rfc/types.py tests/test_rfc_types.py
git commit -m "feat(rfc): add data types for RFC service layer"
```

---

### Task 2: Structured Analyzer (`core/rfc/analyzer.py`)

**Files:**
- Create: `ivy_lsp/core/rfc/analyzer.py`
- Test: `tests/test_rfc_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rfc_analyzer.py
"""Tests for RFC structured analyzer."""

import pytest

from ivy_lsp.core.rfc.analyzer import RfcAnalyzer
from ivy_lsp.core.rfc.parser import RfcSection
from ivy_lsp.core.rfc.types import CrossReference, NormativeStatement


RFC_SECTION_TEXT = """\
   A BGP speaker MUST NOT allow a TCP connection to be configured for a
   remote peer if it already has an established connection to that peer.

   If a BGP speaker receives a connection request and it is not in the
   Idle state, it SHOULD reject the connection attempt.

   Implementations MAY impose additional restrictions on the use of
   this field.  See Section 6.3 for more details.

   As described in [RFC1771], the Hold Time MUST be either zero or at
   least three seconds.
"""

CROSS_REF_TEXT = """\
   The UPDATE message (see Section 4.3) is used to transfer routing
   information between BGP peers.  As defined in RFC 1771, the message
   format has changed.  Refer to [RFC4456] Section 2.1 for route
   reflection procedures.
"""


class TestNormativeExtraction:
    def setup_method(self):
        self.analyzer = RfcAnalyzer()

    def test_extracts_must(self):
        section = RfcSection(number="6.2", title="Test", start_line=0, text=RFC_SECTION_TEXT)
        stmts = self.analyzer.extract_normative_statements(section, rfc="rfc4271")
        keywords = [s.keyword for s in stmts]
        assert "MUST NOT" in keywords
        assert "MUST" in keywords

    def test_extracts_should(self):
        section = RfcSection(number="6.2", title="Test", start_line=0, text=RFC_SECTION_TEXT)
        stmts = self.analyzer.extract_normative_statements(section, rfc="rfc4271")
        keywords = [s.keyword for s in stmts]
        assert "SHOULD" in keywords

    def test_extracts_may(self):
        section = RfcSection(number="6.2", title="Test", start_line=0, text=RFC_SECTION_TEXT)
        stmts = self.analyzer.extract_normative_statements(section, rfc="rfc4271")
        keywords = [s.keyword for s in stmts]
        assert "MAY" in keywords

    def test_tag_matches_section(self):
        section = RfcSection(number="6.2", title="Test", start_line=0, text=RFC_SECTION_TEXT)
        stmts = self.analyzer.extract_normative_statements(section, rfc="rfc4271")
        for stmt in stmts:
            assert stmt.tag == "rfc4271:6.2"

    def test_deduplicates_multi_keyword_sentence(self):
        text = "A sender MUST NOT send and SHOULD NOT accept invalid frames."
        section = RfcSection(number="3.1", title="Test", start_line=0, text=text)
        stmts = self.analyzer.extract_normative_statements(section, rfc="rfc9000")
        texts = [s.text for s in stmts]
        # Same sentence should appear once with the first (strongest) keyword
        assert len([t for t in texts if "invalid frames" in t]) == 1

    def test_handles_line_wrapped_sentences(self):
        text = "   The implementation\n   MUST handle this\n   correctly."
        section = RfcSection(number="2.0", title="Test", start_line=0, text=text)
        stmts = self.analyzer.extract_normative_statements(section, rfc="rfc9000")
        assert len(stmts) == 1
        assert "MUST" in stmts[0].keyword

    def test_empty_section(self):
        section = RfcSection(number="1.0", title="Test", start_line=0, text="")
        stmts = self.analyzer.extract_normative_statements(section, rfc="rfc9000")
        assert stmts == []


class TestCrossReferenceExtraction:
    def setup_method(self):
        self.analyzer = RfcAnalyzer()

    def test_same_document_section_ref(self):
        section = RfcSection(number="4.1", title="Test", start_line=0, text=CROSS_REF_TEXT)
        refs = self.analyzer.extract_cross_references(section)
        section_refs = [r for r in refs if r.target_rfc is None and r.target_section == "4.3"]
        assert len(section_refs) == 1

    def test_bare_rfc_mention(self):
        section = RfcSection(number="4.1", title="Test", start_line=0, text=CROSS_REF_TEXT)
        refs = self.analyzer.extract_cross_references(section)
        bare_refs = [r for r in refs if r.target_rfc == "rfc1771" and r.target_section is None]
        assert len(bare_refs) >= 1

    def test_rfc_with_section(self):
        section = RfcSection(number="4.1", title="Test", start_line=0, text=CROSS_REF_TEXT)
        refs = self.analyzer.extract_cross_references(section)
        full_refs = [r for r in refs if r.target_rfc == "rfc4456" and r.target_section == "2.1"]
        assert len(full_refs) == 1

    def test_empty_section(self):
        section = RfcSection(number="1.0", title="Test", start_line=0, text="")
        refs = self.analyzer.extract_cross_references(section)
        assert refs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_analyzer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.core.rfc.analyzer'`

- [ ] **Step 3: Write minimal implementation**

```python
# ivy_lsp/core/rfc/analyzer.py
"""Structured semantic analysis of RFC section text.

Extracts normative statements (RFC 2119 keywords) and cross-references
from parsed RFC sections. Separate from parser.py to keep section
detection and semantic analysis as distinct concerns.
"""

from __future__ import annotations

import re
from typing import List

from ivy_lsp.core.rfc.parser import RfcSection
from ivy_lsp.core.rfc.types import CrossReference, NormativeStatement

# RFC 2119 keywords, ordered by strength (strongest first for dedup).
_KEYWORD_PRIORITY = [
    "MUST NOT",
    "SHALL NOT",
    "SHOULD NOT",
    "MUST",
    "SHALL",
    "REQUIRED",
    "SHOULD",
    "RECOMMENDED",
    "MAY",
    "OPTIONAL",
]

_KEYWORD_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _KEYWORD_PRIORITY) + r")\b"
)

# Cross-reference patterns.
# "Section 4.3", "see Section 8.2.1"
_SECTION_REF_RE = re.compile(
    r"(?:see\s+)?Section\s+(\d+(?:\.\d+)*)", re.IGNORECASE
)

# "[RFC4271] Section 2.1" or "[RFC4271], Section 2.1"
_RFC_SECTION_REF_RE = re.compile(
    r"\[RFC\s*(\d+)\]\s*,?\s*Section\s+(\d+(?:\.\d+)*)", re.IGNORECASE
)

# Bare RFC mentions: "RFC 1771", "[RFC1771]", "as defined in RFC 4271"
_BARE_RFC_RE = re.compile(
    r"(?:\[RFC\s*(\d+)\]|RFC\s+(\d+))", re.IGNORECASE
)


def _join_lines(text: str) -> str:
    """Join RFC line-wrapped text into continuous sentences.

    RFC text wraps at ~72 columns with leading whitespace on continuation
    lines. This collapses those wraps so sentence boundary detection works.
    """
    # Replace newline + leading whitespace with a single space.
    return re.sub(r"\n\s+", " ", text).strip()


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences on period-space or period-EOF boundaries."""
    joined = _join_lines(text)
    # Split on ". " followed by uppercase or end of string.
    parts = re.split(r"\.(?:\s+(?=[A-Z])|\s*$)", joined)
    return [p.strip() + "." for p in parts if p.strip()]


class RfcAnalyzer:
    """Extracts normative statements and cross-references from RFC sections."""

    def extract_normative_statements(
        self, section: RfcSection, rfc: str
    ) -> List[NormativeStatement]:
        """Extract sentences containing RFC 2119 keywords.

        Args:
            section: Parsed RFC section with text content.
            rfc: RFC identifier (e.g. "rfc4271") for tag generation.

        Returns:
            List of NormativeStatement objects. When a sentence contains
            multiple keywords, only the strongest (by RFC 2119 priority)
            is kept.
        """
        if not section.text:
            return []

        results: list[NormativeStatement] = []
        seen_sentences: set[str] = set()

        for sentence in _split_sentences(section.text):
            matches = _KEYWORD_RE.findall(sentence)
            if not matches:
                continue

            # Normalize for dedup.
            norm = re.sub(r"\s+", " ", sentence.strip())
            if norm in seen_sentences:
                continue
            seen_sentences.add(norm)

            # Pick the strongest keyword by priority order.
            best_keyword = min(
                matches, key=lambda k: _KEYWORD_PRIORITY.index(k)
            )

            results.append(
                NormativeStatement(
                    keyword=best_keyword,
                    text=norm,
                    section=section.number,
                    rfc=rfc,
                )
            )

        return results

    def extract_cross_references(
        self, section: RfcSection
    ) -> List[CrossReference]:
        """Extract cross-references to other RFCs and sections.

        Args:
            section: Parsed RFC section with text content.

        Returns:
            List of CrossReference objects.
        """
        if not section.text:
            return []

        joined = _join_lines(section.text)
        results: list[CrossReference] = []
        seen: set[tuple] = set()

        # 1. [RFCnnnn] Section X.Y (most specific, check first)
        for m in _RFC_SECTION_REF_RE.finditer(joined):
            rfc_num = m.group(1)
            sec_num = m.group(2)
            key = (f"rfc{rfc_num}", sec_num)
            if key not in seen:
                seen.add(key)
                start = max(0, m.start() - 40)
                end = min(len(joined), m.end() + 40)
                results.append(
                    CrossReference(
                        source_section=section.number,
                        target_rfc=f"rfc{rfc_num}",
                        target_section=sec_num,
                        context=joined[start:end].strip(),
                    )
                )

        # 2. Same-document "Section X.Y"
        for m in _SECTION_REF_RE.finditer(joined):
            sec_num = m.group(1)
            # Skip if this was already captured as part of an [RFCnnnn] Section pattern.
            prefix = joined[max(0, m.start() - 15) : m.start()]
            if re.search(r"\[RFC\s*\d+\]\s*,?\s*$", prefix, re.IGNORECASE):
                continue
            key = (None, sec_num)
            if key not in seen:
                seen.add(key)
                start = max(0, m.start() - 40)
                end = min(len(joined), m.end() + 40)
                results.append(
                    CrossReference(
                        source_section=section.number,
                        target_rfc=None,
                        target_section=sec_num,
                        context=joined[start:end].strip(),
                    )
                )

        # 3. Bare RFC mentions (without section)
        for m in _BARE_RFC_RE.finditer(joined):
            rfc_num = m.group(1) or m.group(2)
            rfc_id = f"rfc{rfc_num}"
            # Skip if already captured with a section number.
            if any(k[0] == rfc_id for k in seen):
                continue
            key = (rfc_id, None)
            if key not in seen:
                seen.add(key)
                start = max(0, m.start() - 40)
                end = min(len(joined), m.end() + 40)
                results.append(
                    CrossReference(
                        source_section=section.number,
                        target_rfc=rfc_id,
                        target_section=None,
                        context=joined[start:end].strip(),
                    )
                )

        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_analyzer.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/rfc/analyzer.py tests/test_rfc_analyzer.py
git commit -m "feat(rfc): add structured analyzer for normative statements and cross-references"
```

---

### Task 3: Two-Tier Cache (`core/rfc/cache.py`)

**Files:**
- Create: `ivy_lsp/core/rfc/cache.py`
- Test: `tests/test_rfc_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rfc_cache.py
"""Tests for RFC two-tier cache."""

import json
import os
import tempfile
import time

import pytest

from ivy_lsp.core.rfc.cache import RfcCache


class TestMemoryTier:
    def setup_method(self):
        self.cache = RfcCache(cache_dir=None, cache_ttl=3600)

    def test_miss_returns_none(self):
        assert self.cache.get("rfc9000") is None

    def test_put_and_get(self):
        self.cache.put("rfc9000", "some text", "abc123", "https://example.com")
        entry = self.cache.get("rfc9000")
        assert entry is not None
        assert entry["text"] == "some text"
        assert entry["content_hash"] == "abc123"

    def test_ttl_expiry(self):
        self.cache = RfcCache(cache_dir=None, cache_ttl=0)
        self.cache.put("rfc9000", "text", "hash", "source")
        # TTL=0 means immediately stale
        time.sleep(0.01)
        assert self.cache.get("rfc9000") is None

    def test_clear(self):
        self.cache.put("rfc9000", "text", "hash", "source")
        self.cache.clear()
        assert self.cache.get("rfc9000") is None


class TestDiskTier:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cache = RfcCache(cache_dir=self.tmpdir, cache_ttl=3600)

    def test_put_creates_files(self):
        self.cache.put("rfc4271", "BGP text", "hash123", "https://example.com")
        rfc_dir = os.path.join(self.tmpdir, "rfc4271")
        assert os.path.isfile(os.path.join(rfc_dir, "raw.txt"))
        assert os.path.isfile(os.path.join(rfc_dir, "meta.json"))

    def test_disk_fallback_on_memory_miss(self):
        self.cache.put("rfc4271", "BGP text", "hash123", "https://example.com")
        # Create a fresh cache instance pointing at same dir (empty memory)
        fresh = RfcCache(cache_dir=self.tmpdir, cache_ttl=3600)
        entry = fresh.get("rfc4271")
        assert entry is not None
        assert entry["text"] == "BGP text"

    def test_meta_json_content(self):
        self.cache.put("rfc4271", "text", "hash123", "https://src.com")
        meta_path = os.path.join(self.tmpdir, "rfc4271", "meta.json")
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["content_hash"] == "hash123"
        assert meta["source"] == "https://src.com"
        assert "fetch_time" in meta


class TestLocalFiles:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.local_dir = tempfile.mkdtemp()
        self.cache = RfcCache(
            cache_dir=self.tmpdir, cache_ttl=3600, local_dir=self.local_dir
        )

    def test_local_file_found(self):
        local_path = os.path.join(self.local_dir, "rfc4271.txt")
        with open(local_path, "w") as f:
            f.write("Local BGP content")
        entry = self.cache.get_local("rfc4271")
        assert entry is not None
        assert entry["text"] == "Local BGP content"

    def test_local_file_not_found(self):
        assert self.cache.get_local("rfc9999") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.core.rfc.cache'`

- [ ] **Step 3: Write minimal implementation**

```python
# ivy_lsp/core/rfc/cache.py
"""Two-tier (memory + disk) cache for RFC documents."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class RfcCache:
    """Two-tier cache: in-memory dict backed by on-disk file store.

    Args:
        cache_dir: Directory for persistent disk cache. None disables disk tier.
        cache_ttl: Seconds before a cached entry is considered stale.
        local_dir: Directory of user-provided local RFC text files.
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        cache_ttl: int = 3600,
        local_dir: str | Path | None = None,
    ):
        self._memory: dict[str, tuple[dict, float]] = {}
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._cache_ttl = cache_ttl
        self._local_dir = Path(local_dir) if local_dir else None

    def get(self, rfc_id: str) -> Optional[dict]:
        """Look up *rfc_id* in memory, then disk. Returns None on miss."""
        rfc_id = self._normalize_id(rfc_id)

        # Memory tier.
        if rfc_id in self._memory:
            entry, ts = self._memory[rfc_id]
            if time.time() - ts < self._cache_ttl:
                return entry
            del self._memory[rfc_id]

        # Disk tier.
        if self._cache_dir is not None:
            disk_entry = self._read_disk(rfc_id)
            if disk_entry is not None:
                self._memory[rfc_id] = (disk_entry, time.time())
                return disk_entry

        return None

    def put(
        self, rfc_id: str, text: str, content_hash: str, source: str
    ) -> None:
        """Store an RFC in both memory and disk tiers."""
        rfc_id = self._normalize_id(rfc_id)
        entry = {
            "text": text,
            "content_hash": content_hash,
            "source": source,
        }
        self._memory[rfc_id] = (entry, time.time())

        if self._cache_dir is not None:
            self._write_disk(rfc_id, text, content_hash, source)

    def get_local(self, rfc_id: str) -> Optional[dict]:
        """Check local RFC directory for a matching file."""
        if self._local_dir is None:
            return None

        rfc_id = self._normalize_id(rfc_id)
        for ext in (".txt", ".text", ""):
            path = self._local_dir / f"{rfc_id}{ext}"
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                content_hash = hashlib.sha256(text.encode()).hexdigest()
                return {
                    "text": text,
                    "content_hash": content_hash,
                    "source": str(path),
                }
        return None

    def clear(self) -> None:
        """Clear the in-memory cache. Disk cache is not deleted."""
        self._memory.clear()

    @staticmethod
    def _normalize_id(rfc_id: str) -> str:
        """Normalize to lowercase, strip 'rfc' prefix inconsistencies."""
        rfc_id = rfc_id.lower().strip()
        if rfc_id.startswith("rfc"):
            return rfc_id
        if rfc_id.isdigit():
            return f"rfc{rfc_id}"
        return rfc_id

    def _read_disk(self, rfc_id: str) -> Optional[dict]:
        """Read cached RFC from disk if present and not stale."""
        rfc_dir = self._cache_dir / rfc_id  # type: ignore[union-attr]
        meta_path = rfc_dir / "meta.json"
        raw_path = rfc_dir / "raw.txt"

        if not meta_path.is_file() or not raw_path.is_file():
            return None

        try:
            with open(meta_path) as f:
                meta = json.load(f)
            fetch_time = meta.get("fetch_time", 0)
            if time.time() - fetch_time >= self._cache_ttl:
                return None
            text = raw_path.read_text(encoding="utf-8", errors="replace")
            return {
                "text": text,
                "content_hash": meta.get("content_hash", ""),
                "source": meta.get("source", ""),
            }
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read disk cache for %s: %s", rfc_id, exc)
            return None

    def _write_disk(
        self, rfc_id: str, text: str, content_hash: str, source: str
    ) -> None:
        """Write RFC text and metadata to disk cache."""
        rfc_dir = self._cache_dir / rfc_id  # type: ignore[union-attr]
        try:
            rfc_dir.mkdir(parents=True, exist_ok=True)
            (rfc_dir / "raw.txt").write_text(text, encoding="utf-8")
            meta = {
                "content_hash": content_hash,
                "source": source,
                "fetch_time": time.time(),
            }
            with open(rfc_dir / "meta.json", "w") as f:
                json.dump(meta, f, indent=2)
        except OSError as exc:
            logger.warning("Failed to write disk cache for %s: %s", rfc_id, exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_cache.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/rfc/cache.py tests/test_rfc_cache.py
git commit -m "feat(rfc): add two-tier cache with local RFC file support"
```

---

### Task 4: IETF Datatracker Search Client (`core/rfc/search.py`)

**Files:**
- Create: `ivy_lsp/core/rfc/search.py`
- Test: `tests/test_rfc_search.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rfc_search.py
"""Tests for IETF Datatracker search client."""

import json
from unittest.mock import patch

import pytest

from ivy_lsp.core.rfc.search import DataTrackerClient
from ivy_lsp.core.rfc.types import RfcSearchResult

MOCK_RESPONSE = {
    "meta": {"total_count": 2},
    "objects": [
        {
            "name": "rfc4271",
            "title": "A Border Gateway Protocol 4 (BGP-4)",
            "time": "2006-01-01T00:00:00",
            "std_level": "/api/v1/name/stdlevelname/ps/",
            "abstract": "This document discusses the Border Gateway Protocol.",
        },
        {
            "name": "rfc4456",
            "title": "BGP Route Reflection",
            "time": "2006-04-01T00:00:00",
            "std_level": "/api/v1/name/stdlevelname/ps/",
            "abstract": "Route reflection for BGP.",
        },
    ],
}


class TestDataTrackerClient:
    def setup_method(self):
        self.client = DataTrackerClient()

    @pytest.mark.asyncio
    async def test_search_parses_results(self):
        with patch(
            "ivy_lsp.core.rfc.search._fetch_json", return_value=MOCK_RESPONSE
        ):
            results = await self.client.search("BGP", limit=5)

        assert len(results) == 2
        assert isinstance(results[0], RfcSearchResult)
        assert results[0].number == "rfc4271"
        assert results[0].title == "A Border Gateway Protocol 4 (BGP-4)"

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        empty_response = {"meta": {"total_count": 0}, "objects": []}
        with patch(
            "ivy_lsp.core.rfc.search._fetch_json", return_value=empty_response
        ):
            results = await self.client.search("nonexistent_xyz")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_caches_results(self):
        with patch(
            "ivy_lsp.core.rfc.search._fetch_json", return_value=MOCK_RESPONSE
        ) as mock_fetch:
            results1 = await self.client.search("BGP", limit=5)
            results2 = await self.client.search("BGP", limit=5)

        # Second call should hit cache, so only one HTTP call
        assert mock_fetch.call_count == 1
        assert len(results2) == 2

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        with patch(
            "ivy_lsp.core.rfc.search._fetch_json",
            side_effect=OSError("Connection refused"),
        ):
            results = await self.client.search("BGP")

        assert results == []

    def test_extract_rfc_number(self):
        assert self.client._extract_rfc_number("rfc4271") == "rfc4271"
        assert self.client._extract_rfc_number("RFC 9000") == "rfc9000"

    def test_extract_std_level(self):
        assert self.client._extract_std_level("/api/v1/name/stdlevelname/ps/") == "Proposed Standard"
        assert self.client._extract_std_level("unknown") == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_search.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.core.rfc.search'`

- [ ] **Step 3: Write minimal implementation**

```python
# ivy_lsp/core/rfc/search.py
"""Async client for the IETF Datatracker REST API.

Uses urllib.request + asyncio.to_thread, matching the pattern in fetcher.py.
No external HTTP dependencies required.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import urllib.request
import urllib.parse
from typing import List

from ivy_lsp.core.rfc.types import RfcSearchResult

logger = logging.getLogger(__name__)

_DATATRACKER_BASE = "https://datatracker.ietf.org/api/v1/doc/document/"
_REQUEST_TIMEOUT = 10  # seconds
_CACHE_TTL = 300  # 5 minutes for search results

_STD_LEVEL_MAP = {
    "ps": "Proposed Standard",
    "ds": "Draft Standard",
    "std": "Internet Standard",
    "bcp": "Best Current Practice",
    "inf": "Informational",
    "exp": "Experimental",
    "hist": "Historic",
}


def _fetch_json(url: str) -> dict:
    """Blocking JSON fetch via urllib (run in thread pool)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


class DataTrackerClient:
    """Async client for searching RFCs via the IETF Datatracker API."""

    def __init__(self) -> None:
        self._search_cache: dict[str, tuple[List[RfcSearchResult], float]] = {}

    async def search(
        self, query: str, limit: int = 10
    ) -> List[RfcSearchResult]:
        """Search for RFCs matching *query*.

        Args:
            query: Search terms.
            limit: Maximum number of results.

        Returns:
            List of RfcSearchResult objects.
        """
        cache_key = f"{query}:{limit}"
        if cache_key in self._search_cache:
            results, ts = self._search_cache[cache_key]
            if time.time() - ts < _CACHE_TTL:
                return results

        params = urllib.parse.urlencode({
            "format": "json",
            "name__contains": query.lower(),
            "type": "rfc",
            "limit": str(limit),
        })
        url = f"{_DATATRACKER_BASE}?{params}"

        try:
            data = await asyncio.to_thread(_fetch_json, url)
        except (OSError, json.JSONDecodeError, TimeoutError) as exc:
            logger.warning("Datatracker search failed: %s", exc)
            return []

        results: list[RfcSearchResult] = []
        for obj in data.get("objects", []):
            name = obj.get("name", "")
            results.append(
                RfcSearchResult(
                    number=self._extract_rfc_number(name),
                    title=obj.get("title", ""),
                    date=obj.get("time", "")[:10],
                    status=self._extract_std_level(
                        obj.get("std_level", "")
                    ),
                    abstract=obj.get("abstract", "")[:500],
                )
            )

        self._search_cache[cache_key] = (results, time.time())
        return results

    @staticmethod
    def _extract_rfc_number(name: str) -> str:
        """Normalize an RFC name like 'rfc4271' or 'RFC 9000' to 'rfcNNNN'."""
        m = re.search(r"(\d+)", name)
        return f"rfc{m.group(1)}" if m else name.lower()

    @staticmethod
    def _extract_std_level(level_uri: str) -> str:
        """Convert Datatracker std_level URI to human-readable string."""
        for key, label in _STD_LEVEL_MAP.items():
            if f"/{key}/" in level_uri:
                return label
        return level_uri if level_uri else "Unknown"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_search.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/rfc/search.py tests/test_rfc_search.py
git commit -m "feat(rfc): add IETF Datatracker search client"
```

---

### Task 5: RFC Service Facade (`core/rfc/service.py`)

**Files:**
- Create: `ivy_lsp/core/rfc/service.py`
- Test: `tests/test_rfc_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rfc_service.py
"""Tests for the RfcService facade."""

import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from ivy_lsp.core.rfc.parser import ParsedRfc, RfcSection
from ivy_lsp.core.rfc.service import RfcService
from ivy_lsp.core.rfc.types import RfcDocument

SAMPLE_RFC_TEXT = """\
Network Working Group                                         Y. Rekhter
Request for Comments: 4271                                      T. Li


         A Border Gateway Protocol 4 (BGP-4)

Status of this Memo

   This document specifies an Internet standards track protocol.

1.  Introduction

   The Border Gateway Protocol (BGP) is an inter-Autonomous System
   routing protocol.

2.  Summary of Operation

   BGP peers MUST use TCP as the transport protocol.

3.  Message Formats

3.1.  Message Header Format

   Each message has a fixed-size header.  See Section 2 for context.
   Implementations SHOULD follow [RFC1771] guidelines.
"""


class TestRfcServiceGetRfc:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.service = RfcService(cache_dir=self.tmpdir)

    @pytest.mark.asyncio
    async def test_get_rfc_full(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            from ivy_lsp.core.rfc.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc123",
            )
            doc = await self.service.get_rfc("4271", format="full")

        assert isinstance(doc, RfcDocument)
        assert doc.number == "rfc4271"
        assert len(doc.sections) > 0

    @pytest.mark.asyncio
    async def test_get_rfc_metadata(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            from ivy_lsp.core.rfc.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc123",
            )
            doc = await self.service.get_rfc("4271", format="metadata")

        assert doc.number == "rfc4271"
        assert doc.sections == []  # metadata mode strips sections

    @pytest.mark.asyncio
    async def test_get_rfc_sections_toc(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            from ivy_lsp.core.rfc.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc123",
            )
            doc = await self.service.get_rfc("4271", format="sections")

        assert len(doc.sections) > 0
        for s in doc.sections:
            assert s.text == ""  # sections mode strips body text


class TestRfcServiceGetSection:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.service = RfcService(cache_dir=self.tmpdir)

    @pytest.mark.asyncio
    async def test_get_existing_section(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            from ivy_lsp.core.rfc.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc123",
            )
            section = await self.service.get_section("4271", "2")

        assert section is not None
        assert section.number == "2"
        assert "MUST" in section.text

    @pytest.mark.asyncio
    async def test_get_nonexistent_section(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            from ivy_lsp.core.rfc.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc123",
            )
            section = await self.service.get_section("4271", "99.9")

        assert section is None


class TestRfcServiceTagResolution:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.service = RfcService(cache_dir=self.tmpdir)

    @pytest.mark.asyncio
    async def test_resolve_tag(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            from ivy_lsp.core.rfc.fetcher import FetchResult

            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc123",
            )
            section = await self.service.resolve_tag_to_section("rfc4271:2")

        assert section is not None
        assert section.number == "2"

    @pytest.mark.asyncio
    async def test_resolve_invalid_tag(self):
        section = await self.service.resolve_tag_to_section("not-a-tag")
        assert section is None


class TestRfcServiceLocalCache:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.local_dir = tempfile.mkdtemp()
        self.service = RfcService(
            cache_dir=self.tmpdir, local_dir=self.local_dir
        )

    @pytest.mark.asyncio
    async def test_local_file_used_first(self):
        local_path = os.path.join(self.local_dir, "rfc4271.txt")
        with open(local_path, "w") as f:
            f.write(SAMPLE_RFC_TEXT)

        # Should NOT call fetch_rfc since local file exists
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            doc = await self.service.get_rfc("4271")
            mock_fetch.assert_not_called()

        assert doc.number == "rfc4271"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.core.rfc.service'`

- [ ] **Step 3: Write minimal implementation**

```python
# ivy_lsp/core/rfc/service.py
"""Unified RFC service layer.

Composes fetcher, parser, analyzer, cache, and search into a single
facade for all RFC operations.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

from ivy_lsp.core.rfc.analyzer import RfcAnalyzer
from ivy_lsp.core.rfc.cache import RfcCache
from ivy_lsp.core.rfc.fetcher import FetchError, fetch_rfc
from ivy_lsp.core.rfc.parser import RfcSection, parse_rfc_text
from ivy_lsp.core.rfc.search import DataTrackerClient
from ivy_lsp.core.rfc.types import (
    CrossReference,
    NormativeStatement,
    RfcDocument,
    RfcMetadata,
    RfcSearchResult,
)

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"^(rfc\d+):(.+)$", re.IGNORECASE)
_RFC_NUM_RE = re.compile(r"^(?:rfc\s*)?(\d+)$", re.IGNORECASE)


class RfcService:
    """Unified entry point for RFC document operations.

    Args:
        cache_dir: Directory for persistent disk cache.
        cache_ttl: Seconds before cached entries are stale.
        local_dir: Directory of user-provided local RFC files.
        offline: If True, never attempt remote fetch.
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        cache_ttl: int = 3600,
        local_dir: str | Path | None = None,
        offline: bool = False,
    ):
        self._cache = RfcCache(
            cache_dir=cache_dir, cache_ttl=cache_ttl, local_dir=local_dir
        )
        self._analyzer = RfcAnalyzer()
        self._search_client = DataTrackerClient()
        self._offline = offline

    async def get_rfc(
        self, number: str, format: str = "full"
    ) -> RfcDocument:
        """Fetch and parse an RFC document.

        Args:
            number: RFC number (e.g. "4271", "rfc9000") or draft ID.
            format: "full" (all sections with text), "metadata" (no sections),
                    or "sections" (TOC only, no body text).

        Returns:
            RfcDocument with content based on format.

        Raises:
            FetchError: If the RFC cannot be retrieved.
        """
        rfc_id = self._normalize_rfc_id(number)
        text = await self._fetch_text(rfc_id, number)
        parsed = parse_rfc_text(text)

        rfc_number = parsed.rfc_number or rfc_id
        if not rfc_number.startswith("rfc"):
            rfc_number = f"rfc{rfc_number}"
        rfc_number = rfc_number.lower()

        metadata = RfcMetadata(date="", status="")

        if format == "metadata":
            return RfcDocument(
                number=rfc_number,
                title=parsed.title,
                sections=[],
                metadata=metadata,
            )

        if format == "sections":
            toc_sections = [
                RfcSection(
                    number=s.number,
                    title=s.title,
                    start_line=s.start_line,
                    text="",
                )
                for s in parsed.sections
            ]
            return RfcDocument(
                number=rfc_number,
                title=parsed.title,
                sections=toc_sections,
                metadata=metadata,
            )

        # "full"
        return RfcDocument(
            number=rfc_number,
            title=parsed.title,
            sections=parsed.sections,
            metadata=metadata,
        )

    async def get_section(
        self, number: str, section: str
    ) -> Optional[RfcSection]:
        """Fetch a specific section from an RFC.

        Args:
            number: RFC number.
            section: Section number (e.g. "6.2", "4.1.1").

        Returns:
            RfcSection if found, None otherwise.
        """
        doc = await self.get_rfc(number, format="full")
        for s in doc.sections:
            if s.number == section:
                return s
        return None

    async def search(
        self, query: str, limit: int = 10
    ) -> List[RfcSearchResult]:
        """Search for RFCs by keyword via the IETF Datatracker API.

        Args:
            query: Search terms.
            limit: Maximum results.

        Returns:
            List of search results. Empty list if offline or on error.
        """
        if self._offline:
            logger.info("RFC search skipped: offline mode")
            return []
        return await self._search_client.search(query, limit=limit)

    def extract_normative_statements(
        self, section: RfcSection, rfc: str
    ) -> List[NormativeStatement]:
        """Extract normative statements from a section."""
        return self._analyzer.extract_normative_statements(section, rfc=rfc)

    def extract_cross_references(
        self, section: RfcSection
    ) -> List[CrossReference]:
        """Extract cross-references from a section."""
        return self._analyzer.extract_cross_references(section)

    async def resolve_tag_to_section(
        self, tag: str
    ) -> Optional[RfcSection]:
        """Resolve a bracket-tag annotation to its RFC section.

        Args:
            tag: Tag like "rfc4271:6.2".

        Returns:
            RfcSection if the tag parses and section exists, None otherwise.
        """
        m = _TAG_RE.match(tag)
        if not m:
            return None
        rfc_id = m.group(1).lower()
        section_num = m.group(2)
        try:
            return await self.get_section(rfc_id, section_num)
        except FetchError:
            logger.warning("Failed to resolve tag '%s': fetch error", tag)
            return None

    def set_local_cache_dir(self, path: Path) -> None:
        """Override the local RFC directory at runtime."""
        self._cache._local_dir = path

    def clear_cache(self) -> None:
        """Clear all in-memory caches."""
        self._cache.clear()

    async def _fetch_text(self, rfc_id: str, original_source: str) -> str:
        """Fetch RFC text using resolution order: local → cache → remote."""
        # 1. Local files
        local = self._cache.get_local(rfc_id)
        if local is not None:
            return local["text"]

        # 2. Cache (memory + disk)
        cached = self._cache.get(rfc_id)
        if cached is not None:
            return cached["text"]

        # 3. Remote fetch
        if self._offline:
            raise FetchError(
                f"RFC {rfc_id} not found locally and offline mode is enabled"
            )

        result = await fetch_rfc(original_source, use_cache=False)
        self._cache.put(
            rfc_id, result.text, result.content_hash, result.source
        )
        return result.text

    @staticmethod
    def _normalize_rfc_id(number: str) -> str:
        """Normalize input to 'rfcNNNN' format."""
        number = number.strip()
        m = _RFC_NUM_RE.match(number)
        if m:
            return f"rfc{m.group(1)}"
        if number.lower().startswith("rfc"):
            return number.lower()
        return number.lower()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_service.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/rfc/service.py tests/test_rfc_service.py
git commit -m "feat(rfc): add RfcService facade composing fetcher, parser, analyzer, cache, search"
```

---

### Task 6: Update Exports and Configuration

**Files:**
- Modify: `ivy_lsp/core/rfc/__init__.py`
- Modify: `ivy_lsp/infra/config.py`
- Test: `tests/test_rfc_config.py`

- [ ] **Step 1: Write the failing test for config**

```python
# tests/test_rfc_config.py
"""Tests for RFC-related configuration."""

import os
from unittest.mock import patch

from ivy_lsp.infra.config import ServerConfig, reset_config


class TestRfcConfig:
    def teardown_method(self):
        reset_config()

    def test_default_values(self):
        with patch.dict(os.environ, {}, clear=False):
            cfg = ServerConfig.from_env()
        assert cfg.rfc_cache_ttl == 3600
        assert cfg.rfc_offline is False
        assert cfg.rfc_cache_dir is None
        assert cfg.rfc_local_dir is None

    def test_custom_values(self):
        env = {
            "IVY_LSP_RFC_CACHE_TTL": "7200",
            "IVY_LSP_RFC_OFFLINE": "1",
            "IVY_LSP_RFC_CACHE_DIR": "/tmp/rfc-cache",
            "IVY_LSP_RFC_LOCAL_DIR": "/tmp/rfc-local",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = ServerConfig.from_env()
        assert cfg.rfc_cache_ttl == 7200
        assert cfg.rfc_offline is True
        assert cfg.rfc_cache_dir == "/tmp/rfc-cache"
        assert cfg.rfc_local_dir == "/tmp/rfc-local"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_config.py -v`
Expected: FAIL with `AttributeError: 'ServerConfig' object has no attribute 'rfc_cache_ttl'`

- [ ] **Step 3: Add RFC fields to ServerConfig**

Add these fields to the `ServerConfig` dataclass in `ivy_lsp/infra/config.py`:

```python
    # RFC service
    rfc_cache_dir: str | None = None
    rfc_cache_ttl: int = 3600
    rfc_local_dir: str | None = None
    rfc_offline: bool = False
```

Add these lines to `ServerConfig.from_env()`:

```python
        rfc_cache_dir=os.environ.get("IVY_LSP_RFC_CACHE_DIR"),
        rfc_cache_ttl=_int_env("IVY_LSP_RFC_CACHE_TTL", 3600),
        rfc_local_dir=os.environ.get("IVY_LSP_RFC_LOCAL_DIR"),
        rfc_offline=_bool_env("IVY_LSP_RFC_OFFLINE", "0"),
```

- [ ] **Step 4: Update `core/rfc/__init__.py` exports**

Replace the contents of `ivy_lsp/core/rfc/__init__.py` with:

```python
from ivy_lsp.core.rfc.analyzer import RfcAnalyzer
from ivy_lsp.core.rfc.cache import RfcCache
from ivy_lsp.core.rfc.fetcher import FetchError, FetchResult, fetch_rfc
from ivy_lsp.core.rfc.parser import ParsedRfc, RfcSection, parse_rfc_text
from ivy_lsp.core.rfc.search import DataTrackerClient
from ivy_lsp.core.rfc.service import RfcService
from ivy_lsp.core.rfc.types import (
    CrossReference,
    NormativeStatement,
    RfcDocument,
    RfcMetadata,
    RfcSearchResult,
)

__all__ = [
    "CrossReference",
    "DataTrackerClient",
    "FetchError",
    "FetchResult",
    "NormativeStatement",
    "ParsedRfc",
    "RfcAnalyzer",
    "RfcCache",
    "RfcDocument",
    "RfcMetadata",
    "RfcSearchResult",
    "RfcSection",
    "RfcService",
    "fetch_rfc",
    "parse_rfc_text",
]
```

- [ ] **Step 5: Run tests to verify**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_config.py tests/test_rfc_types.py tests/test_rfc_analyzer.py tests/test_rfc_cache.py tests/test_rfc_service.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/core/rfc/__init__.py ivy_lsp/infra/config.py tests/test_rfc_config.py
git commit -m "feat(rfc): update exports and add RFC config env vars"
```

---

### Task 7: Wire RfcService into MCP Server

**Files:**
- Modify: `ivy_lsp/mcp/context.py` (add `rfc_service` field)
- Modify: `ivy_lsp/mcp/server.py` (instantiate `RfcService` in `build_tool_context`)

- [ ] **Step 1: Add `rfc_service` field to ToolContext**

In `ivy_lsp/mcp/context.py`, add this field to the `ToolContext` dataclass after the `stdlib_modules` field:

```python
    # RFC service (lazy — set by McpServerState.build_tool_context)
    rfc_service: Any = None
```

- [ ] **Step 2: Instantiate RfcService in McpServerState.build_tool_context**

In `ivy_lsp/mcp/server.py`, at the end of `build_tool_context()` method, before `return ctx`, add:

```python
        # Wire up RFC service
        from ivy_lsp.core.rfc.service import RfcService
        from ivy_lsp.infra.config import get_config

        cfg = get_config()
        cache_dir = cfg.rfc_cache_dir
        if cache_dir is None and self.root:
            cache_dir = os.path.join(self.root, ".ivy-cache", "rfc")
        ctx.rfc_service = RfcService(
            cache_dir=cache_dir,
            cache_ttl=cfg.rfc_cache_ttl,
            local_dir=cfg.rfc_local_dir,
            offline=cfg.rfc_offline,
        )
```

- [ ] **Step 3: Verify existing tests still pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: No regressions

- [ ] **Step 4: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/context.py ivy_lsp/mcp/server.py
git commit -m "feat(rfc): wire RfcService into MCP server context"
```

---

### Task 8: MCP Tools (`mcp/tools/rfc_tools.py`)

**Files:**
- Create: `ivy_lsp/mcp/tools/rfc_tools.py`
- Modify: `ivy_lsp/mcp/tools/__init__.py` (register tools + metadata)
- Test: `tests/test_rfc_tools.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rfc_tools.py
"""Tests for RFC MCP tools."""

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ivy_lsp.core.rfc.fetcher import FetchResult
from ivy_lsp.core.rfc.service import RfcService


SAMPLE_RFC_TEXT = """\
Network Working Group                                         Y. Rekhter
Request for Comments: 4271


         A Border Gateway Protocol 4 (BGP-4)

1.  Introduction

   The Border Gateway Protocol is inter-AS routing.

2.  Summary

   Peers MUST use TCP.  See Section 1 for background.
   Implementations SHOULD validate all fields.

3.  Messages

   Each message has a header.
"""


class TestIvyRfcGetTool:
    """Test the ivy_rfc_get tool logic directly via RfcService."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.service = RfcService(cache_dir=self.tmpdir)

    @pytest.mark.asyncio
    async def test_get_full(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc",
            )
            doc = await self.service.get_rfc("4271", format="full")
        assert doc.number == "rfc4271"
        assert len(doc.sections) >= 3

    @pytest.mark.asyncio
    async def test_get_sections_toc(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc",
            )
            doc = await self.service.get_rfc("4271", format="sections")
        for s in doc.sections:
            assert s.text == ""


class TestIvyRfcSectionTool:
    """Test the ivy_rfc_section tool logic."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.service = RfcService(cache_dir=self.tmpdir)

    @pytest.mark.asyncio
    async def test_section_with_analysis(self):
        with patch("ivy_lsp.core.rfc.service.fetch_rfc") as mock_fetch:
            mock_fetch.return_value = FetchResult(
                text=SAMPLE_RFC_TEXT,
                source="https://rfc-editor.org/rfc/rfc4271.txt",
                content_hash="abc",
            )
            section = await self.service.get_section("4271", "2")
            assert section is not None
            stmts = self.service.extract_normative_statements(section, rfc="rfc4271")
            refs = self.service.extract_cross_references(section)

        assert len(stmts) >= 1
        assert any(s.keyword == "MUST" for s in stmts)
        assert any(r.target_section == "1" for r in refs)


class TestIvyRfcSearchTool:
    """Test the ivy_rfc_search tool logic."""

    def setup_method(self):
        self.service = RfcService()

    @pytest.mark.asyncio
    async def test_offline_returns_empty(self):
        self.service._offline = True
        results = await self.service.search("BGP")
        assert results == []


class TestToolMetadataRegistration:
    """Verify tool metadata is registered correctly."""

    def test_rfc_tools_in_metadata(self):
        from ivy_lsp.mcp.tools import get_tool_metadata

        for tool_name in ["ivy_rfc_get", "ivy_rfc_search", "ivy_rfc_section"]:
            meta = get_tool_metadata(tool_name)
            assert meta is not None, f"{tool_name} not registered"
            assert meta["category"] == "rfc"
            assert meta["needs_model"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_tools.py -v`
Expected: FAIL on `TestToolMetadataRegistration` (tools not registered yet)

- [ ] **Step 3: Create `rfc_tools.py`**

```python
# ivy_lsp/mcp/tools/rfc_tools.py
"""RFC lookup, search, and section analysis MCP tools."""

from __future__ import annotations

import logging
from typing import Any

from ivy_lsp.mcp.tools import error_response, safe_tool

logger = logging.getLogger(__name__)


def register_rfc_tools(mcp: Any, ctx: Any) -> None:
    """Register RFC MCP tools."""

    @mcp.tool()
    @safe_tool(ctx=ctx)
    async def ivy_rfc_get(
        number: str,
        format: str = "full",
    ) -> dict:
        """Retrieve an RFC document by number.

        Fetches from local cache, disk cache, or IETF remote (in that order).

        Args:
            number: RFC number (e.g. "4271", "rfc9000") or draft ID.
            format: "full" (complete document), "metadata" (title/status only),
                    or "sections" (table of contents without body text).
        """
        if ctx.rfc_service is None:
            return error_response("RFC service not initialized.")

        if format not in ("full", "metadata", "sections"):
            return error_response(
                f"Unknown format '{format}'. Valid: full, metadata, sections."
            )

        try:
            doc = await ctx.rfc_service.get_rfc(number, format=format)
        except Exception as exc:
            return error_response(f"Failed to fetch RFC {number}: {exc}")

        result: dict[str, Any] = {
            "status": "ok",
            "number": doc.number,
            "title": doc.title,
            "format": format,
        }

        if format == "metadata":
            result["metadata"] = {
                "authors": doc.metadata.authors,
                "date": doc.metadata.date,
                "status": doc.metadata.status,
                "obsoletes": doc.metadata.obsoletes,
                "updates": doc.metadata.updates,
            }
        elif format == "sections":
            result["sections"] = [
                {"number": s.number, "title": s.title}
                for s in doc.sections
            ]
        else:  # full
            result["sections"] = [
                {
                    "number": s.number,
                    "title": s.title,
                    "text": s.text,
                }
                for s in doc.sections
            ]

        return result

    @mcp.tool()
    @safe_tool(ctx=ctx)
    async def ivy_rfc_search(
        query: str,
        limit: int = 10,
    ) -> dict:
        """Search for RFCs by keyword via the IETF Datatracker API.

        Args:
            query: Search terms (e.g. "BGP path attributes").
            limit: Maximum number of results (default 10).
        """
        if ctx.rfc_service is None:
            return error_response("RFC service not initialized.")

        try:
            results = await ctx.rfc_service.search(query, limit=limit)
        except Exception as exc:
            return error_response(f"Search failed: {exc}")

        return {
            "status": "ok",
            "query": query,
            "count": len(results),
            "results": [
                {
                    "number": r.number,
                    "title": r.title,
                    "date": r.date,
                    "status": r.status,
                    "abstract": r.abstract,
                }
                for r in results
            ],
        }

    @mcp.tool()
    @safe_tool(ctx=ctx)
    async def ivy_rfc_section(
        number: str,
        section: str,
        analyze: bool = True,
    ) -> dict:
        """Extract a specific RFC section with optional normative analysis.

        Returns the section text and, when analyze=True, structured
        normative statements (MUST/SHOULD/MAY) with tag IDs matching
        the bracket-tag format used in Ivy annotations, plus
        cross-references to other RFCs/sections.

        Args:
            number: RFC number (e.g. "4271", "rfc9000").
            section: Section number (e.g. "6.2", "4.1.1").
            analyze: If True (default), include normative statements
                     and cross-references.
        """
        if ctx.rfc_service is None:
            return error_response("RFC service not initialized.")

        try:
            sec = await ctx.rfc_service.get_section(number, section)
        except Exception as exc:
            return error_response(f"Failed to fetch section: {exc}")

        if sec is None:
            return error_response(
                f"Section {section} not found in RFC {number}."
            )

        rfc_id = number.lower()
        if not rfc_id.startswith("rfc"):
            rfc_id = f"rfc{rfc_id}"

        result: dict[str, Any] = {
            "status": "ok",
            "rfc": rfc_id,
            "section": sec.number,
            "title": sec.title,
            "text": sec.text,
        }

        if analyze:
            stmts = ctx.rfc_service.extract_normative_statements(
                sec, rfc=rfc_id
            )
            refs = ctx.rfc_service.extract_cross_references(sec)

            result["normative_statements"] = [
                {
                    "keyword": s.keyword,
                    "text": s.text,
                    "tag": s.tag,
                }
                for s in stmts
            ]
            result["cross_references"] = [
                {
                    "target_rfc": r.target_rfc,
                    "target_section": r.target_section,
                    "context": r.context,
                }
                for r in refs
            ]

        return result
```

- [ ] **Step 4: Register tools in `__init__.py`**

In `ivy_lsp/mcp/tools/__init__.py`, add the import:

```python
from ivy_lsp.mcp.tools.rfc_tools import register_rfc_tools
```

Add the tool metadata entries to `_TOOL_METADATA`:

```python
    "ivy_rfc_get": {"cost": "low", "category": "rfc", "needs_model": False},
    "ivy_rfc_search": {"cost": "medium", "category": "rfc", "needs_model": False},
    "ivy_rfc_section": {"cost": "low", "category": "rfc", "needs_model": False},
```

Add the timeout entries to `_TOOL_TIMEOUTS`:

```python
    "ivy_rfc_get": 30.0,
    "ivy_rfc_search": 15.0,
    "ivy_rfc_section": 30.0,
```

Add the registration call in `register_all_tools()`:

```python
    register_rfc_tools(mcp, ctx)
```

- [ ] **Step 5: Run all RFC tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_rfc_types.py tests/test_rfc_analyzer.py tests/test_rfc_cache.py tests/test_rfc_search.py tests/test_rfc_service.py tests/test_rfc_tools.py tests/test_rfc_config.py -v`
Expected: ALL PASS

- [ ] **Step 6: Run the full test suite to check for regressions**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: No regressions from existing tests

- [ ] **Step 7: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/mcp/tools/rfc_tools.py ivy_lsp/mcp/tools/__init__.py tests/test_rfc_tools.py
git commit -m "feat(rfc): add ivy_rfc_get, ivy_rfc_search, ivy_rfc_section MCP tools"
```

---

### Task 9: Update Submodule Pointer in Parent Repo

**Files:**
- Modify: submodule pointer at `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp`

- [ ] **Step 1: Verify all tests pass in submodule**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20`
Expected: ALL PASS

- [ ] **Step 2: Verify git log shows all RFC commits**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && git log --oneline -8`
Expected: 7 commits with `feat(rfc):` prefix

- [ ] **Step 3: Update submodule pointer in parent repo**

```bash
cd /Users/elniak/Documents/Documents/Work/Project/Protocol-Testing-Security/PANTHER/master/.claude/worktrees/lsp-to-claude
git add panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git commit -m "chore: update ivy-lsp submodule for RFC service integration"
```
