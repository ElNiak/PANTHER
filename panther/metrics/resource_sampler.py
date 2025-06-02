"""Resource monitoring for CPU and memory usage."""

import psutil
import threading
import time


class ResourceSampler:
    """Samples system resources (CPU, memory) during operation."""

    def __init__(self, interval: float = 1.0):
        """Initialize the resource sampler.

        Args:
            interval: Sampling interval in seconds
        """
        self.interval = interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._cpu_samples: list[float] = []
        self._memory_samples: list[float] = []
        self._lock = threading.Lock()

        # Get current process for memory monitoring
        self._process = psutil.Process()

    def start(self) -> None:
        """Start resource sampling in a background thread."""
        if self._running:
            return

        self._running = True
        self._cpu_samples.clear()
        self._memory_samples.clear()

        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, float]:
        """Stop resource sampling and return metrics.

        Returns:
            Dictionary containing CPU and memory metrics
        """
        if not self._running:
            return {}

        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

        with self._lock:
            cpu_samples = self._cpu_samples.copy()
            memory_samples = self._memory_samples.copy()

        if not cpu_samples or not memory_samples:
            return {}

        return {
            "cpu.avg_load": sum(cpu_samples) / len(cpu_samples),
            "cpu.max_load": max(cpu_samples),
            "ram.peak_mb": max(memory_samples),
            "ram.avg_mb": sum(memory_samples) / len(memory_samples),
        }

    def _sample_loop(self) -> None:
        """Main sampling loop running in background thread."""
        while self._running:
            try:
                # Sample CPU usage (system-wide)
                cpu_percent = psutil.cpu_percent(interval=None)

                # Sample memory usage (current process)
                memory_info = self._process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB

                with self._lock:
                    self._cpu_samples.append(cpu_percent)
                    self._memory_samples.append(memory_mb)

                time.sleep(self.interval)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process might have changed, try to get new one
                try:
                    self._process = psutil.Process()
                except psutil.NoSuchProcess:
                    break
            except Exception:
                # Ignore sampling errors and continue
                pass

    def get_current_stats(self) -> dict[str, float]:
        """Get current resource usage without stopping sampling.

        Returns:
            Current CPU and memory usage
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            return {
                "cpu.current_load": cpu_percent,
                "ram.current_mb": memory_mb,
            }
        except Exception:
            return {}
