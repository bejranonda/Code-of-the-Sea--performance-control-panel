#!/bin/bash
# manage_led_service.sh - Start/stop LED service properly

LED_SCRIPT="/home/payas/cos/led/lighting_menu.py"
PYTHON_PATH="/home/payas/venv/bin/python"
PIDFILE="/tmp/led_service.pid"
LOGFILE="/home/payas/cos/led/led_service_management.log"

# Function to log events with timestamp
log_event() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] LED SERVICE SCRIPT: $1" >> "$LOGFILE"
    echo "LED SERVICE SCRIPT: $1"
}

start_service() {
    log_event "START command received - checking for existing instances"

    # First kill any existing instances
    EXISTING_PIDS=$(pgrep -f "lighting_menu.py" 2>/dev/null)
    if [ -n "$EXISTING_PIDS" ]; then
        log_event "Found existing instances: $EXISTING_PIDS - terminating them"
        pkill -f "lighting_menu.py"
        sleep 2
    fi

    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_event "Service already running (PID: $PID) - start request ignored"
            return 1
        else
            log_event "Removing stale PID file"
            rm -f "$PIDFILE"
        fi
    fi

    log_event "Starting LED service..."
    cd /home/payas/cos
    nohup "$PYTHON_PATH" "$LED_SCRIPT" > /dev/null 2>&1 &
    PID=$!
    echo $PID > "$PIDFILE"
    sleep 2

    if ps -p "$PID" > /dev/null 2>&1; then
        log_event "LED service started successfully (PID: $PID)"
        return 0
    else
        log_event "FAILED to start LED service - process died immediately"
        rm -f "$PIDFILE"
        return 1
    fi
}

stop_service() {
    log_event "STOP command received - terminating LED service"

    # Kill any running LED processes (gentle first)
    RUNNING_PIDS=$(pgrep -f "lighting_menu.py" 2>/dev/null)
    if [ -n "$RUNNING_PIDS" ]; then
        log_event "Found running processes: $RUNNING_PIDS - sending TERM signal"
        pkill -f "lighting_menu.py" 2>/dev/null
    else
        log_event "No running processes found"
    fi

    # Wait a moment for graceful shutdown
    sleep 2

    # Force kill if still running
    STILL_RUNNING=$(pgrep -f "lighting_menu.py" 2>/dev/null)
    if [ -n "$STILL_RUNNING" ]; then
        log_event "Processes still running: $STILL_RUNNING - sending KILL signal"
        pkill -9 -f "lighting_menu.py" 2>/dev/null
    fi

    # Remove PID file
    rm -f "$PIDFILE"

    # Final wait and verify
    sleep 2

    # Check for any remaining processes
    REMAINING=$(pgrep -f "lighting_menu.py" 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        log_event "WARNING: Some processes may still be running: $REMAINING"
        ps -p $REMAINING 2>/dev/null || true
        return 1
    else
        log_event "LED service stopped successfully"
        return 0
    fi
}

status_service() {
    log_event "STATUS command received - checking service state"
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_event "Service is running (PID: $PID)"
            return 0
        else
            log_event "PID file exists but process is not running (stale PID file)"
            return 1
        fi
    else
        if pgrep -f "lighting_menu.py" > /dev/null; then
            ORPHAN_PIDS=$(pgrep -f "lighting_menu.py")
            log_event "Service appears to be running but no PID file found (orphan PIDs: $ORPHAN_PIDS)"
            return 2
        else
            log_event "Service is not running"
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