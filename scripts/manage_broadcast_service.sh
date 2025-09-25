#!/bin/bash
# manage_broadcast_service.sh - Start/stop broadcast service properly

BROADCAST_SCRIPT="/home/payas/cos/broadcast/broadcast_menu.py"
PYTHON_PATH="/home/payas/venv/bin/python"
PIDFILE="/tmp/broadcast_service.pid"

# Source shared performance mode checking functions
source "/home/payas/cos/scripts/performance_mode_check.sh"

start_service() {
    # Check if this service should start during performance mode
    if ! should_service_start_during_performance "broadcast"; then
        log_performance_decision "broadcast" "SKIP_START" "Performance mode active - broadcast service should remain stopped"
        return 0
    fi
    # First kill any existing instances
    echo "Checking for existing broadcast service instances..."
    EXISTING_PIDS=$(pgrep -f "broadcast_menu.py" 2>/dev/null)
    if [ -n "$EXISTING_PIDS" ]; then
        echo "Found existing instances: $EXISTING_PIDS"
        pkill -f "broadcast_menu.py"
        sleep 2
    fi

    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Broadcast service is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PIDFILE"
        fi
    fi

    echo "Starting broadcast service..."
    cd /home/payas/cos
    nohup "$PYTHON_PATH" "$BROADCAST_SCRIPT" > /dev/null 2>&1 &
    PID=$!
    echo $PID > "$PIDFILE"
    sleep 2

    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Broadcast service started successfully (PID: $PID)"
        return 0
    else
        echo "Failed to start broadcast service"
        rm -f "$PIDFILE"
        return 1
    fi
}

stop_service() {
    echo "Stopping broadcast service..."

    # Kill any running broadcast processes (gentle first)
    pkill -f "broadcast_menu.py" 2>/dev/null

    # Stop any mpg123 processes that might be playing audio
    pkill -f "mpg123" 2>/dev/null

    # Wait a moment for graceful shutdown
    sleep 2

    # Force kill if still running
    pkill -9 -f "broadcast_menu.py" 2>/dev/null
    pkill -9 -f "mpg123" 2>/dev/null

    # Remove PID file
    rm -f "$PIDFILE"

    # Final wait and verify
    sleep 2

    # Check for any remaining processes
    REMAINING=$(pgrep -f "broadcast_menu.py" 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        echo "Warning: Some processes may still be running:"
        ps -p $REMAINING 2>/dev/null || true
        return 1
    else
        echo "Broadcast service stopped successfully"
        return 0
    fi
}

status_service() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Broadcast service is running (PID: $PID)"
            return 0
        else
            echo "PID file exists but process is not running (stale PID file)"
            return 1
        fi
    else
        if pgrep -f "broadcast_menu.py" > /dev/null; then
            echo "Broadcast service appears to be running but no PID file found"
            pgrep -f "broadcast_menu.py"
            return 2
        else
            echo "Broadcast service is not running"
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