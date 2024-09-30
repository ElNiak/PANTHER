# apply_policy_of_scalability.py
import subprocess
import sys
import time
import docker
from paramiko import SSHClient, AutoAddPolicy
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def end_script(reason):
    if reason == "notManager":
        logging.error("This node is not a swarm manager. Run this script on a swarm manager.")
    elif reason == "wrongArgs":
        logging.error(f"Wrong number of arguments.\nUsage: {sys.argv[0]} <name-of-stack> <name-of-service-to-scale> <threshold> <scale>")
    elif reason == "unknownStack":
        logging.error("The stack name you provided does not exist.")
    elif reason == "unknownService":
        logging.error("The service name you provided does not exist.")
    logging.info(f"End of {sys.argv[0]}")
    sys.exit(1)

def get_workers_ips():
    workers_ips = []
    try:
        output = subprocess.check_output(["docker", "node", "ls"]).decode()
        lines = output.strip().split("\n")[1:]
        for line in lines:
            parts = line.split()
            if parts[1] != "*":
                node_id = parts[0]
                node_info = subprocess.check_output(["docker", "node", "inspect", node_id]).decode()
                for line in node_info.split("\n"):
                    if "Addr" in line:
                        ip = line.split(":")[1].strip().strip('"')
                        workers_ips.append(ip)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error: {e.output.decode()}")
    return workers_ips

def update_avg(service, workers_ips):
    total_cpu = 0.0
    replicas = 0

    client = docker.from_env()
    containers = client.containers.list(filters={"name": service})
    for container in containers:
        cpu_usage = get_container_cpu_usage(container.id)
        total_cpu += cpu_usage
        replicas += 1

    for ip in workers_ips:
        ssh_client = SSHClient()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())
        ssh_client.connect(ip)
        stdin, stdout, stderr = ssh_client.exec_command(f"docker ps | grep {service}")
        containers = stdout.read().decode().strip().split("\n")
        for container_info in containers:
            if container_info:
                container_id = container_info.split()[0]
                stdin, stdout, stderr = ssh_client.exec_command(f"docker stats --no-stream {container_id}")
                stats = stdout.read().decode()
                cpu_usage = get_stats_cpu_usage(stats)
                total_cpu += cpu_usage
                replicas += 1
        ssh_client.close()

    if replicas > 0:
        avg_cpu = total_cpu / replicas
    else:
        avg_cpu = 0.0

    return avg_cpu, replicas

def get_container_cpu_usage(container_id):
    client = docker.from_env()
    container_stats = client.containers.get(container_id).stats(stream=False)
    cpu_usage = container_stats["cpu_stats"]["cpu_usage"]["total_usage"]
    system_cpu_usage = container_stats["cpu_stats"]["system_cpu_usage"]
    if system_cpu_usage > 0:
        return (cpu_usage / system_cpu_usage) * 100
    return 0.0

def get_stats_cpu_usage(stats):
    lines = stats.strip().split("\n")
    if len(lines) > 1:
        parts = lines[1].split()
        if "%" in parts[-1]:
            return float(parts[-1].strip("%"))
    return 0.0

def threshold_not_reached(avg_cpu, threshold):
    return avg_cpu < threshold

if __name__ == "__main__":
    if len(sys.argv) != 5:
        end_script("wrongArgs")

    stack_name = sys.argv[1]
    service_name = sys.argv[2]
    threshold = float(sys.argv[3])
    scale_factor = int(sys.argv[4])

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
