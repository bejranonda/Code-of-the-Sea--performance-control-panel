#!/usr/bin/env python3
"""
Dashboard State Manager
Handles saving and restoring dashboard mode, options, and configurations
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class DashboardStateManager:
    """Manages dashboard state persistence across restarts"""

    def __init__(self, state_file: str = "dashboard_state.json"):
        self.state_file = state_file
        self.default_state = {
            "mode": "dashboard",
            "service_configs": {},
            "ui_preferences": {
                "theme": "default",
                "auto_refresh": True,
                "refresh_interval": 5
            },
            "last_active_services": [],
            "user_selections": {},
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.0"
        }

    def save_dashboard_state(self, state_data: Dict[str, Any]) -> bool:
        """Save current dashboard state to persistent storage"""
        try:
            # Merge with existing state to preserve other settings
            current_state = self.load_dashboard_state()
            current_state.update(state_data)
            current_state["timestamp"] = datetime.now().isoformat()

            with open(self.state_file, 'w') as f:
                json.dump(current_state, f, indent=2)

            print(f"Dashboard state saved: mode={current_state.get('mode')}")
            return True

        except Exception as e:
            print(f"Failed to save dashboard state: {e}")
            return False

    def load_dashboard_state(self) -> Dict[str, Any]:
        """Load dashboard state from persistent storage"""
        try:
            if not os.path.exists(self.state_file):
                print("No dashboard state file found - using defaults")
                return self.default_state.copy()

            with open(self.state_file, 'r') as f:
                state_data = json.load(f)

            # Ensure all required keys exist with defaults
            for key, default_value in self.default_state.items():
                if key not in state_data:
                    state_data[key] = default_value

            timestamp = state_data.get("timestamp", "unknown")
            print(f"Loaded dashboard state from {timestamp}")
            return state_data

        except Exception as e:
            print(f"Failed to load dashboard state: {e}")
            return self.default_state.copy()

    def save_mode(self, mode: str) -> bool:
        """Save current application mode"""
        return self.save_dashboard_state({"mode": mode})

    def get_mode(self) -> str:
        """Get current application mode"""
        state = self.load_dashboard_state()
        return state.get("mode", "dashboard")

    def save_service_config(self, service_name: str, config: Dict[str, Any]) -> bool:
        """Save configuration for a specific service"""
        state = self.load_dashboard_state()
        if "service_configs" not in state:
            state["service_configs"] = {}

        state["service_configs"][service_name] = {
            **config,
            "last_updated": datetime.now().isoformat()
        }

        return self.save_dashboard_state(state)

    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get saved configuration for a specific service"""
        state = self.load_dashboard_state()
        return state.get("service_configs", {}).get(service_name, {})

    def save_ui_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Save UI preferences (theme, refresh settings, etc.)"""
        state = self.load_dashboard_state()
        state["ui_preferences"].update(preferences)
        return self.save_dashboard_state(state)

    def get_ui_preferences(self) -> Dict[str, Any]:
        """Get saved UI preferences"""
        state = self.load_dashboard_state()
        return state.get("ui_preferences", self.default_state["ui_preferences"])

    def save_user_selection(self, key: str, value: Any) -> bool:
        """Save a user selection (dropdown choice, checkbox state, etc.)"""
        state = self.load_dashboard_state()
        if "user_selections" not in state:
            state["user_selections"] = {}

        state["user_selections"][key] = value
        return self.save_dashboard_state(state)

    def get_user_selection(self, key: str, default: Any = None) -> Any:
        """Get a saved user selection"""
        state = self.load_dashboard_state()
        return state.get("user_selections", {}).get(key, default)

    def save_active_services(self, services: list) -> bool:
        """Save list of currently active services"""
        return self.save_dashboard_state({"last_active_services": services})

    def get_active_services(self) -> list:
        """Get list of previously active services"""
        state = self.load_dashboard_state()
        return state.get("last_active_services", [])

    def restore_unified_config(self, config_manager) -> bool:
        """Restore service configurations to unified_config.json"""
        try:
            state = self.load_dashboard_state()
            service_configs = state.get("service_configs", {})

            if not service_configs:
                print("No service configurations to restore")
                return True

            # Update each service configuration
            for service_name, config in service_configs.items():
                # Remove metadata before saving
                clean_config = {k: v for k, v in config.items() if k != "last_updated"}
                config_manager.update_service_config(service_name, clean_config)

            print(f"Restored configurations for {len(service_configs)} services")
            return True

        except Exception as e:
            print(f"Failed to restore unified config: {e}")
            return False

    def backup_current_config(self, config_manager) -> bool:
        """Backup current configurations from unified_config.json"""
        try:
            all_configs = config_manager.get_all_configs()

            # Save each service configuration
            for service_name, config in all_configs.items():
                if service_name != "_metadata":  # Skip metadata
                    self.save_service_config(service_name, config)

            print(f"Backed up configurations for {len(all_configs)} services")
            return True

        except Exception as e:
            print(f"Failed to backup current config: {e}")
            return False

    def get_full_state(self) -> Dict[str, Any]:
        """Get complete dashboard state for debugging/export"""
        return self.load_dashboard_state()

    def clear_state(self) -> bool:
        """Clear all saved dashboard state"""
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                print("Dashboard state cleared")
            return True
        except Exception as e:
            print(f"Failed to clear dashboard state: {e}")
            return False

    def migrate_legacy_mode(self) -> bool:
        """Migrate from legacy app_mode.json if it exists"""
        try:
            legacy_file = "app_mode.json"
            if os.path.exists(legacy_file):
                with open(legacy_file, 'r') as f:
                    legacy_data = json.load(f)

                mode = legacy_data.get('mode', 'dashboard')
                self.save_mode(mode)

                # Archive the legacy file
                os.rename(legacy_file, f"{legacy_file}.migrated")
                print(f"Migrated legacy mode: {mode}")
                return True

            return False

        except Exception as e:
            print(f"Failed to migrate legacy mode: {e}")
            return False


# Convenience functions for direct use
def save_current_mode(mode: str):
    """Save the current dashboard mode"""
    manager = DashboardStateManager()
    return manager.save_mode(mode)

def get_current_mode():
    """Get the current dashboard mode"""
    manager = DashboardStateManager()
    # Try to migrate legacy mode first
    manager.migrate_legacy_mode()
    return manager.get_mode()

def save_service_configuration(service: str, config: dict):
    """Save service configuration"""
    manager = DashboardStateManager()
    return manager.save_service_config(service, config)

def restore_dashboard_state(config_manager):
    """Restore complete dashboard state"""
    manager = DashboardStateManager()
    return manager.restore_unified_config(config_manager)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        manager = DashboardStateManager()

        if command == "status":
            state = manager.get_full_state()
            print(f"Current mode: {state.get('mode')}")
            print(f"Services configured: {len(state.get('service_configs', {}))}")
            print(f"Last updated: {state.get('timestamp')}")
        elif command == "clear":
            manager.clear_state()
        elif command == "export":
            state = manager.get_full_state()
            print(json.dumps(state, indent=2))
        else:
            print("Usage: python dashboard_state.py [status|clear|export]")
    else:
        print("Usage: python dashboard_state.py [status|clear|export]")