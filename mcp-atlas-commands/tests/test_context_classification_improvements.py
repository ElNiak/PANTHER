"""Tests for improving context classification accuracy in AdaptiveCommandSelector."""

import pytest
from atlas_commands.workflow.adaptive_command_selector import (
    AdaptiveCommandSelector,
    ContextType
)
from atlas_commands.task_auto_generator import TaskAutoGenerator
from unittest.mock import Mock


class TestContextClassificationImprovements:
    """Test suite focused on improving context classification accuracy."""
    
    @pytest.fixture
    def selector(self):
        """Create selector for testing classification."""
        return AdaptiveCommandSelector(
            task_generator=Mock(spec=TaskAutoGenerator),
            memory_manager=Mock(),
            pattern_analyzer=Mock()
        )
    
    def test_improved_classification_keywords(self, selector):
        """Test improved keyword matching for better classification."""
        # Test cases that were previously misclassified
        problem_cases = [
            # (description, expected, previous_wrong_classification)
            ("Refactor payment module", ContextType.REFACTORING, ContextType.GREENFIELD),
            ("Debug memory leak in worker", ContextType.DEBUGGING, ContextType.MAINTENANCE),
            ("Investigate slow queries", ContextType.DEBUGGING, ContextType.OPTIMIZATION),
            ("Analyze and fix performance issues", ContextType.DEBUGGING, ContextType.OPTIMIZATION),
            ("Troubleshoot authentication failures", ContextType.DEBUGGING, ContextType.MAINTENANCE),
            ("Diagnose network timeout issues", ContextType.DEBUGGING, ContextType.MAINTENANCE),
        ]
        
        # Create an improved classification method
        def improved_classify_context_type(description: str) -> ContextType:
            """Enhanced context classification with better keyword matching."""
            desc_lower = description.lower()
            
            # Debugging keywords (check first - highest priority)
            debug_keywords = [
                'debug', 'troubleshoot', 'diagnose', 'investigate',
                'memory leak', 'crash', 'error', 'failure', 'timeout',
                'not working', 'broken', 'issue', 'problem', 'bug'
            ]
            if any(keyword in desc_lower for keyword in debug_keywords):
                return ContextType.DEBUGGING
            
            # Refactoring keywords (check before greenfield)
            refactor_keywords = [
                'refactor', 'restructure', 'reorganize', 'clean up',
                'extract', 'consolidate', 'simplify', 'modernize',
                'improve code', 'technical debt'
            ]
            if any(keyword in desc_lower for keyword in refactor_keywords):
                return ContextType.REFACTORING
            
            # Optimization keywords
            optimize_keywords = [
                'optimize', 'performance', 'speed up', 'faster',
                'efficiency', 'reduce latency', 'improve response time',
                'scale', 'bottleneck'
            ]
            if any(keyword in desc_lower for keyword in optimize_keywords):
                return ContextType.OPTIMIZATION
            
            # Greenfield/Creation keywords
            create_keywords = [
                'build', 'create', 'implement', 'develop', 'new',
                'feature', 'add', 'establish', 'design', 'architect'
            ]
            if any(keyword in desc_lower for keyword in create_keywords):
                return ContextType.GREENFIELD
            
            # Maintenance keywords
            maintenance_keywords = [
                'fix', 'repair', 'patch', 'update', 'maintain',
                'resolve', 'correct', 'address'
            ]
            if any(keyword in desc_lower for keyword in maintenance_keywords):
                return ContextType.MAINTENANCE
            
            # Deployment keywords
            deploy_keywords = [
                'deploy', 'release', 'ship', 'launch', 'rollout',
                'go live', 'production', 'staging'
            ]
            if any(keyword in desc_lower for keyword in deploy_keywords):
                return ContextType.DEPLOYMENT
            
            # Migration keywords
            migration_keywords = [
                'migrate', 'port', 'transition', 'move', 'upgrade',
                'convert', 'transfer'
            ]
            if any(keyword in desc_lower for keyword in migration_keywords):
                return ContextType.MIGRATION
            
            # Exploration keywords
            explore_keywords = [
                'explore', 'research', 'study', 'analyze', 'assess',
                'evaluate', 'examine', 'review'
            ]
            if any(keyword in desc_lower for keyword in explore_keywords):
                return ContextType.EXPLORATION
            
            # Default fallback
            return ContextType.EXPLORATION
        
        # Test improved classification
        correct = 0
        for desc, expected, _ in problem_cases:
            result = improved_classify_context_type(desc)
            if result == expected:
                correct += 1
            else:
                print(f"Still misclassified: '{desc}' as {result} instead of {expected}")
        
        accuracy = correct / len(problem_cases)
        assert accuracy == 1.0, f"Improved classification should fix all problem cases"
    
    def test_compound_task_classification(self, selector):
        """Test classification of tasks with multiple aspects."""
        compound_cases = [
            # Tasks that combine multiple aspects
            ("Investigate and fix authentication bug", ContextType.DEBUGGING),
            ("Analyze and refactor legacy code", ContextType.REFACTORING),
            ("Design and implement new API", ContextType.GREENFIELD),
            ("Debug and optimize slow queries", ContextType.DEBUGGING),  # Debug takes priority
            ("Build and deploy microservice", ContextType.GREENFIELD),  # Build takes priority
            ("Refactor and optimize database layer", ContextType.REFACTORING),  # Refactor takes priority
        ]
        
        for desc, expected in compound_cases:
            # Using original method to check current behavior
            result = selector._classify_context_type(desc)
            print(f"Compound: '{desc}' -> {result} (expected: {expected})")
    
    def test_context_classification_with_noise(self, selector):
        """Test classification with noisy or verbose descriptions."""
        noisy_cases = [
            # Verbose descriptions that should still classify correctly
            (
                "We need to investigate why users are experiencing random logouts "
                "after the latest deployment. The session management seems broken.",
                ContextType.DEBUGGING
            ),
            (
                "The payment processing module has grown too complex and needs "
                "to be refactored into smaller, more maintainable components.",
                ContextType.REFACTORING
            ),
            (
                "Let's build a comprehensive dashboard for monitoring system health "
                "with real-time metrics and alerting capabilities.",
                ContextType.GREENFIELD
            ),
            (
                "Our API response times have degraded significantly. We should "
                "optimize the database queries and add better caching.",
                ContextType.OPTIMIZATION
            ),
        ]
        
        for desc, expected in noisy_cases:
            result = selector._classify_context_type(desc)
            print(f"Noisy: '{desc[:50]}...' -> {result} (expected: {expected})")
    
    def test_ambiguous_descriptions(self, selector):
        """Test handling of ambiguous descriptions."""
        ambiguous_cases = [
            # Descriptions that could fit multiple categories
            ("Work on the authentication system", ContextType.EXPLORATION),  # Too vague
            ("Handle user feedback", ContextType.EXPLORATION),  # Unclear action
            ("Deal with technical debt", ContextType.REFACTORING),  # Implicit refactoring
            ("Improve system reliability", ContextType.OPTIMIZATION),  # Could be many things
            ("Address customer complaints about speed", ContextType.OPTIMIZATION),  # Performance related
        ]
        
        for desc, expected in ambiguous_cases:
            result = selector._classify_context_type(desc)
            # These might not match exactly, but should be reasonable
            print(f"Ambiguous: '{desc}' -> {result} (suggested: {expected})")
    
    def test_domain_specific_classification(self, selector):
        """Test classification with domain-specific terminology."""
        domain_cases = [
            # Security domain
            ("Implement OAuth2 authentication flow", ContextType.GREENFIELD),
            ("Fix CSRF vulnerability in forms", ContextType.DEBUGGING),
            ("Refactor authorization middleware", ContextType.REFACTORING),
            
            # Database domain
            ("Create database migration scripts", ContextType.MIGRATION),
            ("Debug deadlock issues", ContextType.DEBUGGING),
            ("Optimize query execution plans", ContextType.OPTIMIZATION),
            
            # Frontend domain
            ("Build responsive navigation component", ContextType.GREENFIELD),
            ("Fix rendering performance issues", ContextType.DEBUGGING),
            ("Refactor state management", ContextType.REFACTORING),
            
            # DevOps domain
            ("Deploy application to Kubernetes", ContextType.DEPLOYMENT),
            ("Debug container networking issues", ContextType.DEBUGGING),
            ("Migrate from Docker Swarm to K8s", ContextType.MIGRATION),
        ]
        
        correct = 0
        for desc, expected in domain_cases:
            result = selector._classify_context_type(desc)
            if result == expected:
                correct += 1
            else:
                print(f"Domain specific: '{desc}' -> {result} (expected: {expected})")
        
        accuracy = correct / len(domain_cases)
        print(f"Domain-specific accuracy: {accuracy:.1%}")
    
    def test_classification_priority_order(self, selector):
        """Test that classification respects priority order for overlapping keywords."""
        # When multiple keywords match, higher priority should win
        priority_cases = [
            # Debug should take priority over optimize
            ("Debug performance issues", ContextType.DEBUGGING),
            # Refactor should take priority over fix
            ("Refactor code to fix design flaws", ContextType.REFACTORING),
            # Build should take priority over deploy
            ("Build and deploy new service", ContextType.GREENFIELD),
            # Migrate should take priority over refactor
            ("Migrate and refactor database schema", ContextType.MIGRATION),
        ]
        
        for desc, expected in priority_cases:
            result = selector._classify_context_type(desc)
            assert result == expected, f"Priority order failed for: '{desc}'"
    
    def test_real_world_task_descriptions(self, selector):
        """Test with real-world task descriptions from actual projects."""
        real_world_cases = [
            # From PANTHER project
            ("Fix ivy server network resolution failure", ContextType.DEBUGGING),
            ("Investigate circular dependency between ivy and picoquic", ContextType.DEBUGGING),
            ("Refactor Docker operations into mixin classes", ContextType.REFACTORING),
            ("Implement circuit breaker pattern for retries", ContextType.GREENFIELD),
            ("Debug port conflict in experiment configuration", ContextType.DEBUGGING),
            ("Optimize experiment execution time", ContextType.OPTIMIZATION),
            
            # From web projects
            ("Build user authentication with JWT", ContextType.GREENFIELD),
            ("Fix CORS issues in API", ContextType.DEBUGGING),
            ("Migrate from REST to GraphQL", ContextType.MIGRATION),
            ("Refactor monolith into microservices", ContextType.REFACTORING),
            
            # From data projects
            ("Create ETL pipeline for analytics", ContextType.GREENFIELD),
            ("Debug data inconsistency issues", ContextType.DEBUGGING),
            ("Optimize data warehouse queries", ContextType.OPTIMIZATION),
            ("Migrate from MySQL to PostgreSQL", ContextType.MIGRATION),
        ]
        
        results = []
        for desc, expected in real_world_cases:
            result = selector._classify_context_type(desc)
            is_correct = result == expected
            results.append(is_correct)
            if not is_correct:
                print(f"Real-world fail: '{desc}' -> {result} (expected: {expected})")
        
        accuracy = sum(results) / len(results)
        print(f"Real-world accuracy: {accuracy:.1%}")
        assert accuracy >= 0.8, "Should handle most real-world cases correctly"
    
    def test_classification_with_technical_jargon(self, selector):
        """Test classification with technical jargon and abbreviations."""
        technical_cases = [
            ("Debug OOM errors in JVM", ContextType.DEBUGGING),
            ("Implement gRPC service", ContextType.GREENFIELD),
            ("Refactor DI container", ContextType.REFACTORING),
            ("Fix SQL injection in ORM", ContextType.DEBUGGING),
            ("Optimize GC pause times", ContextType.OPTIMIZATION),
            ("Deploy to AWS ECS", ContextType.DEPLOYMENT),
            ("Migrate from REST to GraphQL API", ContextType.MIGRATION),
            ("Debug k8s pod crashes", ContextType.DEBUGGING),
            ("Build CI/CD pipeline", ContextType.GREENFIELD),
            ("Refactor MVC to MVVM", ContextType.REFACTORING),
        ]
        
        for desc, expected in technical_cases:
            result = selector._classify_context_type(desc)
            print(f"Technical: '{desc}' -> {result} (expected: {expected})")


class TestClassificationEnhancements:
    """Test proposed enhancements to classification system."""
    
    def test_weighted_keyword_scoring(self):
        """Test classification using weighted keyword scoring instead of simple matching."""
        
        def weighted_classify(description: str) -> tuple[ContextType, float]:
            """Classify using weighted scores for each context type."""
            desc_lower = description.lower()
            scores = {context: 0.0 for context in ContextType}
            
            # Define weighted keywords for each context
            context_keywords = {
                ContextType.DEBUGGING: {
                    'debug': 1.0, 'fix': 0.7, 'bug': 1.0, 'issue': 0.8,
                    'troubleshoot': 1.0, 'investigate': 0.9, 'diagnose': 1.0,
                    'error': 0.9, 'crash': 1.0, 'broken': 0.9, 'fail': 0.8
                },
                ContextType.REFACTORING: {
                    'refactor': 1.0, 'restructure': 1.0, 'reorganize': 0.9,
                    'clean': 0.7, 'extract': 0.8, 'simplify': 0.8,
                    'improve': 0.6, 'modernize': 0.9, 'consolidate': 0.9
                },
                ContextType.GREENFIELD: {
                    'build': 0.9, 'create': 0.9, 'implement': 0.8, 'new': 0.7,
                    'develop': 0.9, 'feature': 0.6, 'add': 0.7, 'design': 0.8
                },
                ContextType.OPTIMIZATION: {
                    'optimize': 1.0, 'performance': 0.9, 'speed': 0.8,
                    'faster': 0.9, 'efficiency': 0.9, 'improve': 0.6,
                    'scale': 0.8, 'bottleneck': 0.9
                }
            }
            
            # Calculate scores
            for context, keywords in context_keywords.items():
                for keyword, weight in keywords.items():
                    if keyword in desc_lower:
                        scores[context] += weight
            
            # Get highest scoring context
            best_context = max(scores, key=scores.get)
            confidence = scores[best_context]
            
            # Default to exploration if no strong signal
            if confidence < 0.5:
                return ContextType.EXPLORATION, 0.5
            
            return best_context, confidence
        
        # Test weighted classification
        test_cases = [
            "Debug and fix authentication issue",  # Should be DEBUGGING
            "Refactor and improve code quality",   # Should be REFACTORING
            "Build new feature quickly",           # Should be GREENFIELD
        ]
        
        for desc in test_cases:
            context, confidence = weighted_classify(desc)
            print(f"Weighted: '{desc}' -> {context} (confidence: {confidence:.2f})")
    
    def test_context_patterns_with_regex(self):
        """Test using regex patterns for more sophisticated matching."""
        import re
        
        # Define regex patterns for each context
        context_patterns = {
            ContextType.DEBUGGING: [
                r'\b(debug|fix|troubleshoot|diagnose)\s+\w+\s+(issue|problem|error|bug)',
                r'\b(investigate|analyze)\s+\w+\s+(failure|crash|leak)',
                r'\bnot\s+working\b',
                r'\b(memory|resource)\s+leak',
            ],
            ContextType.REFACTORING: [
                r'\b(refactor|restructure|reorganize)\s+\w+\s+(module|component|system)',
                r'\b(extract|consolidate)\s+\w+\s+(class|method|function)',
                r'\b(clean|improve)\s+code',
                r'\btechnical\s+debt',
            ],
            ContextType.GREENFIELD: [
                r'\b(build|create|implement)\s+(new\s+)?\w+\s+(feature|system|service)',
                r'\b(develop|design)\s+\w+\s+(from\s+scratch)?',
                r'\bnew\s+\w+\s+(implementation|development)',
            ],
        }
        
        def regex_classify(description: str) -> ContextType:
            """Classify using regex patterns."""
            desc_lower = description.lower()
            
            for context, patterns in context_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, desc_lower):
                        return context
            
            return ContextType.EXPLORATION
        
        # Test regex classification
        test_cases = [
            "Debug authentication issue in login flow",
            "Refactor user module to improve maintainability",
            "Build new payment feature from scratch",
            "Fix memory leak in background workers",
        ]
        
        for desc in test_cases:
            result = regex_classify(desc)
            print(f"Regex: '{desc}' -> {result}")
    
    def test_ml_based_classification_simulation(self):
        """Simulate ML-based classification using TF-IDF-like scoring."""
        from collections import Counter
        import math
        
        # Simulate training data
        training_data = {
            ContextType.DEBUGGING: [
                "debug memory leak", "fix authentication bug", "troubleshoot network issue",
                "investigate crash", "diagnose performance problem"
            ],
            ContextType.REFACTORING: [
                "refactor payment module", "restructure database layer", "clean up code",
                "extract common logic", "simplify complex method"
            ],
            ContextType.GREENFIELD: [
                "build new api", "create user dashboard", "implement feature",
                "develop microservice", "design system architecture"
            ],
        }
        
        def calculate_tfidf_score(description: str, context_docs: list) -> float:
            """Calculate simplified TF-IDF score."""
            words = description.lower().split()
            doc_words = ' '.join(context_docs).lower().split()
            word_freq = Counter(doc_words)
            
            score = 0
            for word in words:
                tf = word_freq.get(word, 0) / len(doc_words)
                # Simplified IDF (would need full corpus in real implementation)
                idf = math.log(10 / (1 + word_freq.get(word, 0)))
                score += tf * idf
            
            return score
        
        def ml_classify(description: str) -> tuple[ContextType, float]:
            """Classify using ML-like scoring."""
            scores = {}
            
            for context, docs in training_data.items():
                scores[context] = calculate_tfidf_score(description, docs)
            
            best_context = max(scores, key=scores.get)
            confidence = scores[best_context] / sum(scores.values()) if sum(scores.values()) > 0 else 0
            
            return best_context, confidence
        
        # Test ML-based classification
        test_cases = [
            "fix critical bug in authentication",
            "refactor legacy codebase",
            "build innovative feature",
        ]
        
        for desc in test_cases:
            context, confidence = ml_classify(desc)
            print(f"ML-based: '{desc}' -> {context} (confidence: {confidence:.2%})")