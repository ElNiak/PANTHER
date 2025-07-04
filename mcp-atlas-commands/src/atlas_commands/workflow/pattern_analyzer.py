"""Workflow pattern analyzer for detecting inefficiencies and suggesting optimizations."""

from datetime import datetime
from typing import Any, Dict, List, Tuple


class WorkflowPatternAnalyzer:
    """Analyzes workflow patterns to detect inefficiencies and suggest optimizations."""
    
    def __init__(self):
        self.known_patterns = self._load_known_patterns()
        self.prerequisite_rules = self._load_prerequisite_rules()
    
    def analyze_patterns(self, workflow_data: List[Dict]) -> Dict:
        """Analyze command sequence patterns in workflow data."""
        patterns = {
            "common_patterns": [],
            "success_patterns": [],
            "failure_patterns": [],
            "sequence_frequency": {},
            "timing_patterns": {}
        }
        
        # Extract command sequences by outcome
        all_sequences = []
        success_sequences = []
        failure_sequences = []
        
        for workflow in workflow_data:
            sequence = workflow.get("command_sequence", [])
            outcome = workflow.get("outcome", "unknown")
            
            all_sequences.append(sequence)
            
            if outcome == "success":
                success_sequences.append(sequence)
            elif outcome == "failure":
                failure_sequences.append(sequence)
        
        # Analyze common patterns (sequences of 2-4 commands)
        for seq_length in [2, 3, 4]:
            pattern_counts = {}
            
            for sequence in all_sequences:
                for i in range(len(sequence) - seq_length + 1):
                    pattern = tuple(sequence[i:i + seq_length])
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            # Find most common patterns
            common = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            patterns["common_patterns"].extend([
                {"pattern": list(pattern), "frequency": count, "length": seq_length}
                for pattern, count in common if count > 1
            ])
        
        # Analyze success vs failure patterns
        patterns["success_patterns"] = self._get_unique_patterns(success_sequences, failure_sequences)
        patterns["failure_patterns"] = self._get_unique_patterns(failure_sequences, success_sequences)
        
        return patterns
    
    def detect_inefficiencies(self, workflow_data: List[Dict]) -> Dict:
        """Detect inefficiencies in workflow patterns."""
        inefficiencies = {
            "issues": [],
            "severity_scores": {},
            "categories": {
                "redundant_commands": [],
                "missing_prerequisites": [],
                "resource_conflicts": [],
                "timing_issues": []
            }
        }
        
        for i, workflow in enumerate(workflow_data):
            sequence = workflow.get("command_sequence", [])
            timestamps = workflow.get("timestamps", [])
            outcome = workflow.get("outcome", "unknown")
            
            # Detect redundant commands
            redundant = self._find_redundant_commands(sequence)
            if redundant:
                inefficiencies["categories"]["redundant_commands"].extend([
                    {"workflow_index": i, "redundant_commands": redundant}
                ])
            
            # Detect missing prerequisites
            missing_prereq = self._find_missing_prerequisites(sequence)
            if missing_prereq:
                inefficiencies["categories"]["missing_prerequisites"].extend([
                    {"workflow_index": i, "missing_prerequisites": missing_prereq}
                ])
            
            # Detect timing issues
            if len(timestamps) == len(sequence):
                timing_issues = self._find_timing_issues(sequence, timestamps)
                if timing_issues:
                    inefficiencies["categories"]["timing_issues"].extend([
                        {"workflow_index": i, "timing_issues": timing_issues}
                    ])
        
        # Compile all issues with severity
        for category, issues in inefficiencies["categories"].items():
            if issues:
                inefficiencies["issues"].append({
                    "category": category,
                    "count": len(issues),
                    "severity": self._calculate_severity(category, issues)
                })
        
        return inefficiencies
    
    def generate_optimization_suggestions(self, workflow_data: List[Dict], domain: str, complexity_level: str) -> List[Dict]:
        """Generate workflow optimization suggestions."""
        suggestions = []
        
        # Domain-specific optimization patterns
        domain_patterns = self._get_domain_patterns()
        
        # Complexity-based suggestions
        if complexity_level == "complex":
            suggestions.append({
                "type": "workflow_structure",
                "suggestion": "Break down into smaller, manageable phases",
                "priority": "high",
                "reasoning": "Complex tasks benefit from decomposition"
            })
        
        # Pattern-based suggestions from known good patterns
        patterns = domain_patterns.get(domain, domain_patterns["general"])
        for pattern_info in patterns:
            suggestions.append({
                "type": "pattern_improvement",
                "suggestion": pattern_info["optimization"],
                "priority": "medium",
                "reasoning": f"Common optimization for {pattern_info['pattern']} pattern"
            })
        
        # Analyze actual workflows for specific suggestions
        for workflow in workflow_data:
            sequence = workflow.get("command_sequence", [])
            outcome = workflow.get("outcome", "unknown")
            
            if outcome == "failure":
                # Suggest missing validation steps
                if not any(cmd in sequence for cmd in ["test", "verify", "validate"]):
                    suggestions.append({
                        "type": "missing_validation",
                        "suggestion": "Add testing/validation phase to catch issues early",
                        "priority": "high",
                        "reasoning": "Failed workflow lacks validation steps"
                    })
                
                # Suggest breaking down complex workflows
                if len(sequence) > 5:
                    suggestions.append({
                        "type": "complexity_reduction",
                        "suggestion": "Consider breaking into smaller workflows",
                        "priority": "medium",
                        "reasoning": "Long sequences are harder to debug when they fail"
                    })
        
        return self._deduplicate_suggestions(suggestions)
    
    def calculate_confidence_scores(self, workflow_data: List[Dict], analysis_results: Dict) -> Dict:
        """Calculate confidence scores for analysis results."""
        confidence = {}
        
        # Base confidence on sample size
        sample_size = len(workflow_data)
        base_confidence = min(0.9, 0.3 + (sample_size * 0.1))
        
        # Pattern analysis confidence
        pattern_count = len(analysis_results.get("pattern_analysis", {}).get("common_patterns", []))
        confidence["pattern_analysis"] = base_confidence * (1.0 if pattern_count > 0 else 0.5)
        
        # Inefficiency detection confidence
        issue_count = len(analysis_results.get("inefficiency_report", {}).get("issues", []))
        confidence["inefficiency_detection"] = base_confidence * (1.0 if issue_count > 0 else 0.7)
        
        # Suggestions confidence
        suggestion_count = len(analysis_results.get("optimization_suggestions", []))
        confidence["optimization_suggestions"] = base_confidence * (1.0 if suggestion_count > 0 else 0.6)
        
        # Overall confidence (weighted average)
        confidence["overall"] = (
            confidence["pattern_analysis"] * 0.4 +
            confidence["inefficiency_detection"] * 0.3 +
            confidence["optimization_suggestions"] * 0.3
        )
        
        return confidence
    
    def generate_memory_insights(self, workflow_data: List[Dict], analysis_results: Dict, project_name: str, domain: str) -> List[str]:
        """Generate insights for memory storage and learning."""
        insights = []
        
        # Pattern insights
        common_patterns = analysis_results.get("pattern_analysis", {}).get("common_patterns", [])
        if common_patterns:
            insights.append(f"Identified {len(common_patterns)} recurring workflow patterns in {domain}")
        
        # Success pattern insights
        success_patterns = analysis_results.get("pattern_analysis", {}).get("success_patterns", [])
        if success_patterns:
            insights.append(f"Found {len(success_patterns)} patterns associated with successful outcomes")
        
        # Inefficiency insights
        issues = analysis_results.get("inefficiency_report", {}).get("issues", [])
        if issues:
            insights.append(f"Detected {len(issues)} categories of workflow inefficiencies")
        
        # Optimization insights
        suggestions = analysis_results.get("optimization_suggestions", [])
        high_priority = [s for s in suggestions if s.get("priority") == "high"]
        if high_priority:
            insights.append(f"Generated {len(high_priority)} high-priority optimization recommendations")
        
        return insights
    
    # Private helper methods
    
    def _load_known_patterns(self) -> Dict:
        """Load known successful workflow patterns."""
        return {
            "automation": [
                {"pattern": ["explore", "plan", "code", "test"], "success_rate": 0.85},
                {"pattern": ["analyze", "design", "implement", "verify"], "success_rate": 0.90}
            ],
            "development": [
                {"pattern": ["explore", "plan", "code", "review", "test", "commit"], "success_rate": 0.92},
                {"pattern": ["analyze", "design", "code", "test"], "success_rate": 0.87}
            ],
            "debugging": [
                {"pattern": ["investigate", "analyze", "fix", "test", "verify"], "success_rate": 0.80},
                {"pattern": ["explore", "isolate", "fix", "validate"], "success_rate": 0.75}
            ]
        }
    
    def _load_prerequisite_rules(self) -> Dict:
        """Load prerequisite rules for commands."""
        return {
            "commit": ["test", "review"],
            "deploy": ["test", "build"],
            "test": ["code", "build"],
            "review": ["code"],
            "build": ["code"],
            "verify": ["implement", "test"],
            "complete": ["verify", "test"]
        }
    
    def _get_domain_patterns(self) -> Dict:
        """Get optimization patterns by domain."""
        return {
            "automation": [
                {"pattern": ["plan", "code", "test"], "optimization": "Add dependency check before code"},
                {"pattern": ["analyze", "implement"], "optimization": "Add design phase between analyze and implement"}
            ],
            "development": [
                {"pattern": ["code", "commit"], "optimization": "Add review and test phases before commit"},
                {"pattern": ["explore", "implement"], "optimization": "Add planning phase after exploration"}
            ],
            "debugging": [
                {"pattern": ["fix", "deploy"], "optimization": "Add testing phase before deployment"},
                {"pattern": ["investigate", "fix"], "optimization": "Add analysis phase between investigate and fix"}
            ],
            "general": [
                {"pattern": ["start", "finish"], "optimization": "Add progress tracking and validation phases"}
            ]
        }
    
    def _get_unique_patterns(self, primary_sequences: List[List], secondary_sequences: List[List]) -> List[Dict]:
        """Find patterns unique to primary sequences compared to secondary."""
        primary_patterns = set()
        secondary_patterns = set()
        
        # Build pattern sets for sequences of length 2-3
        for sequence in primary_sequences:
            for length in [2, 3]:
                for i in range(len(sequence) - length + 1):
                    primary_patterns.add(tuple(sequence[i:i+length]))
        
        for sequence in secondary_sequences:
            for length in [2, 3]:
                for i in range(len(sequence) - length + 1):
                    secondary_patterns.add(tuple(sequence[i:i+length]))
        
        # Find unique patterns
        unique_patterns = primary_patterns - secondary_patterns
        return [{"pattern": list(pattern), "frequency": 1} for pattern in unique_patterns]
    
    def _find_redundant_commands(self, sequence: List[str]) -> List[Dict]:
        """Find redundant commands in a sequence."""
        redundant = []
        command_positions = {}
        
        for i, command in enumerate(sequence):
            if command in command_positions:
                # Check if it's truly redundant (not separated by meaningful work)
                last_pos = command_positions[command]
                distance = i - last_pos
                
                # Consider redundant if repeated within 3 commands without clear reason
                if distance <= 3:
                    redundant.append({
                        "command": command,
                        "positions": [last_pos, i],
                        "distance": distance
                    })
            
            command_positions[command] = i
        
        return redundant
    
    def _find_missing_prerequisites(self, sequence: List[str]) -> List[str]:
        """Find missing prerequisite commands."""
        missing = []
        
        for i, command in enumerate(sequence):
            if command in self.prerequisite_rules:
                required = self.prerequisite_rules[command]
                preceding_commands = sequence[:i]
                
                for req in required:
                    if req not in preceding_commands:
                        missing.append(f"{req} before {command}")
        
        return missing
    
    def _find_timing_issues(self, sequence: List[str], timestamps: List[str]) -> List[Dict]:
        """Find timing-related issues in command execution."""
        issues = []
        
        if len(timestamps) != len(sequence):
            issues.append({
                "type": "timestamp_mismatch",
                "description": "Number of timestamps doesn't match command sequence"
            })
            return issues
        
        # Check for unusually long gaps between commands
        try:
            parsed_times = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in timestamps]
            
            for i in range(1, len(parsed_times)):
                gap = (parsed_times[i] - parsed_times[i-1]).total_seconds()
                
                # Flag gaps longer than 1 hour as potential issues
                if gap > 3600:
                    issues.append({
                        "type": "long_gap",
                        "description": f"Long gap ({gap/3600:.1f}h) between {sequence[i-1]} and {sequence[i]}",
                        "gap_seconds": gap
                    })
        except (ValueError, TypeError):
            issues.append({
                "type": "timestamp_parsing_error",
                "description": "Could not parse timestamps for timing analysis"
            })
        
        return issues
    
    def _calculate_severity(self, category: str, issues: List[Dict]) -> str:
        """Calculate severity level for a category of issues."""
        severity_map = {
            "redundant_commands": "medium",
            "missing_prerequisites": "high",
            "resource_conflicts": "high",
            "timing_issues": "low"
        }
        
        base_severity = severity_map.get(category, "medium")
        issue_count = len(issues)
        
        # Escalate severity based on frequency
        if issue_count > 5:
            if base_severity == "low":
                return "medium"
            elif base_severity == "medium":
                return "high"
        
        return base_severity
    
    def _deduplicate_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """Remove duplicate suggestions."""
        seen = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            # Create a key based on type and suggestion text
            key = (suggestion.get("type"), suggestion.get("suggestion"))
            
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions