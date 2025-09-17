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
        self.services_script_map = {
            "radio": "scripts/manage_radio_service.sh",
            "led": "scripts/manage_led_service.sh",
            "fan": "scripts/manage_fan_service.sh",
            "broadcast": "scripts/manage_broadcast_service.sh",
            "mixing": "scripts/manage_mixing_service.sh"
        }

    def save_service_state(self, running_services: Set[str]) -> bool:
        """Save current running services to persistent storage"""
        try:
            state_data = {
                "timestamp": datetime.now().isoformat(),
                "running_services": list(running_services),
                "version": "2.1.0"
            }

            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)

            print(f"Service state saved: {running_services}")
            return True

        except Exception as e:
            print(f"Failed to save service state: {e}")
            return False

    def load_service_state(self) -> Set[str]:
        """Load previously running services from persistent storage"""
        try:
            if not os.path.exists(self.state_file):
                print("No service state file found - starting fresh")
                return set()

            with open(self.state_file, 'r') as f:
                state_data = json.load(f)

            running_services = set(state_data.get("running_services", []))
            timestamp = state_data.get("timestamp", "unknown")

            print(f"Loaded service state from {timestamp}: {running_services}")
            return running_services

        except Exception as e:
            print(f"Failed to load service state: {e}")
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

    def restore_services(self, base_path: str = "/home/payas/cos") -> List[str]:
        """Restore previously running services"""
        restored = []
        failed = []

        # Load the service state
        target_services = self.load_service_state()

        if not target_services:
            print("No services to restore")
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
            if self._restore_single_service(service_name, base_path):
                restored.append(service_name)
                print(f"✅ Restored {service_name} service")
            else:
                failed.append(service_name)
                print(f"❌ Failed to restore {service_name} service")

            # Small delay between service starts
            time.sleep(1)

        # Update state with currently running services (including newly restored)
        final_running = self.get_currently_running_services()
        self.save_service_state(final_running)

        if failed:
            print(f"Failed to restore services: {failed}")

        print(f"Service restoration complete. Running: {final_running}")
        return restored

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
    """Restore services that were running before shutdown"""
    manager = ServicePersistenceManager()
    return manager.restore_services()

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