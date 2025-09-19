#!/usr/bin/env python3
"""
Metrics Recording System for Exhibition Monitor
Records lux values, CPU usage, CPU temperature, and disk usage every 5 minutes
"""

import json
import time
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from hardware_monitor import HardwareMonitor


class MetricsRecorder:
    """Records and manages system metrics for exhibition monitoring"""

    def __init__(self, data_file: str = None, max_records: int = 10000):
        self.data_file = data_file or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'exhibition_metrics.json'
        )
        self.max_records = max_records
        self.hardware_monitor = HardwareMonitor()
        self.recording_interval = 300  # 5 minutes in seconds
        self.recording_thread = None
        self.should_stop = False
        self.last_lux_file = os.path.join(
            os.path.dirname(__file__), '..', 'led', 'lux_history.json'
        )

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

        # Migrate existing lux data on first run
        self._migrate_lux_data()

    def _migrate_lux_data(self):
        """Migrate existing lux data from led/lux_history.json"""
        if os.path.exists(self.last_lux_file) and not os.path.exists(self.data_file):
            try:
                with open(self.last_lux_file, 'r') as f:
                    lux_data = json.load(f)

                # Convert lux data to new format
                migrated_records = []
                for entry in lux_data[-1000:]:  # Take last 1000 entries
                    timestamp = entry.get('timestamp')
                    if timestamp:
                        migrated_records.append({
                            'timestamp': timestamp,
                            'lux_value': entry.get('lux', 0),
                            'cpu_usage': None,  # Will be filled in later
                            'cpu_temperature': None,
                            'disk_usage': None
                        })

                if migrated_records:
                    self._save_records(migrated_records)
                    print(f"Migrated {len(migrated_records)} lux records to new metrics system")

            except Exception as e:
                print(f"Error migrating lux data: {e}")

    def get_latest_lux_value(self) -> Optional[float]:
        """Get the latest lux value from the LED service"""
        try:
            if os.path.exists(self.last_lux_file):
                with open(self.last_lux_file, 'r') as f:
                    lux_data = json.load(f)
                    if lux_data:
                        return lux_data[-1].get('lux', 0)
        except Exception:
            pass
        return None

    def record_metrics(self) -> Dict[str, Any]:
        """Record current system metrics"""
        try:
            # Get hardware metrics
            hw_info = self.hardware_monitor.get_comprehensive_info()

            # Get latest lux value
            lux_value = self.get_latest_lux_value()

            # Create record
            record = {
                'timestamp': datetime.now().isoformat(),
                'lux_value': lux_value,
                'cpu_usage': hw_info.get('cpu_percent', 0),
                'cpu_temperature': hw_info.get('cpu_temp'),
                'disk_usage': hw_info.get('disk', {}).get('percent', 0)
            }

            # Load existing records
            records = self._load_records()

            # Add new record
            records.append(record)

            # Trim to max records
            if len(records) > self.max_records:
                records = records[-self.max_records:]

            # Save records
            self._save_records(records)

            return record

        except Exception as e:
            print(f"Error recording metrics: {e}")
            return {}

    def _load_records(self) -> List[Dict[str, Any]]:
        """Load existing records from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading records: {e}")
        return []

    def _save_records(self, records: List[Dict[str, Any]]):
        """Save records to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            print(f"Error saving records: {e}")

    def get_records(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get records from the last N hours"""
        records = self._load_records()

        if not records:
            return []

        # Filter records by time
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_records = []

        for record in records:
            try:
                record_time = datetime.fromisoformat(record['timestamp'])
                if record_time >= cutoff_time:
                    filtered_records.append(record)
            except (ValueError, KeyError):
                continue

        return filtered_records

    def get_chart_data(self, hours: int = 24) -> Dict[str, Any]:
        """Get data formatted for charts"""
        records = self.get_records(hours)

        if not records:
            return {
                'timestamps': [],
                'lux_values': [],
                'cpu_usage': [],
                'cpu_temperature': [],
                'disk_usage': []
            }

        # Extract data for charts
        timestamps = []
        lux_values = []
        cpu_usage = []
        cpu_temperature = []
        disk_usage = []

        for record in records:
            timestamps.append(record['timestamp'])
            lux_values.append(record.get('lux_value', 0) or 0)
            cpu_usage.append(record.get('cpu_usage', 0) or 0)
            cpu_temperature.append(record.get('cpu_temperature', 0) or 0)
            disk_usage.append(record.get('disk_usage', 0) or 0)

        return {
            'timestamps': timestamps,
            'lux_values': lux_values,
            'cpu_usage': cpu_usage,
            'cpu_temperature': cpu_temperature,
            'disk_usage': disk_usage
        }

    def start_recording(self):
        """Start automatic recording every 5 minutes"""
        if self.recording_thread and self.recording_thread.is_alive():
            return

        self.should_stop = False
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()
        print("Metrics recording started")

    def stop_recording(self):
        """Stop automatic recording"""
        self.should_stop = True
        if self.recording_thread:
            self.recording_thread.join(timeout=5)
        print("Metrics recording stopped")

    def _recording_loop(self):
        """Main recording loop"""
        while not self.should_stop:
            try:
                self.record_metrics()
                print(f"Metrics recorded at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                print(f"Error in recording loop: {e}")

            # Wait for next interval (5 minutes)
            for _ in range(self.recording_interval):
                if self.should_stop:
                    break
                time.sleep(1)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the recorded data"""
        records = self._load_records()

        if not records:
            return {
                'total_records': 0,
                'oldest_record': None,
                'newest_record': None,
                'disk_usage_mb': 0
            }

        # Calculate file size
        file_size = 0
        if os.path.exists(self.data_file):
            file_size = os.path.getsize(self.data_file) / (1024 * 1024)  # MB

        return {
            'total_records': len(records),
            'oldest_record': records[0].get('timestamp') if records else None,
            'newest_record': records[-1].get('timestamp') if records else None,
            'disk_usage_mb': round(file_size, 2)
        }


# Global instance
_metrics_recorder = None

def get_metrics_recorder() -> MetricsRecorder:
    """Get singleton metrics recorder instance"""
    global _metrics_recorder
    if _metrics_recorder is None:
        _metrics_recorder = MetricsRecorder()
    return _metrics_recorder