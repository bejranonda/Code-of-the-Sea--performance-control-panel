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
    import smbus2 as smbus
    SMBUS_AVAILABLE = True
except ImportError as e:
    try:
        import smbus
        SMBUS_AVAILABLE = True
    except ImportError as e2:
        SMBUS_AVAILABLE = False
        print(f"Warning: Neither smbus2 nor smbus library available: {e}, {e2}")

# -------------------------------
# Configuration
# -------------------------------
I2C_BUS = 1
TEA5767_ADDR = 0x60

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "service_config.json")  # Absolute path to parent directory  
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
    "connection_status": "disconnected",
    "loop_duration": 30,  # Default loop duration in seconds
    "current_station_index": 0,
    "loop_start_time": None,
    "stations": []  # List of found stations for looping
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

        # Initialize TEA5767 with quick write (from working fm-radio.py)
        try:
            bus.write_quick(TEA5767_ADDR)
            time.sleep(0.1)
            log_event("TEA5767 initialized with quick write")
        except Exception as e:
            log_event(f"Quick write initialization failed: {e}", "WARNING")

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
            
        # Use exact working formula and structure from fm-radio.py
        freq14bit = int(4 * (freq_mhz * 1_000_000 + 225_000) / 32_768)

        # Byte 1: MSB of PLL word (bits 15-8) + MUTE bit (bit 7) - exact match to working script
        byte1 = (freq14bit >> 8) & 0xFF

        # Byte 2: LSB of PLL word (bits 7-0)
        byte2 = freq14bit & 0xFF

        # Byte 3: Control bits (SSL1, SSL2; HLSI, MS, MR, ML; SWP1)
        # Using 0xB0 from working script: SSL=01 (Search Stop Level 7), HLSI=1, others 0
        byte3 = 0xB0

        # Byte 4: Control bits (SWP2; STBY, BL; XTAL; smut; HCC, SNC, SI)
        # Base value 0x10 from working script
        # SNC is bit 0 (0x01), HCC is bit 1 (0x02) - ENABLE BOTH for better audio quality
        byte4 = 0x10
        byte4 |= 0x01  # Set SNC bit (Stereo Noise Cancellation) - from working fm-radio.py
        byte4 |= 0x02  # Set HCC bit (High Cut Control) - from working fm-radio.py

        # Byte 5: Control bits (PLREFF; DTC; 0; 0; 0; 0; 0; 0)
        # Set to 0x00 for 32.768kHz crystal, as per working script
        byte5 = 0x00

        # The data list for write_i2c_block_data should be [byte2, byte3, byte4, byte5]
        # and byte1 is passed as the 'register' argument - exact match to working fm-radio.py
        data = [byte2, byte3, byte4, byte5]

        # Retry mechanism for I2C communication
        for attempt in range(3):
            try:
                bus.write_i2c_block_data(TEA5767_ADDR, byte1, data)
                # Wait for device to settle
                time.sleep(0.1)
                # Success - frequency set
                update_status(frequency=freq_mhz)
                return True

            except OSError as e:
                if attempt == 2:  # Last attempt
                    log_error(f"I2C error setting frequency {freq_mhz:.2f} MHz after 3 attempts", e)
                    current_status["error_count"] += 1
                else:
                    log_event(f"I2C error on attempt {attempt+1}, retrying", "WARNING")
                time.sleep(0.3)  # Match working fm-radio.py timing
        return False
        
    except Exception as e:
        log_error(f"Unexpected error setting frequency {freq_mhz:.2f} MHz", e)
        return False

def read_signal_level():
    """Read signal level from TEA5767 with error handling (matches working fm-radio.py)"""
    try:
        if not bus:
            return 0

        data = bus.read_i2c_block_data(TEA5767_ADDR, 0x00, 5)
        # RSSI: Bits 4-1 of byte 4 (data[3]) - exact match to working fm-radio.py
        signal = (data[3] >> 4) & 0x0F
        update_status(signal_level=signal)
        return signal

    except Exception as e:
        log_error("Error reading signal level", e)
        current_status["error_count"] += 1
        return 0

# Frequency reading functions disabled - problematic for TEA5767 chip reading
# (Following the approach in working fm-radio.py which removed frequency_mhz calculation)

# def read_current_frequency():
#     """Read the actual frequency currently set on the TEA5767 device"""
#     # DISABLED: Frequency reading from chip is problematic (per working fm-radio.py)
#     return None

# def validate_frequency_setting(requested_freq):
#     """Validate that the device is actually tuned to the requested frequency"""
#     # DISABLED: Frequency validation causes issues - working fm-radio.py doesn't use this
#     return {"status": "success", "message": "Validation disabled"}

def read_station_info():
    """Read comprehensive station information (signal, stereo, ready) - matches working fm-radio.py"""
    try:
        if not bus:
            return {"signal": 0, "stereo": False, "ready": False}

        data = bus.read_i2c_block_data(TEA5767_ADDR, 0x00, 5)

        # Extract information from TEA5767 registers (exact match to working fm-radio.py)
        # RSSI: Bits 4-1 of byte 4 (data[3])
        signal = (data[3] >> 4) & 0x0F
        # Stereo indicator: Bit 7 of byte 1 (data[1]) - corrected from data[2]
        stereo = bool(data[1] & 0x80)
        # PLL Lock Indicator: Bit 7 of byte 2 (data[2])
        ready = bool(data[2] & 0x80)

        return {
            "signal": signal,
            "stereo": stereo,
            "ready": ready
        }

    except Exception as e:
        log_error("Error reading station info", e)
        return {"signal": 0, "stereo": False, "ready": False}

def get_min_signal_threshold():
    """Get minimum signal threshold from config"""
    try:
        # Load config if it exists
        config_file = os.path.join(os.path.dirname(__file__), "radio_search_config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get("min_signal_strength", 8)
    except:
        pass
    return 8  # Default threshold

def search_station(start_freq, direction="Up", step=0.1):
    """Enhanced station search with wraparound and intelligent selection"""
    try:
        min_signal = get_min_signal_threshold()
        log_event(f"Starting enhanced station search from {start_freq:.2f} MHz, direction: {direction}, min_signal: {min_signal}")

        freq = start_freq
        original_start = start_freq
        wrapped = False

        # Search with wraparound
        while True:
            # Check bounds and handle wraparound
            if direction.lower() == "up":
                if freq > 108:
                    if not wrapped:
                        freq = 87.0  # Wrap to beginning
                        wrapped = True
                        log_event("Reached 108 MHz, wrapping to 87 MHz")
                    else:
                        # Completed full scan, check if we're back to start
                        if freq >= original_start:
                            break
                freq += step
            else:  # direction == "down"
                if freq < 87:
                    if not wrapped:
                        freq = 108.0  # Wrap to end
                        wrapped = True
                        log_event("Reached 87 MHz, wrapping to 108 MHz")
                    else:
                        # Completed full scan, check if we're back to start
                        if freq <= original_start:
                            break
                freq -= step

            # Set frequency and test signal
            if not set_frequency(freq):
                continue

            time.sleep(0.8)  # Allow more settling time
            info = read_station_info()

            # Enhanced station selection criteria
            if (info["signal"] >= min_signal and
                info["ready"] and
                (info["stereo"] or info["signal"] >= min_signal + 2)):  # Prefer stereo or very strong mono

                stereo_text = "Stereo" if info["stereo"] else "Mono"
                log_event(f"Found station {freq:.2f} MHz (signal {info['signal']}, {stereo_text})")
                return freq

            # Check if we've completed a full loop
            if wrapped:
                if direction.lower() == "up" and freq >= original_start:
                    break
                elif direction.lower() == "down" and freq <= original_start:
                    break

        log_event("No suitable station found in full band search", "WARNING")
        return original_start  # Return to original frequency

    except Exception as e:
        log_error("Error during enhanced station search", e)
        return start_freq

def search_all_stations():
    """Scan entire FM band and return list of all good stations"""
    try:
        min_signal = get_min_signal_threshold()
        stations = []

        log_event(f"Starting full band scan (87-108 MHz), min_signal: {min_signal}")

        freq = 87.0
        step = 0.1

        # Create a stop signal file to check for interruption
        stop_file = os.path.join(os.path.dirname(__file__), "scan_stop_signal.txt")

        # Remove any existing stop signal
        if os.path.exists(stop_file):
            os.remove(stop_file)

        while freq <= 108.0:
            # Check for stop signal every few frequencies
            if int(freq * 10) % 20 == 0:  # Check every 2 MHz
                if os.path.exists(stop_file):
                    log_event(f"Scan interrupted by user at {freq:.1f} MHz")
                    break

            if set_frequency(freq):
                time.sleep(0.5)
                info = read_station_info()

                # Save stations that meet criteria
                if (info["signal"] >= min_signal and info["ready"]):
                    station_info = {
                        "frequency": round(freq, 1),
                        "signal": info["signal"],
                        "stereo": info["stereo"],
                        "quality": "Excellent" if info["signal"] >= 12 else "Good" if info["signal"] >= 9 else "Fair"
                    }
                    stations.append(station_info)

                    stereo_text = "Stereo" if info["stereo"] else "Mono"
                    log_event(f"Found station {freq:.1f} MHz (signal {info['signal']}, {stereo_text})")

                    # Save partial results periodically (every 10 stations or every 10 MHz)
                    if len(stations) % 10 == 0 or int(freq) % 10 == 0:
                        save_partial_results(stations)

            freq += step

        # Sort by signal strength (best first)
        stations.sort(key=lambda x: (-x["signal"], x["stereo"]), reverse=False)

        # Save final station list
        save_final_results(stations)

        completed_msg = f"Full band scan completed: {len(stations)} stations found"
        if os.path.exists(stop_file):
            completed_msg = f"Scan stopped by user: {len(stations)} stations found"
            os.remove(stop_file)

        log_event(completed_msg)
        return stations

    except Exception as e:
        log_error("Error during full band scan", e)
        return []

def save_partial_results(stations):
    """Save partial scan results to file"""
    try:
        stations_file = os.path.join(os.path.dirname(__file__), "found_stations.json")
        with open(stations_file, 'w') as f:
            json.dump({
                "scan_time": datetime.now().isoformat(),
                "stations": stations,
                "total_found": len(stations),
                "status": "partial"
            }, f, indent=2)
    except Exception as e:
        log_error("Error saving partial results", e)

def save_final_results(stations):
    """Save final scan results to file"""
    try:
        stations_file = os.path.join(os.path.dirname(__file__), "found_stations.json")
        with open(stations_file, 'w') as f:
            json.dump({
                "scan_time": datetime.now().isoformat(),
                "stations": stations,
                "total_found": len(stations),
                "status": "complete"
            }, f, indent=2)
    except Exception as e:
        log_error("Error saving final results", e)

def stop_scan():
    """Create stop signal to interrupt ongoing scan"""
    try:
        stop_file = os.path.join(os.path.dirname(__file__), "scan_stop_signal.txt")
        with open(stop_file, 'w') as f:
            f.write(f"STOP:{datetime.now().isoformat()}")
        log_event("Scan stop signal created")
    except Exception as e:
        log_error("Error creating stop signal", e)

# -------------------------------
# Loop Mode Functions
# -------------------------------
def handle_loop_mode():
    """Handle Loop mode station cycling with configurable duration"""
    try:
        stations = current_status.get("stations", [])
        if not stations or len(stations) == 0:
            log_event("No stations available for looping, switching to Fixed mode")
            current_status["mode"] = "Fixed"
            return

        loop_duration = float(current_status.get("loop_duration", 30))  # Convert to float
        loop_start_time = current_status.get("loop_start_time", time.time())
        current_station_index = current_status.get("current_station_index", 0)

        # Check if it's time to switch to the next station
        elapsed_time = time.time() - loop_start_time

        if elapsed_time >= loop_duration:
            # Time to switch to next station
            current_station_index = (current_station_index + 1) % len(stations)
            current_station = stations[current_station_index]

            # Set the new frequency - PASSIVE MODE like Manual Frequency
            # Don't read anything from I2C to prevent frequency corruption
            freq = float(current_station["frequency"])
            if set_frequency(freq):
                # No time.sleep() needed - just set and move on like Manual mode
                # No signal reading or I2C operations to avoid corruption

                # Update status with new station
                current_status["current_station_index"] = current_station_index
                current_status["loop_start_time"] = time.time()
                current_status["frequency"] = freq

                update_status(
                    current_station_index=current_station_index,
                    loop_start_time=time.time(),
                    frequency=freq
                )

                log_event(f"Loop: Station {current_station_index + 1}/{len(stations)} - {freq:.1f} MHz ({current_station.get('quality', 'Unknown')})")
            else:
                log_error(f"Failed to set loop frequency {freq:.2f} MHz")

        # Update time remaining for dashboard display
        time_remaining = max(0, loop_duration - elapsed_time)
        current_status["time_remaining"] = time_remaining

    except Exception as e:
        log_error("Error in loop mode handler", e)

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
                    # Use mode_selector if available, otherwise fall back to mode
                    mode = cfg.get("mode_selector", cfg.get("mode", "Fixed"))
                    log_event(f"Config change: mode={mode}, freq={cfg.get('frequency', 'N/A')}")

                    if mode == "Fixed":
                        freq = float(cfg.get("frequency", 99.5))
                        if set_frequency(freq):
                            # Allow time for frequency stabilization (matching search behavior)
                            time.sleep(0.8)
                            update_status(mode="Fixed", frequency=freq)
                            log_event(f"Set frequency: {freq:.2f} MHz")
                        else:
                            log_error(f"Failed to set frequency {freq:.2f} MHz")

                    # Continuous search mode removed - only Fixed and Scan modes supported

                    elif mode == "Scan":
                        log_event("Starting full band scan (87-108 MHz)")
                        update_status(mode="Scanning", frequency=87.0)

                        try:
                            stations = search_all_stations()

                            if stations:
                                # Set to first (strongest) station
                                best_station = stations[0]
                                cfg["frequency"] = best_station["frequency"]

                                # Check if we should go to Loop mode or Fixed mode
                                original_config = read_config()
                                target_mode = original_config.get("mode_selector", original_config.get("mode", "Fixed"))

                                if target_mode == "Loop":
                                    # Keep Loop mode and set up station cycling
                                    cfg["mode"] = "Loop"
                                    cfg["mode_selector"] = "Loop"
                                    current_status["stations"] = stations
                                    current_status["current_station_index"] = 0
                                    log_event(f"Scan complete: {len(stations)} stations found, switching to Loop mode")
                                else:
                                    # Switch to Fixed mode with best station
                                    cfg["mode"] = "Fixed"
                                    cfg["mode_selector"] = "Fixed"
                                    log_event(f"Scan complete: {len(stations)} stations found, switching to Fixed mode")

                                write_config(cfg)

                                log_event(f"Scan complete: {len(stations)} stations found, will tune to {best_station['frequency']:.1f} MHz")
                                # Prepare station list for dashboard display
                                station_list = []
                                for station in stations:
                                    station_list.append({
                                        "frequency": station["frequency"],
                                        "signal": station["signal"],  # Changed from signal_strength to signal
                                        "stereo": station["stereo"],
                                        "quality": station["quality"]  # Added missing quality field
                                    })
                                update_status(mode="Fixed", frequency=best_station["frequency"], stations=station_list)
                                # Remove duplicate set_frequency call - let main loop handle it via config change
                            else:
                                log_event("Scan complete: No stations found")
                                cfg["mode"] = "Fixed"  # Fall back to fixed mode
                                cfg["mode_selector"] = "Fixed"  # Set mode_selector to Fixed
                                write_config(cfg)
                                update_status(mode="Fixed")

                        except Exception as e:
                            log_error("Error during full band scan", e)
                            cfg["mode"] = "Fixed"  # Fall back to fixed mode
                            cfg["mode_selector"] = "Fixed"  # Set mode_selector to Fixed
                            write_config(cfg)
                            update_status(mode="Fixed")

                    elif mode == "Loop":
                        # Loop mode - cycle through found stations with configurable duration
                        loop_duration = float(cfg.get("loop_duration", 30))  # Convert to float from config

                        # Check if we have stations to loop through
                        if current_status.get("stations") and len(current_status["stations"]) > 0:
                            log_event(f"Starting Loop mode with {len(current_status['stations'])} stations, {loop_duration}s per station")
                            update_status(
                                mode="Loop",
                                loop_duration=loop_duration,
                                loop_start_time=time.time()
                            )
                        else:
                            log_event("Loop mode requested but no stations available, scanning first...")
                            # No stations available, perform scan first
                            stations = search_all_stations()
                            if stations:
                                current_status["stations"] = stations
                                current_status["current_station_index"] = 0
                                log_event(f"Scan complete: {len(stations)} stations found, starting loop mode")
                                update_status(
                                    mode="Loop",
                                    loop_duration=loop_duration,
                                    loop_start_time=time.time(),
                                    stations=stations,
                                    current_station_index=0
                                )
                            else:
                                log_event("No stations found, falling back to Fixed mode")
                                cfg["mode"] = "Fixed"
                                cfg["mode_selector"] = "Fixed"
                                write_config(cfg)
                                update_status(mode="Fixed")

                    last_config = cfg.copy()

                # MODE-SPECIFIC OPERATIONS
                current_mode = current_status.get("mode", "")

                if current_mode == "Fixed":
                    # PASSIVE MODE: Do absolutely nothing after frequency is set
                    # Just like the working fm-radio.py - set frequency and leave it alone
                    # No logging, no I2C operations, no file operations - radio silence
                    time.sleep(5)  # Sleep longer to reduce any potential interference

                elif current_mode == "Loop":
                    # LOOP MODE: Cycle through stations with timing
                    handle_loop_mode()
                    time.sleep(1)  # Check every second for timing

                else:
                    # In other modes (like Scanning), minimal operations
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
                set_frequency_with_mute(87.5, mute=True)
                bus.close()
                log_event("I2C bus closed")
        except Exception as e:
            log_error("Error during cleanup", e)
        
        update_status(connection_status="disconnected")
        log_event("Radio service stopped")

def set_frequency_with_mute(freq_mhz, mute=False):
    """Enhanced frequency setting with mute capability - matches working fm-radio.py exactly"""
    try:
        if not bus:
            log_error("I2C bus not initialized")
            return False

        # Use exact working formula and structure from fm-radio.py
        freq14bit = int(4 * (freq_mhz * 1_000_000 + 225_000) / 32_768)

        # Byte 1: MSB of PLL word (bits 15-8) + MUTE bit (bit 7) - exact match to working script
        byte1 = (freq14bit >> 8) & 0xFF
        if mute:
            byte1 |= 0x80  # Set MUTE bit

        # Byte 2: LSB of PLL word (bits 7-0)
        byte2 = freq14bit & 0xFF

        # Byte 3: Control bits (SSL1, SSL2; HLSI, MS, MR, ML; SWP1)
        # Using 0xB0 from working script: SSL=01 (Search Stop Level 7), HLSI=1, others 0
        byte3 = 0xB0

        # Byte 4: Control bits (SWP2; STBY, BL; XTAL; smut; HCC, SNC, SI)
        # Base value 0x10 from working script
        # SNC is bit 0 (0x01), HCC is bit 1 (0x02) - ENABLE BOTH for better audio quality
        byte4 = 0x10
        byte4 |= 0x01  # Set SNC bit (Stereo Noise Cancellation) - from working fm-radio.py
        byte4 |= 0x02  # Set HCC bit (High Cut Control) - from working fm-radio.py

        # Byte 5: Control bits (PLREFF; DTC; 0; 0; 0; 0; 0; 0)
        # Set to 0x00 for 32.768kHz crystal, as per working script
        byte5 = 0x00

        # The data list for write_i2c_block_data should be [byte2, byte3, byte4, byte5]
        # and byte1 is passed as the 'register' argument - exact match to working fm-radio.py
        data = [byte2, byte3, byte4, byte5]

        # Retry mechanism
        for attempt in range(3):
            try:
                bus.write_i2c_block_data(TEA5767_ADDR, byte1, data)

                # Wait for device to settle
                time.sleep(0.1)

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
                time.sleep(0.3)  # Match working fm-radio.py timing
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