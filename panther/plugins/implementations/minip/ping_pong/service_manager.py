import subprocess
import logging
import os
from core.interfaces.service_manager_interface import IServiceManager

class PingPongServiceManager(IServiceManager):
    def __init__(self):
        self.process = None
        self.logger = logging.getLogger("PingPongServiceManager")
    
    def start_service(self, parameters: dict):
        """
        Starts the Picoquic server or client based on the role.
        Parameters should include 'role' and any other necessary configurations.
        """
        role = parameters.get("role")
        if role == "server":
            cmd = "./picoquicdemo_server -p 4443"
        elif role == "client":
            target = parameters.get("target", "picoquic_server")
            message = parameters.get("message", "Hello from Picoquic Client!")
            cmd = f"./picoquicdemo_client -p 4443 -s {target} \"{message}\""
        else:
            self.logger.error(f"Unknown role '{role}'. Cannot start service.")
            return
        
        self.logger.info(f"Starting Picoquic {role} with command: {cmd}")
        try:
            self.process = subprocess.Popen(
                cmd,
                shell=True,
                cwd="/opt/picoquic",  # Adjust based on Dockerfile's WORKDIR
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            self.logger.info(f"Picoquic {role} started with PID {self.process.pid}")
        except Exception as e:
            self.logger.error(f"Failed to start Picoquic {role}: {e}")
    
    def stop_service(self):
        """
        Stops the Picoquic service gracefully.
        """
        if self.process:
            self.logger.info(f"Stopping Picoquic service with PID {self.process.pid}")
            try:
                os.killpg(os.getpgid(self.process.pid), 15)  # SIGTERM
                self.process.wait(timeout=10)
                self.logger.info("Picoquic service stopped successfully.")
            except Exception as e:
                self.logger.error(f"Failed to stop Picoquic service: {e}")
