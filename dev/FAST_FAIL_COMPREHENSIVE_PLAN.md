# Comprehensive Fast-Fail Implementation Plan for PANTHER

## Overview
This document outlines a complete fast-fail implementation strategy for PANTHER, covering all critical failure points and providing graceful degradation where appropriate.

## New Exception Classes to Add

### 1. Network and Infrastructure Exceptions

```python
# In panther/core/exceptions/fast_fail.py

class NetworkSetupException(PantherException):
    """Network initialization or setup failure."""
    def __init__(self, message: str, network_type: str, details: str):
        context = {
            "network_type": network_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        super().__init__(message, ErrorSeverity.CRITICAL, ErrorCategory.NETWORK_SETUP, context)

class PortConflictException(PantherException):
    """Port binding conflict detected."""
    def __init__(self, message: str, port: int, service: str, existing_process: Optional[str] = None):
        context = {
            "port": port,
            "service": service,
            "existing_process": existing_process
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.NETWORK_SETUP, context)

class ResourceExhaustionException(PantherException):
    """System resource exhaustion (disk, memory, CPU)."""
    def __init__(self, message: str, resource_type: str, current_value: float, threshold: float):
        context = {
            "resource_type": resource_type,
            "current_value": current_value,
            "threshold": threshold,
            "percentage_used": (current_value / threshold * 100) if threshold > 0 else 100
        }
        severity = ErrorSeverity.CRITICAL if resource_type == "disk_space" else ErrorSeverity.HIGH
        super().__init__(message, severity, ErrorCategory.RESOURCE, context)
```

### 2. Security and Authentication Exceptions

```python
class CertificateException(PantherException):
    """Certificate generation or validation failure."""
    def __init__(self, message: str, cert_type: str, cert_path: str, error_detail: str):
        context = {
            "cert_type": cert_type,
            "cert_path": cert_path,
            "error_detail": error_detail
        }
        super().__init__(message, ErrorSeverity.CRITICAL, ErrorCategory.SECURITY, context)

class AuthenticationException(PantherException):
    """Authentication or authorization failure."""
    def __init__(self, message: str, auth_type: str, service: str):
        context = {
            "auth_type": auth_type,
            "service": service
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.SECURITY, context)
```

### 3. Test Framework Exceptions

```python
class IvyCompilationException(PantherException):
    """Ivy test compilation failure."""
    def __init__(self, message: str, test_name: str, compilation_output: str, exit_code: int):
        context = {
            "test_name": test_name,
            "compilation_output": compilation_output[:1000],  # Truncate for logging
            "exit_code": exit_code
        }
        super().__init__(message, ErrorSeverity.CRITICAL, ErrorCategory.TEST_FRAMEWORK, context)

class CriticalAssertionException(PantherException):
    """Critical test assertion failure."""
    def __init__(self, message: str, assertion_type: str, expected: Any, actual: Any):
        context = {
            "assertion_type": assertion_type,
            "expected": str(expected),
            "actual": str(actual)
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.TEST_EXECUTION, context)
```

### 4. Configuration and Dependency Exceptions

```python
class ConfigurationException(PantherException):
    """Configuration validation or parsing error."""
    def __init__(self, message: str, config_file: str, field: str, validation_error: str):
        context = {
            "config_file": config_file,
            "field": field,
            "validation_error": validation_error
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.CONFIGURATION, context)

class DependencyException(PantherException):
    """Dependency resolution or version mismatch."""
    def __init__(self, message: str, dependency: str, required_version: str, found_version: Optional[str] = None):
        context = {
            "dependency": dependency,
            "required_version": required_version,
            "found_version": found_version or "not found"
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.DEPENDENCY, context)
```

### 5. Cascade Detection Exceptions

```python
class TimeoutCascadeException(PantherException):
    """Multiple consecutive timeouts detected."""
    def __init__(self, message: str, timeout_count: int, services: List[str], threshold: int = 3):
        context = {
            "timeout_count": timeout_count,
            "services": services,
            "threshold": threshold
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.TIMEOUT, context)

class ErrorCascadeException(PantherException):
    """Multiple errors of same type in succession."""
    def __init__(self, message: str, error_type: str, error_count: int, threshold: int):
        context = {
            "error_type": error_type,
            "error_count": error_count,
            "threshold": threshold
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.CASCADE, context)
```

## Implementation Plan by File

### 1. `panther/core/exceptions/fast_fail.py`

**Actions:**
- Add all new exception classes above
- Add new ErrorCategory enums: SECURITY, TEST_FRAMEWORK, TEST_EXECUTION, DEPENDENCY, CASCADE
- Enhance FastFailHandler with pattern matching and cascade detection

```python
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
    TEST_EXECUTION = "test_execution"
    DEPENDENCY = "dependency"
    CASCADE = "cascade"

class FastFailHandler:
    """Enhanced handler with cascade detection."""
    
    def __init__(self, enabled: bool = True, logger: Optional[logging.Logger] = None):
        # ... existing code ...
        self.error_history: List[Tuple[datetime, PantherException]] = []
        self.cascade_thresholds = {
            ErrorCategory.TIMEOUT: 3,
            ErrorCategory.DOCKER_RUNTIME: 2,
            ErrorCategory.SERVICE_START: 3,
        }
    
    def detect_cascade(self, error: PantherException) -> Optional[ErrorCascadeException]:
        """Detect if we're in an error cascade situation."""
        # Check recent errors of same category
        recent_errors = [
            e for t, e in self.error_history[-10:]
            if e.category == error.category and 
            (datetime.now() - t).seconds < 300  # Within 5 minutes
        ]
        
        threshold = self.cascade_thresholds.get(error.category, 5)
        if len(recent_errors) >= threshold:
            return ErrorCascadeException(
                f"Cascade detected: {len(recent_errors)} {error.category.value} errors",
                error.category.value,
                len(recent_errors),
                threshold
            )
        return None
```

### 2. `panther/plugins/environments/network_environment/docker_compose/docker_compose.py`

**Actions:**
- Add port conflict detection before docker-compose up
- Add disk space validation before building
- Enhance error handling with specific exceptions

```python
def _check_port_availability(self, ports: List[str]) -> None:
    """Check if required ports are available."""
    for port_mapping in ports:
        host_port = int(port_mapping.split(':')[0])
        
        # Check if port is in use
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', host_port))
        sock.close()
        
        if result == 0:
            # Port is in use, try to find what's using it
            try:
                result = subprocess.run(
                    ['lsof', '-i', f':{host_port}'],
                    capture_output=True,
                    text=True
                )
                process_info = result.stdout if result.returncode == 0 else "unknown process"
            except:
                process_info = "unknown process"
            
            raise PortConflictException(
                f"Port {host_port} is already in use",
                host_port,
                self.name,
                process_info
            )

def _check_disk_space(self, required_gb: float = 5.0) -> None:
    """Check available disk space before operations."""
    import shutil
    
    stat = shutil.disk_usage('/')
    available_gb = stat.free / (1024**3)
    
    if available_gb < required_gb:
        raise ResourceExhaustionException(
            f"Insufficient disk space: {available_gb:.2f}GB available, {required_gb}GB required",
            "disk_space",
            available_gb,
            required_gb
        )
```

### 3. `panther/plugins/services/testers/panther_ivy/panther_ivy.py`

**Actions:**
- Wrap Ivy compilation with proper exception handling
- Add compilation output capture and error reporting

```python
def _compile_ivy_test(self, test_name: str) -> None:
    """Compile Ivy test with enhanced error handling."""
    compile_cmd = [
        "python", "build.py", 
        f"test={test_name}",
        f"protocol={self.protocol}"
    ]
    
    try:
        result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=self.ivy_dir
        )
        
        if result.returncode != 0:
            raise IvyCompilationException(
                f"Ivy compilation failed for test {test_name}",
                test_name,
                result.stdout + result.stderr,
                result.returncode
            )
            
    except subprocess.TimeoutExpired:
        raise IvyCompilationException(
            f"Ivy compilation timed out for test {test_name}",
            test_name,
            "Compilation exceeded 300 second timeout",
            -1
        )
```

### 4. `panther/core/config/config_manager.py`

**Actions:**
- Add comprehensive validation with specific exceptions
- Check for circular dependencies and missing references

```python
def validate_configuration(self, config: Dict[str, Any]) -> None:
    """Validate configuration with fast-fail exceptions."""
    # Check required fields
    required_fields = ['tests', 'logging', 'paths']
    for field in required_fields:
        if field not in config:
            raise ConfigurationException(
                f"Missing required configuration field: {field}",
                self.config_file,
                field,
                "Field is required but not present"
            )
    
    # Validate plugin references
    for test in config.get('tests', []):
        for service_name, service in test.get('services', {}).items():
            plugin_name = service.get('implementation', {}).get('name')
            plugin_type = service.get('implementation', {}).get('type')
            
            if not self._plugin_exists(plugin_name, plugin_type):
                raise ConfigurationException(
                    f"Referenced plugin does not exist: {plugin_name}",
                    self.config_file,
                    f"tests.services.{service_name}.implementation",
                    f"Plugin '{plugin_name}' of type '{plugin_type}' not found"
                )
```

### 5. `panther/core/test_cases/test_case_impl.py`

**Actions:**
- Add timeout cascade detection
- Track consecutive failures
- Implement critical assertion handling

```python
class TestCase:
    def __init__(self, ...):
        # ... existing code ...
        self.timeout_history: List[Tuple[datetime, str]] = []
        self.assertion_failures: List[CriticalAssertionException] = []
    
    def _check_timeout_cascade(self, service_name: str) -> None:
        """Check for timeout cascade pattern."""
        now = datetime.now()
        self.timeout_history.append((now, service_name))
        
        # Check recent timeouts (within last 10 minutes)
        recent_timeouts = [
            (t, s) for t, s in self.timeout_history
            if (now - t).seconds < 600
        ]
        
        if len(recent_timeouts) >= 3:
            services = list(set(s for _, s in recent_timeouts))
            raise TimeoutCascadeException(
                f"Multiple timeouts detected in test {self.test_config.name}",
                len(recent_timeouts),
                services
            )
    
    def assert_critical(self, condition: bool, message: str, expected: Any, actual: Any):
        """Critical assertion that can trigger fast-fail."""
        if not condition:
            exc = CriticalAssertionException(
                message,
                "critical_assertion",
                expected,
                actual
            )
            self.assertion_failures.append(exc)
            
            # Check if we should fail fast on assertions
            if self.global_config.fast_fail.critical_assertions:
                raise exc
```

### 6. `panther/plugins/environments/network_environment/mixins/error_handler.py`

**Actions:**
- Create centralized error classification
- Map error patterns to appropriate exceptions

```python
class ErrorClassifier:
    """Classify errors and determine appropriate exception type."""
    
    ERROR_PATTERNS = {
        r".*address already in use.*": (PortConflictException, {"port": r":(\d+)"}),
        r".*no space left on device.*": (ResourceExhaustionException, {"resource_type": "disk_space"}),
        r".*certificate.*failed.*": (CertificateException, {"cert_type": "unknown"}),
        r".*compilation failed.*": (IvyCompilationException, {"test_name": r"test[_=](\w+)"}),
        r".*timeout.*exceeded.*": (TimeoutCascadeException, {"service": r"service[_=](\w+)"}),
    }
    
    @classmethod
    def classify_error(cls, error_message: str, context: Dict[str, Any]) -> Optional[PantherException]:
        """Classify error message and return appropriate exception."""
        for pattern, (exc_class, extractors) in cls.ERROR_PATTERNS.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                # Extract additional context from error message
                extracted = {}
                for key, extractor in extractors.items():
                    match = re.search(extractor, error_message)
                    if match:
                        extracted[key] = match.group(1)
                
                # Merge with provided context
                full_context = {**context, **extracted}
                
                # Create appropriate exception
                return cls._create_exception(exc_class, error_message, full_context)
        
        return None
```

### 7. `panther/core/observer/impl/storage_observer.py`

**Actions:**
- Monitor disk space during experiment
- Emit warnings and trigger fast-fail on critical thresholds

```python
class StorageObserver:
    def __init__(self, ...):
        # ... existing code ...
        self.disk_check_interval = 30  # seconds
        self.last_disk_check = time.time()
        self.disk_warning_threshold = 1.0  # GB
        self.disk_critical_threshold = 0.5  # GB
    
    def _check_disk_space(self):
        """Periodic disk space check."""
        current_time = time.time()
        if current_time - self.last_disk_check < self.disk_check_interval:
            return
        
        import shutil
        stat = shutil.disk_usage(self.storage_path)
        available_gb = stat.free / (1024**3)
        
        if available_gb < self.disk_critical_threshold:
            raise ResourceExhaustionException(
                f"Critical: Only {available_gb:.2f}GB disk space remaining",
                "disk_space",
                available_gb,
                self.disk_critical_threshold
            )
        elif available_gb < self.disk_warning_threshold:
            self.logger.warning(
                f"Low disk space warning: {available_gb:.2f}GB remaining"
            )
        
        self.last_disk_check = current_time
```

### 8. `panther/config/config_global_schema.py`

**Actions:**
- Extend FastFailConfig with granular controls

```python
@dataclass
class FastFailConfig:
    """Enhanced configuration for fast-fail behavior."""
    enabled: bool = True
    docker_build_failures: bool = True
    docker_runtime_failures: bool = True
    plugin_load_failures: bool = True
    service_start_failures: bool = True
    network_setup_failures: bool = True
    certificate_failures: bool = True
    ivy_compilation_failures: bool = True
    resource_exhaustion: bool = True
    timeout_cascades: bool = True
    critical_assertions: bool = False  # Default off, user must opt-in
    
    # Thresholds
    timeout_cascade_threshold: int = 3
    error_cascade_threshold: int = 5
    disk_space_threshold_gb: float = 1.0
    memory_threshold_percent: float = 90.0
    
    # Selective categories
    critical_only: bool = False
    ignored_categories: List[str] = field(default_factory=list)
    max_errors_before_fail: int = 0  # 0 = unlimited
```

## Usage Examples

### Example 1: Port Conflict Handling

```yaml
# experiment_config.yaml
fast_fail:
  enabled: true
  network_setup_failures: true

tests:
  - name: "Test with specific ports"
    services:
      server:
        ports:
          - "8080:8080"  # Will fail fast if port already in use
```

### Example 2: Ivy Compilation with Fast-Fail

```yaml
fast_fail:
  enabled: true
  ivy_compilation_failures: true  # Fail immediately if Ivy can't compile

tests:
  - name: "Formal verification test"
    services:
      ivy_tester:
        implementation:
          name: panther_ivy
          test: quic_complex_test  # Will fail fast if compilation fails
```

### Example 3: Resource Monitoring

```yaml
fast_fail:
  enabled: true
  resource_exhaustion: true
  disk_space_threshold_gb: 2.0  # Fail if less than 2GB available
  
observers:
  storage:
    enabled: true
    monitor_resources: true  # Enable resource monitoring
```

### Example 4: Timeout Cascade Prevention

```yaml
fast_fail:
  enabled: true
  timeout_cascades: true
  timeout_cascade_threshold: 2  # Fail after 2 consecutive timeouts

tests:
  - name: "Network stress test"
    services:
      client:
        timeout: 30  # If multiple services timeout, experiment stops
```

## Migration Guide

1. **Update configuration files** to include new fast_fail options
2. **Replace generic exception handling** with specific PantherException subclasses
3. **Add resource checks** before resource-intensive operations
4. **Implement cascade detection** in test execution loops
5. **Configure thresholds** based on infrastructure capabilities

## Benefits

1. **Fail Fast on Infrastructure Issues**: Don't waste time on doomed experiments
2. **Resource Protection**: Prevent system exhaustion
3. **Better Error Messages**: Specific exceptions with detailed context
4. **Configurable Behavior**: Fine-grained control over what triggers fast-fail
5. **Cascade Prevention**: Stop error avalanches before they consume resources
6. **Graceful Degradation**: Non-critical errors can still allow partial completion

This comprehensive fast-fail system will make PANTHER more robust, user-friendly, and resource-efficient.