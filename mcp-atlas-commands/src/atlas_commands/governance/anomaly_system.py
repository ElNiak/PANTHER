"""Anomaly detection system for ATLAS governance."""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
import threading
import logging

from .adaptive_engine import get_adaptive_engine
from .monitor import get_governance_monitor, GovernanceViolation
from .metrics import get_metrics_collector

@dataclass
class AnomalyEvent:
    """Represents an anomaly detection event."""
    event_id: str
    timestamp: float
    anomaly_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    tool_name: str
    description: str
    anomaly_score: float
    confidence: float
    context: Dict[str, Any]
    mitigation_suggestions: List[str]
    
    def to_alert_format(self) -> Dict[str, Any]:
        """Convert to alert format for external systems."""
        return {
            "id": self.event_id,
            "type": "ANOMALY_DETECTION",
            "severity": self.severity,
            "tool": self.tool_name,
            "anomaly_type": self.anomaly_type,
            "score": self.anomaly_score,
            "confidence": self.confidence,
            "message": self.description,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "suggestions": self.mitigation_suggestions,
            "context": self.context
        }

class AnomalyDetectionSystem:
    """Real-time anomaly detection system for governance."""
    
    def __init__(self, detection_interval: float = 30.0):
        """Initialize anomaly detection system."""
        self.detection_interval = detection_interval
        self.adaptive_engine = get_adaptive_engine()
        self.governance_monitor = get_governance_monitor()
        self.metrics_collector = get_metrics_collector()
        
        # Anomaly tracking
        self.detected_anomalies: List[AnomalyEvent] = []
        self.recent_anomalies = deque(maxlen=100)
        
        # Pattern detection
        self.tool_patterns = defaultdict(list)
        self.session_patterns = {}
        
        # Detection thresholds
        self.thresholds = {
            "critical_anomaly_score": -0.5,
            "high_anomaly_score": -0.3,
            "medium_anomaly_score": -0.1,
            "pattern_deviation_threshold": 0.7,
            "frequency_spike_threshold": 3.0,
            "performance_degradation_threshold": 2.0
        }
        
        # Background monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Event handlers
        self.anomaly_handlers: List[Callable[[AnomalyEvent], None]] = []
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self) -> None:
        """Start background anomaly monitoring."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            self.logger.info("Anomaly detection monitoring started")
            
    def stop_monitoring(self) -> None:
        """Stop background anomaly monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        self.logger.info("Anomaly detection monitoring stopped")
        
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                self._detect_system_anomalies()
                time.sleep(self.detection_interval)
            except Exception as e:
                self.logger.error(f"Anomaly detection error: {e}")
                time.sleep(self.detection_interval)
                
    def detect_tool_anomaly(self, tool_name: str, arguments: Dict[str, Any],
                           context: Dict[str, Any]) -> Optional[AnomalyEvent]:
        """Detect anomalies in individual tool usage."""
        try:
            # Use ML-based anomaly detection
            anomaly_result = self.adaptive_engine.anomaly_detector.detect_anomaly(
                tool_name, arguments, context
            )
            
            if anomaly_result.get("is_anomaly", False):
                # Create anomaly event
                anomaly_score = anomaly_result.get("anomaly_score", 0.0)
                confidence = anomaly_result.get("confidence", 0.0)
                
                # Determine severity based on score
                if anomaly_score <= self.thresholds["critical_anomaly_score"]:
                    severity = "CRITICAL"
                elif anomaly_score <= self.thresholds["high_anomaly_score"]:
                    severity = "HIGH"
                elif anomaly_score <= self.thresholds["medium_anomaly_score"]:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"
                    
                # Generate mitigation suggestions
                suggestions = self._generate_mitigation_suggestions(
                    tool_name, anomaly_score, context
                )
                
                anomaly_event = AnomalyEvent(
                    event_id=f"anomaly_{int(time.time() * 1000)}",
                    timestamp=time.time(),
                    anomaly_type="USAGE_PATTERN_ANOMALY",
                    severity=severity,
                    tool_name=tool_name,
                    description=f"Anomalous usage pattern detected for {tool_name} (score: {anomaly_score:.3f})",
                    anomaly_score=anomaly_score,
                    confidence=confidence,
                    context=context,
                    mitigation_suggestions=suggestions
                )
                
                self._process_anomaly(anomaly_event)
                return anomaly_event
                
        except Exception as e:
            self.logger.error(f"Tool anomaly detection failed: {e}")
            
        return None
        
    def _detect_system_anomalies(self) -> None:
        """Detect system-level anomalies."""
        try:
            # Get current system metrics
            current_metrics = self.metrics_collector.calculate_session_metrics()
            
            # Check for performance anomalies
            if (current_metrics.performance_ms > 
                self.thresholds["performance_degradation_threshold"] * 1000):
                
                anomaly_event = AnomalyEvent(
                    event_id=f"perf_anomaly_{int(time.time() * 1000)}",
                    timestamp=time.time(),
                    anomaly_type="PERFORMANCE_DEGRADATION",
                    severity="HIGH",
                    tool_name="SYSTEM",
                    description=f"System performance degradation detected: {current_metrics.performance_ms:.1f}ms",
                    anomaly_score=-0.4,  # High severity score
                    confidence=0.9,
                    context={"performance_ms": current_metrics.performance_ms},
                    mitigation_suggestions=[
                        "Check system resources and CPU usage",
                        "Review recent tool usage patterns for inefficiencies",
                        "Consider restarting governance monitoring services"
                    ]
                )
                
                self._process_anomaly(anomaly_event)
                
            # Check for compliance degradation
            if current_metrics.compliance_score < 0.7:
                anomaly_event = AnomalyEvent(
                    event_id=f"compliance_anomaly_{int(time.time() * 1000)}",
                    timestamp=time.time(),
                    anomaly_type="COMPLIANCE_DEGRADATION",
                    severity="MEDIUM",
                    tool_name="SYSTEM",
                    description=f"System compliance score degradation: {current_metrics.compliance_score:.3f}",
                    anomaly_score=-0.2,
                    confidence=0.8,
                    context={"compliance_score": current_metrics.compliance_score},
                    mitigation_suggestions=[
                        "Review recent tool usage for governance violations",
                        "Check entropy quality of memory operations",
                        "Verify workflow patterns are following best practices"
                    ]
                )
                
                self._process_anomaly(anomaly_event)
                
        except Exception as e:
            self.logger.error(f"System anomaly detection failed: {e}")
            
    def _generate_mitigation_suggestions(self, tool_name: str, anomaly_score: float,
                                       context: Dict[str, Any]) -> List[str]:
        """Generate mitigation suggestions for anomalies."""
        suggestions = []
        
        # Tool-specific suggestions
        if "memory" in tool_name.lower():
            suggestions.extend([
                "Review information entropy - store only surprising, non-obvious content",
                "Ensure observations contain meaningful insights for future debugging",
                "Check that entity types and names are descriptive and specific"
            ])
        elif "task" in tool_name.lower():
            suggestions.extend([
                "Verify task descriptions are specific and actionable",
                "Check hierarchical task organization and dependencies",
                "Ensure project context is provided for task management operations"
            ])
        elif "github" in tool_name.lower():
            suggestions.extend([
                "Review commit messages and PR descriptions for clarity",
                "Check branch naming conventions and workflow patterns",
                "Verify authentication and permissions are correctly configured"
            ])
        
        # Score-based suggestions
        if anomaly_score < -0.4:
            suggestions.extend([
                "This appears to be a significant deviation - review tool usage carefully",
                "Consider consulting governance documentation for best practices",
                "Check if this usage pattern is intentional and document if so"
            ])
        elif anomaly_score < -0.2:
            suggestions.extend([
                "Review arguments and context for potential improvements",
                "Check recent usage patterns for consistency"
            ])
            
        # Context-based suggestions
        error_rate = context.get("recent_error_rate", 0)
        if error_rate > 0.2:
            suggestions.append("High error rate detected - check tool arguments and system health")
            
        frequency = context.get("recent_usage_count", 0)
        if frequency > 15:
            suggestions.append("High frequency usage - consider batching operations or using workflow tools")
            
        return suggestions
        
    def _process_anomaly(self, anomaly_event: AnomalyEvent) -> None:
        """Process detected anomaly."""
        # Add to tracking lists
        self.detected_anomalies.append(anomaly_event)
        self.recent_anomalies.append(anomaly_event)
        
        # Call registered handlers
        for handler in self.anomaly_handlers:
            try:
                handler(anomaly_event)
            except Exception as e:
                self.logger.error(f"Anomaly handler failed: {e}")
                
        # Write to file for external monitoring
        self._write_anomaly_alert(anomaly_event)
        
        # Log the anomaly
        self.logger.warning(
            f"Anomaly detected: {anomaly_event.anomaly_type} - "
            f"{anomaly_event.description} (severity: {anomaly_event.severity})"
        )
        
    def _write_anomaly_alert(self, anomaly_event: AnomalyEvent) -> None:
        """Write anomaly alert to file."""
        try:
            alerts_dir = Path("~/.atlas/anomalies").expanduser()
            alerts_dir.mkdir(exist_ok=True)
            
            alert_file = alerts_dir / f"anomaly_{anomaly_event.event_id}.json"
            with open(alert_file, 'w') as f:
                json.dump(anomaly_event.to_alert_format(), f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to write anomaly alert: {e}")
            
    def register_anomaly_handler(self, handler: Callable[[AnomalyEvent], None]) -> None:
        """Register an anomaly event handler."""
        self.anomaly_handlers.append(handler)
        
    def get_anomaly_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of anomalies in the last N hours."""
        cutoff = time.time() - (hours * 3600)
        recent = [a for a in self.detected_anomalies if a.timestamp > cutoff]
        
        summary = {
            "total_anomalies": len(recent),
            "by_severity": defaultdict(int),
            "by_type": defaultdict(int),
            "by_tool": defaultdict(int),
            "avg_anomaly_score": 0.0,
            "time_range_hours": hours
        }
        
        if recent:
            total_score = 0
            for anomaly in recent:
                summary["by_severity"][anomaly.severity] += 1
                summary["by_type"][anomaly.anomaly_type] += 1
                summary["by_tool"][anomaly.tool_name] += 1
                total_score += anomaly.anomaly_score
                
            summary["avg_anomaly_score"] = total_score / len(recent)
            
        return dict(summary)
        
    def export_monitoring_data(self) -> Dict[str, Any]:
        """Export data for monitoring dashboards."""
        return {
            "anomaly_summary": self.get_anomaly_summary(),
            "recent_anomalies": [a.to_alert_format() for a in list(self.recent_anomalies)[-10:]],
            "detection_thresholds": self.thresholds,
            "monitoring_active": self.monitoring_active,
            "detection_interval": self.detection_interval,
            "last_updated": datetime.now().isoformat()
        }

# Console anomaly handler
def console_anomaly_handler(anomaly: AnomalyEvent) -> None:
    """Simple console anomaly handler."""
    severity_colors = {
        "CRITICAL": "\033[95m",   # Magenta
        "HIGH": "\033[91m",       # Red
        "MEDIUM": "\033[93m",     # Yellow
        "LOW": "\033[94m"         # Blue
    }
    reset_color = "\033[0m"
    
    color = severity_colors.get(anomaly.severity, "")
    print(f"{color}⚠️  ANOMALY DETECTED [{anomaly.severity}]{reset_color}")
    print(f"   Type: {anomaly.anomaly_type}")
    print(f"   Tool: {anomaly.tool_name}")
    print(f"   Score: {anomaly.anomaly_score:.3f} (confidence: {anomaly.confidence:.3f})")
    print(f"   Description: {anomaly.description}")
    if anomaly.mitigation_suggestions:
        print("   Suggestions:")
        for suggestion in anomaly.mitigation_suggestions[:2]:  # Show top 2
            print(f"     - {suggestion}")
    print()

# Global anomaly detection system
_anomaly_system = None

def get_anomaly_system() -> AnomalyDetectionSystem:
    """Get or create global anomaly detection system."""
    global _anomaly_system
    if _anomaly_system is None:
        _anomaly_system = AnomalyDetectionSystem()
        # Register default console handler
        _anomaly_system.register_anomaly_handler(console_anomaly_handler)
    return _anomaly_system