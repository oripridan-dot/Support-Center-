"""
Real-time ingestion status tracker for UI updates
Writes status to JSON file that API endpoints serve in real-time
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Callable
import threading
import fcntl
import os

INGESTION_STATUS_FILE = Path("/tmp/ingestion_status.json")

class IngestionTracker:
    """Process-safe tracker for ingestion progress using file locking"""
    
    def __init__(self):
        self.status = {
            "is_running": False,
            "current_brand": None,
            "current_step": None,
            "current_document": None,
            "total_documents": 0,
            "documents_by_brand": {},
            "urls_discovered": 0,
            "urls_processed": 0,
            "progress_percent": 0.0,
            "last_updated": "",
            "errors": [],
            "start_time": "",
            "estimated_completion": "",
            "brand_progress": {}
        }
        # Ensure file exists
        if not INGESTION_STATUS_FILE.exists():
            self._save_initial()

    def _save_initial(self):
        try:
            with open(INGESTION_STATUS_FILE, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception:
            pass

    def _read_modify_write(self, update_func: Callable[[Dict], None]):
        """Safely read, modify, and write status using file locking"""
        try:
            # Open file for reading and writing
            # We use os.open to ensure we can lock it properly
            with open(INGESTION_STATUS_FILE, 'r+') as f:
                # Acquire exclusive lock
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    # Read current content
                    content = f.read()
                    if content:
                        try:
                            data = json.loads(content)
                            self.status.update(data)
                        except json.JSONDecodeError:
                            pass # Corrupt file, overwrite with current memory state
                    
                    # Apply update
                    update_func(self.status)
                    self.status["last_updated"] = datetime.now().isoformat()
                    
                    # Write back
                    f.seek(0)
                    f.truncate()
                    json.dump(self.status, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    # Release lock
                    fcntl.flock(f, fcntl.LOCK_UN)
        except FileNotFoundError:
            # If file doesn't exist, create it
            self._save_initial()
            self._read_modify_write(update_func)
        except Exception as e:
            print(f"Failed to update ingestion status: {e}")

    def reload(self):
        """Force reload of status from file"""
        def noop(status): pass
        self._read_modify_write(noop)
    
    def start(self, brand: Optional[str] = None):
        """Mark ingestion as started"""
        def update(status):
            status["is_running"] = True
            status["start_time"] = datetime.now().isoformat()
            status["current_brand"] = brand
            status["current_document"] = None
            status["total_documents"] = 0
            status["urls_discovered"] = 0
            status["urls_processed"] = 0
            status["documents_by_brand"] = {}
            status["errors"] = []
            status["brand_progress"] = {}
        self._read_modify_write(update)
    
    def update_progress(self, updates: Dict):
        """Generic update method"""
        def update(status):
            status.update(updates)
        self._read_modify_write(update)

    def update_step(self, step: str, brand: Optional[str] = None):
        """Update current step"""
        def update(status):
            status["current_step"] = step
            if brand:
                status["current_brand"] = brand
        self._read_modify_write(update)
    
    def update_urls(self, discovered: int, processed: int, brand_name: Optional[str] = None):
        """Update URL discovery/processing progress"""
        def update(status):
            # Update global stats (this might be inaccurate in parallel mode, but gives an idea)
            status["urls_discovered"] = discovered
            status["urls_processed"] = processed
            if discovered > 0:
                status["progress_percent"] = min(100, (processed / discovered) * 100)
            
            # Update specific brand progress if provided
            if brand_name and brand_name in status["brand_progress"]:
                status["brand_progress"][brand_name]["urls_discovered"] = discovered
                status["brand_progress"][brand_name]["documents_ingested"] = processed
                status["brand_progress"][brand_name]["status"] = "processing"
        self._read_modify_write(update)
    
    def update_brand_start(self, brand_name: str, brand_id: int):
        """Called when starting to process a new brand"""
        def update(status):
            status["current_brand"] = brand_name
            status["current_step"] = f"Discovering URLs for {brand_name}..."
            
            status["brand_progress"][brand_name] = {
                "brand_id": brand_id,
                "status": "discovering",
                "urls_discovered": 0,
                "documents_ingested": 0,
                "start_time": datetime.now().isoformat()
            }
        self._read_modify_write(update)
    
    def update_urls_discovered(self, brand_name: str, count: int):
        """Update URL discovery count for a brand"""
        def update(status):
            status["current_step"] = f"Discovered {count} URLs for {brand_name}, processing..."
            if brand_name in status["brand_progress"]:
                status["brand_progress"][brand_name]["urls_discovered"] = count
                status["brand_progress"][brand_name]["status"] = "processing"
        self._read_modify_write(update)
    
    def update_document_count(self, brand: str, count: int):
        """Update document count for a brand"""
        def update(status):
            status["documents_by_brand"][brand] = count
            status["total_documents"] = sum(status["documents_by_brand"].values())
            
            if brand in status["brand_progress"]:
                status["brand_progress"][brand]["documents_ingested"] = count
        self._read_modify_write(update)
    
    def update_brand_complete(self, brand_name: str, total_docs: int):
        """Mark a brand as complete"""
        def update(status):
            if brand_name in status["brand_progress"]:
                status["brand_progress"][brand_name]["status"] = "complete"
                status["brand_progress"][brand_name]["documents_ingested"] = total_docs
                # Force 100% completion for UI
                status["brand_progress"][brand_name]["urls_discovered"] = total_docs
                status["brand_progress"][brand_name]["end_time"] = datetime.now().isoformat()
            
            status["current_step"] = f"✅ {brand_name} complete ({total_docs} documents)"
        self._read_modify_write(update)
    
    def add_error(self, error: str):
        """Add an error to the list"""
        def update(status):
            status["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "message": error
            })
        self._read_modify_write(update)
    
    def complete(self):
        """Mark ingestion as complete"""
        def update(status):
            status["is_running"] = False
            status["progress_percent"] = 100.0
            status["current_step"] = "✅ Comprehensive ingestion complete!"
            status["estimated_completion"] = datetime.now().isoformat()
        self._read_modify_write(update)
    
    def reset(self):
        """Reset tracker"""
        def update(status):
            status.clear()
            status.update({
                "is_running": False,
                "current_brand": None,
                "current_step": None,
                "total_documents": 0,
                "documents_by_brand": {},
                "urls_discovered": 0,
                "urls_processed": 0,
                "progress_percent": 0.0,
                "last_updated": "",
                "errors": [],
                "start_time": "",
                "estimated_completion": "",
                "brand_progress": {}
            })
        self._read_modify_write(update)
    
    def save(self):
        pass


# Global tracker instance
tracker = IngestionTracker()
