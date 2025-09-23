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

# Add core modules to path for device configuration
core_path = os.path.join(os.path.dirname(__file__), '..', 'core')
core_path = os.path.abspath(core_path)
if core_path not in sys.path:
    sys.path.insert(0, core_path)

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
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "unified_config.json")  # Absolute path to parent directory
LOG_FILE = os.path.join(os.path.dirname(__file__), "led_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "led_status.json")

# --- Tuya Device Configuration ---
# Load device configuration from config file
try:
    from device_config import DeviceConfig
    # Use absolute path to config file since LED service runs from led/ directory
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'devices.json')
    config_path = os.path.abspath(config_path)
    config = DeviceConfig(config_path)
    led_config = config.get_led_config()
    tuya_config = led_config['tuya_controller']
    
    DEVICE_ID = tuya_config['device_id']
    DEVICE_IP = tuya_config['device_ip'] 
    DEVICE_KEY = tuya_config['device_key']
    PROTOCOL_VERSION = float(tuya_config.get('protocol_version', '3.5'))
    
    print(f"✅ LED service loaded device config: {DEVICE_ID}")
except Exception as e:
    print(f"❌ Failed to load device config: {e}")
    print("❌ LED service cannot start without valid device configuration")
    sys.exit(1)

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
SAMPLERATE = 44100 # 44100 default
CHANNELS = 1
BLOCKSIZE = 4096

def cleanup_audio_processes():
    """Clean up audio processes that might interfere with Musical mode."""
    import subprocess
    import time

    log_event("Cleaning up audio processes before Musical mode startup...")

    try:
        # Kill any existing audio processes that might be using the microphone
        audio_processes = ['arecord', 'parecord', 'pulseaudio', 'alsa_in', 'alsa_out']

        for process in audio_processes:
            try:
                result = subprocess.run(['pkill', '-f', process], capture_output=True, timeout=3)
                if result.returncode == 0:
                    log_event(f"Stopped {process} processes")
                else:
                    log_event(f"No {process} processes found to stop")
            except Exception as e:
                log_event(f"Error stopping {process}: {e}")

        # Stop and restart PulseAudio to clear any audio device locks
        try:
            log_event("Restarting PulseAudio to clear device locks...")
            subprocess.run(['pulseaudio', '--kill'], capture_output=True, timeout=5)
            time.sleep(1)  # Wait for cleanup
            subprocess.run(['pulseaudio', '--start'], capture_output=True, timeout=5)
            time.sleep(2)  # Wait for initialization

            # Also try systemctl restart as a more thorough restart
            subprocess.run(['systemctl', '--user', 'restart', 'pulseaudio'], capture_output=True, timeout=10)
            time.sleep(1)  # Wait for systemctl restart
            log_event("PulseAudio restarted successfully via both methods")
        except Exception as e:
            log_event(f"PulseAudio restart failed: {e}")

        # Clear any ALSA device locks and reset USB audio device
        try:
            # Reset ALSA state
            subprocess.run(['sudo', 'fuser', '-k', '/dev/snd/*'], capture_output=True, timeout=3)
            log_event("Cleared ALSA device locks")

            # Try to reset the USB audio device
            subprocess.run(['sudo', 'alsamixer', '--card=1', '--exit'], capture_output=True, timeout=3)
            log_event("Reset USB audio device")
        except Exception as e:
            log_event(f"ALSA cleanup warning: {e}")


    except Exception as e:
        log_event(f"Audio cleanup error: {e}")

def detect_audio_input_device():
    """Auto-detect the best available audio input device."""
    import sounddevice as sd
    import subprocess

    log_event("Detecting available audio input devices...")

    # First, ensure PulseAudio can see the USB microphone
    try:
        result = subprocess.run(['pactl', 'list', 'short', 'sources'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'USB_Audio_Device' in line and 'input' in line:
                    source_name = line.split('\t')[1]
                    log_event(f"Found USB Audio input source: {source_name}")
                    # Set as default input source
                    try:
                        subprocess.run(['pactl', 'set-default-source', source_name], capture_output=True, timeout=3)
                        log_event(f"Set USB Audio as default input source: {source_name}")
                    except Exception as e:
                        log_event(f"Failed to set default source: {e}")
                    break
    except Exception as e:
        log_event(f"Failed to configure PulseAudio sources: {e}")

    # Method 1: Check for USB Audio devices via ALSA
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'USB Audio' in line and 'device' in line:
                    # Extract card number from line like "card 1: Device [USB Audio Device], device 0:"
                    parts = line.split(':')
                    if len(parts) >= 2:
                        card_part = parts[0].strip()
                        if 'card' in card_part:
                            card_num = card_part.split('card')[1].strip().split()[0]
                            device_spec = f"plughw:{card_num},0"
                            log_event(f"Found USB Audio device: {device_spec}")

                            # Test if the device actually works
                            try:
                                with sd.InputStream(device=device_spec, samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE):
                                    log_event(f"USB Audio device {device_spec} is working")
                                    return device_spec
                            except Exception as e:
                                log_event(f"USB Audio device {device_spec} test failed: {e}")
    except Exception as e:
        log_event(f"Failed to check ALSA devices: {e}")

    # Method 2: Check sounddevice for devices with input channels
    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                device_name = device['name']
                log_event(f"Found input device {i}: {device_name} ({device['max_input_channels']} channels)")

                # Prefer USB Audio devices
                if 'USB Audio' in device_name or 'USB' in device_name:
                    try:
                        with sd.InputStream(device=i, samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE):
                            log_event(f"USB device {i} ({device_name}) is working")
                            return i
                    except Exception as e:
                        log_event(f"USB device {i} test failed: {e}")

                # Try pulse device if available
                elif 'pulse' in device_name.lower():
                    try:
                        with sd.InputStream(device=i, samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE):
                            log_event(f"PulseAudio device {i} ({device_name}) is working")
                            return i
                    except Exception as e:
                        log_event(f"PulseAudio device {i} test failed: {e}")

                # Try default device if available
                elif 'default' in device_name.lower():
                    try:
                        with sd.InputStream(device=i, samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE):
                            log_event(f"Default device {i} ({device_name}) is working")
                            return i
                    except Exception as e:
                        log_event(f"Default device {i} test failed: {e}")
    except Exception as e:
        log_event(f"Failed to query sounddevice: {e}")

    # Method 3: Try common device specifications
    common_devices = ['pulse', 'default', 'plughw:1,0', 'plughw:0,0']
    for device in common_devices:
        try:
            with sd.InputStream(device=device, samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE):
                log_event(f"Fallback device '{device}' is working")
                return device
        except Exception as e:
            log_event(f"Fallback device '{device}' failed: {e}")

    log_event("No working audio input device found", "WARNING")
    return None
# Default RMS thresholds - will be overridden by config if available
MIC_RMS_QUIET = 0.002   # RMS value considered "quiet" / "emotional" music
MIC_RMS_LOUD = 0.04     # RMS value considered "loud" / "crazy" music

# Load RMS configuration from unified config if available
try:
    unified_config_path = os.path.join(os.path.dirname(__file__), '..', 'unified_config.json')
    if os.path.exists(unified_config_path):
        with open(unified_config_path, 'r') as f:
            unified_config = json.load(f)
            led_config = unified_config.get('LED Service', {})
            MIC_RMS_QUIET = float(led_config.get('mic_rms_quiet', MIC_RMS_QUIET))
            MIC_RMS_LOUD = float(led_config.get('mic_rms_loud', MIC_RMS_LOUD))
            log_event(f"Loaded RMS config: QUIET={MIC_RMS_QUIET:.4f}, LOUD={MIC_RMS_LOUD:.3f}")
except Exception as e:
    try:
        log_event(f"Using default RMS values: QUIET={MIC_RMS_QUIET:.4f}, LOUD={MIC_RMS_LOUD:.3f}")
    except:
        pass
RMS_SMOOTHING_WINDOW = 2
rms_history = collections.deque(maxlen=RMS_SMOOTHING_WINDOW)

# --- Light Sensor Configuration (for Lighting LED mode) ---
SENSOR_LUX_MIN = 20
SENSOR_LUX_MAX = 1500

# --- Command Rate Limiting ---
MIN_COMMAND_INTERVAL_SECONDS = 0.5
COMMAND_TIMEOUT_SECONDS = 0.3
BRIGHTNESS_MINIMUM_CHANGE = 18  # Minimum brightness change required to trigger update
last_command_time = 0
previous_brightness_percent = -1

# --- Hardware-Controlled Smooth Transitions ---
current_brightness = 0.0            # Current brightness for display tracking

# --- RMS Statistics Tracking ---
current_rms = 0.0
max_rms_minute = 0.0
min_rms_minute = 999.0
rms_minute_start = time.time()

# --- Global Variables ---
d = None
power_on_state = False
lux_history = []
last_recorded_lux = None
LUX_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "lux_history.json")
LUX_CHANGE_THRESHOLD = 50  # Only record when lux changes by 50 or more
MAX_HISTORY_ENTRIES = 5000  # Maximum number of history entries to keep
MAX_FILE_SIZE_MB = 1  # Maximum file size in MB before trimming

current_status = {
    "mode": "Manual LED",
    "brightness": 0,
    "power_state": False,
    "lux_level": 0,  # Add lux level tracking
    "current_rms": 0.0,  # Add RMS tracking
    "max_rms_minute": 0.0,
    "min_rms_minute": 0.0,
    "last_update": None,
    "error_count": 0,
    "connection_status": "disconnected",
    "tuya_available": False
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

def check_and_trim_history():
    """Check file size and trim history if needed"""
    global lux_history

    try:
        # Check if file exists and get its size
        if os.path.exists(LUX_HISTORY_FILE):
            file_size_mb = os.path.getsize(LUX_HISTORY_FILE) / (1024 * 1024)

            # If file is too large or we have too many entries, trim it
            if file_size_mb > MAX_FILE_SIZE_MB or len(lux_history) > MAX_HISTORY_ENTRIES:
                # Keep only the most recent entries (half of max to avoid frequent trimming)
                entries_to_keep = MAX_HISTORY_ENTRIES // 2
                lux_history = lux_history[-entries_to_keep:]

                # Save trimmed history
                try:
                    with open(LUX_HISTORY_FILE, "w") as f:
                        json.dump(lux_history, f, indent=2)
                    log_event(f"Lux history trimmed to {len(lux_history)} entries (was {file_size_mb:.2f}MB)")
                except Exception as e:
                    log_error("Failed to save trimmed lux history", e)

    except Exception as e:
        log_error("Error in check_and_trim_history", e)

def save_lux_history(lux_value):
    """Save lux value to history if it changed significantly"""
    global last_recorded_lux, lux_history

    try:
        # Check if we should record this lux value
        should_record = False
        if last_recorded_lux is None:
            should_record = True  # First reading
        elif abs(lux_value - last_recorded_lux) >= LUX_CHANGE_THRESHOLD:
            should_record = True  # Significant change

        if should_record:
            timestamp = datetime.now().isoformat()
            lux_entry = {
                "timestamp": timestamp,
                "lux": round(lux_value, 2),
                "change": round(lux_value - last_recorded_lux, 2) if last_recorded_lux is not None else 0
            }

            # Add to memory
            lux_history.append(lux_entry)

            # Check and trim if needed (do this before limiting in memory to be safe)
            check_and_trim_history()

            # Also limit in memory as backup
            if len(lux_history) > MAX_HISTORY_ENTRIES:
                lux_history = lux_history[-MAX_HISTORY_ENTRIES:]

            # Save to file
            try:
                with open(LUX_HISTORY_FILE, "w") as f:
                    json.dump(lux_history, f, indent=2)
                log_event(f"Lux history recorded: {lux_value:.2f} (change: {lux_entry['change']:.2f})")
            except Exception as e:
                log_error("Failed to save lux history file", e)

            last_recorded_lux = lux_value

    except Exception as e:
        log_error("Error in save_lux_history", e)

def load_lux_history():
    """Load lux history from file"""
    global lux_history, last_recorded_lux

    try:
        with open(LUX_HISTORY_FILE, "r") as f:
            lux_history = json.load(f)
            if lux_history:
                last_recorded_lux = lux_history[-1]["lux"]
                log_event(f"Loaded {len(lux_history)} lux history entries")

                # Check and trim on startup if needed
                check_and_trim_history()
    except FileNotFoundError:
        lux_history = []
        last_recorded_lux = None
        log_event("No lux history file found, starting fresh")
    except Exception as e:
        log_error("Error loading lux history", e)
        lux_history = []
        last_recorded_lux = None

async def read_lux_sensor():
    """Read the latest lux value from sensor/history"""
    global lux_history
    try:
        # Try to get the latest lux value from the history
        if lux_history and len(lux_history) > 0:
            return lux_history[-1].get('lux', 0.0)

        # If no history in memory, try to load from file
        if os.path.exists(LUX_HISTORY_FILE):
            with open(LUX_HISTORY_FILE, "r") as f:
                file_lux_history = json.load(f)
                if file_lux_history and len(file_lux_history) > 0:
                    return file_lux_history[-1].get('lux', 0.0)

        # Default fallback value
        log_event("No lux data available, returning default value 0.0")
        return 0.0

    except Exception as e:
        log_error("Error reading lux sensor", e)
        return 0.0

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
        brightness = map_range(rms, MIC_RMS_QUIET, MIC_RMS_LOUD, 0, 100)  # Map to 0-100% like lighting.py
        return max(1, min(100, brightness))  # Clamp to valid range
    except Exception as e:
        log_error(f"Error calculating brightness from RMS {rms}", e)
        return 1  # Return 1% instead of 0% on error

def get_brightness_from_lux(lux_value, config=None):
    """Maps lux value to LED brightness for Lux sensor mode (inverse)."""
    try:
        # Get configurable min/max lux values, with fallback to defaults
        if config:
            lux_min = float(config.get("lux_min", SENSOR_LUX_MIN))
            lux_max = float(config.get("lux_max", SENSOR_LUX_MAX))
        else:
            lux_min = SENSOR_LUX_MIN
            lux_max = SENSOR_LUX_MAX

        # Inverse mapping: low lux = high brightness, high lux = low brightness
        brightness_percent = map_range(lux_value, lux_min, lux_max, 100, 0)

        # Update status with current lux level and save history
        update_status(lux_level=lux_value)
        save_lux_history(lux_value)

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

                # Log command being sent
                if verbose_logging:
                    log_event(f"LED Command: DP {DP_ID_WORK_MODE}='white', DP {DP_ID_BRIGHTNESS}={tuya_brightness} (Target: {brightness_percent:.1f}%)")

                await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_WORK_MODE, 'white'), timeout=COMMAND_TIMEOUT_SECONDS)
                await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_BRIGHTNESS, tuya_brightness), timeout=COMMAND_TIMEOUT_SECONDS)

                if verbose_logging:
                    log_event(f"LED Command completed: Brightness {brightness_percent:.1f}% (Tuya: {tuya_brightness})")
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

def check_mixing_service_active():
    """Check if mixing service is currently recording and needs audio device"""
    try:
        # Check mixing service status file
        mixing_status_file = os.path.join(os.path.dirname(__file__), "..", "mixing", "mixing_status.json")
        if os.path.exists(mixing_status_file):
            with open(mixing_status_file, 'r') as f:
                mixing_status = json.load(f)
                # If mixing service is recording, yield audio device
                if mixing_status.get("recording", False) or mixing_status.get("status") == "recording":
                    return True
        return False
    except Exception:
        return False

async def musical_led_mode():
    """Musical LED mode - brightness reacts to sound level with mixing service coordination."""
    log_event("Starting Musical LED mode with mixing service coordination")
    update_status(mode="Musical LED")

    # Clean up any audio processes that might interfere
    # cleanup_audio_processes()  # Temporarily disabled to test direct approach

    # Turn on LED at start
    await set_brightness_and_power(50, force_update=True)  # Start with 50% brightness

    # Try to use audio input with same approach as working lighting.py
    audio_available = False
    try:
        # Test default audio device first (device=6 pulse or None for default)
        with sd.InputStream(device=None, samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE) as test_stream:
            audio_available = True
            log_event("Default audio input device available for Musical LED mode")
    except Exception as e:
        log_error("Audio device unavailable for Musical LED mode, falling back to lux monitoring", e)
        # Fall back to lux-based lighting instead of crashing
        await lighting_led_mode()
        return

    try:
        # Initialize audio stream using default device (None)
        log_event(f"Initializing audio stream - Samplerate: {SAMPLERATE}, Channels: {CHANNELS}, Blocksize: {BLOCKSIZE}")
        stream = sd.InputStream(device=None, samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE)
        log_event("Using default audio device for audio stream")
        stream.start()
        log_event(f"Audio stream started successfully - Device: {stream.device}, Active: {stream.active}")
        fallback_mode = False
        
        ### Check conflict with mixing service
        if check_mixing_service_active():
            if stream is not None:
                log_event("Mixing service recording detected - temporarily releasing audio device")
                try:
                    stream.stop()
                    stream.close()
                    stream = None
                    fallback_mode = True
                    log_event("Audio device successfully released for mixing service")
                except Exception as e:
                    log_error("Error releasing audio device for mixing service", e)

            # Use lux-based lighting while mixing service is recording
            if fallback_mode:
                try:
                    lux = await read_lux_sensor()
                    brightness_percent = get_brightness_from_lux(lux)
                    await set_brightness_and_power(brightness_percent)

                    if current_time % 10 < 1:  # Log every ~10 seconds
                        log_event(f"Musical LED (fallback) - Lux: {lux:.1f}, Brightness: {brightness_percent:.1f}%")

                except Exception as e:
                    log_error("Error in Musical LED fallback mode", e)

                await asyncio.sleep(1)

        else:
            # Mixing service not recording, return to audio mode if needed
            if fallback_mode and stream is None:
                try:
                    log_event("Mixing service recording finished - resuming audio input")
                    stream = sd.InputStream(device=1, samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE)
                    stream.start()
                    fallback_mode = False
                    log_event(f"Audio input resumed successfully - Device: {stream.device}, Active: {stream.active}")
                except Exception as e:
                    log_error("Failed to resume audio input, staying in fallback mode", e)
                    fallback_mode = True


        while True:
            # Check if mode changed
            config = load_config()
            if config["mode"] != "Musical LED":
                break

            current_time = time.time()


            # If we're in fallback mode, continue with lux-based lighting
            if fallback_mode or stream is None:
                await asyncio.sleep(0.5)
                continue

            try:
                # Direct read approach like working lighting.py - no need to check available
                data, overflowed = stream.read(BLOCKSIZE)
                if overflowed:
                    log_event(f"Audio buffer overflowed - blocksize: {BLOCKSIZE}", "WARNING")
                    update_status(error_count=current_status.get("error_count", 0) + 1)

                current_rms_value = np.sqrt(np.mean(data**2))
                rms_history.append(current_rms_value)
                smoothed_rms = np.mean(rms_history)

                # Log audio processing every minute to track stream health
                if int(current_time) % 60 == 0:
                    log_event(f"Audio stream health check - RMS: {smoothed_rms:.6f}, Available data: {len(data)}, Stream active: {stream.active}")

                # Log if RMS drops to zero unexpectedly (might indicate stream issue)
                if smoothed_rms == 0.0 and len(rms_history) >= RMS_SMOOTHING_WINDOW:
                    log_event(f"Warning: Zero RMS detected - Data length: {len(data)}, Stream available: {len(data)}", "WARNING")

                # Update global RMS statistics
                global current_rms, max_rms_minute, min_rms_minute, rms_minute_start
                current_rms = smoothed_rms
                current_time = time.time()

                # Reset min/max every minute
                if current_time - rms_minute_start > 60:
                    max_rms_minute = current_rms
                    min_rms_minute = current_rms
                    rms_minute_start = current_time
                else:
                    max_rms_minute = max(max_rms_minute, current_rms)
                    min_rms_minute = min(min_rms_minute, current_rms)

                # Update status with RMS data for API access
                update_status(
                    current_rms=current_rms,
                    max_rms_minute=max_rms_minute,
                    min_rms_minute=min_rms_minute
                )

                # Use hardware-controlled smooth transitions - let Tuya controller handle smoothing
                brightness_percent = get_brightness_from_rms(smoothed_rms)

                # Update global current_brightness for display purposes
                global current_brightness
                current_brightness = brightness_percent

                # Only send brightness updates when there's a meaningful change to allow hardware smooth transitions
                brightness_change = abs(brightness_percent - previous_brightness_percent)

                if brightness_change >= BRIGHTNESS_MINIMUM_CHANGE:  # Update when change >= defined
                    tuya_brightness = int(map_range(brightness_percent, 1, 100, TUYA_BRIGHTNESS_MIN, TUYA_BRIGHTNESS_MAX))
                    log_event(f"Musical LED - RMS: {smoothed_rms:.4f} -> Brightness: {brightness_percent:.1f}% (Tuya: {tuya_brightness})")

                    # Send to hardware and let Tuya controller handle smooth transition
                    await set_brightness_and_power(brightness_percent, verbose_logging=False)

                try:
                    print(f"Musical LED - RMS: {smoothed_rms:.4f} -> Brightness: {brightness_percent:.1f}%", end='\r')
                except (BrokenPipeError, OSError):
                    pass  # Ignore broken pipe errors in background service

                await asyncio.sleep(0.01)

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                log_error(f"Error in musical LED processing - Type: {error_type}, Message: {error_msg}, Stream state: {stream.active if stream else 'None'}", e)
                update_status(error_count=current_status.get("error_count", 0) + 1)

                # Try to recover from audio stream errors
                if stream and ("closed" in error_msg.lower() or "device" in error_msg.lower()):
                    log_event("Audio stream appears corrupted, attempting to recreate stream", "WARNING")
                    try:
                        stream.stop()
                        stream.close()
                        stream = sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE)
                        stream.start()
                        log_event("Audio stream successfully recreated", "INFO")
                    except Exception as stream_error:
                        log_error("Failed to recreate audio stream, entering fallback mode", stream_error)
                        fallback_mode = True
                        stream = None

                await asyncio.sleep(0.1)

    except Exception as e:
        log_error("Error starting Musical LED mode, falling back to lux monitoring", e)
        # Don't let the service crash - fall back to lux monitoring
        try:
            await lighting_led_mode()
        except Exception as fallback_e:
            log_error("Fallback to lux mode also failed, continuing with basic operation", fallback_e)
            # Keep service running with basic LED functionality
            await asyncio.sleep(1)
    finally:
        # Clean up stream if it exists
        if 'stream' in locals() and stream is not None:
            try:
                stream.close()
            except Exception:
                pass

async def lighting_led_mode():
    """Lux sensor mode - brightness reacts to light sensor (inverse)."""
    log_event("Starting Lux sensor mode")
    update_status(mode="Lux sensor")

    # Load lux history on startup
    load_lux_history()

    if not VEML7700_AVAILABLE:
        log_error("VEML7700 libraries not available for Lux sensor mode")
        update_status(tuya_available=False)
        return

    # Try to initialize light sensor
    veml7700 = None
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        veml7700 = adafruit_veml7700.VEML7700(i2c)
        veml7700.integration_time = "100ms"
        veml7700.gain = "1x"
        log_event("VEML7700 sensor initialized successfully")
    except Exception as e:
        log_error("Error initializing VEML7700 sensor", e)
        update_status(tuya_available=False)
        return

    # Check if Tuya LED is available
    tuya_available = current_status.get("connection_status") == "connected"

    # Turn on LED at start of lux sensor mode
    if tuya_available and d is not None:
        try:
            await set_brightness_and_power(50, force_update=True)  # Start with 50% brightness
            log_event("LED turned ON for lux sensor mode")
        except Exception as e:
            log_error("Failed to turn on LED for lux sensor mode", e)

    while True:
        # Check if mode changed
        config = load_config()
        if config["mode"] not in ["Lighting LED", "Lux sensor"]:  # Support both names during transition
            break

        try:
            # Always read and display lux value
            lux_value = veml7700.lux
            brightness_percent = get_brightness_from_lux(lux_value, config)

            # Save lux value to history for monitoring and exhibition display
            save_lux_history(lux_value)

            # Try to control Tuya LED if available
            if tuya_available and d is not None:
                try:
                    # Control only significant changes when controlling LED
                    if abs(brightness_percent - current_status.get("brightness", 0)) > 5:
                        await set_brightness_and_power(brightness_percent)
                        log_event(f"Lux sensor - Lux: {lux_value:.2f} -> Brightness: {brightness_percent:.1f}%")
                except Exception as e:
                    log_error("Error controlling Tuya LED, continuing with lux monitoring", e)
                    tuya_available = False
                    update_status(tuya_available=False)
            else:
                # Just monitor lux without controlling LED
                if abs(lux_value - current_status.get("lux_level", 0)) > 10:
                    log_event(f"Lux monitoring - Current lux: {lux_value:.2f} (LED control unavailable)")

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
            
            # Update only if brightness changed - let hardware handle smooth transitions
            if brightness_percent != last_brightness:
                await set_brightness_and_power(brightness_percent, force_update=True)
                log_event(f"Manual brightness -> {brightness_percent}% (Hardware Smooth Transition)")
                last_brightness = brightness_percent
                
            try:
                print(f"Manual LED - Brightness: {brightness_percent:.1f}%", end='\r')
            except (BrokenPipeError, OSError):
                pass  # Ignore broken pipe errors in background service
            await asyncio.sleep(0.1)  # Check config 10 times per second for fast response
            
        except Exception as e:
            log_error("Error in manual LED mode", e)
            await asyncio.sleep(1)

async def initialize_tuya_device():
    """Initialize Tuya device with comprehensive error handling"""
    global d, power_on_state

    try:
        log_event(f"Initializing Tuya device connection (Device ID: {DEVICE_ID})")
        d = tinytuya.BulbDevice(dev_id=DEVICE_ID, address=DEVICE_IP, local_key=DEVICE_KEY)
        d.set_version(PROTOCOL_VERSION)
        d.set_socketPersistent(True)

        # Test connection
        status_data = await asyncio.wait_for(asyncio.to_thread(d.status), timeout=5.0)
        power_on_state = status_data.get('dps', {}).get(str(DP_ID_POWER), False)

        log_event(f"Connected to Tuya device - Initial status: {status_data}")
        update_status(connection_status="connected", power_state=power_on_state, tuya_available=True)
        return True

    except asyncio.TimeoutError:
        log_error("Tuya device connection timed out - continuing with lux monitoring only")
        update_status(connection_status="timeout", tuya_available=False)
        return False
    except Exception as e:
        log_error(f"Error connecting to Tuya device - continuing with lux monitoring only: {e}")
        update_status(connection_status="error", tuya_available=False)
        return False

async def disable_mode():
    """Disable mode - LED is off and service does nothing"""
    global d
    log_event("Disable mode started")
    update_status(mode="Disable")

    try:
        # Turn off LED
        if d:
            await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, False), timeout=COMMAND_TIMEOUT_SECONDS)
            update_status(power_state=False, brightness=0)

        while True:
            try:
                config = load_config()
                # Check if mode changed
                if config["mode"] != "Disable":
                    log_event("Mode changed from Disable")
                    break

                # Do nothing in disable mode
                await asyncio.sleep(2)

            except Exception as e:
                log_error("Error in disable mode loop", e)
                await asyncio.sleep(2)

    except Exception as e:
        log_error("Error in disable mode", e)

    log_event("Disable mode stopped")

async def main():
    """Main function that switches between modes based on config."""
    global d, power_on_state

    log_event("LED Service starting")
    update_status(mode="Initializing", connection_status="connecting")

    # Try to initialize Tuya device, but continue even if it fails
    tuya_initialized = await initialize_tuya_device()
    if not tuya_initialized:
        log_event("Tuya LED not available, continuing with lux monitoring only")
        update_status(tuya_available=False)
    
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
                elif mode in ["Lighting LED", "Lux sensor"]:  # Support both names during transition
                    await lighting_led_mode()
                elif mode == "Manual LED":
                    await manual_led_mode()
                elif mode == "Disable":
                    await disable_mode()
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