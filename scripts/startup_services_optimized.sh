#!/bin/bash
# startup_services_optimized.sh - Conflict-aware startup for COS services

SCRIPT_DIR="/home/payas/cos/scripts"
LOG_FILE="/home/payas/cos/startup.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to wait for audio system to be ready
wait_for_audio() {
    log_message "Waiting for audio system to be ready..."
    for i in {1..10}; do
        if pactl list short sources | grep -q "RUNNING"; then
            log_message "Audio system ready"
            return 0
        fi
        sleep 2
    done
    log_message "Warning: Audio system may not be fully ready"
    return 1
}

# Function to start services with conflict awareness
start_services_sequentially() {
    log_message "Starting COS services with conflict awareness..."

    # Phase 1: Non-audio dependent services first
    log_message "Phase 1: Starting non-audio services..."

    # Radio service (independent)
    if [ -f "$SCRIPT_DIR/manage_radio_service.sh" ]; then
        log_message "Starting Radio service..."
        "$SCRIPT_DIR/manage_radio_service.sh" start 2>&1 | tee -a "$LOG_FILE"
        sleep 2
    fi

    # Fan service (independent)
    if [ -f "$SCRIPT_DIR/manage_fan_service.sh" ]; then
        log_message "Starting Fan service..."
        "$SCRIPT_DIR/manage_fan_service.sh" start 2>&1 | tee -a "$LOG_FILE"
        sleep 2
    fi

    # Wait for audio system
    wait_for_audio

    # Phase 2: Audio-dependent services
    log_message "Phase 2: Starting audio-dependent services..."

    # LED service first (primary audio user for performance mode)
    if [ -f "$SCRIPT_DIR/manage_led_service.sh" ]; then
        log_message "Starting LED service (primary audio user)..."
        "$SCRIPT_DIR/manage_led_service.sh" start 2>&1 | tee -a "$LOG_FILE"
        sleep 3
    fi

    # Broadcast service (audio output)
    if [ -f "$SCRIPT_DIR/manage_broadcast_service.sh" ]; then
        log_message "Starting Broadcast service..."
        "$SCRIPT_DIR/manage_broadcast_service.sh" start 2>&1 | tee -a "$LOG_FILE"
        sleep 2
    fi

    # Mixing service last (can conflict with LED audio input)
    # Start in disabled mode to avoid immediate conflict
    if [ -f "$SCRIPT_DIR/manage_mixing_service.sh" ]; then
        log_message "Starting Mixing service (disabled mode to avoid audio conflicts)..."
        "$SCRIPT_DIR/manage_mixing_service.sh" start 2>&1 | tee -a "$LOG_FILE"

        # Ensure mixing starts in disabled mode
        sleep 2
        python3 -c "
import json
import os
mixing_config_file = '/home/payas/cos/service_config.json'
if os.path.exists(mixing_config_file):
    with open(mixing_config_file, 'r') as f:
        config = json.load(f)
    config['Mixing Service']['mode'] = 'Disable'
    with open(mixing_config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print('Set mixing service to disabled mode to prevent audio conflicts')
"
    fi

    log_message "Phase 3: Service health check..."
    sleep 5
    "$SCRIPT_DIR/manage_all_services.sh" status 2>&1 | tee -a "$LOG_FILE"
}

# Main execution
log_message "Optimized COS services startup initiated"

# Wait for system to be ready
log_message "Waiting for system to be ready..."
sleep 15

# Change to correct directory
cd /home/payas/cos

# Start services with conflict awareness
start_services_sequentially

log_message "Optimized startup completed - Services started with conflict prevention"
log_message "Note: Mixing service started in disabled mode to prevent audio conflicts with LED service"
log_message "Use web interface to enable mixing when not using LED performance mode"