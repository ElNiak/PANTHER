"""PANTHER webapp UI components --- reusable NiceGUI building blocks for the dashboard.

This package contains self-contained, composable UI components that
pages assemble to build their interfaces.  Each component renders
into the currently active NiceGUI container, making them embeddable
in cards, dialogs, expansion panels, or full-page layouts.

Component catalog
-----------------

**Forms and editors**

- ``config_form_panel`` -- renders a PydanticForm inside an expansion
  panel for a single config section (logging, services, etc.).
- ``TestListEditor`` -- interactive list editor for adding, removing,
  and reordering test configurations.
- ``YamlEditor`` (not re-exported) -- CodeMirror-based YAML text
  editor with syntax highlighting.
- ``PydanticForm`` (not re-exported) -- recursive Pydantic-to-NiceGUI
  form renderer; the core of the config builder page.
- ``dict_list_widgets`` (not re-exported) -- custom NiceGUI widgets
  for Dict and List[BaseModel] fields.

**Display and visualization**

- ``metrics_panel`` -- renders charts and tables for experiment
  metrics (timing, throughput, error rates).
- ``event_viewer`` -- live-scrolling event log with importance-based
  color coding and filtering.
- ``test_detail_panel`` -- tabbed detail view for a single test
  result (summary, events, artifacts).
- ``plugin_card`` -- compact card showing plugin name, type, and
  version with a click-to-expand affordance.
- ``render_plugin_detail`` -- expanded detail view for a plugin
  (capabilities, supported protocols, metadata).
- ``service_health_card`` -- status card for a running service
  (healthy/degraded/down indicators).
- ``service_log_browser`` -- scrollable log viewer for per-service
  output with auto-scroll.
- ``stat_cards`` (not re-exported) -- small KPI cards for the
  dashboard summary row.
- ``TopologyEditor`` (not re-exported) -- vis.js Network graph for
  visual experiment topology editing.

**Status and feedback**

- ``status_badge`` -- colored badge reflecting experiment or service
  status (running, passed, failed, idle).
- ``ExperimentProgress`` -- animated progress bar bound to experiment
  phase transitions.
- ``error_boundary`` -- wraps a callable and renders a friendly error
  card if it raises.
- ``notify_success``, ``notify_error``, ``notify_warning``,
  ``notify_info`` -- thin wrappers around ``ui.notify`` with
  consistent styling.

**Navigation**

- ``layout`` (not re-exported) -- shared page shell with sidebar
  navigation, header, and status indicator.
"""

from panther.webapp.components.config_form_panel import config_form_panel
from panther.webapp.components.error_boundary import error_boundary
from panther.webapp.components.event_viewer import event_viewer
from panther.webapp.components.metrics_panel import metrics_panel
from panther.webapp.components.notifications import (
    notify_error,
    notify_info,
    notify_success,
    notify_warning,
)
from panther.webapp.components.plugin_card import plugin_card
from panther.webapp.components.plugin_detail_panel import render_plugin_detail
from panther.webapp.components.progress_bar import ExperimentProgress
from panther.webapp.components.service_health_card import service_health_card
from panther.webapp.components.service_log_browser import service_log_browser
from panther.webapp.components.status_badge import status_badge
from panther.webapp.components.test_detail_panel import test_detail_panel
from panther.webapp.components.test_list_editor import TestListEditor
