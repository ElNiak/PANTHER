"""PANTHER webapp UI components --- reusable NiceGUI building blocks for the dashboard.

This package contains self-contained, composable UI components that
pages assemble to build their interfaces.  Each component renders
into the currently active NiceGUI container, making them embeddable
in cards, dialogs, expansion panels, or full-page layouts.

Sub-packages
------------

``forms/``
    Form rendering: PydanticForm, YamlEditor, ConfigFormPanel,
    TestListEditor, DictListWidgets, form model introspection,
    plugin-to-form bridging.

``display/``
    Data visualisation: MetricsPanel, EventViewer, TestDetailPanel,
    PluginCard, PluginDetailPanel, ServiceHealthCard,
    ServiceLogBrowser, StatCards, LogViewer.

``status/``
    Feedback: StatusBadge, ExperimentProgress, ErrorBoundary,
    Notifications.

``topology/``
    Visual topology editor (thesis student work).

``layout.py``
    Shared page shell (sidebar, header, status indicator).
"""

try:
    from panther.webapp.components.display.event_viewer import event_viewer
    from panther.webapp.components.display.metrics_panel import metrics_panel
    from panther.webapp.components.display.plugin_card import plugin_card
    from panther.webapp.components.display.plugin_detail_panel import (
        render_plugin_detail,
    )
    from panther.webapp.components.display.service_health_card import (
        service_health_card,
    )
    from panther.webapp.components.display.service_log_browser import (
        service_log_browser,
    )
    from panther.webapp.components.display.test_detail_panel import test_detail_panel
    from panther.webapp.components.forms.config_form_panel import config_form_panel
    from panther.webapp.components.forms.test_list_editor import TestListEditor
    from panther.webapp.components.status.error_boundary import error_boundary
    from panther.webapp.components.status.notifications import (
        notify_error,
        notify_info,
        notify_success,
        notify_warning,
    )
    from panther.webapp.components.status.progress_bar import ExperimentProgress
    from panther.webapp.components.status.status_badge import status_badge

    __all__ = [
        "event_viewer",
        "metrics_panel",
        "plugin_card",
        "render_plugin_detail",
        "service_health_card",
        "service_log_browser",
        "test_detail_panel",
        "config_form_panel",
        "TestListEditor",
        "error_boundary",
        "notify_error",
        "notify_info",
        "notify_success",
        "notify_warning",
        "ExperimentProgress",
        "status_badge",
    ]
except ImportError:
    __all__ = []
