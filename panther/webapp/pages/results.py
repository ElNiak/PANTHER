"""Results page — browse past experiment outputs with charts and tabbed detail."""

import logging
from collections import defaultdict

from nicegui import app, ui

from panther.webapp.components.error_boundary import error_boundary
from panther.webapp.components.event_viewer import event_viewer
from panther.webapp.components.metrics_panel import metrics_panel
from panther.webapp.components.service_health_card import service_health_card
from panther.webapp.components.stat_cards import stat_card
from panther.webapp.components.test_detail_panel import test_detail_panel
from panther.webapp.services.results_service import ResultsService

logger = logging.getLogger(__name__)

_ARTIFACT_ICONS = {
    ".pcap": "lan",
    ".json": "data_object",
    ".csv": "table_chart",
    ".yaml": "settings",
    ".yml": "settings",
    ".log": "terminal",
}


def content():
    """Render the results browser page content."""
    output_dir = app.storage.general.get("output_dir", "outputs")
    results_svc = ResultsService(output_dir)

    ui.label("Experiment Results").classes("text-h5 q-mb-md")

    experiments = results_svc.list_experiments()

    # --- Summary stat cards ---
    with error_boundary("Summary Stats"):
        _render_summary_cards(experiments)

    if not experiments:
        with ui.card().classes("w-full q-pa-lg text-center"):
            ui.icon("inbox", size="xl").classes("text-grey-5")
            ui.label("No experiment results found.").classes(
                "text-body1 text-grey-7 q-mt-sm"
            )
            ui.label(f"Looking in: {output_dir}").classes("text-caption text-grey-5")
        return

    # --- Build rows ---
    columns = [
        {
            "name": "date",
            "label": "Date",
            "field": "date",
            "sortable": True,
            "align": "left",
        },
        {
            "name": "name",
            "label": "Experiment",
            "field": "name",
            "sortable": True,
            "align": "left",
        },
        {"name": "tests", "label": "Tests", "field": "test_count", "align": "center"},
        {"name": "status", "label": "Status", "field": "status", "align": "center"},
    ]
    all_rows = [
        {
            "date": exp["date"],
            "name": exp["name"],
            "test_count": exp.get("test_count", "?"),
            "status": exp.get("status", "unknown"),
            "path": exp.get("path", ""),
        }
        for exp in experiments
    ]

    # --- Filter bar ---
    with ui.row().classes("w-full gap-3 q-mb-md items-end"):
        search_input = (
            ui.input(
                placeholder="Search experiments...",
            )
            .props("outlined dense clearable")
            .classes("col-3")
        )

        status_select = (
            ui.select(
                ["all", "completed", "failed", "interrupted", "timeout", "unknown"],
                value="all",
                label="Status",
            )
            .props("outlined dense")
            .classes("col-2")
        )

        date_from = (
            ui.input(
                label="From",
                placeholder="YYYY-MM-DD",
            )
            .props("outlined dense clearable")
            .classes("col-2")
        )

        date_to = (
            ui.input(
                label="To",
                placeholder="YYYY-MM-DD",
            )
            .props("outlined dense clearable")
            .classes("col-2")
        )

    # --- Table with pagination ---
    table = ui.table(
        columns=columns,
        rows=all_rows,
        row_key="name",
        pagination={"rowsPerPage": 15, "sortBy": "date", "descending": True},
    ).classes("w-full")

    # Status badge slot via Quasar template
    table.add_slot(
        "body-cell-status",
        r"""
        <q-td :props="props">
            <q-badge
                :color="{'completed': 'green', 'passed': 'green', 'failed': 'red',
                          'running': 'amber', 'interrupted': 'orange', 'timeout': 'deep-orange',
                          'unknown': 'grey'}[props.value] || 'grey'"
                :label="props.value"
                class="text-capitalize"
            />
        </q-td>
        """,
    )

    # Bind search to table's built-in filter
    search_input.bind_value_to(table, "filter")

    def _refresh_table():
        status_val = status_select.value
        from_val = date_from.value or ""
        to_val = date_to.value or ""
        filtered = all_rows
        if status_val and status_val != "all":
            filtered = [r for r in filtered if r["status"] == status_val]
        if from_val:
            filtered = [r for r in filtered if r["date"] >= from_val]
        if to_val:
            filtered = [r for r in filtered if r["date"] <= to_val]
        table.rows = filtered

    status_select.on_value_change(lambda _: _refresh_table())
    date_from.on_value_change(lambda _: _refresh_table())
    date_to.on_value_change(lambda _: _refresh_table())

    # --- Detail dialog ---
    detail_dialog = ui.dialog().props("full-width")

    def _on_row_click(e):
        row = e.args[1]
        _show_detail(detail_dialog, results_svc, row)

    table.on("rowClick", _on_row_click)


def _render_summary_cards(experiments: list[dict]):
    """Row of stat cards summarizing all experiments."""
    total = len(experiments)
    completed = sum(1 for e in experiments if e.get("status") == "completed")
    failed = sum(1 for e in experiments if e.get("status") == "failed")
    latest = experiments[0].get("status", "N/A") if experiments else "N/A"

    with ui.row().classes("w-full gap-4 q-mb-md"):
        stat_card("Total Experiments", str(total), icon="science", color="primary")
        stat_card("Completed", str(completed), icon="check_circle", color="green")
        stat_card("Failed", str(failed), icon="error", color="red")
        stat_card("Latest Status", latest.capitalize(), icon="schedule", color="amber")


def _show_detail(dialog: ui.dialog, results_svc: ResultsService, row: dict):
    """Render tabbed detail view in a dialog modal."""
    dialog.clear()
    name = row["name"]
    exp_path = row.get("path", "")

    with dialog:
        with (
            ui.card()
            .classes("w-full")
            .style("display: flex; flex-direction: column; height: 90vh")
        ):
            # Header row with close button
            with (
                ui.row()
                .classes("justify-between items-center w-full q-mb-sm")
                .style("flex-shrink: 0")
            ):
                ui.label(f"Experiment: {name}").classes("text-h6")
                ui.button(icon="close", on_click=dialog.close).props("flat round")

            detail = results_svc.get_experiment_detail(name)
            if not detail:
                ui.label("No details available").classes("text-grey-7")
            else:
                with ui.tabs().classes("w-full").style("flex-shrink: 0") as tabs:
                    summary_tab = ui.tab("Summary", icon="analytics")
                    tests_tab = ui.tab("Tests", icon="science")
                    logs_tab = ui.tab("Logs", icon="terminal")
                    events_tab = ui.tab("Events", icon="event")
                    metrics_tab = ui.tab("Metrics", icon="speed")
                    artifacts_tab = ui.tab("Artifacts", icon="folder_open")

                with (
                    ui.tab_panels(tabs, value=summary_tab)
                    .classes("w-full")
                    .style("flex: 1 1 auto; overflow-y: auto")
                ):
                    with ui.tab_panel(summary_tab):
                        _render_summary_tab(results_svc, detail, exp_path)
                    with ui.tab_panel(tests_tab):
                        _render_tests_tab(results_svc, exp_path)
                    with ui.tab_panel(logs_tab):
                        _render_logs_tab(results_svc, exp_path)
                    with ui.tab_panel(events_tab):
                        _render_events_tab(results_svc, exp_path)
                    with ui.tab_panel(metrics_tab):
                        with error_boundary("Metrics"):
                            metrics_panel(results_svc, exp_path)
                    with ui.tab_panel(artifacts_tab):
                        _render_artifacts_tab(detail)

    dialog.open()


def _render_summary_tab(results_svc: ResultsService, detail: dict, exp_path: str):
    """Summary tab: aggregate stats, bar chart, service health grouped by test, report."""
    # Aggregate stats
    with error_boundary("Aggregate Stats"):
        stats = results_svc.get_aggregate_stats(exp_path) if exp_path else {}
        if stats and stats.get("total", 0) > 0:
            with ui.row().classes("w-full gap-4 q-mb-md"):
                stat_card(
                    "Total Tests",
                    str(stats.get("total", 0)),
                    icon="quiz",
                    color="primary",
                )
                stat_card(
                    "Passed", str(stats.get("passed", 0)), icon="check", color="green"
                )
                stat_card(
                    "Failed", str(stats.get("failed", 0)), icon="close", color="red"
                )
                rate = stats.get("success_rate", 0)
                stat_card("Success Rate", f"{rate:.0f}%", icon="percent", color="blue")
                duration = stats.get("duration")
                if duration is not None:
                    stat_card(
                        "Duration", f"{duration:.1f}s", icon="timer", color="amber"
                    )

    # Bar chart of per-test results with dataZoom for large sets
    with error_boundary("Test Results Chart"):
        test_results = results_svc.get_test_results(exp_path) if exp_path else []
        if test_results:
            names = [r.get("name", f"Test {i}") for i, r in enumerate(test_results)]
            durations = [r.get("duration", 0) or 0 for r in test_results]
            colors = [
                "#4caf50" if r.get("status") in ("passed", "completed") else "#f44336"
                for r in test_results
            ]
            chart_opts = {
                "tooltip": {"trigger": "axis"},
                "xAxis": {
                    "type": "category",
                    "data": names,
                    "axisLabel": {"rotate": 45},
                },
                "yAxis": {"type": "value", "name": "Duration (s)"},
                "series": [
                    {
                        "type": "bar",
                        "data": [
                            {"value": d, "itemStyle": {"color": c}}
                            for d, c in zip(durations, colors)
                        ],
                    }
                ],
            }
            if len(names) > 15:
                chart_opts["dataZoom"] = [
                    {
                        "type": "slider",
                        "xAxisIndex": 0,
                        "start": 0,
                        "end": int(15 / len(names) * 100),
                    },
                    {"type": "inside", "xAxisIndex": 0},
                ]
            ui.echart(chart_opts).classes("w-full").style("height: 400px")

    # Service health — grouped by test
    with error_boundary("Service Health"):
        services = results_svc.get_service_health(exp_path) if exp_path else []
        if services:
            _render_grouped_services(services)

    # Report markdown
    with error_boundary("Report"):
        if detail.get("report_content"):
            ui.label("Report").classes("text-subtitle1 q-mt-md q-mb-sm")
            ui.markdown(detail["report_content"])


def _render_grouped_services(services: list[dict]):
    """Group service health cards by test_name, with expansion panels."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for svc in services:
        test_name = svc.get("test_name", "")
        grouped[test_name].append(svc)

    # If no test_name grouping, show flat
    if len(grouped) == 1 and "" in grouped:
        with ui.expansion(
            f"Service Health ({len(services)})",
            icon="health_and_safety",
            value=len(services) <= 6,
        ).classes("w-full q-mt-md"):
            with ui.row().classes("w-full gap-3 flex-wrap"):
                for svc in services:
                    with ui.element("div").classes("col-12 col-sm-6 col-md-4 col-lg-3"):
                        service_health_card(svc)
        return

    with ui.expansion(
        f"Service Health ({len(services)} services, {len(grouped)} tests)",
        icon="health_and_safety",
        value=len(grouped) <= 4,
    ).classes("w-full q-mt-md"):
        for test_name, test_services in sorted(grouped.items()):
            label = test_name if test_name else "Ungrouped"
            with ui.expansion(
                f"{label} ({len(test_services)})", icon="science"
            ).classes("w-full q-ml-md"):
                with ui.row().classes("w-full gap-3 flex-wrap"):
                    for svc in test_services:
                        with ui.element("div").classes(
                            "col-12 col-sm-6 col-md-4 col-lg-3"
                        ):
                            service_health_card(svc)


def _render_tests_tab(results_svc: ResultsService, exp_path: str):
    """Tests tab: list of tests with drill-down panel."""
    with error_boundary("Tests"):
        tests = results_svc.list_tests(exp_path) if exp_path else []
        if not tests:
            ui.label("No tests found.").classes("text-grey-7")
            return

        # Tests table
        test_columns = [
            {
                "name": "name",
                "label": "Test Name",
                "field": "name",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "status",
                "label": "Status",
                "field": "status",
                "sortable": True,
                "align": "center",
            },
            {
                "name": "duration",
                "label": "Duration (s)",
                "field": "duration",
                "sortable": True,
                "align": "center",
            },
            {
                "name": "services",
                "label": "Services",
                "field": "service_count",
                "align": "center",
            },
            {
                "name": "events",
                "label": "Events",
                "field": "has_events",
                "align": "center",
            },
            {
                "name": "analysis",
                "label": "Analysis",
                "field": "has_analysis",
                "align": "center",
            },
        ]
        test_rows = [
            {
                "name": t["name"],
                "status": t.get("status", "unknown"),
                "duration": f"{t['duration']:.1f}" if t.get("duration") else "-",
                "service_count": t.get("service_count", 0),
                "has_events": "Yes" if t.get("has_events") else "-",
                "has_analysis": "Yes" if t.get("has_analysis") else "-",
            }
            for t in tests
        ]

        test_table = ui.table(
            columns=test_columns,
            rows=test_rows,
            row_key="name",
            pagination={"rowsPerPage": 10, "sortBy": "name"},
        ).classes("w-full")

        # Status badge slot
        test_table.add_slot(
            "body-cell-status",
            r"""
            <q-td :props="props">
                <q-badge
                    :color="{'completed': 'green', 'passed': 'green', 'failed': 'red',
                              'running': 'amber', 'unknown': 'grey'}[props.value] || 'grey'"
                    :label="props.value"
                    class="text-capitalize"
                />
            </q-td>
            """,
        )

        # Detail panel container (rendered below the table when a test is clicked)
        detail_container = ui.column().classes("w-full q-mt-md")

        def _on_test_click(e):
            row = e.args[1]
            test_name = row["name"]
            detail_container.clear()
            with detail_container:
                ui.separator().classes("q-my-sm")
                test_detail_panel(results_svc, exp_path, test_name)

        test_table.on("rowClick", _on_test_click)


def _render_logs_tab(results_svc: ResultsService, exp_path: str):
    """Logs tab: filterable, scrollable code block."""
    with error_boundary("Logs"):
        log_lines = results_svc.read_log_lines(exp_path, tail=1000) if exp_path else []
        if not log_lines:
            ui.label("No logs available").classes("text-grey-7")
            return

        log_filter = (
            ui.input(
                placeholder="Filter logs...",
            )
            .props("outlined dense clearable")
            .classes("w-full q-mb-sm")
        )

        with ui.scroll_area().style("max-height: 600px"):
            code_display = ui.code("\n".join(log_lines)).classes("w-full")

        def _on_filter_change():
            query = (log_filter.value or "").lower()
            if query:
                filtered = [line for line in log_lines if query in line.lower()]
            else:
                filtered = log_lines
            code_display.content = "\n".join(filtered)

        log_filter.on_value_change(lambda _: _on_filter_change())


def _render_events_tab(results_svc: ResultsService, exp_path: str):
    """Events tab: experiment-level events."""
    with error_boundary("Experiment Events"):
        events = results_svc.get_experiment_events(exp_path) if exp_path else []
        if not events:
            ui.label("No experiment events found.").classes("text-grey-7")
            return
        event_viewer(events)


def _render_artifacts_tab(detail: dict):
    """Artifacts tab: organized by test directory, then by extension."""
    with error_boundary("Artifacts"):
        artifacts = detail.get("artifacts", [])
        if not artifacts:
            ui.label("No artifacts found").classes("text-grey-7")
            return

        # Group by test_name first
        by_test: dict[str, list[dict]] = defaultdict(list)
        for artifact in artifacts:
            test_name = artifact.get("test_name", "")
            by_test[test_name].append(artifact)

        for test_name in sorted(by_test.keys()):
            test_artifacts = by_test[test_name]
            label = test_name if test_name else "Experiment-level"

            # Group by extension within each test
            by_ext: dict[str, list[dict]] = defaultdict(list)
            for a in test_artifacts:
                name = a["name"]
                ext = "." + name.rsplit(".", 1)[-1] if "." in name else "(no ext)"
                by_ext[ext].append(a)

            with ui.expansion(
                f"{label} ({len(test_artifacts)} files)", icon="folder"
            ).classes("w-full"):
                for ext, items in sorted(by_ext.items()):
                    icon = _ARTIFACT_ICONS.get(ext, "insert_drive_file")
                    with ui.expansion(f"{ext} ({len(items)})", icon=icon).classes(
                        "w-full q-ml-md"
                    ):
                        for artifact in items:
                            with ui.row().classes("items-center gap-2 q-py-xs"):
                                ui.icon(icon, size="sm").classes("text-grey-7")
                                ui.label(artifact["name"]).classes("text-body2")
