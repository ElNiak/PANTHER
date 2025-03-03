# :wrench: Installation

Note, before implementation were added as submodule. Now we only consider Docker containers installation. (To be updated)

```bash
git clone git@github.com:ElNiak/PANTHER.git;
cd PANTHER;
git submodule update --init --recursive
```

## :wrench: Requirements

Tested on:

* Python 3.10
* Docker version 27.2.1, build 9e34c9b
* Ubuntu 20.04.3 LTS

```bash
sudo apt install libgraphviz-dev python3.10-venv python3.10-dev docker docker
```


-  Verify Docker is installed:

```bash
docker --version;
docker-compose --version;
```

### :gear: Pre-commit and Black

```bash
cd PANTHER;
python3.10 -m venv .venv
.venv/bin/pip install pre-commit black
.venv/bin/pre-commit install
```

## :computer: Local Installation

```bash
cd PANTHER;
python3.10 -m venv .venv
.venv/bin/pip install .
source .venv/bin/activate
```

## :whale: Pypi Installation

- [Pypi Installation](https://pypi.org/project/panther-net/)

```bash
python3.10 -m venv .venv
.venv/bin/pip install panther_net
source .venv/bin/activate
```

## :whale:Docker Installation

The docker image will be automatically built and run when defined in the experiment configuration file.

```bash
cd PANTHER;
python3.10 -m venv .venv
.venv/bin/pip install .
source .venv/bin/activate
```


## :warning: Clean Up


```bash
# To clean Docker images and system:
make clean-docker-full
```

---
