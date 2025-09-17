#!/usr/bin/env python3
# wifi_monitor.py - WiFi Connection Stability Monitor

import time
import json
import os
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
PREFERRED_WIFI_INTERFACE = "wlan1"  # Primary choice
FALLBACK_WIFI_INTERFACE = "wlan0"   # Fallback choice
ETHERNET_INTERFACE = "eth0"
LOG_FILE = os.path.join(os.path.dirname(__file__), "network_connection_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "network_status.json")
CHECK_INTERVAL = 5  # seconds
PING_TEST_HOST = "8.8.8.8"  # Google DNS for connectivity test

class WiFiMonitor:
    def __init__(self):
        self.last_status = None
        self.connection_start_time = None
        self.disconnection_count = 0
        self.last_signal_quality = None
        self.current_wifi_interface = None

    def log_event(self, message, level="INFO"):
        """Log WiFi events with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}\n"

        try:
            # Read existing logs
            existing_logs = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    existing_logs = f.readlines()

            # Add new log at the top (newest first)
            with open(LOG_FILE, 'w') as f:
                f.write(log_entry)
                for line in existing_logs[:999]:  # Keep last 1000 entries
                    f.write(line)

            print(f"WiFi Monitor - {message}")

        except Exception as e:
            print(f"Error logging WiFi event: {e}")

    def interface_exists(self, interface: str) -> bool:
        """Check if a network interface exists"""
        try:
            result = subprocess.run(['ip', 'link', 'show', interface],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def determine_wifi_interface(self) -> str:
        """Determine which WiFi interface to use based on availability and priority"""
        # Priority: WLAN1 > WLAN0

        # Check if preferred interface (wlan1) exists and is usable
        if self.interface_exists(PREFERRED_WIFI_INTERFACE):
            try:
                # Quick check if interface can be used
                result = subprocess.run(['iwconfig', PREFERRED_WIFI_INTERFACE],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # If we're not currently using this interface or it's available, prefer it
                    if self.current_wifi_interface != PREFERRED_WIFI_INTERFACE:
                        self.log_event(f"Switching to preferred interface: {PREFERRED_WIFI_INTERFACE}")
                        self.current_wifi_interface = PREFERRED_WIFI_INTERFACE
                    return PREFERRED_WIFI_INTERFACE
            except Exception as e:
                self.log_event(f"Error checking {PREFERRED_WIFI_INTERFACE}: {e}", "WARNING")

        # Fall back to wlan0 if wlan1 is not available
        if self.interface_exists(FALLBACK_WIFI_INTERFACE):
            try:
                result = subprocess.run(['iwconfig', FALLBACK_WIFI_INTERFACE],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    if self.current_wifi_interface != FALLBACK_WIFI_INTERFACE:
                        self.log_event(f"Using fallback interface: {FALLBACK_WIFI_INTERFACE}")
                        self.current_wifi_interface = FALLBACK_WIFI_INTERFACE
                    return FALLBACK_WIFI_INTERFACE
            except Exception as e:
                self.log_event(f"Error checking {FALLBACK_WIFI_INTERFACE}: {e}", "WARNING")

        # No suitable interface found
        self.log_event("No suitable WiFi interface found", "ERROR")
        return FALLBACK_WIFI_INTERFACE  # Default fallback

    def get_ethernet_info(self) -> Optional[Dict]:
        """Get current Ethernet connection information"""
        try:
            info = {
                "timestamp": datetime.now().isoformat(),
                "connected": False,
                "interface": ETHERNET_INTERFACE,
                "ip_address": None,
                "speed": None,
                "duplex": None
            }

            # Check if interface is up
            result = subprocess.run(['ip', 'link', 'show', ETHERNET_INTERFACE],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout
                if "state UP" in output:
                    info["connected"] = True

                    # Get IP address
                    ip_result = subprocess.run(['ip', 'addr', 'show', ETHERNET_INTERFACE],
                                             capture_output=True, text=True, timeout=10)
                    if ip_result.returncode == 0:
                        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
                        if ip_match:
                            info["ip_address"] = ip_match.group(1)

                    # Get speed and duplex info from ethtool (if available)
                    try:
                        ethtool_result = subprocess.run(['ethtool', ETHERNET_INTERFACE],
                                                      capture_output=True, text=True, timeout=5)
                        if ethtool_result.returncode == 0:
                            speed_match = re.search(r'Speed: (\d+)Mb/s', ethtool_result.stdout)
                            if speed_match:
                                info["speed"] = f"{speed_match.group(1)} Mb/s"

                            duplex_match = re.search(r'Duplex: (\w+)', ethtool_result.stdout)
                            if duplex_match:
                                info["duplex"] = duplex_match.group(1)
                    except:
                        pass  # ethtool might not be available

            return info

        except Exception as e:
            self.log_event(f"Error getting Ethernet info: {e}", "ERROR")
            return None

    def get_wifi_info_for_interface(self, interface: str) -> Optional[Dict]:
        """Get WiFi connection information for a specific interface"""
        try:
            # Get iwconfig output
            result = subprocess.run(['iwconfig', interface],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return None

            output = result.stdout

            # Parse connection info
            info = {
                "timestamp": datetime.now().isoformat(),
                "interface": interface,
                "connected": False,
                "essid": None,
                "signal_quality": None,
                "signal_level": None,
                "bit_rate": None,
                "access_point": None,
                "frequency": None
            }

            # Check if connected
            if "ESSID:" in output and 'ESSID:off/any' not in output:
                info["connected"] = True

                # Extract ESSID
                essid_match = re.search(r'ESSID:"([^"]*)"', output)
                if essid_match:
                    info["essid"] = essid_match.group(1)

                # Extract signal quality
                quality_match = re.search(r'Link Quality=(\d+)/(\d+)', output)
                if quality_match:
                    info["signal_quality"] = f"{quality_match.group(1)}/{quality_match.group(2)}"
                    info["signal_quality_percent"] = int(quality_match.group(1)) / int(quality_match.group(2)) * 100

                # Extract signal level
                level_match = re.search(r'Signal level=(-?\d+) dBm', output)
                if level_match:
                    info["signal_level"] = int(level_match.group(1))

                # Extract bit rate
                rate_match = re.search(r'Bit Rate=([0-9.]+) ([A-Za-z/]+)', output)
                if rate_match:
                    info["bit_rate"] = f"{rate_match.group(1)} {rate_match.group(2)}"

                # Extract access point
                ap_match = re.search(r'Access Point: ([A-Fa-f0-9:]+)', output)
                if ap_match:
                    info["access_point"] = ap_match.group(1)

                # Extract frequency
                freq_match = re.search(r'Frequency:([0-9.]+) GHz', output)
                if freq_match:
                    info["frequency"] = f"{freq_match.group(1)} GHz"

            return info

        except Exception as e:
            self.log_event(f"Error getting WiFi info for {interface}: {e}", "ERROR")
            return None

    def get_dual_wifi_info(self) -> Dict:
        """Get WiFi information for both interfaces"""
        wlan0_info = self.get_wifi_info_for_interface(FALLBACK_WIFI_INTERFACE)
        wlan1_info = self.get_wifi_info_for_interface(PREFERRED_WIFI_INTERFACE)

        return {
            "wlan0": wlan0_info,
            "wlan1": wlan1_info,
            "primary_interface": self.determine_wifi_interface()
        }

    def get_wifi_info(self) -> Optional[Dict]:
        """Get current WiFi connection information (legacy method for backward compatibility)"""
        try:
            # Determine which WiFi interface to use
            wifi_interface = self.determine_wifi_interface()
            return self.get_wifi_info_for_interface(wifi_interface)
        except Exception as e:
            self.log_event(f"Error getting WiFi info: {e}", "ERROR")
            return None

    def test_internet_connectivity(self) -> bool:
        """Test internet connectivity with ping"""
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '3', PING_TEST_HOST],
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def get_network_stats(self, interface: str) -> Dict:
        """Get network interface statistics"""
        try:
            stats = {}
            stats_path = f"/sys/class/net/{interface}/statistics"

            if os.path.exists(stats_path):
                for stat_file in ['rx_packets', 'tx_packets', 'rx_bytes', 'tx_bytes', 'rx_errors', 'tx_errors']:
                    try:
                        with open(f"{stats_path}/{stat_file}", 'r') as f:
                            stats[stat_file] = int(f.read().strip())
                    except:
                        stats[stat_file] = 0

            return stats

        except Exception as e:
            self.log_event(f"Error getting network stats for {interface}: {e}", "ERROR")
            return {}

    def analyze_signal_changes(self, current_info: Dict):
        """Analyze signal quality changes"""
        if not current_info.get("connected"):
            return

        current_quality = current_info.get("signal_quality_percent")
        if current_quality is None:
            return

        if self.last_signal_quality is not None:
            quality_diff = current_quality - self.last_signal_quality

            if abs(quality_diff) >= 20:  # Significant change
                direction = "improved" if quality_diff > 0 else "degraded"
                self.log_event(f"Signal quality {direction}: {self.last_signal_quality:.1f}% → {current_quality:.1f}%", "WARNING")

        self.last_signal_quality = current_quality

    def monitor_connection(self):
        """Main monitoring loop"""
        self.log_event("WiFi monitoring started")

        while True:
            try:
                # Get current network status (both WiFi and Ethernet)
                wifi_info = self.get_wifi_info()
                ethernet_info = self.get_ethernet_info()

                if wifi_info is None and ethernet_info is None:
                    self.log_event("Failed to get network information", "ERROR")
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Get current WiFi interface name for stats
                current_wifi_interface = wifi_info.get("interface", FALLBACK_WIFI_INTERFACE) if wifi_info else FALLBACK_WIFI_INTERFACE

                # Get dual WiFi information
                dual_wifi_info = self.get_dual_wifi_info()

                # Combine network information
                current_info = {
                    "timestamp": datetime.now().isoformat(),
                    "wifi": wifi_info,  # Primary WiFi interface for backward compatibility
                    "wlan0": dual_wifi_info["wlan0"],  # WLAN0 specific info
                    "wlan1": dual_wifi_info["wlan1"],  # WLAN1 specific info
                    "ethernet": ethernet_info,
                    "internet_accessible": self.test_internet_connectivity(),
                    "current_wifi_interface": current_wifi_interface,
                    "primary_wifi_interface": dual_wifi_info["primary_interface"],
                    "network_stats": {
                        "wifi": self.get_network_stats(current_wifi_interface),
                        "wlan0": self.get_network_stats(FALLBACK_WIFI_INTERFACE),
                        "wlan1": self.get_network_stats(PREFERRED_WIFI_INTERFACE),
                        "ethernet": self.get_network_stats(ETHERNET_INTERFACE)
                    }
                }

                # Determine primary connection
                if wifi_info and wifi_info.get("connected"):
                    current_info["primary_connection"] = "wifi"
                    current_info["connected"] = True
                elif ethernet_info and ethernet_info.get("connected"):
                    current_info["primary_connection"] = "ethernet"
                    current_info["connected"] = True
                else:
                    current_info["primary_connection"] = None
                    current_info["connected"] = False

                # Check for status changes
                if self.last_status is None:
                    # First run
                    if current_info["connected"]:
                        if current_info["primary_connection"] == "wifi" and current_info.get("wifi"):
                            essid = current_info["wifi"].get("essid", "unknown")
                            quality = current_info["wifi"].get("signal_quality", "N/A")
                            signal = current_info["wifi"].get("signal_level", "N/A")
                            self.log_event(f"Initial WiFi connection: {essid} (Quality: {quality}, Signal: {signal} dBm)")
                        elif current_info["primary_connection"] == "ethernet":
                            self.log_event("Initial Ethernet connection detected")
                        self.connection_start_time = datetime.now()
                    else:
                        self.log_event("No network connection detected at startup", "WARNING")

                elif self.last_status["connected"] and not current_info["connected"]:
                    # Connection lost
                    if self.connection_start_time:
                        duration = datetime.now() - self.connection_start_time
                        duration_str = str(duration).split('.')[0]  # Remove microseconds

                        last_connection = "unknown"
                        if self.last_status.get("wifi") and self.last_status["wifi"].get("connected"):
                            last_connection = self.last_status["wifi"].get("essid", "WiFi")
                        elif self.last_status.get("ethernet") and self.last_status["ethernet"].get("connected"):
                            last_connection = "Ethernet"

                        self.log_event(f"CONNECTION LOST after {duration_str} - was connected to {last_connection}", "ERROR")
                    else:
                        self.log_event("CONNECTION LOST", "ERROR")

                    self.disconnection_count += 1
                    self.connection_start_time = None

                elif not self.last_status["connected"] and current_info["connected"]:
                    # Connection restored/established
                    if current_info["primary_connection"] == "wifi" and current_info.get("wifi"):
                        essid = current_info["wifi"].get("essid", "unknown")
                        quality = current_info["wifi"].get("signal_quality", "N/A")
                        signal = current_info["wifi"].get("signal_level", "N/A")
                        self.log_event(f"WiFi CONNECTION ESTABLISHED: {essid} (Quality: {quality}, Signal: {signal} dBm)", "INFO")
                    elif current_info["primary_connection"] == "ethernet":
                        self.log_event("Ethernet CONNECTION ESTABLISHED", "INFO")
                    self.connection_start_time = datetime.now()

                elif current_info["connected"] and self.last_status["connected"]:
                    # Connected - check for changes
                    current_essid = None
                    last_essid = None

                    if current_info.get("wifi") and current_info["wifi"].get("connected"):
                        current_essid = current_info["wifi"].get("essid")
                    if self.last_status.get("wifi") and self.last_status["wifi"].get("connected"):
                        last_essid = self.last_status["wifi"].get("essid")

                    if current_essid != last_essid and current_essid and last_essid:
                        self.log_event(f"Network changed: {last_essid} → {current_essid}")

                    # Check internet connectivity issues
                    if self.last_status.get("internet_accessible") and not current_info["internet_accessible"]:
                        self.log_event("Internet connectivity lost (WiFi connected but no internet)", "WARNING")
                    elif not self.last_status.get("internet_accessible") and current_info["internet_accessible"]:
                        self.log_event("Internet connectivity restored")

                # Analyze signal quality changes (only for WiFi)
                if current_info.get("wifi"):
                    self.analyze_signal_changes(current_info["wifi"])

                # Add monitoring metadata
                current_info["disconnection_count"] = self.disconnection_count
                if self.connection_start_time:
                    current_info["connection_duration"] = str(datetime.now() - self.connection_start_time).split('.')[0]

                # Save current status
                try:
                    with open(STATUS_FILE, 'w') as f:
                        json.dump(current_info, f, indent=2)
                except Exception as e:
                    self.log_event(f"Error saving status: {e}", "ERROR")

                self.last_status = current_info
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                self.log_event("WiFi monitoring stopped by user")
                break
            except Exception as e:
                self.log_event(f"Unexpected error in monitoring loop: {e}", "ERROR")
                time.sleep(CHECK_INTERVAL)

def main():
    """Main entry point"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    monitor = WiFiMonitor()
    try:
        monitor.monitor_connection()
    except Exception as e:
        monitor.log_event(f"Fatal error: {e}", "ERROR")

if __name__ == "__main__":
    main()