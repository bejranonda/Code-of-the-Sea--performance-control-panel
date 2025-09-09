import psutil
import time
import os
from typing import Dict, Any, Optional


class HardwareMonitor:
    """Hardware monitoring utilities for Raspberry Pi"""
    
    def __init__(self):
        self.temp_sensor_path = "/sys/class/thermal/thermal_zone0/temp"
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information"""
        try:
            return {
                'load_avg': list(psutil.getloadavg()),
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count()
            }
        except Exception as e:
            return {
                'load_avg': [0, 0, 0],
                'percent': 0,
                'count': 1,
                'error': str(e)
            }
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        try:
            mem = psutil.virtual_memory()
            return {
                'total': mem.total,
                'available': mem.available,
                'percent': mem.percent,
                'used': mem.used,
                'free': mem.free,
                'total_gb': round(mem.total / (1024**3), 2),
                'used_gb': round(mem.used / (1024**3), 2),
                'free_gb': round(mem.free / (1024**3), 2)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_disk_info(self) -> Dict[str, Any]:
        """Get disk usage information"""
        try:
            disk = psutil.disk_usage('/')
            return {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100,
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network I/O information"""
        try:
            net = psutil.net_io_counters()
            return {
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
                'packets_sent': net.packets_sent,
                'packets_recv': net.packets_recv,
                'bytes_sent_mb': round(net.bytes_sent / (1024**2), 2),
                'bytes_recv_mb': round(net.bytes_recv / (1024**2), 2)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_temperature(self) -> Optional[float]:
        """Get CPU temperature from Raspberry Pi sensor"""
        try:
            if os.path.exists(self.temp_sensor_path):
                with open(self.temp_sensor_path, "r") as f:
                    return round(float(f.read()) / 1000.0, 1)
        except Exception:
            pass
        return None
    
    def get_uptime(self) -> Dict[str, Any]:
        """Get system uptime information"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            return {
                'total_seconds': int(uptime_seconds),
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'formatted': f"{days}d {hours}h {minutes}m"
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_process_count(self, processes: Dict) -> int:
        """Get count of active processes being managed"""
        try:
            return len([p for p in processes.values() if psutil.pid_exists(p.pid)])
        except Exception:
            return 0
    
    def get_comprehensive_info(self, processes: Dict = None) -> Dict[str, Any]:
        """Get all hardware information in one call"""
        processes = processes or {}
        
        cpu_info = self.get_cpu_info()
        memory_info = self.get_memory_info()
        disk_info = self.get_disk_info()
        uptime_info = self.get_uptime()
        
        return {
            # Flatten CPU info for template compatibility
            'cpu_percent': cpu_info.get('percent', 0),
            'cpu_load': cpu_info.get('load_avg', [0, 0, 0]),
            'cpu_count': cpu_info.get('count', 1),
            
            # Keep structured data as well
            'cpu': cpu_info,
            'memory': memory_info,
            'disk': disk_info,
            'network': self.get_network_info(),
            
            # Flatten commonly used values for template
            'cpu_temp': self.get_temperature(),
            'uptime_hours': uptime_info.get('hours', 0),
            'uptime_minutes': uptime_info.get('minutes', 0),
            'uptime': uptime_info,
            
            'gpio_in_use': self.get_process_count(processes),
            'active_processes': self.get_process_count(processes),
            'timestamp': time.time()
        }
    
    def is_system_healthy(self, thresholds: Dict[str, float] = None) -> Dict[str, Any]:
        """Check if system is within healthy parameters"""
        if thresholds is None:
            thresholds = {
                'cpu_percent': 80.0,
                'memory_percent': 85.0,
                'disk_percent': 90.0,
                'temperature': 70.0
            }
        
        info = self.get_comprehensive_info()
        health = {
            'overall': True,
            'issues': [],
            'warnings': []
        }
        
        # Check CPU
        if info['cpu'].get('percent', 0) > thresholds['cpu_percent']:
            health['issues'].append(f"High CPU usage: {info['cpu']['percent']:.1f}%")
            health['overall'] = False
        
        # Check memory
        if info['memory'].get('percent', 0) > thresholds['memory_percent']:
            health['issues'].append(f"High memory usage: {info['memory']['percent']:.1f}%")
            health['overall'] = False
        
        # Check disk
        if info['disk'].get('percent', 0) > thresholds['disk_percent']:
            health['issues'].append(f"High disk usage: {info['disk']['percent']:.1f}%")
            health['overall'] = False
        
        # Check temperature
        temp = info.get('temperature')
        if temp and temp > thresholds['temperature']:
            health['issues'].append(f"High temperature: {temp}°C")
            health['overall'] = False
        
        return health