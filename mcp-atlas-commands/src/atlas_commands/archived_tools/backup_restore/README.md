# Backup/Restore Tools Archive

## Overview

This archive contains 7 backup and restore tools that were moved from the main ATLAS MCP server to streamline the active toolset while preserving functionality.

## Archived Tools

### 1. create_task_backup
- **Purpose**: Create backup of current task state
- **Type**: Manual backup operation
- **Reason for Archive**: Replaced by intelligent backup triggers in workflow automation

### 2. archive_task  
- **Purpose**: Archive completed task to compressed format
- **Type**: Manual archival operation
- **Reason for Archive**: Integrated into automated task lifecycle management

### 3. create_hierarchical_backup
- **Purpose**: Create hierarchical backup with parent-child relationships
- **Type**: Manual hierarchical backup
- **Reason for Archive**: Superseded by automatic hierarchical state management

### 4. list_checkpoints
- **Purpose**: List all checkpoints for a task, optionally in tree format
- **Type**: Administrative listing operation
- **Reason for Archive**: Integrated into task context retrieval

### 5. restore_from_checkpoint
- **Purpose**: Restore task from a specific checkpoint
- **Type**: Manual restore operation
- **Reason for Archive**: Available through intelligent restoration recommendations

### 6. memory_force_backup
- **Purpose**: Force backup of memory state
- **Type**: Manual memory backup
- **Reason for Archive**: Automated by entropy-triggered memory management

### 7. memory_restore
- **Purpose**: Restore memory from backup
- **Type**: Manual memory restore
- **Reason for Archive**: Integrated into intelligent memory recovery

## Intelligent Alternatives

Instead of these manual tools, the system now provides:

- **Automatic Backup Triggers**: `track_progress_milestones` detects when backups are needed
- **Intelligent Restoration**: `adaptive_command_selection` recommends restoration when appropriate
- **Entropy-Based Memory**: Memory backups happen automatically when entropy thresholds are met
- **Workflow Orchestration**: `orchestrate_intelligent_tasks` handles backup/restore as part of task flow

## Restoration Process

To restore these tools if needed:

1. Extract the archived tool definitions from `backup_restore_tools.json`
2. Add them back to the server tool list
3. Restore corresponding handler methods from `backup_restore_handlers.py`
4. Update tool registry to include restored tools

## Archive Date

Created: 2025-06-24
Original Tool Count: 27 → Active Count: 20 (after archiving 7 backup/restore tools)
Token Efficiency Gain: ~15% reduction in tool registry overhead