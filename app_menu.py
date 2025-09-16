# app_menu.py
# Enhanced Flask Web Control Panel for Raspberry Pi Services

import subprocess, os, signal, json, time, psutil, traceback, sys
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request

app = Flask(__name__)

# Paths to services (updated to use the new _menu.py versions)
SCRIPTS = {
    "LED Service": "led/lighting_menu.py",
    "Radio Service": "radio/fm-radio_menu.py", 
    "Fan Service": "fan/fan_mic_menu.py",
    "Broadcast Service": "broadcast/broadcast_menu.py",
}

# Status files for inter-service communication
STATUS_FILES = {
    "LED Service": "led/led_status.json",
    "Radio Service": "radio/radio_status.json",
    "Fan Service": "fan/fan_status.json",
    "Broadcast Service": "broadcast/broadcast_status.json",
}

# Store running processes { "service": Popen_object }
processes = {}

# Config file to store last selected options
CONFIG_FILE = "service_config.json"
LOG_FILE = "app_menu_log.txt"

# Default configs
default_configs = {
    "LED Service": {"mode": "Manual LED", "brightness": 50},
    "Radio Service": {"mode": "Fixed", "frequency": 101.1, "direction": "Up"},
    "Fan Service": {"mode": "Fixed", "speed": 50},
    "Broadcast Service": {"mode": "Loop", "volume": 50},
}

# Load saved configs with error handling
try:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            configs = json.load(f)
    else:
        configs = default_configs.copy()
except Exception as e:
    print(f"Error loading config: {e}")
    configs = default_configs.copy()

def log_event(message, level="INFO"):
    """Log events to main app log file with timestamp and level"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {level}: {message}\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}")

def log_error(message, exception=None):
    """Log errors with full traceback"""
    if exception:
        tb = traceback.format_exc()
        log_event(f"{message}\nException: {str(exception)}\nTraceback:\n{tb}", "ERROR")
    else:
        log_event(message, "ERROR")

def save_configs():
    """Save configurations with error handling"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(configs, f, indent=2)
        log_event("Configurations saved successfully")
    except Exception as e:
        log_error("Error saving configurations", e)

def read_service_status(service):
    """Read status from service status file"""
    status_file = STATUS_FILES.get(service)
    if not status_file or not os.path.exists(status_file):
        return {}
    
    try:
        with open(status_file, "r") as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Error reading status for {service}", e)
        return {}

def get_all_service_statuses():
    """Get status from all services"""
    statuses = {}
    for service in SCRIPTS.keys():
        statuses[service] = read_service_status(service)
    return statuses

def cleanup_processes():
    """Remove dead processes from dictionary and log status"""
    dead = []
    for name, proc in processes.items():
        try:
            if not psutil.pid_exists(proc.pid):
                dead.append(name)
        except Exception as e:
            log_error(f"Error checking process status for {name}", e)
            dead.append(name)
    
    for name in dead:
        processes.pop(name, None)
        log_event(f"Removed dead process: {name}")

def get_hardware_info():
    """Get comprehensive hardware information with error handling"""
    hardware_info = {
        'cpu_load': [0, 0, 0],
        'cpu_percent': 0,
        'cpu_temp': None,
        'memory': None,
        'disk': None,
        'network_io': None,
        'uptime_hours': 0,
        'uptime_minutes': 0,
        'gpio_in_use': 0
    }
    
    try:
        # CPU info
        hardware_info['cpu_load'] = psutil.getloadavg()
        hardware_info['cpu_percent'] = psutil.cpu_percent(interval=0.1)
    except Exception as e:
        log_error("Error getting CPU info", e)
    
    try:
        # Memory info
        hardware_info['memory'] = psutil.virtual_memory()
    except Exception as e:
        log_error("Error getting memory info", e)
    
    try:
        # Disk usage
        hardware_info['disk'] = psutil.disk_usage('/')
    except Exception as e:
        log_error("Error getting disk info", e)
    
    try:
        # Network info
        hardware_info['network_io'] = psutil.net_io_counters()
    except Exception as e:
        log_error("Error getting network info", e)
    
    try:
        # System uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        hardware_info['uptime_hours'] = int(uptime_seconds // 3600)
        hardware_info['uptime_minutes'] = int((uptime_seconds % 3600) // 60)
    except Exception as e:
        log_error("Error calculating uptime", e)
    
    try:
        # Read temperature from sysfs (Raspberry Pi)
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            hardware_info['cpu_temp'] = float(f.read()) / 1000.0
    except FileNotFoundError:
        log_event("CPU temperature sensor not found", "WARNING")
    except Exception as e:
        log_error("Error reading CPU temperature", e)
    
    try:
        # GPIO usage count (approximation)
        hardware_info['gpio_in_use'] = len([p for p in processes.values() if psutil.pid_exists(p.pid)])
    except Exception as e:
        log_error("Error counting GPIO usage", e)
    
    return hardware_info

@app.route("/")
def index():
    """Main dashboard route with comprehensive error handling"""
    try:
        cleanup_processes()
        hardware_info = get_hardware_info()
        service_statuses = get_all_service_statuses()
        
        # Log successful page load
        log_event("Dashboard loaded successfully")

        return render_template('dashboard.html',
                               scripts=SCRIPTS,
                               processes=processes,
                               configs=configs,
                               hardware_info=hardware_info,
                               service_statuses=service_statuses)
    except Exception as e:
        log_error("Error loading dashboard", e)
        return f"Error loading dashboard: {str(e)}", 500

@app.route("/start/<service>", methods=["POST"])
def start_service(service):
    """Start service with comprehensive error handling"""
    try:
        cleanup_processes()
        if service not in SCRIPTS:
            log_error(f"Unknown service: {service}")
            return redirect(url_for("index"))
        
        # Stop existing process if running
        if service in processes and psutil.pid_exists(processes[service].pid):
            log_event(f"Stopping existing instance of {service} before starting new one")
            try:
                os.killpg(os.getpgid(processes[service].pid), signal.SIGTERM)
                time.sleep(1)  # Give time for graceful shutdown
            except Exception as e:
                log_error(f"Error stopping existing {service} process", e)
            processes.pop(service, None)
        
        # Start new process
        try:
            # Get working directory for service
            script_dir = os.path.dirname(SCRIPTS[service])
            working_dir = script_dir if script_dir else "."
            
            proc = subprocess.Popen(
                ["python3", SCRIPTS[service]],
                preexec_fn=os.setsid,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            processes[service] = proc
            log_event(f"Started service: {service} (PID: {proc.pid})")
        except Exception as e:
            log_error(f"Error starting service {service}", e)
            
    except Exception as e:
        log_error(f"Unexpected error starting service {service}", e)
    
    return redirect(url_for("index"))

@app.route("/stop/<service>", methods=["POST"])
def stop_service(service):
    """Stop service with comprehensive error handling"""
    try:
        if service in processes:
            proc = processes[service]
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                log_event(f"Stopped service: {service}")
                
                # Wait a bit for graceful shutdown
                time.sleep(0.5)
                
                # Force kill if still running
                if psutil.pid_exists(proc.pid):
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    log_event(f"Force killed service: {service}")
                    
            except ProcessLookupError:
                log_event(f"Process for {service} already terminated")
            except Exception as e:
                log_error(f"Error stopping service {service}", e)
            
            processes.pop(service, None)
        else:
            log_event(f"Service {service} not running")
            
    except Exception as e:
        log_error(f"Unexpected error stopping service {service}", e)
    
    return redirect(url_for("index"))

@app.route("/save/<service>", methods=["POST"])
def save_service_config(service):
    """Save service configuration with comprehensive error handling"""
    try:
        data = request.form.to_dict()
        log_event(f"Saving config for {service}: {data}")
        
        # Convert numeric strings to appropriate types
        try:
            if service == "LED Service" and "brightness" in data:
                data["brightness"] = int(data["brightness"])
            elif service == "Radio Service":
                if "frequency" in data:
                    data["frequency"] = float(data["frequency"])
            elif service == "Fan Service" and "speed" in data:
                data["speed"] = int(data["speed"])
            elif service == "Broadcast Service" and "volume" in data:
                data["volume"] = int(data["volume"])
        except ValueError as e:
            log_error(f"Error converting config values for {service}", e)
            return redirect(url_for("index"))
        
        configs[service].update(data)
        save_configs()
        log_event(f"Updated config for {service}: {data}")
        
    except Exception as e:
        log_error(f"Error saving config for service {service}", e)
    
    return redirect(url_for("index"))

@app.route("/restart_pi", methods=["POST"])
def restart_pi():
    """Restart Pi with error handling"""
    try:
        log_event("Initiating Raspberry Pi restart")
        # Stop all services first
        for service in list(processes.keys()):
            try:
                stop_service(service)
            except Exception as e:
                log_error(f"Error stopping {service} before restart", e)
        
        os.system("sudo reboot")
        return "Rebooting..."
    except Exception as e:
        log_error("Error restarting Raspberry Pi", e)
        return f"Error restarting: {str(e)}", 500

@app.route("/logs")
def view_logs():
    """Display the main app log file (newest first)"""
    try:
        with open(LOG_FILE, "r") as f:
            log_lines = f.readlines()
        
        # Logs are already in newest-first order from log_event function
        # Process log lines to add color styling for errors
        processed_lines = []
        for line in log_lines:
            if 'ERROR:' in line:
                # Wrap error lines in red span
                processed_lines.append(f'<span style="color: #ef4444; font-weight: bold;">{line.rstrip()}</span>\n')
            elif 'WARNING:' in line:
                # Wrap warning lines in orange span
                processed_lines.append(f'<span style="color: #f59e0b; font-weight: bold;">{line.rstrip()}</span>\n')
            else:
                processed_lines.append(line)
        
        logs_content = ''.join(processed_lines)
        
        return f"""
        <h2>Main Control Panel Logs</h2>
        <div style="margin-bottom: 10px;">
            <a href="/clear_logs/main" onclick="return confirm('Clear main logs?')" style="background: #ef4444; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px;">Clear Logs</a>
            <a href="/" style="background: #3b82f6; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Back to Control Panel</a>
        </div>
        <div style="background: #f1f5f9; padding: 15px; border-radius: 5px; max-height: 80vh; overflow-y: auto; font-family: monospace; white-space: pre-wrap;">{logs_content}</div>
        """
    except FileNotFoundError:
        return "No logs found.<br><a href='/'>Back to Control Panel</a>"
    except Exception as e:
        log_error("Error reading logs", e)
        return f"Error reading logs: {str(e)}<br><a href='/'>Back to Control Panel</a>"

@app.route("/service_logs/<service>")
def view_service_logs(service):
    """Display service-specific log files"""
    try:
        service_log_files = {
            "LED Service": "led/led_log.txt",
            "Radio Service": "radio/radio_log.txt",
            "Fan Service": "fan/fan_log.txt",
            "Broadcast Service": "broadcast/broadcast_log.txt",
        }
        
        log_file = service_log_files.get(service)
        if not log_file or not os.path.exists(log_file):
            return f"No logs found for {service}.<br><a href='/'>Back to Control Panel</a>"
        
        with open(log_file, "r") as f:
            log_lines = f.readlines()
        
        # Logs are already in newest-first order from log_event function
        # Process log lines to add color styling for errors
        processed_lines = []
        for line in log_lines:
            if 'ERROR:' in line:
                # Wrap error lines in red span
                processed_lines.append(f'<span style="color: #ef4444; font-weight: bold;">{line.rstrip()}</span>\n')
            elif 'WARNING:' in line:
                # Wrap warning lines in orange span
                processed_lines.append(f'<span style="color: #f59e0b; font-weight: bold;">{line.rstrip()}</span>\n')
            else:
                processed_lines.append(line)
        
        logs_content = ''.join(processed_lines)
        
        return f"""
        <h2>{service} Logs</h2>
        <div style="margin-bottom: 10px;">
            <a href="/clear_logs/{service}" onclick="return confirm('Clear {service} logs?')" style="background: #ef4444; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px;">Clear Logs</a>
            <a href="/" style="background: #3b82f6; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Back to Control Panel</a>
        </div>
        <div style="background: #f1f5f9; padding: 15px; border-radius: 5px; max-height: 80vh; overflow-y: auto; font-family: monospace; white-space: pre-wrap;">{logs_content}</div>
        """
        
    except Exception as e:
        log_error(f"Error reading logs for {service}", e)
        return f"Error reading logs for {service}: {str(e)}<br><a href='/'>Back to Control Panel</a>"

@app.route("/clear_logs/<log_type>")
def clear_logs(log_type):
    """Clear log files"""
    try:
        if log_type == "main":
            with open(LOG_FILE, "w") as f:
                f.write("")
            log_event("Main logs cleared")
        else:
            service_log_files = {
                "LED Service": "led/led_log.txt",
                "Radio Service": "radio/radio_log.txt", 
                "Fan Service": "fan/fan_log.txt",
                "Broadcast Service": "broadcast/broadcast_log.txt",
            }
            log_file = service_log_files.get(log_type)
            if log_file and os.path.exists(log_file):
                with open(log_file, "w") as f:
                    f.write("")
                log_event(f"Cleared logs for {log_type}")
        
        return redirect(url_for('index'))
    except Exception as e:
        log_error(f"Error clearing logs for {log_type}", e)
        return f"Error clearing logs: {str(e)}", 500

@app.route("/api/status")
def api_status():
    """API endpoint for getting all service statuses"""
    try:
        return {
            "hardware": get_hardware_info(),
            "services": get_all_service_statuses(),
            "processes": {name: proc.pid for name, proc in processes.items() if psutil.pid_exists(proc.pid)},
            "health": get_service_health_summary()
        }
    except Exception as e:
        log_error("Error getting API status", e)
        return {"error": str(e)}, 500

@app.route("/health/<service>")
def service_health(service):
    """Get detailed health information for a specific service"""
    try:
        if service not in SCRIPTS:
            return {"error": "Unknown service"}, 404
        
        health_info = check_service_health(service)
        return health_info
    except Exception as e:
        log_error(f"Error getting health for {service}", e)
        return {"error": str(e)}, 500

if __name__ == "__main__":
    try:
        log_event("Control Panel starting")
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        log_error("Fatal error in control panel", e)
        print(f"Fatal error: {e}")