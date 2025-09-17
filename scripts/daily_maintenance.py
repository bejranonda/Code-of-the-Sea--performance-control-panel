#!/usr/bin/env python3
"""
Daily Maintenance Script for Code of the Sea Exhibition
Automated maintenance tasks for long-term stability
"""

import os
import sys
import time
import logging
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add core modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from exhibition_watchdog import get_watchdog

class DailyMaintenance:
    """Automated daily maintenance for exhibition stability"""
    
    def __init__(self):
        self.setup_logging()
        self.maintenance_log = []
        
    def setup_logging(self):
        """Setup logging for maintenance tasks"""
        log_dir = Path("/var/log")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/cos-maintenance.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('DailyMaintenance')
        
    def log_task(self, task_name: str, status: str, details: str = ""):
        """Log maintenance task result"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'task': task_name,
            'status': status,
            'details': details
        }
        self.maintenance_log.append(entry)
        
        if status == 'completed':
            self.logger.info(f"✅ {task_name}: {details}")
        elif status == 'failed':
            self.logger.error(f"❌ {task_name}: {details}")
        else:
            self.logger.warning(f"⚠️ {task_name}: {details}")
            
    def cleanup_temp_files(self):
        """Clean up temporary files and caches"""
        try:
            cleaned_count = 0
            
            # Clean mpg123 temp files
            result = subprocess.run([
                'find', '/tmp', '-name', 'mpg_pid_*', '-delete'
            ], capture_output=True)
            
            result = subprocess.run([
                'find', '/tmp', '-name', 'play_*.sh', '-delete'
            ], capture_output=True)
            
            # Clean old audio files
            result = subprocess.run([
                'find', '/tmp', '-name', '*.mpg', '-mtime', '+1', '-delete'
            ], capture_output=True)
            
            # Clean old health data
            result = subprocess.run([
                'find', '/tmp', '-name', 'cos_health*.json', '-mtime', '+2', '-delete'
            ], capture_output=True)
            
            # Clean old Python cache files
            result = subprocess.run([
                'find', '/home/payas/cos', '-name', '__pycache__', '-type', 'd', '-exec', 'rm', '-rf', '{}', '+', '2>/dev/null'
            ], capture_output=True, shell=True)
            
            result = subprocess.run([
                'find', '/home/payas/cos', '-name', '*.pyc', '-delete'
            ], capture_output=True)
            
            self.log_task("Cleanup Temp Files", "completed", "Temporary files cleaned")
            
        except Exception as e:
            self.log_task("Cleanup Temp Files", "failed", str(e))
            
    def rotate_logs(self):
        """Rotate and compress old log files"""
        try:
            log_files = [
                '/var/log/cos-watchdog.log',
                '/var/log/cos-maintenance.log',
                '/home/payas/cos/unified_app.log',
                '/home/payas/cos/led/led_log.txt',
                '/home/payas/cos/radio/radio_log.txt',
                '/home/payas/cos/fan/fan_log.txt',
                '/home/payas/cos/broadcast/broadcast_log.txt'
            ]
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    # Check file size
                    file_size = os.path.getsize(log_file)
                    if file_size > 10 * 1024 * 1024:  # 10MB
                        # Rotate large log files
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_name = f"{log_file}.{timestamp}"
                        
                        subprocess.run(['mv', log_file, backup_name])
                        subprocess.run(['touch', log_file])
                        subprocess.run(['gzip', backup_name])
                        
                        self.logger.info(f"Rotated log file: {log_file}")
            
            # Clean old rotated logs (older than 7 days)
            subprocess.run([
                'find', '/var/log', '-name', 'cos-*.log.*.gz', 
                '-mtime', '+7', '-delete'
            ], capture_output=True)
            
            subprocess.run([
                'find', '/home/payas/cos', '-name', '*.log.*.gz', 
                '-mtime', '+7', '-delete'
            ], capture_output=True)
            
            self.log_task("Log Rotation", "completed", "Log files rotated and compressed")
            
        except Exception as e:
            self.log_task("Log Rotation", "failed", str(e))
            
    def system_cleanup(self):
        """Perform system-level cleanup"""
        try:
            # Clear system logs (keep last 7 days)
            subprocess.run([
                'sudo', 'journalctl', '--vacuum-time=7d'
            ], capture_output=True)
            
            # Clear package cache
            subprocess.run([
                'sudo', 'apt-get', 'autoremove', '-y'
            ], capture_output=True)
            
            subprocess.run([
                'sudo', 'apt-get', 'autoclean'
            ], capture_output=True)
            
            # Sync and drop caches
            subprocess.run(['sudo', 'sync'], capture_output=True)
            subprocess.run([
                'sudo', 'sysctl', 'vm.drop_caches=1'
            ], capture_output=True)
            
            self.log_task("System Cleanup", "completed", "System caches cleared")
            
        except Exception as e:
            self.log_task("System Cleanup", "failed", str(e))
            
    def check_disk_space(self):
        """Check and report disk space usage"""
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            disk_info = result.stdout.strip().split('\n')[1]
            usage_percent = disk_info.split()[4]
            
            usage_num = int(usage_percent.rstrip('%'))
            
            if usage_num > 90:
                self.log_task("Disk Space Check", "failed", 
                             f"Critical disk space: {usage_percent} used")
                # Emergency cleanup
                self.emergency_disk_cleanup()
            elif usage_num > 80:
                self.log_task("Disk Space Check", "warning", 
                             f"High disk usage: {usage_percent} used")
            else:
                self.log_task("Disk Space Check", "completed", 
                             f"Disk usage normal: {usage_percent} used")
                             
        except Exception as e:
            self.log_task("Disk Space Check", "failed", str(e))
            
    def emergency_disk_cleanup(self):
        """Emergency disk cleanup when space is critical"""
        try:
            # Remove old logs more aggressively
            subprocess.run([
                'find', '/var/log', '-name', '*.log.*', '-mtime', '+1', '-delete'
            ], capture_output=True)
            
            # Clean more temporary files
            subprocess.run([
                'find', '/tmp', '-type', 'f', '-mtime', '+1', '-delete'
            ], capture_output=True)
            
            # Remove old compressed logs
            subprocess.run([
                'find', '/home/payas/cos', '-name', '*.gz', '-mtime', '+3', '-delete'
            ], capture_output=True)
            
            self.log_task("Emergency Disk Cleanup", "completed", 
                         "Emergency cleanup performed")
                         
        except Exception as e:
            self.log_task("Emergency Disk Cleanup", "failed", str(e))
            
    def update_system_packages(self):
        """Update system packages (security updates only)"""
        try:
            # Update package lists
            result = subprocess.run([
                'sudo', 'apt-get', 'update', '-qq'
            ], capture_output=True)
            
            # Install security updates only
            result = subprocess.run([
                'sudo', 'unattended-upgrade', '-v'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_task("System Updates", "completed", 
                             "Security updates installed")
            else:
                self.log_task("System Updates", "warning", 
                             "No updates available or update failed")
                             
        except Exception as e:
            self.log_task("System Updates", "failed", str(e))
            
    def check_service_health(self):
        """Check all services health"""
        try:
            # Check systemd service
            result = subprocess.run([
                'systemctl', 'is-active', 'cos-control-panel'
            ], capture_output=True, text=True)
            
            service_active = result.returncode == 0
            
            if service_active:
                self.log_task("Service Health", "completed", 
                             "Main service running normally")
            else:
                self.log_task("Service Health", "failed", 
                             "Main service not running")
                # Try to restart
                subprocess.run([
                    'sudo', 'systemctl', 'restart', 'cos-control-panel'
                ], capture_output=True)
                
        except Exception as e:
            self.log_task("Service Health", "failed", str(e))
            
    def generate_health_report(self):
        """Generate daily health report"""
        try:
            watchdog = get_watchdog()
            if watchdog and len(watchdog.health_history) > 0:
                recent_health = watchdog.health_history[-24:]  # Last 24 hours
                
                avg_cpu = sum(h.cpu_percent for h in recent_health) / len(recent_health)
                avg_memory = sum(h.memory_percent for h in recent_health) / len(recent_health)
                avg_temp = sum(h.cpu_temperature for h in recent_health) / len(recent_health)
                
                error_count = sum(h.error_count for h in recent_health)
                network_issues = sum(1 for h in recent_health if not h.network_connected)
                
                report = {
                    'date': datetime.now().isoformat(),
                    'averages': {
                        'cpu_percent': round(avg_cpu, 1),
                        'memory_percent': round(avg_memory, 1),
                        'temperature': round(avg_temp, 1)
                    },
                    'issues': {
                        'total_errors': error_count,
                        'network_disconnections': network_issues,
                        'restarts': watchdog.restart_count
                    },
                    'maintenance_tasks': self.maintenance_log
                }
                
                # Save report
                report_file = f"/tmp/cos_daily_report_{datetime.now().strftime('%Y%m%d')}.json"
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2)
                    
                self.log_task("Health Report", "completed", 
                             f"Daily report saved: {report_file}")
                             
            else:
                self.log_task("Health Report", "warning", 
                             "No health data available")
                             
        except Exception as e:
            self.log_task("Health Report", "failed", str(e))
            
    def run_all_tasks(self):
        """Run all daily maintenance tasks"""
        self.logger.info("🔧 Starting daily maintenance routine")
        start_time = time.time()
        
        # Run all maintenance tasks
        self.cleanup_temp_files()
        self.rotate_logs()
        self.system_cleanup()
        self.check_disk_space()
        self.update_system_packages()
        self.check_service_health()
        self.generate_health_report()
        
        duration = time.time() - start_time
        
        # Summary
        completed = len([t for t in self.maintenance_log if t['status'] == 'completed'])
        failed = len([t for t in self.maintenance_log if t['status'] == 'failed'])
        warnings = len([t for t in self.maintenance_log if t['status'] == 'warning'])
        
        self.logger.info(f"🏁 Daily maintenance completed in {duration:.1f}s")
        self.logger.info(f"📊 Results: {completed} completed, {warnings} warnings, {failed} failed")
        
        return {
            'duration': duration,
            'completed': completed,
            'warnings': warnings,
            'failed': failed,
            'tasks': self.maintenance_log
        }

def main():
    """Main entry point"""
    maintenance = DailyMaintenance()
    
    try:
        result = maintenance.run_all_tasks()
        
        # Exit with error code if any tasks failed
        if result['failed'] > 0:
            print(f"❌ {result['failed']} maintenance tasks failed")
            sys.exit(1)
        elif result['warnings'] > 0:
            print(f"⚠️ {result['warnings']} maintenance tasks had warnings")
            sys.exit(2)
        else:
            print("✅ All maintenance tasks completed successfully")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("🛑 Maintenance interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Maintenance script error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()