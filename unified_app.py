#!/usr/bin/env python3
"""
Unified Raspberry Pi Control Panel
Consolidated Flask application with modular service management
"""

import os
import sys
import json
import time
from datetime import datetime
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
    APP_VERSION = "3.0.0"

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

# Initialize service protection system
try:
    from core.service_protection import start_service_protection
    service_protection = start_service_protection()
    print("✅ Service protection system initialized successfully")
except Exception as e:
    print(f"⚠️  Service protection system failed to start: {e}")
    service_protection = None

# Initialize metrics recording
try:
    metrics_recorder = get_metrics_recorder()
    metrics_recorder.start_recording()
    print("✅ Metrics recording initialized successfully (1-minute interval)")
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

        # Auto-switch LED service from Musical mode to Lux mode when returning to dashboard
        try:
            service_manager.log_event("Dashboard load: Checking LED service for auto-switch")
            led_config = config_manager.get_service_config("LED Service")
            service_manager.log_event(f"Dashboard load: LED config retrieved - mode: {led_config.get('mode') if led_config else 'None'}")

            if led_config and led_config.get("mode") in ["Musical LED", "Manual LED"]:
                service_manager.log_event(f"Dashboard load: Auto-switching LED from {led_config.get('mode')} to Lux sensor mode")

                # Switch to Lux sensor mode with current brightness
                current_brightness = led_config.get("brightness", 50)
                new_led_config = {
                    "mode": "Lux sensor",
                    "brightness": current_brightness,
                    "lux_min": led_config.get("lux_min", "10"),
                    "lux_max": led_config.get("lux_max", "700")
                }

                service_manager.log_event(f"Dashboard load: Updating LED config to: {new_led_config}")
                config_manager.update_service_config("LED Service", new_led_config)
                # Also save to dashboard state for persistence
                dashboard_state.save_service_config("LED Service", new_led_config)
                service_manager.log_event(f"LED auto-switched to Lux sensor mode with brightness {current_brightness}")
            else:
                service_manager.log_event(f"Dashboard load: No auto-switch needed - LED mode is {led_config.get('mode') if led_config else 'None'}")
        except Exception as e:
            service_manager.log_error("Error auto-switching LED to Lux mode", e)

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
    try:
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

    except Exception as e:
        # Critical safety net to prevent dashboard crashes
        service_manager.log_error(f"CRITICAL: Unexpected error in stop_service endpoint for {service}", e)
        try:
            persistence_manager.log_service_event(service, "STOP_CRITICAL_ERROR", f"Dashboard stop endpoint crashed: {str(e)}", False)
        except:
            # Even logging failed - write to a simple log file
            with open("/tmp/dashboard_crash.log", "a") as f:
                f.write(f"[{datetime.now()}] CRITICAL STOP ERROR for {service}: {str(e)}\n")

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

@app.route("/api/led_rms_status")
def api_led_rms_status():
    """API endpoint for LED RMS statistics"""
    try:
        # Read RMS data from LED status file instead of importing module
        led_status = config_manager.read_service_status("LED Service")

        if led_status:
            return jsonify({
                "current_rms": float(led_status.get("current_rms", 0.0)),
                "max_rms": float(led_status.get("max_rms_minute", 0.0)),
                "min_rms": float(led_status.get("min_rms_minute", 0.0)),
                "brightness": float(led_status.get("brightness", 0.0))
            })
        else:
            return jsonify({
                "current_rms": 0.0,
                "max_rms": 0.0,
                "min_rms": 0.0,
                "brightness": 0.0
            })
    except Exception as e:
        service_manager.log_error("Error reading LED RMS status", e)
        return jsonify({
            "current_rms": 0.0,
            "max_rms": 0.0,
            "min_rms": 0.0,
            "brightness": 0.0
        }), 500

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

@app.route("/performing")
def performing_page():
    """Performance mode page"""
    return render_template('performing.html')

@app.route("/performing/status", methods=["GET"])
def performing_status():
    """Get current performing mode status"""
    try:
        led_config = config_manager.get_service_config("LED Service")
        led_status = config_manager.read_service_status("LED Service")

        # Determine current performing mode based on LED mode
        led_mode = led_config.get("mode", "Disable")
        if led_mode == "Musical LED":
            current_mode = "auto"
        elif led_mode == "Manual LED":
            current_mode = "manual"
        else:
            current_mode = "disable"

        brightness = led_status.get("brightness", 0) if led_status else 0

        return jsonify({
            "status": "success",
            "current_mode": current_mode,
            "brightness": brightness,
            "led_mode": led_mode
        })
    except Exception as e:
        service_manager.log_error("Error getting performing status", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/performing/set_mode", methods=["POST"])
def set_performing_mode():
    """Set performing mode and manage other services"""
    try:
        mode = request.form.get('mode')  # Musical LED, Manual LED, or Disable
        brightness = int(request.form.get('brightness', 50))

        stopped_services = []

        if mode in ["Musical LED", "Manual LED"]:
            # Create performance mode flag to prevent service protection from restarting services
            try:
                performance_flag = "/tmp/cos_performance_mode_active"
                with open(performance_flag, 'w') as f:
                    f.write(f"Performance mode {mode} active since: {datetime.now().isoformat()}\n")
                    f.write("Services should remain stopped until performance mode ends\n")
                service_manager.log_event(f"Created performance mode flag: {performance_flag}")
            except Exception as e:
                service_manager.log_error("Failed to create performance mode flag", e)

            # Stop all other services when entering performance mode to ensure LED service has full audio access
            service_manager.log_event(f"Performance mode {mode}: Stopping all other services for optimal audio performance")

            # Use management scripts to properly stop services
            script_mapping = {
                "Fan Service": "scripts/manage_fan_service.sh",
                "Broadcast Service": "scripts/manage_broadcast_service.sh",
                "Mixing Service": "scripts/manage_mixing_service.sh",
                "Radio Service": "scripts/manage_radio_service.sh"
            }

            for service_name in SERVICES:
                if service_name != "LED Service":
                    script_path = script_mapping.get(service_name)
                    if script_path and os.path.exists(script_path):
                        try:
                            # Stop the service using its management script
                            result = subprocess.run([script_path, "stop"],
                                                  capture_output=True, text=True, timeout=10)

                            if result.returncode == 0:
                                stopped_services.append(service_name)
                                service_manager.log_event(f"Stopped {service_name} for performance mode using management script")
                            else:
                                service_manager.log_error(f"Failed to stop {service_name}: {result.stderr}")
                                # Fallback to service manager stop
                                if service_manager.is_service_running(service_name):
                                    stopped_services.append(service_name)
                                    service_manager.stop_service(service_name)
                                    service_manager.log_event(f"Stopped {service_name} for performance mode using fallback method")

                        except Exception as e:
                            service_manager.log_error(f"Error stopping {service_name} with script, using fallback", e)
                            # Fallback to service manager stop
                            if service_manager.is_service_running(service_name):
                                stopped_services.append(service_name)
                                service_manager.stop_service(service_name)
                                service_manager.log_event(f"Stopped {service_name} for performance mode using fallback method")
                    else:
                        # Fallback to service manager stop if script not found
                        if service_manager.is_service_running(service_name):
                            stopped_services.append(service_name)
                            service_manager.stop_service(service_name)
                            service_manager.log_event(f"Stopped {service_name} for performance mode (no management script found)")

            # Also explicitly stop mixing service recording state to prevent conflicts
            try:
                mixing_status_file = os.path.join('mixing', 'mixing_status.json')
                if os.path.exists(mixing_status_file):
                    with open(mixing_status_file, 'r') as f:
                        mixing_status = json.load(f)

                    if mixing_status.get('recording', False):
                        mixing_status['recording'] = False
                        mixing_status['status'] = 'idle'

                        with open(mixing_status_file, 'w') as f:
                            json.dump(mixing_status, f, indent=2)

                        service_manager.log_event("Performance mode: Disabled mixing service recording state")
            except Exception as e:
                service_manager.log_error("Error updating mixing service status for performance mode", e)

            # For both performance modes, clean up audio processes that could interfere
            try:
                import subprocess
                # Kill any remaining mpg123 processes that might not have been stopped by service scripts
                service_manager.log_event(f"Performance mode {mode}: Killing any remaining audio processes (mpg123, etc.)")
                subprocess.run(['pkill', '-f', 'mpg123'], capture_output=True, timeout=5)

                # Kill other audio processes that might interfere
                subprocess.run(['pkill', '-f', 'arecord'], capture_output=True, timeout=5)
                subprocess.run(['pkill', '-f', 'parecord'], capture_output=True, timeout=5)

            except Exception as e:
                service_manager.log_error(f"Error killing audio processes for {mode}", e)

            # For Musical LED (Auto mode), also stop PulseAudio to prevent audio device conflicts
            if mode == "Musical LED":
                try:
                    # Kill PulseAudio processes that might be blocking audio device access
                    service_manager.log_event("Performance mode Auto: Stopping PulseAudio to free audio device for LED service")
                    subprocess.run(['pkill', '-f', 'pulseaudio'], capture_output=True, timeout=5)

                    # Restart LED service to ensure fresh audio access
                    service_manager.log_event("Performance mode Auto: Restarting LED service for fresh audio access")
                    subprocess.run(['/home/payas/cos/scripts/manage_led_service.sh', 'restart'], capture_output=True, timeout=10)

                except Exception as e:
                    service_manager.log_error("Error stopping audio conflicts for Auto mode", e)

        elif mode == "Disable":
            # Remove performance mode flag first
            try:
                performance_flag = "/tmp/cos_performance_mode_active"
                if os.path.exists(performance_flag):
                    os.remove(performance_flag)
                    service_manager.log_event(f"Removed performance mode flag: {performance_flag}")
            except Exception as e:
                service_manager.log_error("Failed to remove performance mode flag", e)

            # When disabling LED performance mode, restart all services and switch LED to Lux sensor mode
            service_manager.log_event(f"Exiting performance mode: Switching LED to Lux sensor mode and restarting all services")

            # First, switch LED service to Lux sensor mode to prevent audio device conflicts
            try:
                led_config_file = os.path.join(os.getcwd(), "led", "led_config.json")
                if os.path.exists(led_config_file):
                    with open(led_config_file, 'r') as f:
                        led_config_data = json.load(f)

                    # Switch to Lux sensor mode (lighting mode)
                    led_config_data["mode"] = "lighting"
                    led_config_data["_auto_switched"] = datetime.now().isoformat()
                    led_config_data["_reason"] = "auto-switch-after-performance-mode"

                    with open(led_config_file, 'w') as f:
                        json.dump(led_config_data, f, indent=2)

                    service_manager.log_event("Switched LED service to Lux sensor mode to prevent audio conflicts")
                else:
                    service_manager.log_error("LED config file not found for auto-switching")

            except Exception as e:
                service_manager.log_error("Failed to switch LED to Lux sensor mode after performance", e)

            # Restart all essential services (they should have been stopped during performance mode)
            services_to_restart = ["Fan Service", "Broadcast Service", "Mixing Service", "Radio Service"]
            restarted_services = []

            for service_name in services_to_restart:
                try:
                    # Get the script path for this service
                    script_mapping = {
                        "Fan Service": "scripts/manage_fan_service.sh",
                        "Broadcast Service": "scripts/manage_broadcast_service.sh",
                        "Mixing Service": "scripts/manage_mixing_service.sh",
                        "Radio Service": "scripts/manage_radio_service.sh"
                    }

                    script_path = script_mapping.get(service_name)
                    if script_path and os.path.exists(script_path):
                        # Start the service using its management script
                        result = subprocess.run([script_path, "start"],
                                              capture_output=True, text=True, timeout=15)

                        if result.returncode == 0:
                            restarted_services.append(service_name)
                            service_manager.log_event(f"Restarted {service_name} after performance mode")
                        else:
                            service_manager.log_error(f"Failed to restart {service_name}: {result.stderr}")
                    else:
                        service_manager.log_error(f"Management script not found for {service_name}")

                except Exception as e:
                    service_manager.log_error(f"Error restarting {service_name} after performance mode", e)

            # Update the service state to reflect restarted services
            try:
                persistence_manager.update_running_services()
                service_manager.log_event(f"Performance mode exit complete: LED switched to Lux sensor, services restarted: {restarted_services}")
            except Exception as e:
                service_manager.log_error("Error updating service state after performance restart", e)

        # Update LED service configuration
        led_config = {
            "mode": mode,
            "brightness": brightness
        }

        success = config_manager.update_service_config("LED Service", led_config)

        if success:
            # Also save to dashboard state for persistence across restarts
            dashboard_state.save_service_config("LED Service", led_config)
            service_manager.log_event(f"Set performing mode: {mode}")
            return jsonify({
                "status": "success",
                "mode": mode,
                "stopped_services": stopped_services
            })
        else:
            return jsonify({"status": "error", "message": "Failed to update configuration"}), 500

    except Exception as e:
        service_manager.log_error("Error setting performing mode", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/performing/set_brightness", methods=["POST"])
def set_performing_brightness():
    """Set LED brightness for manual mode"""
    try:
        # Log comprehensive request details
        service_manager.log_event(f"=== BRIGHTNESS UPDATE REQUEST ===")
        service_manager.log_event(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        service_manager.log_event(f"Request method: {request.method}")
        service_manager.log_event(f"Request content_type: {request.content_type}")
        service_manager.log_event(f"Request form data: {dict(request.form)}")
        service_manager.log_event(f"Raw request data: {request.data}")

        brightness_str = request.form.get('brightness', '0')
        service_manager.log_event(f"Extracted brightness value: '{brightness_str}'")

        # Validate brightness value
        try:
            brightness = int(brightness_str)
            if brightness < 0 or brightness > 100:
                return jsonify({"status": "error", "message": "Brightness must be between 0 and 100"}), 400
        except ValueError as ve:
            service_manager.log_error(f"Invalid brightness value: {brightness_str}", ve)
            return jsonify({"status": "error", "message": f"Invalid brightness value: {brightness_str}"}), 400

        # Get current LED service configuration
        try:
            service_manager.log_event("Attempting to get LED service config...")
            led_config = config_manager.get_service_config("LED Service")
            service_manager.log_event(f"Current LED config retrieved successfully: {led_config}")

            # Verify config is a dict and can be modified
            if not isinstance(led_config, dict):
                service_manager.log_error(f"LED config is not a dict: {type(led_config)}", None)
                return jsonify({"status": "error", "message": "Invalid LED service configuration format"}), 500

        except Exception as e:
            service_manager.log_error("Failed to get LED service config", e)
            return jsonify({"status": "error", "message": "Failed to get LED service configuration"}), 500

        # Update brightness
        led_config["brightness"] = brightness
        service_manager.log_event(f"Updating LED config with brightness: {brightness}")

        # Save updated configuration with retry logic
        success = False
        max_retries = 3
        for attempt in range(max_retries):
            try:
                service_manager.log_event(f"Saving LED config attempt {attempt + 1}/{max_retries}")
                success = config_manager.update_service_config("LED Service", led_config)
                if success:
                    service_manager.log_event("Config save successful")
                    break
                else:
                    service_manager.log_event(f"Config save returned False on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.1 * (attempt + 1))  # Progressive delay: 100ms, 200ms, 300ms
            except Exception as e:
                service_manager.log_error(f"Failed to save LED service config on attempt {attempt + 1}", e)
                if attempt == max_retries - 1:
                    return jsonify({"status": "error", "message": "Failed to save LED service configuration"}), 500
                else:
                    import time
                    time.sleep(0.1 * (attempt + 1))

        if success:
            service_manager.log_event(f"Brightness successfully updated to {brightness}%")
            response = jsonify({"status": "success", "brightness": brightness})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'POST')
            return response
        else:
            service_manager.log_error("Config update returned False", None)
            response = jsonify({"status": "error", "message": "Failed to update brightness configuration"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500

    except Exception as e:
        service_manager.log_error("Unexpected error in set_performing_brightness", e)
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500

@app.route("/performing/test_brightness", methods=["POST"])
def test_brightness():
    """Simple test endpoint for brightness debugging"""
    try:
        service_manager.log_event("=== TEST BRIGHTNESS REQUEST ===")
        brightness_str = request.form.get('brightness', 'NOT_FOUND')
        service_manager.log_event(f"Received brightness: {brightness_str}")

        # Just return what we received, don't try to save anything
        response = jsonify({"status": "test_success", "received_brightness": brightness_str, "form_data": dict(request.form)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    except Exception as e:
        service_manager.log_error("Error in test_brightness", e)
        return jsonify({"status": "test_error", "message": str(e)}), 500

@app.route("/performing/direct_brightness", methods=["POST"])
def direct_brightness_control():
    """Direct LED brightness control that immediately updates the LED without config polling delays"""
    try:
        brightness_str = request.form.get('brightness', '0')
        brightness = int(brightness_str)

        if brightness < 0 or brightness > 100:
            return jsonify({"status": "error", "message": "Brightness must be between 0 and 100"}), 400

        service_manager.log_event(f"Direct LED brightness control: {brightness}%")

        # Update config for persistence
        led_config = config_manager.get_service_config("LED Service")
        led_config["brightness"] = brightness
        config_manager.update_service_config("LED Service", led_config)

        # Also trigger immediate LED update by writing to LED status file
        import json
        led_status_file = "led/led_status.json"
        try:
            # Read current status
            with open(led_status_file, 'r') as f:
                led_status = json.load(f)

            # Update brightness and power state
            led_status["brightness"] = float(brightness)
            led_status["power_state"] = brightness > 0
            led_status["mode"] = "Manual LED"
            led_status["last_update"] = datetime.now().isoformat()

            # Write updated status
            with open(led_status_file, 'w') as f:
                json.dump(led_status, f, indent=2)

            service_manager.log_event(f"Direct LED update: brightness={brightness}%, power={'on' if brightness > 0 else 'off'}")

        except Exception as e:
            service_manager.log_error("Failed to update LED status file", e)

        response = jsonify({"status": "success", "brightness": brightness, "method": "direct"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except ValueError:
        return jsonify({"status": "error", "message": "Invalid brightness value"}), 400
    except Exception as e:
        service_manager.log_error("Error in direct_brightness_control", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/performing/update_rms", methods=["POST"])
def update_rms_settings():
    """Update RMS sensitivity settings for auto mode"""
    try:
        mic_rms_quiet = float(request.form.get('mic_rms_quiet', 0.002))
        mic_rms_loud = float(request.form.get('mic_rms_loud', 0.04))

        # Validate values
        if mic_rms_quiet < 0 or mic_rms_quiet > 1:
            return jsonify({"status": "error", "message": "Quiet threshold must be between 0 and 1"}), 400
        if mic_rms_loud < 0 or mic_rms_loud > 1:
            return jsonify({"status": "error", "message": "Loud threshold must be between 0 and 1"}), 400
        if mic_rms_quiet >= mic_rms_loud:
            return jsonify({"status": "error", "message": "Quiet threshold must be less than loud threshold"}), 400

        # Update LED service configuration
        led_config = config_manager.get_service_config("LED Service")
        led_config["mic_rms_quiet"] = str(mic_rms_quiet)
        led_config["mic_rms_loud"] = str(mic_rms_loud)

        success = config_manager.update_service_config("LED Service", led_config)
        if success:
            # Also save to dashboard state for persistence
            dashboard_state.save_service_config("LED Service", led_config)
            service_manager.log_event(f"Updated RMS settings: quiet={mic_rms_quiet}, loud={mic_rms_loud}")
            return jsonify({
                "status": "success",
                "mic_rms_quiet": mic_rms_quiet,
                "mic_rms_loud": mic_rms_loud
            })
        else:
            return jsonify({"status": "error", "message": "Failed to update configuration"}), 500

    except Exception as e:
        service_manager.log_error("Error updating RMS settings", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/performing/get_rms_settings", methods=["GET"])
def get_rms_settings():
    """Get current RMS sensitivity settings"""
    try:
        led_config = config_manager.get_service_config("LED Service")
        return jsonify({
            "status": "success",
            "mic_rms_quiet": float(led_config.get("mic_rms_quiet", 0.002)),
            "mic_rms_loud": float(led_config.get("mic_rms_loud", 0.04)),
            "musical_led_active": led_config.get("musical_led_active", "active")
        })
    except Exception as e:
        service_manager.log_error("Error getting RMS settings", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/performing/update_musical_led_active", methods=["POST"])
def update_musical_led_active():
    """Update musical LED active state (active/off)"""
    try:
        musical_led_active = request.form.get('musical_led_active', 'active')

        # Validate input
        if musical_led_active not in ['active', 'off']:
            return jsonify({"status": "error", "message": "Invalid musical_led_active value. Must be 'active' or 'off'."}), 400

        # Update configuration
        config_manager.update_service_config("LED Service", {"musical_led_active": musical_led_active})

        service_manager.log_event(f"Performance mode: Musical LED active state updated to {musical_led_active}")

        return jsonify({
            "status": "success",
            "musical_led_active": musical_led_active,
            "message": f"Musical LED active state set to {musical_led_active}"
        })

    except Exception as e:
        service_manager.log_error("Error updating musical LED active state", e)
        return jsonify({"status": "error", "message": str(e)}), 500

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