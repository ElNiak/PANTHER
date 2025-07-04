"""Workflow enforcement for ATLAS command system."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import json


class CommandStatus(Enum):
    """Status of command execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep:
    """Represents a step in a workflow."""
    
    def __init__(
        self,
        command: str,
        target: str,
        parameters: Dict[str, Any],
        prerequisites: List[str] = None,
        optional: bool = False
    ):
        self.command = command
        self.target = target
        self.parameters = parameters
        self.prerequisites = prerequisites or []
        self.optional = optional
        self.status = CommandStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.validation_errors: List[str] = []


class WorkflowEnforcer:
    """Enforces workflow execution order and validation."""
    
    def __init__(self):
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}
        self.validation_rules = self._define_validation_rules()
    
    def _define_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Define validation rules for command sequences."""
        
        return {
            "plan_before_execute": {
                "description": "Execute command requires prior planning",
                "required_predecessors": ["plan"],
                "target_commands": ["execute"],
                "severity": "error"
            },
            "verify_after_execute": {
                "description": "Verification should follow execution",
                "recommended_successors": ["verify"],
                "target_commands": ["execute"],
                "severity": "warning"
            },
            "complete_after_verify": {
                "description": "Completion should follow verification",
                "required_predecessors": ["verify"],
                "target_commands": ["complete"],
                "severity": "error"
            },
            "analyze_before_design": {
                "description": "Design should be based on analysis",
                "recommended_predecessors": ["analyze"],
                "target_commands": ["design"],
                "severity": "warning"
            },
            "design_before_decompose": {
                "description": "Decomposition should follow design",
                "recommended_predecessors": ["design"],
                "target_commands": ["decompose"],
                "severity": "warning"
            }
        }
    
    def create_workflow(
        self,
        workflow_id: str,
        pattern: str,
        target: str,
        flags: Optional[Dict[str, Any]] = None
    ) -> List[WorkflowStep]:
        """Create a workflow based on pattern."""
        
        workflow_patterns = {
            "explore-plan-code-commit": [
                ("plan", {}),
                ("analyze", {"focus": "architecture"}),
                ("design", {"approach": "detailed"}),
                ("decompose", {}),
                ("execute", {}),
                ("verify", {"level": "thorough"}),
                ("complete", {"archive_level": "comprehensive"})
            ],
            "quick-fix": [
                ("plan", {"complexity": "simple"}),
                ("execute", {"mode": "quick"}),
                ("verify", {"level": "basic"}),
                ("complete", {"archive_level": "minimal"})
            ],
            "refactor": [
                ("analyze", {"focus": "refactoring"}),
                ("plan", {"type": "refactor"}),
                ("execute", {"type": "refactor"}),
                ("verify", {"level": "thorough"}),
                ("complete", {"archive_level": "standard"})
            ],
            "tdd": [
                ("plan", {"approach": "tdd"}),
                ("design", {"focus": "test_driven"}),
                ("execute", {"pattern": "red_green_refactor"}),
                ("verify", {"level": "comprehensive"}),
                ("complete", {"archive_level": "standard"})
            ]
        }
        
        if pattern not in workflow_patterns:
            raise ValueError(f"Unknown workflow pattern: {pattern}")
        
        steps = []
        for i, (command, params) in enumerate(workflow_patterns[pattern]):
            # Merge pattern parameters with user flags
            all_params = {**params}
            if flags:
                all_params.update(flags)
            
            # Set prerequisites (previous step)
            prerequisites = [f"{workflow_id}_{i-1}"] if i > 0 else []
            
            step = WorkflowStep(
                command=command,
                target=target,
                parameters=all_params,
                prerequisites=prerequisites
            )
            steps.append(step)
        
        self.workflows[workflow_id] = steps
        self.execution_history[workflow_id] = []
        
        return steps
    
    def validate_command_execution(
        self,
        workflow_id: str,
        command: str,
        target: str
    ) -> Tuple[bool, List[str]]:
        """Validate if command can be executed in current workflow state."""
        
        if workflow_id not in self.workflows:
            return True, []  # No workflow constraints
        
        workflow = self.workflows[workflow_id]
        errors = []
        warnings = []
        
        # Find current step
        current_step = None
        for step in workflow:
            if step.command == command and step.target == target:
                current_step = step
                break
        
        if not current_step:
            errors.append(f"Command '{command}' not found in workflow '{workflow_id}'")
            return False, errors
        
        # Check prerequisites
        for prereq_id in current_step.prerequisites:
            prereq_completed = False
            for step in workflow:
                if f"{workflow_id}_{workflow.index(step)}" == prereq_id:
                    if step.status == CommandStatus.COMPLETED:
                        prereq_completed = True
                    break
            
            if not prereq_completed:
                errors.append(f"Prerequisite '{prereq_id}' not completed")
        
        # Check validation rules
        rule_violations = self._check_validation_rules(workflow_id, command, target)
        errors.extend([v for v in rule_violations if v.get('severity') == 'error'])
        warnings.extend([v for v in rule_violations if v.get('severity') == 'warning'])
        
        # Check if step is already completed
        if current_step.status == CommandStatus.COMPLETED:
            warnings.append(f"Command '{command}' already completed for target '{target}'")
        
        return len(errors) == 0, errors + [f"Warning: {w['description']}" for w in warnings]
    
    def _check_validation_rules(
        self,
        workflow_id: str,
        command: str,
        target: str
    ) -> List[Dict[str, Any]]:
        """Check validation rules against workflow state."""
        
        violations = []
        workflow = self.workflows[workflow_id]
        
        for rule_name, rule in self.validation_rules.items():
            if command in rule.get("target_commands", []):
                
                # Check required predecessors
                if "required_predecessors" in rule:
                    for required_cmd in rule["required_predecessors"]:
                        found = False
                        for step in workflow:
                            if (step.command == required_cmd and 
                                step.target == target and 
                                step.status == CommandStatus.COMPLETED):
                                found = True
                                break
                        
                        if not found:
                            violations.append({
                                "rule": rule_name,
                                "description": f"{rule['description']}: Missing {required_cmd}",
                                "severity": rule["severity"]
                            })
                
                # Check recommended predecessors (warnings only)
                if "recommended_predecessors" in rule:
                    for recommended_cmd in rule["recommended_predecessors"]:
                        found = False
                        for step in workflow:
                            if (step.command == recommended_cmd and 
                                step.target == target and 
                                step.status == CommandStatus.COMPLETED):
                                found = True
                                break
                        
                        if not found:
                            violations.append({
                                "rule": rule_name,
                                "description": f"{rule['description']}: Recommended {recommended_cmd} not found",
                                "severity": "warning"
                            })
        
        return violations
    
    def start_command_execution(
        self,
        workflow_id: str,
        command: str,
        target: str
    ) -> bool:
        """Mark command as started in workflow."""
        
        if workflow_id not in self.workflows:
            return True  # No workflow tracking
        
        workflow = self.workflows[workflow_id]
        
        for step in workflow:
            if step.command == command and step.target == target:
                step.status = CommandStatus.IN_PROGRESS
                step.started_at = datetime.now()
                
                # Record in execution history
                self.execution_history[workflow_id].append({
                    "action": "started",
                    "command": command,
                    "target": target,
                    "timestamp": datetime.now().isoformat()
                })
                
                return True
        
        return False
    
    def complete_command_execution(
        self,
        workflow_id: str,
        command: str,
        target: str,
        result: Dict[str, Any],
        success: bool = True
    ) -> bool:
        """Mark command as completed in workflow."""
        
        if workflow_id not in self.workflows:
            return True  # No workflow tracking
        
        workflow = self.workflows[workflow_id]
        
        for step in workflow:
            if step.command == command and step.target == target:
                step.status = CommandStatus.COMPLETED if success else CommandStatus.FAILED
                step.completed_at = datetime.now()
                step.result = result
                
                # Record in execution history
                self.execution_history[workflow_id].append({
                    "action": "completed",
                    "command": command,
                    "target": target,
                    "success": success,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return True
        
        return False
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current status of workflow."""
        
        if workflow_id not in self.workflows:
            return {"error": "Workflow not found"}
        
        workflow = self.workflows[workflow_id]
        
        total_steps = len(workflow)
        completed_steps = len([s for s in workflow if s.status == CommandStatus.COMPLETED])
        failed_steps = len([s for s in workflow if s.status == CommandStatus.FAILED])
        in_progress_steps = len([s for s in workflow if s.status == CommandStatus.IN_PROGRESS])
        
        return {
            "workflow_id": workflow_id,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "in_progress_steps": in_progress_steps,
            "progress_percentage": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "current_step": self._get_current_step(workflow),
            "next_available_steps": self._get_next_available_steps(workflow),
            "steps": [
                {
                    "command": step.command,
                    "target": step.target,
                    "status": step.status.value,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "optional": step.optional
                }
                for step in workflow
            ]
        }
    
    def _get_current_step(self, workflow: List[WorkflowStep]) -> Optional[Dict[str, Any]]:
        """Get the currently executing step."""
        
        for step in workflow:
            if step.status == CommandStatus.IN_PROGRESS:
                return {
                    "command": step.command,
                    "target": step.target,
                    "started_at": step.started_at.isoformat() if step.started_at else None
                }
        
        return None
    
    def _get_next_available_steps(self, workflow: List[WorkflowStep]) -> List[Dict[str, Any]]:
        """Get steps that are ready to execute."""
        
        available_steps = []
        
        for step in workflow:
            if step.status == CommandStatus.PENDING:
                # Check if all prerequisites are met
                prerequisites_met = True
                for prereq_id in step.prerequisites:
                    prereq_step_index = int(prereq_id.split('_')[-1])
                    if prereq_step_index < len(workflow):
                        prereq_step = workflow[prereq_step_index]
                        if prereq_step.status != CommandStatus.COMPLETED:
                            prerequisites_met = False
                            break
                
                if prerequisites_met:
                    available_steps.append({
                        "command": step.command,
                        "target": step.target,
                        "parameters": step.parameters,
                        "optional": step.optional
                    })
        
        return available_steps
    
    def auto_execute_workflow(
        self,
        workflow_id: str,
        auto_continue: bool = False
    ) -> Dict[str, Any]:
        """Auto-execute workflow steps (for YOLO mode)."""
        
        if workflow_id not in self.workflows:
            return {"error": "Workflow not found"}
        
        workflow = self.workflows[workflow_id]
        execution_results = []
        
        for step in workflow:
            if step.status == CommandStatus.PENDING:
                # Check prerequisites
                can_execute, errors = self.validate_command_execution(
                    workflow_id, step.command, step.target
                )
                
                if not can_execute and not step.optional:
                    return {
                        "status": "blocked",
                        "step": step.command,
                        "errors": errors,
                        "executed_steps": execution_results
                    }
                
                if can_execute or step.optional:
                    # Mark as started
                    self.start_command_execution(workflow_id, step.command, step.target)
                    
                    # Simulate execution (in real implementation, would call actual command)
                    execution_result = {
                        "command": step.command,
                        "target": step.target,
                        "parameters": step.parameters,
                        "simulated": True,
                        "success": True
                    }
                    
                    # Mark as completed
                    self.complete_command_execution(
                        workflow_id, step.command, step.target, execution_result
                    )
                    
                    execution_results.append(execution_result)
                    
                    if not auto_continue:
                        break  # Execute one step at a time
        
        return {
            "status": "success",
            "executed_steps": execution_results,
            "workflow_status": self.get_workflow_status(workflow_id)
        }