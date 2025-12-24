"""
Real-time ingestion status tracker for UI updates
Writes status to JSON file that API endpoints serve in real-time
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import threading

INGESTION_STATUS_FILE = Path("/tmp/ingestion_status.json")

class IngestionTracker:
    """Thread-safe tracker for ingestion progress"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self.status = {
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
        }
        self._load_existing()
    
    def _load_existing(self):
        """Load existing status from file if it exists"""
        if INGESTION_STATUS_FILE.exists():
            try:
                with open(INGESTION_STATUS_FILE, 'r') as f:
                    data = json.load(f)
                    self.status.update(data)
            except Exception:
                pass
    
    def start(self, brand: Optional[str] = None):
        """Mark ingestion as started"""
        with self._lock:
            self.status["is_running"] = True
            self.status["start_time"] = datetime.now().isoformat()
            self.status["current_brand"] = brand
            self.status["total_documents"] = 0
            self.status["urls_discovered"] = 0
            self.status["urls_processed"] = 0
            self.status["documents_by_brand"] = {}
            self.status["errors"] = []
            self.status["brand_progress"] = {}
        self.save()
    
    def update_step(self, step: str, brand: Optional[str] = None):
        """Update current step"""
        with self._lock:
            self.status["current_step"] = step
            if brand:
                self.status["current_brand"] = brand
            self.status["last_updated"] = datetime.now().isoformat()
        self.save()
    
    def update_urls(self, discovered: int, processed: int):
        """Update URL discovery/processing progress"""
        with self._lock:
            self.status["urls_discovered"] = discovered
            self.status["urls_processed"] = processed
            if discovered > 0:
                self.status["progress_percent"] = min(100, (processed / discovered) * 100)
            self.status["last_updated"] = datetime.now().isoformat()
        self.save()
    
    def update_brand_start(self, brand_name: str, brand_id: int):
        """Called when starting to process a new brand"""
        with self._lock:
            self.status["current_brand"] = brand_name
            self.status["current_step"] = f"Discovering URLs for {brand_name}..."
            self.status["brand_progress"][brand_name] = {
                "brand_id": brand_id,
                "status": "discovering",
                "urls_discovered": 0,
                "documents_ingested": 0,
                "start_time": datetime.now().isoformat()
            }
        self.save()
    
    def update_urls_discovered(self, brand_name: str, count: int):
        """Update URL discovery count for a brand"""
        with self._lock:
            self.status["urls_discovered"] = count
            self.status["current_step"] = f"Discovered {count} URLs for {brand_name}, processing..."
            if brand_name in self.status["brand_progress"]:
                self.status["brand_progress"][brand_name]["urls_discovered"] = count
                self.status["brand_progress"][brand_name]["status"] = "processing"
        self.save()
    
    def update_document_count(self, brand: str, count: int):
        """Update document count for a brand"""
        with self._lock:
            self.status["documents_by_brand"][brand] = count
            self.status["total_documents"] = sum(self.status["documents_by_brand"].values())
            self.status["last_updated"] = datetime.now().isoformat()
            
            if brand in self.status["brand_progress"]:
                self.status["brand_progress"][brand]["documents_ingested"] = count
        self.save()
    
    def update_brand_complete(self, brand_name: str, total_docs: int):
        """Mark a brand as complete"""
        with self._lock:
            if brand_name in self.status["brand_progress"]:
                self.status["brand_progress"][brand_name]["status"] = "complete"
                self.status["brand_progress"][brand_name]["documents_ingested"] = total_docs
                # Force 100% completion for UI
                self.status["brand_progress"][brand_name]["urls_discovered"] = total_docs
                self.status["brand_progress"][brand_name]["end_time"] = datetime.now().isoformat()
            
            self.status["current_step"] = f"✅ {brand_name} complete ({total_docs} documents)"
        self.save()
    
    def add_error(self, error: str):
        """Add an error to the list"""
        with self._lock:
            self.status["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "message": error
            })
        self.save()
    
    def complete(self):
        """Mark ingestion as complete"""
        with self._lock:
            self.status["is_running"] = False
            self.status["progress_percent"] = 100.0
            self.status["current_step"] = "✅ Comprehensive ingestion complete!"
            self.status["estimated_completion"] = datetime.now().isoformat()
            self.status["last_updated"] = datetime.now().isoformat()
        self.save()
    
    def reset(self):
        """Reset tracker"""
        with self._lock:
            self.status = {
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
            }
        self.save()
    
    def save(self):
        """Persist status to JSON file"""
        try:
            with self._lock:
                with open(INGESTION_STATUS_FILE, 'w') as f:
                    json.dump(self.status, f, indent=2)
        except Exception as e:
            print(f"Failed to save ingestion status: {e}")


# Global tracker instance
tracker = IngestionTracker()
