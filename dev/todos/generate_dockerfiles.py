#!/usr/bin/env python3
"""Script to generate standardized Dockerfiles for all QUIC implementations."""

from panther.plugins.services.base.docker_build_base import (
    QUIC_DOCKER_BUILDERS,
    DockerBuilderFactory
)


def generate_all_dockerfiles():
    """Generate Dockerfiles for all QUIC implementations."""
    print("Generating standardized Dockerfiles for QUIC implementations...")
    print("=" * 70)
    
    for impl_name, builder in QUIC_DOCKER_BUILDERS.items():
        print(f"\nGenerating Dockerfile for {impl_name}...")
        
        dockerfile_content = builder.generate_complete_dockerfile()
        
        # Write to file
        dockerfile_path = f"./panther/plugins/services/iut/quic/{impl_name}/Dockerfile.generated"
        
        try:
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            print(f"✅ Generated: {dockerfile_path}")
        except Exception as e:
            print(f"❌ Failed to write {dockerfile_path}: {e}")
    
    print("\n" + "=" * 70)
    print("Dockerfile generation complete!")


def demonstrate_builder_usage():
    """Demonstrate how to use the Docker builder factory."""
    print("\nDemonstrating Docker builder factory usage...")
    print("-" * 50)
    
    # Example: Create a custom C builder
    custom_c_builder = DockerBuilderFactory.create_builder(
        implementation_name="custom_quic",
        language="c",
        repo_url="https://github.com/example/custom-quic.git",
        build_commands=["make clean", "make all"]
    )
    
    print("Custom C builder created:")
    print(custom_c_builder.generate_complete_dockerfile()[:200] + "...")
    
    # Example: Create a custom Rust builder
    custom_rust_builder = DockerBuilderFactory.create_builder(
        implementation_name="custom_rust_quic",
        language="rust",
        repo_url="https://github.com/example/rust-quic.git",
        cargo_features=["crypto", "async"]
    )
    
    print("\nCustom Rust builder created successfully!")


if __name__ == "__main__":
    generate_all_dockerfiles()
    demonstrate_builder_usage()