### lighting_menu.py

import tinytuya
import time
import sounddevice as sd
import numpy as np
import collections
import asyncio
import json
import os
import sys
import traceback
from datetime import datetime

# Disable colorama and stdout/stderr to prevent broken pipe errors in background service
if not sys.stdout.isatty():
    os.environ['TERM'] = 'dumb'
    os.environ['NO_COLOR'] = '1'
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # Create a safe null writer class
    class NullWriter:
        def write(self, *args): pass
        def flush(self): pass
        def isatty(self): return False
        def close(self): pass
    
    # Replace stdout/stderr with null writers
    sys.stdout = NullWriter()
    sys.stderr = NullWriter()
    
    # Also disable colorama init
    os.environ['COLORAMA_AUTORESET'] = 'False'
    os.environ['COLORAMA_DISABLE'] = '1'
    
    # Monkey patch colorama to prevent initialization
    try:
        import colorama
        colorama.init = lambda *args, **kwargs: None
        colorama.deinit = lambda *args, **kwargs: None
        if hasattr(colorama, 'ansitowin32'):
            colorama.ansitowin32.AnsiToWin32 = lambda *args, **kwargs: NullWriter()
    except ImportError:
        pass

# Try importing sensor libraries with error handling
try:
    import board
    import busio
    import adafruit_veml7700
    VEML7700_AVAILABLE = True
except ImportError as e:
    VEML7700_AVAILABLE = False
    try:
        print(f"Warning: VEML7700 libraries not available: {e}")
    except (BrokenPipeError, OSError):
        pass  # Ignore broken pipe errors in background service

# --- Configuration Files ---
CONFIG_FILE = "../unified_config.json"  # Look in parent directory
LOG_FILE = os.path.join(os.path.dirname(__file__), "led_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "led_status.json")

# --- Tuya Device Configuration ---
DEVICE_ID = "bf549c1fed6b2bbd43l1ow"
DEVICE_IP = "192.168.0.80"
DEVICE_KEY = "[L7c*$TBS:_XxPr6"

# --- Tuya Data Point IDs ---
DP_ID_POWER = 20
DP_ID_WORK_MODE = 21
DP_ID_BRIGHTNESS = 22
DP_ID_COLOR_TEMP = 23

# --- Tuya Controller Value Ranges ---
TUYA_BRIGHTNESS_MIN = 10
TUYA_BRIGHTNESS_MAX = 1000
TUYA_CCT_MIN = 0
TUYA_CCT_MAX = 1000

# --- Fixed Color Temperature ---
FIXED_KELVIN_TEMP = 2900
FIXED_TUYA_CCT_VALUE = int((FIXED_KELVIN_TEMP - 2700) * (TUYA_CCT_MAX - TUYA_CCT_MIN) / (6500 - 2700) + TUYA_CCT_MIN)

# --- Audio Configuration (for Musical LED mode) ---
SAMPLERATE = 44100
CHANNELS = 1
BLOCKSIZE = 2048
MIC_RMS_QUIET = 0.001  # Lowered to match typical ambient levels
MIC_RMS_LOUD = 0.01     # Lowered to be more sensitive to audio
RMS_SMOOTHING_WINDOW = 5
rms_history = collections.deque(maxlen=RMS_SMOOTHING_WINDOW)

# --- Light Sensor Configuration (for Lighting LED mode) ---
SENSOR_LUX_MIN = 20
SENSOR_LUX_MAX = 1500

# --- Command Rate Limiting ---
MIN_COMMAND_INTERVAL_SECONDS = 0.2
COMMAND_TIMEOUT_SECONDS = 0.5
BRIGHTNESS_MINIMUM_CHANGE = 1  # Minimum brightness change required to trigger update
last_command_time = 0
previous_brightness_percent = -1

# --- Global Variables ---
d = None
power_on_state = False
current_status = {
    "mode": "Manual LED",
    "brightness": 0,
    "power_state": False,
    "last_update": None,
    "error_count": 0,
    "connection_status": "disconnected"
}

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
        try:
            print(f"Failed to write to log file: {e}")
        except (BrokenPipeError, OSError):
            pass  # Ignore broken pipe errors in background service

def log_to_main_log(message, level="INFO"):
    """Log to main application log file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    main_log_file = "../unified_app.log"  # Main log is in parent directory
    
    try:
        # Append to main log file (not prepending to avoid conflicts)
        with open(main_log_file, "a") as f:
            f.write(f"[{timestamp}] {level}: {message}\n")
    except Exception as e:
        try:
            print(f"Failed to write to main log: {e}")
        except (BrokenPipeError, OSError):
            pass  # Ignore broken pipe errors in background service

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
    log_to_main_log(f"LED Service - {error_msg}", "ERROR")

def make_serializable(obj):
    """Convert objects to JSON serializable format"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    else:
        return str(obj)

def update_status(**kwargs):
    """Update current status and save to file"""
    global current_status
    current_status.update(kwargs)
    current_status["last_update"] = datetime.now().isoformat()
    
    try:
        serializable_status = make_serializable(current_status)
        with open(STATUS_FILE, "w") as f:
            json.dump(serializable_status, f, indent=2)
    except Exception as e:
        log_error("Failed to update status file", e)

def load_config():
    """Load configuration from JSON file with error handling and retry logic"""
    import time
    
    max_retries = 3
    retry_delay = 0.1  # 100ms
    
    for attempt in range(max_retries):
        try:
            with open(CONFIG_FILE, "r") as f:
                content = f.read().strip()
                if not content:  # File is empty, likely being written
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    raise json.JSONDecodeError("File is empty", "", 0)
                
                config = json.loads(content)
                return config.get("LED Service", {"mode": "Manual LED", "brightness": 50})
                
        except FileNotFoundError:
            log_event("Config file not found, using defaults", "WARNING")
            return {"mode": "Manual LED", "brightness": 50}
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                log_event(f"JSON decode error on attempt {attempt + 1}, retrying...", "WARNING")
                time.sleep(retry_delay)
                continue
            else:
                log_error("Config file JSON decode error after retries", e)
                return {"mode": "Manual LED", "brightness": 50}
        except Exception as e:
            log_error("Unexpected error loading config", e)
            return {"mode": "Manual LED", "brightness": 50}
    
    return {"mode": "Manual LED", "brightness": 50}

def map_range(value, in_min, in_max, out_min, out_max):
    """Maps a value from one numerical range to another."""
    try:
        value = max(in_min, min(in_max, value))
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    except Exception as e:
        log_error(f"Error in map_range with value {value}", e)
        return out_min

def get_brightness_from_rms(rms):
    """Maps RMS to LED brightness for Musical LED mode."""
    try:
        brightness = map_range(rms, MIC_RMS_QUIET, MIC_RMS_LOUD, 1, 100)  # Minimum 1% instead of 0%
        return max(1, min(100, brightness))  # Clamp to valid range
    except Exception as e:
        log_error(f"Error calculating brightness from RMS {rms}", e)
        return 1  # Return 1% instead of 0% on error

def get_brightness_from_lux(lux_value):
    """Maps lux value to LED brightness for Lighting LED mode (inverse)."""
    try:
        brightness_percent = map_range(lux_value, SENSOR_LUX_MIN, SENSOR_LUX_MAX, 100, 0)
        return max(0, min(100, brightness_percent))
    except Exception as e:
        log_error(f"Error calculating brightness from lux {lux_value}", e)
        return 0

async def set_brightness_and_power(brightness_percent, force_update=False, verbose_logging=True):
    """Set LED brightness and power state with comprehensive error handling."""
    global last_command_time, previous_brightness_percent, power_on_state
    
    try:
        current_time = time.monotonic()
        
        # Rate limiting check
        if not force_update and (current_time - last_command_time) < MIN_COMMAND_INTERVAL_SECONDS:
            return
        
        # Check if brightness change is significant
        if not force_update and abs(brightness_percent - previous_brightness_percent) < BRIGHTNESS_MINIMUM_CHANGE:
            return
        
        # Determine power state
        should_be_on = brightness_percent > 0
        
        # Handle power state changes
        if power_on_state != should_be_on:
            try:
                # Use boolean values for tinytuya compatibility
                await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, should_be_on), timeout=COMMAND_TIMEOUT_SECONDS)
                power_on_state = should_be_on
                if verbose_logging:
                    log_event(f"Power {'ON' if should_be_on else 'OFF'}")
                update_status(power_state=should_be_on)
            except asyncio.TimeoutError:
                log_error("Power command timed out")
                current_status["error_count"] += 1
                return
            except Exception as e:
                log_error(f"Error setting power state to {should_be_on}", e)
                current_status["error_count"] += 1
                return
        
        # Set brightness if LED is on
        if should_be_on:
            try:
                tuya_brightness = int(map_range(brightness_percent, 0, 100, TUYA_BRIGHTNESS_MIN, TUYA_BRIGHTNESS_MAX))
                await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_WORK_MODE, 'white'), timeout=COMMAND_TIMEOUT_SECONDS)
                await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_BRIGHTNESS, tuya_brightness), timeout=COMMAND_TIMEOUT_SECONDS)
                
                if verbose_logging:
                    log_event(f"Brightness set to {brightness_percent:.1f}% (Tuya: {tuya_brightness})")
                update_status(brightness=brightness_percent)
                
            except asyncio.TimeoutError:
                log_error("Brightness command timed out")
                current_status["error_count"] += 1
                return
            except Exception as e:
                log_error(f"Error setting brightness to {brightness_percent}%", e)
                current_status["error_count"] += 1
                return
        
        last_command_time = current_time
        previous_brightness_percent = brightness_percent
        
    except Exception as e:
        log_error("Unexpected error in set_brightness_and_power", e)
        current_status["error_count"] += 1

async def musical_led_mode():
    """Musical LED mode - brightness reacts to sound level."""
    log_event("Starting Musical LED mode")
    update_status(mode="Musical LED")
    
    # Turn on LED at start
    await set_brightness_and_power(50, force_update=True)  # Start with 50% brightness
    
    try:
        with sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE) as stream:
            while True:
                # Check if mode changed
                config = load_config()
                if config["mode"] != "Musical LED":
                    break
                
                try:
                    data, overflowed = stream.read(BLOCKSIZE)
                    if overflowed:
                        log_event("Audio buffer overflowed", "WARNING")
                    
                    current_rms = np.sqrt(np.mean(data**2))
                    rms_history.append(current_rms)
                    smoothed_rms = np.mean(rms_history)
                    
                    brightness_percent = get_brightness_from_rms(smoothed_rms)
                    
                    # Log significant brightness changes in Musical LED mode
                    if abs(brightness_percent - previous_brightness_percent) >= 10:  # Log changes >= 10%
                        log_event(f"Musical LED - Brightness: {brightness_percent:.1f}% (RMS: {smoothed_rms:.4f})")
                    
                    await set_brightness_and_power(brightness_percent, verbose_logging=False)
                    
                    try:
                        print(f"Musical LED - RMS: {smoothed_rms:.4f} -> Brightness: {brightness_percent:.1f}%", end='\r')
                    except (BrokenPipeError, OSError):
                        pass  # Ignore broken pipe errors in background service
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    log_error("Error in musical LED processing", e)
                    await asyncio.sleep(0.1)
                    
    except Exception as e:
        log_error("Error starting Musical LED mode", e)

async def lighting_led_mode():
    """Lighting LED mode - brightness reacts to light sensor (inverse)."""
    log_event("Starting Lighting LED mode")
    update_status(mode="Lighting LED")
    
    if not VEML7700_AVAILABLE:
        log_error("VEML7700 libraries not available for Lighting LED mode")
        return
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        veml7700 = adafruit_veml7700.VEML7700(i2c)
        veml7700.integration_time = "100ms"
        veml7700.gain = "1x"
        log_event("VEML7700 sensor initialized successfully")
    except Exception as e:
        log_error("Error initializing VEML7700 sensor", e)
        return
    
    while True:
        # Check if mode changed
        config = load_config()
        if config["mode"] != "Lighting LED":
            break
            
        try:
            lux_value = veml7700.lux
            brightness_percent = get_brightness_from_lux(lux_value)
            await set_brightness_and_power(brightness_percent)
            
            # Log only significant changes
            if abs(brightness_percent - current_status.get("brightness", 0)) > 5:
                log_event(f"Lighting LED - Lux: {lux_value:.2f} -> Brightness: {brightness_percent:.1f}%")
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            log_error("Error reading lux sensor", e)
            await asyncio.sleep(1)

async def manual_led_mode():
    """Manual LED mode - fixed brightness from config."""
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
                await set_brightness_and_power(brightness_percent, force_update=True)
                log_event(f"Manual brightness set to {brightness_percent}%")
                last_brightness = brightness_percent
                
            try:
                print(f"Manual LED - Brightness: {brightness_percent:.1f}%", end='\r')
            except (BrokenPipeError, OSError):
                pass  # Ignore broken pipe errors in background service
            await asyncio.sleep(1)
            
        except Exception as e:
            log_error("Error in manual LED mode", e)
            await asyncio.sleep(1)

async def initialize_tuya_device():
    """Initialize Tuya device with comprehensive error handling"""
    global d, power_on_state
    
    try:
        log_event("Initializing Tuya device connection")
        d = tinytuya.BulbDevice(dev_id=DEVICE_ID, address=DEVICE_IP, local_key=DEVICE_KEY)
        d.set_version(3.5)
        d.set_socketPersistent(True)
        
        # Test connection
        status_data = await asyncio.wait_for(asyncio.to_thread(d.status), timeout=5.0)
        power_on_state = status_data.get('dps', {}).get(str(DP_ID_POWER), False)
        
        log_event(f"Connected to Tuya device - Initial status: {status_data}")
        update_status(connection_status="connected", power_state=power_on_state)
        return True
        
    except asyncio.TimeoutError:
        log_error("Tuya device connection timed out")
        update_status(connection_status="timeout")
        return False
    except Exception as e:
        log_error("Error connecting to Tuya device", e)
        update_status(connection_status="error")
        return False

async def main():
    """Main function that switches between modes based on config."""
    global d, power_on_state
    
    log_event("LED Service starting")
    update_status(mode="Initializing", connection_status="connecting")
    
    # Initialize Tuya device
    if not await initialize_tuya_device():
        log_error("Failed to initialize Tuya device, service cannot start")
        return
    
    try:
        while True:
            try:
                config = load_config()
                mode = config.get("mode", "Manual LED")
                
                try:
                    print(f"\nSwitching to {mode}")
                except (BrokenPipeError, OSError):
                    pass  # Ignore broken pipe errors in background service
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
            if d:
                await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, False), timeout=COMMAND_TIMEOUT_SECONDS)
                log_event("LED turned off on exit")
                update_status(power_state=False, connection_status="disconnected")
        except Exception as e:
            log_error("Error turning off LED on exit", e)
        
        if d:
            try:
                d.close()
            except Exception as e:
                log_error("Error closing Tuya connection", e)
        
        log_event("LED Service stopped")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        log_error("Fatal error in LED service", e)
        try:
            print(f"Fatal error: {e}")
        except (BrokenPipeError, OSError):
            pass  # Ignore broken pipe errors in background service