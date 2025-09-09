### fan_mic_menu.py

import os
import json
import time
import random
import math
import traceback
from datetime import datetime

# Try importing hardware libraries with error handling
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError as e:
    GPIO_AVAILABLE = False
    print(f"Warning: RPi.GPIO library not available: {e}")

try:
    import alsaaudio
    import audioop
    AUDIO_AVAILABLE = True
except ImportError as e:
    AUDIO_AVAILABLE = False
    print(f"Warning: Audio libraries not available: {e}")

# -------------------------------
# Configuration
# -------------------------------
FAN_PIN = 18   # Use GPIO18 (supports hardware PWM)
PWM_FREQUENCY = 25000  # 25 kHz PWM (good for fans)

CONFIG_FILE = "../service_config.json"  # Look in parent directory
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
    "sound_level": 0,
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
    """Read configuration from JSON file with error handling"""
    try:
        if not os.path.exists(CONFIG_FILE):
            log_event("Config file not found, using defaults", "WARNING")
            return {"mode": "Fixed", "speed": 50}
        
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            fan_config = config.get("Fan Service", {"mode": "Fixed", "speed": 50})
            
            # Normalize mode names
            mode_mapping = {
                "fixed": "Fixed",
                "Fixed": "Fixed",
                "cycle": "Cycle",
                "Cycle": "Cycle",
                "random": "Random",
                "Random": "Random",
                "sounding": "Sounding",
                "Sounding": "Sounding"
            }
            fan_config["mode"] = mode_mapping.get(fan_config.get("mode", "Fixed"), "Fixed")
            
            return fan_config
            
    except json.JSONDecodeError as e:
        log_error("Config file JSON decode error", e)
        return {"mode": "Fixed", "speed": 50}
    except Exception as e:
        log_error("Unexpected error reading config", e)
        return {"mode": "Fixed", "speed": 50}

def write_config(cfg):
    """Write configuration to JSON file with error handling"""
    try:
        # Load existing config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                full_config = json.load(f)
        else:
            full_config = {}
        
        # Update fan service config
        full_config["Fan Service"] = cfg
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(full_config, f, indent=2)
            
    except Exception as e:
        log_error("Error writing config", e)

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
# Audio Functions
# -------------------------------
def get_sound_level():
    """Get current sound level with comprehensive error handling"""
    try:
        if not AUDIO_AVAILABLE:
            return 0
            
        inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK)
        inp.setchannels(1)
        inp.setrate(44100)
        inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        inp.setperiodsize(1024)

        l, data = inp.read()
        if l:
            rms = audioop.rms(data, 2)
            level = min(100, int(rms / 100))  # normalize
            update_status(sound_level=level)
            return level
        return 0
        
    except Exception as e:
        log_error("Error reading sound level", e)
        current_status["error_count"] += 1
        return 0

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

def run_cycle(t):
    """Cycle speed mode with error handling"""
    try:
        speed = int((math.sin(t / 5.0) + 1) * 40 + 20)
        update_status(target_speed=speed, mode="Cycle")
        return set_fan_speed(speed)
    except Exception as e:
        log_error("Error in cycle mode", e)
        return False

def run_random():
    """Random speed mode with error handling"""
    try:
        speed = random.randint(20, 100)
        update_status(target_speed=speed, mode="Random")
        success = set_fan_speed(speed)
        if success:
            time.sleep(2)
        return success
    except Exception as e:
        log_error("Error in random mode", e)
        return False

def run_sounding():
    """Sound-reactive mode with error handling"""
    try:
        level = get_sound_level()
        # Map sound level to fan speed (20-100% range)
        speed = max(20, min(100, 20 + level))
        update_status(target_speed=speed, mode="Sounding")
        return set_fan_speed(speed)
    except Exception as e:
        log_error("Error in sounding mode", e)
        return False

# -------------------------------
# Main Loop
# -------------------------------
def main():
    """Main service loop"""
    log_event("Fan service starting")
    update_status(mode="Initializing", connection_status="connecting")
    
    # Initialize hardware
    if not initialize_gpio():
        log_error("Failed to initialize GPIO, service cannot start")
        return
    
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
                elif mode == "Cycle":
                    success = run_cycle(t)
                elif mode == "Random":
                    success = run_random()
                elif mode == "Sounding":
                    success = run_sounding()
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