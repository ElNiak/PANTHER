# Task Breakdown: PANTHER Web Dashboard

Due end May 2026.

Each phase interleaves code and thesis writing.

The thesis requires 40-60 pages plus working code, with focus on **visual experiment configuration, topology design, and output analysis**.

---

## Contribution Delineation

| Component | Built by | Status |
|-----------|----------|--------|
| Webapp scaffold (5 pages, service layer, layout) | Supervisor | Complete |
| PydanticForm (recursive Pydantic-to-NiceGUI renderer) | Supervisor | Complete |
| Config builder (form+YAML tabs, save/load/validate) | Supervisor | Complete |
| Experiment launch + WebObserver + live logs | Supervisor | Complete |
| Results page (table, detail view, ECharts bar chart) | Supervisor | Complete |
| Plugin page (cards, type filter, detail drawer) | Supervisor | Complete |
| Bug fixes (race conditions, path safety, error handling) | Supervisor | Complete |
| **Visual Topology Editor (vis.js)** | **Muhammad** | **Core thesis contribution** |
| **Integration polish + real-usage bug fixes** | **Muhammad** | To build |
| **Evaluation study (user study, comparison)** | **Muhammad** | To conduct |
| **Thesis document** | **Muhammad** | To write |

**Muhammad's thesis contribution**: Design and implementation of a visual experiment designer for protocol conformance testing, enabling intuitive topology-based configuration of PANTHER experiments through a cyber-range-inspired interface.

---

## Completed Foundation

The scaffold provides a fully functional NiceGUI webapp:

- **5 pages** load and work: Dashboard, Config Builder, Experiments, Results, Plugins
- **PydanticForm** renders any Pydantic BaseModel as editable NiceGUI widgets (711 lines, recursive)
- **Service layer** wraps PANTHER core: ConfigService, ExperimentService, ResultsService, PluginService
- **Config builder** has Form Editor + YAML Preview tabs with auto-sync, save/load/validate
- **Experiment launcher** with `asyncio.to_thread()`, WebObserver, live log viewer
- **Results browser** with filtering, tabbed detail view (Summary, Tests, Logs, Events, Artifacts), ECharts
- **40+ unit tests** passing
- **Topology editor bridge** scaffolded (vis.js Python wrapper + Vue component)

---

## Phase 1: Onboarding + Real Usage (Week 1-2)

**Code focus:**
1. Run `panther web --reload`, click through all 5 pages. Document what works and what doesn't.
2. Run 3+ real experiments through the webapp end-to-end (config → launch → monitor → results).
3. Document all bugs/issues found, fix the simple ones.
4. Study vis.js Network docs and the scaffolded `TopologyEditor` wrapper.
5. Read PANTHER config models: `ServiceConfig`, `TestConfig`, `NetworkEnvironmentConfig`.
6. Explore the scaffolded `TopologyEditor` wrapper — understand the Python ↔ JS bridge.

**Thesis writing:**
- Background chapter outline.
- Related work: cyber ranges, visual testing tools, protocol testing frameworks, NiceGUI/Streamlit/Flask comparisons.

**Deliverable:** Bug report from real usage. Background chapter outline. Familiarity with codebase.

**Acceptance criteria:**
- `panther web --reload` starts without errors.
- At least 3 experiments completed successfully through the webapp.
- Bug report with screenshots of any issues found.

---

## Phase 2: Topology Editor MVP (Week 2-5)

**Code focus:**
1. **Week 2-3**: Palette sidebar + drag-and-drop node creation on canvas.
   - Node types: IUT, Tester, Network Environment.
   - Different colors/icons per node type.
2. **Week 3-4**: Edge creation (connect nodes), protocol labels on edges, node type icons/colors.
3. **Week 4-4.5**: Properties panel — click node → PydanticForm renders in right panel.
   - Reuse existing PydanticForm for ServiceConfig, TestConfig forms.
4. **Week 4.5-5**: Export topology → PANTHER YAML config. Import existing YAML → render as graph.
5. **Week 5**: Basic validation — visual red borders for invalid configs, warnings.

**Thesis writing:**
- Architecture chapter: component design, technology choices (vis.js, NiceGUI custom elements), integration patterns.

**Deliverable:** Working topology editor that can create, edit, and export experiment configs.

**Acceptance criteria:**
- Can drag nodes from palette onto canvas.
- Can connect nodes with labeled edges.
- Click node shows editable properties panel.
- Export produces valid PANTHER YAML config.
- Import renders existing config as graph.
- Invalid configs get visual indicators.

---

## Phase 3: Integration + Polish (Week 5-7)

**Code focus:**
1. Wire topology editor into config builder as new tab (alongside Form Editor and YAML Preview).
2. Auto-layout algorithm (vis.js has built-in layout engines).
3. Bug fixes from real usage testing (Phase 1 bug report).
4. Undo/redo (basic state history).
5. `pip install .[web]` verification in a fresh venv.
6. Integration test suite: topology → YAML → experiment → results roundtrip.

**Thesis writing:**
- Implementation chapter: detailed feature walkthrough with code excerpts + screenshots.

**Deliverable:** Topology editor integrated into config builder. Integration tests.

**Acceptance criteria:**
- Config builder has 3 tabs: Form Editor, Topology Editor, YAML Preview.
- Auto-layout arranges nodes cleanly.
- `pip install -e ".[web]" && panther web` starts without errors.

---

## Phase 4: Evaluation + Thesis Writing (Week 7-10)

**Code focus:**
1. Mini user study with 3-5 protocol dev students:
   - Task: configure a QUIC test scenario using (a) CLI, (b) form builder, (c) topology editor.
   - Measure: task completion time, errors, satisfaction (SUS questionnaire).
   - Compare approaches: CLI vs form-based vs visual topology.
2. Final polish and bug fixes.
3. Prepare demo script for defense.

**Thesis writing:**
- Evaluation chapter with study results.
- Conclusion, future work.
- Full revision, abstract, acknowledgments.
- **Submission deadline: end May.**

**Deliverable:** Submitted thesis + working demo.

**Acceptance criteria:**
- User study completed with at least 3 participants.
- Full thesis submitted.
- Demo script runs without errors.

---

## Technology Reference

### vis.js Network Integration

The topology editor uses **vis.js Network** wrapped as a NiceGUI custom Vue component:

| Component | File | Purpose |
|-----------|------|---------|
| Python wrapper | `components/topology_editor.py` | `TopologyEditor` class, props, events |
| Vue component | `components/topology_editor.js` | vis.js initialization, canvas rendering |
| Topology page | `pages/topology.py` | Route `/topology`, sample data |

**Key vis.js features to use:**
- `network.addNodeMode()` / `network.addEdgeMode()` for creating elements
- `manipulation` option for built-in edit UI
- `physics` option for auto-layout
- `selectNode` / `selectEdge` events for properties panel

### Data Models Reference

These are the key data structures for the config builder and results page:

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
| vis.js + NiceGUI integration complexity | Scaffold provides working bridge; study `nodegraph-editor-nicegui` reference |
| JavaScript debugging unfamiliar | Use browser DevTools; vis.js has good docs and examples |
| Real experiments take too long | Use minimal configs (picoquic ping-pong, ~30 seconds) |
| Thesis writing falls behind | Writing starts Phase 1. Each phase has writing tasks. |
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
