"""Unified checklist management for ATLAS commands."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class ChecklistItem:
    """Individual checklist item with unified format."""
    
    def __init__(
        self,
        id: str,
        description: str,
        priority: str = "MEDIUM",
        estimate: str = "15m",
        status: str = "PENDING",
        dependencies: Optional[List[str]] = None
    ):
        self.id = id
        self.description = description
        self.priority = priority
        self.estimate = estimate
        self.status = status
        self.dependencies = dependencies or []
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None


class ChecklistManager:
    """Manages unified checklists across all ATLAS commands."""
    
    def __init__(self):
        self.checklists: Dict[str, List[ChecklistItem]] = {}
    
    def create_unified_checklist(
        self,
        items: List[Dict[str, Any]],
        title: str,
        checklist_id: Optional[str] = None
    ) -> str:
        """Create a unified checklist with consistent formatting."""
        
        if not checklist_id:
            checklist_id = f"checklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Convert dict items to ChecklistItem objects
        checklist_items = []
        for item_data in items:
            item = ChecklistItem(**item_data)
            checklist_items.append(item)
        
        self.checklists[checklist_id] = checklist_items
        
        # Generate markdown representation
        return self._generate_markdown(checklist_items, title, checklist_id)
    
    def _generate_markdown(
        self,
        items: List[ChecklistItem],
        title: str,
        checklist_id: str
    ) -> str:
        """Generate unified markdown format for checklist."""
        
        completed = len([item for item in items if item.status == "COMPLETED"])
        total = len(items)
        
        markdown = f"## {title} ({completed}/{total} complete)\n\n"
        
        # Group by priority
        high_priority = [item for item in items if item.priority == "HIGH"]
        medium_priority = [item for item in items if item.priority == "MEDIUM"]
        low_priority = [item for item in items if item.priority == "LOW"]
        
        if high_priority:
            markdown += "### High Priority Items\n"
            for item in high_priority:
                checkbox = "x" if item.status == "COMPLETED" else " "
                status_text = f" - {item.status}" if item.status != "PENDING" else ""
                deps_text = f" (depends: {', '.join(item.dependencies)})" if item.dependencies else ""
                markdown += f"- [{checkbox}] {item.description} [EST: {item.estimate}]{status_text}{deps_text}\n"
            markdown += "\n"
        
        if medium_priority:
            markdown += "### Medium Priority Items\n"
            for item in medium_priority:
                checkbox = "x" if item.status == "COMPLETED" else " "
                status_text = f" - {item.status}" if item.status != "PENDING" else ""
                deps_text = f" (depends: {', '.join(item.dependencies)})" if item.dependencies else ""
                markdown += f"- [{checkbox}] {item.description} [EST: {item.estimate}]{status_text}{deps_text}\n"
            markdown += "\n"
        
        if low_priority:
            markdown += "### Low Priority Items\n"
            for item in low_priority:
                checkbox = "x" if item.status == "COMPLETED" else " "
                status_text = f" - {item.status}" if item.status != "PENDING" else ""
                deps_text = f" (depends: {', '.join(item.dependencies)})" if item.dependencies else ""
                markdown += f"- [{checkbox}] {item.description} [EST: {item.estimate}]{status_text}{deps_text}\n"
            markdown += "\n"
        
        # Add progress summary
        completion_rate = (completed / total * 100) if total > 0 else 0
        total_estimate = self._calculate_total_estimate(items)
        
        markdown += f"""## Progress Summary
- **Total Items**: {total}
- **Completed**: {completed}
- **In Progress**: {len([item for item in items if item.status == "IN_PROGRESS"])}
- **Blocked**: {len([item for item in items if item.status == "BLOCKED"])}
- **Completion Rate**: {completed}/{total} ({completion_rate:.1f}%)
- **Estimated Total Time**: {total_estimate}
- **Checklist ID**: {checklist_id}
"""
        
        return markdown
    
    def _calculate_total_estimate(self, items: List[ChecklistItem]) -> str:
        """Calculate total time estimate for all items."""
        
        total_minutes = 0
        for item in items:
            # Parse estimate like "15m", "2h", "1h30m"
            estimate = item.estimate.lower()
            minutes = 0
            
            if 'h' in estimate and 'm' in estimate:
                # Format like "1h30m"
                parts = estimate.split('h')
                hours = int(parts[0])
                mins = int(parts[1].replace('m', ''))
                minutes = hours * 60 + mins
            elif 'h' in estimate:
                # Format like "2h"
                hours = int(estimate.replace('h', ''))
                minutes = hours * 60
            elif 'm' in estimate:
                # Format like "15m"
                minutes = int(estimate.replace('m', ''))
            
            total_minutes += minutes
        
        # Convert back to human readable
        if total_minutes >= 60:
            hours = total_minutes // 60
            remaining_minutes = total_minutes % 60
            if remaining_minutes > 0:
                return f"{hours}h{remaining_minutes}m"
            else:
                return f"{hours}h"
        else:
            return f"{total_minutes}m"
    
    def update_item_status(
        self,
        checklist_id: str,
        item_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update the status of a checklist item."""
        
        if checklist_id not in self.checklists:
            return False
        
        for item in self.checklists[checklist_id]:
            if item.id == item_id:
                old_status = item.status
                item.status = status
                
                if status == "IN_PROGRESS" and old_status == "PENDING":
                    item.started_at = datetime.now()
                elif status == "COMPLETED":
                    item.completed_at = datetime.now()
                
                return True
        
        return False
    
    def get_checklist_progress(self, checklist_id: str) -> Dict[str, Any]:
        """Get progress summary for a checklist."""
        
        if checklist_id not in self.checklists:
            return {}
        
        items = self.checklists[checklist_id]
        completed = len([item for item in items if item.status == "COMPLETED"])
        in_progress = len([item for item in items if item.status == "IN_PROGRESS"])
        blocked = len([item for item in items if item.status == "BLOCKED"])
        total = len(items)
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked,
            "pending": total - completed - in_progress - blocked,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "items": [
                {
                    "id": item.id,
                    "description": item.description,
                    "status": item.status,
                    "priority": item.priority,
                    "estimate": item.estimate,
                    "dependencies": item.dependencies
                }
                for item in items
            ]
        }
    
    def get_ready_items(self, checklist_id: str) -> List[str]:
        """Get items that are ready to start (dependencies met)."""
        
        if checklist_id not in self.checklists:
            return []
        
        items = self.checklists[checklist_id]
        completed_items = {item.id for item in items if item.status == "COMPLETED"}
        
        ready_items = []
        for item in items:
            if item.status == "PENDING":
                # Check if all dependencies are completed
                if all(dep in completed_items for dep in item.dependencies):
                    ready_items.append(item.id)
        
        return ready_items