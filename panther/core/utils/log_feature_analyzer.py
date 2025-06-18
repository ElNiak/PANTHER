"""
Log Feature Analyzer

Advanced analytics module for analyzing feature-specific logging patterns,
performance characteristics, and optimization recommendations.
"""

import logging
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional, Set, Tuple

from .log_statistics_collector import LogStatisticsCollector


class LogFeatureAnalyzer:
    """
    Advanced analyzer for feature-specific logging patterns and performance.

    Provides deep analysis of logging behavior per feature, including
    activity patterns, level distribution analysis, and optimization
    recommendations.
    """

    def __init__(self, collector: LogStatisticsCollector):
        """
        Initialize the feature analyzer.

        Args:
            collector: The statistics collector to analyze
        """
        self.collector = collector

        # Analysis caches
        self._analysis_cache = {}
        self._last_analysis_time = None
        self._cache_ttl = 30  # Cache TTL in seconds

        # Configuration thresholds for analysis
        self.thresholds = {
            "high_volume_percentage": 20.0,  # % of total messages to be considered high volume
            "low_activity_threshold": 5,  # Minimum messages to be considered active
            "error_rate_concern": 5.0,  # % error rate to flag as concerning
            "burst_detection_factor": 3.0,  # Factor above average to detect bursts
            "efficiency_threshold": 0.8,  # Efficiency score threshold
            "verbosity_concern": 1000,  # Messages per minute to flag as too verbose
        }

    def analyze_feature_activity(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Analyze logging activity by feature.

        Args:
            force_refresh: Force refresh of cached analysis

        Returns:
            Comprehensive feature activity analysis
        """
        if not force_refresh and self._is_cache_valid("activity"):
            return self._analysis_cache["activity"]

        try:
            feature_stats = self.collector._analyze_features()
            total_messages = self.collector.stats["total_messages"]
            session_duration = self.collector.stats["session_duration"]

            analysis = {
                "timestamp": datetime.now(),
                "summary": {
                    "total_features_active": len(feature_stats),
                    "total_messages": total_messages,
                    "session_duration": session_duration,
                    "analysis_type": "feature_activity",
                },
                "feature_rankings": {},
                "activity_categories": {
                    "high_volume": [],
                    "moderate_volume": [],
                    "low_volume": [],
                    "inactive": [],
                },
                "patterns": {},
                "recommendations": [],
            }

            # Analyze each feature
            feature_analysis = {}
            for feature_name, data in feature_stats.items():
                feature_analysis[feature_name] = self._analyze_single_feature(
                    feature_name, data, total_messages, session_duration
                )

            # Create rankings
            analysis["feature_rankings"] = self._create_feature_rankings(
                feature_analysis
            )

            # Categorize features by activity
            analysis["activity_categories"] = self._categorize_features_by_activity(
                feature_analysis, total_messages
            )

            # Detect patterns
            analysis["patterns"] = self._detect_activity_patterns(feature_analysis)

            # Generate recommendations
            analysis["recommendations"] = self._generate_activity_recommendations(
                feature_analysis, total_messages
            )

            # Cache the result
            self._analysis_cache["activity"] = analysis
            self._last_analysis_time = datetime.now()

            return analysis

        except Exception as e:
            logging.getLogger(__name__).error("Error analyzing feature activity: %s", e)
            return {"error": f"Failed to analyze feature activity: {e}"}

    def _analyze_single_feature(
        self,
        feature_name: str,
        data: Dict[str, Any],
        total_messages: int,
        session_duration: float,
    ) -> Dict[str, Any]:
        """Analyze a single feature's logging characteristics."""
        total_msgs = data.get("total_messages", 0)
        message_rate = data.get("message_rate", 0)
        level_distribution = data.get("level_distribution", {})
        unique_modules = data.get("unique_modules", 0)
        active_duration = data.get("active_duration", 0)

        # Calculate metrics
        volume_percentage = (total_msgs / max(total_messages, 1)) * 100
        efficiency_score = self._calculate_efficiency_score(level_distribution)
        verbosity_score = self._calculate_verbosity_score(message_rate, total_msgs)
        error_rate = self._calculate_error_rate(level_distribution, total_msgs)

        # Activity pattern analysis
        activity_pattern = self._classify_activity_pattern(
            message_rate, active_duration, session_duration
        )

        return {
            "name": feature_name,
            "metrics": {
                "total_messages": total_msgs,
                "message_rate": message_rate,
                "volume_percentage": volume_percentage,
                "unique_modules": unique_modules,
                "active_duration": active_duration,
                "efficiency_score": efficiency_score,
                "verbosity_score": verbosity_score,
                "error_rate": error_rate,
            },
            "level_distribution": level_distribution,
            "activity_pattern": activity_pattern,
            "flags": self._identify_feature_flags(
                volume_percentage, error_rate, verbosity_score, efficiency_score
            ),
        }

    def _calculate_efficiency_score(self, level_distribution: Dict[str, int]) -> float:
        """Calculate efficiency score based on level distribution."""
        if not level_distribution:
            return 0.0

        total = sum(level_distribution.values())
        if total == 0:
            return 0.0

        # Weight levels by importance (INFO/WARN good, DEBUG/TRACE less efficient, ERROR bad)
        weights = {
            "CRITICAL": 0.1,  # Very inefficient
            "ERROR": 0.2,  # Inefficient
            "WARNING": 0.7,  # Moderately efficient
            "INFO": 1.0,  # Efficient
            "DEBUG": 0.5,  # Less efficient
            "TRACE": 0.3,  # Least efficient
        }

        weighted_score = sum(
            level_distribution.get(level, 0) * weight
            for level, weight in weights.items()
        )

        return weighted_score / total

    def _calculate_verbosity_score(
        self, message_rate: float, total_messages: int
    ) -> float:
        """Calculate verbosity score (higher = more verbose)."""
        if message_rate == 0:
            return 0.0

        # Convert to messages per minute for better interpretation
        messages_per_minute = message_rate * 60

        # Normalize to 0-1 scale where 1 is very verbose
        return min(messages_per_minute / self.thresholds["verbosity_concern"], 1.0)

    def _calculate_error_rate(
        self, level_distribution: Dict[str, int], total_messages: int
    ) -> float:
        """Calculate error rate percentage."""
        if total_messages == 0:
            return 0.0

        error_count = level_distribution.get("ERROR", 0) + level_distribution.get(
            "CRITICAL", 0
        )

        return (error_count / total_messages) * 100

    def _classify_activity_pattern(
        self, message_rate: float, active_duration: float, session_duration: float
    ) -> str:
        """Classify the activity pattern of a feature."""
        if active_duration == 0:
            return "inactive"

        activity_ratio = active_duration / max(session_duration, 1)

        if activity_ratio > 0.8:
            if message_rate > 1.0:  # More than 1 message per second
                return "continuous_high"
            else:
                return "continuous_low"
        elif activity_ratio > 0.3:
            return "intermittent"
        elif message_rate > 5.0:  # High rate but short duration
            return "burst"
        else:
            return "sporadic"

    def _identify_feature_flags(
        self,
        volume_percentage: float,
        error_rate: float,
        verbosity_score: float,
        efficiency_score: float,
    ) -> List[str]:
        """Identify flags/issues for a feature."""
        flags = []

        if volume_percentage > self.thresholds["high_volume_percentage"]:
            flags.append("high_volume")

        if error_rate > self.thresholds["error_rate_concern"]:
            flags.append("high_error_rate")

        if verbosity_score > 0.8:
            flags.append("very_verbose")

        if efficiency_score < self.thresholds["efficiency_threshold"]:
            flags.append("low_efficiency")

        if volume_percentage > 50:
            flags.append("dominant_feature")

        return flags

    def _create_feature_rankings(
        self, feature_analysis: Dict[str, Dict]
    ) -> Dict[str, List]:
        """Create rankings of features by different metrics."""
        rankings = {}

        # Sort by different metrics
        metrics_to_rank = [
            ("by_volume", "metrics.total_messages"),
            ("by_rate", "metrics.message_rate"),
            ("by_error_rate", "metrics.error_rate"),
            ("by_efficiency", "metrics.efficiency_score"),
            ("by_verbosity", "metrics.verbosity_score"),
        ]

        for rank_name, metric_path in metrics_to_rank:
            sorted_features = sorted(
                feature_analysis.items(),
                key=lambda x: self._get_nested_value(x[1], metric_path),
                reverse=True,
            )

            rankings[rank_name] = [
                {
                    "feature": name,
                    "value": self._get_nested_value(data, metric_path),
                    "flags": data.get("flags", []),
                }
                for name, data in sorted_features[:10]  # Top 10
            ]

        return rankings

    def _categorize_features_by_activity(
        self, feature_analysis: Dict[str, Dict], total_messages: int
    ) -> Dict[str, List]:
        """Categorize features by their activity level."""
        categories = {
            "high_volume": [],
            "moderate_volume": [],
            "low_volume": [],
            "inactive": [],
        }

        for feature_name, data in feature_analysis.items():
            volume_pct = data["metrics"]["volume_percentage"]
            total_msgs = data["metrics"]["total_messages"]

            if total_msgs == 0:
                categories["inactive"].append(feature_name)
            elif volume_pct > self.thresholds["high_volume_percentage"]:
                categories["high_volume"].append(feature_name)
            elif total_msgs > self.thresholds["low_activity_threshold"]:
                categories["moderate_volume"].append(feature_name)
            else:
                categories["low_volume"].append(feature_name)

        return categories

    def _detect_activity_patterns(
        self, feature_analysis: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Detect overall patterns in feature activity."""
        patterns = {
            "activity_distribution": defaultdict(int),
            "common_flags": Counter(),
            "efficiency_stats": {},
            "volume_concentration": {},
        }

        # Count activity patterns
        for data in feature_analysis.values():
            pattern = data["activity_pattern"]
            patterns["activity_distribution"][pattern] += 1

            # Count flags
            for flag in data.get("flags", []):
                patterns["common_flags"][flag] += 1

        # Efficiency statistics
        efficiency_scores = [
            data["metrics"]["efficiency_score"] for data in feature_analysis.values()
        ]

        if efficiency_scores:
            patterns["efficiency_stats"] = {
                "mean": mean(efficiency_scores),
                "median": median(efficiency_scores),
                "std": stdev(efficiency_scores) if len(efficiency_scores) > 1 else 0,
                "min": min(efficiency_scores),
                "max": max(efficiency_scores),
            }

        # Volume concentration (how concentrated is the logging across features)
        volume_percentages = [
            data["metrics"]["volume_percentage"] for data in feature_analysis.values()
        ]

        if volume_percentages:
            # Calculate Gini coefficient for volume concentration
            gini = self._calculate_gini_coefficient(volume_percentages)
            patterns["volume_concentration"] = {
                "gini_coefficient": gini,
                "interpretation": self._interpret_gini(gini),
                "top_3_percentage": sum(sorted(volume_percentages, reverse=True)[:3]),
            }

        return patterns

    def _calculate_gini_coefficient(self, values: List[float]) -> float:
        """Calculate Gini coefficient for measuring inequality."""
        if not values or len(values) == 1:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = 0

        for i, value in enumerate(sorted_values):
            cumsum += (2 * (i + 1) - n - 1) * value

        return cumsum / (n * sum(sorted_values))

    def _interpret_gini(self, gini: float) -> str:
        """Interpret Gini coefficient value."""
        if gini < 0.2:
            return "Very even distribution"
        elif gini < 0.4:
            return "Relatively even distribution"
        elif gini < 0.6:
            return "Moderate concentration"
        elif gini < 0.8:
            return "High concentration"
        else:
            return "Very high concentration"

    def _generate_activity_recommendations(
        self, feature_analysis: Dict[str, Dict], total_messages: int
    ) -> List[str]:
        """Generate recommendations based on feature activity analysis."""
        recommendations = []

        # Find problematic features
        high_volume_features = []
        high_error_features = []
        inefficient_features = []
        very_verbose_features = []

        for feature_name, data in feature_analysis.items():
            flags = data.get("flags", [])
            metrics = data["metrics"]

            if "high_volume" in flags or "dominant_feature" in flags:
                high_volume_features.append(
                    (feature_name, metrics["volume_percentage"])
                )

            if "high_error_rate" in flags:
                high_error_features.append((feature_name, metrics["error_rate"]))

            if "low_efficiency" in flags:
                inefficient_features.append((feature_name, metrics["efficiency_score"]))

            if "very_verbose" in flags:
                very_verbose_features.append((feature_name, metrics["verbosity_score"]))

        # Generate specific recommendations
        if high_volume_features:
            top_volume = max(high_volume_features, key=lambda x: x[1])
            recommendations.append(
                f"Consider reducing log level for '{top_volume[0]}' feature "
                f"(generating {top_volume[1]:.1f}% of all messages)"
            )

        if high_error_features:
            recommendations.append(
                f"Investigate high error rates in features: "
                f"{', '.join([name for name, _ in high_error_features[:3]])}"
            )

        if inefficient_features:
            recommendations.append(
                f"Review log level distribution for inefficient features: "
                f"{', '.join([name for name, _ in inefficient_features[:3]])}"
            )

        if very_verbose_features:
            recommendations.append(
                f"Consider reducing verbosity for features: "
                f"{', '.join([name for name, _ in very_verbose_features[:3]])}"
            )

        # Overall patterns
        total_active = len(
            [f for f in feature_analysis.values() if f["metrics"]["total_messages"] > 0]
        )
        if total_active > 15:
            recommendations.append(
                f"High number of active features ({total_active}) - "
                "consider consolidating similar logging concerns"
            )

        return recommendations

    def compare_with_configuration(
        self, config_levels: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Compare actual activity with configured levels.

        Args:
            config_levels: Dictionary mapping features to configured log levels

        Returns:
            Comparison analysis with recommendations
        """
        try:
            activity_analysis = self.analyze_feature_activity()
            feature_stats = activity_analysis.get("feature_rankings", {}).get(
                "by_volume", []
            )

            comparison = {
                "timestamp": datetime.now(),
                "mismatches": [],
                "recommendations": [],
                "efficiency_analysis": {},
                "configuration_effectiveness": {},
            }

            # Level hierarchy for comparison
            level_hierarchy = {
                "TRACE": 0,
                "DEBUG": 1,
                "INFO": 2,
                "WARNING": 3,
                "ERROR": 4,
                "CRITICAL": 5,
            }

            for feature_data in feature_stats:
                feature_name = feature_data["feature"]
                actual_volume = feature_data["value"]

                if feature_name in config_levels:
                    configured_level = config_levels[feature_name].upper()

                    # Analyze if configuration matches activity
                    if actual_volume > 1000:  # High activity
                        if (
                            level_hierarchy.get(configured_level, 2) < 2
                        ):  # DEBUG or TRACE
                            comparison["mismatches"].append(
                                {
                                    "feature": feature_name,
                                    "issue": "high_activity_low_level",
                                    "actual_volume": actual_volume,
                                    "configured_level": configured_level,
                                    "recommendation": f"Consider raising level from {configured_level} to INFO or WARNING",
                                }
                            )

                    elif actual_volume < 10:  # Low activity
                        if (
                            level_hierarchy.get(configured_level, 2) > 2
                        ):  # WARNING or higher
                            comparison["mismatches"].append(
                                {
                                    "feature": feature_name,
                                    "issue": "low_activity_high_level",
                                    "actual_volume": actual_volume,
                                    "configured_level": configured_level,
                                    "recommendation": f"Consider lowering level from {configured_level} to DEBUG for more details",
                                }
                            )

            return comparison

        except Exception as e:
            return {"error": f"Failed to compare with configuration: {e}"}

    def suggest_level_optimizations(self) -> Dict[str, str]:
        """
        Suggest optimal logging levels based on activity analysis.

        Returns:
            Dictionary mapping features to suggested log levels
        """
        try:
            activity_analysis = self.analyze_feature_activity()
            feature_rankings = activity_analysis.get("feature_rankings", {})

            suggestions = {}

            # Get volume and error rankings
            volume_ranking = feature_rankings.get("by_volume", [])
            error_ranking = feature_rankings.get("by_error_rate", [])

            # Create sets for quick lookup
            high_volume_features = {item["feature"] for item in volume_ranking[:5]}
            high_error_features = {
                item["feature"] for item in error_ranking if item["value"] > 5.0
            }

            for feature_data in volume_ranking:
                feature_name = feature_data["feature"]
                volume = feature_data["value"]
                flags = feature_data.get("flags", [])

                if feature_name in high_error_features:
                    # High error rate - keep at INFO or WARNING for visibility
                    suggestions[feature_name] = "WARNING"
                elif "dominant_feature" in flags or volume > 10000:
                    # Very high volume - reduce to WARNING
                    suggestions[feature_name] = "WARNING"
                elif "high_volume" in flags or volume > 1000:
                    # High volume - reduce to INFO
                    suggestions[feature_name] = "INFO"
                elif volume < 10:
                    # Low volume - can use DEBUG for more details
                    suggestions[feature_name] = "DEBUG"
                else:
                    # Moderate volume - keep at INFO
                    suggestions[feature_name] = "INFO"

            return suggestions

        except Exception as e:
            logging.getLogger(__name__).error("Error suggesting optimizations: %s", e)
            return {}

    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get nested dictionary value using dot notation."""
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return 0

        return value

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached analysis is still valid."""
        if cache_key not in self._analysis_cache or self._last_analysis_time is None:
            return False

        age = (datetime.now() - self._last_analysis_time).total_seconds()
        return age < self._cache_ttl

    def clear_cache(self) -> None:
        """Clear all cached analysis results."""
        self._analysis_cache.clear()
        self._last_analysis_time = None

    def get_feature_insights(self, feature_name: str) -> Dict[str, Any]:
        """
        Get detailed insights for a specific feature.

        Args:
            feature_name: Name of the feature to analyze

        Returns:
            Detailed insights for the feature
        """
        try:
            activity_analysis = self.analyze_feature_activity()

            # Find the feature in rankings
            feature_data = None
            for ranking in activity_analysis.get("feature_rankings", {}).values():
                for item in ranking:
                    if item["feature"] == feature_name:
                        feature_data = item
                        break
                if feature_data:
                    break

            if not feature_data:
                return {"error": f"Feature '{feature_name}' not found in analysis"}

            # Get additional insights
            insights = {
                "feature_name": feature_name,
                "basic_metrics": feature_data,
                "comparative_analysis": {},
                "recommendations": [],
                "trend_analysis": {},
            }

            # Comparative analysis
            all_features = activity_analysis.get("feature_rankings", {}).get(
                "by_volume", []
            )
            total_features = len(all_features)

            feature_rank = next(
                (
                    i
                    for i, item in enumerate(all_features)
                    if item["feature"] == feature_name
                ),
                total_features,
            )

            insights["comparative_analysis"] = {
                "volume_rank": feature_rank + 1,
                "total_features": total_features,
                "volume_percentile": ((total_features - feature_rank) / total_features)
                * 100,
            }

            # Feature-specific recommendations
            flags = feature_data.get("flags", [])
            if "high_volume" in flags:
                insights["recommendations"].append(
                    "Consider reducing log level to WARNING or ERROR to reduce volume"
                )
            if "high_error_rate" in flags:
                insights["recommendations"].append(
                    "Investigate underlying issues causing high error rate"
                )
            if "very_verbose" in flags:
                insights["recommendations"].append(
                    "Review if all logged information is necessary"
                )

            return insights

        except Exception as e:
            return {
                "error": f"Failed to get insights for feature '{feature_name}': {e}"
            }


def create_feature_analyzer(collector: LogStatisticsCollector) -> LogFeatureAnalyzer:
    """
    Factory function to create a feature analyzer.

    Args:
        collector: Statistics collector instance

    Returns:
        Configured LogFeatureAnalyzer instance
    """
    return LogFeatureAnalyzer(collector)
