#!/usr/bin/env python3
# mixing_menu.py - Audio Mixing Service

import time
import json
import os
import sys
import subprocess
import shutil
import traceback
from datetime import datetime
from pathlib import Path

# Configuration
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "service_config.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "mixing_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "mixing_status.json")

# Audio directories
MASTER_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "master_audio")
MIXED_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "mixed_output")
BROADCAST_MEDIA_DIR = os.path.join(os.path.dirname(__file__), "..", "broadcast", "media")

# Microphone settings
MIC_SAMPLE_RATE = 44100
MIC_DURATION = 30  # seconds for microphone recording

def detect_usb_microphone():
    """Automatically detect best USB audio input device with PulseAudio compatibility"""
    try:
        # For systems with PulseAudio running, always prefer pulse device for reliability
        # Check if PulseAudio is running
        pulse_running = False
        try:
            result = subprocess.run(['pgrep', '-f', 'pulseaudio'], capture_output=True, text=True)
            pulse_running = result.returncode == 0
        except:
            pass

        if pulse_running:
            log_event("PulseAudio detected - using pulse device for better compatibility")
            # Test pulse device first
            if test_audio_device_recording("pulse"):
                log_event("Successfully detected working microphone: pulse")
                return "pulse"

        # Fallback: Try other devices if pulse doesn't work
        devices_to_test = []

        # Method 1: arecord -l for capture devices
        result = subprocess.run(['/usr/bin/arecord', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'card' in line and ('USB' in line or 'Audio' in line or 'Microphone' in line):
                    # Extract card number
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.startswith('card'):
                            card_num = parts[i+1].rstrip(':')
                            # Prefer plughw over hw for better compatibility
                            plughw_device = f"plughw:{card_num},0"
                            hw_device = f"hw:{card_num},0"
                            if plughw_device not in devices_to_test:
                                devices_to_test.append(plughw_device)
                            if hw_device not in devices_to_test:
                                devices_to_test.append(hw_device)

        # Method 2: Add common compatible devices
        common_devices = ["default", "plughw:1,0", "plughw:2,0", "plughw:3,0"]
        for device in common_devices:
            if device not in devices_to_test:
                devices_to_test.append(device)

        # Test each device with longer recording test to catch intermittent failures
        for device in devices_to_test:
            if test_audio_device_recording(device, test_duration=3):  # 3 second test
                log_event(f"Successfully detected working microphone: {device}")
                return device

        log_event("No working microphone found, using pulse fallback", "WARNING")
        return "pulse"  # PulseAudio fallback for better compatibility

    except Exception as e:
        log_event(f"Error detecting microphone: {e}", "WARNING")
        return "pulse"  # PulseAudio fallback for better compatibility

def test_audio_device(device):
    """Test if an audio device exists and is accessible"""
    try:
        # Handle different device formats
        if device == 'pulse':
            return True  # PulseAudio device should always be testable
        elif device == 'default':
            return True  # Default device should always be testable
        elif device.startswith('plughw:'):
            card_num = device.split(':')[1].split(',')[0]
        elif device.startswith('hw:'):
            card_num = device.split(':')[1].split(',')[0]
        else:
            return False

        if not card_num.isdigit():
            return False

        # Check if card exists
        cards_result = subprocess.run(['/usr/bin/cat', '/proc/asound/cards'], capture_output=True, text=True)
        if cards_result.returncode != 0:
            return False

        # Look for the card number in available cards
        for line in cards_result.stdout.split('\n'):
            if line.strip().startswith(card_num + ' '):
                return True
        return False
    except:
        return False

def test_audio_device_recording(device, test_duration=1):
    """Test if device can actually record audio with configurable duration test"""
    try:
        # Configurable duration recording test
        test_file = f"/tmp/mic_test_{device.replace(':', '_').replace('/', '_')}.wav"
        cmd = [
            "/usr/bin/arecord",
            "-D", device,
            "-f", "S16_LE",
            "-r", "44100",
            "-c", "1",
            "-d", str(test_duration),
            test_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=test_duration + 5)

        # Check if recording was successful and completed the full duration
        expected_min_size = int(test_duration * 44100 * 2 * 0.8)  # 80% of expected size
        success = (result.returncode == 0 and
                  os.path.exists(test_file) and
                  os.path.getsize(test_file) >= expected_min_size and
                  "read error" not in result.stderr and
                  "No such device" not in result.stderr)

        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

        if not success and result.stderr:
            log_event(f"Device {device} test failed: {result.stderr.strip()}", "WARNING")

        return success

    except Exception as e:
        log_event(f"Device {device} test exception: {e}", "WARNING")
        return False

# Global status
current_status = {
    "mode": "Auto",
    "master_volume": 70,
    "mic_volume": 30,
    "recording_duration": 30,  # Recording duration in seconds
    "last_mixing": None,
    "mixed_files_count": 0,
    "last_update": None,
    "recording": False,
    "error_count": 0,
    "status": "idle",
    "latest_output_file": None,
    "master_position": 0,  # Current position in master file (seconds)
    "master_duration": 0   # Total duration of master file (seconds)
}

def log_event(message, level="INFO"):
    """Log events with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {level}: {message}\n"

    try:
        # Read existing logs
        existing_logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                existing_logs = f.readlines()

        # Add new log at the top (newest first)
        with open(LOG_FILE, 'w') as f:
            f.write(log_entry)
            for line in existing_logs[:999]:  # Keep last 1000 entries
                f.write(line)

        print(f"Mixing Service - {message}")
    except Exception as e:
        print(f"Error logging event: {e}")

def log_error(message, error):
    """Log error with traceback"""
    error_details = f"{message}\nException: {str(error)}\nTraceback:\n{traceback.format_exc()}"
    log_event(error_details, "ERROR")

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
    """Read configuration for mixing service"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config.get("Mixing Service", {
                    "mode": "Auto",
                    "master_volume": 70,
                    "mic_volume": 30,
                    "master_file": "",
                    "auto_interval": 60  # seconds
                })
        return {
            "mode": "Auto",
            "master_volume": 70,
            "mic_volume": 30,
            "master_file": "",
            "auto_interval": 60
        }
    except Exception as e:
        log_error("Error reading config", e)
        return {}

def write_config(config):
    """Write configuration to file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                full_config = json.load(f)
        else:
            full_config = {}

        full_config["Mixing Service"] = config

        with open(CONFIG_FILE, "w") as f:
            json.dump(full_config, f, indent=2)

    except Exception as e:
        log_error("Error writing config", e)

def get_master_files():
    """Get list of available master audio files"""
    try:
        master_files = []
        if os.path.exists(MASTER_AUDIO_DIR):
            for file in os.listdir(MASTER_AUDIO_DIR):
                if file.lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                    file_path = os.path.join(MASTER_AUDIO_DIR, file)
                    master_files.append({
                        "filename": file,
                        "path": file_path,
                        "size": os.path.getsize(file_path),
                        "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    })
        return sorted(master_files, key=lambda x: x['modified'], reverse=True)
    except Exception as e:
        log_error("Error getting master files", e)
        return []

def get_audio_duration(file_path):
    """Get duration of audio file in seconds using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return 0
    except Exception:
        return 0

def record_microphone(output_file, duration=MIC_DURATION):
    """Record from microphone using arecord with auto-detection and error recovery"""
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            # Auto-detect microphone device fresh each attempt
            mic_device = detect_usb_microphone()
            log_event(f"Detected microphone device: {mic_device}")
            log_event(f"Starting microphone recording ({duration}s) - attempt {attempt + 1}/{max_retries}")
            log_event(f"Recording start time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            update_status(recording=True, status="recording")

            # Kill any stuck arecord processes before starting
            try:
                subprocess.run(['pkill', '-9', '-f', 'arecord'], timeout=5, capture_output=True)
                # Reset audio system if on retry
                if attempt > 0:
                    subprocess.run(['sudo', 'alsa', 'force-reload'], timeout=10, capture_output=True)
                    time.sleep(2)
                    log_event(f"Reset audio system before retry {attempt + 1}")
            except:
                pass

            # Use full path to arecord
            arecord_path = "/usr/bin/arecord"
            if not os.path.exists(arecord_path):
                arecord_path = "arecord"

            # More robust recording command with better error handling
            cmd = [
                arecord_path,
                "-D", mic_device,
                "-f", "S16_LE",
                "-r", str(MIC_SAMPLE_RATE),
                "-c", "1",  # Mono
                "-d", str(duration),
                "--max-file-time", str(duration + 5),  # Allow extra time for file writes
                output_file
            ]

            # Ensure proper environment
            env = os.environ.copy()
            env['PATH'] = '/usr/bin:/bin:/usr/local/bin:' + env.get('PATH', '')
            env['ALSA_PCM_CARD'] = mic_device.split(':')[1].split(',')[0] if ':' in mic_device else '1'

            log_event(f"Executing arecord command: {' '.join(cmd)}")
            start_time = time.time()

            # Extended timeout to allow for full recording + buffer
            timeout_duration = int(duration) + 15
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_duration, env=env)

            end_time = time.time()
            actual_duration = end_time - start_time

            log_event(f"Recording end time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            log_event(f"Actual recording duration: {actual_duration:.2f}s (expected: {duration}s)")
            log_event(f"arecord return code: {result.returncode}")
            if result.stdout:
                log_event(f"arecord stdout: {result.stdout}")
            if result.stderr:
                log_event(f"arecord stderr: {result.stderr}")

            # Check if recording was successful
            success = False
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                log_event(f"Output file size: {file_size} bytes")

                # Calculate expected minimum file size (duration * sample_rate * 2 bytes * 0.8 for tolerance)
                expected_min_size = int(duration * MIC_SAMPLE_RATE * 2 * 0.8)

                if file_size >= expected_min_size:
                    log_event(f"Recording successful - file size {file_size} >= expected minimum {expected_min_size}")
                    success = True
                elif file_size > 10000:  # At least 10KB
                    log_event(f"Recording partially successful - file size {file_size} (minimum would be {expected_min_size})", "WARNING")
                    # Accept partial recording if it's substantial
                    success = True
                else:
                    log_event(f"Recording failed - file too small: {file_size} bytes (expected minimum: {expected_min_size})", "ERROR")
            else:
                log_event("Output file was not created", "ERROR")

            if success:
                log_event(f"Microphone recording completed: {output_file}")
                return True

            # Analyze the error for retry decision
            error_msg = f"stdout: {result.stdout.strip()}, stderr: {result.stderr.strip()}, returncode: {result.returncode}"

            if "Device or resource busy" in result.stderr:
                log_event(f"Microphone device busy (attempt {attempt + 1}), will retry with different device", "WARNING")
            elif "No such device" in result.stderr:
                log_event(f"Microphone device disconnected during recording (attempt {attempt + 1}), will retry", "WARNING")
            elif "read error" in result.stderr:
                log_event(f"Device read error during recording (attempt {attempt + 1}), will retry", "WARNING")
            else:
                log_error(f"Microphone recording failed: {error_msg}", Exception(error_msg))
                # Still retry for unknown errors

            if attempt < max_retries - 1:  # Don't sleep on last attempt
                time.sleep(retry_delay)
                continue

        except subprocess.TimeoutExpired:
            log_error(f"Microphone recording timed out after {timeout_duration}s (attempt {attempt + 1})", Exception("Recording timeout"))
            # Kill any stuck processes
            try:
                subprocess.run(['pkill', '-9', '-f', 'arecord'], timeout=5, capture_output=True)
            except:
                pass
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
        except Exception as e:
            log_error(f"Error during microphone recording (attempt {attempt + 1})", e)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
        finally:
            update_status(recording=False)

    # All attempts failed
    log_error("Microphone recording failed after all retry attempts", Exception("Max retries exceeded"))
    return False

def mix_audio_files(master_file, mic_file, output_file, master_volume=70, mic_volume=30):
    """Mix master audio file with microphone recording using ffmpeg"""
    try:
        log_event(f"Mixing audio: {master_file} + {mic_file} -> {output_file}")
        update_status(status="mixing")

        # Calculate volume levels (0-100 to dB conversion)
        master_vol = float(master_volume)
        mic_vol = float(mic_volume)

        # Handle mute (0% = -60dB, 100% = 0dB)
        if master_vol <= 0:
            master_db = -60  # Effectively muted
        else:
            master_db = -60 + (master_vol / 100) * 60  # -60dB to 0dB

        if mic_vol <= 0:
            mic_db = -60  # Effectively muted
        else:
            mic_db = -60 + (mic_vol / 100) * 60  # -60dB to 0dB

        log_event(f"Volume levels: Master {master_vol}% ({master_db}dB), Mic {mic_vol}% ({mic_db}dB)")

        cmd = [
            "/usr/bin/ffmpeg",
            "-y",  # Overwrite output file
            "-i", master_file,
            "-i", mic_file,
            "-filter_complex",
            f"[0:a]volume={master_db}dB[master];[1:a]volume={mic_db}dB[mic];[master][mic]amix=inputs=2:duration=longest[out]",
            "-map", "[out]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            log_event(f"Audio mixing completed successfully: {output_file}")
            return True
        else:
            log_error("Audio mixing failed", Exception(f"ffmpeg error: {result.stderr}"))
            return False

    except subprocess.TimeoutExpired:
        log_error("Audio mixing timed out", Exception("Mixing timeout"))
        return False
    except Exception as e:
        log_error("Error during audio mixing", e)
        return False

def mix_audio_with_position(master_file, mic_file, output_file, start_position=0, master_volume=70, mic_volume=30, duration=30):
    """Mix master audio segment with microphone recording using ffmpeg"""
    try:
        log_event(f"Mixing audio segment: {master_file} (from {start_position}s) + {mic_file} -> {output_file}")
        update_status(status="mixing")

        # Calculate volume levels (0-100 to dB conversion)
        master_vol = float(master_volume)
        mic_vol = float(mic_volume)

        # Handle mute (0% = -60dB, 100% = 0dB)
        if master_vol <= 0:
            master_db = -60  # Effectively muted
        else:
            master_db = -60 + (master_vol / 100) * 60  # -60dB to 0dB

        if mic_vol <= 0:
            mic_db = -60  # Effectively muted
        else:
            mic_db = -60 + (mic_vol / 100) * 60  # -60dB to 0dB

        log_event(f"Volume levels: Master {master_vol}% ({master_db}dB), Mic {mic_vol}% ({mic_db}dB)")

        cmd = [
            "/usr/bin/ffmpeg",
            "-y",  # Overwrite output file
            "-ss", str(start_position),  # Start position in master file
            "-t", str(duration),     # Configurable duration
            "-i", master_file,
            "-i", mic_file,
            "-filter_complex",
            f"[0:a]volume={master_db}dB[master];[1:a]volume={mic_db}dB[mic];[master][mic]amix=inputs=2:duration=shortest[out]",
            "-map", "[out]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            log_event(f"Audio segment mixing completed successfully: {output_file}")
            return True
        else:
            log_error("Audio segment mixing failed", Exception(f"ffmpeg error: {result.stderr}"))
            return False

    except subprocess.TimeoutExpired:
        log_error("Audio segment mixing timed out", Exception("Mixing timeout"))
        return False
    except Exception as e:
        log_error("Error during audio segment mixing", e)
        return False

def cleanup_old_files(directory, max_files=10):
    """Remove old files, keeping only the newest max_files"""
    try:
        if not os.path.exists(directory):
            return

        files = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                files.append((file_path, os.path.getmtime(file_path)))

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x[1], reverse=True)

        # Remove old files
        for file_path, _ in files[max_files:]:
            try:
                os.remove(file_path)
                log_event(f"Removed old file: {os.path.basename(file_path)}")
            except Exception as e:
                log_error(f"Error removing file {file_path}", e)

    except Exception as e:
        log_error("Error during cleanup", e)

def copy_to_broadcast(mixed_file):
    """Copy mixed file to broadcast directory"""
    try:
        if not os.path.exists(BROADCAST_MEDIA_DIR):
            os.makedirs(BROADCAST_MEDIA_DIR)

        filename = os.path.basename(mixed_file)
        broadcast_file = os.path.join(BROADCAST_MEDIA_DIR, filename)

        shutil.copy2(mixed_file, broadcast_file)
        log_event(f"Copied mixed file to broadcast: {filename}")
        return broadcast_file

    except Exception as e:
        log_error("Error copying to broadcast directory", e)
        return None

def perform_mixing(config):
    """Perform the complete mixing process with sequential master file positioning"""
    try:
        # Ensure directories exist
        os.makedirs(MIXED_OUTPUT_DIR, exist_ok=True)
        os.makedirs(BROADCAST_MEDIA_DIR, exist_ok=True)

        master_files = get_master_files()
        if not master_files:
            log_event("No master audio files found", "WARNING")
            return False

        # Select master file
        master_file = None
        if config.get("master_file"):
            # Use specific file if configured
            for mf in master_files:
                if mf["filename"] == config["master_file"]:
                    master_file = mf["path"]
                    break

        if not master_file:
            # Use the newest master file
            master_file = master_files[0]["path"]

        log_event(f"Using master file: {os.path.basename(master_file)}")

        # Get master file duration and update position tracking
        master_duration = get_audio_duration(master_file)
        if master_duration == 0:
            log_event("Could not determine master file duration, using full file mixing", "WARNING")
            # Fall back to original mixing method
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mic_file = os.path.join(MIXED_OUTPUT_DIR, f"mic_recording_{timestamp}.wav")

            if not record_microphone(mic_file):
                return False

            mixed_file = os.path.join(BROADCAST_MEDIA_DIR, f"mixed_audio_{timestamp}.mp3")
            success = mix_audio_files(
                master_file, mic_file, mixed_file,
                config.get("master_volume", 70),
                config.get("mic_volume", 30)
            )
            if success:
                update_status(latest_output_file=os.path.basename(mixed_file))
            return success

        # Update master duration in status
        current_status["master_duration"] = master_duration

        # Calculate current position in master file
        current_position = current_status.get("master_position", 0)

        # If we've reached the end of the master file, reset to beginning
        if current_position >= master_duration:
            current_position = 0
            log_event(f"Master file reached end ({master_duration}s), restarting from beginning")

        log_event(f"Master file position: {current_position}s / {master_duration}s")

        # Record microphone
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mic_file = os.path.join(MIXED_OUTPUT_DIR, f"mic_recording_{timestamp}.wav")

        # Get recording duration from config
        recording_duration = int(config.get("recording_duration", 30))
        if not record_microphone(mic_file, recording_duration):
            return False

        # Mix audio with current position - save directly to broadcast media directory
        mixed_file = os.path.join(BROADCAST_MEDIA_DIR, f"mixed_audio_{timestamp}.mp3")

        if not mix_audio_with_position(
            master_file, mic_file, mixed_file, current_position,
            config.get("master_volume", 70),
            config.get("mic_volume", 30),
            recording_duration
        ):
            return False

        # Update position for next mixing (advance by recording duration)
        next_position = current_position + recording_duration
        current_status["master_position"] = next_position

        # Update status with successful mixing
        update_status(
            last_mixing=timestamp,
            mixed_files_count=current_status["mixed_files_count"] + 1,
            latest_output_file=os.path.basename(mixed_file),
            master_position=next_position,
            master_duration=master_duration,
            status="completed"
        )

        # Cleanup old files in broadcast media directory (keep only 5 newest)
        cleanup_old_files(BROADCAST_MEDIA_DIR, 25)
        # Also cleanup mixed output directory (temp files) - keep only 3 newest to prevent overflow
        cleanup_old_files(MIXED_OUTPUT_DIR, 3)

        # Remove temporary mic recording
        try:
            os.remove(mic_file)
        except:
            pass

        return True

    except Exception as e:
        log_error("Error during mixing process", e)
        current_status["error_count"] += 1
        update_status(status="error")
        return False

def main():
    """Main mixing service loop"""
    log_event("=== MIXING SERVICE STARTING ===")
    log_event(f"Process ID: {os.getpid()}")
    log_event(f"Python executable: {os.sys.executable}")
    log_event(f"Working directory: {os.getcwd()}")

    # Clean up any orphaned audio processes that might block recording
    def cleanup_orphaned_audio_processes():
        """Kill any orphaned audio processes that might be blocking the audio device"""
        try:
            import subprocess
            # Find and kill orphaned arecord processes
            result = subprocess.run(['pgrep', 'arecord'], capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        log_event(f"Killing orphaned arecord process: {pid}")
                        subprocess.run(['kill', pid], capture_output=True)

            # Also check for other audio processes that might be blocking recording
            for process in ['mpg123', 'aplay', 'paplay', 'ffplay']:
                result = subprocess.run(['pgrep', process], capture_output=True, text=True)
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            log_event(f"Killing orphaned {process} process: {pid}")
                            subprocess.run(['kill', pid], capture_output=True)
        except Exception as e:
            log_event(f"Error cleaning up orphaned processes: {e}")

    # Clean up orphaned processes before starting
    cleanup_orphaned_audio_processes()

    update_status(mode="Auto", status="initializing")

    # Ensure directories exist
    os.makedirs(MASTER_AUDIO_DIR, exist_ok=True)
    os.makedirs(MIXED_OUTPUT_DIR, exist_ok=True)
    os.makedirs(BROADCAST_MEDIA_DIR, exist_ok=True)

    last_config = None
    last_auto_mixing = 0

    try:
        while True:
            try:
                # Read current configuration
                config = read_config()

                # Log configuration changes
                if config != last_config:
                    log_event(f"Configuration updated: {config}")
                    current_status.update({
                        "mode": config.get("mode", "Auto"),
                        "master_volume": config.get("master_volume", 70),
                        "mic_volume": config.get("mic_volume", 30)
                    })
                    last_config = config.copy()

                current_time = time.time()
                mode = config.get("mode", "Auto")

                if mode == "Auto":
                    # Auto mixing mode
                    auto_interval = config.get("auto_interval", 60)

                    if current_time - last_auto_mixing >= auto_interval:
                        update_status(status="preparing")
                        if perform_mixing(config):
                            last_auto_mixing = current_time
                        time.sleep(5)  # Brief pause between auto mixes
                    else:
                        update_status(status="waiting")

                elif mode == "Once":
                    # Manual once mode
                    if current_status.get("status") != "completed":
                        update_status(status="preparing")
                        if perform_mixing(config):
                            # Switch back to Auto mode after completion
                            config["mode"] = "Auto"
                            write_config(config)

                elif mode == "Disable":
                    # Disable mode - service does nothing
                    update_status(mode="Disable", status="disabled")

                else:
                    update_status(status="idle")

                time.sleep(2)  # Main loop interval

            except Exception as e:
                log_error("Error in main service loop", e)
                time.sleep(5)

    except KeyboardInterrupt:
        log_event("=== MIXING SERVICE STOPPED BY USER ===")
    except Exception as e:
        log_error("=== MIXING SERVICE CRASHED ===", e)
    finally:
        update_status(status="stopped")
        log_event("=== MIXING SERVICE STOPPING ===")
        log_event(f"Final process ID: {os.getpid()}")
        log_event("=== MIXING SERVICE STOPPED ===")

if __name__ == "__main__":
    main()