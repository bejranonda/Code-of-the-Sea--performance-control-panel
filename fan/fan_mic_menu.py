### fan_mic_menu.py

import os
import json
import time
import random
import math
import traceback
import fcntl
from datetime import datetime

# Try importing hardware libraries with error handling
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError as e:
    GPIO_AVAILABLE = False
    print(f"Warning: RPi.GPIO library not available: {e}")



# -------------------------------
# Configuration
# -------------------------------
FAN_PIN = 12   # Use GPIO12 (supports hardware PWM)
PWM_FREQUENCY = 200  # 25 kHz PWM (good for fans)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "service_config.json")  # Absolute path to parent directory
LOG_FILE = os.path.join(os.path.dirname(__file__), "fan_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "fan_status.json")

# -------------------------------
# Global Variables
# -------------------------------
pwm = None
current_status = {
    "mode": "Fixed",
    "speed": 0,
    "target_speed": 0,
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
    log_to_main_log(f"Fan Service - {error_msg}", "ERROR")

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
    """Read configuration from JSON file with file locking and retry logic"""
    max_retries = 3
    retry_delay = 0.1

    for attempt in range(max_retries):
        try:
            if not os.path.exists(CONFIG_FILE):
                log_event("Config file not found, using defaults", "WARNING")
                return {"mode": "Fixed", "speed": 50}

            # Check if file is empty or too small
            file_size = os.path.getsize(CONFIG_FILE)
            if file_size == 0:
                if attempt < max_retries - 1:
                    log_event(f"Config file is empty, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})", "WARNING")
                    time.sleep(retry_delay)
                    continue
                else:
                    log_event("Config file is consistently empty, using defaults", "WARNING")
                    return {"mode": "Fixed", "speed": 50}

            with open(CONFIG_FILE, "r") as f:
                try:
                    # Use file locking to prevent race conditions
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    file_content = f.read().strip()

                    if not file_content:
                        if attempt < max_retries - 1:
                            log_event(f"Config file content is empty, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})", "WARNING")
                            time.sleep(retry_delay)
                            continue
                        else:
                            log_event("Config file content is consistently empty, using defaults", "WARNING")
                            return {"mode": "Fixed", "speed": 50}

                    config = json.loads(file_content)
                    fan_config = config.get("Fan Service", {"mode": "Fixed", "speed": 50})

                    # Normalize mode names
                    mode_mapping = {
                        "fixed": "Fixed",
                        "Fixed": "Fixed",
                        "disable": "Disable",
                        "Disable": "Disable",
                        "disabled": "Disable",
                        "Disabled": "Disable"
                    }
                    fan_config["mode"] = mode_mapping.get(fan_config.get("mode", "Fixed"), "Fixed")

                    return fan_config

                except BlockingIOError:
                    # File is locked by another process, retry
                    if attempt < max_retries - 1:
                        log_event(f"Config file is locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})", "WARNING")
                        time.sleep(retry_delay)
                        continue
                    else:
                        log_event("Config file is consistently locked, using defaults", "WARNING")
                        return {"mode": "Fixed", "speed": 50}

        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                log_event(f"Config file JSON decode error, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries}): {e}", "WARNING")
                time.sleep(retry_delay)
                continue
            else:
                log_error("Config file JSON decode error after all retries", e)
                return {"mode": "Fixed", "speed": 50}
        except Exception as e:
            if attempt < max_retries - 1:
                log_event(f"Unexpected error reading config, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries}): {e}", "WARNING")
                time.sleep(retry_delay)
                continue
            else:
                log_error("Unexpected error reading config after all retries", e)
                return {"mode": "Fixed", "speed": 50}

    # This should never be reached, but just in case
    return {"mode": "Fixed", "speed": 50}

def write_config(cfg):
    """Write configuration to JSON file with file locking and error handling"""
    max_retries = 3
    retry_delay = 0.1

    for attempt in range(max_retries):
        try:
            # Load existing config
            full_config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                        full_config = json.load(f)
                    except BlockingIOError:
                        if attempt < max_retries - 1:
                            log_event(f"Config file is locked for reading, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})", "WARNING")
                            time.sleep(retry_delay)
                            continue
                        else:
                            log_error("Config file is consistently locked for reading, cannot update config")
                            return

            # Update fan service config
            full_config["Fan Service"] = cfg

            # Write config with exclusive lock
            with open(CONFIG_FILE, "w") as f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    json.dump(full_config, f, indent=2)
                    return  # Success
                except BlockingIOError:
                    if attempt < max_retries - 1:
                        log_event(f"Config file is locked for writing, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})", "WARNING")
                        time.sleep(retry_delay)
                        continue
                    else:
                        log_error("Config file is consistently locked for writing, cannot update config")
                        return

        except Exception as e:
            if attempt < max_retries - 1:
                log_event(f"Error writing config, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries}): {e}", "WARNING")
                time.sleep(retry_delay)
                continue
            else:
                log_error("Error writing config after all retries", e)
                return

# -------------------------------
# Hardware Control Functions
# -------------------------------
def initialize_gpio():
    """Initialize GPIO and PWM with error handling"""
    global pwm
    
    if not GPIO_AVAILABLE:
        log_error("RPi.GPIO library not available - cannot initialize fan control")
        return False
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FAN_PIN, GPIO.OUT)
        pwm = GPIO.PWM(FAN_PIN, PWM_FREQUENCY)
        pwm.start(0)
        
        log_event(f"GPIO {FAN_PIN} configured for PWM at {PWM_FREQUENCY} Hz")
        update_status(connection_status="connected")
        return True
        
    except Exception as e:
        log_error("Error initializing GPIO/PWM", e)
        update_status(connection_status="error")
        return False

def set_fan_speed(percent):
    """Set fan speed with error handling and status updates"""
    try:
        if not pwm:
            log_error("PWM not initialized")
            return False
            
        percent = max(0, min(100, percent))
        pwm.ChangeDutyCycle(percent)
        
        # Only log significant speed changes to avoid log spam
        if abs(percent - current_status.get("speed", 0)) > 2:
            log_event(f"Fan speed set to {percent:.1f}%")
        
        update_status(speed=percent)
        return True
        
    except Exception as e:
        log_error(f"Error setting fan speed to {percent}%", e)
        current_status["error_count"] += 1
        return False

def cleanup_gpio():
    """Clean up GPIO with error handling"""
    global pwm
    try:
        if pwm:
            pwm.stop()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        log_event("GPIO cleaned up successfully")
        update_status(connection_status="disconnected", speed=0)
    except Exception as e:
        log_error("Error during GPIO cleanup", e)



# -------------------------------
# Mode Implementations
# -------------------------------
def run_fixed(cfg):
    """Fixed speed mode with error handling"""
    try:
        speed = int(cfg.get("speed", 50))
        update_status(target_speed=speed, mode="Fixed")
        return set_fan_speed(speed)
    except Exception as e:
        log_error("Error in fixed mode", e)
        return False



def run_disable():
    """Disable mode - fan is off and service does nothing"""
    try:
        update_status(target_speed=0, mode="Disable")
        return set_fan_speed(0)
    except Exception as e:
        log_error("Error in disable mode", e)
        return False


# -------------------------------
# Main Loop
# -------------------------------
def main():
    """Main service loop"""
    log_event("Fan service starting")
    update_status(mode="Initializing", connection_status="connecting")
    
    # Initialize hardware
    gpio_available = initialize_gpio()
    if not gpio_available:
        log_error("Failed to initialize GPIO, continuing in monitoring-only mode")
        # Don't exit - continue running in monitoring mode without GPIO control

    
    last_config = {}
    t = 0
    
    try:
        while True:
            try:
                cfg = read_config()

                if cfg != last_config:
                    log_event(f"Configuration changed: {cfg}")
                    last_config = cfg.copy()

                mode = cfg.get("mode", "Fixed")

                success = False
                if mode == "Fixed":
                    success = run_fixed(cfg)
                elif mode == "Disable":
                    success = run_disable()
                else:
                    log_error(f"Unknown mode: {mode}")
                    set_fan_speed(0)

                if not success:
                    log_event(f"Mode {mode} execution failed", "WARNING")

                # Display current status
                print(f"Fan - Mode: {mode}, Speed: {current_status.get('speed', 0):.1f}%, Target: {current_status.get('target_speed', 0)}%", end='\r')

                time.sleep(0.2)
                t += 0.2
                
            except Exception as e:
                log_error("Error in main service loop", e)
                time.sleep(1)

    except KeyboardInterrupt:
        log_event("Fan service stopped by user")
    except Exception as e:
        log_error("Unexpected error in main", e)
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error("Fatal error in fan service", e)
        print(f"Fatal error: {e}")