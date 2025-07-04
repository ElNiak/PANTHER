"""OpenTelemetry observability manager for ATLAS MCP."""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Core OpenTelemetry imports
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.semantic_conventions.resource import ResourceAttributes
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = metrics = None
    # Create dummy classes for fallback
    class Resource:
        def __init__(self, *args, **kwargs):
            pass
    
    class TracerProvider:
        def __init__(self, *args, **kwargs):
            pass
        def add_span_processor(self, *args):
            pass
    
    class MeterProvider:
        def __init__(self, *args, **kwargs):
            pass

# Optional exporters - import individually
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False
    OTLPSpanExporter = OTLPMetricExporter = None

try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    JAEGER_AVAILABLE = True
except ImportError:
    JAEGER_AVAILABLE = False
    JaegerExporter = None

try:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    PrometheusMetricReader = None

try:
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    LOGGING_INSTRUMENTATION_AVAILABLE = True
except ImportError:
    LOGGING_INSTRUMENTATION_AVAILABLE = False
    LoggingInstrumentor = None

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Centralized OpenTelemetry configuration and management."""
    
    def __init__(self, service_name: str = "atlas-mcp", service_version: str = "1.0.0"):
        """Initialize observability manager.
        
        Args:
            service_name: Name of the service for telemetry
            service_version: Version of the service
        """
        self.service_name = service_name
        self.service_version = service_version
        self.enabled = OTEL_AVAILABLE and os.environ.get('OTEL_ENABLED', 'true').lower() == 'true'
        
        # Telemetry objects
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self.tracer = None
        self.meter = None
        
        # Configuration
        self.config = self._load_config()
        
        if self.enabled:
            self._setup_telemetry()
        else:
            logger.warning("OpenTelemetry disabled - observability features unavailable")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load OpenTelemetry configuration from environment."""
        return {
            # Service configuration
            'service_name': os.environ.get('OTEL_SERVICE_NAME', self.service_name),
            'service_version': os.environ.get('OTEL_SERVICE_VERSION', self.service_version),
            'deployment_environment': os.environ.get('DEPLOYMENT_ENV', 'development'),
            
            # Exporter configuration
            'otlp_endpoint': os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT'),
            'jaeger_endpoint': os.environ.get('JAEGER_ENDPOINT'),
            'prometheus_enabled': os.environ.get('PROMETHEUS_ENABLED', 'false').lower() == 'true',
            'console_exporter': os.environ.get('OTEL_CONSOLE_EXPORTER', 'true').lower() == 'true',
            
            # Sampling configuration
            'trace_sample_rate': float(os.environ.get('OTEL_TRACE_SAMPLE_RATE', '1.0')),
            'metrics_export_interval': int(os.environ.get('OTEL_METRICS_EXPORT_INTERVAL', '60')),
            
            # Custom attributes
            'atlas_project': os.environ.get('ATLAS_PROJECT', 'unknown'),
            'atlas_version': os.environ.get('ATLAS_VERSION', 'unknown')
        }
    
    def _setup_telemetry(self) -> None:
        """Setup OpenTelemetry tracing and metrics."""
        try:
            # Create resource with service information
            resource = Resource.create({
                SERVICE_NAME: self.config['service_name'],
                SERVICE_VERSION: self.config['service_version'],
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.config['deployment_environment'],
                "atlas.project": self.config['atlas_project'],
                "atlas.version": self.config['atlas_version']
            })
            
            # Setup tracing
            self._setup_tracing(resource)
            
            # Setup metrics
            self._setup_metrics(resource)
            
            # Setup logging instrumentation if available
            if LOGGING_INSTRUMENTATION_AVAILABLE:
                LoggingInstrumentor().instrument(set_logging_format=True)
            
            logger.info(f"OpenTelemetry initialized for {self.config['service_name']}")
            
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry: {e}")
            self.enabled = False
    
    def _setup_tracing(self, resource: Resource) -> None:
        """Setup distributed tracing."""
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Add span processors based on configuration
        if self.config['console_exporter']:
            console_processor = BatchSpanProcessor(ConsoleSpanExporter())
            self.tracer_provider.add_span_processor(console_processor)
        
        if self.config['otlp_endpoint'] and OTLP_AVAILABLE:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config['otlp_endpoint'],
                insecure=True  # Use secure=True in production with TLS
            )
            otlp_processor = BatchSpanProcessor(otlp_exporter)
            self.tracer_provider.add_span_processor(otlp_processor)
        
        if self.config['jaeger_endpoint'] and JAEGER_AVAILABLE:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.config['jaeger_endpoint'].split('://')[1].split(':')[0],
                agent_port=int(self.config['jaeger_endpoint'].split(':')[-1])
            )
            jaeger_processor = BatchSpanProcessor(jaeger_exporter)
            self.tracer_provider.add_span_processor(jaeger_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        self.tracer = trace.get_tracer(__name__)
    
    def _setup_metrics(self, resource: Resource) -> None:
        """Setup metrics collection."""
        readers = []
        
        # Console metrics exporter
        if self.config['console_exporter']:
            console_reader = PeriodicExportingMetricReader(
                exporter=ConsoleMetricExporter(),
                export_interval_millis=self.config['metrics_export_interval'] * 1000
            )
            readers.append(console_reader)
        
        # Prometheus metrics exporter
        if self.config['prometheus_enabled'] and PROMETHEUS_AVAILABLE:
            prometheus_reader = PrometheusMetricReader()
            readers.append(prometheus_reader)
        
        # OTLP metrics exporter
        if self.config['otlp_endpoint'] and OTLP_AVAILABLE:
            otlp_reader = PeriodicExportingMetricReader(
                exporter=OTLPMetricExporter(
                    endpoint=self.config['otlp_endpoint'],
                    insecure=True
                ),
                export_interval_millis=self.config['metrics_export_interval'] * 1000
            )
            readers.append(otlp_reader)
        
        # Create meter provider
        self.meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(self.meter_provider)
        self.meter = metrics.get_meter(__name__)
    
    def get_tracer(self, name: str = None):
        """Get tracer instance."""
        if not self.enabled:
            return None
        return trace.get_tracer(name or __name__)
    
    def get_meter(self, name: str = None):
        """Get meter instance.""" 
        if not self.enabled:
            return None
        return metrics.get_meter(name or __name__)
    
    def create_span(self, name: str, **kwargs):
        """Create and return a new span."""
        if not self.enabled or not self.tracer:
            return DummySpan()
        return self.tracer.start_span(name, **kwargs)
    
    def get_current_span(self):
        """Get current active span."""
        if not self.enabled:
            return None
        return trace.get_current_span()
    
    def add_span_attributes(self, span, attributes: Dict[str, Any]) -> None:
        """Add attributes to span safely."""
        if not self.enabled or not span:
            return
        
        for key, value in attributes.items():
            try:
                # Convert value to string if needed
                if isinstance(value, (dict, list)):
                    value = str(value)
                span.set_attribute(key, value)
            except Exception as e:
                logger.warning(f"Failed to set span attribute {key}: {e}")
    
    def record_exception(self, span, exception: Exception) -> None:
        """Record exception in span."""
        if not self.enabled or not span:
            return
        try:
            span.record_exception(exception)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
        except Exception as e:
            logger.warning(f"Failed to record exception: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get observability system health status."""
        status = {
            'enabled': self.enabled,
            'otel_available': OTEL_AVAILABLE,
            'service_name': self.config['service_name'],
            'service_version': self.config['service_version'],
            'deployment_environment': self.config['deployment_environment'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self.enabled:
            status.update({
                'tracer_provider': self.tracer_provider is not None,
                'meter_provider': self.meter_provider is not None,
                'exporters': {
                    'console': self.config['console_exporter'],
                    'otlp': bool(self.config['otlp_endpoint']),
                    'jaeger': bool(self.config['jaeger_endpoint']),
                    'prometheus': self.config['prometheus_enabled']
                }
            })
        
        return status
    
    def shutdown(self) -> None:
        """Shutdown observability system gracefully."""
        if not self.enabled:
            return
        
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            logger.info("OpenTelemetry shutdown completed")
        except Exception as e:
            logger.error(f"Error during OpenTelemetry shutdown: {e}")


class DummySpan:
    """Dummy span for when OpenTelemetry is disabled."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def set_attribute(self, key, value):
        pass
    
    def record_exception(self, exception):
        pass
    
    def set_status(self, status):
        pass
    
    def end(self):
        pass