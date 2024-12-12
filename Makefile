# Determine the number of processing cores available
NPROC := $(shell nproc)

###################################################################################################
# CLEANUP COMMANDS
###################################################################################################

package:
	python3.10 -m pip install build wheel
	python3.10 -m pip uninstall --yes panther
	rm -rf build/ dist/ *.egg-info;
	python3.10 -m build --wheel --no-isolation
	python3.10 -m pip install --force-reinstall dist/panther-*.whl

package-dev:
	python3.10 -m pip install build wheel
	python3.10 -m pip uninstall --yes panther
	rm -rf build/ dist/ *.egg-info;
	python3.10 -m build --wheel --no-isolation
	python3.10 -m pip install --force-reinstall  --editable .

package-test:
	pytest

mkdocs:
	python3.10 docs-gen/mkdocs/automate_mkdocs.py
	gendocs --config docs-gen/mkdocs/mkgendocs.yml
	cp README.md docs-gen/home.md
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

clean-docker-volume:
	# Removes all Docker volumes
	docker volume prune -f

# Fully clean Docker environment
clean-docker-full:
	docker system prune -a
