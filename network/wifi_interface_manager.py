#!/usr/bin/env python3
# wifi_interface_manager.py - Smart WiFi Interface Manager with WLAN1 Priority

import time
import json
import os
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configuration
PREFERRED_INTERFACE = "wlan1"  # Primary choice
FALLBACK_INTERFACE = "wlan0"   # Fallback choice
LOG_FILE = os.path.join(os.path.dirname(__file__), "wifi_interface_log.txt")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "wifi_interface_status.json")
CHECK_INTERVAL = 10  # seconds
PING_TEST_HOST = "8.8.8.8"  # Google DNS for connectivity test

class WiFiInterfaceManager:
    def __init__(self):
        self.current_interface = None
        self.last_check_time = None
        self.interface_switch_count = 0

    def log_event(self, message, level="INFO"):
        """Log WiFi interface events with timestamp"""
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

            print(f"WiFi Interface Manager - {message}")

        except Exception as e:
            print(f"Error logging WiFi interface event: {e}")

    def interface_exists(self, interface: str) -> bool:
        """Check if a WiFi interface exists"""
        try:
            result = subprocess.run(['ip', 'link', 'show', interface],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def get_interface_info(self, interface: str) -> Optional[Dict]:
        """Get detailed information about a WiFi interface"""
        try:
            if not self.interface_exists(interface):
                return None

            info = {
                "interface": interface,
                "timestamp": datetime.now().isoformat(),
                "available": False,
                "connected": False,
                "essid": None,
                "signal_quality": None,
                "signal_level": None,
                "bit_rate": None,
                "ip_address": None
            }

            # Check if interface is up
            ip_result = subprocess.run(['ip', 'link', 'show', interface],
                                     capture_output=True, text=True, timeout=5)
            if ip_result.returncode == 0:
                if "state UP" in ip_result.stdout:
                    info["available"] = True

            # Get wireless info using iwconfig
            iwconfig_result = subprocess.run(['iwconfig', interface],
                                           capture_output=True, text=True, timeout=5)

            if iwconfig_result.returncode == 0:
                output = iwconfig_result.stdout

                # Check if connected (has ESSID)
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

            # Get IP address if connected
            if info["connected"]:
                ip_addr_result = subprocess.run(['ip', 'addr', 'show', interface],
                                              capture_output=True, text=True, timeout=5)
                if ip_addr_result.returncode == 0:
                    ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_addr_result.stdout)
                    if ip_match:
                        info["ip_address"] = ip_match.group(1)

            return info

        except Exception as e:
            self.log_event(f"Error getting info for {interface}: {e}", "ERROR")
            return None

    def test_connectivity(self, interface: str) -> bool:
        """Test internet connectivity through specific interface"""
        try:
            # Use ping with specific interface
            result = subprocess.run(['ping', '-I', interface, '-c', '1', '-W', '3', PING_TEST_HOST],
                                  capture_output=True, timeout=8)
            return result.returncode == 0
        except Exception:
            return False

    def get_available_networks(self, interface: str) -> List[Dict]:
        """Scan for available networks on specified interface"""
        try:
            if not self.interface_exists(interface):
                return []

            # Perform WiFi scan
            result = subprocess.run(['iwlist', interface, 'scan'],
                                  capture_output=True, text=True, timeout=15)

            if result.returncode != 0:
                return []

            networks = []
            current_network = {}

            for line in result.stdout.split('\n'):
                line = line.strip()

                if 'Cell ' in line and 'Address:' in line:
                    if current_network:
                        networks.append(current_network)
                    current_network = {"interface": interface}

                    # Extract MAC address
                    mac_match = re.search(r'Address: ([A-Fa-f0-9:]+)', line)
                    if mac_match:
                        current_network["mac"] = mac_match.group(1)

                elif 'ESSID:' in line:
                    essid_match = re.search(r'ESSID:"([^"]*)"', line)
                    if essid_match:
                        current_network["essid"] = essid_match.group(1)

                elif 'Quality=' in line:
                    quality_match = re.search(r'Quality=(\d+)/(\d+)', line)
                    if quality_match:
                        current_network["quality"] = f"{quality_match.group(1)}/{quality_match.group(2)}"
                        current_network["quality_percent"] = int(quality_match.group(1)) / int(quality_match.group(2)) * 100

                    signal_match = re.search(r'Signal level=(-?\d+) dBm', line)
                    if signal_match:
                        current_network["signal_level"] = int(signal_match.group(1))

                elif 'Frequency:' in line:
                    freq_match = re.search(r'Frequency:([0-9.]+) GHz', line)
                    if freq_match:
                        current_network["frequency"] = f"{freq_match.group(1)} GHz"

                elif 'Encryption key:' in line:
                    current_network["encrypted"] = "on" in line.lower()

            # Add the last network
            if current_network:
                networks.append(current_network)

            return networks

        except Exception as e:
            self.log_event(f"Error scanning networks on {interface}: {e}", "ERROR")
            return []

    def bring_interface_up(self, interface: str) -> bool:
        """Bring up a WiFi interface"""
        try:
            self.log_event(f"Bringing up interface {interface}")
            result = subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'up'],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                time.sleep(2)  # Wait for interface to come up
                return True
            else:
                self.log_event(f"Failed to bring up {interface}: {result.stderr}", "ERROR")
                return False

        except Exception as e:
            self.log_event(f"Error bringing up {interface}: {e}", "ERROR")
            return False

    def connect_to_network(self, interface: str, essid: str) -> bool:
        """Connect to a specific network on specified interface"""
        try:
            self.log_event(f"Attempting to connect {interface} to {essid}")

            # Use wpa_supplicant to connect (assumes network is already configured)
            # This is a simplified version - in practice you'd want proper network configuration
            result = subprocess.run(['sudo', 'iwconfig', interface, 'essid', essid],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                time.sleep(3)  # Wait for connection

                # Try to get IP via DHCP
                dhcp_result = subprocess.run(['sudo', 'dhclient', interface],
                                           capture_output=True, text=True, timeout=15)

                time.sleep(2)  # Wait for DHCP

                # Check if we got an IP
                info = self.get_interface_info(interface)
                if info and info.get("ip_address"):
                    self.log_event(f"Successfully connected {interface} to {essid}, IP: {info['ip_address']}")
                    return True
                else:
                    self.log_event(f"Connected to {essid} but no IP address obtained", "WARNING")
                    return False
            else:
                self.log_event(f"Failed to connect {interface} to {essid}: {result.stderr}", "ERROR")
                return False

        except Exception as e:
            self.log_event(f"Error connecting {interface} to {essid}: {e}", "ERROR")
            return False

    def switch_to_interface(self, target_interface: str) -> bool:
        """Switch to using the specified interface as primary"""
        try:
            if target_interface == self.current_interface:
                return True  # Already using this interface

            self.log_event(f"Switching from {self.current_interface} to {target_interface}")

            # Bring up the target interface if needed
            if not self.bring_interface_up(target_interface):
                return False

            # Get current network info to try to connect to same network
            current_info = None
            if self.current_interface:
                current_info = self.get_interface_info(self.current_interface)

            # If we have a current network, try to connect target interface to same network
            if current_info and current_info.get("essid"):
                if self.connect_to_network(target_interface, current_info["essid"]):
                    self.current_interface = target_interface
                    self.interface_switch_count += 1
                    self.log_event(f"Successfully switched to {target_interface}")
                    return True

            # If no current network or connection failed, scan for available networks
            networks = self.get_available_networks(target_interface)
            if networks:
                # Try to connect to the strongest network
                best_network = max(networks, key=lambda n: n.get("quality_percent", 0))
                if best_network.get("essid"):
                    if self.connect_to_network(target_interface, best_network["essid"]):
                        self.current_interface = target_interface
                        self.interface_switch_count += 1
                        self.log_event(f"Successfully switched to {target_interface} (new network: {best_network['essid']})")
                        return True

            self.log_event(f"Failed to switch to {target_interface}", "ERROR")
            return False

        except Exception as e:
            self.log_event(f"Error switching to {target_interface}: {e}", "ERROR")
            return False

    def determine_best_interface(self) -> Tuple[str, Dict]:
        """Determine which interface should be used based on availability and priority"""
        interfaces_info = {}

        # Check preferred interface first
        if self.interface_exists(PREFERRED_INTERFACE):
            preferred_info = self.get_interface_info(PREFERRED_INTERFACE)
            if preferred_info:
                interfaces_info[PREFERRED_INTERFACE] = preferred_info

        # Check fallback interface
        if self.interface_exists(FALLBACK_INTERFACE):
            fallback_info = self.get_interface_info(FALLBACK_INTERFACE)
            if fallback_info:
                interfaces_info[FALLBACK_INTERFACE] = fallback_info

        # Priority logic:
        # 1. If WLAN1 is connected and working, use it
        # 2. If WLAN1 is available but not connected, try to use it
        # 3. Otherwise use WLAN0 if available and connected
        # 4. If neither connected, prefer WLAN1 if available

        preferred_info = interfaces_info.get(PREFERRED_INTERFACE)
        fallback_info = interfaces_info.get(FALLBACK_INTERFACE)

        if preferred_info:
            if preferred_info.get("connected"):
                return PREFERRED_INTERFACE, interfaces_info
            elif preferred_info.get("available"):
                return PREFERRED_INTERFACE, interfaces_info

        if fallback_info and fallback_info.get("connected"):
            return FALLBACK_INTERFACE, interfaces_info

        # If neither connected, prefer WLAN1 if available
        if preferred_info and preferred_info.get("available"):
            return PREFERRED_INTERFACE, interfaces_info
        elif fallback_info and fallback_info.get("available"):
            return FALLBACK_INTERFACE, interfaces_info

        # No suitable interface found
        return None, interfaces_info

    def monitor_and_manage(self):
        """Main monitoring and management loop"""
        self.log_event(f"WiFi Interface Manager started - Priority: {PREFERRED_INTERFACE} > {FALLBACK_INTERFACE}")

        while True:
            try:
                # Determine best interface
                best_interface, interfaces_info = self.determine_best_interface()

                if best_interface is None:
                    self.log_event("No suitable WiFi interfaces available", "WARNING")
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Check if we need to switch interfaces
                if self.current_interface != best_interface:
                    if self.switch_to_interface(best_interface):
                        self.current_interface = best_interface
                    else:
                        self.log_event(f"Failed to switch to {best_interface}, staying with {self.current_interface}", "WARNING")

                # Test connectivity of current interface
                if self.current_interface:
                    connectivity_ok = self.test_connectivity(self.current_interface)

                    current_info = interfaces_info.get(self.current_interface, {})
                    current_info["connectivity_test"] = connectivity_ok

                    if not connectivity_ok:
                        self.log_event(f"Connectivity test failed for {self.current_interface}", "WARNING")

                # Create status report
                status = {
                    "timestamp": datetime.now().isoformat(),
                    "current_interface": self.current_interface,
                    "interface_switch_count": self.interface_switch_count,
                    "interfaces": interfaces_info,
                    "priority_order": [PREFERRED_INTERFACE, FALLBACK_INTERFACE]
                }

                # Save status
                try:
                    with open(STATUS_FILE, 'w') as f:
                        json.dump(status, f, indent=2)
                except Exception as e:
                    self.log_event(f"Error saving status: {e}", "ERROR")

                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                self.log_event("WiFi Interface Manager stopped by user")
                break
            except Exception as e:
                self.log_event(f"Unexpected error in monitoring loop: {e}", "ERROR")
                time.sleep(CHECK_INTERVAL)

def main():
    """Main entry point"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    manager = WiFiInterfaceManager()
    try:
        manager.monitor_and_manage()
    except Exception as e:
        manager.log_event(f"Fatal error: {e}", "ERROR")

if __name__ == "__main__":
    main()