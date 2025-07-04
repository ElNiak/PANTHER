"""Real-time governance violation detection and monitoring system."""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
import logging

from .metrics import GovernanceMetricsCollector, get_metrics_collector
from .policies import TOOL_POLICIES, TOOL_CATEGORIES

@dataclass
class GovernanceViolation:
    """Represents a governance violation."""
    violation_id: str
    type: str
    severity: str  # HIGH, MEDIUM, LOW
    tool_name: str
    description: str
    timestamp: float
    context: Dict[str, Any]
    suggested_action: Optional[str] = None
    
    def to_alert_format(self) -> Dict[str, Any]:
        """Convert violation to alert format."""
        return {
            "id": self.violation_id,
            "type": self.type,
            "severity": self.severity,
            "tool": self.tool_name,
            "message": self.description,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "suggested_action": self.suggested_action,
            "context": self.context
        }

@dataclass
class AlertConfig:
    """Configuration for alerting thresholds."""
    high_error_rate_threshold: float = 0.15
    memory_pollution_threshold: int = 5
    inefficient_usage_threshold: int = 3
    low_compliance_threshold: float = 0.8
    performance_degradation_threshold: float = 10.0  # ms
    alert_cooldown_minutes: int = 5

class GovernanceMonitor:
    """Real-time governance violation detection and monitoring."""
    
    def __init__(self, metrics_collector: Optional[GovernanceMetricsCollector] = None,
                 alert_config: Optional[AlertConfig] = None):
        """Initialize governance monitor."""
        self.metrics_collector = metrics_collector or get_metrics_collector()
        self.alert_config = alert_config or AlertConfig()
        
        self.violations: List[GovernanceViolation] = []
        self.recent_violations = deque(maxlen=100)  # Keep recent violations for analysis
        
        # Alert management
        self.last_alert_times: Dict[str, float] = {}
        self.alert_handlers: List[Callable[[GovernanceViolation], None]] = []
        
        # Performance tracking
        self.violation_counts = defaultdict(int)
        self.tool_error_rates = defaultdict(lambda: {"successes": 0, "errors": 0})
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
    def detect_governance_violations(self, metrics: Dict[str, Any]) -> List[GovernanceViolation]:
        """Detect governance violations from current metrics."""
        violations = []
        current_time = time.time()
        
        # High error rate detection
        error_rate = metrics.get("error_rate", 0.0)
        if error_rate > self.alert_config.high_error_rate_threshold:
            violations.append(GovernanceViolation(
                violation_id=f"error_rate_{int(current_time)}",
                type="HIGH_ERROR_RATE",
                severity="HIGH",
                tool_name=metrics.get("tool_name", "unknown"),
                description=f"Tool error rate {error_rate:.2%} exceeds threshold of {self.alert_config.high_error_rate_threshold:.2%}",
                timestamp=current_time,
                context={"error_rate": error_rate, "threshold": self.alert_config.high_error_rate_threshold},
                suggested_action="Review tool usage patterns and validate input parameters"
            ))
            
        # Memory pollution detection
        low_entropy_writes = metrics.get("low_entropy_memory_writes", 0)
        if low_entropy_writes > self.alert_config.memory_pollution_threshold:
            violations.append(GovernanceViolation(
                violation_id=f"memory_pollution_{int(current_time)}",
                type="MEMORY_POLLUTION",
                severity="MEDIUM", 
                tool_name=metrics.get("tool_name", "unknown"),
                description=f"Multiple low-entropy memory writes detected: {low_entropy_writes}",
                timestamp=current_time,
                context={"low_entropy_writes": low_entropy_writes, "threshold": self.alert_config.memory_pollution_threshold},
                suggested_action="Review memory content for surprising/non-obvious information only"
            ))
            
        # Inefficient usage detection
        redundant_calls = metrics.get("redundant_tool_calls", 0)
        if redundant_calls > self.alert_config.inefficient_usage_threshold:
            violations.append(GovernanceViolation(
                violation_id=f"inefficient_usage_{int(current_time)}",
                type="INEFFICIENT_USAGE",
                severity="LOW",
                tool_name=metrics.get("tool_name", "unknown"),
                description=f"Redundant tool calls detected: {redundant_calls}",
                timestamp=current_time,
                context={"redundant_calls": redundant_calls, "threshold": self.alert_config.inefficient_usage_threshold},
                suggested_action="Consider batching operations or using higher-level workflow tools"
            ))
            
        # Low compliance score detection
        compliance_score = metrics.get("compliance_score", 1.0)
        if compliance_score < self.alert_config.low_compliance_threshold:
            violations.append(GovernanceViolation(
                violation_id=f"low_compliance_{int(current_time)}",
                type="LOW_COMPLIANCE",
                severity="MEDIUM",
                tool_name=metrics.get("tool_name", "unknown"),
                description=f"Low compliance score detected: {compliance_score:.2f}",
                timestamp=current_time,
                context={"compliance_score": compliance_score, "threshold": self.alert_config.low_compliance_threshold},
                suggested_action="Review governance policies and improve tool usage patterns"
            ))
            
        # Performance degradation detection
        performance_ms = metrics.get("performance_ms", 0.0)
        if performance_ms > self.alert_config.performance_degradation_threshold:
            violations.append(GovernanceViolation(
                violation_id=f"performance_degradation_{int(current_time)}",
                type="PERFORMANCE_DEGRADATION",
                severity="MEDIUM",
                tool_name=metrics.get("tool_name", "unknown"),
                description=f"Performance degradation detected: {performance_ms:.1f}ms",
                timestamp=current_time,
                context={"performance_ms": performance_ms, "threshold": self.alert_config.performance_degradation_threshold},
                suggested_action="Optimize tool usage or check system resources"
            ))
            
        return violations
        
    def process_tool_execution(self, tool_name: str, success: bool, execution_time_ms: float,
                             context: Dict[str, Any]) -> List[GovernanceViolation]:
        """Process tool execution and detect violations."""
        # Update error rates
        if success:
            self.tool_error_rates[tool_name]["successes"] += 1
        else:
            self.tool_error_rates[tool_name]["errors"] += 1
            
        # Calculate current metrics for violation detection
        tool_stats = self.tool_error_rates[tool_name]
        total_calls = tool_stats["successes"] + tool_stats["errors"]
        error_rate = tool_stats["errors"] / total_calls if total_calls > 0 else 0.0
        
        metrics = {
            "tool_name": tool_name,
            "error_rate": error_rate,
            "performance_ms": execution_time_ms,
            "compliance_score": context.get("compliance_score", 1.0),
            "low_entropy_memory_writes": context.get("low_entropy_memory_writes", 0),
            "redundant_tool_calls": context.get("redundant_tool_calls", 0)
        }
        
        # Detect violations
        violations = self.detect_governance_violations(metrics)
        
        # Process and store violations
        for violation in violations:
            self._process_violation(violation)
            
        return violations
        
    def _process_violation(self, violation: GovernanceViolation) -> None:
        """Process a detected violation."""
        # Add to violation lists
        self.violations.append(violation)
        self.recent_violations.append(violation)
        
        # Update violation counts
        self.violation_counts[violation.type] += 1
        
        # Check if we should send an alert (respect cooldown)
        if self._should_send_alert(violation):
            self._send_alert(violation)
            self.last_alert_times[violation.type] = violation.timestamp
            
        # Log violation
        self.logger.warning(f"Governance violation detected: {violation.type} - {violation.description}")
        
    def _should_send_alert(self, violation: GovernanceViolation) -> bool:
        """Check if an alert should be sent for this violation."""
        # Always alert for HIGH severity
        if violation.severity == "HIGH":
            return True
            
        # Check cooldown for other severities
        last_alert = self.last_alert_times.get(violation.type, 0)
        cooldown_seconds = self.alert_config.alert_cooldown_minutes * 60
        
        return (violation.timestamp - last_alert) > cooldown_seconds
        
    def _send_alert(self, violation: GovernanceViolation) -> None:
        """Send alert for violation."""
        # Call all registered alert handlers
        for handler in self.alert_handlers:
            try:
                handler(violation)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")
                
        # Write alert to file for external monitoring
        self._write_alert_file(violation)
        
    def _write_alert_file(self, violation: GovernanceViolation) -> None:
        """Write alert to file for external monitoring systems."""
        alerts_dir = Path("~/.atlas/alerts").expanduser()
        alerts_dir.mkdir(exist_ok=True)
        
        alert_file = alerts_dir / f"alert_{violation.violation_id}.json"
        with open(alert_file, 'w') as f:
            json.dump(violation.to_alert_format(), f, indent=2)
            
    def register_alert_handler(self, handler: Callable[[GovernanceViolation], None]) -> None:
        """Register an alert handler function."""
        self.alert_handlers.append(handler)
        
    def get_violation_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of violations in the last N hours."""
        cutoff = time.time() - (hours * 3600)
        recent = [v for v in self.violations if v.timestamp > cutoff]
        
        summary = {
            "total_violations": len(recent),
            "by_severity": defaultdict(int),
            "by_type": defaultdict(int),
            "by_tool": defaultdict(int),
            "time_range_hours": hours
        }
        
        for violation in recent:
            summary["by_severity"][violation.severity] += 1
            summary["by_type"][violation.type] += 1
            summary["by_tool"][violation.tool_name] += 1
            
        return dict(summary)
        
    def export_monitoring_data(self) -> Dict[str, Any]:
        """Export data for monitoring dashboards."""
        return {
            "violation_summary": self.get_violation_summary(),
            "recent_violations": [v.to_alert_format() for v in list(self.recent_violations)[-10:]],
            "violation_counts_by_type": dict(self.violation_counts),
            "tool_error_rates": {
                tool: {
                    "error_rate": stats["errors"] / (stats["successes"] + stats["errors"])
                    if (stats["successes"] + stats["errors"]) > 0 else 0.0,
                    "total_calls": stats["successes"] + stats["errors"]
                }
                for tool, stats in self.tool_error_rates.items()
            },
            "monitoring_status": "active",
            "last_updated": datetime.now().isoformat()
        }

# Console alert handler
def console_alert_handler(violation: GovernanceViolation) -> None:
    """Simple console alert handler."""
    severity_colors = {
        "HIGH": "\033[91m",     # Red
        "MEDIUM": "\033[93m",   # Yellow  
        "LOW": "\033[94m"       # Blue
    }
    reset_color = "\033[0m"
    
    color = severity_colors.get(violation.severity, "")
    print(f"{color}🚨 GOVERNANCE VIOLATION [{violation.severity}]{reset_color}")
    print(f"   Type: {violation.type}")
    print(f"   Tool: {violation.tool_name}")
    print(f"   Description: {violation.description}")
    if violation.suggested_action:
        print(f"   Suggested Action: {violation.suggested_action}")
    print()

# Global monitor instance
_governance_monitor = None

def get_governance_monitor() -> GovernanceMonitor:
    """Get or create global governance monitor."""
    global _governance_monitor
    if _governance_monitor is None:
        _governance_monitor = GovernanceMonitor()
        # Register default console handler
        _governance_monitor.register_alert_handler(console_alert_handler)
    return _governance_monitor