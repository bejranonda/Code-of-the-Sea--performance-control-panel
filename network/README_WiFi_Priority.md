# WiFi Interface Priority System

## 🌐 Overview

The WiFi Interface Priority System automatically manages WiFi connections on Raspberry Pi systems with multiple WiFi adapters, prioritizing **WLAN1** over **WLAN0** when both are available.

## 📋 Priority Logic

The system follows this priority order:

1. **WLAN1 (Preferred)** - Primary WiFi interface
   - If WLAN1 exists and is connected → Use WLAN1
   - If WLAN1 exists but not connected → Bring up and prefer WLAN1

2. **WLAN0 (Fallback)** - Secondary WiFi interface
   - If WLAN1 is unavailable → Use WLAN0
   - If both are connected → Set WLAN1 as primary route

## 📁 System Components

### Core Scripts
- **`wifi_interface_priority.sh`** - Main priority management script
- **`wifi_monitor.py`** - Enhanced network monitoring with dynamic interface support
- **`wifi_interface_manager.py`** - Advanced WiFi interface management (optional)
- **`start_wifi_monitor.sh`** - Startup script with priority integration

### Service Files
- **`wifi-priority.service`** - Systemd service for automatic priority management
- **`install_wifi_priority_service.sh`** - Service installation script

### Status and Logs
- **`wifi_interface_priority.log`** - Priority management logs
- **`wifi_interface_status.json`** - Current interface status (if using manager)
- **`network_status.json`** - Enhanced network monitoring status

## 🚀 Installation and Setup

### 1. **Install WiFi Priority Service (Recommended)**

```bash
# Install and enable automatic priority management
sudo /home/payas/cos/scripts/install_wifi_priority_service.sh
```

This will:
- Install the systemd service
- Enable automatic startup on boot
- Start monitoring WiFi interface priority

### 2. **Manual Management**

```bash
# Check current WiFi interface status
/home/payas/cos/scripts/wifi_interface_priority.sh status

# Set interface priority once
/home/payas/cos/scripts/wifi_interface_priority.sh check

# Start continuous monitoring
/home/payas/cos/scripts/wifi_interface_priority.sh monitor
```

### 3. **Integration with Existing WiFi Monitor**

The enhanced `wifi_monitor.py` automatically detects and uses the appropriate WiFi interface:

```bash
# Start enhanced WiFi monitoring
/home/payas/cos/scripts/start_wifi_monitor.sh
```

## 🔧 Configuration

### Interface Priority Settings

Edit the configuration in script headers:

```bash
# In wifi_interface_priority.sh
PREFERRED_INTERFACE="wlan1"  # Primary choice
FALLBACK_INTERFACE="wlan0"   # Fallback choice

# In wifi_monitor.py
PREFERRED_WIFI_INTERFACE = "wlan1"
FALLBACK_WIFI_INTERFACE = "wlan0"
```

### Service Management

```bash
# Service status and control
sudo systemctl status wifi-priority     # Check service status
sudo systemctl start wifi-priority      # Start service
sudo systemctl stop wifi-priority       # Stop service
sudo systemctl restart wifi-priority    # Restart service

# View logs
sudo journalctl -u wifi-priority -f     # Live logs
sudo journalctl -u wifi-priority --since today  # Today's logs
```

## 📊 Monitoring and Status

### WiFi Interface Status

```bash
# Comprehensive status check
/home/payas/cos/scripts/wifi_interface_priority.sh status
```

Output example:
```
WiFi Interface Priority Status:
==============================
wlan1: EXISTS, UP, CONNECTED to 'MyNetwork' (IP: 192.168.1.100)
wlan0: EXISTS, UP, NO CONNECTION

Current routes:
default via 192.168.1.1 dev wlan1 proto dhcp src 192.168.1.100 metric 100
default via 192.168.1.1 dev wlan0 proto dhcp src 192.168.1.101 metric 200
```

### Network Monitoring Status

```bash
# View enhanced network status
cat /home/payas/cos/network/network_status.json
```

### Log Files

```bash
# Priority management logs
tail -f /home/payas/cos/network/wifi_interface_priority.log

# General network connection logs
tail -f /home/payas/cos/network/network_connection_log.txt

# WiFi monitor startup logs
tail -f /home/payas/cos/network/wifi_monitor_startup.log
```

## 🔄 How It Works

### Automatic Priority Management

1. **System Startup**
   - WiFi priority service starts automatically
   - Checks available WiFi interfaces
   - Brings up WLAN1 if available
   - Sets routing priorities

2. **Runtime Monitoring** (every 30 seconds)
   - Checks interface availability and connections
   - Switches to WLAN1 if it becomes available
   - Maintains routing table priorities
   - Logs all interface changes

3. **Route Management**
   - WLAN1 gets metric 100 (higher priority)
   - WLAN0 gets metric 200 (lower priority)
   - Lower metric = higher priority in Linux routing

### Integration with WiFi Monitor

The enhanced `wifi_monitor.py` now:
- Dynamically selects the best available WiFi interface
- Monitors both WLAN1 and WLAN0
- Reports which interface is currently active
- Maintains compatibility with existing dashboard integration

## 🛠️ Troubleshooting

### Common Issues

**WLAN1 not being used despite being available:**
```bash
# Check if WLAN1 is properly brought up
sudo ip link set wlan1 up

# Check if WiFi priority service is running
sudo systemctl status wifi-priority

# Manual priority check
/home/payas/cos/scripts/wifi_interface_priority.sh check
```

**Both interfaces connected but wrong priority:**
```bash
# Check routing table
ip route show

# Manually fix routing (temporary)
sudo ip route del default dev wlan0
sudo ip route add default dev wlan1 metric 100
sudo ip route add default dev wlan0 metric 200
```

**Service not starting:**
```bash
# Check service logs
sudo journalctl -u wifi-priority --since today

# Reinstall service
sudo /home/payas/cos/scripts/install_wifi_priority_service.sh
```

### Network Configuration Conflicts

If you have static network configurations that conflict:

```bash
# Check network manager status
systemctl status NetworkManager

# Check if dhcpcd is running
systemctl status dhcpcd

# View current network configuration
cat /etc/dhcpcd.conf
```

## 📈 Dashboard Integration

The Code of the Sea dashboard automatically displays:
- Current active WiFi interface (WLAN0 or WLAN1)
- Connection status and signal strength
- IP addresses for both interfaces
- Interface switching history

No dashboard changes needed - the existing WiFi monitoring seamlessly works with the priority system.

## 🔒 Security Considerations

- The WiFi priority service runs as root (required for network interface management)
- Service has restricted filesystem access via systemd security settings
- All network changes are logged for audit purposes

## 📝 Development Notes

### Adding New Interfaces

To support additional WiFi interfaces (e.g., WLAN2):

1. Update interface lists in scripts
2. Modify priority logic in `determine_wifi_interface()`
3. Update routing table management
4. Test interface switching scenarios

### Custom Priority Logic

The priority system can be extended to include:
- Signal strength-based switching
- Load balancing between interfaces
- Automatic failover testing
- Custom network preference rules

---

**🎯 Result**: Raspberry Pi will automatically use WLAN1 when available, gracefully falling back to WLAN0 when needed, ensuring optimal WiFi connectivity for the Code of the Sea interactive art installation.