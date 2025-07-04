"""Real-time governance metrics collection and monitoring."""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
import os

@dataclass
class GovernanceMetrics:
    """Governance metrics data structure."""
    timestamp: float
    compliance_score: float
    violation_count: int
    tool_usage_count: int
    entropy_average: float
    performance_ms: float
    session_id: str
    
    def to_prometheus_format(self) -> str:
        """Convert metrics to Prometheus format."""
        timestamp_ms = int(self.timestamp * 1000)
        return f"""# HELP atlas_governance_compliance_score Current compliance score (0-1)
# TYPE atlas_governance_compliance_score gauge
atlas_governance_compliance_score{{session_id="{self.session_id}"}} {self.compliance_score} {timestamp_ms}

# HELP atlas_governance_violations_total Total governance violations
# TYPE atlas_governance_violations_total counter  
atlas_governance_violations_total{{session_id="{self.session_id}"}} {self.violation_count} {timestamp_ms}

# HELP atlas_tool_usage_total Total tool usage count
# TYPE atlas_tool_usage_total counter
atlas_tool_usage_total{{session_id="{self.session_id}"}} {self.tool_usage_count} {timestamp_ms}

# HELP atlas_entropy_average Average information entropy
# TYPE atlas_entropy_average gauge
atlas_entropy_average{{session_id="{self.session_id}"}} {self.entropy_average} {timestamp_ms}

# HELP atlas_governance_performance_ms Governance processing time
# TYPE atlas_governance_performance_ms gauge
atlas_governance_performance_ms{{session_id="{self.session_id}"}} {self.performance_ms} {timestamp_ms}
"""

@dataclass
class ToolUsageMetric:
    """Individual tool usage metric."""
    tool_name: str
    category: str
    execution_time_ms: float
    success: bool
    compliance_score: float
    entropy_score: Optional[float] = None
    violation_type: Optional[str] = None

class GovernanceMetricsCollector:
    """Collects and manages governance metrics for monitoring."""
    
    def __init__(self, metrics_dir: str = "~/.atlas"):
        """Initialize metrics collector."""
        self.metrics_dir = Path(metrics_dir).expanduser()
        self.metrics_dir.mkdir(exist_ok=True)
        
        self.session_metrics: List[GovernanceMetrics] = []
        self.tool_metrics: List[ToolUsageMetric] = []
        self.session_id = f"session_{int(time.time())}"
        
        # Performance tracking
        self.start_time = time.time()
        self.last_metrics_export = time.time()
        
    def record_tool_usage(self, tool_name: str, category: str, 
                         execution_time_ms: float, success: bool,
                         compliance_score: float, entropy_score: Optional[float] = None,
                         violation_type: Optional[str] = None) -> None:
        """Record individual tool usage metrics."""
        metric = ToolUsageMetric(
            tool_name=tool_name,
            category=category,
            execution_time_ms=execution_time_ms,
            success=success,
            compliance_score=compliance_score,
            entropy_score=entropy_score,
            violation_type=violation_type
        )
        
        self.tool_metrics.append(metric)
        
        # Update real-time metrics file
        self._update_realtime_metrics()
        
    def calculate_session_metrics(self) -> GovernanceMetrics:
        """Calculate current session governance metrics."""
        if not self.tool_metrics:
            return GovernanceMetrics(
                timestamp=time.time(),
                compliance_score=1.0,
                violation_count=0,
                tool_usage_count=0,
                entropy_average=0.0,
                performance_ms=0.0,
                session_id=self.session_id
            )
            
        # Calculate aggregate metrics
        total_tools = len(self.tool_metrics)
        violations = len([m for m in self.tool_metrics if m.violation_type])
        
        compliance_scores = [m.compliance_score for m in self.tool_metrics]
        avg_compliance = sum(compliance_scores) / len(compliance_scores)
        
        entropy_scores = [m.entropy_score for m in self.tool_metrics if m.entropy_score is not None]
        avg_entropy = sum(entropy_scores) / len(entropy_scores) if entropy_scores else 0.0
        
        performance_times = [m.execution_time_ms for m in self.tool_metrics]
        avg_performance = sum(performance_times) / len(performance_times)
        
        return GovernanceMetrics(
            timestamp=time.time(),
            compliance_score=avg_compliance,
            violation_count=violations,
            tool_usage_count=total_tools,
            entropy_average=avg_entropy,
            performance_ms=avg_performance,
            session_id=self.session_id
        )
    
    def _update_realtime_metrics(self) -> None:
        """Update real-time metrics file for monitoring."""
        metrics = self.calculate_session_metrics()
        
        # Write JSON metrics for dashboards
        metrics_file = self.metrics_dir / "governance_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)
            
        # Write Prometheus metrics for monitoring
        prometheus_file = self.metrics_dir / "governance_metrics.prom" 
        with open(prometheus_file, 'w') as f:
            f.write(metrics.to_prometheus_format())
            
        self.session_metrics.append(metrics)
        
    def get_compliance_trend(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get compliance score trend over time."""
        cutoff = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.session_metrics if m.timestamp > cutoff]
        
        return [
            {
                "timestamp": m.timestamp,
                "compliance_score": m.compliance_score,
                "violation_count": m.violation_count
            }
            for m in recent_metrics
        ]
        
    def get_tool_usage_distribution(self) -> Dict[str, int]:
        """Get tool usage distribution by category."""
        categories = Counter(m.category for m in self.tool_metrics)
        return dict(categories)
        
    def get_violation_breakdown(self) -> Dict[str, int]:
        """Get breakdown of violations by type."""
        violations = Counter(
            m.violation_type for m in self.tool_metrics 
            if m.violation_type
        )
        return dict(violations)
        
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        if not self.tool_metrics:
            return {"avg_ms": 0.0, "max_ms": 0.0, "min_ms": 0.0}
            
        times = [m.execution_time_ms for m in self.tool_metrics]
        return {
            "avg_ms": sum(times) / len(times),
            "max_ms": max(times),
            "min_ms": min(times),
            "total_tools": len(times)
        }
        
    def export_dashboard_data(self) -> Dict[str, Any]:
        """Export data formatted for dashboard consumption."""
        current_metrics = self.calculate_session_metrics()
        
        return {
            "current_state": asdict(current_metrics),
            "compliance_trend": self.get_compliance_trend(),
            "tool_distribution": self.get_tool_usage_distribution(),
            "violation_breakdown": self.get_violation_breakdown(),
            "performance_stats": self.get_performance_stats(),
            "session_duration_hours": (time.time() - self.start_time) / 3600,
            "last_updated": datetime.now().isoformat()
        }
        
    def create_grafana_dashboard_config(self) -> Dict[str, Any]:
        """Create Grafana dashboard configuration."""
        return {
            "dashboard": {
                "title": "ATLAS MCP Tool Governance",
                "tags": ["atlas", "governance", "mcp"],
                "time": {
                    "from": "now-6h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "Compliance Score",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "atlas_governance_compliance_score",
                                "legendFormat": "Compliance Score"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0.7},
                                        {"color": "yellow", "value": 0.85}, 
                                        {"color": "green", "value": 0.95}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": 2,
                        "title": "Governance Violations",
                        "type": "piechart",
                        "targets": [
                            {
                                "expr": "sum by (violation_type) (atlas_governance_violations_total)",
                                "legendFormat": "{{violation_type}}"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Tool Usage Distribution",
                        "type": "barchart",
                        "targets": [
                            {
                                "expr": "sum by (category) (atlas_tool_usage_total)",
                                "legendFormat": "{{category}}"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "Performance Metrics",
                        "type": "timeseries",
                        "targets": [
                            {
                                "expr": "atlas_governance_performance_ms",
                                "legendFormat": "Processing Time (ms)"
                            }
                        ]
                    }
                ]
            }
        }

# Global metrics collector instance
_metrics_collector = None

def get_metrics_collector() -> GovernanceMetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = GovernanceMetricsCollector()
    return _metrics_collector

def record_governance_metric(tool_name: str, category: str, execution_time_ms: float,
                           success: bool, compliance_score: float, 
                           entropy_score: Optional[float] = None,
                           violation_type: Optional[str] = None) -> None:
    """Convenience function to record governance metrics."""
    collector = get_metrics_collector()
    collector.record_tool_usage(
        tool_name=tool_name,
        category=category, 
        execution_time_ms=execution_time_ms,
        success=success,
        compliance_score=compliance_score,
        entropy_score=entropy_score,
        violation_type=violation_type
    )