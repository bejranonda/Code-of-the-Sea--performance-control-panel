#!/bin/bash
# WiFi Monitor and Priority Manager Startup Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIFI_MONITOR_PATH="$(dirname "$SCRIPT_DIR")/network/wifi_monitor.py"
WIFI_PRIORITY_SCRIPT="$SCRIPT_DIR/wifi_interface_priority.sh"
LOG_PATH="$(dirname "$SCRIPT_DIR")/network/wifi_monitor_startup.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting WiFi services..." >> "$LOG_PATH"

# Step 1: Set WiFi interface priority first
echo "$(date '+%Y-%m-%d %H:%M:%S') - Setting WiFi interface priority..." >> "$LOG_PATH"
"$WIFI_PRIORITY_SCRIPT" check >> "$LOG_PATH" 2>&1

# Step 2: Check if WiFi monitor is already running
if pgrep -f "wifi_monitor.py" > /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - WiFi Monitor already running" >> "$LOG_PATH"
else
    # Start WiFi monitor in background
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting WiFi Monitor..." >> "$LOG_PATH"
    cd "$(dirname "$WIFI_MONITOR_PATH")"
    python3 "$WIFI_MONITOR_PATH" >> "$LOG_PATH" 2>&1 &

    MONITOR_PID=$!
    echo "$(date '+%Y-%m-%d %H:%M:%S') - WiFi Monitor started with PID $MONITOR_PID" >> "$LOG_PATH"
fi

# Step 3: Show current WiFi status
echo "$(date '+%Y-%m-%d %H:%M:%S') - Current WiFi status:" >> "$LOG_PATH"
"$WIFI_PRIORITY_SCRIPT" status >> "$LOG_PATH" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - WiFi services startup complete" >> "$LOG_PATH"

# Optional: Add to system startup (uncomment to enable)
# echo "@reboot /home/payas/cos/scripts/start_wifi_monitor.sh" | crontab -