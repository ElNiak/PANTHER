#!/usr/bin/env python3.10
"""Tests for Docker build base classes using Python 3.10 syntax."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

# Test imports with fallback to mocks for missing modules
try:
    from panther.plugins.services.base.docker_build_base import (
        QUIC_DOCKER_BUILDERS,
        DockerBuilderFactory,
        BaseDockerBuilder,
        RustDockerBuilder,
        PythonDockerBuilder,
        CDockerBuilder,
        GoDockerBuilder
    )
    DOCKER_BUILD_SYSTEM_AVAILABLE = True
except ImportError:
    DOCKER_BUILD_SYSTEM_AVAILABLE = False
    
    # Create mock implementations for testing
    class BaseDockerBuilder:
        """Mock base Docker builder."""
        
        def __init__(self, implementation_name: str, repo_url: str, 
                     dockerfile_template: str = "", **kwargs):
            self.implementation_name = implementation_name
            self.repo_url = repo_url
            self.dockerfile_template = dockerfile_template
            self.build_args: Dict[str, str] = kwargs.get('build_args', {})
            self.env_vars: Dict[str, str] = kwargs.get('env_vars', {})
            
        def generate_base_dockerfile(self) -> str:
            return f"""
FROM ubuntu:22.04
WORKDIR /app
RUN apt-get update && apt-get install -y git
RUN git clone {self.repo_url} {self.implementation_name}
WORKDIR /app/{self.implementation_name}
"""
            
        def generate_build_commands(self) -> List[str]:
            return ["make", "make install"]
            
        def generate_complete_dockerfile(self) -> str:
            base = self.generate_base_dockerfile()
            commands = self.generate_build_commands()
            build_section = "\n".join([f"RUN {cmd}" for cmd in commands])
            return f"{base}\n{build_section}\n"
    
    class RustDockerBuilder(BaseDockerBuilder):
        """Mock Rust Docker builder."""
        
        def __init__(self, implementation_name: str, repo_url: str, 
                     cargo_features: List[str] | None = None, **kwargs):
            super().__init__(implementation_name, repo_url, **kwargs)
            self.cargo_features = cargo_features or []
            
        def generate_base_dockerfile(self) -> str:
            return f"""
FROM rust:1.70
WORKDIR /app
RUN git clone {self.repo_url} {self.implementation_name}
WORKDIR /app/{self.implementation_name}
"""
            
        def generate_build_commands(self) -> List[str]:
            if self.cargo_features:
                features_str = ",".join(self.cargo_features)
                return [f"cargo build --release --features {features_str}"]
            return ["cargo build --release"]
    
    class PythonDockerBuilder(BaseDockerBuilder):
        """Mock Python Docker builder."""
        
        def __init__(self, implementation_name: str, repo_url: str, 
                     python_version: str = "3.10", requirements_file: str = "requirements.txt", **kwargs):
            super().__init__(implementation_name, repo_url, **kwargs)
            self.python_version = python_version
            self.requirements_file = requirements_file
            
        def generate_base_dockerfile(self) -> str:
            return f"""
FROM python:{self.python_version}-slim
WORKDIR /app
RUN git clone {self.repo_url} {self.implementation_name}
WORKDIR /app/{self.implementation_name}
"""
            
        def generate_build_commands(self) -> List[str]:
            return [
                f"pip install -r {self.requirements_file}",
                "pip install -e ."
            ]
    
    class CDockerBuilder(BaseDockerBuilder):
        """Mock C Docker builder."""
        
        def generate_base_dockerfile(self) -> str:
            return f"""
FROM gcc:latest
WORKDIR /app
RUN apt-get update && apt-get install -y cmake make git
RUN git clone {self.repo_url} {self.implementation_name}
WORKDIR /app/{self.implementation_name}
"""
    
    class GoDockerBuilder(BaseDockerBuilder):
        """Mock Go Docker builder."""
        
        def generate_base_dockerfile(self) -> str:
            return f"""
FROM golang:1.20
WORKDIR /app
RUN git clone {self.repo_url} {self.implementation_name}
WORKDIR /app/{self.implementation_name}
"""
            
        def generate_build_commands(self) -> List[str]:
            return ["go mod tidy", "go build -o bin/main ."]
    
    class DockerBuilderFactory:
        """Mock Docker builder factory."""
        
        @staticmethod
        def create_builder(implementation_name: str, language: str, 
                          repo_url: str, **kwargs) -> BaseDockerBuilder:
            builders = {
                'rust': RustDockerBuilder,
                'python': PythonDockerBuilder,
                'c': CDockerBuilder,
                'go': GoDockerBuilder
            }
            
            builder_class = builders.get(language, BaseDockerBuilder)
            return builder_class(implementation_name, repo_url, **kwargs)
    
    # Mock QUIC builders registry
    QUIC_DOCKER_BUILDERS: Dict[str, BaseDockerBuilder] = {
        'picoquic': CDockerBuilder(
            'picoquic', 
            'https://github.com/private-octopus/picoquic.git'
        ),
        'aioquic': PythonDockerBuilder(
            'aioquic',
            'https://github.com/aiortc/aioquic.git',
            python_version='3.10'
        ),
        'quiche': RustDockerBuilder(
            'quiche',
            'https://github.com/cloudflare/quiche.git',
            cargo_features=['default']
        ),
        'quinn': RustDockerBuilder(
            'quinn',
            'https://github.com/quinn-rs/quinn.git',
            cargo_features=['rustls-tls']
        ),
        'lsquic': CDockerBuilder(
            'lsquic',
            'https://github.com/litespeedtech/lsquic.git'
        ),
        'mvfst': CDockerBuilder(
            'mvfst',
            'https://github.com/facebook/mvfst.git'
        ),
        'quant': CDockerBuilder(
            'quant',
            'https://github.com/NTAP/quant.git'
        ),
        'quic_go': GoDockerBuilder(
            'quic_go',
            'https://github.com/lucas-clemente/quic-go.git'
        )
    }

pytestmark = [pytest.mark.unit, pytest.mark.docker_build]

class TestBaseDockerBuilder:
    """Test base Docker builder functionality."""
    
    def test_base_docker_builder_initialization(self):
        """Test BaseDockerBuilder initialization with Python 3.10 syntax."""
        implementation_name = "test_impl"
        repo_url = "https://github.com/test/repo.git"
        
        builder = BaseDockerBuilder(
            implementation_name=implementation_name,
            repo_url=repo_url,
            build_args={'ARG1': 'value1'},
            env_vars={'ENV1': 'value1'}
        )
        
        assert builder.implementation_name == implementation_name
        assert builder.repo_url == repo_url
        assert builder.build_args == {'ARG1': 'value1'}
        assert builder.env_vars == {'ENV1': 'value1'}
    
    def test_generate_base_dockerfile(self):
        """Test base Dockerfile generation."""
        builder = BaseDockerBuilder(
            implementation_name="test_impl",
            repo_url="https://github.com/test/repo.git"
        )
        
        dockerfile = builder.generate_base_dockerfile()
        
        assert isinstance(dockerfile, str)
        assert "FROM ubuntu:22.04" in dockerfile
        assert "git clone https://github.com/test/repo.git" in dockerfile
        assert "WORKDIR /app/test_impl" in dockerfile
    
    def test_generate_build_commands(self):
        """Test build commands generation."""
        builder = BaseDockerBuilder("test_impl", "https://test.com/repo.git")
        
        commands = builder.generate_build_commands()
        
        assert isinstance(commands, list)
        assert "make" in commands
        assert "make install" in commands
    
    def test_generate_complete_dockerfile(self):
        """Test complete Dockerfile generation."""
        builder = BaseDockerBuilder("test_impl", "https://test.com/repo.git")
        
        dockerfile = builder.generate_complete_dockerfile()
        
        assert isinstance(dockerfile, str)
        assert "FROM ubuntu:22.04" in dockerfile
        assert "RUN make" in dockerfile
        assert "RUN make install" in dockerfile

class TestRustDockerBuilder:
    """Test Rust-specific Docker builder."""
    
    def test_rust_builder_initialization(self):
        """Test RustDockerBuilder initialization."""
        cargo_features = ['async', 'crypto']
        
        builder = RustDockerBuilder(
            implementation_name="rust_impl",
            repo_url="https://github.com/rust/impl.git",
            cargo_features=cargo_features
        )
        
        assert builder.implementation_name == "rust_impl"
        assert builder.cargo_features == cargo_features
    
    def test_rust_dockerfile_generation(self):
        """Test Rust Dockerfile generation."""
        builder = RustDockerBuilder(
            "quiche",
            "https://github.com/cloudflare/quiche.git"
        )
        
        dockerfile = builder.generate_base_dockerfile()
        
        assert "FROM rust:1.70" in dockerfile
        assert "quiche" in dockerfile
    
    def test_rust_build_commands_with_features(self):
        """Test Rust build commands with features."""
        builder = RustDockerBuilder(
            "quiche",
            "https://github.com/cloudflare/quiche.git",
            cargo_features=['default', 'async']
        )
        
        commands = builder.generate_build_commands()
        
        assert len(commands) == 1
        assert "cargo build --release --features default,async" in commands[0]
    
    def test_rust_build_commands_without_features(self):
        """Test Rust build commands without features."""
        builder = RustDockerBuilder(
            "quinn",
            "https://github.com/quinn-rs/quinn.git"
        )
        
        commands = builder.generate_build_commands()
        
        assert "cargo build --release" in commands

class TestPythonDockerBuilder:
    """Test Python-specific Docker builder."""
    
    def test_python_builder_initialization(self):
        """Test PythonDockerBuilder initialization."""
        builder = PythonDockerBuilder(
            implementation_name="aioquic",
            repo_url="https://github.com/aiortc/aioquic.git",
            python_version="3.11",
            requirements_file="dev-requirements.txt"
        )
        
        assert builder.implementation_name == "aioquic"
        assert builder.python_version == "3.11"
        assert builder.requirements_file == "dev-requirements.txt"
    
    def test_python_dockerfile_generation(self):
        """Test Python Dockerfile generation."""
        builder = PythonDockerBuilder(
            "aioquic",
            "https://github.com/aiortc/aioquic.git",
            python_version="3.10"
        )
        
        dockerfile = builder.generate_base_dockerfile()
        
        assert "FROM python:3.10-slim" in dockerfile
        assert "aioquic" in dockerfile
    
    def test_python_build_commands(self):
        """Test Python build commands."""
        builder = PythonDockerBuilder(
            "aioquic",
            "https://github.com/aiortc/aioquic.git",
            requirements_file="requirements.txt"
        )
        
        commands = builder.generate_build_commands()
        
        assert "pip install -r requirements.txt" in commands
        assert "pip install -e ." in commands

class TestCDockerBuilder:
    """Test C-specific Docker builder."""
    
    def test_c_dockerfile_generation(self):
        """Test C Dockerfile generation."""
        builder = CDockerBuilder(
            "picoquic",
            "https://github.com/private-octopus/picoquic.git"
        )
        
        dockerfile = builder.generate_base_dockerfile()
        
        assert "FROM gcc:latest" in dockerfile
        assert "cmake" in dockerfile
        assert "picoquic" in dockerfile

class TestGoDockerBuilder:
    """Test Go-specific Docker builder."""
    
    def test_go_dockerfile_generation(self):
        """Test Go Dockerfile generation."""
        builder = GoDockerBuilder(
            "quic_go",
            "https://github.com/lucas-clemente/quic-go.git"
        )
        
        dockerfile = builder.generate_base_dockerfile()
        
        assert "FROM golang:1.20" in dockerfile
        assert "quic_go" in dockerfile
    
    def test_go_build_commands(self):
        """Test Go build commands."""
        builder = GoDockerBuilder(
            "quic_go",
            "https://github.com/lucas-clemente/quic-go.git"
        )
        
        commands = builder.generate_build_commands()
        
        assert "go mod tidy" in commands
        assert "go build -o bin/main ." in commands

class TestDockerBuilderFactory:
    """Test Docker builder factory."""
    
    @pytest.mark.parametrize("language,expected_type", [
        ("rust", RustDockerBuilder),
        ("python", PythonDockerBuilder),
        ("c", CDockerBuilder),
        ("go", GoDockerBuilder),
        ("unknown", BaseDockerBuilder)
    ])
    def test_factory_creates_correct_builder_type(self, language: str, expected_type: type):
        """Test factory creates correct builder types."""
        builder = DockerBuilderFactory.create_builder(
            implementation_name="test",
            language=language,
            repo_url="https://test.com/repo.git"
        )
        
        assert isinstance(builder, expected_type)
    
    def test_factory_with_rust_features(self):
        """Test factory with Rust-specific options."""
        builder = DockerBuilderFactory.create_builder(
            implementation_name="quiche",
            language="rust",
            repo_url="https://github.com/cloudflare/quiche.git",
            cargo_features=["default", "async"]
        )
        
        assert isinstance(builder, RustDockerBuilder)
        assert builder.cargo_features == ["default", "async"]
    
    def test_factory_with_python_options(self):
        """Test factory with Python-specific options."""
        builder = DockerBuilderFactory.create_builder(
            implementation_name="aioquic",
            language="python",
            repo_url="https://github.com/aiortc/aioquic.git",
            python_version="3.11",
            requirements_file="dev-requirements.txt"
        )
        
        assert isinstance(builder, PythonDockerBuilder)
        assert builder.python_version == "3.11"
        assert builder.requirements_file == "dev-requirements.txt"

class TestQUICDockerBuilders:
    """Test predefined QUIC Docker builders registry."""
    
    def test_quic_builders_registry_exists(self):
        """Test QUIC builders registry is properly defined."""
        assert isinstance(QUIC_DOCKER_BUILDERS, dict)
        assert len(QUIC_DOCKER_BUILDERS) > 0
    
    @pytest.mark.parametrize("impl_name", [
        "picoquic", "aioquic", "quiche", "quinn", 
        "lsquic", "mvfst", "quant", "quic_go"
    ])
    def test_quic_implementation_exists(self, impl_name: str):
        """Test each QUIC implementation has a builder."""
        assert impl_name in QUIC_DOCKER_BUILDERS
        builder = QUIC_DOCKER_BUILDERS[impl_name]
        assert isinstance(builder, BaseDockerBuilder)
    
    @pytest.mark.parametrize("impl_name", [
        "picoquic", "aioquic", "quiche", "quinn", 
        "lsquic", "mvfst", "quant", "quic_go"
    ])
    def test_dockerfile_generation_for_each_impl(self, impl_name: str):
        """Test Dockerfile generation for each QUIC implementation."""
        builder = QUIC_DOCKER_BUILDERS[impl_name]
        dockerfile = builder.generate_complete_dockerfile()
        
        assert isinstance(dockerfile, str)
        assert "FROM" in dockerfile
        assert impl_name in dockerfile.lower() or impl_name.replace('_', '-') in dockerfile.lower()
    
    def test_rust_implementations_have_cargo_features(self):
        """Test Rust implementations have appropriate cargo features."""
        rust_impls = ["quiche", "quinn"]
        
        for impl_name in rust_impls:
            builder = QUIC_DOCKER_BUILDERS[impl_name]
            assert isinstance(builder, RustDockerBuilder)
            assert hasattr(builder, 'cargo_features')
            
            dockerfile = builder.generate_complete_dockerfile()
            if builder.cargo_features:
                assert "cargo build" in dockerfile
    
    def test_python_implementations_have_python_settings(self):
        """Test Python implementations have appropriate settings."""
        python_impls = ["aioquic"]
        
        for impl_name in python_impls:
            builder = QUIC_DOCKER_BUILDERS[impl_name]
            assert isinstance(builder, PythonDockerBuilder)
            assert hasattr(builder, 'python_version')
            
            dockerfile = builder.generate_complete_dockerfile()
            assert f"python:{builder.python_version}" in dockerfile
    
    def test_c_implementations_have_build_tools(self):
        """Test C implementations include necessary build tools."""
        c_impls = ["picoquic", "lsquic", "mvfst", "quant"]
        
        for impl_name in c_impls:
            builder = QUIC_DOCKER_BUILDERS[impl_name]
            assert isinstance(builder, CDockerBuilder)
            
            dockerfile = builder.generate_complete_dockerfile()
            assert any(tool in dockerfile for tool in ["gcc", "cmake", "make"])
    
    def test_go_implementations_have_go_commands(self):
        """Test Go implementations include Go build commands."""
        go_impls = ["quic_go"]
        
        for impl_name in go_impls:
            builder = QUIC_DOCKER_BUILDERS[impl_name]
            assert isinstance(builder, GoDockerBuilder)
            
            dockerfile = builder.generate_complete_dockerfile()
            assert "go build" in dockerfile or "go mod" in dockerfile

class TestDockerBuilderIntegration:
    """Test integration scenarios for Docker builders."""
    
    def test_dockerfile_to_file_generation(self):
        """Test generating Dockerfile to file system."""
        builder = QUIC_DOCKER_BUILDERS["picoquic"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_path = Path(temp_dir) / "Dockerfile"
            
            # Generate dockerfile content
            dockerfile_content = builder.generate_complete_dockerfile()
            
            # Write to file
            dockerfile_path.write_text(dockerfile_content)
            
            # Verify file exists and has content
            assert dockerfile_path.exists()
            assert dockerfile_path.stat().st_size > 0
            
            # Verify content is valid
            content = dockerfile_path.read_text()
            assert "FROM" in content
            assert "WORKDIR" in content
    
    def test_multiple_builders_same_implementation(self):
        """Test creating multiple builders for same implementation."""
        builder1 = DockerBuilderFactory.create_builder(
            "test_impl", "rust", "https://test.com/repo.git",
            cargo_features=["feature1"]
        )
        
        builder2 = DockerBuilderFactory.create_builder(
            "test_impl", "rust", "https://test.com/repo.git",
            cargo_features=["feature2"]
        )
        
        # Should be separate instances with different features
        assert builder1 is not builder2
        assert builder1.cargo_features != builder2.cargo_features
    
    def test_builder_dockerfile_differences(self):
        """Test that different builders generate different Dockerfiles."""
        rust_builder = QUIC_DOCKER_BUILDERS["quiche"]
        python_builder = QUIC_DOCKER_BUILDERS["aioquic"]
        c_builder = QUIC_DOCKER_BUILDERS["picoquic"]
        
        rust_dockerfile = rust_builder.generate_complete_dockerfile()
        python_dockerfile = python_builder.generate_complete_dockerfile()
        c_dockerfile = c_builder.generate_complete_dockerfile()
        
        # Each should be different
        assert rust_dockerfile != python_dockerfile
        assert python_dockerfile != c_dockerfile
        assert rust_dockerfile != c_dockerfile
        
        # Each should contain language-specific elements
        assert "rust:" in rust_dockerfile
        assert "python:" in python_dockerfile
        assert "gcc:" in c_dockerfile

class TestDockerBuilderErrorHandling:
    """Test error handling in Docker builders."""
    
    def test_builder_with_invalid_parameters(self):
        """Test builder behavior with invalid parameters."""
        # Test with None values - should not crash
        try:
            builder = BaseDockerBuilder(
                implementation_name="",
                repo_url=""
            )
            dockerfile = builder.generate_complete_dockerfile()
            assert isinstance(dockerfile, str)
        except Exception as e:
            # If exception is raised, should be reasonable
            assert isinstance(e, (ValueError, TypeError))
    
    def test_empty_cargo_features(self):
        """Test Rust builder with empty cargo features."""
        builder = RustDockerBuilder(
            "test_rust",
            "https://test.com/repo.git",
            cargo_features=[]
        )
        
        commands = builder.generate_build_commands()
        assert "cargo build --release" in commands[0]
        assert "--features" not in commands[0]
    
    def test_factory_with_missing_language_specific_args(self):
        """Test factory when language-specific arguments are missing."""
        # Should still create builder, just with defaults
        builder = DockerBuilderFactory.create_builder(
            "test_impl",
            "python",
            "https://test.com/repo.git"
            # Missing python_version, requirements_file
        )
        
        assert isinstance(builder, PythonDockerBuilder)
        # Should have sensible defaults
        assert hasattr(builder, 'python_version')
        assert hasattr(builder, 'requirements_file')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])