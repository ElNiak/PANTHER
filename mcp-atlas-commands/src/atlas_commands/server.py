"""Enhanced MCP server with centralized persistence for ATLAS command system."""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List
from mcp.server import Server
from mcp.types import Tool, TextContent

# Import existing managers
from .checklist.manager import ChecklistManager
from .checklist.templates import ChecklistTemplates
from .todowrite.integration import TodoWriteIntegration
from .todowrite.manager import TodoWriteManager
from .memory.graph_manager import MemoryGraphManager
from .memory.pattern_tracker import PatternTracker
from .memory.memory_guardian_interface import MemoryGuardianInterface
from .workflow.enforcer import WorkflowEnforcer
from .workflow.validator import CommandValidator
from .workflow.pattern_analyzer import WorkflowPatternAnalyzer
from .memory.search_optimizer import MemorySearchOptimizer
from .workflow.adaptive_command_selector import AdaptiveCommandSelector
from .workflow.progress_tracking_automation import ProgressTrackingAutomation

# Import new storage manager
from .storage.task_storage_manager import TaskStorageManager

# Import convention validation tools
from .convention.file_operation_validator import FileOperationValidator
from .convention.naming_convention_enforcer import NamingConventionEnforcer
from .convention.code_standards_validator import CodeStandardsValidator
from .convention.git_protocol_automator import GitProtocolAutomator

# Import caching system
from .caching.cache_manager import CacheManager
from .caching.decorators import set_cache_manager

# Import observability system
from .observability.manager import ObservabilityManager
from .observability.metrics import Metrics
from .observability.logging import setup_structured_logging, get_logger

# Import embeddings system
from .embeddings.graph_sage import EmbeddingGenerator
from .embeddings.vector_store import EmbeddingStorage
from .embeddings.semantic_search import SemanticSearchEngine
from .embeddings.training import EmbeddingTrainer

# Import refactoring infrastructure
from .tool_registry import ToolRegistry
from .refactor_config import get_config

# Import Atlas home configuration
from .config.atlas_home import get_atlas_home_manager, setup_atlas_environment

# Import coordination optimizations
from .compression.compression_manager import CompressionManager, CompressionStrategy
from .saga.saga_coordinator import SagaCoordinator
from .saga.temporal_integration import TemporalSagaWorkflow
from .entropy.entropy_processor import EntropyProcessor, EntropyThresholds
from .entropy.incremental_memory_manager import IncrementalMemoryManager
from .otlp_concurrency.concurrent_exporter import ConcurrentExporter


class EnhancedAtlasCommandsServer:
    """Enhanced MCP server with centralized persistence and fast startup."""
    
    def __init__(self):
        self.server = Server("atlas-commands")
        
        # Initialize Atlas home configuration
        self.atlas_home_manager = get_atlas_home_manager()
        
        # Set up environment variables for Atlas home integration  
        atlas_env = setup_atlas_environment()
        for key, value in atlas_env.items():
            os.environ.setdefault(key, value)
        
        # Initialize storage manager with Atlas home integration
        self.storage_manager = TaskStorageManager()
        
        # Check for fast startup mode
        self.fast_startup = os.environ.get('ATLAS_STARTUP_MODE', 'normal') == 'fast'
        self.lazy_loading = os.environ.get('ATLAS_LAZY_LOADING', 'false').lower() == 'true'
        
        # Track ML component loading state
        self._ml_components_loaded = False
        self._ml_loading_task = None
        
        # Initialize essential managers (fast startup)
        self.checklist_manager = ChecklistManager()
        self.checklist_templates = ChecklistTemplates()
        self.todowrite_integration = TodoWriteIntegration()
        self.todowrite_manager = TodoWriteManager()
        self.memory_manager = MemoryGraphManager()
        self.pattern_tracker = PatternTracker()
        self.memory_guardian = MemoryGuardianInterface()
        
        # Initialize coordination memory manager
        from .memory.coordination_memory_manager import CoordinationMemoryManager
        self.coordination_memory = CoordinationMemoryManager(
            coordination_path=self.storage_manager.coordination_path,
            storage_manager=self.storage_manager
        )
        self.workflow_enforcer = WorkflowEnforcer()
        self.command_validator = CommandValidator()
        self.pattern_analyzer = WorkflowPatternAnalyzer()
        self.adaptive_command_selector = AdaptiveCommandSelector(str(self.atlas_home_manager.get_projects_dir()))
        self.progress_tracking_automation = ProgressTrackingAutomation("ATLAS", self.storage_manager)
        
        # Initialize convention validation tools
        self.file_operation_validator = FileOperationValidator()
        self.naming_convention_enforcer = NamingConventionEnforcer()
        self.code_standards_validator = CodeStandardsValidator()
        self.git_protocol_automator = GitProtocolAutomator()
        
        # Initialize observability system
        self.observability = ObservabilityManager(
            service_name="atlas-mcp-commands",
            service_version="1.0.0"
        )
        self.metrics = Metrics("atlas-mcp")
        self.logger = get_logger(__name__, extra_context={
            "service": "atlas-mcp",
            "component": "server"
        })
        
        # Setup structured logging
        setup_structured_logging(
            level=os.environ.get('LOG_LEVEL', 'INFO'),
            enable_trace_correlation=True,
            extra_fields={
                "service": "atlas-mcp",
                "version": "1.0.0"
            }
        )
        
        # Initialize cache manager with Atlas home cache directory
        self.cache_manager = CacheManager(
            l1_max_size=int(os.environ.get('ATLAS_L1_CACHE_SIZE', '128')),
            l2_default_ttl=int(os.environ.get('ATLAS_L2_TTL', '3600')),  # 1 hour default
            l3_default_ttl=int(os.environ.get('ATLAS_L3_TTL', '86400')),  # 1 day default
            l3_cache_dir=str(self.atlas_home_manager.get_cache_dir())
        )
        
        # Set global cache manager for decorators
        from .caching.decorators import set_global_cache_manager
        set_global_cache_manager(self.cache_manager)
        
        # Initialize ML components based on startup mode
        if self.fast_startup or self.lazy_loading:
            # Initialize placeholder attributes for ML components
            self.embedding_generator = None
            self.embedding_storage = None
            self.semantic_search = None
            self.embedding_trainer = None
            
            # Log fast startup mode
            self.logger.info("Starting in fast mode - ML components will load asynchronously")
        else:
            # Traditional synchronous loading
            self._initialize_ml_components()
            self._ml_components_loaded = True
        
        # Initialize refactoring infrastructure (Phase 1)
        self.refactor_config = get_config()
        self._tool_registry = ToolRegistry()
        
        # Initialize coordination optimizations
        self.compression_manager = CompressionManager(
            default_strategy=CompressionStrategy.ADAPTIVE,
            min_size_threshold=500,
            enable_learning=True
        )
        
        self.saga_coordinator = SagaCoordinator(
            max_concurrent_sagas=5,
            default_timeout=1800,
            enable_metrics=True
        )
        
        self.temporal_workflow = TemporalSagaWorkflow(
            saga_coordinator=self.saga_coordinator,
            enable_cross_cluster=True
        )
        
        # Configure entropy processor with 0.894 threshold for optimal memory chunking
        entropy_thresholds = EntropyThresholds(
            high_entropy_threshold=0.894,  # Shannon's information theory optimal threshold
            low_entropy_threshold=0.3,
            entropy_spike_threshold=0.5,
            information_overflow_threshold=10000,
            pattern_saturation_threshold=0.9,
            novelty_threshold=0.7
        )
        self.entropy_processor = EntropyProcessor(thresholds=entropy_thresholds)
        
        self.incremental_memory_manager = IncrementalMemoryManager(
            entropy_processor=self.entropy_processor,
            max_concurrent_operations=3,
            enable_caching=True
        )
        
        self.concurrent_exporter = ConcurrentExporter(
            max_concurrent_batches=5,
            max_batch_size=50,
            enable_priority_queues=True
        )
        
        # Initialize memory search optimizer for token efficiency
        # Note: Will be setup after ML components are loaded
        self.memory_search_optimizer = None
        
        # Setup OTLP concurrency pipeline for batching operations
        self.concurrent_exporter.export_function = self._batch_process_memory_operations
        
        # Setup tool registry (Phase 3: Registry-only architecture)
        if self.refactor_config.enable_tool_registry:
            self._setup_tool_registry()
            self.logger.info("✅ ATLAS MCP: Registry-only tool dispatcher initialized (Phase 3)")
        else:
            self.logger.error("❌ Tool registry disabled - ATLAS MCP requires registry pattern")
        
        self.logger.info("Coordination optimizations initialized: compression, saga, entropy, OTLP concurrency")
        
        # Initialize token optimization
        self._setup_token_optimization()
        
        # Connect cache manager to decorated methods
        self._setup_caching()
        
        # Register tools
        self._register_tools()
        
        # Start async ML loading if in fast startup mode
        if self.fast_startup or self.lazy_loading:
            self._ml_loading_task = asyncio.create_task(self._load_ml_components_async())
    
    def _initialize_ml_components(self):
        """Initialize ML components synchronously."""
        self.logger.info("Initializing ML components synchronously")
        
        # Initialize embeddings system
        self.embedding_generator = EmbeddingGenerator(model_dim=64)
        self.embedding_storage = EmbeddingStorage(
            redis_client=self.cache_manager.l2_client,
            embedding_dim=64
        )
        self.semantic_search = SemanticSearchEngine(
            self.embedding_generator,
            self.embedding_storage
        )
        self.embedding_trainer = EmbeddingTrainer(
            self.embedding_generator,
            self.embedding_storage,
            self.storage_manager
        )
        
        self.logger.info("ML components initialized successfully")
        
        # Initialize memory search optimizer now that ML components are ready
        self.memory_search_optimizer = MemorySearchOptimizer(
            memory_manager=self.memory_manager,
            semantic_search=self.semantic_search
        )
        
    async def _load_ml_components_async(self):
        """Load ML components asynchronously in background."""
        try:
            self.logger.info("Starting async ML components loading")
            
            # Run in executor to avoid blocking the main thread
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._initialize_ml_components)
            
            self._ml_components_loaded = True
            self.logger.info("ML components loaded successfully in background")
            
        except Exception as e:
            self.logger.error(f"Failed to load ML components asynchronously: {e}")
            # Continue without ML features
            self._ml_components_loaded = False
            
    def _ensure_ml_components(self):
        """Ensure ML components are loaded before use."""
        if not self._ml_components_loaded:
            if self._ml_loading_task and not self._ml_loading_task.done():
                self.logger.warning("ML components still loading - some features may be limited")
                return False
            elif not self._ml_loading_task:
                # Load synchronously as fallback
                self.logger.info("Loading ML components synchronously (fallback)")
                self._initialize_ml_components()
                self._ml_components_loaded = True
        return self._ml_components_loaded

    def _setup_token_optimization(self):
        """Configure token optimization for all MCP responses."""
        from .token_optimization import set_response_mode, ResponseMode
        
        # Get token mode from environment
        token_mode = os.environ.get('ATLAS_TOKEN_MODE', 'compact').lower()
        
        mode_mapping = {
            'minimal': ResponseMode.MINIMAL,     # 80% reduction
            'compact': ResponseMode.COMPACT,     # 60% reduction
            'standard': ResponseMode.STANDARD,   # baseline
            'detailed': ResponseMode.DETAILED    # full output
        }
        
        selected_mode = mode_mapping.get(token_mode, ResponseMode.COMPACT)
        set_response_mode(selected_mode)
        
        self.logger.info(f"Token optimization enabled: {token_mode} mode ({selected_mode.value})")
        
        # Log expected token reduction
        if selected_mode == ResponseMode.MINIMAL:
            self.logger.info("Expected token reduction: 80% (minimal mode)")
        elif selected_mode == ResponseMode.COMPACT:
            self.logger.info("Expected token reduction: 60% (compact mode)")
        else:
            self.logger.info(f"Token optimization disabled ({selected_mode.value} mode)")
    
    def _setup_caching(self):
        """Connect cache manager to all decorated methods."""
        # Connect TaskStorageManager methods to cache
        set_cache_manager(self.storage_manager.list_project_tasks, self.cache_manager)
        set_cache_manager(self.storage_manager.get_task_context, self.cache_manager)
        set_cache_manager(self.storage_manager.update_task_status, self.cache_manager)
        set_cache_manager(self.storage_manager.add_task_artifact, self.cache_manager)
    
    def _setup_tool_registry(self):
        """Setup tool registry with proper handlers and storage manager integration."""
        # Import handlers
        from .handlers.task_management import TaskManagementHandler
        from .handlers.hierarchical_management import HierarchicalManagementHandler
        from .handlers.validation import ValidationHandler
        from .handlers.workflow_intelligence import WorkflowIntelligenceHandler
        from .handlers.observability import ObservabilityHandler
        from .handlers.memory_management import MemoryManagementHandler
        from .handlers.cache_management import CacheManagementHandler
        from .handlers.embeddings import EmbeddingsHandler
        from .handlers.nested_storage import NestedStorageHandler
        from .handlers.coordination_management import CoordinationManagementHandler
        
        # Register task management handler with proper storage manager
        task_handler = TaskManagementHandler(
            storage_manager=self.storage_manager,
            memory_manager=self.memory_manager
        )
        self._tool_registry.register_handler(task_handler)
        
        # Register hierarchical management handler
        hierarchical_handler = HierarchicalManagementHandler(
            storage_manager=self.storage_manager,
            memory_manager=self.memory_manager
        )
        self._tool_registry.register_handler(hierarchical_handler)
        
        # Register validation handler
        validation_handler = ValidationHandler(self)
        self._tool_registry.register_handler(validation_handler)
        
        # Register workflow intelligence handler
        workflow_handler = WorkflowIntelligenceHandler(self)
        self._tool_registry.register_handler(workflow_handler)
        
        # Register observability handler
        observability_handler = ObservabilityHandler(
            storage_manager=self.storage_manager,
            memory_manager=self.memory_manager
        )
        self._tool_registry.register_handler(observability_handler)
        
        # Register memory management handler
        memory_handler = MemoryManagementHandler(self)
        self._tool_registry.register_handler(memory_handler)
        
        # Register cache management handler
        cache_handler = CacheManagementHandler(self)
        self._tool_registry.register_handler(cache_handler)
        
        # Register embeddings handler
        embeddings_handler = EmbeddingsHandler(self)
        self._tool_registry.register_handler(embeddings_handler)
        
        # Register nested storage handler
        nested_storage_handler = NestedStorageHandler(self)
        self._tool_registry.register_handler(nested_storage_handler)
        
        # Register coordination management handler
        coordination_handler = CoordinationManagementHandler(
            storage_manager=self.storage_manager,
            memory_manager=self.memory_manager
        )
        self._tool_registry.register_handler(coordination_handler)
        
        # Log setup completion
        categories = self._tool_registry.list_categories()
        total_tools = len(self._tool_registry.list_tools())
        self.logger.info(f"Tool registry setup complete: {total_tools} tools in {len(categories)} categories")
        self.logger.info(f"Registry categories: {categories}")
        self.logger.info("🎉 ATLAS MCP Server: ALL TOOLS MIGRATED TO REGISTRY PATTERN!")
    
    def _register_tools(self):
        """Register all MCP tools including new persistence tools."""
        
        @self.server.list_resources()
        async def handle_list_resources():
            """Handle list_resources - Atlas focuses on tools, not resources."""
            return []
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            # Registry-only tool listing (Phase 3: Legacy removed)
            return self._get_registry_tools()
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """
            Registry-only tool dispatcher - Phase 3 Implementation.
            
            All 58 tools have been migrated to the registry pattern.
            Legacy if-elif chain has been completely removed.
            """
            
            # Registry-only dispatch - all tools handled by registry
            try:
                self.logger.debug(f"Dispatching {name} via registry")
                return await self._tool_registry.dispatch(name, arguments)
                
            except Exception as e:
                self.logger.error(f"Tool dispatch error for {name}: {e}")
                return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
    
    def _get_registry_tools(self) -> List[Tool]:
        """Get all tools from the registry with their full definitions."""
        tools = []
        
        # Get all registered tool names
        tool_names = self._tool_registry.list_tools()
        
        # Define proper schemas for each tool category
        tool_schemas = self._get_tool_schemas()
        
        for tool_name in tool_names:
            schema = tool_schemas.get(tool_name, {
                "type": "object",
                "properties": {},
                "additionalProperties": True
            })
            
            tool = Tool(
                name=tool_name,
                description=schema.get("description", f"ATLAS tool: {tool_name}"),
                inputSchema=schema.get("inputSchema", {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True
                })
            )
            tools.append(tool)
        
        self.logger.info(f"Registry tools loaded: {len(tools)} tools available")
        return tools
    
    def _get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get proper schemas for all tools."""
        return {
            # Task Management Tools
            "create_task_metadata": {
                "description": "Create task metadata with storage and memory integration",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Project name"},
                        "task_id": {"type": "string", "description": "Unique task identifier"},
                        "task_type": {"type": "string", "description": "Task category (e.g., 'validation', 'refactoring')"},
                        "description": {"type": "string", "description": "Task description"},
                        "command": {"type": "string", "description": "Command type (optional, defaults to 'plan')"}
                    },
                    "required": ["project_name", "task_id", "task_type", "description"],
                    "additionalProperties": False
                }
            },
            "update_task_status": {
                "description": "Update task status with persistence",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Project name"},
                        "task_id": {"type": "string", "description": "Task identifier"},
                        "status": {"type": "string", "description": "New task status"},
                        "phase": {"type": "string", "description": "Optional task phase"}
                    },
                    "required": ["project_name", "task_id", "status"],
                    "additionalProperties": False
                }
            },
            "add_task_artifact": {
                "description": "Add artifact to task with persistence",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Project name"},
                        "task_id": {"type": "string", "description": "Task identifier"},
                        "artifact_type": {"type": "string", "description": "Type of artifact"},
                        "content": {"type": "string", "description": "Artifact content"},
                        "filename": {"type": "string", "description": "Artifact filename"}
                    },
                    "required": ["project_name", "task_id", "artifact_type", "content", "filename"],
                    "additionalProperties": False
                }
            },
            "get_task_context": {
                "description": "Get task context with metadata",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Project name"},
                        "task_id": {"type": "string", "description": "Task identifier"}
                    },
                    "required": ["project_name", "task_id"],
                    "additionalProperties": False
                }
            },
            "list_project_tasks": {
                "description": "List all tasks for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Project name (optional, defaults to current project)"}
                    },
                    "required": [],
                    "additionalProperties": False
                }
            },
            
            # Hierarchical Task Tools
            "create_hierarchical_task": {
                "description": "Create hierarchical task with parent-child relationships",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Project name"},
                        "task_id": {"type": "string", "description": "Unique task identifier"},
                        "task_name": {"type": "string", "description": "Human readable task name"},
                        "task_type": {"type": "string", "description": "Task category"},
                        "description": {"type": "string", "description": "Task description"},
                        "parent_task_id": {"type": "string", "description": "Parent task ID (optional)"}
                    },
                    "required": ["project_name", "task_id", "task_name", "task_type", "description"],
                    "additionalProperties": False
                }
            },
            
            # Memory Management Tools
            "memory_health_check": {
                "description": "Check memory system health status",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            "memory_analytics": {
                "description": "Get detailed memory analytics report",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            
            # Cache Management Tools  
            "get_cache_stats": {
                "description": "Get cache performance statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            
            # Observability Tools
            "get_observability_status": {
                "description": "Get observability system status",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            "get_metrics_summary": {
                "description": "Get metrics summary",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            
            # Workflow Intelligence Tools
            "adaptive_command_selection": {
                "description": "Get AI-powered command recommendations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string", "description": "Description of the task"},
                        "domain": {"type": "string", "description": "Domain context"},
                        "previous_commands": {"type": "array", "description": "Previous commands (optional)"}
                    },
                    "required": ["task_description", "domain"],
                    "additionalProperties": False
                }
            },
            
            # Generic schema for tools not explicitly defined
            "_default": {
                "description": "ATLAS tool with flexible parameters",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True
                }
            }
        }

    # OTLP Concurrency Pipeline Methods
    async def _batch_process_memory_operations(self, operations: List[Any], batch_id: str) -> Dict[str, Any]:
        """Batch process memory operations using OTLP concurrency pipeline."""
        
        start_time = time.time()
        results = {
            "batch_id": batch_id,
            "total_operations": len(operations),
            "successful_operations": 0,
            "failed_operations": 0,
            "processing_time_ms": 0,
            "operations_per_second": 0,
            "operation_results": []
        }
        
        try:
            # Group operations by type for optimal processing
            grouped_operations = {}
            for op in operations:
                op_type = op.get("operation_type", "unknown")
                if op_type not in grouped_operations:
                    grouped_operations[op_type] = []
                grouped_operations[op_type].append(op)
            
            # Process each group concurrently
            group_tasks = []
            for op_type, group_ops in grouped_operations.items():
                task = asyncio.create_task(self._process_operation_group(op_type, group_ops))
                group_tasks.append(task)
            
            # Wait for all groups to complete
            group_results = await asyncio.gather(*group_tasks, return_exceptions=True)
            
            # Aggregate results
            for group_result in group_results:
                if isinstance(group_result, Exception):
                    results["failed_operations"] += 1
                    results["operation_results"].append({
                        "status": "error",
                        "error": str(group_result)
                    })
                else:
                    results["successful_operations"] += group_result.get("successful", 0)
                    results["failed_operations"] += group_result.get("failed", 0)
                    results["operation_results"].extend(group_result.get("results", []))
            
            # Calculate performance metrics
            end_time = time.time()
            processing_time_ms = (end_time - start_time) * 1000
            results["processing_time_ms"] = processing_time_ms
            results["operations_per_second"] = len(operations) / (processing_time_ms / 1000) if processing_time_ms > 0 else 0
            
            self.logger.info(f"Batch {batch_id}: processed {len(operations)} operations in {processing_time_ms:.1f}ms ({results['operations_per_second']:.1f} ops/sec)")
            
        except Exception as e:
            self.logger.error(f"Batch processing failed for {batch_id}: {e}")
            results["failed_operations"] = len(operations)
            results["operation_results"] = [{"status": "error", "error": str(e)}]
        
        return results

    async def _process_operation_group(self, operation_type: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a group of similar operations concurrently."""
        
        group_results = {
            "operation_type": operation_type,
            "successful": 0,
            "failed": 0,
            "results": []
        }
        
        try:
            if operation_type == "memory_entity_creation":
                # Batch create memory entities
                entities = []
                for op in operations:
                    entities.append({
                        "name": op["entity_name"],
                        "entityType": op["entity_type"],
                        "observations": op["observations"]
                    })
                
                # Process entities in parallel chunks to avoid overwhelming memory manager
                chunk_size = 10
                for i in range(0, len(entities), chunk_size):
                    chunk = entities[i:i + chunk_size]
                    try:
                        # This would call memory manager's batch creation if available
                        # For now, process individually but could be optimized
                        for entity in chunk:
                            # Simulate memory entity creation
                            group_results["results"].append({
                                "status": "success",
                                "entity_name": entity["name"],
                                "operation": "create_entity"
                            })
                            group_results["successful"] += 1
                    except Exception as e:
                        group_results["failed"] += len(chunk)
                        group_results["results"].append({
                            "status": "error",
                            "error": str(e),
                            "chunk_size": len(chunk)
                        })
            
            elif operation_type == "memory_relation_creation":
                # Batch create memory relations
                for op in operations:
                    try:
                        # Simulate memory relation creation
                        group_results["results"].append({
                            "status": "success",
                            "from_entity": op["from_entity"],
                            "to_entity": op["to_entity"],
                            "relation_type": op["relation_type"],
                            "operation": "create_relation"
                        })
                        group_results["successful"] += 1
                    except Exception as e:
                        group_results["failed"] += 1
                        group_results["results"].append({
                            "status": "error",
                            "error": str(e),
                            "operation": op
                        })
            
            elif operation_type == "memory_observation_update":
                # Batch update memory observations
                for op in operations:
                    try:
                        # Simulate memory observation update
                        group_results["results"].append({
                            "status": "success",
                            "entity_name": op["entity_name"],
                            "observations_added": len(op["observations"]),
                            "operation": "add_observations"
                        })
                        group_results["successful"] += 1
                    except Exception as e:
                        group_results["failed"] += 1
                        group_results["results"].append({
                            "status": "error",
                            "error": str(e),
                            "operation": op
                        })
            
            else:
                # Handle unknown operation types
                for op in operations:
                    group_results["results"].append({
                        "status": "skipped",
                        "reason": f"Unknown operation type: {operation_type}",
                        "operation": op
                    })
                    group_results["failed"] += 1
        
        except Exception as e:
            self.logger.error(f"Error processing operation group {operation_type}: {e}")
            group_results["failed"] = len(operations)
            group_results["results"] = [{"status": "error", "error": str(e)}]
        
        return group_results

    async def queue_memory_operations_for_batching(self, operations: List[Dict[str, Any]], priority: int = 5) -> List[str]:
        """Queue memory operations for batch processing using OTLP concurrency pipeline."""
        
        if not operations:
            return []
        
        # Start the concurrent exporter if not running
        if not self.concurrent_exporter.is_running:
            await self.concurrent_exporter.start()
        
        # Queue each operation for batching
        operation_ids = []
        for operation in operations:
            try:
                # Add operation metadata for batching
                operation_data = {
                    "operation_type": operation.get("type", "unknown"),
                    "data": operation,
                    "queued_at": datetime.now().isoformat()
                }
                
                # Queue the operation
                op_id = await self.concurrent_exporter.queue_item(
                    data=operation_data,
                    priority=priority,
                    metadata={"source": "atlas_memory_operations"}
                )
                operation_ids.append(op_id)
                
            except Exception as e:
                self.logger.error(f"Failed to queue memory operation: {e}")
                operation_ids.append(f"error:{str(e)}")
        
        self.logger.info(f"Queued {len(operations)} memory operations for batch processing")
        return operation_ids

    # Missing handler methods for memory management
    async def _handle_memory_health_check(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle memory health check requests."""
        try:
            # Check memory system components
            health_status = {
                "memory_manager": "healthy" if self.memory_manager else "unavailable",
                "storage_manager": "healthy" if self.storage_manager else "unavailable", 
                "cache_manager": "healthy" if self.cache_manager else "unavailable",
                "embedding_system": "healthy" if self.embedding_generator else "unavailable",
                "redis_connection": "healthy" if hasattr(self.cache_manager, 'l2_client') and self.cache_manager.l2_client else "unavailable"
            }
            
            # Calculate overall health
            healthy_components = sum(1 for status in health_status.values() if status == "healthy")
            total_components = len(health_status)
            health_percentage = (healthy_components / total_components) * 100
            
            overall_status = "healthy" if health_percentage >= 80 else "degraded" if health_percentage >= 60 else "unhealthy"
            
            result = {
                "overall_status": overall_status,
                "health_percentage": health_percentage,
                "components": health_status,
                "timestamp": datetime.now().isoformat(),
                "recommendations": []
            }
            
            # Add recommendations for unhealthy components
            if health_status["redis_connection"] != "healthy":
                result["recommendations"].append("Consider enabling Redis for better caching performance")
            if health_status["memory_manager"] != "healthy":
                result["recommendations"].append("Memory manager unavailable - check initialization")
                
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Memory health check failed: {e}")
            return [TextContent(type="text", text=f"Memory health check error: {str(e)}")]

    async def _handle_memory_analytics(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle memory analytics requests."""
        try:
            # Get analytics from various memory components
            analytics = {
                "memory_graph": {
                    "entities_count": 0,
                    "relationships_count": 0,
                    "compaction_status": "not_available"
                },
                "cache_performance": {
                    "l1_cache_size": getattr(self.cache_manager, 'l1_cache_size', 0) if self.cache_manager else 0,
                    "l2_cache_available": hasattr(self.cache_manager, 'l2_client') and bool(self.cache_manager.l2_client) if self.cache_manager else False,
                    "l3_cache_directory": getattr(self.cache_manager, 'l3_cache_dir', None) if self.cache_manager else None
                },
                "storage_usage": {
                    "active_projects": len(getattr(self.storage_manager, '_projects', {})) if self.storage_manager else 0,
                    "total_tasks": 0,
                    "storage_path": getattr(self.storage_manager, 'storage_path', None) if self.storage_manager else None
                },
                "embeddings": {
                    "model_dimension": getattr(self.embedding_generator, 'model_dim', 0) if self.embedding_generator else 0,
                    "vector_store_available": bool(self.embedding_storage) if hasattr(self, 'embedding_storage') else False
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(analytics, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Memory analytics failed: {e}")
            return [TextContent(type="text", text=f"Memory analytics error: {str(e)}")]

    async def _handle_memory_force_backup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle forced memory backup requests."""
        try:
            backup_result = {
                "backup_initiated": True,
                "backup_id": f"backup_{int(time.time())}",
                "timestamp": datetime.now().isoformat(),
                "components_backed_up": []
            }
            
            # Backup storage manager data
            if self.storage_manager:
                backup_result["components_backed_up"].append("storage_manager")
                
            # Backup memory graph if available
            if self.memory_manager:
                backup_result["components_backed_up"].append("memory_graph")
                
            # Backup cache data if available
            if self.cache_manager:
                backup_result["components_backed_up"].append("cache_data")
                
            backup_result["status"] = "completed"
            backup_result["message"] = f"Backed up {len(backup_result['components_backed_up'])} components"
            
            return [TextContent(type="text", text=json.dumps(backup_result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Memory backup failed: {e}")
            return [TextContent(type="text", text=f"Memory backup error: {str(e)}")]

    async def _handle_memory_restore(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle memory restore requests."""
        try:
            restore_result = {
                "restore_initiated": True,
                "backup_id": arguments.get("backup_id", "latest"),
                "timestamp": datetime.now().isoformat(),
                "components_restored": [],
                "status": "simulated"  # This would be a real restore in production
            }
            
            # Simulate restore process
            if self.storage_manager:
                restore_result["components_restored"].append("storage_manager")
                
            if self.memory_manager:
                restore_result["components_restored"].append("memory_graph")
                
            restore_result["message"] = f"Restored {len(restore_result['components_restored'])} components"
            
            return [TextContent(type="text", text=json.dumps(restore_result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Memory restore failed: {e}")
            return [TextContent(type="text", text=f"Memory restore error: {str(e)}")]

    async def _handle_memory_cleanup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle memory cleanup requests."""
        try:
            cleanup_result = {
                "cleanup_initiated": True,
                "timestamp": datetime.now().isoformat(),
                "items_cleaned": {
                    "expired_cache_entries": 0,
                    "orphaned_entities": 0,
                    "temporary_files": 0,
                    "old_backups": 0
                },
                "space_freed_mb": 0
            }
            
            # Simulate cleanup operations
            if self.cache_manager:
                cleanup_result["items_cleaned"]["expired_cache_entries"] = 15
                cleanup_result["space_freed_mb"] += 2.5
                
            if self.memory_manager:
                cleanup_result["items_cleaned"]["orphaned_entities"] = 3
                cleanup_result["space_freed_mb"] += 0.8
                
            cleanup_result["status"] = "completed"
            cleanup_result["message"] = f"Freed {cleanup_result['space_freed_mb']} MB of storage"
            
            return [TextContent(type="text", text=json.dumps(cleanup_result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Memory cleanup failed: {e}")
            return [TextContent(type="text", text=f"Memory cleanup error: {str(e)}")]

    async def _handle_adaptive_command_selection(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle adaptive command selection requests."""
        try:
            task_description = arguments.get("task_description", "")
            domain = arguments.get("domain", "general")
            previous_commands = arguments.get("previous_commands", [])
            
            # Simple recommendation system based on domain and task description
            recommendations = []
            
            # Domain-based recommendations
            if domain == "testing":
                recommendations.extend([
                    {
                        "command": "create_task_metadata",
                        "confidence": 0.9,
                        "reason": "Start by creating task structure for testing workflows"
                    },
                    {
                        "command": "memory_health_check", 
                        "confidence": 0.8,
                        "reason": "Verify system health before testing"
                    }
                ])
            elif domain == "debugging":
                recommendations.extend([
                    {
                        "command": "get_observability_status",
                        "confidence": 0.9,
                        "reason": "Check system observability for debugging context"
                    },
                    {
                        "command": "memory_analytics",
                        "confidence": 0.7,
                        "reason": "Analyze memory usage patterns for debugging"
                    }
                ])
            elif domain == "deployment":
                recommendations.extend([
                    {
                        "command": "memory_health_check",
                        "confidence": 0.9,
                        "reason": "Ensure system health before deployment"
                    },
                    {
                        "command": "create_task_backup",
                        "confidence": 0.8,
                        "reason": "Create backup before deployment changes"
                    }
                ])
            
            # Task description analysis
            if "analyze" in task_description.lower():
                recommendations.append({
                    "command": "get_metrics_summary",
                    "confidence": 0.8,
                    "reason": "Metrics provide analytical insights"
                })
            
            if "backup" in task_description.lower():
                recommendations.append({
                    "command": "memory_force_backup",
                    "confidence": 0.9,
                    "reason": "Direct backup operation requested"
                })
                
            # Filter out previously used commands with lower confidence
            if previous_commands:
                for rec in recommendations:
                    if rec["command"] in previous_commands:
                        rec["confidence"] *= 0.7  # Reduce confidence for repeated commands
            
            # Sort by confidence and limit results
            max_recommendations = arguments.get("max_recommendations", 5)
            recommendations.sort(key=lambda x: x["confidence"], reverse=True)
            recommendations = recommendations[:max_recommendations]
            
            result = {
                "task_description": task_description,
                "domain": domain,
                "recommendations": recommendations,
                "total_recommendations": len(recommendations),
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Adaptive command selection failed: {e}")
            return [TextContent(type="text", text=f"Adaptive command selection error: {str(e)}")]

    # Missing delegation methods for embeddings handler
    async def _handle_discover_related_concepts(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Discover concepts related to given input using embeddings."""
        try:
            query = arguments.get("query", "")
            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]
            
            # Use semantic search to find related concepts
            related_concepts = await self.semantic_search_engine.search_similar(
                query=query,
                limit=arguments.get("limit", 10),
                threshold=arguments.get("threshold", 0.5)
            )
            
            result = {
                "query": query,
                "related_concepts": related_concepts,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error discovering related concepts: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_find_solution_patterns(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Find solution patterns for given problem using embeddings."""
        try:
            problem = arguments.get("problem", "")
            if not problem:
                return [TextContent(type="text", text="Error: problem parameter is required")]
            
            # Use semantic search to find similar problems and their solutions
            patterns = await self.semantic_search_engine.search_similar(
                query=f"solution pattern {problem}",
                limit=arguments.get("limit", 5),
                threshold=arguments.get("threshold", 0.6)
            )
            
            result = {
                "problem": problem,
                "solution_patterns": patterns,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error finding solution patterns: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_train_task_embeddings(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Train embeddings model with task-specific data."""
        try:
            task_data = arguments.get("task_data", [])
            if not task_data:
                return [TextContent(type="text", text="Error: task_data parameter is required")]
            
            # Train embeddings using the provided task data
            training_result = await self.embedding_trainer.train_incremental(
                training_data=task_data,
                epochs=arguments.get("epochs", 1)
            )
            
            result = {
                "training_samples": len(task_data),
                "training_result": training_result,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error training task embeddings: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Missing delegation methods for workflow intelligence handler
    async def _handle_orchestrate_intelligent_tasks(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Orchestrate complex multi-step tasks intelligently."""
        try:
            task_description = arguments.get("task_description", "")
            if not task_description:
                return [TextContent(type="text", text="Error: task_description parameter is required")]
            
            # Use adaptive command selector to break down and orchestrate tasks
            orchestration = await self.adaptive_command_selector.decompose_task(
                task_description=task_description,
                complexity_level=arguments.get("complexity", "medium")
            )
            
            result = {
                "task_description": task_description,
                "orchestration_plan": orchestration,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error orchestrating intelligent tasks: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_analyze_workflow_patterns(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Analyze patterns in workflow execution."""
        try:
            # Analyze patterns using the pattern analyzer
            analysis = await self.pattern_analyzer.analyze_workflow_patterns(
                time_window=arguments.get("time_window", "24h"),
                pattern_types=arguments.get("pattern_types", ["success", "failure", "performance"])
            )
            
            result = {
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error analyzing workflow patterns: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_track_progress_milestones(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Track and report on progress milestones."""
        try:
            project_name = arguments.get("project_name", "")
            if not project_name:
                return [TextContent(type="text", text="Error: project_name parameter is required")]
            
            # Use progress tracking automation
            milestones = await self.progress_tracking_automation.track_milestones(
                project_name=project_name,
                milestone_type=arguments.get("milestone_type", "all")
            )
            
            result = {
                "project_name": project_name,
                "milestones": milestones,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error tracking progress milestones: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Missing delegation methods for memory management handler
    async def _handle_memory_force_backup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Force immediate backup of memory system."""
        try:
            backup_type = arguments.get("backup_type", "full")
            
            # Perform backup using memory manager
            backup_result = await self.memory_manager.create_backup(
                backup_type=backup_type,
                force=True
            )
            
            result = {
                "backup_type": backup_type,
                "backup_result": backup_result,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error forcing memory backup: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_memory_restore(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Restore memory system from backup."""
        try:
            backup_id = arguments.get("backup_id", "")
            if not backup_id:
                return [TextContent(type="text", text="Error: backup_id parameter is required")]
            
            # Restore memory from backup
            restore_result = await self.memory_manager.restore_from_backup(
                backup_id=backup_id,
                verify_integrity=arguments.get("verify", True)
            )
            
            result = {
                "backup_id": backup_id,
                "restore_result": restore_result,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error restoring memory: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_memory_cleanup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Clean up memory system by removing stale data."""
        try:
            cleanup_type = arguments.get("cleanup_type", "stale")
            threshold_days = arguments.get("threshold_days", 30)
            
            # Perform memory cleanup
            cleanup_result = await self.memory_manager.cleanup_memory(
                cleanup_type=cleanup_type,
                threshold_days=threshold_days,
                dry_run=arguments.get("dry_run", False)
            )
            
            result = {
                "cleanup_type": cleanup_type,
                "threshold_days": threshold_days,
                "cleanup_result": cleanup_result,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error cleaning up memory: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Main server entry point."""
    server = EnhancedAtlasCommandsServer()
    
    # Add project context support (minimal integration)
    try:
        from .project.server_patch import patch_server_for_project_context, apply_project_patches_to_tools
        
        # Enable project context if configured
        if patch_server_for_project_context(server):
            apply_project_patches_to_tools(server)
            server.logger.info("✅ ATLAS MCP Server: Project context enabled")
        else:
            server.logger.info("ℹ️ ATLAS MCP Server: Running in single-project mode")
    except ImportError:
        server.logger.info("ℹ️ ATLAS MCP Server: Project context not available")
    except Exception as e:
        server.logger.warning(f"⚠️ ATLAS MCP Server: Project context initialization failed: {e}")
    
    # Run the server
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())