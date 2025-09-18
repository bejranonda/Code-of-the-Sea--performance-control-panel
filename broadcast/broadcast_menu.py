#!/usr/bin/env python3
# broadcast_menu.py

import os
import json
import time
import glob
import traceback
from datetime import datetime
import subprocess
import threading

# -------------------------------
# Configuration
# -------------------------------
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "service_config.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "broadcast_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "broadcast_status.json")
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
CONTROL_SIGNAL_FILE = os.path.join(os.path.dirname(__file__), "control_signal.txt")

# Supported audio file extensions
SUPPORTED_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.m4a', '.flac']

# -------------------------------
# Global Variables
# -------------------------------
current_status = {
    "mode": "Loop",
    "current_file": "",
    "playing": False,
    "paused": False,
    "playlist": [],
    "current_index": 0,
    "volume": 50,
    "last_update": None,
    "error_count": 0,
    "connection_status": "disconnected"
}
playback_process = None
playback_thread = None
stop_requested = False
pause_requested = False
next_requested = False
previous_requested = False

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
    log_to_main_log(f"Broadcast Service - {error_msg}", "ERROR")

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

def check_pulseaudio_connection():
    """Check if PulseAudio is available and responsive"""
    try:
        result = subprocess.run(['pactl', 'info'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False

def set_system_volume(volume_percent):
    """Set system volume using PulseAudio with retry logic"""
    try:
        # Ensure volume is within valid range
        volume_percent = max(0, min(100, volume_percent))

        # Check PulseAudio connection first
        if not check_pulseaudio_connection():
            log_event("PulseAudio not ready, skipping volume control", "WARNING")
            return False

        # Try to set volume with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{volume_percent}%'],
                                      capture_output=True, text=True, timeout=5)

                if result.returncode == 0:
                    log_event(f"System volume set to {volume_percent}%")
                    return True
                else:
                    if "Connection refused" in result.stderr:
                        if attempt < max_retries - 1:
                            log_event(f"PulseAudio connection refused, retrying in 1 second (attempt {attempt + 1}/{max_retries})")
                            time.sleep(1)
                            continue
                    log_error(f"Failed to set system volume: {result.stderr}")
                    return False

            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    log_event(f"Volume control timeout, retrying (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    log_error("Volume control timeout after retries")
                    return False

        return False

    except Exception as e:
        log_error("Error setting system volume", e)
        return False

def read_config():
    """Read configuration from JSON file with error handling"""
    try:
        if not os.path.exists(CONFIG_FILE):
            log_event(f"Config file not found at {CONFIG_FILE}, using defaults", "WARNING")
            return {"mode": "Loop", "volume": 50}

        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            broadcast_config = config.get("Broadcast Service", {"mode": "Loop", "volume": 50})
            return broadcast_config

    except json.JSONDecodeError as e:
        log_error("Config file JSON decode error", e)
        return {"mode": "Loop", "volume": 50}
    except Exception as e:
        log_error("Unexpected error reading config", e)
        return {"mode": "Loop", "volume": 50}

def check_control_signals():
    """Check for playback control signals (play, pause, stop, next, previous)"""
    global pause_requested, next_requested, previous_requested, stop_requested
    
    try:
        if os.path.exists(CONTROL_SIGNAL_FILE):
            # Read and remove the control signal file
            with open(CONTROL_SIGNAL_FILE, 'r') as f:
                signal_content = f.read().strip()
            
            # Remove the signal file
            os.remove(CONTROL_SIGNAL_FILE)
            
            # Parse control command
            if ':' in signal_content:
                command = signal_content.split(':')[0].upper()
                
                if command == 'PLAY':
                    log_event("Play signal received")
                    pause_requested = False
                    return 'play'
                elif command == 'PAUSE':
                    log_event("Pause signal received")
                    pause_requested = True
                    return 'pause'
                elif command == 'STOP':
                    log_event("Stop signal received")
                    stop_requested = True
                    return 'stop'
                elif command == 'NEXT':
                    log_event("Next track signal received")
                    next_requested = True
                    return 'next'
                elif command == 'PREVIOUS':
                    log_event("Previous track signal received")
                    previous_requested = True
                    return 'previous'
                    
    except Exception as e:
        log_error("Error checking control signals", e)
    
    return None

# -------------------------------
# Media Playback Functions
# -------------------------------
def get_playlist():
    """Get all supported audio files from media directory"""
    try:
        if not os.path.exists(MEDIA_DIR):
            os.makedirs(MEDIA_DIR)
            log_event(f"Created media directory: {MEDIA_DIR}")
            return []
        
        playlist = []
        for ext in SUPPORTED_EXTENSIONS:
            pattern = os.path.join(MEDIA_DIR, f"*{ext}")
            playlist.extend(glob.glob(pattern))
        
        # Sort playlist for consistent playback order
        playlist.sort()
        log_event(f"Found {len(playlist)} media files")
        return playlist
        
    except Exception as e:
        log_error("Error scanning media directory", e)
        return []

def play_file(file_path, volume=50):
    """Play a single audio file using system audio player with volume control"""
    global playback_process
    log_event(f"DEBUG: play_file called with: {os.path.basename(file_path)}, volume: {volume}%")

    try:
        if not os.path.exists(file_path):
            log_error(f"Media file not found: {file_path}")
            return False

        # Convert volume percentage (0-100) to appropriate format for different players
        # Most players use 0-1 or 0-100 scale
        volume_decimal = volume / 100.0  # For players that use 0-1 scale
        volume_percent = int(volume)     # For players that use 0-100 scale

        # Select appropriate player based on file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.mp3':
            players = [
                ['mpg123', '-a', 'pulse', file_path],  # Use pulse audio output (volume controlled at system level)
                ['ffplay', '-nodisp', '-autoexit', '-af', f'aresample=48000', file_path],  # Force 48kHz
                ['cvlc', '--intf', 'dummy', '--play-and-exit', file_path],
                ['mpg123', file_path]  # Basic fallback
            ]
        elif file_ext in ['.wav']:
            players = [
                ['aplay', '-D', 'pulse', file_path],  # Use pulse audio output (volume controlled at system level)
                ['ffplay', '-nodisp', '-autoexit', file_path],
                ['cvlc', '--intf', 'dummy', '--play-and-exit', file_path],
                ['aplay', file_path]  # Basic fallback
            ]
        elif file_ext == '.ogg':
            players = [
                ['ogg123', file_path],  # Volume controlled at system level
                ['ffplay', '-nodisp', '-autoexit', file_path],
                ['cvlc', '--intf', 'dummy', '--play-and-exit', file_path]
            ]
        else:
            # For other formats, try universal players
            players = [
                ['ffplay', '-nodisp', '-autoexit', '-af', f'aresample=48000', file_path],
                ['cvlc', '--intf', 'dummy', '--play-and-exit', file_path],
                ['mpg123', '-a', 'pulse', file_path],  # Might work for some formats
                ['aplay', '-D', 'pulse', file_path]    # Last resort with pulse
            ]
        
        for player_cmd in players:
            try:
                # Check if player exists
                which_result = subprocess.run(['which', player_cmd[0]],
                             capture_output=True, text=True)
                if which_result.returncode != 0:
                    log_event(f"Player {player_cmd[0]} not found, trying next")
                    continue

                # Start playback
                log_event(f"Starting playback: {os.path.basename(file_path)} using {' '.join(player_cmd)}")
                # Use a more robust approach
                if player_cmd[0] == 'mpg123':
                    # Create a more robust background script with pulse audio
                    script_path = f'/tmp/play_{os.getpid()}.sh'
                    cmd_str = ' '.join([f'"{arg}"' for arg in player_cmd])
                    with open(script_path, 'w') as f:
                        f.write(f'#!/bin/bash\nexport PULSE_RUNTIME_PATH=/run/user/$(id -u)/pulse\n{cmd_str} -q 2>/tmp/mpg_error_{os.getpid()} &\necho $! > /tmp/mpg_pid_{os.getpid()}\n')
                    os.chmod(script_path, 0o755)
                    
                    # Execute the script
                    subprocess.run([script_path])
                    
                    # Read the PID and create a mock process object
                    try:
                        with open(f'/tmp/mpg_pid_{os.getpid()}', 'r') as f:
                            pid = int(f.read().strip())
                        
                        # Create a simple process-like object to track the PID
                        class MockProcess:
                            def __init__(self, pid):
                                self.pid = pid
                                self._terminated = False
                            def poll(self):
                                if self._terminated:
                                    return 1  # Already terminated
                                try:
                                    os.kill(self.pid, 0)  # Check if process exists
                                    return None  # Still running
                                except OSError:
                                    self._terminated = True
                                    return 1  # Process ended
                            def terminate(self):
                                try:
                                    os.kill(self.pid, 15)
                                    self._terminated = True
                                except OSError:
                                    pass
                            def kill(self):
                                try:
                                    os.kill(self.pid, 9)
                                    self._terminated = True
                                except OSError:
                                    pass
                            def wait(self, timeout=None):
                                # Simple wait implementation
                                import time
                                start_time = time.time()
                                while self.poll() is None:
                                    if timeout and (time.time() - start_time) > timeout:
                                        # Just return instead of raising exception
                                        return -1
                                    time.sleep(0.1)
                                return 0
                                    
                        playback_process = MockProcess(pid)
                        
                    except Exception as e:
                        log_error(f"MockProcess creation failed: {e}")
                        playback_process = None
                        return False
                else:
                    # For other players, add environment variables for audio
                    env = os.environ.copy()
                    env['PULSE_RUNTIME_PATH'] = f'/run/user/{os.getuid()}/pulse'
                    env['DISPLAY'] = ':0'  # For ffplay

                    playback_process = subprocess.Popen(player_cmd,
                                                      stdout=subprocess.DEVNULL,
                                                      stderr=subprocess.PIPE,
                                                      env=env)

                    # Give it a moment to start and check for immediate errors
                    time.sleep(0.5)
                    if playback_process.poll() is not None:
                        # Process exited immediately, check for errors
                        stderr_output = playback_process.stderr.read().decode() if playback_process.stderr else 'No error info'
                        log_event(f"Player {player_cmd[0]} failed immediately: {stderr_output.strip()}", "WARNING")
                        continue
                
                update_status(current_file=os.path.basename(file_path), playing=True)
                return True
                
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                log_event(f"Error testing {player_cmd[0]}: {str(e)}", "WARNING")
                continue
            except Exception as e:
                log_event(f"Unexpected error with {player_cmd[0]}: {str(e)}", "WARNING")
                continue
        
        log_error(f"No suitable audio player found for: {file_path}")
        return False
        
    except Exception as e:
        log_error(f"Error playing file {file_path}", e)
        return False

def stop_playback():
    """Stop current playback with improved process management"""
    global playback_process
    
    try:
        # Don't set stop_requested=True here - that exits the entire broadcast loop
        # This function should only stop the current audio playback
        
        if playback_process and playback_process.poll() is None:
            try:
                # First try graceful termination
                playback_process.terminate()
                
                # Wait up to 2 seconds for graceful shutdown
                result = playback_process.wait(timeout=2)
                if result == -1:
                    # Timeout occurred, force kill
                    playback_process.kill()
                    result2 = playback_process.wait(timeout=1)
                    if result2 == -1:
                        log_error("Failed to stop playback process")
                    else:
                        log_event("Playback force stopped")
                else:
                    log_event("Playback stopped gracefully")
                        
            except Exception as e:
                log_error("Error terminating playback process", e)
        
        update_status(playing=False, current_file="")
        playback_process = None
        
    except Exception as e:
        log_error("Error stopping playback", e)

def broadcast_loop():
    """Simplified and more robust broadcast loop"""
    global current_status, stop_requested, pause_requested, next_requested, previous_requested, playback_process
    
    current_index = 0
    playlist = []
    last_playlist_check = 0
    
    log_event("Broadcast loop starting")
    
    # Auto-start playing when service starts
    auto_start = True
    
    while not stop_requested:
        try:
            # Check for control signals
            control = check_control_signals()
            
            if control == 'stop':
                stop_playback()
                pause_requested = False
                current_index = 0
                update_status(playing=False, paused=False, current_file="")
                log_event("Playback stopped")
                
            elif control == 'pause':
                stop_playback()
                pause_requested = True
                update_status(playing=False, paused=True)
                log_event("Playback paused")
                
            elif control == 'play':
                pause_requested = False
                auto_start = False  # Clear auto-start flag
                log_event("Play requested")
                
            elif control == 'next':
                stop_playback()
                if playlist:
                    current_index = (current_index + 1) % len(playlist)
                    log_event(f"Next track: {current_index}")
                pause_requested = False
                
            elif control == 'previous':
                stop_playback()
                if playlist:
                    current_index = (current_index - 1) % len(playlist)
                    log_event(f"Previous track: {current_index}")
                pause_requested = False
            
            # Get and update playlist (only every 10 seconds to reduce log flooding)
            current_time = time.time()
            if current_time - last_playlist_check >= 10.0:
                old_playlist = playlist
                playlist = get_playlist()
                last_playlist_check = current_time

                # Check if playlist has changed and reset index if needed
                if old_playlist != playlist:
                    log_event(f"Playlist changed - resetting current index from {current_index} to 0")
                    current_index = 0

                # Update status with playlist
                if playlist:
                    playlist_names = [os.path.basename(f) for f in playlist]
                    update_status(playlist=playlist_names)

            # Read volume configuration
            config = read_config()
            volume = config.get("volume", 50)

            # Update system volume if it's different from current status
            if current_status.get("volume") != volume:
                log_event(f"Volume changed from {current_status.get('volume')} to {volume}, updating system volume")
                set_system_volume(volume)

            # Update status with current volume
            update_status(volume=volume)
            
            if not playlist:
                update_status(playlist=[], playing=False, paused=False, current_file="")
                time.sleep(1)
                continue
            
            # Validate current index
            if current_index >= len(playlist):
                current_index = 0
            elif current_index < 0:
                current_index = len(playlist) - 1
            
            # Update current file in status
            current_file = os.path.basename(playlist[current_index])
            update_status(current_index=current_index, current_file=current_file)
            
            # Handle playback state
            if pause_requested:
                update_status(playing=False, paused=True)
                time.sleep(0.5)
                continue
                
            # Auto-start playing on first run
            if auto_start and playlist:
                auto_start = False
                log_event("Auto-starting playback")
                # Force start playing the first track
            
            # Check if still playing current track
            if playback_process and playback_process.poll() is None:
                # Still playing
                update_status(playing=True, paused=False)
                time.sleep(0.5)
                continue
            
            # Check if process died unexpectedly  
            if playback_process and playback_process.poll() is not None:
                log_event(f"Playback process ended for {current_file}, trying next track")
                # Move to next track when current one ends
                current_index = (current_index + 1) % len(playlist)
                log_event(f"DEBUG: Moving to next track, new index: {current_index}")
                playback_process = None
            
            # Not playing, start next track
            log_event(f"DEBUG: Checking if should play - playlist={len(playlist) if playlist else 0}, current_index={current_index}, playback_process={playback_process is not None}")
            if playlist and current_index < len(playlist):
                file_path = playlist[current_index]

                # Double-check file exists before trying to play
                if not os.path.exists(file_path):
                    log_error(f"File no longer exists: {os.path.basename(file_path)}, refreshing playlist")
                    playlist = get_playlist()
                    current_index = 0
                    continue

                log_event(f"DEBUG: About to play file: {os.path.basename(file_path)}")
                # Try to play the file, but don't crash if it fails
                try:
                    if play_file(file_path, volume):
                        update_status(playing=True, paused=False, current_file=os.path.basename(file_path))
                        log_event(f"Playing: {os.path.basename(file_path)} at {volume}% volume")
                        # Give the process a moment to initialize
                        time.sleep(1.0)
                        
                        # Double-check if process is still running after initialization
                        if playback_process and playback_process.poll() is not None:
                            log_event(f"File {os.path.basename(file_path)} failed to play continuously, trying next")
                            current_index = (current_index + 1) % len(playlist)
                            playback_process = None
                            continue
                    else:
                        # Failed to start, skip to next
                        log_error(f"Failed to start playing {os.path.basename(file_path)}, trying next")
                        current_index = (current_index + 1) % len(playlist)
                        
                except Exception as e:
                    log_error(f"Error playing {os.path.basename(file_path)}", e)
                    current_index = (current_index + 1) % len(playlist)
            else:
                # No playlist, wait
                update_status(playing=False, paused=False, current_file="")
                time.sleep(1)
            
            # Short sleep before next iteration
            time.sleep(0.5)
            
        except Exception as e:
            log_error(f"ERROR in broadcast loop: {e}")
            log_event(f"DEBUG: Exception details: {traceback.format_exc()}")
            log_event(f"DEBUG: stop_requested={stop_requested} after exception")
            time.sleep(1)
    
    # Cleanup on exit
    log_event(f"DEBUG: Loop exiting - stop_requested={stop_requested}")
    stop_playback()
    update_status(playing=False, paused=False, current_file="")
    log_event("Broadcast loop ended")

# -------------------------------
# Main Service Function
# -------------------------------
def main():
    """Main service loop"""
    global playback_thread, stop_requested, pause_requested, next_requested, previous_requested
    
    log_event("Broadcast service starting")
    update_status(mode="Initializing", connection_status="connecting")
    
    # Initialize control flags
    stop_requested = False
    pause_requested = False
    next_requested = False
    previous_requested = False
    
    # Create media directory if it doesn't exist
    try:
        if not os.path.exists(MEDIA_DIR):
            os.makedirs(MEDIA_DIR)
            log_event(f"Created media directory: {MEDIA_DIR}")
    except Exception as e:
        log_error("Failed to create media directory", e)
        return
    
    # Check for media files and ensure initial playlist is loaded
    playlist = get_playlist()
    if not playlist:
        log_event("No media files found in media directory", "WARNING")
        log_event(f"Please add audio files to: {MEDIA_DIR}")
    else:
        log_event(f"Initial playlist loaded with {len(playlist)} files")

    # Set initial system volume based on config
    config = read_config()
    initial_volume = config.get("volume", 50)
    log_event(f"Setting initial system volume to {initial_volume}%")
    set_system_volume(initial_volume)

    update_status(connection_status="connected", volume=initial_volume)
    
    try:
        # Start broadcast loop in background thread
        stop_requested = False
        playback_thread = threading.Thread(target=broadcast_loop, daemon=True)
        playback_thread.start()
        log_event("Broadcast loop started")
        
        # Main monitoring loop with broadcast thread monitoring
        last_config_check = 0
        while True:
            try:
                # Only read config every 30 seconds
                current_time = time.time()
                if current_time - last_config_check >= 30:
                    config = read_config()
                    mode = config.get("mode", "Loop")
                    update_status(mode=mode)
                    last_config_check = current_time
                
                # Check if broadcast thread is still alive, restart if needed
                if not playback_thread.is_alive() and not stop_requested:
                    log_event("Broadcast thread died, restarting...", "WARNING")
                    stop_requested = False
                    # Reset all control flags
                    pause_requested = False
                    next_requested = False
                    previous_requested = False
                    # Create new thread
                    playback_thread = threading.Thread(target=broadcast_loop, daemon=True)
                    playback_thread.start()
                    log_event("Broadcast loop restarted")
                    # Give it a moment to start
                    time.sleep(1)
                
                # Sleep longer to reduce CPU usage
                time.sleep(5)
                
            except Exception as e:
                log_error("Error in main monitoring loop", e)
                time.sleep(5)
                
    except KeyboardInterrupt:
        log_event("Broadcast service stopped by user")
    except Exception as e:
        log_error("Unexpected error in main", e)
    finally:
        stop_requested = True
        stop_playback()
        
        if playback_thread and playback_thread.is_alive():
            playback_thread.join(timeout=5)
        
        update_status(connection_status="disconnected", playing=False)
        log_event("Broadcast service stopped")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error("Fatal error in broadcast service", e)
        print(f"Fatal error: {e}")