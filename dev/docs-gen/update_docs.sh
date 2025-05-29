#!/usr/bin/env bash
# Documentation Update Script
# This script runs all documentation-related tasks in the correct order
#
# Usage: ./update_docs.sh [--strict] [--no-fix-yaml]
#   --strict: Enable strict mode, which will exit with error code 1 when any issues are found.
#            Without this flag, the script will continue despite errors, showing warnings instead.
#   --no-fix-yaml: Skip automatic fixing of YAML configuration issues.

# Process command line arguments
STRICT_MODE=false
FIX_YAML=true  # Default to automatically fixing YAML issues

while [ $# -gt 0 ]; do
    case "$1" in
        --strict)
            STRICT_MODE=true
            shift
            ;;
        --no-fix-yaml)
            FIX_YAML=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--strict] [--no-fix-yaml]"
            echo "  --strict      Exit with error code when issues are found"
            echo "  --no-fix-yaml Skip automatic fixing of YAML configuration issues"
            exit 1
            ;;
    esac
done

# Change to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Create docs directory structure based on mkdocs.yml
echo "🔧 Creating documentation directory structure..."
rm -rf docs/
mkdir -p docs/

# Create required subdirectories for documentation
mkdir -p docs/environments/execution_environment docs/environments/network_environment
mkdir -p docs/protocols/client_server docs/protocols/peer_to_peer
mkdir -p docs/services/iut docs/services/testers

# Ensure we have development and API reference directories
mkdir -p docs/development docs/api_reference

# Create directories for user guides
mkdir -p docs/user_guide

# Link existing README files instead of creating new index files
echo "📄 Linking project README files as index files..."

# Copy main README to plugin system overview
if [ -f README.md ]; then
    cp README.md docs/index.md
fi

# Check for plugin system directories and READMEs
if [ -d panther/plugins ]; then
    # Link to environment plugins READMEs
    if [ -d panther/plugins/environments ] && [ -f panther/plugins/environments/README.md ]; then
        cp panther/plugins/environments/README.md docs/environments/index.md
    elif [ ! -f docs/environments/index.md ]; then
        echo "# Environment Plugins\n\nEnvironment plugins define the execution context for PANTHER." > docs/environments/index.md
    fi

    # Link to protocol plugins READMEs
    if [ -d panther/plugins/protocols ] && [ -f panther/plugins/protocols/README.md ]; then
        cp panther/plugins/protocols/README.md docs/protocols/index.md
    elif [ ! -f docs/protocols/index.md ]; then
        echo "# Protocol Plugins\n\nProtocol plugins implement various network protocols." > docs/protocols/index.md
    fi

    # Link to service plugins READMEs
    if [ -d panther/plugins/services ] && [ -f panther/plugins/services/README.md ]; then
        cp panther/plugins/services/README.md docs/services/index.md
    elif [ ! -f docs/services/index.md ]; then
        echo "# Service Plugins\n\nService plugins provide testing capabilities." > docs/services/index.md
    fi

    # Link environment sub-directories READMEs
    if [ -d panther/plugins/environments/execution ] && [ -f panther/plugins/environments/execution/README.md ]; then
        cp panther/plugins/environments/execution/README.md docs/environments/execution_environment/index.md
    fi
    if [ -d panther/plugins/environments/network ] && [ -f panther/plugins/environments/network/README.md ]; then
        cp panther/plugins/environments/network/README.md docs/environments/network_environment/index.md
    fi

    # Link protocol sub-directories READMEs
    if [ -d panther/plugins/protocols/client_server ] && [ -f panther/plugins/protocols/client_server/README.md ]; then
        cp panther/plugins/protocols/client_server/README.md docs/protocols/client_server/index.md
    fi
    if [ -d panther/plugins/protocols/peer ] && [ -f panther/plugins/protocols/peer/README.md ]; then
        cp panther/plugins/protocols/peer/README.md docs/protocols/peer_to_peer/index.md
    fi

    # Link service sub-directories READMEs
    if [ -d panther/plugins/services/iut ] && [ -f panther/plugins/services/iut/README.md ]; then
        cp panther/plugins/services/iut/README.md docs/services/iut/index.md
    fi
    if [ -d panther/plugins/services/testers ] && [ -f panther/plugins/services/testers/README.md ]; then
        cp panther/plugins/services/testers/README.md docs/services/testers/index.md
    fi
fi

# No need to create special documentation files as they should come from the main project

# Use the main README.md as the home.md file, with some processing to ensure links work properly
echo "📄 Creating home page from main README..."
if [ -f README.md ]; then
    # Convert the README.md to home.md with proper links
    sed 's/\(INSTALL\|CONTRIBUTING\|EXPERIMENT_GUIDE\)\.md/\L\1.md/g' README.md > docs/home.md
    # If there are any relative links to other markdown files, fix them
    sed -i.bak 's|\.\./\([^/]*\)\.md|\1.md|g' docs/home.md
    sed -i.bak 's|\./\([^/]*\)\.md|\1.md|g' docs/home.md
    # Remove any backup files created by sed
    rm -f docs/home.md.bak
else
    if [ "$STRICT_MODE" = "true" ]; then
        echo "❌ Error: Main README.md not found. Stopping in strict mode."
        exit 1
    else
        echo "⚠️ Warning: Main README.md not found, skipping home page creation"
    fi
fi

# Copy core documentation files from project root to docs directory
echo "📋 Copying core documentation files..."

# Copy README.md to docs directory (ensuring proper links)
if [ -f README.md ]; then
    cp README.md docs/
fi

# Copy CONTRIBUTING.md to development directory
if [ -f CONTRIBUTING.md ]; then
    cp CONTRIBUTING.md docs/development/
fi

# Copy installation and quick start guides
if [ -f install.md ]; then
    cp install.md docs/
elif [ -f INSTALLATION.md ]; then
    cp INSTALLATION.md docs/INSTALL.md
fi

if [ -f quick_start.md ]; then
    cp quick_start.md docs/
fi

# Copy changelog and other documentation
if [ -f CHANGELOG.md ]; then
    cp CHANGELOG.md docs/development/
fi

if [ -f workflow.md ]; then
    cp workflow.md docs/development/
fi

# Copy any experiment guide if it exists
if [ -f EXPERIMENT_GUIDE.md ]; then
    cp EXPERIMENT_GUIDE.md docs/
elif [ -f experiment_guide.md ]; then
    cp experiment_guide.md docs/EXPERIMENT_GUIDE.md
fi

# Copy documentation style guide
if [ -f docs-gen/style_guide.md ]; then
    cp docs-gen/style_guide.md docs/development/
fi

echo "🔍 Updating PANTHER documentation..."
echo "==============================="

# 1. Add cross-references between documentation files
echo -e "\n📚 Adding cross-references..."
python docs-gen/add_cross_references.py
if [ $? -ne 0 ]; then
    if [ "$STRICT_MODE" = "true" ]; then
        echo "❌ Error: Cross-references script encountered issues. Stopping in strict mode."
        exit 1
    else
        echo "⚠️  Warning: Cross-references script encountered issues but continuing..."
    fi
fi

# 2. Generate plugin documentation
echo -e "\n🔌 Generating plugin documentation..."

# Extract plugin documentation from the actual plugins, but skip top-level README files
# which were already processed in the index file step
echo "    Extracting documentation from plugins..."
if [ -d panther/plugins ]; then
    # Process environment plugins
    if [ -d panther/plugins/environments ]; then
        find panther/plugins/environments -type f -name "README.md" | grep -v "panther/plugins/environments/README.md" | while read readme; do
            plugin_dir=$(dirname "$readme")
            plugin_name=$(basename "$plugin_dir")
            # Skip if this is a category directory that was already handled
            if [[ "$plugin_name" == "execution" ]] || [[ "$plugin_name" == "network" ]]; then
                continue
            fi

            # Determine the plugin type based on directory structure
            plugin_type="execution_environment"
            if [[ "$plugin_dir" == *"network"* ]]; then
                plugin_type="network_environment"
            fi

            echo "    Processing plugin: $plugin_name ($plugin_type)"
            mkdir -p "docs/environments/$plugin_type/$plugin_name"
            cp "$readme" "docs/environments/$plugin_type/$plugin_name/index.md"

            # Copy any additional markdown files in the plugin directory
            find "$plugin_dir" -type f -name "*.md" -not -name "README.md" | while read mdfile; do
                filename=$(basename "$mdfile")
                cp "$mdfile" "docs/environments/$plugin_type/$plugin_name/$filename"
            done
        done
    fi

    # Process protocol plugins
    if [ -d panther/plugins/protocols ]; then
        find panther/plugins/protocols -type f -name "README.md" | grep -v "panther/plugins/protocols/README.md" | while read readme; do
            plugin_dir=$(dirname "$readme")
            plugin_name=$(basename "$plugin_dir")
            # Skip if this is a category directory that was already handled
            if [[ "$plugin_name" == "client_server" ]] || [[ "$plugin_name" == "peer" ]]; then
                continue
            fi

            # Determine the plugin type based on directory structure
            plugin_type="client_server"
            if [[ "$plugin_dir" == *"peer"* ]]; then
                plugin_type="peer_to_peer"
            fi

            echo "    Processing plugin: $plugin_name ($plugin_type)"
            mkdir -p "docs/protocols/$plugin_type/$plugin_name"
            cp "$readme" "docs/protocols/$plugin_type/$plugin_name/index.md"

            # Copy any additional markdown files in the plugin directory
            find "$plugin_dir" -type f -name "*.md" -not -name "README.md" | while read mdfile; do
                filename=$(basename "$mdfile")
                cp "$mdfile" "docs/protocols/$plugin_type/$plugin_name/$filename"
            done
        done
    fi

    # Process service plugins
    if [ -d panther/plugins/services ]; then
        find panther/plugins/services -type f -name "README.md" | grep -v "panther/plugins/services/README.md" | while read readme; do
            plugin_dir=$(dirname "$readme")
            plugin_name=$(basename "$plugin_dir")
            # Skip if this is a category directory that was already handled
            if [[ "$plugin_name" == "iut" ]] || [[ "$plugin_name" == "testers" ]]; then
                continue
            fi

            # Determine the plugin type based on directory structure
            plugin_type="iut"
            if [[ "$plugin_dir" == *"tester"* ]]; then
                plugin_type="testers"
            fi

            echo "    Processing plugin: $plugin_name ($plugin_type)"
            mkdir -p "docs/services/$plugin_type/$plugin_name"
            cp "$readme" "docs/services/$plugin_type/$plugin_name/index.md"

            # Copy any additional markdown files in the plugin directory
            find "$plugin_dir" -type f -name "*.md" -not -name "README.md" | while read mdfile; do
                filename=$(basename "$mdfile")
                cp "$mdfile" "docs/services/$plugin_type/$plugin_name/$filename"
            done
        done
    fi
fi

# Then run the Python script for more sophisticated processing if available
# Remove old plugin_docs directory as we'll now generate directly to docs/
if [ -d plugin_docs ]; then
    echo "    Removing old plugin_docs directory..."
    rm -rf plugin_docs
fi

# Check if --strict flag is provided to enable strict error handling
if [ "$STRICT_MODE" = "true" ]; then
    STRICT_FLAG="--strict"
else
    STRICT_FLAG=""
fi

if [ -f docs-gen/mkdocs/generate_plugin_docs.py ]; then
    python docs-gen/mkdocs/generate_plugin_docs.py $STRICT_FLAG || {
        if [ "$STRICT_MODE" = "true" ]; then
            echo "❌ Error: Plugin documentation generation failed in strict mode. Stopping."
            exit 1
        else
            echo "⚠️  Warning: Plugin documentation generation encountered issues, but continuing..."
        fi
    }
else
    echo "⚠️  Warning: Plugin documentation generator not found, skipping..."
fi

# 3. Generate API reference documentation
echo -e "\n📖 Generating API documentation..."
if [ -f docs-gen/mkdocs/gen_ref_pages.py ]; then
    python docs-gen/mkdocs/gen_ref_pages.py || {
        if [ "$STRICT_MODE" = "true" ]; then
            echo "❌ Error: API documentation generation failed in strict mode. Stopping."
            exit 1
        else
            echo "⚠️  Warning: API documentation generation encountered issues, but continuing..."
        fi
    }
else
    if [ "$STRICT_MODE" = "true" ]; then
        echo "❌ Error: API documentation generator not found. Stopping in strict mode."
        exit 1
    else
        echo "⚠️  Warning: API documentation generator not found, skipping..."
    fi
fi

# Fix MkDocs YAML configuration if needed
echo -e "\n🔧 Checking and fixing MkDocs YAML configuration..."
if [ -f docs-gen/fix_mkdocs_yaml.py ] && [ "$FIX_YAML" = "true" ]; then
    python docs-gen/fix_mkdocs_yaml.py || {
        if [ "$STRICT_MODE" = "true" ]; then
            echo "❌ Error: Unable to fix MkDocs configuration. Stopping in strict mode."
            exit 1
        else
            echo "⚠️  Warning: Unable to fix MkDocs configuration, but continuing..."
        fi
    }
elif [ "$FIX_YAML" = "false" ]; then
    echo "Skipping YAML fixing as requested with --no-fix-yaml"
else
    if [ "$STRICT_MODE" = "true" ]; then
        echo "❌ Error: MkDocs YAML fixer not found. Stopping in strict mode."
        exit 1
    else
        echo "⚠️  Warning: MkDocs YAML fixer not found, skipping..."
    fi
fi

# 4. Verify and fix links
echo -e "\n🔗 Verifying links..."
python docs-gen/verify_links.py --autofix || {
    if [ "$STRICT_MODE" = "true" ]; then
        echo "❌ Error: Link verification found issues. Stopping in strict mode."
        exit 1
    else
        echo "⚠️  Warning: Link verification found issues, but continuing..."
    fi
}


# 5. Update MkDocs navigation
echo -e "\n📋 Updating MkDocs navigation..."
python docs-gen/update_mkdocs_nav.py || {
    if [ "$STRICT_MODE" = "true" ]; then
        echo "❌ Error: Navigation update encountered issues. Stopping in strict mode."
        exit 1
    else
        echo "⚠️  Warning: Navigation update encountered issues, but continuing..."
    fi
}

# 6. Enhance MkDocs config with link checking plugins
echo -e "\n⚙️ Enhancing MkDocs configuration..."
if [ -f docs-gen/enhance_mkdocs_config.py ]; then
    python docs-gen/enhance_mkdocs_config.py || {
        if [ "$STRICT_MODE" = "true" ]; then
            echo "❌ Error: MkDocs configuration enhancement encountered issues. Stopping in strict mode."
            exit 1
        else
            echo "⚠️  Warning: MkDocs configuration enhancement encountered issues, but continuing..."
        fi
    }
else
    if [ "$STRICT_MODE" = "true" ]; then
        echo "❌ Error: MkDocs configuration enhancer not found. Stopping in strict mode."
        exit 1
    else
        echo "⚠️  Warning: MkDocs configuration enhancer not found, skipping..."
    fi
fi

# 7. Build documentation to verify everything works
echo -e "\n🏗️ Building documentation..."
if command -v mkdocs &> /dev/null; then
    mkdocs build || {
        if [ "$STRICT_MODE" = "true" ]; then
            echo "❌ Error: MkDocs build encountered issues. Stopping in strict mode."
            exit 1
        else
            echo "⚠️  Warning: MkDocs build encountered issues. The documentation may need additional fixes."
        fi
    }
else
    if [ "$STRICT_MODE" = "true" ]; then
        echo "❌ Error: MkDocs not found. Please install MkDocs to build the documentation. Stopping in strict mode."
        echo "    pip install mkdocs mkdocs-material"
        exit 1
    else
        echo "⚠️  Warning: MkDocs not found. Please install MkDocs to build the documentation."
        echo "    pip install mkdocs mkdocs-material"
    fi
fi

echo -e "\n✅ Documentation update process completed!"
echo "Run 'mkdocs serve' to preview the documentation locally"
echo -e "\nIf you encounter any issues, make sure you have all the necessary dependencies:"
echo "    pip install mkdocs mkdocs-material mkdocstrings mkdocstrings-python pyyaml requests"
