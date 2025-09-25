#!/bin/bash
# manage_mixing_service.sh - Start/stop mixing service properly

MIXING_SCRIPT="/home/payas/cos/mixing/mixing_menu.py"
PYTHON_PATH="/home/payas/venv/bin/python"
PIDFILE="/tmp/mixing_service.pid"

# Source shared performance mode checking functions
source "/home/payas/cos/scripts/performance_mode_check.sh"

start_service() {
    # Check if this service should start during performance mode
    if ! should_service_start_during_performance "mixing"; then
        log_performance_decision "mixing" "SKIP_START" "Performance mode active - mixing service should remain stopped"
        return 0
    fi
    # First kill any existing instances
    echo "Checking for existing mixing service instances..."
    EXISTING_PIDS=$(pgrep -f "mixing_menu.py" 2>/dev/null)
    if [ -n "$EXISTING_PIDS" ]; then
        echo "Found existing instances: $EXISTING_PIDS"
        pkill -f "mixing_menu.py"
        sleep 2
    fi

    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Mixing service is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PIDFILE"
        fi
    fi

    echo "Starting mixing service..."
    cd /home/payas/cos
    nohup "$PYTHON_PATH" "$MIXING_SCRIPT" > /dev/null 2>&1 &
    PID=$!
    echo $PID > "$PIDFILE"
    sleep 2

    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Mixing service started successfully (PID: $PID)"
        return 0
    else
        echo "Failed to start mixing service"
        rm -f "$PIDFILE"
        return 1
    fi
}

stop_service() {
    echo "Stopping mixing service..."

    # Kill any running mixing processes (gentle first)
    pkill -f "mixing_menu.py" 2>/dev/null

    # Kill all arecord processes (any format)
    pkill -f "arecord" 2>/dev/null

    # Kill any Python processes related to mixing
    pkill -f "python.*mixing" 2>/dev/null

    # Wait a moment for graceful shutdown
    sleep 2

    # Force kill if still running
    pkill -9 -f "mixing_menu.py" 2>/dev/null
    pkill -9 -f "arecord" 2>/dev/null
    pkill -9 -f "python.*mixing" 2>/dev/null

    # Kill any processes holding audio devices
    fuser -k /dev/snd/* 2>/dev/null

    # Remove PID file
    rm -f "$PIDFILE"

    # Final wait and verify
    sleep 2

    # Check for any remaining processes
    REMAINING=$(pgrep -f "mixing_menu.py|arecord" 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        echo "Warning: Some processes may still be running:"
        ps -p $REMAINING 2>/dev/null || true
        return 1
    else
        echo "Mixing service stopped successfully"
        return 0
    fi
}

status_service() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Mixing service is running (PID: $PID)"
            return 0
        else
            echo "PID file exists but process is not running (stale PID file)"
            return 1
        fi
    else
        if pgrep -f "mixing_menu.py" > /dev/null; then
            echo "Mixing service appears to be running but no PID file found"
            pgrep -f "mixing_menu.py"
            return 2
        else
            echo "Mixing service is not running"
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