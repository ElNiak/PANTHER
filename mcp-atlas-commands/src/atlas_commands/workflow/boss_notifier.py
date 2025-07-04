"""
Boss Notification System for Git Protocol and Task Management

Provides contextual notifications to the boss about important events,
task progress, and decisions that require review or approval.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class NotificationType(Enum):
    """Types of notifications"""
    GIT_STAGING = "git_staging"
    GIT_REVIEW_REQUEST = "git_review_request"
    GIT_COMMIT = "git_commit"
    TASK_COMPLETED = "task_completed"
    TASK_BLOCKED = "task_blocked"
    MILESTONE_REACHED = "milestone_reached"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    DECISION_NEEDED = "decision_needed"
    ERROR_OCCURRED = "error_occurred"
    PROGRESS_UPDATE = "progress_update"


class NotificationPriority(Enum):
    """Priority levels for notifications"""
    LOW = "low"         # Informational only
    MEDIUM = "medium"   # Should be reviewed
    HIGH = "high"       # Needs attention soon
    CRITICAL = "critical"  # Immediate attention required


@dataclass
class BossNotification:
    """Represents a notification to the boss"""
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    requires_action: bool
    suggested_actions: List[str]


class BossNotifier:
    """Manages notifications to the boss with context and prioritization"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.getcwd()
        self.working_log_path = self._find_working_log()
        self.notification_history: List[BossNotification] = []
        
        # Notification templates for consistency
        self.templates = {
            NotificationType.GIT_STAGING: {
                "emoji": "📝",
                "title": "Files Staged for Review",
                "priority": NotificationPriority.MEDIUM
            },
            NotificationType.GIT_REVIEW_REQUEST: {
                "emoji": "👀",
                "title": "Code Review Requested",
                "priority": NotificationPriority.HIGH
            },
            NotificationType.GIT_COMMIT: {
                "emoji": "✅",
                "title": "Changes Committed",
                "priority": NotificationPriority.LOW
            },
            NotificationType.TASK_COMPLETED: {
                "emoji": "🎉",
                "title": "Task Completed",
                "priority": NotificationPriority.MEDIUM
            },
            NotificationType.TASK_BLOCKED: {
                "emoji": "🚫",
                "title": "Task Blocked",
                "priority": NotificationPriority.HIGH
            },
            NotificationType.MILESTONE_REACHED: {
                "emoji": "🏆",
                "title": "Milestone Reached",
                "priority": NotificationPriority.MEDIUM
            },
            NotificationType.QUALITY_GATE_FAILED: {
                "emoji": "❌",
                "title": "Quality Gate Failed",
                "priority": NotificationPriority.CRITICAL
            },
            NotificationType.DECISION_NEEDED: {
                "emoji": "🤔",
                "title": "Decision Required",
                "priority": NotificationPriority.CRITICAL
            },
            NotificationType.ERROR_OCCURRED: {
                "emoji": "🔥",
                "title": "Error Occurred",
                "priority": NotificationPriority.CRITICAL
            },
            NotificationType.PROGRESS_UPDATE: {
                "emoji": "📊",
                "title": "Progress Update",
                "priority": NotificationPriority.LOW
            }
        }
    
    def _find_working_log(self) -> Optional[Path]:
        """Find the current working log file"""
        today = datetime.now()
        log_filename = f"wl_{today.strftime('%Y_%m_%d')}.md"
        month_folder = today.strftime("%m-%b").lower()
        
        # Try common locations
        possible_paths = [
            Path(self.project_root) / "WORKING_LOG" / str(today.year) / month_folder / log_filename,
            Path(self.project_root) / "working_log" / str(today.year) / month_folder / log_filename,
            Path(self.project_root) / log_filename
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Create if doesn't exist
        default_path = possible_paths[0]
        default_path.parent.mkdir(parents=True, exist_ok=True)
        return default_path
    
    def notify_git_staging(self, 
                          files: List[str], 
                          quality_report: Optional[Dict[str, Any]] = None,
                          context: Optional[str] = None) -> List[str]:
        """Notify boss about Git staging with quality report"""
        template = self.templates[NotificationType.GIT_STAGING]
        
        # Build message
        file_count = len(files) if files else "all"
        message_parts = [f"Staged {file_count} files for review"]
        
        if quality_report:
            if quality_report.get("overall_status") == "passed":
                message_parts.append("✓ All quality checks passed")
            elif quality_report.get("overall_status") == "warning":
                warnings = quality_report.get("warnings", [])
                message_parts.append(f"⚠️  {len(warnings)} warnings found (non-blocking)")
            else:
                errors = quality_report.get("errors", [])
                message_parts.append(f"❌ {len(errors)} quality issues need fixing")
        
        if context:
            message_parts.append(f"Context: {context}")
        
        # Suggested actions
        suggested_actions = [
            "Review staged changes: git diff --cached",
            "Run tests locally to verify",
            "Approve for commit when ready"
        ]
        
        notification = BossNotification(
            notification_type=NotificationType.GIT_STAGING,
            priority=template["priority"],
            title=template["title"],
            message="\n".join(message_parts),
            context={
                "files": files,
                "quality_report": quality_report,
                "review_context": context
            },
            timestamp=datetime.now(),
            requires_action=True,
            suggested_actions=suggested_actions
        )
        
        return self._send_notification(notification, template["emoji"])
    
    def notify_review_request(self, 
                             staged_files: List[str],
                             quality_summary: Optional[str] = None,
                             blocking_issues: Optional[List[str]] = None) -> List[str]:
        """Notify boss about review request with detailed context"""
        template = self.templates[NotificationType.GIT_REVIEW_REQUEST]
        
        # Build detailed message
        message_parts = [
            f"Review requested for {len(staged_files)} staged files",
            "",
            "**Files to review:**"
        ]
        
        # Group files by type
        file_groups = self._group_files_by_type(staged_files)
        for file_type, files in file_groups.items():
            message_parts.append(f"- {file_type}: {len(files)} files")
        
        if quality_summary:
            message_parts.extend(["", "**Quality Summary:**", quality_summary])
        
        if blocking_issues:
            message_parts.extend(["", "**Blocking Issues:**"])
            for issue in blocking_issues[:5]:  # First 5 issues
                message_parts.append(f"- {issue}")
        
        # Context for review
        suggested_actions = [
            "Review changes: git diff --cached",
            "Check specific file: git diff --cached <filename>",
            "Run tests: pytest (or appropriate test command)",
            "Approve: Reply 'approved' or use git commit"
        ]
        
        notification = BossNotification(
            notification_type=NotificationType.GIT_REVIEW_REQUEST,
            priority=NotificationPriority.CRITICAL if blocking_issues else template["priority"],
            title=template["title"],
            message="\n".join(message_parts),
            context={
                "staged_files": staged_files,
                "file_groups": file_groups,
                "has_blocking_issues": bool(blocking_issues)
            },
            timestamp=datetime.now(),
            requires_action=True,
            suggested_actions=suggested_actions
        )
        
        return self._send_notification(notification, template["emoji"])
    
    def notify_task_progress(self,
                            task_id: str,
                            task_name: str,
                            completion_percentage: float,
                            completed_subtasks: List[str],
                            remaining_subtasks: List[str],
                            estimated_time_remaining: Optional[float] = None) -> List[str]:
        """Notify boss about task progress with smart insights"""
        template = self.templates[NotificationType.PROGRESS_UPDATE]
        
        # Determine if this is a significant update
        is_milestone = completion_percentage in [25, 50, 75, 100]
        if is_milestone:
            template = self.templates[NotificationType.MILESTONE_REACHED]
        
        # Build progress message
        message_parts = [
            f"Task: {task_name}",
            f"Progress: {completion_percentage:.0f}% complete",
            ""
        ]
        
        if completed_subtasks:
            message_parts.append(f"**Completed ({len(completed_subtasks)}):**")
            for subtask in completed_subtasks[-3:]:  # Last 3 completed
                message_parts.append(f"✓ {subtask}")
        
        if remaining_subtasks:
            message_parts.append(f"\n**Remaining ({len(remaining_subtasks)}):**")
            for subtask in remaining_subtasks[:3]:  # Next 3 to do
                message_parts.append(f"○ {subtask}")
        
        if estimated_time_remaining:
            hours = estimated_time_remaining
            if hours < 1:
                time_str = f"{int(hours * 60)} minutes"
            else:
                time_str = f"{hours:.1f} hours"
            message_parts.append(f"\n**Estimated time remaining:** {time_str}")
        
        notification = BossNotification(
            notification_type=NotificationType.MILESTONE_REACHED if is_milestone else NotificationType.PROGRESS_UPDATE,
            priority=template["priority"],
            title=f"{template['title']}: {task_name}",
            message="\n".join(message_parts),
            context={
                "task_id": task_id,
                "completion_percentage": completion_percentage,
                "is_milestone": is_milestone
            },
            timestamp=datetime.now(),
            requires_action=False,
            suggested_actions=[]
        )
        
        return self._send_notification(notification, template["emoji"])
    
    def notify_blocker(self,
                      task_id: str,
                      task_name: str,
                      blocker_description: str,
                      blocker_type: str,
                      suggested_solutions: List[str]) -> List[str]:
        """Notify boss about a blocker requiring attention"""
        template = self.templates[NotificationType.TASK_BLOCKED]
        
        message_parts = [
            f"Task blocked: {task_name}",
            f"Blocker type: {blocker_type}",
            "",
            f"**Issue:** {blocker_description}",
            "",
            "**Suggested solutions:**"
        ]
        
        for i, solution in enumerate(suggested_solutions, 1):
            message_parts.append(f"{i}. {solution}")
        
        notification = BossNotification(
            notification_type=NotificationType.TASK_BLOCKED,
            priority=NotificationPriority.CRITICAL,
            title=f"{template['title']}: {task_name}",
            message="\n".join(message_parts),
            context={
                "task_id": task_id,
                "blocker_type": blocker_type
            },
            timestamp=datetime.now(),
            requires_action=True,
            suggested_actions=["Review blocker", "Provide guidance", "Unblock task"]
        )
        
        return self._send_notification(notification, template["emoji"])
    
    def notify_milestone_risk(self,
                             milestone_id: str,
                             milestone_name: str,
                             risk_level: str,
                             completion_percentage: float,
                             days_remaining: Optional[int],
                             at_risk_reasons: List[str],
                             recommended_actions: List[str]) -> List[str]:
        """Notify boss about milestone at risk"""
        # Determine priority based on risk level
        if risk_level == "missed":
            priority = NotificationPriority.CRITICAL
            emoji = "🚨"
            title = "MILESTONE MISSED"
        elif risk_level == "high_risk":
            priority = NotificationPriority.HIGH
            emoji = "⚠️"
            title = "Milestone at High Risk"
        else:
            priority = NotificationPriority.MEDIUM
            emoji = "⚡"
            title = "Milestone at Risk"
        
        message_parts = [
            f"Milestone: {milestone_name}",
            f"Progress: {completion_percentage:.0f}% complete",
        ]
        
        if days_remaining is not None:
            if days_remaining < 0:
                message_parts.append(f"**OVERDUE by {-days_remaining} days**")
            else:
                message_parts.append(f"Days remaining: {days_remaining}")
        
        message_parts.extend([
            "",
            "**Risk Factors:**"
        ])
        for reason in at_risk_reasons:
            message_parts.append(f"• {reason}")
        
        message_parts.extend([
            "",
            "**Recommended Actions:**"
        ])
        for i, action in enumerate(recommended_actions, 1):
            message_parts.append(f"{i}. {action}")
        
        notification = BossNotification(
            notification_type=NotificationType.MILESTONE_REACHED,
            priority=priority,
            title=f"{emoji} {title}: {milestone_name}",
            message="\n".join(message_parts),
            context={
                "milestone_id": milestone_id,
                "risk_level": risk_level,
                "completion_percentage": completion_percentage
            },
            timestamp=datetime.now(),
            requires_action=True,
            suggested_actions=recommended_actions
        )
        
        return self._send_notification(notification, emoji)
    
    def notify_decision_needed(self,
                              decision_title: str,
                              decision_context: str,
                              options: List[Dict[str, str]],
                              recommendation: Optional[str] = None) -> List[str]:
        """Notify boss about a decision that needs to be made"""
        template = self.templates[NotificationType.DECISION_NEEDED]
        
        message_parts = [
            f"**Decision needed:** {decision_title}",
            "",
            f"**Context:** {decision_context}",
            "",
            "**Options:**"
        ]
        
        for i, option in enumerate(options, 1):
            message_parts.append(f"\n{i}. **{option.get('title', 'Option')}**")
            if option.get('description'):
                message_parts.append(f"   {option['description']}")
            if option.get('pros'):
                message_parts.append(f"   ✓ Pros: {option['pros']}")
            if option.get('cons'):
                message_parts.append(f"   ✗ Cons: {option['cons']}")
        
        if recommendation:
            message_parts.extend(["", f"**Recommendation:** {recommendation}"])
        
        notification = BossNotification(
            notification_type=NotificationType.DECISION_NEEDED,
            priority=NotificationPriority.CRITICAL,
            title=template["title"],
            message="\n".join(message_parts),
            context={
                "decision_title": decision_title,
                "options": options
            },
            timestamp=datetime.now(),
            requires_action=True,
            suggested_actions=["Review options", "Make decision", "Provide guidance"]
        )
        
        return self._send_notification(notification, template["emoji"])
    
    def _send_notification(self, notification: BossNotification, emoji: str) -> List[str]:
        """Send notification through multiple channels"""
        sent_notifications = []
        
        # Console notification (always)
        console_msg = f"{emoji} {notification.title}"
        if notification.priority == NotificationPriority.CRITICAL:
            console_msg = f"🚨 {console_msg} 🚨"
        print(console_msg)
        if notification.requires_action:
            print("   ⚡ Action required!")
        sent_notifications.append(f"Console: {notification.title}")
        
        # Working log entry
        if self.working_log_path:
            try:
                log_entry = self._format_working_log_entry(notification, emoji)
                with open(self.working_log_path, 'a') as f:
                    f.write(log_entry)
                sent_notifications.append(f"Working log: {self.working_log_path}")
            except Exception as e:
                print(f"Could not write to working log: {e}")
        
        # Store in history
        self.notification_history.append(notification)
        
        return sent_notifications
    
    def _format_working_log_entry(self, notification: BossNotification, emoji: str) -> str:
        """Format notification for working log"""
        timestamp = notification.timestamp.strftime("%H:%M")
        
        entry_parts = [
            f"\n### {timestamp} - {emoji} {notification.title}\n",
            notification.message
        ]
        
        if notification.requires_action:
            entry_parts.append("\n**Action Required:**")
            for action in notification.suggested_actions:
                entry_parts.append(f"- {action}")
        
        entry_parts.append("\n")
        return "\n".join(entry_parts)
    
    def _group_files_by_type(self, files: List[str]) -> Dict[str, List[str]]:
        """Group files by their type/extension"""
        groups = {}
        
        for file_path in files:
            ext = Path(file_path).suffix.lower()
            if ext in ['.py', '.pyw']:
                file_type = "Python"
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                file_type = "JavaScript/TypeScript"
            elif ext in ['.md', '.rst', '.txt']:
                file_type = "Documentation"
            elif ext in ['.json', '.yaml', '.yml', '.toml']:
                file_type = "Configuration"
            elif ext in ['.html', '.css', '.scss']:
                file_type = "Frontend"
            else:
                file_type = "Other"
            
            if file_type not in groups:
                groups[file_type] = []
            groups[file_type].append(file_path)
        
        return groups
    
    def get_pending_notifications(self, priority_filter: Optional[NotificationPriority] = None) -> List[BossNotification]:
        """Get pending notifications that require action"""
        pending = [n for n in self.notification_history if n.requires_action]
        
        if priority_filter:
            pending = [n for n in pending if n.priority == priority_filter]
        
        # Sort by priority and timestamp
        priority_order = {
            NotificationPriority.CRITICAL: 0,
            NotificationPriority.HIGH: 1,
            NotificationPriority.MEDIUM: 2,
            NotificationPriority.LOW: 3
        }
        
        pending.sort(key=lambda n: (priority_order[n.priority], n.timestamp))
        
        return pending
    
    def notify_approval_received(self, 
                                approved_by: str,
                                files: List[str],
                                approval_context: Optional[str] = None) -> List[str]:
        """Notify that boss approval has been received"""
        file_groups = self._group_files_by_type(files)
        
        message_parts = [
            f"Approval received from {approved_by}",
            f"\nFiles approved ({len(files)} total):"
        ]
        
        for file_type, file_list in file_groups.items():
            message_parts.append(f"\n{file_type} ({len(file_list)} files):")
            for file_path in file_list[:3]:  # Show first 3
                message_parts.append(f"  ✓ {file_path}")
            if len(file_list) > 3:
                message_parts.append(f"  ... and {len(file_list) - 3} more")
        
        if approval_context:
            message_parts.append(f"\nApproval context: {approval_context}")
        
        message_parts.append("\n✅ Auto-commit is now enabled for these files")
        
        notification = BossNotification(
            type=NotificationType.GIT_PROTOCOL,
            priority=NotificationPriority.HIGH,
            title="Boss Approval Received",
            message="\n".join(message_parts),
            timestamp=datetime.now(),
            requires_action=False,
            suggested_actions=[],
            metadata={
                "approved_by": approved_by,
                "file_count": len(files),
                "approval_context": approval_context
            }
        )
        
        return self._send_notification(notification, "✅")