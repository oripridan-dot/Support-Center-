"""
Activity Logger - Logs HP worker activity for Recent Activity panel
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import threading

ACTIVITY_LOG_FILE = Path("/tmp/hp_activity_log.json")
_lock = threading.Lock()


class ActivityLogger:
    """Logs worker activity for real-time UI display"""
    
    def __init__(self, max_events: int = 100):
        self.max_events = max_events
    
    def log_event(self, message: str, category: str = "info", brand: str = None):
        """Log an activity event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "category": category,  # info, success, error, warning
            "brand": brand
        }
        
        with _lock:
            events = self._read_events()
            events.insert(0, event)  # Add to front
            events = events[:self.max_events]  # Trim to max
            self._write_events(events)
    
    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """Get recent activity events"""
        with _lock:
            events = self._read_events()
            return events[:limit]
    
    def clear(self):
        """Clear all events"""
        with _lock:
            self._write_events([])
    
    def _read_events(self) -> List[Dict]:
        """Read events from file"""
        try:
            if ACTIVITY_LOG_FILE.exists():
                with open(ACTIVITY_LOG_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return []
    
    def _write_events(self, events: List[Dict]):
        """Write events to file"""
        try:
            ACTIVITY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ACTIVITY_LOG_FILE, 'w') as f:
                json.dump(events, f, indent=2)
        except Exception as e:
            print(f"Failed to write activity log: {e}")


# Global instance
activity_logger = ActivityLogger()
