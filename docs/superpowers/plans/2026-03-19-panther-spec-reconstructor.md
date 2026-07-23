# PANTHER Spec Reconstructor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an event-driven tool that reconstructs Ivy formal protocol specifications from git commit histories, with developer interviews interleaved, working both as a Claude Code plugin (local) and an Agent SDK CLI (CI/CD).

**Architecture:** Three tightly integrated components:
1. **spec-reconstructor** (new submodule of panther_ivy) — core analysis library + SDK CLI, imports from ivy-lsp's SemanticModel/RequirementGraph
2. **panther-ivy-plugin** (extended) — new agents, skills, commands, hooks for the interactive reconstruction workflow
3. **ivy-lsp** (used as-is) — provides MCP tools (ivy_verify, ivy_coverage, etc.) and semantic analysis

Event-sourced SpecEvents extracted from commit diffs drive per-layer Ivy code generation. Low-confidence events trigger developer interview questions.

**Tech Stack:** Python 3.10+, dataclasses, JSONL/YAML persistence, Claude Code plugin SDK (hooks/agents/skills/commands), Claude Agent SDK, GitHub Actions, GitLab CI

**Design Spec:** `/Users/elniak/.claude/plans/mutable-imagining-tiger.md`

---

## Module Architecture

```
panther_ivy/submodules/
├── ivy-lsp/                          # EXISTING — provides MCP tools + SemanticModel
│   └── ivy_lsp/
│       ├── semantic/model.py         # SemanticModel (imported by spec-reconstructor)
│       ├── analysis/requirement_graph.py  # RequirementGraph (imported)
│       └── tools/                    # MCP tools: ivy_verify, ivy_coverage, etc.
│
├── panther-ivy-plugin/               # EXISTING — EXTENDED with reconstruction workflow
│   └── plugins/panther-ivy-plugin/
│       ├── agents/
│       │   ├── reconstructor.md      # NEW: main reconstruction orchestrator
│       │   └── commit-analyst.md     # NEW: commit analysis specialist
│       ├── skills/
│       │   ├── reconstruction-workflow/SKILL.md  # NEW: 4-phase workflow
│       │   └── commit-analysis/SKILL.md          # NEW: diff interpretation
│       ├── commands/
│       │   ├── reconstruct-init.md   # NEW: /reconstruct-init
│       │   ├── reconstruct-status.md # NEW: /reconstruct-status
│       │   ├── reconstruct-resume.md # NEW: /reconstruct-resume
│       │   └── reconstruct-answer.md # NEW: /reconstruct-answer
│       └── hooks/
│           └── hooks.json            # MODIFIED: add reconstruction hooks
│
└── spec-reconstructor/               # NEW SUBMODULE — core library + SDK
    ├── pyproject.toml
    ├── spec_reconstructor/           # Python package
    │   ├── __init__.py
    │   ├── events/
    │   │   ├── __init__.py
    │   │   ├── spec_events.py        # SpecEvent hierarchy (dataclasses)
    │   │   ├── event_store.py        # JSONL append-only persistence
    │   │   └── event_handlers/
    │   │       ├── __init__.py       # Handler registry
    │   │       ├── base_handler.py   # Abstract handler interface
    │   │       ├── types_handler.py  # Layer 1
    │   │       ├── frame_handler.py  # Layer 4
    │   │       ├── connection_handler.py  # Layer 7
    │   │       ├── error_handler.py  # Layer 9
    │   │       └── behavior_handler.py    # Layer 11
    │   ├── analysis/
    │   │   ├── __init__.py
    │   │   ├── commit_analyzer.py    # git diff → SpecEvents
    │   │   ├── relevance_classifier.py
    │   │   ├── rfc_reference_extractor.py
    │   │   └── language_analyzers/
    │   │       ├── __init__.py       # Language detector + router
    │   │       └── c_analyzer.py     # C/C++ semantic extraction
    │   ├── state/
    │   │   ├── __init__.py
    │   │   ├── spec_state.py         # Event-sourced SpecificationState
    │   │   ├── layer_snapshot.py     # Per-layer tracking
    │   │   └── coverage_tracker.py
    │   ├── interview/
    │   │   ├── __init__.py
    │   │   ├── question_generator.py # Confidence-based question gen
    │   │   ├── question_store.py     # YAML persistence
    │   │   ├── answer_processor.py   # Answer → Ivy update mapping
    │   │   └── templates/
    │   └── verification/
    │       ├── __init__.py
    │       ├── verification_loop.py  # Wraps ivy-lsp MCP tools
    │       └── fix_generator.py
    ├── sdk/                          # AGENT SDK CLI
    │   ├── __init__.py
    │   ├── app.py                    # Headless async driver
    │   ├── config.py
    │   ├── github_adapter.py
    │   └── gitlab_adapter.py
    ├── actions/                      # CI/CD TEMPLATES
    │   ├── github/action.yml
    │   └── gitlab/.gitlab-ci.yml
    └── tests/
        ├── conftest.py
        ├── test_spec_events.py
        ├── test_event_store.py
        ├── test_relevance_classifier.py
        ├── test_commit_analyzer.py
        ├── test_c_analyzer.py
        ├── test_spec_state.py
        ├── test_types_handler.py
        ├── test_frame_handler.py
        ├── test_connection_handler.py
        ├── test_question_generator.py
        └── test_answer_processor.py
```

**Key integration points:**
- `spec_reconstructor.verification.verification_loop` imports ivy-lsp MCP tool interfaces
- `spec_reconstructor.state.coverage_tracker` uses ivy-lsp's `RequirementGraph` snapshots
- panther-ivy-plugin agents invoke `spec_reconstructor` Python modules for analysis
- SDK CLI wraps `spec_reconstructor` + ivy-lsp for headless CI/CD execution

---

## Phase 1: Core Data Model (MVP Foundation)

### Task 1: Package Scaffold + SpecEvent Type Hierarchy

**Files:**
- Create: `spec-reconstructor/pyproject.toml`
- Create: `spec-reconstructor/spec_reconstructor/__init__.py`
- Create: `spec-reconstructor/spec_reconstructor/events/__init__.py`
- Create: `spec-reconstructor/spec_reconstructor/events/spec_events.py`
- Test: `spec-reconstructor/tests/test_spec_events.py`

- [ ] **Step 1: Create package scaffold**

```bash
# Create the new submodule directory inside panther_ivy/submodules/
SPEC_ROOT=panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor
mkdir -p $SPEC_ROOT/{spec_reconstructor/{events/event_handlers,analysis/language_analyzers,state,interview,verification},sdk,actions/{github,gitlab},tests}
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel>=0.41.0"]
build-backend = "setuptools.build_meta"

[project]
name = "panther-spec-reconstructor"
version = "0.1.0"
requires-python = ">=3.10"
description = "Reconstruct Ivy formal protocol specs from git commit histories"
dependencies = [
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov"]
sdk = ["anthropic>=0.40.0"]

[project.scripts]
panther-spec-reconstruct = "sdk.app:main"

[tool.setuptools]
packages = { find = { include = ["spec_reconstructor*", "sdk*"] } }
```

- [ ] **Step 3: Write the failing test for SpecEvent hierarchy**

```python
# tests/test_spec_events.py
"""Tests for the SpecEvent type hierarchy."""
import json
from datetime import datetime

from spec_reconstructor.events.spec_events import (
    FieldDef,
    FrameTypeDefined,
    HandlerAdded,
    HandlerKind,
    LayerName,
    ProtocolErrorDefined,
    RelevanceLevel,
    RequirementExtracted,
    RequirementLevel,
    SpecEvent,
    StateTransitionDefined,
    TypeAdded,
    TypeKind,
)


class TestSpecEventBase:
    def test_create_event_with_all_fields(self):
        event = TypeAdded(
            source_commit="abc1234",
            relevance=RelevanceLevel.HIGH,
            confidence=0.85,
            target_layer=LayerName.TYPES,
            type_name="quic_packet_type",
            kind=TypeKind.ENUM,
            fields=[FieldDef(name="initial", type_str="this")],
        )
        assert event.source_commit == "abc1234"
        assert event.confidence == 0.85
        assert event.target_layer == LayerName.TYPES
        assert isinstance(event.timestamp, datetime)
        assert isinstance(event.event_id, str)

    def test_event_serialization_roundtrip(self):
        event = TypeAdded(
            source_commit="abc1234",
            relevance=RelevanceLevel.HIGH,
            confidence=0.9,
            target_layer=LayerName.TYPES,
            type_name="stream_id",
            kind=TypeKind.BIT_VECTOR,
            fields=[],
        )
        d = event.to_dict()
        json_str = json.dumps(d)
        loaded = json.loads(json_str)
        assert loaded["event_type"] == "TypeAdded"
        assert loaded["type_name"] == "stream_id"
        assert loaded["confidence"] == 0.9

    def test_deterministic_event_id(self):
        """Same content produces same event_id."""
        kwargs = dict(
            source_commit="abc1234",
            relevance=RelevanceLevel.HIGH,
            confidence=0.9,
            target_layer=LayerName.TYPES,
            type_name="cid",
            kind=TypeKind.UNINTERPRETED,
            fields=[],
        )
        e1 = TypeAdded(**kwargs)
        e2 = TypeAdded(**kwargs)
        assert e1.event_id == e2.event_id


class TestConcreteEvents:
    def test_state_transition_defined(self):
        event = StateTransitionDefined(
            source_commit="def5678",
            relevance=RelevanceLevel.HIGH,
            confidence=0.7,
            target_layer=LayerName.CONNECTION,
            from_state="idle",
            to_state="initial",
            trigger_action="packet_event",
            guards=["pkt.ptype = initial"],
        )
        assert event.target_layer == LayerName.CONNECTION
        d = event.to_dict()
        assert d["from_state"] == "idle"
        assert d["guards"] == ["pkt.ptype = initial"]

    def test_handler_added(self):
        event = HandlerAdded(
            source_commit="ghi9012",
            relevance=RelevanceLevel.MEDIUM,
            confidence=0.6,
            target_layer=LayerName.ENTITY_BEHAVIOR,
            action_name="packet_event",
            handler_kind=HandlerKind.AFTER,
            parameters=[FieldDef(name="pkt", type_str="quic_packet")],
            body_hints=["conn_total_data := conn_total_data + pkt.payload_length"],
        )
        assert event.handler_kind == HandlerKind.AFTER
        assert len(event.parameters) == 1

    def test_frame_type_defined(self):
        event = FrameTypeDefined(
            source_commit="jkl3456",
            relevance=RelevanceLevel.HIGH,
            confidence=0.8,
            target_layer=LayerName.FRAME,
            frame_name="stream_frame",
            fields=[
                FieldDef(name="stream_id", type_str="stream_id"),
                FieldDef(name="offset", type_str="stream_pos"),
                FieldDef(name="length", type_str="stream_pos"),
                FieldDef(name="data", type_str="stream_data"),
            ],
        )
        assert len(event.fields) == 4

    def test_protocol_error_defined(self):
        event = ProtocolErrorDefined(
            source_commit="mno7890",
            relevance=RelevanceLevel.MEDIUM,
            confidence=0.75,
            target_layer=LayerName.ERROR_HANDLING,
            error_name="FLOW_CONTROL_ERROR",
            error_code=3,
            description="Peer violated flow control protocol",
        )
        assert event.error_code == 3

    def test_requirement_extracted(self):
        event = RequirementExtracted(
            source_commit="pqr1234",
            relevance=RelevanceLevel.HIGH,
            confidence=0.95,
            target_layer=LayerName.PACKET,
            rfc_section="rfc9000:17.2.2",
            requirement_text="Initial packets MUST include a version field",
            level=RequirementLevel.MUST,
        )
        assert event.level == RequirementLevel.MUST
        d = event.to_dict()
        assert d["rfc_section"] == "rfc9000:17.2.2"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_spec_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.events.spec_events'`

- [ ] **Step 5: Implement SpecEvent hierarchy**

```python
# core/events/spec_events.py
"""Specification Event type hierarchy.

Events are the core abstraction of the Spec Reconstructor. Every commit
produces typed SpecEvents with confidence scores. Event handlers update
corresponding Ivy layers. The event log (append-only JSONL) is the
single source of truth.

Follows the pattern of panther.core.events.base.event_base.BaseEvent
but uses dataclasses for simplicity and serializability.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

_UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class RelevanceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class LayerName(str, Enum):
    TYPES = "types"                       # Layer 1
    APPLICATION = "application"           # Layer 2
    SECURITY = "security"                 # Layer 3
    FRAME = "frame"                       # Layer 4
    PACKET = "packet"                     # Layer 5
    PROTECTION = "protection"             # Layer 6
    CONNECTION = "connection"             # Layer 7
    TRANSPORT_PARAMS = "transport_params" # Layer 8
    ERROR_HANDLING = "error_handling"     # Layer 9
    ENTITY_DEFS = "entity_defs"          # Layer 10
    ENTITY_BEHAVIOR = "entity_behavior"  # Layer 11
    SHIMS = "shims"                       # Layer 12
    SERIALIZATION = "serialization"       # Layer 13
    UTILITIES = "utilities"               # Layer 14


class TypeKind(str, Enum):
    ENUM = "enum"
    STRUCT = "struct"
    BIT_VECTOR = "bit_vector"
    UNINTERPRETED = "uninterpreted"


class HandlerKind(str, Enum):
    BEFORE = "before"
    AFTER = "after"


class RequirementLevel(str, Enum):
    MUST = "MUST"
    MUST_NOT = "MUST_NOT"
    SHOULD = "SHOULD"
    SHOULD_NOT = "SHOULD_NOT"
    MAY = "MAY"


@dataclass(frozen=True)
class FieldDef:
    """A typed field in a type, frame, or parameter list."""
    name: str
    type_str: str


def _content_uuid(content: str) -> str:
    """Deterministic UUID5 from content string."""
    return str(uuid.uuid5(_UUID_NAMESPACE, content))


@dataclass
class SpecEvent:
    """Base event produced by commit analysis.

    Every event has a source commit, relevance level, confidence score,
    and target Ivy layer. The event_id is deterministic (content-based
    UUID5) so that replaying the same commit produces the same events.
    """
    source_commit: str
    relevance: RelevanceLevel
    confidence: float
    target_layer: LayerName
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default="", init=False)

    def __post_init__(self) -> None:
        sig = self._content_signature()
        object.__setattr__(self, "event_id", _content_uuid(sig))

    def _content_signature(self) -> str:
        """Deterministic signature excluding timestamp."""
        parts = [
            type(self).__name__,
            self.source_commit,
            str(self.relevance.value),
            str(self.confidence),
            str(self.target_layer.value),
        ]
        parts.extend(self._extra_signature_parts())
        return "|".join(parts)

    def _extra_signature_parts(self) -> List[str]:
        """Override in subclasses to include extra fields in the signature."""
        return []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        d = {}
        d["event_type"] = type(self).__name__
        d["event_id"] = self.event_id
        d["source_commit"] = self.source_commit
        d["relevance"] = self.relevance.value
        d["confidence"] = self.confidence
        d["target_layer"] = self.target_layer.value
        d["timestamp"] = self.timestamp.isoformat()
        d.update(self._extra_dict_fields())
        return d

    def _extra_dict_fields(self) -> Dict[str, Any]:
        """Override in subclasses to include extra fields in serialization."""
        return {}


@dataclass
class TypeAdded(SpecEvent):
    """A new type/struct/enum extracted from implementation code."""
    type_name: str = ""
    kind: TypeKind = TypeKind.UNINTERPRETED
    fields: List[FieldDef] = field(default_factory=list)

    def _extra_signature_parts(self) -> List[str]:
        field_sigs = [f"{f.name}:{f.type_str}" for f in self.fields]
        return [self.type_name, self.kind.value] + field_sigs

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "type_name": self.type_name,
            "kind": self.kind.value,
            "fields": [asdict(f) for f in self.fields],
        }


@dataclass
class StateTransitionDefined(SpecEvent):
    """A state machine transition extracted from implementation."""
    from_state: str = ""
    to_state: str = ""
    trigger_action: str = ""
    guards: List[str] = field(default_factory=list)

    def _extra_signature_parts(self) -> List[str]:
        return [self.from_state, self.to_state, self.trigger_action] + self.guards

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "trigger_action": self.trigger_action,
            "guards": self.guards,
        }


@dataclass
class HandlerAdded(SpecEvent):
    """A before/after handler extracted from implementation."""
    action_name: str = ""
    handler_kind: HandlerKind = HandlerKind.AFTER
    parameters: List[FieldDef] = field(default_factory=list)
    body_hints: List[str] = field(default_factory=list)

    def _extra_signature_parts(self) -> List[str]:
        param_sigs = [f"{p.name}:{p.type_str}" for p in self.parameters]
        return [self.action_name, self.handler_kind.value] + param_sigs + self.body_hints

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "action_name": self.action_name,
            "handler_kind": self.handler_kind.value,
            "parameters": [asdict(p) for p in self.parameters],
            "body_hints": self.body_hints,
        }


@dataclass
class FrameTypeDefined(SpecEvent):
    """A new frame/message type extracted from implementation."""
    frame_name: str = ""
    fields: List[FieldDef] = field(default_factory=list)

    def _extra_signature_parts(self) -> List[str]:
        field_sigs = [f"{f.name}:{f.type_str}" for f in self.fields]
        return [self.frame_name] + field_sigs

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "frame_name": self.frame_name,
            "fields": [asdict(f) for f in self.fields],
        }


@dataclass
class ProtocolErrorDefined(SpecEvent):
    """A protocol error code/type extracted from implementation."""
    error_name: str = ""
    error_code: Optional[int] = None
    description: str = ""

    def _extra_signature_parts(self) -> List[str]:
        return [self.error_name, str(self.error_code or ""), self.description]

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "error_name": self.error_name,
            "error_code": self.error_code,
            "description": self.description,
        }


@dataclass
class RequirementExtracted(SpecEvent):
    """An RFC requirement extracted from implementation comments."""
    rfc_section: str = ""
    requirement_text: str = ""
    level: RequirementLevel = RequirementLevel.MUST

    def _extra_signature_parts(self) -> List[str]:
        return [self.rfc_section, self.requirement_text, self.level.value]

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "rfc_section": self.rfc_section,
            "requirement_text": self.requirement_text,
            "level": self.level.value,
        }


@dataclass
class SecurityPropertyAdded(SpecEvent):
    """A security/crypto property extracted from implementation."""
    property_name: str = ""
    property_kind: str = ""  # "handshake", "key_establishment", "encryption"

    def _extra_signature_parts(self) -> List[str]:
        return [self.property_name, self.property_kind]

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "property_name": self.property_name,
            "property_kind": self.property_kind,
        }


@dataclass
class PacketStructureDefined(SpecEvent):
    """A packet-level structure extracted from implementation."""
    packet_name: str = ""
    fields: List[FieldDef] = field(default_factory=list)

    def _extra_signature_parts(self) -> List[str]:
        field_sigs = [f"{f.name}:{f.type_str}" for f in self.fields]
        return [self.packet_name] + field_sigs

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "packet_name": self.packet_name,
            "fields": [asdict(f) for f in self.fields],
        }


@dataclass
class SerializationDefined(SpecEvent):
    """Serialization/deserialization logic extracted from implementation."""
    format_name: str = ""
    direction: str = ""  # "serialize" | "deserialize"

    def _extra_signature_parts(self) -> List[str]:
        return [self.format_name, self.direction]

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "format_name": self.format_name,
            "direction": self.direction,
        }


@dataclass
class TransportParamDefined(SpecEvent):
    """A transport parameter extracted from implementation."""
    param_name: str = ""
    param_type: str = ""  # "integer" | "boolean" | "opaque"
    default_value: str = ""

    def _extra_signature_parts(self) -> List[str]:
        return [self.param_name, self.param_type, self.default_value]

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "param_name": self.param_name,
            "param_type": self.param_type,
            "default_value": self.default_value,
        }


@dataclass
class EntityRoleDefined(SpecEvent):
    """A protocol entity role (client/server/MIM) extracted from implementation."""
    role_name: str = ""  # "client" | "server" | "mim"
    entity_type: str = ""

    def _extra_signature_parts(self) -> List[str]:
        return [self.role_name, self.entity_type]

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "role_name": self.role_name,
            "entity_type": self.entity_type,
        }


@dataclass
class ShimInterfaceDefined(SpecEvent):
    """A shim interface (bridge between formal model and implementation) extracted."""
    shim_name: str = ""
    direction: str = ""  # "inbound" | "outbound"

    def _extra_signature_parts(self) -> List[str]:
        return [self.shim_name, self.direction]

    def _extra_dict_fields(self) -> Dict[str, Any]:
        return {
            "shim_name": self.shim_name,
            "direction": self.direction,
        }


# Layer dependency order (used for batch processing in retroactive mode)
LAYER_DEPENDENCY_ORDER: List[LayerName] = [
    LayerName.TYPES,
    LayerName.ERROR_HANDLING,
    LayerName.FRAME,
    LayerName.PACKET,
    LayerName.PROTECTION,
    LayerName.SECURITY,
    LayerName.CONNECTION,
    LayerName.TRANSPORT_PARAMS,
    LayerName.APPLICATION,
    LayerName.ENTITY_DEFS,
    LayerName.ENTITY_BEHAVIOR,
    LayerName.SHIMS,
    LayerName.SERIALIZATION,
    LayerName.UTILITIES,
]
```

- [ ] **Step 6: Create __init__.py files**

```python
# spec_reconstructor/__init__.py
"""PANTHER Spec Reconstructor - core analysis library."""

# spec_reconstructor/events/__init__.py
"""Specification event system."""
from spec_reconstructor.events.spec_events import (
    EntityRoleDefined,
    FieldDef,
    FrameTypeDefined,
    HandlerAdded,
    HandlerKind,
    LayerName,
    PacketStructureDefined,
    ProtocolErrorDefined,
    RelevanceLevel,
    RequirementExtracted,
    RequirementLevel,
    SecurityPropertyAdded,
    SerializationDefined,
    ShimInterfaceDefined,
    SpecEvent,
    StateTransitionDefined,
    TransportParamDefined,
    TypeAdded,
    TypeKind,
    LAYER_DEPENDENCY_ORDER,
)

# tests/__init__.py
# (empty)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_spec_events.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/
git commit -m "feat(spec-reconstructor): add SpecEvent type hierarchy with 9 event types"
```

---

### Task 2: Event Store (JSONL Persistence)

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/events/event_store.py`
- Test: `spec-reconstructor/tests/test_event_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_event_store.py
"""Tests for JSONL event store."""
import json
import tempfile
from pathlib import Path

from spec_reconstructor.events.spec_events import (
    FieldDef,
    LayerName,
    RelevanceLevel,
    TypeAdded,
    TypeKind,
    StateTransitionDefined,
)
from spec_reconstructor.events.event_store import EventStore


class TestEventStore:
    def test_append_and_read_single_event(self, tmp_path):
        store = EventStore(tmp_path / "events.jsonl")
        event = TypeAdded(
            source_commit="abc1234",
            relevance=RelevanceLevel.HIGH,
            confidence=0.9,
            target_layer=LayerName.TYPES,
            type_name="cid",
            kind=TypeKind.UNINTERPRETED,
            fields=[],
        )
        store.append(event)
        events = store.read_all()
        assert len(events) == 1
        assert events[0]["event_type"] == "TypeAdded"
        assert events[0]["type_name"] == "cid"

    def test_append_multiple_events(self, tmp_path):
        store = EventStore(tmp_path / "events.jsonl")
        for i in range(5):
            store.append(TypeAdded(
                source_commit=f"commit_{i}",
                relevance=RelevanceLevel.MEDIUM,
                confidence=0.5,
                target_layer=LayerName.TYPES,
                type_name=f"type_{i}",
                kind=TypeKind.ENUM,
                fields=[],
            ))
        events = store.read_all()
        assert len(events) == 5

    def test_read_empty_store(self, tmp_path):
        store = EventStore(tmp_path / "events.jsonl")
        assert store.read_all() == []

    def test_read_events_for_commit(self, tmp_path):
        store = EventStore(tmp_path / "events.jsonl")
        store.append(TypeAdded(
            source_commit="aaa",
            relevance=RelevanceLevel.HIGH,
            confidence=0.9,
            target_layer=LayerName.TYPES,
            type_name="t1",
            kind=TypeKind.ENUM,
            fields=[],
        ))
        store.append(StateTransitionDefined(
            source_commit="bbb",
            relevance=RelevanceLevel.HIGH,
            confidence=0.8,
            target_layer=LayerName.CONNECTION,
            from_state="idle",
            to_state="active",
            trigger_action="connect",
            guards=[],
        ))
        store.append(TypeAdded(
            source_commit="aaa",
            relevance=RelevanceLevel.MEDIUM,
            confidence=0.7,
            target_layer=LayerName.TYPES,
            type_name="t2",
            kind=TypeKind.STRUCT,
            fields=[],
        ))
        aaa_events = store.read_for_commit("aaa")
        assert len(aaa_events) == 2
        assert all(e["source_commit"] == "aaa" for e in aaa_events)

    def test_persistence_across_instances(self, tmp_path):
        path = tmp_path / "events.jsonl"
        store1 = EventStore(path)
        store1.append(TypeAdded(
            source_commit="abc",
            relevance=RelevanceLevel.HIGH,
            confidence=0.9,
            target_layer=LayerName.TYPES,
            type_name="x",
            kind=TypeKind.ENUM,
            fields=[],
        ))
        store2 = EventStore(path)
        assert len(store2.read_all()) == 1

    def test_last_processed_commit(self, tmp_path):
        store = EventStore(tmp_path / "events.jsonl")
        assert store.last_processed_commit() is None
        store.append(TypeAdded(
            source_commit="first",
            relevance=RelevanceLevel.LOW,
            confidence=0.3,
            target_layer=LayerName.TYPES,
            type_name="x",
            kind=TypeKind.ENUM,
            fields=[],
        ))
        store.append(TypeAdded(
            source_commit="second",
            relevance=RelevanceLevel.LOW,
            confidence=0.3,
            target_layer=LayerName.TYPES,
            type_name="y",
            kind=TypeKind.ENUM,
            fields=[],
        ))
        assert store.last_processed_commit() == "second"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_event_store.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement EventStore**

```python
# core/events/event_store.py
"""Append-only JSONL event store.

Events are persisted as one JSON object per line. This is the single
source of truth for the Spec Reconstructor — both retroactive replay
and forward mode produce the same event log format.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from spec_reconstructor.events.spec_events import SpecEvent


class EventStore:
    """Append-only JSONL event persistence."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, event: SpecEvent) -> None:
        """Append a single event to the log."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def append_batch(self, events: List[SpecEvent]) -> None:
        """Append multiple events atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as f:
            for event in events:
                f.write(json.dumps(event.to_dict()) + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        """Read all events from the log."""
        if not self._path.exists():
            return []
        events = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def read_for_commit(self, commit_sha: str) -> List[Dict[str, Any]]:
        """Read all events for a specific commit."""
        return [e for e in self.read_all() if e["source_commit"] == commit_sha]

    def last_processed_commit(self) -> Optional[str]:
        """Return the source_commit of the last event, or None if empty."""
        events = self.read_all()
        if not events:
            return None
        return events[-1]["source_commit"]

    def event_count(self) -> int:
        """Return total number of events in the log."""
        return len(self.read_all())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_event_store.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/events/event_store.py spec-reconstructor/tests/test_event_store.py
git commit -m "feat(spec-reconstructor): add JSONL event store with append/read/filter"
```

---

### Task 3: Relevance Classifier

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/analysis/relevance_classifier.py`
- Create: `spec-reconstructor/spec_reconstructor/analysis/__init__.py`
- Test: `spec-reconstructor/tests/test_relevance_classifier.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_relevance_classifier.py
"""Tests for commit relevance classification."""
from spec_reconstructor.events.spec_events import RelevanceLevel
from spec_reconstructor.analysis.relevance_classifier import classify_relevance, RelevanceResult


class TestRelevanceClassifier:
    def test_high_relevance_state_machine(self):
        diff = """
diff --git a/src/quic/connection.c b/src/quic/connection.c
+++ b/src/quic/connection.c
@@ -100,0 +101,15 @@
+static int handle_state_transition(quic_conn_t *conn, quic_packet_t *pkt) {
+    if (conn->state == CONN_STATE_IDLE) {
+        conn->state = CONN_STATE_INITIAL;
+        return 0;
+    }
+    return -1;
+}
"""
        result = classify_relevance(diff, "feat: add connection state machine")
        assert result.level == RelevanceLevel.HIGH
        assert result.score >= 0.8
        assert "connection" in result.affected_layers or "state_machine" in result.reason

    def test_high_relevance_packet_parsing(self):
        diff = """
diff --git a/src/quic/packet.c b/src/quic/packet.c
+++ b/src/quic/packet.c
+typedef struct {
+    uint8_t type;
+    uint32_t version;
+    uint8_t dcid[20];
+    uint8_t scid[20];
+} quic_long_header_t;
+
+int parse_initial_packet(const uint8_t *buf, size_t len, quic_long_header_t *hdr) {
"""
        result = classify_relevance(diff, "feat: add Initial packet parsing")
        assert result.level == RelevanceLevel.HIGH
        assert result.score >= 0.7

    def test_low_relevance_docs_only(self):
        diff = """
diff --git a/README.md b/README.md
+++ b/README.md
+## New Feature
+Added initial packet handling.
"""
        result = classify_relevance(diff, "docs: update README")
        assert result.level in (RelevanceLevel.LOW, RelevanceLevel.NONE)
        assert result.score < 0.2

    def test_low_relevance_build_system(self):
        diff = """
diff --git a/CMakeLists.txt b/CMakeLists.txt
+++ b/CMakeLists.txt
+add_library(quic_new src/new.c)
"""
        result = classify_relevance(diff, "build: add new library target")
        assert result.level == RelevanceLevel.LOW
        assert result.score < 0.3

    def test_medium_relevance_test_code(self):
        diff = """
diff --git a/tests/test_connection.c b/tests/test_connection.c
+++ b/tests/test_connection.c
+void test_initial_packet_handling() {
+    quic_conn_t *conn = create_connection();
+    quic_packet_t pkt = {.type = INITIAL, .version = QUIC_V1};
+    assert(handle_packet(conn, &pkt) == 0);
+    assert(conn->state == CONN_STATE_INITIAL);
+}
"""
        result = classify_relevance(diff, "test: add connection state test")
        assert result.level in (RelevanceLevel.MEDIUM, RelevanceLevel.LOW)

    def test_result_has_affected_layers(self):
        diff = """
diff --git a/src/quic/crypto.c b/src/quic/crypto.c
+++ b/src/quic/crypto.c
+int derive_initial_keys(const uint8_t *dcid, size_t dcid_len, quic_keys_t *keys) {
"""
        result = classify_relevance(diff, "feat: add initial key derivation")
        assert isinstance(result.affected_layers, list)
        assert len(result.affected_layers) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_relevance_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement relevance classifier**

```python
# core/analysis/relevance_classifier.py
"""Commit relevance classification for protocol implementations.

Scores commits by how relevant they are to formal specification
construction. Uses pattern-matching heuristics on unified diffs
and commit messages to classify into HIGH/MEDIUM/LOW/NONE.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from spec_reconstructor.events.spec_events import RelevanceLevel


@dataclass
class RelevanceResult:
    """Result of commit relevance classification."""
    level: RelevanceLevel
    score: float  # 0.0–1.0
    reason: str
    affected_layers: List[str] = field(default_factory=list)


# Patterns that indicate protocol-relevant code changes
_HIGH_PATTERNS = [
    (re.compile(r"\bstate\s*=\s*\w+STATE\w*", re.I), 0.9, "state_machine", ["connection"]),
    (re.compile(r"\bconn->state\b|\bconn\.state\b", re.I), 0.9, "state_machine", ["connection"]),
    (re.compile(r"\bparse_\w*packet\b|\bhandle_\w*packet\b", re.I), 0.85, "packet_parsing", ["packet"]),
    (re.compile(r"\btypedef\s+struct\s+\{[^}]*\b(type|version|dcid|scid)\b", re.I | re.S), 0.85, "packet_struct", ["packet", "types"]),
    (re.compile(r"\bparse_\w*frame\b|\bhandle_\w*frame\b|\bframe_type\b", re.I), 0.85, "frame_handling", ["frame"]),
    (re.compile(r"\bencrypt\b|\bdecrypt\b|\bderive_\w*key\b|\btls_", re.I), 0.8, "crypto", ["protection", "security"]),
    (re.compile(r"\bconnection_close\b|\berror_code\b|\btransport_error\b", re.I), 0.75, "error_handling", ["error_handling"]),
    (re.compile(r"\bstream_\w+\b.*\boffset\b|\bflow_control\b", re.I), 0.8, "stream_handling", ["frame", "connection"]),
    (re.compile(r"\bsend_\w*packet\b|\brecv_\w*packet\b", re.I), 0.8, "packet_io", ["packet", "shims"]),
]

_MEDIUM_PATTERNS = [
    (re.compile(r"\bassert\s*\(.*\bstate\b", re.I), 0.5, "state_assertion", ["connection"]),
    (re.compile(r"\btest_\w+\b.*\bpacket\b|\btest_\w+\b.*\bconn", re.I), 0.4, "test_code", []),
    (re.compile(r"\bconfig\b.*\bmax_\w+\b|\btransport_param", re.I), 0.5, "transport_params", ["transport_params"]),
    (re.compile(r"\bserialize\b|\bdeserialize\b|\bmarshal\b|\bunmarshal\b", re.I), 0.5, "serialization", ["serialization"]),
]

_LOW_FILE_PATTERNS = [
    re.compile(r"\.(md|txt|rst)$", re.I),
    re.compile(r"CMakeLists\.txt$|Makefile$|\.cmake$", re.I),
    re.compile(r"\.gitignore$|\.github/|\.gitlab", re.I),
    re.compile(r"Dockerfile|docker-compose", re.I),
    re.compile(r"\.yml$|\.yaml$", re.I),  # CI configs
]

_LOW_MESSAGE_PATTERNS = [
    re.compile(r"^(docs|doc|readme|chore|ci|build|style|format):", re.I),
]


def classify_relevance(diff: str, commit_message: str) -> RelevanceResult:
    """Classify a commit's relevance to formal specification construction."""
    # Check for low-relevance commit messages first
    for pattern in _LOW_MESSAGE_PATTERNS:
        if pattern.search(commit_message):
            # Still check diff for protocol content (docs might mention protocol concepts)
            score, reason, layers = _scan_diff_patterns(diff)
            if score < 0.5:
                return RelevanceResult(
                    level=RelevanceLevel.LOW if score > 0.1 else RelevanceLevel.NONE,
                    score=max(0.1, score * 0.5),
                    reason=f"low-relevance commit message ({reason})",
                    affected_layers=layers,
                )

    # Check if diff only touches low-relevance files
    changed_files = _extract_file_paths(diff)
    low_file_count = sum(
        1 for f in changed_files
        if any(p.search(f) for p in _LOW_FILE_PATTERNS)
    )
    if changed_files and low_file_count == len(changed_files):
        return RelevanceResult(
            level=RelevanceLevel.LOW,
            score=0.1,
            reason="only low-relevance files changed",
            affected_layers=[],
        )

    # Scan diff content for protocol-relevant patterns
    score, reason, layers = _scan_diff_patterns(diff)

    if score >= 0.7:
        level = RelevanceLevel.HIGH
    elif score >= 0.4:
        level = RelevanceLevel.MEDIUM
    elif score >= 0.15:
        level = RelevanceLevel.LOW
    else:
        level = RelevanceLevel.NONE

    return RelevanceResult(
        level=level,
        score=score,
        reason=reason,
        affected_layers=layers,
    )


def _scan_diff_patterns(diff: str) -> tuple[float, str, list[str]]:
    """Scan diff for protocol-relevant patterns. Returns (score, reason, layers)."""
    best_score = 0.0
    best_reason = "no protocol patterns found"
    all_layers: set[str] = set()

    for pattern, weight, reason, layers in _HIGH_PATTERNS:
        if pattern.search(diff):
            if weight > best_score:
                best_score = weight
                best_reason = reason
            all_layers.update(layers)

    for pattern, weight, reason, layers in _MEDIUM_PATTERNS:
        if pattern.search(diff):
            if weight > best_score:
                best_score = weight
                best_reason = reason
            all_layers.update(layers)

    return best_score, best_reason, sorted(all_layers)


def _extract_file_paths(diff: str) -> list[str]:
    """Extract changed file paths from unified diff."""
    paths = []
    for match in re.finditer(r"^diff --git a/.+ b/(.+)$", diff, re.MULTILINE):
        paths.append(match.group(1))
    return paths
```

```python
# spec_reconstructor/analysis/__init__.py
"""Commit analysis pipeline."""
from spec_reconstructor.analysis.relevance_classifier import classify_relevance, RelevanceResult
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_relevance_classifier.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/analysis/ spec-reconstructor/tests/test_relevance_classifier.py
git commit -m "feat(spec-reconstructor): add commit relevance classifier with pattern heuristics"
```

---

### Task 4: C Language Analyzer

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/analysis/language_analyzers/__init__.py`
- Create: `spec-reconstructor/spec_reconstructor/analysis/language_analyzers/c_analyzer.py`
- Create: `spec-reconstructor/spec_reconstructor/analysis/rfc_reference_extractor.py`
- Test: `spec-reconstructor/tests/test_c_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_c_analyzer.py
"""Tests for C language analyzer — extracts SpecEvents from C diff hunks."""
from spec_reconstructor.events.spec_events import (
    FieldDef,
    FrameTypeDefined,
    HandlerAdded,
    LayerName,
    PacketStructureDefined,
    ProtocolErrorDefined,
    RelevanceLevel,
    RequirementExtracted,
    SecurityPropertyAdded,
    StateTransitionDefined,
    TypeAdded,
    TypeKind,
)
from spec_reconstructor.analysis.language_analyzers.c_analyzer import CAnalyzer


class TestCAnalyzerTypeExtraction:
    def test_extract_enum(self):
        diff_hunk = """
+typedef enum {
+    QUIC_PACKET_INITIAL = 0x00,
+    QUIC_PACKET_ZERO_RTT = 0x01,
+    QUIC_PACKET_HANDSHAKE = 0x02,
+    QUIC_PACKET_RETRY = 0x03,
+} quic_packet_type_t;
"""
        analyzer = CAnalyzer()
        events = analyzer.analyze_hunk(diff_hunk, "src/quic/types.h", "abc123")
        type_events = [e for e in events if isinstance(e, TypeAdded)]
        assert len(type_events) >= 1
        assert type_events[0].kind == TypeKind.ENUM
        assert "quic_packet_type" in type_events[0].type_name

    def test_extract_struct(self):
        diff_hunk = """
+typedef struct {
+    uint8_t type;
+    uint32_t version;
+    uint8_t dcid[20];
+    uint8_t scid[20];
+    size_t payload_length;
+} quic_long_header_t;
"""
        analyzer = CAnalyzer()
        events = analyzer.analyze_hunk(diff_hunk, "src/quic/packet.h", "abc123")
        type_events = [e for e in events if isinstance(e, TypeAdded)]
        assert len(type_events) >= 1
        assert type_events[0].kind == TypeKind.STRUCT
        assert len(type_events[0].fields) >= 3


class TestCAnalyzerStateTransition:
    def test_extract_state_transition(self):
        diff_hunk = """
+    if (conn->state == CONN_STATE_IDLE) {
+        conn->state = CONN_STATE_INITIAL;
+        return 0;
+    }
"""
        analyzer = CAnalyzer()
        events = analyzer.analyze_hunk(diff_hunk, "src/quic/connection.c", "def456")
        st_events = [e for e in events if isinstance(e, StateTransitionDefined)]
        assert len(st_events) >= 1
        assert "idle" in st_events[0].from_state.lower()
        assert "initial" in st_events[0].to_state.lower()


class TestCAnalyzerErrorCodes:
    def test_extract_error_define(self):
        diff_hunk = """
+#define QUIC_ERROR_FLOW_CONTROL 0x03
+#define QUIC_ERROR_STREAM_LIMIT 0x04
"""
        analyzer = CAnalyzer()
        events = analyzer.analyze_hunk(diff_hunk, "src/quic/errors.h", "ghi789")
        err_events = [e for e in events if isinstance(e, ProtocolErrorDefined)]
        assert len(err_events) >= 2
        names = {e.error_name for e in err_events}
        assert "QUIC_ERROR_FLOW_CONTROL" in names or "FLOW_CONTROL" in names


class TestCAnalyzerRfcReferences:
    def test_extract_rfc_comment(self):
        diff_hunk = """
+    /* RFC 9000, Section 17.2.2: Initial Packet */
+    if (pkt->type == QUIC_PACKET_INITIAL) {
"""
        analyzer = CAnalyzer()
        events = analyzer.analyze_hunk(diff_hunk, "src/quic/packet.c", "jkl012")
        req_events = [e for e in events if isinstance(e, RequirementExtracted)]
        assert len(req_events) >= 1
        assert "9000" in req_events[0].rfc_section
        assert "17.2" in req_events[0].rfc_section


class TestCAnalyzerCryptoPatterns:
    def test_extract_key_derivation(self):
        diff_hunk = """
+int derive_initial_keys(const uint8_t *dcid, size_t dcid_len, quic_keys_t *keys) {
+    /* Derive Initial secrets per RFC 9001, Section 5.2 */
"""
        analyzer = CAnalyzer()
        events = analyzer.analyze_hunk(diff_hunk, "src/quic/crypto.c", "mno345")
        sec_events = [e for e in events if isinstance(e, SecurityPropertyAdded)]
        assert len(sec_events) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_c_analyzer.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement C analyzer**

```python
# core/analysis/language_analyzers/__init__.py
"""Language-specific semantic analyzers."""
from spec_reconstructor.analysis.language_analyzers.c_analyzer import CAnalyzer

ANALYZERS = {
    "c": CAnalyzer,
    "h": CAnalyzer,
    "cpp": CAnalyzer,
    "cc": CAnalyzer,
}


def get_analyzer(file_extension: str):
    """Get the appropriate analyzer for a file extension."""
    return ANALYZERS.get(file_extension.lstrip("."))
```

```python
# core/analysis/language_analyzers/c_analyzer.py
"""C/C++ semantic analyzer.

Extracts SpecEvents from C/C++ diff hunks by pattern-matching on
struct/enum definitions, state transitions, error codes, RFC comments,
and crypto function signatures.
"""
from __future__ import annotations

import re
from typing import List

from spec_reconstructor.events.spec_events import (
    FieldDef,
    FrameTypeDefined,
    HandlerAdded,
    HandlerKind,
    LayerName,
    PacketStructureDefined,
    ProtocolErrorDefined,
    RelevanceLevel,
    RequirementExtracted,
    RequirementLevel,
    SecurityPropertyAdded,
    SpecEvent,
    StateTransitionDefined,
    TypeAdded,
    TypeKind,
)

# Pattern: typedef enum { ... } name_t;
_ENUM_RE = re.compile(
    r"typedef\s+enum\s*\{([^}]+)\}\s*(\w+)\s*;",
    re.DOTALL,
)

# Pattern: typedef struct { fields } name_t;
_STRUCT_RE = re.compile(
    r"typedef\s+struct\s*\{([^}]+)\}\s*(\w+)\s*;",
    re.DOTALL,
)

# Pattern: field inside struct — type name; or type name[N];
_FIELD_RE = re.compile(
    r"(\w[\w\s*]+?)\s+(\w+)(?:\[(\d+)\])?\s*;",
)

# Pattern: state transition — x->state = NEW_STATE or x.state = NEW_STATE
_STATE_TRANSITION_RE = re.compile(
    r"(\w+)->state\s*==\s*(\w+).*?(\w+)->state\s*=\s*(\w+)",
    re.DOTALL,
)

# Pattern: #define ERROR_NAME 0xNN
_ERROR_DEFINE_RE = re.compile(
    r"#define\s+(\w*(?:ERROR|ERR)\w*)\s+(0x[0-9a-fA-F]+|\d+)",
)

# Pattern: RFC NNNN, Section X.Y or RFC NNNN Section X.Y.Z
_RFC_RE = re.compile(
    r"RFC\s+(\d{4}),?\s*(?:Section|Sec\.?)\s+([\d.]+)",
    re.I,
)

# Pattern: crypto/key derivation functions
_CRYPTO_RE = re.compile(
    r"\b(derive_\w*key|encrypt|decrypt|aead_\w+|hkdf_\w+|tls_\w+)\s*\(",
    re.I,
)

# Pattern: parse/handle packet or frame functions
_HANDLER_RE = re.compile(
    r"\b(parse|handle|process|send|recv)_(\w+)\s*\(",
    re.I,
)


class CAnalyzer:
    """Extracts SpecEvents from C/C++ diff hunks."""

    def analyze_hunk(
        self, hunk: str, file_path: str, commit_sha: str
    ) -> List[SpecEvent]:
        """Analyze a single diff hunk and return extracted events."""
        events: List[SpecEvent] = []
        # Only look at added lines (lines starting with +)
        added_text = self._extract_added_lines(hunk)

        events.extend(self._extract_enums(added_text, commit_sha))
        events.extend(self._extract_structs(added_text, file_path, commit_sha))
        events.extend(self._extract_state_transitions(added_text, commit_sha))
        events.extend(self._extract_error_codes(added_text, commit_sha))
        events.extend(self._extract_rfc_references(hunk, commit_sha))  # scan full hunk for comments
        events.extend(self._extract_crypto_patterns(added_text, commit_sha))

        return events

    def _extract_added_lines(self, hunk: str) -> str:
        """Extract only the added lines from a diff hunk."""
        lines = []
        for line in hunk.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(line[1:])
        return "\n".join(lines)

    def _extract_enums(self, text: str, sha: str) -> List[SpecEvent]:
        events = []
        for match in _ENUM_RE.finditer(text):
            body, name = match.group(1), match.group(2)
            # Extract enum members
            members = re.findall(r"(\w+)\s*(?:=\s*(?:0x[0-9a-fA-F]+|\d+))?", body)
            fields = [FieldDef(name=m, type_str="this") for m in members if m.strip()]
            # Strip _t suffix for Ivy name
            ivy_name = name.rstrip("_t").rstrip("_T")
            events.append(TypeAdded(
                source_commit=sha,
                relevance=RelevanceLevel.HIGH,
                confidence=0.85,
                target_layer=LayerName.TYPES,
                type_name=ivy_name,
                kind=TypeKind.ENUM,
                fields=fields,
            ))
        return events

    def _extract_structs(
        self, text: str, file_path: str, sha: str
    ) -> List[SpecEvent]:
        events = []
        for match in _STRUCT_RE.finditer(text):
            body, name = match.group(1), match.group(2)
            fields = []
            for fm in _FIELD_RE.finditer(body):
                type_str = fm.group(1).strip()
                field_name = fm.group(2)
                fields.append(FieldDef(name=field_name, type_str=type_str))
            ivy_name = name.rstrip("_t").rstrip("_T")

            # Determine target layer based on file path and struct content
            layer = self._guess_layer_from_path(file_path, ivy_name)

            events.append(TypeAdded(
                source_commit=sha,
                relevance=RelevanceLevel.HIGH,
                confidence=0.8,
                target_layer=layer,
                type_name=ivy_name,
                kind=TypeKind.STRUCT,
                fields=fields,
            ))
        return events

    def _extract_state_transitions(self, text: str, sha: str) -> List[SpecEvent]:
        events = []
        for match in _STATE_TRANSITION_RE.finditer(text):
            from_state = match.group(2).lower()
            to_state = match.group(4).lower()
            events.append(StateTransitionDefined(
                source_commit=sha,
                relevance=RelevanceLevel.HIGH,
                confidence=0.75,
                target_layer=LayerName.CONNECTION,
                from_state=from_state,
                to_state=to_state,
                trigger_action="",
                guards=[],
            ))
        return events

    def _extract_error_codes(self, text: str, sha: str) -> List[SpecEvent]:
        events = []
        for match in _ERROR_DEFINE_RE.finditer(text):
            name = match.group(1)
            code_str = match.group(2)
            code = int(code_str, 16) if code_str.startswith("0x") else int(code_str)
            events.append(ProtocolErrorDefined(
                source_commit=sha,
                relevance=RelevanceLevel.MEDIUM,
                confidence=0.8,
                target_layer=LayerName.ERROR_HANDLING,
                error_name=name,
                error_code=code,
                description="",
            ))
        return events

    def _extract_rfc_references(self, text: str, sha: str) -> List[SpecEvent]:
        events = []
        for match in _RFC_RE.finditer(text):
            rfc_num = match.group(1)
            section = match.group(2)
            events.append(RequirementExtracted(
                source_commit=sha,
                relevance=RelevanceLevel.HIGH,
                confidence=0.9,
                target_layer=LayerName.PACKET,  # default, refined later
                rfc_section=f"rfc{rfc_num}:{section}",
                requirement_text=match.group(0),
                level=RequirementLevel.MUST,
            ))
        return events

    def _extract_crypto_patterns(self, text: str, sha: str) -> List[SpecEvent]:
        events = []
        seen = set()
        for match in _CRYPTO_RE.finditer(text):
            func_name = match.group(1)
            if func_name in seen:
                continue
            seen.add(func_name)
            kind = "key_establishment" if "key" in func_name.lower() else "encryption"
            events.append(SecurityPropertyAdded(
                source_commit=sha,
                relevance=RelevanceLevel.HIGH,
                confidence=0.7,
                target_layer=LayerName.PROTECTION,
                property_name=func_name,
                property_kind=kind,
            ))
        return events

    def _guess_layer_from_path(self, file_path: str, type_name: str) -> LayerName:
        """Heuristic: guess the Ivy layer from file path and type name."""
        path_lower = file_path.lower()
        name_lower = type_name.lower()
        if "packet" in path_lower or "packet" in name_lower:
            return LayerName.PACKET
        if "frame" in path_lower or "frame" in name_lower:
            return LayerName.FRAME
        if "connection" in path_lower or "conn" in name_lower:
            return LayerName.CONNECTION
        if "crypto" in path_lower or "tls" in path_lower:
            return LayerName.PROTECTION
        if "error" in path_lower or "error" in name_lower:
            return LayerName.ERROR_HANDLING
        return LayerName.TYPES
```

```python
# core/analysis/rfc_reference_extractor.py
"""Extract RFC references from source code comments."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

_RFC_PATTERNS = [
    re.compile(r"RFC\s+(\d{4}),?\s*(?:Section|Sec\.?)\s+([\d.]+)", re.I),
    re.compile(r"rfc(\d{4})(?:\s*[:#]\s*|,\s*(?:section|sec\.?)\s*)([\d.]+)", re.I),
    re.compile(r"See\s+RFC\s+(\d{4})\s+(\d+(?:\.\d+)*)", re.I),
]


@dataclass
class RfcReference:
    rfc_number: str
    section: str
    context: str  # surrounding text


def extract_rfc_references(text: str) -> List[RfcReference]:
    """Extract RFC references from text (source code comments, docstrings)."""
    refs = []
    for pattern in _RFC_PATTERNS:
        for match in pattern.finditer(text):
            refs.append(RfcReference(
                rfc_number=match.group(1),
                section=match.group(2),
                context=text[max(0, match.start() - 40):match.end() + 40].strip(),
            ))
    return refs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_c_analyzer.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/analysis/language_analyzers/ spec-reconstructor/spec_reconstructor/analysis/rfc_reference_extractor.py spec-reconstructor/tests/test_c_analyzer.py
git commit -m "feat(spec-reconstructor): add C language analyzer with struct/enum/state/error/RFC extraction"
```

---

### Task 5: Commit Analyzer (Orchestrator)

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/analysis/commit_analyzer.py`
- Test: `spec-reconstructor/tests/test_commit_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_commit_analyzer.py
"""Tests for the commit analyzer orchestrator."""
from spec_reconstructor.events.spec_events import RelevanceLevel, TypeAdded, SpecEvent
from spec_reconstructor.analysis.commit_analyzer import CommitAnalyzer, CommitAnalysisResult


class TestCommitAnalyzer:
    def test_analyze_c_commit(self):
        diff = """diff --git a/src/quic/types.h b/src/quic/types.h
--- /dev/null
+++ b/src/quic/types.h
@@ -0,0 +1,6 @@
+typedef enum {
+    QUIC_PACKET_INITIAL = 0x00,
+    QUIC_PACKET_HANDSHAKE = 0x02,
+} quic_packet_type_t;
"""
        analyzer = CommitAnalyzer()
        result = analyzer.analyze(
            diff=diff,
            commit_sha="abc123",
            commit_message="feat: add packet types",
        )
        assert isinstance(result, CommitAnalysisResult)
        assert result.relevance.level == RelevanceLevel.HIGH
        assert len(result.events) >= 1
        assert any(isinstance(e, TypeAdded) for e in result.events)

    def test_analyze_docs_commit(self):
        diff = """diff --git a/README.md b/README.md
+++ b/README.md
@@ -1,0 +1,1 @@
+# QUIC Implementation
"""
        analyzer = CommitAnalyzer()
        result = analyzer.analyze(
            diff=diff,
            commit_sha="def456",
            commit_message="docs: update readme",
        )
        assert result.relevance.level in (RelevanceLevel.LOW, RelevanceLevel.NONE)
        assert len(result.events) == 0

    def test_splits_diff_by_file(self):
        diff = """diff --git a/src/types.h b/src/types.h
+++ b/src/types.h
@@ -0,0 +1,3 @@
+typedef enum { A = 0 } my_type_t;
diff --git a/src/connection.c b/src/connection.c
+++ b/src/connection.c
@@ -0,0 +1,3 @@
+    if (conn->state == STATE_IDLE) {
+        conn->state = STATE_ACTIVE;
+    }
"""
        analyzer = CommitAnalyzer()
        result = analyzer.analyze(diff=diff, commit_sha="ghi", commit_message="feat: init")
        # Should have events from both files
        assert len(result.events) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_commit_analyzer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement CommitAnalyzer**

```python
# core/analysis/commit_analyzer.py
"""Commit analyzer — orchestrates diff parsing and SpecEvent extraction.

This is the main entry point for converting a git commit diff into
a list of typed SpecEvents. It splits the diff by file, routes each
file to the appropriate language analyzer, and aggregates results.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from spec_reconstructor.events.spec_events import SpecEvent
from spec_reconstructor.analysis.relevance_classifier import RelevanceResult, classify_relevance
from spec_reconstructor.analysis.language_analyzers import get_analyzer


@dataclass
class CommitAnalysisResult:
    """Result of analyzing a single commit."""
    commit_sha: str
    commit_message: str
    relevance: RelevanceResult
    events: List[SpecEvent] = field(default_factory=list)


_FILE_DIFF_RE = re.compile(
    r"^diff --git a/.+ b/(.+)$",
    re.MULTILINE,
)


class CommitAnalyzer:
    """Orchestrates commit diff analysis into SpecEvents."""

    def analyze(
        self,
        diff: str,
        commit_sha: str,
        commit_message: str,
    ) -> CommitAnalysisResult:
        """Analyze a commit diff and produce SpecEvents."""
        relevance = classify_relevance(diff, commit_message)

        if relevance.level.value in ("low", "none") and relevance.score < 0.2:
            return CommitAnalysisResult(
                commit_sha=commit_sha,
                commit_message=commit_message,
                relevance=relevance,
                events=[],
            )

        file_hunks = self._split_by_file(diff)
        all_events: List[SpecEvent] = []

        for file_path, hunk in file_hunks:
            ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
            analyzer_cls = get_analyzer(ext)
            if analyzer_cls is None:
                continue
            analyzer = analyzer_cls()
            events = analyzer.analyze_hunk(hunk, file_path, commit_sha)
            all_events.extend(events)

        return CommitAnalysisResult(
            commit_sha=commit_sha,
            commit_message=commit_message,
            relevance=relevance,
            events=all_events,
        )

    def _split_by_file(self, diff: str) -> List[tuple[str, str]]:
        """Split a unified diff into (file_path, hunk_text) pairs."""
        matches = list(_FILE_DIFF_RE.finditer(diff))
        if not matches:
            return []
        result = []
        for i, match in enumerate(matches):
            file_path = match.group(1)
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(diff)
            hunk_text = diff[start:end]
            result.append((file_path, hunk_text))
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_commit_analyzer.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/analysis/commit_analyzer.py spec-reconstructor/tests/test_commit_analyzer.py
git commit -m "feat(spec-reconstructor): add commit analyzer orchestrator with file splitting"
```

---

### Task 6: SpecificationState (Event-Sourced State Machine)

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/state/spec_state.py`
- Create: `spec-reconstructor/spec_reconstructor/state/layer_snapshot.py`
- Create: `spec-reconstructor/spec_reconstructor/state/__init__.py`
- Test: `spec-reconstructor/tests/test_spec_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spec_state.py
"""Tests for event-sourced SpecificationState."""
from spec_reconstructor.events.spec_events import (
    FieldDef,
    LayerName,
    RelevanceLevel,
    TypeAdded,
    TypeKind,
    StateTransitionDefined,
    ProtocolErrorDefined,
)
from spec_reconstructor.state.spec_state import SpecificationState
from spec_reconstructor.state.layer_snapshot import LayerSnapshot, LayerStatus


class TestSpecificationState:
    def test_initial_state_all_layers_empty(self):
        state = SpecificationState(protocol="quic")
        for layer in LayerName:
            snapshot = state.get_layer(layer)
            assert snapshot.status == LayerStatus.EMPTY

    def test_apply_type_added_updates_types_layer(self):
        state = SpecificationState(protocol="quic")
        event = TypeAdded(
            source_commit="abc",
            relevance=RelevanceLevel.HIGH,
            confidence=0.9,
            target_layer=LayerName.TYPES,
            type_name="quic_packet_type",
            kind=TypeKind.ENUM,
            fields=[FieldDef(name="initial", type_str="this")],
        )
        state.apply(event)
        snapshot = state.get_layer(LayerName.TYPES)
        assert snapshot.status != LayerStatus.EMPTY
        assert "quic_packet_type" in snapshot.types_defined

    def test_apply_state_transition_updates_connection(self):
        state = SpecificationState(protocol="quic")
        event = StateTransitionDefined(
            source_commit="def",
            relevance=RelevanceLevel.HIGH,
            confidence=0.8,
            target_layer=LayerName.CONNECTION,
            from_state="idle",
            to_state="initial",
            trigger_action="packet_event",
            guards=[],
        )
        state.apply(event)
        snapshot = state.get_layer(LayerName.CONNECTION)
        assert snapshot.status != LayerStatus.EMPTY
        assert any("idle" in t and "initial" in t for t in snapshot.transitions_defined)

    def test_replay_produces_same_state(self):
        events = [
            TypeAdded(
                source_commit="a",
                relevance=RelevanceLevel.HIGH,
                confidence=0.9,
                target_layer=LayerName.TYPES,
                type_name="cid",
                kind=TypeKind.UNINTERPRETED,
                fields=[],
            ),
            ProtocolErrorDefined(
                source_commit="b",
                relevance=RelevanceLevel.MEDIUM,
                confidence=0.8,
                target_layer=LayerName.ERROR_HANDLING,
                error_name="FLOW_CONTROL_ERROR",
                error_code=3,
                description="Flow control violation",
            ),
        ]
        state1 = SpecificationState(protocol="quic")
        for e in events:
            state1.apply(e)

        state2 = SpecificationState(protocol="quic")
        state2.replay(events)

        assert state1.get_layer(LayerName.TYPES).types_defined == state2.get_layer(LayerName.TYPES).types_defined
        assert state1.get_layer(LayerName.ERROR_HANDLING).errors_defined == state2.get_layer(LayerName.ERROR_HANDLING).errors_defined

    def test_event_log_tracks_all_applied_events(self):
        state = SpecificationState(protocol="quic")
        for i in range(3):
            state.apply(TypeAdded(
                source_commit=f"c{i}",
                relevance=RelevanceLevel.MEDIUM,
                confidence=0.5,
                target_layer=LayerName.TYPES,
                type_name=f"t{i}",
                kind=TypeKind.ENUM,
                fields=[],
            ))
        assert len(state.event_log) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_spec_state.py -v`
Expected: FAIL

- [ ] **Step 3: Implement LayerSnapshot**

```python
# core/state/layer_snapshot.py
"""Per-layer state tracking for the Ivy formal model."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from spec_reconstructor.events.spec_events import LayerName


class LayerStatus(str, Enum):
    EMPTY = "empty"
    SKELETON = "skeleton"
    PARTIAL = "partial"
    VERIFIED = "verified"
    FINALIZED = "finalized"


@dataclass
class LayerSnapshot:
    """Snapshot of a single Ivy layer's state."""
    layer: LayerName
    status: LayerStatus = LayerStatus.EMPTY
    ivy_file_path: Optional[str] = None
    last_modified_by: Optional[str] = None  # commit SHA
    types_defined: List[str] = field(default_factory=list)
    relations_defined: List[str] = field(default_factory=list)
    actions_defined: List[str] = field(default_factory=list)
    invariants_defined: List[str] = field(default_factory=list)
    requirements_covered: List[str] = field(default_factory=list)  # rfc bracket-tags
    errors_defined: List[str] = field(default_factory=list)
    transitions_defined: List[str] = field(default_factory=list)  # "from -> to"
    frames_defined: List[str] = field(default_factory=list)
    security_properties: List[str] = field(default_factory=list)

    def add_type(self, name: str, commit: str) -> None:
        if name not in self.types_defined:
            self.types_defined.append(name)
        self.last_modified_by = commit
        self._update_status()

    def add_transition(self, from_state: str, to_state: str, commit: str) -> None:
        t = f"{from_state} -> {to_state}"
        if t not in self.transitions_defined:
            self.transitions_defined.append(t)
        self.last_modified_by = commit
        self._update_status()

    def add_error(self, name: str, commit: str) -> None:
        if name not in self.errors_defined:
            self.errors_defined.append(name)
        self.last_modified_by = commit
        self._update_status()

    def add_frame(self, name: str, commit: str) -> None:
        if name not in self.frames_defined:
            self.frames_defined.append(name)
        self.last_modified_by = commit
        self._update_status()

    def add_requirement(self, tag: str, commit: str) -> None:
        if tag not in self.requirements_covered:
            self.requirements_covered.append(tag)
        self.last_modified_by = commit

    def add_security_property(self, name: str, commit: str) -> None:
        if name not in self.security_properties:
            self.security_properties.append(name)
        self.last_modified_by = commit
        self._update_status()

    def add_action(self, name: str, commit: str) -> None:
        if name not in self.actions_defined:
            self.actions_defined.append(name)
        self.last_modified_by = commit
        self._update_status()

    def _update_status(self) -> None:
        """Promote status based on content count."""
        total = (
            len(self.types_defined)
            + len(self.transitions_defined)
            + len(self.errors_defined)
            + len(self.frames_defined)
            + len(self.actions_defined)
            + len(self.security_properties)
        )
        if total == 0:
            self.status = LayerStatus.EMPTY
        elif total < 3:
            self.status = LayerStatus.SKELETON
        else:
            self.status = LayerStatus.PARTIAL
```

- [ ] **Step 4: Implement SpecificationState**

```python
# core/state/spec_state.py
"""Event-sourced specification state.

All state is derived from the event log. The apply() method dispatches
events to the appropriate layer snapshot. replay() rebuilds state
from a list of events (for resuming from a checkpoint).
"""
from __future__ import annotations

from typing import Dict, List

from spec_reconstructor.events.spec_events import (
    FrameTypeDefined,
    HandlerAdded,
    LayerName,
    PacketStructureDefined,
    ProtocolErrorDefined,
    RequirementExtracted,
    SecurityPropertyAdded,
    SerializationDefined,
    SpecEvent,
    StateTransitionDefined,
    TypeAdded,
)
from spec_reconstructor.state.layer_snapshot import LayerSnapshot, LayerStatus


class SpecificationState:
    """Event-sourced state of the formal specification."""

    def __init__(self, protocol: str) -> None:
        self.protocol = protocol
        self.event_log: List[SpecEvent] = []
        self._layers: Dict[LayerName, LayerSnapshot] = {
            layer: LayerSnapshot(layer=layer) for layer in LayerName
        }

    def get_layer(self, layer: LayerName) -> LayerSnapshot:
        return self._layers[layer]

    def apply(self, event: SpecEvent) -> None:
        """Apply a single event to the state."""
        self.event_log.append(event)
        self._dispatch(event)

    def replay(self, events: List[SpecEvent]) -> None:
        """Replay events to rebuild state from scratch."""
        for event in events:
            self.apply(event)

    def _dispatch(self, event: SpecEvent) -> None:
        """Route an event to the appropriate layer handler."""
        layer = self._layers[event.target_layer]

        if isinstance(event, TypeAdded):
            layer.add_type(event.type_name, event.source_commit)
        elif isinstance(event, StateTransitionDefined):
            layer.add_transition(
                event.from_state, event.to_state, event.source_commit
            )
        elif isinstance(event, ProtocolErrorDefined):
            layer.add_error(event.error_name, event.source_commit)
        elif isinstance(event, FrameTypeDefined):
            layer.add_frame(event.frame_name, event.source_commit)
        elif isinstance(event, RequirementExtracted):
            layer.add_requirement(event.rfc_section, event.source_commit)
        elif isinstance(event, SecurityPropertyAdded):
            layer.add_security_property(
                event.property_name, event.source_commit
            )
        elif isinstance(event, HandlerAdded):
            layer.add_action(event.action_name, event.source_commit)
        elif isinstance(event, PacketStructureDefined):
            layer.add_type(event.packet_name, event.source_commit)
        elif isinstance(event, SerializationDefined):
            layer.add_type(event.format_name, event.source_commit)
```

```python
# spec_reconstructor/state/__init__.py
"""Specification state management."""
from spec_reconstructor.state.spec_state import SpecificationState
from spec_reconstructor.state.layer_snapshot import LayerSnapshot, LayerStatus
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_spec_state.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/state/ spec-reconstructor/tests/test_spec_state.py
git commit -m "feat(spec-reconstructor): add event-sourced SpecificationState with layer snapshots"
```

---

## Phase 2: Event Handlers + Verification

### Task 7: Base Event Handler + Types Handler (Layer 1)

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/events/event_handlers/__init__.py`
- Create: `spec-reconstructor/spec_reconstructor/events/event_handlers/base_handler.py`
- Create: `spec-reconstructor/spec_reconstructor/events/event_handlers/types_handler.py`
- Test: `spec-reconstructor/tests/test_types_handler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_types_handler.py
"""Tests for Types layer event handler — generates Ivy type declarations."""
from spec_reconstructor.events.spec_events import (
    FieldDef,
    LayerName,
    RelevanceLevel,
    TypeAdded,
    TypeKind,
)
from spec_reconstructor.events.event_handlers.types_handler import TypesHandler


class TestTypesHandler:
    def test_generate_enum_declaration(self):
        event = TypeAdded(
            source_commit="abc",
            relevance=RelevanceLevel.HIGH,
            confidence=0.9,
            target_layer=LayerName.TYPES,
            type_name="quic_packet_type",
            kind=TypeKind.ENUM,
            fields=[
                FieldDef(name="initial", type_str="this"),
                FieldDef(name="handshake", type_str="this"),
                FieldDef(name="retry", type_str="this"),
            ],
        )
        handler = TypesHandler(protocol="quic")
        ivy_code = handler.generate(event)
        assert "type quic_packet_type" in ivy_code or "object quic_packet_type" in ivy_code
        assert "initial" in ivy_code
        assert "handshake" in ivy_code

    def test_generate_uninterpreted_type(self):
        event = TypeAdded(
            source_commit="def",
            relevance=RelevanceLevel.HIGH,
            confidence=0.9,
            target_layer=LayerName.TYPES,
            type_name="cid",
            kind=TypeKind.UNINTERPRETED,
            fields=[],
        )
        handler = TypesHandler(protocol="quic")
        ivy_code = handler.generate(event)
        assert "type cid" in ivy_code

    def test_generate_struct_type(self):
        event = TypeAdded(
            source_commit="ghi",
            relevance=RelevanceLevel.HIGH,
            confidence=0.8,
            target_layer=LayerName.TYPES,
            type_name="stream_data",
            kind=TypeKind.STRUCT,
            fields=[
                FieldDef(name="stream_id", type_str="stream_id"),
                FieldDef(name="offset", type_str="stream_pos"),
                FieldDef(name="data", type_str="byte"),
            ],
        )
        handler = TypesHandler(protocol="quic")
        ivy_code = handler.generate(event)
        assert "stream_data" in ivy_code
        assert "stream_id" in ivy_code

    def test_target_file_path(self):
        handler = TypesHandler(protocol="quic")
        assert handler.target_file() == "quic_types.ivy"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_types_handler.py -v`
Expected: FAIL

- [ ] **Step 3: Implement base handler and types handler**

```python
# core/events/event_handlers/base_handler.py
"""Abstract base for per-layer event handlers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from spec_reconstructor.events.spec_events import SpecEvent


class BaseEventHandler(ABC):
    """Base class for event handlers that generate Ivy code."""

    def __init__(self, protocol: str) -> None:
        self.protocol = protocol

    @abstractmethod
    def generate(self, event: SpecEvent) -> str:
        """Generate Ivy code from an event. Returns Ivy source text."""

    @abstractmethod
    def target_file(self) -> str:
        """Return the target .ivy file name for this handler's layer."""
```

```python
# core/events/event_handlers/types_handler.py
"""Types layer (Layer 1) event handler.

Generates Ivy type declarations: enumerations, uninterpreted types,
and struct-like object types.
"""
from __future__ import annotations

from spec_reconstructor.events.spec_events import FieldDef, SpecEvent, TypeAdded, TypeKind
from spec_reconstructor.events.event_handlers.base_handler import BaseEventHandler


class TypesHandler(BaseEventHandler):
    """Generates Ivy type declarations for Layer 1."""

    def target_file(self) -> str:
        return f"{self.protocol}_types.ivy"

    def generate(self, event: SpecEvent) -> str:
        if not isinstance(event, TypeAdded):
            return ""
        if event.kind == TypeKind.ENUM:
            return self._generate_enum(event)
        elif event.kind == TypeKind.UNINTERPRETED:
            return self._generate_uninterpreted(event)
        elif event.kind == TypeKind.STRUCT:
            return self._generate_struct(event)
        elif event.kind == TypeKind.BIT_VECTOR:
            return self._generate_bitvector(event)
        return ""

    def _generate_enum(self, event: TypeAdded) -> str:
        members = [f.name for f in event.fields]
        if not members:
            return f"type {event.type_name}"
        variants = "\n".join(f"    variant {m}" for m in members)
        return (
            f"object {event.type_name} = {{\n"
            f"    type this = {{" + ", ".join(members) + "}\n"
            f"}}"
        )

    def _generate_uninterpreted(self, event: TypeAdded) -> str:
        return f"type {event.type_name}"

    def _generate_struct(self, event: TypeAdded) -> str:
        fields_str = "\n".join(
            f"    individual {f.name} : {f.type_str}"
            for f in event.fields
        )
        return (
            f"object {event.type_name} = {{\n"
            f"{fields_str}\n"
            f"}}"
        )

    def _generate_bitvector(self, event: TypeAdded) -> str:
        return f"type {event.type_name}  # bit vector"
```

```python
# core/events/event_handlers/__init__.py
"""Event handler registry."""
from spec_reconstructor.events.spec_events import LayerName
from spec_reconstructor.events.event_handlers.base_handler import BaseEventHandler
from spec_reconstructor.events.event_handlers.types_handler import TypesHandler

_HANDLER_REGISTRY = {
    LayerName.TYPES: TypesHandler,
}


def get_handler(layer: LayerName, protocol: str) -> BaseEventHandler | None:
    """Get the handler for a given layer."""
    cls = _HANDLER_REGISTRY.get(layer)
    if cls:
        return cls(protocol=protocol)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_types_handler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/events/event_handlers/ spec-reconstructor/tests/test_types_handler.py
git commit -m "feat(spec-reconstructor): add base event handler + Types layer handler"
```

---

### Task 8: Connection Handler (Layer 7) + Frame Handler (Layer 4)

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/events/event_handlers/connection_handler.py`
- Create: `spec-reconstructor/spec_reconstructor/events/event_handlers/frame_handler.py`
- Test: `spec-reconstructor/tests/test_connection_handler.py`
- Test: `spec-reconstructor/tests/test_frame_handler.py`

- [ ] **Step 1: Write failing tests for both handlers**

```python
# tests/test_connection_handler.py
from spec_reconstructor.events.spec_events import *
from spec_reconstructor.events.event_handlers.connection_handler import ConnectionHandler

class TestConnectionHandler:
    def test_generate_state_transition(self):
        event = StateTransitionDefined(
            source_commit="abc", relevance=RelevanceLevel.HIGH,
            confidence=0.8, target_layer=LayerName.CONNECTION,
            from_state="idle", to_state="initial",
            trigger_action="packet_event", guards=["pkt.ptype = initial"],
        )
        handler = ConnectionHandler(protocol="quic")
        ivy = handler.generate(event)
        assert "relation" in ivy or "conn_" in ivy
        assert "idle" in ivy and "initial" in ivy

    def test_target_file(self):
        handler = ConnectionHandler(protocol="quic")
        assert handler.target_file() == "quic_connection.ivy"
```

```python
# tests/test_frame_handler.py
from spec_reconstructor.events.spec_events import *
from spec_reconstructor.events.event_handlers.frame_handler import FrameHandler

class TestFrameHandler:
    def test_generate_frame_variant(self):
        event = FrameTypeDefined(
            source_commit="abc", relevance=RelevanceLevel.HIGH,
            confidence=0.85, target_layer=LayerName.FRAME,
            frame_name="stream_frame",
            fields=[FieldDef(name="stream_id", type_str="stream_id"),
                    FieldDef(name="offset", type_str="stream_pos")],
        )
        handler = FrameHandler(protocol="quic")
        ivy = handler.generate(event)
        assert "stream_frame" in ivy
        assert "stream_id" in ivy

    def test_target_file(self):
        handler = FrameHandler(protocol="quic")
        assert handler.target_file() == "quic_frame.ivy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_connection_handler.py tests/test_frame_handler.py -v`
Expected: FAIL

- [ ] **Step 3: Implement both handlers**

```python
# core/events/event_handlers/connection_handler.py
"""Connection layer (Layer 7) event handler.

Generates Ivy state machine relations, predicates, and transition
monitors from StateTransitionDefined events.
"""
from __future__ import annotations

from spec_reconstructor.events.spec_events import SpecEvent, StateTransitionDefined
from spec_reconstructor.events.event_handlers.base_handler import BaseEventHandler


class ConnectionHandler(BaseEventHandler):
    def target_file(self) -> str:
        return f"{self.protocol}_connection.ivy"

    def generate(self, event: SpecEvent) -> str:
        if not isinstance(event, StateTransitionDefined):
            return ""
        from_s = event.from_state.lower().replace("conn_state_", "").replace("state_", "")
        to_s = event.to_state.lower().replace("conn_state_", "").replace("state_", "")

        lines = [
            f"# State transition: {from_s} -> {to_s}",
            f"relation conn_{from_s}(C:cid)",
            f"relation conn_{to_s}(C:cid)",
            "",
            f"after init {{",
            f"    conn_{from_s}(C) := false;",
            f"    conn_{to_s}(C) := false;",
            f"}}",
        ]
        if event.trigger_action:
            guard = event.guards[0] if event.guards else ""
            guard_clause = f" & {guard}" if guard else ""
            lines.extend([
                "",
                f"after {event.trigger_action}(src:ip.endpoint, dst:ip.endpoint, pkt:quic_packet) {{",
                f"    if conn_{from_s}(the_cid){guard_clause} {{",
                f"        conn_{from_s}(the_cid) := false;",
                f"        conn_{to_s}(the_cid) := true;",
                f"    }}",
                f"}}",
            ])
        return "\n".join(lines)
```

```python
# core/events/event_handlers/frame_handler.py
"""Frame layer (Layer 4) event handler.

Generates Ivy frame object variants with fields from
FrameTypeDefined events.
"""
from __future__ import annotations

from spec_reconstructor.events.spec_events import FrameTypeDefined, SpecEvent
from spec_reconstructor.events.event_handlers.base_handler import BaseEventHandler


class FrameHandler(BaseEventHandler):
    def target_file(self) -> str:
        return f"{self.protocol}_frame.ivy"

    def generate(self, event: SpecEvent) -> str:
        if not isinstance(event, FrameTypeDefined):
            return ""
        fields_str = "\n".join(
            f"    individual {f.name} : {f.type_str}"
            for f in event.fields
        )
        return (
            f"object frame.{event.frame_name} = {{\n"
            f"{fields_str}\n"
            f"}}"
        )
```

- [ ] **Step 4: Register handlers and run tests**

Update `core/events/event_handlers/__init__.py` to add:
```python
from spec_reconstructor.events.event_handlers.connection_handler import ConnectionHandler
from spec_reconstructor.events.event_handlers.frame_handler import FrameHandler

_HANDLER_REGISTRY = {
    LayerName.TYPES: TypesHandler,
    LayerName.CONNECTION: ConnectionHandler,
    LayerName.FRAME: FrameHandler,
}
```

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_connection_handler.py tests/test_frame_handler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/events/event_handlers/ spec-reconstructor/tests/test_connection_handler.py spec-reconstructor/tests/test_frame_handler.py
git commit -m "feat(spec-reconstructor): add Connection (Layer 7) and Frame (Layer 4) handlers"
```

---

### Task 9: Question Generator (Interview System Core)

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/interview/question_generator.py`
- Create: `spec-reconstructor/spec_reconstructor/interview/__init__.py`
- Test: `spec-reconstructor/tests/test_question_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_question_generator.py
"""Tests for confidence-based interview question generation."""
from spec_reconstructor.events.spec_events import *
from spec_reconstructor.interview.question_generator import (
    InterviewQuestion,
    QuestionCategory,
    generate_questions,
)


class TestQuestionGeneration:
    def test_high_confidence_no_questions(self):
        event = TypeAdded(
            source_commit="abc", relevance=RelevanceLevel.HIGH,
            confidence=0.95, target_layer=LayerName.TYPES,
            type_name="cid", kind=TypeKind.UNINTERPRETED, fields=[],
        )
        questions = generate_questions([event])
        assert len(questions) == 0  # auto-apply at >=0.9

    def test_medium_confidence_generates_question(self):
        event = StateTransitionDefined(
            source_commit="def", relevance=RelevanceLevel.HIGH,
            confidence=0.6, target_layer=LayerName.CONNECTION,
            from_state="idle", to_state="initial",
            trigger_action="packet_event", guards=[],
        )
        questions = generate_questions([event])
        assert len(questions) >= 1
        assert questions[0].category in (QuestionCategory.CLARIFICATION, QuestionCategory.INTENT)

    def test_low_confidence_skipped(self):
        event = TypeAdded(
            source_commit="ghi", relevance=RelevanceLevel.LOW,
            confidence=0.2, target_layer=LayerName.TYPES,
            type_name="internal_buf", kind=TypeKind.STRUCT, fields=[],
        )
        questions = generate_questions([event])
        assert len(questions) == 0  # below threshold

    def test_question_has_required_fields(self):
        event = HandlerAdded(
            source_commit="jkl", relevance=RelevanceLevel.HIGH,
            confidence=0.5, target_layer=LayerName.ENTITY_BEHAVIOR,
            action_name="packet_event", handler_kind=HandlerKind.AFTER,
            parameters=[FieldDef(name="pkt", type_str="quic_packet")],
            body_hints=[],
        )
        questions = generate_questions([event])
        assert len(questions) >= 1
        q = questions[0]
        assert isinstance(q, InterviewQuestion)
        assert q.event_id == event.event_id
        assert q.source_commit == "jkl"
        assert len(q.text) > 10

    def test_rfc_requirement_generates_design_question(self):
        event = RequirementExtracted(
            source_commit="mno", relevance=RelevanceLevel.HIGH,
            confidence=0.6, target_layer=LayerName.PACKET,
            rfc_section="rfc9000:17.2.2",
            requirement_text="Initial packets MUST include version",
            level=RequirementLevel.MUST,
        )
        questions = generate_questions([event])
        assert len(questions) >= 1
        assert questions[0].category == QuestionCategory.DESIGN
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_question_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Implement question generator**

```python
# core/interview/question_generator.py
"""Confidence-based interview question generation.

Questions are generated for events with confidence below the auto-apply
threshold (0.9). The category and text are derived from the event type
and its fields.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from spec_reconstructor.events.spec_events import (
    FrameTypeDefined,
    HandlerAdded,
    ProtocolErrorDefined,
    RequirementExtracted,
    SecurityPropertyAdded,
    SpecEvent,
    StateTransitionDefined,
    TypeAdded,
)

AUTO_APPLY_THRESHOLD = 0.9
QUESTION_THRESHOLD = 0.4
SKIP_THRESHOLD = 0.4


class QuestionCategory(str, Enum):
    INTENT = "intent"
    CLARIFICATION = "clarification"
    DESIGN = "design"
    VALIDATION = "validation"
    BOUNDARY = "boundary"


@dataclass
class InterviewQuestion:
    """A question to ask the developer about a low-confidence event."""
    question_id: str
    event_id: str
    source_commit: str
    category: QuestionCategory
    text: str
    context: str = ""


def generate_questions(events: List[SpecEvent]) -> List[InterviewQuestion]:
    """Generate interview questions for events below auto-apply threshold."""
    questions: List[InterviewQuestion] = []
    for event in events:
        if event.confidence >= AUTO_APPLY_THRESHOLD:
            continue
        if event.confidence < SKIP_THRESHOLD:
            continue
        q = _question_for_event(event)
        if q:
            questions.append(q)
    return questions


def _question_for_event(event: SpecEvent) -> InterviewQuestion | None:
    """Generate a question for a specific event based on its type."""
    if isinstance(event, TypeAdded):
        return _type_question(event)
    elif isinstance(event, StateTransitionDefined):
        return _transition_question(event)
    elif isinstance(event, HandlerAdded):
        return _handler_question(event)
    elif isinstance(event, RequirementExtracted):
        return _requirement_question(event)
    elif isinstance(event, ProtocolErrorDefined):
        return _error_question(event)
    elif isinstance(event, FrameTypeDefined):
        return _frame_question(event)
    elif isinstance(event, SecurityPropertyAdded):
        return _security_question(event)
    return None


def _type_question(event: TypeAdded) -> InterviewQuestion:
    return InterviewQuestion(
        question_id=f"q-{event.source_commit[:7]}-{event.event_id[:8]}",
        event_id=event.event_id,
        source_commit=event.source_commit,
        category=QuestionCategory.INTENT,
        text=(
            f"Commit {event.source_commit[:7]} adds type `{event.type_name}` "
            f"({event.kind.value}). Is this a protocol-level type that should "
            f"appear in the formal spec, or an implementation-internal type?"
        ),
    )


def _transition_question(event: StateTransitionDefined) -> InterviewQuestion:
    return InterviewQuestion(
        question_id=f"q-{event.source_commit[:7]}-{event.event_id[:8]}",
        event_id=event.event_id,
        source_commit=event.source_commit,
        category=QuestionCategory.CLARIFICATION,
        text=(
            f"State transition detected: `{event.from_state}` → `{event.to_state}` "
            f"on `{event.trigger_action}`. Is this the complete transition, or are "
            f"there intermediate states?"
        ),
    )


def _handler_question(event: HandlerAdded) -> InterviewQuestion:
    params = ", ".join(f"{p.name}:{p.type_str}" for p in event.parameters)
    return InterviewQuestion(
        question_id=f"q-{event.source_commit[:7]}-{event.event_id[:8]}",
        event_id=event.event_id,
        source_commit=event.source_commit,
        category=QuestionCategory.INTENT,
        text=(
            f"Handler `{event.action_name}({params})` detected as `{event.handler_kind.value}` "
            f"monitor. What invariant does this handler maintain? Which RFC section does it implement?"
        ),
    )


def _requirement_question(event: RequirementExtracted) -> InterviewQuestion:
    return InterviewQuestion(
        question_id=f"q-{event.source_commit[:7]}-{event.event_id[:8]}",
        event_id=event.event_id,
        source_commit=event.source_commit,
        category=QuestionCategory.DESIGN,
        text=(
            f"RFC reference `{event.rfc_section}` found: \"{event.requirement_text}\". "
            f"Is this a {event.level.value} requirement? Which Ivy layer should model it?"
        ),
    )


def _error_question(event: ProtocolErrorDefined) -> InterviewQuestion:
    code_str = f" (0x{event.error_code:02x})" if event.error_code is not None else ""
    return InterviewQuestion(
        question_id=f"q-{event.source_commit[:7]}-{event.event_id[:8]}",
        event_id=event.event_id,
        source_commit=event.source_commit,
        category=QuestionCategory.BOUNDARY,
        text=(
            f"Error code `{event.error_name}`{code_str} detected. "
            f"Should the Ivy model treat this as a MUST NOT violation (CONNECTION_CLOSE) "
            f"or a soft SHOULD?"
        ),
    )


def _frame_question(event: FrameTypeDefined) -> InterviewQuestion:
    fields = ", ".join(f.name for f in event.fields)
    return InterviewQuestion(
        question_id=f"q-{event.source_commit[:7]}-{event.event_id[:8]}",
        event_id=event.event_id,
        source_commit=event.source_commit,
        category=QuestionCategory.DESIGN,
        text=(
            f"Frame type `{event.frame_name}` with fields [{fields}] detected. "
            f"Which RFC section defines this frame format?"
        ),
    )


def _security_question(event: SecurityPropertyAdded) -> InterviewQuestion:
    return InterviewQuestion(
        question_id=f"q-{event.source_commit[:7]}-{event.event_id[:8]}",
        event_id=event.event_id,
        source_commit=event.source_commit,
        category=QuestionCategory.DESIGN,
        text=(
            f"Crypto function `{event.property_name}` ({event.property_kind}) detected. "
            f"Which RFC section covers this? Should the Ivy model include it in the "
            f"Protection or Security layer?"
        ),
    )
```

```python
# spec_reconstructor/interview/__init__.py
"""Interview system for developer questioning."""
from spec_reconstructor.interview.question_generator import (
    InterviewQuestion,
    QuestionCategory,
    generate_questions,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_question_generator.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/interview/ spec-reconstructor/tests/test_question_generator.py
git commit -m "feat(spec-reconstructor): add confidence-based interview question generator"
```

---

### Task 10: Answer Processor + Question Store

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/interview/answer_processor.py`
- Create: `spec-reconstructor/spec_reconstructor/interview/question_store.py`
- Test: `spec-reconstructor/tests/test_answer_processor.py`

- [ ] **Step 1: Write the failing test for answer processor**

```python
# tests/test_answer_processor.py
"""Tests for answer processing — maps developer answers to Ivy updates."""
from spec_reconstructor.interview.answer_processor import (
    AnswerResult,
    ConfidenceLevel,
    process_answer,
)
from spec_reconstructor.interview.question_generator import InterviewQuestion, QuestionCategory


class TestAnswerProcessor:
    def test_rfc_answer_produces_bracket_tag(self):
        question = InterviewQuestion(
            question_id="q-abc1234-001",
            event_id="evt-001",
            source_commit="abc1234",
            category=QuestionCategory.DESIGN,
            text="Which RFC section does this implement?",
        )
        result = process_answer(question, "RFC 9000, Section 17.2.2")
        assert result.confidence == ConfidenceLevel.CONFIRMED
        assert "rfc9000:17.2.2" in result.bracket_tag

    def test_skip_answer(self):
        question = InterviewQuestion(
            question_id="q-def5678-001",
            event_id="evt-002",
            source_commit="def5678",
            category=QuestionCategory.INTENT,
            text="What invariant does this maintain?",
        )
        result = process_answer(question, "skip")
        assert result.confidence == ConfidenceLevel.INFERRED

    def test_idk_answer(self):
        question = InterviewQuestion(
            question_id="q-ghi9012-001",
            event_id="evt-003",
            source_commit="ghi9012",
            category=QuestionCategory.CLARIFICATION,
            text="Is this transition complete?",
        )
        result = process_answer(question, "idk")
        assert result.confidence == ConfidenceLevel.UNCERTAIN
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_answer_processor.py -v`
Expected: FAIL

- [ ] **Step 3: Implement answer processor and question store**

```python
# core/interview/answer_processor.py
"""Maps developer answers to Ivy spec updates."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from spec_reconstructor.interview.question_generator import InterviewQuestion, QuestionCategory


class ConfidenceLevel(str, Enum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


@dataclass
class AnswerResult:
    """Result of processing a developer's answer."""
    question_id: str
    confidence: ConfidenceLevel
    bracket_tag: str = ""
    ivy_update: str = ""
    notes: str = ""


_RFC_RE = re.compile(r"RFC\s*(\d{4}),?\s*(?:Section|Sec\.?)\s*([\d.]+)", re.I)


def process_answer(question: InterviewQuestion, answer: str) -> AnswerResult:
    """Process a developer's answer and return an Ivy update action."""
    answer_stripped = answer.strip().lower()

    if answer_stripped == "skip":
        return AnswerResult(
            question_id=question.question_id,
            confidence=ConfidenceLevel.INFERRED,
            notes="Developer skipped — using inferred assertion",
        )
    if answer_stripped in ("idk", "i don't know", "not sure"):
        return AnswerResult(
            question_id=question.question_id,
            confidence=ConfidenceLevel.UNCERTAIN,
            notes="Developer uncertain — flagged for re-questioning",
        )

    # Extract RFC references from the answer
    bracket_tag = ""
    rfc_match = _RFC_RE.search(answer)
    if rfc_match:
        bracket_tag = f"rfc{rfc_match.group(1)}:{rfc_match.group(2)}"

    return AnswerResult(
        question_id=question.question_id,
        confidence=ConfidenceLevel.CONFIRMED,
        bracket_tag=bracket_tag,
        ivy_update=answer,
        notes="Developer confirmed",
    )
```

```python
# core/interview/question_store.py
"""YAML persistence for interview questions and answers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from spec_reconstructor.interview.question_generator import InterviewQuestion


class QuestionStore:
    """Persists interview questions/answers per commit in YAML."""

    def __init__(self, interviews_dir: Path) -> None:
        self._dir = interviews_dir

    def save_questions(
        self, commit_sha: str, questions: List[InterviewQuestion]
    ) -> None:
        """Save questions for a commit."""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{commit_sha[:7]}.yaml"
        data = {
            "commit": commit_sha,
            "questions": [
                {
                    "id": q.question_id,
                    "event_id": q.event_id,
                    "category": q.category.value,
                    "text": q.text,
                    "answer": None,
                    "status": "pending",
                }
                for q in questions
            ],
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def load_questions(self, commit_sha: str) -> Optional[Dict[str, Any]]:
        """Load questions for a commit."""
        path = self._dir / f"{commit_sha[:7]}.yaml"
        if not path.exists():
            return None
        with open(path) as f:
            return yaml.safe_load(f)

    def update_answer(
        self, commit_sha: str, question_id: str, answer: str
    ) -> None:
        """Record an answer for a question."""
        data = self.load_questions(commit_sha)
        if not data:
            return
        for q in data["questions"]:
            if q["id"] == question_id:
                q["answer"] = answer
                q["status"] = "answered"
                break
        path = self._dir / f"{commit_sha[:7]}.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def pending_questions(self) -> List[Dict[str, Any]]:
        """Return all unanswered questions across all commits."""
        pending = []
        if not self._dir.exists():
            return pending
        for path in sorted(self._dir.glob("*.yaml")):
            with open(path) as f:
                data = yaml.safe_load(f)
            if data and "questions" in data:
                for q in data["questions"]:
                    if q.get("status") == "pending":
                        q["commit"] = data["commit"]
                        pending.append(q)
        return pending
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/test_answer_processor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/interview/ spec-reconstructor/tests/test_answer_processor.py
git commit -m "feat(spec-reconstructor): add answer processor and question store"
```

---

### Task 11: Verification Loop

**Files:**
- Create: `spec-reconstructor/spec_reconstructor/verification/verification_loop.py`
- Create: `spec-reconstructor/spec_reconstructor/verification/__init__.py`

- [ ] **Step 1: Implement verification loop**

```python
# core/verification/verification_loop.py
"""Verification pipeline — wraps ivy_verify, ivy_coverage, ivy_quality.

In Claude Code plugin mode, these are invoked via MCP tools.
In SDK headless mode, these call the ivy-lsp tools directly.
The interface is the same: file paths in, results out.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional


class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class VerificationResult:
    """Result of running the verification pipeline on an Ivy file."""
    file_path: str
    status: VerificationStatus
    diagnostics: List[str]
    coverage_delta: Optional[float] = None
    error_message: str = ""


class VerificationLoop:
    """Orchestrates ivy_verify -> ivy_coverage -> ivy_quality.

    This class defines the interface. The actual MCP tool calls
    are injected via the `tool_runner` callback, which differs
    between plugin mode (MCP) and SDK mode (direct CLI).
    """

    def __init__(self, tool_runner=None, max_fix_attempts: int = 3):
        self._tool_runner = tool_runner
        self._max_fix_attempts = max_fix_attempts

    def verify_file(self, ivy_file: Path) -> VerificationResult:
        """Run verification pipeline on a single .ivy file."""
        if self._tool_runner is None:
            return VerificationResult(
                file_path=str(ivy_file),
                status=VerificationStatus.SKIP,
                diagnostics=["No tool runner configured — skipping verification"],
            )

        # Step 1: Structural diagnostics (fast)
        diag_result = self._tool_runner(
            "ivy_diagnostics",
            {"file": str(ivy_file), "mode": "structural"},
        )

        # Step 2: Formal verification
        verify_result = self._tool_runner(
            "ivy_verify",
            {"file": str(ivy_file)},
        )

        status = (
            VerificationStatus.PASS
            if verify_result.get("success", False)
            else VerificationStatus.FAIL
        )
        diagnostics = verify_result.get("diagnostics", [])
        if diag_result.get("diagnostics"):
            diagnostics = diag_result["diagnostics"] + diagnostics

        return VerificationResult(
            file_path=str(ivy_file),
            status=status,
            diagnostics=diagnostics,
            error_message=verify_result.get("error", ""),
        )
```

```python
# spec_reconstructor/verification/__init__.py
"""Verification pipeline."""
from spec_reconstructor.verification.verification_loop import (
    VerificationLoop,
    VerificationResult,
    VerificationStatus,
)
```

- [ ] **Step 2: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/verification/
git commit -m "feat(spec-reconstructor): add verification loop with MCP tool interface"
```

---

## Phase 3: Extend panther-ivy-plugin

> These tasks add reconstruction components to the EXISTING panther-ivy-plugin.
> Path prefix: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/`

### Task 12: New Agents in panther-ivy-plugin

**Files:**
- Create: `{plugin}/agents/reconstructor.md` — main reconstruction orchestrator
- Create: `{plugin}/agents/commit-analyst.md` — commit analysis specialist

- [ ] **Step 1: Write reconstructor agent definition**

Main orchestrator agent with YAML frontmatter. Dispatches to `spec_reconstructor` Python modules for analysis, uses existing `spec-analyst`/`model-reviewer` for verification.

- [ ] **Step 2: Write commit-analyst agent definition**

Specialist for analyzing diffs and generating SpecEvents. Invokes `spec_reconstructor.analysis.commit_analyzer`.

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/
git commit -m "feat(panther-ivy-plugin): add reconstructor and commit-analyst agents"
```

---

### Task 13: New Commands in panther-ivy-plugin

**Files:**
- Create: `{plugin}/commands/reconstruct-init.md` — start retroactive reconstruction
- Create: `{plugin}/commands/reconstruct-status.md` — show progress
- Create: `{plugin}/commands/reconstruct-resume.md` — resume from checkpoint
- Create: `{plugin}/commands/reconstruct-answer.md` — answer pending questions

- [ ] **Step 1: Write /reconstruct-init command**

Entry point for starting retroactive reconstruction. Invokes `spec_reconstructor` via Python or dispatches reconstructor agent.

- [ ] **Step 2: Write /reconstruct-status command**

Shows progress: commits processed, events generated, coverage, pending questions.

- [ ] **Step 3: Write /reconstruct-resume command**

Resume from last checkpoint (reads `.panther-spec/events.jsonl`).

- [ ] **Step 4: Write /reconstruct-answer command**

Process developer answers to pending interview questions.

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/
git commit -m "feat(panther-ivy-plugin): add /reconstruct-init, /status, /resume, /answer commands"
```

---

### Task 14: Reconstruction Workflow Skill + Hooks in panther-ivy-plugin

**Files:**
- Create: `{plugin}/skills/reconstruction-workflow/SKILL.md`
- Create: `{plugin}/skills/commit-analysis/SKILL.md`
- Modify: `{plugin}/hooks/hooks.json` — add reconstruction-related hooks

- [ ] **Step 1: Write reconstruction-workflow skill**

4-phase workflow: SCAN → ANALYZE → INTERVIEW → VERIFY, adapted from ivy-workflow-orchestrator. References `spec_reconstructor` Python modules.

- [ ] **Step 2: Write commit-analysis skill**

Guidance for interpreting diff output and mapping to Ivy layers.

- [ ] **Step 3: Add reconstruction hooks to hooks.json**

- PostToolUse hook for `spec_reconstructor` analysis results → interview checkpoint
- SessionStart hook to detect `.panther-spec/` directory and load reconstruction state

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/
git commit -m "feat(panther-ivy-plugin): add reconstruction-workflow skill and hooks"
```

---

## Phase 4: SDK + CI/CD

### Task 14: Agent SDK Headless Driver

**Files:**
- Create: `spec-reconstructor/sdk/app.py`
- Create: `spec-reconstructor/sdk/__init__.py`
- Create: `spec-reconstructor/sdk/config.py`

- [ ] **Step 1: Implement CLI entry point**

```python
# sdk/app.py — CLI with subcommands: analyze, post-questions, process-answer, report
```

- [ ] **Step 2: Implement config loading from .panther-spec/config.yaml**

- [ ] **Step 3: Test CLI invocation**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m sdk.app --help`
Expected: Shows usage with subcommands

- [ ] **Step 4: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/sdk/
git commit -m "feat(spec-reconstructor): add Agent SDK headless CLI driver"
```

---

### Task 15: GitHub Adapter

**Files:**
- Create: `spec-reconstructor/sdk/github_adapter.py`

- [ ] **Step 1: Implement PR comment posting**

Uses `gh api` to post/read PR review comments.

- [ ] **Step 2: Implement answer parsing from comments**

Parses `A<N>: <answer>` format from PR comment replies.

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/sdk/github_adapter.py
git commit -m "feat(spec-reconstructor): add GitHub adapter for PR comment Q&A"
```

---

### Task 16: GitHub Action + GitLab CI Templates

**Files:**
- Create: `spec-reconstructor/actions/github/action.yml`
- Create: `spec-reconstructor/actions/gitlab/.gitlab-ci.yml`

- [ ] **Step 1: Write GitHub Action definition**

- [ ] **Step 2: Write GitLab CI template**

- [ ] **Step 3: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/actions/
git commit -m "feat(spec-reconstructor): add GitHub Action and GitLab CI templates"
```

---

## Phase 5: Integration Testing

### Task 17: End-to-End Test with Sample Commits

**Files:**
- Create: `spec-reconstructor/tests/conftest.py` (fixtures with real picoquic-style diffs)
- Create: `spec-reconstructor/tests/test_end_to_end.py`

- [ ] **Step 1: Create fixtures with 5 realistic C commit diffs**

Cover: type definition, packet struct, state machine, error codes, crypto function.

- [ ] **Step 2: Write E2E test: analyze 5 commits → verify event log → verify state**

- [ ] **Step 3: Write E2E test: generate questions → verify categories and counts**

- [ ] **Step 4: Run full test suite**

Run: `cd panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor/tests/
git commit -m "test(spec-reconstructor): add end-to-end integration tests with realistic diffs"
```

---

## Verification

### How to test end-to-end

```bash
SPEC_ROOT=panther/plugins/services/testers/panther_ivy/submodules/spec-reconstructor
```

1. **Unit tests:**
   ```bash
   cd $SPEC_ROOT
   python -m pytest tests/ -v --cov=spec_reconstructor --cov-report=term-missing
   ```

2. **Plugin validation (panther-ivy-plugin already installed):**
   ```bash
   # The reconstruction commands are part of panther-ivy-plugin
   # Run /reconstruct-init on a protocol repo
   /reconstruct-init
   /reconstruct-status
   ```

3. **SDK validation:**
   ```bash
   cd $SPEC_ROOT
   python -m sdk.app analyze --mode retroactive \
     --repo /path/to/picoquic \
     --commit-range HEAD~10..HEAD \
     --output-dir /tmp/test-panther-spec
   # Verify .panther-spec/ is populated
   ls /tmp/test-panther-spec/.panther-spec/
   ```

4. **Ivy verification (requires ivy-lsp):**
   ```bash
   # After generating formal spec, verify it compiles
   ivy_check /tmp/test-panther-spec/formal-spec/quic_types.ivy
   ```
