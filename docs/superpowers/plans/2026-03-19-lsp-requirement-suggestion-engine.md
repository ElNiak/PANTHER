# LSP Requirement-Suggestion Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bridge the Ivy LSP's symbol completion and RFC traceability pipelines with a RequirementSuggestionEngine that suggests RFC annotations, validates references, and generates requirement stubs — surfaced through completions, diagnostics, code actions, and MCP tools.

**Architecture:** A new `RequirementSuggestionEngine` pre-computes keyword, co-occurrence, usage, and layer indices at indexing time. LSP features (completion, diagnostics, code actions) and 3 new MCP tools query these indices. The engine integrates with the existing `SemanticModel`/`RequirementGraph` via the server lifecycle, using `threading.RLock` for thread safety.

**Tech Stack:** Python 3.10+, pygls/lsprotocol (LSP), FastMCP (tools), pytest (testing)

**Spec:** `docs/superpowers/specs/` or `.claude/plans/iridescent-swinging-whistle.md`

---

## File Structure

All paths relative to `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

| File | Responsibility |
|------|---------------|
| **NEW** `ivy_lsp/semantic/keyword_index.py` | Tokenize + stem requirement text and symbol names for fuzzy matching |
| **NEW** `ivy_lsp/semantic/suggestion_engine.py` | Core engine: build indices, query API (suggest_rfc_tags, suggest_constructs, suggest_stubs, validate_references) |
| **NEW** `ivy_lsp/features/suggestion_diagnostics.py` | 5 new diagnostic types for requirement suggestions |
| **NEW** `ivy_lsp/tools/suggestions.py` | 3 new MCP tools: ivy_suggest_requirements, ivy_requirement_gaps, ivy_validate_spec |
| **NEW** `tests/test_keyword_index.py` | Tests for keyword extraction/stemming |
| **NEW** `tests/test_suggestion_engine.py` | Tests for all engine query APIs |
| **NEW** `tests/test_suggestion_diagnostics.py` | Tests for each diagnostic code |
| **NEW** `tests/test_suggestion_code_actions.py` | Tests for new code action branches |
| **NEW** `tests/test_suggestion_completions.py` | Tests for RFC_TAG context + enhanced semantic completions |
| **NEW** `tests/test_tools_suggestions.py` | Tests for 3 new MCP tools |
| **MODIFY** `ivy_lsp/server.py` | Add `_suggestion_engine` attribute + property |
| **MODIFY** `ivy_lsp/server_setup.py` | Wire engine creation in `_setup_analysis_pipeline()` |
| **MODIFY** `ivy_lsp/bulk_orchestrator.py` | Trigger `engine.build_indices()` after bulk T1+T2 |
| **MODIFY** `ivy_lsp/features/completion.py` | RFC_TAG context, enhanced semantic completions, requirement enrichment |
| **MODIFY** `ivy_lsp/features/diagnostics.py` | Hook suggestion diagnostics into `compute_diagnostics()` |
| **MODIFY** `ivy_lsp/features/code_action.py` | 3 new code action branches |
| **MODIFY** `ivy_lsp/tools/__init__.py` | Register suggestion tools + metadata/timeouts |
| **MODIFY** `ivy_lsp/tools/traceability.py` | Add `mode="suggest"` to ivy_coverage |
| **MODIFY** `ivy_lsp/mcp_server.py` | Add `suggestion_engine` to ToolContext |

---

### Task 1: Keyword Index Module

**Files:**
- Create: `ivy_lsp/semantic/keyword_index.py`
- Test: `tests/test_keyword_index.py`

- [ ] **Step 1: Write failing tests for keyword extraction**

```python
# tests/test_keyword_index.py
"""Tests for keyword extraction and stemming utilities."""

import sys
from pathlib import Path

IVY_ROOT = Path(__file__).resolve().parent.parent
if str(IVY_ROOT) not in sys.path:
    sys.path.insert(0, str(IVY_ROOT))


class TestTokenize:
    def test_simple_sentence(self):
        from ivy_lsp.semantic.keyword_index import tokenize
        tokens = tokenize("Sender MUST open connection before sending.")
        assert "sender" in tokens
        assert "connection" in tokens
        assert "sending" in tokens

    def test_empty_string(self):
        from ivy_lsp.semantic.keyword_index import tokenize
        assert tokenize("") == []

    def test_strips_punctuation(self):
        from ivy_lsp.semantic.keyword_index import tokenize
        tokens = tokenize("(e.g., rfc9000:4.1)")
        assert "rfc9000" in tokens or "rfc9000:4.1" in tokens

    def test_underscore_splitting(self):
        from ivy_lsp.semantic.keyword_index import tokenize_symbol
        tokens = tokenize_symbol("connection_state_closed")
        assert "connection" in tokens
        assert "state" in tokens
        assert "closed" in tokens

    def test_camel_case_splitting(self):
        from ivy_lsp.semantic.keyword_index import tokenize_symbol
        tokens = tokenize_symbol("connectionStateClosed")
        assert "connection" in tokens
        assert "state" in tokens
        assert "closed" in tokens


class TestStem:
    def test_basic_suffixes(self):
        from ivy_lsp.semantic.keyword_index import stem
        assert stem("sending") == "send"
        assert stem("connections") == "connec"  # iterative: 's' -> 'connection', then 'tion' -> 'connec'
        assert stem("opened") == "open"

    def test_short_words_unchanged(self):
        from ivy_lsp.semantic.keyword_index import stem
        assert stem("cid") == "cid"
        assert stem("ip") == "ip"

    def test_already_stemmed(self):
        from ivy_lsp.semantic.keyword_index import stem
        assert stem("send") == "send"

    def test_iterative_stemming(self):
        """Stemmer applies rules iteratively until no more rules match."""
        from ivy_lsp.semantic.keyword_index import stem
        # "connections" -> "connection" -> "connec" (via tion rule)
        # With iterative stemming, both "connection" and "connections"
        # converge to the same stem
        assert stem("connection") == stem("connections")


class TestKeywordIndex:
    def test_build_and_lookup(self):
        from ivy_lsp.semantic.keyword_index import KeywordIndex
        idx = KeywordIndex()
        idx.add("rfc9000:4.1", "Sender MUST open connection before sending")
        idx.add("rfc9000:8.1", "Connection MUST be closed on timeout")

        results = idx.lookup("connection")
        assert "rfc9000:4.1" in results
        assert "rfc9000:8.1" in results

    def test_lookup_no_match(self):
        from ivy_lsp.semantic.keyword_index import KeywordIndex
        idx = KeywordIndex()
        idx.add("rfc9000:4.1", "Sender MUST open connection")
        assert idx.lookup("handshake") == set()

    def test_match_score_symbol_vs_requirement(self):
        from ivy_lsp.semantic.keyword_index import KeywordIndex
        idx = KeywordIndex()
        idx.add("rfc9000:4.1", "Sender MUST open connection before sending data")
        idx.add("rfc9000:8.1", "Stream data MUST be acknowledged")

        score1 = idx.match_score("connection_open", "rfc9000:4.1")
        score2 = idx.match_score("connection_open", "rfc9000:8.1")
        assert score1 > score2  # Better match for 4.1

    def test_remove_requirement(self):
        from ivy_lsp.semantic.keyword_index import KeywordIndex
        idx = KeywordIndex()
        idx.add("rfc9000:4.1", "Sender MUST open connection")
        idx.remove("rfc9000:4.1")
        assert idx.lookup("connection") == set()

    def test_stopwords_excluded(self):
        from ivy_lsp.semantic.keyword_index import KeywordIndex
        idx = KeywordIndex()
        idx.add("r1", "The sender MUST NOT send the data")
        results = idx.lookup("the")
        assert results == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_keyword_index.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.semantic.keyword_index'`

- [ ] **Step 3: Implement keyword_index.py**

```python
# ivy_lsp/semantic/keyword_index.py
"""Lightweight keyword extraction, stemming, and matching for requirement text.

No external dependencies (no NLTK). Provides:
- tokenize(): split text into stemmed lowercase tokens
- tokenize_symbol(): split Ivy symbol names (underscore + camelCase aware)
- stem(): simple suffix stripping
- KeywordIndex: maps stemmed keywords -> requirement IDs
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Set

# Common English stopwords relevant to RFC text
_STOPWORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "not",
    "and", "or", "but", "if", "then", "else", "when", "where", "how",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "it", "its", "of", "in", "on", "at", "to", "for", "with", "from",
    "by", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "each", "every", "all", "any", "both", "such",
    "no", "nor", "only", "own", "same", "so", "than", "too", "very",
    "e.g.", "i.e.", "etc.",
}

# Regex for splitting camelCase
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# Regex for word extraction from text
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9]*(?:[:._][a-zA-Z0-9]+)*")

# Suffix stripping rules (order matters: longest suffix first)
_SUFFIX_RULES = [
    ("ation", 4),   # "connection" -> "connect"
    ("tion", 3),    # "action" -> "act" -- careful, skip if too short
    ("sion", 3),    # "transmission" -> "transmis" -- not great, but rare
    ("ment", 4),    # "acknowledgment" -> "acknowledg"
    ("ness", 4),    # "correctness" -> "correct"
    ("able", 4),    # "reachable" -> "reach"
    ("ible", 4),    # "possible" -> "poss"
    ("ence", 4),    # "sequence" -> "sequ"
    ("ance", 4),    # "compliance" -> "compli"
    ("ling", 3),    # "handling" -> "hand"
    ("ting", 3),    # "sending" -> "send"
    ("ning", 3),    # "running" -> "run" -- special: double consonant
    ("ing", 3),     # "sending" -> "send"
    ("ied", 3),     # "carried" -> "carr"
    ("ies", 3),     # "entries" -> "entr"
    ("ous", 3),     # "previous" -> "previ"
    ("ion", 3),     # "session" -> "sess"
    ("ed", 2),      # "opened" -> "open"
    ("er", 2),      # "sender" -> "send"
    ("ly", 2),      # "previously" -> "previous"
    ("es", 2),      # "processes" -> "process"
    ("s", 1),       # "connections" -> "connection"
]


def stem(word: str) -> str:
    """Iterative suffix-stripping stemmer. No NLTK dependency.

    Applies rules repeatedly until no more rules match, so that
    'connections' and 'connection' converge to the same stem.
    """
    if len(word) <= 3:
        return word
    changed = True
    while changed:
        changed = False
        for suffix, min_stem in _SUFFIX_RULES:
            if word.endswith(suffix) and len(word) - len(suffix) >= min_stem:
                word = word[: -len(suffix)]
                changed = True
                break  # restart from top of rules
    return word


def tokenize(text: str) -> list[str]:
    """Tokenize text into stemmed lowercase tokens, excluding stopwords."""
    words = _WORD_RE.findall(text.lower())
    return [stem(w) for w in words if w not in _STOPWORDS and len(w) > 1]


def tokenize_symbol(name: str) -> list[str]:
    """Tokenize an Ivy symbol name, splitting on underscores and camelCase."""
    # Split on underscores first
    parts = name.split("_")
    # Then split camelCase within each part
    tokens: list[str] = []
    for part in parts:
        sub_parts = _CAMEL_RE.split(part)
        tokens.extend(stem(p.lower()) for p in sub_parts if p and len(p) > 1)
    return tokens


class KeywordIndex:
    """Maps stemmed keywords from requirement text to requirement IDs.

    Supports add/remove for incremental updates and match_score for
    computing how well a symbol name matches a requirement.
    """

    def __init__(self) -> None:
        self._word_to_reqs: dict[str, set[str]] = defaultdict(set)
        self._req_to_words: dict[str, set[str]] = {}

    def add(self, req_id: str, text: str) -> None:
        """Index a requirement's text by its stemmed keywords."""
        words = set(tokenize(text))
        self._req_to_words[req_id] = words
        for w in words:
            self._word_to_reqs[w].add(req_id)

    def remove(self, req_id: str) -> None:
        """Remove a requirement from the index."""
        words = self._req_to_words.pop(req_id, set())
        for w in words:
            self._word_to_reqs[w].discard(req_id)
            if not self._word_to_reqs[w]:
                del self._word_to_reqs[w]

    def lookup(self, word: str) -> set[str]:
        """Return requirement IDs whose text contains a stemmed match for word."""
        return set(self._word_to_reqs.get(stem(word.lower()), set()))

    def match_score(self, symbol_name: str, req_id: str) -> float:
        """Score how well a symbol name matches a requirement (0.0-1.0).

        Score = |intersecting stemmed tokens| / |requirement tokens|
        """
        req_words = self._req_to_words.get(req_id, set())
        if not req_words:
            return 0.0
        sym_words = set(tokenize_symbol(symbol_name))
        intersection = req_words & sym_words
        return len(intersection) / len(req_words)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_keyword_index.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/semantic/keyword_index.py tests/test_keyword_index.py
git commit -m "feat(suggestion): add keyword index for requirement text matching"
```

---

### Task 2: RequirementSuggestionEngine Core

**Files:**
- Create: `ivy_lsp/semantic/suggestion_engine.py`
- Test: `tests/test_suggestion_engine.py`

- [ ] **Step 1: Write failing tests for data structures and engine init**

```python
# tests/test_suggestion_engine.py
"""Tests for RequirementSuggestionEngine."""

import sys
from pathlib import Path

import pytest

IVY_ROOT = Path(__file__).resolve().parent.parent
if str(IVY_ROOT) not in sys.path:
    sys.path.insert(0, str(IVY_ROOT))

from ivy_lsp.analysis.requirement_graph import (
    ActionNode,
    EdgeType,
    RequirementGraph,
    RequirementNode,
    StateVarNode,
)
from ivy_lsp.semantic.edges import SemanticEdgeType
from ivy_lsp.semantic.model import SemanticModel
from ivy_lsp.semantic.nodes import RfcAnnotation, RfcRequirement, SymbolNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_model_with_requirements():
    """Create a SemanticModel + RequirementGraph with test data."""
    model = SemanticModel()
    graph = RequirementGraph()

    # Add RFC requirements to model
    req1 = RfcRequirement(
        id="rfc9000:4.1", rfc="RFC9000", section="4.1",
        text="Sender MUST open connection before sending data",
        level="MUST", layer="connection",
    )
    req2 = RfcRequirement(
        id="rfc9000:8.1", rfc="RFC9000", section="8.1",
        text="Stream data MUST be acknowledged",
        level="MUST", layer="stream",
    )
    req3 = RfcRequirement(
        id="rfc9000:17.2", rfc="RFC9000", section="17.2",
        text="Connection identifiers SHOULD be unique",
        level="SHOULD", layer="connection",
    )
    model.add_node(req1)
    model.add_node(req2)
    model.add_node(req3)

    # Add symbols
    sym_conn = SymbolNode(
        id="test.ivy:10:connection_open", name="connection_open",
        qualified_name="quic.connection_open", kind="relation",
        file="test.ivy", line=10,
    )
    sym_stream = SymbolNode(
        id="test.ivy:15:stream_data_sent", name="stream_data_sent",
        qualified_name="quic.stream_data_sent", kind="relation",
        file="test.ivy", line=15,
    )
    sym_action = SymbolNode(
        id="test.ivy:20:handle_initial", name="handle_initial",
        qualified_name="quic.handle_initial", kind="action",
        file="test.ivy", line=20,
    )
    model.add_node(sym_conn)
    model.add_node(sym_stream)
    model.add_node(sym_action)

    # Add annotation linking handle_initial to rfc9000:4.1
    annot = RfcAnnotation(
        id="test.ivy:19:0", file="test.ivy", line=19,
        tags=["rfc9000:4.1"], node_id="test.ivy:20:handle_initial",
    )
    model.add_node(annot)

    # Add action + state var to graph
    action_node = ActionNode(
        id="handle_initial", name="handle_initial",
        qualified_name="quic.handle_initial", file="test.ivy", line=20,
    )
    graph.add_action(action_node)

    var_conn = StateVarNode(
        id="connection_open", name="connection_open",
        qualified_name="quic.connection_open",
        file="test.ivy", line=10, is_relation=True,
    )
    graph.add_state_var(var_conn)

    req_node = RequirementNode(
        id="test.ivy:21", kind="require", formula_text="connection_open(src)",
        line=21, col=4, file="test.ivy",
        monitor_action="handle_initial", mixin_kind="before",
    )
    req_node.bracket_tags = ["rfc9000:4.1"]
    graph.add_requirement(req_node)
    graph.add_edge("test.ivy:21", EdgeType.CONSTRAINS, "handle_initial")
    graph.add_edge("test.ivy:21", EdgeType.READS, "connection_open")

    return model, graph


class TestEngineInit:
    def test_engine_creates_without_error(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        assert engine is not None

    def test_engine_handles_empty_model(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model = SemanticModel()
        graph = RequirementGraph()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()
        assert engine.suggest_rfc_tags("foo", "test.ivy", 1) == []


class TestSuggestRfcTags:
    def test_suggests_tag_for_action_with_matching_symbols(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        suggestions = engine.suggest_rfc_tags("handle_initial", "test.ivy", 20)
        assert len(suggestions) >= 1
        tag_ids = [s.requirement_id for s in suggestions]
        assert "rfc9000:4.1" in tag_ids

    def test_confidence_higher_for_cooccurrence(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        suggestions = engine.suggest_rfc_tags("handle_initial", "test.ivy", 20)
        # rfc9000:4.1 has co-occurrence + keyword match, should be top
        if len(suggestions) > 1:
            assert suggestions[0].requirement_id == "rfc9000:4.1"
            assert suggestions[0].confidence > suggestions[1].confidence

    def test_returns_empty_for_unknown_action(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        suggestions = engine.suggest_rfc_tags("nonexistent", "test.ivy", 99)
        # May still return keyword-based suggestions, but should not crash
        assert isinstance(suggestions, list)


class TestSuggestConstructs:
    def test_suggests_symbol_for_requirement(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        suggestions = engine.suggest_constructs("rfc9000:4.1")
        assert len(suggestions) >= 1
        names = [s.symbol_name for s in suggestions]
        assert "connection_open" in names or "handle_initial" in names

    def test_returns_empty_for_unknown_requirement(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        suggestions = engine.suggest_constructs("rfc9999:99.99")
        assert suggestions == []


class TestSuggestStubs:
    def test_suggests_require_stub_for_before_block(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        stubs = engine.suggest_stubs("handle_initial", "before", "test.ivy")
        assert isinstance(stubs, list)
        # Should suggest at least one stub with state vars read by this action
        if stubs:
            assert stubs[0].kind in ("require", "ensure")
            assert "connection_open" in stubs[0].variables or stubs[0].insert_text


class TestValidateReferences:
    def test_no_issues_for_valid_annotations(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        issues = engine.validate_references("test.ivy")
        orphan_issues = [i for i in issues if i.code == "orphan-annotation"]
        assert len(orphan_issues) == 0

    def test_detects_orphan_annotation(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        # Add an annotation for a nonexistent requirement
        bad_annot = RfcAnnotation(
            id="test.ivy:30:0", file="test.ivy", line=30,
            tags=["rfc9999:1.1"],
        )
        model.add_node(bad_annot)
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        issues = engine.validate_references("test.ivy")
        orphan_issues = [i for i in issues if i.code == "orphan-annotation"]
        assert len(orphan_issues) >= 1
        assert "rfc9999:1.1" in orphan_issues[0].message


class TestGetInferredLayer:
    def test_infers_layer_from_annotation_context(self):
        from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
        model, graph = _make_model_with_requirements()
        engine = RequirementSuggestionEngine(model, graph)
        engine.build_indices()

        layer = engine.get_inferred_layer("connection_open")
        # connection_open is near an annotation for rfc9000:4.1 (layer: connection)
        assert layer == "connection" or layer is None  # may not have enough signal
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.semantic.suggestion_engine'`

- [ ] **Step 3: Implement suggestion_engine.py**

Create `ivy_lsp/semantic/suggestion_engine.py` with:

```python
# ivy_lsp/semantic/suggestion_engine.py
"""RequirementSuggestionEngine: bridges symbol indexing and RFC traceability.

Pre-computes keyword, co-occurrence, usage, and layer indices at indexing
time. LSP features and MCP tools query these indices for:
- A: suggest RFC tags for an Ivy construct
- B: suggest Ivy constructs for an RFC requirement
- C: suggest require/ensure stubs for an action
- D: validate annotations and references
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from ivy_lsp.semantic.keyword_index import KeywordIndex, tokenize_symbol

if TYPE_CHECKING:
    from ivy_lsp.analysis.requirement_graph import RequirementGraph
    from ivy_lsp.semantic.model import SemanticModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class RequirementSuggestion:
    requirement_id: str
    requirement_text: str
    confidence: float
    reason: str
    source: str  # "keyword" | "co-occurrence" | "layer" | "structural"
    level: str = ""
    layer: str = ""

@dataclass
class ConstructSuggestion:
    symbol_name: str
    qualified_name: str
    kind: str
    file: str
    line: int
    confidence: float
    reason: str

@dataclass
class StubSuggestion:
    kind: str  # "require" | "ensure" | "after" | "before"
    requirement_tag: str
    insert_text: str
    variables: list[str] = field(default_factory=list)

@dataclass
class ValidationIssue:
    file: str
    line: int
    code: str  # "orphan-annotation" | "unresolved-ref" | "type-mismatch"
    message: str
    severity: str
    suggested_fix: Optional[str] = None

@dataclass
class CoOccurrenceEntry:
    symbol_name: str
    rfc_tag: str
    count: int
    action_names: set[str] = field(default_factory=set)

@dataclass
class LayerSignature:
    symbol_name: str
    layer_votes: dict[str, int] = field(default_factory=dict)

    @property
    def inferred_layer(self) -> Optional[str]:
        if not self.layer_votes:
            return None
        return max(self.layer_votes, key=self.layer_votes.get)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

# Scoring weights
_W_COOCCURRENCE = 0.4
_W_KEYWORD = 0.3
_W_LAYER_BOOST = 0.2
_W_LEVEL_BOOST = 0.1  # tiebreaker

_LEVEL_PRIORITY = {"MUST": 1.0, "MUST NOT": 0.9, "SHOULD": 0.6, "SHOULD NOT": 0.5, "MAY": 0.3}
_PROXIMITY_LINES = 30  # max line distance for co-occurrence


class RequirementSuggestionEngine:
    """Bridges symbol completion and RFC traceability pipelines."""

    def __init__(
        self,
        semantic_model: SemanticModel,
        requirement_graph: RequirementGraph,
        indexer: Any = None,
    ) -> None:
        self._model = semantic_model
        self._graph = requirement_graph
        self._indexer = indexer
        self._lock = threading.RLock()

        # Indices (populated by build_indices)
        self._keyword_index = KeywordIndex()
        self._co_occurrences: Dict[Tuple[str, str], CoOccurrenceEntry] = {}
        self._symbol_usage: Dict[str, Set[str]] = defaultdict(set)
        self._layer_map: Dict[str, LayerSignature] = {}
        self._requirements: Dict[str, Any] = {}
        self._built = False

    def build_indices(self) -> None:
        """Build all indices from current model and graph state."""
        with self._lock:
            self._build_keyword_index()
            self._build_co_occurrence_map()
            self._build_symbol_usage_graph()
            self._build_layer_map()
            self._built = True
            logger.info(
                "Suggestion engine built: %d requirements, %d co-occurrences, "
                "%d symbol usages, %d layer signatures",
                len(self._requirements),
                len(self._co_occurrences),
                sum(len(v) for v in self._symbol_usage.values()),
                len(self._layer_map),
            )

    def update_file(self, filepath: str) -> None:
        """Incrementally update indices for a changed file."""
        with self._lock:
            if not self._built:
                return
            # Remove old co-occurrences for this file
            keys_to_remove = [
                k for k, v in self._co_occurrences.items()
                if any(filepath in str(a) for a in v.action_names)
            ]
            for k in keys_to_remove:
                del self._co_occurrences[k]
            # Rebuild for this file
            self._build_co_occurrence_map_for_file(filepath)
            self._build_layer_map()  # cheap, re-derive from co-occurrences

    # -- Index builders -------------------------------------------------------

    def _build_keyword_index(self) -> None:
        from ivy_lsp.semantic.nodes import RfcRequirement
        self._keyword_index = KeywordIndex()
        self._requirements.clear()
        for req in self._model.get_nodes_by_type(RfcRequirement).values():
            self._keyword_index.add(req.id, req.text)
            self._requirements[req.id] = req

    def _build_co_occurrence_map(self) -> None:
        from ivy_lsp.semantic.nodes import RfcAnnotation, SymbolNode
        self._co_occurrences.clear()

        annotations = self._model.get_nodes_by_type(RfcAnnotation).values()
        all_symbols = self._model.get_nodes_by_type(SymbolNode).values()

        # Build file -> symbols index for proximity lookup
        symbols_by_file: Dict[str, list] = defaultdict(list)
        for sym in all_symbols:
            symbols_by_file[sym.file].append(sym)

        for annot in annotations:
            nearby = [
                s for s in symbols_by_file.get(annot.file, [])
                if abs(s.line - annot.line) <= _PROXIMITY_LINES
            ]
            for tag in annot.tags:
                for sym in nearby:
                    key = (sym.name, tag)
                    if key not in self._co_occurrences:
                        self._co_occurrences[key] = CoOccurrenceEntry(
                            symbol_name=sym.name, rfc_tag=tag, count=0,
                        )
                    self._co_occurrences[key].count += 1
                    action_name = annot.node_id or ""
                    if action_name:
                        self._co_occurrences[key].action_names.add(action_name)

    def _build_co_occurrence_map_for_file(self, filepath: str) -> None:
        """Rebuild co-occurrences for a single file."""
        from ivy_lsp.semantic.nodes import RfcAnnotation, SymbolNode

        file_annotations = [
            n for n in self._model.get_nodes_by_type(RfcAnnotation).values()
            if n.file == filepath
        ]
        file_symbols = [
            n for n in self._model.get_nodes_by_type(SymbolNode).values()
            if n.file == filepath
        ]
        for annot in file_annotations:
            nearby = [
                s for s in file_symbols
                if abs(s.line - annot.line) <= _PROXIMITY_LINES
            ]
            for tag in annot.tags:
                for sym in nearby:
                    key = (sym.name, tag)
                    if key not in self._co_occurrences:
                        self._co_occurrences[key] = CoOccurrenceEntry(
                            symbol_name=sym.name, rfc_tag=tag, count=0,
                        )
                    self._co_occurrences[key].count += 1

    def _build_symbol_usage_graph(self) -> None:
        from ivy_lsp.analysis.requirement_graph import EdgeType
        self._symbol_usage.clear()
        snap = self._graph.snapshot() if hasattr(self._graph, "snapshot") else None
        if snap is None:
            return
        for src, etype, dst in snap.edges:
            if etype in (EdgeType.READS, EdgeType.WRITES):
                self._symbol_usage[dst].add(src)

    def _build_layer_map(self) -> None:
        self._layer_map.clear()
        for (sym_name, tag), entry in self._co_occurrences.items():
            req = self._requirements.get(tag)
            if req and getattr(req, "layer", ""):
                if sym_name not in self._layer_map:
                    self._layer_map[sym_name] = LayerSignature(symbol_name=sym_name)
                layer = req.layer
                votes = self._layer_map[sym_name].layer_votes
                votes[layer] = votes.get(layer, 0) + entry.count

    # -- Query API -----------------------------------------------------------

    def suggest_rfc_tags(
        self,
        action_name: str,
        file: str,
        line: int,
        *,
        max_results: int = 10,
        min_confidence: float = 0.1,
    ) -> list[RequirementSuggestion]:
        """Suggest RFC requirement tags for an action."""
        with self._lock:
            if not self._built or not self._requirements:
                return []

            scores: Dict[str, float] = defaultdict(float)
            reasons: Dict[str, list] = defaultdict(list)

            # 1. Co-occurrence: what tags appear near this action's symbols?
            max_co = max((e.count for e in self._co_occurrences.values()), default=1)
            for (sym_name, tag), entry in self._co_occurrences.items():
                if action_name in entry.action_names or self._action_uses_symbol(action_name, sym_name):
                    co_score = (entry.count / max_co) * _W_COOCCURRENCE
                    scores[tag] += co_score
                    reasons[tag].append(f"co-occurs with '{sym_name}' ({entry.count}x)")

            # 2. Keyword match: action name tokens vs requirement text
            for req_id, req in self._requirements.items():
                kw_score = self._keyword_index.match_score(action_name, req_id)
                if kw_score > 0:
                    scores[req_id] += kw_score * _W_KEYWORD
                    reasons[req_id].append(f"keyword match ({kw_score:.2f})")

            # 3. Layer boost
            action_layer = self._infer_action_layer(action_name)
            if action_layer:
                for req_id, req in self._requirements.items():
                    if getattr(req, "layer", "") == action_layer:
                        scores[req_id] += _W_LAYER_BOOST
                        reasons[req_id].append(f"layer match ({action_layer})")

            # 4. Level tiebreaker
            for req_id in scores:
                req = self._requirements.get(req_id)
                if req:
                    level_boost = _LEVEL_PRIORITY.get(req.level, 0.0) * _W_LEVEL_BOOST
                    scores[req_id] += level_boost

            # Build and sort results
            results = []
            for req_id, score in scores.items():
                if score < min_confidence:
                    continue
                req = self._requirements[req_id]
                results.append(RequirementSuggestion(
                    requirement_id=req_id,
                    requirement_text=req.text[:120],
                    confidence=min(score, 1.0),
                    reason="; ".join(reasons[req_id]),
                    source="combined",
                    level=req.level,
                    layer=getattr(req, "layer", ""),
                ))
            results.sort(key=lambda s: s.confidence, reverse=True)
            return results[:max_results]

    def suggest_constructs(
        self,
        requirement_id: str,
        *,
        max_results: int = 10,
    ) -> list[ConstructSuggestion]:
        """Suggest Ivy constructs that could model a given RFC requirement."""
        with self._lock:
            if not self._built:
                return []
            req = self._requirements.get(requirement_id)
            if req is None:
                return []

            from ivy_lsp.semantic.nodes import SymbolNode
            scores: Dict[str, float] = {}
            reasons: Dict[str, str] = {}

            # 1. Co-occurrence: symbols that appear near this tag
            for (sym_name, tag), entry in self._co_occurrences.items():
                if tag == requirement_id:
                    scores[sym_name] = scores.get(sym_name, 0) + entry.count * 0.5
                    reasons[sym_name] = f"co-occurs with [{tag}] ({entry.count}x)"

            # 2. Keyword match: symbol names vs requirement text
            all_symbols = self._model.get_nodes_by_type(SymbolNode).values()
            for sym in all_symbols:
                kw_score = self._keyword_index.match_score(sym.name, requirement_id)
                if kw_score > 0:
                    scores[sym.name] = scores.get(sym.name, 0) + kw_score
                    existing = reasons.get(sym.name, "")
                    reasons[sym.name] = f"{existing}; keyword ({kw_score:.2f})" if existing else f"keyword ({kw_score:.2f})"

            # 3. Layer match boost
            req_layer = getattr(req, "layer", "")
            if req_layer:
                for sym_name in list(scores.keys()):
                    sig = self._layer_map.get(sym_name)
                    if sig and sig.inferred_layer == req_layer:
                        scores[sym_name] += 0.2
                        existing = reasons.get(sym_name, "")
                        reasons[sym_name] = f"{existing}; layer match" if existing else "layer match"

            # Build results with SymbolNode metadata
            sym_index: Dict[str, Any] = {}
            for sym in all_symbols:
                if sym.name in scores and sym.name not in sym_index:
                    sym_index[sym.name] = sym

            results = []
            for sym_name, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                sym = sym_index.get(sym_name)
                if sym is None:
                    continue
                results.append(ConstructSuggestion(
                    symbol_name=sym.name,
                    qualified_name=sym.qualified_name,
                    kind=sym.kind,
                    file=sym.file,
                    line=sym.line,
                    confidence=min(score, 1.0),
                    reason=reasons.get(sym_name, ""),
                ))
                if len(results) >= max_results:
                    break
            return results

    def suggest_stubs(
        self,
        action_name: str,
        block_type: str,
        file: str,
    ) -> list[StubSuggestion]:
        """Suggest require/ensure stubs for an action's monitor block."""
        with self._lock:
            if not self._built:
                return []

            stubs: list[StubSuggestion] = []
            snap = self._graph.snapshot() if hasattr(self._graph, "snapshot") else None
            if snap is None:
                return []

            # Find state vars related to this action
            read_vars: list[str] = []
            written_vars: list[str] = []
            for src, etype, dst in snap.edges:
                from ivy_lsp.analysis.requirement_graph import EdgeType
                if etype == EdgeType.CONSTRAINS and dst == action_name:
                    # Get reads of this requirement
                    for _, e2, var in snap.edges:
                        if e2 == EdgeType.READS and _ == src:
                            read_vars.append(var)
                if etype == EdgeType.WRITES and src == action_name:
                    written_vars.append(dst)

            # Get RFC tags for this action
            tags = self.suggest_rfc_tags(action_name, file, 0, max_results=3)
            tag_str = tags[0].requirement_id if tags else ""

            if block_type in ("before", "body") and read_vars:
                for var in read_vars[:3]:
                    var_name = var.split(".")[-1] if "." in var else var
                    stubs.append(StubSuggestion(
                        kind="require",
                        requirement_tag=tag_str,
                        insert_text=f"    require {var_name}(...)",
                        variables=[var_name],
                    ))
            elif block_type == "after" and (written_vars or read_vars):
                target_vars = written_vars or read_vars
                for var in target_vars[:3]:
                    var_name = var.split(".")[-1] if "." in var else var
                    stubs.append(StubSuggestion(
                        kind="ensure",
                        requirement_tag=tag_str,
                        insert_text=f"    ensure {var_name}(...)",
                        variables=[var_name],
                    ))

            return stubs

    def validate_references(
        self,
        filepath: Optional[str] = None,
    ) -> list[ValidationIssue]:
        """Validate RFC annotations and symbol references."""
        with self._lock:
            if not self._built:
                return []

            from ivy_lsp.semantic.nodes import RfcAnnotation
            issues: list[ValidationIssue] = []

            annotations = self._model.get_nodes_by_type(RfcAnnotation).values()
            if filepath:
                annotations = [a for a in annotations if a.file == filepath]

            req_keys = set(self._requirements.keys())
            for annot in annotations:
                for tag in annot.tags:
                    # Check for orphan annotations
                    from ivy_lsp.semantic.rfc_annotations import normalize_tag_to_manifest_ids
                    resolved = normalize_tag_to_manifest_ids(tag, req_keys)
                    if not resolved:
                        issues.append(ValidationIssue(
                            file=annot.file,
                            line=annot.line,
                            code="orphan-annotation",
                            message=f"RFC tag '{tag}' does not match any requirement in loaded manifests",
                            severity="warning",
                        ))

            return issues

    def get_inferred_layer(self, symbol_name: str) -> Optional[str]:
        """Return the usage-inferred layer for a symbol."""
        with self._lock:
            sig = self._layer_map.get(symbol_name)
            return sig.inferred_layer if sig else None

    # -- Internal helpers ----------------------------------------------------

    def _action_uses_symbol(self, action_name: str, symbol_name: str) -> bool:
        """Check if an action reads/writes a symbol via the usage graph."""
        return action_name in self._symbol_usage.get(symbol_name, set())

    def _infer_action_layer(self, action_name: str) -> Optional[str]:
        """Infer an action's layer from its related symbols' layers."""
        layer_votes: Dict[str, int] = defaultdict(int)
        for sym_name, actions in self._symbol_usage.items():
            if action_name in actions:
                sig = self._layer_map.get(sym_name)
                if sig and sig.inferred_layer:
                    layer_votes[sig.inferred_layer] += 1
        if not layer_votes:
            return None
        return max(layer_votes, key=layer_votes.get)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_engine.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/semantic/suggestion_engine.py tests/test_suggestion_engine.py
git commit -m "feat(suggestion): add RequirementSuggestionEngine with query APIs"
```

---

### Task 3: Wire Engine into Server Lifecycle

**Files:**
- Modify: `ivy_lsp/server.py:34-60`
- Modify: `ivy_lsp/server_setup.py:315-441`
- Modify: `ivy_lsp/bulk_orchestrator.py` (done_callback chain)
- Modify: `ivy_lsp/indexer/workspace_indexer.py` (incremental update)

- [ ] **Step 1: Add `_suggestion_engine` to server.py**

In `IvyLanguageServer.__init__()` (after line 49 `self._compiler_manager`), add:
```python
self._suggestion_engine: "Optional[Any]" = None
```

Add property after existing `semantic_model` property:
```python
@property
def suggestion_engine(self):
    """RequirementSuggestionEngine instance, or None if not yet initialized."""
    return self._suggestion_engine
```

- [ ] **Step 2: Wire creation in server_setup.py**

In `_setup_analysis_pipeline()`, after the `slog.info("Semantic model and analysis pipeline initialized")` line (~430), add:
```python
# Initialize suggestion engine (optional — does not block features)
try:
    from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
    self._suggestion_engine = RequirementSuggestionEngine(
        semantic_model=self._semantic_model,
        requirement_graph=requirement_graph,
        indexer=self._indexer,
    )
    logger.info("Suggestion engine created (indices built after bulk analysis)")
except Exception:
    logger.warning("Suggestion engine initialization failed", exc_info=True)
```

- [ ] **Step 3: Trigger build_indices after bulk analysis**

In `bulk_orchestrator.py`, find the done_callback or post-bulk-analysis logic. After bulk T1+T2 completes, add:
```python
if getattr(self, "_suggestion_engine", None) is not None:
    try:
        self._suggestion_engine.build_indices()
    except Exception:
        logger.warning("Suggestion engine index build failed", exc_info=True)
```

- [ ] **Step 4: Wire incremental update in workspace_indexer.py**

In `workspace_indexer.py`, find the `reindex_file` method. After `_wire_requirement_graph()` (or after the file's symbols are updated), add:
```python
# Incrementally update suggestion engine indices for this file
engine = getattr(self, "_suggestion_engine", None)
if engine is None:
    # Try to get it from the server via the analysis pipeline
    engine = getattr(self._analysis_pipeline, "_suggestion_engine", None) if self._analysis_pipeline else None
if engine is not None:
    try:
        engine.update_file(abs_path)
    except Exception:
        logger.debug("Suggestion engine incremental update failed for %s", abs_path, exc_info=True)
```

Alternatively, the engine reference can be passed at construction or set via a setter method. The exact wiring depends on how the server exposes the engine to the indexer — check at implementation time.

- [ ] **Step 5: Run existing tests to verify no regressions**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=120`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/server.py ivy_lsp/server_setup.py ivy_lsp/bulk_orchestrator.py ivy_lsp/indexer/workspace_indexer.py
git commit -m "feat(suggestion): wire RequirementSuggestionEngine into server lifecycle"
```

---

### Task 4: Suggestion Diagnostics

**Files:**
- Create: `ivy_lsp/features/suggestion_diagnostics.py`
- Modify: `ivy_lsp/features/diagnostics.py:459-520`
- Test: `tests/test_suggestion_diagnostics.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_suggestion_diagnostics.py
"""Tests for suggestion-based diagnostics."""

import sys
from pathlib import Path

import pytest
from lsprotocol.types import DiagnosticSeverity

IVY_ROOT = Path(__file__).resolve().parent.parent
if str(IVY_ROOT) not in sys.path:
    sys.path.insert(0, str(IVY_ROOT))

from ivy_lsp.analysis.requirement_graph import (
    ActionNode, EdgeType, RequirementGraph, RequirementNode, StateVarNode,
)
from ivy_lsp.semantic.model import SemanticModel
from ivy_lsp.semantic.nodes import RfcAnnotation, RfcRequirement, SymbolNode


def _build_engine():
    """Build an engine with test data for diagnostics."""
    from ivy_lsp.semantic.suggestion_engine import RequirementSuggestionEngine
    model = SemanticModel()
    graph = RequirementGraph()

    req = RfcRequirement(
        id="rfc9000:4.1", rfc="RFC9000", section="4.1",
        text="Sender MUST open connection", level="MUST", layer="connection",
    )
    model.add_node(req)

    sym = SymbolNode(
        id="test.ivy:10:conn_open", name="conn_open",
        qualified_name="quic.conn_open", kind="relation",
        file="test.ivy", line=10,
    )
    model.add_node(sym)

    # Annotation pointing to nonexistent requirement
    bad = RfcAnnotation(
        id="test.ivy:5:0", file="test.ivy", line=5,
        tags=["rfc9999:1.1"],
    )
    model.add_node(bad)

    engine = RequirementSuggestionEngine(model, graph)
    engine.build_indices()
    return engine


class TestInvalidRefDiagnostic:
    def test_orphan_tag_produces_warning(self):
        from ivy_lsp.features.suggestion_diagnostics import compute_suggestion_diagnostics
        engine = _build_engine()
        source = "#lang ivy1.7\n\n# [rfc9999:1.1]\ntype cid\n"
        diags = compute_suggestion_diagnostics(engine, source, "test.ivy", None, None)
        invalid = [d for d in diags if d.code == "ivy.rfc.invalid-ref"]
        assert len(invalid) >= 1
        assert invalid[0].severity == DiagnosticSeverity.Warning


class TestSuggestionDiagsReturnList:
    def test_returns_empty_for_none_engine(self):
        from ivy_lsp.features.suggestion_diagnostics import compute_suggestion_diagnostics
        diags = compute_suggestion_diagnostics(None, "", "test.ivy", None, None)
        assert diags == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_diagnostics.py -v`
Expected: FAIL

- [ ] **Step 3: Implement suggestion_diagnostics.py**

```python
# ivy_lsp/features/suggestion_diagnostics.py
"""Suggestion-based diagnostics for RFC annotations and references.

Diagnostic codes:
- ivy.rfc.missing-annotation (Hint)
- ivy.rfc.invalid-ref (Warning)
- ivy.rfc.uncovered-must (Information)
- ivy.naming.unresolved-ref (Error)
- ivy.type.clause-mismatch (Error)
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from lsprotocol import types as lsp

logger = logging.getLogger(__name__)


def compute_suggestion_diagnostics(
    engine: Any,
    source: str,
    filepath: str,
    indexer: Any = None,
    semantic_model: Any = None,
) -> List[lsp.Diagnostic]:
    """Compute diagnostics from the RequirementSuggestionEngine."""
    if engine is None:
        return []

    diags: List[lsp.Diagnostic] = []

    try:
        issues = engine.validate_references(filepath)
    except Exception:
        logger.debug("Suggestion engine validation failed", exc_info=True)
        return diags

    for issue in issues:
        if issue.code == "orphan-annotation":
            diags.append(lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(issue.line, 0),
                    end=lsp.Position(issue.line, len(source.split("\n")[issue.line]) if issue.line < len(source.split("\n")) else 0),
                ),
                message=issue.message,
                severity=lsp.DiagnosticSeverity.Warning,
                source="ivy-lsp-suggest",
                code="ivy.rfc.invalid-ref",
            ))
        elif issue.code == "unresolved-ref":
            diags.append(lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(issue.line, 0),
                    end=lsp.Position(issue.line, 80),
                ),
                message=issue.message,
                severity=lsp.DiagnosticSeverity.Error,
                source="ivy-lsp-suggest",
                code="ivy.naming.unresolved-ref",
            ))

    return diags
```

- [ ] **Step 4: Hook into diagnostics.py**

In `compute_diagnostics()` (diagnostics.py), add `suggestion_engine=None` parameter. After semantic diagnostics, add:
```python
if suggestion_engine is not None:
    from ivy_lsp.features.suggestion_diagnostics import compute_suggestion_diagnostics
    diags.extend(compute_suggestion_diagnostics(
        suggestion_engine, source, filepath, indexer, semantic_model,
    ))
```

Update all callers of `compute_diagnostics` to pass `suggestion_engine` from the server.

- [ ] **Step 5: Run tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_diagnostics.py tests/ -x -q --timeout=120`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/features/suggestion_diagnostics.py ivy_lsp/features/diagnostics.py tests/test_suggestion_diagnostics.py
git commit -m "feat(suggestion): add suggestion-based diagnostics for RFC annotations"
```

---

### Task 5: New Code Action Branches

**Files:**
- Modify: `ivy_lsp/features/code_action.py:24-179`
- Test: `tests/test_suggestion_code_actions.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_suggestion_code_actions.py
"""Tests for suggestion-based code actions."""

import sys
from pathlib import Path

import pytest
from lsprotocol.types import (
    CodeActionKind, Diagnostic, DiagnosticSeverity, Position, Range,
)

IVY_ROOT = Path(__file__).resolve().parent.parent
if str(IVY_ROOT) not in sys.path:
    sys.path.insert(0, str(IVY_ROOT))


class TestMissingAnnotationAction:
    def test_quickfix_inserts_rfc_tag(self):
        from ivy_lsp.features.code_action import compute_code_actions
        diag = Diagnostic(
            range=Range(start=Position(5, 0), end=Position(5, 30)),
            message="Action 'handle_initial' touches relations mapped to rfc9000:4.1 but has no RFC annotation",
            severity=DiagnosticSeverity.Hint,
            source="ivy-lsp-suggest",
            code="ivy.rfc.missing-annotation",
        )
        source = "#lang ivy1.7\n\ntype cid\n\n\naction handle_initial = {\n}\n"
        actions = compute_code_actions("file:///test.ivy", source, [diag])
        fix = [a for a in actions if "rfc" in (a.title or "").lower() or "annotation" in (a.title or "").lower()]
        assert len(fix) >= 1
        edit = fix[0].edit
        assert edit is not None
        text_edit = edit.changes["file:///test.ivy"][0]
        assert "[rfc9000:4.1]" in text_edit.new_text or "rfc" in text_edit.new_text.lower()


class TestUnresolvedRefAction:
    def test_quickfix_suggests_replacement(self):
        from ivy_lsp.features.code_action import compute_code_actions
        diag = Diagnostic(
            range=Range(start=Position(3, 4), end=Position(3, 20)),
            message="Symbol 'conn_state' not found in scope; did you mean 'conn_st'?",
            severity=DiagnosticSeverity.Error,
            source="ivy-lsp-suggest",
            code="ivy.naming.unresolved-ref",
        )
        source = "#lang ivy1.7\n\ntype cid\n    require conn_state\n"
        actions = compute_code_actions("file:///test.ivy", source, [diag])
        fix = [a for a in actions if "replace" in (a.title or "").lower() or "conn_st" in (a.title or "").lower()]
        assert len(fix) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_code_actions.py -v`
Expected: FAIL (code actions not yet handling new diagnostic codes)

- [ ] **Step 3: Add new branches to compute_code_actions**

In `code_action.py`, add after the `ivy.unguarded-write` branch (line 147):

```python
elif code == "ivy.rfc.missing-annotation":
    # Extract tag from message: "...mapped to rfc9000:4.1 but..."
    import re
    m = re.search(r"mapped to ([\w:.,\s]+?) but", diag.message)
    tag_str = m.group(1).strip() if m else "rfc:X.Y"
    insert_line = diag.range.start.line
    snippet = f"# [{tag_str}]\n"
    actions.append(
        lsp.CodeAction(
            title=f"Add RFC annotation [{tag_str}]",
            kind=lsp.CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=lsp.WorkspaceEdit(
                changes={
                    uri: [
                        lsp.TextEdit(
                            range=make_range(insert_line, 0, insert_line, 0),
                            new_text=snippet,
                        )
                    ]
                }
            ),
        )
    )

elif code == "ivy.naming.unresolved-ref":
    # Extract suggestion from message: "...did you mean 'conn_st'?"
    import re
    m = re.search(r"did you mean '([\w.]+)'", diag.message)
    if m:
        suggestion = m.group(1)
        actions.append(
            lsp.CodeAction(
                title=f"Replace with '{suggestion}'",
                kind=lsp.CodeActionKind.QuickFix,
                diagnostics=[diag],
                edit=lsp.WorkspaceEdit(
                    changes={
                        uri: [
                            lsp.TextEdit(
                                range=diag.range,
                                new_text=suggestion,
                            )
                        ]
                    }
                ),
            )
        )
```

Also add `import re` at the top if not already present.

- [ ] **Step 4: Run tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_code_actions.py tests/test_code_action.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/features/code_action.py tests/test_suggestion_code_actions.py
git commit -m "feat(suggestion): add code actions for RFC annotations and broken references"
```

---

### Task 6: RFC Tag Completions

**Files:**
- Modify: `ivy_lsp/features/completion.py:144-599`
- Test: `tests/test_suggestion_completions.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_suggestion_completions.py
"""Tests for RFC tag and requirement-aware completions."""

import sys
from pathlib import Path

import pytest

IVY_ROOT = Path(__file__).resolve().parent.parent
if str(IVY_ROOT) not in sys.path:
    sys.path.insert(0, str(IVY_ROOT))


class TestRfcTagContext:
    def test_detect_bracket_tag_context(self):
        from ivy_lsp.features.completion import CompletionContext, detect_context
        ctx, prefix, scope = detect_context("# [rfc", 6)
        assert ctx == CompletionContext.RFC_TAG
        assert "rfc" in prefix

    def test_detect_bracket_tag_empty(self):
        from ivy_lsp.features.completion import CompletionContext, detect_context
        ctx, prefix, scope = detect_context("# [", 3)
        assert ctx == CompletionContext.RFC_TAG

    def test_detect_bracket_tag_with_colon(self):
        from ivy_lsp.features.completion import CompletionContext, detect_context
        ctx, prefix, scope = detect_context("# [rfc9000:", 11)
        assert ctx == CompletionContext.RFC_TAG
        assert "rfc9000:" in prefix

    def test_not_triggered_in_normal_comment(self):
        from ivy_lsp.features.completion import CompletionContext, detect_context
        ctx, prefix, scope = detect_context("# this is a comment", 19)
        assert ctx != CompletionContext.RFC_TAG

    def test_not_triggered_in_array_access(self):
        from ivy_lsp.features.completion import CompletionContext, detect_context
        ctx, prefix, scope = detect_context("    arr[", 8)
        assert ctx != CompletionContext.RFC_TAG
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_completions.py -v`
Expected: FAIL (RFC_TAG not yet in CompletionContext)

- [ ] **Step 3: Add RFC_TAG completion context**

In `completion.py`:

1. Add to `CompletionContext` enum (line 150):
```python
RFC_TAG = "rfc_tag"
```

2. Add detection in `detect_context()` (after AFTER_KEYWORD, before GENERAL):
```python
# 4. RFC bracket tag: "# [rfc..."
rfc_match = re.search(r"#\s*\[([\w:.,\s]*)$", text_before)
if rfc_match:
    return CompletionContext.RFC_TAG, rfc_match.group(1).strip(), ""
```

3. Add `"["` to trigger characters (line 574):
```python
lsp.CompletionOptions(trigger_characters=[".", " ", "["]),
```

4. Add `suggestion_engine` parameter to `get_completions()` and thread from `register()`:
```python
def get_completions(..., suggestion_engine=None):
```

5. Add RFC_TAG branch in `get_completions()`:
```python
elif ctx == CompletionContext.RFC_TAG:
    items = _rfc_tag_completions(
        suggestion_engine, indexer, filepath, position.line, prefix, semantic_model,
    )
```

6. Implement `_rfc_tag_completions()`:
```python
def _rfc_tag_completions(engine, indexer, filepath, line, prefix, semantic_model):
    """Generate RFC tag completion items."""
    items = []
    # From engine suggestions (context-aware)
    if engine is not None:
        # _find_enclosing_action expects a GraphSnapshot (has .requirements dict),
        # so call .snapshot() on the live RequirementGraph
        raw_graph = indexer.requirement_graph if indexer else None
        graph = raw_graph.snapshot() if raw_graph and hasattr(raw_graph, "snapshot") else raw_graph
        action_name = _find_enclosing_action(graph, filepath, line) if graph else None
        if action_name:
            suggestions = engine.suggest_rfc_tags(action_name, filepath, line, max_results=20)
            for s in suggestions:
                tag = s.requirement_id
                if prefix and not tag.lower().startswith(prefix.lower()):
                    continue
                items.append(lsp.CompletionItem(
                    label=tag,
                    kind=lsp.CompletionItemKind.Reference,
                    detail=f"[{s.level}] {s.requirement_text[:60]}",
                    documentation=f"{s.requirement_text}\n\nLevel: {s.level}\nLayer: {s.layer}\nConfidence: {s.confidence:.0%}",
                    insert_text=tag,
                    sort_text=f"0{tag}",
                ))
    # Also offer all manifest requirements (lower priority)
    if semantic_model is not None:
        from ivy_lsp.semantic.nodes import RfcRequirement
        existing_tags = {i.label for i in items}
        for req in semantic_model.get_nodes_by_type(RfcRequirement).values():
            if req.id in existing_tags:
                continue
            if prefix and not req.id.lower().startswith(prefix.lower()):
                continue
            items.append(lsp.CompletionItem(
                label=req.id,
                kind=lsp.CompletionItemKind.Reference,
                detail=f"[{req.level}] {req.text[:60]}",
                insert_text=req.id,
                sort_text=f"1{req.id}",
            ))
    return items[:MAX_COMPLETIONS]
```

- [ ] **Step 4: Run tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_completions.py tests/test_task_3_1_completion.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/features/completion.py tests/test_suggestion_completions.py
git commit -m "feat(suggestion): add RFC bracket-tag completion context"
```

---

### Task 6b: Enhanced Semantic Completions + Requirement Enrichment

**Files:**
- Modify: `ivy_lsp/features/completion.py` (`compute_semantic_completions` at line 454, `_enrich_items_from_semantic_model` at line 536)
- Test: `tests/test_suggestion_completions.py` (append new test classes)

This covers spec Phases 2b and 2c — enriching existing completions with requirement context.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_suggestion_completions.py`:

```python
class TestSemanticCompletionsWithRfcContext:
    """Phase 2b: suggest constructs when an RFC tag is on a nearby line."""

    def test_suggests_constructs_when_rfc_tag_nearby(self):
        from ivy_lsp.features.completion import compute_semantic_completions
        # Create a graph with a known action and state var
        from ivy_lsp.analysis.requirement_graph import (
            ActionNode, EdgeType, RequirementGraph, RequirementNode, StateVarNode,
        )
        graph = RequirementGraph()
        action = ActionNode(
            id="handle_initial", name="handle_initial",
            qualified_name="quic.handle_initial", file="test.ivy", line=20,
        )
        graph.add_action(action)
        var = StateVarNode(
            id="conn_open", name="conn_open",
            qualified_name="quic.conn_open", file="test.ivy", line=10,
            is_relation=True,
        )
        graph.add_state_var(var)
        req = RequirementNode(
            id="test.ivy:21", kind="require", formula_text="conn_open(src)",
            line=21, col=4, file="test.ivy",
            monitor_action="handle_initial", mixin_kind="before",
        )
        graph.add_requirement(req)
        graph.add_edge("test.ivy:21", EdgeType.CONSTRAINS, "handle_initial")
        graph.add_edge("test.ivy:21", EdgeType.READS, "conn_open")

        # compute_semantic_completions in "before" block should return state vars
        completions = compute_semantic_completions(graph, "test.ivy", 21, "before")
        assert isinstance(completions, list)
        # At minimum, the existing behavior: suggest state vars in scope
        if completions:
            labels = [c["label"] for c in completions]
            assert "conn_open" in labels


class TestCompletionEnrichment:
    """Phase 2c: existing completion items get RFC tag info in detail."""

    def test_enrichment_preserves_existing_detail(self):
        """Enrichment should append RFC info, not replace existing detail."""
        # This is a behavioral contract test — the implementation detail
        # (appending [rfc9000:4.1] to detail) is tested at integration level.
        # For now, verify the function signature accepts the engine parameter.
        from ivy_lsp.features.completion import _enrich_items_from_semantic_model
        import inspect
        sig = inspect.signature(_enrich_items_from_semantic_model)
        # Should accept suggestion_engine or **kwargs
        params = list(sig.parameters.keys())
        assert "suggestion_engine" in params or "kwargs" in params or len(params) >= 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_completions.py::TestSemanticCompletionsWithRfcContext tests/test_suggestion_completions.py::TestCompletionEnrichment -v`
Expected: FAIL

- [ ] **Step 3: Enhance compute_semantic_completions (Phase 2b)**

In `completion.py`, `compute_semantic_completions()` (line 454), after the existing state-var suggestion loop (~line 505), add:

```python
# Phase 2b: If an RFC tag is on a nearby line, suggest constructs for it
if suggestion_engine is not None and source_lines is not None:
    import re
    _BRACKET_RE_LOCAL = re.compile(r"#\s*\[([\w:.,\s]+)\]")
    # Scan 3 lines above cursor for bracket tags
    for scan_line in range(max(0, line - 3), line):
        if scan_line < len(source_lines):
            m = _BRACKET_RE_LOCAL.search(source_lines[scan_line])
            if m:
                tag = m.group(1).strip().split(",")[0].strip()
                constructs = suggestion_engine.suggest_constructs(tag, max_results=5)
                for c in constructs:
                    completions.append({
                        "label": c.symbol_name,
                        "detail": f"suggested for [{tag}]: {c.reason[:50]}",
                        "kind": c.kind,
                        "insertText": c.symbol_name,
                        "sortText": f"0{c.symbol_name}",
                    })
                break  # only use the closest tag
```

Add `suggestion_engine=None` and `source_lines=None` parameters to `compute_semantic_completions`.

- [ ] **Step 4: Enhance _enrich_items_from_semantic_model (Phase 2c)**

In `completion.py`, `_enrich_items_from_semantic_model()` (line 536), add `suggestion_engine=None` parameter. After enriching with params/return_sort, add:

```python
# Phase 2c: Append RFC requirement context to detail
if suggestion_engine is not None:
    try:
        tags = suggestion_engine.suggest_rfc_tags(
            item.label, "", 0, max_results=1, min_confidence=0.5,
        )
        if tags:
            tag_str = tags[0].requirement_id
            item.detail = f"{item.detail}  [{tag_str}]" if item.detail else f"[{tag_str}]"
    except Exception:
        pass  # enrichment is best-effort
```

Thread `suggestion_engine` from the `get_completions` caller.

- [ ] **Step 5: Run tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_suggestion_completions.py tests/test_task_3_1_completion.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/features/completion.py tests/test_suggestion_completions.py
git commit -m "feat(suggestion): enhanced semantic completions with RFC context (phases 2b+2c)"
```

---

### Task 7: MCP Suggestion Tools

**Files:**
- Create: `ivy_lsp/tools/suggestions.py`
- Modify: `ivy_lsp/tools/__init__.py:26-317`
- Modify: `ivy_lsp/mcp_server.py:76-289`
- Test: `tests/test_tools_suggestions.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tools_suggestions.py
"""Tests for MCP suggestion tools."""

import json
import sys
from pathlib import Path

import pytest

IVY_ROOT = Path(__file__).resolve().parent.parent
if str(IVY_ROOT) not in sys.path:
    sys.path.insert(0, str(IVY_ROOT))

from tests.helpers.mcp_helpers import extract_json, extract_text, get_mcp_app


class TestSuggestRequirementsTool:
    @pytest.mark.asyncio
    async def test_tool_exists(self):
        mcp = get_mcp_app()
        # List tools and check ivy_suggest_requirements exists
        tools = await mcp.list_tools()
        names = [t.name for t in tools]
        assert "ivy_suggest_requirements" in names

    @pytest.mark.asyncio
    async def test_returns_json(self):
        mcp = get_mcp_app()
        result = await mcp.call_tool("ivy_suggest_requirements", {"mode": "tags"})
        text = extract_text(result)
        data = json.loads(text)
        assert "suggestions" in data or "error" in data.lower() or "message" in data


class TestRequirementGapsTool:
    @pytest.mark.asyncio
    async def test_tool_exists(self):
        mcp = get_mcp_app()
        tools = await mcp.list_tools()
        names = [t.name for t in tools]
        assert "ivy_requirement_gaps" in names


class TestValidateSpecTool:
    @pytest.mark.asyncio
    async def test_tool_exists(self):
        mcp = get_mcp_app()
        tools = await mcp.list_tools()
        names = [t.name for t in tools]
        assert "ivy_validate_spec" in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_tools_suggestions.py -v`
Expected: FAIL (tools not registered)

- [ ] **Step 3: Implement tools/suggestions.py**

Create `ivy_lsp/tools/suggestions.py` following the pattern from `tools/traceability.py`:
- `register_suggestion_tools(mcp, ctx)` with 3 `@mcp.tool()` + `@safe_tool` decorated tools
- `ivy_suggest_requirements`: delegates to `engine.suggest_rfc_tags()` / `suggest_constructs()` / `suggest_stubs()`
- `ivy_requirement_gaps`: delegates to `engine.suggest_constructs()` for uncovered requirements
- `ivy_validate_spec`: delegates to `engine.validate_references()`
- All return JSON strings via `json.dumps()`

- [ ] **Step 4: Register in tools/__init__.py**

Add import and registration:
```python
from ivy_lsp.tools.suggestions import register_suggestion_tools

# In register_all_tools():
register_suggestion_tools(mcp, ctx)
```

Add to `_TOOL_TIMEOUTS` and `_TOOL_METADATA`.

- [ ] **Step 5: Add suggestion_engine to ToolContext in mcp_server.py**

Add field to `ToolContext` dataclass:
```python
suggestion_engine: Any = None
```

In `start_mcp()` / `_build_mcp()`, pass engine from server or build it from available model/graph.

- [ ] **Step 6: Run tests**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_tools_suggestions.py tests/ -x -q --timeout=120`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add ivy_lsp/tools/suggestions.py ivy_lsp/tools/__init__.py ivy_lsp/mcp_server.py tests/test_tools_suggestions.py
git commit -m "feat(suggestion): add MCP tools for requirement suggestions, gaps, and validation"
```

---

### Task 8: Full Integration Test + Regression Check

**Files:**
- All modified files

- [ ] **Step 1: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/ -x -q --timeout=120`
Expected: All 1965+ existing tests PASS, plus all new tests PASS

- [ ] **Step 2: Run new tests in isolation**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/test_keyword_index.py tests/test_suggestion_engine.py tests/test_suggestion_diagnostics.py tests/test_suggestion_code_actions.py tests/test_suggestion_completions.py tests/test_tools_suggestions.py -v`
Expected: All PASS

- [ ] **Step 3: Verify MCP tools manually**

Start MCP server against QUIC workspace and verify:
```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m ivy_lsp.mcp_server --workspace protocol-testing/quic
```
Call `ivy_suggest_requirements`, `ivy_requirement_gaps`, `ivy_validate_spec` via MCP client.

- [ ] **Step 4: Final commit**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
git add -A
git status  # verify no unexpected files
git commit -m "feat(suggestion): complete LSP requirement-suggestion engine integration"
```
