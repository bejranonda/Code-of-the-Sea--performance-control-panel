#!/usr/bin/env python3
"""
Service Persistence Manager
Handles saving and restoring service states across system restarts
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Set

class ServicePersistenceManager:
    """Manages service state persistence for automatic restoration"""

    def __init__(self, state_file: str = "/home/payas/cos/cos_service_state.json"):
        self.state_file = state_file
        self.log_file = "/home/payas/cos/service_events.log"
        self.services_script_map = {
            "radio": "scripts/manage_radio_service.sh",
            "led": "scripts/manage_led_service.sh",
            "fan": "scripts/manage_fan_service.sh",
            "broadcast": "scripts/manage_broadcast_service.sh",
            "mixing": "scripts/manage_mixing_service.sh"
        }
        # Track services that failed to start to prevent repeated restart attempts
        self.failed_services = set()

    def log_service_event(self, service_name: str, action: str, reason: str, success: bool = True):
        """Log all service start/stop events with detailed information"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status = "SUCCESS" if success else "FAILED"
            log_entry = f"[{timestamp}] {status}: {service_name.upper()} {action.upper()} - {reason}\n"

            # Read existing logs to keep them manageable (last 1000 entries)
            existing_logs = []
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    existing_logs = f.readlines()

            # Write new log at the top (newest first)
            with open(self.log_file, 'w') as f:
                f.write(log_entry)
                for line in existing_logs[:999]:  # Keep last 999 entries + new one = 1000
                    f.write(line)

            # Also print to console for immediate visibility
            print(f"SERVICE EVENT: {service_name.upper()} {action.upper()} - {reason} ({status})")

        except Exception as e:
            print(f"Failed to log service event: {e}")

    def save_service_state(self, running_services: Set[str], manually_stopped: Set[str] = None) -> bool:
        """Save current running services and manually stopped services to persistent storage"""
        try:
            # Load existing state to preserve manually stopped services
            existing_state = self._load_raw_state()
            existing_manually_stopped = set(existing_state.get("manually_stopped", []))

            # Update manually stopped if provided, otherwise preserve existing
            if manually_stopped is not None:
                final_manually_stopped = manually_stopped
            else:
                final_manually_stopped = existing_manually_stopped

            state_data = {
                "timestamp": datetime.now().isoformat(),
                "running_services": list(running_services),
                "manually_stopped": list(final_manually_stopped),
                "version": "3.0.0"
            }

            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)

            print(f"Service state saved - Running: {running_services}, Manually stopped: {final_manually_stopped}")
            return True

        except Exception as e:
            print(f"Failed to save service state: {e}")
            return False

    def _load_raw_state(self) -> Dict:
        """Load raw state data from file"""
        try:
            if not os.path.exists(self.state_file):
                return {}

            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def load_service_state(self) -> Set[str]:
        """Load previously running services from persistent storage"""
        try:
            state_data = self._load_raw_state()
            if not state_data:
                print("No service state file found - starting fresh")
                return set()

            running_services = set(state_data.get("running_services", []))
            timestamp = state_data.get("timestamp", "unknown")

            print(f"Loaded service state from {timestamp}: {running_services}")
            return running_services

        except Exception as e:
            print(f"Failed to load service state: {e}")
            return set()

    def load_manually_stopped_services(self) -> Set[str]:
        """Load manually stopped services from persistent storage"""
        try:
            state_data = self._load_raw_state()
            manually_stopped = set(state_data.get("manually_stopped", []))
            print(f"Loaded manually stopped services: {manually_stopped}")
            return manually_stopped
        except Exception as e:
            print(f"Failed to load manually stopped services: {e}")
            return set()

    def get_currently_running_services(self) -> Set[str]:
        """Detect which services are currently running via PID files and process detection"""
        running = set()

        for service_name in self.services_script_map.keys():
            if self._is_service_running(service_name):
                running.add(service_name)

        return running

    def _is_service_running(self, service_name: str) -> bool:
        """Check if a specific service is currently running"""
        try:
            # Check PID file first
            pid_file = f"/tmp/{service_name}_service.pid"
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())

                # Check if process with this PID exists
                try:
                    os.kill(pid, 0)  # Signal 0 checks if process exists
                    return True
                except OSError:
                    # PID file exists but process doesn't - clean up stale PID file
                    os.remove(pid_file)

            return False

        except Exception:
            return False

    def restore_services(self, base_path: str = "/home/payas/cos", force_all_services: bool = False) -> List[str]:
        """Restore previously running services (respects manual stops)"""
        restored = []
        failed = []

        # Load manually stopped services to respect user decisions
        manually_stopped = self.load_manually_stopped_services()

        if force_all_services:
            # Start ALL services EXCEPT manually stopped ones (for exhibition reliability)
            print("🚀 Starting all services by default for exhibition mode...")
            all_services = set(self.services_script_map.keys())
            target_services = all_services - manually_stopped
            print(f"All services: {all_services}")
            print(f"Manually stopped services: {manually_stopped}")
            print(f"Target services for auto-start: {target_services}")
        else:
            # Load the service state (default behavior)
            previously_running = self.load_service_state()
            # Only restore services that were running AND not manually stopped
            target_services = previously_running - manually_stopped
            print(f"Previously running: {previously_running}")
            print(f"Manually stopped services: {manually_stopped}")
            print(f"Target services to restore: {target_services}")
            if not target_services:
                print("No services to restore - respecting user preferences")
                return restored

        # Get currently running services to avoid duplicates
        currently_running = self.get_currently_running_services()

        # Only restore services that aren't already running
        to_restore = target_services - currently_running

        if currently_running:
            print(f"Services already running: {currently_running}")

        if not to_restore:
            print("All target services are already running")
            return list(currently_running)

        print(f"Restoring services: {to_restore}")

        # Restore each service
        for service_name in to_restore:
            # Skip services that previously failed to start (until manually started)
            if service_name in self.failed_services:
                print(f"⚠️  Skipping {service_name} - previously failed to start (manual start required)")
                self.log_service_event(service_name, "AUTO_START_SKIPPED", "Service previously failed - manual intervention required")
                continue

            if self._restore_single_service(service_name, base_path):
                restored.append(service_name)
                # Clear from failed services on successful start
                self.failed_services.discard(service_name)
                self.log_service_event(service_name, "AUTO_STARTED", "Automatic startup after unified app restart")
                print(f"✅ Restored {service_name} service")
            else:
                failed.append(service_name)
                # Mark service as failed to prevent repeated restart attempts
                self.failed_services.add(service_name)
                self.log_service_event(service_name, "AUTO_START_FAILED", "Failed during automatic startup - will not auto-retry until manual start", False)
                print(f"❌ Failed to restore {service_name} service - marked for manual intervention")

            # Small delay between service starts
            time.sleep(1)

        # Update state with currently running services (including newly restored)
        final_running = self.get_currently_running_services()
        self.save_service_state(final_running)

        if failed:
            print(f"Failed to restore services: {failed}")

        print(f"Service restoration complete. Running: {final_running}")
        return restored

    def mark_service_manually_stopped(self, service_name: str) -> bool:
        """Mark a service as manually stopped to prevent auto-restart"""
        try:
            manually_stopped = self.load_manually_stopped_services()
            manually_stopped.add(service_name)

            # Log the manual stop action
            self.log_service_event(service_name, "MARKED_STOPPED", "User clicked STOP button in dashboard")

            # Save updated state
            current_running = self.get_currently_running_services()
            return self.save_service_state(current_running, manually_stopped)
        except Exception as e:
            self.log_service_event(service_name, "MARK_STOPPED_FAILED", f"Error marking as manually stopped: {e}", False)
            print(f"Failed to mark {service_name} as manually stopped: {e}")
            return False

    def mark_service_manually_started(self, service_name: str) -> bool:
        """Remove a service from manually stopped list and failed services list (allow auto-restart)"""
        try:
            manually_stopped = self.load_manually_stopped_services()
            manually_stopped.discard(service_name)  # Remove if present, no error if not

            # Clear from failed services list since user manually started it
            self.failed_services.discard(service_name)

            # Log the manual start action
            self.log_service_event(service_name, "MARKED_STARTED", "User clicked START button in dashboard - cleared from failed services")

            # Save updated state
            current_running = self.get_currently_running_services()
            return self.save_service_state(current_running, manually_stopped)
        except Exception as e:
            self.log_service_event(service_name, "MARK_STARTED_FAILED", f"Error marking as manually started: {e}", False)
            print(f"Failed to remove {service_name} from manually stopped list: {e}")
            return False

    def _restore_single_service(self, service_name: str, base_path: str) -> bool:
        """Restore a single service using the service management scripts"""
        try:
            script_path = self.services_script_map.get(service_name)
            if not script_path:
                print(f"No script mapping found for service: {service_name}")
                return False

            full_script_path = os.path.join(base_path, script_path)

            if not os.path.exists(full_script_path):
                print(f"Service script not found: {full_script_path}")
                return False

            # Execute the start command
            import subprocess
            result = subprocess.run(
                [full_script_path, "start"],
                cwd=base_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True
            else:
                print(f"Service start failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"Error restoring {service_name}: {e}")
            return False

    def update_running_services(self, base_path: str = "/home/payas/cos") -> None:
        """Update the persistent state with currently running services"""
        current_services = self.get_currently_running_services()
        self.save_service_state(current_services)
        print(f"Updated service state: {current_services}")

    def clear_service_state(self) -> bool:
        """Clear the persistent service state file"""
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                print("Service state cleared")
            return True
        except Exception as e:
            print(f"Failed to clear service state: {e}")
            return False


# Convenience functions for direct use
def save_current_service_state():
    """Save the current service state"""
    manager = ServicePersistenceManager()
    current_services = manager.get_currently_running_services()
    return manager.save_service_state(current_services)

def restore_previous_services():
    """Start all services by default for exhibition reliability"""
    manager = ServicePersistenceManager()
    return manager.restore_services(force_all_services=True)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        manager = ServicePersistenceManager()

        if command == "save":
            save_current_service_state()
        elif command == "restore":
            restore_previous_services()
        elif command == "status":
            running = manager.get_currently_running_services()
            print(f"Currently running services: {running}")
        elif command == "clear":
            manager.clear_service_state()
        else:
            print("Usage: python service_persistence.py [save|restore|status|clear]")
    else:
        print("Usage: python service_persistence.py [save|restore|status|clear]")