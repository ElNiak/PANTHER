"""
Adaptive Command Selection Module - Enhanced with Bayesian Learning

Provides intelligent command recommendations based on context, historical patterns,
and project state analysis. Now uses dynamic Bayesian confidence and Thompson Sampling
to replace the static confidence system that provided 0.000 improvement.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from .pattern_analyzer import WorkflowPatternAnalyzer
from .task_auto_generator import TaskAutoGenerator, TaskComplexity
from .validator import ValidationLevel
from .adaptive_recommendation_engine import (
    AdaptiveRecommendationEngine, 
    AdaptiveRecommendation,
    RecommendationMode
)


class ContextType(Enum):
    """Types of project context for command selection"""
    GREENFIELD = "greenfield"      # New project/feature
    MAINTENANCE = "maintenance"    # Bug fixes, updates
    REFACTORING = "refactoring"   # Code restructuring
    INTEGRATION = "integration"   # Adding new components
    DEBUGGING = "debugging"       # Problem investigation
    OPTIMIZATION = "optimization" # Performance improvements
    DOCUMENTATION = "documentation" # Content creation


@dataclass
class CommandRecommendation:
    """Represents a command recommendation with metadata"""
    command: str
    confidence: float
    reasoning: str
    prerequisites: List[str]
    expected_outcome: str
    risk_level: str  # low, medium, high
    estimated_time: float  # hours


@dataclass
class ProjectContext:
    """Current project state context for command selection"""
    domain: str
    complexity: str
    current_phase: str
    previous_commands: List[str]
    success_indicators: List[str]
    blocking_issues: List[str]
    available_resources: List[str]


class AdaptiveCommandSelector:
    """
    Selects optimal commands using adaptive learning and Bayesian confidence.
    
    This class now uses the new AdaptiveRecommendationEngine to provide
    dynamic confidence calculations that actually improve over time,
    replacing the static system that provided 0.000 improvement.
    """
    
    # Command categories and their typical success patterns
    COMMAND_CATEGORIES = {
        "exploration": ["explore", "analyze", "investigate", "research"],
        "planning": ["plan", "design", "decompose", "estimate"],
        "implementation": ["execute", "code", "implement", "develop"],
        "validation": ["test", "verify", "validate", "review"],
        "completion": ["complete", "document", "deploy", "finalize"]
    }
    
    # Context-specific command preferences (kept for compatibility)
    CONTEXT_PREFERENCES = {
        ContextType.GREENFIELD: {
            "preferred_sequence": ["explore", "plan", "design", "implement", "test"],
            "risk_tolerance": "medium",
            "emphasis": "planning"
        },
        ContextType.MAINTENANCE: {
            "preferred_sequence": ["investigate", "analyze", "fix", "test", "verify"],
            "risk_tolerance": "low",
            "emphasis": "validation"
        },
        ContextType.REFACTORING: {
            "preferred_sequence": ["analyze", "plan", "refactor", "test", "verify"],
            "risk_tolerance": "low",
            "emphasis": "testing"
        },
        ContextType.DEBUGGING: {
            "preferred_sequence": ["investigate", "reproduce", "analyze", "fix", "validate"],
            "risk_tolerance": "low",
            "emphasis": "investigation"
        },
        ContextType.OPTIMIZATION: {
            "preferred_sequence": ["profile", "analyze", "optimize", "benchmark", "validate"],
            "risk_tolerance": "medium",
            "emphasis": "measurement"
        }
    }
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize with new adaptive recommendation engine"""
        # Legacy components for compatibility
        self.pattern_analyzer = WorkflowPatternAnalyzer()
        self.task_generator = TaskAutoGenerator(storage_path)
        
        # NEW: Adaptive recommendation engine with Bayesian learning
        self.adaptive_engine = AdaptiveRecommendationEngine(
            storage_path=storage_path,
            recommendation_mode=RecommendationMode.BALANCED
        )
        
        # Keep legacy for gradual migration
        self.historical_patterns = {}
        self.success_cache = {}
    
    def analyze_context(self, 
                       task_description: str,
                       domain: str,
                       current_phase: str = "planning",
                       previous_commands: List[str] = None,
                       project_state: Dict[str, Any] = None) -> ProjectContext:
        """
        Analyze current project context to inform command selection.
        
        Args:
            task_description: Description of current task
            domain: Project domain
            current_phase: Current workflow phase
            previous_commands: Previously executed commands
            project_state: Additional project state information
            
        Returns:
            Analyzed project context
        """
        previous_commands = previous_commands or []
        project_state = project_state or {}
        
        # Determine complexity using task generator
        complexity, _ = self.task_generator.analyze_complexity(task_description, domain)
        
        # Extract success indicators from description
        success_indicators = self._extract_success_indicators(task_description)
        
        # Identify potential blocking issues
        blocking_issues = self._identify_blocking_issues(task_description, previous_commands)
        
        # Determine available resources
        available_resources = self._determine_available_resources(project_state)
        
        # Add task description as a special success indicator for classification
        # This is a workaround to pass task description to _classify_context_type
        success_indicators_with_desc = success_indicators.copy()
        success_indicators_with_desc.insert(0, f"__TASK_DESC__:{task_description}")
        
        return ProjectContext(
            domain=domain,
            complexity=complexity.value,
            current_phase=current_phase,
            previous_commands=previous_commands,
            success_indicators=success_indicators_with_desc,
            blocking_issues=blocking_issues,
            available_resources=available_resources
        )
    
    def recommend_commands(self,
                          context: ProjectContext,
                          limit: int = 5,
                          include_alternatives: bool = True) -> List[CommandRecommendation]:
        """
        Generate command recommendations using adaptive Bayesian learning.
        
        CRITICAL CHANGE: Now uses dynamic Bayesian confidence instead of static caps!
        This addresses the root cause: static confidence calculation prevented learning.

        Args:
            context: Analyzed project context
            limit: Maximum number of recommendations
            include_alternatives: Whether to include alternative approaches
            
        Returns:
            List of command recommendations with dynamic confidence that actually improves
        """
        # Extract task description from success indicators (legacy compatibility)
        task_description = ""
        for indicator in context.success_indicators:
            if indicator.startswith("__TASK_DESC__:"):
                task_description = indicator.replace("__TASK_DESC__:", "")
                break
        
        if not task_description:
            task_description = f"Task in {context.domain} domain, phase: {context.current_phase}"
        
        # Use NEW adaptive recommendation engine with Bayesian confidence
        adaptive_recommendations = self.adaptive_engine.recommend_commands(
            task_description=task_description,
            domain=context.domain,
            current_phase=context.current_phase,
            previous_commands=context.previous_commands,
            project_state={
                "complexity": context.complexity,
                "blocking_issues": context.blocking_issues,
                "available_resources": context.available_resources
            },
            limit=limit
        )
        
        # Convert AdaptiveRecommendation to legacy CommandRecommendation for compatibility
        legacy_recommendations = []
        for adaptive_rec in adaptive_recommendations:
            legacy_rec = CommandRecommendation(
                command=adaptive_rec.command,
                confidence=adaptive_rec.expected_confidence,  # Use expected confidence for predictable learning verification
                reasoning=adaptive_rec.reasoning,
                prerequisites=adaptive_rec.prerequisites,
                expected_outcome=adaptive_rec.expected_outcome,
                risk_level=adaptive_rec.risk_level,
                estimated_time=adaptive_rec.estimated_time
            )
            legacy_recommendations.append(legacy_rec)
        
        # Add alternatives using legacy method if needed
        if include_alternatives and len(legacy_recommendations) < limit:
            alternatives = self._get_alternative_recommendations(context, legacy_recommendations)
            legacy_recommendations.extend(alternatives[:limit - len(legacy_recommendations)])
        
        return legacy_recommendations[:limit]
    
    def learn_from_outcome(self,
                          commands_used: List[str],
                          context: ProjectContext,
                          outcome: str,
                          execution_time: float = None,
                          notes: str = None) -> Dict[str, Any]:
        """
        Learn from command execution outcomes to improve future recommendations.
        
        CRITICAL CHANGE: Now uses adaptive learning engine to update Bayesian confidence!
        This is where the actual learning happens that was missing from the old system.
        
        Args:
            commands_used: Commands that were executed
            context: Context in which commands were used
            outcome: success/failure/partial
            execution_time: Time taken for execution
            notes: Additional notes about the outcome
            
        Returns:
            Learning impact summary showing confidence improvements
        """
        # Extract task description from context
        task_description = ""
        for indicator in context.success_indicators:
            if indicator.startswith("__TASK_DESC__:"):
                task_description = indicator.replace("__TASK_DESC__:", "")
                break
        
        if not task_description:
            task_description = f"Task in {context.domain} domain, phase: {context.current_phase}"
        
        # Use NEW adaptive learning engine to update Bayesian confidence distributions
        learning_impact = self.adaptive_engine.learn_from_outcome(
            commands_used=commands_used,
            task_description=task_description,
            domain=context.domain,
            current_phase=context.current_phase,
            outcome=outcome,
            execution_time=execution_time,
            notes=notes
        )
        
        # Keep legacy pattern storage for compatibility
        learning_key = f"{context.domain}_{context.complexity}_{context.current_phase}"
        
        if learning_key not in self.success_cache:
            self.success_cache[learning_key] = {
                "successful_patterns": [],
                "failed_patterns": [],
                "timing_data": {},
                "context_notes": []
            }
        
        # Record the pattern and outcome (legacy)
        pattern_record = {
            "commands": commands_used,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "notes": notes
        }
        
        if outcome == "success":
            self.success_cache[learning_key]["successful_patterns"].append(pattern_record)
        else:
            self.success_cache[learning_key]["failed_patterns"].append(pattern_record)
        
        # Update timing data (legacy)
        if execution_time:
            for cmd in commands_used:
                if cmd not in self.success_cache[learning_key]["timing_data"]:
                    self.success_cache[learning_key]["timing_data"][cmd] = []
                self.success_cache[learning_key]["timing_data"][cmd].append(execution_time / len(commands_used))
        
        return learning_impact
    
    def get_learning_effectiveness_report(self) -> Dict[str, Any]:
        """
        Get comprehensive report on learning effectiveness.
        
        This is the key method that demonstrates adaptive improvement,
        replacing the static system that provided 0.000 improvement.
        
        Returns:
            Detailed report showing actual learning improvements
        """
        return self.adaptive_engine.get_learning_effectiveness_report()
    
    def analyze_command_learning_pattern(self, command: str, domain: str) -> Dict[str, Any]:
        """
        Analyze learning patterns for specific command.
        
        Args:
            command: Command to analyze
            domain: Domain context
            
        Returns:
            Detailed learning pattern analysis
        """
        return self.adaptive_engine.analyze_command_learning_pattern(command, domain)
    
    def get_confidence_explanation(self, recommendation: CommandRecommendation) -> Dict[str, Any]:
        """
        Provide detailed explanation of confidence scoring.
        
        Args:
            recommendation: Command recommendation to explain
            
        Returns:
            Detailed confidence breakdown
        """
        return {
            "command": recommendation.command,
            "confidence": recommendation.confidence,
            "factors": {
                "historical_success": "Pattern appears in successful workflows",
                "context_match": "Command fits current project context",
                "sequence_logic": "Command follows logical workflow progression",
                "risk_assessment": f"Risk level: {recommendation.risk_level}"
            },
            "prerequisites_met": len(recommendation.prerequisites) == 0,
            "estimated_value": recommendation.expected_outcome,
            "time_investment": f"{recommendation.estimated_time:.1f} hours"
        }
    
    # Private helper methods
    
    def _classify_context_type(self, context: ProjectContext) -> ContextType:
        """Classify the type of work context based on description and state"""
        # Extract task description from success indicators (if present)
        task_desc = ""
        for indicator in context.success_indicators:
            if indicator.startswith("__TASK_DESC__:"):
                task_desc = indicator.replace("__TASK_DESC__:", "")
                break
        
        # Combine all context information for classification
        description_lower = " ".join([
            task_desc,
            context.domain,
            context.current_phase,
            " ".join(context.success_indicators)
        ]).lower()
        
        # Enhanced keyword matching with priority order
        # Check debugging first (highest priority)
        debug_keywords = [
            'debug', 'troubleshoot', 'diagnose', 'investigate',
            'memory leak', 'crash', 'error', 'failure', 'timeout',
            'not working', 'broken', 'issue', 'problem', 'bug',
            'trace', 'analyze error', 'fix bug'
        ]
        if any(keyword in description_lower for keyword in debug_keywords):
            return ContextType.DEBUGGING
        
        # Check refactoring (before maintenance/fixes)
        refactor_keywords = [
            'refactor', 'restructure', 'reorganize', 'clean up',
            'extract', 'consolidate', 'simplify', 'modernize',
            'improve code', 'technical debt', 'redesign',
            'decouple', 'modularize'
        ]
        if any(keyword in description_lower for keyword in refactor_keywords):
            return ContextType.REFACTORING
        
        # Check optimization
        optimize_keywords = [
            'optimize', 'performance', 'speed up', 'faster',
            'efficiency', 'reduce latency', 'improve response',
            'scale', 'bottleneck', 'tune', 'enhance performance'
        ]
        if any(keyword in description_lower for keyword in optimize_keywords):
            return ContextType.OPTIMIZATION
        
        # Check maintenance (general fixes)
        maintenance_keywords = [
            'fix', 'repair', 'patch', 'update', 'maintain',
            'resolve', 'correct', 'address', 'handle'
        ]
        if any(keyword in description_lower for keyword in maintenance_keywords):
            return ContextType.MAINTENANCE
        
        # Check integration
        integration_keywords = [
            'integrate', 'connect', 'link', 'interface',
            'api integration', 'webhook', 'sync', 'bridge'
        ]
        if any(keyword in description_lower for keyword in integration_keywords):
            return ContextType.INTEGRATION
        
        # Check documentation
        doc_keywords = [
            'document', 'documentation', 'readme', 'guide',
            'tutorial', 'api doc', 'write doc', 'update doc'
        ]
        if any(keyword in description_lower for keyword in doc_keywords):
            return ContextType.DOCUMENTATION
        
        # Check greenfield/creation (last as it's most general)
        create_keywords = [
            'build', 'create', 'implement', 'develop', 'new',
            'feature', 'add', 'establish', 'design', 'architect',
            'from scratch', 'initialize', 'setup', 'start'
        ]
        if any(keyword in description_lower for keyword in create_keywords):
            return ContextType.GREENFIELD
        
        # Default to GREENFIELD for unclear tasks
        return ContextType.GREENFIELD
    
    def _determine_workflow_position(self, previous_commands: List[str], preferred_sequence: List[str]) -> int:
        """Determine where we are in the typical workflow sequence"""
        if not previous_commands:
            return 0
        
        # Find the last command that matches our preferred sequence
        last_position = -1
        for cmd in reversed(previous_commands):
            for i, seq_cmd in enumerate(preferred_sequence):
                if seq_cmd in cmd.lower():
                    last_position = max(last_position, i)
                    break
        
        return last_position + 1 if last_position >= 0 else 0
    
    def _get_sequence_recommendations(self,
                                    context: ProjectContext,
                                    preferences: Dict[str, Any],
                                    position: int) -> List[Dict[str, Any]]:
        """Get recommendations based on preferred workflow sequence"""
        recommendations = []
        sequence = preferences["preferred_sequence"]
        
        # Recommend next 2-3 commands in sequence
        for i in range(position, min(position + 3, len(sequence))):
            recommendations.append({
                "command": sequence[i],
                "source": "sequence",
                "position": i,
                "context_fit": 0.8  # High fit for sequence-based
            })
        
        return recommendations
    
    def _get_pattern_recommendations(self, context: ProjectContext) -> List[Dict[str, Any]]:
        """Get recommendations based on historical patterns"""
        recommendations = []
        
        # Check our success cache for similar contexts
        learning_key = f"{context.domain}_{context.complexity}_{context.current_phase}"
        
        if learning_key in self.success_cache:
            successful_patterns = self.success_cache[learning_key]["successful_patterns"]
            
            # Extract commonly successful commands
            command_counts = {}
            for pattern in successful_patterns:
                for cmd in pattern["commands"]:
                    command_counts[cmd] = command_counts.get(cmd, 0) + 1
            
            # Recommend most successful commands
            for cmd, count in sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                recommendations.append({
                    "command": cmd,
                    "source": "pattern",
                    "success_count": count,
                    "context_fit": 0.7
                })
        
        return recommendations
    
    # DEPRECATED: _score_command method removed - it caused the 0.000 learning improvement
    # 
    # The old _score_command method contained this critical bug:
    #   confidence = min(0.95, base_confidence + context_bonus)
    # 
    # This static cap at 0.95 prevented any learning from affecting confidence values.
    # Learning data was stored but never used to adjust confidence calculations.
    # 
    # NOW REPLACED BY: AdaptiveRecommendationEngine with dynamic Bayesian confidence
    # that actually uses learning data to improve recommendations over time.
    #
    # def _score_command(self, cmd_info, context, preferences):
    #     """REMOVED: Static confidence calculation that prevented learning"""
    #     # This method has been replaced by Bayesian confidence in adaptive_engine
    #     pass
    
    def _get_alternative_recommendations(self,
                                       context: ProjectContext,
                                       existing: List[CommandRecommendation]) -> List[CommandRecommendation]:
        """Generate alternative command recommendations"""
        alternatives = []
        existing_commands = {rec.command for rec in existing}
        
        # Domain-specific alternatives
        domain_alternatives = {
            "automation": ["quick-check", "validate", "monitor"],
            "development": ["review", "optimize", "document"],
            "debugging": ["profile", "trace", "isolate"],
            "testing": ["benchmark", "stress-test", "mock"]
        }
        
        alt_commands = domain_alternatives.get(context.domain, ["review", "validate", "monitor"])
        
        for cmd in alt_commands:
            if cmd not in existing_commands:
                # Use adaptive engine to get learned confidence for alternative commands
                task_description = ""
                for indicator in context.success_indicators:
                    if indicator.startswith("__TASK_DESC__:"):
                        task_description = indicator.replace("__TASK_DESC__:", "")
                        break
                
                if not task_description:
                    task_description = f"Task in {context.domain} domain, phase: {context.current_phase}"
                
                # Get adaptive recommendation for this alternative command
                adaptive_alts = self.adaptive_engine.recommend_commands(
                    task_description=task_description,
                    domain=context.domain,
                    current_phase=context.current_phase,
                    previous_commands=context.previous_commands,
                    project_state={
                        "complexity": context.complexity,
                        "blocking_issues": context.blocking_issues,
                        "available_resources": context.available_resources
                    },
                    candidate_commands=[cmd],
                    limit=1
                )
                
                if adaptive_alts:
                    # Use the adaptive confidence
                    confidence = adaptive_alts[0].expected_confidence
                else:
                    # Fallback to default
                    confidence = 0.4
                
                alternatives.append(CommandRecommendation(
                    command=cmd,
                    confidence=confidence,
                    reasoning=f"Alternative approach for {context.domain} domain",
                    prerequisites=[],
                    expected_outcome=f"Alternative outcome using {cmd}",
                    risk_level="medium",
                    estimated_time=2.0
                ))
        
        return alternatives
    
    def _extract_success_indicators(self, description: str) -> List[str]:
        """Extract success indicators from task description"""
        indicators = []
        description_lower = description.lower()
        
        # Look for measurable outcomes
        if "test" in description_lower:
            indicators.append("tests_passing")
        if "deploy" in description_lower:
            indicators.append("deployment_ready")
        if "performance" in description_lower:
            indicators.append("performance_improved")
        if "bug" in description_lower or "fix" in description_lower:
            indicators.append("issue_resolved")
        
        return indicators
    
    def _identify_blocking_issues(self, description: str, previous_commands: List[str]) -> List[str]:
        """Identify potential blocking issues"""
        issues = []
        description_lower = description.lower()
        
        # Check for common blockers
        if "test" in description_lower and not any("test" in cmd for cmd in previous_commands):
            issues.append("missing_test_setup")
        if "deploy" in description_lower and not any("build" in cmd for cmd in previous_commands):
            issues.append("missing_build_step")
        
        return issues
    
    def _determine_available_resources(self, project_state: Dict[str, Any]) -> List[str]:
        """Determine available project resources"""
        resources = ["basic_tools"]  # Always available
        
        if project_state.get("has_tests"):
            resources.append("test_suite")
        if project_state.get("has_ci"):
            resources.append("continuous_integration")
        if project_state.get("has_docs"):
            resources.append("documentation")
        
        return resources
    
    def _get_command_prerequisites(self, command: str, context: ProjectContext) -> List[str]:
        """Determine prerequisites for a command"""
        prereqs = []
        
        # Common prerequisites
        if command in ["test", "verify"]:
            if "implementation" not in " ".join(context.previous_commands):
                prereqs.append("implementation_required")
        
        if command in ["deploy", "complete"]:
            if "test" not in " ".join(context.previous_commands):
                prereqs.append("testing_required")
        
        return prereqs
    
    def _assess_risk_level(self, command: str, context: ProjectContext, preferences: Dict[str, Any]) -> str:
        """Assess risk level for a command"""
        high_risk_commands = ["deploy", "delete", "migrate", "overwrite"]
        medium_risk_commands = ["refactor", "optimize", "restructure"]
        
        if any(risk_cmd in command.lower() for risk_cmd in high_risk_commands):
            return "high"
        elif any(risk_cmd in command.lower() for risk_cmd in medium_risk_commands):
            return "medium"
        else:
            return "low"
    
    def _generate_reasoning(self, command: str, cmd_info: Dict[str, Any], context: ProjectContext) -> str:
        """Generate reasoning for command recommendation"""
        source = cmd_info["source"]
        
        if source == "sequence":
            return f"Next logical step in {context.domain} workflow sequence"
        elif source == "pattern":
            success_count = cmd_info.get("success_count", 0)
            return f"Command successful in {success_count} similar contexts"
        else:
            return f"Contextually appropriate for {context.complexity} {context.domain} task"
    
    def _estimate_command_time(self, command: str, context: ProjectContext) -> float:
        """Estimate time required for command execution"""
        base_times = {
            "explore": 2.0,
            "plan": 3.0,
            "analyze": 4.0,
            "design": 5.0,
            "implement": 8.0,
            "code": 6.0,
            "test": 3.0,
            "verify": 2.0,
            "review": 2.0,
            "deploy": 1.0,
            "complete": 1.0
        }
        
        base_time = base_times.get(command, 4.0)
        
        # Adjust for complexity
        if context.complexity == "complex":
            base_time *= 1.5
        elif context.complexity == "epic":
            base_time *= 2.0
        elif context.complexity == "simple":
            base_time *= 0.7
        
        return base_time
    
    def _generate_expected_outcome(self, command: str, context: ProjectContext) -> str:
        """Generate expected outcome description"""
        outcomes = {
            "explore": f"Understanding of {context.domain} requirements and constraints",
            "plan": f"Structured approach for {context.complexity} task implementation",
            "analyze": f"Detailed analysis of current {context.domain} state",
            "design": f"Architecture and design artifacts for implementation",
            "implement": f"Working implementation of {context.domain} functionality",
            "test": f"Validated functionality with comprehensive test coverage",
            "verify": f"Confirmed working solution meeting requirements",
            "deploy": f"Live deployment of {context.domain} functionality"
        }
        
        return outcomes.get(command, f"Progress towards {context.domain} task completion")