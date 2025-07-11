# syntax=docker/dockerfile:1
# =============================================================================
# PANTHER Builder - Heavy compilation stage (temporary, discarded)
# =============================================================================
FROM panther-build-base AS panther-builder

USER root

# Heavy compilation dependencies that won't be in runtime
RUN --mount=type=cache,target=/var/cache/apt,id=builder-$TARGETPLATFORM,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=builderlib-$TARGETPLATFORM,sharing=locked \
    apt-get update && \
    apt-get install --no-install-recommends -y \
    # Additional build tools
    software-properties-common \
    sudo && \
    rm -rf /var/lib/apt/lists/*

# Build gperftools with comprehensive caching
WORKDIR /gperftools
RUN --mount=type=cache,target=/tmp/git-cache,id=git-gperftools-$TARGETPLATFORM,sharing=locked \
    --mount=type=cache,target=/tmp/build-cache,id=build-gperftools-$TARGETPLATFORM,sharing=private \
    # Use cached repo if available
    if [ -d "/tmp/git-cache/gperftools/.git" ]; then \
        echo "Using cached gperftools repository"; \
        cp -r /tmp/git-cache/gperftools /gperftools; \
        cd /gperftools && git pull; \
    else \
        echo "Cloning fresh gperftools repository"; \
        git clone https://github.com/gperftools/gperftools /gperftools; \
        cp -r /gperftools /tmp/git-cache/gperftools; \
    fi && \
    cd /gperftools && \
    # Use build cache for compilation
    if [ -d "/tmp/build-cache/gperftools-build" ]; then \
        echo "Restoring build cache"; \
        cp -r /tmp/build-cache/gperftools-build/* . 2>/dev/null || true; \
    fi && \
    ./autogen.sh && \
    ./configure && \
    make && \
    make install && \
    # Save build artifacts to cache
    mkdir -p /tmp/build-cache/gperftools-build && \
    cp -r .libs configure Makefile /tmp/build-cache/gperftools-build/ 2>/dev/null || true && \
    whereis libprofiler && whereis libtcmalloc

# Builder metadata (temporary stage)
LABEL panther.stage="builder" \
      panther.temporary="true" \
      panther.artifacts="gperftools"

USER pantheruser
