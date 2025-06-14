"""Base classes for Docker build patterns in QUIC implementations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseDockerBuilder(ABC):
    """Base class for Docker build pattern extraction."""

    def __init__(
        self, implementation_name: str, base_image: str = "panther_base_service:latest"
    ):
        """Initialize Docker builder.

        Args:
            implementation_name: Name of the implementation
            base_image: Base Docker image to use
        """
        self.implementation_name = implementation_name
        self.base_image = base_image

    def generate_dockerfile_header(self) -> List[str]:
        """Generate common Dockerfile header."""
        return [
            f"FROM {self.base_image}",
            "",
            "ENV DEBIAN_FRONTEND=noninteractive",
            "# Define build arguments for version-specific configurations",
            "ARG VERSION=master",
            'ARG DEPENDENCIES="[]"  # JSON-formatted list of dependencies',
            "ENV VERSION=${VERSION}",
            "ENV DEPENDENCIES=${DEPENDENCIES}",
            "",
        ]

    def generate_common_dependencies(self) -> List[str]:
        """Generate common dependency installation commands."""
        return [
            "# Perl stuff is for the picotls test code",
            "RUN echo install Test::TCP | perl -MCPAN -",
            "RUN echo install Scope::Guard | perl -MCPAN -",
            "",
            "# Install jq for JSON parsing",
            "RUN apt-get install --fix-missing -y jq",
            "",
            "USER ${USER_N}",
            "",
        ]

    def generate_dependency_parser(self) -> List[str]:
        """Generate JSON dependency parser commands."""
        return [
            "# Function to parse and build dependencies",
            "RUN cd /opt && \\",
            '    echo "Starting dependency installation..." && \\',
            "    echo $DEPENDENCIES | jq -c '.[]' | while read -r dep; do \\",
            "        DEP_NAME=$(echo $dep | jq -r '.name'); \\",
            "        DEP_URL=$(echo $dep | jq -r '.url'); \\",
            "        DEP_COMMIT=$(echo $dep | jq -r '.commit'); \\",
            '        if [ -n "$DEP_NAME" ] && [ -n "$DEP_URL" ] && [ -n "$DEP_COMMIT" ]; then \\',
            "            echo \"Cloning dependency '$DEP_NAME' from '$DEP_URL' at commit '$DEP_COMMIT'\" && \\",
            '            git clone "$DEP_URL" "$DEP_NAME" && \\',
            '            cd "$DEP_NAME" && \\',
            '            git checkout "$DEP_COMMIT" && \\',
            "            cd /opt; \\",
            "        fi; \\",
            "    done",
            "",
        ]

    @abstractmethod
    def generate_implementation_specific_commands(self) -> List[str]:
        """Generate implementation-specific Docker commands."""
        pass

    def generate_cleanup_commands(self) -> List[str]:
        """Generate cleanup commands."""
        return [
            "",
            "# Cleanup",
            "RUN apt-get clean && rm -rf /var/lib/apt/lists/*",
            "",
            "# Set working directory",
            f"WORKDIR /opt/{self.implementation_name}",
            "",
            "# Copy entrypoint and make executable",
            "COPY entrypoint.sh /entrypoint.sh",
            "RUN chmod +x /entrypoint.sh",
            "",
            'ENTRYPOINT ["/entrypoint.sh"]',
        ]

    def generate_complete_dockerfile(self) -> str:
        """Generate complete Dockerfile content."""
        lines = []
        lines.extend(self.generate_dockerfile_header())
        lines.extend(self.generate_common_dependencies())
        lines.extend(self.generate_dependency_parser())
        lines.extend(self.generate_implementation_specific_commands())
        lines.extend(self.generate_cleanup_commands())

        return "\n".join(lines)


class CDockerBuilder(BaseDockerBuilder):
    """Docker builder for C-based QUIC implementations (PicoQUIC, lsquic, quant)."""

    def __init__(
        self, implementation_name: str, repo_url: str, build_commands: List[str]
    ):
        """Initialize C Docker builder.

        Args:
            implementation_name: Name of the implementation
            repo_url: Git repository URL
            build_commands: List of build commands
        """
        super().__init__(implementation_name)
        self.repo_url = repo_url
        self.build_commands = build_commands

    def generate_implementation_specific_commands(self) -> List[str]:
        """Generate C implementation specific commands."""
        commands = [
            f"# Build {self.implementation_name}",
            f"RUN git clone {self.repo_url} {self.implementation_name} && \\",
            f"    cd {self.implementation_name} && \\",
        ]

        # Add build commands
        for i, cmd in enumerate(self.build_commands):
            if i == len(self.build_commands) - 1:
                commands.append(f"    {cmd}")
            else:
                commands.append(f"    {cmd} && \\")

        return commands


class RustDockerBuilder(BaseDockerBuilder):
    """Docker builder for Rust-based QUIC implementations (quiche, quinn)."""

    def __init__(
        self,
        implementation_name: str,
        repo_url: str,
        cargo_features: Optional[List[str]] = None,
    ):
        """Initialize Rust Docker builder.

        Args:
            implementation_name: Name of the implementation
            repo_url: Git repository URL
            cargo_features: Optional list of Cargo features
        """
        super().__init__(implementation_name)
        self.repo_url = repo_url
        self.cargo_features = cargo_features or []

    def generate_rust_dependencies(self) -> List[str]:
        """Generate Rust-specific dependencies."""
        return [
            "# Install Rust and Cargo",
            "RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
            'ENV PATH="/root/.cargo/bin:${PATH}"',
            "",
        ]

    def generate_implementation_specific_commands(self) -> List[str]:
        """Generate Rust implementation specific commands."""
        features_flag = ""
        if self.cargo_features:
            features_flag = f" --features \"{' '.join(self.cargo_features)}\""

        commands = self.generate_rust_dependencies()
        commands.extend(
            [
                f"# Build {self.implementation_name}",
                f"RUN git clone {self.repo_url} {self.implementation_name} && \\",
                f"    cd {self.implementation_name} && \\",
                f"    cargo build --release{features_flag}",
            ]
        )

        return commands


class PythonDockerBuilder(BaseDockerBuilder):
    """Docker builder for Python-based QUIC implementations (aioquic)."""

    def __init__(
        self,
        implementation_name: str,
        repo_url: str,
        python_requirements: Optional[List[str]] = None,
    ):
        """Initialize Python Docker builder.

        Args:
            implementation_name: Name of the implementation
            repo_url: Git repository URL
            python_requirements: Optional list of Python requirements
        """
        super().__init__(implementation_name)
        self.repo_url = repo_url
        self.python_requirements = python_requirements or []

    def generate_python_dependencies(self) -> List[str]:
        """Generate Python-specific dependencies."""
        commands = [
            "# Install Python dependencies",
            "RUN apt-get update && apt-get install -y python3-pip python3-dev",
        ]

        if self.python_requirements:
            req_string = " ".join(self.python_requirements)
            commands.append(f"RUN pip3 install {req_string}")

        commands.append("")
        return commands

    def generate_implementation_specific_commands(self) -> List[str]:
        """Generate Python implementation specific commands."""
        commands = self.generate_python_dependencies()
        commands.extend(
            [
                f"# Build {self.implementation_name}",
                f"RUN git clone {self.repo_url} {self.implementation_name} && \\",
                f"    cd {self.implementation_name} && \\",
                "    pip3 install -e .",
            ]
        )

        return commands


class GoDockerBuilder(BaseDockerBuilder):
    """Docker builder for Go-based QUIC implementations (quic-go)."""

    def __init__(
        self, implementation_name: str, repo_url: str, go_version: str = "1.19"
    ):
        """Initialize Go Docker builder.

        Args:
            implementation_name: Name of the implementation
            repo_url: Git repository URL
            go_version: Go version to install
        """
        super().__init__(implementation_name)
        self.repo_url = repo_url
        self.go_version = go_version

    def generate_go_dependencies(self) -> List[str]:
        """Generate Go-specific dependencies."""
        return [
            f"# Install Go {self.go_version}",
            f"RUN wget https://golang.org/dl/go{self.go_version}.linux-amd64.tar.gz && \\",
            "    tar -C /usr/local -xzf go*.tar.gz && \\",
            "    rm go*.tar.gz",
            'ENV PATH="/usr/local/go/bin:${PATH}"',
            'ENV GOPATH="/opt/go"',
            "",
        ]

    def generate_implementation_specific_commands(self) -> List[str]:
        """Generate Go implementation specific commands."""
        commands = self.generate_go_dependencies()
        commands.extend(
            [
                f"# Build {self.implementation_name}",
                f"RUN git clone {self.repo_url} {self.implementation_name} && \\",
                f"    cd {self.implementation_name} && \\",
                "    go mod download && \\",
                "    go build ./...",
            ]
        )

        return commands


class DockerBuilderFactory:
    """Factory for creating appropriate Docker builders based on implementation type."""

    @staticmethod
    def create_builder(
        implementation_name: str, language: str, **kwargs
    ) -> BaseDockerBuilder:
        """Create appropriate Docker builder.

        Args:
            implementation_name: Name of the implementation
            language: Implementation language (c, rust, python, go)
            **kwargs: Additional arguments for specific builders

        Returns:
            Appropriate Docker builder instance

        Raises:
            ValueError: If language is not supported
        """
        if language.lower() == "c":
            return CDockerBuilder(
                implementation_name=implementation_name,
                repo_url=kwargs.get("repo_url", ""),
                build_commands=kwargs.get("build_commands", []),
            )
        elif language.lower() == "rust":
            return RustDockerBuilder(
                implementation_name=implementation_name,
                repo_url=kwargs.get("repo_url", ""),
                cargo_features=kwargs.get("cargo_features", []),
            )
        elif language.lower() == "python":
            return PythonDockerBuilder(
                implementation_name=implementation_name,
                repo_url=kwargs.get("repo_url", ""),
                python_requirements=kwargs.get("python_requirements", []),
            )
        elif language.lower() == "go":
            return GoDockerBuilder(
                implementation_name=implementation_name,
                repo_url=kwargs.get("repo_url", ""),
                go_version=kwargs.get("go_version", "1.19"),
            )
        else:
            raise ValueError(f"Unsupported language: {language}")


# Predefined builders for common QUIC implementations
QUIC_DOCKER_BUILDERS = {
    "picoquic": CDockerBuilder(
        implementation_name="picoquic",
        repo_url="https://github.com/private-octopus/picoquic.git",
        build_commands=[
            "git submodule init",
            "git submodule update",
            "cmake .",
            "make",
        ],
    ),
    "lsquic": CDockerBuilder(
        implementation_name="lsquic",
        repo_url="https://github.com/litespeedtech/lsquic.git",
        build_commands=[
            "git submodule init",
            "git submodule update",
            "cmake .",
            "make",
        ],
    ),
    "quiche": RustDockerBuilder(
        implementation_name="quiche",
        repo_url="https://github.com/cloudflare/quiche.git",
        cargo_features=["ffi", "pkg-config-meta"],
    ),
    "quinn": RustDockerBuilder(
        implementation_name="quinn", repo_url="https://github.com/quinn-rs/quinn.git"
    ),
    "aioquic": PythonDockerBuilder(
        implementation_name="aioquic",
        repo_url="https://github.com/aiortc/aioquic.git",
        python_requirements=["cryptography", "certifi"],
    ),
    "quic_go": GoDockerBuilder(
        implementation_name="quic-go",
        repo_url="https://github.com/lucas-clemente/quic-go.git",
    ),
    "quant": CDockerBuilder(
        implementation_name="quant",
        repo_url="https://github.com/NTAP/quant.git",
        build_commands=[
            "git submodule update --init --recursive",
            "mkdir Debug",
            "cd Debug",
            "cmake ..",
            "make",
        ],
    ),
    "mvfst": CDockerBuilder(
        implementation_name="mvfst",
        repo_url="https://github.com/facebookincubator/mvfst.git",
        build_commands=["mkdir _build", "cd _build", "cmake ..", "make -j$(nproc)"],
    ),
}
