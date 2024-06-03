# panther_swarm.py
import docker
from panther_cli import execute_command
import logging
import yaml
import shutil
from panther_scalability.scalability_policy import *

def update_docker_swarm(config, yaml_path="docker-swarm.yml", prod=False):
    with open(yaml_path, "r") as file:
        # save backup version
        shutil.copyfile(yaml_path, f"{yaml_path}.bak")
        docker_compose = yaml.safe_load(file)

    base_ip = [172, 27, 1, 11]
    base_port = 49160
    defined_services = set()
    defined_services.add("panther-webapp")
    implem_build_commands = dict(config.items("implem_build_commands"))
    
     # Get docker limits from config
    normal_cpu = config['docker_limits']['normal_cpu']
    normal_mem = config['docker_limits']['normal_mem']
    shadow_cpu = config['docker_limits']['shadow_cpu']
    shadow_mem = config['docker_limits']['shadow_mem']
    shadow_support = config['shadow_support']
    

    for implem, should_build in config["implems"].items():
        if should_build.lower() == "true":
            tag, path, dockerfile = eval(implem_build_commands[implem])
            service_name = tag.replace("_", "-") + "-panther"
            defined_services.add(service_name)
            
            base_ip[-1] += 1
            base_port += 1
            ipv4_address = ".".join(map(str, base_ip))
            port = base_port
            
            if prod:
                volumes = [ 
                    "/tmp/.X11-unix:/tmp/.X11-unix" 
                ]
            else:
                volumes = [
                    "/tmp/.X11-unix:/tmp/.X11-unix",
                    "${PWD}/panther_worker/app/:/app/",
                    "/app/panther-ivy/",
                    "/app/implementations/",
                    "${PWD}/panther_worker/app/panther-ivy/protocol-testing/:/app/panther-ivy/protocol-testing/",
                    "${PWD}/panther_worker/app/panther-ivy/ivy/include/:/app/panther-ivy/ivy/include/",
                    "${PWD}/outputs/tls-keys:/app/tls-keys",
                    "${PWD}/outputs/tickets:/app/tickets",
                    "${PWD}/outputs/qlogs:/app/qlogs",
                ]
            
            is_shadow = shadow_support.getboolean(implem)
            cpus = shadow_cpu if is_shadow else normal_cpu
            memory = shadow_mem if is_shadow else normal_mem

            docker_compose["services"][service_name] = {
                "hostname": service_name,
                "container_name": service_name,
                "image": f"{service_name}:latest",
                "command": 'bash -c "stty cols 100 rows 100 && python3 panther_client.py"',
                "ports": [f"{port}:80"],
                "volumes": volumes,
                "networks": {"net": {"ipv4_address": ipv4_address}},
                "privileged": True,
                "tty": True,
                "stdin_open": True,
                # Spectre/Meltdown mitigation ~30% performance hit
                "security_opt": ["seccomp:unconfined"],
                "environment": [
                    "DISPLAY=${DISPLAY}",
                    "XAUTHORITY=~/.Xauthority",
                    "ROOT_PATH=${PWD}",
                    'MPLBACKEND="Agg"',
                    "COLUMNS=100",
                    "LINES=100",
                ],
                "restart": "always",
                "deploy": {
                    "resources": {
                        "limits": {
                            "cpus": cpus,
                            "memory": memory,
                        },
                        "reservations": {
                            "cpus": str(float(cpus)/2), 
                            "memory": str(int(memory.replace("M",""))/2)+"M",
                        },
                    },
                },
                "depends_on": ["panther-webapp"],
            }
            
            if not prod:
                # Spectre/Meltdown mitigation ~30% performance hit
                docker_compose["services"][service_name]["security_opt"] = ["seccomp:unconfined"]

    # Remove services not defined in config
    services_to_remove = set(docker_compose["services"].keys()) - defined_services
    for service in services_to_remove:
        del docker_compose["services"][service]

    with open(yaml_path, "w") as file:
        yaml.safe_dump(docker_compose, file)

    logging.info("Docker Swarm configuration updated successfully.")
    return yaml_path, defined_services

def apply_scalability(service_name, threshold, scale_factor, stack_name="panther"):

    threshold = float(threshold)
    scale_factor = int(scale_factor)

    try:
        subprocess.check_call(["docker", "node", "ls"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        end_script("notManager")

    stack_list = subprocess.check_output(["docker", "stack", "ls"]).decode().split()
    if stack_name not in stack_list:
        end_script("unknownStack")

    service_full_name = f"{stack_name}_{service_name}"
    service_list = subprocess.check_output(["docker", "stack", "services", stack_name]).decode().split()
    if service_full_name not in service_list:
        end_script("unknownService")

    workers_ips = get_workers_ips()

    avg_cpu, replicas = 0.0, 0
    while threshold_not_reached(avg_cpu, threshold):
        avg_cpu, replicas = update_avg(service_full_name, workers_ips)
        logging.info(f"[{service_full_name}] {avg_cpu} < {threshold} ? Yes, threshold not reached.")
        time.sleep(2)

    logging.info(f"[{service_full_name}] {avg_cpu} < {threshold} ? No, threshold reached!")
    new_replicas = replicas * scale_factor
    subprocess.check_call(["docker", "service", "scale", f"{service_full_name}={new_replicas}"])

    logging.info(f"[{service_full_name}] End of {sys.argv[0]}")
