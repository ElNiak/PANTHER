# Task Breakdown: PANTHER Web Dashboard

Muhammad's 8-week plan for the master thesis (60 ECTS, UCLouvain EPL).

Each week interleaves code and thesis writing. The thesis requires 40-60 pages plus working code, with focus on **experiment configuration, visualization, and output analysis**.

---

## Scope Decisions

| Feature | Decision | Rationale |
|---------|----------|-----------|
| Dashboard page | **Keep as-is** | Already functional with stat cards and quick actions |
| Plugins page | **Keep as-is** | Already functional with plugin table |
| Config builder (NiceCRUD forms) | **Build** | Core thesis contribution |
| One-way form-to-YAML preview | **Build** | Demonstrates Pydantic-to-UI pipeline |
| Two-way YAML sync | **Cut** | High complexity, marginal thesis value |
| Experiment launch + WebObserver | **Build** | GUIObserver exists, integration is straightforward |
| Results browser + analysis dashboard | **Build** | Rich data available (ExperimentSummary, TestResult, ServiceHealth, metrics JSON) |
| ECharts visualizations | **Build** | NiceGUI has built-in ECharts support |
| Cross-experiment comparison | **Build** | High thesis value for evaluation chapter |
| Drag-and-drop topology | **Cut** | High complexity, low thesis value |
| 70% test coverage | **Cut** | 5-6 smoke tests instead |
| `pip install .[web]` smoke test | **Keep** | Quick verification |

---

## Week 1: Bug Fixes + NiceCRUD Spike

**Code focus:**
1. Fix scaffold bugs (already done in this commit):
   - `results.py`: Wire `table.on('rowClick', ...)` to `show_detail()`.
   - `experiment_service.py`: Replace busy-loop with `asyncio.to_thread()`. Verify ExperimentManager constructor matches real signature.
   - `config_service.py`: Use `Path` relative to project root with fallback.
2. NiceCRUD spike with real PANTHER models:
   - Test `LoggingConfig`, `DockerConfig`, `PathsConfig` with NiceCRUD.
   - Document: does `id_field` work? Do nested models render? Are Enums rendered as dropdowns?
   - Write a 1-page spike report.

**Thesis writing:**
- Background chapter outline.
- Related work research: web-based testing tools, protocol testing frameworks, NiceGUI/Streamlit/Flask comparisons.

**Deliverable:** All 5 pages load without errors. Spike report written.

**Acceptance criteria:**
- `panther web --reload` starts without errors.
- Navigate to `/results`, click a row, detail panel appears.
- NiceCRUD spike report documents what works and what doesn't.

---

## Week 2: Config Builder -- Global Config Forms

**Code focus:**
1. Add NiceCRUD forms for `LoggingConfig`, `DockerConfig`, `PathsConfig` to `/config`.
   - Use `NiceCRUD(Model, id_field='<unique_field>')` pattern.
   - Layout: `ui.expansion` accordion panels, one per config section.
2. One-way form-to-YAML preview:
   - On form change: `model.model_dump()` -> `yaml.dump()` -> update YAML editor.
   - No YAML-to-form sync (cut from scope).
3. Add "Validate" button that runs `GlobalConfig(**form_data)` and shows Pydantic errors.

**Thesis writing:**
- Introduction chapter draft.
- Related work draft (framework comparison, testing tool landscape).

**Deliverable:** `/config` page with working forms for global config sections.

**Acceptance criteria:**
- All fields from LoggingConfig, DockerConfig, PathsConfig render as appropriate inputs.
- Invalid values show Pydantic validation errors inline.
- YAML preview updates when form fields change.

---

## Week 3: Config Builder -- Test + Service Forms + Save

**Code focus:**
1. Add `TestConfig` + `ServiceConfig` forms to the config builder:
   - Test name, description, iterations, timeout.
   - Service: name, implementation, protocol, role, target, ports.
   - Network environment: type selector (docker_compose, localhost, shadow).
2. "Save YAML" button writes config to `experiment-config/`.
3. "Load YAML" button reads a file and populates the form.

**Thesis writing:**
- Architecture chapter: design decisions, Pydantic-to-UI pipeline, service layer pattern.
- Framework comparison section (NiceGUI vs Flask vs Streamlit).

**Deliverable:** Full config builder with save/load.

**Acceptance criteria:**
- Can build a complete experiment config through forms.
- "Save YAML" writes a valid, loadable config file.
- "Load YAML" populates form fields from an existing config.

---

## Week 4: Experiment Launch + WebObserver

**Code focus:**
1. Verify `ExperimentService.run_experiment()` works with a real config.
2. Implement `WebObserver` (subclass `GUIObserver`):
   - Override `update_gui(event)` to push events to subscribed UI components.
   - Register with `EventManager` when experiment launches.
3. Add to `/experiments` page:
   - Live log viewer (`ui.log`) subscribed to `WebObserver`.
   - Progress bar tracking test completion.
   - Color-coded events (test=blue, error=red, service=green).

**Thesis writing:**
- Architecture chapter continued: observer pattern integration, real-time update mechanism.

**Deliverable:** Live experiment monitoring with progress and logs.

**Acceptance criteria:**
- Launch an experiment from the browser; logs appear in real time.
- Progress bar advances as tests complete.
- No UI freezes during long-running experiments.

---

## Week 5: Results Page -- ExperimentSummary + Test Details

**Code focus:**
1. Parse `ExperimentSummary` JSON from output directories:
   - Use `StatusCollector` to build `ExperimentSummary` from `outputs/<date>/<id>/`.
   - Display: experiment status, duration, test count, success rate.
2. Per-test detail panel:
   - Test name, status badge (pass/fail/skip/timeout), duration.
   - Expandable log viewer per test.
   - Error message display for failed tests.
3. Service health cards:
   - Parse `ServiceHealthSummary` from `analysis/service_health.json`.
   - Show: service name, status, exit code, compilation status, output completeness.

**Thesis writing:**
- Implementation chapter: config builder, experiment launch, results parsing.

**Deliverable:** `/results` page with full experiment details.

**Acceptance criteria:**
- Clicking an experiment shows per-test results with status badges.
- Failed tests show error messages.
- Service health cards display correctly.
- Works with real experiment output.

---

## Week 6: Analysis Dashboard with ECharts

**Code focus:**
1. Add ECharts visualizations to the results page:
   - Pass/fail rate pie chart per experiment.
   - Test duration bar chart.
   - Metrics line charts (from `metrics*.json` files).
2. Cross-experiment comparison view:
   - Select 2+ experiments to compare.
   - Side-by-side success rate, duration, and resource usage.
3. Parse `analysis_results.json` for tester-specific results.

**Thesis writing:**
- Implementation chapter continued: visualization pipeline, ECharts integration.

**Deliverable:** Analysis dashboard with charts and cross-experiment comparison.

**Acceptance criteria:**
- Charts render correctly with real data.
- Cross-experiment comparison works with 2+ experiments.
- Empty states handled (no data, missing metrics).

---

## Week 7: Integration Testing + Polish

**Code focus:**
1. Run a real experiment end-to-end through the webapp:
   - Config -> Launch -> Monitor -> Results -> Analysis.
   - Fix any integration issues discovered.
2. Write 5-6 smoke tests:
   - `test_config_service.py`: load/validate/save YAML.
   - `test_results_service.py`: list experiments, parse summary.
   - `test_pages_load.py`: verify each page renders without exceptions.
3. `pip install .[web]` smoke test.
4. Bug fixes and UI polish (toast notifications, loading spinners).

**Thesis writing:**
- Evaluation chapter: testing methodology, results analysis, comparison with manual workflow.
- Conclusion draft.

**Deliverable:** Working end-to-end webapp with smoke tests.

**Acceptance criteria:**
- Full config-to-results workflow works through the browser.
- `pytest tests/unit/test_webapp/ -v` passes.
- `pip install -e ".[web]" && panther web` starts without errors.

---

## Week 8: Buffer + Demo + Thesis Submission

**Code focus:**
- Buffer for any remaining bugs.
- Prepare demo script for defense (scripted walkthrough: config -> launch -> monitor -> results).
- Final code cleanup and README updates.

**Thesis writing:**
- Full thesis revision.
- Abstract, acknowledgments, table of contents.
- Submission.

**Deliverable:** Submitted thesis + working demo.

---

## Data Models Reference

These are the key data structures the results page and analysis dashboard will use:

### ExperimentSummary (`panther/core/reporting/status_collector.py`)
```
ExperimentSummary
  experiment_id: str
  status: ExperimentStatus (completed/failed/interrupted/timeout/unknown)
  start_time, end_time, duration
  configuration_file: str
  tests: List[TestResult]
  fast_fail: FastFailInfo
  resources: ResourceUsage
  services: List[ServiceHealthSummary]
  -- computed: total_tests, passed_tests, failed_tests, success_rate
```

### TestResult
```
TestResult
  name, status (passed/failed/skipped/timeout/interrupted/unknown)
  duration: float
  start_time, end_time
  error_message: Optional[str]
  logs_path: Optional[str]
  fast_fail_triggered: bool
```

### ServiceHealthSummary
```
ServiceHealthSummary
  service_name, service_type, status (healthy/degraded/failed/unknown)
  exit_code, crashed, compilation_succeeded
  phases_completed: Dict[str, bool]
  error_summary, output_completeness: float
```

### Output Directory Structure
```
outputs/<experiment_date_name>/
  experiment.log                    # Main experiment log
  <test_name>/
    test.log                        # Per-test log
    logs/                           # Service logs
      <service>.log
      <service>.err.log
    analysis/
      analysis_results.json         # Tester results (passed/failed per tester)
      service_health.json           # Per-service health data
    artifacts/                      # PCAPfiles, etc.
  metrics*.json                     # Resource metrics
  docker-compose*.yml               # Docker configs used
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| NiceCRUD doesn't handle nested models | Fall back to manual NiceGUI forms. Week 1 spike determines this. |
| ExperimentManager blocks unexpectedly | `asyncio.to_thread()` with daemon thread. Add "Force Stop" button. |
| NiceGUI hot reload breaks | Use `--no-reload` as fallback. |
| ECharts data format mismatch | Test with mock data first, then real experiment output. |
| Thesis writing falls behind | Writing starts Week 1, not Week 7. Each week has writing tasks. |
| Real experiment takes too long for testing | Use minimal config with fast tests (minip ping-pong). |
