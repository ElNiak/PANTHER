#!/usr/bin/env python3
"""Universal test service that can simulate any role."""

import json
import os
import sys
import time
from pathlib import Path


def create_output_files():
    """Create output files based on service configuration."""
    log_dir = Path("/app/logs")
    log_dir.mkdir(exist_ok=True)

    service_name = os.environ.get("SERVICE_NAME", "test_service")
    service_role = os.environ.get("SERVICE_ROLE", "server")

    # Standard outputs
    with open(log_dir / "stdout.log", "w") as f:
        f.write(f"Mock {service_role} ({service_name}) started\n")
        f.write(f"Role: {service_role}\n")
        f.write(f"Service: {service_name}\n")
        f.write("Operations completed successfully\n")

    with open(log_dir / "stderr.log", "w") as f:
        f.write(f"Mock {service_role} stderr output\n")

    # SSL keylog file
    with open(log_dir / "sslkeylogfile.txt", "w") as f:
        f.write(f"# SSL Key Log File - {service_name}\n")
        f.write(f"# Role: {service_role}\n")
        f.write("CLIENT_RANDOM mock_random mock_secret\n")

    # Service-specific pcap file
    with open(log_dir / f"{service_name}.pcap", "wb") as f:
        f.write(
            b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00"
        )

    # Create additional files for pattern testing if requested
    create_additional = (
        os.environ.get("CREATE_ADDITIONAL_FILES", "false").lower() == "true"
    )
    if create_additional:
        # Additional SSL keylog patterns
        with open(log_dir / "tls_keylog_custom.txt", "w") as f:
            f.write("Custom TLS keylog\n")

        with open(log_dir / "ssl_keys_debug.keys", "w") as f:
            f.write("Debug SSL keys\n")

        # Additional pcap patterns
        with open(log_dir / "packet_capture_extra.pcapng", "wb") as f:
            f.write(b"\x0a\x0d\x0d\x0a")

        with open(log_dir / "network_trace.cap", "wb") as f:
            f.write(b"\xd4\xc3\xb2\xa1")


def main():
    """Main service execution."""
    service_name = os.environ.get("SERVICE_NAME", "test_service")
    runtime = int(os.environ.get("MOCK_RUNTIME", "5"))

    print(f"Starting universal test service: {service_name}")

    create_output_files()

    # Simulate service runtime
    for i in range(runtime):
        print(f"Service {service_name} running... {i+1}/{runtime}")
        time.sleep(1)

    print(f"Service {service_name} completed successfully")


if __name__ in {"__main__", "__mp_main__"}:
    main()
