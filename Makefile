# Determine the number of processing cores available
NPROC := $(shell nproc)

###################################################################################################
# CLEANUP COMMANDS
###################################################################################################

package:
	python -m pip install build wheel
	python -m pip uninstall --yes panther
	rm -rf build/ dist/ *.egg-info;
	python -m build --wheel --no-isolation
	python -m pip install --force-reinstall dist/panther-*.whl

package-dev:
	python -m pip install build wheel
	python -m pip uninstall --yes panther
	rm -rf build/ dist/ *.egg-info;
	python -m build --wheel --no-isolation
	python -m pip install --force-reinstall  --editable .

install-local:
	python -m pip install build wheel
	python -m pip uninstall --yes panther
	python -m build --wheel --no-isolation
	python -m pip install --force-reinstall  --editable .

package-test:
	rm -rf build/ dist/ *.egg-info || true
	python -m pip install .[tests]
	pytest tests/

package-test-ci:
	rm -rf build/ dist/ *.egg-info || true
	python -m pip install .[tests]
	pytest tests/unit/ --cov=panther --cov-report=term-missing

mkdocs:
	rm -rf build/ dist/ *.egg-info || true
	python -m pip install .[doc]
	python docs-gen/mkdocs/automate_mkdocs.py
	gendocs --config docs-gen/mkdocs/mkgendocs.yml
	cp README.md docs/home.md
	cp CHANGELOG.md docs/CHANGELOG.md
	# cp LICENSE docs/LICENSE.md
	cp CONTRIBUTING.md docs/CONTRIBUTING.md
	cp EXPERIMENT_GUIDE.md docs/EXPERIMENT_GUIDE.md
	cp INSTALL.md docs/INSTALL.md
	cp USAGE.md docs/USAGE.md
	cp PACKAGING.md docs/PACKAGING.md
	cp ADDING_EXEC_ENV.md docs/ADDING_EXEC_ENV.md
	cp ADDING_NET_ENV.md docs/ADDING_NET_ENV.md
	cp ADDING_IUT.md docs/ADDING_IUT.md
	cp PLUGIN_GUIDE.md docs/PLUGIN_GUIDE.md
	cp CONFIG_GUIDE.md docs/CONFIG_GUIDE.md
	cp DEV_GUIDE.md docs/DEV_GUIDE.md
	mkdocs build --verbose --config-file mkdocs.yaml
	mkdocs serve --verbose --config-file mkdocs.yaml

mkdocs-ci:
	rm -rf build/ dist/ *.egg-info || true
	python -m pip install .[doc]
	python docs-gen/mkdocs/automate_mkdocs.py
	gendocs --config docs-gen/mkdocs/mkgendocs.yml
	cp README.md docs/home.md
	cp CHANGELOG.md docs/CHANGELOG.md
	# cp LICENSE docs/LICENSE.md
	cp CONTRIBUTING.md docs/CONTRIBUTING.md
	cp EXPERIMENT_GUIDE.md docs/EXPERIMENT_GUIDE.md
	cp INSTALL.md docs/INSTALL.md
	cp ADDING_EXEC_ENV.md docs/ADDING_EXEC_ENV.md
	cp ADDING_NET_ENV.md docs/ADDING_NET_ENV.md
	cp ADDING_IUT.md docs/ADDING_IUT.md
	cp USAGE.md docs/USAGE.md
	cp PACKAGING.md docs/PACKAGING.md
	cp PLUGIN_GUIDE.md docs/PLUGIN_GUIDE.md
	cp CONFIG_GUIDE.md docs/CONFIG_GUIDE.md
	cp DEV_GUIDE.md docs/DEV_GUIDE.md
	mkdocs build --verbose --config-file mkdocs.yaml
	mkdocs gh-deploy --force --clean --config-file mkdocs.yaml
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
