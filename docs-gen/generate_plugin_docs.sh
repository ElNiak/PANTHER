#!/bin/bash
# filepath: /Users/elniak/Documents/Project/PANTHER/docs-gen/generate_plugin_docs.sh

# Script to automate the creation of documentation for PANTHER plugins
# using the template

PANTHER_ROOT="/Users/elniak/Documents/Project/PANTHER"
TEMPLATE_PATH="$PANTHER_ROOT/docs/templates/plugin_template.md"
PLUGINS_PATH="$PANTHER_ROOT/panther/plugins"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to create documentation for a plugin
create_plugin_doc() {
    local plugin_path="$1"
    local plugin_type="$2"
    local plugin_subtype="$3"
    local plugin_name="$4"
    
    # Full path to the plugin
    local full_path="$PLUGINS_PATH/$plugin_type/$plugin_subtype/$plugin_name"
    
    # Check if plugin directory exists
    if [ ! -d "$full_path" ]; then
        echo -e "${RED}Plugin directory not found: $full_path${NC}"
        return 1
    fi
    
    # Create docs directory if it doesn't exist
    mkdir -p "$full_path/docs"
    
    # Check if README already exists
    if [ -f "$full_path/README.md" ]; then
        echo -e "${YELLOW}README.md already exists for $plugin_type/$plugin_subtype/$plugin_name${NC}"
        # Optionally, uncomment to overwrite existing README.md
        # cp "$TEMPLATE_PATH" "$full_path/README.md"
    else
        # Copy template to README.md
        cp "$TEMPLATE_PATH" "$full_path/README.md"
        
        # Replace placeholders in the template
        if [[ "$plugin_subtype" == "execution_environment" || "$plugin_subtype" == "network_environment" ]]; then
            # For environment plugins
            display_type="Environment ($plugin_subtype)"
            source_loc="plugins/environments/$plugin_subtype/$plugin_name/"
        elif [[ "$plugin_type" == "protocols" ]]; then
            # For protocol plugins
            display_type="Protocol ($plugin_subtype)"
            source_loc="plugins/protocols/$plugin_subtype/$plugin_name/"
        elif [[ "$plugin_subtype" == "iut" || "$plugin_subtype" == "testers" ]]; then
            # For service plugins
            display_type="Service ($plugin_subtype)"
            source_loc="plugins/services/$plugin_subtype/$plugin_name/"
        else
            display_type="Unknown"
            source_loc="plugins/$plugin_type/$plugin_subtype/$plugin_name/"
        fi
        
        # Capitalize and format plugin name
        formatted_name=$(echo "$plugin_name" | sed -e 's/_/ /g' -e 's/\b\(.\)/\u\1/g')
        
        # Fix the first line of the template (has a typo with D#)
        sed -i '' '1s/^D# /{Plugin Name}/' "$full_path/README.md"
        
        # Replace placeholders
        sed -i '' "s/{Plugin Name}/$formatted_name/g" "$full_path/README.md"
        sed -i '' "s/{Protocol|Environment|Service|Tester}/$display_type/g" "$full_path/README.md"
        sed -i '' "s|plugins/{plugin_type}/{plugin_name}/|$source_loc|g" "$full_path/README.md"
        
        echo -e "${GREEN}Created README.md for $plugin_type/$plugin_subtype/$plugin_name${NC}"
    fi
}

# Process environment plugins
echo "Processing environment plugins..."
for env_type in execution_environment network_environment; do
    for plugin in "$PLUGINS_PATH/environments/$env_type"/*; do
        if [ -d "$plugin" ] && [ "$(basename "$plugin")" != "__pycache__" ]; then
            plugin_name=$(basename "$plugin")
            create_plugin_doc "environments" "$env_type" "$plugin_name"
        fi
    done
done

# Process protocol plugins
echo "Processing protocol plugins..."
for proto_type in client_server peer_to_peer; do
    if [ -d "$PLUGINS_PATH/protocols/$proto_type" ]; then
        for plugin in "$PLUGINS_PATH/protocols/$proto_type"/*; do
            if [ -d "$plugin" ] && [ "$(basename "$plugin")" != "__pycache__" ]; then
                plugin_name=$(basename "$plugin")
                create_plugin_doc "protocols" "$proto_type" "$plugin_name"
            fi
        done
    fi
done

# Process service plugins
echo "Processing service plugins..."
for service_type in iut testers; do
    for plugin in "$PLUGINS_PATH/services/$service_type"/*; do
        if [ -d "$plugin" ] && [ "$(basename "$plugin")" != "__pycache__" ]; then
            plugin_name=$(basename "$plugin")
            create_plugin_doc "services" "$service_type" "$plugin_name"
        fi
    done
done

# Generate updated plugin inventory
echo "Generating updated plugin inventory..."
python "$PANTHER_ROOT/docs-gen/generate_plugin_inventory.py" --format markdown --output "$PANTHER_ROOT/docs/plugin_inventory.md"

echo -e "\n${GREEN}Documentation generation complete!${NC}"
echo "Please check and complete the documentation for each plugin."
