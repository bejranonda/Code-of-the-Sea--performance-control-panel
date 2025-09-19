#!/bin/bash
# Monitor for reboot requests from the web interface

REBOOT_FILE="/tmp/cos_reboot_request"
LOG_FILE="/home/payas/cos/reboot_monitor.log"

echo "$(date): Reboot monitor started" >> "$LOG_FILE"

while true; do
    if [ -f "$REBOOT_FILE" ]; then
        echo "$(date): Reboot request detected, executing reboot" >> "$LOG_FILE"
        cat "$REBOOT_FILE" >> "$LOG_FILE"
        rm -f "$REBOOT_FILE"

        # Give a moment for cleanup
        sleep 2

        # Execute reboot
        sudo /sbin/reboot
        break
    fi

    # Check every 5 seconds
    sleep 5
done