#!/usr/bin/env python3
"""
Unified Raspberry Pi Control Panel
Consolidated Flask application with modular service management
"""

import os
import sys
import json
import time
from typing import Dict, Any
from flask import Flask, render_template, redirect, url_for, request, jsonify

# Add core modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from service_manager import ServiceManager
from config_manager import ConfigManager
from hardware_monitor import HardwareMonitor

app = Flask(__name__)

# Service definitions
SERVICES = {
    "LED Service": {
        "script": "led/lighting_menu.py",
        "icon": "fas fa-lightbulb"
    },
    "Radio Service": {
        "script": "radio/fm-radio_menu.py",
        "icon": "fas fa-radio"
    },
    "Fan Service": {
        "script": "fan/fan_mic_menu.py",
        "icon": "fas fa-fan"
    },
    "Broadcast Service": {
        "script": "broadcast/broadcast_menu.py",
        "icon": "fas fa-broadcast-tower"
    }
}

# Initialize managers
service_manager = ServiceManager("unified_app.log")
config_manager = ConfigManager("unified_config.json")
hardware_monitor = HardwareMonitor()

# App configuration
APP_MODES = {
    'dashboard': {
        'template': 'dashboard.html',
        'title': 'Enhanced Dashboard',
        'features': ['hardware_monitoring', 'service_health', 'advanced_controls']
    },
    'simple': {
        'template': 'simple_control.html', 
        'title': 'Simple Control',
        'features': ['basic_controls']
    },
    'enhanced': {
        'template': 'enhanced_control.html',
        'title': 'Code of the Sea',
        'features': ['themed_ui', 'fan_controls']
    }
}

def get_current_mode():
    """Get current application mode from config"""
    try:
        with open('app_mode.json', 'r') as f:
            return json.load(f).get('mode', 'dashboard')
    except:
        return 'dashboard'

def set_current_mode(mode: str):
    """Set application mode"""
    try:
        with open('app_mode.json', 'w') as f:
            json.dump({'mode': mode, 'updated': time.time()}, f)
        return True
    except:
        return False

def check_service_health(service_name: str) -> Dict[str, Any]:
    """Check comprehensive health of a service"""
    health = {
        'process_running': service_manager.is_service_running(service_name),
        'status_fresh': False,
        'service_healthy': False,
        'last_seen': 'Never',
        'issues': []
    }
    
    # Check status file freshness
    status = config_manager.read_service_status(service_name)
    if status and status.get('last_update'):
        try:
            last_update = status['last_update']
            # Simple freshness check - status should be updated within last 30 seconds
            health['status_fresh'] = True  # Simplified for now
            health['last_seen'] = last_update
            
            # Check service-specific health indicators
            if status.get('error_count', 0) == 0:
                health['service_healthy'] = True
            else:
                health['issues'].append(f"Service has {status['error_count']} errors")
                
        except Exception as e:
            health['issues'].append(f"Error parsing status: {str(e)}")
    else:
        health['issues'].append("No status file found")
    
    return health

def get_service_health_summary() -> Dict[str, Any]:
    """Get health summary for all services"""
    summary = {
        'healthy_count': 0,
        'total_count': len(SERVICES),
        'issues': []
    }
    
    for service_name in SERVICES:
        health = check_service_health(service_name)
        if health['process_running'] and health['service_healthy']:
            summary['healthy_count'] += 1
        else:
            summary['issues'].extend([f"{service_name}: {issue}" for issue in health['issues']])
    
    summary['health_percentage'] = (summary['healthy_count'] / summary['total_count']) * 100
    return summary

@app.route("/")
def index():
    """Main dashboard route - adapts based on current mode"""
    mode = get_current_mode()
    mode_config = APP_MODES.get(mode, APP_MODES['dashboard'])
    
    try:
        service_manager.cleanup_processes()
        
        # Prepare context based on mode features
        context = {
            'scripts': {name: info['script'] for name, info in SERVICES.items()},
            'processes': service_manager.processes,
            'configs': config_manager.get_all_configs(),
            'current_mode': mode,
            'available_modes': APP_MODES
        }
        
        if 'hardware_monitoring' in mode_config['features']:
            context['hardware_info'] = hardware_monitor.get_comprehensive_info(service_manager.processes)
            
        if 'service_health' in mode_config['features']:
            context['service_statuses'] = config_manager.get_all_service_statuses()
            context['service_health'] = {name: check_service_health(name) for name in SERVICES}
            
        if 'fan_controls' in mode_config['features']:
            # Legacy fan config for enhanced mode
            fan_config = {"mode": "off", "speed_percent": 0}
            if os.path.exists("fan_config.json"):
                try:
                    with open("fan_config.json", 'r') as f:
                        fan_config = json.load(f)
                except:
                    pass
            context['fan_config'] = fan_config
        
        service_manager.log_event(f"Dashboard loaded in {mode} mode")
        return render_template(mode_config['template'], **context)
        
    except Exception as e:
        service_manager.log_error("Error loading dashboard", e)
        return f"Error loading dashboard: {str(e)}", 500

@app.route("/mode/<mode_name>", methods=["POST"])
def change_mode(mode_name):
    """Change application mode"""
    if mode_name in APP_MODES:
        if set_current_mode(mode_name):
            service_manager.log_event(f"Switched to {mode_name} mode")
        else:
            service_manager.log_error(f"Failed to switch to {mode_name} mode")
    return redirect(url_for("index"))

@app.route("/start/<service>", methods=["POST"])
def start_service(service):
    """Start a service"""
    if service in SERVICES:
        script_path = SERVICES[service]['script']
        working_dir = os.path.dirname(script_path) or "."
        success = service_manager.start_service(service, script_path, working_dir)
        
        if not success:
            service_manager.log_error(f"Failed to start {service}")
    else:
        service_manager.log_error(f"Unknown service: {service}")
    
    return redirect(url_for("index"))

@app.route("/stop/<service>", methods=["POST"])
def stop_service(service):
    """Stop a service"""
    if service in SERVICES:
        success = service_manager.stop_service(service)
        if not success:
            service_manager.log_error(f"Failed to stop {service}")
    else:
        service_manager.log_error(f"Unknown service: {service}")
    
    return redirect(url_for("index"))

@app.route("/save/<service>", methods=["POST"])
def save_service_config(service):
    """Save service configuration"""
    if service in SERVICES:
        data = request.form.to_dict()
        success = config_manager.update_service_config(service, data)
        
        if success:
            service_manager.log_event(f"Updated config for {service}: {data}")
        else:
            service_manager.log_error(f"Failed to update config for {service}")
    else:
        service_manager.log_error(f"Unknown service: {service}")
    
    return redirect(url_for("index"))

# Legacy routes for backward compatibility
@app.route("/start_fan_service", methods=["POST"])
def start_fan_service():
    """Legacy fan service start"""
    return start_service("Fan Service")

@app.route("/stop_fan_service", methods=["POST"])
def stop_fan_service():
    """Legacy fan service stop"""
    return stop_service("Fan Service")

@app.route("/set_fan_mode", methods=["POST"])
def set_fan_mode():
    """Legacy fan mode setting"""
    mode = request.form.get("mode")
    fan_config = {"mode": mode, "speed_percent": 0}
    try:
        with open("fan_config.json", 'w') as f:
            json.dump(fan_config, f)
    except:
        pass
    return redirect(url_for("index"))

@app.route("/set_fan_speed", methods=["POST"])
def set_fan_speed():
    """Legacy fan speed setting"""
    data = request.json
    speed = int(data.get("speed", 0))
    fan_config = {"mode": "manual", "speed_percent": speed}
    try:
        with open("fan_config.json", 'w') as f:
            json.dump(fan_config, f)
        return jsonify({"status": "ok"})
    except:
        return jsonify({"status": "error"}), 500

@app.route("/start/<script>", methods=["POST"])
def start_script(script):
    """Legacy script start route"""
    # Map old script names to new service names
    script_mapping = {
        "Lighting": "LED Service",
        "Light Sensor": "LED Service",
        "FM Radio": "Radio Service"
    }
    service = script_mapping.get(script, script)
    return start_service(service)

@app.route("/stop/<script>", methods=["POST"])  
def stop_script(script):
    """Legacy script stop route"""
    script_mapping = {
        "Lighting": "LED Service", 
        "Light Sensor": "LED Service",
        "FM Radio": "Radio Service"
    }
    service = script_mapping.get(script, script)
    return stop_service(service)

@app.route("/restart_pi", methods=["POST"])
def restart_pi():
    """Restart Raspberry Pi"""
    try:
        service_manager.log_event("Initiating Raspberry Pi restart")
        service_manager.stop_all_services()
        os.system("sudo reboot")
        return "Rebooting..."
    except Exception as e:
        service_manager.log_error("Error restarting Raspberry Pi", e)
        return f"Error restarting: {str(e)}", 500

@app.route("/logs")
def view_logs():
    """Display main application logs (newest first)"""
    try:
        with open(service_manager.log_file, "r") as f:
            log_lines = f.readlines()
        
        # Logs should already be in newest-first order, but service_manager appends
        # so we need to reverse for main logs
        # Process log lines to add color styling for errors
        processed_lines = []
        for line in reversed(log_lines):  # Reverse because service_manager appends
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
        <h2>Application Logs</h2>
        <div style="margin-bottom: 10px;">
            <a href="/clear_logs" onclick="return confirm('Clear logs?')" style="background: #ef4444; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px;">Clear Logs</a>
            <a href="/" style="background: #3b82f6; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Back to Control Panel</a>
        </div>
        <div style="background: #f1f5f9; padding: 15px; border-radius: 5px; max-height: 80vh; overflow-y: auto; font-family: monospace; white-space: pre-wrap;">{logs_content}</div>
        """
    except FileNotFoundError:
        return "No logs found.<br><a href='/'>Back to Control Panel</a>"
    except Exception as e:
        return f"Error reading logs: {str(e)}<br><a href='/'>Back to Control Panel</a>"

@app.route("/service_logs/<service>")
def view_service_logs(service):
    """Display service-specific logs (newest first)"""
    service_log_files = {
        "LED Service": "led/led_log.txt",
        "Radio Service": "radio/radio_log.txt", 
        "Fan Service": "fan/fan_log.txt",
        "Broadcast Service": "broadcast/broadcast_log.txt",
    }
    
    log_file = service_log_files.get(service)
    if not log_file or not os.path.exists(log_file):
        return f"No logs found for {service}.<br><a href='/'>Back to Control Panel</a>"
    
    try:
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
            <a href="/clear_service_logs/{service}" onclick="return confirm('Clear {service} logs?')" style="background: #ef4444; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px;">Clear Logs</a>
            <a href="/" style="background: #3b82f6; color: white; padding: 5px 10px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Back to Control Panel</a>
        </div>
        <div style="background: #f1f5f9; padding: 15px; border-radius: 5px; max-height: 80vh; overflow-y: auto; font-family: monospace; white-space: pre-wrap;">{logs_content}</div>
        """
    except Exception as e:
        return f"Error reading logs for {service}: {str(e)}<br><a href='/'>Back to Control Panel</a>"

@app.route("/clear_logs")
def clear_logs():
    """Clear main application logs"""
    try:
        with open(service_manager.log_file, "w") as f:
            f.write("")
        service_manager.log_event("Logs cleared")
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error clearing logs: {str(e)}", 500

@app.route("/clear_service_logs/<service>")
def clear_service_logs(service):
    """Clear service-specific logs"""
    service_log_files = {
        "LED Service": "led/led_log.txt",
        "Radio Service": "radio/radio_log.txt",
        "Fan Service": "fan/fan_log.txt",
        "Broadcast Service": "broadcast/broadcast_log.txt",
    }
    
    log_file = service_log_files.get(service)
    if log_file and os.path.exists(log_file):
        try:
            with open(log_file, "w") as f:
                f.write("")
            service_manager.log_event(f"Cleared logs for {service}")
        except Exception as e:
            service_manager.log_error(f"Error clearing logs for {service}", e)
    
    return redirect(url_for('index'))

@app.route("/api/status")
def api_status():
    """API endpoint for system status"""
    try:
        return jsonify({
            "hardware": hardware_monitor.get_comprehensive_info(service_manager.processes),
            "services": config_manager.get_all_service_statuses(),
            "processes": {name: proc.pid for name, proc in service_manager.processes.items()},
            "health": get_service_health_summary(),
            "mode": get_current_mode()
        })
    except Exception as e:
        service_manager.log_error("Error getting API status", e)
        return jsonify({"error": str(e)}), 500

@app.route("/health/<service>")
def service_health(service):
    """Get health information for a specific service"""
    try:
        if service not in SERVICES:
            return jsonify({"error": "Unknown service"}), 404
        
        health_info = check_service_health(service)
        return jsonify(health_info)
    except Exception as e:
        service_manager.log_error(f"Error getting health for {service}", e)
        return jsonify({"error": str(e)}), 500

@app.route("/upload_broadcast_file", methods=["POST"])
def upload_broadcast_file():
    """Upload audio file to broadcast service"""
    try:
        if 'audio_file' not in request.files:
            return redirect(url_for('index'))
        
        file = request.files['audio_file']
        if file.filename == '':
            return redirect(url_for('index'))
        
        # Check file extension
        allowed_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            service_manager.log_error(f"Invalid file type: {file_ext}")
            return redirect(url_for('index'))
        
        # Ensure broadcast media directory exists
        media_dir = os.path.join('broadcast', 'media')
        os.makedirs(media_dir, exist_ok=True)
        
        # Save file
        filename = file.filename
        file_path = os.path.join(media_dir, filename)
        file.save(file_path)
        
        service_manager.log_event(f"Uploaded broadcast file: {filename}")
        return redirect(url_for('index'))
        
    except Exception as e:
        service_manager.log_error("Error uploading broadcast file", e)
        return redirect(url_for('index'))

@app.route("/delete_broadcast_file", methods=["POST"])
def delete_broadcast_file():
    """Delete audio file from broadcast service"""
    try:
        filename = request.form.get('filename')
        if not filename:
            return redirect(url_for('index'))
        
        # Security: ensure filename doesn't contain path traversal
        filename = os.path.basename(filename)
        
        file_path = os.path.join('broadcast', 'media', filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            service_manager.log_event(f"Deleted broadcast file: {filename}")
        else:
            service_manager.log_error(f"File not found for deletion: {filename}")
        
        return redirect(url_for('index'))
        
    except Exception as e:
        service_manager.log_error("Error deleting broadcast file", e)
        return redirect(url_for('index'))

@app.route("/broadcast_control/<action>", methods=["POST"])
def broadcast_control(action):
    """Control broadcast service playback (play, pause, stop, next, previous)"""
    try:
        valid_actions = ['play', 'pause', 'stop', 'next', 'previous']
        
        if action not in valid_actions:
            service_manager.log_error(f"Invalid broadcast control action: {action}")
            return redirect(url_for('index'))
        
        # Create control signal file that the broadcast service will monitor
        control_file_path = os.path.join('broadcast', 'control_signal.txt')
        
        # Write control command with timestamp
        with open(control_file_path, 'w') as f:
            f.write(f"{action.upper()}:{time.time()}")
        
        service_manager.log_event(f"Broadcast control: {action}")
        return redirect(url_for('index'))
        
    except Exception as e:
        service_manager.log_error(f"Error controlling broadcast service: {action}", e)
        return redirect(url_for('index'))

if __name__ == "__main__":
    try:
        service_manager.log_event("Unified Control Panel starting")
        print(f"Starting Raspberry Pi Control Panel")
        print(f"Available modes: {', '.join(APP_MODES.keys())}")
        print(f"Current mode: {get_current_mode()}")
        print(f"Access at: http://0.0.0.0:5000")
        
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        service_manager.log_error("Fatal error in control panel", e)
        print(f"Fatal error: {e}")
        sys.exit(1)