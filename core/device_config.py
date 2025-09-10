#!/usr/bin/env python3
"""
Device Configuration Manager for Code of the Sea
Manages loading of device-specific credentials and settings
"""

import json
import os
from typing import Dict, Any, Optional

class DeviceConfigError(Exception):
    """Exception raised for device configuration errors"""
    pass

class DeviceConfig:
    """
    Device Configuration Manager
    
    Loads device-specific settings from config/devices.json
    Separates sensitive credentials from code repository
    """
    
    def __init__(self, config_path: str = "config/devices.json"):
        """
        Initialize device configuration
        
        Args:
            config_path: Path to device configuration file
        """
        self.config_path = config_path
        self._config = None
        self.load_config()
    
    def load_config(self) -> None:
        """Load device configuration from file"""
        if not os.path.exists(self.config_path):
            raise DeviceConfigError(
                f"Device configuration not found: {self.config_path}\n"
                f"Please copy config/devices.example.json to {self.config_path} "
                f"and update with your device credentials"
            )
        
        try:
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise DeviceConfigError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise DeviceConfigError(f"Failed to load config: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get complete configuration"""
        return self._config
    
    def get_led_config(self) -> Dict[str, Any]:
        """Get LED controller configuration"""
        return self._config.get('led', {})
    
    def get_tuya_config(self) -> Dict[str, Any]:
        """Get Tuya device configuration for LED controller"""
        led_config = self.get_led_config()
        return led_config.get('tuya_controller', {})
    
    def get_veml7700_config(self) -> Dict[str, Any]:
        """Get VEML7700 light sensor configuration"""
        led_config = self.get_led_config()
        return led_config.get('veml7700_sensor', {})
    
    def get_radio_config(self) -> Dict[str, Any]:
        """Get radio configuration"""
        return self._config.get('radio', {})
    
    def get_tea5767_config(self) -> Dict[str, Any]:
        """Get TEA5767 FM radio module configuration"""
        radio_config = self.get_radio_config()
        return radio_config.get('tea5767', {})
    
    def get_fan_config(self) -> Dict[str, Any]:
        """Get fan configuration"""
        return self._config.get('fan', {})
    
    def get_grove_mosfet_config(self) -> Dict[str, Any]:
        """Get Grove MOSFET fan controller configuration"""
        fan_config = self.get_fan_config()
        return fan_config.get('grove_mosfet', {})
    
    def is_module_enabled(self, module_name: str) -> bool:
        """Check if a module is enabled"""
        module_config = self._config.get(module_name, {})
        return module_config.get('enabled', False)
    
    def get_tuya_credentials(self) -> tuple:
        """
        Get Tuya device credentials
        
        Returns:
            tuple: (device_id, device_ip, device_key, protocol_version)
        """
        tuya_config = self.get_tuya_config()
        
        device_id = tuya_config.get('device_id')
        device_ip = tuya_config.get('device_ip') 
        device_key = tuya_config.get('device_key')
        protocol_version = tuya_config.get('protocol_version', '3.5')
        
        if not all([device_id, device_ip, device_key]):
            raise DeviceConfigError(
                "Missing Tuya credentials in config file. "
                "Please run 'python3 -m tinytuya wizard' and update config/devices.json"
            )
        
        return device_id, device_ip, device_key, protocol_version

# Global instance for easy access
_device_config = None

def get_device_config() -> DeviceConfig:
    """Get global device configuration instance"""
    global _device_config
    if _device_config is None:
        _device_config = DeviceConfig()
    return _device_config