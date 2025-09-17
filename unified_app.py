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

# Initialize exhibition watchdog
try:
    from core.exhibition_watchdog import get_watchdog, start_watchdog
    exhibition_watchdog = start_watchdog()
    print("✅ Exhibition watchdog started")
except Exception as e:
    print(f"⚠️  Exhibition watchdog failed to start: {e}")
    exhibition_watchdog = None

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
    """Exhibition monitoring dashboard"""
    try:
        if not exhibition_watchdog:
            return "Exhibition watchdog not available", 503
            
        # Get recent health history for charts
        recent_history = exhibition_watchdog.health_history[-50:]  # Last 50 readings
        
        dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code of the Sea - Exhibition Monitor</title>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #0f172a; color: #e2e8f0; }}
                .header {{ background: linear-gradient(135deg, #1e40af, #7c3aed); padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }}
                .status-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 20px; }}
                .status-card h3 {{ margin-top: 0; color: #3b82f6; }}
                .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
                .metric-label {{ color: #94a3b8; }}
                .metric-value {{ font-weight: bold; }}
                .status-healthy {{ color: #10b981; }}
                .status-warning {{ color: #f59e0b; }}
                .status-error {{ color: #ef4444; }}
                .chart-container {{ background: #1e293b; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .nav-links {{ margin: 20px 0; }}
                .nav-links a {{ background: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-right: 10px; }}
                .nav-links a:hover {{ background: #2563eb; }}
                .process-list {{ max-height: 200px; overflow-y: auto; }}
                .process-item {{ background: #334155; margin: 5px 0; padding: 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🌊 Code of the Sea - Exhibition Monitor</h1>
                <p>Long-term art installation monitoring & stability system</p>
            </div>
            
            <div class="nav-links">
                <a href="/exhibition/health">API Health</a>
                <a href="/">Main Control Panel</a>
                <a href="/logs">System Logs</a>
            </div>
            
            <div id="status-content">
                <p>Loading exhibition status...</p>
            </div>
            
            <script>
                async function loadStatus() {{
                    try {{
                        const response = await fetch('/exhibition/health');
                        const data = await response.json();
                        updateDashboard(data);
                    }} catch (error) {{
                        document.getElementById('status-content').innerHTML = `
                            <div class="status-card">
                                <h3 class="status-error">❌ Connection Error</h3>
                                <p>Could not load exhibition status: ${{error.message}}</p>
                            </div>
                        `;
                    }}
                }}
                
                function updateDashboard(data) {{
                    const statusClass = data.status === 'healthy' ? 'status-healthy' : 
                                      data.status === 'degraded' ? 'status-warning' : 'status-error';
                    
                    const statusIcon = data.status === 'healthy' ? '✅' : 
                                     data.status === 'degraded' ? '⚠️' : '❌';
                    
                    document.getElementById('status-content').innerHTML = `
                        <div class="status-grid">
                            <div class="status-card">
                                <h3 class="${{statusClass}}">${{statusIcon}} System Status: ${{data.status.toUpperCase()}}</h3>
                                <div class="metric">
                                    <span class="metric-label">Last Update:</span>
                                    <span class="metric-value">${{new Date(data.timestamp).toLocaleString()}}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Uptime:</span>
                                    <span class="metric-value">${{Math.round(data.system.uptime_hours * 10) / 10}}h</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Restart Count:</span>
                                    <span class="metric-value">${{data.watchdog.restart_count}}</span>
                                </div>
                            </div>
                            
                            <div class="status-card">
                                <h3>📊 System Resources</h3>
                                <div class="metric">
                                    <span class="metric-label">CPU Usage:</span>
                                    <span class="metric-value ${{data.system.cpu_percent > 80 ? 'status-error' : data.system.cpu_percent > 60 ? 'status-warning' : 'status-healthy'}}">${{data.system.cpu_percent.toFixed(1)}}%</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Memory Usage:</span>
                                    <span class="metric-value ${{data.system.memory_percent > 85 ? 'status-error' : data.system.memory_percent > 70 ? 'status-warning' : 'status-healthy'}}">${{data.system.memory_percent.toFixed(1)}}%</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Disk Usage:</span>
                                    <span class="metric-value ${{data.system.disk_percent > 90 ? 'status-error' : data.system.disk_percent > 80 ? 'status-warning' : 'status-healthy'}}">${{data.system.disk_percent.toFixed(1)}}%</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">CPU Temperature:</span>
                                    <span class="metric-value ${{data.system.cpu_temperature > 70 ? 'status-error' : data.system.cpu_temperature > 60 ? 'status-warning' : 'status-healthy'}}">${{data.system.cpu_temperature.toFixed(1)}}°C</span>
                                </div>
                            </div>
                            
                            <div class="status-card">
                                <h3>🌐 WiFi Connection Status</h3>
                                <div class="metric">
                                    <span class="metric-label">Connectivity:</span>
                                    <span class="metric-value ${{data.network.detailed_wifi_status?.wifi?.connected ? 'status-healthy' : 'status-error'}}">${{data.network.detailed_wifi_status?.wifi?.connected ? '✅ Connected' : '❌ Disconnected'}}</span>
                                </div>
                                ${{data.network.detailed_wifi_status?.wifi?.essid ? `
                                <div class="metric">
                                    <span class="metric-label">Network:</span>
                                    <span class="metric-value">${{data.network.detailed_wifi_status.wifi.essid}} (${{data.network.detailed_wifi_status.wifi.frequency || 'N/A'}})</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.wifi?.signal_quality_percent ? `
                                <div class="metric">
                                    <span class="metric-label">Signal Quality:</span>
                                    <span class="metric-value ${{data.network.detailed_wifi_status.wifi.signal_quality_percent > 80 ? 'status-healthy' : data.network.detailed_wifi_status.wifi.signal_quality_percent > 50 ? 'status-warning' : 'status-error'}}">${{data.network.detailed_wifi_status.wifi.signal_quality_percent.toFixed(0)}}% (${{data.network.detailed_wifi_status.wifi.signal_quality}})</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.wifi?.signal_level ? `
                                <div class="metric">
                                    <span class="metric-label">Signal Strength:</span>
                                    <span class="metric-value ${{data.network.detailed_wifi_status.wifi.signal_level > -50 ? 'status-healthy' : data.network.detailed_wifi_status.wifi.signal_level > -70 ? 'status-warning' : 'status-error'}}">${{data.network.detailed_wifi_status.wifi.signal_level}} dBm</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.connection_duration ? `
                                <div class="metric">
                                    <span class="metric-label">Connected Duration:</span>
                                    <span class="metric-value">${{data.network.detailed_wifi_status.connection_duration}}</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.disconnection_count !== undefined ? `
                                <div class="metric">
                                    <span class="metric-label">Disconnections Today:</span>
                                    <span class="metric-value ${{data.network.detailed_wifi_status.disconnection_count > 5 ? 'status-error' : data.network.detailed_wifi_status.disconnection_count > 2 ? 'status-warning' : 'status-healthy'}}">${{data.network.detailed_wifi_status.disconnection_count}}</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.wifi?.bit_rate ? `
                                <div class="metric">
                                    <span class="metric-label">Data Rate:</span>
                                    <span class="metric-value">${{data.network.detailed_wifi_status.wifi.bit_rate}}</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.internet_accessible !== undefined ? `
                                <div class="metric">
                                    <span class="metric-label">Internet Access:</span>
                                    <span class="metric-value ${{data.network.detailed_wifi_status.internet_accessible ? 'status-healthy' : 'status-error'}}">${{data.network.detailed_wifi_status.internet_accessible ? '🌍 Available' : '🚫 Blocked'}}</span>
                                </div>
                                ` : ''}}
                                <div style="margin-top: 15px;">
                                    <button onclick="showWifiLogs()" style="background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">
                                        📋 View Connection Log
                                    </button>
                                </div>
                            </div>

                            <div class="status-card">
                                <h3>🔌 LAN Connection Status</h3>
                                <div class="metric">
                                    <span class="metric-label">Connectivity:</span>
                                    <span class="metric-value ${{data.network.detailed_wifi_status?.ethernet?.connected ? 'status-healthy' : 'status-error'}}">${{data.network.detailed_wifi_status?.ethernet?.connected ? '✅ Connected' : '❌ Disconnected'}}</span>
                                </div>
                                ${{data.network.detailed_wifi_status?.ethernet?.ip_address ? `
                                <div class="metric">
                                    <span class="metric-label">IP Address:</span>
                                    <span class="metric-value">${{data.network.detailed_wifi_status.ethernet.ip_address}}</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.ethernet?.speed ? `
                                <div class="metric">
                                    <span class="metric-label">Link Speed:</span>
                                    <span class="metric-value">${{data.network.detailed_wifi_status.ethernet.speed}}</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.ethernet?.duplex ? `
                                <div class="metric">
                                    <span class="metric-label">Duplex Mode:</span>
                                    <span class="metric-value">${{data.network.detailed_wifi_status.ethernet.duplex}}</span>
                                </div>
                                ` : ''}}
                                ${{data.network.detailed_wifi_status?.network_stats?.ethernet ? `
                                <div class="metric">
                                    <span class="metric-label">RX/TX Packets:</span>
                                    <span class="metric-value">${{data.network.detailed_wifi_status.network_stats.ethernet.rx_packets.toLocaleString()}} / ${{data.network.detailed_wifi_status.network_stats.ethernet.tx_packets.toLocaleString()}}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">RX/TX Bytes:</span>
                                    <span class="metric-value">${{(data.network.detailed_wifi_status.network_stats.ethernet.rx_bytes / 1024 / 1024).toFixed(1)}} MB / ${{(data.network.detailed_wifi_status.network_stats.ethernet.tx_bytes / 1024 / 1024).toFixed(1)}} MB</span>
                                </div>
                                ` : ''}}
                                ${{!data.network.detailed_wifi_status?.ethernet?.connected ? `
                                <div class="metric">
                                    <span class="metric-label">Status:</span>
                                    <span class="metric-value status-info">No Ethernet cable connected</span>
                                </div>
                                ` : ''}}
                            </div>
                            
                            <div class="status-card">
                                <h3>⚙️ Hardware Status</h3>
                                <div class="metric">
                                    <span class="metric-label">Overall Health:</span>
                                    <span class="metric-value ${{data.hardware.healthy ? 'status-healthy' : 'status-error'}}">${{data.hardware.healthy ? '✅ Healthy' : '❌ Issues'}}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">I2C Devices:</span>
                                    <span class="metric-value ${{data.hardware.i2c_devices_ok ? 'status-healthy' : 'status-error'}}">${{data.hardware.i2c_devices_ok ? '✅ OK' : '❌ Issues'}}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">GPIO Devices:</span>
                                    <span class="metric-value ${{data.hardware.gpio_devices_ok ? 'status-healthy' : 'status-error'}}">${{data.hardware.gpio_devices_ok ? '✅ OK' : '❌ Issues'}}</span>
                                </div>
                            </div>
                            
                            <div class="status-card">
                                <h3>🚨 Services & Errors</h3>
                                <div class="metric">
                                    <span class="metric-label">Service Health:</span>
                                    <span class="metric-value ${{data.services.main_service_healthy ? 'status-healthy' : 'status-error'}}">${{data.services.main_service_healthy ? '✅ Healthy' : '❌ Issues'}}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Recent Errors:</span>
                                    <span class="metric-value ${{data.services.error_count > 5 ? 'status-error' : data.services.error_count > 0 ? 'status-warning' : 'status-healthy'}}">${{data.services.error_count}}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Memory Leak:</span>
                                    <span class="metric-value ${{data.performance.memory_leak_detected ? 'status-error' : 'status-healthy'}}">${{data.performance.memory_leak_detected ? '⚠️ Detected' : '✅ None'}}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Last Restart:</span>
                                    <span class="metric-value">${{data.services.last_restart ? new Date(data.services.last_restart).toLocaleString() : 'Never'}}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="chart-container">
                            <h3>🔄 Resource Intensive Processes</h3>
                            <div class="process-list">
                                ${{data.performance.resource_intensive_processes.map(proc => `
                                    <div class="process-item">
                                        <strong>${{proc.name}}</strong> (PID: ${{proc.pid}}) - 
                                        CPU: ${{proc.cpu_percent.toFixed(1)}}%, 
                                        Memory: ${{proc.memory_percent.toFixed(1)}}%
                                    </div>
                                `).join('')}}
                                ${{data.performance.resource_intensive_processes.length === 0 ? '<p style="color: #10b981;">✅ No resource-intensive processes detected</p>' : ''}}
                            </div>
                        </div>
                    `;
                }}
                
                // Load status on page load and refresh every 30 seconds
                loadStatus();
                setInterval(loadStatus, 30000);

                // WiFi log functions
                function showWifiLogs() {{
                    const modal = document.createElement('div');
                    modal.id = 'wifiLogsModal';
                    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; display: flex; align-items: center; justify-content: center;';

                    modal.innerHTML = `
                        <div style="background: #1e293b; padding: 20px; border-radius: 10px; max-width: 800px; max-height: 80%; overflow-y: auto; border: 1px solid #334155;">
                            <h3 style="color: #3b82f6; margin-top: 0;">📡 WiFi Connection Log</h3>
                            <div id="wifiLogsContent" style="font-family: monospace; font-size: 12px; background: #0f172a; padding: 15px; border-radius: 4px; max-height: 400px; overflow-y: scroll; color: #e2e8f0;">
                                Loading WiFi connection logs...
                            </div>
                            <div style="margin-top: 15px; text-align: right;">
                                <button onclick="hideWifiLogs()" style="background: #6b7280; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">Close</button>
                            </div>
                        </div>
                    `;

                    document.body.appendChild(modal);

                    fetch('/wifi_status')
                        .then(response => response.json())
                        .then(data => {{
                            const content = document.getElementById('wifiLogsContent');
                            if (data.status === 'success' && data.recent_logs && data.recent_logs.length > 0) {{
                                const logHtml = data.recent_logs.map(log => {{
                                    const isError = log.includes('ERROR') || log.includes('CONNECTION LOST');
                                    const isSuccess = log.includes('CONNECTION ESTABLISHED');
                                    const color = isError ? '#ef4444' : isSuccess ? '#10b981' : '#e2e8f0';
                                    return `<div style="margin-bottom: 5px; padding: 5px; border-left: 3px solid ${{color}}; color: ${{color}};">${{log}}</div>`;
                                }}).join('');
                                content.innerHTML = `
                                    <div style="margin-bottom: 10px; color: #3b82f6;"><strong>Recent WiFi Events (${{data.log_count}} entries):</strong></div>
                                    ${{logHtml}}
                                `;
                            }} else {{
                                content.innerHTML = '<div style="color: #6b7280;">No WiFi log entries found. The WiFi monitor may not be running yet.</div>';
                            }}
                        }})
                        .catch(error => {{
                            document.getElementById('wifiLogsContent').innerHTML = `<div style="color: #ef4444;">Error loading WiFi logs: ${{error}}</div>`;
                        }});
                }}

                function hideWifiLogs() {{
                    const modal = document.getElementById('wifiLogsModal');
                    if (modal) {{
                        modal.remove();
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
        return dashboard_html
        
    except Exception as e:
        return f"Error loading exhibition dashboard: {str(e)}", 500

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

if __name__ == "__main__":
    try:
        service_manager.log_event("Unified Control Panel starting")
        print(f"Starting Raspberry Pi Control Panel")
        print(f"Available modes: {', '.join(APP_MODES.keys())}")
        print(f"Current mode: {get_current_mode()}")
        print(f"Access at: http://0.0.0.0:5000")
        
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        service_manager.log_error("Fatal error in control panel", e)
        print(f"Fatal error: {e}")
        sys.exit(1)