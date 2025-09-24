#!/usr/bin/env python3
"""
Coordinated Service Protection System
Prevents services from stopping themselves inappropriately while avoiding conflicts
between different monitoring and watchdog systems.
"""

import os
import json
import time
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
from dataclasses import dataclass

@dataclass
class ProtectionState:
    """Service protection state tracking"""
    service_name: str
    protected: bool = True
    last_config_check: datetime = None
    original_mode: str = None
    performance_mode_active: bool = False
    forced_stop_allowed: bool = False
    protection_reason: str = "auto-protection"

class ServiceProtectionManager:
    """
    Coordinates service protection across multiple monitoring systems

    Key Features:
    - Prevents services from stopping themselves unexpectedly
    - Coordinates with existing cron jobs and watchdog
    - Respects LED performance mode requirements
    - Provides centralized protection logging
    """

    def __init__(self):
        self.protection_file = "/tmp/cos_service_protection.json"
        self.lock_file = "/tmp/cos_protection.lock"
        self.services = ["fan", "broadcast", "mixing", "radio", "led"]
        self.config_base_path = "/home/payas/cos"
        self.protection_states: Dict[str, ProtectionState] = {}

        # Initialize protection states
        for service in self.services:
            self.protection_states[service] = ProtectionState(service_name=service)

        # Start protection monitoring (but coordinate with existing systems)
        self.running = False
        self.monitor_thread = None

    def _acquire_lock(self) -> bool:
        """Acquire protection lock to coordinate with other monitoring systems"""
        try:
            if os.path.exists(self.lock_file):
                # Check if lock is stale (older than 30 seconds)
                lock_age = time.time() - os.path.getmtime(self.lock_file)
                if lock_age < 30:
                    return False  # Lock is active
                else:
                    os.remove(self.lock_file)  # Remove stale lock

            # Create lock file
            with open(self.lock_file, 'w') as f:
                f.write(f"{os.getpid()}:{datetime.now().isoformat()}")
            return True
        except:
            return False

    def _release_lock(self):
        """Release protection lock"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except:
            pass

    def load_protection_state(self) -> Dict:
        """Load current protection state from file"""
        try:
            if os.path.exists(self.protection_file):
                with open(self.protection_file, 'r') as f:
                    return json.load(f)
            return {}
        except:
            return {}

    def save_protection_state(self):
        """Save protection state to coordinate with other systems"""
        try:
            state_data = {
                "timestamp": datetime.now().isoformat(),
                "pid": os.getpid(),
                "services": {
                    name: {
                        "protected": state.protected,
                        "performance_mode_active": state.performance_mode_active,
                        "forced_stop_allowed": state.forced_stop_allowed,
                        "protection_reason": state.protection_reason,
                        "original_mode": state.original_mode
                    } for name, state in self.protection_states.items()
                }
            }

            with open(self.protection_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            self.log_event(f"Failed to save protection state: {e}", "ERROR")

    def log_event(self, message: str, level: str = "INFO"):
        """Log protection events"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] SERVICE-PROTECTION {level}: {message}"

        # Log to console and file
        print(log_entry)
        try:
            with open("/home/payas/cos/service_protection.log", "a") as f:
                f.write(log_entry + "\n")
        except:
            pass

    def is_performance_mode_active(self) -> bool:
        """Check if LED performance mode is currently active"""
        try:
            # Check the actual LED status file for the real-time mode
            status_file = os.path.join(self.config_base_path, "led", "led_status.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status = json.load(f)
                    mode = status.get("mode", "Disable")
                    # Check if current running mode is a performance mode
                    return mode in ["Musical LED", "Manual LED"]

            # Fallback: check config file if status not available
            config_file = os.path.join(self.config_base_path, "led", "led_config.json")
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    mode = config.get("mode", "disable")
                    # Map LED modes to check for performance modes
                    return mode in ["auto", "manual"]

            return False
        except:
            return False

    def get_service_config_mode(self, service_name: str) -> Optional[str]:
        """Get current service configuration mode"""
        try:
            # Handle LED service special case - it uses different config location
            if service_name == "led":
                config_file = os.path.join(self.config_base_path, "led", "led_config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        # Map LED modes to unified format
                        mode = config.get("mode", "Unknown")
                        if mode in ["manual", "Manual LED"]:
                            return "Manual LED"
                        elif mode in ["auto", "Musical LED"]:
                            return "Musical LED"
                        elif mode in ["lighting", "Lux sensor"]:
                            return "Lux sensor"
                        elif mode == "disable":
                            return "Disable"
                        return mode
            else:
                config_file = os.path.join(self.config_base_path, "config", f"{service_name}_service.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        return config.get("mode", "Unknown")
            return None
        except:
            return None

    def restore_service_config(self, service_name: str, mode: str):
        """Restore service configuration to prevent self-stopping"""
        try:
            # Handle LED service special case
            if service_name == "led":
                config_file = os.path.join(self.config_base_path, "led", "led_config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)

                    # Map unified modes back to LED service format
                    led_mode = mode
                    if mode == "Manual LED":
                        led_mode = "manual"
                    elif mode == "Musical LED":
                        led_mode = "auto"
                    elif mode == "Lux sensor":
                        led_mode = "lighting"
                    elif mode == "Disable":
                        led_mode = "disable"

                    if config.get("mode") != led_mode:
                        config["mode"] = led_mode
                        config["_protection_restored"] = datetime.now().isoformat()
                        config["_protection_reason"] = "auto-protection-restore"

                        with open(config_file, 'w') as f:
                            json.dump(config, f, indent=2)

                        self.log_event(f"Restored LED service config mode to {led_mode} (unified: {mode})")
                        return True
            else:
                config_file = os.path.join(self.config_base_path, "config", f"{service_name}_service.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)

                    if config.get("mode") != mode:
                        config["mode"] = mode
                        config["_protection_restored"] = datetime.now().isoformat()
                        config["_protection_reason"] = "auto-protection-restore"

                        with open(config_file, 'w') as f:
                            json.dump(config, f, indent=2)

                        self.log_event(f"Restored {service_name} config mode to {mode}")
                        return True
            return False
        except Exception as e:
            self.log_event(f"Failed to restore {service_name} config: {e}", "ERROR")
            return False

    def protect_service(self, service_name: str, reason: str = "auto-protection"):
        """Enable protection for a specific service"""
        if service_name in self.protection_states:
            state = self.protection_states[service_name]

            # Store original mode if not already stored
            if not state.original_mode:
                state.original_mode = self.get_service_config_mode(service_name)

            state.protected = True
            state.protection_reason = reason
            state.last_config_check = datetime.now()

            # If service config shows "Disable" but performance mode is not active,
            # restore it to a working mode
            current_mode = self.get_service_config_mode(service_name)
            performance_active = self.is_performance_mode_active()

            if current_mode == "Disable" and not performance_active:
                # Restore to appropriate default mode
                default_modes = {
                    "fan": "Fixed",
                    "broadcast": "Auto",
                    "mixing": "Manual",
                    "radio": "Auto",
                    "led": "Manual LED"
                }
                restore_mode = default_modes.get(service_name, "Auto")
                self.restore_service_config(service_name, restore_mode)
                self.log_event(f"Protected {service_name}: restored from Disable to {restore_mode} (performance mode not active)")

            self.log_event(f"Service protection enabled for {service_name}: {reason}")

    def unprotect_service(self, service_name: str, reason: str = "manual-override"):
        """Disable protection for a specific service"""
        if service_name in self.protection_states:
            state = self.protection_states[service_name]
            state.protected = False
            state.forced_stop_allowed = True
            state.protection_reason = f"unprotected-{reason}"

            self.log_event(f"Service protection disabled for {service_name}: {reason}")

    def enable_performance_mode(self, stopped_services: Set[str]):
        """Temporarily allow services to be stopped for performance mode"""
        performance_active = self.is_performance_mode_active()

        for service_name in stopped_services:
            if service_name in self.protection_states:
                state = self.protection_states[service_name]
                state.performance_mode_active = performance_active
                state.forced_stop_allowed = performance_active

                if performance_active:
                    self.log_event(f"Performance mode: allowing {service_name} to stop")
                else:
                    self.log_event(f"Performance mode ended: re-protecting {service_name}")

        self.save_protection_state()

    def check_and_protect_services(self):
        """Check all services and apply protection as needed"""
        if not self._acquire_lock():
            return  # Another monitoring system is active

        try:
            performance_mode = self.is_performance_mode_active()

            for service_name in self.services:
                state = self.protection_states[service_name]
                current_mode = self.get_service_config_mode(service_name)

                # Update performance mode state
                state.performance_mode_active = performance_mode

                # Only protect if performance mode is NOT active
                if not performance_mode and state.protected:
                    # Remove performance mode flag when exiting performance mode
                    if state.performance_mode_active:
                        self._remove_performance_mode_flag()
                        # Reset forced stop permission
                        state.forced_stop_allowed = False

                        # Auto-switch LED to Lux sensor mode to prevent audio conflicts
                        self._switch_led_to_lux_sensor_mode()
                    # Check if service is in "Disable" mode inappropriately
                    if current_mode == "Disable":
                        # Restore service unless explicitly allowed to stop
                        if not state.forced_stop_allowed:
                            default_modes = {
                                "fan": "Fixed",
                                "broadcast": "Auto",
                                "mixing": "Manual",
                                "radio": "Auto",
                                "led": "Manual LED"
                            }
                            restore_mode = state.original_mode or default_modes.get(service_name, "Auto")
                            self.restore_service_config(service_name, restore_mode)

                            # Also restart the service if it's not running
                            self._restart_service_if_needed(service_name)
                elif performance_mode:
                    # During performance mode, ensure services stay stopped (don't let cron restart them)
                    if service_name != "led":  # LED service should stay running during its own performance mode
                        self.log_event(f"Performance mode active: {service_name} should remain stopped")
                        # Don't restart service during performance mode
                        state.forced_stop_allowed = True
                        state.performance_mode_active = True

                        # Create a flag file to prevent cron jobs from restarting services
                        self._create_performance_mode_flag()

                state.last_config_check = datetime.now()

            self.save_protection_state()

        finally:
            self._release_lock()

    def _create_performance_mode_flag(self):
        """Create a flag file to signal cron jobs that performance mode is active"""
        try:
            flag_file = "/tmp/cos_performance_mode_active"
            with open(flag_file, 'w') as f:
                f.write(f"Performance mode active since: {datetime.now().isoformat()}\n")
                f.write("Services should remain stopped until performance mode ends\n")
        except Exception as e:
            self.log_event(f"Failed to create performance mode flag: {e}", "ERROR")

    def _remove_performance_mode_flag(self):
        """Remove performance mode flag file"""
        try:
            flag_file = "/tmp/cos_performance_mode_active"
            if os.path.exists(flag_file):
                os.remove(flag_file)
                self.log_event("Performance mode flag removed - services can be restarted normally")
        except Exception as e:
            self.log_event(f"Failed to remove performance mode flag: {e}", "ERROR")

    def _switch_led_to_lux_sensor_mode(self):
        """Automatically switch LED service to Lux sensor mode after performance mode"""
        try:
            led_config_file = os.path.join(self.config_base_path, "led", "led_config.json")
            if os.path.exists(led_config_file):
                with open(led_config_file, 'r') as f:
                    led_config = json.load(f)

                current_mode = led_config.get("mode", "disable")
                # Only switch if currently in a performance mode
                if current_mode in ["auto", "manual"]:
                    led_config["mode"] = "lighting"  # Lux sensor mode
                    led_config["_auto_switched"] = datetime.now().isoformat()
                    led_config["_reason"] = "auto-switch-prevent-audio-conflict"

                    with open(led_config_file, 'w') as f:
                        json.dump(led_config, f, indent=2)

                    self.log_event(f"Auto-switched LED from {current_mode} to Lux sensor mode to prevent audio conflicts")
                else:
                    self.log_event(f"LED already in non-performance mode ({current_mode}), no auto-switch needed")
            else:
                self.log_event("LED config file not found for auto-switching", "WARNING")

        except Exception as e:
            self.log_event(f"Failed to auto-switch LED to Lux sensor mode: {e}", "ERROR")

    def _restart_service_if_needed(self, service_name: str):
        """Restart service if it's not running (coordinate with existing cron jobs)"""
        try:
            # LED service has special handling - it's managed by a different cron schedule
            if service_name == "led":
                script_path = f"/home/payas/cos/scripts/manage_led_service.sh"
            else:
                script_path = f"/home/payas/cos/scripts/manage_{service_name}_service.sh"

            if os.path.exists(script_path):
                # Check status first
                status_result = subprocess.run([script_path, "status"],
                                             capture_output=True, text=True, timeout=10)

                if status_result.returncode != 0:  # Service not running
                    # Let the existing cron job handle restart (avoid conflict)
                    # Just log that we detected the issue
                    self.log_event(f"Detected {service_name} service not running - existing monitoring will restart it")

                    # But we can also manually trigger it if urgent
                    start_result = subprocess.run([script_path, "start"],
                                                capture_output=True, text=True, timeout=15)

                    if start_result.returncode == 0:
                        self.log_event(f"Successfully restarted {service_name} service")
                    else:
                        self.log_event(f"Failed to restart {service_name} service: {start_result.stderr}", "ERROR")
        except Exception as e:
            self.log_event(f"Error checking/restarting {service_name}: {e}", "ERROR")

    def start_monitoring(self):
        """Start coordinated protection monitoring"""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.log_event("Service protection monitoring started")

    def stop_monitoring(self):
        """Stop protection monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self._release_lock()
        self.log_event("Service protection monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop (runs less frequently than cron to avoid conflicts)"""
        while self.running:
            try:
                # Run checks every 4 minutes (offset from 3-minute cron jobs)
                # This provides coverage between cron runs without conflicting
                self.check_and_protect_services()

                # Sleep for 240 seconds (4 minutes)
                for _ in range(240):  # Check every second for shutdown
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                self.log_event(f"Error in protection monitoring loop: {e}", "ERROR")
                time.sleep(60)  # Wait before retrying

    def get_protection_status(self) -> Dict:
        """Get current protection status for all services"""
        performance_mode = self.is_performance_mode_active()

        status = {
            "timestamp": datetime.now().isoformat(),
            "performance_mode_active": performance_mode,
            "services": {}
        }

        for service_name, state in self.protection_states.items():
            current_mode = self.get_service_config_mode(service_name)
            status["services"][service_name] = {
                "protected": state.protected,
                "current_mode": current_mode,
                "original_mode": state.original_mode,
                "performance_mode_active": state.performance_mode_active,
                "forced_stop_allowed": state.forced_stop_allowed,
                "protection_reason": state.protection_reason,
                "last_check": state.last_config_check.isoformat() if state.last_config_check else None
            }

        return status


# Global instance for coordination
_protection_manager = None

def get_protection_manager() -> ServiceProtectionManager:
    """Get global protection manager instance"""
    global _protection_manager
    if _protection_manager is None:
        _protection_manager = ServiceProtectionManager()
    return _protection_manager

def start_service_protection():
    """Start coordinated service protection"""
    manager = get_protection_manager()

    # Enable protection for all services by default
    for service in manager.services:
        manager.protect_service(service, "startup-protection")

    manager.start_monitoring()
    return manager

def stop_service_protection():
    """Stop service protection"""
    manager = get_protection_manager()
    manager.stop_monitoring()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        manager = get_protection_manager()

        if command == "start":
            start_service_protection()
            print("Service protection started")
        elif command == "stop":
            stop_service_protection()
            print("Service protection stopped")
        elif command == "status":
            status = manager.get_protection_status()
            print(json.dumps(status, indent=2))
        elif command == "protect" and len(sys.argv) > 2:
            service_name = sys.argv[2]
            manager.protect_service(service_name, "manual-protection")
            print(f"Protection enabled for {service_name}")
        elif command == "unprotect" and len(sys.argv) > 2:
            service_name = sys.argv[2]
            manager.unprotect_service(service_name, "manual-unprotect")
            print(f"Protection disabled for {service_name}")
        else:
            print("Usage: python service_protection.py [start|stop|status|protect <service>|unprotect <service>]")
    else:
        print("Usage: python service_protection.py [start|stop|status|protect <service>|unprotect <service>]")