"""Centralized task storage manager for MCP server."""

import os
import json
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from ..caching.decorators import cache_result, cache_invalidate
from ..config.atlas_home import get_projects_dir, get_coordination_dir

logger = logging.getLogger(__name__)


class TaskStorageManager:
    """Handles all file I/O operations for task management."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize storage manager with Atlas home integration.
        
        Args:
            base_path: Base directory for task storage. If None, uses Atlas home projects directory.
        """
        if base_path is None:
            self.base_path = get_projects_dir()
        else:
            self.base_path = Path(base_path)
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize coordination paths using Atlas home
        self.coordination_path = get_coordination_dir()
        self.coordination_path.mkdir(parents=True, exist_ok=True)
        
    def get_project_name(self) -> str:
        """Detect current project name from git or directory."""
        # In Docker context, this would be passed as environment variable
        # For now, return from env or default
        return os.environ.get('PROJECT_NAME', 'default-project')
    
    def list_projects(self) -> List[str]:
        """List all available projects by scanning for {PROJECT}_TASKS directories."""
        if not self.base_path.exists():
            return []
        
        # Make task suffix configurable
        task_suffix = os.environ.get('ATLAS_TASK_SUFFIX', '_TASKS')
        
        projects = []
        try:
            for item in self.base_path.iterdir():
                if item.is_dir() and item.name.endswith(task_suffix):
                    # Extract project name by removing task suffix
                    project_name = item.name[:-len(task_suffix)]
                    projects.append(project_name)
        except Exception as e:
            logger.warning(f"Error scanning for projects: {e}")
            return []
        
        return sorted(projects)
    
    def get_task_root(self, project_name: str, task_id: str) -> Path:
        """Get root directory for task files."""
        task_suffix = os.environ.get('ATLAS_TASK_SUFFIX', '_TASKS')
        return self.base_path / f"{project_name}{task_suffix}" / task_id
    
    def get_task_paths(self, project_name: str, task_id: str) -> Dict[str, Path]:
        """Get all standard task subdirectories."""
        root = self.get_task_root(project_name, task_id)
        return {
            "root": root,
            "artifacts": root / "artifacts",
            "tasks": root / "artifacts" / "tasks",
            "analysis": root / "artifacts" / "analysis",
            "design": root / "artifacts" / "design",
            "verification": root / "artifacts" / "verification",
            "completion": root / "artifacts" / "completion",
            "backups": root / "backups",
            "yolo": root / "backups" / "yolo",
            "workflow": root / "backups" / "workflow",
            "checkpoint": root / "backups" / "checkpoint",
            "memory": root / "memory",
            "temp": root / "temp",
            "scratchpads": root / "temp" / "scratchpads",
            "cache": root / "temp" / "cache",
            "vscode": root / ".vscode"
        }
    
    def ensure_task_directories(self, project_name: str, task_id: str) -> Dict[str, Path]:
        """Create all task directories if they don't exist."""
        paths = self.get_task_paths(project_name, task_id)
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        return paths
    
    def create_task_metadata(
        self,
        project_name: str,
        task_id: str,
        task_type: str,
        description: str,
        command: str = "plan"
    ) -> Dict[str, Any]:
        """Create or update task.json metadata file."""
        paths = self.ensure_task_directories(project_name, task_id)
        metadata_path = paths['root'] / "task.json"
        
        # Load existing or create new
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "task_id": task_id,
                "project_name": project_name,
                "task_type": task_type,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "status": "planning",
                "commands_executed": [],
                "current_phase": "planning",
                "artifacts": {},
                "dependencies": [],
                "quality_metrics": {},
                "timestamps": {},
                "checklist_items": [],
                "todowrite_integration": {
                    "enabled": True,
                    "task_ids": [],
                    "last_sync": None
                },
                "memory_graph": {
                    "entities_created": [],
                    "relationships_mapped": [],
                    "context_preserved": False
                },
                "coherence_tracking": {
                    "checklist_format": "unified",
                    "todowrite_synced": False,
                    "memory_compacted": False,
                    "workflow_enforced": False
                }
            }
        
        # Update command history
        metadata["commands_executed"].append({
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "status": "started"
        })
        
        # Update timestamps
        metadata["timestamps"][f"{command}_started"] = datetime.now().isoformat()
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Created/updated task metadata for {task_id}")
        return metadata
    
    @cache_invalidate("task")
    def update_task_status(
        self,
        project_name: str,
        task_id: str,
        status: str,
        phase: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update task status in metadata."""
        root = self.get_task_root(project_name, task_id)
        metadata_path = root / "task.json"
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Task metadata not found: {task_id}")
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        metadata["status"] = status
        if phase:
            metadata["current_phase"] = phase
        
        metadata["timestamps"][f"status_{status}"] = datetime.now().isoformat()
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Updated task {task_id} status to {status}")
        return metadata
    
    @cache_invalidate("task")
    async def update_task_metadata(
        self,
        project_name: str,
        task_id: str,
        metadata_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update task metadata with additional fields."""
        root = self.get_task_root(project_name, task_id)
        metadata_path = root / "task.json"
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Task metadata not found: {task_id}")
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Update metadata with new fields
        metadata.update(metadata_updates)
        metadata["updated_at"] = datetime.now().isoformat()
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Updated task {task_id} metadata")
        return metadata
    
    @cache_invalidate("task")
    def add_task_artifact(
        self,
        project_name: str,
        task_id: str,
        artifact_type: str,
        content: str,
        filename: str,
        description: str = ""
    ) -> str:
        """Add an artifact to task and register in metadata."""
        paths = self.get_task_paths(project_name, task_id)
        
        # Determine artifact directory based on type
        if artifact_type in paths:
            artifact_dir = paths[artifact_type]
        else:
            artifact_dir = paths["artifacts"] / artifact_type
            artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Write artifact file
        artifact_path = artifact_dir / filename
        with open(artifact_path, 'w') as f:
            f.write(content)
        
        # Update metadata
        root = self.get_task_root(project_name, task_id)
        metadata_path = root / "task.json"
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        if artifact_type not in metadata["artifacts"]:
            metadata["artifacts"][artifact_type] = []
        
        metadata["artifacts"][artifact_type].append({
            "path": str(artifact_path.relative_to(root)),
            "filename": filename,
            "description": description,
            "created_at": datetime.now().isoformat()
        })
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Added artifact {filename} to task {task_id}")
        return str(artifact_path)
    
    @cache_result("task", l1_ttl=300, l2_ttl=1800, l3_ttl=3600)
    def get_task_context(self, project_name: str, task_id: str) -> Dict[str, Any]:
        """Get full context for a task including all artifacts."""
        root = self.get_task_root(project_name, task_id)
        metadata_path = root / "task.json"
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Task not found: {task_id}")
        
        with open(metadata_path, 'r') as f:
            context = json.load(f)
        
        # Add artifact summary
        context["artifact_summary"] = {}
        for artifact_type, artifacts in context.get("artifacts", {}).items():
            context["artifact_summary"][artifact_type] = len(artifacts)
        
        return context
    
    @cache_result("task", l1_ttl=300, l2_ttl=1800, l3_ttl=3600)
    def list_project_tasks(self, project_name: Optional[str] = None, include_hierarchical: bool = True) -> List[Dict[str, Any]]:
        """List all tasks for current or specified project, including hierarchical tasks by default."""
        if not project_name:
            project_name = self.get_project_name()
        
        tasks_dir = self.base_path / f"{project_name}_TASKS"
        
        if not tasks_dir.exists():
            return []
        
        tasks = []
        for task_id_dir in tasks_dir.iterdir():
            if task_id_dir.is_dir():
                metadata_path = task_id_dir / "task.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            task_data = json.load(f)
                            
                        # Always include task if include_hierarchical is True
                        # or if it's not a hierarchical task (no parent_task_id)
                        if include_hierarchical or not task_data.get("hierarchical", False):
                            tasks.append(task_data)
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(f"Could not read task metadata from {metadata_path}: {e}")
                        continue
        
        return sorted(tasks, key=lambda t: t.get("created_at", ""), reverse=True)
    
    def generate_task_summary(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate concise task summary with essential fields only."""
        # Calculate quick progress
        checklist = task.get("checklist_items", [])
        progress = 0.0
        if checklist:
            completed = len([i for i in checklist if i.get("status") == "COMPLETED"])
            progress = round((completed / len(checklist)) * 100, 1)
        
        # Extract task name from description or use task_id
        task_name = task.get("task_name", task.get("description", "")[:50])
        if not task_name:
            # Extract meaningful part from task_id
            parts = task.get("task_id", "").split("_")
            if len(parts) > 3:
                task_name = "-".join(parts[3:])
            else:
                task_name = task.get("task_id", "Unknown")
        
        return {
            "task_id": task.get("task_id"),
            "task_name": task_name,
            "status": task.get("status", "unknown"),
            "priority": task.get("priority", "medium"),
            "created_at": task.get("created_at", "")[:10],  # Date only
            "progress": progress,
            "phase": task.get("current_phase", "unknown"),
            "subtask_count": len(task.get("subtasks", [])),
            "artifact_count": sum(len(v) for v in task.get("artifacts", {}).values())
        }
    
    def list_project_tasks_summary(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """List tasks with summary statistics instead of full data."""
        tasks = self.list_project_tasks(project_name)
        
        # Generate statistics
        status_counts = {}
        priority_counts = {}
        phase_counts = {}
        recent_tasks = []
        total_progress = 0.0
        
        for task in tasks:
            # Count by status
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by priority
            priority = task.get("priority", "medium")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Count by phase
            phase = task.get("current_phase", "unknown")
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            
            # Get recent tasks (last 5)
            if len(recent_tasks) < 5:
                recent_tasks.append(self.generate_task_summary(task))
            
            # Calculate total progress
            summary = self.generate_task_summary(task)
            total_progress += summary["progress"]
        
        # Calculate average progress
        avg_progress = round(total_progress / len(tasks), 1) if tasks else 0.0
        
        return {
            "project_name": project_name or self.get_project_name(),
            "total_tasks": len(tasks),
            "average_progress": avg_progress,
            "by_status": status_counts,
            "by_priority": priority_counts,
            "by_phase": phase_counts,
            "recent_tasks": recent_tasks,
            "summary_generated_at": datetime.now().isoformat()
        }
    
    def filter_tasks(
        self,
        project_name: Optional[str] = None,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        priority: Optional[str] = None,
        ready_only: bool = False,
        blocked_only: bool = False,
        days_old: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Filter tasks based on multiple criteria."""
        tasks = self.list_project_tasks(project_name)
        filtered_tasks = []
        
        for task in tasks:
            # Filter by status
            if status and task.get("status") != status:
                continue
                
            # Filter by task type
            if task_type and task.get("task_type") != task_type:
                continue
                
            # Filter by priority
            if priority and task.get("priority") != priority:
                continue
                
            # Filter ready tasks (no blockers, dependencies met)
            if ready_only:
                if task.get("status") != "pending" or task.get("dependencies", []):
                    continue
                    
            # Filter blocked tasks
            if blocked_only:
                if task.get("status") != "blocked":
                    continue
                    
            # Filter by age
            if days_old:
                created_date = datetime.fromisoformat(task.get("created_at", ""))
                cutoff_date = datetime.now() - timedelta(days=days_old)
                if created_date < cutoff_date:
                    continue
                    
            filtered_tasks.append(task)
            
        return filtered_tasks
    
    def calculate_task_progress(self, project_name: str, task_id: str) -> Dict[str, Any]:
        """Calculate detailed progress for a task including subtasks."""
        metadata = self.get_task_context(project_name, task_id)
        
        # Basic progress calculation
        checklist_items = metadata.get("checklist_items", [])
        total_items = len(checklist_items)
        completed_items = len([item for item in checklist_items if item.get("status") == "COMPLETED"])
        
        progress_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
        
        # Analyze artifacts for completion indicators
        artifacts = metadata.get("artifacts", {})
        phases_completed = []
        for phase in ["planning", "analysis", "design", "execution", "verification", "completion"]:
            if phase in artifacts and artifacts[phase]:
                phases_completed.append(phase)
        
        # Calculate phase-based progress
        total_phases = 6  # Standard workflow phases
        phase_progress = (len(phases_completed) / total_phases * 100)
        
        # Combine metrics for overall progress
        overall_progress = (progress_percentage + phase_progress) / 2
        
        return {
            "overall_progress": round(overall_progress, 1),
            "checklist_progress": round(progress_percentage, 1),
            "phase_progress": round(phase_progress, 1),
            "completed_phases": phases_completed,
            "total_checklist_items": total_items,
            "completed_checklist_items": completed_items,
            "status": metadata.get("status", "unknown"),
            "current_phase": metadata.get("current_phase", "unknown")
        }
    
    def create_hierarchical_backup(
        self,
        project_name: str,
        task_id: str,
        backup_type: str = "checkpoint",
        description: str = "",
        parent_checkpoint: Optional[str] = None,
        level: str = "task",
        command: str = "manual"
    ) -> str:
        """Create hierarchical backup with parent-child relationships."""
        paths = self.get_task_paths(project_name, task_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Hierarchical checkpoint naming
        if level == "task":
            backup_name = f"{command}_{timestamp}"
        elif level == "subtask":
            subtask_id = description.split("-")[0] if "-" in description else "00"
            backup_name = f"{command}_{subtask_id}_{timestamp}"
        else:  # micro
            backup_name = f"step_{timestamp}"
        
        # Determine parent directory for hierarchical structure
        if parent_checkpoint:
            parent_dir = paths['checkpoint'] / parent_checkpoint
            if level == "micro":
                backup_dir = parent_dir / "micro_checkpoints" / backup_name
            else:
                backup_dir = parent_dir / "subtasks" / backup_name
        else:
            backup_dir = paths[backup_type] / backup_name
        
        # Create backup directory
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all task files except backups
        items_to_backup = ["artifacts", "memory", "temp", ".vscode"]
        for item in items_to_backup:
            if item in paths and paths[item].exists():
                dest = backup_dir / item
                if paths[item].is_dir():
                    shutil.copytree(paths[item], dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(paths[item], dest)
        
        # Copy task.json metadata file
        task_metadata_file = paths["root"] / "task.json"
        if task_metadata_file.exists():
            shutil.copy2(task_metadata_file, backup_dir / "task.json")
        
        # Create hierarchical backup metadata
        backup_metadata = {
            "checkpoint_id": backup_name,
            "backup_type": backup_type,
            "level": level,
            "parent_id": parent_checkpoint,
            "timestamp": timestamp,
            "description": description,
            "command": command,
            "task_metadata": self.get_task_context(project_name, task_id),
            "children": []
        }
        
        with open(backup_dir / "backup_metadata.json", 'w') as f:
            json.dump(backup_metadata, f, indent=2)
        
        # Update parent checkpoint if exists
        if parent_checkpoint:
            parent_metadata_path = paths['checkpoint'] / parent_checkpoint / "backup_metadata.json"
            if parent_metadata_path.exists():
                with open(parent_metadata_path, 'r') as f:
                    parent_metadata = json.load(f)
                parent_metadata["children"].append(backup_name)
                with open(parent_metadata_path, 'w') as f:
                    json.dump(parent_metadata, f, indent=2)
        
        # Register backup in task metadata
        self.add_task_artifact(
            project_name, task_id, f"backup_{backup_type}",
            json.dumps(backup_metadata, indent=2),
            f"backup_{backup_name}.json",
            description
        )
        
        logger.info(f"Created hierarchical backup {backup_name} for task {task_id}")
        return str(backup_dir)
    
    def create_task_backup(
        self,
        project_name: str,
        task_id: str,
        backup_type: str = "checkpoint",
        description: str = ""
    ) -> str:
        """Create backup of current task state (legacy compatibility)."""
        return self.create_hierarchical_backup(
            project_name, task_id, backup_type, description, level="task"
        )
    
    def list_checkpoints(self, project_name: str, task_id: str, tree: bool = False) -> List[Dict[str, Any]]:
        """List all checkpoints for a task, optionally in tree format."""
        paths = self.get_task_paths(project_name, task_id)
        checkpoint_dir = paths['checkpoint']
        
        if not checkpoint_dir.exists():
            return []
        
        checkpoints = []
        
        def scan_checkpoint_dir(dir_path: Path, parent_id: Optional[str] = None, indent: int = 0):
            """Recursively scan checkpoint directories."""
            if not dir_path.exists():
                return
                
            for item in sorted(dir_path.iterdir()):
                if item.is_dir():
                    metadata_path = item / "backup_metadata.json"
                    
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        checkpoint_info = {
                            "id": metadata["checkpoint_id"],
                            "level": metadata["level"],
                            "parent": parent_id,
                            "timestamp": metadata["timestamp"],
                            "command": metadata["command"],
                            "description": metadata["description"],
                            "indent": indent,
                            "path": str(item)
                        }
                        
                        checkpoints.append(checkpoint_info)
                        
                        # Check for subtasks
                        subtasks_dir = item / "subtasks"
                        if subtasks_dir.exists():
                            scan_checkpoint_dir(subtasks_dir, metadata["checkpoint_id"], indent + 1)
                        
                        # Check for micro checkpoints
                        micro_dir = item / "micro_checkpoints"
                        if micro_dir.exists():
                            scan_checkpoint_dir(micro_dir, metadata["checkpoint_id"], indent + 2)
        
        scan_checkpoint_dir(checkpoint_dir)
        
        if tree:
            # Format as tree structure
            tree_output = []
            for cp in checkpoints:
                prefix = "  " * cp["indent"] + ("├── " if cp["indent"] > 0 else "")
                tree_output.append(f"{prefix}{cp['id']} ({cp['level']}) - {cp['description']}")
            return [{"tree_view": "\n".join(tree_output)}]
        
        return checkpoints
    
    def restore_from_checkpoint(self, project_name: str, task_id: str, checkpoint_id: str) -> bool:
        """Restore task from a specific checkpoint."""
        paths = self.get_task_paths(project_name, task_id)
        
        # Find checkpoint (search in hierarchical structure)
        checkpoint_path = None
        for checkpoint_info in self.list_checkpoints(project_name, task_id):
            if checkpoint_info["id"] == checkpoint_id:
                checkpoint_path = Path(checkpoint_info["path"])
                break
        
        if not checkpoint_path or not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")
        
        # Create restoration backup first
        self.create_hierarchical_backup(
            project_name, task_id, "checkpoint", 
            f"Before restoring {checkpoint_id}", command="restore"
        )
        
        # Clear current state (except backups)
        items_to_clear = ["artifacts", "memory", "temp", ".vscode"]
        for item in items_to_clear:
            if item in paths and paths[item].exists():
                if paths[item].is_dir():
                    shutil.rmtree(paths[item])
                else:
                    paths[item].unlink()
        
        # Restore from checkpoint
        for item in checkpoint_path.iterdir():
            if item.name != "backup_metadata.json":
                dest = paths["root"] / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
        
        # Update task metadata
        self.update_task_status(project_name, task_id, "restored", f"Restored from {checkpoint_id}")
        
        logger.info(f"Restored task {task_id} from checkpoint {checkpoint_id}")
        return True
    
    def archive_task(
        self,
        project_name: str,
        task_id: str,
        keep_backups: bool = True
    ) -> str:
        """Archive completed task to compressed format."""
        root = self.get_task_root(project_name, task_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create archives directory
        archives_dir = self.base_path / f"{project_name}_TASKS" / ".archives"
        archives_dir.mkdir(parents=True, exist_ok=True)
        
        # Create archive
        archive_path = archives_dir / f"{task_id}_{timestamp}.tar.gz"
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(root, arcname=task_id)
        
        # Remove original if not keeping backups
        if not keep_backups:
            shutil.rmtree(root)
        
        logger.info(f"Archived task {task_id} to {archive_path}")
        return str(archive_path)
    
    # Nested Storage Methods (Phase 1: Dual Storage Mode)
    
    def create_nested_task(
        self,
        project_name: str,
        parent_id: str,
        subtask_data: Dict[str, Any]
    ) -> str:
        """Create subtask within parent's task.json (dual mode).
        
        Phase 1: Creates both nested entry and separate directory for backward compatibility.
        
        Args:
            project_name: Project name
            parent_id: Parent task ID
            subtask_data: Subtask information
            
        Returns:
            Generated subtask ID
        """
        # Load parent task
        parent_root = self.get_task_root(project_name, parent_id)
        parent_metadata_path = parent_root / "task.json"
        
        if not parent_metadata_path.exists():
            raise FileNotFoundError(f"Parent task not found: {parent_id}")
        
        with open(parent_metadata_path, 'r') as f:
            parent_task = json.load(f)
        
        # Initialize subtasks array if needed
        if "subtasks" not in parent_task:
            parent_task["subtasks"] = []
        
        # Generate simple subtask ID
        subtask_count = len(parent_task["subtasks"]) + 1
        subtask_id = f"SUBTASK_{subtask_count:02d}"
        
        # Prepare subtask data
        subtask_data["task_id"] = subtask_id
        subtask_data["parent_id"] = parent_id
        subtask_data["created_at"] = datetime.now().isoformat()
        subtask_data["status"] = subtask_data.get("status", "planning")
        subtask_data["task_type"] = "subtask"
        
        # Add to parent's subtasks
        parent_task["subtasks"].append(subtask_data)
        
        # Save updated parent
        with open(parent_metadata_path, 'w') as f:
            json.dump(parent_task, f, indent=2)
        
        # Phase 1: Also create separate directory (backward compatibility)
        if parent_task.get("nested_storage_enabled", False) is False:
            # Create traditional flat storage
            full_subtask_id = f"{project_name}_SUBTASK_{parent_id}_{subtask_id}"
            self.create_task_metadata(
                project_name=project_name,
                task_id=full_subtask_id,
                task_type="subtask",
                description=subtask_data.get("description", ""),
                command="nested_create"
            )
        
        logger.info(f"Created nested subtask {subtask_id} under {parent_id}")
        return subtask_id
    
    def get_nested_task(
        self,
        project_name: str,
        parent_id: str,
        subtask_path: List[str]
    ) -> Dict[str, Any]:
        """Navigate to nested subtask using path.
        
        Args:
            project_name: Project name
            parent_id: Root parent task ID
            subtask_path: Path to subtask (e.g., ["SUBTASK_01", "SUBSUBTASK_02"])
            
        Returns:
            Subtask data
        """
        # Load parent
        parent_root = self.get_task_root(project_name, parent_id)
        parent_metadata_path = parent_root / "task.json"
        
        with open(parent_metadata_path, 'r') as f:
            task = json.load(f)
        
        # Navigate through path
        for subtask_id in subtask_path:
            subtasks = task.get("subtasks", [])
            found = False
            for subtask in subtasks:
                if subtask.get("task_id") == subtask_id:
                    task = subtask
                    found = True
                    break
            if not found:
                raise ValueError(f"Subtask {subtask_id} not found in path")
        
        return task
    
    def update_nested_task(
        self,
        project_name: str,
        parent_id: str,
        subtask_path: List[str],
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update nested subtask data.
        
        Args:
            project_name: Project name
            parent_id: Root parent task ID
            subtask_path: Path to subtask
            updates: Updates to apply
            
        Returns:
            Updated subtask data
        """
        # Load parent
        parent_root = self.get_task_root(project_name, parent_id)
        parent_metadata_path = parent_root / "task.json"
        
        with open(parent_metadata_path, 'r') as f:
            parent_task = json.load(f)
        
        # Navigate to target subtask
        current = parent_task
        for i, subtask_id in enumerate(subtask_path):
            subtasks = current.get("subtasks", [])
            for j, subtask in enumerate(subtasks):
                if subtask.get("task_id") == subtask_id:
                    if i == len(subtask_path) - 1:
                        # Found target - apply updates
                        subtasks[j].update(updates)
                        subtasks[j]["updated_at"] = datetime.now().isoformat()
                    else:
                        # Keep navigating
                        current = subtask
                    break
        
        # Save updated parent
        with open(parent_metadata_path, 'w') as f:
            json.dump(parent_task, f, indent=2)
        
        logger.info(f"Updated nested task at path {'/'.join(subtask_path)}")
        return self.get_nested_task(project_name, parent_id, subtask_path)
    
    def get_full_hierarchy(
        self,
        project_name: str,
        task_id: str,
        max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """Load task with all nested subtasks.
        
        Args:
            project_name: Project name
            task_id: Task ID
            max_depth: Maximum depth to traverse (None for unlimited)
            
        Returns:
            Complete task hierarchy
        """
        root = self.get_task_root(project_name, task_id)
        metadata_path = root / "task.json"
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Task not found: {task_id}")
        
        with open(metadata_path, 'r') as f:
            task = json.load(f)
        
        # Recursively expand subtasks
        def expand_subtasks(task_data: Dict[str, Any], current_depth: int = 0):
            if max_depth is not None and current_depth >= max_depth:
                return task_data
            
            subtasks = task_data.get("subtasks", [])
            for subtask in subtasks:
                expand_subtasks(subtask, current_depth + 1)
            
            return task_data
        
        return expand_subtasks(task)
    
    def count_nested_tasks(self, task_data: Dict[str, Any]) -> Dict[str, int]:
        """Count tasks at each level in hierarchy.
        
        Args:
            task_data: Task data with nested subtasks
            
        Returns:
            Count by level (tasks, subtasks, subsubtasks)
        """
        counts = {"tasks": 1, "subtasks": 0, "subsubtasks": 0}
        
        def count_recursive(task: Dict[str, Any], level: int = 0):
            subtasks = task.get("subtasks", [])
            for subtask in subtasks:
                if level == 0:
                    counts["subtasks"] += 1
                elif level == 1:
                    counts["subsubtasks"] += 1
                count_recursive(subtask, level + 1)
        
        count_recursive(task_data)
        return counts
    
    def migrate_to_nested_storage(
        self,
        project_name: str,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Migrate flat task storage to nested format.
        
        Args:
            project_name: Project name to migrate
            dry_run: If True, only analyze without making changes
            
        Returns:
            Migration report
        """
        tasks_dir = self.base_path / f"{project_name}_TASKS"
        if not tasks_dir.exists():
            return {"error": f"No tasks found for project {project_name}"}
        
        migration_report = {
            "project_name": project_name,
            "dry_run": dry_run,
            "tasks_analyzed": 0,
            "subtasks_found": 0,
            "migrations_planned": [],
            "directories_to_remove": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Find all tasks
        task_dirs = {}
        subtask_dirs = {}
        
        for item in tasks_dir.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue
            
            if "_SUBTASK_" in item.name:
                # Extract parent task ID from subtask directory name
                # Pattern: PROJECT_SUBTASK_PROJECT_TASK_domain_name_YYYYMMDD_HHMMSS_subtask-specific-name_NN
                parts = item.name.split("_SUBTASK_")
                if len(parts) >= 2:
                    subtask_part = parts[1]  # e.g., "PANTHER_TASK_config_...._20250621_033504_protocol-compatibility-validation_04"
                    
                    if subtask_part.startswith(f"{project_name}_TASK_"):
                        # Find the parent task by locating the timestamp pattern
                        # Pattern: PROJECT_TASK_domain_name_YYYYMMDD_HHMMSS_subtask-specific-parts
                        task_parts = subtask_part.split("_")
                        
                        # Look for timestamp pattern: 8-digit date followed by 6-digit time
                        parent_task_full = None
                        for i in range(len(task_parts)):
                            if (i < len(task_parts) - 1 and 
                                len(task_parts[i]) == 8 and task_parts[i].isdigit() and  # YYYYMMDD
                                len(task_parts[i + 1]) == 6 and task_parts[i + 1].isdigit()):  # HHMMSS
                                # Found timestamp pattern, parent task ends after the time part
                                parent_task_full = "_".join(task_parts[:i + 2])
                                break
                        
                        if parent_task_full:
                            parent_id = parent_task_full.replace(f"{project_name}_", "")
                            if parent_id not in subtask_dirs:
                                subtask_dirs[parent_id] = []
                            subtask_dirs[parent_id].append(item)
            elif item.name.startswith(f"{project_name}_TASK_"):
                task_id = item.name.replace(f"{project_name}_", "")
                task_dirs[task_id] = item
        
        migration_report["tasks_analyzed"] = len(task_dirs)
        migration_report["subtasks_found"] = sum(len(v) for v in subtask_dirs.values())
        
        # Plan migrations
        for task_id, task_dir in task_dirs.items():
            if task_id in subtask_dirs:
                migration = {
                    "task_id": task_id,
                    "task_dir": str(task_dir),
                    "subtask_count": len(subtask_dirs[task_id]),
                    "subtask_dirs": [str(d) for d in subtask_dirs[task_id]]
                }
                migration_report["migrations_planned"].append(migration)
                migration_report["directories_to_remove"].extend(migration["subtask_dirs"])
                
                if not dry_run:
                    # Perform actual migration
                    self._perform_migration(task_dir, subtask_dirs[task_id])
        
        return migration_report
    
    def _perform_migration(
        self,
        parent_dir: Path,
        subtask_dirs: List[Path]
    ) -> None:
        """Perform actual migration of subtasks into parent.
        
        Args:
            parent_dir: Parent task directory
            subtask_dirs: List of subtask directories to migrate
        """
        parent_metadata_path = parent_dir / "task.json"
        
        with open(parent_metadata_path, 'r') as f:
            parent_task = json.load(f)
        
        # Initialize subtasks if needed
        if "subtasks" not in parent_task:
            parent_task["subtasks"] = []
        
        # Migrate each subtask
        for subtask_dir in subtask_dirs:
            subtask_metadata_path = subtask_dir / "task.json"
            if subtask_metadata_path.exists():
                with open(subtask_metadata_path, 'r') as f:
                    subtask_data = json.load(f)
                
                # Clean up the task ID to be simple
                old_id = subtask_data.get("task_id", "")
                if "_SUBTASK_" in old_id:
                    # Extract just the SUBTASK_XX part
                    parts = old_id.split("_")
                    if parts[-1].isdigit() and len(parts[-1]) == 2:
                        subtask_data["task_id"] = f"SUBTASK_{parts[-1]}"
                
                # Add to parent's subtasks
                parent_task["subtasks"].append(subtask_data)
                
                # Archive the old directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_path = subtask_dir.parent / ".migrated" / f"{subtask_dir.name}_{timestamp}"
                archive_path.parent.mkdir(exist_ok=True)
                shutil.move(str(subtask_dir), str(archive_path))
        
        # Enable nested storage flag
        parent_task["nested_storage_enabled"] = True
        parent_task["migration_completed_at"] = datetime.now().isoformat()
        
        # Save updated parent
        with open(parent_metadata_path, 'w') as f:
            json.dump(parent_task, f, indent=2)
        
        logger.info(f"Migrated {len(subtask_dirs)} subtasks into {parent_dir.name}")

    # ========== COORDINATION METHODS ==========
    
    def get_coordination_registry(self) -> Path:
        """Get path to coordination registry directory."""
        return self.coordination_path / "registry"
        
    def get_global_cache(self) -> Path:
        """Get path to global coordination cache."""
        return self.coordination_path / "cache" / "global_cache"
        
    def get_project_cache(self, project_name: str) -> Path:
        """Get path to project-specific cache."""
        project_cache = self.coordination_path / "cache" / "project_caches" / project_name
        project_cache.mkdir(parents=True, exist_ok=True)
        return project_cache
        
    def register_project(self, project_name: str, project_type: str, coordination_role: str = "secondary") -> Dict[str, Any]:
        """Register project in global coordination registry."""
        registry_path = self.get_coordination_registry() / "projects.json"
        
        try:
            if registry_path.exists():
                with open(registry_path, 'r') as f:
                    registry = json.load(f)
            else:
                registry = {"projects": {}, "coordination_metadata": {}}
            
            # Add or update project
            registry["projects"][project_name] = {
                "type": project_type,
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "coordination_role": coordination_role,
                "memory_scope": "isolated" if coordination_role != "primary" else "global",
                "command_framework": "mcp_optimized",
                "resource_sharing": "enabled",
                "description": f"Project {project_name} registered via coordination system"
            }
            
            # Update metadata
            registry["coordination_metadata"].update({
                "last_updated": datetime.now().isoformat(),
                "total_projects": len(registry["projects"]),
                "coordination_mode": "hierarchical"
            })
            
            # Save registry
            with open(registry_path, 'w') as f:
                json.dump(registry, f, indent=2)
                
            logger.info(f"Registered project {project_name} in coordination registry")
            return registry["projects"][project_name]
            
        except Exception as e:
            logger.error(f"Failed to register project {project_name}: {e}")
            return {"error": str(e)}
    
    def get_cross_project_tasks(self) -> List[Dict]:
        """Get tasks across all registered projects."""
        tasks_registry_path = self.get_coordination_registry() / "tasks_global.json"
        
        try:
            if tasks_registry_path.exists():
                with open(tasks_registry_path, 'r') as f:
                    global_registry = json.load(f)
                return list(global_registry.get("global_tasks", {}).values())
            else:
                return []
        except Exception as e:
            logger.error(f"Failed to get cross-project tasks: {e}")
            return []
    
    def create_cross_project_task(
        self, 
        task_id: str, 
        project_name: str, 
        description: str, 
        coordination_priority: str = "medium",
        cross_project_dependencies: List[str] = None
    ) -> Dict[str, Any]:
        """Create a task with cross-project coordination metadata."""
        
        if cross_project_dependencies is None:
            cross_project_dependencies = []
            
        global_task_id = f"atlas-{project_name}-{task_id}"
        
        # Create coordination metadata
        coordination_metadata = {
            "atlas_project": "primary" if project_name == "Software-Engineer-AI-Agent-Atlas" else "secondary",
            "cross_project_dependencies": cross_project_dependencies,
            "resource_sharing": {
                "memory": "shared" if coordination_priority == "critical" else "isolated",
                "cache": "hierarchical",
                "tools": "coordinated"
            },
            "coordination_priority": coordination_priority
        }
        
        # Create project context
        project_context = {
            "project_name": project_name,
            "project_type": self._detect_project_type(project_name),
            "local_task_id": task_id
        }
        
        # Create coordination status
        coordination_status = {
            "global_phase": "planning",
            "project_coordination": "synchronized",
            "resource_allocation": "exclusive" if coordination_priority == "critical" else "shared"
        }
        
        # Add to global task registry
        tasks_registry_path = self.get_coordination_registry() / "tasks_global.json"
        
        try:
            if tasks_registry_path.exists():
                with open(tasks_registry_path, 'r') as f:
                    global_registry = json.load(f)
            else:
                global_registry = {
                    "global_tasks": {},
                    "coordination_index": {
                        "by_project": {},
                        "by_priority": {"critical": [], "high": [], "medium": [], "low": []},
                        "by_status": {"planning": [], "coordination": [], "execution": [], "verification": [], "completion": []}
                    },
                    "metadata": {}
                }
            
            # Add task
            global_registry["global_tasks"][global_task_id] = {
                "global_task_id": global_task_id,
                "coordination_metadata": coordination_metadata,
                "project_context": project_context,
                "coordination_status": coordination_status,
                "task_metadata": {
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "priority": coordination_priority
                }
            }
            
            # Update indexes
            if project_name not in global_registry["coordination_index"]["by_project"]:
                global_registry["coordination_index"]["by_project"][project_name] = []
            global_registry["coordination_index"]["by_project"][project_name].append(global_task_id)
            
            global_registry["coordination_index"]["by_priority"][coordination_priority].append(global_task_id)
            global_registry["coordination_index"]["by_status"]["planning"].append(global_task_id)
            
            # Update metadata
            global_registry["metadata"].update({
                "total_global_tasks": len(global_registry["global_tasks"]),
                "last_updated": datetime.now().isoformat(),
                "coordination_version": "1.0.0"
            })
            
            # Save registry
            with open(tasks_registry_path, 'w') as f:
                json.dump(global_registry, f, indent=2)
                
            logger.info(f"Created cross-project task {global_task_id}")
            return global_registry["global_tasks"][global_task_id]
            
        except Exception as e:
            logger.error(f"Failed to create cross-project task {global_task_id}: {e}")
            return {"error": str(e)}
    
    def _detect_project_type(self, project_name: str) -> str:
        """Detect project type based on name and structure."""
        if "PANTHER" in project_name:
            return "programming"
        elif "atlas-command" in project_name:
            return "programming"
        elif project_name == "Software-Engineer-AI-Agent-Atlas":
            return "documentation"
        else:
            return "unknown"
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get overall coordination system status."""
        try:
            # Load project registry
            projects_path = self.get_coordination_registry() / "projects.json"
            tasks_path = self.get_coordination_registry() / "tasks_global.json"
            
            status = {
                "coordination_enabled": True,
                "timestamp": datetime.now().isoformat()
            }
            
            if projects_path.exists():
                with open(projects_path, 'r') as f:
                    projects_registry = json.load(f)
                status["projects"] = projects_registry.get("coordination_metadata", {})
            
            if tasks_path.exists():
                with open(tasks_path, 'r') as f:
                    tasks_registry = json.load(f)
                status["tasks"] = tasks_registry.get("metadata", {})
                status["coordination_index"] = tasks_registry.get("coordination_index", {})
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get coordination status: {e}")
            return {"error": str(e), "coordination_enabled": False}
    
    def resolve_resource_conflict(self, project_a: str, project_b: str, resource_type: str) -> Dict[str, Any]:
        """Resolve resource allocation conflicts between projects."""
        try:
            conflict_resolution = {
                "conflict_id": f"{project_a}-{project_b}-{resource_type}",
                "projects": [project_a, project_b],
                "resource_type": resource_type,
                "resolution_strategy": "priority_based",
                "resolved_at": datetime.now().isoformat()
            }
            
            # Simple priority-based resolution
            if project_a == "Software-Engineer-AI-Agent-Atlas":
                conflict_resolution["winner"] = project_a
                conflict_resolution["reason"] = "Primary project has priority"
            elif "PANTHER" in project_a and "PANTHER" not in project_b:
                conflict_resolution["winner"] = project_a
                conflict_resolution["reason"] = "Active programming project priority"
            else:
                conflict_resolution["winner"] = project_b
                conflict_resolution["reason"] = "Default to second project"
            
            # Log conflict resolution
            conflicts_path = self.coordination_path / "intelligence" / "conflict_resolution"
            conflicts_path.mkdir(parents=True, exist_ok=True)
            
            conflict_file = conflicts_path / f"{conflict_resolution['conflict_id']}.json"
            with open(conflict_file, 'w') as f:
                json.dump(conflict_resolution, f, indent=2)
            
            logger.info(f"Resolved resource conflict: {conflict_resolution['conflict_id']}")
            return conflict_resolution
            
        except Exception as e:
            logger.error(f"Failed to resolve resource conflict: {e}")
            return {"error": str(e)}