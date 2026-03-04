# Task Breakdown: PANTHER Web Dashboard

12-week plan. Weeks 1-10 are development, weeks 11-12 are thesis writing.

Each week assumes ~4 working days. If a task finishes early, pull from the next week.

---

## Phase 1: Foundation (Weeks 1-3) -- "Walking Skeleton"

Goal: A running NiceGUI app with shared layout, one working page, and the `panther web` CLI command.

### Week 1: Project Setup + CLI Command + Shared Layout

**Tasks:**
1. Create `panther/cli_click/commands/web.py` with a Click command `web` that starts a NiceGUI/Uvicorn server.
   - Options: `--host` (default 127.0.0.1), `--port` (default 8080), `--reload` (dev mode).
   - Register the command in `panther/cli_click/core/main.py` via `register_commands()`.
2. Create `panther/webapp/app.py` -- NiceGUI application factory.
   - Initialize NiceGUI app, register pages, set up shared state (services).
3. Create `panther/webapp/components/layout.py` -- shared page layout.
   - Left sidebar with navigation links: Dashboard, Config Builder, Experiments, Results, Plugins.
   - Top header with PANTHER logo/title.
   - Use `ui.left_drawer` and `ui.header` from NiceGUI/Quasar.
4. Create a minimal dashboard page (`pages/dashboard.py`) that just says "PANTHER Dashboard" inside the shared layout.

**Deliverable:** `panther web` starts a server; opening the browser shows a sidebar + header + placeholder content.

**Acceptance criteria:**
- `pip install -e ".[web]"` installs nicegui and niceguicrud without errors.
- `panther web` starts the server and prints the URL.
- Navigating to `http://localhost:8080` shows the layout with working sidebar links.
- `--reload` flag enables NiceGUI's hot-reload mode.

**Key files to touch:**
- `panther/cli_click/commands/web.py` (new)
- `panther/webapp/app.py` (new)
- `panther/webapp/components/layout.py` (new)
- `panther/webapp/pages/dashboard.py` (new)
- `panther/cli_click/core/main.py` (add "web" to `commands_to_register`)
- `panther/webapp/__init__.py` (update imports)

---

### Week 2: Plugin Browser Page

**Tasks:**
1. Create `panther/webapp/services/plugin_service.py` -- wraps `PluginManager`.
   - Method `list_all()`: returns list of dicts with plugin name, type, protocol, roles.
   - Method `get_metadata(name)`: returns detailed plugin info.
   - Instantiate `PluginManager` with `GlobalConfig` defaults (no experiment needed).
2. Create `panther/webapp/pages/plugins.py` -- the `/plugins` page.
   - Table listing all discovered plugins (IUTs, testers, environments, protocols).
   - Columns: Name, Type, Protocol, Supported Roles.
   - Use `ui.table` with rows from `plugin_service.list_all()`.
   - Optional: click a row to see plugin details in an expansion panel.

**Deliverable:** `/plugins` page shows a table of all installed PANTHER plugins.

**Acceptance criteria:**
- Table renders without errors, even if no plugins are found (empty state message).
- Plugin types (IUT, tester, environment, protocol) are visually distinguishable (badge or color).
- Page loads in under 2 seconds.

**Key files to touch:**
- `panther/webapp/services/plugin_service.py` (new)
- `panther/webapp/pages/plugins.py` (new)
- `panther/webapp/app.py` (register the page)

---

### Week 3: Dashboard + Config Viewer

**Tasks:**
1. Create `panther/webapp/services/config_service.py` -- wraps config loading.
   - Method `load_yaml(path)`: reads a YAML file, returns dict.
   - Method `validate(data)`: parses through Pydantic models, returns errors or validated config.
   - Method `list_configs()`: scans `experiment-config/` for YAML files.
2. Create `panther/webapp/components/stat_cards.py` -- reusable stat card component.
   - Shows a label, a number, and an optional icon/color.
3. Update `panther/webapp/pages/dashboard.py`:
   - Show stat cards: number of config files, number of plugins, number of output directories.
   - Show a list of recent config files from `experiment-config/` with "View" buttons.
   - "View" button opens a read-only YAML display using `ui.code` with YAML syntax highlighting.

**Deliverable:** Dashboard shows stats and a config file browser. Clicking a config shows its YAML.

**Acceptance criteria:**
- Stats update on page load (no hard-coded numbers).
- Config list shows real files from `experiment-config/`.
- YAML display is read-only and syntax-highlighted.
- Empty states handled (no configs found, no outputs yet).

**Key files to touch:**
- `panther/webapp/services/config_service.py` (new)
- `panther/webapp/components/stat_cards.py` (new)
- `panther/webapp/pages/dashboard.py` (update)

---

## Phase 2: Core MVP (Weeks 4-7) -- "Config -> Launch -> Monitor"

Goal: Users can build a config, launch an experiment, and watch it run.

### Week 4: Config Builder -- Global Config Forms

**Tasks:**
1. Create `panther/webapp/pages/config_builder.py` -- the `/config` page.
2. Use NiceCRUD to generate forms for `GlobalConfig` sub-models:
   - `LoggingConfig` (log level, format, color toggle)
   - `DockerConfig` (force build, buildx, cache settings)
   - `PathsConfig` (output dir, log dir)
   - `ProgressConfig` (progress bar, spinner toggles)
3. Layout: accordion/expansion panels, one per config section.
4. Wire form changes to an in-memory `GlobalConfig` Pydantic instance.
5. Add a "Validate" button that runs `GlobalConfig(**form_data)` and shows errors.

**Deliverable:** `/config` page with working forms for global config sections. Validation feedback on errors.

**Acceptance criteria:**
- All fields from GlobalConfig render as appropriate form inputs (text, number, toggle, select).
- Invalid values (e.g., negative port) show Pydantic validation errors inline.
- Changing a field updates the in-memory model (verify by printing to console).
- NiceCRUD forms match the Pydantic model fields -- no missing fields.

**Key files to touch:**
- `panther/webapp/pages/config_builder.py` (new)
- `panther/webapp/app.py` (register page)

---

### Week 5: Test Config Forms + YAML Sync

**Tasks:**
1. Extend `config_builder.py` with TestConfig editing:
   - Test name, description, iterations, timeout.
   - Service configuration: name, implementation, protocol, role, target, ports.
   - Network environment: type selector (docker_compose, localhost, shadow).
2. Create `panther/webapp/components/yaml_editor.py` -- CodeMirror YAML editor.
   - Use `ui.codemirror` with YAML mode (or `ui.textarea` with monospace font as fallback).
3. Implement two-way sync:
   - Form -> YAML: on any form change, `model.model_dump()` -> `yaml.dump()` -> update editor.
   - YAML -> Form: on editor change (debounced), `yaml.safe_load()` -> validate -> update form.
4. Add "Save as YAML" button that writes the config to `experiment-config/`.

**Deliverable:** Full config builder with forms and live YAML preview. Save to file.

**Acceptance criteria:**
- Editing a form field updates the YAML preview within 500ms.
- Editing the YAML updates the form fields (after a 1s debounce).
- Invalid YAML shows a parse error, does not crash.
- Pydantic validation errors from YAML edits show in the form.
- "Save as YAML" writes a valid, loadable config file.

**Key files to touch:**
- `panther/webapp/pages/config_builder.py` (extend)
- `panther/webapp/components/yaml_editor.py` (new)
- `panther/webapp/services/config_service.py` (add save method)

---

### Week 6: Experiment Launch

**Tasks:**
1. Create `panther/webapp/services/experiment_service.py`:
   - Method `launch(config_path)`: loads config, creates ExperimentManager, runs in background thread.
   - Method `get_status()`: returns current experiment state (idle, running, completed, failed).
   - Method `stop()`: signals the experiment to stop (best-effort).
   - Stores a reference to the running thread and the WebObserver.
2. Create `panther/webapp/pages/experiments.py` -- the `/experiments` page.
   - Config file selector (dropdown of files from `experiment-config/`).
   - "Launch" button that calls `experiment_service.launch()`.
   - Status indicator showing current state.
   - Disable "Launch" while an experiment is already running.

**Deliverable:** Users can select a config and start an experiment from the browser.

**Acceptance criteria:**
- Launching an experiment starts a background thread (does not block the UI).
- Status indicator updates to "Running" when experiment starts.
- Status updates to "Completed" or "Failed" when experiment finishes.
- Starting a second experiment while one is running shows an error.
- Server logs show experiment events flowing through ExperimentManager.

**Key files to touch:**
- `panther/webapp/services/experiment_service.py` (new)
- `panther/webapp/pages/experiments.py` (new)
- `panther/webapp/app.py` (register page, instantiate service)

---

### Week 7: Real-Time Monitoring

**Tasks:**
1. Implement `WebObserver` in `experiment_service.py` (subclass `GUIObserver`).
   - Override `update_gui(event)` to push events to subscribed UI components.
   - Register the observer with `EventManager` when an experiment launches.
2. Create `panther/webapp/components/log_viewer.py`:
   - Uses `ui.log` to display scrolling log messages.
   - Subscribes to `WebObserver` for real-time events.
   - Color-code by event type (test=blue, error=red, service=green).
3. Update `pages/experiments.py`:
   - Add a progress bar that tracks experiment completion (% of tests done).
   - Add the log viewer component below the progress bar.
   - Show per-test status cards (pending, running, passed, failed).

**Deliverable:** Live experiment monitoring with progress bar, log viewer, and test status cards.

**Acceptance criteria:**
- Log viewer shows events as they happen (within 1s of the event firing).
- Progress bar advances as tests complete.
- Test status cards update from "pending" to "running" to "passed/failed".
- No UI freezes during long-running experiments.
- Works with at least one real experiment config (e.g., the minimal example).

**Key files to touch:**
- `panther/webapp/services/experiment_service.py` (add WebObserver)
- `panther/webapp/components/log_viewer.py` (new)
- `panther/webapp/pages/experiments.py` (update)

---

## Phase 3: Results + Polish (Weeks 8-10)

### Week 8: Results Browser

**Tasks:**
1. Create `panther/webapp/services/results_service.py`:
   - Method `list_experiments()`: scans `outputs/` for experiment directories.
   - Method `get_experiment(path)`: returns metadata (date, test count, status).
   - Method `get_test_result(path)`: reads individual test output files.
2. Create `panther/webapp/pages/results.py` -- the `/results` page.
   - Table of past experiments: date, name, number of tests, overall status.
   - Click to expand: per-test results (name, status, duration).
   - "View logs" button opens log files in a read-only text viewer.
   - "View YAML" button shows the config that was used for the experiment.

**Deliverable:** `/results` page browsing all past experiment outputs.

**Acceptance criteria:**
- Lists all directories under `outputs/`.
- Shows correct test counts and statuses from output files.
- Log viewer displays log file contents.
- Works with real output from a previously-run experiment.
- Empty state handled (no experiments run yet).

**Key files to touch:**
- `panther/webapp/services/results_service.py` (new)
- `panther/webapp/pages/results.py` (new)
- `panther/webapp/app.py` (register page)

---

### Week 9: UX Polish + Error Handling

**Tasks:**
1. Add toast notifications for user actions (experiment started, config saved, validation error).
   - Use `ui.notify()` from NiceGUI.
2. Add loading spinners for async operations (plugin loading, config validation).
3. Add confirmation dialogs for destructive actions (overwrite config, stop experiment).
4. Improve error handling:
   - Catch exceptions in all service methods, return user-friendly messages.
   - Show a global error banner if the server loses connection to the browser.
5. Responsive layout adjustments (test on different window sizes).
6. Add favicon and PANTHER branding to header.

**Deliverable:** Polished UI with proper feedback for all user actions and error states.

**Acceptance criteria:**
- No unhandled exceptions visible to the user (all errors show as toast or error panel).
- All async operations show loading indicators.
- Destructive actions require confirmation.
- UI is usable at 1280x720 and 1920x1080 screen sizes.

**Key files to touch:**
- All files in `pages/` and `components/` (incremental updates)
- `panther/webapp/components/layout.py` (branding, error handling)

---

### Week 10: Testing + Documentation

**Tasks:**
1. Write unit tests in `tests/unit/test_webapp/`:
   - `test_config_service.py` -- config loading, validation, save.
   - `test_plugin_service.py` -- plugin listing, metadata retrieval.
   - `test_results_service.py` -- output directory scanning.
   - `test_experiment_service.py` -- launch/status/stop lifecycle.
2. Write integration tests:
   - `test_pages.py` -- use NiceGUI's test client to verify pages render without errors.
3. Add docstrings to all public functions in services/ and pages/.
4. Update this TASKS.md with final status of each feature.
5. Update README.md feature status table.

**Deliverable:** Test suite with >70% coverage on webapp code. All public APIs documented.

**Acceptance criteria:**
- `pytest tests/unit/test_webapp/ -v` passes.
- Coverage report shows >70% on `panther/webapp/` (excluding `_legacy/`).
- All service classes have docstrings.
- README.md feature status table is accurate.

**Key files to touch:**
- `tests/unit/test_webapp/` (new directory, all test files)
- All files in `panther/webapp/` (docstrings)
- `panther/webapp/README.md` (status update)

---

## Phase 4: Thesis Writing (Weeks 11-12)

### Week 11: Thesis Draft

- Write the webapp chapter: motivation, architecture, implementation decisions.
- Include screenshots of the working dashboard.
- Document the NiceGUI/NiceCRUD evaluation process and comparison with alternatives.
- Describe the integration with PANTHER core (observer pattern, service layer).

### Week 12: Thesis Revision + Defense Prep

- Revise based on advisor feedback.
- Prepare demo for thesis defense (scripted walkthrough of config -> launch -> monitor -> results).
- Final code cleanup and README updates.

---

## Risk Mitigation

| Risk                                       | Mitigation                                              |
|--------------------------------------------|---------------------------------------------------------|
| NiceCRUD does not handle nested Pydantic models well | Fall back to manual NiceGUI forms for complex nested models. Budget Week 4 for discovery. |
| ExperimentManager blocks unexpectedly       | Run in daemon thread with timeout. Add a "Force Stop" button. |
| NiceGUI hot reload breaks during development | Use `--no-reload` and manual restart as fallback.       |
| Scope creep (adding features beyond MVP)    | Refer to "Not in Scope" list in ARCHITECTURE.md. Only add features if ahead of schedule. |
| Plugin discovery slow on first load         | Cache plugin list in memory after first scan. Show loading spinner. |
