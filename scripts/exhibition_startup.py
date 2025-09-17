#!/usr/bin/env python3
"""
Exhibition Startup Script for Code of the Sea
Ensures proper initialization and health checks on system startup
"""

import os
import sys
import time
import logging
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add core modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

class ExhibitionStartup:
    """Exhibition startup and initialization manager"""
    
    def __init__(self):
        self.setup_logging()
        self.startup_log = []
        
    def setup_logging(self):
        """Setup logging for startup tasks"""
        # Use local log file if /var/log not writable
        log_file = '/var/log/cos-startup.log'
        try:
            # Test if we can write to /var/log
            with open(log_file, 'a'):
                pass
        except (PermissionError, FileNotFoundError):
            # Fall back to local directory
            log_file = 'logs/cos-startup.log'
            os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ExhibitionStartup')
        
    def log_task(self, task_name: str, status: str, details: str = ""):
        """Log startup task result"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'task': task_name,
            'status': status,
            'details': details
        }
        self.startup_log.append(entry)
        
        if status == 'completed':
            self.logger.info(f"✅ {task_name}: {details}")
        elif status == 'failed':
            self.logger.error(f"❌ {task_name}: {details}")
        else:
            self.logger.warning(f"⚠️ {task_name}: {details}")
            
    def wait_for_network(self, timeout=120):
        """Wait for network connectivity"""
        self.logger.info("🌐 Waiting for network connectivity...")
        
        for attempt in range(timeout):
            try:
                result = subprocess.run([
                    'ping', '-c', '1', '-W', '3', '192.168.0.1'
                ], capture_output=True, timeout=5)
                
                if result.returncode == 0:
                    self.log_task("Network Wait", "completed", 
                                 f"Network available after {attempt}s")
                    return True
                    
            except:
                pass
                
            time.sleep(1)
            
        self.log_task("Network Wait", "failed", 
                     f"Network not available after {timeout}s")
        return False
        
    def check_hardware_devices(self):
        """Check that hardware devices are accessible"""
        try:
            devices_ok = True
            
            # Check I2C bus
            result = subprocess.run([
                'i2cdetect', '-y', '1'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Check for expected devices
                output = result.stdout
                veml_detected = '10' in output  # VEML7700
                tea_detected = '60' in output   # TEA5767
                
                if veml_detected:
                    self.logger.info("✅ VEML7700 light sensor detected")
                else:
                    self.logger.warning("⚠️ VEML7700 light sensor not detected")
                    
                if tea_detected:
                    self.logger.info("✅ TEA5767 FM radio detected")
                else:
                    self.logger.warning("⚠️ TEA5767 FM radio not detected")
                    
                self.log_task("Hardware Check", "completed", 
                             f"I2C devices: VEML={veml_detected}, TEA={tea_detected}")
            else:
                devices_ok = False
                self.log_task("Hardware Check", "failed", "I2C bus not accessible")
                
            # Check GPIO access
            if os.path.exists('/sys/class/gpio'):
                self.logger.info("✅ GPIO system accessible")
            else:
                devices_ok = False
                self.logger.error("❌ GPIO system not accessible")
                
            return devices_ok
            
        except Exception as e:
            self.log_task("Hardware Check", "failed", str(e))
            return False
            
    def check_device_config(self):
        """Verify device configuration is available"""
        try:
            config_file = '/home/payas/cos/config/devices.json'
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    
                # Check for required sections
                required_sections = ['led', 'radio', 'fan']
                missing_sections = []
                
                for section in required_sections:
                    if section not in config:
                        missing_sections.append(section)
                        
                if missing_sections:
                    self.log_task("Config Check", "warning", 
                                 f"Missing sections: {missing_sections}")
                else:
                    self.log_task("Config Check", "completed", 
                                 "All device configurations present")
                    
                return len(missing_sections) == 0
                
            else:
                self.log_task("Config Check", "failed", 
                             "Device configuration file not found")
                return False
                
        except Exception as e:
            self.log_task("Config Check", "failed", str(e))
            return False
            
    def initialize_directories(self):
        """Create necessary directories"""
        try:
            directories = [
                '/home/payas/cos/logs',
                '/home/payas/cos/tmp',
                '/var/log',
                '/tmp/cos'
            ]
            
            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)
                
            self.log_task("Directory Init", "completed", 
                         f"Created {len(directories)} directories")
            return True
            
        except Exception as e:
            self.log_task("Directory Init", "failed", str(e))
            return False
            
    def cleanup_stale_processes(self):
        """Clean up any stale processes from previous runs"""
        try:
            # Kill any orphaned mpg123 processes
            subprocess.run(['sudo', 'pkill', '-f', 'mpg123'], capture_output=True)
            
            # Clean up old PID files
            subprocess.run([
                'find', '/tmp', '-name', 'mpg_pid_*', '-delete'
            ], capture_output=True)
            
            subprocess.run([
                'find', '/tmp', '-name', 'play_*.sh', '-delete'
            ], capture_output=True)
            
            self.log_task("Process Cleanup", "completed", 
                         "Cleaned up stale processes")
            return True
            
        except Exception as e:
            self.log_task("Process Cleanup", "failed", str(e))
            return False
            
    def test_system_services(self):
        """Test that system services are working"""
        try:
            services_ok = True
            
            # Test systemd
            result = subprocess.run([
                'systemctl', 'is-system-running'
            ], capture_output=True, text=True)
            
            if 'running' in result.stdout or 'degraded' in result.stdout:
                self.logger.info("✅ Systemd is running")
            else:
                self.logger.warning("⚠️ Systemd system not fully running")
                services_ok = False
                
            # Test cron service (for scheduled maintenance)
            result = subprocess.run([
                'systemctl', 'is-active', 'cron'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("✅ Cron service active")
            else:
                self.logger.warning("⚠️ Cron service not active")
                # Try to start it
                subprocess.run([
                    'sudo', 'systemctl', 'start', 'cron'
                ], capture_output=True)
                
            self.log_task("System Services", "completed" if services_ok else "warning", 
                         "System services checked")
            return services_ok
            
        except Exception as e:
            self.log_task("System Services", "failed", str(e))
            return False
            
    def install_cron_jobs(self):
        """Install cron jobs for maintenance"""
        try:
            # Daily maintenance at 6 AM
            daily_job = "0 6 * * * /usr/bin/python3 /home/payas/cos/scripts/daily_maintenance.py"
            
            # Weekly reboot on Sunday at 5 AM
            weekly_reboot = "0 5 * * 0 /sbin/shutdown -r +5"
            
            # Add cron jobs
            cron_content = f"""
# Code of the Sea Exhibition Maintenance
{daily_job}
{weekly_reboot}
"""
            
            # Write to temporary file and install
            with open('/tmp/cos_crontab', 'w') as f:
                f.write(cron_content)
                
            result = subprocess.run([
                'crontab', '/tmp/cos_crontab'
            ], capture_output=True)
            
            if result.returncode == 0:
                self.log_task("Cron Installation", "completed", 
                             "Maintenance cron jobs installed")
                os.remove('/tmp/cos_crontab')
                return True
            else:
                self.log_task("Cron Installation", "failed", 
                             "Could not install cron jobs")
                return False
                
        except Exception as e:
            self.log_task("Cron Installation", "failed", str(e))
            return False
            
    def start_exhibition_watchdog(self):
        """Start the exhibition watchdog system"""
        try:
            from exhibition_watchdog import start_watchdog
            
            watchdog = start_watchdog()
            if watchdog:
                self.log_task("Watchdog Start", "completed", 
                             "Exhibition watchdog started")
                return True
            else:
                self.log_task("Watchdog Start", "failed", 
                             "Could not start watchdog")
                return False
                
        except Exception as e:
            self.log_task("Watchdog Start", "failed", str(e))
            return False
            
    def create_startup_summary(self):
        """Create startup summary report"""
        try:
            summary = {
                'startup_time': datetime.now().isoformat(),
                'tasks': self.startup_log,
                'status': 'completed' if all(t['status'] == 'completed' for t in self.startup_log) else 'partial'
            }
            
            with open('/tmp/cos_startup_summary.json', 'w') as f:
                json.dump(summary, f, indent=2)
                
            completed = len([t for t in self.startup_log if t['status'] == 'completed'])
            failed = len([t for t in self.startup_log if t['status'] == 'failed'])
            warnings = len([t for t in self.startup_log if t['status'] == 'warning'])
            
            self.logger.info(f"📊 Startup Summary: {completed} completed, {warnings} warnings, {failed} failed")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating startup summary: {e}")
            return None
            
    def run_startup_sequence(self):
        """Run complete startup sequence"""
        self.logger.info("🚀 Starting Code of the Sea exhibition startup sequence")
        start_time = time.time()
        
        # Core startup tasks
        self.initialize_directories()
        self.cleanup_stale_processes()
        
        # Wait for network (non-blocking for hardware-only mode)
        network_available = self.wait_for_network(timeout=60)
        
        # Hardware and configuration checks
        self.check_hardware_devices()
        self.check_device_config()
        
        # System services
        self.test_system_services()
        self.install_cron_jobs()
        
        # Start monitoring
        self.start_exhibition_watchdog()
        
        # Generate summary
        summary = self.create_startup_summary()
        
        duration = time.time() - start_time
        self.logger.info(f"🏁 Exhibition startup completed in {duration:.1f}s")
        
        return summary

def main():
    """Main entry point"""
    startup = ExhibitionStartup()
    
    try:
        summary = startup.run_startup_sequence()
        
        if summary and summary['status'] == 'completed':
            print("✅ Exhibition startup completed successfully")
            sys.exit(0)
        else:
            print("⚠️ Exhibition startup completed with issues")
            sys.exit(2)
            
    except KeyboardInterrupt:
        print("🛑 Startup interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Startup script error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()