#!/bin/bash
# startup_services.sh - Automatically start all COS services on system boot

SCRIPT_DIR="/home/payas/cos/scripts"
LOG_FILE="/home/payas/cos/startup.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Wait for system to be ready
log_message "Waiting for system to be ready..."
sleep 10

# Change to the correct directory
cd /home/payas/cos

log_message "Starting all COS services..."

# Start all services using the existing script
if [ -f "$SCRIPT_DIR/manage_all_services.sh" ]; then
    "$SCRIPT_DIR/manage_all_services.sh" start 2>&1 | tee -a "$LOG_FILE"
    log_message "Service startup completed"
else
    log_message "ERROR: manage_all_services.sh not found"
    exit 1
fi

log_message "Startup script finished"