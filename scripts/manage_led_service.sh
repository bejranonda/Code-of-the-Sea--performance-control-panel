#!/bin/bash
# manage_led_service.sh - Start/stop LED service properly

LED_SCRIPT="/home/payas/cos/led/lighting_menu.py"
PYTHON_PATH="/home/payas/venv/bin/python"
PIDFILE="/home/payas/cos/led/led_service.pid"  # Moved from /tmp to project directory
LOGFILE="/home/payas/cos/led/led_service_management.log"
STATUSFILE="/home/payas/cos/led/led_status.json"

# Function to log events with timestamp
log_event() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] LED SERVICE SCRIPT: $1" >> "$LOGFILE"
    echo "LED SERVICE SCRIPT: $1"
}

# Source shared performance mode checking functions
source "/home/payas/cos/scripts/performance_mode_check.sh"

# Function to detect and adopt orphaned processes
adopt_orphan() {
    local orphan_pids=$(pgrep -f "lighting_menu.py" 2>/dev/null)
    if [ -n "$orphan_pids" ]; then
        # Check if orphan is actually working by checking status file age
        if [ -f "$STATUSFILE" ]; then
            local status_age=$(($(date +%s) - $(stat -c %Y "$STATUSFILE" 2>/dev/null || echo 0)))
            if [ $status_age -lt 30 ]; then  # Status file updated within 30 seconds
                # Orphan is working, adopt it
                local main_pid=$(echo $orphan_pids | awk '{print $1}')
                echo $main_pid > "$PIDFILE"
                log_event "Adopted working orphaned process (PID: $main_pid) - PID file recreated"
                return 0
            else
                log_event "Found orphaned process with stale status (age: ${status_age}s) - will terminate and restart"
                pkill -f "lighting_menu.py" 2>/dev/null
                sleep 2
            fi
        else
            log_event "Found orphaned process with no status file - will terminate and restart"
            pkill -f "lighting_menu.py" 2>/dev/null
            sleep 2
        fi
    fi
    return 1
}

start_service() {
    log_event "START command received - checking for existing instances"

    # Check if this service should start during performance mode
    if ! should_service_start_during_performance "led"; then
        log_performance_decision "led" "SKIP_START" "Performance mode active but not LED performance mode"
        return 0
    fi

    if is_performance_mode_active; then
        log_performance_decision "led" "ALLOW_START" "LED performance mode requires LED service to run"
    fi

    # Check if we have a valid PID file first
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_event "Service already running (PID: $PID) - start request ignored"
            return 0
        else
            log_event "PID file exists but process not running - removing stale PID file"
            rm -f "$PIDFILE"
        fi
    fi

    # Try to adopt orphaned processes first (avoid unnecessary restarts)
    if adopt_orphan; then
        log_event "Successfully adopted orphaned process - no restart needed"
        return 0
    fi

    # Kill any remaining instances after orphan adoption failed
    EXISTING_PIDS=$(pgrep -f "lighting_menu.py" 2>/dev/null)
    if [ -n "$EXISTING_PIDS" ]; then
        log_event "Found remaining instances: $EXISTING_PIDS - terminating them"
        pkill -f "lighting_menu.py"
        sleep 2
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
            rm -f "$PIDFILE"
            # Check for orphans after removing stale PID file
            if adopt_orphan; then
                log_event "Adopted orphaned process during status check"
                return 0
            else
                return 1
            fi
        fi
    else
        # No PID file - check for orphans and try to adopt them
        if adopt_orphan; then
            log_event "Found and adopted orphaned process during status check"
            return 0
        elif pgrep -f "lighting_menu.py" > /dev/null; then
            ORPHAN_PIDS=$(pgrep -f "lighting_menu.py")
            log_event "Found non-working orphaned processes (PIDs: $ORPHAN_PIDS)"
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