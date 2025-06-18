# Fast-Fail Concrete Code Changes

## 1. Enhanced Exception Classes (panther/core/exceptions/fast_fail.py)

```python
# Add after existing imports
import socket
from typing import List, Optional, Dict, Any

# Add new ErrorCategory values
class ErrorCategory(Enum):
    """Categories of errors for specific handling."""
    DOCKER_BUILD = "docker_build"
    DOCKER_RUNTIME = "docker_runtime" 
    PLUGIN_LOAD = "plugin_load"
    SERVICE_START = "service_start"
    NETWORK_SETUP = "network_setup"
    COMMAND_EXECUTION = "command_execution"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    SECURITY = "security"
    TEST_FRAMEWORK = "test_framework"
    CASCADE = "cascade"

# Add new exception classes
class NetworkSetupException(PantherException):
    """Network initialization or setup failure."""
    def __init__(self, message: str, network_type: str, details: str):
        context = {
            "network_type": network_type,
            "details": details,
        }
        super().__init__(message, ErrorSeverity.CRITICAL, ErrorCategory.NETWORK_SETUP, context)

class PortConflictException(PantherException):
    """Port binding conflict detected."""
    def __init__(self, message: str, port: int, service: str):
        context = {
            "port": port,
            "service": service,
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.NETWORK_SETUP, context)

class IvyCompilationException(PantherException):
    """Ivy test compilation failure."""
    def __init__(self, message: str, test_name: str, output: str, exit_code: int):
        context = {
            "test_name": test_name,
            "compilation_output": output[:500],  # Truncate
            "exit_code": exit_code
        }
        super().__init__(message, ErrorSeverity.CRITICAL, ErrorCategory.TEST_FRAMEWORK, context)

class ResourceExhaustionException(PantherException):
    """System resource exhaustion."""
    def __init__(self, message: str, resource_type: str, available: float, required: float):
        context = {
            "resource_type": resource_type,
            "available": available,
            "required": required
        }
        super().__init__(message, ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE, context)

class CertificateException(PantherException):
    """Certificate generation or validation failure."""
    def __init__(self, message: str, cert_path: str, error: str):
        context = {
            "cert_path": cert_path,
            "error": error
        }
        super().__init__(message, ErrorSeverity.CRITICAL, ErrorCategory.SECURITY, context)

class TimeoutCascadeException(PantherException):
    """Multiple consecutive timeouts detected."""
    def __init__(self, message: str, count: int, services: List[str]):
        context = {
            "timeout_count": count,
            "affected_services": services
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.CASCADE, context)
```

## 2. Port Conflict Detection (panther/plugins/environments/network_environment/docker_compose/docker_compose.py)

```python
# Add imports
import socket
from panther.core.exceptions.fast_fail import PortConflictException, ResourceExhaustionException

# Add method to DockerComposeNetworkEnvironment class
def _check_port_availability(self, services: Dict[str, Any]) -> None:
    """Check if required ports are available before starting containers."""
    for service_name, service_config in services.items():
        ports = service_config.get('ports', [])
        for port_mapping in ports:
            if ':' in port_mapping:
                host_port = int(port_mapping.split(':')[0])
                
                # Check if port is available
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', host_port))
                sock.close()
                
                if result == 0:
                    raise PortConflictException(
                        f"Port {host_port} is already in use, cannot start {service_name}",
                        host_port,
                        service_name
                    )
                    
def _check_disk_space(self, required_gb: float = 2.0) -> None:
    """Check available disk space before building images."""
    import shutil
    
    stat = shutil.disk_usage('/')
    available_gb = stat.free / (1024**3)
    
    if available_gb < required_gb:
        raise ResourceExhaustionException(
            f"Insufficient disk space for Docker operations",
            "disk_space",
            available_gb,
            required_gb
        )

# Modify prepare() method
def prepare(self) -> None:
    """Prepare the Docker Compose environment with enhanced checks."""
    try:
        self.logger.info("Preparing Docker Compose environment...")
        
        # Check disk space first
        self._check_disk_space()
        
        # Check port availability
        self._check_port_availability(self.services)
        
        # ... rest of existing prepare code ...
```

## 3. Ivy Compilation Handling (panther/plugins/services/testers/panther_ivy/panther_ivy.py)

```python
# Add import
from panther.core.exceptions.fast_fail import IvyCompilationException

# Modify generate_deployment_commands() method
def generate_deployment_commands(self, service_name, output_dir, docker_networks=None):
    """Generate deployment commands with compilation check."""
    # ... existing code ...
    
    # Add compilation check
    if self.test:
        compile_result = self._compile_ivy_test(self.test)
        if not compile_result['success']:
            raise IvyCompilationException(
                f"Failed to compile Ivy test '{self.test}'",
                self.test,
                compile_result['output'],
                compile_result['exit_code']
            )
    
    # ... rest of existing code ...

# Add helper method
def _compile_ivy_test(self, test_name: str) -> Dict[str, Any]:
    """Compile Ivy test and return result."""
    import subprocess
    
    compile_cmd = [
        "python", "build.py",
        f"test={test_name}",
        f"protocol={self.config.get('protocol', 'quic')}"
    ]
    
    try:
        result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=self.ivy_src_dir
        )
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout + result.stderr,
            'exit_code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': 'Compilation timed out after 300 seconds',
            'exit_code': -1
        }
```

## 4. Certificate Validation (panther/plugins/services/base/service_command_builder.py)

```python
# Add import
from panther.core.exceptions.fast_fail import CertificateException

# Add certificate validation method
def validate_certificates(self, cert_config: Dict[str, Any]) -> None:
    """Validate certificate files exist and are readable."""
    cert_path = cert_config.get('cert', {}).get('file')
    key_path = cert_config.get('key', {}).get('file')
    
    for path, path_type in [(cert_path, 'certificate'), (key_path, 'key')]:
        if path and not os.path.exists(path):
            # Try to generate if missing
            try:
                self._generate_certificate(path)
            except Exception as e:
                raise CertificateException(
                    f"Failed to generate {path_type}",
                    path,
                    str(e)
                )
        
        # Verify file is readable
        if path and not os.access(path, os.R_OK):
            raise CertificateException(
                f"{path_type} file exists but is not readable",
                path,
                "Permission denied"
            )
```

## 5. Update Experiment Manager (panther/core/experiment_manager.py)

```python
# Add imports
from panther.core.exceptions.fast_fail import (
    FastFailHandler,
    ErrorSeverity,
    ErrorCategory,
    DockerComposeException,
    PortConflictException,
    IvyCompilationException,
    ResourceExhaustionException,
    CertificateException,
    TimeoutCascadeException,
)

# Update exception handling in run_tests() method
except (
    TestCaseInitializationError,
    TestExecutionError,
    ValueError,
    TypeError,
    AttributeError,
    RuntimeError,
    OSError,
    PantherExperimentError,
    subprocess.CalledProcessError,
    DockerComposeException,
    PortConflictException,
    IvyCompilationException,
    ResourceExhaustionException,
    CertificateException,
    TimeoutCascadeException,
) as test_error:
    # Existing error handling code...
    
    # Add specific handling for critical infrastructure errors
    if isinstance(test_error, (
        DockerComposeException,
        PortConflictException, 
        IvyCompilationException,
        ResourceExhaustionException,
        CertificateException
    )):
        # These are always critical - use fast-fail handler
        should_continue = self.fast_fail_handler.handle_error(
            test_error, raise_on_critical=False
        )
        if not should_continue:
            self.logger.critical(
                "Critical infrastructure error in test %s, terminating experiment: %s",
                test_case.test_config.name,
                str(test_error)
            )
            # Emit experiment failure
            self.experiment_emitter.emit_finished_early(
                reason=f"Critical {test_error.category.value} Failure",
                details={
                    "test_name": test_case.test_config.name,
                    "error_type": type(test_error).__name__,
                    "error_details": test_error.context,
                }
            )
            raise test_error  # Stop experiment
```

## 6. Enhanced Config Schema (panther/config/config_global_schema.py)

```python
@dataclass
class FastFailConfig:
    """Enhanced configuration for fast-fail behavior."""
    # Basic switches
    enabled: bool = True
    docker_build_failures: bool = True
    docker_runtime_failures: bool = True
    plugin_load_failures: bool = True  
    service_start_failures: bool = True
    
    # New categories
    network_setup_failures: bool = True
    port_conflict_failures: bool = True
    ivy_compilation_failures: bool = True
    resource_exhaustion: bool = True
    certificate_failures: bool = True
    timeout_cascades: bool = True
    
    # Thresholds
    timeout_cascade_threshold: int = 3
    disk_space_threshold_gb: float = 1.0
    
    # Control options
    critical_only: bool = False
    max_errors_before_fail: int = 0  # 0 = unlimited
```

## 7. Timeout Cascade Detection (panther/core/test_cases/test_case_impl.py)

```python
# Add imports
from panther.core.exceptions.fast_fail import TimeoutCascadeException
from collections import deque
from datetime import datetime, timedelta

# Add to TestCase.__init__
self.timeout_history: deque = deque(maxlen=10)  # Track last 10 timeouts

# Add method
def _check_timeout_cascade(self, service_name: str) -> None:
    """Check for timeout cascade and raise exception if detected."""
    now = datetime.now()
    self.timeout_history.append((now, service_name))
    
    # Count recent timeouts (within 5 minutes)
    cutoff_time = now - timedelta(minutes=5)
    recent_timeouts = [
        (t, s) for t, s in self.timeout_history 
        if t > cutoff_time
    ]
    
    threshold = self.global_config.fast_fail.timeout_cascade_threshold
    if len(recent_timeouts) >= threshold:
        services = list(set(s for _, s in recent_timeouts))
        raise TimeoutCascadeException(
            f"Timeout cascade detected in test '{self.test_config.name}'",
            len(recent_timeouts),
            services
        )

# Modify run() method - add after timeout exceptions
except subprocess.TimeoutExpired as e:
    self.logger.error(f"Service {service_name} timed out")
    self._check_timeout_cascade(service_name)
    # ... rest of timeout handling ...
```

## Usage Example

```yaml
# experiment_config.yaml
fast_fail:
  enabled: true
  port_conflict_failures: true
  ivy_compilation_failures: true
  resource_exhaustion: true
  disk_space_threshold_gb: 2.0
  timeout_cascade_threshold: 2

tests:
  - name: "Comprehensive QUIC Test"
    services:
      server:
        implementation:
          name: picoquic
        ports:
          - "4443:4443"  # Will check port availability
      ivy_client:
        implementation:
          name: panther_ivy
          test: quic_complex_test  # Will verify compilation
```

These concrete code changes implement the most critical fast-fail features while maintaining backward compatibility.