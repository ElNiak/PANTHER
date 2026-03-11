# Development Roadmap: PANTHER Web Dashboard

Target completion: end May 2026.

The development focus is on **visual experiment configuration, topology design, and
output analysis** — extending the existing webapp scaffold into a complete interactive
experiment designer.

---

## Contribution Delineation

| Component | Owner | Status |
|-----------|-------|--------|
| Webapp scaffold (6 pages, service layer, layout) | Scaffold | Complete |
| PydanticForm (recursive Pydantic-to-NiceGUI renderer) | Scaffold | Complete |
| Config builder (form+YAML tabs, save/load/validate) | Scaffold | Complete |
| Experiment launch + WebObserver + live logs | Scaffold | Complete |
| Results page (table, detail view, ECharts bar chart) | Scaffold | Complete |
| Plugin page (cards, type filter, detail drawer) | Scaffold | Complete |
| Bug fixes (race conditions, path safety, error handling) | Scaffold | Complete |
| **Visual Topology Editor** | **Student** | **Core contribution** |
| **Library evaluation (vis.js vs React Flow vs NiceGUI native)** | **Student** | Analytical chapter |
| **UX improvements** | **Student** | Parallel with topology |
| **Service→core integration testing** | **Student** | Testing contribution |
| **Evaluation study** | **Student** | To conduct |
| **Thesis document** | **Student** | To write |

**Core contribution**: Design and implementation of a visual experiment designer for
protocol conformance testing, including an analytical evaluation of visualization
approaches (vis.js, React Flow, NiceGUI native), service→core integration testing,
and UX improvements for a research-oriented workflow.

---

## Completed Foundation

The scaffold provides a fully functional NiceGUI webapp:

- **6 pages** load and work: Dashboard, Config Builder, Topology (placeholder), Experiments, Results, Plugins
- **PydanticForm** renders any Pydantic BaseModel as editable NiceGUI widgets (recursive)
- **Service layer** wraps PANTHER core: ConfigService, ExperimentService, ResultsService, PluginService
- **Config builder** has Form Editor + YAML Preview tabs with auto-sync, save/load/validate
- **Experiment launcher** with `asyncio.to_thread()`, WebObserver, live log viewer
- **Results browser** with filtering, tabbed detail view, ECharts metrics
- **60+ unit tests**, 30+ browser integration tests, 7 E2E tests passing

---

## Phase 1: Onboarding + Research (Week 1)

**Goal**: Become productive in the codebase and produce a library evaluation chapter.

- Run `panther web --reload`, explore all 6 pages, run 3+ real experiments end-to-end.
- Study the scaffold: NiceGUI patterns, PydanticForm, service layer, config models.
- Evaluate at least 3 visualization approaches (vis.js, React Flow, NiceGUI native)
  for the topology editor. The evaluation criteria and methodology are yours to define.
- Produce an analytical comparison with justified recommendation.
- Improve onboarding docs based on your experience.
- Usage scenarios to explore:
  - Config builder → export YAML → CLI validation
  - Config builder → launch experiment → view results
  - Plugin page → plugin details → source code link
  - Experiment page → live logs → experiment summary
  - ...
- This will be used for the "Library Evaluation" chapter of the thesis and to inform the topology editor design.

---

NOTE:
- It is advice to produce frequently diagrams during development — these become thesis figures and help clarify design decisions.

## Phase 2: Topology Editor Implementation + Parallel UX (Week 2-5)

**Goal**: Build a working topology editor and improve overall webapp UX.

### Topology Editor

Design and implement a visual topology editor where:
- Services are represented as nodes in a graph
- Protocol relationships are represented as edges
- Users can create, edit, and connect nodes interactively
- Node properties are editable (consider reusing PydanticForm)
- The topology can be exported to valid PANTHER YAML config
- Existing YAML configs can be imported and rendered as graphs

### UX Improvements

Improve the overall webapp experience as you encounter friction:
- Navigation aids (breadcrumbs, "next step" buttons, workflow stepper)
- Structured data display (replace raw JSON with formatted views where appropriate)
- Cross-page linking (e.g., results linking back to source config)

---

## Phase 3: Integration Testing + Workflow Polish (Week 5-8)

**Goal**: Verify the full pipeline works and polish the end-to-end experience.

### Service→Core Integration Testing

Design and implement integration tests that verify the webapp services work with
real PANTHER core components (not mocked). The existing browser tests mock all
services — the student extends this by replacing mocks with real calls where feasible.

Key integration paths to consider:
- ConfigService → real YAML → OmegaConf → ConfigManager validation
- ResultsService → real experiment output directory parsing
- WebObserver → EventManager → real event stream
- ExperimentService → ExperimentManager (requires Docker)
- Full workflow: topology export → config validation → experiment launch → results

The existing test infrastructure provides patterns to build on.

### Workflow Polish

- Make the Config → Topology → Launch → Results flow seamless
- Fix all bugs found during Phase 1
- Verify `pip install .[web]` works in a fresh venv

### Stretch Goals (Priority Order)

Implement as time allows:
1. CLI command integration (expose CLI commands as webapp actions)
2. Conformance matrix (IUT × Test pass/fail grid)
3. Batch comparison (same test across multiple IUTs)
4. Export for papers (charts as CSV, LaTeX, SVG)

---

## Phase 4: Evaluation + Thesis Writing (Week 8-10)

**Goal**: Evaluate the work and write the thesis.

### Evaluation

- Conduct a user study (3-5 participants): compare CLI, form builder, and topology
  editor for configuring a test scenario.
- Measure task completion time, errors, and satisfaction.

### Thesis Writing

- 40-60 pages covering: introduction, background, library evaluation, architecture,
  implementation, evaluation, future work, conclusion.
- All diagrams produced during development become thesis figures.

---

## Existing Test Suite

Tests in `tests/unit/test_webapp/`, `tests/integration/`, `tests/e2e/`:

| Category | Count | What they test |
|----------|-------|---------------|
| Unit tests | 60+ | Services, WebObserver, forms, models |
| Browser tests | 30+ | Page rendering via Selenium (services mocked) |
| E2E tests | 7 | Page loads via NiceGUI user simulation |

Run with: `pytest tests/unit/test_webapp/ -v -o "addopts=-v --tb=short"`
