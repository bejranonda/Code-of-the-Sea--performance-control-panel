#!/usr/bin/env python3
# fm-radio_menu.py

import time
import json
import os
import traceback
from datetime import datetime
from random import uniform

# Try importing hardware libraries with error handling
try:
    import smbus
    SMBUS_AVAILABLE = True
except ImportError as e:
    SMBUS_AVAILABLE = False
    print(f"Warning: smbus library not available: {e}")

# -------------------------------
# Configuration
# -------------------------------
I2C_BUS = 1
TEA5767_ADDR = 0x60

CONFIG_FILE = "../service_config.json"  # Look in parent directory  
LOG_FILE = os.path.join(os.path.dirname(__file__), "radio_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "radio_status.json")

# -------------------------------
# Global Variables
# -------------------------------
bus = None
current_status = {
    "mode": "Fixed",
    "frequency": 99.5,
    "signal_level": 0,
    "last_update": None,
    "error_count": 0,
    "connection_status": "disconnected"
}

# -------------------------------
# Logging Functions
# -------------------------------
def log_event(message, level="INFO"):
    """Log events to file with timestamp and level (newest on top)"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_log_entry = f"[{timestamp}] {level}: {message}\n"
    
    try:
        # Read existing log content
        existing_content = ""
        try:
            with open(LOG_FILE, "r") as f:
                existing_content = f.read()
        except FileNotFoundError:
            existing_content = ""
        
        # Write new entry at the top
        with open(LOG_FILE, "w") as f:
            f.write(new_log_entry + existing_content)
    except Exception as e:
        print(f"Failed to write to log file: {e}")

def log_to_main_log(message, level="INFO"):
    """Log to main application log file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    main_log_file = "../unified_app.log"  # Main log is in parent directory
    
    try:
        # Append to main log file (not prepending to avoid conflicts)
        with open(main_log_file, "a") as f:
            f.write(f"[{timestamp}] {level}: {message}\n")
    except Exception as e:
        print(f"Failed to write to main log: {e}")

def log_error(message, exception=None):
    """Log errors with full traceback"""
    error_msg = ""
    if exception:
        tb = traceback.format_exc()
        error_msg = f"{message}\nException: {str(exception)}\nTraceback:\n{tb}"
        log_event(error_msg, "ERROR")
    else:
        error_msg = message
        log_event(error_msg, "ERROR")
    
    # Also log to main application log
    log_to_main_log(f"Radio Service - {error_msg}", "ERROR")

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

def read_config():
    """Read configuration from JSON file with error handling"""
    try:
        if not os.path.exists(CONFIG_FILE):
            log_event("Config file not found, using defaults", "WARNING")
            return {"mode": "Fixed", "frequency": 99.5, "direction": "Up"}
        
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            radio_config = config.get("Radio Service", {"mode": "Fixed", "frequency": 99.5, "direction": "Up"})
            
            # Normalize mode names to match web interface
            mode_mapping = {
                "fixed": "Fixed",
                "Fixed": "Fixed",
                "search": "Search", 
                "Search": "Search"
            }
            radio_config["mode"] = mode_mapping.get(radio_config.get("mode", "Fixed"), "Fixed")
            
            return radio_config
            
    except json.JSONDecodeError as e:
        log_error("Config file JSON decode error", e)
        return {"mode": "Fixed", "frequency": 99.5, "direction": "Up"}
    except Exception as e:
        log_error("Unexpected error reading config", e)
        return {"mode": "Fixed", "frequency": 99.5, "direction": "Up"}

def write_config(cfg):
    """Write configuration to JSON file with error handling"""
    try:
        # Load existing config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                full_config = json.load(f)
        else:
            full_config = {}
        
        # Update radio service config
        full_config["Radio Service"] = cfg
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(full_config, f, indent=2)
            
    except Exception as e:
        log_error("Error writing config", e)

# -------------------------------
# Hardware Initialization
# -------------------------------
def initialize_radio():
    """Initialize I2C bus and TEA5767 with error handling"""
    global bus
    
    if not SMBUS_AVAILABLE:
        log_error("smbus library not available - cannot initialize radio")
        return False
    
    try:
        bus = smbus.SMBus(I2C_BUS)
        log_event("I2C bus initialized")
        
        # Test communication with a simple read
        test_data = bus.read_i2c_block_data(TEA5767_ADDR, 0, 5)
        log_event(f"TEA5767 communication test successful: {[hex(b) for b in test_data]}")
        update_status(connection_status="connected")
        return True
        
    except Exception as e:
        log_error("Error initializing TEA5767 radio module", e)
        update_status(connection_status="error")
        return False

# -------------------------------
# TEA5767 Control Functions
# -------------------------------
def set_frequency(freq_mhz):
    """Set the TEA5767 frequency in MHz with error handling"""
    try:
        if not bus:
            log_error("I2C bus not initialized")
            return False
            
        pll = int((4 * (freq_mhz * 1000000 + 225000)) / 32768)
        data = [
            (pll >> 8) & 0x3F,  # high byte
            pll & 0xFF,         # low byte
            0xB0,               # high cut, stereo, soft mute
            0x10,               # xtal, soft mute, etc.
            0x00                # PLL ref off
        ]
        
        # Retry mechanism for I2C communication
        for attempt in range(3):
            try:
                bus.write_i2c_block_data(TEA5767_ADDR, data[0], data[1:])
                log_event(f"Set frequency: {freq_mhz:.2f} MHz")
                update_status(frequency=freq_mhz)
                return True
            except OSError as e:
                if attempt == 2:  # Last attempt
                    log_error(f"I2C error setting frequency {freq_mhz:.2f} MHz after 3 attempts", e)
                    current_status["error_count"] += 1
                else:
                    log_event(f"I2C error on attempt {attempt+1}, retrying", "WARNING")
                time.sleep(0.1)
        return False
        
    except Exception as e:
        log_error(f"Unexpected error setting frequency {freq_mhz:.2f} MHz", e)
        return False

def read_signal_level():
    """Read signal level from TEA5767 with error handling"""
    try:
        if not bus:
            return 0
            
        data = bus.read_i2c_block_data(TEA5767_ADDR, 0, 5)
        signal = (data[3] >> 4) & 0x0F
        update_status(signal_level=signal)
        return signal
        
    except Exception as e:
        log_error("Error reading signal level", e)
        current_status["error_count"] += 1
        return 0

def search_station(start_freq, direction="Up", step=0.1):
    """Search next available station with comprehensive error handling"""
    try:
        log_event(f"Starting station search from {start_freq:.2f} MHz, direction: {direction}")
        
        freq = start_freq
        max_attempts = int((108 - 87) / step) + 10  # Prevent infinite loops
        attempts = 0
        
        if direction.lower() == "up":
            while freq <= 108 and attempts < max_attempts:
                attempts += 1
                if not set_frequency(freq):
                    freq += step
                    continue
                    
                time.sleep(0.5)
                level = read_signal_level()
                
                if level > 8:  # threshold for "good" station
                    log_event(f"Found station {freq:.2f} MHz (signal {level})")
                    return freq
                freq += step
        else:
            while freq >= 87 and attempts < max_attempts:
                attempts += 1
                if not set_frequency(freq):
                    freq -= step
                    continue
                    
                time.sleep(0.5)
                level = read_signal_level()
                
                if level > 8:
                    log_event(f"Found station {freq:.2f} MHz (signal {level})")
                    return freq
                freq -= step
        
        log_event("No station found in search", "WARNING")
        return start_freq  # fallback
        
    except Exception as e:
        log_error("Error during station search", e)
        return start_freq

# -------------------------------
# Main Loop
# -------------------------------
def main():
    """Main service loop with comprehensive error handling"""
    log_event("Radio service starting")
    update_status(mode="Initializing", connection_status="connecting")
    
    # Initialize hardware
    if not initialize_radio():
        log_error("Failed to initialize radio hardware, service cannot start")
        return
    
    last_config = {}
    
    try:
        while True:
            try:
                cfg = read_config()

                if cfg != last_config:
                    mode = cfg.get("mode", "Fixed")
                    log_event(f"Configuration changed: {cfg}")

                    if mode == "Fixed":
                        freq = float(cfg.get("frequency", 99.5))
                        if set_frequency(freq):
                            log_event(f"Mode: Fixed at {freq:.2f} MHz")
                            update_status(mode="Fixed")
                        else:
                            log_error(f"Failed to set fixed frequency {freq:.2f} MHz")

                    elif mode == "Search":
                        start = float(cfg.get("frequency", 99.5))
                        direction = cfg.get("direction", "Up")
                        
                        try:
                            new_freq = search_station(start, direction=direction)
                            cfg["frequency"] = new_freq
                            write_config(cfg)  # save found station
                            log_event(f"Mode: Search, tuned to {new_freq:.2f} MHz")
                            update_status(mode="Search")
                        except Exception as e:
                            log_error("Error during station search", e)

                    last_config = cfg.copy()

                # Update signal level periodically
                try:
                    signal = read_signal_level()
                    if signal != current_status.get("signal_level", 0):
                        print(f"Radio - Freq: {current_status.get('frequency', 0):.2f} MHz, Signal: {signal}/15", end='\r')
                except Exception as e:
                    log_error("Error updating signal level", e)

                time.sleep(1)
                
            except Exception as e:
                log_error("Error in main service loop", e)
                time.sleep(2)

    except KeyboardInterrupt:
        log_event("Radio service stopped by user")
    except Exception as e:
        log_error("Unexpected error in main", e)
    finally:
        try:
            if bus:
                # Mute radio before closing
                set_frequency(87.5, mute=True)
                bus.close()
                log_event("I2C bus closed")
        except Exception as e:
            log_error("Error during cleanup", e)
        
        update_status(connection_status="disconnected")
        log_event("Radio service stopped")

def set_frequency_with_mute(freq_mhz, mute=False):
    """Enhanced frequency setting with mute capability"""
    try:
        if not bus:
            log_error("I2C bus not initialized")
            return False
            
        pll = int((4 * (freq_mhz * 1000000 + 225000)) / 32768)
        
        # Byte 1: MSB of PLL word + MUTE bit
        byte1 = (pll >> 8) & 0x3F
        if mute:
            byte1 |= 0x80  # Set MUTE bit
        
        data = [
            pll & 0xFF,         # low byte
            0xB0,               # high cut, stereo, soft mute
            0x10,               # xtal, soft mute, etc.
            0x00                # PLL ref off
        ]
        
        # Retry mechanism
        for attempt in range(3):
            try:
                bus.write_i2c_block_data(TEA5767_ADDR, byte1, data)
                if not mute:
                    log_event(f"Set frequency: {freq_mhz:.2f} MHz")
                    update_status(frequency=freq_mhz)
                else:
                    log_event(f"Muted at frequency: {freq_mhz:.2f} MHz")
                return True
            except OSError as e:
                if attempt == 2:
                    log_error(f"I2C error setting frequency {freq_mhz:.2f} MHz after 3 attempts", e)
                    current_status["error_count"] += 1
                else:
                    log_event(f"I2C error on attempt {attempt+1}, retrying", "WARNING")
                time.sleep(0.1)
        return False
        
    except Exception as e:
        log_error(f"Unexpected error setting frequency {freq_mhz:.2f} MHz", e)
        return False

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error("Fatal error in radio service", e)
        print(f"Fatal error: {e}")