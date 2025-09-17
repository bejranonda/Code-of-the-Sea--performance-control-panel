#!/usr/bin/env python3
"""
LED Service with Graceful Dependency Handling
Falls back to mock mode when hardware libraries are unavailable
"""

import time
import json
import os
import traceback
import asyncio
from datetime import datetime

# Import dependencies with fallbacks
try:
    import tinytuya
    TINYTUYA_AVAILABLE = True
except ImportError:
    TINYTUYA_AVAILABLE = False
    print("Warning: tinytuya not available - running in mock mode")

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Warning: sounddevice/numpy not available - audio features disabled")

try:
    import board
    import busio
    import adafruit_veml7700
    VEML7700_AVAILABLE = True
except ImportError:
    VEML7700_AVAILABLE = False
    print("Warning: VEML7700 libraries not available - light sensor disabled")

# Configuration Files
CONFIG_FILE = "../unified_config.json"
LOG_FILE = os.path.join(os.path.dirname(__file__), "led_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "led_status.json")

# Mock device for testing
class MockTuyaDevice:
    def __init__(self):
        self.power_state = False
        self.brightness = 50
        
    def set_value(self, dp_id, value):
        if dp_id == 20:  # Power
            self.power_state = value
        elif dp_id == 22:  # Brightness
            self.brightness = value
        time.sleep(0.1)  # Simulate network delay
        
    def status(self):
        return {"dps": {"20": self.power_state, "22": self.brightness}}
    
    def close(self):
        pass
    
    def set_version(self, version):
        pass
        
    def set_socketPersistent(self, persistent):
        pass

# Global status tracking
current_status = {
    "mode": "Manual LED",
    "brightness": 0,
    "power_state": False,
    "last_update": None,
    "error_count": 0,
    "connection_status": "disconnected",
    "mock_mode": not TINYTUYA_AVAILABLE
}

def log_event(message, level="INFO"):
    """Log events to file with timestamp and level"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {level}: {message}\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}")

def log_error(message, exception=None):
    """Log errors with full traceback"""
    if exception:
        tb = traceback.format_exc()
        log_event(f"{message}\nException: {str(exception)}\nTraceback:\n{tb}", "ERROR")
    else:
        log_event(message, "ERROR")

def update_status(**kwargs):
    """Update current status and save to file"""
    global current_status
    current_status.update(kwargs)
    current_status["last_update"] = datetime.now().isoformat()
    
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(current_status, f, indent=2)
    except Exception as e:
        log_error("Failed to update status file", e)

def load_config():
    """Load configuration from unified config file"""
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("LED Service", {"mode": "Manual LED", "brightness": 50})
    except FileNotFoundError:
        log_event("Config file not found, using defaults", "WARNING")
        return {"mode": "Manual LED", "brightness": 50}
    except json.JSONDecodeError as e:
        log_error("Config file JSON decode error", e)
        return {"mode": "Manual LED", "brightness": 50}
    except Exception as e:
        log_error("Unexpected error loading config", e)
        return {"mode": "Manual LED", "brightness": 50}

async def initialize_device():
    """Initialize LED device (real or mock)"""
    global d
    
    if TINYTUYA_AVAILABLE:
        try:
            # Load device configuration from config file
            import sys
            import os
            core_path = os.path.join(os.path.dirname(__file__), '..', 'core')
            core_path = os.path.abspath(core_path)
            if core_path not in sys.path:
                sys.path.insert(0, core_path)
            
            from device_config import DeviceConfig
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'devices.json')
            config_path = os.path.abspath(config_path)
            config = DeviceConfig(config_path)
            led_config = config.get_led_config()
            tuya_config = led_config['tuya_controller']
            
            device_id = tuya_config['device_id']
            device_ip = tuya_config['device_ip']
            device_key = tuya_config['device_key']
            protocol_version = float(tuya_config.get('protocol_version', '3.5'))
            
            log_event(f"Attempting to connect to real Tuya device (Device ID: {device_id})")
            d = tinytuya.BulbDevice(
                dev_id=device_id,
                address=device_ip, 
                local_key=device_key
            )
            d.set_version(protocol_version)
            d.set_socketPersistent(True)
            
            # Test connection
            status_data = await asyncio.wait_for(asyncio.to_thread(d.status), timeout=3.0)
            log_event("Connected to real Tuya device")
            update_status(connection_status="connected", mock_mode=False)
            return True
            
        except Exception as e:
            log_error("Failed to connect to real device, using mock", e)
    
    # Use mock device
    log_event("Using mock LED device")
    d = MockTuyaDevice()
    update_status(connection_status="mock", mock_mode=True)
    return True

async def set_led_brightness(brightness_percent):
    """Set LED brightness (works with real or mock device)"""
    global d
    
    try:
        # Convert percentage to device values
        should_be_on = brightness_percent > 0
        
        if hasattr(d, 'set_value'):
            # Set power state
            await asyncio.to_thread(d.set_value, 20, should_be_on)  # DP_ID_POWER
            
            if should_be_on:
                # Set brightness (10-1000 range for Tuya)
                tuya_brightness = int(10 + (brightness_percent / 100) * 990)
                await asyncio.to_thread(d.set_value, 21, 'white')  # Work mode
                await asyncio.to_thread(d.set_value, 22, tuya_brightness)  # Brightness
        
        log_event(f"Brightness set to {brightness_percent}% (Power: {'ON' if should_be_on else 'OFF'})")
        update_status(brightness=brightness_percent, power_state=should_be_on)
        
    except Exception as e:
        log_error(f"Error setting brightness to {brightness_percent}%", e)
        current_status["error_count"] += 1

async def manual_led_mode():
    """Manual LED mode - fixed brightness from config"""
    log_event("Starting Manual LED mode")
    update_status(mode="Manual LED")
    
    last_brightness = -1
    
    while True:
        try:
            config = load_config()
            if config["mode"] != "Manual LED":
                break
                
            brightness_percent = float(config.get("brightness", 50))
            
            # Update only if brightness changed
            if brightness_percent != last_brightness:
                await set_led_brightness(brightness_percent)
                last_brightness = brightness_percent
                
            print(f"Manual LED - Brightness: {brightness_percent:.1f}% ({'Mock' if current_status.get('mock_mode') else 'Real'})", end='\r')
            await asyncio.sleep(1)
            
        except Exception as e:
            log_error("Error in manual LED mode", e)
            await asyncio.sleep(1)

async def musical_led_mode():
    """Musical LED mode - mock mode if audio unavailable"""
    log_event("Starting Musical LED mode")
    update_status(mode="Musical LED")
    
    if not AUDIO_AVAILABLE:
        log_event("Audio libraries not available - simulating musical mode", "WARNING")
        # Simulate audio reactive behavior
        while True:
            config = load_config()
            if config["mode"] != "Musical LED":
                break
                
            # Simulate varying brightness
            import math
            brightness = abs(math.sin(time.time() * 2)) * 100
            await set_led_brightness(brightness)
            print(f"Musical LED (Simulated) - Brightness: {brightness:.1f}%", end='\r')
            await asyncio.sleep(0.1)
        return
    
    # Real audio processing would go here
    log_event("Real audio processing not implemented yet - using simulation")
    await musical_led_mode()  # Fall back to simulation

async def lighting_led_mode():
    """Lighting LED mode - mock mode if sensor unavailable"""
    log_event("Starting Lighting LED mode")
    update_status(mode="Lighting LED")
    
    if not VEML7700_AVAILABLE:
        log_event("Light sensor not available - simulating lighting mode", "WARNING")
        # Simulate inverse lighting behavior
        while True:
            config = load_config()
            if config["mode"] != "Lighting LED":
                break
                
            # Simulate varying ambient light
            import math
            simulated_lux = 500 + 300 * math.sin(time.time() * 0.5)
            brightness = max(0, min(100, (1500 - simulated_lux) / 1500 * 100))
            await set_led_brightness(brightness)
            print(f"Lighting LED (Simulated) - Lux: {simulated_lux:.1f} -> Brightness: {brightness:.1f}%", end='\r')
            await asyncio.sleep(1)
        return
    
    # Real sensor processing would go here
    log_event("Real sensor processing not implemented yet - using simulation")
    await lighting_led_mode()  # Fall back to simulation

async def main():
    """Main function that switches between modes based on config"""
    global d
    
    log_event("LED Service starting (with dependency fallbacks)")
    update_status(mode="Initializing", connection_status="connecting")
    
    # Initialize device (real or mock)
    if not await initialize_device():
        log_error("Failed to initialize LED device")
        return
    
    try:
        while True:
            try:
                config = load_config()
                mode = config.get("mode", "Manual LED")
                
                print(f"\nSwitching to {mode}")
                log_event(f"Mode changed to: {mode}")
                
                if mode == "Musical LED":
                    await musical_led_mode()
                elif mode == "Lighting LED":
                    await lighting_led_mode()
                elif mode == "Manual LED":
                    await manual_led_mode()
                else:
                    log_error(f"Unknown mode: {mode}")
                    await asyncio.sleep(1)
                    
            except Exception as e:
                log_error("Error in main mode loop", e)
                await asyncio.sleep(2)
                
    except KeyboardInterrupt:
        log_event("Service stopped by user")
    except Exception as e:
        log_error("Unexpected error in main", e)
    finally:
        try:
            if hasattr(d, 'set_value'):
                await asyncio.to_thread(d.set_value, 20, False)  # Turn off
                log_event("LED turned off on exit")
            update_status(power_state=False, connection_status="disconnected")
        except Exception as e:
            log_error("Error turning off LED on exit", e)
        
        if hasattr(d, 'close'):
            try:
                d.close()
            except Exception as e:
                log_error("Error closing device connection", e)
        
        log_event("LED Service stopped")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        log_error("Fatal error in LED service", e)
        print(f"Fatal error: {e}")