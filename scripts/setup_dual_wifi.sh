#!/bin/bash
# setup_dual_wifi.sh - Configure WLAN1 with same credentials as WLAN0
# Priority: WLAN1 (primary) -> WLAN0 (backup)

set -e

LOGFILE="/home/payas/cos/network/dual_wifi_setup.log"
WLAN0_INTERFACE="wlan0"
WLAN1_INTERFACE="wlan1"

# Create log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log "Starting dual WiFi setup"

# Check if both interfaces exist
if ! ip link show "$WLAN0_INTERFACE" >/dev/null 2>&1; then
    log "ERROR: $WLAN0_INTERFACE not found"
    exit 1
fi

if ! ip link show "$WLAN1_INTERFACE" >/dev/null 2>&1; then
    log "ERROR: $WLAN1_INTERFACE not found"
    exit 1
fi

log "Both WiFi interfaces found: $WLAN0_INTERFACE and $WLAN1_INTERFACE"

# Get current network configuration from wlan0
CURRENT_SSID=$(sudo wpa_cli -i "$WLAN0_INTERFACE" list_networks | grep CURRENT | awk '{print $2}')

if [ -z "$CURRENT_SSID" ]; then
    log "ERROR: No current network found on $WLAN0_INTERFACE"
    exit 1
fi

log "Found current SSID: $CURRENT_SSID"

# Create a simple interactive password prompt for the user
echo "Please enter the WiFi password for '$CURRENT_SSID':"
read -s WIFI_PASSWORD

if [ -z "$WIFI_PASSWORD" ]; then
    log "ERROR: No password provided"
    exit 1
fi

log "Configuring $WLAN1_INTERFACE with same credentials..."

# Configure wlan1 with the same network
sudo wpa_cli -i "$WLAN1_INTERFACE" add_network
sudo wpa_cli -i "$WLAN1_INTERFACE" set_network 0 ssid "\"$CURRENT_SSID\""
sudo wpa_cli -i "$WLAN1_INTERFACE" set_network 0 psk "\"$WIFI_PASSWORD\""
sudo wpa_cli -i "$WLAN1_INTERFACE" enable_network 0
sudo wpa_cli -i "$WLAN1_INTERFACE" save_config

log "WLAN1 configured successfully"

# Create interface-specific wpa_supplicant configurations
log "Creating interface-specific configurations..."

# Create wpa_supplicant config for wlan0
sudo tee /etc/wpa_supplicant/wpa_supplicant-wlan0.conf > /dev/null << EOF
country=DE
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
ap_scan=1

network={
    ssid="$CURRENT_SSID"
    psk="$WIFI_PASSWORD"
    priority=1
}
EOF

# Create wpa_supplicant config for wlan1
sudo tee /etc/wpa_supplicant/wpa_supplicant-wlan1.conf > /dev/null << EOF
country=DE
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
ap_scan=1

network={
    ssid="$CURRENT_SSID"
    psk="$WIFI_PASSWORD"
    priority=2
}
EOF

log "Created interface-specific wpa_supplicant configurations"

# Create systemd service for wlan1
sudo tee /etc/systemd/system/wpa_supplicant@wlan1.service > /dev/null << 'EOF'
[Unit]
Description=WPA supplicant daemon (interface-specific version)
Requires=sys-subsystem-net-devices-%i.device
After=sys-subsystem-net-devices-%i.device
Before=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/sbin/wpa_supplicant -c/etc/wpa_supplicant/wpa_supplicant-%i.conf -i%i

[Install]
WantedBy=multi-user.target
EOF

# Enable wlan1 service
sudo systemctl enable wpa_supplicant@wlan1.service

log "Created and enabled wpa_supplicant service for wlan1"

# Configure dhcpcd for both interfaces with priority
if [ ! -f /etc/dhcpcd.conf ]; then
    sudo touch /etc/dhcpcd.conf
fi

# Add interface priority configuration to dhcpcd.conf
if ! grep -q "interface wlan1" /etc/dhcpcd.conf; then
    sudo tee -a /etc/dhcpcd.conf > /dev/null << EOF

# Dual WiFi configuration - WLAN1 priority over WLAN0
interface wlan1
metric 100
noipv6

interface wlan0
metric 200
noipv6

# Allow both interfaces to coexist
allowinterfaces wlan0 wlan1 eth0
EOF
    log "Added dual WiFi configuration to dhcpcd.conf"
else
    log "dhcpcd.conf already configured for dual WiFi"
fi

log "Dual WiFi setup completed successfully!"
log "WLAN1 (priority 100) will be preferred over WLAN0 (priority 200)"
log "Please restart networking or reboot to activate the new configuration"

echo ""
echo "Setup complete! To activate:"
echo "sudo systemctl restart dhcpcd"
echo "sudo systemctl restart wpa_supplicant@wlan1"
echo ""
echo "Or reboot the system for full activation."