# Docker Build Centralization - Implementation Roadmap

## Phase 1: Core Infrastructure (Week 1-2)

### Task 1.1: Enhance DockerBuilder Class
**File**: `panther/core/docker_builder/docker_builder.py`

```python
# Add these methods to existing DockerBuilder class

def build_with_cache(
    self,
    dockerfile_path: Path,
    context_path: Path,
    cache_key: str,
    build_args: Dict[str, str] = None,
    target: str = None,
    cache_from: List[str] = None
) -> str:
    """Build with cache management."""
    # Check local cache first
    if self.cache_enabled and self.check_cache(cache_key):
        return self.get_cached_image(cache_key)
    
    # Build with cache-from support
    build_kwargs = {
        'path': str(context_path),
        'dockerfile': str(dockerfile_path.relative_to(context_path)),
        'buildargs': build_args or {},
        'cache_from': cache_from or [],
        'target': target,
    }
    
    image, logs = self.client.images.build(**build_kwargs)
    self.cache_image(cache_key, image.tags[0])
    return image.tags[0]

def build_parallel_stages(
    self,
    stages: List[Dict[str, Any]],
    max_workers: int = 4
) -> Dict[str, str]:
    """Build multiple stages in parallel."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        results = {}
        
        for stage in stages:
            if self._can_build_stage(stage, results):
                future = executor.submit(
                    self.build_with_cache,
                    **stage['build_params']
                )
                futures[stage['name']] = future
        
        for name, future in futures.items():
            results[name] = future.result()
            
    return results
```

### Task 1.2: Create Cache Management System
**File**: `panther/core/docker_builder/cache_manager.py`

```python
from pathlib import Path
import json
import time
from typing import Dict, Optional

class DockerCacheManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "cache_index.json"
        self.index = self._load_index()
        
    def _load_index(self) -> Dict:
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return {}
        
    def _save_index(self):
        self.index_file.write_text(json.dumps(self.index, indent=2))
        
    def add_entry(self, key: str, image_tag: str, metadata: Dict = None):
        self.index[key] = {
            'image_tag': image_tag,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        self._save_index()
        
    def get_entry(self, key: str) -> Optional[str]:
        if key in self.index:
            return self.index[key]['image_tag']
        return None
```

### Task 1.3: Build Stage Definition System
**File**: `panther/core/docker_builder/stage_builder.py`

```python
from dataclasses import dataclass
from typing import List, Set, Dict, Any
import networkx as nx

@dataclass
class DockerStage:
    name: str
    from_image: str
    dependencies: Set[str]
    packages: List[str] = None
    commands: List[str] = None
    build_args: Dict[str, str] = None
    cache_key: str = None
    
class StageBuilder:
    def __init__(self):
        self.stages = {}
        self.dependency_graph = nx.DiGraph()
        
    def add_stage(self, stage: DockerStage):
        self.stages[stage.name] = stage
        self.dependency_graph.add_node(stage.name)
        
        for dep in stage.dependencies:
            self.dependency_graph.add_edge(dep, stage.name)
            
    def get_build_order(self) -> List[str]:
        return list(nx.topological_sort(self.dependency_graph))
        
    def generate_dockerfile_for_stage(self, stage_name: str) -> str:
        stage = self.stages[stage_name]
        lines = [f"FROM {stage.from_image} AS {stage.name}"]
        
        if stage.build_args:
            for arg, value in stage.build_args.items():
                lines.append(f"ARG {arg}={value}")
                
        if stage.packages:
            lines.extend([
                "RUN apt-get update && apt-get install -y \\",
                "    " + " ".join(stage.packages) + " \\",
                "    && rm -rf /var/lib/apt/lists/*"
            ])
            
        if stage.commands:
            for cmd in stage.commands:
                lines.append(f"RUN {cmd}")
                
        return "\n".join(lines)
```

## Phase 2: Configuration System (Week 2-3)

### Task 2.1: Create Configuration Schema
**File**: `panther/core/docker_builder/config_schema.py`

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class StageConfig(BaseModel):
    from_image: str = Field(alias="from")
    platform: Optional[str] = None
    args: Optional[Dict[str, str]] = None
    packages: Optional[List[str]] = None
    commands: Optional[List[str]] = None
    scripts: Optional[List[str]] = None
    cache_key: Optional[str] = None
    
class ServiceBuildConfig(BaseModel):
    stages: List[str]
    repo: str
    branch: str = "master"
    build_commands: List[str]
    runtime_config: Optional[Dict[str, Any]] = None
    
class DockerBuildConfig(BaseModel):
    build_config: Dict[str, Any]
    stages: Dict[str, StageConfig]
    services: Dict[str, ServiceBuildConfig]
```

### Task 2.2: Configuration Loader
**File**: `panther/core/docker_builder/config_loader.py`

```python
import yaml
from pathlib import Path
from .config_schema import DockerBuildConfig

class DockerConfigLoader:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> DockerBuildConfig:
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
        return DockerBuildConfig(**data)
        
    def get_service_config(self, service_name: str) -> ServiceBuildConfig:
        if service_name not in self.config.services:
            raise ValueError(f"Service {service_name} not found in config")
        return self.config.services[service_name]
        
    def get_stage_config(self, stage_name: str) -> StageConfig:
        if stage_name not in self.config.stages:
            raise ValueError(f"Stage {stage_name} not found in config")
        return self.config.stages[stage_name]
```

### Task 2.3: Default Configuration File
**File**: `panther/core/docker_builder/default_config.yaml`

```yaml
build_config:
  registry: "cyberelniak"
  cache_enabled: true
  cache_dir: "~/.panther/docker-cache"
  parallel_builds: true
  max_workers: 4
  push_to_registry: false
  
stages:
  # Base stage for all PANTHER services
  panther-base:
    from: "ubuntu:20.04"
    platform: "linux/amd64"
    args:
      DEBIAN_FRONTEND: "noninteractive"
      USER_UID: "${USER_UID:-1000}"
      USER_GID: "${USER_GID:-1000}"
      USER_N: "${USER_N:-panther}"
    packages:
      - build-essential
      - git
      - cmake
      - software-properties-common
      - openssl
      - libssl-dev
      - pkg-config
      - python3
      - net-tools
      - tcpdump
      - wireshark
      - tshark
      - curl
      - wget
      - sudo
    commands:
      - "ln -fs /usr/share/zoneinfo/UTC /etc/localtime"
      - "yes yes | DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common"
      - "groupadd -g ${USER_GID} ${USER_N} || true"
      - "useradd -u ${USER_UID} -g ${USER_GID} -m ${USER_N} || true"
      - "usermod -aG wireshark ${USER_N} || true"
      - "mkdir -p /app /opt && chown -R ${USER_N}:${USER_N} /app /opt || true"
    cache_key: "base-v1"
    
  # C/C++ development tools
  cpp-dev:
    from: "panther-base"
    packages:
      - clang
      - libcap2-bin
      - valgrind
      - gdb
      - autoconf
      - automake
      - libtool
    cache_key: "cpp-dev-v1"
    
  # Rust development
  rust-dev:
    from: "panther-base"
    commands:
      - "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
    cache_key: "rust-dev-v1"
    
  # Python development
  python-dev:
    from: "panther-base"
    packages:
      - python3-pip
      - python3-dev
      - python3-venv
    cache_key: "python-dev-v1"
    
  # Go development
  go-dev:
    from: "panther-base"
    args:
      GO_VERSION: "1.21"
    commands:
      - "wget -q https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz"
      - "tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz"
      - "rm go${GO_VERSION}.linux-amd64.tar.gz"
      - "echo 'export PATH=/usr/local/go/bin:$PATH' >> /etc/profile"
    cache_key: "go-dev-v1"
    
  # Performance tools
  perf-tools:
    from: "cpp-dev"
    packages:
      - google-perftools
      - libunwind-dev
      - graphviz
    commands:
      - "cd /tmp && git clone https://github.com/gperftools/gperftools"
      - "cd /tmp/gperftools && ./autogen.sh && ./configure && make && make install"
      - "rm -rf /tmp/gperftools"
    cache_key: "perf-tools-v1"
```

## Phase 3: Build Orchestrator (Week 3-4)

### Task 3.1: Main Orchestrator Class
**File**: `panther/core/docker_builder/build_orchestrator.py`

```python
from typing import Dict, List, Optional
import asyncio
from pathlib import Path

from .docker_builder import DockerBuilder
from .config_loader import DockerConfigLoader
from .stage_builder import StageBuilder, DockerStage
from .cache_manager import DockerCacheManager

class DockerBuildOrchestrator:
    def __init__(self, config_path: Path, docker_builder: DockerBuilder):
        self.config_loader = DockerConfigLoader(config_path)
        self.docker_builder = docker_builder
        self.stage_builder = StageBuilder()
        self.cache_manager = DockerCacheManager(
            Path(self.config_loader.config.build_config['cache_dir']).expanduser()
        )
        self._initialize_stages()
        
    def _initialize_stages(self):
        """Load all stages from configuration."""
        for name, stage_config in self.config_loader.config.stages.items():
            stage = DockerStage(
                name=name,
                from_image=stage_config.from_image,
                dependencies=self._get_stage_dependencies(stage_config.from_image),
                packages=stage_config.packages,
                commands=stage_config.commands,
                build_args=stage_config.args,
                cache_key=stage_config.cache_key
            )
            self.stage_builder.add_stage(stage)
            
    def build_service(self, service_name: str, version: str = "latest",
                     force_rebuild: bool = False) -> Dict[str, Any]:
        """Build a service with all dependencies."""
        service_config = self.config_loader.get_service_config(service_name)
        
        # Build all required stages
        stage_results = {}
        for stage_name in self.stage_builder.get_build_order():
            if stage_name in service_config.stages:
                result = self._build_stage(
                    stage_name,
                    stage_results,
                    force_rebuild
                )
                stage_results[stage_name] = result
                
        # Build final service image
        service_result = self._build_service_image(
            service_name,
            service_config,
            stage_results,
            version
        )
        
        return {
            'stages': stage_results,
            'service': service_result,
            'total_time': sum(r.get('build_time', 0) for r in stage_results.values())
        }
```

### Task 3.2: Parallel Build Support
**File**: `panther/core/docker_builder/parallel_builder.py`

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set

class ParallelDockerBuilder:
    def __init__(self, docker_builder, max_workers: int = 4):
        self.docker_builder = docker_builder
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.build_lock = asyncio.Lock()
        self.completed_stages: Set[str] = set()
        
    async def build_stages_parallel(self, stages: List[DockerStage]) -> Dict[str, Any]:
        """Build stages in parallel respecting dependencies."""
        results = {}
        futures = {}
        
        async def build_when_ready(stage: DockerStage):
            # Wait for dependencies
            while not all(dep in self.completed_stages for dep in stage.dependencies):
                await asyncio.sleep(0.1)
                
            # Submit build task
            future = self.executor.submit(
                self.docker_builder.build_with_cache,
                stage_name=stage.name,
                dockerfile_content=self._generate_dockerfile(stage),
                cache_key=stage.cache_key
            )
            
            # Wait for completion
            result = await asyncio.get_event_loop().run_in_executor(
                None, future.result
            )
            
            async with self.build_lock:
                self.completed_stages.add(stage.name)
                results[stage.name] = result
                
            return result
            
        # Start all builds
        tasks = [build_when_ready(stage) for stage in stages]
        await asyncio.gather(*tasks)
        
        return results
```

## Phase 4: Integration (Week 4-5)

### Task 4.1: Update DockerOperationsMixin
**File**: `panther/core/docker_builder/docker_operations_mixin.py`

Add to existing class:

```python
def prepare_docker_image_v2(
    self,
    orchestrator: Optional[DockerBuildOrchestrator] = None,
    **kwargs
) -> bool:
    """Enhanced prepare method using orchestrator."""
    if orchestrator and hasattr(self, 'implementation_name'):
        try:
            results = orchestrator.build_service(
                service_name=self.implementation_name,
                version=kwargs.get('version', 'latest'),
                force_rebuild=self.should_force_build()
            )
            
            # Extract final image tag
            self.docker_image_name = results['service']['image_tag']
            return True
            
        except Exception as e:
            self.logger.error(f"Orchestrator build failed: {e}")
            # Fall back to traditional method
            
    return self.prepare_docker_image(**kwargs)
```

### Task 4.2: Update PluginManager
**File**: `panther/plugins/plugin_manager.py`

Add to __init__:

```python
# Initialize build orchestrator
config_path = Path("panther/core/docker_builder/default_config.yaml")
if global_config and hasattr(global_config, 'docker_build_config'):
    config_path = Path(global_config.docker_build_config)
    
self.build_orchestrator = DockerBuildOrchestrator(
    config_path=config_path,
    docker_builder=self.docker_builder
)
```

### Task 4.3: Create Migration Helper
**File**: `panther/core/docker_builder/migration.py`

```python
import os
from typing import Dict, Any
import yaml

class DockerBuildMigration:
    """Helper for migrating to centralized Docker builds."""
    
    @staticmethod
    def analyze_dockerfile(dockerfile_path: Path) -> Dict[str, Any]:
        """Analyze existing Dockerfile for migration."""
        content = dockerfile_path.read_text()
        analysis = {
            'base_image': None,
            'stages': [],
            'packages': [],
            'commands': [],
            'complexity': 'low'
        }
        
        # Parse Dockerfile
        for line in content.split('\n'):
            if line.startswith('FROM'):
                analysis['base_image'] = line.split()[1]
            elif line.startswith('RUN apt-get install'):
                # Extract packages
                pass
                
        return analysis
        
    @staticmethod
    def generate_service_config(service_name: str, dockerfile_path: Path) -> Dict:
        """Generate service configuration from existing Dockerfile."""
        analysis = DockerBuildMigration.analyze_dockerfile(dockerfile_path)
        
        return {
            'stages': ['panther-base', 'cpp-dev'],  # Based on analysis
            'repo': f"https://github.com/example/{service_name}.git",
            'branch': 'master',
            'build_commands': analysis['commands']
        }
```

## Phase 5: Testing & Monitoring (Week 5-6)

### Task 5.1: Build Progress Monitoring
**File**: `panther/core/docker_builder/build_monitor.py`

```python
import time
import psutil
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class BuildMetrics:
    stage_name: str
    start_time: float
    end_time: float
    cpu_usage: List[float]
    memory_usage: List[float]
    cache_hit: bool
    image_size: int
    
class BuildMonitor:
    def __init__(self):
        self.metrics: Dict[str, BuildMetrics] = {}
        self.monitoring = False
        
    def start_monitoring(self, stage_name: str):
        """Start monitoring a build."""
        self.metrics[stage_name] = BuildMetrics(
            stage_name=stage_name,
            start_time=time.time(),
            end_time=0,
            cpu_usage=[],
            memory_usage=[],
            cache_hit=False,
            image_size=0
        )
        
    def stop_monitoring(self, stage_name: str):
        """Stop monitoring and finalize metrics."""
        if stage_name in self.metrics:
            self.metrics[stage_name].end_time = time.time()
            
    def generate_report(self) -> Dict[str, Any]:
        """Generate build performance report."""
        total_time = sum(
            m.end_time - m.start_time 
            for m in self.metrics.values()
        )
        
        cache_hits = sum(
            1 for m in self.metrics.values() 
            if m.cache_hit
        )
        
        return {
            'total_build_time': total_time,
            'stages_built': len(self.metrics),
            'cache_hit_rate': cache_hits / len(self.metrics) if self.metrics else 0,
            'stage_metrics': {
                name: {
                    'duration': m.end_time - m.start_time,
                    'avg_cpu': sum(m.cpu_usage) / len(m.cpu_usage) if m.cpu_usage else 0,
                    'peak_memory': max(m.memory_usage) if m.memory_usage else 0,
                    'image_size_mb': m.image_size / 1024 / 1024
                }
                for name, m in self.metrics.items()
            }
        }
```

### Task 5.2: Test Suite
**File**: `tests/unit/test_core/test_docker_builder_v2.py`

```python
import pytest
from pathlib import Path
from panther.core.docker_builder import EnhancedDockerBuilder
from panther.core.docker_builder.build_orchestrator import DockerBuildOrchestrator

class TestDockerBuilderV2:
    @pytest.fixture
    def docker_builder(self):
        return EnhancedDockerBuilder(cache_dir="/tmp/test-cache")
        
    @pytest.fixture
    def orchestrator(self, docker_builder):
        config_path = Path("tests/fixtures/docker-config.yaml")
        return DockerBuildOrchestrator(config_path, docker_builder)
        
    def test_parallel_stage_build(self, orchestrator):
        """Test parallel building of independent stages."""
        results = orchestrator.build_service(
            "test-service",
            version="test",
            force_rebuild=True
        )
        
        assert 'stages' in results
        assert 'service' in results
        assert results['stages']['panther-base']['cache_hit'] == False
        
    def test_cache_effectiveness(self, orchestrator):
        """Test that cache is used on second build."""
        # First build
        results1 = orchestrator.build_service("picoquic")
        
        # Second build should use cache
        results2 = orchestrator.build_service("picoquic")
        
        assert results2['stages']['panther-base']['cache_hit'] == True
        assert results2['total_time'] < results1['total_time']
```

## Phase 6: Documentation & Rollout (Week 6-7)

### Task 6.1: User Documentation
**File**: `docs/docker-build-guide.md`

```markdown
# Docker Build System Guide

## Quick Start

1. Enable centralized builds:
   ```bash
   export PANTHER_USE_CENTRALIZED_DOCKER=true
   ```

2. Build a service:
   ```python
   plugin_manager.build_orchestrator.build_service("picoquic")
   ```

## Configuration

Create a custom configuration:

```yaml
# my-docker-config.yaml
services:
  my-service:
    stages:
      - panther-base
      - cpp-dev
    repo: "https://github.com/my-org/my-service.git"
    build_commands:
      - "cmake ."
      - "make"
```

## Migration Guide

### Step 1: Analyze existing Dockerfile
```bash
python -m panther.tools.docker_migration analyze path/to/Dockerfile
```

### Step 2: Generate configuration
```bash
python -m panther.tools.docker_migration generate my-service
```

### Step 3: Test new build
```bash
python -m panther.tools.docker_migration test my-service
```
```

### Task 6.2: Performance Dashboard
**File**: `panther/tools/docker_build_dashboard.py`

```python
#!/usr/bin/env python3
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

@click.command()
@click.option('--service', help='Service to build')
@click.option('--watch', is_flag=True, help='Watch build progress')
def build_dashboard(service, watch):
    """Interactive Docker build dashboard."""
    console = Console()
    
    if watch:
        with Progress() as progress:
            task = progress.add_task(f"Building {service}...", total=100)
            # Monitor build progress
            
    # Show results
    table = Table(title="Build Results")
    table.add_column("Stage", style="cyan")
    table.add_column("Time", style="magenta")
    table.add_column("Cache", style="green")
    table.add_column("Size", style="yellow")
    
    # Add rows from build results
    console.print(table)
```

## Deliverables Summary

1. **Enhanced DockerBuilder** with multistage and caching support
2. **Configuration system** for declarative builds
3. **Build orchestrator** for dependency management
4. **Parallel build support** for performance
5. **Migration tools** for existing services
6. **Monitoring and reporting** for visibility
7. **Comprehensive testing** for reliability
8. **Documentation** for adoption

## Success Criteria

- [ ] All QUIC services build successfully with new system
- [ ] Build times reduced by at least 50%
- [ ] Cache hit rate above 80% for common stages
- [ ] Zero regression in functionality
- [ ] Positive developer feedback
- [ ] Complete documentation and examples

This roadmap provides a clear path to implementing the centralized Docker build system with specific tasks, code examples, and deliverables for each phase.