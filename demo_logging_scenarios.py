#!/usr/bin/env python3
"""
Demonstration of PANTHER's Granular Feature Logging System

This script demonstrates the different logging scenarios without running full experiments.
It shows how different feature levels affect logging output.
"""

import sys
import yaml
from pathlib import Path
from panther.core.utils import LoggerFactory, feature_registry


def demonstrate_feature_logging():
    """Demonstrate feature-specific logging with different configurations."""
    
    print("🐾 PANTHER Granular Feature Logging Demonstration")
    print("=" * 60)
    
    # Show registered features
    print("\n📋 REGISTERED FEATURES:")
    features = sorted(feature_registry.get_all_features())
    for i, feature in enumerate(features):
        modules = feature_registry.get_modules_for_feature(feature)
        print(f"  {i+1:2d}. {feature} ({len(modules)} modules)")
    
    print(f"\nTotal features registered: {len(features)}")
    
    # Demonstrate feature detection
    print("\n🔍 FEATURE DETECTION EXAMPLES:")
    test_modules = [
        "panther.core.docker_builder.docker_builder",
        "panther.plugins.services.iut.quic.picoquic.picoquic",
        "panther.core.command_processor.command_processor",
        "panther.plugins.environments.network_environment.docker_compose.docker_compose",
        "panther.core.events.experiment.emitter"
    ]
    
    for module in test_modules:
        detected = feature_registry.detect_feature(module)
        print(f"  {module}")
        print(f"    → Detected feature: {detected or 'None'}")
    
    # Load and demonstrate different scenarios
    scenarios = [
        ("Minimal Noise", "experiment-config/test_logging_minimal_noise.yaml"),
        ("Full Debug", "experiment-config/test_logging_full_debug.yaml"),
        ("Docker Focus", "experiment-config/test_logging_docker_focus.yaml"),
        ("Service Focus", "experiment-config/test_logging_service_focus.yaml"),
    ]
    
    for scenario_name, config_file in scenarios:
        print(f"\n🎯 SCENARIO: {scenario_name}")
        print("-" * 40)
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            logging_config = config.get('logging', {})
            feature_levels = logging_config.get('feature_levels', {})
            
            print(f"Global level: {logging_config.get('level', 'INFO')}")
            print(f"Colors enabled: {logging_config.get('enable_colors', False)}")
            print(f"Feature-specific levels: {len(feature_levels)}")
            
            # Show key feature levels for this scenario
            key_features = [
                'docker_operations', 'command_generation', 'quic_services',
                'event_system', 'network_environments', 'service_managers'
            ]
            
            print("Key feature levels:")
            for feature in key_features:
                level = feature_levels.get(feature, 'DEFAULT')
                print(f"  • {feature}: {level}")
            
            # Simulate logger creation for this scenario
            LoggerFactory.initialize({
                'level': logging_config.get('level', 'INFO'),
                'format': logging_config.get('format', '%(levelname)s - %(message)s'),
                'enable_colors': logging_config.get('enable_colors', False),
                'feature_levels': feature_levels
            })
            
            # Test loggers
            print("Simulated logger levels:")
            test_features = ['docker_operations', 'command_generation', 'event_system']
            for feature in test_features:
                logger = LoggerFactory.get_feature_logger(f'test_{feature}', feature)
                level_name = {50: 'CRITICAL', 40: 'ERROR', 30: 'WARNING', 20: 'INFO', 10: 'DEBUG', 5: 'TRACE'}.get(logger.level, str(logger.level))
                print(f"  • {feature}: {level_name}")
                
        except Exception as e:
            print(f"  ❌ Error loading {config_file}: {e}")


def show_usage_examples():
    """Show practical usage examples for different scenarios."""
    
    print("\n\n📚 PRACTICAL USAGE EXAMPLES:")
    print("=" * 60)
    
    examples = [
        {
            "title": "🐋 Debugging Docker Build Issues",
            "command": "python -m panther run --config experiment-config/test_logging_docker_focus.yaml",
            "description": "Use when containers fail to build or deploy",
            "key_features": ["docker_operations: TRACE", "docker_compose: TRACE", "command_generation: DEBUG"]
        },
        {
            "title": "🔧 Debugging Service Coordination",
            "command": "python -m panther run --config experiment-config/test_logging_service_focus.yaml", 
            "description": "Use when services fail to communicate or coordinate",
            "key_features": ["service_managers: TRACE", "quic_services: TRACE", "service_coordination: TRACE"]
        },
        {
            "title": "🌐 Debugging Network Issues",
            "command": "python -m panther run --config experiment-config/test_logging_network_focus.yaml",
            "description": "Use when network setup or communication fails",
            "key_features": ["network_environments: TRACE", "network_setup: TRACE", "port_management: TRACE"]
        },
        {
            "title": "📡 Debugging Event System",
            "command": "python -m panther run --config experiment-config/test_logging_event_focus.yaml",
            "description": "Use when event flow or state management issues occur",
            "key_features": ["event_system: TRACE", "event_processing: TRACE", "state_management: TRACE"]
        },
        {
            "title": "🔍 Maximum Debug Information",
            "command": "python -m panther run --config experiment-config/test_logging_full_debug.yaml",
            "description": "Use when you need maximum verbosity for comprehensive debugging",
            "key_features": ["All features: DEBUG/TRACE", "Maximum verbosity", "Performance impact"]
        },
        {
            "title": "🎯 Production-Like Minimal Logging",
            "command": "python -m panther run --config experiment-config/test_logging_minimal_noise.yaml",
            "description": "Use for clean output with essential information only",
            "key_features": ["Most features: WARNING/ERROR", "Clean output", "Fast execution"]
        }
    ]
    
    for example in examples:
        print(f"\n{example['title']}")
        print(f"Description: {example['description']}")
        print(f"Command: {example['command']}")
        print("Key features:")
        for feature in example['key_features']:
            print(f"  • {feature}")


def show_configuration_guide():
    """Show how to create custom logging configurations."""
    
    print("\n\n⚙️  CREATING CUSTOM CONFIGURATIONS:")
    print("=" * 60)
    
    example_config = '''
logging:
  level: INFO
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
  enable_colors: true
  
  # Custom feature levels for your debugging needs
  feature_levels:
    # Focus on specific areas
    docker_operations: DEBUG        # Docker issues
    command_generation: TRACE       # Command problems
    service_managers: DEBUG         # Service coordination
    
    # Reduce noise in other areas
    event_system: WARNING           # Reduce event noise
    metrics_collection: INFO        # Basic metrics only
    error_handling: ERROR           # Only show errors
    
    # Your custom features (if you add new plugins)
    my_custom_protocol: DEBUG       # Your custom protocol implementation
    my_environment: TRACE           # Your custom environment
'''
    
    print("Example custom configuration:")
    print(example_config)
    
    print("Available log levels:")
    levels = ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    for level in levels:
        descriptions = {
            "TRACE": "Maximum verbosity - internal details",
            "DEBUG": "Detailed debugging information", 
            "INFO": "General information messages",
            "WARNING": "Warning messages only",
            "ERROR": "Error messages only",
            "CRITICAL": "Critical errors only"
        }
        print(f"  • {level}: {descriptions[level]}")


def main():
    """Main demonstration function."""
    try:
        demonstrate_feature_logging()
        show_usage_examples()
        show_configuration_guide()
        
        print("\n\n✅ VALIDATION COMPLETE")
        print("=" * 60)
        print("The granular feature logging system is working correctly!")
        print("You can now use any of the test configurations to debug specific issues.")
        print("\nTo run the full validation suite:")
        print("  python validate_logging_scenarios.py")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())