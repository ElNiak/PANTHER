"""
Machine Learning Pipeline for Task Decomposition Analysis

Implements ML models for intelligent task decomposition including:
- Feature extraction from natural language task descriptions
- Classification models for complexity and domain prediction
- Similarity scoring for pattern matching
- Continuous learning from decomposition outcomes
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import pickle
import json
import re
from pathlib import Path

# Sklearn imports for ML pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin

from .task_decomposition_engine import TaskComplexity, DomainType, TaskDecomposition


@dataclass
class TaskFeatures:
    """Extracted features from task description"""
    text_features: Dict[str, float]
    complexity_features: Dict[str, int]
    domain_features: Dict[str, float]
    semantic_features: np.ndarray
    metadata_features: Dict[str, Any]


@dataclass
class DecompositionTrainingData:
    """Training data for ML models"""
    task_description: str
    features: TaskFeatures
    actual_subtasks: List[str]
    actual_complexity: TaskComplexity
    actual_domains: List[DomainType]
    actual_effort_hours: float
    success_score: float
    decomposition_quality: float


class TaskFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Custom transformer for extracting features from task descriptions.
    
    Extracts multiple types of features:
    - Text features (TF-IDF, word counts, sentiment)
    - Complexity indicators (scope words, integration points)
    - Domain indicators (technology keywords, domain-specific terms)
    - Semantic features (embeddings, topic modeling)
    """
    
    def __init__(self, max_features: int = 1000):
        self.max_features = max_features
        self.tfidf_vectorizer = None
        self.complexity_patterns = None
        self.domain_keywords = None
        self.topic_model = None
        self._is_fitted = False
    
    def fit(self, X: List[str], y=None):
        """Fit the feature extractor on training data"""
        # Initialize TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words='english',
            ngram_range=(1, 3),
            lowercase=True
        )
        self.tfidf_vectorizer.fit(X)
        
        # Initialize complexity patterns
        self._init_complexity_patterns()
        
        # Initialize domain keywords
        self._init_domain_keywords()
        
        # Fit topic model
        self.topic_model = LatentDirichletAllocation(
            n_components=10,
            random_state=42,
            max_iter=100
        )
        tfidf_matrix = self.tfidf_vectorizer.transform(X)
        self.topic_model.fit(tfidf_matrix)
        
        self._is_fitted = True
        return self
    
    def transform(self, X: List[str]) -> np.ndarray:
        """Transform task descriptions into feature vectors"""
        if not self._is_fitted:
            raise ValueError("Feature extractor must be fitted before transform")
        
        features_list = []
        for description in X:
            features = self._extract_features(description)
            features_list.append(features)
        
        return np.array(features_list)
    
    def _extract_features(self, description: str) -> np.ndarray:
        """Extract comprehensive features from a single task description"""
        # Text features (TF-IDF)
        tfidf_features = self.tfidf_vectorizer.transform([description]).toarray()[0]
        
        # Complexity features
        complexity_features = self._extract_complexity_features(description)
        
        # Domain features
        domain_features = self._extract_domain_features(description)
        
        # Topic features
        topic_features = self.topic_model.transform(
            self.tfidf_vectorizer.transform([description])
        )[0]
        
        # Combine all features
        all_features = np.concatenate([
            tfidf_features,
            complexity_features,
            domain_features,
            topic_features
        ])
        
        return all_features
    
    def _init_complexity_patterns(self):
        """Initialize patterns for complexity detection"""
        self.complexity_patterns = {
            'scope_indicators': [
                r'\b(all|every|entire|complete|comprehensive|full|total)\b',
                r'\b(multiple|several|many|various)\b',
                r'\b(system|platform|application|solution)\b'
            ],
            'integration_indicators': [
                r'\b(integrate|connect|sync|merge|combine|link)\b',
                r'\b(api|service|microservice|webhook)\b',
                r'\b(third[- ]party|external|remote)\b'
            ],
            'new_development': [
                r'\b(new|create|build|develop|implement|design)\b',
                r'\b(from scratch|ground up|fresh)\b'
            ],
            'modification_indicators': [
                r'\b(refactor|restructure|redesign|migrate|update|modify)\b',
                r'\b(improve|enhance|optimize|upgrade)\b'
            ],
            'technical_complexity': [
                r'\b(algorithm|machine learning|ai|distributed|concurrent)\b',
                r'\b(performance|optimization|scalability|security)\b',
                r'\b(real[- ]time|streaming|queue|cache)\b'
            ]
        }
    
    def _init_domain_keywords(self):
        """Initialize domain-specific keywords"""
        self.domain_keywords = {
            'frontend': [
                'ui', 'ux', 'interface', 'component', 'react', 'vue', 'angular',
                'css', 'html', 'javascript', 'typescript', 'responsive', 'mobile'
            ],
            'backend': [
                'api', 'server', 'service', 'endpoint', 'microservice', 'business logic',
                'node', 'python', 'java', 'golang', 'rest', 'graphql'
            ],
            'database': [
                'database', 'db', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql',
                'migration', 'schema', 'query', 'index', 'transaction'
            ],
            'infrastructure': [
                'deploy', 'deployment', 'docker', 'kubernetes', 'cloud', 'aws', 'azure',
                'infrastructure', 'devops', 'ci/cd', 'pipeline', 'monitoring'
            ],
            'security': [
                'security', 'auth', 'authentication', 'authorization', 'encrypt',
                'secure', 'ssl', 'tls', 'oauth', 'jwt', 'session'
            ],
            'mobile': [
                'mobile', 'ios', 'android', 'react native', 'flutter', 'app',
                'native', 'hybrid', 'responsive'
            ],
            'testing': [
                'test', 'testing', 'unit test', 'integration test', 'e2e',
                'qa', 'quality', 'validation', 'verification'
            ]
        }
    
    def _extract_complexity_features(self, description: str) -> np.ndarray:
        """Extract complexity-related features"""
        features = []
        description_lower = description.lower()
        
        for category, patterns in self.complexity_patterns.items():
            count = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, description_lower))
                count += matches
            features.append(count)
        
        # Additional complexity metrics
        features.extend([
            len(description.split()),  # Word count
            len(description.split('.')),  # Sentence count
            description.count('and'),  # Coordination complexity
            description.count('or'),   # Alternative complexity
        ])
        
        return np.array(features, dtype=float)
    
    def _extract_domain_features(self, description: str) -> np.ndarray:
        """Extract domain-related features"""
        features = []
        description_lower = description.lower()
        
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in description_lower)
            # Normalize by number of keywords in domain
            normalized_score = score / len(keywords)
            features.append(normalized_score)
        
        return np.array(features, dtype=float)


class ComplexityPredictor:
    """ML model for predicting task complexity"""
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.label_encoder = LabelEncoder()
        self.is_fitted = False
    
    def fit(self, features: np.ndarray, complexities: List[TaskComplexity]):
        """Train the complexity prediction model"""
        # Encode complexity labels
        complexity_labels = [c.value for c in complexities]
        encoded_labels = self.label_encoder.fit_transform(complexity_labels)
        
        # Train the model
        self.model.fit(features, encoded_labels)
        self.is_fitted = True
        
        return self
    
    def predict(self, features: np.ndarray) -> List[TaskComplexity]:
        """Predict task complexity"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        predictions = self.model.predict(features)
        complexity_labels = self.label_encoder.inverse_transform(predictions)
        
        return [TaskComplexity(label) for label in complexity_labels]
    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Get prediction probabilities"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        return self.model.predict_proba(features)


class EffortEstimator:
    """ML model for predicting effort (hours) required"""
    
    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def fit(self, features: np.ndarray, effort_hours: List[float]):
        """Train the effort estimation model"""
        # Scale features
        scaled_features = self.scaler.fit_transform(features)
        
        # Train the model
        self.model.fit(scaled_features, effort_hours)
        self.is_fitted = True
        
        return self
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict effort in hours"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        scaled_features = self.scaler.transform(features)
        return self.model.predict(scaled_features)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before getting feature importance")
        
        return dict(enumerate(self.model.feature_importances_))


class SimilarityMatcher:
    """Find similar historical decompositions using various similarity metrics"""
    
    def __init__(self):
        self.historical_features = None
        self.historical_metadata = None
        self.vectorizer = None
        self.is_fitted = False
    
    def fit(self, historical_data: List[DecompositionTrainingData]):
        """Fit similarity matcher on historical data"""
        # Extract features and metadata
        descriptions = [data.task_description for data in historical_data]
        self.historical_metadata = historical_data
        
        # Fit TF-IDF vectorizer for semantic similarity
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.historical_features = self.vectorizer.fit_transform(descriptions)
        
        self.is_fitted = True
        return self
    
    def find_similar(
        self,
        query_description: str,
        top_k: int = 5,
        min_similarity: float = 0.1
    ) -> List[Tuple[DecompositionTrainingData, float]]:
        """Find similar historical decompositions"""
        if not self.is_fitted:
            raise ValueError("Similarity matcher must be fitted before use")
        
        # Transform query
        query_features = self.vectorizer.transform([query_description])
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_features, self.historical_features)[0]
        
        # Get top similar items
        similar_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in similar_indices:
            similarity_score = similarities[idx]
            if similarity_score >= min_similarity:
                results.append((self.historical_metadata[idx], similarity_score))
        
        return results


class MLDecompositionPipeline:
    """
    Complete ML pipeline for intelligent task decomposition.
    
    Combines feature extraction, complexity prediction, effort estimation,
    and similarity matching for comprehensive task analysis.
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.models_path = self.storage_path / 'ml_models'
        self.models_path.mkdir(exist_ok=True)
        
        # Initialize components
        self.feature_extractor = TaskFeatureExtractor()
        self.complexity_predictor = ComplexityPredictor()
        self.effort_estimator = EffortEstimator()
        self.similarity_matcher = SimilarityMatcher()
        
        # Training data
        self.training_data: List[DecompositionTrainingData] = []
        
        # Model state
        self.is_trained = False
        
        # Load existing models if available
        self._load_models()
    
    def add_training_data(self, training_data: DecompositionTrainingData):
        """Add new training data for model improvement"""
        self.training_data.append(training_data)
        
        # Auto-retrain if we have enough new data
        if len(self.training_data) % 10 == 0:  # Retrain every 10 new examples
            self.train_models()
    
    def train_models(self):
        """Train all ML models on available data"""
        if len(self.training_data) < 5:
            print(f"Not enough training data: {len(self.training_data)} examples (need at least 5)")
            return
        
        print(f"Training models on {len(self.training_data)} examples...")
        
        # Extract features and labels
        descriptions = [data.task_description for data in self.training_data]
        complexities = [data.actual_complexity for data in self.training_data]
        effort_hours = [data.actual_effort_hours for data in self.training_data]
        
        # Train feature extractor
        self.feature_extractor.fit(descriptions)
        features = self.feature_extractor.transform(descriptions)
        
        # Train complexity predictor
        self.complexity_predictor.fit(features, complexities)
        
        # Train effort estimator
        self.effort_estimator.fit(features, effort_hours)
        
        # Train similarity matcher
        self.similarity_matcher.fit(self.training_data)
        
        self.is_trained = True
        
        # Save models
        self._save_models()
        
        print("Model training completed successfully!")
    
    def analyze_task(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive ML analysis of a task description.
        
        Returns predictions for complexity, effort, similar tasks, and recommendations.
        """
        if not self.is_trained:
            return self._fallback_analysis(task_description)
        
        # Extract features
        features = self.feature_extractor.transform([task_description])
        
        # Predict complexity
        predicted_complexity = self.complexity_predictor.predict(features)[0]
        complexity_proba = self.complexity_predictor.predict_proba(features)[0]
        
        # Predict effort
        predicted_effort = self.effort_estimator.predict(features)[0]
        
        # Find similar tasks
        similar_tasks = self.similarity_matcher.find_similar(task_description, top_k=3)
        
        # Generate recommendations based on similar tasks
        recommendations = self._generate_recommendations(similar_tasks, predicted_complexity)
        
        return {
            'predicted_complexity': {
                'complexity': predicted_complexity.value,
                'confidence': float(np.max(complexity_proba)),
                'probabilities': {
                    complexity.value: float(prob) 
                    for complexity, prob in zip(TaskComplexity, complexity_proba)
                }
            },
            'predicted_effort_hours': float(predicted_effort),
            'similar_tasks': [
                {
                    'description': task.task_description,
                    'similarity_score': float(score),
                    'actual_complexity': task.actual_complexity.value,
                    'actual_effort': task.actual_effort_hours,
                    'success_score': task.success_score
                }
                for task, score in similar_tasks
            ],
            'recommendations': recommendations,
            'confidence': self._calculate_overall_confidence(complexity_proba, similar_tasks)
        }
    
    def get_model_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the ML models"""
        if not self.is_trained or len(self.training_data) < 5:
            return {'error': 'Insufficient training data for metrics'}
        
        # Prepare data for evaluation
        descriptions = [data.task_description for data in self.training_data]
        complexities = [data.actual_complexity for data in self.training_data]
        effort_hours = [data.actual_effort_hours for data in self.training_data]
        
        features = self.feature_extractor.transform(descriptions)
        
        # Complexity prediction accuracy
        complexity_labels = [c.value for c in complexities]
        encoded_complexities = self.complexity_predictor.label_encoder.transform(complexity_labels)
        complexity_accuracy = cross_val_score(
            self.complexity_predictor.model, features, encoded_complexities, cv=3
        ).mean()
        
        # Effort estimation accuracy (R²)
        effort_r2 = cross_val_score(
            self.effort_estimator.model, 
            self.effort_estimator.scaler.transform(features), 
            effort_hours, 
            cv=3,
            scoring='r2'
        ).mean()
        
        return {
            'training_examples': len(self.training_data),
            'complexity_accuracy': float(complexity_accuracy),
            'effort_r2_score': float(effort_r2),
            'feature_count': features.shape[1],
            'last_trained': datetime.now().isoformat()
        }
    
    def _fallback_analysis(self, task_description: str) -> Dict[str, Any]:
        """Fallback analysis when models aren't trained"""
        # Simple rule-based analysis
        description_lower = task_description.lower()
        
        # Estimate complexity based on keywords
        complexity_score = 0
        if any(word in description_lower for word in ['simple', 'easy', 'quick']):
            complexity_score -= 1
        if any(word in description_lower for word in ['complex', 'difficult', 'comprehensive']):
            complexity_score += 2
        if any(word in description_lower for word in ['integrate', 'multiple', 'system']):
            complexity_score += 1
        
        # Map to complexity enum
        if complexity_score <= 0:
            predicted_complexity = TaskComplexity.SIMPLE
        elif complexity_score == 1:
            predicted_complexity = TaskComplexity.MODERATE
        else:
            predicted_complexity = TaskComplexity.COMPLEX
        
        # Estimate effort based on word count and complexity
        word_count = len(task_description.split())
        base_hours = max(2, word_count / 10)  # Rough estimation
        complexity_multipliers = {
            TaskComplexity.TRIVIAL: 0.5,
            TaskComplexity.SIMPLE: 1.0,
            TaskComplexity.MODERATE: 2.0,
            TaskComplexity.COMPLEX: 4.0,
            TaskComplexity.VERY_COMPLEX: 8.0
        }
        predicted_effort = base_hours * complexity_multipliers[predicted_complexity]
        
        return {
            'predicted_complexity': {
                'complexity': predicted_complexity.value,
                'confidence': 0.3,  # Low confidence for rule-based
                'probabilities': {c.value: 0.2 for c in TaskComplexity}
            },
            'predicted_effort_hours': predicted_effort,
            'similar_tasks': [],
            'recommendations': ['Consider gathering more training data for better predictions'],
            'confidence': 0.3,
            'note': 'Using rule-based fallback - train models with data for better accuracy'
        }
    
    def _generate_recommendations(
        self,
        similar_tasks: List[Tuple[DecompositionTrainingData, float]],
        predicted_complexity: TaskComplexity
    ) -> List[str]:
        """Generate recommendations based on similar tasks and complexity"""
        recommendations = []
        
        if similar_tasks:
            # Analyze successful patterns
            successful_tasks = [task for task, score in similar_tasks if task.success_score > 0.7]
            
            if successful_tasks:
                avg_effort = sum(task.actual_effort_hours for task in successful_tasks) / len(successful_tasks)
                recommendations.append(f"Similar successful tasks averaged {avg_effort:.1f} hours")
                
                # Common success factors
                common_domains = set()
                for task in successful_tasks:
                    common_domains.update(task.actual_domains)
                
                if common_domains:
                    recommendations.append(f"Consider expertise in: {', '.join(d.value for d in common_domains)}")
        
        # Complexity-based recommendations
        if predicted_complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]:
            recommendations.extend([
                "Consider breaking into smaller subtasks",
                "Plan for multiple iterations and reviews",
                "Identify critical dependencies early"
            ])
        elif predicted_complexity == TaskComplexity.SIMPLE:
            recommendations.append("Good candidate for quick implementation")
        
        return recommendations
    
    def _calculate_overall_confidence(
        self,
        complexity_proba: np.ndarray,
        similar_tasks: List[Tuple[DecompositionTrainingData, float]]
    ) -> float:
        """Calculate overall confidence in the analysis"""
        # Base confidence from model certainty
        complexity_confidence = float(np.max(complexity_proba))
        
        # Boost confidence if we have similar tasks
        similarity_boost = 0
        if similar_tasks:
            avg_similarity = sum(score for _, score in similar_tasks) / len(similar_tasks)
            similarity_boost = avg_similarity * 0.3
        
        # Training data boost
        training_boost = min(len(self.training_data) / 100, 0.2)  # Up to 20% boost
        
        overall_confidence = min(complexity_confidence + similarity_boost + training_boost, 0.95)
        return float(overall_confidence)
    
    def _save_models(self):
        """Save trained models to disk"""
        models = {
            'feature_extractor': self.feature_extractor,
            'complexity_predictor': self.complexity_predictor,
            'effort_estimator': self.effort_estimator,
            'similarity_matcher': self.similarity_matcher,
            'training_data': self.training_data
        }
        
        model_file = self.models_path / 'ml_decomposition_models.pkl'
        with open(model_file, 'wb') as f:
            pickle.dump(models, f)
        
        print(f"Models saved to {model_file}")
    
    def _load_models(self):
        """Load previously trained models from disk"""
        model_file = self.models_path / 'ml_decomposition_models.pkl'
        
        if model_file.exists():
            try:
                with open(model_file, 'rb') as f:
                    models = pickle.load(f)
                
                self.feature_extractor = models['feature_extractor']
                self.complexity_predictor = models['complexity_predictor']
                self.effort_estimator = models['effort_estimator']
                self.similarity_matcher = models['similarity_matcher']
                self.training_data = models.get('training_data', [])
                
                self.is_trained = True
                print(f"Models loaded from {model_file}")
                
            except Exception as e:
                print(f"Error loading models: {e}")
                self.is_trained = False
        else:
            print("No saved models found - will train on first use")