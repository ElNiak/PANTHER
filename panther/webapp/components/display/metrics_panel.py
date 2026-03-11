"""Metrics panel component for the experiment detail dialog."""

import logging
from typing import Any

from nicegui import ui

from panther.webapp.components.display.stat_cards import stat_card
from panther.webapp.components.status.error_boundary import error_boundary

logger = logging.getLogger(__name__)


def metrics_panel(results_svc: Any, exp_path: str) -> None:
    """Render the Metrics tab content for an experiment.

    Shows timing breakdown, resource usage, and error analysis
    from the experiment's ``metrics.json`` (collected via ``--enable-metrics``).
    """
    data = results_svc.get_metrics_data(exp_path)
    if data is None:
        with ui.card().classes("w-full q-pa-lg"):
            ui.icon("info", size="xl").classes("text-grey-5")
            ui.label("No metrics data available").classes("text-h6 text-grey-7")
            ui.label(
                "Run the experiment with --enable-metrics to collect performance data."
            ).classes("text-caption text-grey-6")
        return

    _render_timing_section(data)
    _render_resource_section(data)
    _render_insights_section(data)


def _render_timing_section(data: dict) -> None:
    """Timing breakdown: stat cards + phase bar chart + operation table."""
    with error_boundary("Timing Breakdown"):
        timing = data.get("timing_metrics", {})
        phase_metrics = data.get("phase_metrics", {})
        summary = data.get("summary", {})

        # Stat cards
        total_time = summary.get("total_execution_time")
        timing_count = len(timing) if isinstance(timing, dict) else 0
        with ui.row().classes("w-full gap-4 q-mb-md"):
            if total_time is not None:
                stat_card(
                    "Execution Time",
                    (
                        f"{total_time:.1f}s"
                        if isinstance(total_time, (int, float))
                        else str(total_time)
                    ),
                    icon="timer",
                    color="purple",
                )
            stat_card("Timing Metrics", str(timing_count), icon="speed", color="blue")

        # Phase duration bar chart
        if isinstance(phase_metrics, dict):
            active_phases = {
                k: v
                for k, v in phase_metrics.items()
                if isinstance(v, dict) and v.get("total_time", 0) > 0
            }
            if active_phases:
                names = list(active_phases.keys())
                times = [v.get("total_time", 0) for v in active_phases.values()]
                success_rates = [
                    v.get("success_rate", 1.0) for v in active_phases.values()
                ]
                colors = [
                    "#4caf50" if sr >= 0.8 else "#ff9800" if sr >= 0.5 else "#f44336"
                    for sr in success_rates
                ]

                ui.label("Phase Durations").classes("text-subtitle2 q-mt-md q-mb-sm")
                chart_opts = {
                    "tooltip": {"trigger": "axis"},
                    "grid": {"left": "25%", "right": "5%"},
                    "xAxis": {"type": "value", "name": "Duration (s)"},
                    "yAxis": {
                        "type": "category",
                        "data": names,
                        "axisLabel": {"width": 150, "overflow": "truncate"},
                    },
                    "series": [
                        {
                            "type": "bar",
                            "data": [
                                {"value": t, "itemStyle": {"color": c}}
                                for t, c in zip(times, colors)
                            ],
                        }
                    ],
                }
                ui.echart(chart_opts).classes("w-full").style("height: 300px")

        # Operation timings table
        if isinstance(timing, dict) and timing:
            ui.label("Operation Timings").classes("text-subtitle2 q-mt-md q-mb-sm")
            rows = sorted(
                [
                    {"operation": k, "duration": round(v, 4)}
                    for k, v in timing.items()
                    if isinstance(v, (int, float))
                ],
                key=lambda r: r["duration"],
                reverse=True,
            )
            columns = [
                {
                    "name": "operation",
                    "label": "Operation",
                    "field": "operation",
                    "sortable": True,
                },
                {
                    "name": "duration",
                    "label": "Duration (s)",
                    "field": "duration",
                    "sortable": True,
                },
            ]
            ui.table(columns=columns, rows=rows, row_key="operation").classes(
                "w-full"
            ).props("dense flat")


def _render_resource_section(data: dict) -> None:
    """Resource usage: stat cards + time-series line chart."""
    with error_boundary("Resource Usage"):
        resource = data.get("resource_metrics", {})
        if not isinstance(resource, dict) or not resource:
            ui.label("No resource metrics recorded.").classes("text-grey-6")
            return

        cpu = resource.get("cpu_usage", {})
        mem = resource.get("memory_usage", {})

        # Stat cards
        with ui.row().classes("w-full gap-4 q-mb-md"):
            if isinstance(cpu, dict) and cpu.get("average") is not None:
                stat_card(
                    "Avg CPU",
                    f"{cpu['average']:.1f}%",
                    icon="memory",
                    color="blue",
                )
                stat_card(
                    "Peak CPU",
                    f"{cpu.get('peak', 0):.1f}%",
                    icon="trending_up",
                    color="orange" if cpu.get("peak", 0) > 80 else "blue",
                )
            if isinstance(mem, dict) and mem.get("average") is not None:
                stat_card(
                    "Avg Memory",
                    f"{mem['average']:.1f}%",
                    icon="storage",
                    color="green",
                )
                stat_card(
                    "Peak Memory",
                    f"{mem.get('peak', 0):.1f}%",
                    icon="trending_up",
                    color="orange" if mem.get("peak", 0) > 80 else "green",
                )

        # Time-series chart from raw metrics
        from panther.core.metrics import MetricsDataLoader

        timeseries = MetricsDataLoader.get_timeseries(data)
        if timeseries:
            ui.label("Resource Usage Over Time").classes(
                "text-subtitle2 q-mt-md q-mb-sm"
            )
            timestamps = [str(t["timestamp"]) for t in timeseries]
            cpu_series = [t.get("cpu_percent") for t in timeseries]
            mem_series = [t.get("memory_percent") for t in timeseries]

            chart_opts = {
                "tooltip": {"trigger": "axis"},
                "legend": {"data": ["CPU %", "Memory %"]},
                "xAxis": {
                    "type": "category",
                    "data": timestamps,
                    "axisLabel": {"rotate": 45},
                },
                "yAxis": {"type": "value", "name": "%", "max": 100},
                "series": [
                    {
                        "name": "CPU %",
                        "type": "line",
                        "data": cpu_series,
                        "smooth": True,
                        "lineStyle": {"color": "#2196f3"},
                        "itemStyle": {"color": "#2196f3"},
                    },
                    {
                        "name": "Memory %",
                        "type": "line",
                        "data": mem_series,
                        "smooth": True,
                        "lineStyle": {"color": "#4caf50"},
                        "itemStyle": {"color": "#4caf50"},
                    },
                ],
            }
            if len(timestamps) > 30:
                chart_opts["dataZoom"] = [
                    {
                        "type": "slider",
                        "xAxisIndex": 0,
                        "start": 0,
                        "end": int(30 / len(timestamps) * 100),
                    },
                    {"type": "inside", "xAxisIndex": 0},
                ]
            ui.echart(chart_opts).classes("w-full").style("height: 350px")


def _render_insights_section(data: dict) -> None:
    """Error analysis + performance insights."""
    with error_boundary("Performance Insights"):
        from panther.core.metrics import MetricsDataLoader

        insights = MetricsDataLoader.get_performance_insights(data)
        error_metrics = data.get("error_metrics", {})

        # Stat cards
        score = insights.get("performance_score", "unknown")
        score_color = {
            "excellent": "green",
            "good": "blue",
            "fair": "orange",
            "poor": "red",
        }.get(score, "grey")
        score_icon = {
            "excellent": "emoji_events",
            "good": "thumb_up",
            "fair": "warning",
            "poor": "error",
        }.get(score, "help")

        total_errors = (
            error_metrics.get("total_errors", 0)
            if isinstance(error_metrics, dict)
            else 0
        )

        with ui.row().classes("w-full gap-4 q-mb-md"):
            stat_card(
                "Performance",
                score.capitalize(),
                icon=score_icon,
                color=score_color,
            )
            stat_card(
                "Total Errors",
                str(total_errors),
                icon="bug_report",
                color="red" if total_errors > 0 else "green",
            )

        # Alerts
        alerts = insights.get("alerts", [])
        if alerts:
            ui.label("Alerts").classes("text-subtitle2 q-mt-md q-mb-sm")
            for alert in alerts:
                color_cls = (
                    "text-red-9 bg-red-1"
                    if "Critical" in alert
                    else "text-orange-9 bg-orange-1"
                )
                with ui.card().classes(f"w-full q-pa-sm q-mb-xs {color_cls}"):
                    ui.label(alert).classes("text-caption")

        # Bottlenecks
        bottlenecks = insights.get("bottlenecks", [])
        if bottlenecks:
            ui.label("Bottlenecks").classes("text-subtitle2 q-mt-md q-mb-sm")
            rows = [
                {
                    "operation": b["operation"],
                    "avg_time": round(b["average_time"], 2),
                    "total_time": round(b["total_time"], 2),
                }
                for b in bottlenecks
            ]
            columns = [
                {
                    "name": "operation",
                    "label": "Operation",
                    "field": "operation",
                    "sortable": True,
                },
                {
                    "name": "avg_time",
                    "label": "Avg Time (s)",
                    "field": "avg_time",
                    "sortable": True,
                },
                {
                    "name": "total_time",
                    "label": "Total Time (s)",
                    "field": "total_time",
                    "sortable": True,
                },
            ]
            ui.table(columns=columns, rows=rows, row_key="operation").classes(
                "w-full"
            ).props("dense flat")

        # Recommendations
        recommendations = insights.get("recommendations", [])
        if recommendations:
            ui.label("Recommendations").classes("text-subtitle2 q-mt-md q-mb-sm")
            for rec in recommendations:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("lightbulb", size="sm").classes("text-amber")
                    ui.label(rec).classes("text-caption")

        # Error category pie chart
        if isinstance(error_metrics, dict):
            categories = error_metrics.get("error_categories", {})
            if isinstance(categories, dict) and categories:
                ui.label("Error Distribution").classes("text-subtitle2 q-mt-md q-mb-sm")
                pie_data = [
                    {"name": cat, "value": count} for cat, count in categories.items()
                ]
                chart_opts = {
                    "tooltip": {"trigger": "item"},
                    "series": [
                        {
                            "type": "pie",
                            "radius": ["40%", "70%"],
                            "data": pie_data,
                            "emphasis": {
                                "itemStyle": {
                                    "shadowBlur": 10,
                                    "shadowOffsetX": 0,
                                    "shadowColor": "rgba(0, 0, 0, 0.5)",
                                }
                            },
                        }
                    ],
                }
                ui.echart(chart_opts).classes("w-full").style("height: 300px")

            # Error timeline table
            timeline = error_metrics.get("error_timeline", [])
            if isinstance(timeline, list) and timeline:
                ui.label("Error Timeline").classes("text-subtitle2 q-mt-md q-mb-sm")
                rows = [
                    {
                        "phase": e.get("phase", ""),
                        "component": e.get("component", ""),
                        "error_type": e.get("error_type", ""),
                        "message": e.get("error_message", ""),
                    }
                    for e in timeline[:50]  # Limit to 50 entries
                ]
                columns = [
                    {
                        "name": "phase",
                        "label": "Phase",
                        "field": "phase",
                        "sortable": True,
                    },
                    {
                        "name": "component",
                        "label": "Component",
                        "field": "component",
                        "sortable": True,
                    },
                    {
                        "name": "error_type",
                        "label": "Type",
                        "field": "error_type",
                        "sortable": True,
                    },
                    {"name": "message", "label": "Message", "field": "message"},
                ]
                ui.table(columns=columns, rows=rows, row_key="message").classes(
                    "w-full"
                ).props("dense flat")
