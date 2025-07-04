"""Grafana dashboard configurations for ATLAS governance monitoring."""

import json
from typing import Dict, Any, List

def create_governance_dashboard() -> Dict[str, Any]:
    """Create main governance monitoring dashboard configuration."""
    return {
        "dashboard": {
            "id": None,
            "title": "ATLAS MCP Tool Governance",
            "tags": ["atlas", "governance", "mcp", "monitoring"],
            "timezone": "browser",
            "refresh": "5s",
            "time": {
                "from": "now-6h",
                "to": "now"
            },
            "timepicker": {
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m"],
                "time_options": ["1h", "6h", "12h", "24h", "7d"]
            },
            "panels": [
                {
                    "id": 1,
                    "title": "Governance Compliance Score",
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "atlas_governance_compliance_score",
                            "legendFormat": "Current Score",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "min": 0,
                            "max": 1,
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "red", "value": 0},
                                    {"color": "red", "value": 0.7},
                                    {"color": "yellow", "value": 0.85},
                                    {"color": "green", "value": 0.95}
                                ]
                            }
                        }
                    },
                    "options": {
                        "colorMode": "background",
                        "graphMode": "area",
                        "justifyMode": "center",
                        "orientation": "horizontal"
                    }
                },
                {
                    "id": 2,
                    "title": "Tool Usage Count",
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                    "targets": [
                        {
                            "expr": "sum(increase(atlas_tool_usage_total[1h]))",
                            "legendFormat": "Tools/Hour",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "color": {"mode": "palette-classic"}
                        }
                    }
                },
                {
                    "id": 3,
                    "title": "Governance Violations",
                    "type": "stat", 
                    "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "sum(increase(atlas_governance_violations_total[1h]))",
                            "legendFormat": "Violations/Hour",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 5},
                                    {"color": "red", "value": 15}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 4,
                    "title": "Average Processing Time",
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                    "targets": [
                        {
                            "expr": "avg(atlas_governance_performance_ms)",
                            "legendFormat": "Avg Time (ms)",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ms",
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 5},
                                    {"color": "red", "value": 10}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 5,
                    "title": "Compliance Score Trend",
                    "type": "timeseries",
                    "gridPos": {"h": 9, "w": 12, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "atlas_governance_compliance_score",
                            "legendFormat": "Compliance Score",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "min": 0,
                            "max": 1,
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "fillOpacity": 10
                            }
                        }
                    },
                    "options": {
                        "legend": {"displayMode": "visible"},
                        "tooltip": {"mode": "single"}
                    }
                },
                {
                    "id": 6,
                    "title": "Tool Performance Distribution",
                    "type": "timeseries",
                    "gridPos": {"h": 9, "w": 12, "x": 12, "y": 8},
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, atlas_governance_performance_ms_bucket)",
                            "legendFormat": "95th percentile",
                            "refId": "A"
                        },
                        {
                            "expr": "histogram_quantile(0.50, atlas_governance_performance_ms_bucket)",
                            "legendFormat": "Median",
                            "refId": "B"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ms",
                            "custom": {"drawStyle": "line"}
                        }
                    }
                },
                {
                    "id": 7,
                    "title": "Violations by Type",
                    "type": "piechart",
                    "gridPos": {"h": 9, "w": 8, "x": 0, "y": 17},
                    "targets": [
                        {
                            "expr": "sum by (violation_type) (atlas_governance_violations_total)",
                            "legendFormat": "{{violation_type}}",
                            "refId": "A"
                        }
                    ],
                    "options": {
                        "pieType": "pie",
                        "legend": {"displayMode": "table", "placement": "right"}
                    }
                },
                {
                    "id": 8,
                    "title": "Tool Usage by Category",
                    "type": "barchart",
                    "gridPos": {"h": 9, "w": 8, "x": 8, "y": 17},
                    "targets": [
                        {
                            "expr": "sum by (category) (atlas_tool_usage_total)",
                            "legendFormat": "{{category}}",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "custom": {"orientation": "horizontal"}
                        }
                    }
                },
                {
                    "id": 9,
                    "title": "Information Entropy Distribution", 
                    "type": "histogram",
                    "gridPos": {"h": 9, "w": 8, "x": 16, "y": 17},
                    "targets": [
                        {
                            "expr": "atlas_entropy_average",
                            "legendFormat": "Entropy Score",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "min": 0,
                            "max": 1
                        }
                    }
                }
            ],
            "annotations": {
                "list": [
                    {
                        "name": "Governance Violations",
                        "enable": True,
                        "iconColor": "red",
                        "type": "tags",
                        "tags": ["governance", "violation"]
                    }
                ]
            }
        }
    }

def create_violation_details_dashboard() -> Dict[str, Any]:
    """Create detailed violations analysis dashboard."""
    return {
        "dashboard": {
            "id": None,
            "title": "ATLAS Governance Violations Analysis",
            "tags": ["atlas", "governance", "violations", "analysis"],
            "timezone": "browser",
            "refresh": "10s",
            "time": {
                "from": "now-24h",
                "to": "now"
            },
            "panels": [
                {
                    "id": 1,
                    "title": "Violation Timeline",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "sum by (violation_type) (rate(atlas_governance_violations_total[5m]))",
                            "legendFormat": "{{violation_type}}",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short",
                            "custom": {"drawStyle": "line", "stacking": {"mode": "normal"}}
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "Top Violating Tools",
                    "type": "table",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "targets": [
                        {
                            "expr": "topk(10, sum by (tool_name) (atlas_governance_violations_total))",
                            "format": "table",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {"custom": {"displayMode": "basic"}}
                    }
                },
                {
                    "id": 3,
                    "title": "Violation Severity Breakdown",
                    "type": "piechart",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "targets": [
                        {
                            "expr": "sum by (severity) (atlas_governance_violations_total)",
                            "legendFormat": "{{severity}}",
                            "refId": "A"
                        }
                    ]
                }
            ]
        }
    }

def create_performance_dashboard() -> Dict[str, Any]:
    """Create performance monitoring dashboard."""
    return {
        "dashboard": {
            "id": None,
            "title": "ATLAS Governance Performance",
            "tags": ["atlas", "governance", "performance"],
            "timezone": "browser", 
            "refresh": "5s",
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "panels": [
                {
                    "id": 1,
                    "title": "Governance Overhead",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [
                        {
                            "expr": "atlas_governance_performance_ms",
                            "legendFormat": "Processing Time (ms)",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ms",
                            "custom": {"drawStyle": "line"}
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "Tool Execution Success Rate",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [
                        {
                            "expr": "rate(atlas_tool_success_total[5m]) / rate(atlas_tool_usage_total[5m])",
                            "legendFormat": "Success Rate",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percentunit",
                            "min": 0,
                            "max": 1
                        }
                    }
                }
            ]
        }
    }

def generate_all_dashboards() -> List[Dict[str, Any]]:
    """Generate all dashboard configurations."""
    return [
        create_governance_dashboard(),
        create_violation_details_dashboard(), 
        create_performance_dashboard()
    ]

def save_dashboard_configs(output_dir: str = "~/.atlas/dashboards") -> None:
    """Save all dashboard configurations to files."""
    from pathlib import Path
    
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(exist_ok=True)
    
    dashboards = {
        "governance_main.json": create_governance_dashboard(),
        "violations_analysis.json": create_violation_details_dashboard(),
        "performance_monitoring.json": create_performance_dashboard()
    }
    
    for filename, config in dashboards.items():
        filepath = output_path / filename
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
            
    print(f"Dashboard configurations saved to {output_path}")

def create_prometheus_rules() -> Dict[str, Any]:
    """Create Prometheus alerting rules."""
    return {
        "groups": [
            {
                "name": "atlas_governance_alerts",
                "rules": [
                    {
                        "alert": "GovernanceComplianceLow",
                        "expr": "atlas_governance_compliance_score < 0.8",
                        "for": "2m",
                        "labels": {"severity": "warning"},
                        "annotations": {
                            "summary": "ATLAS governance compliance score is low",
                            "description": "Compliance score has been below 0.8 for more than 2 minutes"
                        }
                    },
                    {
                        "alert": "GovernanceViolationsHigh", 
                        "expr": "rate(atlas_governance_violations_total[5m]) > 0.1",
                        "for": "1m",
                        "labels": {"severity": "warning"},
                        "annotations": {
                            "summary": "High rate of governance violations",
                            "description": "Governance violations are occurring at rate > 0.1/sec"
                        }
                    },
                    {
                        "alert": "GovernancePerformanceDegraded",
                        "expr": "atlas_governance_performance_ms > 10",
                        "for": "30s",
                        "labels": {"severity": "warning"},
                        "annotations": {
                            "summary": "Governance processing time is high", 
                            "description": "Governance processing time is above 10ms threshold"
                        }
                    }
                ]
            }
        ]
    }