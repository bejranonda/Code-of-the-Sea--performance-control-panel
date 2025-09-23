import subprocess
import os
import signal
import json
import time
import psutil
import traceback
from datetime import datetime
from typing import Dict, Any, Optional


class ServiceManager:
    """Unified service management for all Raspberry Pi services"""
    
    def __init__(self, log_file: str = "service_manager.log"):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.log_file = log_file
        
    def log_event(self, message: str, level: str = "INFO"):
        """Log events with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.log_file, "a") as f:
                f.write(f"[{timestamp}] {level}: {message}\n")
        except Exception as e:
            print(f"Failed to write to log file: {e}")
    
    def log_error(self, message: str, exception: Exception = None):
        """Log errors with traceback"""
        if exception:
            tb = traceback.format_exc()
            self.log_event(f"{message}\nException: {str(exception)}\nTraceback:\n{tb}", "ERROR")
        else:
            self.log_event(message, "ERROR")
    
    def cleanup_processes(self):
        """Remove dead processes from tracking"""
        dead = []
        for name, proc in self.processes.items():
            try:
                # Check if process exists and is not zombie
                if not psutil.pid_exists(proc.pid):
                    dead.append(name)
                else:
                    # Check if process is zombie
                    try:
                        p = psutil.Process(proc.pid)
                        if p.status() == psutil.STATUS_ZOMBIE:
                            dead.append(name)
                            self.log_event(f"Found zombie process for {name}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        dead.append(name)
            except Exception as e:
                self.log_error(f"Error checking process status for {name}", e)
                dead.append(name)
        
        for name in dead:
            self.processes.pop(name, None)
            self.log_event(f"Removed dead/zombie process: {name}")
    
    def start_service(self, name: str, script_path: str, working_dir: str = None) -> bool:
        """Start a service with comprehensive error handling"""
        try:
            self.cleanup_processes()

            # For LED Service, use the management script instead of direct Python execution
            if name == "LED Service":
                return self._start_led_service_via_script()

            # Stop any existing instance of this service before starting
            if name in self.processes and psutil.pid_exists(self.processes[name].pid):
                self.log_event(f"Stopping existing instance of {name} before starting new one")
                self.stop_service(name)
                # Give some time for the service to stop cleanly
                time.sleep(1)

            # Also kill any other instances of the same script (prevents conflicts with other unified apps)
            script_name = os.path.basename(script_path)
            try:
                existing_pids = subprocess.run(['pgrep', '-f', script_name], capture_output=True, text=True)
                if existing_pids.returncode == 0 and existing_pids.stdout.strip():
                    pids = existing_pids.stdout.strip().split('\n')
                    self.log_event(f"Found existing instances of {script_name}: {pids}")
                    subprocess.run(['pkill', '-f', script_name], capture_output=True)
                    time.sleep(1)
            except Exception as e:
                self.log_event(f"Error checking for existing {script_name} processes: {e}")

            # Set working directory
            if not working_dir:
                working_dir = os.path.dirname(script_path) or "."

            self.log_event(f"Script path: {script_path}, Working dir: {working_dir}, Full path: {os.path.abspath(working_dir)}")

            # Check if virtual environment should be used
            venv_python = self._get_venv_python()

            # Use absolute path for script to avoid path resolution issues
            abs_script_path = os.path.abspath(script_path)

            if venv_python:
                cmd = [venv_python, abs_script_path]
                self.log_event(f"Using virtual environment: {venv_python}")
            else:
                cmd = ["python3", abs_script_path]

            # All services redirect stdout/stderr to null to avoid broken pipe errors
            proc = subprocess.Popen(
                cmd,
                preexec_fn=os.setsid,
                cwd=working_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            
            self.processes[name] = proc
            self.log_event(f"Started service: {name} (PID: {proc.pid})")
            
            # For LED service debugging, capture initial output
            if name == "LED Service" and hasattr(proc, 'stdout') and proc.stdout is not None:
                import threading
                
                def capture_output():
                    time.sleep(0.5)  # Give process time to start
                    try:
                        if proc.poll() is None:  # Process still running
                            output = proc.stdout.read(1000)  # Read first 1000 chars
                            if output:
                                self.log_event(f"LED Service initial output: {output[:500]}")
                        else:
                            # Process already exited
                            returncode = proc.poll()
                            self.log_event(f"LED Service exited immediately with code: {returncode}")
                    except Exception as e:
                        self.log_error(f"Error capturing LED service output", e)
                
                thread = threading.Thread(target=capture_output, daemon=True)
                thread.start()
            
            return True
            
        except Exception as e:
            self.log_error(f"Error starting service {name}", e)
            return False
    
    def _get_venv_python(self) -> str:
        """Find virtual environment Python executable"""
        # Check common venv locations
        venv_paths = [
            "venv/bin/python",
            "venv/bin/python3",
            "../venv/bin/python", 
            "../venv/bin/python3",
            "/home/payas/venv/bin/python",
            "/home/payas/venv/bin/python3",
            "env/bin/python",
            "env/bin/python3"
        ]
        
        for venv_path in venv_paths:
            full_path = os.path.abspath(venv_path)
            if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                return full_path
        
        return None

    def _start_led_service_via_script(self) -> bool:
        """Start LED service using the management script"""
        try:
            script_path = "/home/payas/cos/scripts/manage_led_service.sh"
            result = subprocess.run([script_path, "start"], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_event("LED service started successfully via management script")
                # Don't track the process in self.processes since it's managed by the script
                return True
            else:
                self.log_error(f"LED service start script failed: {result.stderr}")
                return False

        except Exception as e:
            self.log_error(f"Error starting LED service via script", e)
            return False

    def _stop_led_service_via_script(self) -> bool:
        """Stop LED service using the management script"""
        try:
            script_path = "/home/payas/cos/scripts/manage_led_service.sh"
            result = subprocess.run([script_path, "stop"], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_event("LED service stopped successfully via management script")
                return True
            else:
                self.log_error(f"LED service stop script failed: {result.stderr}")
                return False

        except Exception as e:
            self.log_error(f"Error stopping LED service via script", e)
            return False

    def stop_service(self, name: str) -> bool:
        """Stop a service with comprehensive error handling"""
        try:
            # For LED Service, use the management script
            if name == "LED Service":
                return self._stop_led_service_via_script()

            if name not in self.processes:
                self.log_event(f"Service {name} not running")
                return True

            proc = self.processes[name]
            try:
                # Get our own process group to avoid killing ourselves
                our_pgid = os.getpgid(os.getpid())
                target_pgid = os.getpgid(proc.pid)

                # Safety check: Don't kill our own process group
                if target_pgid == our_pgid:
                    self.log_event(f"WARNING: {name} is in same process group as dashboard - using direct process kill")
                    # Kill only the specific process, not the whole group
                    proc.terminate()
                    time.sleep(0.5)
                    if psutil.pid_exists(proc.pid):
                        proc.kill()
                        self.log_event(f"Force killed process for {name}")
                else:
                    # Graceful shutdown of process group
                    os.killpg(target_pgid, signal.SIGTERM)
                    self.log_event(f"Stopped service: {name}")

                    # Wait for graceful shutdown
                    time.sleep(0.5)

                    # Force kill if still running
                    if psutil.pid_exists(proc.pid):
                        os.killpg(target_pgid, signal.SIGKILL)
                        self.log_event(f"Force killed service: {name}")

            except ProcessLookupError:
                self.log_event(f"Process for {name} already terminated")
            except Exception as e:
                self.log_error(f"Error stopping service {name}", e)

            self.processes.pop(name, None)
            return True

        except Exception as e:
            self.log_error(f"Unexpected error stopping service {name}", e)
            return False
    
    def is_service_running(self, name: str) -> bool:
        """Check if a service is currently running"""
        # First check if we have the process tracked
        if name in self.processes:
            try:
                if not psutil.pid_exists(self.processes[name].pid):
                    # Process died, remove from tracking
                    del self.processes[name]
                    return False
                # Check if process is not zombie
                p = psutil.Process(self.processes[name].pid)
                if p.status() == psutil.STATUS_ZOMBIE:
                    del self.processes[name]
                    return False
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                # Process died, remove from tracking
                if name in self.processes:
                    del self.processes[name]
                return False

        # If not tracked, check if process exists by looking for running processes
        return self._find_existing_service(name)

    def _find_existing_service(self, name: str) -> bool:
        """Find if service is running by checking PID files first, then process search"""
        try:
            # First check PID files (more reliable for shell-script managed services)
            if self._check_service_pid_file(name):
                return True

            # Fall back to process detection
            # Define script mappings for services
            script_patterns = {
                "LED Service": ["lighting_menu.py", "lighting.py"],
                "Radio Service": ["fm-radio_menu.py", "fm-radio.py"],
                "Fan Service": ["fan_mic_menu.py", "fan.py"],
                "Broadcast Service": ["broadcast_menu.py", "broadcast.py"],
                "Mixing Service": ["mixing_menu.py", "mixing.py"]
            }

            if name not in script_patterns:
                return False

            patterns = script_patterns[name]

            # Search through all Python processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] in ['python', 'python3']:
                        cmdline = proc.info['cmdline']
                        if cmdline and len(cmdline) > 1:
                            # Check if any of our script patterns match the command line
                            for pattern in patterns:
                                if any(pattern in arg for arg in cmdline):
                                    # Found a matching process - create a mock Popen object for tracking
                                    mock_process = type('MockProcess', (), {'pid': proc.info['pid']})()
                                    self.processes[name] = mock_process
                                    self.log_event(f"Found existing {name} process (PID: {proc.info['pid']})")
                                    return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
                    continue

            return False

        except Exception as e:
            self.log_error(f"Error finding existing service {name}", e)
            return False

    def _check_service_pid_file(self, name: str) -> bool:
        """Check if service is running by examining PID files from shell scripts"""
        try:
            # Map service names to PID file names
            service_to_pidfile = {
                "LED Service": "/tmp/led_service.pid",
                "Radio Service": "/tmp/radio_service.pid",
                "Fan Service": "/tmp/fan_service.pid",
                "Broadcast Service": "/tmp/broadcast_service.pid",
                "Mixing Service": "/tmp/mixing_service.pid"
            }

            pid_file = service_to_pidfile.get(name)
            if not pid_file or not os.path.exists(pid_file):
                return False

            # Read PID from file
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())

            # Check if process with this PID exists and is not zombie
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    if proc.status() != psutil.STATUS_ZOMBIE:
                        # Create mock process object for tracking
                        mock_process = type('MockProcess', (), {'pid': pid})()
                        self.processes[name] = mock_process
                        self.log_event(f"Found {name} via PID file (PID: {pid})")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return False

        except Exception as e:
            self.log_error(f"Error checking PID file for {name}", e)
            return False

    def get_service_pid(self, name: str) -> Optional[int]:
        """Get PID of running service"""
        if name in self.processes and self.is_service_running(name):
            return self.processes[name].pid
        return None
    
    def get_all_services_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tracked services"""
        self.cleanup_processes()
        status = {}
        
        for name, proc in self.processes.items():
            try:
                is_running = psutil.pid_exists(proc.pid)
                status[name] = {
                    'running': is_running,
                    'pid': proc.pid if is_running else None,
                    'started': getattr(proc, 'start_time', None)
                }
            except Exception as e:
                self.log_error(f"Error getting status for {name}", e)
                status[name] = {'running': False, 'pid': None, 'error': str(e)}
        
        return status
    
    def stop_all_services(self):
        """Stop all running services"""
        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)