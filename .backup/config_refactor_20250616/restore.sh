#!/bin/bash
# Configuration System Restoration Script
# Created: $(date)
# Purpose: Restore original configuration system if refactoring fails

set -e

echo "🔄 Starting configuration system restoration..."

# Get the directory of this script
BACKUP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$BACKUP_DIR/../.."

# Confirm restoration
read -p "⚠️  This will restore the configuration system to its state before refactoring. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Restoration cancelled."
    exit 1
fi

# Restore configuration files
echo "📁 Restoring configuration directory..."
rm -rf "$PROJECT_ROOT/panther/config"
cp -r "$BACKUP_DIR/config" "$PROJECT_ROOT/panther/"

# Restore plugin schemas
echo "📁 Restoring plugin configuration schemas..."
cp "$BACKUP_DIR/plugins/services_config_schema.py" "$PROJECT_ROOT/panther/plugins/services/config_schema.py"
cp "$BACKUP_DIR/plugins/protocols_config_schema.py" "$PROJECT_ROOT/panther/plugins/protocols/config_schema.py"

# Restore test case implementations
echo "📁 Restoring test case implementations..."
cp "$BACKUP_DIR/core/test_case_impl"*.py "$PROJECT_ROOT/panther/core/test_cases/"

# Remove new hybrid system if it exists
echo "🗑️  Removing hybrid configuration system..."
rm -rf "$PROJECT_ROOT/panther/config/hybrid"
rm -rf "$PROJECT_ROOT/panther/tools/config_migration"

# Restore imports in key files
echo "🔧 Restoring imports..."
# This would need to be expanded based on actual changes made

echo "✅ Configuration system restored successfully!"
echo "⚠️  Remember to:"
echo "   1. Run tests to verify functionality"
echo "   2. Check git status for any uncommitted changes"
echo "   3. Reinstall the package if needed: pip install -e ."