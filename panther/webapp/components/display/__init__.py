"""Display components — data visualization, event logs, plugin browsers."""

from panther.webapp.components.display.event_viewer import event_viewer
from panther.webapp.components.display.highlight_label import (
    HighlightLabel,
    highlight_html,
    highlight_label,
    live_status,
)
from panther.webapp.components.display.log_viewer import LogViewer
from panther.webapp.components.display.metrics_panel import metrics_panel
from panther.webapp.components.display.plugin_card import (
    PLUGIN_STATUS_COLORS,
    plugin_card,
)
from panther.webapp.components.display.plugin_detail_panel import render_plugin_detail
from panther.webapp.components.display.service_health_card import service_health_card
from panther.webapp.components.display.service_log_browser import service_log_browser
from panther.webapp.components.display.stat_cards import stat_card
from panther.webapp.components.display.test_detail_panel import test_detail_panel
