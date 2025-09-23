### veml7700_led_control.py (optimized)

import tinytuya
import time
import asyncio
import board
import busio
import adafruit_veml7700

# --- VEML7700 Lux Sensor Wiring to Raspberry Pi ---
# Pi 3V3  -> sensor VIN
# Pi GND   -> sensor GND
# Pi SCL (GPIO3) -> sensor SCL
# Pi SDA (GPIO2) -> sensor SDA
# Ensure I2C is enabled on your Raspberry Pi via 'sudo raspi-config'.

# --- Tuya Device Configuration ---
DEVICE_ID = "bf549c1fed6b2bbd43l1ow"
DEVICE_IP = "192.168.178.42"
DEVICE_KEY = "73b0K93QaO&EI=dB"

# --- Tuya Data Point (DP) IDs ---
DP_ID_POWER = 20
DP_ID_WORK_MODE = 21
DP_ID_BRIGHTNESS = 22

# --- Tuya Controller Value Ranges ---
TUYA_BRIGHTNESS_MIN = 10
TUYA_BRIGHTNESS_MAX = 1000

# --- Lux Mapping Configuration ---
SENSOR_LUX_MIN = 20    # Dark room -> 100% LED
SENSOR_LUX_MAX = 1500   # Bright room -> 0% LED

# --- Lux Scale Bar Configuration ---
BAR_MAX_LENGTH = 50 # Maximum length of the scale bar in characters
BAR_CHAR = '█'      # Character to use for the bar (U+2588 Full Block)

# --- Command Rate Limiting ---
MIN_COMMAND_INTERVAL_SECONDS = 0.3
COMMAND_TIMEOUT_SECONDS = 0.5

# --- Globals ---
last_command_time = 0
previous_brightness_percent = -1
d = None
cached_power_state = None  # Track last known power state

# --- Helper Functions ---
def map_range(value, in_min, in_max, out_min, out_max):
    """Maps a value from one numerical range to another, clamping to the output range."""
    clamped_value = max(in_min, min(in_max, value))
    return (clamped_value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def get_brightness_from_lux(lux_value):
    """Maps lux value to an LED brightness percentage (0-100%) with inverse mapping."""
    brightness_percent = map_range(
        lux_value, SENSOR_LUX_MIN, SENSOR_LUX_MAX, 100, 0
    )
    return max(0, min(100, brightness_percent))

def apply_gamma(brightness_percent, gamma=2.2):
    """Convert linear % to gamma-corrected Tuya brightness value"""
    normalized = brightness_percent / 100
    corrected = normalized ** gamma
    return int(TUYA_BRIGHTNESS_MIN + 
               (TUYA_BRIGHTNESS_MAX - TUYA_BRIGHTNESS_MIN) * corrected)

# --- Tuya Control ---
async def set_brightness_from_lux(lux_value):
    global d, last_command_time, previous_brightness_percent, cached_power_state

    current_time = time.monotonic()
    brightness_percent = get_brightness_from_lux(lux_value)
    tuya_brightness = apply_gamma(brightness_percent)

    # --- Create Lux Scale Bar ---
    bar_length = int(map_range(lux_value, SENSOR_LUX_MIN, SENSOR_LUX_MAX, 0, BAR_MAX_LENGTH))
    sound_bar = BAR_CHAR * bar_length + ' ' * (BAR_MAX_LENGTH - bar_length)

    is_command_needed = (
        (current_time - last_command_time) >= MIN_COMMAND_INTERVAL_SECONDS
        and int(brightness_percent) != int(previous_brightness_percent)
    )
    if not is_command_needed:
        # Print the bar without a command send
        print(f"Lux: {lux_value:.2f} [{sound_bar}] -> Brightness: {brightness_percent:.1f}% (Tuya {tuya_brightness})", end='\r')
        return

    power_state = (brightness_percent > 0)

    try:
        # Only change power state if different from cached
        if cached_power_state != power_state:
            await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, power_state), timeout=COMMAND_TIMEOUT_SECONDS)
            cached_power_state = power_state
            print(f"LED Power {'ON' if power_state else 'OFF'}")

        if power_state:
            await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_WORK_MODE, 'white'), timeout=COMMAND_TIMEOUT_SECONDS)
            await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_BRIGHTNESS, tuya_brightness), timeout=COMMAND_TIMEOUT_SECONDS)

        last_command_time = current_time
        previous_brightness_percent = brightness_percent
        print(f"Lux: {lux_value:.2f} [{sound_bar}] -> Brightness: {brightness_percent:.1f}% (Tuya {tuya_brightness})", end='\r')

    except asyncio.TimeoutError:
        print(f"⚠️ Tuya command timed out after {COMMAND_TIMEOUT_SECONDS}s")
    except Exception as e:
        print(f"❌ Error sending command: {e}")

# --- Main ---
async def main():
    global d, cached_power_state

    # print("Connecting to Tuya controller...")
    # try:
        # d = tinytuya.BulbDevice(dev_id=DEVICE_ID, address=DEVICE_IP, local_key=DEVICE_KEY)
        # d.set_version(3.5)
        # d.set_socketPersistent(True)

        # status_data = await asyncio.to_thread(d.status)
        # cached_power_state = status_data.get('dps', {}).get(str(DP_ID_POWER), None)
        # print(f"Initial status: {status_data}")

    # except Exception as e:
        # print(f"❌ Error connecting to Tuya device: {e}")
        # return

    print("\nInitializing VEML7700 Lux Sensor...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        veml7700 = adafruit_veml7700.VEML7700(i2c)

        # Set recommended defaults
        veml7700.integration_time = "100ms"
        veml7700.gain = "1x"

        print("✅ VEML7700 Sensor ready.")
    except Exception as e:
        print(f"❌ Error initializing VEML7700: {e}")
        return


    print(f"\nStarting light monitoring. Mapping Lux {SENSOR_LUX_MIN} (darkest) → {SENSOR_LUX_MAX} (brightest).")

    try:
        while True:
            lux_value = veml7700.lux
            await set_brightness_from_lux(lux_value)
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        try:
            await asyncio.wait_for(asyncio.to_thread(d.set_value, DP_ID_POWER, False), timeout=COMMAND_TIMEOUT_SECONDS)
            print("LED strip turned OFF.")
        except Exception:
            pass
        d.close()

if __name__ == "__main__":
    asyncio.run(main())
