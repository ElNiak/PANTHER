# Determine the number of processing cores available
NPROC := $(shell nproc)

###################################################################################################
# CLEANUP COMMANDS
###################################################################################################

# Clean Docker images and containers
clean:
    # This command removes all stopped containers and unused images
	docker image prune -a

# Remove all unused Docker images
clean-docker:
    # Removes unused Docker images
	docker image prune
    # Removes all Docker images
	docker image prune -a
    # Force removal of all images
	docker rmi $(docker images -a -q)

# Fully clean Docker environment
clean-docker-full:
    # Removes unused Docker images and containers
	docker image prune
	docker image prune -a
    # Fully clean the Docker system (containers, networks, and images)
	docker system prune -a -f
    # Force removal of all images
	docker rmi $(docker images -a -q)

###################################################################################################
# INSTALLATION AND SETUP
###################################################################################################

# Install and update submodules, prepare directories
install:
    # Initialize and update git submodules recursively
	git submodule update --init --recursive
	git submodule update --recursive
    # Checkout specific branches and set up directories for QUIC protocol examples and testing
	cd src/Protocols-Ivy/; git fetch; git checkout development-CoAP
	cd src/Protocols-Ivy; git submodule update --init --recursive
	cd src/Protocols-Ivy; git submodule update --recursive
    # Create necessary directories and files for QUIC, MiniP, and CoAP protocol testing
	cd src/Protocols-Ivy; mkdir -p doc/examples/quic/build; mkdir -p doc/examples/quic/test/temp
	cd src/Protocols-Ivy; mkdir -p protocol-testing/quic/build; mkdir -p protocol-testing/quic/test/temp; touch protocol-testing/quic/test/temp/data.csv
	cd src/Protocols-Ivy; mkdir -p protocol-testing/minip/build; mkdir -p protocol-testing/minip/test/temp; touch protocol-testing/minip/test/temp/data.csv
	cd src/Protocols-Ivy; mkdir -p protocol-testing/coap/build; mkdir -p protocol-testing/coap/test/temp; touch protocol-testing/coap/test/temp/data.csv
	cd src/Protocols-Ivy; mkdir -p protocol-testing/bgp/build; mkdir -p protocol-testing/bgp/test/temp; touch protocol-testing/bgp/test/temp/data.csv
    # Perform additional setup and build Docker containers
	make checkout-git
	make build-docker-compose-full

# Check out specific commits of submodules for consistency
checkout-git:
	cd src/Protocols-Ivy/; git fetch; git checkout development-CoAP
	cd src/Protocols-Ivy; git submodule update --init --recursive
	cd src/Protocols-Ivy; git submodule update --recursive
    # Specific commits are checked out for each submodule to ensure consistency and reproducibility
	cd src/Protocols-Ivy/submodules/picotls/; git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76
    # QUIC implementations
	cd src/implementations/quic-implementations/aioquic/;git checkout d272be10b93b09b75325b139090007dae16b9f16
	cd src/implementations/quic-implementations/boringssl/; git checkout a9670a8b476470e6f874fef3554e8059683e1413; git submodule init; git submodule update
	cd src/implementations/quic-implementations/lsquic/; git checkout 0a4f8953dc92dd3085e48ed90f293f052cff8427; 
	cd src/implementations/quic-implementations/picoquic/; git checkout bb67995f2d7c0e577c2c8788313c3b580d3df9a7; 
	cd src/implementations/quic-implementations/quant/; git checkout 9e309c05f79fb6aa3889dcf7df60b550249d2a2a;  git submodule update --init --recursive
	cd src/implementations/quic-implementations/picoquic/; git checkout bb67995f2d7c0e577c2c8788313c3b580d3df9a7; 
	cd src/implementations/quic-implementations/picotls/; git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76; 

###################################################################################################
# docker build  --network=host COMMANDS
###################################################################################################

# Build Docker images for protocol testing with Shadow
# Example: IMPLEM="picoquic" make build-docker
build-docker:
    # Change ownership of the Ivy Protocol source directory
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/Protocols-Ivy/
    # Build a series of Docker images, each dependent on the previous, for various testing environments
	docker build  --network=host --rm -t ubuntu-ivy -f src/containers/Dockerfile.ubuntu .
    # [+] Building 1046.5s (19/19) FINISHED     
	docker build  --network=host --rm -t ivy -f src/containers/Dockerfile.ivy_1 .
	docker build  --network=host --rm -t shadow-ivy -f src/containers/Dockerfile.shadow .
	docker build  --network=host --rm -t shadow-ivy-picotls -f src/containers/Dockerfile.picotls --build-arg image=shadow-ivy .
	docker build  --network=host --rm -t $(IMPLEM) -f src/containers/Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
	docker build  --network=host --rm -t $(IMPLEM)-ivy -f src/containers/Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# Build Docker images for protocol testing with Shadow from implementation layer
# Example: IMPLEM="picoquic" make build-docker-impem
build-docker-impem:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/Protocols-Ivy/
	docker build  --network=host --rm -t $(IMPLEM) -f src/containers/Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
	docker build  --network=host --rm -t $(IMPLEM)-ivy -f src/containers/Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

build-docker-impem-standalone:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/Protocols-Ivy/
	docker build  --network=host --rm -t ubuntu-ivy -f src/containers/Dockerfile.ubuntu .
	docker build  --network=host --rm -t ivy -f src/containers/Dockerfile.ivy_1 .
	docker build  --network=host -t ivy-picotls -f src/containers/Dockerfile.picotls --build-arg image=ivy .
	docker build  --network=host --rm -t ivy-picotls-standalone -f src/containers/Dockerfile.ivy_2 --build-arg image=ivy-picotls .

# Build Docker images for protocol testing with Shadow
# TODO use docker-compose build command
build-docker-compose:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/Protocols-Ivy/
    # QUIC
	IMPLEM="picoquic-shadow" make build-docker-impem
	# IMPLEM="picoquic-no-retransmission-shadow" make build-docker-impem
	# IMPLEM="picoquic-old-shadow" make build-docker-impem
	# IMPLEM="picoquic" make build-docker-impem
	# IMPLEM="picoquic-shadow-bad" make build-docker-impem
	# IMPLEM="quant" make build-docker-impem
    # MiniP
	IMPLEM="ping-pong" make build-docker-impem
	# IMPLEM="ping-pong-flaky" make build-docker-impem
	# IMPLEM="ping-pong-fail" make build-docker-impem
    # CoAP
    # ...
    # BGP 
    # ...
    # QUIC tools
	# make build-docker-visualizer
	make build-docker-impem-standalone

# Build Docker images for protocol testing with Shadow
build-docker-compose-full:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/Protocols-Ivy/
    # QUIC
	IMPLEM="picoquic-shadow" make build-docker
	# IMPLEM="picoquic-old-shadow" make build-docker-impem
	# IMPLEM="picoquic-shadow-bad" make build-docker-impem
	# IMPLEM="picoquic-no-retransmission-shadow" make build-docker-impem
	IMPLEM="picoquic" make build-docker-impem
	# IMPLEM="quant" make build-docker-impem
    # MiniP
	IMPLEM="ping-pong" make build-docker-impem
	# IMPLEM="ping-pong-flaky" make build-docker-impem
	# IMPLEM="ping-pong-fail" make build-docker-impem
    # CoAP
    # ...
    # BGP 
    # ...
    # QUIC tools
	make build-docker-visualizer
	make build-docker-impem-standalone

###################################################################################################
# RUNNER COMMANDS
###################################################################################################

# Compose the full Docker environment for all implementations
# Launch the web application interface for protocol testing
compose:
	docker network inspect net >/dev/null 2>&1 || docker network create --gateway 172.27.1.1 --subnet 172.27.1.0/24 net
    # Set up host permissions and launch Docker Compose
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/Protocols-Ivy/
	xhost +
	docker-compose up -d
    # Update host settings for network testing
	cd src/pfv/scripts/hosts/; bash update_etc_hosts.sh

# Start a Docker container for interactive Bash access
# Example: IMPLEM="picoquic" make start-bash
start-bash:
    # Run a Docker container with increased memory limits and volume mounts
	docker run --privileged --cpus="$(NPROC).0" --memory="10g" --memory-reservation="9.5g" \
               -v $(PWD)/tls-keys:/PFV/tls-keys \
               -v $(PWD)/tickets:/PFV/tickets \
               -v $(PWD)/qlogs:/PFV/qlogs \
               -v $(PWD)/src/Protocols-Ivy/doc/examples/quic:/PFV/Protocols-Ivy/doc/examples/quic \
               -v $(PWD)/src/Protocols-Ivy/ivy/include/1.7:/PFV/Protocols-Ivy/ivy/include/1.7 \
               -it $(IMPLEM)-ivy bash
