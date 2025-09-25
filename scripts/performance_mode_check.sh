#!/bin/bash
# performance_mode_check.sh - Shared performance mode checking functions

# Function to check if performance mode is active
is_performance_mode_active() {
    # Check for performance mode flag file
    if [ -f "/tmp/cos_performance_mode_active" ]; then
        # Check if flag is stale (older than 10 minutes)
        local flag_age=$(($(date +%s) - $(stat -c %Y "/tmp/cos_performance_mode_active" 2>/dev/null || echo 0)))
        if [ $flag_age -gt 600 ]; then
            echo "Performance mode flag is stale (${flag_age}s old), removing it"
            rm -f "/tmp/cos_performance_mode_active" 2>/dev/null
            return 1
        else
            return 0
        fi
    fi
    return 1
}

# Function to check if a service should be allowed to start during performance mode
should_service_start_during_performance() {
    local service_name="$1"

    if ! is_performance_mode_active; then
        return 0  # Not in performance mode, service can start
    fi

    # Get performance mode type
    local performance_type=""
    if [ -f "/tmp/cos_performance_mode_active" ]; then
        performance_type=$(head -n 1 "/tmp/cos_performance_mode_active" 2>/dev/null || echo "unknown")
    fi

    case "$service_name" in
        "led")
            # LED service should run during LED performance modes
            if [[ "$performance_type" =~ "Musical LED" ]] || [[ "$performance_type" =~ "Manual LED" ]]; then
                return 0
            else
                return 1
            fi
            ;;
        "fan"|"broadcast"|"mixing"|"radio")
            # Other services should NOT start during any performance mode
            return 1
            ;;
        *)
            # Unknown service - be conservative and don't start
            return 1
            ;;
    esac
}

# Function to log performance mode decisions
log_performance_decision() {
    local service_name="$1"
    local decision="$2"
    local reason="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] PERFORMANCE-MODE-CHECK ($service_name): $decision - $reason"

    # Also log to service-specific logs if they exist
    case "$service_name" in
        "led")
            echo "[$timestamp] PERFORMANCE-MODE-CHECK: $decision - $reason" >> "/home/payas/cos/led/led_service_management.log" 2>/dev/null
            ;;
        "fan")
            echo "[$timestamp] PERFORMANCE-MODE-CHECK: $decision - $reason" >> "/home/payas/cos/fan/fan_service_management.log" 2>/dev/null
            ;;
        "broadcast")
            echo "[$timestamp] PERFORMANCE-MODE-CHECK: $decision - $reason" >> "/home/payas/cos/broadcast/broadcast_service_management.log" 2>/dev/null
            ;;
        "mixing")
            echo "[$timestamp] PERFORMANCE-MODE-CHECK: $decision - $reason" >> "/home/payas/cos/mixing/mixing_service_management.log" 2>/dev/null
            ;;
        "radio")
            echo "[$timestamp] PERFORMANCE-MODE-CHECK: $decision - $reason" >> "/home/payas/cos/radio/radio_service_management.log" 2>/dev/null
            ;;
    esac
}