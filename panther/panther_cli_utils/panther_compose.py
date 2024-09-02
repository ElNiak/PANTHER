# panther_compose.py
import docker
from panther_cli import execute_command
import logging
import yaml
import shutil


def update_docker_compose(config, yaml_path="docker-compose.yml", prod=False):
    """_summary_

    Args:
        config (_type_): _description_
        yaml_path (str, optional): _description_. Defaults to "docker-compose.yml".
        prod (bool, optional): _description_. Defaults to False.

    Returns:
        _type_: _description_
    """
    with open(yaml_path, "r") as file:
        # save backup version
        shutil.copyfile(yaml_path, f"{yaml_path}.bak")
        docker_compose = yaml.safe_load(file)

    # TODO update for production
    base_ip = [172, 27, 1, 11]
    base_port = 49160
    defined_services = set()
    defined_services.add("panther-webapp")
    implem_build_commands = dict(config.items("implem_build_commands"))

    # Get docker limits from config
    normal_cpu = config["docker_limits"]["normal_cpu"]
    normal_mem = config["docker_limits"]["normal_mem"]
    shadow_cpu = config["docker_limits"]["shadow_cpu"]
    shadow_mem = config["docker_limits"]["shadow_mem"]
    shadow_support = config["shadow_support"]

    for implem, should_build in config["implems"].items():
        if should_build.lower() == "true":
            tag, path, dockerfile = eval(implem_build_commands[implem])
            service_name = tag.replace("_", "-") + "-panther"
            defined_services.add(service_name)

            base_ip[-1] += 1
            base_port += 1
            ipv4_address = ".".join(map(str, base_ip))
            port = base_port

            is_shadow = shadow_support.getboolean(implem)
            cpus = shadow_cpu if is_shadow else normal_cpu
            memory = shadow_mem if is_shadow else normal_mem

            if prod:
                volumes = ["/tmp/.X11-unix:/tmp/.X11-unix"]
            else:
                volumes = [
                    "/tmp/.X11-unix:/tmp/.X11-unix",
                    "${PWD}/panther_worker/app/:/app/",
                    "/app/panther-ivy/",
                    "/app/implementations/",
                    "${PWD}/panther_worker/app/panther-ivy/protocol-testing/:/app/panther-ivy/protocol-testing/",
                    "${PWD}/panther_worker/app/panther-ivy/ivy/include/:/app/panther-ivy/ivy/include/",
                    "${PWD}/panther_worker/app/panther-ivy/ivy/ivy_to_cpp.py:/app/panther-ivy/ivy/ivy_to_cpp.py",
                    "${PWD}/outputs/tls-keys:/app/tls-keys",
                    "${PWD}/outputs/tickets:/app/tickets",
                    "${PWD}/outputs/qlogs:/app/qlogs",
                ]
            docker_compose["services"]["panther-webapp"]["environment"] = [
                "ROOT_PATH=${PWD}",
                "DISPLAY=${DISPLAY}",
                "XAUTHORITY=~/.Xauthority",
                "COLUMNS=100",
                "FLASK_ENV=development",
                "LINES=100",
                f"LOG_LEVEL={logging.getLogger().level}",
            ]
            docker_compose["services"][service_name] = {
                "hostname": service_name,
                "container_name": service_name,
                "image": f"{service_name}:latest",
                "command": 'bash -c "stty cols 100 rows 100 && python3 panther_client.py"',
                "ports": [f"{port}:80"],
                "volumes": volumes,
                "networks": {"net": {"ipv4_address": ipv4_address}},
                "privileged": True,  # TODO what are the security implications of this?
                "tty": True,
                "stdin_open": True,
                # ,"vm.mmap_rnd_bits=28"  https://github.com/actions/runner-images/issues/9491#issuecomment-1989718917
                "sysctls": ["net.ipv6.conf.all.disable_ipv6=1"],
                "environment": [
                    "DISPLAY=${DISPLAY}",
                    "XAUTHORITY=~/.Xauthority",
                    "ROOT_PATH=${PWD}",
                    'MPLBACKEND="Agg"',
                    "COLUMNS=100",
                    "LINES=100",
                    f"LOG_LEVEL={logging.getLogger().level}",
                    "PYTHONUNBUFFERED=1",
                    "PYTHONPATH=${PYTHONPATH}:/app/implementations/quic-implementations/aioquic/src",
                ],
                "restart": "always",
                "deploy": {
                    "resources": {
                        "limits": {
                            "cpus": cpus,
                            "memory": memory,
                        },
                        "reservations": {
                            "cpus": str(float(cpus) / 2),
                            "memory": str(int(memory.replace("M", "")) / 2) + "M",
                        },
                    },
                },
                "depends_on": ["panther-webapp"],
            }

            if not prod:
                # Spectre/Meltdown mitigation ~30% performance hit
                docker_compose["services"][service_name]["security_opt"] = [
                    "seccomp:unconfined"
                ]

    # Remove services not defined in config
    services_to_remove = set(docker_compose["services"].keys()) - defined_services
    for service in services_to_remove:
        del docker_compose["services"][service]

    with open(yaml_path, "w") as file:
        yaml.safe_dump(docker_compose, file)

    logging.info("Docker Compose configuration updated successfully.")
    return yaml_path, defined_services
