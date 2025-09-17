#!/bin/bash
# manage_led_service.sh - Start/stop LED service properly

LED_SCRIPT="/home/payas/cos/led/lighting_menu.py"
PYTHON_PATH="/home/payas/venv/bin/python"
PIDFILE="/tmp/led_service.pid"

start_service() {
    # First kill any existing instances
    echo "Checking for existing LED service instances..."
    EXISTING_PIDS=$(pgrep -f "lighting_menu.py" 2>/dev/null)
    if [ -n "$EXISTING_PIDS" ]; then
        echo "Found existing instances: $EXISTING_PIDS"
        pkill -f "lighting_menu.py"
        sleep 2
    fi

    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "LED service is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PIDFILE"
        fi
    fi

    echo "Starting LED service..."
    cd /home/payas/cos
    nohup "$PYTHON_PATH" "$LED_SCRIPT" > /dev/null 2>&1 &
    PID=$!
    echo $PID > "$PIDFILE"
    sleep 2

    if ps -p "$PID" > /dev/null 2>&1; then
        echo "LED service started successfully (PID: $PID)"
        return 0
    else
        echo "Failed to start LED service"
        rm -f "$PIDFILE"
        return 1
    fi
}

stop_service() {
    echo "Stopping LED service..."

    # Kill any running LED processes (gentle first)
    pkill -f "lighting_menu.py" 2>/dev/null

    # Wait a moment for graceful shutdown
    sleep 2

    # Force kill if still running
    pkill -9 -f "lighting_menu.py" 2>/dev/null

    # Remove PID file
    rm -f "$PIDFILE"

    # Final wait and verify
    sleep 2

    # Check for any remaining processes
    REMAINING=$(pgrep -f "lighting_menu.py" 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        echo "Warning: Some processes may still be running:"
        ps -p $REMAINING 2>/dev/null || true
        return 1
    else
        echo "LED service stopped successfully"
        return 0
    fi
}

status_service() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "LED service is running (PID: $PID)"
            return 0
        else
            echo "PID file exists but process is not running (stale PID file)"
            return 1
        fi
    else
        if pgrep -f "lighting_menu.py" > /dev/null; then
            echo "LED service appears to be running but no PID file found"
            pgrep -f "lighting_menu.py"
            return 2
        else
            echo "LED service is not running"
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