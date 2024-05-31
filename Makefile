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
# RUNNER COMMANDS
###################################################################################################

# Compose the full Docker environment for all implementations
# Launch the web application interface for protocol testing
compose:
	docker network inspect net >/dev/null 2>&1 || docker network create --gateway 172.27.1.1 --subnet 172.27.1.0/24 net
    # Set up host permissions and launch Docker Compose
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/Protocols-Ivy/
	xhost +
	docker compose up -d
    # Update host settings for network testing
	cd src/panther/scripts/hosts/; bash update_etc_hosts.sh

# Start a Docker container for interactive Bash access
# Example: IMPLEM="picoquic" make start-bash
start-bash:
    # Run a Docker container with increased memory limits and volume mounts
	docker run --privileged --cpus="$(NPROC).0" --memory="10g" --memory-reservation="9.5g" \
               -v $(PWD)/tls-keys:/PANTHER/tls-keys \
               -v $(PWD)/tickets:/PANTHER/tickets \
               -v $(PWD)/qlogs:/PANTHER/qlogs \
               -v $(PWD)/src/Protocols-Ivy/doc/examples/quic:/PANTHER/Protocols-Ivy/doc/examples/quic \
               -v $(PWD)/src/Protocols-Ivy/ivy/include/1.7:/PANTHER/Protocols-Ivy/ivy/include/1.7 \
               -it $(IMPLEM)-ivy bash
