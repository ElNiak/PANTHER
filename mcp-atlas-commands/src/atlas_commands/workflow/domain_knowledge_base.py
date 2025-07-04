"""
Domain Knowledge Base for Workflow Intelligence

Comprehensive knowledge base containing domain-specific patterns, best practices,
and decomposition strategies for different types of software development tasks.

This module provides structured knowledge for:
- Technology-specific decomposition patterns
- Domain expertise and best practices
- Risk factors and mitigation strategies
- Success patterns from different industries and contexts
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import timedelta
import json
from pathlib import Path

from .task_decomposition_engine import TaskComplexity, DomainType, SubTask, TaskDependency


@dataclass
class DecompositionPattern:
    """A reusable pattern for task decomposition"""
    pattern_id: str
    name: str
    description: str
    domains: List[DomainType]
    complexity_range: Tuple[TaskComplexity, TaskComplexity]
    trigger_keywords: List[str]
    subtask_templates: List[Dict[str, Any]]
    dependency_rules: List[Dict[str, str]]
    success_rate: float
    typical_effort_hours: float
    risk_factors: List[str]
    best_practices: List[str]
    anti_patterns: List[str]


@dataclass
class TechnologyStack:
    """Information about a specific technology stack"""
    name: str
    category: str  # frontend, backend, database, etc.
    common_patterns: List[str]
    complexity_factors: Dict[str, float]
    typical_decomposition: List[str]
    integration_points: List[str]
    common_issues: List[str]
    recommended_practices: List[str]


@dataclass
class IndustryPattern:
    """Industry-specific patterns and requirements"""
    industry: str
    common_requirements: List[str]
    compliance_needs: List[str]
    typical_constraints: Dict[str, Any]
    success_metrics: List[str]
    common_pitfalls: List[str]


class DomainKnowledgeBase:
    """
    Comprehensive knowledge base for domain-specific task decomposition.
    
    Provides structured access to:
    - Proven decomposition patterns
    - Technology-specific knowledge
    - Industry best practices
    - Risk assessment frameworks
    - Success pattern repositories
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.knowledge_path = self.storage_path / 'domain_knowledge'
        self.knowledge_path.mkdir(exist_ok=True)
        
        # Core knowledge structures
        self.decomposition_patterns: Dict[str, DecompositionPattern] = {}
        self.technology_stacks: Dict[str, TechnologyStack] = {}
        self.industry_patterns: Dict[str, IndustryPattern] = {}
        
        # Initialize with default knowledge
        self._initialize_default_patterns()
        self._initialize_technology_stacks()
        self._initialize_industry_patterns()
    
    def get_relevant_patterns(
        self,
        task_description: str,
        domains: List[str],
        complexity: TaskComplexity,
        tech_stack: List[str] = None
    ) -> List[DecompositionPattern]:
        """
        Get decomposition patterns relevant to the given task context.
        
        Args:
            task_description: Natural language description of the task
            domains: Identified domains for the task
            complexity: Estimated complexity level
            tech_stack: Technologies being used
            
        Returns:
            List of relevant decomposition patterns, sorted by relevance
        """
        relevant_patterns = []
        task_lower = task_description.lower()
        
        for pattern in self.decomposition_patterns.values():
            relevance_score = self._calculate_pattern_relevance(
                pattern, task_lower, domains, complexity, tech_stack or []
            )
            
            if relevance_score > 0.3:  # Threshold for relevance
                relevant_patterns.append((pattern, relevance_score))
        
        # Sort by relevance score
        relevant_patterns.sort(key=lambda x: x[1], reverse=True)
        
        return [pattern for pattern, score in relevant_patterns]
    
    def get_technology_guidance(self, tech_stack: List[str]) -> Dict[str, Any]:
        """
        Get technology-specific guidance for decomposition.
        
        Args:
            tech_stack: List of technologies being used
            
        Returns:
            Comprehensive guidance including patterns, risks, and best practices
        """
        guidance = {
            'technologies': {},
            'integration_concerns': [],
            'recommended_patterns': [],
            'risk_factors': [],
            'best_practices': []
        }
        
        for tech in tech_stack:
            tech_lower = tech.lower()
            
            # Find matching technology information
            for tech_name, tech_info in self.technology_stacks.items():
                if tech_lower in tech_name.lower() or any(
                    tech_lower in pattern.lower() for pattern in tech_info.common_patterns
                ):
                    guidance['technologies'][tech] = asdict(tech_info)
                    guidance['integration_concerns'].extend(tech_info.integration_points)
                    guidance['recommended_patterns'].extend(tech_info.common_patterns)
                    guidance['risk_factors'].extend(tech_info.common_issues)
                    guidance['best_practices'].extend(tech_info.recommended_practices)
        
        # Remove duplicates
        for key in ['integration_concerns', 'recommended_patterns', 'risk_factors', 'best_practices']:
            guidance[key] = list(set(guidance[key]))
        
        return guidance
    
    def get_domain_expertise(self, domain: DomainType) -> Dict[str, Any]:
        """
        Get domain-specific expertise and recommendations.
        
        Args:
            domain: The domain to get expertise for
            
        Returns:
            Domain-specific knowledge including patterns, practices, and considerations
        """
        domain_knowledge = {
            'domain': domain.value,
            'common_patterns': [],
            'typical_subtasks': [],
            'dependency_patterns': [],
            'risk_factors': [],
            'best_practices': [],
            'anti_patterns': [],
            'tools_and_frameworks': [],
            'quality_considerations': []
        }
        
        # Get patterns specific to this domain
        domain_patterns = [
            pattern for pattern in self.decomposition_patterns.values()
            if domain in pattern.domains
        ]
        
        for pattern in domain_patterns:
            domain_knowledge['common_patterns'].append({
                'name': pattern.name,
                'description': pattern.description,
                'typical_effort': pattern.typical_effort_hours,
                'success_rate': pattern.success_rate
            })
            domain_knowledge['risk_factors'].extend(pattern.risk_factors)
            domain_knowledge['best_practices'].extend(pattern.best_practices)
            domain_knowledge['anti_patterns'].extend(pattern.anti_patterns)
        
        # Add domain-specific considerations
        domain_specific = self._get_domain_specific_knowledge(domain)
        domain_knowledge.update(domain_specific)
        
        # Remove duplicates
        for key in ['risk_factors', 'best_practices', 'anti_patterns']:
            if key in domain_knowledge:
                domain_knowledge[key] = list(set(domain_knowledge[key]))
        
        return domain_knowledge
    
    def assess_integration_complexity(self, integration_points: List[str]) -> Dict[str, Any]:
        """
        Assess complexity of integration requirements.
        
        Args:
            integration_points: List of systems/services to integrate with
            
        Returns:
            Assessment of integration complexity and recommendations
        """
        assessment = {
            'complexity_score': 0,
            'risk_level': 'low',
            'critical_considerations': [],
            'recommended_approach': [],
            'potential_issues': [],
            'testing_requirements': []
        }
        
        complexity_factors = {
            'api': 2,
            'database': 3,
            'third-party': 4,
            'legacy': 5,
            'real-time': 4,
            'authentication': 3,
            'payment': 5,
            'external service': 3
        }
        
        for integration_point in integration_points:
            point_lower = integration_point.lower()
            
            for factor, complexity in complexity_factors.items():
                if factor in point_lower:
                    assessment['complexity_score'] += complexity
                    
                    # Add specific considerations
                    considerations = self._get_integration_considerations(factor)
                    assessment['critical_considerations'].extend(considerations)
        
        # Determine risk level
        total_score = assessment['complexity_score']
        if total_score <= 5:
            assessment['risk_level'] = 'low'
        elif total_score <= 10:
            assessment['risk_level'] = 'medium'
        elif total_score <= 20:
            assessment['risk_level'] = 'high'
        else:
            assessment['risk_level'] = 'very_high'
        
        # Add recommendations based on complexity
        assessment['recommended_approach'] = self._get_integration_recommendations(
            assessment['risk_level'], integration_points
        )
        
        return assessment
    
    def get_success_patterns(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get proven success patterns for similar contexts.
        
        Args:
            context: Context information (team size, timeline, domain, etc.)
            
        Returns:
            List of success patterns with implementation guidance
        """
        success_patterns = []
        
        # Match context to historical success patterns
        team_size = context.get('team_size', 1)
        timeline_pressure = context.get('timeline_pressure', 'medium')
        domains = context.get('domains', [])
        
        # Pattern: Small team, high pressure
        if team_size <= 3 and timeline_pressure == 'high':
            success_patterns.append({
                'pattern': 'MVP-First Development',
                'description': 'Focus on minimum viable product with iterative enhancement',
                'key_practices': [
                    'Identify core features only',
                    'Defer nice-to-have features',
                    'Use proven technologies',
                    'Minimize custom development',
                    'Plan for technical debt management'
                ],
                'success_rate': 0.85,
                'typical_outcome': 'Faster initial delivery with planned iterations'
            })
        
        # Pattern: Large team, complex integration
        if team_size > 5 and 'integration' in str(domains).lower():
            success_patterns.append({
                'pattern': 'Contract-First Development',
                'description': 'Define interfaces first, develop in parallel',
                'key_practices': [
                    'Design API contracts early',
                    'Create mock services',
                    'Establish integration testing',
                    'Plan regular integration checkpoints',
                    'Use feature flags for rollout'
                ],
                'success_rate': 0.78,
                'typical_outcome': 'Reduced integration issues and parallel development'
            })
        
        # Pattern: Security-sensitive domains
        if any('security' in domain.lower() for domain in domains):
            success_patterns.append({
                'pattern': 'Security-First Development',
                'description': 'Integrate security considerations from the start',
                'key_practices': [
                    'Threat modeling in design phase',
                    'Security code reviews',
                    'Automated security testing',
                    'Principle of least privilege',
                    'Regular security assessments'
                ],
                'success_rate': 0.92,
                'typical_outcome': 'Fewer security vulnerabilities and compliance issues'
            })
        
        return success_patterns
    
    def _initialize_default_patterns(self):
        """Initialize the knowledge base with proven decomposition patterns"""
        
        # Web Application Development Pattern
        self.decomposition_patterns['web_app_development'] = DecompositionPattern(
            pattern_id='web_app_development',
            name='Web Application Development',
            description='Standard pattern for building web applications',
            domains=[DomainType.FRONTEND, DomainType.BACKEND, DomainType.API],
            complexity_range=(TaskComplexity.MODERATE, TaskComplexity.COMPLEX),
            trigger_keywords=['web app', 'website', 'web application', 'frontend', 'backend'],
            subtask_templates=[
                {
                    'title': 'Design System Architecture',
                    'description': 'Define overall system architecture and component interactions',
                    'estimated_hours': 8,
                    'complexity': 'moderate',
                    'domain': 'backend',
                    'deliverables': ['Architecture diagram', 'Technology decisions', 'API design']
                },
                {
                    'title': 'Set Up Development Environment',
                    'description': 'Configure development tools, CI/CD, and local environment',
                    'estimated_hours': 4,
                    'complexity': 'simple',
                    'domain': 'infrastructure',
                    'deliverables': ['Dev environment setup', 'CI/CD pipeline', 'Documentation']
                },
                {
                    'title': 'Implement Backend API',
                    'description': 'Build server-side logic and API endpoints',
                    'estimated_hours': 16,
                    'complexity': 'complex',
                    'domain': 'backend',
                    'deliverables': ['API endpoints', 'Business logic', 'Database integration']
                },
                {
                    'title': 'Develop Frontend Components',
                    'description': 'Create user interface components and pages',
                    'estimated_hours': 12,
                    'complexity': 'moderate',
                    'domain': 'frontend',
                    'deliverables': ['UI components', 'Page layouts', 'State management']
                },
                {
                    'title': 'Integration Testing',
                    'description': 'Test frontend-backend integration and end-to-end workflows',
                    'estimated_hours': 6,
                    'complexity': 'moderate',
                    'domain': 'testing',
                    'deliverables': ['Integration tests', 'E2E tests', 'Test reports']
                }
            ],
            dependency_rules=[
                {'from': 'Design System Architecture', 'to': 'Implement Backend API', 'type': 'prerequisite'},
                {'from': 'Set Up Development Environment', 'to': 'Implement Backend API', 'type': 'prerequisite'},
                {'from': 'Implement Backend API', 'to': 'Develop Frontend Components', 'type': 'prerequisite'},
                {'from': 'Develop Frontend Components', 'to': 'Integration Testing', 'type': 'prerequisite'}
            ],
            success_rate=0.85,
            typical_effort_hours=46,
            risk_factors=[
                'Scope creep in UI requirements',
                'Integration complexity between frontend and backend',
                'Performance issues under load'
            ],
            best_practices=[
                'Start with API design and contracts',
                'Use established frameworks and libraries',
                'Implement automated testing early',
                'Plan for responsive design from start'
            ],
            anti_patterns=[
                'Building UI before API is defined',
                'Skipping automated testing',
                'Over-engineering the initial version'
            ]
        )
        
        # Authentication System Pattern
        self.decomposition_patterns['auth_system'] = DecompositionPattern(
            pattern_id='auth_system',
            name='Authentication System Implementation',
            description='Secure user authentication and authorization system',
            domains=[DomainType.SECURITY, DomainType.BACKEND, DomainType.API],
            complexity_range=(TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX),
            trigger_keywords=['auth', 'authentication', 'login', 'user management', 'security'],
            subtask_templates=[
                {
                    'title': 'Design Security Architecture',
                    'description': 'Plan authentication flow, token management, and security measures',
                    'estimated_hours': 6,
                    'complexity': 'complex',
                    'domain': 'security',
                    'deliverables': ['Security design doc', 'Threat model', 'Auth flow diagram']
                },
                {
                    'title': 'Implement User Registration',
                    'description': 'Build user signup with validation and verification',
                    'estimated_hours': 8,
                    'complexity': 'moderate',
                    'domain': 'backend',
                    'deliverables': ['Registration API', 'Email verification', 'Validation rules']
                },
                {
                    'title': 'Build Login System',
                    'description': 'Implement secure login with session/token management',
                    'estimated_hours': 10,
                    'complexity': 'complex',
                    'domain': 'security',
                    'deliverables': ['Login API', 'Token generation', 'Session management']
                },
                {
                    'title': 'Add Authorization Controls',
                    'description': 'Implement role-based access control and permissions',
                    'estimated_hours': 12,
                    'complexity': 'complex',
                    'domain': 'security',
                    'deliverables': ['RBAC system', 'Permission middleware', 'Role management']
                },
                {
                    'title': 'Security Testing',
                    'description': 'Comprehensive security testing and penetration testing',
                    'estimated_hours': 8,
                    'complexity': 'complex',
                    'domain': 'testing',
                    'deliverables': ['Security tests', 'Penetration test report', 'Vulnerability assessment']
                }
            ],
            dependency_rules=[
                {'from': 'Design Security Architecture', 'to': 'Implement User Registration', 'type': 'prerequisite'},
                {'from': 'Implement User Registration', 'to': 'Build Login System', 'type': 'prerequisite'},
                {'from': 'Build Login System', 'to': 'Add Authorization Controls', 'type': 'prerequisite'},
                {'from': 'Add Authorization Controls', 'to': 'Security Testing', 'type': 'prerequisite'}
            ],
            success_rate=0.75,
            typical_effort_hours=44,
            risk_factors=[
                'Security vulnerabilities',
                'Complex integration with existing systems',
                'Compliance requirements',
                'Session management complexity'
            ],
            best_practices=[
                'Use established security libraries',
                'Implement multi-factor authentication',
                'Regular security audits',
                'Secure token storage and transmission',
                'Rate limiting on auth endpoints'
            ],
            anti_patterns=[
                'Rolling custom crypto',
                'Storing passwords in plain text',
                'Weak session management',
                'Insufficient input validation'
            ]
        )
        
        # Add more patterns for different domains...
        self._add_performance_optimization_pattern()
        self._add_mobile_app_pattern()
        self._add_data_migration_pattern()
    
    def _add_performance_optimization_pattern(self):
        """Add performance optimization decomposition pattern"""
        self.decomposition_patterns['performance_optimization'] = DecompositionPattern(
            pattern_id='performance_optimization',
            name='Performance Optimization',
            description='Systematic approach to improving application performance',
            domains=[DomainType.PERFORMANCE, DomainType.BACKEND, DomainType.DATABASE],
            complexity_range=(TaskComplexity.MODERATE, TaskComplexity.COMPLEX),
            trigger_keywords=['performance', 'optimization', 'speed', 'latency', 'throughput'],
            subtask_templates=[
                {
                    'title': 'Performance Baseline Assessment',
                    'description': 'Measure current performance and identify bottlenecks',
                    'estimated_hours': 6,
                    'complexity': 'moderate',
                    'domain': 'performance',
                    'deliverables': ['Performance metrics', 'Bottleneck analysis', 'Benchmark results']
                },
                {
                    'title': 'Database Query Optimization',
                    'description': 'Optimize database queries and add appropriate indexes',
                    'estimated_hours': 10,
                    'complexity': 'complex',
                    'domain': 'database',
                    'deliverables': ['Optimized queries', 'Index strategy', 'Query performance metrics']
                },
                {
                    'title': 'Implement Caching Strategy',
                    'description': 'Add caching layers to reduce computation and I/O',
                    'estimated_hours': 8,
                    'complexity': 'moderate',
                    'domain': 'backend',
                    'deliverables': ['Caching implementation', 'Cache invalidation strategy', 'Performance improvement']
                },
                {
                    'title': 'Code-Level Optimizations',
                    'description': 'Optimize algorithms and data structures',
                    'estimated_hours': 12,
                    'complexity': 'complex',
                    'domain': 'backend',
                    'deliverables': ['Optimized algorithms', 'Profiling results', 'Performance tests']
                }
            ],
            dependency_rules=[
                {'from': 'Performance Baseline Assessment', 'to': 'Database Query Optimization', 'type': 'prerequisite'},
                {'from': 'Performance Baseline Assessment', 'to': 'Implement Caching Strategy', 'type': 'prerequisite'},
                {'from': 'Database Query Optimization', 'to': 'Code-Level Optimizations', 'type': 'parallel'},
                {'from': 'Implement Caching Strategy', 'to': 'Code-Level Optimizations', 'type': 'parallel'}
            ],
            success_rate=0.88,
            typical_effort_hours=36,
            risk_factors=[
                'Premature optimization',
                'Breaking existing functionality',
                'Complexity increases maintenance cost'
            ],
            best_practices=[
                'Measure before optimizing',
                'Focus on biggest bottlenecks first',
                'Maintain comprehensive test coverage',
                'Monitor performance continuously'
            ],
            anti_patterns=[
                'Optimizing without measuring',
                'Micro-optimizations before macro-optimizations',
                'Sacrificing code readability'
            ]
        )
    
    def _add_mobile_app_pattern(self):
        """Add mobile app development pattern"""
        self.decomposition_patterns['mobile_app'] = DecompositionPattern(
            pattern_id='mobile_app',
            name='Mobile Application Development',
            description='Cross-platform mobile application development approach',
            domains=[DomainType.MOBILE, DomainType.FRONTEND, DomainType.API],
            complexity_range=(TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX),
            trigger_keywords=['mobile app', 'ios', 'android', 'react native', 'flutter'],
            subtask_templates=[
                {
                    'title': 'Mobile Architecture Design',
                    'description': 'Design mobile-specific architecture and navigation',
                    'estimated_hours': 8,
                    'complexity': 'complex',
                    'domain': 'mobile',
                    'deliverables': ['Architecture design', 'Navigation flow', 'State management plan']
                },
                {
                    'title': 'Core UI Components',
                    'description': 'Build reusable mobile UI components',
                    'estimated_hours': 16,
                    'complexity': 'moderate',
                    'domain': 'frontend',
                    'deliverables': ['UI component library', 'Design system', 'Responsive layouts']
                },
                {
                    'title': 'API Integration',
                    'description': 'Integrate with backend APIs and handle offline scenarios',
                    'estimated_hours': 12,
                    'complexity': 'complex',
                    'domain': 'api',
                    'deliverables': ['API client', 'Offline support', 'Data synchronization']
                },
                {
                    'title': 'Device Features Integration',
                    'description': 'Integrate camera, GPS, push notifications, etc.',
                    'estimated_hours': 10,
                    'complexity': 'complex',
                    'domain': 'mobile',
                    'deliverables': ['Device integrations', 'Permission handling', 'Feature implementations']
                },
                {
                    'title': 'App Store Deployment',
                    'description': 'Prepare and deploy to app stores',
                    'estimated_hours': 6,
                    'complexity': 'moderate',
                    'domain': 'mobile',
                    'deliverables': ['App store packages', 'Store listings', 'Release documentation']
                }
            ],
            dependency_rules=[
                {'from': 'Mobile Architecture Design', 'to': 'Core UI Components', 'type': 'prerequisite'},
                {'from': 'Core UI Components', 'to': 'API Integration', 'type': 'prerequisite'},
                {'from': 'API Integration', 'to': 'Device Features Integration', 'type': 'parallel'},
                {'from': 'Device Features Integration', 'to': 'App Store Deployment', 'type': 'prerequisite'}
            ],
            success_rate=0.72,
            typical_effort_hours=52,
            risk_factors=[
                'Platform-specific issues',
                'App store approval delays',
                'Device compatibility problems',
                'Performance on lower-end devices'
            ],
            best_practices=[
                'Test on multiple devices early',
                'Plan for app store requirements',
                'Implement proper error handling',
                'Optimize for different screen sizes'
            ],
            anti_patterns=[
                'Not testing on real devices',
                'Ignoring platform guidelines',
                'Poor offline experience'
            ]
        )
    
    def _add_data_migration_pattern(self):
        """Add data migration pattern"""
        self.decomposition_patterns['data_migration'] = DecompositionPattern(
            pattern_id='data_migration',
            name='Data Migration Project',
            description='Safe and reliable data migration between systems',
            domains=[DomainType.DATABASE, DomainType.BACKEND, DomainType.INFRASTRUCTURE],
            complexity_range=(TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX),
            trigger_keywords=['migration', 'data migration', 'database migration', 'system migration'],
            subtask_templates=[
                {
                    'title': 'Migration Planning and Analysis',
                    'description': 'Analyze source and target systems, plan migration strategy',
                    'estimated_hours': 12,
                    'complexity': 'complex',
                    'domain': 'database',
                    'deliverables': ['Migration plan', 'Data mapping', 'Risk assessment']
                },
                {
                    'title': 'Build Migration Tools',
                    'description': 'Create tools for data extraction, transformation, and loading',
                    'estimated_hours': 20,
                    'complexity': 'complex',
                    'domain': 'backend',
                    'deliverables': ['ETL scripts', 'Data validation tools', 'Error handling']
                },
                {
                    'title': 'Test Migration Process',
                    'description': 'Test migration with sample data and validate results',
                    'estimated_hours': 16,
                    'complexity': 'complex',
                    'domain': 'testing',
                    'deliverables': ['Test results', 'Data validation reports', 'Performance metrics']
                },
                {
                    'title': 'Production Migration',
                    'description': 'Execute production migration with monitoring and rollback plan',
                    'estimated_hours': 8,
                    'complexity': 'very_complex',
                    'domain': 'infrastructure',
                    'deliverables': ['Migration execution', 'Monitoring dashboard', 'Rollback procedures']
                }
            ],
            dependency_rules=[
                {'from': 'Migration Planning and Analysis', 'to': 'Build Migration Tools', 'type': 'prerequisite'},
                {'from': 'Build Migration Tools', 'to': 'Test Migration Process', 'type': 'prerequisite'},
                {'from': 'Test Migration Process', 'to': 'Production Migration', 'type': 'prerequisite'}
            ],
            success_rate=0.68,
            typical_effort_hours=56,
            risk_factors=[
                'Data loss during migration',
                'Downtime exceeds maintenance window',
                'Data consistency issues',
                'Rollback complexity'
            ],
            best_practices=[
                'Always test with production-like data',
                'Plan for rollback scenarios',
                'Monitor data integrity continuously',
                'Communicate with stakeholders throughout'
            ],
            anti_patterns=[
                'Migrating without testing',
                'No rollback plan',
                'Insufficient data validation'
            ]
        )
    
    def _initialize_technology_stacks(self):
        """Initialize technology stack knowledge"""
        
        # React Frontend Stack
        self.technology_stacks['react_frontend'] = TechnologyStack(
            name='React Frontend',
            category='frontend',
            common_patterns=['Component-based architecture', 'State management', 'Routing'],
            complexity_factors={'state_management': 1.5, 'component_reuse': 0.8, 'testing': 1.2},
            typical_decomposition=[
                'Set up build tooling',
                'Create component library',
                'Implement routing',
                'Add state management',
                'Build pages/screens',
                'Add testing'
            ],
            integration_points=['REST APIs', 'GraphQL', 'Authentication', 'CSS frameworks'],
            common_issues=[
                'State management complexity',
                'Bundle size optimization',
                'SEO considerations',
                'Browser compatibility'
            ],
            recommended_practices=[
                'Use TypeScript for type safety',
                'Implement code splitting',
                'Use established UI libraries',
                'Set up automated testing'
            ]
        )
        
        # Node.js Backend Stack
        self.technology_stacks['nodejs_backend'] = TechnologyStack(
            name='Node.js Backend',
            category='backend',
            common_patterns=['Express server', 'Middleware pattern', 'Async/await'],
            complexity_factors={'async_handling': 1.4, 'error_handling': 1.3, 'performance': 1.6},
            typical_decomposition=[
                'Set up Express server',
                'Design API routes',
                'Implement middleware',
                'Add database integration',
                'Build business logic',
                'Add authentication'
            ],
            integration_points=['Databases', 'External APIs', 'Message queues', 'File storage'],
            common_issues=[
                'Callback hell / Promise chains',
                'Memory leaks',
                'Error handling complexity',
                'Performance bottlenecks'
            ],
            recommended_practices=[
                'Use async/await consistently',
                'Implement proper error handling',
                'Use environment configuration',
                'Add request logging and monitoring'
            ]
        )
        
        # Add more technology stacks...
        self._add_more_tech_stacks()
    
    def _add_more_tech_stacks(self):
        """Add additional technology stacks"""
        
        # Python Django Stack
        self.technology_stacks['django_backend'] = TechnologyStack(
            name='Django Backend',
            category='backend',
            common_patterns=['MVT pattern', 'ORM', 'Admin interface'],
            complexity_factors={'orm_complexity': 1.3, 'migrations': 1.2, 'admin_customization': 1.1},
            typical_decomposition=[
                'Set up Django project',
                'Design models and database',
                'Create views and templates',
                'Implement authentication',
                'Build admin interface',
                'Add API endpoints'
            ],
            integration_points=['PostgreSQL', 'Redis', 'Celery', 'REST Framework'],
            common_issues=[
                'Migration conflicts',
                'Query optimization',
                'Static file serving',
                'Scaling challenges'
            ],
            recommended_practices=[
                'Use Django REST Framework for APIs',
                'Implement proper model relationships',
                'Use database indexes effectively',
                'Set up proper logging'
            ]
        )
    
    def _initialize_industry_patterns(self):
        """Initialize industry-specific patterns"""
        
        # Healthcare Industry
        self.industry_patterns['healthcare'] = IndustryPattern(
            industry='Healthcare',
            common_requirements=['HIPAA compliance', 'Patient data security', 'Audit trails'],
            compliance_needs=['HIPAA', 'HITECH', 'FDA regulations'],
            typical_constraints={
                'data_retention': '7+ years',
                'security_level': 'highest',
                'audit_requirements': 'comprehensive',
                'uptime_requirements': '99.9%+'
            },
            success_metrics=['Security audit pass rate', 'Compliance score', 'Data integrity'],
            common_pitfalls=[
                'Insufficient data encryption',
                'Poor audit trail implementation',
                'Inadequate access controls'
            ]
        )
        
        # Financial Services
        self.industry_patterns['financial'] = IndustryPattern(
            industry='Financial Services',
            common_requirements=['PCI DSS compliance', 'Financial regulations', 'Real-time processing'],
            compliance_needs=['PCI DSS', 'SOX', 'PSD2', 'GDPR'],
            typical_constraints={
                'transaction_speed': 'sub-second',
                'data_accuracy': '100%',
                'availability': '99.99%',
                'security_level': 'highest'
            },
            success_metrics=['Transaction success rate', 'Security incidents', 'Compliance score'],
            common_pitfalls=[
                'Insufficient fraud detection',
                'Poor error handling in transactions',
                'Inadequate disaster recovery'
            ]
        )
    
    # Helper methods for calculations and assessments
    def _calculate_pattern_relevance(
        self,
        pattern: DecompositionPattern,
        task_description: str,
        domains: List[str],
        complexity: TaskComplexity,
        tech_stack: List[str]
    ) -> float:
        """Calculate how relevant a pattern is to the current task"""
        relevance_score = 0.0
        
        # Keyword matching
        keyword_matches = sum(1 for keyword in pattern.trigger_keywords if keyword in task_description)
        relevance_score += keyword_matches * 0.2
        
        # Domain matching
        pattern_domains = [d.value for d in pattern.domains]
        domain_matches = len(set(domains) & set(pattern_domains))
        relevance_score += domain_matches * 0.3
        
        # Complexity range matching
        complexity_values = {
            TaskComplexity.TRIVIAL: 1,
            TaskComplexity.SIMPLE: 2,
            TaskComplexity.MODERATE: 3,
            TaskComplexity.COMPLEX: 4,
            TaskComplexity.VERY_COMPLEX: 5
        }
        
        current_complexity = complexity_values[complexity]
        min_complexity = complexity_values[pattern.complexity_range[0]]
        max_complexity = complexity_values[pattern.complexity_range[1]]
        
        if min_complexity <= current_complexity <= max_complexity:
            relevance_score += 0.3
        
        # Success rate bonus
        relevance_score += pattern.success_rate * 0.2
        
        return min(relevance_score, 1.0)
    
    def _get_domain_specific_knowledge(self, domain: DomainType) -> Dict[str, Any]:
        """Get domain-specific knowledge and considerations"""
        domain_knowledge = {
            DomainType.FRONTEND: {
                'typical_subtasks': [
                    'UI/UX design and prototyping',
                    'Component development',
                    'State management implementation',
                    'Responsive design',
                    'Cross-browser testing'
                ],
                'tools_and_frameworks': ['React', 'Vue', 'Angular', 'CSS frameworks', 'Design systems'],
                'quality_considerations': ['Accessibility', 'Performance', 'SEO', 'User experience']
            },
            DomainType.BACKEND: {
                'typical_subtasks': [
                    'API design and implementation',
                    'Business logic development',
                    'Database integration',
                    'Authentication and authorization',
                    'Error handling and logging'
                ],
                'tools_and_frameworks': ['Express', 'Django', 'Spring Boot', 'FastAPI'],
                'quality_considerations': ['Scalability', 'Security', 'Performance', 'Maintainability']
            },
            DomainType.SECURITY: {
                'typical_subtasks': [
                    'Threat modeling',
                    'Authentication system',
                    'Authorization controls',
                    'Data encryption',
                    'Security testing'
                ],
                'tools_and_frameworks': ['OAuth', 'JWT', 'TLS/SSL', 'Security scanners'],
                'quality_considerations': ['Confidentiality', 'Integrity', 'Availability', 'Compliance']
            }
        }
        
        return domain_knowledge.get(domain, {})
    
    def _get_integration_considerations(self, integration_type: str) -> List[str]:
        """Get considerations for specific integration types"""
        considerations = {
            'api': [
                'API versioning strategy',
                'Rate limiting and throttling',
                'Error handling and retries',
                'Authentication and authorization'
            ],
            'database': [
                'Data consistency requirements',
                'Transaction management',
                'Connection pooling',
                'Migration strategy'
            ],
            'third-party': [
                'Service level agreements',
                'Vendor lock-in considerations',
                'Fallback mechanisms',
                'Cost implications'
            ],
            'legacy': [
                'Limited documentation',
                'Technology constraints',
                'Data format compatibility',
                'Migration complexity'
            ],
            'payment': [
                'PCI DSS compliance',
                'Transaction security',
                'Fraud prevention',
                'Reconciliation processes'
            ]
        }
        
        return considerations.get(integration_type, [])
    
    def _get_integration_recommendations(self, risk_level: str, integration_points: List[str]) -> List[str]:
        """Get recommendations based on integration risk level"""
        base_recommendations = [
            'Design clear integration contracts',
            'Implement comprehensive error handling',
            'Add monitoring and alerting',
            'Plan for graceful degradation'
        ]
        
        if risk_level in ['high', 'very_high']:
            base_recommendations.extend([
                'Implement circuit breaker pattern',
                'Add extensive integration testing',
                'Plan phased rollout strategy',
                'Create detailed runbooks'
            ])
        
        if risk_level == 'very_high':
            base_recommendations.extend([
                'Consider proof of concept first',
                'Implement comprehensive monitoring',
                'Plan for disaster recovery',
                'Engage architecture review board'
            ])
        
        return base_recommendations