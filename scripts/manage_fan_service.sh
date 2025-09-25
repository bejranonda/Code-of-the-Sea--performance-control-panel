#!/bin/bash
# manage_fan_service.sh - Start/stop fan service properly

FAN_SCRIPT="/home/payas/cos/fan/fan_mic_menu.py"
PYTHON_PATH="/home/payas/venv/bin/python"
PIDFILE="/tmp/fan_service.pid"
LOGFILE="/home/payas/cos/fan/fan_service_management.log"

# Function to log events with timestamp
log_event() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAN SERVICE SCRIPT: $1" >> "$LOGFILE"
    echo "FAN SERVICE SCRIPT: $1"
}

# Source shared performance mode checking functions
source "/home/payas/cos/scripts/performance_mode_check.sh"

start_service() {
    log_event "START command received - checking performance mode"

    # Check if this service should start during performance mode
    if ! should_service_start_during_performance "fan"; then
        log_performance_decision "fan" "SKIP_START" "Performance mode active - fan service should remain stopped"
        return 0
    fi
    # First kill any existing instances
    echo "Checking for existing fan service instances..."
    EXISTING_PIDS=$(pgrep -f "fan_mic_menu.py" 2>/dev/null)
    if [ -n "$EXISTING_PIDS" ]; then
        echo "Found existing instances: $EXISTING_PIDS"
        pkill -f "fan_mic_menu.py"
        sleep 2
    fi

    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Fan service is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PIDFILE"
        fi
    fi

    echo "Starting fan service..."
    cd /home/payas/cos
    nohup "$PYTHON_PATH" "$FAN_SCRIPT" > /dev/null 2>&1 &
    PID=$!
    echo $PID > "$PIDFILE"
    sleep 2

    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Fan service started successfully (PID: $PID)"
        return 0
    else
        echo "Failed to start fan service"
        rm -f "$PIDFILE"
        return 1
    fi
}

stop_service() {
    echo "Stopping fan service..."

    # Kill any running fan processes (gentle first)
    pkill -f "fan_mic_menu.py" 2>/dev/null

    # Wait a moment for graceful shutdown
    sleep 2

    # Force kill if still running
    pkill -9 -f "fan_mic_menu.py" 2>/dev/null

    # Remove PID file
    rm -f "$PIDFILE"

    # Final wait and verify
    sleep 2

    # Check for any remaining processes
    REMAINING=$(pgrep -f "fan_mic_menu.py" 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        echo "Warning: Some processes may still be running:"
        ps -p $REMAINING 2>/dev/null || true
        return 1
    else
        echo "Fan service stopped successfully"
        return 0
    fi
}

status_service() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Fan service is running (PID: $PID)"
            return 0
        else
            echo "PID file exists but process is not running (stale PID file)"
            return 1
        fi
    else
        if pgrep -f "fan_mic_menu.py" > /dev/null; then
            echo "Fan service appears to be running but no PID file found"
            pgrep -f "fan_mic_menu.py"
            return 2
        else
            echo "Fan service is not running"
            return 3
        fi
    fi
}

case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        sleep 2
        start_service
        ;;
    status)
        status_service
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac