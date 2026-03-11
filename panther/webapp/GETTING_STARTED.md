# Getting Started: PANTHER Web Dashboard

Muhammad, this guide gets you from zero to productive in your first day. Follow it step by step.

## Prerequisites

- Python 3.10+ installed
- git
- A modern browser (Chrome or Firefox)
- Docker (only needed to run real experiments -- not required for webapp development)

## Step 1: Setup (30 minutes)

```bash
# Clone the repository
git clone https://github.com/ElNiak/PANTHER.git
cd PANTHER

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install PANTHER with web dependencies
pip install -e ".[web,dev]"
```

Verify:
```bash
panther --help          # Should show CLI commands including 'web'
python -c "import nicegui; print(nicegui.__version__)"   # Should print 3.x
python -c "from panther.webapp.components.pydantic_form import PydanticForm; print('OK')"  # Should print OK
```

## Step 2: Run the Webapp (5 minutes)

```bash
panther web --reload
```

Open `http://localhost:8080`. You should see a sidebar with 5 navigation links.

Click through every page and note the current status:

| Page | Route | Status |
|------|-------|--------|
| Dashboard | `/` | Working -- stat cards, quick actions |
| Config Builder | `/config` | Skeleton -- placeholder forms, YAML editor works |
| Experiments | `/experiments` | Skeleton -- launch works, monitoring to build |
| Results | `/results` | Working -- table with row-click detail view |
| Plugins | `/plugins` | Working -- plugin table grouped by type |

## Step 3: Understand the Code (1 hour)

Read these files in this order:

### Webapp files (your main working area):

1. **`panther/webapp/app.py`** -- Application factory. Registers all 5 pages.
2. **`panther/webapp/components/layout.py`** -- Shared sidebar, header. Every page uses this.
3. **`panther/webapp/pages/plugins.py`** -- Simplest complete page. Shows the pattern: import service -> call method -> render.
4. **`panther/webapp/services/plugin_service.py`** -- Simplest service. Wraps `PluginManager`.
5. **`panther/webapp/pages/config_builder.py`** -- Main feature to build. Has placeholder forms and a YAML editor.

### Core PANTHER files (read, rarely edit):

6. **`panther/config/core/models/global_config.py`** -- Pydantic models (GlobalConfig, LoggingConfig, DockerConfig, PathsConfig). These are what the config builder forms generate UIs for.
7. **`panther/core/experiment_manager.py`** -- Central orchestrator. Read `__init__` carefully (lines 136-219) to understand the constructor signature.
8. **`panther/core/observer/impl/gui_observer.py`** -- GUIObserver base class. Your WebObserver will subclass this.
9. **`panther/core/reporting/status_collector.py`** -- ExperimentSummary, TestResult, ServiceHealthSummary. The results page parses these.

## Step 4: PydanticForm Exploration (1 hour)

The config builder uses `PydanticForm` — a custom component that recursively
renders any Pydantic `BaseModel` as editable NiceGUI widgets.

```python
from panther.webapp.components.pydantic_form import PydanticForm, FormConfig
from panther.config.core.models.global_config import LoggingConfig

# PydanticForm handles nested models, enums, Optional fields, etc. automatically
form = PydanticForm(LoggingConfig, config=FormConfig(section_style="card"))
data = form.get_value()  # Returns validated dict
form.set_value({"level": "DEBUG"})
```

Run `panther web --reload` and navigate to `/config` to see PydanticForm in action.

See `panther/webapp/components/pydantic_form.py` for the implementation and
`tests/integration/test_pydantic_form_browser.py` for comprehensive tests.

## Step 5: Verify Bug Fixes (15 minutes)

The scaffold bugs have been fixed in this commit. Verify they work:

1. **Results row-click**: Navigate to `/results`. Click a row. The detail panel should appear below the table.
2. **Config service**: The config service now resolves paths relative to the project root. Verify `panther web` starts without path errors.
3. **Experiment service**: Uses `asyncio.to_thread()` instead of a busy-loop. The experiment launch should not block the UI.

## Step 6: Read the Plan

Now read your development plan and architecture docs:

- **`panther/webapp/TASKS.md`** -- 4-phase plan with code and thesis tasks per phase
- **`panther/webapp/ARCHITECTURE.md`** -- Design decisions, integration patterns, data models, scope

Run the existing test suite to make sure everything works:
```bash
pytest tests/unit/test_webapp/ -v -o "addopts=-v --tb=short"
# Should show 40 passed
```

## Key Concepts

### NiceGUI Basics
- Every UI element is a Python object: `ui.label("text")`, `ui.button("click me")`
- Layout uses context managers: `with ui.row():`, `with ui.card():`
- Styling via Quasar classes: `.classes('text-h4 text-primary')`
- Binding: `ui.input().bind_value(model, 'field_name')`
- Events: `button.on('click', handler)`
- Charts: `ui.echart({'xAxis': ..., 'series': ...})`

### Pydantic in PANTHER
- All config models inherit from `BaseConfig` (extends Pydantic `BaseModel`)
- `model.model_dump()` -> dict, `ModelClass(**data)` -> validated instance
- Validation errors are `pydantic.ValidationError` with per-field messages

### The Service Layer
- Pages never import core PANTHER classes directly
- Services wrap core classes, handle errors, provide async-safe interfaces
- Each service maps to one core component (see ARCHITECTURE.md)

### PydanticForm
- `PydanticForm(ModelClass)` renders any Pydantic BaseModel as editable widgets
- `form.get_value()` returns a validated dict; `form.set_value(data)` populates fields
- `FormConfig` controls layout: section style (expansion/card/flat), advanced toggle, CSS prefix
- Nested models are handled recursively; enums become dropdowns; Optional[BaseModel] gets a toggle
- See `panther/webapp/components/pydantic_form.py` for implementation details

## Understanding Config as a Graph

PANTHER config files describe a graph: services are nodes, protocol relationships are
edges, and network environments group them. This section surveys how industrial tools
model topologies, proposes approaches for PANTHER, and covers attack-scenario design,
tester-specific UX, and the mapping rules that connect YAML to visual elements.

### Industry Landscape

Before designing PANTHER's topology editor, study how existing tools represent
network and service topologies. The table below captures the most relevant systems
and what we can learn from each.

| Tool | Domain | Graph Model | Format | Key Lesson |
|------|--------|-------------|--------|------------|
| **GNS3** | Network emulation | Flat: nodes[] + links[] with UUID refs, x/y coords | JSON (.gns3) | Simple node+link with position persistence |
| **EVE-NG** | Network emulation | Similar flat graph, web canvas | XML (.unl) | Web-based drag-drop, export/import |
| **KYPO CRP** | Cyber range | Three-tier: hosts[], networks[], routers[] + mappings | YAML | Semantic node types with typed layer mappings |
| **Mininet/MiniEdit** | SDN emulation | addHost()/addSwitch()/addLink() Python API | Python/JSON | Visual editor exports runnable scripts |
| **CRATE** | Cyber range | Router-based LAN/WAN, auto-generation | Java/Vaadin | Network generator, auto-layout |
| **VSDL** | Cyber range DSL | Declarative constraints (nodes + networks) | Custom DSL | High-level spec -> SMT solver -> deployment |
| **TOSCA** | Cloud orchestration | Node Templates + Relationship Templates (directed graph) | YAML | Requirements/Capabilities, typed relationships |
| **Docker Compose viz** | Container orchestration | Services as nodes, depends_on/networks as edges | YAML->DOT | Closest to PANTHER's service-in-container model |
| **Kathara** | Network emulation | Devices via collision domains | lab.conf | Minimal declarative format |

**References**: GNS3 file format docs, KYPO topology definition (Masaryk University),
VSDL (Costa et al. 2020), TOSCA OASIS Simple Profile YAML v1.3.

### Multiple Topology Approaches for PANTHER

PANTHER's topology is unique: nodes are protocol implementations (not generic network
devices), edges are protocol-level client->server relationships (not physical links).
Four possible approaches follow.

**Approach A: Flat Service Graph (GNS3/Docker-Compose style)**

- Each `services` dict entry = 1 node (colored by `ImplementationType`: IUT=green, Tester=orange).
- `ProtocolConfig.target` = directed edge (client->server).
- Network environment = property badge on test group, not a node.
- Pro: Direct 1:1 mapping to YAML. Simplest.
- Con: No L2/L3 network detail.

**Approach B: Three-Tier Semantic Graph (KYPO style)**

- Service nodes + Network nodes + Environment nodes.
- Typed connections between layers.
- Pro: Richer network context. Good for thesis novelty.
- Con: PANTHER config doesn't have explicit network-as-node; requires synthesizing. More complex mapping.

**Approach C: Typed Relationships (TOSCA-inspired)**

- Nodes have typed capabilities and requirements.
- Relationships are first-class objects with properties.
- Pro: Most semantically rich. Academically interesting.
- Con: Most complex. Overkill for current config model.

**Approach D: Hybrid with Progressive Disclosure**

- Default = Approach A flat graph.
- Toggle overlay: network grouping, Docker details.
- Click node -> expand details with PydanticForm.
- Pro: Starts simple, complexity on demand. Best UX.
- Con: Two representations. More engineering.

> **Note**: These are starting points. Muhamad should evaluate, propose his own
> variant, and justify the choice in his thesis. The final approach IS the thesis
> contribution.

### Beyond Topology -- Attack Scenario Design

PANTHER supports attack scenario testing via `panther_ivy` and the NACT
(Network-Attack Compositional Testing) methodology, following the APT 6-stage
lifecycle:

```
Reconnaissance -> Infiltration -> C2 -> Priv. Escalation -> Persistence -> Exfiltration
```

The topology editor should eventually support not just "which services connect" but
"what attack logic runs against them."

Industry references for visual attack scenario design:

| Tool | What it visualizes | Graph model | Relevance |
|------|-------------------|-------------|-----------|
| **ATT&CK Flow Builder** | Attack sequences | Directed graph: Action + Condition + AND/OR | Gold-standard for visual scenario composition |
| **CACAO Roaster** | Security playbooks | Workflow: sequential/parallel/branching steps | Executable workflow model |
| **TTCN-3 GFT** | Protocol test logic | MSC lifelines: send/receive/timer/verdict | Only standard for protocol test visualization |
| **Peach Fuzzer State Model** | Protocol FSM | States + Actions (output/input/changeState) | Closest fuzzer model to protocol test logic |
| **CALDERA Magma** | Adversary operations | Ability list + agent topology | Operation monitoring UX |

Key insight: topology (infrastructure) and test logic (scenario) are two separate
concerns. This separation is recognized industry-wide (TOSCA, SimSpace, KYPO all
separate them).

For thesis scope: start with topology (Phase 2). Architecture should be extensible
toward scenario visualization. NACT data available: `attack_life_cycle.ivy`,
`apt_tests/` with CVE-specific tests, protocol-specific bindings, `.dsc` parameter
files.

### Tester-Specific UX

Different tester types need different config and results UX:

| Tester Type | Example | Config Needs | Output Needs |
|-------------|---------|-------------|-------------|
| Formal verification | panther_ivy | Test selection, iterations, build mode, Z3 source | Verdict, .iev event logs, assumption failures |
| Fuzzer (future) | boofuzz, Peach | Mutation strategy, seed corpus, target fields | Crash count, coverage %, unique crashes |
| Conformance (future) | Scapy-based | Packet sequence, expected responses | Per-packet pass/fail, timing |
| Performance (future) | iperf, wrk | Load profile, duration, concurrency | Throughput, latency histograms |

Plugin-extensible UI patterns from industry:

| Pattern | Example | How it works | PANTHER fit |
|---------|---------|-------------|-------------|
| Schema-driven forms | RJSF, JSON Forms | Plugin provides schema -> UI auto-generates form | Best fit -- `config_schema.py` already exists |
| Extension point registry | Grafana panels | Plugin registers component at named slot | Good for result visualizations |
| Conditional rendering | ZAP scan types | Selecting type swaps visible fields | Natural for properties panel |
| Progressive disclosure | TLA+ Toolbox | Basic visible, "Advanced" expands | Already supported via `json_schema_extra` |

> **Note**: `PydanticForm` + `config_schema.py` already handles most of this
> automatically. Worth documenting and evaluating in thesis. Future evolution (out of
> scope): plugin-contributed result panels, schema-driven conditional fields, attack
> scenario composer overlay.

### Mapping Rules and Workflow

Invariant mapping rules (regardless of approach chosen):

| Config Concept | Graph Concept |
|---------------|---------------|
| `TestConfig` | Independent subgraph/group |
| `TestConfig.services[key]` | Node (key = label) |
| `ImplementationType` | Node category (color/shape) |
| `ProtocolConfig.role` | Node role badge |
| `ProtocolConfig.target` | Directed edge (source->target) |
| `ProtocolConfig.name` + `version` | Edge label |
| `NetworkEnvironmentConfig.type` | Group property or background |
| `ServiceConfig.depends_on` | Dashed dependency edge |

Workflow expectations:

- These docs, services, and components are a starting scaffold -- improve, extend, refine them.
- Missing features or unclear APIs -> open a GitHub issue.
- All work goes through GitHub PRs with code review.
- PRs should reference issues and include design rationale.

## Your First Two Weeks Deliverables

By end of Phase 1 (Week 2), you should have:
1. All 5 pages loading without errors (verified by running `panther web --reload`)
2. All existing tests passing (verified by running `pytest tests/unit/test_webapp/`)
3. At least 3 real experiments run end-to-end through the webapp
4. Bug report documenting any issues found (with screenshots)
5. Familiarity with vis.js Network docs and the scaffolded TopologyEditor
6. Background chapter outline for thesis
7. Related work research notes (cyber ranges, visual testing tools, framework comparisons)

## Thesis Writing Tips (UCLouvain EPL)

Your thesis should be 40-60 pages. Suggested chapter structure:

1. **Introduction** (5-7 pages): Problem statement, contributions, structure
2. **Background & Related Work** (8-12 pages): Protocol testing, PANTHER framework, web UI frameworks, comparison
3. **Architecture & Design** (8-12 pages): Stack choice, service layer, observer integration, topology editor design
4. **Implementation** (10-15 pages): Topology editor, config builder, experiment launch, results dashboard
5. **Evaluation** (5-8 pages): User study (CLI vs forms vs topology), usability metrics, demo walkthrough
6. **Conclusion & Future Work** (3-5 pages)

Start writing in Week 1. Each week has thesis writing tasks alongside code tasks.
