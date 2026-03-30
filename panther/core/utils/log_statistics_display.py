"""Log Statistics Display.

Real-time display system for logging statistics with threading support
and configurable display modes for live monitoring during experiments.
"""

import signal
import sys
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from .log_statistics_collector import LogStatisticsCollector
from .log_statistics_reporter import LogStatisticsReporter


class LogStatisticsDisplay:
    """Real-time display system for logging statistics.

    Provides live statistics updates in a separate thread during experiment
    execution with configurable display modes and update intervals.
    """

    def __init__(
        self,
        collector: LogStatisticsCollector,
        interval: int = 10,
        display_mode: str = "detailed",
        auto_clear: bool = True,
    ):
        """Initialize the real-time display system.

        Args:
            collector: The statistics collector to display from
            interval: Update interval in seconds
            display_mode: Display mode ('compact', 'detailed', 'minimal', 'dashboard')
            auto_clear: Whether to clear screen between updates
        """
        self.collector = collector
        self.reporter = LogStatisticsReporter(collector)
        self.interval = interval
        self.display_mode = display_mode
        self.auto_clear = auto_clear

        # Threading control
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Display state
        self.update_count = 0
        self.start_time: Optional[datetime] = None
        self.last_update: Optional[datetime] = None

        # Display customization
        self.show_features = True
        self.show_performance = True
        self.show_errors = True
        self.max_features_displayed = 5

        # Callbacks for custom handling
        self.update_callbacks: list[Callable[[Dict[str, Any]], None]] = []

        # Handle graceful shutdown
        self._setup_signal_handlers()

    def start_display(self) -> bool:
        """Start real-time statistics display in separate thread.

        Returns:
            True if started successfully, False if already running
        """
        if self.running:
            return False

        self.running = True
        self.start_time = datetime.now()
        self._stop_event.clear()

        self.thread = threading.Thread(
            target=self._display_loop, name="LogStatisticsDisplay", daemon=True
        )
        self.thread.start()

        return True

    def stop_display(self) -> None:
        """Stop real-time display and cleanup."""
        if not self.running:
            return

        self.running = False
        self._stop_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

        # Final update
        self._print_final_summary()

    def _display_loop(self) -> None:
        """Main display loop running in separate thread."""
        try:
            while self.running and not self._stop_event.wait(self.interval):
                self._update_display()
                self.update_count += 1
                self.last_update = datetime.now()

        except Exception as e:
            print(f"Error in statistics display loop: {e}")
        finally:
            self.running = False

    def _update_display(self) -> None:
        """Update the display with current statistics."""
        try:
            # Get current statistics
            stats = self.collector.get_real_time_stats()

            # Call custom callbacks
            for callback in self.update_callbacks:
                try:
                    callback(stats)
                except Exception as e:
                    print(f"Error in display callback: {e}")

            # Clear screen if requested
            if self.auto_clear and self.display_mode != "minimal":
                self._clear_screen()

            # Display based on mode
            if self.display_mode == "compact":
                self._display_compact(stats)
            elif self.display_mode == "detailed":
                self._display_detailed(stats)
            elif self.display_mode == "minimal":
                self._display_minimal(stats)
            elif self.display_mode == "dashboard":
                self._display_dashboard(stats)
            else:
                self._display_detailed(stats)  # Default fallback

        except Exception as e:
            print(f"Error updating statistics display: {e}")

    def _display_compact(self, stats: Dict[str, Any]) -> None:
        """Display compact one-line statistics."""
        session = stats["session_info"]
        errors = stats["error_statistics"]
        perf = stats["performance_metrics"]

        timestamp = datetime.now().strftime("%H:%M:%S")

        print(
            f"\r[{timestamp}] 📊 Logs: {session['total_messages']} | "
            f"Rate: {session['messages_per_second']:.1f}/s | "
            f"Errors: {errors['total_errors']} ({errors['error_rate_percent']:.1f}%) | "
            f"Memory: {perf.get('memory_usage_mb', 0):.1f}MB",
            end="",
            flush=True,
        )

    def _display_minimal(self, stats: Dict[str, Any]) -> None:
        """Display minimal statistics (no clearing, just append)."""
        session = stats["session_info"]
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(
            f"[{timestamp}] Logs: {session['total_messages']}, Rate: {session['messages_per_second']:.1f}/s"
        )

    def _display_detailed(self, stats: Dict[str, Any]) -> None:
        """Display detailed multi-section statistics."""
        self.reporter.print_real_time_stats(
            show_features=self.show_features,
            show_performance=self.show_performance,
            compact=False,
        )

        # Add display metadata
        print(
            f"\n🕐 Last Update: {datetime.now().strftime('%H:%M:%S')} | "
            f"Update #{self.update_count} | "
            f"Display Mode: {self.display_mode.title()}"
        )

        if self.interval > 1:
            print(f"⏱️  Next update in {self.interval} seconds...")

    def _display_dashboard(self, stats: Dict[str, Any]) -> None:
        """Display dashboard-style statistics with visual elements."""
        session = stats["session_info"]
        distribution = stats["message_distribution"]
        errors = stats["error_statistics"]
        performance = stats["performance_metrics"]

        # Header with visual separator
        print("┌" + "─" * 78 + "┐")
        print("│" + "🐾 PANTHER LOGGING DASHBOARD".center(78) + "│")
        print("├" + "─" * 78 + "┤")

        # Main metrics in columns
        duration = session["duration_seconds"]
        total_msgs = session["total_messages"]
        rate = session["messages_per_second"]
        error_rate = errors["error_rate_percent"]

        print(
            f"│ Duration: {duration:8.1f}s │ Messages: {total_msgs:8d} │ Rate: {rate:8.1f}/s │ Errors: {error_rate:6.1f}% │"
        )

        # Visual level distribution
        print("├" + "─" * 78 + "┤")
        print("│ Level Distribution" + " " * 60 + "│")

        total = max(session["total_messages"], 1)
        for level, count in distribution["by_level"].items():
            percentage = (count / total) * 100
            bar = self._create_visual_bar(percentage, 50)
            print(f"│ {level:8s}: {bar} {percentage:5.1f}% ({count:6d}) │")

        # Feature activity
        if self.show_features and distribution["by_feature"]:
            print("├" + "─" * 78 + "┤")
            print("│ Top Features" + " " * 66 + "│")

            features = list(distribution["by_feature"].items())[:3]  # Top 3
            for feature, count in features:
                percentage = (count / total) * 100
                bar = self._create_visual_bar(percentage, 40)
                print(f"│ {feature[:15]:15s}: {bar} {percentage:5.1f}% │")

        # Performance indicators
        if self.show_performance:
            print("├" + "─" * 78 + "┤")
            memory_mb = performance.get("memory_usage_mb", 0)
            peak_rate = performance.get("peak_message_rate", 0)

            print(
                f"│ Memory: {memory_mb:6.1f}MB │ Peak Rate: {peak_rate:8.1f}/s │ Updates: {self.update_count:6d} │"
            )

        print("└" + "─" * 78 + "┘")

        # Status line
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Last updated: {timestamp} | Next update in {self.interval}s")

    def _create_visual_bar(self, percentage: float, width: int) -> str:
        """Create a visual progress bar with Unicode characters."""
        filled = int((percentage / 100) * width)
        empty = width - filled

        # Use different characters for better visual appeal
        if filled == 0:
            return "░" * width
        elif filled == width:
            return "█" * width
        else:
            return "█" * filled + "▒" * min(1, empty) + "░" * max(0, empty - 1)

    def _clear_screen(self) -> None:
        """Clear the terminal screen."""
        try:
            # ANSI escape sequence to clear screen and move cursor to top
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
        except Exception:
            # Fallback for systems that don't support ANSI
            pass

    def _print_final_summary(self) -> None:
        """Print final summary when display stops."""
        if self.auto_clear:
            self._clear_screen()

        print("\n" + "=" * 60)
        print("🏁 FINAL LOGGING STATISTICS SUMMARY")
        print("=" * 60)

        try:
            final_stats = self.collector.get_real_time_stats()

            session = final_stats["session_info"]
            distribution = final_stats["message_distribution"]
            errors = final_stats["error_statistics"]

            print(f"📅 Total Duration: {session['duration_seconds']:.1f} seconds")
            print(f"📝 Total Messages: {session['total_messages']}")
            print(
                f"⚡ Average Rate: {session['messages_per_second']:.2f} messages/second"
            )
            print(
                f"❌ Total Errors: {errors['total_errors']} ({errors['error_rate_percent']:.2f}%)"
            )
            print(f"🔄 Display Updates: {self.update_count}")

            if distribution["by_level"]:
                print(f"\n📊 Final Level Distribution:")
                total = session["total_messages"]
                for level, count in distribution["by_level"].items():
                    percentage = (count / max(total, 1)) * 100
                    print(f"  {level:10s}: {count:8d} ({percentage:6.2f}%)")

        except Exception as e:
            print(f"Error generating final summary: {e}")

        print("=" * 60)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            if self.running:
                print("\n🛑 Stopping statistics display...")
                self.stop_display()

        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except Exception:
            # Signal handling might not be available in all environments
            pass

    def add_update_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a callback function to be called on each update.

        Args:
            callback: Function that takes statistics dict as argument
        """
        self.update_callbacks.append(callback)

    def remove_update_callback(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Remove a previously added callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)

    def set_display_options(self, **options) -> None:
        """Update display options dynamically.

        Args:
            **options: Display options to update (show_features, show_performance, etc.)
        """
        for key, value in options.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_display_status(self) -> Dict[str, Any]:
        """Get current status of the display system.

        Returns:
            Dictionary containing display status information
        """
        return {
            "running": self.running,
            "display_mode": self.display_mode,
            "interval_seconds": self.interval,
            "update_count": self.update_count,
            "start_time": self.start_time,
            "last_update": self.last_update,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "auto_clear": self.auto_clear,
            "show_features": self.show_features,
            "show_performance": self.show_performance,
            "callbacks_count": len(self.update_callbacks),
        }

    def take_snapshot(self, filepath: str) -> bool:
        """Take a snapshot of current statistics and save to file.

        Args:
            filepath: Path where to save the snapshot

        Returns:
            True if successful, False otherwise
        """
        from pathlib import Path

        try:
            return self.reporter.save_real_time_snapshot(Path(filepath))
        except Exception as e:
            print(f"Error taking snapshot: {e}")
            return False


class StatisticsDisplayManager:
    """Manager class for handling multiple display instances and configurations."""

    def __init__(self):
        """Initialize the statistics display manager."""
        self.displays: Dict[str, LogStatisticsDisplay] = {}
        self.default_display: Optional[LogStatisticsDisplay] = None

    def create_display(
        self, name: str, collector: LogStatisticsCollector, **kwargs
    ) -> LogStatisticsDisplay:
        """Create a new display instance.

        Args:
            name: Unique name for the display
            collector: Statistics collector instance
            **kwargs: Display configuration options

        Returns:
            Created display instance
        """
        display = LogStatisticsDisplay(collector, **kwargs)
        self.displays[name] = display

        if self.default_display is None:
            self.default_display = display

        return display

    def start_display(self, name: str) -> bool:
        """Start a specific display by name.

        Args:
            name: Name of display to start

        Returns:
            True if started successfully
        """
        if name in self.displays:
            return self.displays[name].start_display()
        return False

    def stop_display(self, name: str) -> None:
        """Stop a specific display by name.

        Args:
            name: Name of display to stop
        """
        if name in self.displays:
            self.displays[name].stop_display()

    def stop_all_displays(self) -> None:
        """Stop all running displays."""
        for display in self.displays.values():
            if display.running:
                display.stop_display()

    def get_display(self, name: str) -> Optional[LogStatisticsDisplay]:
        """Get a display instance by name.

        Args:
            name: Name of display to get

        Returns:
            Display instance or None if not found
        """
        return self.displays.get(name)

    def list_displays(self) -> Dict[str, Dict[str, Any]]:
        """List all displays and their status.

        Returns:
            Dictionary mapping display names to their status
        """
        return {
            name: display.get_display_status()
            for name, display in self.displays.items()
        }


# Global display manager instance
display_manager = StatisticsDisplayManager()


def create_display(
    collector: LogStatisticsCollector,
    display_mode: str = "detailed",
    interval: int = 10,
    **kwargs,
) -> LogStatisticsDisplay:
    """Factory function to create a statistics display.

    Args:
        collector: Statistics collector instance
        display_mode: Display mode ('compact', 'detailed', 'minimal', 'dashboard')
        interval: Update interval in seconds
        **kwargs: Additional display options

    Returns:
        Configured LogStatisticsDisplay instance
    """
    return LogStatisticsDisplay(
        collector=collector, display_mode=display_mode, interval=interval, **kwargs
    )
