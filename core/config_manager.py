import json
import os
from typing import Dict, Any, Optional
from datetime import datetime


class ConfigManager:
    """Unified configuration management for all services"""
    
    def __init__(self, config_file: str = "unified_config.json"):
        self.config_file = config_file
        self.configs = self._load_configs()
        
        # Default configurations for all services
        self.default_configs = {
            "LED Service": {
                "mode": "Manual LED", 
                "brightness": 50,
                "status_file": "led/led_status.json"
            },
            "Radio Service": {
                "mode": "Fixed", 
                "frequency": 101.1, 
                "direction": "Up",
                "status_file": "radio/radio_status.json"
            },
            "Fan Service": {
                "mode": "Fixed", 
                "speed": 50,
                "status_file": "fan/fan_status.json"
            },
            "Broadcast Service": {
                "mode": "Loop",
                "volume": 50,
                "status_file": "broadcast/broadcast_status.json"
            }
        }
    
    def _load_configs(self) -> Dict[str, Any]:
        """Load configurations with error handling"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def save_configs(self) -> bool:
        """Save configurations with error handling using atomic write"""
        try:
            # Add metadata
            self.configs['_metadata'] = {
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }

            # Use atomic write: write to temp file then rename
            temp_file = self.config_file + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(self.configs, f, indent=2)
            
            # Atomic rename
            os.rename(temp_file, self.config_file)

            # Also update service_config.json for backward compatibility with radio service
            self._update_service_config_file()

            return True
        except Exception as e:
            print(f"Error saving configurations: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return False
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service"""
        if service_name not in self.configs:
            # Initialize with defaults if not exists
            self.configs[service_name] = self.default_configs.get(service_name, {}).copy()
            self.save_configs()
        
        return self.configs[service_name].copy()
    
    def update_service_config(self, service_name: str, updates: Dict[str, Any]) -> bool:
        """Update configuration for a service"""
        try:
            if service_name not in self.configs:
                self.configs[service_name] = self.default_configs.get(service_name, {}).copy()
            
            # Convert numeric strings to appropriate types
            processed_updates = self._process_config_values(service_name, updates)
            
            self.configs[service_name].update(processed_updates)
            return self.save_configs()
        except Exception as e:
            print(f"Error updating config for {service_name}: {e}")
            return False

    def _update_service_config_file(self):
        """Update service_config.json for backward compatibility with radio service"""
        try:
            service_config_file = "service_config.json"

            # Load existing service_config.json if it exists
            if os.path.exists(service_config_file):
                with open(service_config_file, "r") as f:
                    service_config = json.load(f)
            else:
                service_config = {}

            # Update with current configs (excluding metadata)
            for service_name, config in self.configs.items():
                if service_name != '_metadata':
                    # Create a clean copy without status_file
                    clean_config = {k: v for k, v in config.items() if k != 'status_file'}
                    service_config[service_name] = clean_config

            # Save updated service_config.json
            with open(service_config_file, "w") as f:
                json.dump(service_config, f, indent=2)

            print(f"✅ Updated {service_config_file} for backward compatibility")

        except Exception as e:
            print(f"⚠️ Warning: Could not update service_config.json: {e}")
    
    def _process_config_values(self, service_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Convert string values to appropriate types based on service"""
        processed = updates.copy()
        
        try:
            if service_name == "LED Service" and "brightness" in processed:
                processed["brightness"] = int(processed["brightness"])
            elif service_name == "Radio Service":
                if "frequency" in processed:
                    processed["frequency"] = float(processed["frequency"])
            elif service_name == "Fan Service" and "speed" in processed:
                processed["speed"] = int(processed["speed"])
            elif service_name == "Broadcast Service" and "volume" in processed:
                processed["volume"] = int(processed["volume"])
        except ValueError as e:
            print(f"Error converting config values for {service_name}: {e}")
        
        return processed
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all service configurations"""
        # Ensure all services have configs
        for service_name in self.default_configs:
            if service_name not in self.configs:
                self.configs[service_name] = self.default_configs[service_name].copy()
        
        return {k: v for k, v in self.configs.items() if not k.startswith('_')}
    
    def read_service_status(self, service_name: str) -> Dict[str, Any]:
        """Read status from service status file"""
        config = self.get_service_config(service_name)
        status_file = config.get('status_file')
        
        if not status_file or not os.path.exists(status_file):
            return {}
        
        try:
            with open(status_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading status for {service_name}: {e}")
            return {}
    
    def get_all_service_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status from all service status files"""
        statuses = {}
        for service_name in self.default_configs:
            statuses[service_name] = self.read_service_status(service_name)
        return statuses