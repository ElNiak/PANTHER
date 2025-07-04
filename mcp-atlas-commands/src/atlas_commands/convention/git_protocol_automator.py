"""Git protocol automation tool for ATLAS development workflow."""

import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

try:
    from pydantic import BaseModel
except ImportError:
    # Fallback for environments without pydantic
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

# Import quality gates if available
try:
    from ..workflow.quality_gates import QualityGates, CheckType, CheckStatus
    QUALITY_GATES_AVAILABLE = True
except ImportError:
    QUALITY_GATES_AVAILABLE = False
    class CheckType:
        LINT = "lint"
        TYPE_CHECK = "type_check"
        TEST = "test"
        CONVENTION = "convention"
    
    class CheckStatus:
        PASSED = "passed"
        FAILED = "failed"
        WARNING = "warning"

# Import boss notifier if available
try:
    from ..workflow.boss_notifier import BossNotifier
    BOSS_NOTIFIER_AVAILABLE = True
except ImportError:
    BOSS_NOTIFIER_AVAILABLE = False


class GitAction(Enum):
    """Git workflow actions."""
    STAGE = "stage"
    REVIEW = "review"
    COMMIT = "commit"
    STATUS = "status"
    APPROVE = "approve"
    AUTO_COMMIT = "auto_commit"


class ProtocolStatus(Enum):
    """Git protocol status states."""
    READY_TO_STAGE = "ready_to_stage"
    STAGED_PENDING_REVIEW = "staged_pending_review"
    REVIEWED_READY_TO_COMMIT = "reviewed_ready_to_commit"
    COMMITTED = "committed"
    ERROR = "error"


class GitProtocolRequest(BaseModel):
    """Request model for Git protocol automation."""
    action: GitAction
    files: Optional[List[str]] = None
    review_context: Optional[str] = None
    commit_message: Optional[str] = None
    auto_notify: bool = True
    approved_by: Optional[str] = None
    approval_context: Optional[str] = None


class GitProtocolResponse(BaseModel):
    """Response model for Git protocol automation."""
    protocol_status: ProtocolStatus
    next_actions: List[str]
    notifications_sent: List[str]
    git_output: Optional[str] = None
    warnings: List[str] = []
    errors: List[str] = []


class GitProtocolAutomator:
    """Automates ATLAS Git workflow: stage → review → commit."""
    
    def __init__(self):
        self.required_checks = [
            "lint_check",
            "type_check", 
            "test_check",
            "convention_check"
        ]
        
        self.boss_notification_methods = [
            "working_log_entry",
            "console_output",
            "status_update"
        ]
        
        self._last_quality_report = None
        self._approval_state = {
            "approved": False,
            "approved_by": None,
            "approval_time": None,
            "approval_context": None,
            "staged_files_at_approval": []
        }
        
        # Initialize boss notifier if available
        if BOSS_NOTIFIER_AVAILABLE:
            self.boss_notifier = BossNotifier()
        else:
            self.boss_notifier = None
    
    def execute_git_protocol(self, request: GitProtocolRequest) -> GitProtocolResponse:
        """
        Execute Git protocol automation step.
        
        Args:
            request: Git protocol request
            
        Returns:
            Git protocol response with status and next actions
        """
        action = request.action
        
        try:
            if action == GitAction.STATUS:
                return self._get_protocol_status()
            elif action == GitAction.STAGE:
                return self._execute_stage_action(request)
            elif action == GitAction.REVIEW:
                return self._execute_review_action(request)
            elif action == GitAction.COMMIT:
                return self._execute_commit_action(request)
            elif action == GitAction.APPROVE:
                return self._execute_approve_action(request)
            elif action == GitAction.AUTO_COMMIT:
                return self.execute_auto_commit_on_approval(request.commit_message)
            else:
                return GitProtocolResponse(
                    protocol_status=ProtocolStatus.ERROR,
                    next_actions=[],
                    notifications_sent=[],
                    errors=[f"Unknown action: {action}"]
                )
        except Exception as e:
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=[],
                notifications_sent=[],
                errors=[f"Git protocol error: {str(e)}"]
            )
    
    def _get_protocol_status(self) -> GitProtocolResponse:
        """Get current Git protocol status."""
        try:
            # Check git status
            status_result = self._run_git_command(["status", "--porcelain"])
            if status_result.returncode != 0:
                return GitProtocolResponse(
                    protocol_status=ProtocolStatus.ERROR,
                    next_actions=[],
                    notifications_sent=[],
                    errors=["Not in a git repository"]
                )
            
            # Check staged files
            staged_result = self._run_git_command(["diff", "--cached", "--name-only"])
            staged_files = staged_result.stdout.strip().split('\n') if staged_result.stdout.strip() else []
            
            # Check unstaged files
            unstaged_result = self._run_git_command(["diff", "--name-only"])
            unstaged_files = unstaged_result.stdout.strip().split('\n') if unstaged_result.stdout.strip() else []
            
            # Check approval state
            approval_status = self.check_approval_status()
            
            # Determine status
            if staged_files:
                if approval_status["approval_valid"]:
                    status = ProtocolStatus.REVIEWED_READY_TO_COMMIT
                    next_actions = ["Ready to commit with approval", "Use 'auto_commit' action"]
                else:
                    status = ProtocolStatus.STAGED_PENDING_REVIEW
                    next_actions = ["Run quality checks", "Get boss review", "Commit after approval"]
            elif unstaged_files:
                status = ProtocolStatus.READY_TO_STAGE
                next_actions = ["Stage files for review"]
            else:
                status = ProtocolStatus.COMMITTED
                next_actions = ["No pending changes"]
            
            output_parts = [f"Staged: {len(staged_files)}, Unstaged: {len(unstaged_files)}"]
            if approval_status["has_approval"]:
                output_parts.append(f"Approved by: {approval_status['approved_by']}")
            
            return GitProtocolResponse(
                protocol_status=status,
                next_actions=next_actions,
                notifications_sent=[],
                git_output=" | ".join(output_parts)
            )
            
        except Exception as e:
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=[],
                notifications_sent=[],
                errors=[f"Status check failed: {str(e)}"]
            )
    
    def _execute_stage_action(self, request: GitProtocolRequest) -> GitProtocolResponse:
        """Execute staging action with quality checks."""
        warnings = []
        notifications = []
        
        # Pre-staging quality checks
        quality_results = self._run_quality_checks(request.files or [])
        if quality_results["errors"]:
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=["Fix quality issues before staging"],
                notifications_sent=[],
                errors=quality_results["errors"]
            )
        
        if quality_results["warnings"]:
            warnings.extend(quality_results["warnings"])
        
        # Stage files
        if request.files:
            # Stage specific files
            git_result = self._run_git_command(["add"] + request.files)
        else:
            # Stage all modified files
            git_result = self._run_git_command(["add", "-A"])
        
        if git_result.returncode != 0:
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=[],
                notifications_sent=[],
                errors=[f"Git add failed: {git_result.stderr}"]
            )
        
        # Notify boss about staging
        if request.auto_notify:
            notifications = self._notify_boss_about_staging(request.files, request.review_context)
        
        return GitProtocolResponse(
            protocol_status=ProtocolStatus.STAGED_PENDING_REVIEW,
            next_actions=[
                "Files staged successfully",
                "Boss notification sent",
                "Awaiting review and testing approval",
                "Run 'git commit' after boss approval"
            ],
            notifications_sent=notifications,
            git_output=git_result.stdout,
            warnings=warnings
        )
    
    def _execute_review_action(self, request: GitProtocolRequest) -> GitProtocolResponse:
        """Execute review action (placeholder for boss review)."""
        # This is primarily for documentation and status tracking
        # Real review happens via boss interaction
        
        notifications = []
        if request.auto_notify:
            notifications = self._notify_boss_about_review_request(request.review_context)
        
        return GitProtocolResponse(
            protocol_status=ProtocolStatus.STAGED_PENDING_REVIEW,
            next_actions=[
                "Review request sent to boss",
                "Waiting for boss to review staged changes",
                "Boss will test and provide approval",
                "Commit will be enabled after approval"
            ],
            notifications_sent=notifications
        )
    
    def _execute_approve_action(self, request: GitProtocolRequest) -> GitProtocolResponse:
        """Record boss approval for staged changes."""
        if not request.approved_by:
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=["Specify who is approving"],
                notifications_sent=[],
                errors=["approved_by field is required for approval action"]
            )
        
        # Record the approval
        success = self.record_boss_approval(request.approved_by, request.approval_context)
        
        if not success:
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=["Stage files before approving"],
                notifications_sent=[],
                errors=["No staged files to approve"]
            )
        
        # Get approval status
        approval_status = self.check_approval_status()
        
        notifications = [f"Approval recorded from {request.approved_by}"]
        if self.boss_notifier:
            notifications.append("Boss notifier updated with approval")
        
        return GitProtocolResponse(
            protocol_status=ProtocolStatus.REVIEWED_READY_TO_COMMIT,
            next_actions=[
                f"Approval recorded for {len(approval_status['approved_files'])} files",
                "Ready for auto-commit or manual commit",
                "Use 'auto_commit' action to commit with approval metadata"
            ],
            notifications_sent=notifications,
            warnings=[]
        )
    
    def _execute_commit_action(self, request: GitProtocolRequest) -> GitProtocolResponse:
        """Execute commit action with ATLAS conventions."""
        # Check if we have staged files
        staged_result = self._run_git_command(["diff", "--cached", "--name-only"])
        staged_files = staged_result.stdout.strip().split('\n') if staged_result.stdout.strip() else []
        
        if not staged_files:
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=["Stage files before committing"],
                notifications_sent=[],
                errors=["No staged files to commit"]
            )
        
        # Generate commit message if not provided
        commit_message = request.commit_message
        if not commit_message:
            commit_message = self._generate_commit_message(staged_files)
        
        # Add ATLAS signature
        atlas_signature = """

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
        
        full_commit_message = commit_message + atlas_signature
        
        # Commit with message
        git_result = self._run_git_command(["commit", "-m", full_commit_message])
        
        if git_result.returncode != 0:
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=[],
                notifications_sent=[],
                errors=[f"Git commit failed: {git_result.stderr}"]
            )
        
        # Notify about successful commit
        notifications = []
        if request.auto_notify:
            notifications = self._notify_boss_about_commit(commit_message, staged_files)
        
        return GitProtocolResponse(
            protocol_status=ProtocolStatus.COMMITTED,
            next_actions=[
                "Commit successful",
                "Boss notified of completion",
                "Ready for next development cycle"
            ],
            notifications_sent=notifications,
            git_output=git_result.stdout
        )
    
    def _run_quality_checks(self, files: List[str]) -> Dict[str, List[str]]:
        """Run quality checks on files before staging."""
        errors = []
        warnings = []
        
        # Check if files exist
        for file_path in files:
            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
        
        if errors:
            return {"errors": errors, "warnings": warnings}
        
        # Use quality gates if available
        if QUALITY_GATES_AVAILABLE:
            try:
                quality_gates = QualityGates()
                
                # Get recommended checks for these files
                check_types = quality_gates.get_recommended_checks(files)
                
                # Run quality gates with auto-fix enabled
                report = quality_gates.run_quality_gates(
                    files=files,
                    check_types=check_types,
                    auto_fix=True
                )
                
                # Convert report to errors/warnings
                for check in report.checks:
                    if check.status == CheckStatus.FAILED:
                        errors.append(f"{check.check_type.value}: {check.message}")
                        if check.file_issues:
                            for file_path, issues in check.file_issues.items():
                                for issue in issues[:3]:  # First 3 issues per file
                                    errors.append(f"  {file_path}: {issue}")
                    elif check.status == CheckStatus.WARNING:
                        warnings.append(f"{check.check_type.value}: {check.message}")
                
                # Add fix suggestions as warnings
                for suggestion in report.fix_suggestions:
                    warnings.append(f"Suggestion: {suggestion}")
                
                # Store quality report for later reference
                self._last_quality_report = report
                
            except Exception as e:
                warnings.append(f"Quality gates error: {str(e)}")
                # Fall back to basic checks
                return self._run_basic_quality_checks(files)
        else:
            # Fall back to basic checks
            return self._run_basic_quality_checks(files)
        
        return {"errors": errors, "warnings": warnings}
    
    def _run_basic_quality_checks(self, files: List[str]) -> Dict[str, List[str]]:
        """Run basic quality checks when quality gates not available."""
        errors = []
        warnings = []
        
        # Python-specific checks
        python_files = [f for f in files if f.endswith('.py')]
        if python_files:
            # Basic syntax check
            for py_file in python_files:
                try:
                    with open(py_file, 'r') as f:
                        compile(f.read(), py_file, 'exec')
                except SyntaxError as e:
                    errors.append(f"Syntax error in {py_file}: {e}")
                except Exception as e:
                    warnings.append(f"Could not validate {py_file}: {e}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _notify_boss_about_staging(self, files: Optional[List[str]], context: Optional[str]) -> List[str]:
        """Notify boss about staging completion."""
        if self.boss_notifier:
            # Use boss notifier for rich notifications
            quality_report = None
            if hasattr(self, '_last_quality_report') and self._last_quality_report:
                quality_report = {
                    "overall_status": self._last_quality_report.overall_status.value,
                    "warnings": [check.message for check in self._last_quality_report.checks 
                               if check.status == CheckStatus.WARNING],
                    "errors": [check.message for check in self._last_quality_report.checks 
                             if check.status == CheckStatus.FAILED]
                }
            
            return self.boss_notifier.notify_git_staging(files, quality_report, context)
        else:
            # Fallback to basic notifications
            notifications = []
            
            # Create working log entry
            log_entry = self._create_working_log_entry("staging", files, context)
            notifications.append(f"Working log updated: {log_entry}")
            
            # Console notification
            file_list = ", ".join(files) if files else "all modified files"
            console_msg = f"📝 ATLAS: Staged {file_list} for review"
            print(console_msg)
            notifications.append(f"Console: {console_msg}")
            
            return notifications
    
    def _notify_boss_about_review_request(self, context: Optional[str]) -> List[str]:
        """Notify boss about review request."""
        if self.boss_notifier:
            # Get staged files
            staged_result = self._run_git_command(["diff", "--cached", "--name-only"])
            staged_files = staged_result.stdout.strip().split('\n') if staged_result.stdout.strip() else []
            
            # Get quality summary
            quality_summary = None
            blocking_issues = None
            if hasattr(self, '_last_quality_report') and self._last_quality_report:
                report = self._last_quality_report
                if report.overall_status == CheckStatus.PASSED:
                    quality_summary = "All quality checks passed ✓"
                elif report.overall_status == CheckStatus.WARNING:
                    quality_summary = f"{len([c for c in report.checks if c.status == CheckStatus.WARNING])} warnings (non-blocking)"
                else:
                    blocking_issues = []
                    for check in report.checks:
                        if check.status == CheckStatus.FAILED:
                            blocking_issues.append(check.message)
            
            return self.boss_notifier.notify_review_request(staged_files, quality_summary, blocking_issues)
        else:
            # Fallback to basic notifications
            notifications = []
            
            # Console notification
            console_msg = f"👀 ATLAS: Review requested - {context or 'staged changes ready for review'}"
            print(console_msg)
            notifications.append(f"Console: {console_msg}")
            
            return notifications
    
    def _notify_boss_about_commit(self, commit_message: str, files: List[str]) -> List[str]:
        """Notify boss about successful commit."""
        notifications = []
        
        # Create working log entry
        log_entry = self._create_working_log_entry("commit", files, commit_message)
        notifications.append(f"Working log updated: {log_entry}")
        
        # Console notification
        first_line = commit_message.split('\n')[0]
        console_msg = f"✅ ATLAS: Committed changes - {first_line}"
        print(console_msg)
        notifications.append(f"Console: {console_msg}")
        
        return notifications
    
    def _create_working_log_entry(self, action: str, files: Optional[List[str]], context: Optional[str]) -> str:
        """Create working log entry for Git action."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_list = ", ".join(files) if files else "all files"
        
        entry = f"[{timestamp}] Git {action}: {file_list}"
        if context:
            entry += f" - {context}"
        
        # In a real implementation, this would write to WORKING_LOG file
        return entry
    
    def _generate_commit_message(self, staged_files: List[str]) -> str:
        """Generate conventional commit message based on staged files."""
        # Analyze file types and changes
        has_new_files = any(self._is_new_file(f) for f in staged_files)
        has_tests = any("test" in f.lower() for f in staged_files)
        has_docs = any(f.endswith('.md') for f in staged_files)
        has_config = any(f.endswith(('.json', '.yaml', '.yml', '.toml')) for f in staged_files)
        
        # Determine commit type
        if has_new_files:
            commit_type = "feat"
        elif has_tests:
            commit_type = "test"
        elif has_docs:
            commit_type = "docs"
        elif has_config:
            commit_type = "config"
        else:
            commit_type = "refactor"
        
        # Generate description
        if len(staged_files) == 1:
            file_desc = os.path.basename(staged_files[0])
        else:
            file_desc = f"{len(staged_files)} files"
        
        return f"{commit_type}: update {file_desc}"
    
    def _is_new_file(self, file_path: str) -> bool:
        """Check if file is new (not in git history)."""
        try:
            result = self._run_git_command(["log", "--oneline", "--", file_path])
            return result.returncode != 0 or not result.stdout.strip()
        except:
            return True
    
    def _run_git_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run git command and return result."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result
        except subprocess.TimeoutExpired:
            raise Exception("Git command timed out")
        except Exception as e:
            raise Exception(f"Git command failed: {str(e)}")
    
    def record_boss_approval(self, approved_by: str, approval_context: Optional[str] = None) -> bool:
        """
        Record boss approval for staged changes.
        
        Args:
            approved_by: Name/ID of the approver
            approval_context: Optional context or comments from the review
            
        Returns:
            True if approval recorded successfully
        """
        # Get current staged files
        staged_result = self._run_git_command(["diff", "--cached", "--name-only"])
        staged_files = staged_result.stdout.strip().split('\n') if staged_result.stdout.strip() else []
        
        if not staged_files:
            return False
        
        # Record approval state
        self._approval_state = {
            "approved": True,
            "approved_by": approved_by,
            "approval_time": datetime.now(),
            "approval_context": approval_context,
            "staged_files_at_approval": staged_files
        }
        
        # Notify about approval
        if self.boss_notifier:
            self.boss_notifier.notify_approval_received(approved_by, staged_files, approval_context)
        else:
            print(f"✅ ATLAS: Approval received from {approved_by} for {len(staged_files)} files")
        
        return True
    
    def execute_auto_commit_on_approval(self, commit_message: Optional[str] = None) -> GitProtocolResponse:
        """
        Execute auto-commit after boss approval.
        
        Args:
            commit_message: Optional custom commit message
            
        Returns:
            Git protocol response with commit status
        """
        # Check if we have approval
        if not self._approval_state.get("approved", False):
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=["Get boss approval before auto-commit"],
                notifications_sent=[],
                errors=["No approval recorded. Boss must approve staged changes first."]
            )
        
        # Check if staged files match approval
        staged_result = self._run_git_command(["diff", "--cached", "--name-only"])
        current_staged = staged_result.stdout.strip().split('\n') if staged_result.stdout.strip() else []
        approved_files = self._approval_state.get("staged_files_at_approval", [])
        
        if set(current_staged) != set(approved_files):
            return GitProtocolResponse(
                protocol_status=ProtocolStatus.ERROR,
                next_actions=["Re-stage original files or get new approval"],
                notifications_sent=[],
                errors=["Staged files have changed since approval. New approval required."],
                warnings=[f"Approved: {approved_files}", f"Current: {current_staged}"]
            )
        
        # Generate commit message with approval info
        if not commit_message:
            commit_message = self._generate_commit_message(current_staged)
        
        # Add approval information to commit message
        approval_info = f"\n\nApproved-by: {self._approval_state['approved_by']}"
        if self._approval_state.get('approval_context'):
            approval_info += f"\nApproval-context: {self._approval_state['approval_context']}"
        
        commit_message += approval_info
        
        # Execute commit
        commit_request = GitProtocolRequest(
            action=GitAction.COMMIT,
            commit_message=commit_message,
            auto_notify=True
        )
        
        response = self._execute_commit_action(commit_request)
        
        # Clear approval state after successful commit
        if response.protocol_status == ProtocolStatus.COMMITTED:
            # Store approver before clearing
            approver = self._approval_state.get('approved_by', 'boss')
            
            # Add auto-commit notification
            response.notifications_sent.append(f"Auto-commit executed after approval from {approver}")
            
            # Now clear the approval state
            self._approval_state = {
                "approved": False,
                "approved_by": None,
                "approval_time": None,
                "approval_context": None,
                "staged_files_at_approval": []
            }
        
        return response
    
    def check_approval_status(self) -> Dict[str, Any]:
        """
        Check current approval status.
        
        Returns:
            Dictionary with approval state information
        """
        # Get current staged files
        staged_result = self._run_git_command(["diff", "--cached", "--name-only"])
        current_staged = staged_result.stdout.strip().split('\n') if staged_result.stdout.strip() else []
        
        status = {
            "has_approval": self._approval_state.get("approved", False),
            "approved_by": self._approval_state.get("approved_by"),
            "approval_time": self._approval_state.get("approval_time"),
            "approval_context": self._approval_state.get("approval_context"),
            "approved_files": self._approval_state.get("staged_files_at_approval", []),
            "current_staged_files": current_staged,
            "approval_valid": False
        }
        
        # Check if approval is still valid
        if status["has_approval"] and set(current_staged) == set(status["approved_files"]):
            status["approval_valid"] = True
        
        return status