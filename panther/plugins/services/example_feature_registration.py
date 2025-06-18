"""
Example showing how new plugins can register themselves for feature logging.

This demonstrates multiple registration methods for new plugins and modules.
"""

from panther.core.utils.feature_registry import (
    feature_logger,
    register_feature,
    register_module_feature,
)
from panther.core.utils.logging_mixin import LoggerMixin

# Method 1: Direct registration in module
# Register this module for a custom feature
register_module_feature(__name__, "example_plugin")

# Register additional patterns for this feature
register_feature("example_plugin", ["example", "demo", "sample"])


# Method 2: Decorator-based registration
@feature_logger("custom_protocol", ["custom", "proto"])
class CustomProtocolManager(LoggerMixin):
    """Example service manager with automatic feature registration."""

    def __init__(self):
        super().__init__()
        # Logging will automatically use 'custom_protocol' feature levels
        self.info("CustomProtocolManager initialized with feature logging")

    def process_request(self):
        self.debug("Processing custom protocol request")
        self.trace("Detailed trace information for custom protocol")


# Method 3: Manual registration for existing classes
class LegacyService:
    """Example of registering an existing class without decorator."""

    def __init__(self):
        # Register this class manually
        register_module_feature(f"{__name__}.LegacyService", "legacy_operations")
        register_feature("legacy_operations", ["legacy", "old"])


# Method 4: Plugin-specific feature registration
def register_plugin_features():
    """
    Function that plugins can call to register their specific features.
    This can be called from plugin __init__.py files.
    """

    # Register a new feature category
    register_feature("distributed_testing", ["distributed", "cluster", "multi_node"])

    # Register specific modules for the feature
    register_module_feature(
        "panther.plugins.environments.kubernetes", "distributed_testing"
    )
    register_module_feature("panther.plugins.environments.nomad", "distributed_testing")

    # Register protocol-specific features
    register_feature("http3_operations", ["http3", "h3", "quic_http"])

    # Register implementation-specific features
    register_feature("rust_implementations", ["rust", "cargo", "rustc"])


# Method 5: Registration in plugin manifest
PLUGIN_FEATURES = {
    "feature": "example_plugin",
    "patterns": ["example", "demo"],
    "modules": [
        "panther.plugins.services.example.manager",
        "panther.plugins.services.example.client",
    ],
}


def auto_register_from_manifest():
    """Register features from plugin manifest."""
    feature = PLUGIN_FEATURES["feature"]
    patterns = PLUGIN_FEATURES["patterns"]
    modules = PLUGIN_FEATURES.get("modules", [])

    # Register patterns
    register_feature(feature, patterns)

    # Register specific modules
    for module in modules:
        register_module_feature(module, feature)


# Example usage for new QUIC implementation
@feature_logger("msquic_operations", ["msquic", "microsoft"])
class MSQuicServiceManager(LoggerMixin):
    """Microsoft QUIC implementation with feature-specific logging."""

    def __init__(self):
        super().__init__()
        self.info("MSQuic service manager initialized")

        # This will use 'msquic_operations' feature logging level
        self.debug("MSQuic debug information")
        self.trace("MSQuic trace details")

    def generate_command(self):
        self.debug("Generating MSQuic command")
        return "msquic_server --port 4443"


# Example for new network environment
@feature_logger(
    "kubernetes_environment", ["k8s", "kubernetes", "container_orchestration"]
)
class KubernetesEnvironment(LoggerMixin):
    """Kubernetes network environment with dedicated feature logging."""

    def __init__(self):
        super().__init__()
        self.info("Kubernetes environment initialized")

    def deploy(self):
        self.debug("Deploying to Kubernetes cluster")
        self.trace("K8s manifest details...")


# Call registration function when module is imported
if __name__ == "__main__":
    register_plugin_features()
    auto_register_from_manifest()

    # Test the registration
    from panther.core.utils.feature_registry import feature_registry

    print("Registered features:")
    for feature in feature_registry.get_all_features():
        modules = feature_registry.get_modules_for_feature(feature)
        print(f"  {feature}: {list(modules)}")

    # Test feature detection
    test_modules = [
        "panther.plugins.services.example.manager",
        "panther.plugins.environments.kubernetes.k8s_env",
        "panther.services.msquic.client",
    ]

    print("\nFeature detection test:")
    for module in test_modules:
        feature = feature_registry.detect_feature(module)
        print(f"  {module} -> {feature}")
