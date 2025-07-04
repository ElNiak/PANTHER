# ATLAS MCP Interaction Tests

## Test Suite Overview

Comprehensive test suite for ATLAS MCP integration with Claude Code, covering all 49 tools across 9 categories with realistic workflow scenarios.

## Test Categories

### 1. Core Task Management Tests

#### Test 1.1: Hierarchical Task Creation
```json
{
  "test_id": "task_creation_001",
  "description": "Create parent task with subtasks",
  "mcp_calls": [
    {
      "tool": "create_hierarchical_task",
      "params": {
        "project_name": "Software-Engineer-AI-Agent-Atlas",
        "task_id": "feature-user-auth",
        "title": "Implement User Authentication System",
        "description": "Complete OAuth2 authentication with JWT tokens",
        "priority": "high",
        "category": "feature"
      },
      "expected": "Task created successfully with unique ID"
    },
    {
      "tool": "create_hierarchical_task", 
      "params": {
        "project_name": "Software-Engineer-AI-Agent-Atlas",
        "task_id": "auth-backend",
        "parent_task_id": "feature-user-auth",
        "title": "Backend Authentication API",
        "description": "REST endpoints for login/logout/refresh",
        "priority": "high"
      },
      "expected": "Subtask linked to parent correctly"
    }
  ],
  "validation": [
    "Parent-child relationship established",
    "Task metadata persisted to storage",
    "Hierarchical structure queryable"
  ]
}
```

#### Test 1.2: Task Status Updates and Progress Tracking
```json
{
  "test_id": "task_progress_001",
  "description": "Update task status and track progress",
  "mcp_calls": [
    {
      "tool": "update_task_status",
      "params": {
        "project_name": "Software-Engineer-AI-Agent-Atlas",
        "task_id": "auth-backend",
        "status": "in_progress",
        "progress_percentage": 25,
        "notes": "Started API endpoint design"
      },
      "expected": "Status updated with timestamp"
    },
    {
      "tool": "get_task_context",
      "params": {
        "project_name": "Software-Engineer-AI-Agent-Atlas",
        "task_id": "feature-user-auth"
      },
      "expected": "Returns parent task with subtask progress"
    }
  ]
}
```

### 2. Memory Graph Integration Tests

#### Test 2.1: Entity Creation and Relationship Mapping
```json
{
  "test_id": "memory_integration_001",
  "description": "Create entities and establish relationships",
  "mcp_calls": [
    {
      "tool": "create_memory_entity",
      "params": {
        "name": "AuthenticationSystem",
        "entity_type": "ArchitecturalComponent",
        "observations": [
          "Uses JWT tokens for stateless authentication",
          "Implements OAuth2 authorization code flow",
          "Requires Redis for token blacklisting"
        ],
        "relations": [
          {
            "to_entity": "UserService",
            "relation_type": "depends_on"
          },
          {
            "to_entity": "TokenService", 
            "relation_type": "utilizes"
          }
        ]
      },
      "expected": "Entity created with relationships"
    }
  ]
}
```

#### Test 2.2: Pattern Recognition and Recommendations
```json
{
  "test_id": "pattern_learning_001", 
  "description": "Track patterns and get recommendations",
  "mcp_calls": [
    {
      "tool": "track_command_pattern",
      "params": {
        "command_type": "implement_api_endpoint",
        "target": "/auth/login",
        "parameters": {
          "framework": "FastAPI",
          "authentication": "JWT",
          "validation": "Pydantic"
        },
        "outcome": "success",
        "metrics": {
          "implementation_time": "45m",
          "lines_of_code": 67,
          "test_coverage": 95
        },
        "observations": [
          "Pydantic validation caught edge cases early",
          "JWT implementation was straightforward"
        ]
      },
      "expected": "Pattern recorded for ML training"
    },
    {
      "tool": "get_pattern_recommendations",
      "params": {
        "command_type": "implement_api_endpoint",
        "target": "/auth/logout",
        "context": {
          "framework": "FastAPI",
          "project_type": "authentication"
        }
      },
      "expected": "Recommendations based on previous success"
    }
  ]
}
```

### 3. Workflow Orchestration Tests

#### Test 3.1: Adaptive Command Selection
```json
{
  "test_id": "workflow_adaptive_001",
  "description": "AI-powered command recommendation",
  "mcp_calls": [
    {
      "tool": "adaptive_command_selection",
      "params": {
        "current_context": {
          "project_type": "web_application",
          "phase": "implementation",
          "last_action": "created_database_models",
          "technologies": ["Python", "FastAPI", "PostgreSQL"]
        },
        "user_intent": "Need to implement API endpoints for user management",
        "max_suggestions": 5
      },
      "expected": "Ranked list of recommended next actions"
    }
  ]
}
```

#### Test 3.2: Workflow Enforcement and Validation
```json
{
  "test_id": "workflow_validation_001",
  "description": "Validate command execution readiness",
  "mcp_calls": [
    {
      "tool": "create_workflow",
      "params": {
        "workflow_name": "api_endpoint_implementation",
        "steps": [
          {
            "command": "design_endpoint",
            "target": "user_api",
            "prerequisites": ["database_models_complete"]
          },
          {
            "command": "implement_endpoint",
            "target": "user_api", 
            "prerequisites": ["design_endpoint"]
          },
          {
            "command": "write_tests",
            "target": "user_api",
            "prerequisites": ["implement_endpoint"]
          }
        ]
      },
      "expected": "Workflow created with dependency graph"
    },
    {
      "tool": "validate_command",
      "params": {
        "command": "implement_endpoint",
        "target": "user_api",
        "workflow_context": {
          "current_step": "design_endpoint",
          "completed_steps": []
        }
      },
      "expected": "Validation failure - prerequisites not met"
    }
  ]
}
```

### 4. Convention Validation Tests

#### Test 4.1: File Operation Validation
```json
{
  "test_id": "convention_file_001",
  "description": "Validate file operations against conventions",
  "mcp_calls": [
    {
      "tool": "validate_file_operation",
      "params": {
        "operation": "create",
        "file_path": "/api/users.py",
        "content_preview": "class UserAPI:\\n    def create_user(self):",
        "project_conventions": {
          "naming_style": "snake_case",
          "max_file_size": 500,
          "required_docstrings": true
        }
      },
      "expected": "Validation warnings for missing docstrings"
    }
  ]
}
```

#### Test 4.2: Code Standards Validation  
```json
{
  "test_id": "convention_code_001",
  "description": "Validate code against standards",
  "mcp_calls": [
    {
      "tool": "validate_code_standards",
      "params": {
        "code_snippet": "def process_user_data(userData, apiKey):\\n    return userData.process()",
        "language": "python",
        "standards": {
          "naming_convention": "snake_case",
          "max_line_length": 88,
          "require_type_hints": true
        }
      },
      "expected": "Violations for naming and missing type hints"
    }
  ]
}
```

### 5. Cache Management Tests

#### Test 5.1: Hierarchical Cache Operations
```json
{
  "test_id": "cache_hierarchical_001",
  "description": "Test hierarchical cache with ML model sharing",
  "mcp_calls": [
    {
      "tool": "warm_cache",
      "params": {
        "cache_keys": ["embedding_model_v2", "pattern_classifier"],
        "priority": "high",
        "cache_layer": "global"
      },
      "expected": "ML models loaded into global cache"
    },
    {
      "tool": "get_cache_stats",
      "params": {
        "include_breakdown": true
      },
      "expected": "Cache statistics across all layers"
    }
  ]
}
```

### 6. Observability and Monitoring Tests

#### Test 6.1: Metrics Collection and Health Monitoring
```json
{
  "test_id": "observability_001",
  "description": "Monitor system health and performance",
  "mcp_calls": [
    {
      "tool": "collect_performance_metrics",
      "params": {
        "duration_seconds": 60,
        "include_detailed": true
      },
      "expected": "Performance metrics over time window"
    },
    {
      "tool": "memory_health_check",
      "params": {
        "check_fragmentation": true,
        "check_leaks": true
      },
      "expected": "Memory health assessment"
    }
  ]
}
```

### 7. Embeddings and Semantic Search Tests

#### Test 7.1: Generate and Search Embeddings
```json
{
  "test_id": "embeddings_001",
  "description": "Generate embeddings and perform semantic search",
  "mcp_calls": [
    {
      "tool": "generate_code_embeddings",
      "params": {
        "code_snippets": [
          "def authenticate_user(username, password):",
          "class UserRepository:",
          "async def get_user_by_id(user_id: int):"
        ],
        "model_name": "code-embeddings-v1"
      },
      "expected": "Vector embeddings for code snippets"
    },
    {
      "tool": "semantic_search",
      "params": {
        "query": "user authentication logic",
        "search_space": "code_embeddings",
        "max_results": 5
      },
      "expected": "Ranked similar code snippets"
    }
  ]
}
```

### 8. Integration Workflow Tests

#### Test 8.1: End-to-End Feature Implementation
```json
{
  "test_id": "integration_e2e_001",
  "description": "Complete feature implementation workflow",
  "workflow_steps": [
    {
      "step": 1,
      "tool": "create_hierarchical_task",
      "description": "Create feature task"
    },
    {
      "step": 2, 
      "tool": "adaptive_command_selection",
      "description": "Get implementation recommendations"
    },
    {
      "step": 3,
      "tool": "create_workflow",
      "description": "Define implementation workflow"
    },
    {
      "step": 4,
      "tool": "validate_command",
      "description": "Validate each workflow step"
    },
    {
      "step": 5,
      "tool": "track_command_pattern",
      "description": "Record implementation patterns"
    },
    {
      "step": 6,
      "tool": "update_task_status",
      "description": "Mark task as complete"
    },
    {
      "step": 7,
      "tool": "create_memory_entity",
      "description": "Store implementation knowledge"
    }
  ]
}
```

## Test Execution Plan

### Phase 1: Basic Tool Connectivity (Duration: 30 minutes)
1. Test MCP server initialization
2. Verify all 49 tools are available
3. Test basic parameter validation
4. Confirm response format consistency

### Phase 2: Core Functionality (Duration: 1 hour)
1. Task management operations
2. Memory graph operations  
3. Workflow orchestration
4. Convention validation

### Phase 3: Advanced Features (Duration: 45 minutes)
1. ML-powered recommendations
2. Hierarchical caching
3. Semantic search
4. Performance monitoring

### Phase 4: Integration Scenarios (Duration: 1 hour)
1. End-to-end workflows
2. Error recovery testing
3. Concurrent operation testing
4. Data persistence validation

## Fixing Plan

### Issue Categories and Solutions

#### 1. Connection Issues
**Problem**: MCP server connection failures
**Detection**: Tool calls timeout or return connection errors
**Fix Strategy**:
- Verify Docker container status
- Check MCP protocol version compatibility
- Validate environment variables
- Restart container if needed

#### 2. Parameter Validation Errors
**Problem**: Tools reject valid parameters
**Detection**: "Input validation error" responses
**Fix Strategy**:
- Review tool schemas in mcp.json
- Update parameter formats
- Add missing required fields
- Validate JSON structure

#### 3. Memory Graph Corruption
**Problem**: Entity relationships become inconsistent
**Detection**: Relationship queries return unexpected results
**Fix Strategy**:
- Run memory graph integrity check
- Rebuild corrupted relationships
- Implement backup/restore mechanism
- Add validation triggers

#### 4. Performance Degradation
**Problem**: Tool responses become slow
**Detection**: Response times > 5 seconds
**Fix Strategy**:
- Clear ML model cache
- Restart language models
- Optimize database queries
- Scale cache layers

#### 5. Storage Persistence Issues  
**Problem**: Task data not persisting between sessions
**Detection**: Previously created tasks disappear
**Fix Strategy**:
- Verify volume mounts in Docker
- Check file permissions
- Validate storage path configuration
- Implement data recovery procedures

### Automated Fix Procedures

#### Quick Fix Script
```bash
#!/bin/bash
# atlas-mcp-quick-fix.sh

echo "ATLAS MCP Quick Fix Procedure"

# 1. Check container health
if ! docker ps | grep -q "atlas-commands-mcp.*healthy"; then
    echo "Restarting ATLAS container..."
    docker-compose restart atlas-commands
    sleep 10
fi

# 2. Clear caches if performance issues
echo "Clearing caches..."
docker exec atlas-commands-mcp python -c "
from atlas_commands.caching.cache_manager import CacheManager
CacheManager.clear_all_cache()
"

# 3. Validate storage permissions
echo "Checking storage permissions..."
docker exec atlas-commands-mcp ls -la /app/REPOS

# 4. Test basic connectivity
echo "Testing MCP connectivity..."
python mcp-client-working.py test

echo "Quick fix completed"
```

### Test Automation Framework

#### Test Runner Configuration
```python
# test_runner.py
class AtlasMcpTestRunner:
    def __init__(self):
        self.client = AtlasMcpClient()
        self.results = []
        
    def run_test_suite(self, test_categories=None):
        """Run specified test categories or all tests."""
        for test in self.load_tests(test_categories):
            result = self.execute_test(test)
            self.results.append(result)
            if result.failed:
                self.apply_fixes(result)
                
    def apply_fixes(self, failed_result):
        """Apply automated fixes based on failure type."""
        if "connection" in failed_result.error.lower():
            self.fix_connection_issues()
        elif "validation" in failed_result.error.lower():
            self.fix_validation_issues()
        # Add more fix patterns...
```

## Success Criteria

### Minimum Viable Integration
- [ ] All 49 tools callable from Claude Code
- [ ] Basic task creation and management works
- [ ] Memory graph operations functional
- [ ] No data loss between sessions

### Full Feature Integration  
- [ ] All test categories pass
- [ ] Performance within acceptable limits (<3s per tool call)
- [ ] Error recovery mechanisms work
- [ ] Integration workflows complete successfully
- [ ] ML recommendations provide value

### Production Readiness
- [ ] Stress testing with concurrent operations
- [ ] Data backup and recovery verified
- [ ] Monitoring and alerting functional
- [ ] Documentation complete and accurate

---

*This test suite ensures comprehensive validation of ATLAS MCP integration with concrete interaction scenarios and systematic fixing procedures.*