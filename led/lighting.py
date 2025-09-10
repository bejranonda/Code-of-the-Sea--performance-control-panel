### lighting.py

import tinytuya
import time
import sounddevice as sd
import numpy as np
import collections
import asyncio # Import asyncio

# --- Tuya Device Configuration (LOADED FROM CONFIG FILE) ---
# Device credentials are loaded from config/devices.json for security
from core.device_config import get_device_config

try:
    config = get_device_config()
    DEVICE_ID, DEVICE_IP, DEVICE_KEY, PROTOCOL_VERSION = config.get_tuya_credentials()
except Exception as e:
    print(f"Error loading device config: {e}")
    # Fallback for testing - remove in production
    DEVICE_ID = "your_device_id_here"
    DEVICE_IP = "192.168.1.100" 
    DEVICE_KEY = "your_device_key_here"
    PROTOCOL_VERSION = "3.5"

# --- Tuya Data Point (DP) IDs (CONFIRMED from your wizard output!) ---
# These DPs are now verified to be correct for your device.
DP_ID_POWER = 20       # DP for ON/OFF (Boolean)
DP_ID_WORK_MODE = 21   # DP for work mode (Enum: "white", "colour", "scene", "music")
DP_ID_BRIGHTNESS = 22  # DP for brightness (Value)
DP_ID_COLOR_TEMP = 23  # DP for color temperature (Value)

# --- Tuya Controller Value Ranges (CONFIRMED from your wizard output!) ---
# These ranges are now verified to be correct for your device.
TUYA_BRIGHTNESS_MIN = 10   # Lowest brightness value the controller accepts
TUYA_BRIGHTNESS_MAX = 1000 # Largest brightness value the controller accepts

TUYA_CCT_MIN = 0     # Value for pure Warm White (based on 2700K mapping)
TUYA_CCT_MAX = 1000  # Value for pure Cool White (based on 6500K mapping)

# --- Fixed Color Temperature Setting ---
FIXED_KELVIN_TEMP = 2900 # Desired fixed color temperature in Kelvin
# Helper function to convert Kelvin to Tuya's 0-1000 temperature scale
def kelvin_to_tuya_temp(kelvin):
    """
    Converts a Kelvin temperature (2700K-6500K) to the Tuya controller's 0-1000 scale.
    Assumes 2700K maps to TUYA_CCT_MIN (warmest) and 6500K maps to TUYA_CCT_MAX (coolest).
    """
    # Ensure Kelvin input is within the expected range
    kelvin = max(2700, min(6500, kelvin))
    
    # Map Kelvin range (2700-6500) to Tuya CCT range (0-1000)
    # Note: Tuya's 'temp_value' often has 0 as warmest and 1000 as coolest.
    # So, 2700K (warm) should map to TUYA_CCT_MIN (0), and 6500K (cool) to TUYA_CCT_MAX (1000).
    tuya_temp_value = int((kelvin - 2700) * (TUYA_CCT_MAX - TUYA_CCT_MIN) / (6500 - 2700) + TUYA_CCT_MIN)
    return tuya_temp_value

# Calculate the fixed Tuya CCT value once
FIXED_TUYA_CCT_VALUE = kelvin_to_tuya_temp(FIXED_KELVIN_TEMP)


# --- Audio Configuration ---
SAMPLERATE = 44100       # samples per second (standard audio sample rate)
CHANNELS = 1             # mono audio
BLOCKSIZE = 2048         # number of samples processed at a time

# --- Sound Level to LED Mapping (Crucial for tuning! Adjust these) ---
MIC_RMS_QUIET = 0.002   # RMS value considered "quiet" / "emotional" music (threshold for active/0% brightness)
MIC_RMS_LOUD = 0.01     # RMS value considered "loud" / "crazy" music

# --- LED Behavior when Sound is Below MIC_RMS_QUIET ---
# Set to True: LED turns OFF completely when sound is below MIC_RMS_QUIET
# Set to False: LED stays ON but goes to 0% brightness when sound is below MIC_RMS_QUIET
TURN_OFF_BELOW_QUIET_THRESHOLD = False 

# Smoothing: Average RMS over a few blocks to prevent jittery changes
RMS_SMOOTHING_WINDOW = 5 # Number of recent RMS values to average
rms_history = collections.deque(maxlen=RMS_SMOOTHING_WINDOW)

# --- Command Rate Limiting & Timeout ---
# Minimum time (in seconds) between sending commands to the Tuya device.
# Adjust this value to balance responsiveness and device load.
# 0.05 seconds = 20 updates/second (good starting point)
# 0.1 seconds = 10 updates/second
MIN_COMMAND_INTERVAL_SECONDS = 0.2 
last_command_time = 0 # To track when the last command was sent

# Timeout for individual Tuya commands. If a command doesn't complete within this time, it's considered failed.
COMMAND_TIMEOUT_SECONDS = 0.5

# --- Brightness Change Optimization ---
# Stores the last brightness percentage sent to avoid redundant commands
previous_brightness_percent = -1 # Initialize with an invalid value to force first send

# --- Mapping Functions ---
def map_range(value, in_min, in_max, out_min, out_max):
    """Maps a value from one numerical range to another."""
    # Clamp value to input range to prevent extrapolation
    value = max(in_min, min(in_max, value))
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def get_brightness_from_rms(rms):
    """Maps RMS to LED brightness (0-100%)."""
    # Brighter when music is crazy (loud), dimmer when emotional (quiet)
    return map_range(rms, MIC_RMS_QUIET, MIC_RMS_LOUD, 0, 100) # Map to 0-100%

# --- Tuya Control Function (now async and non-blocking) ---
async def set_brightness_and_cct(brightness_percent):
    """
    Sends brightness and fixed color temperature commands to the Tuya CCT controller.
    brightness_percent: 0-100 (overall brightness)
    """
    global last_command_time
    global previous_brightness_percent # Declare global to modify the variable

    current_time = time.monotonic()
    
    # Check rate limit first
    if (current_time - last_command_time) < MIN_COMMAND_INTERVAL_SECONDS:
        # print("Skipping command: too soon.") # Uncomment for debugging rate limit
        return # Skip sending command if too soon

    # Check if brightness is effectively the same as last time
    # Convert to Tuya scale for comparison to avoid floating point issues with percentages
    current_tuya_brightness = int(map_range(brightness_percent, 0, 100, TUYA_BRIGHTNESS_MIN, TUYA_BRIGHTNESS_MAX))
    previous_tuya_brightness = int(map_range(previous_brightness_percent, 0, 100, TUYA_BRIGHTNESS_MIN, TUYA_BRIGHTNESS_MAX))

    if abs(current_tuya_brightness - previous_tuya_brightness) < 5:
        #print(f"current_tuya_brightness - previous_tuya_brightness) < 15 {brightness_percent:.1f}%") # Uncomment for debugging
        return
    #if current_tuya_brightness == previous_tuya_brightness:
        # print(f"Skipping command: brightness {brightness_percent:.1f}% is same as previous.") # Uncomment for debugging
     #   return # Skip sending command if brightness hasn't changed

    # Map input percentages (0-100) to Tuya controller's specific ranges
    tuya_brightness = current_tuya_brightness
    tuya_cct = FIXED_TUYA_CCT_VALUE

    tuya_brightness = max(TUYA_BRIGHTNESS_MIN, min(TUYA_BRIGHTNESS_MAX, tuya_brightness))

    try:
        # Use asyncio.to_thread to run blocking d.set_value calls in a separate thread
        # This prevents the main event loop from being blocked.
        # Each set_value call now has a timeout
        #await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_WORK_MODE, 'white'), timeout=COMMAND_TIMEOUT_SECONDS)
        await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_BRIGHTNESS, tuya_brightness), timeout=COMMAND_TIMEOUT_SECONDS)
        #await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_COLOR_TEMP, tuya_cct), timeout=COMMAND_TIMEOUT_SECONDS)

        last_command_time = current_time # Update last command time only on successful send
        previous_brightness_percent = brightness_percent # Update previous brightness

    except asyncio.TimeoutError:
        print(f"Warning: Tuya command timed out after {COMMAND_TIMEOUT_SECONDS}s. Device might be slow or unresponsive.")
        # Do not update last_command_time or previous_brightness_percent on timeout
        # This allows the next loop iteration to attempt sending a command again.
    except Exception as e:
        print(f"Error sending brightness/CCT command: {e}")
        # Consider adding more sophisticated error handling or reconnection logic here

# --- Main Script (now async) ---
async def main():
    print('Connecting to Tuya CCT controller...')
    # Initialize the Tuya device object
    # Note: d is a global variable, so it's accessible within async functions
    global d
    d = tinytuya.BulbDevice(
        dev_id=DEVICE_ID,
        address=DEVICE_IP,
        local_key=DEVICE_KEY
    )
    d.set_version(3.5) # Set the Tuya protocol version to 3.5 as per your working test script
    d.set_socketPersistent(True) # Keep the connection open for continuous control

    # Variable to track the current power state of the LED strip
    global power_on_state
    power_on_state = False

    try:
        # Attempt to get initial status to confirm connection
        # This is a blocking call, so we'll also run it in a thread
        status_data = await asyncio.to_thread(d.status)
        print(f"Initial device status: {status_data}")

        # Initial state: Turn off the LED strip to start clean
        try:
            await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, False), timeout=COMMAND_TIMEOUT_SECONDS)
            power_on_state = False
            print("LED strip initialized to OFF state.")
        except asyncio.TimeoutError:
            print(f"Warning: Initial LED OFF command timed out after {COMMAND_TIMEOUT_SECONDS}s.")
        except Exception as e:
            print(f"Error during initial LED OFF: {e}")

        print('Starting audio monitoring for LED control. Press Ctrl-C to quit.')

        # Use sounddevice to open an audio input stream
        print("\n--- Audio Devices ---")
        # sd.query_devices() is a blocking call, but typically run once at start.
        # No need to await asyncio.to_thread for this as it's not in the main loop.
        print(sd.query_devices()) 
        print("---------------------\n")
        print("If you see multiple input devices, you might need to specify one.")
        print("e.g., sd.InputStream(device='your_device_name_or_index', ...)")
        print("Or ensure your default input device is correctly configured in your OS.")

        with sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, blocksize=BLOCKSIZE) as stream:
            while True:
                # Read audio data from the microphone
                data, overflowed = stream.read(BLOCKSIZE)
                if overflowed:
                    print("Audio buffer overflowed!") # Warn if audio buffer couldn't keep up

                # Calculate the Root Mean Square (RMS) of the audio data
                current_rms = np.sqrt(np.mean(data**2))
                
                # Add current RMS to history and calculate smoothed average
                rms_history.append(current_rms)
                smoothed_rms = np.mean(rms_history)

                # Initialize values for print statement
                brightness_level_percent = 0.0
                tuya_brightness_val_for_print = TUYA_BRIGHTNESS_MIN

                # --- Power and Brightness Management Logic ---
                if smoothed_rms >= MIC_RMS_QUIET:
                    # Sound is above the quiet threshold: normal reactivity
                    brightness_level_percent = get_brightness_from_rms(smoothed_rms)
                    tuya_brightness_val_for_print = int(map_range(brightness_level_percent, 0, 100, TUYA_BRIGHTNESS_MIN, TUYA_BRIGHTNESS_MAX))

                    if not power_on_state:
                        try:
                            await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, True), timeout=COMMAND_TIMEOUT_SECONDS)
                            power_on_state = True
                            print(f"LED ON (RMS: {smoothed_rms:.4f}) - Active Sound")
                            await asyncio.sleep(0.1) # Small async delay
                        except asyncio.TimeoutError:
                            print(f"Warning: LED ON command timed out after {COMMAND_TIMEOUT_SECONDS}s.")
                        except Exception as e:
                            print(f"Error turning LED ON: {e}")
                    
                    if power_on_state: # Check again in case turning on failed
                        await set_brightness_and_cct(brightness_level_percent)
                        print(f"RMS: {smoothed_rms:.4f} -> Brightness: {brightness_level_percent:.1f}% ({tuya_brightness_val_for_print})")

                else: # smoothed_rms < MIC_RMS_QUIET
                    # Sound is below the quiet threshold
                    if TURN_OFF_BELOW_QUIET_THRESHOLD:
                        # Turn off the LED if it's currently on
                        if power_on_state:
                            try:
                                await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, False), timeout=COMMAND_TIMEOUT_SECONDS)
                                power_on_state = False
                                print(f"LED OFF (RMS: {smoothed_rms:.4f}) - Below Quiet Threshold")
                            except asyncio.TimeoutError:
                                print(f"Warning: LED OFF command timed out after {COMMAND_TIMEOUT_SECONDS}s.")
                            except Exception as e:
                                print(f"Error turning LED OFF: {e}")
                    else:
                        # Keep LED on but set to 0% brightness
                        brightness_level_percent = 0.0 # Explicitly 0% brightness
                        tuya_brightness_val_for_print = TUYA_BRIGHTNESS_MIN # Tuya's lowest brightness value

                        if not power_on_state: # If it was off, turn it on first
                             try:
                                await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, True), timeout=COMMAND_TIMEOUT_SECONDS)
                                power_on_state = True
                                print(f"LED ON (RMS: {smoothed_rms:.4f}, setting to 0% brightness) - Below Quiet Threshold")
                                await asyncio.sleep(0.1)
                             except asyncio.TimeoutError:
                                print(f"Warning: LED ON (0%) command timed out after {COMMAND_TIMEOUT_SECONDS}s.")
                             except Exception as e:
                                print(f"Error turning LED ON for 0% brightness: {e}")
                        if power_on_state: # If now on, set to 0% brightness
                            await set_brightness_and_cct(0) # 0% brightness
                            print(f"RMS: {smoothed_rms:.4f} -> Brightness: 0.0% ({tuya_brightness_val_for_print}) - Below Quiet Threshold")

                # Small async sleep to yield control and prevent busy-waiting
                await asyncio.sleep(0.001) # Adjust if needed, but keep small

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Please check the DEVICE_ID, DEVICE_IP, and DEVICE_KEY in the script.")
        print("Ensure your Tuya device is powered on, connected to the same Wi-Fi network as your Raspberry Pi, and not being controlled by the Smart Life/Tuya app simultaneously.")
        print("If the error persists, try running `python3 -m tinytuya wizard` again to re-verify your device credentials.")
        print("\n--- Microphone Troubleshooting ---")
        print("If RMS is always 0.0000, your microphone might not be working or selected correctly.")
        print("1. Ensure your microphone is plugged in and not muted.")
        print("2. Check your operating system's sound settings for input volume/gain.")
        print("3. Look at the '--- Audio Devices ---' list printed above. If your microphone is not the default, you might need to specify it in `sd.InputStream(device='device_name_or_index', ...)`.")
    finally:
        print("Exiting...")
        # Attempt to turn off the LED strip gracefully when the script ends
        try:
            await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, False), timeout=COMMAND_TIMEOUT_SECONDS)
            print("LED strip turned OFF.")
        except asyncio.TimeoutError:
            print(f"Warning: Final LED OFF command timed out after {COMMAND_TIMEOUT_SECONDS}s.")
        except Exception as e:
            print(f"Error turning off device: {e}")
        d.close() # Close the network socket connection

# Run the main asynchronous function
if __name__ == '__main__':
    asyncio.run(main())
