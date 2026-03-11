# Development Roadmap: PANTHER Web Dashboard

Target completion: end May 2026.

**Documentation strategy**: Diagrams-first. Each coding phase produces Mermaid diagrams
(version-controlled in `panther/webapp/diagrams/`). These diagrams serve as both
development documentation and thesis figures.

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
| **Visual Topology Editor** | **Developer** | **Core contribution** |
| **Library comparison (vis.js vs React Flow)** | **Developer** | Analytical chapter |
| **UX improvements (breadcrumbs, JSON viewer, workflow)** | **Developer** | Parallel with topology |
| **CLI command integration** | **Developer** | Stretch goal |
| **End-to-end workflow polish** | **Developer** | Stretch goal |
| **Evaluation study (user study, comparison)** | **Developer** | To conduct |
| **Thesis document** | **Developer** | To write |

**Core contribution**: Design and implementation of a visual experiment designer for
protocol conformance testing, including an analytical comparison of visualization
libraries (vis.js vs React Flow), and UX improvements for a research-oriented workflow.

---

## Completed Foundation

The scaffold provides a fully functional NiceGUI webapp:

- **6 pages** load and work: Dashboard, Config Builder, Topology (scaffolded), Experiments, Results, Plugins
- **PydanticForm** renders any Pydantic BaseModel as editable NiceGUI widgets (711 lines, recursive)
- **Service layer** wraps PANTHER core: ConfigService, ExperimentService, ResultsService, PluginService
- **Config builder** has Form Editor + YAML Preview tabs with auto-sync, save/load/validate
- **Experiment launcher** with `asyncio.to_thread()`, WebObserver, live log viewer
- **Results browser** with filtering, tabbed detail view (Summary, Tests, Logs, Events, Artifacts), ECharts
- **40+ unit tests** passing
- **Topology editor bridge** scaffolded (vis.js Python wrapper, 235 lines)

---

## Phase 1: Onboarding + Research + Library Comparison (Week 1-2)

### Code Focus

1. Run `panther web --reload`, click through all 6 pages. Document what works and what doesn't.
2. Run 3+ real experiments through the webapp end-to-end (config → launch → monitor → results).
3. Document all bugs/issues found, fix the simple ones.
4. Study NiceGUI patterns, PydanticForm (711 lines), service layer architecture.
5. Study PANTHER config models: `ServiceConfig`, `TestConfig`, `NetworkEnvironmentConfig`.
6. Explore the scaffolded `TopologyEditor` wrapper — understand the Python ↔ JS bridge.
7. Research **both vis.js Network AND React Flow**:
   - Integration approaches with NiceGUI (direct JS bridge vs iframe/web component)
   - Feature comparison: physics engine, custom nodes, minimap, manipulation API
   - Ecosystem: documentation quality, community activity, maintenance status
   - Performance: large graph handling, stabilization time
8. Write analytical comparison chapter with criteria table (5+ dimensions) and justified recommendation.
9. Choose implementation library and document rationale.

### Documentation Tasks

- Improve GETTING_STARTED.md and SETUP.md based on onboarding experience (student perspective)
- Add "Common Pitfalls" section based on bugs encountered
- Create first architecture diagrams

### Diagrams to Produce

- `diagrams/01-webapp-architecture.mmd` — Current 6-page architecture with service layer
- `diagrams/02-tech-comparison.mmd` — vis.js vs React Flow feature/integration comparison
- `diagrams/03-page-navigation-flow.mmd` — Current page routing and navigation

### Deliverable

Bug report from real usage. Comparison chapter draft. Library choice with justification. 3 architecture diagrams. Improved onboarding docs.

### Acceptance Criteria

- `panther web --reload` starts without errors
- At least 3 experiments completed successfully through the webapp
- Bug report with screenshots of any issues found
- Comparison chapter has criteria table with 5+ evaluation dimensions
- Library choice documented with clear rationale
- 3 Mermaid diagrams committed to `panther/webapp/diagrams/`

---

## Phase 2: Topology Editor Implementation + Parallel UX Fixes (Week 2-5)

### Core Topology Work

1. **Week 2-3**: Palette sidebar + drag-and-drop node creation on canvas.
   - Node types: IUT (green box), Tester (blue diamond), Environment (orange ellipse).
   - Reuse `DEFAULT_GROUPS` from existing `topology_editor.py`.
   - Different visual treatment per node type (colors, shapes, icons).
2. **Week 3-4**: Edge creation (connect nodes), protocol labels on edges, properties panel.
   - Click node → PydanticForm renders in right panel.
   - Reuse existing `PydanticForm` from `components/pydantic_form.py` for ServiceConfig, ProtocolConfig.
   - Edge labels from `ProtocolConfig` (name, version, role).
3. **Week 4-5**: Export topology → PANTHER YAML config. Import existing YAML → render as graph.
   - Export: graph nodes → `TestConfig.services`, edges → protocol connections
   - Import: parse `TestConfig.services` → nodes, protocol `target` fields → edges
   - Must produce configs matching `experiment-config/base/` format
4. **Week 5**: Validation (red borders for invalid configs, warnings) + auto-layout.
   - Auto-layout via physics engine (vis.js barnesHut / React Flow dagre)
5. Integrate as 3rd tab in config builder (alongside Form Editor + YAML Preview).

### Parallel UX Fixes

Fix these as encountered during topology work — don't wait for a separate phase:

- **Breadcrumbs**: Add to all pages (e.g., Config > Test 1 > picoquic)
- **"Next Step" buttons**: Contextual navigation (Config page → "Launch Experiment", Experiments → "View Results")
- **Stepper/progress indicator**: Show where user is in the Config → Topology → Launch → Results workflow
- **Structured JSON viewer**: Replace raw JSON display where encountered:
  - `analysis_results.json` → collapsible tree with syntax highlighting
  - `service_health.json` → formatted cards (partially done in `service_health_card.py`)
  - Experiment logs → keep LogViewer but add search/filter
- **Deep-links**: From results back to the config that produced them

### Documentation Tasks

- Update ARCHITECTURE.md with topology editor design decisions
- Add component API docs for TopologyEditor (props, events, usage examples)

### Diagrams to Produce

- `diagrams/04-topology-component-architecture.mmd` — TopologyEditor class diagram, Python↔JS bridge
- `diagrams/05-yaml-graph-mapping.mmd` — How YAML config maps to/from graph nodes and edges
- `diagrams/06-user-workflow.mmd` — End-to-end user journey: Dashboard → Config → Topology → Launch → Results

### Key Files to Modify

- `panther/webapp/components/topology_editor.py` — Extend scaffold (currently 235 lines)
- `panther/webapp/pages/topology.py` — Full page implementation (currently 147 lines)
- `panther/webapp/pages/config_builder.py` — Add topology as 3rd tab
- `panther/webapp/components/layout.py` — Breadcrumbs + stepper
- `panther/webapp/pages/results.py` — Structured JSON viewer
- `panther/webapp/services/config_service.py` — YAML↔graph conversion helpers

### Existing Code to Reuse

- `PydanticForm` (`components/pydantic_form.py`) — Properties panel for topology nodes
- `DEFAULT_GROUPS` (`components/topology_editor.py`) — Node type styling
- `YamlEditor` (`components/yaml_editor.py`) — YAML preview tab
- `ConfigService.validate_config()` — Validation in export
- `dict_list_widgets.py` — KeyedModelEditor for service node editing

### Deliverable

Working topology editor integrated in config builder. UX improvements across pages.

### Acceptance Criteria

- Can drag nodes from palette onto canvas
- Can connect nodes with labeled edges
- Click node shows editable PydanticForm properties panel
- Export produces valid PANTHER YAML config
- Import renders existing config as graph
- Invalid configs get visual red borders
- Breadcrumbs visible on all pages
- At least one JSON viewer replaced with structured view

---

## Phase 3: End-to-End Workflow Polish + Stretch Goals (Week 5-8)

### Workflow Polish (Primary Focus)

- Make Config → Topology → Launch → Results flow seamless end-to-end
- Undo/redo in topology editor (basic state history)
- Fix all remaining bugs from Phase 1 bug report
- Integration test: topology → YAML → experiment → results roundtrip
- `pip install .[web]` verification in a fresh venv

### Stretch Goals (Priority Order)

Implement in this order, as time allows:

1. **CLI command integration** — Expose CLI commands in webapp:
   - `panther config validate` → enhance with inline error display
   - `panther config generate` → template picker (minimal/basic/advanced/performance/security)
   - `panther plugins params` → plugin parameter viewer in plugins page
   - `panther plugins check-deps` → dependency checker with fix suggestions
   - `panther tools status` → tool installation status dashboard
   - Pattern: each CLI command → webapp action button, same flags as form inputs, output inline
   - Create `panther/webapp/services/cli_service.py` wrapping CLI functions

2. **Conformance matrix** — IUT × Test pass/fail grid:
   - Aggregate results across experiments
   - Click cell → drill into test details
   - Add to `panther/webapp/pages/results.py` as new tab

3. **Batch comparison** — Run same test across multiple IUTs, side-by-side results

4. **Export for papers** — Charts/tables exportable as CSV, LaTeX snippets, SVG

### Documentation Tasks

- Complete component API reference for all modified components
- Update GETTING_STARTED.md with topology editor usage guide
- Create "CLI ↔ Webapp mapping" reference table

### Diagrams to Produce

- `diagrams/07-cli-webapp-mapping.mmd` — Which CLI commands map to which webapp actions
- `diagrams/08-data-flow-complete.mmd` — Full system data flow including new features
- `diagrams/09-stretch-goal-mockups/` — Mockup diagrams for unimplemented features (for thesis Future Work)

### Deliverable

Polished end-to-end workflow. Stretch goals implemented. Mockups for unimplemented features.

### Acceptance Criteria

- Config → Topology → Launch → Results works without leaving the workflow
- `pip install -e ".[web]" && panther web` starts without errors
- At least 2 stretch goals implemented
- Mockups created for all unimplemented stretch goals

---

## Phase 4: Evaluation + Thesis Writing (Week 8-10)

### Evaluation

1. Mini user study with 3-5 protocol dev students:
   - Task: configure a QUIC test scenario using (a) CLI, (b) form builder, (c) topology editor.
   - Measure: task completion time, errors, satisfaction (SUS questionnaire).
   - Compare approaches quantitatively.
2. Final polish and bug fixes.
3. Prepare demo script for defense.

### Thesis Writing (Prose Sprint)

All accumulated diagrams become thesis figures. Prose wraps around them:

- **Chapter 1**: Introduction (problem statement, research questions, contributions)
- **Chapter 2**: Background (protocol testing, cyber ranges, visual configuration, NiceGUI)
- **Chapter 3**: Library Comparison (analytical vis.js vs React Flow evaluation from Phase 1)
- **Chapter 4**: Architecture & Design (accumulated diagrams + design decisions)
- **Chapter 5**: Implementation (feature walkthrough with code excerpts + screenshots)
- **Chapter 6**: Evaluation (user study results, SUS scores, comparison data)
- **Chapter 7**: Future Work (mockups for unimplemented stretch goals)
- **Chapter 8**: Conclusion

### Diagrams to Produce

- `diagrams/10-evaluation-results.mmd` — Charts from user study data
- `diagrams/11-sus-scores.mmd` — SUS score visualization
- All previous diagrams refined for thesis inclusion (captions, labels, consistent style)

### Deliverable

Submitted thesis (40-60 pages) + working demo.

### Acceptance Criteria

- User study completed with at least 3 participants
- Full thesis submitted
- Demo script runs without errors
- All diagrams are thesis-ready

---

## Diagrams-First Writing Strategy

| Phase | Diagram Artifacts | Thesis Chapter |
|-------|------------------|----------------|
| Phase 1 | Architecture overview, tech comparison, page flow | Background + Comparison |
| Phase 2 | Component architecture, YAML↔graph mapping, user workflow | Architecture + Implementation |
| Phase 3 | CLI mapping, data flow, stretch goal mockups | Implementation + Future Work |
| Phase 4 | Evaluation charts, SUS scores | Evaluation |

**Tool**: Mermaid (`.mmd` files, version-controlled in `panther/webapp/diagrams/`). Alternative: draw.io exported as SVG.

**Rule**: No formal prose writing during Phases 1-3. Only diagrams + brief captions. All thesis writing happens in Phase 4 using diagrams as the backbone.

---

## Technology Reference

### Topology Editor Integration

The topology editor uses a visualization library (chosen in Phase 1) wrapped as a NiceGUI component:

| Component | File | Purpose |
|-----------|------|---------|
| Python wrapper | `components/topology_editor.py` | TopologyEditor class, props, events |
| Page | `pages/topology.py` | Route `/topology`, layout, palette |

**Current scaffold** (vis.js):
- `TopologyEditor.set_graph(nodes, edges)` — Python → JS
- `TopologyEditor.get_graph()` — JS → Python
- `on_node_click(callback)` — Click → Python handler
- `DEFAULT_GROUPS` — Node type styling (IUT/Tester/Environment)

**If React Flow is chosen**: Requires iframe or web component embedding, postMessage bridge for Python↔React communication, and npm build step.

### Data Models Reference

**ExperimentConfig** (`panther/config/core/models/experiment.py`):
- `tests: List[TestConfig]` — each test has services, network env, steps
- `metadata: ExperimentMetadata` — name, author, tags

**ServiceConfig** (`panther/config/core/models/service.py`):
- `implementation: ImplementationConfig` — name, type (IUT/tester)
- `protocol: ProtocolConfig` — name, version, role (server/client)

**ExperimentSummary** (`panther/core/reporting/status_collector.py`):
- `tests: List[TestResult]` — per-test name, status, duration, errors
- `services: List[ServiceHealthSummary]` — health, exit codes, compilation

### Output Directory Structure

```
outputs/<experiment_date_name>/
  experiment.log
  <test_name>/
    test.log
    logs/<service>.log
    analysis/
      analysis_results.json
      service_health.json
    artifacts/
  metrics*.json
  docker-compose*.yml
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Chosen library integration issues | Phase 1 analytical research should surface major blockers early |
| JavaScript debugging unfamiliar | Use browser DevTools; both vis.js and React Flow have good docs |
| Real experiments take too long | Use minimal configs (picoquic ping-pong, ~30 seconds) |
| Scope creep from stretch goals | Prioritized list — stop when time runs out, document rest as Future Work |
| User study recruitment | Ask classmates, use 3 participants minimum |
| NiceGUI hot reload breaks | Use `--no-reload` as fallback |

---

## Existing Test Suite

Tests in `tests/unit/test_webapp/`:

| File | Tests | Coverage |
|------|-------|----------|
| `test_app.py` | 8 | App factory, API models, component imports |
| `test_form_models.py` | 8 | Form model utilities with all config models |
| `test_services.py` | 24 | All 4 services: Plugin, Config, Results, Experiment |

Run with: `pytest tests/unit/test_webapp/ -v -o "addopts=-v --tb=short"`
