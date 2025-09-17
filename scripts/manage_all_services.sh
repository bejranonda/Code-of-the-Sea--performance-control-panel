#!/bin/bash
# manage_all_services.sh - Master script to manage all COS services

SCRIPT_DIR="/home/payas/cos/scripts"
SERVICES=("radio" "led" "fan" "broadcast" "mixing")

usage() {
    echo "Usage: $0 {start|stop|restart|status} [service_name]"
    echo "Services: ${SERVICES[*]}"
    echo "If no service_name specified, applies to all services"
}

manage_service() {
    local action=$1
    local service=$2

    if [ -f "$SCRIPT_DIR/manage_${service}_service.sh" ]; then
        echo "=== $action $service service ==="
        "$SCRIPT_DIR/manage_${service}_service.sh" "$action"
        echo ""
    else
        echo "Error: Service script for $service not found"
        return 1
    fi
}

case "$1" in
    start|stop|restart|status)
        ACTION=$1
        if [ -n "$2" ]; then
            # Single service specified
            SERVICE=$2
            if [[ " ${SERVICES[@]} " =~ " ${SERVICE} " ]]; then
                manage_service "$ACTION" "$SERVICE"
            else
                echo "Error: Unknown service '$SERVICE'"
                usage
                exit 1
            fi
        else
            # All services
            for service in "${SERVICES[@]}"; do
                manage_service "$ACTION" "$service"
            done
        fi
        ;;
    *)
        usage
        exit 1
        ;;
esac