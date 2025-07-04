"""
Enhanced Team Collaboration Features
Phase 4 implementation for intelligent team coordination and knowledge sharing
Enables collaborative development through shared cache insights and coordination
"""

import json
import time
import numpy as np
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter, deque
import threading
import hashlib
import math

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache, LanguageType
from .performance_analytics import CachePerformanceDashboard
from .ml_powered_analytics import MLPatternRecognition


@dataclass
class DeveloperProfile:
    """Profile of a developer's work patterns and expertise"""
    developer_id: str
    developer_name: str
    email: str
    
    # Work patterns
    primary_languages: List[str]
    expertise_areas: List[str]
    work_schedule: Dict[str, Any]  # Peak hours, timezone
    code_patterns: List[str]
    
    # Activity metrics
    daily_commits: float
    files_modified_per_day: float
    lines_changed_per_day: float
    collaboration_frequency: float
    
    # Cache interaction patterns
    cache_usage_patterns: Dict[str, Any]
    preferred_tools: List[str]
    performance_impact_score: float
    
    # Team interaction
    frequent_collaborators: List[str]
    knowledge_sharing_score: float
    mentoring_activity: float
    
    # Profile metadata
    created_at: float
    last_updated: float
    activity_score: float


@dataclass
class CollaborationInsight:
    """Insight about team collaboration patterns"""
    insight_id: str
    insight_type: str  # 'knowledge_gap', 'coordination_opportunity', 'efficiency_improvement'
    severity: str  # 'low', 'medium', 'high', 'critical'
    
    # Involved parties
    affected_developers: List[str]
    related_files: List[str]
    code_areas: List[str]
    
    # Insight details
    description: str
    evidence: Dict[str, Any]
    potential_impact: Dict[str, float]
    
    # Recommendations
    suggested_actions: List[str]
    coordination_strategies: List[str]
    tools_recommendations: List[str]
    
    # Metadata
    discovered_at: float
    confidence_score: float
    urgency_score: float


@dataclass
class KnowledgeArtifact:
    """Shared knowledge artifact created by the team"""
    artifact_id: str
    artifact_type: str  # 'pattern', 'solution', 'best_practice', 'lesson_learned'
    title: str
    description: str
    
    # Content
    code_examples: List[str]
    documentation: str
    related_patterns: List[str]
    applicable_scenarios: List[str]
    
    # Context
    programming_languages: List[str]
    difficulty_level: str
    problem_category: str
    
    # Authorship and curation
    created_by: str
    contributors: List[str]
    review_status: str  # 'draft', 'reviewed', 'approved', 'outdated'
    
    # Usage and feedback
    usage_count: int
    effectiveness_rating: float
    feedback_comments: List[str]
    
    # Metadata
    created_at: float
    last_updated: float
    version: str


@dataclass
class TeamCoordinationEvent:
    """Event requiring team coordination"""
    event_id: str
    event_type: str  # 'cache_conflict', 'performance_impact', 'knowledge_request'
    priority: str  # 'low', 'medium', 'high', 'urgent'
    
    # Event details
    trigger_conditions: List[str]
    affected_resources: List[str]
    impact_assessment: Dict[str, Any]
    
    # Coordination needs
    required_participants: List[str]
    suggested_participants: List[str]
    coordination_deadline: float
    
    # Resolution
    proposed_solutions: List[str]
    decision_required: bool
    escalation_path: List[str]
    
    # Tracking
    created_at: float
    resolved_at: Optional[float]
    resolution_summary: Optional[str]


class DeveloperProfiler:
    """Builds and maintains developer profiles"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard):
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        self.profiles_cache_type = "developer_profiles"
        self._lock = threading.Lock()
        
        # Profile data
        self.developer_profiles = {}
        self.activity_history = defaultdict(lambda: deque(maxlen=1000))
        
        # ML components
        self.ml_available = SKLEARN_AVAILABLE
        if self.ml_available:
            self.pattern_vectorizer = TfidfVectorizer(max_features=100)
            self.expertise_clusterer = KMeans(n_clusters=5, random_state=42)
    
    def create_developer_profile(self, developer_id: str, developer_name: str, 
                                email: str, initial_data: Dict[str, Any] = None) -> DeveloperProfile:
        """Create a new developer profile"""
        current_time = time.time()
        
        # Initialize with defaults or provided data
        initial_data = initial_data or {}
        
        profile = DeveloperProfile(
            developer_id=developer_id,
            developer_name=developer_name,
            email=email,
            
            # Work patterns (will be learned over time)
            primary_languages=initial_data.get("languages", []),
            expertise_areas=initial_data.get("expertise", []),
            work_schedule=initial_data.get("schedule", {"timezone": "UTC", "peak_hours": [9, 17]}),
            code_patterns=[],
            
            # Activity metrics (initialized to defaults)
            daily_commits=0.0,
            files_modified_per_day=0.0,
            lines_changed_per_day=0.0,
            collaboration_frequency=0.0,
            
            # Cache interaction patterns
            cache_usage_patterns={},
            preferred_tools=[],
            performance_impact_score=0.5,
            
            # Team interaction
            frequent_collaborators=[],
            knowledge_sharing_score=0.5,
            mentoring_activity=0.0,
            
            # Metadata
            created_at=current_time,
            last_updated=current_time,
            activity_score=0.0
        )
        
        # Store profile
        self.developer_profiles[developer_id] = profile
        self._store_profile(profile)
        
        return profile
    
    def update_developer_activity(self, developer_id: str, activity_data: Dict[str, Any]):
        """Update developer activity and learn patterns"""
        profile = self.developer_profiles.get(developer_id)
        if not profile:
            # Create profile if it doesn't exist
            profile = self.create_developer_profile(
                developer_id, 
                activity_data.get("name", f"Developer_{developer_id}"),
                activity_data.get("email", f"{developer_id}@example.com")
            )
        
        # Update activity metrics
        self._update_activity_metrics(profile, activity_data)
        
        # Learn patterns from activity
        self._learn_work_patterns(profile, activity_data)
        
        # Update cache interaction patterns
        self._update_cache_patterns(profile, activity_data)
        
        # Update collaboration patterns
        self._update_collaboration_patterns(profile, activity_data)
        
        # Recalculate derived metrics
        profile.activity_score = self._calculate_activity_score(profile)
        profile.last_updated = time.time()
        
        # Store updated profile
        self._store_profile(profile)
    
    def analyze_team_expertise(self, developer_ids: List[str]) -> Dict[str, Any]:
        """Analyze expertise distribution across the team"""
        profiles = [self.developer_profiles.get(dev_id) for dev_id in developer_ids 
                   if dev_id in self.developer_profiles]
        
        if not profiles:
            return {"error": "No profiles found"}
        
        # Analyze language expertise
        language_expertise = defaultdict(list)
        for profile in profiles:
            for lang in profile.primary_languages:
                language_expertise[lang].append(profile.developer_id)
        
        # Analyze expertise areas
        expertise_coverage = defaultdict(list)
        for profile in profiles:
            for area in profile.expertise_areas:
                expertise_coverage[area].append(profile.developer_id)
        
        # Identify gaps and overlaps
        expertise_gaps = self._identify_expertise_gaps(profiles)
        knowledge_overlap = self._calculate_knowledge_overlap(profiles)
        
        # Calculate team collaboration strength
        collaboration_strength = self._calculate_team_collaboration_strength(profiles)
        
        return {
            "team_size": len(profiles),
            "language_expertise": dict(language_expertise),
            "expertise_coverage": dict(expertise_coverage),
            "expertise_gaps": expertise_gaps,
            "knowledge_overlap": knowledge_overlap,
            "collaboration_strength": collaboration_strength,
            "team_velocity": statistics.mean([p.activity_score for p in profiles]),
            "knowledge_sharing_score": statistics.mean([p.knowledge_sharing_score for p in profiles])
        }
    
    def recommend_collaborations(self, task_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend optimal collaborations for a task"""
        required_skills = task_context.get("required_skills", [])
        files_involved = task_context.get("files", [])
        complexity_level = task_context.get("complexity", "medium")
        
        recommendations = []
        
        # Find developers with relevant expertise
        relevant_developers = []
        for dev_id, profile in self.developer_profiles.items():
            relevance_score = self._calculate_task_relevance(profile, task_context)
            if relevance_score > 0.3:  # Minimum relevance threshold
                relevant_developers.append({
                    "developer_id": dev_id,
                    "profile": profile,
                    "relevance_score": relevance_score
                })
        
        # Sort by relevance
        relevant_developers.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Generate collaboration recommendations
        if complexity_level in ["high", "complex"]:
            # Recommend team of 2-3 for complex tasks
            recommendations.extend(self._recommend_team_collaboration(relevant_developers[:3], task_context))
        else:
            # Recommend individual or pair for simpler tasks
            recommendations.extend(self._recommend_pair_collaboration(relevant_developers[:2], task_context))
        
        # Add mentoring opportunities
        mentoring_recommendations = self._identify_mentoring_opportunities(relevant_developers, task_context)
        recommendations.extend(mentoring_recommendations)
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _update_activity_metrics(self, profile: DeveloperProfile, activity_data: Dict[str, Any]):
        """Update basic activity metrics"""
        # Update with exponential moving average
        alpha = 0.3  # Smoothing factor
        
        current_commits = activity_data.get("commits_today", 0)
        profile.daily_commits = alpha * current_commits + (1 - alpha) * profile.daily_commits
        
        current_files = activity_data.get("files_modified_today", 0)
        profile.files_modified_per_day = alpha * current_files + (1 - alpha) * profile.files_modified_per_day
        
        current_lines = activity_data.get("lines_changed_today", 0)
        profile.lines_changed_per_day = alpha * current_lines + (1 - alpha) * profile.lines_changed_per_day
    
    def _learn_work_patterns(self, profile: DeveloperProfile, activity_data: Dict[str, Any]):
        """Learn work patterns from activity"""
        # Update primary languages
        languages_used = activity_data.get("languages_used", [])
        for lang in languages_used:
            if lang not in profile.primary_languages:
                profile.primary_languages.append(lang)
        
        # Limit to top 5 languages
        if len(profile.primary_languages) > 5:
            profile.primary_languages = profile.primary_languages[:5]
        
        # Update work schedule patterns
        current_hour = int((time.time() % 86400) / 3600)
        if "peak_hours" not in profile.work_schedule:
            profile.work_schedule["peak_hours"] = []
        
        # Track active hours
        if activity_data.get("commits_today", 0) > 0:
            peak_hours = profile.work_schedule["peak_hours"]
            if current_hour not in peak_hours:
                peak_hours.append(current_hour)
                # Keep only most frequent hours (top 8)
                if len(peak_hours) > 8:
                    profile.work_schedule["peak_hours"] = peak_hours[-8:]
    
    def _update_cache_patterns(self, profile: DeveloperProfile, activity_data: Dict[str, Any]):
        """Update cache interaction patterns"""
        cache_operations = activity_data.get("cache_operations", [])
        
        if cache_operations:
            # Track cache operation types
            op_types = Counter(op.get("operation_type") for op in cache_operations)
            
            if "operation_types" not in profile.cache_usage_patterns:
                profile.cache_usage_patterns["operation_types"] = {}
            
            for op_type, count in op_types.items():
                if op_type in profile.cache_usage_patterns["operation_types"]:
                    profile.cache_usage_patterns["operation_types"][op_type] += count
                else:
                    profile.cache_usage_patterns["operation_types"][op_type] = count
            
            # Calculate performance impact
            avg_response_time = statistics.mean([op.get("duration_ms", 0) for op in cache_operations])
            hit_rate = len([op for op in cache_operations if op.get("operation_type") == "hit"]) / len(cache_operations)
            
            profile.performance_impact_score = (hit_rate + (1 - min(avg_response_time / 100, 1))) / 2
    
    def _update_collaboration_patterns(self, profile: DeveloperProfile, activity_data: Dict[str, Any]):
        """Update collaboration patterns"""
        collaborators = activity_data.get("collaborators_today", [])
        
        # Update frequent collaborators
        for collaborator in collaborators:
            if collaborator not in profile.frequent_collaborators:
                profile.frequent_collaborators.append(collaborator)
        
        # Keep top 10 collaborators
        if len(profile.frequent_collaborators) > 10:
            profile.frequent_collaborators = profile.frequent_collaborators[:10]
        
        # Update collaboration frequency
        profile.collaboration_frequency = len(collaborators) / max(len(profile.frequent_collaborators), 1)
        
        # Update knowledge sharing score based on help/review activities
        reviews_given = activity_data.get("reviews_given_today", 0)
        help_provided = activity_data.get("help_provided_today", 0)
        
        daily_sharing = (reviews_given + help_provided) / 10.0  # Normalize
        alpha = 0.2
        profile.knowledge_sharing_score = alpha * daily_sharing + (1 - alpha) * profile.knowledge_sharing_score
    
    def _calculate_activity_score(self, profile: DeveloperProfile) -> float:
        """Calculate overall activity score"""
        # Weighted combination of different activity metrics
        commit_score = min(profile.daily_commits / 5.0, 1.0)  # 5 commits = max score
        file_score = min(profile.files_modified_per_day / 10.0, 1.0)  # 10 files = max score
        collaboration_score = profile.collaboration_frequency
        performance_score = profile.performance_impact_score
        
        weights = [0.3, 0.2, 0.3, 0.2]  # commits, files, collaboration, performance
        scores = [commit_score, file_score, collaboration_score, performance_score]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _identify_expertise_gaps(self, profiles: List[DeveloperProfile]) -> List[str]:
        """Identify expertise gaps in the team"""
        all_languages = ["Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++"]
        all_areas = ["Frontend", "Backend", "DevOps", "Database", "ML/AI", "Security", "Testing"]
        
        covered_languages = set()
        covered_areas = set()
        
        for profile in profiles:
            covered_languages.update(profile.primary_languages)
            covered_areas.update(profile.expertise_areas)
        
        language_gaps = [lang for lang in all_languages if lang not in covered_languages]
        area_gaps = [area for area in all_areas if area not in covered_areas]
        
        return language_gaps + area_gaps
    
    def _calculate_knowledge_overlap(self, profiles: List[DeveloperProfile]) -> Dict[str, float]:
        """Calculate knowledge overlap between team members"""
        if len(profiles) < 2:
            return {"overlap_score": 0.0}
        
        # Calculate language overlap
        language_sets = [set(p.primary_languages) for p in profiles]
        language_overlaps = []
        
        for i in range(len(language_sets)):
            for j in range(i + 1, len(language_sets)):
                intersection = len(language_sets[i] & language_sets[j])
                union = len(language_sets[i] | language_sets[j])
                overlap = intersection / max(union, 1)
                language_overlaps.append(overlap)
        
        # Calculate expertise overlap
        expertise_sets = [set(p.expertise_areas) for p in profiles]
        expertise_overlaps = []
        
        for i in range(len(expertise_sets)):
            for j in range(i + 1, len(expertise_sets)):
                intersection = len(expertise_sets[i] & expertise_sets[j])
                union = len(expertise_sets[i] | expertise_sets[j])
                overlap = intersection / max(union, 1)
                expertise_overlaps.append(overlap)
        
        return {
            "language_overlap": statistics.mean(language_overlaps) if language_overlaps else 0.0,
            "expertise_overlap": statistics.mean(expertise_overlaps) if expertise_overlaps else 0.0,
            "overlap_score": statistics.mean((language_overlaps + expertise_overlaps)) if (language_overlaps + expertise_overlaps) else 0.0
        }
    
    def _calculate_team_collaboration_strength(self, profiles: List[DeveloperProfile]) -> float:
        """Calculate team collaboration strength"""
        if len(profiles) < 2:
            return 0.0
        
        # Count bidirectional collaborations
        collaboration_matrix = defaultdict(set)
        
        for profile in profiles:
            for collaborator in profile.frequent_collaborators:
                collaboration_matrix[profile.developer_id].add(collaborator)
        
        # Calculate connection density
        total_possible_connections = len(profiles) * (len(profiles) - 1)
        actual_connections = sum(len(connections) for connections in collaboration_matrix.values())
        
        connection_density = actual_connections / max(total_possible_connections, 1)
        
        # Factor in knowledge sharing scores
        avg_sharing_score = statistics.mean([p.knowledge_sharing_score for p in profiles])
        
        return (connection_density + avg_sharing_score) / 2.0
    
    def _calculate_task_relevance(self, profile: DeveloperProfile, task_context: Dict[str, Any]) -> float:
        """Calculate how relevant a developer is for a task"""
        relevance_score = 0.0
        
        # Language relevance
        required_languages = task_context.get("languages", [])
        language_match = len(set(profile.primary_languages) & set(required_languages))
        if required_languages:
            relevance_score += (language_match / len(required_languages)) * 0.4
        
        # Expertise relevance
        required_expertise = task_context.get("required_skills", [])
        expertise_match = len(set(profile.expertise_areas) & set(required_expertise))
        if required_expertise:
            relevance_score += (expertise_match / len(required_expertise)) * 0.3
        
        # File familiarity (simplified - would check actual file history)
        files_involved = task_context.get("files", [])
        if files_involved:
            # Assume some familiarity based on language patterns
            familiar_files = len([f for f in files_involved 
                                if any(lang.lower() in f.lower() for lang in profile.primary_languages)])
            relevance_score += (familiar_files / len(files_involved)) * 0.2
        
        # Activity level
        relevance_score += profile.activity_score * 0.1
        
        return min(relevance_score, 1.0)
    
    def _recommend_team_collaboration(self, developers: List[Dict], task_context: Dict) -> List[Dict[str, Any]]:
        """Recommend team collaboration for complex tasks"""
        if len(developers) < 2:
            return []
        
        recommendations = []
        
        # Primary recommendation: top 2-3 developers
        team_members = developers[:3]
        complementary_score = self._calculate_team_complementarity([d["profile"] for d in team_members])
        
        recommendations.append({
            "collaboration_type": "team",
            "participants": [d["developer_id"] for d in team_members],
            "roles": self._suggest_team_roles(team_members, task_context),
            "synergy_score": complementary_score,
            "reasoning": "Complementary skills and high task relevance",
            "coordination_strategy": "Daily standups and shared workspace"
        })
        
        return recommendations
    
    def _recommend_pair_collaboration(self, developers: List[Dict], task_context: Dict) -> List[Dict[str, Any]]:
        """Recommend pair collaboration for simpler tasks"""
        if len(developers) < 2:
            return []
        
        recommendations = []
        
        # Pair programming recommendation
        pair = developers[:2]
        synergy_score = self._calculate_pair_synergy(pair[0]["profile"], pair[1]["profile"])
        
        recommendations.append({
            "collaboration_type": "pair",
            "participants": [d["developer_id"] for d in pair],
            "roles": ["driver", "navigator"],
            "synergy_score": synergy_score,
            "reasoning": "Complementary skills for efficient pair programming",
            "coordination_strategy": "Shared coding session with role switching"
        })
        
        return recommendations
    
    def _identify_mentoring_opportunities(self, developers: List[Dict], task_context: Dict) -> List[Dict[str, Any]]:
        """Identify mentoring opportunities"""
        recommendations = []
        
        if len(developers) < 2:
            return recommendations
        
        # Find potential mentor-mentee pairs
        for i, senior_dev in enumerate(developers):
            if senior_dev["profile"].knowledge_sharing_score > 0.7:  # High sharing score
                for junior_dev in developers[i+1:]:
                    if (junior_dev["profile"].activity_score < senior_dev["profile"].activity_score and
                        junior_dev["relevance_score"] > 0.2):  # Some relevance but less experienced
                        
                        recommendations.append({
                            "collaboration_type": "mentoring",
                            "participants": [senior_dev["developer_id"], junior_dev["developer_id"]],
                            "roles": ["mentor", "mentee"],
                            "synergy_score": 0.8,  # High value for mentoring
                            "reasoning": "Knowledge transfer and skill development opportunity",
                            "coordination_strategy": "Structured mentoring with regular check-ins"
                        })
        
        return recommendations[:2]  # Limit mentoring recommendations
    
    def _calculate_team_complementarity(self, profiles: List[DeveloperProfile]) -> float:
        """Calculate how well team members complement each other"""
        if len(profiles) < 2:
            return 0.0
        
        # Check language diversity
        all_languages = set()
        for profile in profiles:
            all_languages.update(profile.primary_languages)
        language_diversity = len(all_languages) / max(len(profiles) * 2, 1)  # Expect ~2 languages per person
        
        # Check expertise diversity
        all_expertise = set()
        for profile in profiles:
            all_expertise.update(profile.expertise_areas)
        expertise_diversity = len(all_expertise) / max(len(profiles) * 2, 1)
        
        # Check activity balance
        activity_scores = [p.activity_score for p in profiles]
        activity_balance = 1.0 - (statistics.stdev(activity_scores) if len(activity_scores) > 1 else 0)
        
        return (language_diversity + expertise_diversity + activity_balance) / 3.0
    
    def _calculate_pair_synergy(self, profile1: DeveloperProfile, profile2: DeveloperProfile) -> float:
        """Calculate synergy between two developers"""
        # Complementary skills
        skill_complement = len(set(profile1.primary_languages) | set(profile2.primary_languages)) / 5.0
        expertise_complement = len(set(profile1.expertise_areas) | set(profile2.expertise_areas)) / 5.0
        
        # Similar activity levels
        activity_similarity = 1.0 - abs(profile1.activity_score - profile2.activity_score)
        
        # Collaboration history
        collaboration_bonus = 0.2 if profile2.developer_id in profile1.frequent_collaborators else 0.0
        
        return min((skill_complement + expertise_complement + activity_similarity) / 3.0 + collaboration_bonus, 1.0)
    
    def _suggest_team_roles(self, team_members: List[Dict], task_context: Dict) -> List[str]:
        """Suggest roles for team members"""
        roles = []
        complexity = task_context.get("complexity", "medium")
        
        if len(team_members) >= 3 and complexity in ["high", "complex"]:
            roles = ["tech_lead", "implementer", "reviewer"]
        elif len(team_members) == 2:
            roles = ["lead_dev", "supporting_dev"]
        else:
            roles = ["developer"] * len(team_members)
        
        return roles[:len(team_members)]
    
    def _store_profile(self, profile: DeveloperProfile):
        """Store developer profile"""
        self.cache_manager.set_cache(
            self.profiles_cache_type,
            profile.developer_id,
            asdict(profile),
            cache_level="global"
        )


class CollaborationInsightEngine:
    """Generates insights about team collaboration patterns"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 developer_profiler: DeveloperProfiler,
                 performance_dashboard: CachePerformanceDashboard):
        self.cache_manager = cache_manager
        self.developer_profiler = developer_profiler
        self.performance_dashboard = performance_dashboard
        self.insights_cache_type = "collaboration_insights"
        self._lock = threading.Lock()
        
        # Insight history
        self.insight_history = deque(maxlen=100)
    
    def analyze_collaboration_patterns(self, team_members: List[str]) -> List[CollaborationInsight]:
        """Analyze collaboration patterns and generate insights"""
        insights = []
        
        # Get team profiles
        profiles = [self.developer_profiler.developer_profiles.get(dev_id) 
                   for dev_id in team_members if dev_id in self.developer_profiler.developer_profiles]
        
        if len(profiles) < 2:
            return insights
        
        # Analyze different collaboration aspects
        knowledge_gap_insights = self._analyze_knowledge_gaps(profiles)
        insights.extend(knowledge_gap_insights)
        
        coordination_insights = self._analyze_coordination_opportunities(profiles)
        insights.extend(coordination_insights)
        
        efficiency_insights = self._analyze_efficiency_improvements(profiles)
        insights.extend(efficiency_insights)
        
        communication_insights = self._analyze_communication_patterns(profiles)
        insights.extend(communication_insights)
        
        # Store insights
        for insight in insights:
            self.insight_history.append(insight)
            self._store_insight(insight)
        
        return insights
    
    def detect_coordination_conflicts(self, current_activities: List[Dict[str, Any]]) -> List[TeamCoordinationEvent]:
        """Detect situations requiring team coordination"""
        events = []
        
        # Analyze current activities for conflicts
        file_conflicts = self._detect_file_conflicts(current_activities)
        events.extend(file_conflicts)
        
        cache_conflicts = self._detect_cache_conflicts(current_activities)
        events.extend(cache_conflicts)
        
        performance_impacts = self._detect_performance_impacts(current_activities)
        events.extend(performance_impacts)
        
        knowledge_requests = self._detect_knowledge_requests(current_activities)
        events.extend(knowledge_requests)
        
        return events
    
    def generate_team_dashboard(self, team_members: List[str]) -> Dict[str, Any]:
        """Generate comprehensive team collaboration dashboard"""
        profiles = [self.developer_profiler.developer_profiles.get(dev_id) 
                   for dev_id in team_members if dev_id in self.developer_profiler.developer_profiles]
        
        if not profiles:
            return {"error": "No profiles available"}
        
        # Team metrics
        team_analysis = self.developer_profiler.analyze_team_expertise(team_members)
        
        # Recent insights
        recent_insights = [insight for insight in self.insight_history 
                         if insight.discovered_at > time.time() - 7 * 24 * 3600]  # Last 7 days
        
        # Collaboration network
        collaboration_network = self._build_collaboration_network(profiles)
        
        # Performance metrics
        team_performance = self._calculate_team_performance_metrics(profiles)
        
        # Recommendations
        recommendations = self._generate_team_recommendations(profiles, recent_insights)
        
        return {
            "dashboard_timestamp": datetime.now().isoformat(),
            "team_composition": team_analysis,
            "collaboration_network": collaboration_network,
            "performance_metrics": team_performance,
            "recent_insights": [asdict(insight) for insight in recent_insights[-10:]],  # Last 10
            "recommendations": recommendations,
            "coordination_status": self._assess_coordination_status(profiles),
            "knowledge_health": self._assess_knowledge_health(team_analysis)
        }
    
    def _analyze_knowledge_gaps(self, profiles: List[DeveloperProfile]) -> List[CollaborationInsight]:
        """Analyze knowledge gaps in the team"""
        insights = []
        
        # Identify critical knowledge gaps
        all_languages = set()
        all_expertise = set()
        
        for profile in profiles:
            all_languages.update(profile.primary_languages)
            all_expertise.update(profile.expertise_areas)
        
        # Check for single points of failure
        for lang in all_languages:
            experts = [p for p in profiles if lang in p.primary_languages]
            if len(experts) == 1:
                insight = CollaborationInsight(
                    insight_id=f"knowledge_gap_{lang}_{int(time.time())}",
                    insight_type="knowledge_gap",
                    severity="high",
                    
                    affected_developers=[experts[0].developer_id],
                    related_files=[],
                    code_areas=[lang],
                    
                    description=f"Single point of failure for {lang} expertise",
                    evidence={"expert_count": 1, "language": lang},
                    potential_impact={"risk_score": 0.8, "knowledge_loss_risk": 0.9},
                    
                    suggested_actions=[
                        f"Cross-train other team members in {lang}",
                        "Document critical {lang} patterns and practices",
                        "Pair programming for {lang} tasks"
                    ],
                    coordination_strategies=[
                        "Knowledge sharing sessions",
                        "Code review requirements for {lang} changes"
                    ],
                    tools_recommendations=[
                        "Code documentation tools",
                        "Learning resources for {lang}"
                    ],
                    
                    discovered_at=time.time(),
                    confidence_score=0.9,
                    urgency_score=0.7
                )
                insights.append(insight)
        
        return insights
    
    def _analyze_coordination_opportunities(self, profiles: List[DeveloperProfile]) -> List[CollaborationInsight]:
        """Analyze coordination opportunities"""
        insights = []
        
        # Find underutilized collaboration potential
        for i, profile1 in enumerate(profiles):
            for profile2 in profiles[i+1:]:
                # Check if they should collaborate more
                shared_skills = set(profile1.primary_languages) & set(profile2.primary_languages)
                shared_expertise = set(profile1.expertise_areas) & set(profile2.expertise_areas)
                
                if shared_skills and profile2.developer_id not in profile1.frequent_collaborators:
                    synergy_score = self.developer_profiler._calculate_pair_synergy(profile1, profile2)
                    
                    if synergy_score > 0.7:
                        insight = CollaborationInsight(
                            insight_id=f"coord_opportunity_{profile1.developer_id}_{profile2.developer_id}_{int(time.time())}",
                            insight_type="coordination_opportunity",
                            severity="medium",
                            
                            affected_developers=[profile1.developer_id, profile2.developer_id],
                            related_files=[],
                            code_areas=list(shared_skills | shared_expertise),
                            
                            description=f"High collaboration potential between {profile1.developer_name} and {profile2.developer_name}",
                            evidence={"synergy_score": synergy_score, "shared_skills": list(shared_skills)},
                            potential_impact={"productivity_boost": 0.3, "knowledge_sharing": 0.5},
                            
                            suggested_actions=[
                                "Assign joint tasks to foster collaboration",
                                "Encourage pair programming sessions",
                                "Cross-team project assignments"
                            ],
                            coordination_strategies=[
                                "Regular sync meetings",
                                "Shared responsibility for code areas"
                            ],
                            tools_recommendations=[
                                "Collaborative development tools",
                                "Shared documentation platforms"
                            ],
                            
                            discovered_at=time.time(),
                            confidence_score=0.8,
                            urgency_score=0.4
                        )
                        insights.append(insight)
        
        return insights
    
    def _analyze_efficiency_improvements(self, profiles: List[DeveloperProfile]) -> List[CollaborationInsight]:
        """Analyze efficiency improvement opportunities"""
        insights = []
        
        # Identify performance bottlenecks
        low_performers = [p for p in profiles if p.performance_impact_score < 0.5]
        
        for profile in low_performers:
            # Find potential mentors
            mentors = [p for p in profiles 
                      if p.performance_impact_score > 0.7 and p.knowledge_sharing_score > 0.6]
            
            if mentors:
                best_mentor = max(mentors, key=lambda p: p.knowledge_sharing_score)
                
                insight = CollaborationInsight(
                    insight_id=f"efficiency_improvement_{profile.developer_id}_{int(time.time())}",
                    insight_type="efficiency_improvement",
                    severity="medium",
                    
                    affected_developers=[profile.developer_id, best_mentor.developer_id],
                    related_files=[],
                    code_areas=profile.primary_languages,
                    
                    description=f"Performance improvement opportunity for {profile.developer_name}",
                    evidence={"current_performance": profile.performance_impact_score, "mentor_available": True},
                    potential_impact={"performance_boost": 0.4, "skill_development": 0.6},
                    
                    suggested_actions=[
                        "Establish mentoring relationship",
                        "Performance optimization training",
                        "Best practices knowledge sharing"
                    ],
                    coordination_strategies=[
                        "Regular mentoring sessions",
                        "Performance goal setting"
                    ],
                    tools_recommendations=[
                        "Performance monitoring tools",
                        "Training resources"
                    ],
                    
                    discovered_at=time.time(),
                    confidence_score=0.7,
                    urgency_score=0.5
                )
                insights.append(insight)
        
        return insights
    
    def _analyze_communication_patterns(self, profiles: List[DeveloperProfile]) -> List[CollaborationInsight]:
        """Analyze communication patterns"""
        insights = []
        
        # Identify communication gaps
        isolated_developers = [p for p in profiles if p.collaboration_frequency < 0.3]
        
        for profile in isolated_developers:
            insight = CollaborationInsight(
                insight_id=f"communication_gap_{profile.developer_id}_{int(time.time())}",
                insight_type="coordination_opportunity",
                severity="medium",
                
                affected_developers=[profile.developer_id],
                related_files=[],
                code_areas=profile.primary_languages,
                
                description=f"Low collaboration frequency for {profile.developer_name}",
                evidence={"collaboration_frequency": profile.collaboration_frequency},
                potential_impact={"integration_risk": 0.6, "knowledge_isolation": 0.5},
                
                suggested_actions=[
                    "Increase participation in team activities",
                    "Assign collaborative tasks",
                    "Regular check-ins with team members"
                ],
                coordination_strategies=[
                    "Buddy system implementation",
                    "Team building activities"
                ],
                tools_recommendations=[
                    "Communication platforms",
                    "Collaboration tools"
                ],
                
                discovered_at=time.time(),
                confidence_score=0.8,
                urgency_score=0.4
            )
            insights.append(insight)
        
        return insights
    
    def _detect_file_conflicts(self, activities: List[Dict[str, Any]]) -> List[TeamCoordinationEvent]:
        """Detect file editing conflicts"""
        events = []
        
        # Group activities by file
        file_activities = defaultdict(list)
        for activity in activities:
            files = activity.get("files_being_edited", [])
            for file_path in files:
                file_activities[file_path].append(activity)
        
        # Check for conflicts
        for file_path, file_activities_list in file_activities.items():
            if len(file_activities_list) > 1:
                developers = [activity["developer_id"] for activity in file_activities_list]
                
                event = TeamCoordinationEvent(
                    event_id=f"file_conflict_{hash(file_path)}_{int(time.time())}",
                    event_type="cache_conflict",
                    priority="high",
                    
                    trigger_conditions=[f"Multiple developers editing {file_path}"],
                    affected_resources=[file_path],
                    impact_assessment={"merge_conflict_risk": 0.8, "coordination_needed": True},
                    
                    required_participants=developers,
                    suggested_participants=[],
                    coordination_deadline=time.time() + 3600,  # 1 hour
                    
                    proposed_solutions=[
                        "Coordinate editing sessions",
                        "Establish file ownership temporarily",
                        "Use feature branches for isolation"
                    ],
                    decision_required=True,
                    escalation_path=["team_lead", "tech_lead"],
                    
                    created_at=time.time(),
                    resolved_at=None,
                    resolution_summary=None
                )
                events.append(event)
        
        return events
    
    def _detect_cache_conflicts(self, activities: List[Dict[str, Any]]) -> List[TeamCoordinationEvent]:
        """Detect cache-related conflicts"""
        events = []
        
        # Check for cache invalidation conflicts
        cache_operations = []
        for activity in activities:
            cache_ops = activity.get("cache_operations", [])
            for op in cache_ops:
                op["developer_id"] = activity["developer_id"]
                cache_operations.append(op)
        
        # Group by cache type and key
        cache_groups = defaultdict(list)
        for op in cache_operations:
            key = f"{op.get('cache_type')}:{op.get('cache_key', 'unknown')}"
            cache_groups[key].append(op)
        
        # Detect conflicts
        for cache_key, operations in cache_groups.items():
            invalidations = [op for op in operations if op.get("operation_type") == "invalidate"]
            if len(invalidations) > 1:
                developers = list(set(op["developer_id"] for op in invalidations))
                
                event = TeamCoordinationEvent(
                    event_id=f"cache_conflict_{hash(cache_key)}_{int(time.time())}",
                    event_type="cache_conflict",
                    priority="medium",
                    
                    trigger_conditions=[f"Multiple cache invalidations for {cache_key}"],
                    affected_resources=[cache_key],
                    impact_assessment={"performance_impact": 0.6, "coordination_needed": True},
                    
                    required_participants=developers,
                    suggested_participants=[],
                    coordination_deadline=time.time() + 1800,  # 30 minutes
                    
                    proposed_solutions=[
                        "Coordinate cache invalidation strategy",
                        "Implement cache invalidation locks",
                        "Use cache versioning"
                    ],
                    decision_required=False,
                    escalation_path=["tech_lead"],
                    
                    created_at=time.time(),
                    resolved_at=None,
                    resolution_summary=None
                )
                events.append(event)
        
        return events
    
    def _detect_performance_impacts(self, activities: List[Dict[str, Any]]) -> List[TeamCoordinationEvent]:
        """Detect performance impact situations"""
        events = []
        
        # Check for high-impact operations
        for activity in activities:
            performance_impact = activity.get("performance_impact_score", 0)
            if performance_impact > 0.8:  # High impact threshold
                
                event = TeamCoordinationEvent(
                    event_id=f"performance_impact_{activity['developer_id']}_{int(time.time())}",
                    event_type="performance_impact",
                    priority="high",
                    
                    trigger_conditions=[f"High performance impact activity by {activity['developer_id']}"],
                    affected_resources=activity.get("affected_resources", []),
                    impact_assessment={"performance_degradation": performance_impact},
                    
                    required_participants=[activity["developer_id"]],
                    suggested_participants=["tech_lead", "performance_team"],
                    coordination_deadline=time.time() + 1800,  # 30 minutes
                    
                    proposed_solutions=[
                        "Review performance optimization opportunities",
                        "Implement performance monitoring",
                        "Coordinate with performance team"
                    ],
                    decision_required=True,
                    escalation_path=["tech_lead", "architecture_team"],
                    
                    created_at=time.time(),
                    resolved_at=None,
                    resolution_summary=None
                )
                events.append(event)
        
        return events
    
    def _detect_knowledge_requests(self, activities: List[Dict[str, Any]]) -> List[TeamCoordinationEvent]:
        """Detect knowledge sharing requests"""
        events = []
        
        # Check for help requests or knowledge gaps
        for activity in activities:
            help_requests = activity.get("help_requests", [])
            for request in help_requests:
                
                event = TeamCoordinationEvent(
                    event_id=f"knowledge_request_{activity['developer_id']}_{int(time.time())}",
                    event_type="knowledge_request",
                    priority="medium",
                    
                    trigger_conditions=[f"Knowledge request: {request.get('topic', 'unknown')}"],
                    affected_resources=[],
                    impact_assessment={"knowledge_gap": True, "urgency": request.get("urgency", "medium")},
                    
                    required_participants=[activity["developer_id"]],
                    suggested_participants=self._find_knowledge_experts(request.get("topic", "")),
                    coordination_deadline=time.time() + 7200,  # 2 hours
                    
                    proposed_solutions=[
                        "Connect with subject matter expert",
                        "Schedule knowledge sharing session",
                        "Create documentation for future reference"
                    ],
                    decision_required=False,
                    escalation_path=["team_lead"],
                    
                    created_at=time.time(),
                    resolved_at=None,
                    resolution_summary=None
                )
                events.append(event)
        
        return events
    
    def _find_knowledge_experts(self, topic: str) -> List[str]:
        """Find experts for a knowledge topic"""
        experts = []
        
        for dev_id, profile in self.developer_profiler.developer_profiles.items():
            # Check if topic matches expertise areas or languages
            if (any(topic.lower() in area.lower() for area in profile.expertise_areas) or
                any(topic.lower() in lang.lower() for lang in profile.primary_languages)):
                
                if profile.knowledge_sharing_score > 0.6:  # Good sharing score
                    experts.append(dev_id)
        
        return experts[:3]  # Top 3 experts
    
    def _build_collaboration_network(self, profiles: List[DeveloperProfile]) -> Dict[str, Any]:
        """Build collaboration network representation"""
        network = {
            "nodes": [],
            "edges": [],
            "metrics": {}
        }
        
        # Add nodes (developers)
        for profile in profiles:
            network["nodes"].append({
                "id": profile.developer_id,
                "name": profile.developer_name,
                "activity_score": profile.activity_score,
                "knowledge_sharing_score": profile.knowledge_sharing_score,
                "primary_languages": profile.primary_languages,
                "expertise_areas": profile.expertise_areas
            })
        
        # Add edges (collaborations)
        for profile in profiles:
            for collaborator in profile.frequent_collaborators:
                if any(p.developer_id == collaborator for p in profiles):
                    # Calculate collaboration strength
                    collab_profile = next((p for p in profiles if p.developer_id == collaborator), None)
                    if collab_profile:
                        strength = self.developer_profiler._calculate_pair_synergy(profile, collab_profile)
                        
                        network["edges"].append({
                            "source": profile.developer_id,
                            "target": collaborator,
                            "strength": strength,
                            "collaboration_frequency": profile.collaboration_frequency
                        })
        
        # Calculate network metrics
        network["metrics"] = {
            "total_nodes": len(network["nodes"]),
            "total_edges": len(network["edges"]),
            "density": len(network["edges"]) / max(len(network["nodes"]) * (len(network["nodes"]) - 1), 1),
            "avg_collaboration_strength": statistics.mean([e["strength"] for e in network["edges"]]) if network["edges"] else 0
        }
        
        return network
    
    def _calculate_team_performance_metrics(self, profiles: List[DeveloperProfile]) -> Dict[str, float]:
        """Calculate team performance metrics"""
        if not profiles:
            return {}
        
        return {
            "avg_activity_score": statistics.mean([p.activity_score for p in profiles]),
            "avg_performance_impact": statistics.mean([p.performance_impact_score for p in profiles]),
            "avg_knowledge_sharing": statistics.mean([p.knowledge_sharing_score for p in profiles]),
            "avg_collaboration_frequency": statistics.mean([p.collaboration_frequency for p in profiles]),
            "team_velocity": sum([p.daily_commits for p in profiles]),
            "total_files_per_day": sum([p.files_modified_per_day for p in profiles]),
            "performance_consistency": 1.0 - statistics.stdev([p.performance_impact_score for p in profiles]) if len(profiles) > 1 else 1.0
        }
    
    def _generate_team_recommendations(self, profiles: List[DeveloperProfile], 
                                     recent_insights: List[CollaborationInsight]) -> List[str]:
        """Generate team improvement recommendations"""
        recommendations = []
        
        # Analyze recent insights for patterns
        high_severity_insights = [i for i in recent_insights if i.severity in ["high", "critical"]]
        if high_severity_insights:
            recommendations.append(f"Address {len(high_severity_insights)} high-priority collaboration issues")
        
        # Check team performance
        avg_performance = statistics.mean([p.performance_impact_score for p in profiles])
        if avg_performance < 0.6:
            recommendations.append("Focus on performance optimization training")
        
        # Check knowledge sharing
        avg_sharing = statistics.mean([p.knowledge_sharing_score for p in profiles])
        if avg_sharing < 0.5:
            recommendations.append("Implement knowledge sharing initiatives")
        
        # Check collaboration frequency
        low_collaborators = [p for p in profiles if p.collaboration_frequency < 0.3]
        if low_collaborators:
            recommendations.append(f"Improve collaboration for {len(low_collaborators)} team members")
        
        # Check expertise coverage
        expertise_gaps = self.developer_profiler._identify_expertise_gaps(profiles)
        if expertise_gaps:
            recommendations.append(f"Address expertise gaps in {len(expertise_gaps)} areas")
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _assess_coordination_status(self, profiles: List[DeveloperProfile]) -> Dict[str, str]:
        """Assess overall coordination status"""
        # Calculate coordination health metrics
        avg_collaboration = statistics.mean([p.collaboration_frequency for p in profiles])
        avg_sharing = statistics.mean([p.knowledge_sharing_score for p in profiles])
        
        # Determine status levels
        coordination_health = "excellent" if avg_collaboration > 0.8 else \
                            "good" if avg_collaboration > 0.6 else \
                            "fair" if avg_collaboration > 0.4 else "poor"
        
        knowledge_health = "excellent" if avg_sharing > 0.8 else \
                         "good" if avg_sharing > 0.6 else \
                         "fair" if avg_sharing > 0.4 else "poor"
        
        # Overall status
        if coordination_health in ["excellent", "good"] and knowledge_health in ["excellent", "good"]:
            overall_status = "healthy"
        elif coordination_health == "poor" or knowledge_health == "poor":
            overall_status = "needs_attention"
        else:
            overall_status = "improving"
        
        return {
            "overall": overall_status,
            "coordination": coordination_health,
            "knowledge_sharing": knowledge_health
        }
    
    def _assess_knowledge_health(self, team_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess knowledge health of the team"""
        expertise_gaps = team_analysis.get("expertise_gaps", [])
        overlap_score = team_analysis.get("knowledge_overlap", {}).get("overlap_score", 0)
        
        gap_severity = "critical" if len(expertise_gaps) > 5 else \
                      "high" if len(expertise_gaps) > 3 else \
                      "medium" if len(expertise_gaps) > 1 else "low"
        
        overlap_status = "healthy" if 0.3 <= overlap_score <= 0.7 else \
                        "too_high" if overlap_score > 0.7 else "too_low"
        
        return {
            "expertise_gap_severity": gap_severity,
            "knowledge_overlap_status": overlap_status,
            "total_gaps": len(expertise_gaps),
            "overlap_score": overlap_score,
            "recommendation": "diversify_expertise" if overlap_score > 0.7 else \
                           "increase_collaboration" if overlap_score < 0.3 else \
                           "maintain_balance"
        }
    
    def _store_insight(self, insight: CollaborationInsight):
        """Store collaboration insight"""
        self.cache_manager.set_cache(
            self.insights_cache_type,
            insight.insight_id,
            asdict(insight),
            cache_level="global"
        )


class TeamCollaborationOrchestrator:
    """Main orchestrator for team collaboration features"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard,
                 ml_pattern_recognition: MLPatternRecognition = None):
        
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        self.ml_pattern_recognition = ml_pattern_recognition
        
        # Initialize components
        self.developer_profiler = DeveloperProfiler(
            cache_manager, symbol_cache, performance_dashboard
        )
        self.insight_engine = CollaborationInsightEngine(
            cache_manager, self.developer_profiler, performance_dashboard
        )
        
        # State management
        self.is_running = False
        self.collaboration_thread = None
        self._stop_event = threading.Event()
        
        # Update intervals
        self.profile_update_interval = 3600  # 1 hour
        self.insight_generation_interval = 6 * 3600  # 6 hours
        self.coordination_check_interval = 1800  # 30 minutes
    
    def start_team_collaboration(self):
        """Start team collaboration system"""
        if self.is_running:
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        # Start collaboration thread
        self.collaboration_thread = threading.Thread(target=self._collaboration_loop)
        self.collaboration_thread.daemon = True
        self.collaboration_thread.start()
    
    def stop_team_collaboration(self):
        """Stop team collaboration system"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        
        if self.collaboration_thread:
            self.collaboration_thread.join(timeout=30)
    
    def register_developer(self, developer_id: str, developer_info: Dict[str, Any]) -> DeveloperProfile:
        """Register a new developer"""
        return self.developer_profiler.create_developer_profile(
            developer_id,
            developer_info.get("name", f"Developer_{developer_id}"),
            developer_info.get("email", f"{developer_id}@example.com"),
            developer_info
        )
    
    def update_developer_activity(self, developer_id: str, activity_data: Dict[str, Any]):
        """Update developer activity"""
        self.developer_profiler.update_developer_activity(developer_id, activity_data)
    
    def analyze_team(self, team_members: List[str]) -> Dict[str, Any]:
        """Comprehensive team analysis"""
        # Generate team analysis
        team_analysis = self.developer_profiler.analyze_team_expertise(team_members)
        
        # Generate collaboration insights
        insights = self.insight_engine.analyze_collaboration_patterns(team_members)
        
        # Generate dashboard
        dashboard = self.insight_engine.generate_team_dashboard(team_members)
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "team_analysis": team_analysis,
            "collaboration_insights": [asdict(insight) for insight in insights],
            "team_dashboard": dashboard,
            "system_status": self.get_collaboration_status()
        }
    
    def recommend_task_assignment(self, task_description: Dict[str, Any], 
                                 available_developers: List[str]) -> Dict[str, Any]:
        """Recommend optimal task assignment"""
        # Get collaboration recommendations
        recommendations = self.developer_profiler.recommend_collaborations(task_description)
        
        # Filter recommendations to available developers
        filtered_recommendations = []
        for rec in recommendations:
            if all(dev_id in available_developers for dev_id in rec["participants"]):
                filtered_recommendations.append(rec)
        
        # If no perfect matches, find best individual assignment
        if not filtered_recommendations:
            individual_recommendations = []
            for dev_id in available_developers:
                profile = self.developer_profiler.developer_profiles.get(dev_id)
                if profile:
                    relevance = self.developer_profiler._calculate_task_relevance(profile, task_description)
                    individual_recommendations.append({
                        "collaboration_type": "individual",
                        "participants": [dev_id],
                        "relevance_score": relevance,
                        "reasoning": f"Best individual match for task requirements"
                    })
            
            individual_recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
            filtered_recommendations = individual_recommendations[:3]
        
        return {
            "task_description": task_description,
            "available_developers": available_developers,
            "recommendations": filtered_recommendations,
            "recommendation_timestamp": datetime.now().isoformat()
        }
    
    def get_collaboration_status(self) -> Dict[str, Any]:
        """Get collaboration system status"""
        return {
            "system_running": self.is_running,
            "registered_developers": len(self.developer_profiler.developer_profiles),
            "active_insights": len(self.insight_engine.insight_history),
            "update_intervals": {
                "profile_update_hours": self.profile_update_interval / 3600,
                "insight_generation_hours": self.insight_generation_interval / 3600,
                "coordination_check_minutes": self.coordination_check_interval / 60
            },
            "last_update": datetime.now().isoformat()
        }
    
    def _collaboration_loop(self):
        """Main collaboration monitoring loop"""
        last_profile_update = 0
        last_insight_generation = 0
        last_coordination_check = 0
        
        while self.is_running and not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Update profiles periodically
                if current_time - last_profile_update >= self.profile_update_interval:
                    self._update_all_profiles()
                    last_profile_update = current_time
                
                # Generate insights periodically
                if current_time - last_insight_generation >= self.insight_generation_interval:
                    self._generate_team_insights()
                    last_insight_generation = current_time
                
                # Check coordination needs periodically
                if current_time - last_coordination_check >= self.coordination_check_interval:
                    self._check_coordination_needs()
                    last_coordination_check = current_time
                
                # Wait before next iteration
                self._stop_event.wait(min(1800, self.coordination_check_interval))  # Max 30 minutes wait
                
            except Exception as e:
                print(f"Error in collaboration loop: {e}")
                self._stop_event.wait(1800)  # Wait 30 minutes before retry
    
    def _update_all_profiles(self):
        """Update all developer profiles"""
        try:
            # This would collect activity data from various sources
            # For now, simulate some activity updates
            for dev_id in self.developer_profiler.developer_profiles.keys():
                # Simulate activity data
                activity_data = {
                    "commits_today": 2,
                    "files_modified_today": 5,
                    "lines_changed_today": 150,
                    "languages_used": ["Python", "JavaScript"],
                    "collaborators_today": [],
                    "cache_operations": []
                }
                self.developer_profiler.update_developer_activity(dev_id, activity_data)
        except Exception as e:
            print(f"Error updating profiles: {e}")
    
    def _generate_team_insights(self):
        """Generate team insights"""
        try:
            team_members = list(self.developer_profiler.developer_profiles.keys())
            if team_members:
                insights = self.insight_engine.analyze_collaboration_patterns(team_members)
                # Insights are automatically stored by the engine
        except Exception as e:
            print(f"Error generating insights: {e}")
    
    def _check_coordination_needs(self):
        """Check for coordination needs"""
        try:
            # This would monitor current activities for coordination needs
            # For now, just placeholder
            current_activities = []  # Would be populated from real activity monitoring
            events = self.insight_engine.detect_coordination_conflicts(current_activities)
            # Events would be processed and notifications sent
        except Exception as e:
            print(f"Error checking coordination: {e}")