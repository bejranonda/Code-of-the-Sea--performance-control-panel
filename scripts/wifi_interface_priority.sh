#!/bin/bash
# WiFi Interface Priority Manager
# Ensures WLAN1 is used when available, falls back to WLAN0

PREFERRED_INTERFACE="wlan1"
FALLBACK_INTERFACE="wlan0"
LOG_FILE="/home/payas/cos/network/wifi_interface_priority.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

interface_exists() {
    ip link show "$1" >/dev/null 2>&1
}

interface_is_up() {
    ip link show "$1" | grep -q "state UP"
}

interface_has_connection() {
    iwconfig "$1" 2>/dev/null | grep -q "ESSID:" && ! iwconfig "$1" 2>/dev/null | grep -q "ESSID:off/any"
}

get_interface_ip() {
    ip addr show "$1" 2>/dev/null | grep -o 'inet [0-9.]*' | cut -d' ' -f2
}

bring_interface_up() {
    local interface="$1"
    if ! interface_is_up "$interface"; then
        log_message "Bringing up interface $interface"
        sudo ip link set "$interface" up
        sleep 2
    fi
}

set_interface_priority() {
    # Check if preferred interface exists and can be used
    if interface_exists "$PREFERRED_INTERFACE"; then
        bring_interface_up "$PREFERRED_INTERFACE"

        if interface_has_connection "$PREFERRED_INTERFACE"; then
            local preferred_ip=$(get_interface_ip "$PREFERRED_INTERFACE")
            log_message "Using preferred interface $PREFERRED_INTERFACE (IP: ${preferred_ip:-none})"

            # If both interfaces are connected, prioritize WLAN1 in routing table
            if interface_exists "$FALLBACK_INTERFACE" && interface_has_connection "$FALLBACK_INTERFACE"; then
                log_message "Both interfaces connected - setting $PREFERRED_INTERFACE as priority"
                # Add route with higher priority for WLAN1 (lower metric = higher priority)
                sudo ip route del default dev "$FALLBACK_INTERFACE" 2>/dev/null || true
                sudo ip route add default dev "$PREFERRED_INTERFACE" metric 100 2>/dev/null || true
                sudo ip route add default dev "$FALLBACK_INTERFACE" metric 200 2>/dev/null || true
            fi
            return 0
        else
            log_message "Preferred interface $PREFERRED_INTERFACE available but not connected"
        fi
    else
        log_message "Preferred interface $PREFERRED_INTERFACE not available"
    fi

    # Fall back to WLAN0
    if interface_exists "$FALLBACK_INTERFACE"; then
        bring_interface_up "$FALLBACK_INTERFACE"

        if interface_has_connection "$FALLBACK_INTERFACE"; then
            local fallback_ip=$(get_interface_ip "$FALLBACK_INTERFACE")
            log_message "Using fallback interface $FALLBACK_INTERFACE (IP: ${fallback_ip:-none})"
            return 0
        else
            log_message "Fallback interface $FALLBACK_INTERFACE available but not connected"
        fi
    else
        log_message "Fallback interface $FALLBACK_INTERFACE not available"
    fi

    log_message "No suitable WiFi interface found"
    return 1
}

# Main execution
case "${1:-check}" in
    "check")
        log_message "Checking WiFi interface priority"
        set_interface_priority
        ;;
    "monitor")
        log_message "Starting WiFi interface priority monitor"
        while true; do
            set_interface_priority
            sleep 30  # Check every 30 seconds
        done
        ;;
    "status")
        echo "WiFi Interface Priority Status:"
        echo "=============================="

        for interface in "$PREFERRED_INTERFACE" "$FALLBACK_INTERFACE"; do
            if interface_exists "$interface"; then
                status="EXISTS"
                if interface_is_up "$interface"; then
                    status="$status, UP"
                    if interface_has_connection "$interface"; then
                        ip=$(get_interface_ip "$interface")
                        essid=$(iwconfig "$interface" 2>/dev/null | grep -o 'ESSID:"[^"]*"' | cut -d'"' -f2)
                        status="$status, CONNECTED to '$essid' (IP: ${ip:-none})"
                    else
                        status="$status, NO CONNECTION"
                    fi
                else
                    status="$status, DOWN"
                fi
            else
                status="NOT AVAILABLE"
            fi

            echo "$interface: $status"
        done

        echo ""
        echo "Current routes:"
        ip route show | grep default
        ;;
    *)
        echo "Usage: $0 {check|monitor|status}"
        echo "  check   - Check and set interface priority once"
        echo "  monitor - Continuously monitor and manage interface priority"
        echo "  status  - Show current interface status"
        exit 1
        ;;
esac