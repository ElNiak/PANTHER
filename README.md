# PANTHER — Protocol Analysis and Testing Harness for Extensible Research

PANTHER is a **plugin‑based, research‑grade test harness** that lets you design, reproduce, and analyse complex **network‑protocol experiments** without hand‑rolling scripts or bespoke infrastructure.

* **What it solves:**  
  - Validating that a new QUIC or custom protocol implementation behaves correctly under failure, jitter, or adverse timing.  
  - Profiling performance characteristics (CPU, heap, syscall mix) across different builds or OS kernels.  
  - Running formal conformance checks (Ivy) inside a deterministic network simulator (Shadow) to catch logic bugs early.  

* **Core characteristics:**  
  ▸ **Reproducible:** every experiment is defined in a single YAML file and executed in an isolated container environment.  
  ▸ **Extensible:** a plugin system adds new protocols, services, profilers, or network back‑ends with minimal boilerplate.  
  ▸ **Multi‑audience:** useful to academic researchers, industrial developers, security analysts, SRE teams, and educators.

---

## 📑 Table of Contents
1. [Quick Start](quick_start.md)  
2. [Core Component](core_component.md)  
3. [Configuration Guide](configuration_guide.md)  
4. [Execution-Environment Modules](execution_environment_modules.md)  
5. [Network-Environment Modules](network_environment_modules.md)  
6. [Protocol Modules](protocol_modules.md)  
7. [Service (IUT) Modules](service_modules.md)  
8. [Tester Modules](tester_modules.md)  
9. [Web-app Interface](webapp_interface.md)  
10. [Output Analysis](output_analysis.md)  
11. [Developer Guide](developer_guide.md)  
12. [Plugin Developer Guide](plugin_guide.md)

---

## System Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python    | 3.10    | Use `venv` for isolation. |
| Docker    | 27.x    | Required for all orchestration modes. |

`pyproject.toml` is the source of truth for Python dependencies.
`requirements.txt` is a frozen snapshot—**do not edit**.

---

## 🗂️ Related Docs
See each Markdown file for deep dives, hands-on examples, and extension points.