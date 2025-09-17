#!/bin/bash
# Disable WiFi Power Management to prevent disconnections
# This script should run at boot

/sbin/iwconfig wlan0 power off 2>/dev/null || true

# Also disable via NetworkManager if available
nmcli dev wifi modify wlan0 802-11-wireless.powersave 2 2>/dev/null || true

echo "$(date): WiFi power management disabled" >> /var/log/wifi-powersave.log