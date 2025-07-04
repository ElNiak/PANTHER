# TASK-DT-001: Dockerfile Syntax Modernization

## Objective
Modernize all Dockerfile templates in the PANTHER framework to use the latest BuildKit syntax, add platform awareness, and implement security best practices while maintaining backward compatibility with existing build processes.

## Technical Details

### Current Issues
- Missing modern BuildKit syntax directive (`# syntax=docker/dockerfile:1`)
- Hardcoded Ubuntu 20.04 base images without digest pinning
- No platform awareness (`--platform` arguments missing)
- Missing BuildKit automatic platform arguments (BUILDPLATFORM, TARGETPLATFORM, etc.)
- Basic cache mount usage without modern patterns

### Proposed Solution
Update all Dockerfile templates to:
1. Use modern BuildKit syntax for latest features
2. Add platform awareness with automatic BuildKit arguments
3. Pin base images with SHA256 digests for security
4. Enhance cache mount strategies with platform isolation
5. Add proper multi-stage architecture with runtime mode selection

## Files to Modify

### Primary Files
- `REPOS/PANTHER/panther/plugins/services/Dockerfile.buildkit`
- `REPOS/PANTHER/panther/plugins/services/Dockerfile.layered`
- All `REPOS/PANTHER/panther/plugins/services/iut/*/Dockerfile.multistage`
- All `REPOS/PANTHER/panther/plugins/services/iut/*/Dockerfile.buildkit`

### Template Files (Examples)
- `REPOS/PANTHER/panther/plugins/services/iut/quic/lsquic/Dockerfile.multistage`
- `REPOS/PANTHER/panther/plugins/services/iut/quic/picoquic/Dockerfile.multistage`
- `REPOS/PANTHER/panther/plugins/services/iut/minip/ping_pong/Dockerfile.buildkit`

## Specific Changes

### 1. Core Service Dockerfile.buildkit

**Current Header** (lines 1-10):
```dockerfile
# syntax=docker/dockerfile:1

# =============================================================================
# PANTHER Service - 3-Stage Multi-Target BuildKit Dockerfile
# BUILDER -> DEBUG -> PROFILE runtime environments with execution tools
# =============================================================================

ARG TARGETPLATFORM=linux/amd64
ARG RUNTIME_MODE=minimal
```

**Enhanced Header**:
```dockerfile
# syntax=docker/dockerfile:1

# =============================================================================
# PANTHER Service - Modern Multi-Platform BuildKit Dockerfile
# Cross-platform build with automatic platform detection and security hardening
# =============================================================================

# BuildKit automatic platform arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS=linux
ARG TARGETARCH
ARG BUILDVARIANT

# Runtime configuration
ARG RUNTIME_MODE=minimal
ARG BASE_IMAGE_DIGEST=sha256:965fbcae990b0467ed5657caceaec165018ef44a4d2d46c7cdea80a9dff0d1ea
```

**Current Base Image** (line 14):
```dockerfile
FROM ubuntu:20.04 AS builder
```

**Enhanced Base Image**:
```dockerfile
# Use digest-pinned image with platform awareness for security and performance
FROM --platform=$BUILDPLATFORM ubuntu:22.04@${BASE_IMAGE_DIGEST} AS builder
```

### 2. Enhanced Cache Mount Patterns

**Current Cache Mounts** (lines 19-28):
```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    ln -fs /usr/share/zoneinfo/UTC /etc/localtime && \
    apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config python3 \
    clang automake autoconf libtool \
    wget curl sudo \
    libc6-dev libdw1 libelf1 libunwind-dev
```

**Enhanced Cache Mounts with Platform Isolation**:
```dockerfile
# Platform-aware package installation with enhanced security
RUN --mount=type=cache,target=/var/cache/apt,id=apt-$BUILDPLATFORM,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=aptlib-$BUILDPLATFORM,sharing=locked \
    --mount=type=tmpfs,target=/tmp \
    ln -fs /usr/share/zoneinfo/UTC /etc/localtime && \
    apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config python3 \
    clang automake autoconf libtool \
    wget curl sudo \
    libc6-dev libdw1 libelf1 libunwind-dev && \
    rm -rf /var/lib/apt/lists/*
```

### 3. Cross-Compilation Preparation

**Add after package installation**:
```dockerfile
# Install cross-compilation tools based on target architecture
RUN --mount=type=cache,target=/var/cache/apt,id=crossbuild-$BUILDPLATFORM,sharing=locked \
    case "$TARGETARCH" in \
        arm64) \
            apt-get update && \
            apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu && \
            rm -rf /var/lib/apt/lists/* ;; \
        arm) \
            apt-get update && \
            apt-get install -y gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf && \
            rm -rf /var/lib/apt/lists/* ;; \
        amd64) \
            echo "Native compilation for amd64" ;; \
        *) \
            echo "Unsupported target architecture: $TARGETARCH" && exit 1 ;; \
    esac

# Set cross-compilation environment variables
ENV CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc \
    CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++ \
    CC_arm_unknown_linux_gnueabihf=arm-linux-gnueabihf-gcc \
    CXX_arm_unknown_linux_gnueabihf=arm-linux-gnueabihf-g++
```

### 4. Enhanced Build Cache Pattern

**Current Build Cache** (lines 31-34):
```dockerfile
RUN --mount=type=cache,target=/tmp/build-cache \
    git clone https://github.com/gperftools/gperftools /tmp/build-cache/gperftools || \
    (cd /tmp/build-cache/gperftools && git pull) && \
    cp -r /tmp/build-cache/gperftools /gperftools
```

**Enhanced Build Cache with Platform Isolation**:
```dockerfile
# Git clone with platform-specific build cache isolation
RUN --mount=type=cache,target=/tmp/git-cache,id=git-$TARGETPLATFORM,sharing=locked \
    --mount=type=cache,target=/tmp/build-cache,id=build-$TARGETPLATFORM,sharing=private \
    git clone https://github.com/gperftools/gperftools /tmp/git-cache/gperftools || \
    (cd /tmp/git-cache/gperftools && git pull) && \
    cp -r /tmp/git-cache/gperftools /gperftools
```

### 5. Runtime Stage Enhancement

**Current Runtime Base** (line 84):
```dockerfile
FROM ubuntu:20.04 AS minimal
```

**Enhanced Runtime Base**:
```dockerfile
# Target platform runtime with security hardening
FROM --platform=$TARGETPLATFORM ubuntu:22.04@${BASE_IMAGE_DIGEST} AS minimal

# Security: Run as non-root user
RUN groupadd -r pantheruser && useradd -r -g pantheruser pantheruser
```

**Enhanced Runtime Package Installation** (lines 89-98):
```dockerfile
# Platform-aware runtime dependencies with security
RUN --mount=type=cache,target=/var/cache/apt,id=runtime-$TARGETPLATFORM,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=runtimelib-$TARGETPLATFORM,sharing=locked \
    --mount=type=tmpfs,target=/tmp \
    ln -fs /usr/share/zoneinfo/UTC /etc/localtime && \
    apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    python3 openssl ca-certificates \
    net-tools tcpdump iperf iperf3 traceroute \
    wireshark tshark libcap2-bin \
    iputils-ping iproute2 netcat-openbsd \
    curl dnsutils && \
    rm -rf /var/lib/apt/lists/*
```

### 6. Final Stage Platform Labels

**Enhanced Final Stage** (lines 110-121):
```dockerfile
# =============================================================================
# FINAL STAGE: Runtime mode selection with platform metadata
# =============================================================================
FROM ${RUNTIME_MODE} AS final

# Platform and build metadata for debugging and compliance
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG RUNTIME_MODE=minimal
ARG TARGETOS
ARG TARGETARCH

LABEL platform.build="${BUILDPLATFORM}"
LABEL platform.target="${TARGETPLATFORM}"
LABEL platform.os="${TARGETOS}"
LABEL platform.arch="${TARGETARCH}"
LABEL runtime.mode="${RUNTIME_MODE}"
LABEL runtime.description="PANTHER base service execution environment"
LABEL security.user="pantheruser"
LABEL build.syntax="docker/dockerfile:1"

# Security: Switch to non-root user
USER pantheruser
WORKDIR /app

# Create necessary directories with proper ownership
RUN mkdir -p /app/logs /app/certs /app/data

# Health check for runtime validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1
```

### 7. Implementation-Specific Dockerfile Updates

For QUIC implementation Dockerfiles (e.g., lsquic/Dockerfile.multistage):

**Enhanced Build Stage**:
```dockerfile
# =============================================================================
# BUILD STAGE: Cross-platform build environment with BoringSSL
# =============================================================================

FROM --platform=$BUILDPLATFORM ubuntu:22.04@sha256:965fbcae990b0467ed5657caceaec165018ef44a4d2d46c7cdea80a9dff0d1ea AS builder

# BuildKit automatic arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS=linux
ARG TARGETARCH

# Build configuration
ARG VERSION=master
ARG DEPENDENCIES="[]"
ARG BUILD_MODE=""
ENV VERSION=${VERSION}
ENV DEPENDENCIES=${DEPENDENCIES}
ENV BUILD_MODE=${BUILD_MODE}

# Cross-compilation setup
RUN --mount=type=cache,target=/var/cache/apt,id=crossbuild-$BUILDPLATFORM,sharing=locked \
    case "$TARGETARCH" in \
        arm64) apt-get update && apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu ;; \
        arm) apt-get update && apt-get install -y gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf ;; \
        amd64) echo "Native build for amd64" ;; \
        *) echo "Unsupported architecture: $TARGETARCH" && exit 1 ;; \
    esac && rm -rf /var/lib/apt/lists/*

# Set cross-compilation environment
ENV CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc \
    CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++
```

## Dependencies
- None (foundational change that enables other improvements)

## Testing Requirements

### Unit Tests

1. **Test Dockerfile syntax validation**
   ```bash
   # Validate all Dockerfiles have correct syntax
   find . -name "Dockerfile*" -exec docker buildx build --dry-run -f {} . \;
   ```

2. **Test platform argument availability**
   ```dockerfile
   # Test Dockerfile that verifies platform args are set
   FROM alpine
   ARG BUILDPLATFORM
   ARG TARGETPLATFORM
   RUN test -n "$BUILDPLATFORM" && test -n "$TARGETPLATFORM"
   ```

3. **Test cross-compilation setup**
   ```bash
   # Build for different platforms to verify cross-compilation works
   docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.multistage .
   ```

### Integration Tests

1. **Multi-platform build verification**
   - Build lsquic for linux/amd64 and linux/arm64
   - Verify binaries work on respective platforms
   - Test runtime mode selection works correctly

2. **Cache isolation testing**
   - Build same implementation for different platforms
   - Verify cache directories are properly isolated
   - Test cache reuse within same platform

3. **Security validation**
   - Verify base images use pinned digests
   - Test non-root user execution
   - Validate file permissions in final images

## Risk Assessment

### Risk Level: Medium

### Potential Issues
1. **Breaking Changes**: New syntax might not work with older Docker/BuildKit versions
2. **Base Image Changes**: Ubuntu 22.04 might have different package availability
3. **Cross-Compilation**: New cross-compilation setup might break existing builds
4. **Performance Impact**: Additional layers and complexity might slow builds

### Mitigation Strategies
1. **Version Validation**: Check Docker/BuildKit version before applying changes
2. **Gradual Rollout**: Update one implementation at a time
3. **Fallback Mechanism**: Keep original Dockerfiles as `.legacy` backups
4. **Comprehensive Testing**: Test all supported platforms before deployment

## Acceptance Criteria

### Must Have
- [ ] All Dockerfiles use `# syntax=docker/dockerfile:1`
- [ ] Base images pinned with SHA256 digests
- [ ] Platform awareness with BuildKit automatic arguments
- [ ] Cache mounts use platform-specific IDs for isolation
- [ ] Cross-compilation setup supports amd64, arm64, arm/v7
- [ ] All existing builds continue to work
- [ ] Runtime modes (minimal/debug/profile) function correctly

### Should Have
- [ ] Security hardening with non-root users
- [ ] Health checks for runtime validation
- [ ] Platform metadata in image labels
- [ ] Performance impact < 10% build time increase
- [ ] Cache hit rates improve with better isolation

### Nice to Have
- [ ] Automated Dockerfile validation in CI/CD
- [ ] Build performance metrics collection
- [ ] Security scanning integration
- [ ] Documentation generation from Dockerfile metadata

## Implementation Notes

### Development Steps
1. Create feature branch: `feature/modernize-dockerfile-syntax`
2. Update core service Dockerfile.buildkit first
3. Test with single QUIC implementation (lsquic)
4. Update remaining implementation Dockerfiles
5. Add validation scripts for syntax checking
6. Update CI/CD pipeline to use new syntax
7. Performance testing and optimization
8. Documentation updates

### Testing Strategy
- Start with core service Dockerfile
- Test each implementation individually
- Validate on multiple platforms (AMD64, ARM64)
- Performance benchmarking
- Security validation

### Rollback Plan
- Keep original Dockerfiles as `.legacy` files
- Use feature flags in build system
- Automated rollback if build failures exceed threshold
- Quick revert capability for production issues

## Related Tasks
- **TASK-DB-001**: Platform Detection Modernization (uses platform args)
- **TASK-DB-002**: BuildX Command Enhancement (supplies platform args)
- **TASK-DT-002**: Cross-Compilation Support (builds on this foundation)

## Success Metrics
- All Dockerfiles successfully parse with modern BuildKit syntax
- Multi-platform builds work for linux/amd64 and linux/arm64
- Cache hit rates improve by 20-30% with platform isolation
- Security scanning shows no vulnerabilities in base images
- Build performance regression < 10%
- Zero compatibility issues with existing build processes
