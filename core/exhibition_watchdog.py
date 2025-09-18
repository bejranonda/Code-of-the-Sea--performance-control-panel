#!/usr/bin/env python3
"""
Exhibition Watchdog System for Code of the Sea
Provides monitoring, recovery, and stability for long-term art installations
"""

import psutil
import time
import subprocess
import logging
import json
import threading
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Fix PATH environment for subprocess calls
if '/usr/bin' not in os.environ.get('PATH', ''):
    os.environ['PATH'] = '/usr/bin:/usr/sbin:/bin:/sbin:' + os.environ.get('PATH', '')

@dataclass
class SystemHealth:
    """System health metrics"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    cpu_temperature: float
    uptime_hours: float
    network_connected: bool
    services_healthy: bool
    error_count: int
    last_restart: Optional[str] = None

class ExhibitionWatchdog:
    """
    Exhibition-grade system monitoring and recovery
    
    Features:
    - Continuous system health monitoring
    - Automatic service recovery
    - Resource cleanup
    - Hardware validation
    - Network resilience
    - Exhibition-specific optimizations
    """
    
    def __init__(self, config_path: str = "config/exhibition.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.health_history: List[SystemHealth] = []
        self.restart_count = 0
        self.last_restart = None
        self.running = False
        self.monitor_cycle = 0  # Track monitoring cycles for network check throttling
        
        # Setup logging (use local log file if /var/log not writable)
        log_file = '/var/log/cos-watchdog.log'
        try:
            # Test if we can write to /var/log
            with open(log_file, 'a'):
                pass
        except (PermissionError, FileNotFoundError):
            # Fall back to local directory
            log_file = 'logs/cos-watchdog.log'
            os.makedirs('logs', exist_ok=True)
            
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ExhibitionWatchdog')
        
    def load_config(self) -> Dict:
        """Load exhibition configuration"""
        default_config = {
            "monitoring": {
                "check_interval": 60,  # seconds
                "memory_threshold": 85,  # %
                "cpu_threshold": 90,  # %
                "disk_threshold": 95,  # %
                "temp_threshold": 75,  # °C
                "max_restarts_per_hour": 3,
                "network_check_frequency": 3,  # Check network every N cycles (reduce frequency)
                "service_timeout": 30  # seconds
            },
            "recovery": {
                "auto_restart": True,
                "cleanup_on_restart": True,
                "network_recovery": True,
                "hardware_reset": True
            },
            "maintenance": {
                "daily_restart_time": "06:00",
                "log_rotation_days": 7,
                "cleanup_temp_files": True,
                "disk_cleanup_threshold": 90
            },
            "alerts": {
                "log_critical_events": True,
                "health_check_endpoint": True
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                config = {**default_config}
                for key, value in user_config.items():
                    if key in config and isinstance(config[key], dict):
                        config[key].update(value)
                    else:
                        config[key] = value
                return config
            else:
                # Create default config file
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return default_config
    
    def get_cpu_temperature(self) -> float:
        """Get Raspberry Pi CPU temperature"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read().strip()) / 1000.0
                return temp
        except:
            return 0.0
    
    def get_system_health(self) -> SystemHealth:
        """Collect comprehensive system health metrics"""
        try:
            # Basic metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Temperature
            cpu_temp = self.get_cpu_temperature()
            
            # Uptime
            boot_time = psutil.boot_time()
            uptime_hours = (time.time() - boot_time) / 3600
            
            # Network connectivity (check less frequently to avoid conflicts)
            network_check_freq = self.config['monitoring']['network_check_frequency']
            if self.monitor_cycle % network_check_freq == 0:
                network_connected = self.check_network_connectivity()
                self._last_network_status = network_connected
            else:
                # Use cached network status
                network_connected = getattr(self, '_last_network_status', True)
            
            # Service health
            services_healthy = self.check_service_health()
            
            # Error count (from logs)
            error_count = self.get_recent_error_count()
            
            return SystemHealth(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=(disk.used / disk.total) * 100,
                cpu_temperature=cpu_temp,
                uptime_hours=uptime_hours,
                network_connected=network_connected,
                services_healthy=services_healthy,
                error_count=error_count,
                last_restart=self.last_restart
            )
        except Exception as e:
            self.logger.error(f"Error collecting system health: {e}")
            return SystemHealth(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0, memory_percent=0, disk_percent=0,
                cpu_temperature=0, uptime_hours=0,
                network_connected=False, services_healthy=False,
                error_count=999
            )

    def get_default_gateway(self) -> str:
        """Get the default gateway IP address"""
        try:
            # Method 1: Parse ip route output
            result = subprocess.run(['ip', 'route', 'show', 'default'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse output like: "default via 192.168.178.1 dev eth0 proto dhcp src 192.168.178.47 metric 100"
                for line in result.stdout.strip().split('\n'):
                    if 'default via' in line:
                        parts = line.split()
                        if len(parts) >= 3 and parts[0] == 'default' and parts[1] == 'via':
                            return parts[2]

            # Method 2: Try alternative route command
            result = subprocess.run(['route', '-n'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('0.0.0.0'):
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]

        except Exception as e:
            self.logger.warning(f"Failed to detect default gateway: {e}")

        return None

    def check_ethernet_connection(self) -> bool:
        """Check if Ethernet interface is connected and has IP"""
        try:
            # Check if eth0 interface exists and is up
            result = subprocess.run(['ip', 'link', 'show', 'eth0'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return False

            # Check if interface is UP
            if 'state UP' not in result.stdout:
                return False

            # Check if interface has an IP address
            result = subprocess.run(['ip', 'addr', 'show', 'eth0'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Look for inet address (IPv4)
                import re
                ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if ip_match:
                    self.logger.info(f"Ethernet connection detected: {ip_match.group(1)}")
                    return True

            return False

        except Exception as e:
            self.logger.warning(f"Error checking ethernet connection: {e}")
            return False

    def check_network_connectivity(self) -> bool:
        """Check comprehensive network connectivity"""
        try:
            # Test 1: Check local gateway (dynamically detected)
            gateway_ip = self.get_default_gateway()
            if gateway_ip:
                gateway_result = subprocess.run(
                    ['ping', '-c', '1', '-W', '3', gateway_ip],
                    capture_output=True, timeout=5
                )
            else:
                # Fallback if gateway detection fails
                gateway_result = subprocess.run(
                    ['ping', '-c', '1', '-W', '3', '8.8.8.8'],
                    capture_output=True, timeout=5
                )
            
            # Test 2: Check DNS resolution
            try:
                dns_result = subprocess.run(
                    ['nslookup', 'google.com'],
                    capture_output=True, timeout=5
                )
            except FileNotFoundError:
                # Fallback to dig if nslookup not available
                try:
                    dns_result = subprocess.run(
                        ['dig', '+short', 'google.com'],
                        capture_output=True, timeout=5
                    )
                except FileNotFoundError:
                    # Skip DNS test if neither command available
                    dns_result = subprocess.run(['true'], capture_output=True)
            
            # Test 3: Check internet connectivity
            internet_result = subprocess.run(
                ['ping', '-c', '1', '-W', '3', '8.8.8.8'],
                capture_output=True, timeout=5
            )
            
            gateway_ok = gateway_result.returncode == 0
            dns_ok = dns_result.returncode == 0
            internet_ok = internet_result.returncode == 0
            
            # Check if we have Ethernet connection as well
            eth_connected = self.check_ethernet_connection()

            # Log specific connectivity issues
            if not gateway_ok:
                self.logger.warning(f"Local network gateway unreachable (tested: {gateway_ip or '8.8.8.8'})")
            if not dns_ok:
                self.logger.warning("DNS resolution failed")
            if not internet_ok:
                self.logger.warning("Internet connectivity failed")

            # Overall connectivity - require at least gateway OR internet access OR ethernet
            # This ensures LAN connections are properly detected
            return gateway_ok or internet_ok or eth_connected
            
        except Exception as e:
            self.logger.error(f"Error checking network connectivity: {e}")
            return False
    
    def get_network_interface_status(self) -> Dict[str, bool]:
        """Get status of network interfaces"""
        try:
            interfaces = {}
            
            # Check WiFi interface
            wifi_result = subprocess.run(
                ['iwconfig', 'wlan0'],
                capture_output=True, text=True
            )
            interfaces['wlan0'] = 'Access Point:' in wifi_result.stdout
            
            # Check Ethernet interface  
            eth_result = subprocess.run(
                ['ip', 'link', 'show', 'eth0'],
                capture_output=True, text=True
            )
            interfaces['eth0'] = 'UP' in eth_result.stdout
            
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Error getting interface status: {e}")
            return {}
    
    def get_wifi_signal_strength(self) -> int:
        """Get WiFi signal strength"""
        try:
            result = subprocess.run(
                ['iwconfig', 'wlan0'],
                capture_output=True, text=True
            )

            for line in result.stdout.split('\n'):
                if 'Signal level=' in line:
                    # Extract signal level (e.g., "Signal level=-45 dBm")
                    parts = line.split('Signal level=')[1].split()[0]
                    signal_dbm = int(parts.replace('dBm', ''))

                    # Convert dBm to percentage (rough approximation)
                    if signal_dbm >= -50:
                        return 100
                    elif signal_dbm >= -60:
                        return 80
                    elif signal_dbm >= -70:
                        return 60
                    elif signal_dbm >= -80:
                        return 40
                    else:
                        return 20

            return 0

        except Exception as e:
            self.logger.error(f"Error getting WiFi signal: {e}")
            return 0

    def get_detailed_wifi_diagnostics(self) -> Dict:
        """Get comprehensive WiFi diagnostics for troubleshooting instability"""
        try:
            diagnostics = {
                'timestamp': datetime.now().isoformat(),
                'connection_status': {},
                'signal_info': {},
                'power_management': {},
                'driver_info': {},
                'network_config': {},
                'interference': {},
                'errors': []
            }

            # 1. Connection Status
            try:
                iwconfig_result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
                if iwconfig_result.returncode == 0:
                    output = iwconfig_result.stdout
                    diagnostics['connection_status']['connected'] = 'Access Point:' in output and 'Not-Associated' not in output

                    # Extract SSID
                    for line in output.split('\n'):
                        if 'ESSID:' in line:
                            essid = line.split('ESSID:')[1].strip().strip('"')
                            diagnostics['connection_status']['ssid'] = essid
                        if 'Frequency:' in line:
                            freq = line.split('Frequency:')[1].split()[0]
                            diagnostics['connection_status']['frequency'] = freq
                        if 'Bit Rate=' in line:
                            bitrate = line.split('Bit Rate=')[1].split()[0]
                            diagnostics['connection_status']['bit_rate'] = bitrate
                        if 'Tx-Power=' in line:
                            power = line.split('Tx-Power=')[1].split()[0]
                            diagnostics['connection_status']['tx_power'] = power
            except Exception as e:
                diagnostics['errors'].append(f"iwconfig error: {str(e)}")

            # 2. Signal Quality and Interference
            try:
                signal_result = subprocess.run(['cat', '/proc/net/wireless'], capture_output=True, text=True)
                if signal_result.returncode == 0:
                    for line in signal_result.stdout.split('\n'):
                        if 'wlan0:' in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                diagnostics['signal_info']['link_quality'] = parts[2]
                                diagnostics['signal_info']['signal_level'] = parts[3]
                                diagnostics['signal_info']['noise_level'] = parts[4] if len(parts) > 4 else 'N/A'
            except Exception as e:
                diagnostics['errors'].append(f"Signal info error: {str(e)}")

            # 3. Power Management Status
            try:
                pm_result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
                if pm_result.returncode == 0:
                    pm_enabled = 'Power Management:on' in pm_result.stdout
                    diagnostics['power_management']['enabled'] = pm_enabled
                    if pm_enabled:
                        diagnostics['power_management']['warning'] = "Power management is ON - this can cause disconnections"
            except Exception as e:
                diagnostics['errors'].append(f"Power management check error: {str(e)}")

            # 4. Driver and Hardware Info
            try:
                lsusb_result = subprocess.run(['lsusb'], capture_output=True, text=True)
                if lsusb_result.returncode == 0:
                    wifi_devices = [line for line in lsusb_result.stdout.split('\n') if any(wifi in line.lower() for wifi in ['wifi', 'wireless', 'wlan', 'realtek', 'broadcom'])]
                    diagnostics['driver_info']['usb_devices'] = wifi_devices

                dmesg_result = subprocess.run(['dmesg', '|', 'tail', '-20'], shell=True, capture_output=True, text=True)
                if dmesg_result.returncode == 0:
                    wifi_messages = [line for line in dmesg_result.stdout.split('\n') if 'wlan0' in line.lower()][-5:]
                    diagnostics['driver_info']['recent_kernel_messages'] = wifi_messages
            except Exception as e:
                diagnostics['errors'].append(f"Driver info error: {str(e)}")

            # 5. Network Configuration
            try:
                ip_result = subprocess.run(['ip', 'addr', 'show', 'wlan0'], capture_output=True, text=True)
                if ip_result.returncode == 0:
                    has_ip = 'inet ' in ip_result.stdout
                    is_up = 'UP' in ip_result.stdout
                    diagnostics['network_config']['has_ip_address'] = has_ip
                    diagnostics['network_config']['interface_up'] = is_up

                    # Extract IP address
                    for line in ip_result.stdout.split('\n'):
                        if 'inet ' in line and 'scope global' in line:
                            ip_addr = line.split('inet ')[1].split('/')[0].strip()
                            diagnostics['network_config']['ip_address'] = ip_addr

                # Check routing
                route_result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
                if route_result.returncode == 0:
                    has_default_route = 'wlan0' in route_result.stdout
                    diagnostics['network_config']['has_default_route'] = has_default_route
                    if has_default_route:
                        gateway = route_result.stdout.split('via ')[1].split()[0]
                        diagnostics['network_config']['gateway'] = gateway

            except Exception as e:
                diagnostics['errors'].append(f"Network config error: {str(e)}")

            # 6. Connection Stability Metrics
            try:
                # Get interface statistics
                stats_result = subprocess.run(['cat', f'/sys/class/net/wlan0/statistics/rx_dropped'], capture_output=True, text=True)
                if stats_result.returncode == 0:
                    diagnostics['interference']['rx_dropped'] = int(stats_result.stdout.strip())

                stats_result = subprocess.run(['cat', f'/sys/class/net/wlan0/statistics/tx_errors'], capture_output=True, text=True)
                if stats_result.returncode == 0:
                    diagnostics['interference']['tx_errors'] = int(stats_result.stdout.strip())

                # Check for nearby networks (interference)
                scan_result = subprocess.run(['iwlist', 'wlan0', 'scan'], capture_output=True, text=True, timeout=10)
                if scan_result.returncode == 0:
                    networks = len([line for line in scan_result.stdout.split('\n') if 'ESSID:' in line])
                    diagnostics['interference']['nearby_networks_count'] = networks

                    # Count networks on same channel
                    current_freq = diagnostics['connection_status'].get('frequency', '')
                    same_channel = len([line for line in scan_result.stdout.split('\n') if current_freq in line])
                    diagnostics['interference']['same_channel_networks'] = same_channel

            except Exception as e:
                diagnostics['errors'].append(f"Interference check error: {str(e)}")

            # Log comprehensive diagnostics
            self.logger.info(f"WiFi Diagnostics: Connection={diagnostics['connection_status'].get('connected', False)}, "
                           f"Signal={diagnostics['signal_info'].get('signal_level', 'N/A')}, "
                           f"PowerMgmt={diagnostics['power_management'].get('enabled', 'Unknown')}, "
                           f"IP={diagnostics['network_config'].get('has_ip_address', False)}, "
                           f"Errors={len(diagnostics['errors'])}")

            return diagnostics

        except Exception as e:
            self.logger.error(f"Error in WiFi diagnostics: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def check_service_health(self) -> bool:
        """Check if main service is running and responding (but don't restart individual services)"""
        try:
            # Check if systemd service is active
            result = subprocess.run(
                ['systemctl', 'is-active', 'cos-control-panel'],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                return False

            # Check if web interface is responding
            try:
                import requests
                response = requests.get('http://localhost:5000/exhibition/health', timeout=5)
                return response.status_code == 200
            except:
                # If requests fails, try curl
                curl_result = subprocess.run(
                    ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                     'http://localhost:5000/', '--connect-timeout', '3'],
                    capture_output=True, text=True
                )
                return curl_result.stdout.strip() == '200'

        except Exception as e:
            self.logger.warning(f"Service health check failed: {e}")
            return False
    
    def get_recent_error_count(self) -> int:
        """Count recent errors in logs"""
        try:
            # Check systemd logs for the last hour
            result = subprocess.run([
                'journalctl', '-u', 'cos-control-panel', 
                '--since', '1 hour ago', '--no-pager'
            ], capture_output=True, text=True)
            
            error_lines = [line for line in result.stdout.split('\\n') 
                          if any(keyword in line.lower() 
                                for keyword in ['error', 'failed', 'exception'])]
            return len(error_lines)
        except:
            return 0
    
    def restart_service(self, reason: str):
        """Restart the main service with recovery procedures"""
        if not self.config['recovery']['auto_restart']:
            self.logger.warning(f"Auto-restart disabled. Reason: {reason}")
            return
        
        # Check restart limits
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        recent_restarts = sum(1 for h in self.health_history 
                            if h.last_restart and 
                            datetime.fromisoformat(h.last_restart) > hour_ago)
        
        if recent_restarts >= self.config['monitoring']['max_restarts_per_hour']:
            self.logger.error(f"Too many restarts in the last hour. Not restarting.")
            return
        
        self.logger.warning(f"Restarting service: {reason}")
        
        try:
            # Cleanup before restart
            if self.config['recovery']['cleanup_on_restart']:
                self.cleanup_system()
            
            # Stop service
            subprocess.run(['sudo', 'systemctl', 'stop', 'cos-control-panel'], 
                         timeout=10)
            
            # Clean up processes
            subprocess.run(['sudo', 'pkill', '-f', 'mpg123'], 
                         capture_output=True)
            
            # Wait a moment
            time.sleep(3)
            
            # Start service
            result = subprocess.run(['sudo', 'systemctl', 'start', 'cos-control-panel'], 
                                  timeout=30)
            
            if result.returncode == 0:
                self.restart_count += 1
                self.last_restart = datetime.now().isoformat()
                self.logger.info(f"Service restarted successfully (count: {self.restart_count})")
            else:
                self.logger.error("Failed to restart service")
                
        except Exception as e:
            self.logger.error(f"Error during service restart: {e}")
    
    def cleanup_system(self):
        """Perform comprehensive system cleanup"""
        try:
            # Clean temporary files
            subprocess.run(['find', '/tmp', '-name', 'mpg_pid_*', '-delete'], 
                         capture_output=True)
            subprocess.run(['find', '/tmp', '-name', 'play_*.sh', '-delete'], 
                         capture_output=True)
            
            # Clean old audio temp files
            subprocess.run(['find', '/tmp', '-name', '*.mpg', '-mtime', '+1', '-delete'], 
                         capture_output=True)
            
            # Clean systemd journal if it's getting large
            subprocess.run(['sudo', 'journalctl', '--vacuum-size=100M'], 
                         capture_output=True)
            
            # Clear memory caches (safe operation)
            subprocess.run(['sudo', 'sync'], capture_output=True)
            subprocess.run(['sudo', 'sysctl', 'vm.drop_caches=1'], capture_output=True)
            
            # Clean old logs if disk usage is high
            if self.get_system_health().disk_percent > self.config['maintenance']['disk_cleanup_threshold']:
                subprocess.run([
                    'find', '/home/payas/cos', '-name', '*.log', 
                    '-mtime', '+3', '-delete'
                ], capture_output=True)
                
                # Clean old health data
                subprocess.run(['find', '/tmp', '-name', 'cos_health*.json', '-mtime', '+1', '-delete'],
                             capture_output=True)
                
            # Kill zombie processes
            self.kill_zombie_processes()
            
            self.logger.info("System cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during system cleanup: {e}")
    
    def kill_zombie_processes(self):
        """Kill any stuck processes that might be consuming resources"""
        try:
            # Kill any orphaned mpg123 processes
            subprocess.run(['sudo', 'pkill', '-f', 'mpg123'], capture_output=True)
            
            # Kill any stuck Python processes older than 1 hour
            result = subprocess.run([
                'ps', 'aux', '--sort=-etime'
            ], capture_output=True, text=True)
            
            for line in result.stdout.split('\n'):
                if 'python' in line.lower() and 'cos' in line:
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        # Check if process has been running for more than 2 hours
                        # This is a safety measure for stuck processes
                        try:
                            process = psutil.Process(int(pid))
                            create_time = process.create_time()
                            if time.time() - create_time > 7200:  # 2 hours
                                self.logger.warning(f"Killing long-running process {pid}")
                                process.terminate()
                        except (psutil.NoSuchProcess, ValueError):
                            continue
                            
        except Exception as e:
            self.logger.error(f"Error killing zombie processes: {e}")
    
    def check_memory_leaks(self) -> bool:
        """Check for potential memory leaks"""
        try:
            # Check if memory usage is consistently high
            if len(self.health_history) < 10:
                return False
                
            recent_memory = [h.memory_percent for h in self.health_history[-10:]]
            avg_memory = sum(recent_memory) / len(recent_memory)
            
            # If average memory usage over last 10 checks is > 80%
            if avg_memory > 80:
                # Check if it's increasing trend
                first_half = sum(recent_memory[:5]) / 5
                second_half = sum(recent_memory[5:]) / 5
                
                if second_half > first_half + 5:  # 5% increase trend
                    self.logger.warning(f"Memory leak detected: {first_half:.1f}% -> {second_half:.1f}%")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Error checking memory leaks: {e}")
            
        return False
    
    def get_resource_intensive_processes(self) -> List[Dict]:
        """Get list of processes using excessive resources"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    # Focus on processes using > 10% CPU or > 20% memory
                    if info['cpu_percent'] > 10 or info['memory_percent'] > 20:
                        processes.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by memory usage
            return sorted(processes, key=lambda x: x['memory_percent'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error getting resource intensive processes: {e}")
            return []
    
    def recover_hardware(self):
        """Attempt comprehensive hardware recovery procedures"""
        try:
            self.logger.info("Starting hardware recovery procedures")
            
            # Test and recover I2C bus
            if not self.test_i2c_devices():
                self.recover_i2c_bus()
            
            # Test and recover GPIO
            if not self.test_gpio_devices():
                self.recover_gpio_devices()
            
            # Test hardware sensors
            self.test_hardware_sensors()
            
            self.logger.info("Hardware recovery procedures completed")
            
        except Exception as e:
            self.logger.error(f"Error during hardware recovery: {e}")
    
    def test_i2c_devices(self) -> bool:
        """Test I2C devices connectivity"""
        try:
            # Test VEML7700 light sensor (default address 0x10)
            veml_result = subprocess.run(
                ['i2cdetect', '-y', '1', '0x10', '0x10'],
                capture_output=True, text=True
            )
            veml_available = '10' in veml_result.stdout
            
            # Test TEA5767 FM radio (address 0x60) 
            tea_result = subprocess.run(
                ['i2cdetect', '-y', '1', '0x60', '0x60'],
                capture_output=True, text=True
            )
            tea_available = '60' in tea_result.stdout
            
            if not veml_available:
                self.logger.warning("VEML7700 light sensor not detected on I2C")
            if not tea_available:
                self.logger.warning("TEA5767 FM radio not detected on I2C")
                
            return veml_available or tea_available  # At least one device working
            
        except Exception as e:
            self.logger.error(f"Error testing I2C devices: {e}")
            return False
    
    def recover_i2c_bus(self):
        """Recover I2C bus functionality"""
        try:
            self.logger.info("Attempting I2C bus recovery")
            
            # Method 1: Reload I2C drivers
            subprocess.run(['sudo', 'modprobe', '-r', 'i2c_bcm2835'], capture_output=True)
            subprocess.run(['sudo', 'modprobe', '-r', 'i2c_dev'], capture_output=True)
            time.sleep(2)
            subprocess.run(['sudo', 'modprobe', 'i2c_dev'], capture_output=True)
            subprocess.run(['sudo', 'modprobe', 'i2c_bcm2835'], capture_output=True)
            time.sleep(2)
            
            # Method 2: Reset I2C bus using GPIO bit-banging (software recovery)
            # Toggle clock line to clear any stuck devices
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(3, GPIO.OUT)  # I2C1 SCL (GPIO3)
                
                # Generate 9 clock pulses to clear stuck devices
                for _ in range(9):
                    GPIO.output(3, GPIO.LOW)
                    time.sleep(0.001)
                    GPIO.output(3, GPIO.HIGH)
                    time.sleep(0.001)
                    
                GPIO.cleanup()
            except ImportError:
                self.logger.warning("RPi.GPIO not available for I2C recovery")
            
            # Verify recovery
            if self.test_i2c_devices():
                self.logger.info("I2C bus recovery successful")
            else:
                self.logger.error("I2C bus recovery failed")
                
        except Exception as e:
            self.logger.error(f"Error during I2C recovery: {e}")
    
    def test_gpio_devices(self) -> bool:
        """Test GPIO devices functionality"""
        try:
            # Test GPIO18 (Fan PWM pin) - check if it's accessible
            gpio18_path = '/sys/class/gpio/gpio18'
            
            # Test if we can access the GPIO export
            test_result = subprocess.run(
                ['ls', '/sys/class/gpio/'],
                capture_output=True, text=True
            )
            
            gpio_accessible = 'export' in test_result.stdout
            
            if not gpio_accessible:
                self.logger.warning("GPIO system not accessible")
                return False
            
            # Test PWM functionality (if available)
            pwm_result = subprocess.run(
                ['ls', '/sys/class/pwm/'],
                capture_output=True, text=True
            )
            
            pwm_available = 'pwmchip' in pwm_result.stdout
            
            if not pwm_available:
                # Only log PWM warning once per hour to avoid spam
                if not hasattr(self, '_last_pwm_warning') or \
                   time.time() - self._last_pwm_warning > 3600:
                    self.logger.warning("PWM system not available")
                    self._last_pwm_warning = time.time()
                
            return gpio_accessible
            
        except Exception as e:
            self.logger.error(f"Error testing GPIO devices: {e}")
            return False
    
    def recover_gpio_devices(self):
        """Recover GPIO functionality"""
        try:
            self.logger.info("Attempting GPIO recovery")
            
            # Reset GPIO state - unexport all our pins first
            gpio_pins = [18]  # Fan control pin
            
            for pin in gpio_pins:
                try:
                    subprocess.run(
                        ['echo', str(pin)], 
                        stdout=open('/sys/class/gpio/unexport', 'w'),
                        stderr=subprocess.DEVNULL
                    )
                except:
                    pass  # Pin might not be exported
            
            time.sleep(1)
            
            # Re-export pins
            for pin in gpio_pins:
                try:
                    subprocess.run(
                        ['echo', str(pin)], 
                        stdout=open('/sys/class/gpio/export', 'w'),
                        stderr=subprocess.DEVNULL
                    )
                except:
                    pass
            
            # Verify recovery
            if self.test_gpio_devices():
                self.logger.info("GPIO recovery successful")
            else:
                self.logger.error("GPIO recovery failed")
                
        except Exception as e:
            self.logger.error(f"Error during GPIO recovery: {e}")
    
    def test_hardware_sensors(self):
        """Test hardware sensors and log status"""
        try:
            # Test CPU temperature sensor
            cpu_temp = self.get_cpu_temperature()
            if cpu_temp > 0:
                self.logger.info(f"CPU temperature sensor working: {cpu_temp:.1f}°C")
            else:
                self.logger.warning("CPU temperature sensor not working")
            
            # Test memory
            memory = psutil.virtual_memory()
            if memory.total > 0:
                self.logger.info(f"Memory sensor working: {memory.percent:.1f}% used")
            else:
                self.logger.warning("Memory monitoring not working")
                
        except Exception as e:
            self.logger.error(f"Error testing hardware sensors: {e}")
    
    def check_hardware_health(self) -> bool:
        """Comprehensive hardware health check"""
        try:
            i2c_ok = self.test_i2c_devices()
            gpio_ok = self.test_gpio_devices()
            
            # Check for hardware-specific errors in logs
            result = subprocess.run([
                'dmesg', '-T', '--since', '1 hour ago'
            ], capture_output=True, text=True)
            
            hardware_errors = []
            for line in result.stdout.split('\n'):
                if any(keyword in line.lower() for keyword in [
                    'i2c', 'gpio', 'hardware', 'usb', 'thermal', 'voltage'
                ]):
                    if any(error in line.lower() for error in [
                        'error', 'fail', 'timeout', 'reset', 'disconnect'
                    ]):
                        hardware_errors.append(line.strip())
            
            if hardware_errors:
                self.logger.warning(f"Hardware errors detected: {len(hardware_errors)} entries")
                # Log first few errors
                for error in hardware_errors[:3]:
                    self.logger.warning(f"Hardware error: {error}")
            
            return i2c_ok and gpio_ok and len(hardware_errors) < 5
            
        except Exception as e:
            self.logger.error(f"Error checking hardware health: {e}")
            return False
    
    def recover_network(self):
        """Attempt comprehensive network recovery"""
        try:
            self.logger.info("Starting network recovery procedures")
            
            # Get current network status
            interfaces = self.get_network_interface_status()
            wifi_signal = self.get_wifi_signal_strength()
            
            self.logger.info(f"Network interfaces: {interfaces}")
            self.logger.info(f"WiFi signal strength: {wifi_signal}%")
            
            # Step 1: Restart WiFi interface
            if 'wlan0' in interfaces:
                self.logger.info("Restarting WiFi interface")
                subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'], timeout=10)
                time.sleep(3)
                subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'], timeout=10)
                time.sleep(5)
            
            # Step 2: Restart wpa_supplicant (WiFi authentication)
            self.logger.info("Restarting wpa_supplicant")
            subprocess.run(['sudo', 'systemctl', 'restart', 'wpa_supplicant'], timeout=30)
            time.sleep(5)
            
            # Step 3: Restart DHCP client
            self.logger.info("Restarting DHCP client")
            subprocess.run(['sudo', 'dhclient', '-r', 'wlan0'], timeout=10)
            subprocess.run(['sudo', 'dhclient', 'wlan0'], timeout=20)
            time.sleep(5)
            
            # Step 4: Restart networking service
            self.logger.info("Restarting networking service")
            subprocess.run(['sudo', 'systemctl', 'restart', 'networking'], timeout=30)
            time.sleep(10)
            
            # Step 5: Check if recovery worked
            if self.check_network_connectivity():
                self.logger.info("Network recovery successful")
            else:
                self.logger.error("Network recovery failed - trying alternative methods")
                self.alternative_network_recovery()
            
        except Exception as e:
            self.logger.error(f"Error during network recovery: {e}")
    
    def alternative_network_recovery(self):
        """Alternative network recovery methods"""
        try:
            # Method 1: Reset network manager (if available)
            try:
                subprocess.run(['sudo', 'systemctl', 'restart', 'NetworkManager'], timeout=30)
                time.sleep(10)
                if self.check_network_connectivity():
                    self.logger.info("Network recovered via NetworkManager restart")
                    return
            except:
                pass
            
            # Method 2: Reset entire network stack
            self.logger.info("Attempting full network stack reset")
            subprocess.run(['sudo', 'systemctl', 'stop', 'networking'], timeout=15)
            subprocess.run(['sudo', 'systemctl', 'stop', 'wpa_supplicant'], timeout=15)
            time.sleep(3)
            subprocess.run(['sudo', 'systemctl', 'start', 'wpa_supplicant'], timeout=15)
            subprocess.run(['sudo', 'systemctl', 'start', 'networking'], timeout=30)
            time.sleep(15)
            
            # Method 3: Manual WiFi reconnection
            if not self.check_network_connectivity():
                self.manual_wifi_reconnect()
                
        except Exception as e:
            self.logger.error(f"Error in alternative network recovery: {e}")
    
    def manual_wifi_reconnect(self):
        """Manual WiFi reconnection procedure"""
        try:
            self.logger.info("Attempting manual WiFi reconnection")
            
            # Kill existing wpa_supplicant processes
            subprocess.run(['sudo', 'pkill', 'wpa_supplicant'], capture_output=True)
            time.sleep(2)
            
            # Start wpa_supplicant with config file
            # Assuming standard Raspberry Pi configuration
            wpa_config = '/etc/wpa_supplicant/wpa_supplicant.conf'
            if os.path.exists(wpa_config):
                subprocess.run([
                    'sudo', 'wpa_supplicant', '-B', '-i', 'wlan0', 
                    '-c', wpa_config, '-D', 'nl80211'
                ], timeout=15)
                time.sleep(5)
                
                # Request DHCP
                subprocess.run(['sudo', 'dhclient', 'wlan0'], timeout=20)
                time.sleep(10)
                
                if self.check_network_connectivity():
                    self.logger.info("Manual WiFi reconnection successful")
                else:
                    self.logger.error("Manual WiFi reconnection failed")
            else:
                self.logger.error("WiFi configuration file not found")
                
        except Exception as e:
            self.logger.error(f"Error in manual WiFi reconnect: {e}")
    
    def monitor_network_stability(self) -> Dict[str, any]:
        """Monitor network stability over time with detailed diagnostics"""
        try:
            # Count recent network disconnections
            network_history = [h.network_connected for h in self.health_history[-20:]]
            disconnections = sum(1 for i in range(1, len(network_history))
                               if network_history[i-1] and not network_history[i])

            # Get current status
            signal_strength = self.get_wifi_signal_strength()
            interfaces = self.get_network_interface_status()

            stability_info = {
                'recent_disconnections': disconnections,
                'signal_strength': signal_strength,
                'interfaces_up': interfaces,
                'stability_score': max(0, 100 - (disconnections * 10) - max(0, 50 - signal_strength))
            }

            # Trigger detailed diagnostics if instability detected
            if disconnections > 2 or signal_strength < 30:
                self.logger.warning(f"Network instability detected: {disconnections} disconnections, signal: {signal_strength}%")

                # Run comprehensive diagnostics
                diagnostics = self.get_detailed_wifi_diagnostics()

                # Log key findings
                if diagnostics.get('power_management', {}).get('enabled', False):
                    self.logger.error("WiFi ISSUE: Power management is enabled - this causes disconnections!")

                if diagnostics.get('interference', {}).get('tx_errors', 0) > 100:
                    self.logger.warning(f"WiFi ISSUE: High TX errors detected: {diagnostics['interference']['tx_errors']}")

                if diagnostics.get('interference', {}).get('nearby_networks_count', 0) > 10:
                    self.logger.warning(f"WiFi ISSUE: High interference - {diagnostics['interference']['nearby_networks_count']} nearby networks")

                if not diagnostics.get('network_config', {}).get('has_default_route', True):
                    self.logger.error("WiFi ISSUE: No default route configured")

                # Save detailed diagnostics to file for later analysis
                wifi_diag_file = f"/home/payas/cos/logs/wifi_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                os.makedirs(os.path.dirname(wifi_diag_file), exist_ok=True)
                with open(wifi_diag_file, 'w') as f:
                    json.dump(diagnostics, f, indent=2)

                self.logger.info(f"Detailed WiFi diagnostics saved to: {wifi_diag_file}")

                # Add diagnostics summary to stability info
                stability_info['diagnostics_available'] = True
                stability_info['diagnostics_file'] = wifi_diag_file
                stability_info['key_issues'] = [
                    "Power management enabled" if diagnostics.get('power_management', {}).get('enabled', False) else None,
                    f"High TX errors ({diagnostics.get('interference', {}).get('tx_errors', 0)})" if diagnostics.get('interference', {}).get('tx_errors', 0) > 100 else None,
                    f"High interference ({diagnostics.get('interference', {}).get('nearby_networks_count', 0)} networks)" if diagnostics.get('interference', {}).get('nearby_networks_count', 0) > 10 else None,
                    "No default route" if not diagnostics.get('network_config', {}).get('has_default_route', True) else None
                ]
                # Remove None values
                stability_info['key_issues'] = [issue for issue in stability_info['key_issues'] if issue is not None]

            elif disconnections > 0:
                self.logger.info(f"Minor network instability: {disconnections} recent disconnections")
            
            if signal_strength < 30:
                self.logger.warning(f"Weak WiFi signal: {signal_strength}%")
                
            return stability_info
            
        except Exception as e:
            self.logger.error(f"Error monitoring network stability: {e}")
            return {'error': str(e)}
    
    def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info("Exhibition watchdog started")

        while self.running:
            try:
                # Increment cycle counter
                self.monitor_cycle += 1

                # Collect health metrics
                health = self.get_system_health()
                self.health_history.append(health)
                
                # Keep only recent history (last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.health_history = [
                    h for h in self.health_history 
                    if datetime.fromisoformat(h.timestamp) > cutoff_time
                ]
                
                # Check thresholds and take action
                self.check_thresholds(health)
                
                # Log health status
                if health.error_count > 0 or not health.services_healthy:
                    self.logger.warning(f"Health check: CPU:{health.cpu_percent:.1f}% "
                                      f"MEM:{health.memory_percent:.1f}% "
                                      f"TEMP:{health.cpu_temperature:.1f}°C "
                                      f"ERRORS:{health.error_count}")
                
                # Save health data for web interface
                self.save_health_data(health)
                
                # Sleep until next check
                time.sleep(self.config['monitoring']['check_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait before retrying
    
    def check_thresholds(self, health: SystemHealth):
        """Check health thresholds and take corrective action"""
        config = self.config['monitoring']
        
        # High memory usage
        if health.memory_percent > config['memory_threshold']:
            self.logger.warning(f"High memory usage: {health.memory_percent}%")
            
            # Log resource intensive processes
            intensive_procs = self.get_resource_intensive_processes()
            if intensive_procs:
                self.logger.warning(f"Resource intensive processes: {intensive_procs[:3]}")
            
            # Check for memory leaks before restarting
            if self.check_memory_leaks():
                self.logger.warning("Memory leak pattern detected, forcing cleanup")
                self.cleanup_system()
            
            self.restart_service("High memory usage")
            return
        
        # High CPU usage (sustained)
        if health.cpu_percent > config['cpu_threshold']:
            self.logger.warning(f"High CPU usage: {health.cpu_percent}%")
            # Don't restart immediately for CPU, wait for pattern
        
        # High temperature
        if health.cpu_temperature > config['temp_threshold']:
            self.logger.warning(f"High temperature: {health.cpu_temperature}°C")
            # Could trigger fan control or throttling
        
        # Service not healthy (only restart main unified app, not individual services)
        if not health.services_healthy:
            self.logger.warning("Main unified service health check failed")
            # Only restart the main control panel service, not individual services
            # Individual services should be managed by the user via dashboard
            self.restart_service("Main unified service health check failed")
            return
        
        # High error count
        if health.error_count > 10:
            self.logger.warning(f"High error count: {health.error_count}")
            self.restart_service("High error count")
            return
        
        # Network connectivity lost
        if not health.network_connected and self.config['recovery']['network_recovery']:
            self.logger.warning("Network connectivity lost")
            self.recover_network()
        
        # Hardware health issues
        if self.config['recovery'].get('hardware_reset', True):
            hardware_ok = self.check_hardware_health()
            if not hardware_ok:
                self.logger.warning("Hardware issues detected")
                self.recover_hardware()
    
    def save_health_data(self, health: SystemHealth):
        """Save health data for web interface"""
        try:
            health_file = '/tmp/cos_health.json'
            with open(health_file, 'w') as f:
                json.dump(asdict(health), f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving health data: {e}")
    
    def start(self):
        """Start the watchdog in a separate thread"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Exhibition watchdog thread started")
    
    def stop(self):
        """Stop the watchdog"""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        self.logger.info("Exhibition watchdog stopped")

# Global instance
_watchdog = None

def get_watchdog() -> ExhibitionWatchdog:
    """Get global watchdog instance"""
    global _watchdog
    if _watchdog is None:
        _watchdog = ExhibitionWatchdog()
    return _watchdog

def start_watchdog():
    """Start the exhibition watchdog"""
    watchdog = get_watchdog()
    watchdog.start()
    return watchdog

if __name__ == "__main__":
    # Run as standalone script
    watchdog = ExhibitionWatchdog()
    watchdog.running = True
    try:
        watchdog.monitor_loop()
    except KeyboardInterrupt:
        print("Watchdog stopped by user")
        watchdog.stop()