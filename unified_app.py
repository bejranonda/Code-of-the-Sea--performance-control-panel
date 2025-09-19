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
from flask import Flask, render_template, redirect, url_for, request, jsonify, send_from_directory

# Add core modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from service_manager import ServiceManager
from config_manager import ConfigManager
from hardware_monitor import HardwareMonitor
from service_persistence import ServicePersistenceManager
from dashboard_state import DashboardStateManager
from metrics_recorder import get_metrics_recorder

# Import version information
try:
    from version_info import get_version
    APP_VERSION = get_version()
except ImportError:
    APP_VERSION = "2.1.0"

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
    },
    "Mixing Service": {
        "script": "mixing/mixing_menu.py",
        "icon": "fas fa-music"
    }
}

# Initialize managers
service_manager = ServiceManager("unified_app.log")
config_manager = ConfigManager("unified_config.json")
hardware_monitor = HardwareMonitor()
persistence_manager = ServicePersistenceManager()
dashboard_state = DashboardStateManager()

# Initialize exhibition watchdog
try:
    from core.exhibition_watchdog import get_watchdog, start_watchdog
    exhibition_watchdog = start_watchdog()
    print("✅ Exhibition watchdog initialized successfully")
except Exception as e:
    print(f"⚠️  Exhibition watchdog failed to start: {e}")
    exhibition_watchdog = None

# Initialize metrics recording
try:
    metrics_recorder = get_metrics_recorder()
    metrics_recorder.start_recording()
    print("✅ Metrics recording initialized successfully (5-minute interval)")
except Exception as e:
    print(f"⚠️  Metrics recording failed to start: {e}")

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
    """Get current application mode from dashboard state"""
    return dashboard_state.get_mode()

def set_current_mode(mode: str):
    """Set application mode"""
    return dashboard_state.save_mode(mode)

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

def get_wifi_status():
    """Get current WiFi status from monitoring system"""
    try:
        # First try new network status file
        network_status_file = os.path.join('network', 'network_status.json')
        if os.path.exists(network_status_file):
            with open(network_status_file, 'r') as f:
                status = json.load(f)
                return status

        # Fallback to old wifi status file
        wifi_status_file = os.path.join('network', 'wifi_status.json')
        if os.path.exists(wifi_status_file):
            with open(wifi_status_file, 'r') as f:
                return json.load(f)

        return {"connected": False, "message": "Network monitor not running"}
    except Exception as e:
        return {"connected": False, "error": str(e)}

@app.route("/")
def index():
    """Main dashboard route - adapts based on current mode"""
    mode = get_current_mode()
    mode_config = APP_MODES.get(mode, APP_MODES['dashboard'])
    
    try:
        service_manager.cleanup_processes()

        # Force refresh of all service statuses (checks PID files and processes)
        for service_name in SERVICES.keys():
            try:
                # Small delay to ensure PID files are readable
                time.sleep(0.1)
                is_running = service_manager.is_service_running(service_name)
                service_manager.log_event(f"Dashboard refresh: {service_name} = {is_running}")
            except Exception as e:
                service_manager.log_error(f"Error refreshing {service_name} status", e)

        # Prepare context based on mode features
        context = {
            'scripts': {name: info['script'] for name, info in SERVICES.items()},
            'processes': service_manager.processes,
            'configs': config_manager.get_all_configs(),
            'current_mode': mode,
            'available_modes': APP_MODES,
            'app_version': APP_VERSION
        }
        
        if 'hardware_monitoring' in mode_config['features']:
            context['hardware_info'] = hardware_monitor.get_comprehensive_info(service_manager.processes)
            
        if 'service_health' in mode_config['features']:
            context['service_statuses'] = config_manager.get_all_service_statuses()
            context['service_health'] = {name: check_service_health(name) for name in SERVICES}
            context['wifi_status'] = get_wifi_status()
            
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
        # Log the start request
        service_manager.log_event(f"User requested START for {service} via dashboard")
        persistence_manager.log_service_event(service, "START_REQUESTED", "User clicked START button in dashboard")

        script_path = SERVICES[service]['script']
        working_dir = os.path.dirname(script_path) or "."
        success = service_manager.start_service(service, script_path, working_dir)

        if not success:
            # Log failed manual start
            persistence_manager.log_service_event(service, "MANUAL_START_FAILED", "User clicked START button but service failed to start", False)
            service_manager.log_error(f"Failed to start {service}")
        else:
            # Log successful manual start
            persistence_manager.log_service_event(service, "MANUAL_STARTED", "User clicked START button in dashboard - service started successfully")

            # Mark service as manually started (remove from stopped list)
            try:
                persistence_manager.mark_service_manually_started(service)
                service_manager.log_event(f"Marked {service} as manually started")
            except Exception as e:
                service_manager.log_error(f"Failed to update manual start state for {service}", e)

            # Update persistent service state after successful start
            try:
                persistence_manager.update_running_services()
            except Exception as e:
                service_manager.log_error(f"Failed to update service state after starting {service}", e)
    else:
        service_manager.log_error(f"Unknown service: {service}")
        persistence_manager.log_service_event(service, "INVALID_SERVICE", f"Unknown service requested: {service}", False)

    return redirect(url_for("index"))

@app.route("/stop/<service>", methods=["POST"])
def stop_service(service):
    """Stop a service"""
    if service in SERVICES:
        # Log the stop request
        service_manager.log_event(f"User requested STOP for {service} via dashboard")
        persistence_manager.log_service_event(service, "STOP_REQUESTED", "User clicked STOP button in dashboard")

        success = service_manager.stop_service(service)
        if not success:
            # Log failed manual stop
            persistence_manager.log_service_event(service, "MANUAL_STOP_FAILED", "User clicked STOP button but service failed to stop", False)
            service_manager.log_error(f"Failed to stop {service}")
        else:
            # Log successful manual stop
            persistence_manager.log_service_event(service, "MANUAL_STOPPED", "User clicked STOP button in dashboard - service stopped successfully")

            # Mark service as manually stopped (prevent auto-restart)
            try:
                persistence_manager.mark_service_manually_stopped(service)
                service_manager.log_event(f"Marked {service} as manually stopped")
            except Exception as e:
                service_manager.log_error(f"Failed to update manual stop state for {service}", e)

            # Update persistent service state after successful stop
            try:
                persistence_manager.update_running_services()
            except Exception as e:
                service_manager.log_error(f"Failed to update service state after stopping {service}", e)
    else:
        service_manager.log_error(f"Unknown service: {service}")
        persistence_manager.log_service_event(service, "INVALID_SERVICE", f"Unknown service stop requested: {service}", False)

    return redirect(url_for("index"))

@app.route("/save/<service>", methods=["POST"])
def save_service_config(service):
    """Save service configuration"""
    if service in SERVICES:
        data = request.form.to_dict()
        success = config_manager.update_service_config(service, data)

        if success:
            service_manager.log_event(f"Updated config for {service}: {data}")
            # Also save to dashboard state for persistence
            try:
                dashboard_state.save_service_config(service, data)
            except Exception as e:
                service_manager.log_error(f"Failed to save {service} config to dashboard state", e)
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

        # Use subprocess for more reliable reboot execution
        import subprocess
        import time

        # Log the restart attempt
        service_manager.log_event("Executing system reboot command")

        # Give services time to stop
        time.sleep(2)

        # Create reboot flag and try multiple reboot methods
        import os
        from datetime import datetime

        try:
            service_manager.log_event("Reboot requested via web interface - creating reboot flag")

            # Create reboot flag file
            with open("/tmp/reboot_now", "w") as f:
                f.write(f"REBOOT\n{datetime.now().isoformat()}\n")

            # Try the most direct approach - immediate reboot
            try:
                # This should work if sudo permissions are properly configured
                os.execl("/usr/bin/sudo", "sudo", "/sbin/reboot")
            except Exception:
                # If exec fails, try system call
                result = os.system("sudo /sbin/reboot")
                if result == 0:
                    return "Rebooting now..."

            # If direct methods fail, return message about flag file
            return "Reboot flag created - system should reboot shortly..."

        except Exception as e:
            service_manager.log_error(f"Failed to initiate reboot: {e}")
            return f"Failed to request reboot: {str(e)}", 500

    except subprocess.TimeoutExpired:
        # Timeout is expected for reboot command
        service_manager.log_event("Reboot command timeout (expected)")
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
        "Mixing Service": "mixing/mixing_log.txt",
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

@app.route("/exhibition/health")
def exhibition_health():
    """Exhibition health endpoint for monitoring"""
    try:
        if exhibition_watchdog:
            # Get current system health
            health = exhibition_watchdog.get_system_health()
            
            # Get network stability info
            network_stability = exhibition_watchdog.monitor_network_stability()
            
            # Get hardware health
            hardware_healthy = exhibition_watchdog.check_hardware_health()
            
            # Get resource intensive processes
            resource_processes = exhibition_watchdog.get_resource_intensive_processes()
            
            response_data = {
                'status': 'healthy' if health.services_healthy and health.network_connected else 'degraded',
                'timestamp': health.timestamp,
                'system': {
                    'cpu_percent': health.cpu_percent,
                    'memory_percent': health.memory_percent,
                    'disk_percent': health.disk_percent,
                    'cpu_temperature': health.cpu_temperature,
                    'uptime_hours': health.uptime_hours
                },
                'services': {
                    'main_service_healthy': health.services_healthy,
                    'error_count': health.error_count,
                    'last_restart': health.last_restart
                },
                'network': {
                    'connected': health.network_connected,
                    'stability': network_stability,
                    'wifi_signal': exhibition_watchdog.get_wifi_signal_strength(),
                    'interfaces': exhibition_watchdog.get_network_interface_status(),
                    'detailed_wifi_status': get_wifi_status()
                },
                'hardware': {
                    'healthy': hardware_healthy,
                    'i2c_devices_ok': exhibition_watchdog.test_i2c_devices(),
                    'gpio_devices_ok': exhibition_watchdog.test_gpio_devices()
                },
                'performance': {
                    'resource_intensive_processes': resource_processes[:5],  # Top 5
                    'memory_leak_detected': exhibition_watchdog.check_memory_leaks()
                },
                'watchdog': {
                    'restart_count': exhibition_watchdog.restart_count,
                    'history_length': len(exhibition_watchdog.health_history)
                }
            }
            
            return jsonify(response_data)
        else:
            return jsonify({
                'status': 'error',
                'message': 'Exhibition watchdog not available',
                'timestamp': time.time()
            }), 503
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

@app.route("/exhibition/dashboard")
def exhibition_dashboard():
    """Exhibition monitoring dashboard with charts"""
    try:
        # Get metrics recorder
        metrics_recorder = get_metrics_recorder()

        # Get time range from query parameter (default 24 hours)
        hours = int(request.args.get('hours', 24))

        # Get chart data
        chart_data = metrics_recorder.get_chart_data(hours)

        # Get current metrics (latest record)
        records = metrics_recorder.get_records(hours=1)  # Last hour
        current_stats = records[-1] if records else {
            'lux_value': 0,
            'cpu_usage': 0,
            'cpu_temperature': 0,
            'disk_usage': 0
        }

        # Get system stats
        stats = metrics_recorder.get_stats()

        return render_template('exhibition_monitor.html',
                             chart_data=json.dumps(chart_data),
                             current_stats=current_stats,
                             stats=stats)

    except Exception as e:
        return f"Error loading exhibition dashboard: {str(e)}", 500

@app.route("/system/health")
def system_health():
    """System health monitoring page"""
    return render_template('system_health.html')

@app.route("/clear_service_logs/<service>")
def clear_service_logs(service):
    """Clear service-specific logs"""
    service_log_files = {
        "LED Service": "led/led_log.txt",
        "Radio Service": "radio/radio_log.txt",
        "Fan Service": "fan/fan_log.txt",
        "Broadcast Service": "broadcast/broadcast_log.txt",
        "Mixing Service": "mixing/mixing_log.txt",
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

@app.route("/radio_scan_all", methods=["POST"])
def radio_scan_all():
    """Trigger full band radio scan and return found stations"""
    try:
        # Import the radio service functions
        import sys
        radio_path = os.path.join(os.path.dirname(__file__), 'radio')
        if radio_path not in sys.path:
            sys.path.insert(0, radio_path)

        import importlib.util
        spec = importlib.util.spec_from_file_location("fm_radio_menu", os.path.join(radio_path, "fm-radio_menu.py"))
        fm_radio_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fm_radio_module)

        service_manager.log_event("Starting full band radio scan")

        # Call the search function
        stations = fm_radio_module.search_all_stations()

        service_manager.log_event(f"Full band scan completed: {len(stations)} stations found")

        return jsonify({
            "status": "success",
            "stations": stations,
            "total_found": len(stations),
            "scan_time": time.time()
        })

    except Exception as e:
        service_manager.log_error("Error during radio scan", e)
        return jsonify({
            "status": "error",
            "message": str(e),
            "stations": []
        }), 500

@app.route("/radio_scan_partial", methods=["GET"])
def radio_scan_partial():
    """Get partial scan results from interrupted scan"""
    try:
        # First check the radio status file for stations
        radio_status_file = os.path.join('radio', 'radio_status.json')
        if os.path.exists(radio_status_file):
            with open(radio_status_file, 'r') as f:
                status_data = json.load(f)

            # If status file contains stations list, return it
            if 'stations' in status_data and status_data['stations']:
                service_manager.log_event(f"Retrieved stations from status file: {len(status_data['stations'])} stations")
                return jsonify({
                    "status": "success",
                    "stations": status_data['stations'],
                    "total_found": len(status_data['stations']),
                    "scan_time": status_data.get('last_update', 'unknown'),
                    "partial": False
                })

        # Fallback: Check if there's a partial scan results file
        stations_file = os.path.join('radio', 'found_stations.json')

        if os.path.exists(stations_file):
            with open(stations_file, 'r') as f:
                data = json.load(f)

            service_manager.log_event(f"Retrieved partial scan results: {data.get('total_found', 0)} stations")

            return jsonify({
                "status": "success",
                "stations": data.get('stations', []),
                "total_found": data.get('total_found', 0),
                "scan_time": data.get('scan_time', 'unknown'),
                "partial": True
            })
        else:
            return jsonify({
                "status": "success",
                "stations": [],
                "total_found": 0,
                "partial": True
            })

    except Exception as e:
        service_manager.log_error("Error getting partial scan results", e)
        return jsonify({
            "status": "error",
            "message": str(e),
            "stations": []
        }), 500

@app.route("/wifi_status", methods=["GET"])
def wifi_status_api():
    """Get detailed WiFi status and recent logs"""
    try:
        # Get current status
        status = get_wifi_status()

        # Get recent logs (try network connection log first, then wifi log)
        network_log_file = os.path.join('network', 'network_connection_log.txt')
        wifi_log_file = os.path.join('network', 'wifi_connection_log.txt')
        recent_logs = []

        if os.path.exists(network_log_file):
            with open(network_log_file, 'r') as f:
                lines = f.readlines()[:20]  # Get last 20 log entries
                recent_logs = [line.strip() for line in lines]
        elif os.path.exists(wifi_log_file):
            with open(wifi_log_file, 'r') as f:
                lines = f.readlines()[:20]  # Get last 20 log entries
                recent_logs = [line.strip() for line in lines]

        return jsonify({
            "status": "success",
            "wifi_status": status,
            "recent_logs": recent_logs,
            "log_count": len(recent_logs)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "wifi_status": {"connected": False, "error": "Failed to get status"},
            "recent_logs": []
        }), 500

@app.route("/media/<filename>")
def serve_media(filename):
    """Serve audio files from broadcast media directory"""
    try:
        media_dir = os.path.join(os.path.dirname(__file__), 'broadcast', 'media')
        return send_from_directory(media_dir, filename)
    except Exception:
        return "File not found", 404

@app.route("/radio_stop_scan", methods=["POST"])
def radio_stop_scan():
    """Stop ongoing radio scan"""
    try:
        # Import the radio service functions
        import sys
        radio_path = os.path.join(os.path.dirname(__file__), 'radio')
        if radio_path not in sys.path:
            sys.path.insert(0, radio_path)

        import importlib.util
        spec = importlib.util.spec_from_file_location("fm_radio_menu", os.path.join(radio_path, "fm-radio_menu.py"))
        fm_radio_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fm_radio_module)

        # Call the stop function
        fm_radio_module.stop_scan()

        service_manager.log_event("Radio scan stop signal sent")

        return jsonify({
            "status": "success",
            "message": "Stop signal sent to scanner"
        })

    except Exception as e:
        service_manager.log_error("Error stopping radio scan", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def restore_services_on_startup():
    """Restore services that were running and not manually stopped"""
    try:
        print("🔄 Restoring services based on previous state...")
        service_manager.log_event("Starting automatic service restoration (respecting manual stops)")

        # Log system startup event
        persistence_manager.log_service_event("SYSTEM", "STARTUP", "Unified app started - beginning service restoration")

        # Wait a moment for system to stabilize
        time.sleep(2)

        # Restore dashboard configurations first
        print("📋 Restoring dashboard configurations...")
        dashboard_state.restore_unified_config(config_manager)

        # Only restore services that were running AND not manually stopped
        restored_services = persistence_manager.restore_services(force_all_services=False)

        if restored_services:
            print(f"✅ Restored services: {', '.join(restored_services)}")
            service_manager.log_event(f"Successfully restored services: {restored_services}")
        else:
            print("ℹ️  No services to restore or all services already running")
            service_manager.log_event("No services to restore")

        # Update current state
        persistence_manager.update_running_services()

        # Backup current configuration state
        dashboard_state.backup_current_config(config_manager)

    except Exception as e:
        print(f"❌ Error during service restoration: {e}")
        service_manager.log_error("Failed to restore services on startup", e)

def save_services_on_shutdown():
    """Save current service state before shutdown"""
    try:
        print("💾 Saving service state before shutdown...")

        # Save service running state
        current_services = persistence_manager.get_currently_running_services()
        persistence_manager.save_service_state(current_services)

        # Save dashboard configuration state
        dashboard_state.backup_current_config(config_manager)

        service_manager.log_event(f"Service state saved before shutdown: {current_services}")
    except Exception as e:
        print(f"❌ Error saving service state: {e}")
        service_manager.log_error("Failed to save service state on shutdown", e)

if __name__ == "__main__":
    try:
        service_manager.log_event("Unified Control Panel starting")
        print(f"🚀 Starting Raspberry Pi Control Panel")
        print(f"Available modes: {', '.join(APP_MODES.keys())}")
        print(f"Current mode: {get_current_mode()}")

        # Restore services that were running before shutdown/restart
        restore_services_on_startup()

        print(f"🌐 Access at: http://0.0.0.0:5000")

        # Register shutdown handler
        import atexit
        atexit.register(save_services_on_shutdown)

        # Register signal handlers for graceful shutdown
        import signal
        def signal_handler(signum, frame):
            print(f"\n⚠️  Received signal {signum}, shutting down gracefully...")
            save_services_on_shutdown()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        app.run(host="0.0.0.0", port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n⚠️  Keyboard interrupt received, shutting down gracefully...")
        save_services_on_shutdown()
        sys.exit(0)
    except Exception as e:
        service_manager.log_error("Fatal error in control panel", e)
        print(f"❌ Fatal error: {e}")
        save_services_on_shutdown()
        sys.exit(1)