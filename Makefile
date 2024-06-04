# Determine the number of processing cores available
NPROC := $(shell nproc)

###################################################################################################
# CLEANUP COMMANDS
###################################################################################################

mkdocs:
	python3 automate_mkdocs.py
	gendocs --config mkgendocs.yml
	cp *.md docs/
	cp -r readme-res/ docs/
	cp README.md docs/home.md
	mkdocs build --verbose
	mkdocs serve 

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
	docker volume prune -a
	# Force removal of all images
	docker rmi $(docker images -a -q)
	