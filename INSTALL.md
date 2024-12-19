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
# https://www.cherryservers.com/blog/install-python-on-ubuntu
sudo apt install build-essential software-properties-common -y;
sudo add-apt-repository ppa:deadsnakes/ppa;
sudo apt update;
sudo apt install libgraphviz-dev python3.10-venv python3.10-dev docker python3.10-venv
wget  https://bootstrap.pypa.io/get-pip.py;
```

This might interest you:
- [WLS](https://learn.microsoft.com/en-us/windows/wsl/install)
- [WSL docker](https://docs.docker.com/desktop/features/wsl/#prerequisites)
- `docker context use desktop-linux`

## :gear: Pre-commit and Black

```bash
cd PANTHER;
python3.10 -m venv .venv
.venv/bin/python3.10 get-pip.py;
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

```bash
python3.10 -m venv .venv
.venv/bin/pip install panther-net
source .venv/bin/activate
```

## :whale:Docker Installation

The docker image will be automatically built and run when defined in the experiment configuration file.

```bash
cd PANTHER;
python3.10 -m venv .venv
.venv/bin/pip install .
source .venv/bin/activate
cd panther;
```


## :warning: Clean Up


```bash
# To clean Docker images and system:
make clean-docker-full
```

---
