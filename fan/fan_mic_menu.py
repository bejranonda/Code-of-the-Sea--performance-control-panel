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

# Try importing VEML7700 libraries for light sensor
try:
    import board
    import busio
    import adafruit_veml7700
    VEML7700_AVAILABLE = True
except ImportError as e:
    VEML7700_AVAILABLE = False
    print(f"Warning: VEML7700 libraries not available: {e}")

# -------------------------------
# Configuration
# -------------------------------
FAN_PIN = 18   # Use GPIO18 (supports hardware PWM)
PWM_FREQUENCY = 200  # 25 kHz PWM (good for fans)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "service_config.json")  # Absolute path to parent directory
LOG_FILE = os.path.join(os.path.dirname(__file__), "fan_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "fan_status.json")

# -------------------------------
# Global Variables
# -------------------------------
pwm = None
last_random_time = 0  # Track last random speed change
veml7700_sensor = None  # VEML7700 light sensor instance
current_status = {
    "mode": "Fixed",
    "speed": 0,
    "target_speed": 0,
    "sound_level": 0,
    "lux_level": 0,  # Add lux level tracking
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
                "Sounding": "Sounding",
                "lux": "Lux sensor",
                "Lux": "Lux sensor",
                "lux sensor": "Lux sensor",
                "Lux sensor": "Lux sensor"
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
# VEML7700 Light Sensor Functions
# -------------------------------
def initialize_veml7700():
    """Initialize VEML7700 light sensor with error handling"""
    global veml7700_sensor

    if not VEML7700_AVAILABLE:
        log_error("VEML7700 libraries not available - cannot initialize light sensor")
        return False

    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        veml7700_sensor = adafruit_veml7700.VEML7700(i2c)
        veml7700_sensor.integration_time = "100ms"
        veml7700_sensor.gain = "1x"

        log_event("VEML7700 light sensor initialized successfully")
        return True

    except Exception as e:
        log_error("Error initializing VEML7700 sensor", e)
        return False

def get_lux_level():
    """Get current lux level with comprehensive error handling"""
    try:
        if not veml7700_sensor:
            return 0

        lux_value = veml7700_sensor.lux
        update_status(lux_level=lux_value)
        return lux_value

    except Exception as e:
        log_error("Error reading lux level", e)
        current_status["error_count"] += 1
        return 0

def lux_to_fan_speed(lux_value, config=None):
    """Convert lux value to fan speed - more light = lower speed, less light = higher speed"""
    try:
        # Get configurable min/max lux values with sensible defaults
        # Default: 1 lux = 100% fan speed, 1000 lux = 0% fan speed
        if config:
            lux_min = float(config.get("lux_min", 1))    # Min lux for 100% speed
            lux_max = float(config.get("lux_max", 1000)) # Max lux for 0% speed
        else:
            lux_min = 1
            lux_max = 1000

        # Ensure valid range
        if lux_min >= lux_max:
            log_error(f"Invalid lux range: min={lux_min}, max={lux_max}. Using defaults.")
            lux_min = 1
            lux_max = 1000

        # Linear interpolation: lux_min = 100% speed, lux_max = 0% speed
        if lux_value <= lux_min:
            return 100  # Very dark - maximum fan speed
        elif lux_value >= lux_max:
            return 0    # Very bright - minimum fan speed
        else:
            # Linear interpolation between min and max
            ratio = (lux_value - lux_min) / (lux_max - lux_min)
            speed = 100 - (ratio * 100)  # Inverse relationship
            return max(0, min(100, speed))

    except Exception as e:
        log_error("Error converting lux to fan speed", e)
        return 50  # Default fallback speed

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
    """Cycle speed mode with error handling - sine wave over 2 minutes (0-100%)"""
    try:
        # 2 minutes = 120 seconds cycle
        cycle_period = 120.0
        # Sine wave from 0 to 100% over 2 minutes
        speed = int((math.sin(2 * math.pi * t / cycle_period) + 1) * 50)
        update_status(target_speed=speed, mode="Cycle")
        return set_fan_speed(speed)
    except Exception as e:
        log_error("Error in cycle mode", e)
        return False

def run_random():
    """Random speed mode with error handling - new random speed every 20 seconds"""
    try:
        speed = random.randint(0, 100)  # Full range 0-100%
        update_status(target_speed=speed, mode="Random")
        log_event(f"Random mode: new speed {speed}% (20s interval)")
        return set_fan_speed(speed)
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

def run_lux():
    """Light-reactive mode with error handling - more light = lower speed, less light = higher speed"""
    try:
        # Get configuration for customizable lux ranges
        config = read_config()
        lux_level = get_lux_level()
        speed = int(lux_to_fan_speed(lux_level, config))
        update_status(target_speed=speed, mode="Lux sensor")

        # Log only significant changes to avoid log spam
        if abs(speed - current_status.get("speed", 0)) > 5:
            log_event(f"Lux sensor mode: {lux_level:.2f} lux -> {speed}% fan speed")

        return set_fan_speed(speed)
    except Exception as e:
        log_error("Error in lux sensor mode", e)
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

    # Initialize VEML7700 sensor for Lux mode (optional)
    veml7700_initialized = initialize_veml7700()
    if veml7700_initialized:
        log_event("VEML7700 sensor available for Lux mode")
    else:
        log_event("VEML7700 sensor not available - Lux mode will not work", "WARNING")
    
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
                    # Only change speed every 20 seconds
                    global last_random_time
                    if t - last_random_time >= 20.0:
                        success = run_random()
                        last_random_time = t
                    else:
                        # Maintain current speed
                        success = True
                elif mode == "Sounding":
                    success = run_sounding()
                elif mode in ["Lux", "Lux sensor"]:  # Support both names during transition
                    if veml7700_initialized:
                        success = run_lux()
                    else:
                        log_error("Lux sensor mode requested but VEML7700 sensor not available")
                        set_fan_speed(0)
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